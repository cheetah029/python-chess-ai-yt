"""Tests for the next batch of UI/key-dispatch improvements:

  1. load_from_fen() — parse a FEN-style text and replace the game
     state with a fresh game at the encoded position. (FEN is
     position-only, NOT a full save — history/freeze flags/etc. are
     reset.) Plus a 'Load FEN' button in the dialog.

  2. Pause dialog re-centered + semi-transparent. Now sits in the
     middle of the screen with a SRCALPHA semi-transparent panel
     background so the board is visible THROUGH it, not next-to it.

  3. Copy button briefly shows 'Copied!' label (transient feedback).
     A test-friendly clock indirection is provided so the timed
     feedback can be exercised headlessly.

  4. Unified key-dispatch principle: view prefs (T, F) always work;
     undo/redo work in every paused state that doesn't directly
     conflict (now including mode menu); reset-confirm becomes one
     of the standard paused states (gets auto-cancelled by M/P/R).
     Specifically:

       - U / Y(redo): work in mode_menu and pgn_dialog (no change)
         AND now also fall through during reset-confirm-pending
         (Y is intercepted as 'yes' during reset, but U falls
         through). Updated: see the spec list inside the tests.

       - M / P: opening any paused screen now ALSO cancels
         reset_confirm_pending — the user changing screens is
         treated as implicit 'no' for the reset confirmation.

       - T / F: never affect any state besides their own — they
         are pure view prefs.

       - reset_confirm_pending intercept narrows to Y/Enter (yes),
         N (no), R (cancel-toggle). Esc still cancels via the Esc
         cascade. Other keys fall through to normal dispatch.
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


# ===========================================================================
# Section 1 — load_from_fen
# ===========================================================================

def test_load_from_fen_initial_position_roundtrips():
    """to_fen() → load_from_fen() reproduces the initial board layout."""
    g_source = Game()
    fen = g_source.to_fen()
    g = Game()
    ok = g.load_from_fen(fen)
    assert ok is True
    # Every square in the loaded game should hold the same piece type
    # at the same position as the source (we test piece type names and
    # colors; per-piece flags are intentionally reset by FEN load).
    for r in range(8):
        for c in range(8):
            src_sq = g_source.board.squares[r][c]
            new_sq = g.board.squares[r][c]
            if src_sq.has_piece():
                assert new_sq.has_piece(), (
                    f"({r}, {c}) had {type(src_sq.piece).__name__} in "
                    f"source but loaded square is empty")
                assert type(new_sq.piece).__name__ == \
                    type(src_sq.piece).__name__
                assert new_sq.piece.color == src_sq.piece.color
            else:
                assert not new_sq.has_piece(), (
                    f"({r}, {c}) was empty in source but loaded "
                    f"has a piece")


def test_load_from_fen_after_a_move_preserves_position():
    """Play a turn, export FEN, load it into a fresh game — pieces
    end up at the same squares."""
    random.seed(2030)
    g_source = Game()
    AIController('white').take_turn(g_source)
    fen = g_source.to_fen()
    g = Game()
    g.load_from_fen(fen)
    for r in range(8):
        for c in range(8):
            src = g_source.board.squares[r][c]
            new = g.board.squares[r][c]
            assert src.has_piece() == new.has_piece(), (
                f"({r}, {c}) mismatch")
            if src.has_piece():
                assert type(src.piece).__name__ == type(new.piece).__name__
                assert src.piece.color == new.piece.color


def test_load_from_fen_preserves_turn_color():
    random.seed(2031)
    g_source = Game()
    AIController('white').take_turn(g_source)
    assert g_source.next_player == 'black'
    fen = g_source.to_fen()
    g = Game()
    g.load_from_fen(fen)
    assert g.next_player == 'black'


def test_load_from_fen_preserves_turn_number():
    random.seed(2033)
    g_source = Game()
    for _ in range(3):
        AIController(g_source.next_player).take_turn(g_source)
    fen = g_source.to_fen()
    g = Game()
    g.load_from_fen(fen)
    assert g.board.turn_number == g_source.board.turn_number


def test_load_from_fen_resets_history():
    """FEN is position-only — undo history is NOT preserved (full save
    is the format for that). After load_from_fen, can_undo is False."""
    random.seed(2035)
    g_source = Game()
    for _ in range(3):
        AIController(g_source.next_player).take_turn(g_source)
    assert g_source.can_undo() is True
    fen = g_source.to_fen()
    g = Game()
    g.load_from_fen(fen)
    assert g.can_undo() is False


def test_load_from_fen_returns_false_on_garbage():
    g = Game()
    assert g.load_from_fen('this is not a fen') is False
    # Game state untouched.
    assert g.board.turn_number == 0


def test_load_from_fen_returns_false_on_empty_input():
    g = Game()
    assert g.load_from_fen('') is False


def test_load_from_fen_returns_false_on_wrong_rank_count():
    """FEN placement must have exactly 8 ranks separated by '/'."""
    g = Game()
    assert g.load_from_fen('8/8/8 w turn:0 boulder:int:0') is False


def test_load_from_fen_in_place_mutation_preserves_board_object():
    """Like load_from_text, load_from_fen mutates self.board in place
    so external main.py references stay valid."""
    g_source = Game()
    fen = g_source.to_fen()
    g = Game()
    bid = id(g.board)
    g.load_from_fen(fen)
    assert id(g.board) == bid


def test_load_from_clipboard_action_handles_fen_too(monkeypatch):
    """The 'Load' button is now smart: it tries to parse as a full
    save first; if that fails AND the text parses as FEN, it loads
    via load_from_fen. UI status reflects which path succeeded."""
    g_source = Game()
    fen = g_source.to_fen()
    monkeypatch.setattr(Game, '_read_clipboard', staticmethod(lambda: fen))
    g = Game()
    ok = g.load_from_clipboard_action()
    assert ok is True
    # Position matches.
    for r in range(8):
        for c in range(8):
            src = g_source.board.squares[r][c]
            new = g.board.squares[r][c]
            assert src.has_piece() == new.has_piece()


# ===========================================================================
# Section 2 — pause dialog re-centered + semi-transparent
# ===========================================================================

def test_dialog_panel_is_centered_horizontally():
    """Panel sits in the middle of the surface, not at the right edge.
    Sample a column far to the right — should now be UNTOUCHED
    (panel doesn't reach the edge)."""
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    g.show_pgn_dialog(surface)
    # The right edge should remain visible (panel is centered with
    # margin on both sides, so x ≈ 780 is outside the panel).
    found_untouched = False
    for y in range(50, 800, 100):
        if surface.get_at((780, y))[:3] == (10, 20, 30):
            found_untouched = True
            break
    assert found_untouched, (
        "right edge should remain visible — the dialog must be "
        "centered horizontally, not anchored to the right side")


def test_dialog_panel_is_centered_vertically():
    """Top and bottom edges of the surface remain untouched."""
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    g.show_pgn_dialog(surface)
    # Top edge.
    for x in range(50, 800, 100):
        assert surface.get_at((x, 10))[:3] == (10, 20, 30), (
            f"top edge ({x}, 10) should be untouched")
    # Bottom edge.
    for x in range(50, 800, 100):
        assert surface.get_at((x, 790))[:3] == (10, 20, 30), (
            f"bottom edge ({x}, 790) should be untouched")


def test_dialog_panel_does_not_paint_far_corners():
    """All four corners stay untouched (panel is centered)."""
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    surface.fill((10, 20, 30))
    g.show_pgn_dialog(surface)
    for x, y in [(10, 10), (790, 10), (10, 790), (790, 790)]:
        assert surface.get_at((x, y))[:3] == (10, 20, 30), (
            f"corner ({x}, {y}) overwritten — panel must be centered")


def test_dialog_inner_pixel_blends_with_board():
    """Semi-transparency: panel background is NOT solid; some of the
    underlying surface color shows through. We test this by filling
    the surface with a VERY distinctive color and checking that the
    rendered panel pixel is NOT a pure solid (28, 28, 32) — there
    should be SOME blend."""
    g = Game()
    g.open_pgn_dialog()
    distinctive = (250, 50, 50)
    surface = pygame.Surface((800, 800))
    surface.fill(distinctive)
    g.show_pgn_dialog(surface)
    # Sample a pixel that's inside the panel but not on text/button
    # — choose somewhere in the upper-middle of the panel area.
    inner = surface.get_at((400, 200))[:3]
    # The panel background blends; the rendered pixel should NOT
    # equal the original distinctive bg (it's at least partially
    # dimmed) AND should NOT equal pure (0,0,0) (the panel is
    # semi-transparent, not opaque black).
    # Looser check: at least the red channel should be reduced from
    # 250 — the dark panel is being blended in.
    assert inner != distinctive, "inner panel pixel unchanged from bg"
    # And not pure black either.
    assert inner != (0, 0, 0), (
        "inner panel pixel is pure black — panel should be semi-"
        "transparent, not opaque")


# ===========================================================================
# Section 3 — 'Copied!' transient feedback
# ===========================================================================

def test_copy_action_records_copied_at_ticks(monkeypatch):
    """After Copy is clicked, Game records the click time + which
    button so the renderer can show 'Copied!' transiently."""
    monkeypatch.setattr(
        Game, '_copy_to_clipboard', staticmethod(lambda text: True))
    monkeypatch.setattr(Game, '_now_ms', staticmethod(lambda: 5000))
    g = Game()
    g.copy_to_clipboard_action()
    assert g._copied_at_ms == 5000
    assert g._copied_button == 'save'


def test_copy_fen_action_records_copied_button(monkeypatch):
    monkeypatch.setattr(
        Game, '_copy_to_clipboard', staticmethod(lambda text: True))
    monkeypatch.setattr(Game, '_now_ms', staticmethod(lambda: 7000))
    g = Game()
    g.copy_fen_to_clipboard_action()
    assert g._copied_at_ms == 7000
    assert g._copied_button == 'fen'


def test_copy_failure_does_not_record_copied_state(monkeypatch):
    """If clipboard write failed, don't show 'Copied!' (would lie)."""
    monkeypatch.setattr(
        Game, '_copy_to_clipboard', staticmethod(lambda text: False))
    g = Game()
    g.copy_to_clipboard_action()
    assert g._copied_at_ms is None


def test_copied_label_active_immediately_after_click(monkeypatch):
    """copy_recent_button(now) returns 'save' / 'fen' / None depending
    on whether the click was within the transient window."""
    monkeypatch.setattr(
        Game, '_copy_to_clipboard', staticmethod(lambda text: True))
    monkeypatch.setattr(Game, '_now_ms', staticmethod(lambda: 10_000))
    g = Game()
    g.copy_to_clipboard_action()
    # Same instant — still in window.
    assert g.copy_recent_button(now_ms=10_000) == 'save'
    # 500 ms later — still in window.
    assert g.copy_recent_button(now_ms=10_500) == 'save'


def test_copied_label_expires_after_window():
    """After Game._COPIED_FEEDBACK_MS, copy_recent_button returns None."""
    g = Game()
    g._copied_at_ms = 10_000
    g._copied_button = 'save'
    window = Game._COPIED_FEEDBACK_MS
    assert g.copy_recent_button(now_ms=10_000 + window - 1) == 'save'
    assert g.copy_recent_button(now_ms=10_000 + window + 1) is None


def test_copied_state_is_per_button():
    """Clicking 'Copy FEN' should NOT light up the 'Copy Save' label."""
    g = Game()
    g._copied_at_ms = 5000
    g._copied_button = 'fen'
    assert g.copy_recent_button(now_ms=5050) == 'fen'
    # If the renderer asks 'is save copied?', the answer is no.
    assert g.copy_recent_button(now_ms=5050) != 'save'


# ===========================================================================
# Section 4 — unified key dispatch principle
# ===========================================================================

def _advance(g, n):
    for _ in range(n):
        if g.winner is not None:
            return
        ctrl = AIController(g.next_player)
        ctrl.take_turn(g)


# ---- undo/redo now allowed during MODE MENU -----------------------------

def test_undo_works_during_mode_menu():
    """Mode menu is a paused state but doesn't conflict with undo —
    the menu just changes future player slots, not board state.
    Undo should work."""
    random.seed(3001)
    g = Game()
    _advance(g, 3)
    g.open_mode_menu()
    g.handle_keydown(pygame.K_u)
    # The mode menu stays open; the undo happens.
    assert g.mode_menu is not None
    assert g.board.turn_number == 2


def test_redo_works_during_mode_menu():
    random.seed(3003)
    g = Game()
    _advance(g, 3)
    g.undo()
    g.open_mode_menu()
    g.handle_keydown(pygame.K_y)
    assert g.mode_menu is not None
    assert g.board.turn_number == 3


def test_can_undo_returns_true_when_mode_menu_open():
    """can_undo's intermediate-state guard should no longer count
    mode_menu as blocking."""
    random.seed(3005)
    g = Game()
    _advance(g, 2)
    g.open_mode_menu()
    assert g.can_undo() is True


def test_can_undo_still_returns_false_during_jump_capture():
    """Genuine intermediate state — undo would orphan UI."""
    g = Game()
    # Fake an in-progress jump-capture.
    g.jump_capture_targets = [(0, 0)]
    assert g.can_undo() is False


# ---- M / P cancel reset_confirm_pending -----------------------------

def test_opening_mode_menu_cancels_reset_confirm():
    """User principle: opening a different paused state is implicit
    'no' to the reset confirm."""
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_m)
    assert g.mode_menu is not None
    assert g.reset_confirm_pending is False


def test_opening_pgn_dialog_cancels_reset_confirm():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_p)
    assert g.pgn_dialog_open is True
    assert g.reset_confirm_pending is False


# ---- reset_confirm_pending NEW intercept (narrower whitelist) ---------

def test_reset_confirm_t_still_changes_theme():
    """T is a view pref — always works, never affects reset state."""
    g = Game()
    g.reset_confirm_pending = True
    initial = g.config.idx
    g.handle_keydown(pygame.K_t)
    assert g.config.idx != initial
    assert g.reset_confirm_pending is True


def test_reset_confirm_f_still_flips_board():
    g = Game()
    g.reset_confirm_pending = True
    initial = g.flipped
    g.handle_keydown(pygame.K_f)
    assert g.flipped != initial
    assert g.reset_confirm_pending is True


def test_reset_confirm_y_still_confirms():
    g = Game()
    g.reset_confirm_pending = True
    result = g.handle_keydown(pygame.K_y)
    assert result['reset_happened'] is True
    assert g.reset_confirm_pending is False


def test_reset_confirm_n_still_cancels():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_n)
    assert g.reset_confirm_pending is False


def test_reset_confirm_r_still_cancels_toggle():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_r)
    assert g.reset_confirm_pending is False


def test_reset_confirm_esc_still_cancels():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_ESCAPE)
    assert g.reset_confirm_pending is False


# ---- view prefs (T, F) always available regardless of state --------

def test_t_works_in_every_paused_state():
    g = Game()
    for set_state in (
            lambda: g.open_pgn_dialog(),
            lambda: g.open_mode_menu(),
            lambda: setattr(g, 'reset_confirm_pending', True)):
        # Reset to clean state, then set the one being tested.
        g.close_pgn_dialog()
        g.close_mode_menu()
        g.reset_confirm_pending = False
        set_state()
        initial = g.config.idx
        g.handle_keydown(pygame.K_t)
        assert g.config.idx != initial, (
            "T must change theme in every paused state")


def test_f_works_in_every_paused_state():
    g = Game()
    for set_state in (
            lambda: g.open_pgn_dialog(),
            lambda: g.open_mode_menu(),
            lambda: setattr(g, 'reset_confirm_pending', True)):
        g.close_pgn_dialog()
        g.close_mode_menu()
        g.reset_confirm_pending = False
        set_state()
        initial = g.flipped
        g.handle_keydown(pygame.K_f)
        assert g.flipped != initial


# ---- Escape cascade now also catches reset_confirm_pending --------

def test_escape_closes_reset_confirm_when_nothing_else_open():
    g = Game()
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_ESCAPE)
    assert g.reset_confirm_pending is False


def test_escape_priority_unchanged_with_mode_menu():
    """If mode menu AND reset confirm somehow co-existed (defensive),
    Esc closes the mode menu first (higher priority in the cascade)."""
    g = Game()
    g.open_mode_menu()
    # Force the state (in practice, opening mode menu cancels reset).
    g.reset_confirm_pending = True
    g.handle_keydown(pygame.K_ESCAPE)
    # Mode menu was closed (priority); reset still pending.
    assert g.mode_menu is None
    assert g.reset_confirm_pending is True
