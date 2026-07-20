"""Tests for undo/redo from the win screen and mid-game in CvC mode.

History of the spec (user-driven):
  - 2026-05-30: U/Y in CvC are no-ops unless a paused screen is open.
  - 2026-07-20 (#127): that gating wrongly swallowed U on the WIN
    SCREEN of a finished CvC game (live or loaded save).
  - 2026-07-20 (#129): the interim fix used a cvc_autoplay_halted
    flag (Esc to resume), extended to mid-game.
  - 2026-07-20 (FINAL, this file): the flag was confusing (invisible
    paused state; the user had to know to press Esc). Final spec: U/Y
    in CvC with no paused screen performs the undo/redo and then
    OPENS the pause (PGN) screen. This keeps the rule "undo/redo
    works only while a pause screen is open" consistent — the pause
    screen itself is the visible paused state, and closing it as
    normal (P / Esc) resumes autoplay. Works identically mid-game
    and on the win screen (the win screen renders behind paused
    screens).
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


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _cvc_game_over(n_turns=4):
    """CvC game with a few real turns of history and a declared
    winner (as main.py declares one after a decisive capture)."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(n_turns):
        assert g.current_ai_controller().take_turn(g)
    g.winner = 'white'
    return g


# ---- win screen ----------------------------------------------------------

def test_undo_from_cvc_win_screen_opens_pause_screen():
    g = _cvc_game_over()
    depth = len(g._history)
    result = g.handle_keydown(pygame.K_u)
    assert result['consumed']
    assert g.winner is None, (
        'U on the CvC win screen must undo (the game is over — the '
        'pause-screen gating must not swallow it)')
    assert len(g._history) < depth
    # The pause screen opened, providing the visible paused state.
    assert g.pgn_dialog_open is True
    assert g.is_autoplay_paused() is True


def test_undo_from_loaded_cvc_save_win_screen():
    """The original #126 scenario: load a finished CvC save, press U."""
    src = _cvc_game_over()
    text = src.serialize_to_text()
    g = Game()
    assert g.load_from_text(text) is True
    assert g.mode == 'computer_vs_computer' and g.winner == 'white'
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)
    assert g.winner is None
    assert len(g._history) < depth
    assert g.pgn_dialog_open is True


def test_subsequent_undo_redo_keep_working_in_pause_screen():
    """After the first U opens the pause screen, further U/Y work
    through the normal paused-screen gating (no re-open needed)."""
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.pgn_dialog_open is True
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)            # step further back
    assert len(g._history) < depth
    assert g.pgn_dialog_open is True        # still the same dialog
    g.handle_keydown(pygame.K_y)            # and redo forward again
    assert len(g._history) == depth


# ---- resuming autoplay ---------------------------------------------------

def test_closing_pause_screen_resumes_autoplay():
    """The normal close controls resume autoplay — no hidden state."""
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.is_autoplay_paused() is True
    g.handle_keydown(pygame.K_ESCAPE)       # Esc closes the dialog
    assert g.pgn_dialog_open is False
    assert g.is_autoplay_paused() is False


def test_p_also_closes_the_auto_opened_dialog():
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    g.handle_keydown(pygame.K_p)            # P toggles the dialog off
    assert g.pgn_dialog_open is False
    assert g.is_autoplay_paused() is False


# ---- mid-game ------------------------------------------------------------

def test_midgame_cvc_undo_opens_pause_screen():
    """Mid-game CvC: U undoes and opens the pause screen; the AIs
    hold while it is open."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(2):
        assert g.current_ai_controller().take_turn(g)
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)
    assert len(g._history) < depth
    assert g.pgn_dialog_open is True
    assert g.is_autoplay_paused() is True


def test_paused_screen_undo_does_not_stack_screens():
    """U with the mode menu open undoes through the existing gating
    and does NOT additionally open the pgn dialog."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(2):
        assert g.current_ai_controller().take_turn(g)
    g.open_mode_menu()
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)
    assert len(g._history) < depth
    assert g.mode_menu is not None
    assert g.pgn_dialog_open is False


# ---- other modes unaffected ---------------------------------------------

def test_hvh_undo_does_not_open_pause_screen():
    g = Game()
    ai = Game()
    ai.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(2):
        assert ai.current_ai_controller().take_turn(ai)
    ai.winner = 'white'
    text = ai.serialize_to_text()
    assert g.load_from_text(text) is True
    g.apply_mode_selection(white_player='human', black_player='human')
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)
    assert g.winner is None
    assert len(g._history) < depth
    assert g.pgn_dialog_open is False
