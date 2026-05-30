"""Tests for the 'R' reset-game confirmation overlay.

Pressing 'R' should NOT immediately wipe an in-progress game — it should
open a confirmation prompt so an accidental keystroke doesn't destroy state.

We test the Game-side state machine (the flag + how it interacts with
is_any_menu_open and reset()), not the pygame key dispatch in main.py,
because main.py is a long-running event loop and isn't unit-test-friendly.
The dispatch itself is a thin 5-line branch over the flag — covered by
manual smoke testing.
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

from game import Game


def test_reset_confirm_pending_defaults_false():
    """A fresh game has no pending reset prompt."""
    g = Game()
    assert g.reset_confirm_pending is False


def test_pending_flag_blocks_other_input_via_is_any_menu_open():
    """While the confirm prompt is up, is_any_menu_open() is True so the
    main loop gates other interactions (matching how the mode/promo menus
    behave). Without this, the user could still click pieces underneath
    the overlay."""
    g = Game()
    assert g.is_any_menu_open() is False
    g.reset_confirm_pending = True
    assert g.is_any_menu_open() is True
    g.reset_confirm_pending = False
    assert g.is_any_menu_open() is False


def test_reset_clears_pending_flag():
    """If the prompt is somehow up when reset() runs (defensive), it should
    be cleared post-reset — reset() calls __init__() which re-initializes
    every flag back to default."""
    g = Game()
    g.reset_confirm_pending = True
    g.reset()
    assert g.reset_confirm_pending is False


def test_show_reset_confirm_noop_when_not_pending():
    """No overlay when no prompt is up — surface must be untouched."""
    surface = pygame.Surface((400, 400))
    surface.fill((10, 20, 30))
    g = Game()
    g.show_reset_confirm(surface)
    # Pixel at center should be unchanged.
    assert surface.get_at((200, 200))[:3] == (10, 20, 30)


def test_show_reset_confirm_draws_overlay_when_pending():
    """Overlay must visibly change the surface when pending."""
    surface = pygame.Surface((400, 400))
    surface.fill((10, 20, 30))
    g = Game()
    g.reset_confirm_pending = True
    g.show_reset_confirm(surface)
    # After the dark backdrop + text blit, the center pixel differs from
    # the original bg color.
    assert surface.get_at((200, 200))[:3] != (10, 20, 30)
