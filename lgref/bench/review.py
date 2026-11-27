"""A blind Claude review of each method's grouping: a SUBJECTIVE metric.

WHY. A reference grouping written beforehand cannot be the last word
when several groupings of a game are acceptable. So, at the user's
instruction (#358), each method's ACTUAL grouping is shown to a reviewer
-- a fresh Claude agent, never the one that wrote the method -- who
judges how sensible and readable each group is, with a short reason.

WHAT IT IS NOT. This is a stand-in for human accessibility, readability
and general agreement. It is not a factual, empirical or exact
evaluation, and it is reported as SECONDARY. The primary judgement of a
grouping rests on the objective metrics: behavioural intervention
agreement, valid intervention rate, grouping consistency across
encodings, and performance on unseen games (docs/paper-a/protocol.md).

BLIND AND COMPARABLE. One packet per game holds every method's grouping
under a neutral label (`G1`, `G2`, ...), in a seeded random order, with
the same fixed prompt (`PROMPT`) for every game. Methods whose groupings
are identical share one label, so they get one review -- said in the
key, never in the packet. The key (label -> methods) is written
separately and is not shown to the reviewer.

The reviewer answers in JSON; `parse` reads it and `summarize` maps
labels back to methods.
"""

import json
import os
import random
import re

from lgref.bench import annotation

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REVIEW_DIR = os.path.join(REPO, 'docs', 'paper-a', 'review')

PROMPT = """\
You are reviewing ways of dividing the statements of a game description
into RULES -- the parts of a game a player would name when explaining
it (how a piece moves, how a capture works, when the game ends, who
wins). Several groupings of the same statements follow, each produced
automatically. Judge each one on its own; do not rank them against each
other, and do not guess how they were made.

For EVERY group of EVERY grouping give:
  - score: an integer 1-5
      5  clearly one recognisable rule, or a sensible shared piece
         several rules need
      4  mostly one rule, with a stray statement or a missing one
      3  a plausible but loose collection
      2  mostly unrelated statements, or a rule cut into a fragment
         that means little alone
      1  arbitrary
  - reason: at most 20 words.
Then, for each grouping as a whole, an overall score 1-5 (how well it
divides the game into its rules, and how readable the result is) and a
reason of at most 30 words. A statement may sit in several groups; that
is allowed. Statements in no group are listed as ungrouped.

Answer from this text alone: do not read files, search, or run tools.
Reply with ONE JSON object and nothing else, of this shape:

{"groupings": {"G1": {"groups": {"1": {"score": 4, "reason": "..."},
                                 "2": {...}},
                      "overall": {"score": 3, "reason": "..."}},
               "G2": {...}}}
"""


def _canonical(grouping):
    return tuple(sorted(tuple(sorted(g)) for g in grouping.groups))


def build(game, groupings, seed=0):
    """(packet text, key). `groupings` is {method: Grouping}; every
    grouping is over the same statements in `load` order. The key maps
    each label to every method whose grouping it shows."""
    statements = annotation.statements(game)
    distinct = []
    for method in groupings:
        canon = _canonical(groupings[method])
        if canon not in [c for c, _m in distinct]:
            distinct.append((canon, method))
    order = list(range(len(distinct)))
    random.Random(seed).shuffle(order)  # nosec B311: blinding, not security
    lines = [PROMPT, '', '## The game', '', annotation.RULES[game], '',
             '## The statements', '', '```']
    for index, text in statements:
        lines.append('{:>3}  {}'.format(index, text))
    lines += ['```', '']
    label_of = {}
    for position, which in enumerate(order, 1):
        canon, method = distinct[which]
        label = 'G{}'.format(position)
        label_of[canon] = label
        grouping = groupings[method]
        ids = {n: i for i, n in enumerate(grouping.node_ids)}
        lines.append('## Grouping {} ({} groups)'.format(label,
                                                         len(grouping)))
        lines.append('')
        for number, group in enumerate(grouping.groups, 1):
            members = sorted(ids[n] for n in group)
            lines.append('- group {}: statements {}'.format(
                number, ', '.join(str(m) for m in members)))
        ungrouped = sorted(ids[n] for n in grouping.unclustered())
        if ungrouped:
            lines.append('- ungrouped: statements {}'.format(
                ', '.join(str(m) for m in ungrouped)))
        lines.append('')
    key = {}
    for method in groupings:
        key.setdefault(label_of[_canonical(groupings[method])],
                       []).append(method)
    return '\n'.join(lines), key


def parse(text):
    """The reviewer's JSON object, from a reply that may wrap it."""
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        raise ValueError('no JSON object in the review')
    data = json.loads(match.group(0))
    return data['groupings']


def summarize(review, key):
    """{method: {'mean_group': x, 'overall': y, 'n_groups': n}}."""
    out = {}
    for label, methods in key.items():
        entry = review.get(label)
        if entry is None:
            continue
        scores = [int(g['score']) for g in entry['groups'].values()]
        row = {'mean_group': (sum(scores) / float(len(scores))
                              if scores else None),
               'overall': int(entry['overall']['score']),
               'overall_reason': entry['overall'].get('reason', ''),
               'n_groups': len(scores), 'label': label}
        for method in methods:
            out[method] = dict(row)
    return out


def write_packet(game, groupings, seed=0, out_dir=None):
    """Write packet.md (shown to the reviewer) and key.json (not)."""
    out_dir = os.path.join(out_dir or REVIEW_DIR, game)
    os.makedirs(out_dir, exist_ok=True)
    text, key = build(game, groupings, seed)
    with open(os.path.join(out_dir, 'packet.md'), 'w') as handle:
        handle.write(text + '\n')
    with open(os.path.join(out_dir, 'key.json'), 'w') as handle:
        json.dump(key, handle, indent=1, sort_keys=True)
    return out_dir


def table(games, review_dir=None):
    """Markdown: overall score (mean group score) per method and game,
    with a bootstrap interval over games. Reads review.json and key.json
    from each game's folder."""
    from lgref.bench import metrics
    from lgref.bench.methods import METHODS

    review_dir = review_dir or REVIEW_DIR
    cells = {}
    for game in games:
        folder = os.path.join(review_dir, game)
        with open(os.path.join(folder, 'review.json')) as handle:
            reviewed = parse(handle.read())
        with open(os.path.join(folder, 'key.json')) as handle:
            key = json.load(handle)
        cells[game] = summarize(reviewed, key)

    def interval(values):
        mean, low, high = metrics.bootstrap_interval(values)
        if low is None:
            return '{:.2f}'.format(mean)
        return '{:.2f} [{:.2f}, {:.2f}]'.format(mean, low, high)

    lines = ['| method | ' + ' | '.join(games)
             + ' | overall, mean over games [95% CI] '
             '| group score, mean over games [95% CI] |',
             '|---' * (len(games) + 3) + '|']
    for method in METHODS:
        if any(method not in cells[g] for g in games):
            lines.append('| {} | not reviewed on every game |'.format(
                method))
            continue
        overall = [cells[g][method]['overall'] for g in games]
        group = [cells[g][method]['mean_group'] for g in games]
        lines.append('| {} | {} | {} | {} |'.format(
            method, ' | '.join('{} ({:.1f})'.format(
                cells[g][method]['overall'], cells[g][method]['mean_group'])
                for g in games), interval(overall), interval(group)))
    return '\n'.join(lines)


def main(argv=None):
    import sys

    from lgref.bench import methods as _methods
    from lgref.bench.catalog import game_path
    from lgref.bench.experiments import grouping_for
    from lgref.identify.clauses import load

    argv = list(argv if argv else sys.argv[1:])
    if argv and argv[0] == '--table':
        print(table(argv[1:]))
        return
    for game in argv:
        nodes = load(game_path(game))
        groupings = {m: grouping_for(m, nodes, 0) for m in _methods.METHODS}
        print(write_packet(game, groupings))


if __name__ == '__main__':
    main()
