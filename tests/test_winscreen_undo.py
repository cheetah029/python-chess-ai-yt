"""Tests for undo/redo from the win screen in CvC mode
(user report 2026-07-20: "I have a previously saved game but now I
cannot undo from the win screen").

ROOT CAUSE: the CvC undo/redo gating (2026-05-30 spec: undo only
during the pause screen, mode menu, or reset confirm) did not treat
the win screen as a paused state — `_handle_undo_key` dropped U
whenever mode == computer_vs_computer with no menu open, even after
the game had ended (live win screen AND loaded finished saves).

FIX: when a winner is set, the game is over and no autoplay is
running, so U/Y are allowed. The first such undo sets
`cvc_autoplay_halted`, which `is_autoplay_paused()` honors — so
(a) CvC autoplay does not instantly replay over the undone position
once the winner is cleared, and (b) subsequent U/Y presses keep
working while stepping through the finished game. Esc (bottom of
the cascade) resumes autoplay; mode changes, reset, and loading a
game clear the flag. Mid-game CvC gating is unchanged.
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


# ---- the reported bug ----------------------------------------------------

def test_undo_from_cvc_win_screen():
    g = _cvc_game_over()
    depth = len(g._history)
    result = g.handle_keydown(pygame.K_u)
    assert result['consumed']
    assert g.winner is None, (
        'U on the CvC win screen must undo (the game is over — the '
        'pause-screen gating must not apply)')
    assert len(g._history) < depth
    # Autoplay is halted so the AIs don't instantly replay over the
    # undone position.
    assert g.cvc_autoplay_halted is True
    assert g.is_autoplay_paused() is True


def test_undo_from_loaded_cvc_save_win_screen():
    """The user's exact scenario: load a finished CvC save, press U."""
    src = _cvc_game_over()
    text = src.serialize_to_text()
    g = Game()
    assert g.load_from_text(text) is True
    assert g.mode == 'computer_vs_computer' and g.winner == 'white'
    assert g.cvc_autoplay_halted is False   # load resets UI state
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)
    assert g.winner is None
    assert len(g._history) < depth


def test_subsequent_undo_redo_keep_working_while_halted():
    """After the first win-screen undo clears the winner, the halt
    flag keeps the gate open for further stepping."""
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.winner is None
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)            # step further back
    assert len(g._history) < depth
    g.handle_keydown(pygame.K_y)            # and redo forward again
    assert len(g._history) == depth


# ---- autoplay resume / flag lifecycle ------------------------------------

def test_escape_resumes_cvc_autoplay():
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.is_autoplay_paused() is True
    g._handle_escape()
    assert g.cvc_autoplay_halted is False
    assert g.is_autoplay_paused() is False


def test_escape_closes_menus_before_resuming_autoplay():
    """Esc cascade: one thing per press — an open paused screen
    closes first; the halt clears on the NEXT press."""
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    g.open_pgn_dialog()
    g._handle_escape()
    assert g.pgn_dialog_open is False
    assert g.cvc_autoplay_halted is True
    g._handle_escape()
    assert g.cvc_autoplay_halted is False


def test_mode_change_clears_halt():
    """Switching a side to human must clear the halt so HvAI/HvH
    autoplay is not silently blocked by a stale flag."""
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.cvc_autoplay_halted is True
    g.apply_mode_selection(white_player='human')
    assert g.cvc_autoplay_halted is False


def test_load_clears_halt():
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.cvc_autoplay_halted is True
    text = _cvc_game_over().serialize_to_text()
    assert g.load_from_text(text) is True
    assert g.cvc_autoplay_halted is False


def test_reset_clears_halt():
    g = _cvc_game_over()
    g.handle_keydown(pygame.K_u)
    assert g.cvc_autoplay_halted is True
    g.reset()
    assert g.cvc_autoplay_halted is False


# ---- the original mid-game gating is preserved ---------------------------

def test_midgame_cvc_undo_still_gated():
    """2026-05-30 spec unchanged: during live CvC play (no winner,
    no paused screen), U remains a no-op."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(2):
        assert g.current_ai_controller().take_turn(g)
    depth = len(g._history)
    g.handle_keydown(pygame.K_u)
    assert len(g._history) == depth
    assert g.cvc_autoplay_halted is False


def test_hvh_win_screen_undo_unaffected():
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
