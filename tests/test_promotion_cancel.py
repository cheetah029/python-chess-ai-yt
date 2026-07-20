"""Tests for cancelable pawn promotion (user request 2026-07-20):

  "I want to enable pawn promotions to be canceled in a similar way
   to how the queen transformation can be canceled."

RULE GROUNDING (RULEBOOK_v2.md): upon reaching the last rank, a pawn
MUST promote — a pawn may never sit unpromoted on the last rank. So
"canceling a promotion" necessarily means canceling the whole pawn
MOVE: the board reverts to the pre-move state (pawn back at origin,
any captured piece restored) and the turn does NOT advance — the
player then chooses a different legal turn. This mirrors the
existing jump-capture cancel, and reuses its pre-move snapshot
mechanism (`Game._snapshot` / `Game._restore`).

UI triggers (wired in main.py, tested at the Game layer here):
  - left-click outside the promotion menu options
  - Esc (via the `_handle_escape` cascade)
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

from game import Game
from piece import King, Pawn, Rook, Queen
from move import Move
from square import Square


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _game_with_promotion_ready(capture_target=False):
    """Game whose board is rebuilt in place: white pawn at (1,3) one
    step from promotion, kings, a recorded previous last_move, and
    (optionally) a black rook at (0,4) as a capture-promotion target."""
    g = Game()
    b = g.board
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[7][7].piece = King('white')
    b.squares[0][0].piece = King('black')
    wp = Pawn('white')
    wp.moved = True
    b.squares[1][3].piece = wp
    if capture_target:
        b.squares[0][4].piece = Rook('black')
    b.last_move = Move(Square(5, 5), Square(4, 5))
    b.last_move_turn_number = 9
    b.turn_number = 10
    g.next_player = 'white'
    return g, b, wp


def _enter_promotion_state(g, b, wp, final_row, final_col, captured):
    """Mirror main.py's promotion-menu entry: snapshot BEFORE the
    move (same snapshot the jump-capture cancel uses), apply the
    spatial move, then open the menu retaining the snapshot."""
    pre_move_snapshot = g._snapshot()
    move = Move(Square(1, 3), Square(final_row, final_col))
    b.move(wp, move)
    assert b.check_promotion(wp, move.final)   # setup sanity
    g.promotion_menu = {
        'pawn': wp,
        'pawn_color': wp.color,
        'row': final_row,
        'col': final_col,
        'captured': captured,
        'was_manipulation': False,
    }
    g._pre_promotion_snapshot = pre_move_snapshot


# ---- Game.cancel_promotion ----------------------------------------------

def test_cancel_promotion_reverts_pawn_move():
    g, b, wp = _game_with_promotion_ready()
    _enter_promotion_state(g, b, wp, 0, 3, captured=False)
    assert b.squares[0][3].piece is wp      # move applied, menu open

    assert g.cancel_promotion() is True
    # Pawn back at origin, last rank empty again.
    assert isinstance(b.squares[1][3].piece, Pawn)
    assert b.squares[0][3].piece is None
    # Menu state fully cleared.
    assert g.promotion_menu is None
    assert g.promotion_menu_rects == []
    assert g._pre_promotion_snapshot is None
    # The turn did NOT advance.
    assert g.next_player == 'white'
    assert b.turn_number == 10
    # The previous last-move highlight is restored.
    assert b.last_move.initial == Square(5, 5)
    assert b.last_move.final == Square(4, 5)


def test_cancel_capture_promotion_restores_captured_piece():
    g, b, wp = _game_with_promotion_ready(capture_target=True)
    n_captured_before = len(b.captured_pieces['black'])
    _enter_promotion_state(g, b, wp, 0, 4, captured=True)
    assert b.squares[0][4].piece is wp      # rook captured by the pawn

    assert g.cancel_promotion() is True
    # The captured rook is back, the pawn is back at origin.
    restored = b.squares[0][4].piece
    assert isinstance(restored, Rook) and restored.color == 'black'
    assert isinstance(b.squares[1][3].piece, Pawn)
    assert len(b.captured_pieces['black']) == n_captured_before


def test_cancel_promotion_without_menu_is_noop():
    g, b, wp = _game_with_promotion_ready()
    assert g.cancel_promotion() is False
    assert g.next_player == 'white'


def test_completing_promotion_still_works_and_drops_snapshot():
    """The normal path (picking a form) is unaffected by the cancel
    machinery; the retained snapshot is dropped on completion so it
    cannot leak into a later cancel."""
    g, b, wp = _game_with_promotion_ready()
    _enter_promotion_state(g, b, wp, 0, 3, captured=False)
    menu = g.promotion_menu
    b.promote(menu['pawn'], menu['row'], menu['col'], 'queen')
    g.promotion_menu = None
    g.promotion_menu_rects = []
    g._pre_promotion_snapshot = None
    promoted = b.squares[0][3].piece
    assert isinstance(promoted, Queen) and not promoted.is_royal
    # A later cancel attempt must be a no-op.
    assert g.cancel_promotion() is False
    assert isinstance(b.squares[0][3].piece, Queen)


# ---- Esc cascade ---------------------------------------------------------

def test_escape_cancels_promotion():
    g, b, wp = _game_with_promotion_ready()
    _enter_promotion_state(g, b, wp, 0, 3, captured=False)
    g._handle_escape()
    assert g.promotion_menu is None
    assert isinstance(b.squares[1][3].piece, Pawn)
    assert b.squares[0][3].piece is None
    assert g.next_player == 'white'


def test_escape_priority_promotion_before_paused_screens():
    """With both a promotion menu and a paused screen open, Esc
    closes the promotion (in-turn state) first, then the paused
    screen on the next press — one thing per press, like the
    jump-capture entry in the cascade."""
    g, b, wp = _game_with_promotion_ready()
    _enter_promotion_state(g, b, wp, 0, 3, captured=False)
    g.reset_confirm_pending = True
    g._handle_escape()
    assert g.promotion_menu is None
    assert g.reset_confirm_pending is True
    g._handle_escape()
    assert g.reset_confirm_pending is False
