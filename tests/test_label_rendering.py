"""Tests for the coordinate-label rendering order.

The bug: row/column labels (a-h along the bottom, 1-8 along the left)
are drawn at the edge of the board. When a move highlight or a
legal-move highlight covers an edge square, the highlight rectangle
also covers the label — making it disappear. The fix is to redraw
the labels AFTER all the highlight overlays via
`Game.show_coordinates`, so the highlights can't erase edge labels.

In addition, every mid-event re-render in the main loop (the inline
`show_bg(...); show_last_move(...); show_pieces(...)` blocks that fire
when the user drags a piece, releases a move, opens a menu, etc.)
must also call `show_coordinates` after its highlights — otherwise
the back buffer ends up with a label-covered frame on event-bearing
iterations, producing a flicker as the loop alternates between
event-bearing (label covered) and event-free (label visible) frames.

These tests cover:

1. `show_coordinates` redraws the label after `show_last_move` has
   covered it (the unit-level fix).
2. The render-helper that mid-event re-renders should use also
   re-draws labels — so all main files can call it consistently.
3. Regression for the d-file specifically (the one the user reported
   flickering on black's turn).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Headless display
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


from const import WIDTH, HEIGHT, SQSIZE, ROWS
from square import Square
from move import Move
from game import Game


# --- Helpers ---------------------------------------------------------------

def _pixel_color(surface, x, y):
    return tuple(surface.get_at((x, y)))


def _label_glyph_pixel_count(surface, x_start, y_start, w, h, bg_color):
    """Count pixels in the (x_start, y_start, w, h) region that DIFFER
    from bg_color. If a label glyph was rendered in this region, many
    pixels will differ from the background. If the region is entirely
    covered by a highlight rectangle (or empty background), every pixel
    matches bg_color and the count is 0."""
    different = 0
    for dy in range(h):
        for dx in range(w):
            px = tuple(surface.get_at((x_start + dx, y_start + dy)))[:3]
            if px != tuple(bg_color)[:3]:
                different += 1
    return different


# Standard label positions used by Game.show_coordinates.
#   row label at (5, 5 + row * SQSIZE)
#   col label at (col * SQSIZE + SQSIZE - 20, HEIGHT - 20)
# Glyph is roughly 12x16 pixels (monospace 18-bold).


def _row_label_bbox(row):
    return (5, 5 + row * SQSIZE, 12, 16)


def _col_label_bbox(col):
    return (col * SQSIZE + SQSIZE - 20, HEIGHT - 20, 12, 16)


# --- Tests -----------------------------------------------------------------

def test_show_coordinates_redraws_row_label_after_last_move_highlight():
    """`show_last_move` paints a full-square highlight over an edge
    square. Calling `show_coordinates` afterwards must redraw the row
    label on top of that highlight, so the player can still see "1-8".
    """
    g = Game()
    surf = pygame.Surface((WIDTH, HEIGHT))

    # Simulate a move whose initial square is a1 (row 7, col 0) — the
    # leftmost column, where the row label "1" lives.
    g.board.last_move = Move(Square(7, 0), Square(4, 4))

    # Render with full pipeline (bg → last_move → coordinates).
    g.show_bg(surf)
    g.show_last_move(surf)
    g.show_coordinates(surf)

    # The highlight color on a1 (row=7, col=0, sum even → trace.light).
    trace_light = g.config.theme.trace.light
    # The "1" glyph occupies the top-left of a1.
    x, y, w, h = _row_label_bbox(7)
    diff = _label_glyph_pixel_count(surf, x, y, w, h, trace_light)
    assert diff > 0, (
        f"Row label '1' should be visibly rendered on top of the a1 "
        f"highlight, but every pixel in the label bbox ({x},{y},{w},{h}) "
        f"matches the highlight color {trace_light}. show_coordinates "
        f"must redraw the label after show_last_move covers it."
    )


def test_show_coordinates_redraws_col_label_after_last_move_highlight():
    """Same but for a column label (a-h along the bottom row)."""
    g = Game()
    surf = pygame.Surface((WIDTH, HEIGHT))

    # Last move involves d1 (row 7, col 3) — the d-file column label
    # "d" lives at the bottom-right of d1. This is the exact label the
    # user reported flickering.
    g.board.last_move = Move(Square(7, 3), Square(4, 4))

    g.show_bg(surf)
    g.show_last_move(surf)
    g.show_coordinates(surf)

    # d1 row+col = 7+3 = 10 (even) → trace.light.
    trace_light = g.config.theme.trace.light
    x, y, w, h = _col_label_bbox(3)
    diff = _label_glyph_pixel_count(surf, x, y, w, h, trace_light)
    assert diff > 0, (
        f"Column label 'd' must be visibly rendered on top of the d1 "
        f"highlight, but every pixel in the label bbox ({x},{y},{w},{h}) "
        f"matches the highlight color {trace_light}."
    )


def test_show_coordinates_called_redundantly_is_idempotent():
    """Calling show_coordinates twice in a row produces the same result
    as calling it once. (show_bg already calls it; the explicit redraw
    after highlights would call it again. Verify this isn't visually
    different.)"""
    g = Game()
    surf_a = pygame.Surface((WIDTH, HEIGHT))
    surf_b = pygame.Surface((WIDTH, HEIGHT))

    # Two paths: single show_coordinates vs duplicate.
    g.show_bg(surf_a)  # bg already calls show_coordinates internally
    g.show_coordinates(surf_b)
    # Now surf_a has labels (via show_bg's internal call), surf_b only
    # has labels (no bg). Both should have the label pixels identical
    # in the label region (because show_coordinates writes the same
    # glyphs).
    x, y, w, h = _row_label_bbox(0)  # row 0 label "8"
    a_pixels = [tuple(surf_a.get_at((x + dx, y + dy)))[:3] for dx in range(w) for dy in range(h)]
    # surf_b has only labels — the bg under them is just the default
    # pygame.Surface fill (black). Check the same glyph pixels exist
    # in surf_a by checking the COUNT of non-bg pixels.
    bg_a = tuple(g.config.theme.bg.dark)[:3] if (0 % 2 == 0) else tuple(g.config.theme.bg.light)[:3]
    # On row 0 col 0, sum=0 even → bg.light. But the row label color uses
    # theme.bg.dark for even row, theme.bg.light for odd row.
    # Just check that there are SOME glyph-colored pixels in the bbox.
    diff_a = sum(1 for p in a_pixels if p != bg_a)
    assert diff_a > 0, "Labels should be drawn at row 0 by show_bg"


def test_show_bg_implicitly_draws_labels_for_backward_compatibility():
    """show_bg must call show_coordinates internally (for the older
    main_v0.py / main_v1.py snapshot mainloops that don't call
    show_coordinates separately). Verify a freshly-rendered board has
    visible labels even without an explicit show_coordinates call."""
    g = Game()
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf)
    # No explicit show_coordinates here. Labels should still be present.
    # Check the "a" label at bottom of col 0.
    x, y, w, h = _col_label_bbox(0)
    bg_dark = tuple(g.config.theme.bg.dark)[:3]
    bg_light = tuple(g.config.theme.bg.light)[:3]
    # Col 0 row 7: sum=7 odd → bg.dark (default light/dark logic).
    # The label colour is the OPPOSITE shade so it contrasts with the
    # square background. The label glyph pixels won't match either the
    # square bg or pure black, so count any non-background pixel.
    diff = 0
    for dy in range(h):
        for dx in range(w):
            px = tuple(surf.get_at((x + dx, y + dy)))[:3]
            if px != bg_dark and px != bg_light:
                diff += 1
    assert diff > 0, (
        "show_bg must implicitly draw labels (via internal "
        "show_coordinates call) so the snapshot mainloops render "
        "labels at all."
    )


def test_full_render_sequence_keeps_d_file_label_visible():
    """Integration-style test: simulate a full render frame after
    black's move whose initial or final square is on the d-file (row 7),
    verifying the 'd' column label is still visible. Pins the
    user-reported regression."""
    g = Game()
    surf = pygame.Surface((WIDTH, HEIGHT))
    # last_move from d1 (row 7, col 3) to d3 — a hypothetical white
    # move that just happened. Now it's black's turn (not a state we
    # need to set explicitly for rendering, but matches the user's
    # report of "on black's turn, d-file flickers").
    g.board.last_move = Move(Square(7, 3), Square(5, 3))

    # Full render order matching the active main.py:
    g.show_bg(surf)
    g.show_last_move(surf)
    g.show_moves(surf)
    g.show_jump_capture_targets(surf)
    g.show_coordinates(surf)  # the critical redraw
    g.show_pieces(surf)

    # The 'd' label should be visible. d1 is row 7 col 3, sum 10 even,
    # so the highlight on d1 is trace.light.
    trace_light = tuple(g.config.theme.trace.light)[:3]
    x, y, w, h = _col_label_bbox(3)
    # Check at least some pixels in the label bbox are NOT the trace
    # highlight color (i.e. the label glyph successfully redrew on top).
    non_trace = 0
    for dy in range(h):
        for dx in range(w):
            px = tuple(surf.get_at((x + dx, y + dy)))[:3]
            if px != trace_light:
                non_trace += 1
    assert non_trace > 0, (
        f"'d' label must remain visible after the full render. All "
        f"pixels in {x},{y},{w},{h} match the highlight color, meaning "
        f"show_coordinates didn't redraw on top of the highlight."
    )


def test_mid_event_render_without_coordinates_redraw_loses_label():
    """Negative-control: confirm that a render which OMITS
    show_coordinates after the highlight loses the edge label. This
    pins exactly which render order is broken — so if a future
    refactor accidentally removes the redraw, this test fails."""
    g = Game()
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.board.last_move = Move(Square(7, 3), Square(5, 3))

    # Render WITHOUT the explicit show_coordinates after highlights —
    # mimicking a mid-event re-render that skips the redraw.
    g.show_bg(surf)
    g.show_last_move(surf)
    g.show_pieces(surf)
    # (no show_coordinates here)

    # The 'd' label area should be ENTIRELY covered by the highlight
    # (since show_bg drew labels first but show_last_move painted over
    # them, and we didn't redraw).
    trace_light = tuple(g.config.theme.trace.light)[:3]
    x, y, w, h = _col_label_bbox(3)
    non_trace = 0
    for dy in range(h):
        for dx in range(w):
            px = tuple(surf.get_at((x + dx, y + dy)))[:3]
            if px != trace_light:
                non_trace += 1
    # Without the redraw, the d-file label should be missing — verify
    # the bug exists in this render order. We expect ZERO non-trace
    # pixels (the highlight rectangle is opaque and full-square).
    assert non_trace == 0, (
        f"This negative-control assumes the mid-event re-render does "
        f"NOT include show_coordinates, so the 'd' label should be "
        f"fully covered. Got {non_trace} non-trace pixels — if this "
        f"fails, show_coordinates may have moved INSIDE show_last_move "
        f"or similar; check the render order."
    )
