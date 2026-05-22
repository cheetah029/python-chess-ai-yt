"""Tests for AIController — the human-vs-AI integration (Goal 2).

The AIController reuses GameEngine only to ENUMERATE legal turns, then applies
the chosen turn through the same board path the human UI uses and advances via
Game.next_turn(). These tests verify, headlessly:

1. is_ai_turn() reflects whose color is to move and whether the game is over.
2. take_turn() applies exactly one legal turn for the AI's color and advances
   the game (turn_number increments, the side to move flips), and is a no-op
   when it isn't the AI's turn.
3. A full random AI-vs-AI game runs to completion without raising — exercising
   moves, captures, transformations, manipulations, boulder moves,
   jump-captures, promotions, the tiny endgame rule, and the repetition rule
   across a real game. This is the strong integration check that the apply
   path stays consistent with Game.next_turn() over many turns.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Headless display/audio so Game (which constructs Config -> fonts/sounds) and
# pygame.display are not required.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

import random
import pytest


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except pygame.error:
        pass


from game import Game
from ai_controller import AIController
from players import RandomPlayer


def test_is_ai_turn_reflects_color_and_game_over():
    game = Game()  # white to move at the start
    white_ai = AIController('white')
    black_ai = AIController('black')
    assert white_ai.is_ai_turn(game) is True
    assert black_ai.is_ai_turn(game) is False
    # When the game is over, it's nobody's AI turn.
    game.winner = 'white'
    assert white_ai.is_ai_turn(game) is False
    assert black_ai.is_ai_turn(game) is False


def test_constructor_rejects_bad_color():
    with pytest.raises(ValueError):
        AIController('green')


def test_take_turn_applies_one_legal_turn_and_advances():
    random.seed(1234)
    game = Game()
    ai = AIController('white')

    turn_number_before = game.board.turn_number
    mover_before = game.next_player           # 'white'
    assert ai.is_ai_turn(game)

    took = ai.take_turn(game)

    assert took is True
    # Exactly one turn advanced: turn_number incremented and side-to-move flipped.
    assert game.board.turn_number == turn_number_before + 1
    assert game.next_player != mover_before   # now 'black'
    # It's no longer white's AI turn.
    assert ai.is_ai_turn(game) is False


def test_take_turn_is_noop_when_not_ai_turn():
    game = Game()                 # white to move
    ai = AIController('black')    # AI plays black, so it's NOT the AI's turn
    turn_number_before = game.board.turn_number
    assert ai.is_ai_turn(game) is False
    took = ai.take_turn(game)
    assert took is False
    assert game.board.turn_number == turn_number_before
    assert game.next_player == 'white'


def test_full_random_ai_vs_ai_game_runs_to_completion():
    """Two AIControllers play a full game. The game must terminate (a winner,
    or the no-legal-moves loss, or the turn cap) without raising, and real
    turns must be taken. Exercises every turn type over a real game."""
    random.seed(2024)
    game = Game()
    white_ai = AIController('white')
    black_ai = AIController('black')
    controllers = {'white': white_ai, 'black': black_ai}

    cap = 400
    turns_taken = 0
    while game.winner is None and turns_taken < cap:
        controller = controllers[game.next_player]
        took = controller.take_turn(game)
        if not took:
            # No legal turn was available; Game.next_turn() should have set a
            # winner via the no-legal-moves loss when this turn began.
            break
        turns_taken += 1

    # The game advanced through real turns without raising.
    assert turns_taken > 0
    assert game.board.turn_number == turns_taken
    # It either produced a winner or is still legally in progress at the cap
    # (random play frequently fails to force a decisive result quickly).
    assert game.winner in (None, 'white', 'black')
    if game.winner is None:
        assert turns_taken == cap
