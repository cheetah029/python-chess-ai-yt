"""Tests for `Game.handle_keydown(key)` — the centralised KEYDOWN
dispatch extracted from main.py.

Why extract: main.py's KEYDOWN block had grown to ~80 lines of nested
ifs with two parallel sub-dispatches (reset-confirm-active vs normal),
each duplicating T / F / reset-toggle handling. Moving the logic onto
the Game lets us:

  - Unit-test every key in every state (HvH / HvAI / CvC × dialog-open
    / mode-menu-open / reset-confirm / clean).
  - Collapse the duplication by sharing helpers between the two
    sub-dispatches.
  - Keep main.py's event loop a thin caller.

Contract:

    result = game.handle_keydown(pygame_key_constant)

`result` is a small dict:

    {
      'consumed': bool,       # whether this dispatcher handled the key
      'reset_happened': bool, # whether game.reset() ran (main.py must
                              # re-fetch its local board/dragger refs)
      'sound':     'capture' | 'move' | None,  # any sound to play
    }

This avoids the previous in-place reassignment ugliness in main.py.
The reset_happened flag is exactly the signal main.py needs to refresh
its local `board` / `dragger` references.
"""

import sys
import os
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

import random
import pytest

from game import Game
from ai_controller import AIController


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


# ---- result shape ---------------------------------------------------------

def test_handle_keydown_returns_dict_with_expected_keys():
    g = Game()
    result = g.handle_keydown(pygame.K_t)
    assert isinstance(result, dict)
    for key in ('consumed', 'reset_happened'):
        assert key in result, f"missing key {key!r} in {result}"


def test_unknown_key_is_not_consumed():
    g = Game()
    result = g.handle_keydown(pygame.K_a)  # 'a' is not bound
    assert result['consumed'] is False


# ---- P: toggle PGN dialog -------------------------------------------------

def test_p_opens_pgn_dialog_when_closed():
    g = Game()
    assert g.pgn_dialog_open is False
    result = g.handle_keydown(pygame.K_p)
    assert result['consumed'] is True
    assert g.pgn_dialog_open is True


def test_p_closes_pgn_dialog_when_open():
    g = Game()
    g.open_pgn_dialog()
    g.handle_keydown(pygame.K_p)
    assert g.pgn_dialog_open is False


# ---- M: toggle mode menu, closes PGN dialog ------------------------------

def test_m_opens_mode_menu_when_closed():
    g = Game()
    g.handle_keydown(pygame.K_m)
    assert g.mode_menu is not None


def test_m_closes_pgn_dialog_when_opening():
    """Mutual exclusion: M from PGN-open state closes PGN + opens mode."""
    g = Game()
    g.open_pgn_dialog()
    g.handle_keydown(pygame.K_m)
    assert g.pgn_dialog_open is False
    assert g.mode_menu is not None


def test_m_closes_mode_menu_when_open():
    g = Game()
    g.open_mode_menu()
    g.handle_keydown(pygame.K_m)
    assert g.mode_menu is None


# ---- Esc: cascade close (jump-capture > mode > PGN > nothing) ----------

def test_esc_closes_mode_menu():
    g = Game()
    g.open_mode_menu()
    g.handle_keydown(pygame.K_ESCAPE)
    assert g.mode_menu is None


def test_esc_closes_pgn_dialog():
    g = Game()
    g.open_pgn_dialog()
    g.handle_keydown(pygame.K_ESCAPE)
    assert g.pgn_dialog_open is False


def test_esc_with_nothing_open_is_a_noop():
    g = Game()
    result = g.handle_keydown(pygame.K_ESCAPE)
    # No menus to close, but consumed is fine either way — what matters
    # is the game state didn't change.
    assert g.mode_menu is None
    assert g.pgn_dialog_open is False
    assert g.board.turn_number == 0


# ---- T (theme) and F (flip) — always available ---------------------------

def test_t_changes_theme():
    g = Game()
    initial_idx = g.config.idx
    g.handle_keydown(pygame.K_t)
    assert g.config.idx != initial_idx


def test_f_flips_board():
    g = Game()
    initial = g.flipped
    g.handle_keydown(pygame.K_f)
    assert g.flipped != initial


def test_t_works_while_pgn_dialog_open():
    """Theme change is a viewing pref — always available, even from
    the paused state."""
    g = Game()
    g.open_pgn_dialog()
    initial_idx = g.config.idx
    g.handle_keydown(pygame.K_t)
    assert g.config.idx != initial_idx


def test_f_works_while_mode_menu_open():
    g = Game()
    g.open_mode_menu()
    initial = g.flipped
    g.handle_keydown(pygame.K_f)
    assert g.flipped != initial


def test_t_works_while_reset_confirm_pending():
    g = Game()
    g.reset_confirm_pending = True
    initial_idx = g.config.idx
    g.handle_keydown(pygame.K_t)
    assert g.config.idx != initial_idx
    # Reset-confirm survives — T is allowed but doesn't dismiss it.
    assert g.reset_confirm_pending is True


# ---- U / Y: undo / redo with CvC auto-pause ------------------------------

def _advance(g, n):
    for _ in range(n):
        if g.winner is not None:
            return
        ctrl = AIController(g.next_player)
        ctrl.take_turn(g)


def test_u_undoes_in_hvh_no_dialog_open():
    random.seed(101)
    g = Game()
    _advance(g, 3)
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number == 2
    # In HvH no dialog auto-opens.
    assert g.pgn_dialog_open is False


def test_y_redoes_in_hvh_no_dialog_open():
    random.seed(103)
    g = Game()
    _advance(g, 3)
    g.undo()
    assert g.board.turn_number == 2
    g.handle_keydown(pygame.K_y)
    assert g.board.turn_number == 3
    assert g.pgn_dialog_open is False


def test_u_in_cvc_no_paused_state_undoes_and_halts():
    """Spec revision 2026-07-20 (supersedes the 2026-05-30 no-op
    rule): U in CvC without a paused state undoes and halts autoplay
    (cvc_autoplay_halted); it still does NOT auto-open the dialog."""
    random.seed(107)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(3):
        g.current_ai_controller().take_turn(g)
    assert g.board.turn_number == 3
    g.handle_keydown(pygame.K_u)
    assert g.pgn_dialog_open is False  # NOT auto-opened
    assert g.board.turn_number < 3     # undone
    assert g.cvc_autoplay_halted is True


def test_y_in_cvc_no_paused_state_redoes_and_halts():
    random.seed(109)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(4):
        g.current_ai_controller().take_turn(g)
    g.undo()  # via direct call — testing the keydown gate, not
              # can_undo guard
    g.handle_keydown(pygame.K_y)
    assert g.pgn_dialog_open is False
    assert g.board.turn_number == 4    # Y redid the undone turn
    assert g.cvc_autoplay_halted is True


def test_u_in_cvc_with_dialog_open_undoes_normally():
    """When a paused state IS open in CvC, U works."""
    random.seed(113)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(3):
        g.current_ai_controller().take_turn(g)
    g.open_pgn_dialog()
    g.handle_keydown(pygame.K_u)
    assert g.pgn_dialog_open is True  # still open
    assert g.board.turn_number == 2


# ---- R: opens reset-confirm ----------------------------------------------

def test_r_opens_reset_confirm():
    g = Game()
    g.handle_keydown(pygame.K_r)
    assert g.reset_confirm_pending is True


def test_r_works_from_paused_state():
    """User spec: R from paused state opens reset confirm."""
    g = Game()
    g.open_pgn_dialog()
    g.handle_keydown(pygame.K_r)
    assert g.reset_confirm_pending is True


# ---- reset-confirm intercept: Y / Enter / N / Esc / R / T / F ------------

def test_reset_confirm_y_no_longer_confirms_reset():
    """2026-05-30 evening user spec change: Y is no longer a confirm
    key (it collided with Y-as-redo). Only Enter confirms."""
    random.seed(127)
    g = Game()
    _advance(g, 2)
    g.reset_confirm_pending = True
    result = g.handle_keydown(pygame.K_y)
    assert result.get('reset_happened') is False
    # Reset confirm STILL pending — Y did not confirm.
    assert g.reset_confirm_pending is True
    # Y as redo would have tried to redo but redo stack is empty
    # at this point — so board state unchanged.
    assert g.board.turn_number == 2


def test_reset_confirm_enter_confirms_reset():
    random.seed(131)
    g = Game()
    _advance(g, 2)
    g.reset_confirm_pending = True
    result = g.handle_keydown(pygame.K_RETURN)
    assert result.get('reset_happened') is True


def test_reset_confirm_n_cancels():
    random.seed(137)
    g = Game()
    _advance(g, 2)
    g.reset_confirm_pending = True
    result = g.handle_keydown(pygame.K_n)
    assert result.get('reset_happened') is False
    assert g.reset_confirm_pending is False
    assert g.board.turn_number == 2  # unchanged


def test_reset_confirm_esc_cancels():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_ESCAPE)
    assert g.reset_confirm_pending is False


def test_reset_confirm_r_cancels():
    """User spec: pressing R again from reset-confirm cancels."""
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_r)
    assert g.reset_confirm_pending is False


def test_reset_confirm_t_still_changes_theme():
    g = Game()
    g.reset_confirm_pending = True
    initial = g.config.idx
    g.handle_keydown(pygame.K_t)
    assert g.config.idx != initial
    assert g.reset_confirm_pending is True  # confirm survives


def test_reset_confirm_f_still_flips_board():
    g = Game()
    g.reset_confirm_pending = True
    initial = g.flipped
    g.handle_keydown(pygame.K_f)
    assert g.flipped != initial
    assert g.reset_confirm_pending is True


def test_reset_confirm_falls_through_to_undo():
    """Per the 2026-05-30 unified spec: reset-confirm only intercepts
    Y/Enter/N/R; other keys fall through to normal dispatch. U undoes
    (the reset confirm survives — only opening M/P/R-toggle would
    cancel it). View prefs and undo/redo are treated as orthogonal
    to the reset decision."""
    random.seed(149)
    g = Game()
    _advance(g, 3)
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number == 2  # undo DID happen
    assert g.reset_confirm_pending is True  # reset still pending


def test_reset_confirm_canceled_when_opening_mode_menu():
    """Per unified spec: opening a competing paused screen is implicit
    'no' to the reset confirm. M opens mode menu AND cancels reset."""
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_m)
    assert g.mode_menu is not None  # opened
    assert g.reset_confirm_pending is False  # cancelled


def test_reset_confirm_canceled_when_opening_pgn_dialog():
    """Same as above, for P."""
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_p)
    assert g.pgn_dialog_open is True
    assert g.reset_confirm_pending is False


# ---- result['reset_happened'] is False in normal flows -------------------

def test_reset_happened_is_false_for_normal_keys():
    g = Game()
    for key in (pygame.K_t, pygame.K_f, pygame.K_p, pygame.K_m,
                pygame.K_u, pygame.K_y, pygame.K_r, pygame.K_ESCAPE):
        result = g.handle_keydown(key)
        assert result.get('reset_happened') is False, (
            f"unexpected reset_happened=True from key {pygame.key.name(key)}")
