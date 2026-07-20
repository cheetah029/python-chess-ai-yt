"""Tests for the CvC key-dispatch behavior + the new undo/redo
gating rule.

User report (2026-05-30): in CvC mode, no key presses worked. Root
cause: main.py's autoplay-wait loop (the 600 ms pre-move pause)
only handled `pygame.QUIT` and silently dropped all KEYDOWN events.

Fix in main.py wires `Game.handle_keydown(event.key)` into the
wait loop too. This file does NOT directly exercise the main.py
loop (that's a long-running event loop); it tests the Game-side
key dispatch under the conditions main.py is asking it about
(CvC mode, no menu open) and trusts the small main.py wiring to
deliver the events.

Plus the new spec on undo/redo:
> "Disable undo/redo during computer vs computer mode and only
> enable it during the pause screen, mode menu, or reset
> confirmation screen."

So in CvC + no paused state, U / Y are NO-OPs. In CvC + any
paused state (pgn dialog / mode menu / reset confirm), U / Y
work normally. HvH / HvAI behaviour is UNCHANGED — undo/redo
always work.
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


def _advance_cvc(g, n):
    for _ in range(n):
        if g.winner is not None:
            return
        ctrl = g.current_ai_controller()
        if ctrl is None:
            return
        ctrl.take_turn(g)


# ===========================================================================
# Section 1 — non-undo keys (T / F / M / P / R) work during CvC
# ===========================================================================

def test_t_changes_theme_during_cvc():
    """View prefs always work — even during CvC autoplay."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.is_autoplay_paused() is False  # baseline: CvC is active
    initial = g.config.idx
    g.handle_keydown(pygame.K_t)
    assert g.config.idx != initial


def test_f_flips_board_during_cvc():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    initial = g.flipped
    g.handle_keydown(pygame.K_f)
    assert g.flipped != initial


def test_m_opens_mode_menu_during_cvc():
    """M during CvC must open the mode menu (pausing autoplay) — the
    user-reported bug was 'all keys disabled', and M is critical for
    switching out of CvC."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    g.handle_keydown(pygame.K_m)
    assert g.mode_menu is not None
    # And autoplay is now paused.
    assert g.is_autoplay_paused() is True


def test_p_opens_pgn_dialog_during_cvc():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    g.handle_keydown(pygame.K_p)
    assert g.pgn_dialog_open is True
    assert g.is_autoplay_paused() is True


def test_r_opens_reset_confirm_during_cvc():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    g.handle_keydown(pygame.K_r)
    assert g.reset_confirm_pending is True
    assert g.is_autoplay_paused() is True


# ===========================================================================
# Section 2 — NEW undo/redo gating: blocked in CvC unless paused state open
# ===========================================================================

def test_undo_halts_autoplay_in_cvc_with_no_paused_state():
    """Spec revision 2026-07-20 (supersedes the 2026-05-30 no-op
    rule): in CvC + no menu/dialog/confirm, U now performs the undo
    and HALTS autoplay (cvc_autoplay_halted) so the AIs don't replay
    over the undone position — same behavior as the win-screen undo
    of #127, now applied mid-game too. It still does NOT auto-open
    the pgn dialog (that older design remains reverted). Esc
    resumes autoplay."""
    random.seed(401)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 3)
    assert g.board.turn_number == 3
    assert g.is_autoplay_paused() is False  # no menu open
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number < 3          # the undo happened
    assert g.cvc_autoplay_halted is True
    assert g.is_autoplay_paused() is True   # AIs held
    assert g.pgn_dialog_open is False       # still no auto-open
    # Esc resumes autoplay.
    g.handle_keydown(pygame.K_ESCAPE)
    assert g.cvc_autoplay_halted is False
    assert g.is_autoplay_paused() is False


def test_redo_halts_autoplay_in_cvc_with_no_paused_state():
    random.seed(403)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 4)
    g.undo()
    assert g.board.turn_number == 3
    g.handle_keydown(pygame.K_y)
    # Y is NOT intercepted as 'yes' (no reset confirm pending); it
    # redoes and halts autoplay (2026-07-20 spec revision).
    assert g.board.turn_number == 4
    assert g.cvc_autoplay_halted is True
    assert g.pgn_dialog_open is False


def test_undo_works_in_cvc_when_pgn_dialog_open():
    """Paused state → undo allowed."""
    random.seed(407)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 3)
    g.open_pgn_dialog()
    assert g.is_autoplay_paused() is True
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number == 2


def test_undo_works_in_cvc_when_mode_menu_open():
    random.seed(409)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 3)
    g.open_mode_menu()
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number == 2


def test_undo_works_in_cvc_when_reset_confirm_pending():
    """Reset confirm is also a paused state — undo allowed.
    Note: U is NOT in the reset-confirm intercept's whitelist, so it
    falls through to normal dispatch, which now permits undo because
    a paused state is open."""
    random.seed(411)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 3)
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number == 2
    assert g.reset_confirm_pending is True  # reset survives


def test_redo_works_in_cvc_when_pgn_dialog_open():
    random.seed(413)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 4)
    g.undo()
    g.open_pgn_dialog()
    g.handle_keydown(pygame.K_y)
    assert g.board.turn_number == 4


# ===========================================================================
# Section 3 — HvH and HvAI undo/redo UNCHANGED
# ===========================================================================

def _advance_hvh(g, n):
    for _ in range(n):
        if g.winner is not None:
            return
        AIController(g.next_player).take_turn(g)


def test_undo_works_in_hvh_no_paused_state():
    """HvH: U undoes immediately, no CvC gating applies."""
    random.seed(421)
    g = Game()  # HvH default
    _advance_hvh(g, 3)
    g.handle_keydown(pygame.K_u)
    assert g.board.turn_number == 2


def test_undo_works_in_hvai_no_paused_state():
    random.seed(423)
    g = Game()
    g.apply_mode_selection(opponent='random')  # HvAI; AI = black
    _advance_hvh(g, 4)
    g.handle_keydown(pygame.K_u)
    # HvAI undo skips back to the previous USER turn.
    assert g.next_player == 'white'  # still user's turn after undo
    assert g.board.turn_number < 4


# ===========================================================================
# Section 4 — pgn dialog does NOT auto-open on U/Y in CvC anymore
# ===========================================================================

def test_u_in_cvc_no_paused_state_does_not_auto_open_dialog():
    """The pre-2026-05-30 behaviour (U auto-opened the PGN dialog)
    stays reverted under the 2026-07-20 spec revision too: U undoes
    and halts autoplay, but never opens the dialog itself."""
    random.seed(431)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 2)
    g.handle_keydown(pygame.K_u)
    assert g.pgn_dialog_open is False
    assert g.board.turn_number < 2          # the undo happened
    assert g.cvc_autoplay_halted is True


def test_y_in_cvc_no_paused_state_does_not_auto_open_dialog():
    random.seed(433)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 3)
    g.undo()  # need redo stack populated... but undo is normally
              # blocked in CvC — bypass via direct call (testing the
              # KEYDOWN path here, not the can_undo guard)
    g.handle_keydown(pygame.K_y)
    assert g.pgn_dialog_open is False
