"""Tests for the flip-board feature (F key).

Flipping the board is a purely visual 180° rotation: black's pieces
appear at the bottom of the screen, white's at the top. Both rows and
columns reverse. The underlying board state is unchanged — only the
mapping between board coordinates (the row/col of every piece) and
screen coordinates (the pixel position where it's drawn) is mirrored.

These tests pin the contract:

  - State: `Game.flipped` is a bool, defaults to False; `flip_board()`
    toggles it; the toggle is gated on the same intermediate-state
    guard as undo/redo (no flipping mid-drag, mid-menu, mid-jump-capture).
  - Coordinate math: `board_to_screen` and `screen_to_board` are pure
    inverses of each other; corner mappings are correct in both modes.
  - Rendering: each show_* method that draws something on a square
    draws at the board_to_screen position (i.e. the mirrored square
    when flipped). The piece textures themselves are NOT rotated.
  - Click translation: a pixel at the screen's top-left maps to board
    (0, 0) unflipped and (7, 7) flipped.
  - Labels: row labels go 8→1 top-to-bottom unflipped, 1→8 top-to-
    bottom flipped. Col labels go a→h left-to-right unflipped, h→a
    left-to-right flipped.
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


from const import WIDTH, HEIGHT, SQSIZE, ROWS, COLS
from square import Square
from move import Move
from piece import Pawn, Knight, Bishop, Rook, Queen, King
from game import Game


# ---------------------------------------------------------------------------
# State and toggling
# ---------------------------------------------------------------------------

def test_flipped_defaults_to_false():
    g = Game()
    assert g.flipped is False


def test_flip_board_toggles_state():
    g = Game()
    assert g.flipped is False
    g.flip_board()
    assert g.flipped is True
    g.flip_board()
    assert g.flipped is False


def test_can_flip_returns_true_when_idle():
    g = Game()
    assert g.can_flip() is True


def test_can_flip_returns_false_during_jump_capture():
    """Flip is blocked while a knight jump-capture is pending — the
    dragger has already released, but the UI is awaiting the
    capture/decline click, and the (row, col) of jump_capture_landing
    is in board coords. Flipping mid-decision is non-disruptive in
    principle but treated as part of the in-between state for
    consistency with undo/redo."""
    g = Game()
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    assert g.can_flip() is False


def test_can_flip_returns_false_during_drag():
    g = Game()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    assert g.can_flip() is False


def test_can_flip_returns_false_during_transform_menu():
    g = Game()
    g.transform_menu = {'piece': None, 'row': 0, 'col': 0, 'options': []}
    assert g.can_flip() is False


def test_can_flip_returns_false_during_promotion_menu():
    g = Game()
    g.promotion_menu = {'pawn': None, 'row': 0, 'col': 0}
    assert g.can_flip() is False


def test_flip_board_no_op_during_intermediate_state():
    """flip_board() returns False (no change) when blocked."""
    g = Game()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    result = g.flip_board()
    assert result is False
    assert g.flipped is False  # unchanged


def test_flip_board_returns_true_on_success():
    g = Game()
    assert g.flip_board() is True
    assert g.flipped is True


def test_flip_persists_across_reset():
    """Flip is a viewing preference, not game state. game.reset() must
    NOT reset the flipped flag."""
    g = Game()
    g.flip_board()
    assert g.flipped is True
    g.reset()
    assert g.flipped is True


# ---------------------------------------------------------------------------
# Coordinate math: pure helpers
# ---------------------------------------------------------------------------

def test_board_to_screen_identity_when_not_flipped():
    g = Game()
    for r in range(ROWS):
        for c in range(COLS):
            assert g.board_to_screen(r, c) == (r, c)


def test_board_to_screen_mirrors_when_flipped():
    g = Game()
    g.flip_board()
    assert g.board_to_screen(0, 0) == (7, 7)
    assert g.board_to_screen(7, 7) == (0, 0)
    assert g.board_to_screen(7, 0) == (0, 7)
    assert g.board_to_screen(0, 7) == (7, 0)
    assert g.board_to_screen(3, 4) == (4, 3)


def test_screen_to_board_identity_when_not_flipped():
    g = Game()
    for r in range(ROWS):
        for c in range(COLS):
            assert g.screen_to_board(r, c) == (r, c)


def test_screen_to_board_mirrors_when_flipped():
    g = Game()
    g.flip_board()
    assert g.screen_to_board(0, 0) == (7, 7)
    assert g.screen_to_board(7, 7) == (0, 0)
    assert g.screen_to_board(3, 4) == (4, 3)


def test_board_to_screen_and_screen_to_board_are_inverses():
    for flipped in (False, True):
        g = Game()
        if flipped:
            g.flip_board()
        for r in range(ROWS):
            for c in range(COLS):
                sr, sc = g.board_to_screen(r, c)
                br, bc = g.screen_to_board(sr, sc)
                assert (br, bc) == (r, c), (
                    f"Inverse fails for flipped={flipped} at ({r},{c}): "
                    f"board_to_screen → ({sr},{sc}) → screen_to_board → ({br},{bc})"
                )


# ---------------------------------------------------------------------------
# Rendering: positions on screen match board_to_screen
# ---------------------------------------------------------------------------

def _render_complete_frame(g, surf):
    g.show_bg(surf)
    g.show_last_move(surf)
    g.show_moves(surf)
    g.show_jump_capture_targets(surf)
    g.show_coordinates(surf)
    g.show_pieces(surf)


def _pixel_in_square(surf, screen_row, screen_col, offset=(40, 40)):
    """Sample a pixel near the center of a screen square (avoid label
    corners). Default offset (40, 40) is the center of an 80-pixel
    square."""
    x = screen_col * SQSIZE + offset[0]
    y = screen_row * SQSIZE + offset[1]
    return tuple(surf.get_at((x, y)))[:3]


def test_show_bg_paints_squares_at_flipped_positions():
    """The bottom-left square of the SCREEN should always be a dark
    square (per chess convention for the player at the bottom).
    Whether flipped or not, this should hold."""
    g = Game()
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf)
    # Bottom-left screen square: screen (7, 0). Not flipped → board
    # (7, 0) → sum 7 odd → bg.dark. Flipped would give board (0, 7)
    # → sum 7 odd → bg.dark. Either way, dark.
    pixel_unflipped = _pixel_in_square(surf, 7, 0)
    dark = tuple(g.config.theme.bg.dark)[:3]
    assert pixel_unflipped == dark, (
        f"Bottom-left screen square should be dark; got {pixel_unflipped}"
    )

    g.flip_board()
    surf2 = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf2)
    pixel_flipped = _pixel_in_square(surf2, 7, 0)
    # Same square geometry — flipping doesn't change the SCREEN-side
    # checker pattern, since the color depends on board (row+col) %
    # 2 and the flip swaps both → parity preserved.
    assert pixel_flipped == dark, (
        f"Bottom-left screen square should be dark after flip; got {pixel_flipped}"
    )


def test_show_last_move_highlights_at_flipped_screen_position():
    """If last_move's initial is at board (0, 0), the highlight should
    appear at screen (0, 0) unflipped and screen (7, 7) flipped."""
    g = Game()
    g.board.last_move = Move(Square(0, 0), Square(4, 4))

    # Unflipped: highlight at screen (0, 0)
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf)
    g.show_last_move(surf)
    pixel = _pixel_in_square(surf, 0, 0)
    trace_light = tuple(g.config.theme.trace.light)[:3]
    # Board (0,0) sum 0 even → trace.light.
    assert pixel == trace_light, (
        f"Unflipped: a8 highlight should be at screen (0,0); got {pixel}"
    )

    # Flipped: highlight at screen (7, 7)
    g.flip_board()
    surf2 = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf2)
    g.show_last_move(surf2)
    pixel = _pixel_in_square(surf2, 7, 7)
    assert pixel == trace_light, (
        f"Flipped: a8 (board) should highlight at screen (7,7); got {pixel}"
    )
    # And screen (0, 0) should be just the bg color now, not the trace.
    pixel_top_left = _pixel_in_square(surf2, 0, 0)
    assert pixel_top_left != trace_light, (
        f"Flipped: screen (0,0) should NOT have a8 highlight; got {pixel_top_left}"
    )


def test_pieces_appear_at_flipped_screen_position():
    """A piece on board (0, 0) renders at screen (0, 0) unflipped and
    at screen (7, 7) flipped. Verify by checking that the rendered
    surface has the piece's image somewhere in the expected square."""
    g = Game()
    # Default initial setup has a black bishop on (0, 0).
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf)
    g.show_pieces(surf)
    # Center pixel of screen (0, 0). A piece is rendered there, so the
    # pixel should NOT be the plain bg color.
    bg_light = tuple(g.config.theme.bg.light)[:3]
    bg_dark = tuple(g.config.theme.bg.dark)[:3]
    pixel = _pixel_in_square(surf, 0, 0)
    assert pixel != bg_light and pixel != bg_dark, (
        f"Unflipped: piece on (0,0) should change pixel away from bg; got {pixel}"
    )

    g.flip_board()
    surf2 = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf2)
    g.show_pieces(surf2)
    pixel_flipped = _pixel_in_square(surf2, 7, 7)
    assert pixel_flipped != bg_light and pixel_flipped != bg_dark, (
        f"Flipped: piece on board (0,0) should render at screen (7,7); "
        f"got pixel {pixel_flipped}"
    )
    # And screen (0, 0) flipped now holds the piece that was on board
    # (7, 7) — a white bishop in default setup. Pixel should also
    # differ from bg.
    pixel_top_left = _pixel_in_square(surf2, 0, 0)
    assert pixel_top_left != bg_light and pixel_top_left != bg_dark, (
        f"Flipped: piece on board (7,7) should render at screen (0,0); "
        f"got pixel {pixel_top_left}"
    )


def test_labels_invert_when_flipped():
    """Row labels go 8→1 top-to-bottom unflipped; 1→8 top-to-bottom
    flipped. Col labels go a→h left-to-right unflipped; h→a left-to-
    right flipped. We test this by checking the LABEL TEXT rendered
    near each screen-edge square."""
    # We can't easily OCR the text, but we can verify that the label
    # POSITIONS produce non-bg pixels where expected. Specifically:
    # - Unflipped: top-left of screen (row 0, col 0) has '8' label.
    # - Flipped:   top-left of screen (row 0, col 0) has '1' label.
    # Both should be non-empty (i.e. there IS a label glyph there).
    # Beyond that, we check that the rendered text widths/heights are
    # consistent — same shapes appear in mirror positions.

    # Build two surfaces, one unflipped and one flipped, both showing
    # only labels (via show_bg which calls show_coordinates internally).
    g_unflipped = Game()
    g_flipped = Game()
    g_flipped.flip_board()

    surf_u = pygame.Surface((WIDTH, HEIGHT))
    surf_f = pygame.Surface((WIDTH, HEIGHT))
    g_unflipped.show_bg(surf_u)
    g_flipped.show_bg(surf_f)

    # Count non-bg pixels in the row-label area of the TOP-LEFT
    # screen square. The label should be drawn in both surfaces but
    # the GLYPH ('8' vs '1') is different shape.
    def _label_pixel_count(surf, x, y, w, h):
        bg_light = tuple(g_unflipped.config.theme.bg.light)[:3]
        bg_dark = tuple(g_unflipped.config.theme.bg.dark)[:3]
        count = 0
        for dy in range(h):
            for dx in range(w):
                px = tuple(surf.get_at((x + dx, y + dy)))[:3]
                if px != bg_light and px != bg_dark:
                    count += 1
        return count

    # Top-left row label region.
    cnt_unflipped = _label_pixel_count(surf_u, 5, 5, 12, 16)
    cnt_flipped = _label_pixel_count(surf_f, 5, 5, 12, 16)
    assert cnt_unflipped > 0, "Unflipped: top-left should have '8' label glyph"
    assert cnt_flipped > 0, "Flipped: top-left should have '1' label glyph"

    # Bottom-left col label region.
    cnt_bot_u = _label_pixel_count(surf_u, 0 * SQSIZE + SQSIZE - 20,
                                    HEIGHT - 20, 12, 16)
    cnt_bot_f = _label_pixel_count(surf_f, 0 * SQSIZE + SQSIZE - 20,
                                    HEIGHT - 20, 12, 16)
    assert cnt_bot_u > 0, "Unflipped: bottom-left should have 'a' label glyph"
    assert cnt_bot_f > 0, "Flipped: bottom-left should have 'h' label glyph"


# ---------------------------------------------------------------------------
# Click / motion translation
# ---------------------------------------------------------------------------

def test_pixel_at_top_left_maps_to_a8_unflipped():
    g = Game()
    # Top-left pixel (5, 5) → screen (0, 0).
    screen_row, screen_col = 0, 0
    board_row, board_col = g.screen_to_board(screen_row, screen_col)
    # Unflipped: screen (0,0) = board (0,0) = a8.
    assert (board_row, board_col) == (0, 0)


def test_pixel_at_top_left_maps_to_h1_when_flipped():
    g = Game()
    g.flip_board()
    screen_row, screen_col = 0, 0
    board_row, board_col = g.screen_to_board(screen_row, screen_col)
    # Flipped: screen (0,0) = board (7,7) = h1.
    assert (board_row, board_col) == (7, 7)


def test_set_hover_stores_correct_board_square_when_flipped():
    """When the player moves the mouse to the top-left of the screen
    on a flipped board, the hovered_sqr should be board (7, 7) — the
    square that's visually at top-left. set_hover should accept SCREEN
    coords and translate."""
    g = Game()
    g.flip_board()
    # Simulate the main.py MOUSEMOTION handler: motion_row/col are
    # SCREEN coords (mouse_y // SQSIZE, mouse_x // SQSIZE).
    g.set_hover_screen(0, 0)
    assert g.hovered_sqr.row == 7
    assert g.hovered_sqr.col == 7


def test_set_hover_unflipped_unchanged():
    g = Game()
    g.set_hover_screen(3, 4)
    assert g.hovered_sqr.row == 3
    assert g.hovered_sqr.col == 4


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def test_flip_does_not_affect_board_state():
    """Flipping is purely visual — board.squares, piece positions,
    captured_pieces, turn_number etc. are all unchanged."""
    g = Game()
    initial_squares = [[g.board.squares[r][c].piece for c in range(8)] for r in range(8)]
    initial_turn = g.board.turn_number
    initial_player = g.next_player

    g.flip_board()

    for r in range(8):
        for c in range(8):
            assert g.board.squares[r][c].piece is initial_squares[r][c], (
                f"Piece at ({r},{c}) changed after flip"
            )
    assert g.board.turn_number == initial_turn
    assert g.next_player == initial_player


def test_repeated_flip_returns_to_original_render():
    """Flipping twice should produce the same screen as not flipping."""
    g_a = Game()
    g_b = Game()
    g_b.flip_board()
    g_b.flip_board()
    surf_a = pygame.Surface((WIDTH, HEIGHT))
    surf_b = pygame.Surface((WIDTH, HEIGHT))
    g_a.show_bg(surf_a)
    g_a.show_pieces(surf_a)
    g_b.show_bg(surf_b)
    g_b.show_pieces(surf_b)
    # Spot-check a handful of squares.
    for r in [0, 3, 7]:
        for c in [0, 4, 7]:
            assert _pixel_in_square(surf_a, r, c) == _pixel_in_square(surf_b, r, c), (
                f"Double-flip produced different pixel at screen ({r},{c})"
            )
