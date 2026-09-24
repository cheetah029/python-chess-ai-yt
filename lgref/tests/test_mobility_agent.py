"""The one-ply mobility agent, and the properties MCTS lacked.

Issue #206. MCTS at an affordable budget was measured to be a uniform
sampler: 0% self-agreement, and on a 65-move root every child received
exactly the same number of visits. The tests here check the properties
whose absence made that invisible -- they are written as the questions
that should have been asked of MCTS before it was called validated.
"""

import random
import sys
import os

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

import pygame
pygame.init()

from experiments.variants import make_engine          # noqa: E402
from lgref.experiments.mobility import MobilityPlayer  # noqa: E402


def _midgame(seed, plies=20):
    engine = make_engine('full', max_turns=1000)
    rng = random.Random(seed)
    for _ in range(plies):
        if engine.is_game_over():
            break
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        engine.execute_turn(turns[rng.randrange(len(turns))])
    return engine


def test_the_agent_distinguishes_its_moves():
    """The property MCTS did not have.

    A search whose moves all score the same is a sampler. MCTS gave all
    65 root children identical visit counts; this must not.
    """
    engine = _midgame(7000)
    turns = engine.get_all_legal_turns()
    player = MobilityPlayer(rng=random.Random(1))
    player.choose_turn(turns, engine)
    assert len(set(player.last_scores)) > 3, (
        'scores are near-uniform, so the agent is not discriminating: '
        '{}'.format(sorted(set(player.last_scores))[:8]))


def test_the_agent_agrees_with_itself():
    """Measured 0% for MCTS across seeds; this should be near-total.

    Not asserted at 100%: genuine ties are broken by the seeded rng on
    purpose, so two seeds may legitimately differ on a tied position.
    """
    same = 0
    trials = 8
    for i in range(trials):
        engine = _midgame(7000 + i)
        if engine.is_game_over():
            continue
        turns = engine.get_all_legal_turns()
        a = MobilityPlayer(rng=random.Random(1)).choose_turn(turns, engine)
        b = MobilityPlayer(rng=random.Random(2)).choose_turn(turns, engine)
        same += str(a) == str(b)
    assert same >= trials - 2, '{}/{} self-agreement'.format(same, trials)


def test_the_agent_is_reproducible_from_its_seed():
    engine = _midgame(7001)
    turns = engine.get_all_legal_turns()
    first = MobilityPlayer(rng=random.Random(5)).choose_turn(turns, engine)
    again = MobilityPlayer(rng=random.Random(5)).choose_turn(turns, engine)
    assert str(first) == str(again)


def test_an_immediately_winning_turn_is_taken():
    """Infinite score for a win, so it cannot be outvoted by mobility."""
    player = MobilityPlayer()

    class _Won(object):
        current_player = 'black'
        winner = 'white'

        def is_game_over(self):
            return True

    assert player._score(_Won(), 'white') == float('inf')
    assert player._score(_Won(), 'black') == float('-inf')


def test_a_censored_position_scores_as_no_information():
    """A game stopped by the cap is not a draw and not a win (#204)."""
    player = MobilityPlayer()

    class _Capped(object):
        current_player = 'black'
        winner = None

        def is_game_over(self):
            return True

    assert player._score(_Capped(), 'white') == 0.0


def test_nothing_in_the_agent_names_a_royal_chess_concept():
    """It has to evaluate rules in any GDL game, not this one.

    The agent may consult only the rules' own legal-turn function and
    the game's terminal and winner tests -- no piece values, no board
    geometry, nothing a different game would not have.
    """
    import inspect

    from lgref.experiments import mobility
    source = inspect.getsource(mobility.MobilityPlayer)
    for concept in ('boulder', 'knight', 'bishop', 'rook', 'pawn', 'queen',
                    'king', 'rank', 'file', 'royal'):
        assert concept not in source.lower(), (
            '{} leaked into the agent'.format(concept))


@pytest.mark.slow
def test_it_beats_random_as_either_colour():
    """A FLOOR test, and only that.

    "MCTS validated at 0.90 vs random" was taken as validation and was
    not: beating random in this variant does not require search, and
    that agent was later measured to be a uniform sampler. This is here
    to catch an agent that is broken, not to show that one is good.
    """
    wins = 0
    games = 4
    for g in range(games):
        rng = random.Random(500 + g)
        engine = make_engine('full', max_turns=1000)
        me = 'white' if g % 2 == 0 else 'black'
        agent = MobilityPlayer(rng=random.Random(g))
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            if engine.current_player == me:
                engine.execute_turn(agent.choose_turn(turns, engine))
            else:
                engine.execute_turn(turns[rng.randrange(len(turns))])
        wins += engine.winner == me
    assert wins >= games - 1, '{}/{} vs random'.format(wins, games)
