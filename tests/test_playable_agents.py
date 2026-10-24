"""Every opponent the mode menu offers must actually play, headlessly.

WHY THIS FILE EXISTS. The playable agent broke five times in one
session and each time the breakage reached a human before a test:

  - a weights file whose feature names no longer matched, so part of
    the evaluation silently never contributed;
  - a payload the loader refused outright, leaving no playable agent;
  - a quiescence path that crashed on any position containing a
    capture, because it recursed on the wrong object;
  - a capture ranker that scored the agent's own pieces as prizes;
  - and `play_mnk.py` declaring one option twice, so it could not start.

Every one of those is reachable by starting the program and playing a
few moves. None of them were caught, because the tests all reached
inside and called a function.

So this file plays. It takes each selectable opponent in turn, at the
SAME depth and budget the window uses, and makes it move in a real
game -- which exercises the weights file, the loader, the extractor,
the search, the ordering and the apply path together.

Headless: SDL dummy drivers, no window, no sound.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

import pytest

from game import Game

#: The opponents that must work without any downloaded artefact. The
#: network checkpoints (`easy`/`medium`/`hard`) resolve to a file that
#: may not exist in a fresh clone, and the menu grays them out when it
#: is missing, so a missing one is not a failure here. `mcts` at UI
#: settings costs seconds per ply and is covered by its own tests.
ALWAYS_AVAILABLE = ('random', 'strong', 'td')


@pytest.fixture(autouse=True)
def _pygame_up():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _every_menu_key():
    return [option['key'] for option in Game.PLAYER_OPTIONS
            if option['key'] != 'human']


def test_the_menu_offers_the_agents_this_file_checks():
    """If a key is renamed, the list above goes stale and the checks
    below quietly stop covering the agent a person selects."""
    offered = _every_menu_key()
    for key in ALWAYS_AVAILABLE:
        assert key in offered, (
            '{0!r} is no longer a menu option; this file is checking an '
            'agent nobody can select'.format(key))


@pytest.mark.parametrize('key', ALWAYS_AVAILABLE)
def test_a_selectable_opponent_plays_legal_moves_in_a_real_game(key):
    """THE SMOKE TEST THAT WAS MISSING.

    Built exactly as the window builds it -- `Game._make_ai_player`,
    which is what reads the shipped weights at `TD_DEPTH` and
    `TD_BUDGET_SECONDS` -- then asked to move in a real position several
    times. A broken weights file, a refused payload, a crash in
    quiescence or an illegal choice all fail here.
    """
    from experiments.variants import make_engine

    game = Game()
    player = game._make_ai_player(key)
    if player is None and key == 'random':
        # `None` MEANS "the controller's default", not "unavailable",
        # and the first version of this test skipped the uniform mover
        # because of it -- a skip for a reason that is not a missing
        # artefact is a hole in the coverage, not a pass.
        from players import RandomPlayer
        player = RandomPlayer()
    if player is None:
        pytest.skip('{0} has no artefact in this checkout'.format(key))

    engine = make_engine('full', max_turns=400)
    mover = random.Random(5)
    for _ply in range(6):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(mover.choice(turns))

    for _ply in range(4):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        chosen = player.choose_turn(turns, engine)
        assert chosen is not None, '{0} returned no move'.format(key)
        assert chosen in turns, (
            '{0} chose a turn that is not in the legal list'.format(key))
        engine.execute_turn(chosen)


def test_the_shipped_agent_never_captures_its_own_piece_in_a_game():
    """A blunder a human found by playing, asked of a whole game.

    The ranker scored the destination occupant by `abs(weight)` without
    asking whose piece it was, so "king takes own rook" was the top
    ranked move on the board. Only the king may take a friendly piece in
    this variant, so these are rare in the move list and catastrophic
    when played -- a reviewer's game had two by move eight.

    A guard on the ranker already exists. This one plays the game, which
    is where it was seen.
    """
    from experiments.variants import make_engine

    game = Game()
    player = game._make_ai_player('td')
    assert player is not None, 'the shipped weights did not load'

    engine = make_engine('full', max_turns=400)
    mover = random.Random(11)
    for _ply in range(10):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(mover.choice(turns))

    for _ply in range(8):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        side = engine.current_player
        chosen = player.choose_turn(turns, engine)
        target = getattr(chosen, 'to_sq', None)
        if getattr(chosen, 'is_capture', False) and target is not None:
            victim = engine.board.squares[target[0]][target[1]].piece
            assert victim is None or getattr(victim, 'color',
                                             None) != side, (
                'the agent captured its own {0}'.format(
                    type(victim).__name__))
        engine.execute_turn(chosen)


def test_the_window_settings_are_the_ones_the_agent_is_tested_at():
    """A depth measured in a test and a depth played in the window that
    differ make every strength claim about the wrong agent.

    Pinned rather than asserted to a value: the test reads the constants
    and the other tests use them, so the two cannot drift silently.
    """
    assert Game.TD_DEPTH >= 2, Game.TD_DEPTH
    assert Game.TD_BUDGET_SECONDS > 0, Game.TD_BUDGET_SECONDS
    assert Game.STRONG_DEPTH >= 1 and Game.STRONG_QUIESCENCE >= 1
