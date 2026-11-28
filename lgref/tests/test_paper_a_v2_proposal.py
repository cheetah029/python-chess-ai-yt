"""Every number in the V2 proposal is recomputed from the saved
development runs, and the proposal reasons from development data only.

Issue #411. The user's rule: a game is spent only when LGREF is tuned on
it, so a proposal that cites a test-set result as a reason would spend
those games. The last tests check that no test game is named outside the
section that lists the evidence deliberately not used.
"""

import collections
import gzip
import json
import os
import re

import pytest

from lgref.bench import report

REPO = os.path.join(os.path.dirname(__file__), '..', '..')
DOC = os.path.join(REPO, 'docs', 'paper-a', 'lgref-v2-proposal.md')
RUNS = os.path.join(REPO, 'docs', 'paper-a', 'runs')

FINE = ('singletons', 'name_tokens', 'link_communities')


def _text():
    with open(DOC) as handle:
        return handle.read()


@pytest.fixture(scope='module')
def exp1():
    with open(os.path.join(RUNS, 'exp1_dev.json')) as handle:
        return json.load(handle)


@pytest.fixture(scope='module')
def draws():
    with gzip.open(os.path.join(RUNS, 'draws_exp1_dev.json.gz'),
                   'rt') as handle:
        return json.load(handle)


def _closest(record, procedure):
    """{method: {(game, change): exactness}} over the targeted rules."""
    out = collections.defaultdict(dict)
    targeted = set(report._targeted(record))
    for (game, method, change), (_row, ab) in report.closest_ablation(
            record, procedure).items():
        if (game, change) in targeted:
            out[method][(game, change)] = ab['exactness']
    return out


def _exact(values):
    return {rule for rule, x in values.items() if x == 0}


def test_the_run_is_the_development_set(exp1):
    assert exp1['split'] == 'dev'
    assert exp1['games'] == ['tictactoe', 'nim', 'corridor',
                             'breakthrough5', 'othello4', 'dropthree',
                             'montyhall']
    assert len(report._targeted(exp1)) == 12
    assert not set(exp1['games']) & set(_test_games())


def test_e1_fine_groups_are_exact_on_the_same_seven_rules(exp1, draws):
    closest = _closest(exp1, 'delete_group')
    sets = {m: _exact(closest[m]) for m in FINE}
    assert all(len(s) == 7 for s in sets.values())
    assert sets['singletons'] == sets['name_tokens'] \
        == sets['link_communities']
    seven = sets['singletons']
    assert {c for _g, c in seven} == {
        'no_capture', 'no_diagonal_move', 'no_far_row_win',
        'no_column_line', 'no_diagonal_line', 'take_one_only', 'no_flip'}
    lgref = _exact(closest['lgref'])
    assert lgref == {('tictactoe', 'no_diagonal_line')} and lgref <= seven
    _counts, mean, (low, high), n = report.draws_summary(draws,
                                                         'delete_group')
    assert n == 12
    assert '| V0 (30 draws) | {:.2f} [{:.2f}, {:.2f}] |'.format(
        mean, low, high) in _text()
    assert '| V0 (30 draws) | 0.27 [0.13, 0.43] |' in _text()


def test_e2_every_development_reference_touches_one_to_three(exp1):
    sizes = [len(exp1['setup'][g]['changes'][c]['touched'])
             for g, c in report._targeted(exp1)]
    assert min(sizes) == 1 and max(sizes) == 3


def test_e3_the_ownership_split(exp1):
    own = _closest(exp1, 'ownership')
    dele = _closest(exp1, 'delete_group')
    assert len(_exact(own['singletons'])) == 1
    assert len(_exact(dele['singletons'])) == 7
    blocking = ('corridor', 'no_blocking')
    assert own['name_tokens'][blocking] == 0
    assert all(values.get(blocking) != 0 for values in dele.values())
    seven = _exact(dele['singletons'])
    outside = set()
    for closest in (own, dele):
        for values in closest.values():
            outside |= _exact(values) - seven
    assert outside == {blocking}
    assert len(own['lgref']) == 10 and len(dele['lgref']) == 7
    summary = report.ablation_summary(exp1, 'ownership')['lgref']
    assert (summary['repaired'], summary['repaired_exact']) == (7, 0)


def test_e4_link_communities_never_beat_singletons(exp1):
    for procedure in ('ownership', 'delete_group'):
        closest = _closest(exp1, procedure)
        for rule in report._targeted(exp1):
            rule = tuple(rule)
            link = closest['link_communities'].get(rule)
            single = closest['singletons'].get(rule)
            assert single is not None
            assert link is None or link >= single, (procedure, rule)


def test_e5_consistency_and_leiden():
    with open(os.path.join(RUNS, 'exp4_dev.json')) as handle:
        rows = json.load(handle)['rows']
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in rows:
        per[row['method']][row['game']].append(row['f1'])
    text = _text()
    labels = {'singletons': 'singletons', 'name_tokens': 'name_tokens',
              'lgref': 'V1 (`lgref`)', 'link_communities':
              'link_communities', 'leiden': 'leiden',
              'louvain_hard': 'louvain_hard', 'random_matched': 'V0'}
    for method, label in labels.items():
        games = per[method]
        assert len(games) == 7
        mean = sum(sum(v) / len(v) for v in games.values()) / len(games)
        assert '| {} | {:.3f} |'.format(label, mean) in text, method
    assert len({r['rewrite'] for r in rows}) == 6
    assert {r['seed'] for r in rows if r['method'] == 'lgref'} \
        == set(range(5))


def test_e6_attempt_counts(exp1):
    counts = collections.Counter(
        r['method'] for r in exp1['rows'] if r['procedure'] == 'ownership')
    text = _text()
    assert (counts['singletons'], counts['name_tokens'],
            counts['link_communities'], counts['lgref'],
            counts['random_matched']) == (251, 79, 83, 40, 40)
    assert 'singletons attempt 251' in text and 'V1 40' in text


def test_e7_four_rules_no_method_reaches(exp1):
    reached = set()
    for procedure in ('ownership', 'delete_group'):
        for values in _closest(exp1, procedure).values():
            reached |= _exact(values)
    missing = {c for _g, c in set(map(tuple, report._targeted(exp1)))
               - reached}
    assert missing == {'last_taker_wins', 'no_tempo', 'place_anywhere',
                       'end_on_pass'}


# ---- the proposal reasons from development data only ----------------------

def _test_games():
    with open(os.path.join(RUNS, 'exp1_test.json')) as handle:
        return json.load(handle)['games']


def test_no_test_game_is_named_outside_the_unused_evidence_section():
    text = _text()
    start = text.index('## Evidence deliberately not used')
    end = text.index('## How V2 would be evaluated')
    outside = text[:start] + text[end:]
    names = set(_test_games()) | {'checkers', 'canjump', 'synth', 'kalah',
                                  'skirmish', 'hex', 'chomp', 'poker'}
    for name in names:
        stem = re.escape(name.split('_')[0])
        assert not re.search(r'(?i)\b' + stem, outside), name


def test_every_component_is_listed_as_development_only():
    text = _text()
    table = text[text.index('**Which evidence was development-only.**'):
                 text.index('## How V2 would be evaluated')]
    for component in re.findall(r'^\*\*(C\d)\. ', text, flags=re.MULTILINE):
        row = [line for line in table.splitlines()
               if line.startswith('| {} '.format(component))]
        assert len(row) == 1 and row[0].endswith('| development only |')


def test_the_proposal_says_nothing_was_implemented():
    assert '**This is a proposal only.**' in _text()


# ---- E8: the accounting tables (lgref.bench.v2_evidence) -------------------

def test_the_accounting_tables_are_reproduced_unchanged():
    from lgref.bench import v2_evidence
    text = _text()
    body = text[text.index('<!-- accounting:begin -->\n')
                + len('<!-- accounting:begin -->\n'):
                text.index('\n<!-- accounting:end -->')]
    assert body == v2_evidence.build()


def test_every_exact_rule_is_reached_by_a_kept_component(exp1):
    from lgref.bench import v2_evidence
    exact = v2_evidence.exact_rules(exp1)
    rules = set().union(*exact.values())
    assert len(rules) == 8
    for rule in rules:
        assert v2_evidence.component(rule, exact) is not None, rule
    assert 'NOT' not in v2_evidence.build()


def test_the_component_claims_rest_on_what_they_say(exp1):
    """A rule credited to C1 is exact for singletons under deletion; one
    credited to C3 + C4 is exact for name tokens under ownership."""
    from lgref.bench import v2_evidence
    exact = v2_evidence.exact_rules(exp1)
    for rule in set().union(*exact.values()):
        got = v2_evidence.component(rule, exact)
        if got.startswith('C1'):
            assert rule in exact[('singletons', 'delete_group')]
        else:
            assert rule in exact[('name_tokens', 'ownership')]


def test_link_communities_add_nothing_beyond_singletons(exp1):
    from lgref.bench import v2_evidence
    exact = v2_evidence.exact_rules(exp1)
    for procedure in ('ownership', 'delete_group'):
        assert exact[('link_communities', procedure)] \
            <= exact[('singletons', procedure)] | exact[
                ('singletons', 'delete_group')]
    assert exact[('link_communities', 'delete_group')] \
        == exact[('singletons', 'delete_group')]
    assert v2_evidence.overlap_check(exp1) == []


def test_louvain_hard_extra_rule_and_leiden_numbers(exp1):
    from lgref.bench import v2_evidence
    exact = v2_evidence.exact_rules(exp1)
    extra = exact[('louvain_hard', 'delete_group')] \
        - exact[('lgref', 'delete_group')]
    assert extra == {('nim', 'take_one_only')}
    assert extra <= exact[('singletons', 'delete_group')]
    assert '`take_one_only`. Single statements are exact on' in _text()
    for method in ('leiden', 'leiden_hard'):
        assert (len(exact[(method, 'ownership')]),
                len(exact[(method, 'delete_group')])) == (0, 1)
    assert (len(exact[('lgref', 'ownership')]),
            len(exact[('lgref', 'delete_group')])) == (1, 1)


def test_every_three_decimal_number_in_the_text_is_a_tested_value(exp1):
    """Numbers quoted in prose (e.g. Leiden's 0.954) must be ones the
    generated accounting table or the tested E5 table carries."""
    from lgref.bench import v2_evidence
    cons = v2_evidence.consistency(v2_evidence.load()[2])
    for name in ('pf_exp4_dev.json', 'po_exp4_dev.json'):
        with open(os.path.join(RUNS, name)) as handle:
            cons.update(v2_evidence.consistency(json.load(handle)))
    allowed = {'{:.3f}'.format(x) for x in cons.values()}
    allowed.add('0.045')  # dev BCubed of #394, cited from results-dev.md
    for number in re.findall(r'(?<![\d.])\d\.\d{3}(?!\d)', _text()):
        assert number in allowed, number


# ---- S1, S2: the after-the-fact ratings (lgref.bench.pairwise_review) ----

def _between(name):
    text = _text()
    begin = '<!-- {}:begin -->\n'.format(name)
    return text[text.index(begin) + len(begin):
                text.index('\n<!-- {}:end -->'.format(name))]


def test_the_rating_tables_are_reproduced_unchanged():
    from lgref.bench import pairwise_review as pr
    assert _between('absolute') == pr.absolute_table()
    assert _between('pairwise') == pr.tally_table()


def test_the_pairwise_packets_are_blind_and_dev_only():
    from lgref.bench import pairwise_review as pr
    from lgref.bench.methods import METHODS
    assert sorted(os.listdir(pr.PAIR_DIR)) == sorted(pr.DEV_GAMES)
    # ('random' alone is not checked: Monty Hall's rules use the word)
    names = set(METHODS) | set(pr.OTHERS) | {'lgref', 'Louvain', 'Leiden'}
    for game in pr.DEV_GAMES:
        with open(os.path.join(pr.PAIR_DIR, game, 'packet.md')) as h:
            packet = h.read()
        for name in names:
            assert not re.search(r'(?i)\b{}\b'.format(name), packet), (
                game, name)
        review, key = pr.load(game)
        assert set(review) == set(key['comparisons'])
        shown = {e['method'] for e in key['comparisons'].values()}
        assert shown | set(key['identical']) == set(pr.OTHERS)
        assert not shown & set(key['identical'])
        sides = {e['lgref'] for e in key['comparisons'].values()}
        assert sides == {'A', 'B'}, game  # the order really varies


@pytest.mark.parametrize('game', ['tictactoe', 'nim'])
def test_a_packet_is_what_the_builder_writes(game):
    from lgref.bench import pairwise_review as pr
    text, key = pr.build(game, pr.groupings_for(game))
    with open(os.path.join(pr.PAIR_DIR, game, 'packet.md')) as h:
        assert h.read() == text + '\n'
    with open(os.path.join(pr.PAIR_DIR, game, 'key.json')) as h:
        assert json.load(h) == key


def test_outcomes_on_a_hand_built_key():
    from lgref.bench import pairwise_review as pr
    key = {'comparisons': {'P1': {'method': 'x', 'lgref': 'A'},
                           'P2': {'method': 'y', 'lgref': 'B'},
                           'P3': {'method': 'z', 'lgref': 'A'}},
           'identical': ['w']}
    review = {'P1': {'verdict': 'A'}, 'P2': {'verdict': 'a'},
              'P3': {'verdict': 'Tie'}}
    assert pr.outcomes(review, key) == {
        'x': 'lgref better', 'y': 'other better', 'z': 'tie',
        'w': 'identical'}
    with pytest.raises(ValueError):
        pr.outcomes({'P1': {'verdict': 'C'}, 'P2': review['P2'],
                     'P3': review['P3']}, key)


def test_the_prose_counts_follow_the_tallies():
    from lgref.bench import pairwise_review as pr
    cells = pr.tally()

    def count(method, outcome):
        return sum(1 for v in cells[method].values() if v == outcome)
    pf = 'lgref_postfreeze_noterminal'
    assert (count(pf, 'other better'), count(pf, 'lgref better'),
            count(pf, 'identical')) == (4, 0, 3)
    for method in ('louvain_hard', 'leiden_hard'):
        assert (count(method, 'other better'),
                count(method, 'lgref better')) == (3, 4)
        assert cells[method]['breakthrough5'] == 'other better'
    assert (count('link_communities', 'other better'),
            count('link_communities', 'lgref better')) == (2, 5)
    assert count('singletons', 'lgref better') == 7
    assert (count('leiden', 'identical'), count('leiden', 'tie'),
            count('leiden', 'lgref better')) == (5, 1, 1)
    assert count('components', 'other better') == 1
    assert cells['components']['nim'] == 'other better'
    shown = sum(1 for m in cells for v in cells[m].values()
                if v != 'identical')
    same = sum(1 for m in cells for v in cells[m].values()
               if v == 'identical')
    assert (shown, same) == (69, 8)
    text = _text()
    assert '7 reviewers rated 69\ncomparisons, and 8 pairs' in text
    assert 'rated better on all 4' in text and 'win 3 of 7 and lose 4' \
        in text and 'win 2 of 7 (tic-tac-toe, Nim) and lose 5' in text


def test_the_terminal_edge_off_variant_equals_v1_objectively_on_dev(exp1):
    from lgref.bench import v2_evidence
    with open(os.path.join(RUNS, 'pf_exp1_dev.json')) as handle:
        pf = json.load(handle)
    name = 'lgref_postfreeze_noterminal'
    mine, base = v2_evidence.exact_rules(pf), v2_evidence.exact_rules(exp1)
    for procedure in ('ownership', 'delete_group'):
        assert mine[(name, procedure)] == base[('lgref', procedure)]
        assert report.ablation_summary(pf, procedure)[name]['n_found'] \
            == report.ablation_summary(exp1, procedure)['lgref']['n_found']
    assert (len(base[('lgref', 'ownership')]),
            report.ablation_summary(exp1, 'ownership')['lgref']['n_found'],
            report.ablation_summary(exp1, 'delete_group')['lgref'][
                'n_found']) == (1, 10, 7)


# ---- S3, S4: one fresh reviewer per pair; overlap isolated ---------------

def test_the_protocol_table_is_reproduced_unchanged():
    from lgref.bench import pairwise_review as pr
    assert _between('protocols') == pr.protocol_table()


def test_the_per_pair_packets_are_blind_complete_and_rebuildable():
    from lgref.bench import pairwise_review as pr
    from lgref.bench.methods import METHODS, RATING_ONLY
    names = (set(METHODS) | set(pr.OTHERS) | set(RATING_ONLY)
             | {'lgref', 'Louvain', 'Leiden'})
    shown = 0
    for game in pr.DEV_GAMES:
        for method in pr.OTHERS + pr.SINGLE_EXTRA:
            folder = pr.single_folder(game, method)
            assert not any(n in folder for n in names), folder
            with open(os.path.join(folder, 'key.json')) as h:
                key = json.load(h)
            assert key['method'] == method
            if key['identical']:
                assert not os.path.exists(os.path.join(folder,
                                                       'packet.md'))
                continue
            shown += 1
            with open(os.path.join(folder, 'packet.md')) as h:
                packet = h.read()
            assert packet.count('## Comparison ') == 1
            for name in names:
                assert not re.search(r'(?i)\b{}\b'.format(name), packet)
            assert pr.single_outcome(game, method) != 'identical'
    assert shown == 76


@pytest.mark.parametrize('game', ['nim'])
def test_a_per_pair_packet_is_what_the_builder_writes(game):
    from lgref.bench import pairwise_review as pr
    groupings = pr.groupings_for(game)
    for method in pr.OTHERS + pr.SINGLE_EXTRA:
        text, key = pr.build_single(game, groupings, method)
        folder = pr.single_folder(game, method)
        with open(os.path.join(folder, 'key.json')) as h:
            assert json.load(h) == key
        if text is not None:
            with open(os.path.join(folder, 'packet.md')) as h:
                assert h.read() == text + '\n'
        # the A/B side is the per-game protocol's
        _review, per_game = pr.load(game)
        for entry in per_game['comparisons'].values():
            if entry['method'] == method:
                assert entry['lgref'] == key['lgref']


def test_the_per_pair_prose_follows_the_tallies():
    from lgref.bench import pairwise_review as pr
    per_game = pr.tally()
    per_pair = pr.single_tally()
    changed = [(m, g) for m in pr.OTHERS for g in pr.DEV_GAMES
               if per_game[m][g] != per_pair[m][g]]
    away = [(m, g) for m, g in changed
            if per_game[m][g] == 'lgref better']
    assert (len(changed), len(away)) == (9, 8)

    def count(method, outcome):
        return sum(1 for v in per_pair[method].values() if v == outcome)
    for method, want in (('name_tokens', (5, 2)),
                         ('link_communities', (4, 3)),
                         ('louvain_hard', (4, 3)),
                         ('lgref_postfreeze_noterminal', (4, 0)),
                         ('dependency_louvain', (1, 6)),
                         ('lgref_plus_overlap', (0, 7))):
        assert (count(method, 'other better'),
                count(method, 'lgref better')) == want, method
    for method in ('singletons', 'one_group', 'random_matched'):
        assert count(method, 'lgref better') == 7
    text = _text()
    assert '9\n  verdicts changed between protocols, 8 of them away' in text
    assert 'LGREF better on all 7 games' in text


def test_plus_overlap_is_v1_plus_shared_members_only(exp1):
    from lgref.bench import methods as M
    from lgref.bench.catalog import game_path
    from lgref.identify.clauses import load
    added = []
    for game in ('tictactoe', 'nim', 'corridor', 'breakthrough5',
                 'othello4', 'dropthree', 'montyhall'):
        nodes = load(game_path(game))
        base, more = M.lgref(nodes, 0), M.run('lgref_plus_overlap', nodes, 0)
        assert more.core == base.core
        assert len(more.groups) == len(base.groups)
        assert all(a <= b for a, b in zip(base.groups, more.groups))
        extra = sum(len(b) - len(a)
                    for a, b in zip(base.groups, more.groups))
        assert extra == more.info['added']
        added.append(extra)
    assert (min(added), max(added)) == (9, 26)
    assert 'adds 9 to 26 memberships' in _text()
    assert M.PLUS_OVERLAP_SHARE == 0.15


def test_plus_overlap_equals_v1_objectively_on_dev(exp1):
    from lgref.bench import v2_evidence
    with open(os.path.join(RUNS, 'po_exp1_dev.json')) as handle:
        po = json.load(handle)
    name = 'lgref_plus_overlap'
    for procedure in ('ownership', 'delete_group'):
        mine = v2_evidence.closest(po, procedure)[name]
        base = v2_evidence.closest(exp1, procedure)['lgref']
        assert mine == base
