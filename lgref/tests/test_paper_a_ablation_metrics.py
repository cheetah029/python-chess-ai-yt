"""The ablation-based grouping metrics (#363), on hand-built cases whose
answers are known, then end to end on a real game.

Atoms are written by hand: ('legal', state, role, move), ('terminal',
state), ('goal', state, role, value).
"""

import pytest

import lgref  # noqa: F401
from lgref.bench import ablation_metrics as am
from lgref.bench import report


def L(s, move, role='p'):
    return ('legal', s, role, move)


BASE = frozenset({L(0, 'a'), L(0, 'b'), L(1, ('c', '1')), L(1, ('c', '2')),
                  ('terminal', 2), ('goal', 2, 'p', 100)})


def test_identical_ablation_is_exact_with_nothing_else():
    ref = BASE - {L(0, 'a')}
    got = am.compare(ref, ref, BASE)
    assert got['exactness'] == got['collateral'] == got['shortfall'] == 0


def test_exactness_is_collateral_plus_shortfall():
    """atoms(A) sym-diff atoms(R) == changed(A) sym-diff changed(R)."""
    ref = BASE - {L(0, 'a')}
    abl = (BASE - {L(0, 'b')}) | {L(0, 'z')}
    got = am.compare(abl, ref, BASE)
    assert got['exactness'] == got['collateral'] + got['shortfall']
    # A removed b and added z (2 collateral), and kept a (1 shortfall).
    assert (got['collateral'], got['shortfall']) == (2, 1)


def test_over_ablation_is_collateral_not_shortfall():
    ref = BASE - {L(0, 'a')}
    abl = BASE - {L(0, 'a'), L(0, 'b')}
    got = am.compare(abl, ref, BASE)
    assert (got['exactness'], got['collateral'], got['shortfall']) == (
        1, 1, 0)


def test_under_ablation_is_shortfall_not_collateral():
    ref = BASE - {L(0, 'a'), L(0, 'b')}
    abl = BASE - {L(0, 'a')}
    got = am.compare(abl, ref, BASE)
    assert (got['collateral'], got['shortfall']) == (0, 1)


def test_doing_nothing_falls_short_by_the_whole_rule():
    ref = BASE - {L(0, 'a'), L(0, 'b')}
    got = am.compare(BASE, ref, BASE)
    assert got['shortfall'] == 2 and got['collateral'] == 0


def test_ending_and_payoff_counted_apart():
    """Metric 9: a change to the ending is never hidden in legal moves."""
    ref = BASE
    abl = BASE - {('terminal', 2), ('goal', 2, 'p', 100)}
    got = am.compare(abl, ref, BASE)
    assert got['collateral_by_kind'] == {'legal': 0, 'terminal': 1,
                                         'goal': 1, 'next': 0}


def test_collateral_is_attributed_to_the_rules_that_own_it():
    """Rule r1 owns move a, r2 owns move b, nobody owns the ending. An
    ablation of r1 that also removes b and the ending damages r2 once,
    and leaves one unowned atom."""
    owners = {'r1': frozenset({L(0, 'a')}), 'r2': frozenset({L(0, 'b')})}
    ref = BASE - {L(0, 'a')}
    abl = BASE - {L(0, 'a'), L(0, 'b'), ('terminal', 2)}
    got = am.compare(abl, ref, BASE, owners, rule='r1')
    assert got['rules_broken'] == ['r2']
    assert got['damage_by_rule'] == {'r2': 1}
    assert got['collateral_unowned'] == 1


def test_a_rule_is_never_its_own_victim():
    owners = {'r1': frozenset({L(0, 'a'), L(0, 'b')})}
    ref = BASE - {L(0, 'a')}
    abl = BASE - {L(0, 'a'), L(0, 'b')}
    got = am.compare(abl, ref, BASE, owners, rule='r1')
    assert got['rules_broken'] == []


def test_scatter_of_one_action_type_is_focused():
    got = am.scatter({L(1, ('c', '1')), L(1, ('c', '2'))})
    assert got['n_action_types'] == 1
    assert got['concentration'] == 1.0 and got['entropy'] == 0.0


def test_scatter_evenly_over_two_types_has_entropy_one():
    got = am.scatter({L(0, 'a'), L(1, ('c', '1'))})
    assert got['n_action_types'] == 2
    assert got['concentration'] == 0.5
    assert got['entropy'] == pytest.approx(1.0)


def test_scatter_counts_rules_touched():
    owners = {'r1': frozenset({L(0, 'a')}), 'r2': frozenset({L(0, 'b')}),
              'r3': frozenset({('terminal', 9)})}
    got = am.scatter({L(0, 'a'), L(0, 'b')}, owners)
    assert got['n_rules'] == 2


def test_empty_change_has_no_scatter():
    got = am.scatter(set())
    assert got['concentration'] is None and got['n_action_types'] == 0


def test_atoms_of_a_description_that_does_not_load_are_none():
    from lgref.bench.behaviour import Behaviour
    assert am.atoms(Behaviour()) is None


# ---- the verdicts and aggregates -----------------------------------------

def _row(**kw):
    row = {'empty': False, 'valid': True, 'invalid_reason': None,
           'changes': True, 'scatter': {'concentration': 1.0},
           'procedure': 'ownership'}
    row.update(kw)
    return row


@pytest.mark.parametrize('kw,verdict', [
    ({'empty': True}, 'empty (nothing removable)'),
    ({'valid': False, 'invalid_reason': 'does not load: X'},
     'does not compile'),
    ({'valid': False, 'invalid_reason': 'roles changed: [a] -> []'},
     'roles removed'),
    ({'valid': False, 'invalid_reason': 'no legal move for p at the start'},
     'unplayable at the start'),
    ({'valid': False, 'invalid_reason': 'state 3: p has no legal move'},
     'stuck state'),
    ({'valid': False, 'invalid_reason': 'state 3: p has two goal values'},
     'two goal values'),
    ({'valid': False, 'invalid_reason': 'own play: x'},
     'ill-formed in its own play'),
    ({'changes': False}, 'inert (no change)'),
    ({'scatter': {'concentration': 0.4}}, 'unfocused (scattered)'),
    ({}, 'accepted'),
])
def test_every_intervention_gets_one_verdict(kw, verdict):
    assert report.rejection(_row(**kw)) == verdict


def _record():
    base = {'empty': False, 'valid': True, 'invalid_reason': None,
            'changes': True, 'scatter': {'concentration': 1.0},
            'procedure': 'ownership', 'game': 'g', 'method': 'lgref',
            'n_relaxed': 0, 'n_protected': 0}

    def ab(exactness, collateral, shortfall, broken=()):
        return {'ablation': {
            'exactness': exactness, 'collateral': collateral,
            'shortfall': shortfall, 'rules_broken': list(broken),
            'exactness_by_kind': {'legal': exactness, 'terminal': 0,
                                  'goal': 0}}}
    rows = [
        dict(base, group=0, changes_by_ref={'r1': ab(0, 0, 0),
                                            'r2': ab(5, 3, 2, ['r1'])}),
        dict(base, group=1, n_relaxed=1,
             changes_by_ref={'r1': ab(4, 4, 0, ['r2']),
                             'r2': ab(1, 1, 0, ['r1'])}),
        dict(base, group=2, valid=False,
             changes_by_ref={'r1': ab(0, 0, 0), 'r2': ab(0, 0, 0)}),
    ]
    return {'rows': rows, 'games': ['g'],
            'setup': {'g': {'changes': {'r1': {'kind': 'targeted'},
                                        'r2': {'kind': 'targeted'}}}}}


def test_closest_ablation_is_the_valid_one_with_least_exactness():
    closest = report.closest_ablation(_record())
    assert closest[('g', 'lgref', 'r1')][0]['group'] == 0
    assert closest[('g', 'lgref', 'r2')][0]['group'] == 1   # 1 < 5
    # The invalid group 2 would have been exact for both, and is ignored.


def test_an_inert_intervention_is_never_the_closest():
    """Found by the validation pass (#363): an inert row scores exactness
    |changed(R)| with no collateral, and beat every real attempt."""
    record = _record()
    record['rows'].append(dict(record['rows'][0], group=3, changes=False,
                               changes_by_ref={'r1': {'ablation': {
                                   'exactness': 0, 'collateral': 0,
                                   'shortfall': 0}},
                                   'r2': {'ablation': {
                                       'exactness': 0, 'collateral': 0,
                                       'shortfall': 0}}}))
    closest = report.closest_ablation(record)
    assert all(row['group'] != 3 for row, _a in closest.values())


def test_ablation_summary_by_hand():
    cell = report.ablation_summary(_record())['lgref']
    assert cell['n_found'] == 2 and cell['exact'] == 1
    assert cell['broken'] == 1                 # r2's closest has collateral
    assert cell['rules_broken'] == [0, 1]      # fragility mean 0.5
    assert (cell['repaired'], cell['repaired_exact']) == (1, 0)
    assert (cell['unrepaired'], cell['unrepaired_exact']) == (1, 1)


def test_rewrite_stability_by_hand():
    """Metric 10: the same closest numbers after a rewrite count as
    stable; an exact ablation lost to the rewrite is shown."""
    original = _record()
    for row in original['rows']:
        row['empty'] = False
    ab = {'exactness': 0, 'collateral': 0, 'shortfall': 0}
    worse = {'exactness': 3, 'collateral': 1, 'shortfall': 2}
    rewritten = {'rows': [
        {'game': 'g', 'rewrite': 'reorder', 'procedure': 'ownership',
         'group': 0, 'empty': False, 'valid': True, 'changes': True,
         'by_ref': {'r1': ab, 'r2': worse}},
        {'game': 'g', 'rewrite': 'inline', 'procedure': 'ownership',
         'group': 0, 'empty': False, 'valid': True, 'changes': True,
         'by_ref': {'r1': worse, 'r2': worse}},
    ]}
    table = report.rewrite_stability(rewritten, original)
    reorder = next(line for line in table.splitlines()
                   if line.startswith('| reorder |'))
    inline = next(line for line in table.splitlines()
                  if line.startswith('| inline |'))
    # original closest: r1 exact (0,0,0); r2 (1,1,0)
    assert reorder.split('|')[3].strip() == '1'
    assert reorder.split('|')[4].strip() == '1 -> 1'
    assert inline.split('|')[4].strip() == '1 -> 0'


def test_rejected_rules_lists_the_rules_touched():
    from lgref.bench.annotation import Sheet
    record = _record()
    record['rows'][2]['touched'] = [0, 1]
    record['rows'][2]['invalid_reason'] = 'state 1: p has no legal move'
    sheet = Sheet('g', {}, [
        {'index': 0, 'statement': 'a', 'rules': ['move'],
         'ambiguous': False, 'note': ''},
        {'index': 1, 'statement': 'b', 'rules': ['end'],
         'ambiguous': False, 'note': ''}])
    for row in record['rows']:
        row.setdefault('touched', [])
    got = report.rejected_rules(record, {'g': sheet})
    assert got == [('g', 2, 'stuck state', ['end', 'move'])]


def test_scramble_is_undone_inside_successor_states():
    from lgref.bench.experiments import _unmap
    inverse = {'xa': 'cell', 'xb': 'white'}
    atom = ('next', 3, (('xa',), 'noop'),
            frozenset({('xa', '1', 'xb')}))
    assert _unmap(atom, inverse) == ('next', 3, (('cell',), 'noop'),
                                     frozenset({('cell', '1', 'white')}))


def test_metric_10_on_scramble_matches_the_original():
    """End to end on Nim: the scrambled description's closest ablations
    equal the original's, number for number."""
    import json
    from lgref.bench import experiments as X
    rows = X.rewrite_ablation_rows(['nim'])
    original_rows, setup = X.intervention_rows(['nim'], ['lgref'])
    original = {'rows': original_rows, 'setup': setup, 'games': ['nim']}
    record = json.loads(json.dumps({'rows': rows}, default=list))
    table = report.rewrite_stability(record, original)
    line = next(x for x in table.splitlines()
                if x.startswith('| scramble |'))
    found = line.split('|')[2].strip()          # 'k -> k of 2'
    same = line.split('|')[3].strip()
    assert found.split(' -> ')[0] == same
