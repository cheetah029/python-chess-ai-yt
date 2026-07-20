"""Regression tests for the transformation-highlight behavior
(user-reported 2026-06-16, spec corrected 2026-07-20):

  "When you right-click on the queen to transform, the last move's
   highlighted square immediately changes to the queen's square …"
  then, correcting PR #121's over-broad fix:
  "the highlight should still change after an action has been
   performed, just not before it is performed when it is still being
   attempted. So change it to the queen's square only after the
   transformation is completed."

FINAL SPEC:
  - While a transformation is merely ATTEMPTED (right-click menu
    open — which repetition-SIMULATES each option through
    `transform_queen` — or canceled), the highlight stays on the
    previous spatial move's squares.
  - After a transformation COMPLETES for real, the highlight moves
    to the queen's square (single-square `last_action` render,
    preferred over `last_move`).

LAYERING: `Board.transform_queen` only touches `last_action` when
its `record_highlight` parameter is explicitly True. The default
(False) keeps every simulation path safe — the repetition filter,
trainer, and engine playouts all call with the default. Only the
two real-execution sites pass True: the transform-menu confirmation
click in main.py, and `AIController._apply_transformation`.
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


def _rebuild_game_board(g):
    """Rebuild g's board in place (preserving the Game->Board
    reference) into the transformable-queen position above."""
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
    return b, wq


# ---- attempts must not touch the highlight ------------------------------

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


def test_transform_queen_default_does_not_set_highlight():
    """Default transform_queen call (the simulation-path signature)
    must NOT set last_action. Simulation callers — repetition filter,
    trainer, engine playouts — all use the default, so any highlight
    side effect here would leak into the UI the moment the
    right-click menu opens."""
    b, wq = _board_with_transformable_queen()
    b.transform_queen(wq, 5, 3, 'rook')
    assert isinstance(b.squares[5][3].piece, Rook)   # transform worked
    assert b.last_action is None
    assert b.last_move.initial.row == 2 and b.last_move.final.row == 3


# ---- a COMPLETED transformation moves the highlight ---------------------

def test_transform_queen_record_highlight_sets_last_action():
    """The real-execution signature (record_highlight=True) marks the
    queen's square as the action highlight."""
    b, wq = _board_with_transformable_queen()
    b.transform_queen(wq, 5, 3, 'rook', record_highlight=True)
    assert isinstance(b.squares[5][3].piece, Rook)
    assert b.last_action == Square(5, 3), (
        'a completed transformation must move the highlight to the '
        "queen's square (corrected user spec 2026-07-20)")
    # last_move itself is untouched — precedence is a render concern.
    assert b.last_move.initial.row == 2 and b.last_move.final.row == 3


def test_ai_transformation_sets_action_highlight():
    """The AI real-execution path (AIController._apply_transformation)
    must record the action highlight just like the human menu click."""
    from game import Game
    from ai_controller import AIController
    from engine import Turn
    g = Game()
    b, wq = _rebuild_game_board(g)
    g.next_player = 'white'
    turn = Turn('transformation', piece=wq, from_sq=(5, 3),
                transform_target='rook')
    ai = AIController('white')
    ai._apply_transformation(g, turn)
    assert isinstance(b.squares[5][3].piece, Rook)
    assert b.last_action == Square(5, 3)


def test_next_spatial_move_clears_action_highlight():
    """Board.move resets last_action, so the very next spatial move
    hands the highlight back to last_move."""
    b, wq = _board_with_transformable_queen()
    b.transform_queen(wq, 5, 3, 'rook', record_highlight=True)
    assert b.last_action is not None
    rook = b.squares[5][3].piece
    b.move(rook, Move(Square(5, 3), Square(5, 4)))
    assert b.last_action is None


# ---- rendering: the actual pixels ---------------------------------------

def _painted_probe(g):
    from const import SQSIZE
    sentinel = (1, 2, 3)
    surface = pygame.Surface((SQSIZE * 8, SQSIZE * 8))
    surface.fill(sentinel)
    g.show_last_move(surface)

    def center_px(row, col):
        sr, sc = g.board_to_screen(row, col)
        return surface.get_at(
            (sc * SQSIZE + SQSIZE // 2, sr * SQSIZE + SQSIZE // 2))[:3]

    return sentinel, center_px


def test_show_last_move_after_menu_open_only():
    """After ONLY opening the menu (simulation ran, nothing chosen),
    show_last_move paints the last move's two squares and does NOT
    paint the queen's square."""
    from game import Game
    g = Game()
    b, wq = _rebuild_game_board(g)

    options = b.get_transformation_options(wq)
    b.filter_transformation_options(wq, 5, 3, options, 'white')

    sentinel, center_px = _painted_probe(g)
    assert center_px(2, 2) != sentinel
    assert center_px(3, 2) != sentinel
    assert center_px(5, 3) == sentinel, (
        "the queen's square must not be highlighted while the "
        'transformation is merely being attempted')


def test_show_last_move_after_completed_transformation():
    """After a REAL completed transformation, show_last_move paints
    the queen's square (single-square action highlight) and no longer
    paints the previous move's squares (last_action takes render
    precedence over last_move)."""
    from game import Game
    g = Game()
    b, wq = _rebuild_game_board(g)

    # Menu open (simulation)… then the real confirmation click.
    options = b.get_transformation_options(wq)
    b.filter_transformation_options(wq, 5, 3, options, 'white')
    b.transform_queen(wq, 5, 3, 'rook', record_highlight=True)

    sentinel, center_px = _painted_probe(g)
    assert center_px(5, 3) != sentinel, (
        "the queen's square must be highlighted after the "
        'transformation is completed (corrected user spec)')
    assert center_px(2, 2) == sentinel
    assert center_px(3, 2) == sentinel
