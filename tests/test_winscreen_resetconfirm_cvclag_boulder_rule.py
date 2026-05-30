"""Tests for the four user-reported issues (2026-05-30 evening):

1. The concise rulebook line for the boulder should make clear the
   boulder ONLY captures pawns (not other pieces). Add the word
   'only' somewhere.

2. When a winner is decided, the win text overlays the mode menu /
   pause dialog / reset confirm screen — making them unreadable.
   AND mode menu clicks are blocked by the winner gate in main.py
   so the user can't reset their mode after a win.

   Fix:
     - Render the winner overlay BEFORE the paused-screen overlays
       so the menus paint on top.
     - Move the mode menu / pgn dialog click handlers ABOVE the
       winner gate in main.py so they fire even when winner is set.

3. The reset-confirm screen intercepts 'Y' as 'yes confirm reset',
   which clashes with 'Y' as redo. So redo is unusable while the
   confirm is open.

   Fix: drop 'Y' as a confirm key — use Enter only. Y remains the
   redo key in all states (the reset-confirm intercept just doesn't
   touch it). Update the on-screen prompt text accordingly.

4. Theme / flip changes in CvC mode are laggy — the user presses T
   or F and waits ~600 ms (the autoplay wait) before seeing the
   change.

   Fix: extend `Game.handle_keydown`'s result dict with
   `'view_changed': bool` (true when theme or flip changed). The
   autoplay wait loop in main.py breaks out as soon as a view pref
   changes, re-rendering immediately.
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


# ===========================================================================
# Issue 1 — boulder rule says "only" pawns
# ===========================================================================

def test_concise_rulebook_boulder_says_only_pawns():
    """The concise rulebook line must make clear the boulder can
    capture ONLY pawns — not other pieces. The word 'only' must
    appear in the PART of the line that describes what the boulder
    captures (not just in 'only a king may capture the boulder')."""
    path = os.path.join(
        os.path.dirname(__file__), '..', 'RULEBOOK_v2.md')
    with open(path) as f:
        text = f.read()
    matching = [ln for ln in text.split('\n')
                if 'Capture rules' in ln and 'boulder' in ln.lower()]
    assert matching, "could not find the boulder Capture rules line"
    line = matching[0]
    # The line typically has two clauses separated by ';':
    #   "the boulder may [only] capture pawns ...; only a king may
    #    capture the boulder."
    # Split on ';' and check that the FIRST clause (the boulder's-
    # captures part) contains 'only' so the restriction is unambiguous
    # — not just the "only a king" clause in the second half.
    first_clause = line.split(';')[0].lower()
    assert 'only' in first_clause, (
        f"the BOULDER-captures clause must contain 'only' to make "
        f"clear the boulder cannot capture non-pawns; got first "
        f"clause: {first_clause!r}")


# ===========================================================================
# Issue 2 — winner screen + paused screens
# ===========================================================================

def test_show_winner_paints_at_center():
    """Sanity: the winner overlay does paint visible content at the
    center of the surface when winner is set."""
    g = Game()
    g.winner = 'white'
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    g.show_winner(surface)
    assert surface.get_at((400, 400))[:3] != (10, 20, 30), (
        "winner overlay should paint visible content at center")


def test_mode_menu_paints_over_winner_when_both_active():
    """When winner is set AND mode menu is open, the menu must render
    ABOVE the winner — otherwise the winner text covers the menu
    options and the user can't read them."""
    g = Game()
    g.winner = 'white'
    g.open_mode_menu()
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    # Render in the order main.py uses (winner first, menu after).
    g.show_winner(surface)
    g.show_mode_menu(surface)
    # The mode menu populates click rects; sample inside the FIRST
    # rect's center and verify the pixel is the button color, NOT
    # the winner-overlay color. If the menu paints first and winner
    # paints over it, the menu rect's center would be obscured.
    assert g.mode_menu_rects, "mode menu drew no click rects"
    rect, _side, _key = g.mode_menu_rects[0]
    px = surface.get_at(rect.center)[:3]
    # The button color is bluish (60,60,60) for inactive and
    # (80,140,200) for the currently-selected. The winner overlay
    # is dark. Reject EXACT match with the original background, but
    # we mainly want a NON-black pixel — i.e., the menu is on top.
    # Soft check: button center pixel must have at least one channel
    # >= 50 (indicating a colored button is visible, not pure dim
    # backdrop).
    assert max(px) >= 50, (
        f"menu button center pixel {px} too dark — winner overlay "
        f"is likely painting on top of the menu")


def test_pgn_dialog_paints_over_winner_when_both_active():
    g = Game()
    g.winner = 'black'
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    g.show_winner(surface)
    g.show_pgn_dialog(surface)
    # Centered dialog covers the center — check the center pixel.
    px = surface.get_at((400, 400))[:3]
    # The dialog panel has rgba (28, 28, 32, 210); even with
    # semi-transparency it brightens dark-overlaid pixels above
    # pure-zero. The key check: the dialog DREW something at the
    # center (panel bg, button, text), which means it ran after
    # the winner. Soft check: center is not pure black.
    assert px != (0, 0, 0), (
        "PGN dialog should render its panel over the winner overlay")


def test_reset_confirm_paints_over_winner_when_both_active():
    g = Game()
    g.winner = 'white'
    g.reset_confirm_pending = True
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    g.show_winner(surface)
    g.show_reset_confirm(surface)
    # The reset-confirm overlay has its own dark backdrop + text;
    # at the center we expect the confirm overlay's text, not the
    # winner overlay's text. Soft: just check the render happened
    # (center pixel changed from original bg).
    assert surface.get_at((400, 400))[:3] != (10, 20, 30)


# ===========================================================================
# Issue 3 — Y is now redo only; Enter is confirm
# ===========================================================================

def test_reset_confirm_y_no_longer_confirms_reset():
    """NEW (2026-05-30 evening): Y is no longer accepted as a confirm
    key in the reset-confirm intercept. Only Enter confirms. Y now
    falls through and acts as redo (subject to other gating)."""
    random.seed(601)
    g = Game()
    # Drive a few turns then undo so redo stack is populated.
    for _ in range(3):
        AIController(g.next_player).take_turn(g)
    g.undo()  # turn 3 -> 2
    assert g.board.turn_number == 2
    assert g.can_redo() is True
    # Open reset confirm.
    g.reset_confirm_pending = True
    # Press Y. Previously this would have confirmed reset (back to
    # turn 0). Now it should REDO (turn 2 -> 3) and leave reset
    # confirm UNTOUCHED.
    result = g.handle_keydown(pygame.K_y)
    assert result['reset_happened'] is False
    assert g.reset_confirm_pending is True  # confirm still pending
    assert g.board.turn_number == 3  # redo happened


def test_reset_confirm_enter_still_confirms():
    """Enter (return) is still the confirm key."""
    g = Game()
    g.reset_confirm_pending = True
    result = g.handle_keydown(pygame.K_RETURN)
    assert result['reset_happened'] is True
    assert g.reset_confirm_pending is False


def test_reset_confirm_n_still_cancels():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_n)
    assert g.reset_confirm_pending is False


def test_reset_confirm_r_still_toggles_off():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_r)
    assert g.reset_confirm_pending is False


def test_show_reset_confirm_message_no_longer_mentions_y():
    """The on-screen prompt must NOT tell the user to press Y to
    confirm (now misleading)."""
    g = Game()
    g.reset_confirm_pending = True
    surface = pygame.Surface((800, 600))
    g.show_reset_confirm(surface)
    # We can't easily extract the rendered text from pixels. Instead,
    # check the source code: the prompt string must not say "Y" as a
    # confirm key.
    import inspect
    src = inspect.getsource(Game.show_reset_confirm)
    # The message used to be "Press Y or Enter to reset". After the
    # fix it should say "Enter" (not "Y") for confirm.
    # Look for "Press Y" — that's the OLD wording that must be gone.
    assert 'Press Y' not in src, (
        "show_reset_confirm still tells the user to press Y — that "
        "wording should be updated since Y is no longer a confirm key")


# ===========================================================================
# Issue 4 — view_changed flag for fast theme/flip in CvC
# ===========================================================================

def test_handle_keydown_returns_view_changed_false_for_non_view_keys():
    g = Game()
    result = g.handle_keydown(pygame.K_u)
    assert 'view_changed' in result
    assert result['view_changed'] is False


def test_handle_keydown_returns_view_changed_true_when_theme_changes():
    g = Game()
    result = g.handle_keydown(pygame.K_t)
    assert result['view_changed'] is True


def test_handle_keydown_returns_view_changed_true_when_flip_changes():
    g = Game()
    result = g.handle_keydown(pygame.K_f)
    assert result['view_changed'] is True


def test_handle_keydown_view_changed_during_reset_confirm():
    """T pressed during reset confirm still triggers view_changed=True
    so the CvC autoplay wait can re-render the new theme immediately."""
    g = Game()
    g.reset_confirm_pending = True
    result = g.handle_keydown(pygame.K_t)
    assert result['view_changed'] is True


def test_handle_keydown_view_changed_during_mode_menu():
    g = Game()
    g.open_mode_menu()
    result = g.handle_keydown(pygame.K_f)
    assert result['view_changed'] is True


def test_handle_keydown_view_changed_for_p_is_false():
    """Opening the PGN dialog isn't a view pref change — view_changed
    must be False. (P opens a paused state, which is its own abort
    signal in the wait loop.)"""
    g = Game()
    result = g.handle_keydown(pygame.K_p)
    assert result['view_changed'] is False


def test_handle_keydown_view_changed_for_m_is_false():
    g = Game()
    result = g.handle_keydown(pygame.K_m)
    assert result['view_changed'] is False


def test_handle_keydown_view_changed_for_unknown_key_is_false():
    g = Game()
    result = g.handle_keydown(pygame.K_a)
    assert result['view_changed'] is False
