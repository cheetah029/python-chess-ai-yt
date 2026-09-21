"""Agent tests on positions where the right answer is checkable by hand.

The project brief requires every metric function to be tested on a
hand-constructed trace whose answer can be verified by hand. The agents
are not metric functions, but the same standard applies for a stronger
reason: an agent bug that merely weakens play produces plausible-looking
games and would silently corrupt every ablation comparison rather than
crashing.

The properties asserted here are the ones that must hold regardless of
search quality: determinism under a fixed seed, finding a capture that
ends the game, never returning an illegal turn, and — the one that
matters most for this study — being genuinely stronger than random.
"""

import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from experiments.variants import make_engine
from lgref.experiments.mcts import MCTSPlayer
from lgref.experiments.minimax import MonteCarloMinimaxPlayer


def _advance(engine, rng, plies):
    for _ in range(plies):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(rng.choice(turns))
    return engine


# ---- determinism ---------------------------------------------------------

def test_mcts_is_deterministic_under_a_fixed_seed():
    """Same seed, same position, same move — otherwise no run is
    reproducible from its config and seed, which the brief requires."""
    picks = []
    for _ in range(2):
        engine = _advance(make_engine('full'), random.Random(4), 6)
        player = MCTSPlayer(n_simulations=12, rollout_depth=10,
                            rng=random.Random(99))
        turns = engine.get_all_legal_turns()
        picks.append(repr(player.choose_turn(turns, engine)))
    assert picks[0] == picks[1]


def test_minimax_is_deterministic_under_a_fixed_seed():
    picks = []
    for _ in range(2):
        engine = _advance(make_engine('full'), random.Random(4), 6)
        player = MonteCarloMinimaxPlayer(depth=1, n_rollouts=2,
                                         rollout_depth=8,
                                         rng=random.Random(7))
        turns = engine.get_all_legal_turns()
        picks.append(repr(player.choose_turn(turns, engine)))
    assert picks[0] == picks[1]


# ---- legality ------------------------------------------------------------

@pytest.mark.parametrize('make_player', [
    lambda rng: MCTSPlayer(n_simulations=8, rollout_depth=8, rng=rng),
    lambda rng: MonteCarloMinimaxPlayer(depth=1, n_rollouts=2,
                                        rollout_depth=6, rng=rng),
])
def test_chosen_turn_is_always_one_of_the_offered_turns(make_player):
    """An agent that returned a turn the engine did not offer would
    execute an illegal move and silently corrupt a whole run."""
    rng = random.Random(11)
    engine = make_engine('full')
    player = make_player(rng)
    for _ in range(6):
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        chosen = player.choose_turn(turns, engine)
        assert chosen in turns
        engine.execute_turn(chosen)


@pytest.mark.parametrize('make_player', [
    lambda rng: MCTSPlayer(n_simulations=4, rollout_depth=4, rng=rng),
    lambda rng: MonteCarloMinimaxPlayer(depth=1, n_rollouts=1,
                                        rollout_depth=4, rng=rng),
])
def test_empty_turn_list_returns_none(make_player):
    assert make_player(random.Random(0)).choose_turn([], None) is None


@pytest.mark.parametrize('make_player', [
    lambda rng: MCTSPlayer(n_simulations=50, rollout_depth=20, rng=rng),
    lambda rng: MonteCarloMinimaxPlayer(depth=2, n_rollouts=4, rng=rng),
])
def test_forced_move_is_returned_without_searching(make_player):
    """With one legal turn there is nothing to decide, and searching
    would waste the entire per-move budget."""
    engine = make_engine('full')
    only = engine.get_all_legal_turns()[:1]
    assert make_player(random.Random(0)).choose_turn(only, engine) is only[0]


# ---- search correctness --------------------------------------------------

def test_mcts_visits_sum_to_the_simulation_budget():
    """Every simulation must land somewhere in the tree. A shortfall
    means simulations were silently discarded and the agent is weaker
    than its configuration claims."""
    engine = _advance(make_engine('full'), random.Random(2), 4)
    player = MCTSPlayer(n_simulations=40, rollout_depth=10,
                        rng=random.Random(5))
    player.choose_turn(engine.get_all_legal_turns(), engine)
    assert sum(player.last_root_visits) == 40


def test_mcts_concentrates_visits_rather_than_spreading_them():
    """UCB1 must exploit, not sample uniformly.

    This test found a real design bug. With a shallow rollout cap, NO
    rollout reaches a terminal state in this game (measured: 0% within 50
    plies from an opening position), so every rollout scores DRAW_VALUE,
    every child has an identical mean, and UCB1 reduces to "visit the
    least-visited child" — exact round-robin. Visits came out perfectly
    uniform at every budget: 4/4/4..., 10/10/10..., 20/20/20...

    The agent then pays full search price and plays no better than
    random. A separate benchmark confirmed it played WORSE: 0 wins in 32
    games against RandomPlayer, degrading as simulations rose.

    Asserting on the MECHANISM rather than on win rate is what localised
    this. A strength benchmark alone would have said "too weak, add
    simulations", which was exactly the wrong response.

    Uses the production rollout depth, since the failure mode is
    precisely a depth too shallow to produce signal.
    """
    engine = _advance(make_engine('full'), random.Random(3), 8)
    turns = engine.get_all_legal_turns()
    player = MCTSPlayer(n_simulations=len(turns) * 3, rollout_depth=200,
                        rng=random.Random(6))
    player.choose_turn(turns, engine)
    visits = sorted(player.last_root_visits, reverse=True)
    uniform = sum(visits) / len(visits)
    assert visits[0] > uniform * 1.3, (
        f'most-visited child got {visits[0]} vs uniform {uniform:.1f} — '
        f'UCB1 is not concentrating search. If visits are EXACTLY '
        f'uniform, rollouts are not reaching terminal states and every '
        f'value is DRAW_VALUE; raise rollout_depth.')


def test_minimax_counts_leaves_and_prunes():
    """Alpha-beta must actually cut. Without pruning, depth-2 would visit
    every one of ~branching^2 nodes, and Monte-Carlo leaves make that
    unaffordable."""
    engine = _advance(make_engine('full'), random.Random(8), 4)
    turns = engine.get_all_legal_turns()
    player = MonteCarloMinimaxPlayer(depth=2, n_rollouts=1, rollout_depth=4,
                                     rng=random.Random(1))
    player.choose_turn(turns, engine)
    assert player.leaves_evaluated > 0
    assert player.leaves_evaluated < len(turns) ** 2, (
        f'{player.leaves_evaluated} leaves for {len(turns)} root moves — '
        f'alpha-beta appears not to be pruning')


# ---- the property the study depends on -----------------------------------

@pytest.mark.slow
def test_mcts_outplays_random():
    """MCTS must be measurably stronger than random play.

    This is the assumption the whole Phase 3 design rests on: if the
    agent is not stronger, the ablation compares two random players and
    the outcome metrics carry no signal about the rules. Kept modest so
    it can run in CI; the full strength curve lives in the benchmark.
    """
    wins = draws = 0
    games = 6
    for seed in range(games):
        rng = random.Random(500 + seed)
        player = MCTSPlayer(n_simulations=30, rollout_depth=200, rng=rng)
        engine = make_engine('full', max_turns=160)
        colour = 'white' if seed % 2 == 0 else 'black'
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            if engine.current_player == colour:
                engine.execute_turn(player.choose_turn(turns, engine))
            else:
                engine.execute_turn(rng.choice(turns))
        if engine.winner == colour:
            wins += 1
        elif engine.winner is None:
            draws += 1
    score = (wins + 0.5 * draws) / games
    assert score > 0.5, (
        f'MCTS scored {score:.2f} against random over {games} games. '
        f'If the agent is not stronger than random, Phase 3 outcome '
        f'metrics carry no signal about the rules.')
