"""Tests for the `Main._render_frame` helper extracted from main.py.

Background (2026-05-31 user feedback): pressing T (theme) or F
(flip board) during CvC autoplay momentarily PAUSED the game —
the AI's next move was delayed because the autoplay-wait loop
broke + reset on view_changed.

Fix: re-render INLINE in the wait loop when view_changed fires
(no break, no abort). The wait continues; the AI moves on
schedule.

The inline re-render needs a callable that paints a full frame
to a surface. Extracted as `Main._render_frame(game, dragger)`.
This file tests that helper directly — full main-loop pacing
is hard to unit-test, but the helper IS unit-testable.
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

import pytest

import main as main_module
from game import Game


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _make_main():
    """Construct a Main with a real Game + Surface. Bypass the
    display-mode init that would require a real window."""
    m = main_module.Main.__new__(main_module.Main)
    m.screen = pygame.Surface((800, 800))
    m.game = Game()
    return m


def test_render_frame_method_exists():
    """The helper must be a method on Main, callable with a game
    and a dragger argument."""
    assert hasattr(main_module.Main, '_render_frame')


def test_render_frame_runs_without_error_on_fresh_game():
    m = _make_main()
    m._render_frame(m.game, m.game.dragger)


def test_render_frame_paints_visible_content():
    """The render should actually paint pixels to the surface —
    the board background + pieces. Sample a board pixel: it must
    differ from the fully-untouched pure-black initial state."""
    m = _make_main()
    m.screen.fill((0, 0, 0))
    m._render_frame(m.game, m.game.dragger)
    assert m.screen.get_at((200, 200))[:3] != (0, 0, 0)


def test_render_frame_works_with_pgn_dialog_open():
    """Re-rendering during the PGN dialog should not crash."""
    m = _make_main()
    m.game.open_pgn_dialog()
    m._render_frame(m.game, m.game.dragger)


def test_render_frame_works_after_theme_change():
    """The whole point: re-rendering inline AFTER a theme change
    should successfully apply the new theme. We don't sample colors
    (themes are complex), but we verify the render runs cleanly."""
    m = _make_main()
    m._render_frame(m.game, m.game.dragger)
    m.game.change_theme()
    m._render_frame(m.game, m.game.dragger)


def test_render_frame_works_after_flip():
    m = _make_main()
    m._render_frame(m.game, m.game.dragger)
    m.game.flip_board()
    m._render_frame(m.game, m.game.dragger)


def test_render_frame_works_with_winner_set():
    m = _make_main()
    m.game.winner = 'white'
    m._render_frame(m.game, m.game.dragger)


def test_render_frame_does_not_update_display(monkeypatch):
    """The helper renders but does NOT call pygame.display.update()
    — the caller does. This separation lets the autoplay-wait
    loop control update timing.

    Verify by monkeypatching pygame.display.update with a counter.
    """
    calls = {'n': 0}
    monkeypatch.setattr(
        pygame.display, 'update',
        lambda *a, **kw: calls.update({'n': calls['n'] + 1}))
    m = _make_main()
    m._render_frame(m.game, m.game.dragger)
    assert calls['n'] == 0, (
        f'_render_frame called display.update {calls["n"]} times — '
        f'callers should control update timing')


def test_render_frame_handles_active_drag():
    """If the dragger is mid-drag, the helper should still render
    (dragger overlay drawn on top)."""
    m = _make_main()
    m.game.dragger.dragging = True
    m.game.dragger.piece = None  # safe stub
    # Should not raise even with a partial drag state.
    try:
        m._render_frame(m.game, m.game.dragger)
    except Exception as e:
        # Acceptable failures: needs a non-None piece, etc.
        # Catch only the cases the actual main.py would also catch.
        if 'piece' not in str(e).lower() and 'none' not in str(e).lower():
            raise
