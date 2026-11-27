"""Paper A metrics (#351): extended BCubed, behavioural agreement,
intervention validity, and the bootstrap.

Each metric is checked against a value worked out by hand, and each
"not measured" case is checked to come back as None rather than 0.
"""

import pytest

import lgref  # noqa: F401
from lgref.bench import behaviour as B
from lgref.bench import interventions as IV
from lgref.bench import methods as M
from lgref.bench import metrics
from lgref.bench import probes
from lgref.bench.annotation import reference
from lgref.bench.catalog import game_path
from lgref.identify.clauses import load


def _hard(*groups):
    out = {}
    for label, members in enumerate(groups):
        for item in members:
            out.setdefault(item, set()).add(label)
    return out


# ---- extended BCubed ----------------------------------------------------

def test_bcubed_on_hard_partitions_is_plain_bcubed():
    """Reference {a,b,c} {d,e}; predicted {a,b} {c,d,e}. By hand:
    precision (1 + 1 + 1/3 + 2/3 + 2/3) / 5, recall (2/3 + 2/3 + 1/3 + 1
    + 1) / 5 -- both 11/15."""
    ref = _hard('abc', 'de')
    pred = _hard('ab', 'cde')
    got = metrics.bcubed(pred, ref)
    assert got['precision'] == pytest.approx(11 / 15.0)
    assert got['recall'] == pytest.approx(11 / 15.0)
    assert got['f1'] == pytest.approx(11 / 15.0)


def test_bcubed_perfect_with_overlap():
    ref = {'a': {1}, 'b': {1, 2}, 'c': {2}}
    pred = {'a': {'x'}, 'b': {'x', 'y'}, 'c': {'y'}}
    got = metrics.bcubed(pred, ref)
    assert got['precision'] == got['recall'] == got['f1'] == 1.0


def test_bcubed_penalises_overlap_the_reference_does_not_have():
    """b is put in two groups, the reference has it in one: precision
    falls, recall does not (Amigo et al.'s multiplicity constraint)."""
    ref = {'a': {1}, 'b': {1}, 'c': {2}}
    pred = {'a': {'x'}, 'b': {'x', 'y'}, 'c': {'y'}}
    got = metrics.bcubed(pred, ref)
    assert got['precision'] < 1.0
    assert got['recall'] == 1.0


def test_bcubed_rewards_missing_overlap_only_in_precision():
    """The reference shares b; the method gives it one home. Recall
    falls, precision stays perfect."""
    ref = {'a': {1}, 'b': {1, 2}, 'c': {2}}
    pred = {'a': {'x'}, 'b': {'x'}, 'c': {'y'}}
    got = metrics.bcubed(pred, ref)
    assert got['precision'] == 1.0 and got['recall'] < 1.0


def test_unclustered_costs_recall_only():
    ref = _hard('abc', 'de')
    got = metrics.bcubed({}, ref)
    assert got['precision'] == 1.0
    assert got['recall'] == pytest.approx((1 / 3.0 * 3 + 0.5 * 2) / 5)


def test_one_group_has_full_recall():
    ref = _hard('abc', 'de')
    got = metrics.bcubed({k: {0} for k in 'abcde'}, ref)
    assert got['recall'] == 1.0 and got['precision'] < 1.0


def test_group_names_do_not_matter():
    ref = _hard('abc', 'de')
    one = metrics.bcubed(_hard('ab', 'cde'), ref)
    two = metrics.bcubed({k: {'Q' + str(v)} for k, vs in
                          _hard('ab', 'cde').items() for v in vs}, ref)
    assert one == two


def test_unassigned_reference_statements_are_not_scored():
    ref = {'a': {1}, 'b': {1}, 'z': set()}
    got = metrics.bcubed({'a': {0}, 'b': {0}, 'z': {0}}, ref)
    assert got['n_scored'] == 2 and got['precision'] == 1.0


def test_shared_recovery_is_none_when_nothing_is_shared():
    assert metrics.shared_recovery({'a': {1, 2}}, {'a': {1}}) is None
    assert metrics.shared_recovery({'a': {1, 2}}, {'a': {1, 2}}) == 1.0


def test_score_grouping_on_the_reference_itself_is_perfect():
    nodes = load(game_path('breakthrough5'))
    sheet = reference('breakthrough5')
    ids = [n.node_id for n in nodes]
    groups = {}
    for index, rules in sheet.membership().items():
        for rule in rules:
            groups.setdefault(rule, set()).add(ids[index])
    perfect = M.Grouping('ref', list(groups.values()), ids)
    got = metrics.score_grouping(perfect, sheet, ids)
    assert got['f1'] == pytest.approx(1.0)
    assert got['shared_recovery'] == 1.0


# ---- bootstrap -----------------------------------------------------------

def test_bootstrap_is_seeded_and_collapses_on_constants():
    assert metrics.bootstrap_interval([0.5] * 5) == (0.5, 0.5, 0.5)
    a = metrics.bootstrap_interval([0.1, 0.4, 0.9, 0.2], seed=3)
    b = metrics.bootstrap_interval([0.1, 0.4, 0.9, 0.2], seed=3)
    assert a == b and a[1] < a[0] < a[2]


def test_bootstrap_of_one_game_has_no_interval():
    assert metrics.bootstrap_interval([0.7]) == (0.7, None, None)
    assert metrics.bootstrap_interval([None]) == (None, None, None)


def test_paired_skips_unmeasured_games():
    assert metrics.paired({'g': 0.5, 'h': None}, {'g': 0.2, 'h': 0.1}) \
        == {'g': pytest.approx(0.3)}


# ---- interventions -------------------------------------------------------

def test_delete_group_removes_exactly_the_group():
    nodes = load(game_path('nim'))
    grouping = M.lgref(nodes)
    for item in IV.build(nodes, grouping, 'delete_group'):
        assert item.removed == grouping.groups[item.group]


def test_ownership_procedure_matches_production_ablation():
    """For LGREF's own groups the builder must remove what production
    ablation removes."""
    from lgref.identify.cluster import calibrate_resolution, cluster
    from lgref.identify.graph import ClauseGraph
    from lgref.identify.intervention import removed_by_ablation

    nodes = load(game_path('breakthrough5'))
    graph = ClauseGraph(nodes)
    rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
    want = sorted(sorted(removed_by_ablation(r)[0]) for r in rules)
    got = sorted(sorted(i.removed)
                 for i in IV.build(nodes, M.lgref(nodes)))
    assert got == want


def test_an_intervention_that_removes_nothing_is_empty():
    nodes = load(game_path('nim'))
    grouping = M.Grouping('none', [set()], [n.node_id for n in nodes])
    grouping.groups = [frozenset()]
    grouping.core = [frozenset()]
    assert IV.build(nodes, grouping)[0].empty


# ---- behaviour and validity ----------------------------------------------

@pytest.fixture(scope='module')
def breakthrough():
    text = open(game_path('breakthrough5')).read()
    states, _how = B.state_set('breakthrough5', text)
    changes = {c.id: c for c in probes.load_variants('breakthrough5')[1]}
    ref_text = probes.variant_text(text, changes['no_capture'])
    return {'text': text, 'states': states, 'ref_text': ref_text,
            'base': B.behaviour(text, states),
            'ref': B.behaviour(ref_text, states)}


def test_the_reference_agrees_with_itself(breakthrough):
    got = B.agreement(breakthrough['base'], breakthrough['ref'],
                      breakthrough['ref'])
    assert got['precision'] == got['recall'] == got['f1'] == 1.0
    assert got['changed_ref'] > 0 and got['unintended'] == 0


def test_doing_nothing_has_no_precision_and_zero_recall(breakthrough):
    """No change made: precision is NOT MEASURABLE (None), and recall is
    a measured zero."""
    got = B.agreement(breakthrough['base'], breakthrough['ref'],
                      breakthrough['base'])
    assert got['precision'] is None and got['recall'] == 0.0
    assert got['f1'] is None


def test_a_description_that_does_not_load(breakthrough):
    broken = B.behaviour('not :- gdl & &', breakthrough['states'])
    assert not broken.loads
    got = B.agreement(breakthrough['base'], breakthrough['ref'], broken)
    assert got['recall'] == 0.0
    assert B.validity('not :- gdl & &', breakthrough['states'],
                      broken)[0] is False


def test_reference_variant_is_valid(breakthrough):
    ok, reason = B.validity(breakthrough['ref_text'],
                            breakthrough['states'], breakthrough['ref'],
                            base=breakthrough['base'])
    assert ok, reason


def test_defects_the_base_has_are_not_charged(breakthrough):
    """S holds a probe state the base never reaches and is ill-formed
    at (a far-row pawn with its own side to move). Without `base`, the
    reference variant would be charged for it."""
    ok, reason = B.validity(breakthrough['ref_text'],
                            breakthrough['states'], breakthrough['ref'])
    assert not ok and 'two goal values' in reason


def test_removing_the_permission_but_not_the_mobility_is_invalid(
        breakthrough):
    """The trap the pilot sets: drop the capture from `legal` but keep it
    in the ending's mobility test, and a player whose only moves were
    captures is stuck in a non-terminal state."""
    text = breakthrough['text'].replace(
        'legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & '
        'capture(P,X,Y,X2,Y2)\n', '')
    ok, reason = B.validity(text, breakthrough['states'],
                            base=breakthrough['base'])
    assert not ok and 'no legal move' in reason


def test_state_set_contains_every_probe_state(breakthrough):
    states = set(breakthrough['states'])
    for change in probes.load_variants('breakthrough5')[1]:
        for probe in change.probes:
            assert frozenset(probes._state(probe['state'])) in states


def test_small_games_use_every_reachable_state():
    states, how = B.state_set('corridor')
    assert 'reachable' in how
