"""Intervention coherence, tested on games with known structure.

This is the filter that decides whether a candidate cluster is a RULE. A
framework that proposed rules without being able to reject any would be
proposing nothing, so the tests here check that it rejects the right
things as well as accepting them.

The four verdicts are deliberately distinct, and collapsing them to
pass/fail would lose the most useful information:

  rule          removable, leaves a playable game, changes behaviour
  load_bearing  removing it leaves no playable game. Very likely a real
                rule — turn alternation certainly is — but its
                contribution CANNOT be measured by ablation, because
                there is nothing to compare against
  inert         nothing observable changed
  broken        the ablated description does not load
  infrastructure  everything in it is needed by another rule, so it
                cannot be ablated without ablating that rule too (#313)

AN ABLATION DELETES WHAT A RULE OWNS AND RELAXES WHAT IT GUARDS (#313).
A helper another rule needs is kept, and a guard -- a relation another
rule only TESTS -- is lifted by dropping the test, exactly as the
reference relaxations in `testgames/reference.py` do.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.identify.clauses import load
from lgref.identify.cluster import cluster
from lgref.identify.graph import ClauseGraph
from lgref.identify.intervention import (ablate_forms, check_all,
                                         check_cluster)

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, '..', 'identify', 'testgames')


def _game(name):
    nodes = load(os.path.join(GAME_DIR, name + '.gdl'))
    rules, _ = cluster(ClauseGraph(nodes))
    return nodes, rules


# ---- ablation mechanics --------------------------------------------------

def test_ablation_removes_exactly_the_named_clauses():
    nodes, rules = _game('nim')
    target = rules[0]
    remaining = ablate_forms(nodes, target.clause_ids)
    assert len(remaining) == len(nodes) - len(target.clause_ids)


def test_ablation_leaves_shared_helpers_in_place():
    """Only a cluster's OWN clauses are removed. Shared helpers serve
    other rules too, so removing them would ablate those rules as well
    and the intervention would isolate nothing."""
    nodes, rules = _game('tictactoe')
    target = next((r for r in rules if r.shared_clause_ids), None)
    if target is None:
        pytest.skip('no cluster with shared helpers in this game')
    remaining = ablate_forms(nodes, target.clause_ids)
    kept = {id(f) for f in remaining}
    for shared in target.shared_clause_ids:
        assert id(nodes_by_id(nodes, shared).raw) in kept


def nodes_by_id(nodes, node_id):
    return next(n for n in nodes if n.node_id == node_id)


# ---- the verdicts --------------------------------------------------------

def test_every_candidate_gets_a_verdict():
    nodes, rules = _game('nim')
    reports = check_all(nodes, rules)
    assert len(reports) == len(rules)
    for report in reports:
        assert report.verdict in ('rule', 'load_bearing', 'inert', 'broken',
                                  'infrastructure')


def test_at_least_one_cluster_is_an_ablatable_rule():
    """If nothing is ablatable, Phase 3 has nothing to measure."""
    for game in ('tictactoe', 'nim'):
        nodes, rules = _game(game)
        reports = check_all(nodes, rules)
        assert any(r.verdict == 'rule' for r in reports), (
            f'{game}: no cluster survived intervention coherence')


def test_removing_every_legal_clause_is_load_bearing_not_a_rule():
    """Deleting what makes anything legal leaves nobody able to move.

    That is the distinction the verdicts exist for: a cluster can be a
    genuine provision yet be unmeasurable by ablation, and letting Phase
    3 compare a game against a non-game would report the breakage as a
    contribution.
    """
    nodes, _ = _game('tictactoe')
    legal = [n.node_id for n in nodes if n.head_kind == 'legal']
    assert legal, 'expected legal clauses'

    class _Fake(object):
        rule_id = 'LEGAL'
        clause_ids = set(legal)
        shared_clause_ids = set()

    report = check_cluster(nodes, _Fake())
    assert report.compiles is True
    assert report.playable is False
    assert report.verdict == 'load_bearing'
    assert report.is_rule is False


def test_removing_nothing_is_inert():
    """An empty ablation changes nothing and must not be called a rule —
    the control that stops the test above passing for the wrong reason."""
    nodes, _ = _game('nim')

    class _Empty(object):
        rule_id = 'NONE'
        clause_ids = set()
        shared_clause_ids = set()

    report = check_cluster(nodes, _Empty())
    assert report.playable is True
    assert report.verdict == 'inert'
    assert report.is_rule is False


def test_a_termination_rule_counts_even_though_no_move_is_lost():
    """Deleting tic-tac-toe's line detection leaves every mark legal and
    simply stops the game being winnable.

    Judging on legal moves alone would call that inert, which is why
    termination is probed separately.
    """
    nodes, _ = _game('tictactoe')
    lines = [n.node_id for n in nodes
             if n.head_predicate in ('line', 'row', 'column', 'diagonal')]
    assert lines

    class _Lines(object):
        rule_id = 'LINES'
        clause_ids = set(lines)
        shared_clause_ids = set()

    report = check_cluster(nodes, _Lines())
    assert report.playable is True
    assert report.moves_before == report.moves_after, (
        'line detection should not change what is legal')
    assert report.changes_termination is True
    assert report.verdict == 'rule'


# ---- focus ---------------------------------------------------------------

def test_one_probe_seed_is_not_enough():
    """A single playout easily misses a rule's effect.

    Deleting tic-tac-toe's line detection leaves a game that still ends
    after nine marks, because the board fills — so seed 0 alone showed
    NO difference and the rule read as inert. Several seeds catch it.
    """
    from lgref.identify.intervention import _termination_probe, _write_gdl
    import os as _os
    nodes, _ = _game('tictactoe')
    lines = {n.node_id for n in nodes
             if n.head_predicate in ('line', 'row', 'column', 'diagonal')}
    full = _write_gdl([n.raw for n in nodes])
    cut = _write_gdl([n.raw for n in nodes if n.node_id not in lines])
    try:
        single_full = _termination_probe(full, seeds=(0,))
        single_cut = _termination_probe(cut, seeds=(0,))
        many_full = _termination_probe(full)
        many_cut = _termination_probe(cut)
    finally:
        _os.unlink(full)
        _os.unlink(cut)
    assert single_full == single_cut, (
        'seed 0 was expected to hide this rule — if it no longer does, '
        'the test has lost its point and should be re-grounded')
    assert many_full != many_cut


def test_goal_clauses_alone_are_inert():
    """Goals say WHO won, not WHEN the game ends, so removing them
    changes no observable behaviour in this probe. Reported as inert
    rather than as a rule — the control that stops the termination test
    above passing for the wrong reason."""
    nodes, _ = _game('tictactoe')
    goals = [n.node_id for n in nodes if n.head_predicate == 'goal']
    assert goals

    class _Goals(object):
        rule_id = 'GOALS'
        clause_ids = set(goals)
        shared_clause_ids = set()

    assert check_cluster(nodes, _Goals()).verdict == 'inert'


def test_focus_is_measured_over_the_games_own_action_names():
    """Nothing here knows Royal Chess's action names, or any game's."""
    nodes, rules = _game('nim')
    reports = check_all(nodes, rules)
    seen = set()
    for report in reports:
        seen |= set(report.actions_before)
    assert seen and seen <= {'take', 'noop'}


# ------------------------------------------------------------ parallelism ----

def test_parallel_sweep_matches_the_serial_one():
    """Results must not depend on worker count or completion order.

    Per-cluster probe cost ranges from ~0s to ~250s on the case-study
    description, so completions arrive in a different order every run.
    Indexing results by completion would make the report depend on
    scheduling -- the same class of defect as the hash-order dependence
    that made clustering unreproducible, and just as invisible.
    """
    from lgref.identify.clauses import load
    from lgref.identify.cluster import cluster
    from lgref.identify.graph import ClauseGraph

    path = os.path.join(GAME_DIR, 'nim.gdl')
    nodes = load(path)
    rules, _ = cluster(ClauseGraph(nodes))

    serial = check_all(nodes, rules, probe_plies=8, probe_seeds=(0, 1),
                       n_workers=1)
    parallel = check_all(nodes, rules, probe_plies=8, probe_seeds=(0, 1),
                         n_workers=4)

    assert [r.rule_id for r in serial] == [r.rule_id for r in parallel]
    assert [r.verdict for r in serial] == [r.verdict for r in parallel]


def test_parallel_sweep_preserves_cluster_order():
    """Report row N must still be cluster N."""
    from lgref.identify.clauses import load
    from lgref.identify.cluster import cluster
    from lgref.identify.graph import ClauseGraph

    nodes = load(os.path.join(GAME_DIR, 'nim.gdl'))
    rules, _ = cluster(ClauseGraph(nodes))
    reports = check_all(nodes, rules, probe_plies=8, probe_seeds=(0,),
                        n_workers=4)
    assert [r.rule_id for r in reports] == [r.rule_id for r in rules]


# ---- owned statements, guards and shared dependencies (#313) -------------

def _rule_holding(rules, nodes, predicate):
    by_id = {n.node_id: n for n in nodes}
    return next(r for r in rules
                if any(by_id[c].head_predicate == predicate
                       for c in r.clause_ids))


def _text(forms):
    from ggp.infix import forms_to_infix_lines
    return '\n'.join(forms_to_infix_lines(forms)) + '\n'


def test_a_guard_is_relaxed_exactly_as_the_reference_relaxes_it():
    """Corridor's boundary is a pure guard: `inside(B)` only tests a
    square `succ` has already bound. Its reference ablation drops that
    test (`reference.ABLATIONS`), and the exhaustive enumeration of the
    result is the known answer -- the rule is REDUNDANT, effect zero.

    LGREF's ablation of whatever cluster holds `inside` must enumerate to
    exactly the same game. Before #313 it deleted the `inside` facts
    instead, which in GDL makes the guard FALSE everywhere: no step was
    ever legal, and the redundant rule measured as a large effect.
    """
    from lgref.identify.intervention import removed_by_ablation
    from lgref.identify.testgames.reference import (enumerate_game,
                                                    enumerate_text)

    nodes, rules = _game('corridor')
    boundary = _rule_holding(rules, nodes, 'inside')
    assert boundary.guard_predicates == ('inside',)
    removed, relaxations = removed_by_ablation(boundary)
    ours = enumerate_text(_text(ablate_forms(nodes, removed, relaxations)))
    assert ours == enumerate_game('corridor', relax=('boundary',))
    assert ours == enumerate_game('corridor'), 'boundary is redundant'

    # The old ablation, still available, is the defect: it empties the
    # step rules.
    old, none = removed_by_ablation(boundary, preserve_dependencies=False)
    assert none == {}
    broken = enumerate_text(_text(ablate_forms(nodes, old)))
    assert broken != ours


def test_a_shared_generator_is_kept_and_its_rule_is_infrastructure():
    """`succ` and `plus2` BIND the destination square in Corridor's step
    rules, so no ablation of their cluster can drop them without leaving
    the step rules unable to move. They are protected, the cluster has
    nothing of its own, and it is reported as infrastructure rather than
    probed -- where before its deletion disabled movement and was
    reported as a rule.
    """
    nodes, rules = _game('corridor')
    arithmetic = _rule_holding(rules, nodes, 'succ')
    by_id = {n.node_id: n for n in nodes}
    assert {by_id[c].head_predicate for c in
            arithmetic.protected_clause_ids} >= {'succ', 'plus2'}
    report = check_cluster(nodes, arithmetic)
    assert report.verdict == 'infrastructure'
    assert check_cluster(nodes, arithmetic,
                         preserve_dependencies=False).verdict == 'rule'


def _calls_left_dangling(nodes, rule):
    """Helper predicates some REMAINING statement calls whose defining
    statements the ablation deleted -- the collateral damage #313 is
    about. Must always be empty.
    """
    from lgref.identify.clauses import _collect_body_predicates
    from lgref.identify.cluster import HELPER_KINDS, _head_name
    from lgref.identify.intervention import removed_by_ablation

    removed, relaxations = removed_by_ablation(rule)
    deleted = {_head_name(n.raw) for n in nodes
               if n.node_id in removed and n.head_kind in HELPER_KINDS}
    kept = {_head_name(n.raw) for n in nodes
            if n.node_id not in removed and n.head_kind in HELPER_KINDS}
    gone = deleted - kept
    dangling = set()
    for form in ablate_forms(nodes, removed, relaxations):
        body = list(form[2:]) if (isinstance(form, tuple)
                                  and form[0] == '<=') else []
        called = set()
        _collect_body_predicates(body, called)
        dangling |= called & gone
    return dangling


@pytest.mark.parametrize('game', ['tictactoe', 'nim', 'corridor'])
def test_no_ablation_deletes_a_helper_something_else_still_calls(game):
    nodes, rules = _game(game)
    for rule in rules:
        assert not _calls_left_dangling(nodes, rule), rule.rule_id


def test_no_ablation_on_royal_chess_leaves_a_call_dangling():
    """The same invariant on the 522-statement description, where it
    was violated by 285 statements before #313. Structural, so cheap:
    nothing is played."""
    from lgref.identify.cluster import calibrate_resolution

    path = os.path.join(HERE, '..', '..', 'docs', 'gdl', 'integrated.gdl')
    nodes = load(path)
    graph = ClauseGraph(nodes)
    rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
    assert any(r.protected_clause_ids for r in rules)
    for rule in rules:
        assert not _calls_left_dangling(nodes, rule), rule.rule_id
    # The old ablation is what the invariant catches.
    from lgref.identify.intervention import removed_by_ablation
    whole = [r for r in rules if r.protected_clause_ids]

    class _Whole(object):
        def __init__(self, rule):
            self.rule_id = rule.rule_id
            self.clause_ids = rule.clause_ids
            self.owned_clause_ids = rule.clause_ids
            self.relaxations = {}

    assert removed_by_ablation(_Whole(whole[0]))[0] == whole[0].clause_ids
    assert _calls_left_dangling(nodes, _Whole(whole[0]))


def test_ownership_partitions_each_community():
    """Owned and protected split the community exactly: nothing is lost
    and nothing counted twice."""
    for game in ('tictactoe', 'nim', 'corridor'):
        _nodes, rules = _game(game)
        for rule in rules:
            assert (rule.owned_clause_ids | rule.protected_clause_ids
                    == rule.clause_ids)
            assert not rule.owned_clause_ids & rule.protected_clause_ids
            assert not rule.owned_clause_ids & rule.dependency_clause_ids
