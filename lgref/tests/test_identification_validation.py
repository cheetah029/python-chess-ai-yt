"""The Phase 1 gate: identification must beat cheaper alternatives.

Rule identification is validated on games whose boundaries a human can
state with certainty, BEFORE it is trusted on Royal Chess — where nobody
knows the right answer and a plausible-looking cluster list is
indistinguishable from a correct one.

The baselines are the point. A method that cannot beat grouping by shared
name tokens has not earned its complexity, and this suite exists to say
so out loud rather than let the method pass on plausibility.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.identify.clauses import load
from lgref.identify.validate import (evaluate, lgref_assignment,
                                     baseline_name_similarity,
                                     pairwise_scores)
from lgref.identify.testgames.ground_truth import GAMES, expected_partition

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, '..', 'identify', 'testgames')


def _load(game):
    return load(os.path.join(GAME_DIR, game + '.gdl'))


def _score(game, method=lgref_assignment, **kw):
    nodes = _load(game)
    predicted = method(nodes, **kw)
    return pairwise_scores(predicted, expected_partition(game, nodes),
                           [n.node_id for n in nodes])


# ---- the gate ------------------------------------------------------------

@pytest.mark.parametrize('game', sorted(GAMES))
def test_identification_beats_the_name_similarity_baseline(game):
    """The cheapest plausible method groups clauses by shared head-name
    tokens. Structure must beat it or the graph is not earning its keep.

    It did NOT, at first: tic-tac-toe scored ARI 0.439 against the
    baseline's 0.659, because hub fluents wired every rule together
    through temporal edges, and because clauses defining one predicate
    had no edge between them at all. Both were real defects this test
    surfaced.
    """
    nodes = _load(game)
    expected = expected_partition(game, nodes)
    ids = [n.node_id for n in nodes]

    ours = pairwise_scores(lgref_assignment(nodes), expected, ids)
    theirs = pairwise_scores(baseline_name_similarity(nodes), expected, ids)

    assert ours['ari'] > theirs['ari'], (
        f'{game}: identification ARI {ours["ari"]:.3f} does not beat the '
        f'name-similarity baseline {theirs["ari"]:.3f}')


@pytest.mark.parametrize('game', sorted(GAMES))
def test_identification_reaches_a_usable_agreement_level(game):
    """A ratchet on absolute quality, not just relative.

    Beating a weak baseline is not enough: the partition has to be
    usable. Measured at the time of writing: tic-tac-toe ARI 0.687,
    nim 0.753. The floor sits below both so it cannot flake, and should
    be raised as identification improves — never lowered to pass.
    """
    scores = _score(game)
    assert scores['ari'] >= 0.60, (
        f'{game}: ARI {scores["ari"]:.3f} below the 0.60 floor')
    assert scores['f1'] >= 0.70


@pytest.mark.parametrize('game', sorted(GAMES))
def test_group_count_is_in_the_right_neighbourhood(game):
    """Neither one blob nor all singletons.

    ARI is chance-corrected and punishes both, but a direct check says
    WHICH failure happened when it happens.
    """
    nodes = _load(game)
    predicted = lgref_assignment(nodes)
    n_groups = len({g for gs in predicted.values() for g in gs})
    n_expected = len(GAMES[game])
    assert 1 < n_groups <= n_expected * 3, (
        f'{game}: {n_groups} groups against {n_expected} expected')


# ---- scoring itself ------------------------------------------------------

def test_perfect_agreement_scores_one():
    """Guard the scorer: if it cannot recognise a perfect match, every
    number it produces is suspect."""
    nodes = _load('nim')
    expected = expected_partition('nim', nodes)
    ids = [n.node_id for n in nodes]
    scores = pairwise_scores(expected, expected, ids)
    assert scores['ari'] == pytest.approx(1.0)
    assert scores['f1'] == pytest.approx(1.0)


def test_one_giant_cluster_is_penalised_by_ari():
    """Merging everything gives perfect RECALL, which is why F1 alone is
    not enough and ARI is the headline number."""
    nodes = _load('nim')
    expected = expected_partition('nim', nodes)
    ids = [n.node_id for n in nodes]
    blob = {i: {'ALL'} for i in ids}
    scores = pairwise_scores(blob, expected, ids)
    assert scores['recall'] == pytest.approx(1.0)
    assert scores['ari'] < 0.5


def test_all_singletons_scores_zero_recall():
    nodes = _load('nim')
    expected = expected_partition('nim', nodes)
    ids = [n.node_id for n in nodes]
    singletons = {i: {i} for i in ids}
    scores = pairwise_scores(singletons, expected, ids)
    assert scores['recall'] == pytest.approx(0.0)


def test_trace_only_reports_not_measured_without_traces():
    """A 0.000 would read as 'tried and failed' rather than 'not yet
    run' — a materially different and more flattering claim."""
    nodes = _load('nim')
    rows = evaluate('nim', nodes, expected_partition('nim', nodes))
    trace_row = [r for r in rows if r['method'] == 'trace_only'][0]
    assert trace_row.get('not_measured') is True


# ---- the games themselves ------------------------------------------------

@pytest.mark.parametrize('game', sorted(GAMES))
def test_validation_games_are_structurally_unlike_royal_chess(game):
    """These exist to test that identification is not chess-shaped, so
    they must not share Royal Chess's vocabulary."""
    nodes = _load(game)
    heads = {n.head_predicate for n in nodes}
    chess = {'boulder_cooldown', 'queen_form', 'manipulation_freeze',
             'reactive_armed', 'tiny_endgame_active'}
    assert not (heads & chess)


@pytest.mark.parametrize('game', sorted(GAMES))
def test_ground_truth_covers_almost_every_clause(game):
    """Uncovered clauses are silently excluded from scoring, so a thin
    reference partition would flatter any method."""
    nodes = _load(game)
    expected = expected_partition(game, nodes)
    labelled = sum(1 for v in expected.values() if v)
    assert labelled / len(nodes) > 0.85


# ---- co-activation: a measured null result ------------------------------

def test_co_activation_is_disabled_by_default():
    """The brief asks for dynamic co-activation, so it was built and
    tested — and it made identification WORSE on every game where the
    answer is known:

        game        static only   + co-activation
        tictactoe         0.687             0.663
        nim               0.753             0.613

    Raw co-occurrence was worse still (0.301, 0.251): each state's
    firing clauses form a clique, and in a well-formed game most clauses
    are satisfiable in most states, so co-firing reports "the position is
    normal" rather than rule membership.

    The weight is therefore 0.0. This test exists so that raising it
    again is a deliberate act supported by evidence, not a silent
    default change.
    """
    from lgref.identify.cluster import DEFAULT_WEIGHTS
    assert DEFAULT_WEIGHTS['co_activation'] == 0.0


def test_co_activation_requires_consistent_association():
    """Raw co-occurrence must not create an edge: two clauses firing in
    one shared state out of many are not related."""
    from lgref.identify.graph import ClauseGraph
    nodes = _load('nim')
    ids = [n.node_id for n in nodes][:3]
    graph = ClauseGraph(nodes)
    # a and b fire together once; a fires alone four more times.
    traces = [{ids[0], ids[1]}] + [{ids[0]}] * 4
    graph.add_co_activation(traces, min_association=0.8)
    assert graph.edge_count('co_activation') == 0

    graph2 = ClauseGraph(nodes)
    graph2.add_co_activation([{ids[0], ids[1]}] * 5, min_association=0.8)
    assert graph2.edge_count('co_activation') == 1


def test_co_activation_ignores_pairs_seen_too_rarely():
    """A ratio over one or two observations is noise, not association."""
    from lgref.identify.graph import ClauseGraph
    nodes = _load('nim')
    ids = [n.node_id for n in nodes][:2]
    graph = ClauseGraph(nodes)
    graph.add_co_activation([{ids[0], ids[1]}], min_association=1.0,
                            min_states=3)
    assert graph.edge_count('co_activation') == 0
