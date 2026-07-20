"""Regression tests for the transformation-highlight bug
(user-reported 2026-06-16):

  "When you right-click on the queen to transform, the last move's
   highlighted square immediately changes to the queen's square …
   the original last square becomes unhighlighted. This causes the
   wrong last move square to be highlighted if the transformation
   is canceled afterwards."

ROOT CAUSE (two parts):
  1. `Board.transform_queen` set `board.last_action = Square(row,
     col)` and `Game.show_last_move` PREFERRED `last_action` over
     the real `last_move` when rendering the highlight.
  2. Opening the right-click transform menu runs
     `filter_transformation_options`, whose repetition check
     SIMULATES each option via `transform_queen` — clobbering
     `last_action` the moment the menu opens, with no restore.

SPEC (user): the highlight must always stay on the last move's
squares and never switch to the queen's square for a
transformation attempt — regardless of whether the transformation
is completed or canceled. Accordingly the `last_action` highlight
override is REMOVED: transformations (simulated OR real) never
touch the last-move highlight.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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

from board import Board
from piece import King, Queen, Rook
from move import Move
from square import Square


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _board_with_transformable_queen():
    """Empty board with: white royal queen at (5,3) (with a captured
    rook so a rook-transformation option exists), kings, and a
    recorded last_move between two OTHER squares (2,2)->(3,2)."""
    b = Board()
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[7][7].piece = King('white')
    b.squares[0][0].piece = King('black')
    wq = Queen('white', is_royal=True)
    b.squares[5][3].piece = wq
    # A friendly rook was captured earlier -> 'rook' transform unlocks.
    b.captured_pieces['white'].append('rook')
    # The REAL last move: some earlier spatial move elsewhere.
    b.last_move = Move(Square(2, 2), Square(3, 2))
    b.last_move_turn_number = 9
    b.turn_number = 10
    return b, wq


# ---- part 2 of the bug: menu-open simulation must not clobber -----------

def test_filter_transformation_options_does_not_touch_highlight_state():
    """Opening the transform menu (which repetition-filters each
    option by SIMULATING it) must leave last_move AND last_action
    untouched — this was the immediate highlight-jump the user saw."""
    b, wq = _board_with_transformable_queen()
    saved_last_move = b.last_move
    options = b.get_transformation_options(wq)
    assert 'rook' in options    # setup sanity
    b.filter_transformation_options(wq, 5, 3, options, 'white')
    assert b.last_move is saved_last_move
    assert b.last_action is None, (
        'simulating transformation options must not set last_action '
        '(this was the highlight jumping to the queen square the '
        'moment the right-click menu opened)')


def test_would_transformation_cause_repetition_restores_highlight_state():
    b, wq = _board_with_transformable_queen()
    b.would_transformation_cause_repetition(wq, 5, 3, 'rook', 'white')
    assert b.last_action is None
    assert b.last_move.initial.row == 2 and b.last_move.final.row == 3


# ---- the spec: even a COMPLETED transformation keeps the highlight ------

def test_completed_transformation_does_not_move_highlight():
    """Per user spec, a completed transformation must not switch the
    highlight to the queen's square: last_action stays None and
    last_move keeps pointing at the previous spatial move."""
    b, wq = _board_with_transformable_queen()
    b.transform_queen(wq, 5, 3, 'rook')
    assert isinstance(b.squares[5][3].piece, Rook)   # transform worked
    assert b.last_action is None, (
        'transform_queen must no longer set the last_action '
        'highlight override')
    assert b.last_move.initial.row == 2 and b.last_move.final.row == 3


# ---- rendering: the actual pixels ---------------------------------------

def test_show_last_move_highlights_move_squares_not_queen_square():
    """End-to-end at the render layer: after opening-menu simulation
    AND a completed transformation, show_last_move paints the last
    move's two squares and does NOT paint the queen's square."""
    from game import Game
    g = Game()
    # Rebuild g's board into the test position (in place, preserving
    # the Game->Board reference).
    b = g.board
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[7][7].piece = King('white')
    b.squares[0][0].piece = King('black')
    wq = Queen('white', is_royal=True)
    b.squares[5][3].piece = wq
    b.captured_pieces['white'].append('rook')
    b.last_move = Move(Square(2, 2), Square(3, 2))
    b.last_move_turn_number = 9
    b.turn_number = 10

    # Simulate the user flow: right-click opens menu (filter runs)…
    options = b.get_transformation_options(wq)
    b.filter_transformation_options(wq, 5, 3, options, 'white')
    # …and then the transformation completes.
    b.transform_queen(wq, 5, 3, 'rook')

    from const import SQSIZE
    sentinel = (1, 2, 3)
    surface = pygame.Surface((SQSIZE * 8, SQSIZE * 8))
    surface.fill(sentinel)
    g.show_last_move(surface)

    def center_px(row, col):
        sr, sc = g.board_to_screen(row, col)
        return surface.get_at(
            (sc * SQSIZE + SQSIZE // 2, sr * SQSIZE + SQSIZE // 2))[:3]

    # Last move's squares ARE highlighted…
    assert center_px(2, 2) != sentinel
    assert center_px(3, 2) != sentinel
    # …and the queen's square is NOT.
    assert center_px(5, 3) == sentinel, (
        "the queen's square must not be highlighted after a "
        'transformation attempt/completion')
