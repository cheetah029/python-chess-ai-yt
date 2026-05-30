"""Tests for the redesigned pause/PGN dialog layout + FEN export.

Two user complaints addressed:

  1. The dialog covered almost the whole board (40-px margins + dark
     backdrop), so undo/redo changes weren't visible underneath.
     New design: a side panel anchored to the right, NO full-screen
     backdrop, so the left ~5 files of the board stay fully visible
     during pause.

  2. The serialized text was shown in full (a wall of base64). New
     design: shows only a few lines as a preview ("first 3 lines …
     <truncated, full text available via Copy>"). The Copy button
     still pushes the full text to the clipboard.

Plus a new capability: FEN export. The dialog now offers BOTH a
'Copy Save' button (full pickle for perfect replay) and a 'Copy FEN'
button (one-line position summary in a FEN-style format).

We test the panel-positioning invariants by pixel sampling: pixels
in the left half of the surface must be unchanged after rendering;
pixels in the panel area must differ.

We test FEN structurally: split-by-spaces, validate the placement
field has 8 ranks separated by '/', validate the turn field is
'w' or 'b', validate the boulder annotation is present.
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
# Section 1 — dialog panel layout (side panel, board visible to the left)
# ===========================================================================

def _filled(size, color=(10, 20, 30)):
    s = pygame.Surface(size)
    s.fill(color)
    return s


def test_dialog_does_not_paint_far_left_of_surface():
    """The dialog must NOT overwrite the LEFT portion of the surface
    so the user can see the board under it. Sample a column at x=20."""
    g = Game()
    g.open_pgn_dialog()
    surface = _filled((800, 800))
    g.show_pgn_dialog(surface)
    for y in (100, 400, 700):
        assert surface.get_at((20, y))[:3] == (10, 20, 30), (
            f"left edge pixel (20, {y}) was overwritten — the dialog "
            f"must stay in a side panel, not cover the whole board")


def test_dialog_does_not_paint_left_half_of_surface():
    """Roughly: the left half of an 800-wide surface should remain
    visible. The cut-off is the panel's left edge."""
    g = Game()
    g.open_pgn_dialog()
    surface = _filled((800, 800))
    g.show_pgn_dialog(surface)
    # Sample a column at x = surface_width // 4 = 200. Anything at
    # x < panel.left must be untouched.
    for y in range(50, 800, 100):
        assert surface.get_at((200, y))[:3] == (10, 20, 30), (
            f"pixel at (200, {y}) was modified — left quarter must "
            f"be entirely unchanged from background")


def test_dialog_does_paint_inside_panel():
    """Inside the panel area (right side), pixels must differ from the
    untouched background. Otherwise the dialog isn't rendering."""
    g = Game()
    g.open_pgn_dialog()
    surface = _filled((800, 800))
    g.show_pgn_dialog(surface)
    found = False
    # Scan a column near the right edge.
    for y in range(50, 800, 50):
        if surface.get_at((700, y))[:3] != (10, 20, 30):
            found = True
            break
    assert found, "dialog drew nothing in the right-side panel area"


def test_dialog_does_not_use_full_screen_dark_backdrop():
    """The previous design painted a near-opaque dark backdrop over
    the WHOLE surface. The redesign drops the backdrop entirely so
    the board stays bright. Sample center-of-board pixel: must match
    background."""
    g = Game()
    g.open_pgn_dialog()
    surface = _filled((800, 800), (180, 200, 220))  # light bg
    g.show_pgn_dialog(surface)
    # Center pixel of the surface (in the board area, not the panel).
    # 400 should fall just within the left half (panel left edge ≥ 480).
    assert surface.get_at((300, 400))[:3] == (180, 200, 220), (
        "center-board pixel was darkened — no full-screen backdrop "
        "should be drawn")


def test_dialog_button_rects_are_within_panel_bounds():
    """All button rects must sit inside the side panel area, so clicks
    on the left half (where the user might still want to interact)
    don't accidentally hit a button."""
    g = Game()
    g.open_pgn_dialog()
    surface = _filled((800, 800))
    g.show_pgn_dialog(surface)
    assert g.pgn_dialog_copy_rect is not None
    assert g.pgn_dialog_load_rect is not None
    # New button: Copy FEN.
    assert g.pgn_dialog_copy_fen_rect is not None
    for rect, name in (
            (g.pgn_dialog_copy_rect, 'copy'),
            (g.pgn_dialog_copy_fen_rect, 'copy_fen'),
            (g.pgn_dialog_load_rect, 'load')):
        assert rect.left >= 400, (
            f"{name} button rect at x={rect.left} is in the left half "
            f"(must be inside the right-side panel)")


def test_save_preview_truncates_long_text():
    """The serialized text can be many KB (the base64 payload grows
    with history). The dialog must display only a short preview — at
    most ~5 lines — and let the user use Copy to get the full text."""
    random.seed(2026)
    g = Game()
    # Play a bunch of turns to grow the payload.
    for _ in range(8):
        ctrl = AIController(g.next_player)
        ctrl.take_turn(g)
    g.open_pgn_dialog()
    # Re-derive the preview-line count by checking the helper directly.
    # Implementation: Game._pgn_dialog_preview_lines returns the
    # truncated, ready-to-render list of strings. (We expose it as a
    # helper rather than scraping the rendered pixels.)
    lines = g._pgn_dialog_preview_lines()
    assert isinstance(lines, list)
    assert len(lines) <= 6, (
        f"preview returned {len(lines)} lines; should be at most 6 "
        f"(a few preview lines + an ellipsis line)")
    # If the full save would be longer than the preview cap, the LAST
    # line should be an ellipsis-style truncation marker.
    full = g.serialize_to_text()
    if len(full.splitlines()) > 6:
        assert any('truncated' in ln or '...' in ln or '…' in ln
                   for ln in lines), (
            "expected an ellipsis/truncated marker in preview lines "
            f"but got {lines}")


# ===========================================================================
# Section 2 — FEN export
# ===========================================================================

def test_to_fen_returns_a_string():
    g = Game()
    fen = g.to_fen()
    assert isinstance(fen, str)
    assert len(fen) > 0


def test_initial_fen_has_8_ranks_separated_by_slash():
    """Standard FEN convention: placement is rank8/rank7/.../rank1."""
    g = Game()
    fen = g.to_fen()
    placement = fen.split()[0]
    ranks = placement.split('/')
    assert len(ranks) == 8, (
        f"placement field must have 8 ranks; got {len(ranks)}: {ranks}")


def test_initial_fen_has_turn_indicator():
    """Field after placement is 'w' (white to move) or 'b'."""
    g = Game()
    fen = g.to_fen()
    parts = fen.split()
    assert len(parts) >= 2
    assert parts[1] in ('w', 'b'), (
        f"expected 'w' or 'b' as turn field; got {parts[1]!r}")


def test_initial_fen_turn_is_white():
    g = Game()
    fen = g.to_fen()
    assert fen.split()[1] == 'w'


def test_initial_fen_contains_kings_at_right_squares():
    """Per RULEBOOK_v2.md back rank (Bishop-Queen-Rook-Knight-Knight-
    Rook-King-Bishop): white king at g1, black king at b8.

    FEN convention: rank 8 (black's back rank) is FIRST, rank 1 (white's
    back rank) is LAST. Within each rank, file a is leftmost.

    Black back rank (rotational symmetry): a8=Bishop, b8=King,
    c8=Rook, d8=Knight, e8=Knight, f8=Rook, g8=Queen, h8=Bishop.
    White back rank: a1=Bishop, b1=Queen, c1=Rook, d1=Knight,
    e1=Knight, f1=Rook, g1=King, h1=Bishop.

    Single-char piece codes: K/Q/R/B/N/P for white; lowercase for
    black; O for the boulder. So rank 8 starts 'b k r ...' and rank
    1 starts 'B Q R ...'.
    """
    g = Game()
    fen = g.to_fen()
    placement = fen.split()[0]
    ranks = placement.split('/')
    # Rank 8 (first): b at file a, k at file b. We don't constrain
    # internal piece-letters here — just the K position.
    assert ranks[0][0] == 'b', (
        f"rank 8 file a should be black bishop 'b'; got {ranks[0][0]!r}")
    assert ranks[0][1] == 'k', (
        f"rank 8 file b should be black king 'k'; got {ranks[0][1]!r}")
    # Rank 1 (last): B at a, Q at b, ..., K at g, B at h.
    assert ranks[7][0] == 'B', \
        f"rank 1 file a should be white bishop 'B'; got {ranks[7][0]!r}"
    assert ranks[7][6] == 'K', \
        f"rank 1 file g should be white king 'K'; got {ranks[7][6]!r}"


def test_initial_fen_contains_pawn_ranks():
    """Rank 7: all-black-pawns; rank 2: all-white-pawns. In FEN
    digit-encoded notation, eight pawns = 'pppppppp' / 'PPPPPPPP'
    (NOT digits, because the squares are occupied)."""
    g = Game()
    fen = g.to_fen()
    ranks = fen.split()[0].split('/')
    assert ranks[1] == 'pppppppp', (
        f"rank 7 should be all black pawns; got {ranks[1]!r}")
    assert ranks[6] == 'PPPPPPPP', (
        f"rank 2 should be all white pawns; got {ranks[6]!r}")


def test_initial_fen_empty_ranks_use_digit_8():
    """Ranks 3-6 are empty at game start; standard FEN compresses
    empty squares into digits — '8' for a fully-empty rank."""
    g = Game()
    fen = g.to_fen()
    ranks = fen.split()[0].split('/')
    # Ranks 6, 5, 4, 3 (indexes 2, 3, 4, 5 in the FEN order). The
    # boulder's intersection position is annotated separately, not
    # placed on any single square, so the central rank stays '8'.
    for idx in (2, 3, 4, 5):
        assert ranks[idx] == '8', (
            f"rank index {idx} should be '8' (empty); got {ranks[idx]!r}")


def test_initial_fen_includes_boulder_at_intersection():
    """Initial boulder is on the central intersection — annotated as
    'boulder:int:<cd>' (or similar 'int' marker) since it isn't on
    a single square."""
    g = Game()
    fen = g.to_fen()
    assert 'boulder:' in fen, (
        f"FEN must annotate the boulder; got {fen!r}")
    # Initial intersection position.
    assert 'int' in fen.lower(), (
        f"initial boulder is on the intersection — expected an 'int' "
        f"marker; got {fen!r}")


def test_fen_turn_field_flips_after_a_move():
    random.seed(11)
    g = Game()
    AIController('white').take_turn(g)
    fen = g.to_fen()
    assert fen.split()[1] == 'b', (
        "after white moves, turn field should read 'b'")


def test_fen_includes_turn_number():
    """Among the extras: 'turn:<n>' so loaders can recreate the
    fullmove counter equivalent."""
    g = Game()
    fen = g.to_fen()
    assert 'turn:' in fen, f"expected 'turn:' marker; got {fen!r}"


# ===========================================================================
# Section 3 — clipboard actions for FEN
# ===========================================================================

def test_copy_fen_to_clipboard_action_pushes_fen(monkeypatch):
    captured = {}
    def fake_copy(text):
        captured['text'] = text
        return True
    monkeypatch.setattr(Game, '_copy_to_clipboard', staticmethod(fake_copy))
    g = Game()
    ok = g.copy_fen_to_clipboard_action()
    assert ok is True
    assert captured['text'] == g.to_fen()


def test_copy_fen_action_failure_reports_status(monkeypatch):
    monkeypatch.setattr(
        Game, '_copy_to_clipboard', staticmethod(lambda text: False))
    g = Game()
    ok = g.copy_fen_to_clipboard_action()
    assert ok is False
    assert g.pgn_dialog_status is not None
    assert 'fail' in g.pgn_dialog_status.lower() or \
        'unavailable' in g.pgn_dialog_status.lower()


# ===========================================================================
# Section 4 — dialog still gates input the same way (regression guard)
# ===========================================================================

def test_dialog_still_gates_autoplay():
    """Layout change must not regress the autoplay gating."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.is_autoplay_paused() is False
    g.open_pgn_dialog()
    assert g.is_autoplay_paused() is True


def test_dialog_still_mutually_exclusive_with_mode_menu():
    g = Game()
    g.open_pgn_dialog()
    g.open_mode_menu()
    assert g.pgn_dialog_open is False
    assert g.mode_menu is not None


def test_close_dialog_clears_all_three_button_rects():
    """All three rects (Copy / Copy FEN / Load) must be cleared on
    close, not just the original two."""
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    g.show_pgn_dialog(surface)
    g.close_pgn_dialog()
    assert g.pgn_dialog_copy_rect is None
    assert g.pgn_dialog_load_rect is None
    assert g.pgn_dialog_copy_fen_rect is None
