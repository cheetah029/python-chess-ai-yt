"""Score a search against EXACT answers, not against another search.

Issue #206 measured MCTS on Royal Chess to be a uniform sampler. That
left a question the measurement could not settle: is the implementation
wrong, or is a branching factor of 68 too wide for an affordable budget?

Tic-tac-toe settles it. Small enough to solve exactly, so every position
has a known optimal-move set; branching at most 9, so a cheap budget
covers the root many times over.

Every accuracy here is reported against a RANDOM BASELINE. In many
tic-tac-toe positions most legal moves are already optimal -- the
baseline is 55% -- so a bare accuracy figure would flatter any agent.
"""

import random

import pytest

from lgref.experiments.mcts import MCTSPlayer
from lgref.experiments.mobility import MobilityPlayer
from lgref.experiments.solvable import (TicTacToe, optimal_moves,
                                        reachable_positions)


def _positions(n=60):
    got = reachable_positions(limit=n, seed=1)
    return [(p, optimal_moves(p)[0]) for p in got]


def _accuracy(make_agent, cases):
    hit = 0
    for position, best in cases:
        agent = make_agent()
        hit += agent.choose_turn(position.get_all_legal_turns(),
                                 position) in best
    return hit / len(cases)


def _baseline(cases):
    return sum(len(best) / len(p.get_all_legal_turns())
               for p, best in cases) / len(cases)


# ------------------------------------------------------- the solver ----

def test_the_solver_agrees_with_the_known_answer():
    """Tic-tac-toe is a draw under perfect play. If this is wrong,
    every accuracy measured against it is wrong too."""
    from lgref.experiments.solvable import _solve
    assert _solve(tuple([None] * 9), 'x') == 0


def test_a_winning_move_is_found():
    game = TicTacToe(['x', 'x', None, None, 'o', None, None, None, 'o'], 'x')
    best, value = optimal_moves(game)
    assert value == 1
    assert 2 in best, 'the immediate three-in-a-row was not optimal'


def test_optimal_moves_is_a_set_not_a_single_choice():
    """Scoring against one arbitrary optimum would penalise an agent
    for a different, equally perfect move."""
    best, _ = optimal_moves(TicTacToe())
    assert len(best) > 1


# -------------------------------------------------------- the search ----

@pytest.mark.slow
def test_mcts_beats_chance_on_a_solvable_game():
    """The implementation is sound; Royal Chess was a budget problem.

    Measured: 55% baseline, 71% at 5 simulations rising to 89% at 200.
    """
    cases = _positions()
    baseline = _baseline(cases)
    accuracy = _accuracy(
        lambda: MCTSPlayer(n_simulations=50, rollout_depth=20,
                           rng=random.Random(11)), cases)
    assert accuracy > baseline + 0.15, (accuracy, baseline)


@pytest.mark.slow
def test_mcts_improves_with_budget_when_the_root_fits():
    """The property absent on Royal Chess, where 40 simulations bought
    0.59 visits per root move and every child got identical visits."""
    cases = _positions()
    low = _accuracy(
        lambda: MCTSPlayer(n_simulations=5, rollout_depth=20,
                           rng=random.Random(11)), cases)
    high = _accuracy(
        lambda: MCTSPlayer(n_simulations=100, rollout_depth=20,
                           rng=random.Random(11)), cases)
    assert high > low, (low, high)


@pytest.mark.slow
def test_mobility_is_weaker_where_mobility_is_not_the_loss_condition():
    """A limitation of the agent, recorded rather than left implicit.

    Mobility wins on Royal Chess because three of its four loss
    conditions are forms of running out of legal turns. Tic-tac-toe has
    no such condition, so the heuristic has nothing to grip: measured
    69% against MCTS's 87% at 50 simulations. The agent is matched to a
    property of the game, and that should not be mistaken for general
    strength.
    """
    cases = _positions()
    mobility = _accuracy(lambda: MobilityPlayer(rng=random.Random(11)),
                         cases)
    search = _accuracy(
        lambda: MCTSPlayer(n_simulations=50, rollout_depth=20,
                           rng=random.Random(11)), cases)
    assert mobility > _baseline(cases), 'mobility is below chance'
    assert search > mobility, (
        'mobility now beats search here; the domain-dependence claim in '
        'docs/lgref-phase3.md needs revisiting')
