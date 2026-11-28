"""A blind, side-by-side rating of LGREF's grouping against each other
method's: a SUBJECTIVE, after-the-fact metric (#411).

WHY. The user (2026-11-27) separates two kinds of subjective evidence:
(a) agreement with a hand-written reference grouping (BCubed F1), weak
because many groupings are valid and the reference is one of them; and
(b) an after-the-fact rating, in which a reviewer looks at two actual
groupings of the same game and says which is better and why. (b) removes
the "which reference" confounder, and the user prefers it. This module
builds (b) as a PAIRWISE comparison, for the development games only.

BLIND. Each pair is shown as grouping A and grouping B, in an order drawn
per (game, method) from a seeded generator; the method names are never
in the packet. Groups the two groupings share are listed once, as
common, so the reviewer looks at what differs. The key (which side is
LGREF) is written apart and never shown. One fresh reviewer agent per
game rates every pair of that game, as the earlier blind review did, and
answers in JSON. A pair whose two groupings are identical is not shown:
it is recorded as "identical", never as a rated tie.

    python -m lgref.bench.pairwise_review GAME...   # write the packets
    python -m lgref.bench.pairwise_review --tally   # the tally table
"""

import hashlib
import json
import os
import random
import re

from lgref.bench import annotation

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PAIR_DIR = os.path.join(REPO, 'docs', 'paper-a', 'review-pairwise')

DEV_GAMES = ('tictactoe', 'nim', 'corridor', 'breakthrough5', 'othello4',
             'dropthree', 'montyhall')

#: Every method compared with LGREF: the baselines, V0 (draw 0, the
#: grouping the runs scored) and the post-freeze variant.
OTHERS = ('louvain_hard', 'leiden', 'leiden_hard', 'link_communities',
          'dependency_louvain', 'components', 'name_tokens', 'singletons',
          'one_group', 'random_matched', 'lgref_postfreeze_noterminal')

#: At most this many differing groups get a reason each.
MAX_REASONS = 12

PROMPT = """\
You are comparing two ways of dividing the statements of a game
description into RULES -- the parts of a game a player would name when
explaining it (how a piece moves, how a capture works, when the game
ends, who wins). Each comparison below shows two groupings of the same
statements, A and B, produced automatically. Groups that A and B share
are listed once as COMMON; then the groups found only in A, and only in
B. A statement may sit in several groups; statements in no group are
listed as ungrouped.

For EVERY comparison, decide which grouping divides the game into its
rules better, and is easier to read: "A", "B" or "tie". Then give a
one-line reason (at most 20 words) for each group found only in A or only
in B, saying whether that difference helps or hurts. If a side has more
than {max_reasons} such groups, comment on the {max_reasons} that matter
most and say how many you skipped. Judge each comparison on its own; do
not guess how the groupings were made.

Answer from this text alone: do not read files, search, or run tools,
except to write your answer where the instructions you were given say.
Your answer is ONE JSON object and nothing else, of this shape:

{{"comparisons": {{"P1": {{"verdict": "A", "reason": "<= 30 words",
                         "differences": [{{"group": "A3", "reason": "..."}},
                                         {{"group": "B1", "reason": "..."}}],
                         "skipped": 0}},
                  "P2": {{...}}}}}}
""".format(max_reasons=MAX_REASONS)


def _canon(grouping):
    ids = grouping.node_ids
    index = {n: i for i, n in enumerate(ids)}
    return [tuple(sorted(index[n] for n in g)) for g in grouping.groups], \
        sorted(index[n] for n in grouping.unclustered())


def _order_seed(game, method, seed):
    digest = hashlib.sha256('{}|{}|{}'.format(game, method, seed)
                            .encode()).hexdigest()
    return int(digest[:12], 16)


def pair_section(label, lgref, other, lgref_first):
    """The text of one comparison, and the side LGREF is on."""
    a, b = (lgref, other) if lgref_first else (other, lgref)
    groups_a, free_a = a
    groups_b, free_b = b
    common = [g for g in dict.fromkeys(groups_a) if g in set(groups_b)]
    only_a = [g for g in groups_a if g not in set(common)]
    only_b = [g for g in groups_b if g not in set(common)]
    lines = ['## Comparison {}'.format(label), '',
             'A has {} groups, B has {}.'.format(
                 len(groups_a), len(groups_b)), '']
    lines.append('COMMON to A and B:')
    for number, g in enumerate(common, 1):
        lines.append('- C{}: statements {}'.format(
            number, ', '.join(map(str, g))))
    if not common:
        lines.append('- none')
    for side, only, free in (('A', only_a, free_a), ('B', only_b, free_b)):
        lines += ['', 'Only in {}:'.format(side)]
        for number, g in enumerate(only, 1):
            lines.append('- {}{}: statements {}'.format(
                side, number, ', '.join(map(str, g))))
        if not only:
            lines.append('- none')
        if free:
            lines.append('- ungrouped in {}: statements {}'.format(
                side, ', '.join(map(str, free))))
    lines.append('')
    return '\n'.join(lines), ('A' if lgref_first else 'B')


def build(game, groupings, seed=0):
    """(packet text, key). `groupings` maps method -> Grouping and must
    hold 'lgref'. The key records, per comparison, the method and which
    side LGREF is on; identical pairs are listed in the key only."""
    statements = annotation.statements(game)
    base = _canon(groupings['lgref'])
    lines = [PROMPT, '', '## The game', '', annotation.RULES[game], '',
             '## The statements', '', '```']
    for index, text in statements:
        lines.append('{:>3}  {}'.format(index, text))
    lines += ['```', '']
    key = {'comparisons': {}, 'identical': []}
    methods = [m for m in OTHERS if m in groupings]
    random.Random(seed).shuffle(methods)  # nosec B311: blinding only
    number = 0
    for method in methods:
        other = _canon(groupings[method])
        if sorted(other[0]) == sorted(base[0]) and other[1] == base[1]:
            key['identical'].append(method)
            continue
        number += 1
        rng = random.Random(_order_seed(game, method, seed))  # nosec B311
        label = 'P{}'.format(number)
        text, side = pair_section(label, base, other, rng.random() < 0.5)
        lines.append(text)
        key['comparisons'][label] = {'method': method, 'lgref': side}
    key['identical'].sort()
    return '\n'.join(lines), key


def parse(text):
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        raise ValueError('no JSON object in the review')
    return json.loads(match.group(0))['comparisons']


def outcomes(review, key):
    """{method: 'other better' | 'lgref better' | 'tie' | 'identical'}."""
    out = {m: 'identical' for m in key['identical']}
    for label, entry in key['comparisons'].items():
        verdict = review[label]['verdict'].strip().upper()
        if verdict == 'TIE':
            out[entry['method']] = 'tie'
        elif verdict == entry['lgref']:
            out[entry['method']] = 'lgref better'
        elif verdict in ('A', 'B'):
            out[entry['method']] = 'other better'
        else:
            raise ValueError('verdict {!r}'.format(verdict))
    return out


def load(game, pair_dir=None):
    folder = os.path.join(pair_dir or PAIR_DIR, game)
    with open(os.path.join(folder, 'key.json')) as handle:
        key = json.load(handle)
    with open(os.path.join(folder, 'review.json')) as handle:
        review = parse(handle.read())
    return review, key


def tally(games=DEV_GAMES, pair_dir=None):
    """{method: {game: outcome}}."""
    out = {m: {} for m in OTHERS}
    for game in games:
        review, key = load(game, pair_dir)
        for method, result in outcomes(review, key).items():
            out[method][game] = result
    return out


SHORT = {'other better': 'O', 'lgref better': 'L', 'tie': 'T',
         'identical': '='}


def tally_table(games=DEV_GAMES, pair_dir=None):
    """Markdown: per method, the outcome on each development game and the
    count: other better / tie / LGREF better (identical apart)."""
    cells = tally(games, pair_dir)
    lines = ['| method | ' + ' | '.join(games) + ' | other better | tie | '
             'LGREF better | identical |', '|---' * (len(games) + 5) + '|']
    for method in OTHERS:
        row = cells[method]
        counts = [sum(1 for g in games if row[g] == k)
                  for k in ('other better', 'tie', 'lgref better',
                            'identical')]
        lines.append('| {} | {} | {} |'.format(
            method, ' | '.join(SHORT[row[g]] for g in games),
            ' | '.join(map(str, counts))))
    return '\n'.join(lines)


def write_packet(game, groupings, seed=0, pair_dir=None):
    folder = os.path.join(pair_dir or PAIR_DIR, game)
    os.makedirs(folder, exist_ok=True)
    text, key = build(game, groupings, seed)
    with open(os.path.join(folder, 'packet.md'), 'w') as handle:
        handle.write(text + '\n')
    with open(os.path.join(folder, 'key.json'), 'w') as handle:
        json.dump(key, handle, indent=1, sort_keys=True)
    return folder


def groupings_for(game, seed=0):
    from lgref.bench.catalog import game_path
    from lgref.bench.experiments import grouping_for
    from lgref.identify.clauses import load as load_nodes

    nodes = load_nodes(game_path(game))
    return {m: grouping_for(m, nodes, seed)
            for m in ('lgref',) + OTHERS + SINGLE_EXTRA}


def main(argv=None):
    import sys
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] == '--tally':
        print(tally_table())
        return
    if argv and argv[0] == '--singles':
        for game in argv[1:]:
            print('\n'.join(write_singles(game, groupings_for(game))))
        return
    for game in argv:
        print(write_packet(game, groupings_for(game)))


def absolute_table(games=DEV_GAMES, review_dir=None):
    """The earlier blind review (`lgref.bench.review`, one score per
    grouping, 1-5) read as kind-(b) evidence against LGREF: per method,
    on how many development games its overall score was higher, equal or
    lower than LGREF's. The post-freeze variant was not in that review."""
    import json as _json

    from lgref.bench import review as _review

    review_dir = review_dir or _review.REVIEW_DIR
    cells = {}
    for game in games:
        folder = os.path.join(review_dir, game)
        with open(os.path.join(folder, 'review.json')) as handle:
            reviewed = _review.parse(handle.read())
        with open(os.path.join(folder, 'key.json')) as handle:
            key = _json.load(handle)
        cells[game] = _review.summarize(reviewed, key)
    lines = ['| method | higher than LGREF | equal | lower | same grouping '
             'as LGREF (one score) |', '|---|---|---|---|---|']
    for method in OTHERS:
        if any(method not in cells[g] for g in games):
            continue
        counts = [0, 0, 0, 0]
        for g in games:
            a, b = cells[g][method], cells[g]['lgref']
            if a['label'] == b['label']:
                counts[3] += 1
            elif a['overall'] > b['overall']:
                counts[0] += 1
            elif a['overall'] == b['overall']:
                counts[1] += 1
            else:
                counts[2] += 1
        lines.append('| {} | {} |'.format(method,
                                          ' | '.join(map(str, counts))))
    return '\n'.join(lines)


# ---- the per-pair protocol: one fresh reviewer per comparison ------------

#: The per-game protocol shows LGREF's grouping in every pair a reviewer
#: rates, which can anchor the reviewer (the user, 2026-11-27). Here
#: every packet holds ONE comparison, rated by its own fresh reviewer,
#: so each reviewer sees LGREF's grouping once. The A/B side of each
#: pair is the per-game protocol's (`_order_seed`), so the two protocols
#: differ only in who rates what.
SINGLE_DIR = os.path.join(REPO, 'docs', 'paper-a', 'review-pairwise-single')

#: Rated only in the per-pair protocol: LGREF plus overlap (#411).
SINGLE_EXTRA = ('lgref_plus_overlap',)


def build_single(game, groupings, method, seed=0):
    """(packet text, key) for the one comparison of LGREF with `method`,
    or (None, key) when the two groupings are identical."""
    statements = annotation.statements(game)
    base = _canon(groupings['lgref'])
    other = _canon(groupings[method])
    if sorted(other[0]) == sorted(base[0]) and other[1] == base[1]:
        return None, {'method': method, 'identical': True}
    lines = [PROMPT, '', '## The game', '', annotation.RULES[game], '',
             '## The statements', '', '```']
    for index, text in statements:
        lines.append('{:>3}  {}'.format(index, text))
    lines += ['```', '']
    rng = random.Random(_order_seed(game, method, seed))  # nosec B311
    text, side = pair_section('P1', base, other, rng.random() < 0.5)
    lines.append(text)
    return '\n'.join(lines), {'method': method, 'identical': False,
                              'lgref': side}


def single_folder(game, method, seed=0, single_dir=None):
    """A comparison's folder. Its name is opaque (a hash), because the
    reviewer is given the packet's path and must not read a method name
    in it; key.json inside says which method it is."""
    digest = hashlib.sha256('pair|{}|{}|{}'.format(game, method, seed)
                            .encode()).hexdigest()[:10]
    return os.path.join(single_dir or SINGLE_DIR, game, 'pair-' + digest)


def write_singles(game, groupings, seed=0, single_dir=None):
    written = []
    for method in OTHERS + SINGLE_EXTRA:
        folder = single_folder(game, method, seed, single_dir)
        text, key = build_single(game, groupings, method, seed)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'key.json'), 'w') as handle:
            json.dump(key, handle, indent=1, sort_keys=True)
        if text is not None:
            with open(os.path.join(folder, 'packet.md'), 'w') as handle:
                handle.write(text + '\n')
            written.append(folder)
    return written


def single_outcome(game, method, single_dir=None):
    folder = single_folder(game, method, 0, single_dir)
    with open(os.path.join(folder, 'key.json')) as handle:
        key = json.load(handle)
    if key['identical']:
        return 'identical'
    with open(os.path.join(folder, 'review.json')) as handle:
        review = parse(handle.read())
    pair = {'comparisons': {'P1': {'method': method,
                                   'lgref': key['lgref']}},
            'identical': []}
    return outcomes(review, pair)[method]


def single_tally(games=DEV_GAMES, methods=None, single_dir=None):
    methods = methods or OTHERS + SINGLE_EXTRA
    return {m: {g: single_outcome(g, m, single_dir) for g in games}
            for m in methods}


def protocol_table(games=DEV_GAMES, pair_dir=None, single_dir=None):
    """Both protocols side by side: per method, other better / tie /
    LGREF better (identical apart) under the per-game protocol and the
    per-pair one, and the games whose verdict differs."""
    per_game = tally(games, pair_dir)
    per_pair = single_tally(games, None, single_dir)

    def counts(row):
        return ' / '.join(str(sum(1 for g in games if row[g] == k))
                          for k in ('other better', 'tie', 'lgref better'))
    lines = ['| method | per game: other / tie / LGREF | per pair: other / '
             'tie / LGREF | identical | verdicts that differ |',
             '|---|---|---|---|---|']
    for method in OTHERS + SINGLE_EXTRA:
        b = per_pair[method]
        a = per_game.get(method)
        same = sum(1 for g in games if b[g] == 'identical')
        if a is None:
            first, changed = 'not rated', 'n/a'
        else:
            first = counts(a)
            diff = ['{} ({} -> {})'.format(g, SHORT[a[g]], SHORT[b[g]])
                    for g in games if a[g] != b[g]]
            changed = ', '.join(diff) if diff else 'none'
        lines.append('| {} | {} | {} | {} | {} |'.format(
            method, first, counts(b), same, changed))
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
