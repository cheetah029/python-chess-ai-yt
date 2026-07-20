"""Unified cancel affordances for the three in-turn cancelable
states (user request 2026-07-20):

  "Since pawn promotion and knight jump capture allow esc to cancel,
   also allow esc to cancel queen transformation, and any similar
   cues, so that all 3 can be canceled in similar ways and as many
   ways as possible."

Target matrix (Game-layer parts tested here; the mouse wiring lives
in main.py and mirrors the same Game methods):

  state            Esc   right-click   left-click outside
  jump-capture     yes   yes           yes  (outside highlights)
  promotion menu   yes   yes (NEW)     yes
  transform menu   yes (NEW)  yes-away (NEW)  yes

Each state has a symmetric Game.cancel_* method:
cancel_jump_capture / cancel_promotion / cancel_transformation
(the last is NEW — closing the menu without transforming; nothing
has been applied yet, so no snapshot restore is involved).
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
from piece import King, Queen
from move import Move
from square import Square


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _game_with_open_transform_menu():
    """Game with a transformable white queen at (5,3) and its
    right-click menu open (as main.py opens it)."""
    g = Game()
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
    options = b.get_transformation_options(wq)
    options = b.filter_transformation_options(wq, 5, 3, options, 'white')
    assert options    # setup sanity
    g.transform_menu = {
        'piece': wq,
        'piece_color': wq.color,
        'row': 5,
        'col': 3,
        'options': options,
    }
    return g, b, wq


# ---- Game.cancel_transformation -----------------------------------------

def test_cancel_transformation_closes_menu_without_transforming():
    g, b, wq = _game_with_open_transform_menu()
    assert g.cancel_transformation() is True
    assert g.transform_menu is None
    assert g.transform_menu_rects == []
    # Nothing was applied: still the same queen, highlight untouched.
    assert b.squares[5][3].piece is wq
    assert b.last_action is None
    assert g.next_player == 'white'


def test_cancel_transformation_without_menu_is_noop():
    g = Game()
    assert g.cancel_transformation() is False


# ---- Esc cancels the transform menu (the NEW cue) ------------------------

def test_escape_cancels_transform_menu():
    g, b, wq = _game_with_open_transform_menu()
    result = g.handle_keydown(pygame.K_ESCAPE)
    assert result['consumed']
    assert g.transform_menu is None
    assert b.squares[5][3].piece is wq       # no transformation happened


def test_escape_priority_transform_menu_before_paused_screens():
    """Esc closes ONE thing per press: the in-turn transform menu
    outranks the paused screens, matching jump-capture/promotion."""
    g, b, wq = _game_with_open_transform_menu()
    g.reset_confirm_pending = True
    g._handle_escape()
    assert g.transform_menu is None
    assert g.reset_confirm_pending is True
    g._handle_escape()
    assert g.reset_confirm_pending is False


# ---- parity: all three states cancel on Esc ------------------------------

def test_escape_parity_across_all_three_states():
    """Esc cancels each of the three in-turn states via the cascade.
    (Jump-capture and promotion are covered in depth in their own
    files; this asserts the three-way parity in one place.)"""
    # transform menu
    g, _, _ = _game_with_open_transform_menu()
    g._handle_escape()
    assert g.transform_menu is None

    # promotion menu (minimal state: menu + snapshot, as main.py sets)
    g2 = Game()
    snap = g2._snapshot()
    g2.promotion_menu = {'pawn': None, 'row': 0, 'col': 0}
    g2._pre_promotion_snapshot = snap
    g2._handle_escape()
    assert g2.promotion_menu is None

    # jump capture (minimal state: targets + snapshot)
    g3 = Game()
    snap3 = g3._snapshot()
    g3.jump_capture_targets = [(3, 3)]
    g3.jump_capture_landing = (4, 4)
    g3._pre_jump_capture_snapshot = snap3
    g3._handle_escape()
    assert g3.jump_capture_targets is None


# ---- right-click inside an option square is a NO-OP ----------------------
# (user refinement 2026-07-20: a right-click on a menu option is more
# likely a mis-pressed left click than a cancel attempt — do nothing.
# Right-click OUTSIDE the option squares still cancels. main.py gates
# its right-click cancel paths on these point_in_* helpers.)

def _rect_probe_points(rects):
    """(inside, outside) screen points for a populated rects list:
    the center of the first option rect, and a point safely outside
    the union of all rects."""
    assert rects    # renderer must have populated them
    first = rects[0][0]
    inside = first.center
    max_right = max(r.right for r, _ in rects)
    max_bottom = max(r.bottom for r, _ in rects)
    outside = (max_right + 50, max_bottom + 50)
    for r, _ in rects:
        assert not r.collidepoint(outside)
    return inside, outside


def test_point_in_transform_menu():
    from const import WIDTH, HEIGHT
    g, b, wq = _game_with_open_transform_menu()
    surface = pygame.Surface((WIDTH, HEIGHT))
    g.show_transform_menu(surface)       # populates transform_menu_rects
    inside, outside = _rect_probe_points(g.transform_menu_rects)
    assert g.point_in_transform_menu(inside) is True
    assert g.point_in_transform_menu(outside) is False


def test_point_in_transform_menu_without_menu_is_false():
    g = Game()
    assert g.point_in_transform_menu((0, 0)) is False


def test_point_in_promotion_menu():
    from const import WIDTH, HEIGHT
    from piece import Pawn
    g = Game()
    b = g.board
    wp = Pawn('white')
    b.squares[0][3].piece = wp
    g.promotion_menu = {
        'pawn': wp,
        'pawn_color': 'white',
        'row': 0,
        'col': 3,
        'captured': False,
        'was_manipulation': False,
    }
    surface = pygame.Surface((WIDTH, HEIGHT))
    g.show_promotion_menu(surface)       # populates promotion_menu_rects
    inside, outside = _rect_probe_points(g.promotion_menu_rects)
    assert g.point_in_promotion_menu(inside) is True
    assert g.point_in_promotion_menu(outside) is False


def test_point_in_promotion_menu_without_menu_is_false():
    g = Game()
    assert g.point_in_promotion_menu((0, 0)) is False


# ---- right-click on the open menu's own piece square toggles it ----------
# (user refinement 2026-07-20: the piece's own square is NOT a menu
# option, so a right-click there cancels — right-clicking a queen
# twice opens then closes the menu. main.py stops the #137
# fall-through from immediately reopening in this one case.)

def test_is_transform_menu_piece_square():
    g, b, wq = _game_with_open_transform_menu()
    assert g.is_transform_menu_piece_square(5, 3) is True
    assert g.is_transform_menu_piece_square(5, 4) is False
    assert g.is_transform_menu_piece_square(0, 0) is False


def test_is_transform_menu_piece_square_without_menu_is_false():
    g = Game()
    assert g.is_transform_menu_piece_square(5, 3) is False


def test_piece_square_is_not_inside_option_rects():
    """Geometry guard: the option strip anchors one square away from
    the piece, so the piece's own square must never fall inside the
    option rects — otherwise the right-click no-op zone would shadow
    the toggle-close zone and right-click-twice could not close."""
    from const import WIDTH, HEIGHT, SQSIZE
    g, b, wq = _game_with_open_transform_menu()
    surface = pygame.Surface((WIDTH, HEIGHT))
    g.show_transform_menu(surface)       # populates transform_menu_rects
    sr, sc = g.board_to_screen(5, 3)
    queen_center = (sc * SQSIZE + SQSIZE // 2, sr * SQSIZE + SQSIZE // 2)
    assert g.point_in_transform_menu(queen_center) is False
    assert g.is_transform_menu_piece_square(5, 3) is True


# ---- jump-capture choice squares (board-space no-op zone) ----------------
# (user refinement 2026-07-20: right-click ON a highlighted choice
# square — the jumped piece or the landing square — is a NO-OP, same
# mis-pressed-left-click reasoning as the menus; right-click elsewhere
# cancels. main.py consults is_jump_choice_square in BOTH mouse
# handlers.)

def test_is_jump_choice_square():
    g = Game()
    g.jump_capture_targets = [(3, 3)]
    g.jump_capture_landing = (4, 4)
    assert g.is_jump_choice_square(3, 3) is True    # jumped piece
    assert g.is_jump_choice_square(4, 4) is True    # landing square
    assert g.is_jump_choice_square(5, 5) is False   # elsewhere
    assert g.is_jump_choice_square(-1, 9) is False  # off-board


def test_is_jump_choice_square_without_jump_state_is_false():
    g = Game()
    assert g.is_jump_choice_square(3, 3) is False


# ---- cancel-then-open: options must come from the RESTORED board ---------

def test_promotion_cancel_then_transform_options_use_restored_board():
    """The cancel-and-open-menu flow (right-click on a transformable
    queen while the promotion menu is open) must re-look-up the piece
    and recompute options AFTER the snapshot restore: the restore
    replaces every piece object, so both the pre-cancel queen object
    and any options computed against the mid-promotion board would be
    stale. main.py achieves this by falling through to the normal
    right-click handler after cancel_promotion(); this test pins the
    Game-layer contract that makes that ordering correct."""
    from piece import Pawn
    g = Game()
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
    wp = Pawn('white')
    wp.moved = True
    b.squares[1][6].piece = wp
    b.turn_number = 10
    g.next_player = 'white'

    # Enter the promotion state exactly as main.py does.
    snap = g._snapshot()
    b.move(wp, Move(Square(1, 6), Square(0, 6)))
    g.promotion_menu = {'pawn': wp, 'pawn_color': 'white', 'row': 0,
                        'col': 6, 'captured': False,
                        'was_manipulation': False}
    g._pre_promotion_snapshot = snap

    assert g.cancel_promotion() is True
    # The queen object was replaced by the restore — the fall-through
    # handler must use the CURRENT board's piece, not a stale ref.
    restored_queen = b.squares[5][3].piece
    assert isinstance(restored_queen, Queen)
    assert restored_queen is not wq
    # And options computed post-restore are valid for the restored
    # position (rook unlocked via the captured-piece list).
    options = b.get_transformation_options(restored_queen)
    options = b.filter_transformation_options(
        restored_queen, 5, 3, options, 'white')
    assert 'rook' in options
    # The pawn is back home; the turn did not advance.
    assert isinstance(b.squares[1][6].piece, Pawn)
    assert b.squares[0][6].piece is None
    assert g.next_player == 'white'
