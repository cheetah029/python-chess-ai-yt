"""The measurement agent must be playable by a human (#265).

Every other player option is a uniform random mover or a trained
ValueNetwork checkpoint, so there was no way to form an impression of the
agent whose numbers the research reports -- and that agent is known not to
be converged on this game: #206 measured it as a uniform sampler here
(0% self-agreement, identical visit counts across all 65 root children),
and self-agreement is 2 of 4 at 2000 simulations.

Playing it does not replace the Phase C measurements against exact
search. It is the cheapest way for a human to see a blunder that a
summary statistic averages away.
"""

import os
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, REPO)

# BEFORE importing pygame, and not optional. `Game()` builds a `Config`,
# which loads sounds, which needs the mixer -- and `pygame.init()` does
# not reliably bring the mixer up. Without these this file passed on a
# machine with working audio and failed six of eight tests on one
# without, which is how it was caught: standalone it passed, in the
# batch it did not. Every other pygame test file here sets them.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()

from ai_controller import AIController
from game import Game


def test_mcts_is_offered_as_a_player():
    keys = [opt['key'] for opt in Game.PLAYER_OPTIONS]
    assert 'mcts' in keys
    # The catalog still carries everything it did before.
    for required in ('human', 'random', 'easy', 'medium', 'hard'):
        assert required in keys


def test_the_mcts_option_is_always_available():
    """Unlike the trained difficulties, it needs no checkpoint on disk."""
    assert Game()._ai_checkpoint_available('mcts') is True


def test_it_builds_the_real_measurement_agent():
    """Not a stand-in: the same class the sweeps use."""
    from lgref.experiments.mcts import MCTSPlayer

    player = Game()._make_ai_player('mcts')
    assert isinstance(player, MCTSPlayer)


def test_the_simulation_budget_is_a_startup_choice():
    game = Game()
    assert game._make_ai_player('mcts').n_simulations == \
        Game.MCTS_UI_SIMULATIONS
    game.mcts_simulations = 123
    assert game._make_ai_player('mcts').n_simulations == 123


def test_the_default_budget_is_playable_not_the_measurement_budget():
    """800 simulations is 43.8s a ply. Nobody plays that."""
    assert Game.MCTS_UI_SIMULATIONS <= 100


def test_mode_selection_accepts_it():
    game = Game()
    game.apply_mode_selection(side='white', opponent='mcts')
    assert game.black_player == 'mcts' or game.white_player == 'mcts'


def test_it_takes_a_real_turn_through_the_human_path():
    """The controller applies turns through the same board mutations the UI
    uses, so an AI turn must be indistinguishable from a human one."""
    game = Game()
    game.mcts_simulations = 10
    game.apply_mode_selection(side='white', opponent='mcts')
    controller = AIController('black', player=game._make_ai_player('mcts'))

    before = game.board.turn_number
    game.next_turn()                      # hand the move to black
    assert controller.is_ai_turn(game)
    started = time.time()
    assert controller.take_turn(game) is True
    assert game.board.turn_number > before
    assert time.time() - started < 60, 'ten simulations must not be slow'


def test_an_unknown_agent_key_is_refused():
    with pytest.raises(ValueError):
        Game()._make_ai_player('no_such_agent')
