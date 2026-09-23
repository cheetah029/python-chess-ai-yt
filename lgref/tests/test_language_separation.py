"""Separating the language a game is written in from its rules.

Issue #202. `file_delta_1` is not a gameplay provision -- it is the
arithmetic provisions are written in -- but the intervention probe
cannot tell, because removing the language removes moves exactly as
removing the rule would.

The criterion: a cluster is LANGUAGE if no clause in it depends, at any
depth, on game state. Everything here is measured on games with
hand-stated boundaries, because on Royal Chess alone a plausible answer
is indistinguishable from a correct one.
"""

import os

import pytest

from lgref.identify.clauses import load
from lgref.identify.cluster import calibrate_resolution, cluster
from lgref.identify.graph import ClauseGraph
from lgref.identify.language import (LANGUAGE, RULE, UNDETERMINED,
                                     classify_all, state_dependent_predicates)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAMES = os.path.join(REPO, 'lgref', 'identify', 'testgames')
OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')


def _classified(path):
    nodes = load(path)
    graph = ClauseGraph(nodes)
    rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
    kinds = classify_all(nodes, rules)
    named = {}
    for rule in rules:
        heads = frozenset(
            n.head_predicate for n in rule.nodes()
            if n.node_id in rule.clause_ids and n.head_predicate)
        named[heads] = kinds[rule.rule_id]
    return named


def test_nim_arithmetic_group_is_recovered_as_language():
    """The decisive validation, against a label written independently.

    `lgref/identify/testgames/ground_truth.py` lists nim's `arithmetic`
    group -- succ, positive, atleast2 -- as its own provision, written
    by hand long before this criterion existed. The criterion isolates
    exactly that set.
    """
    named = _classified(os.path.join(GAMES, 'nim.gdl'))
    flat = {head: kind for heads, kind in named.items() for head in heads}
    for predicate in ('succ', 'positive', 'atleast2'):
        assert flat.get(predicate) == LANGUAGE, (predicate, flat)
    # Asserted per predicate, not as one cluster: at this resolution the
    # group is split across three clusters. Fragmentation is a
    # granularity question; the classification is what is under test.


def test_nim_taking_rule_is_not_language():
    """`pile` is game state, so the taking rule must stay a rule."""
    named = _classified(os.path.join(GAMES, 'nim.gdl'))
    for heads, kind in named.items():
        if 'pile' in heads or 'legal' in heads:
            assert kind == RULE, (sorted(heads), kind)


def test_tictactoe_line_detection_is_not_language():
    """A line is defined over the board STATE, not over coordinates.

    An earlier hand label of mine had the analogous Royal Chess
    predicates (`bishop_diag_los`, `los_diag_ray`) down as geometry.
    The criterion disagreed and was right: a line of sight depends on
    occupancy.
    """
    named = _classified(os.path.join(GAMES, 'tictactoe.gdl'))
    for heads, kind in named.items():
        if {'line', 'row', 'column', 'diagonal'} & set(heads):
            assert kind == RULE, (sorted(heads), kind)


def test_royal_chess_coordinate_arithmetic_is_language():
    named = _classified(OFFICIAL)
    flat = {}
    for heads, kind in named.items():
        for head in heads:
            flat[head] = kind
    for predicate in ('file_delta_1', 'rank_delta_1', 'file_delta_2',
                      'rank_delta_2', 'between_file', 'between_rank',
                      'file_adj'):
        assert flat.get(predicate) == LANGUAGE, (predicate,
                                                 flat.get(predicate))


def test_the_separation_is_PARTIAL_and_this_records_which_part():
    """Recall is incomplete, and pretending otherwise would be the lie.

    `rank_adj`, `perpendicular`, `file_eastward` and `rank_upward` are
    coordinate arithmetic by any reading, and at the calibrated
    resolution soft membership places them in clusters that also carry
    state-dependent clauses, so they come out rule content. The
    criterion's PRECISION is good -- what it calls language is geometry
    -- but its RECALL is not complete, and the gap is clustering
    granularity rather than the criterion itself.

    Pinned so that an improvement shows up as this test failing, rather
    than as nobody noticing.
    """
    flat = {}
    for heads, kind in _classified(OFFICIAL).items():
        for head in heads:
            flat.setdefault(head, kind)
    absorbed = [p for p in ('rank_adj', 'perpendicular', 'file_eastward',
                            'rank_upward')
                if flat.get(p) != LANGUAGE]
    assert absorbed, (
        'geometry that used to be absorbed now separates -- good; update '
        'this test and docs/lgref-phase1.md rather than deleting it')


@pytest.mark.parametrize('predicate', [
    'boulder_cooldown', 'invulnerable', 'distance_count',
    'tiny_endgame_active', 'pawn_forward',
])
def test_royal_chess_provisions_are_rule_content(predicate):
    named = _classified(OFFICIAL)
    for heads, kind in named.items():
        if predicate in heads:
            assert kind != LANGUAGE, (predicate, sorted(heads))
            return
    pytest.fail('{} appeared in no cluster'.format(predicate))


@pytest.mark.parametrize('predicate', ['knight_step'])
def test_a_movement_SHAPE_is_language_and_that_is_correct(predicate):
    """Pinned because it looks wrong at first glance and is not.

    `knight_step(F1,R1,F2,R2)` says two squares are a knight-step apart.
    That holds of the board's names whatever is standing on it, so it is
    geometry in the same sense `file_delta_1` is. The knight's RULE is
    the `legal` clause that permits moving that shape -- it reads
    `control` and `cell`, and comes out rule content.

    The practical consequence is a routing rather than an exclusion: a
    shape is not something to delete, it is something to SWAP. "What if
    the knight moved like a rook?" is a replace-mode variant built by
    substituting one shape for another, which is the structural
    recombination in #196.
    """
    named = _classified(OFFICIAL)
    for heads, kind in named.items():
        if predicate in heads:
            assert kind == LANGUAGE, (predicate, sorted(heads), kind)
            return
    pytest.fail('{} appeared in no cluster'.format(predicate))


def test_calibration_does_not_buy_granularity_with_coverage():
    """The defect in the FIRST version of this calibration.

    Targeting mean clauses-per-rule rewarded exactly the shredding it
    should have penalised: mean size falls partly by ejecting clauses
    into singletons. It drove Royal Chess to resolution 33, where
    coverage is 56.7% and `rook_step`, `pawn_forward` and `invulnerable`
    were in no cluster at all. On the ground-truth games ARI collapses
    exactly when coverage does -- tic-tac-toe 0.711 -> 0.273, nim
    0.734 -> 0.357 -- so coverage is the binding constraint.
    """
    for path in (os.path.join(GAMES, 'tictactoe.gdl'),
                 os.path.join(GAMES, 'nim.gdl'), OFFICIAL):
        nodes = load(path)
        graph = ClauseGraph(nodes)
        coarse, _ = cluster(graph, resolution=0.5)
        chosen, _ = cluster(graph, resolution=calibrate_resolution(graph))
        best = sum(len(r.clause_ids) for r in coarse) / len(nodes)
        got = sum(len(r.clause_ids) for r in chosen) / len(nodes)
        assert got >= best - 0.05, (path, best, got)


def test_state_dependence_is_transitive():
    """`empty` reads no fluent; it depends on `occupied`, which reads `cell`.

    Testing direct reads only left `empty` looking static.
    """
    nodes = load(OFFICIAL)
    stateful = state_dependent_predicates(nodes)
    assert 'empty' in stateful
    assert 'occupied' in stateful
    assert 'file_delta_1' not in stateful


def test_a_cluster_resting_on_an_undefined_predicate_is_undetermined():
    """Incomplete is not the same as static.

    A cluster that bottoms out in a predicate the description never
    defines looks stateless only because the description stops there,
    so it must not be called language.

    `classify` is exercised directly on a hand-built cluster rather than
    through Louvain. Routed through clustering the case never arises --
    the undefined-dependent clause gets grouped with a stateful one and
    the verdict is decided before this branch is reached -- so the test
    would have passed while testing nothing.
    """
    import tempfile

    from lgref.identify.cluster import CandidateRule
    from lgref.identify.language import classify, undefined_predicates

    text = ('threshold_reached :- counts_at_least_7\n'
            'legal(P,go) :- true(control(P)) & threshold_reached\n'
            'next(control(a)) :- true(control(b))\n')
    with tempfile.NamedTemporaryFile('w', suffix='.gdl',
                                     delete=False) as handle:
        handle.write(text)
        path = handle.name
    try:
        nodes = load(path)
        graph = ClauseGraph(nodes)
        stateful = state_dependent_predicates(nodes)
        undefined = undefined_predicates(nodes)
        assert 'counts_at_least_7' in undefined

        stub = next(n for n in nodes
                    if n.head_predicate == 'threshold_reached')
        alone = CandidateRule('RXX', {stub.node_id}, set(), graph)
        assert classify(alone, stateful, undefined) == UNDETERMINED

        # And a genuinely static cluster in the same description is not
        # swept up by the same branch.
        assert 'threshold_reached' not in stateful
    finally:
        os.unlink(path)
