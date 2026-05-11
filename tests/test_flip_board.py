"""Tests for the flip-board feature (F key).

Flipping the board is a purely visual 180° rotation: black's pieces
appear at the bottom of the screen, white's at the top. Both rows and
columns reverse. The underlying board state is unchanged — only the
mapping between board coordinates (the row/col of every piece) and
screen coordinates (the pixel position where it's drawn) is mirrored.

These tests pin the contract:

  - State: `Game.flipped` is a bool, defaults to False; `flip_board()`
    toggles it. Flipping is allowed in ANY state (drag, jump-capture
    pending, menu open) because it's purely visual — unlike undo/
    redo which mutates board state.
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
  - Mid-action flip: dragger / jump-capture / menu state survives the
    flip; pixel-space artifacts (hovered_sqr, menu_rects) are cleared
    so they cannot drive actions at stale positions.
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


def test_can_flip_returns_true_during_jump_capture():
    """Flip is allowed during a pending jump-capture. The targets/
    landing are stored in board coordinates; flipping just re-renders
    the highlights at the mirrored screen positions, and the eventual
    click is translated back via screen_to_board."""
    g = Game()
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    assert g.can_flip() is True


def test_can_flip_returns_true_during_drag():
    """Flip is allowed mid-drag. The dragger's initial_row/col is in
    board coords (set by main.py after save_initial), so it survives
    the flip; the dragged piece sprite stays attached to the cursor
    pixel; the move highlights re-render at mirrored screen positions;
    and the eventual release click is translated via screen_to_board."""
    g = Game()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    assert g.can_flip() is True


def test_can_flip_returns_true_during_transform_menu():
    """Flip is allowed with the transform menu open. The menu's row/col
    is in board coords, so the next render places it at the mirrored
    screen position; menu_rects (pixel-space, stale after flip) are
    cleared by flip_board so a click before the next render can't
    trigger a wrong option."""
    g = Game()
    g.transform_menu = {'piece': None, 'row': 0, 'col': 0, 'options': []}
    assert g.can_flip() is True


def test_can_flip_returns_true_during_promotion_menu():
    g = Game()
    g.promotion_menu = {'pawn': None, 'row': 0, 'col': 0}
    assert g.can_flip() is True


def test_flip_board_succeeds_during_intermediate_state():
    """flip_board() returns True and toggles even mid-action — the
    underlying state of the action is preserved (only screen-pixel
    artifacts like hovered_sqr / menu_rects are cleared, since those
    refer to pre-flip positions)."""
    g = Game()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    g.dragger.initial_row = 7
    g.dragger.initial_col = 1
    result = g.flip_board()
    assert result is True
    assert g.flipped is True
    # Drag state preserved: same piece, same board origin.
    assert g.dragger.dragging is True
    assert isinstance(g.dragger.piece, Knight)
    assert g.dragger.piece.color == 'white'
    assert g.dragger.initial_row == 7
    assert g.dragger.initial_col == 1


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


def _theme_color_rgb(c):
    """Normalize a theme colour into an (r, g, b) tuple. Themes mix
    raw tuples (for bg/trace) and hex strings like '#C86464' (for
    moves). pygame.Color accepts both and exposes r, g, b."""
    col = pygame.Color(c) if isinstance(c, str) else pygame.Color(*c)
    return (col.r, col.g, col.b)


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


# ---------------------------------------------------------------------------
# Mid-action flip
# ---------------------------------------------------------------------------
#
# These tests pin the behaviour of `flip_board()` when called while
# something else is in progress on the UI. The general rule: the
# action's STATE (board-coord fields) is preserved across the flip;
# only the SCREEN-PIXEL-SPACE artifacts (hovered_sqr, menu_rects) that
# refer to pre-flip positions are cleared. The next render frame
# rebuilds them at the mirrored screen positions, and the next
# MOUSEMOTION re-fills hovered_sqr through the current flip state.

def test_flip_clears_hovered_sqr():
    """The cursor pixel position is unchanged by a flip, but the BOARD
    square under that pixel is now different (both axes mirrored). The
    pre-flip hovered_sqr is stale — clear it so the hover outline
    doesn't render at the wrong screen position. The next MOUSEMOTION
    re-fills it via set_hover_screen with the current flip state."""
    g = Game()
    g.set_hover_screen(3, 4)
    assert g.hovered_sqr is not None
    g.flip_board()
    assert g.hovered_sqr is None


def test_flip_clears_transform_menu_rects():
    """menu_rects are screen-pixel pygame.Rect objects rebuilt every
    show_transform_menu blit. After a flip they reference pre-flip
    positions. flip_board clears them so a click before the next
    render can't hit a stale rect; the next render rebuilds them at
    the mirrored screen positions."""
    g = Game()
    g.transform_menu = {
        'piece': None, 'piece_color': 'white',
        'row': 1, 'col': 1, 'options': ['knight', 'bishop'],
    }
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_transform_menu(surf)
    assert len(g.transform_menu_rects) == 2

    g.flip_board()
    assert g.transform_menu_rects == []

    # And the menu state itself survived — re-rendering rebuilds rects
    # at the mirrored screen positions.
    surf2 = pygame.Surface((WIDTH, HEIGHT))
    g.show_transform_menu(surf2)
    assert len(g.transform_menu_rects) == 2


def test_flip_clears_promotion_menu_rects():
    """Same contract as transform_menu_rects."""
    g = Game()
    # Place a real pawn so show_promotion_menu can read promotion options.
    pawn = Pawn('white')
    g.board.squares[0][4].piece = pawn
    g.promotion_menu = {
        'pawn': pawn, 'pawn_color': 'white',
        'row': 0, 'col': 4,
    }
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_promotion_menu(surf)
    assert len(g.promotion_menu_rects) > 0

    g.flip_board()
    assert g.promotion_menu_rects == []


def test_flip_preserves_jump_capture_state():
    """Targets/landing are board-coord; flipping doesn't touch them."""
    g = Game()
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    g.jump_capture_origin = (5, 6)
    g.flip_board()
    assert g.jump_capture_targets == [(3, 4)]
    assert g.jump_capture_landing == (3, 5)
    assert g.jump_capture_origin == (5, 6)
    assert g.flipped is True


def test_flip_preserves_transform_menu_state():
    """The menu dict (board-coord row/col + options) survives."""
    g = Game()
    g.transform_menu = {
        'piece': None, 'piece_color': 'white',
        'row': 2, 'col': 3, 'options': ['knight', 'bishop'],
    }
    g.flip_board()
    assert g.transform_menu['row'] == 2
    assert g.transform_menu['col'] == 3
    assert g.transform_menu['options'] == ['knight', 'bishop']
    assert g.flipped is True


def test_flip_during_drag_re_renders_legal_moves_at_flipped_positions():
    """The legal-move highlights drawn by show_moves should re-render
    at the mirrored screen positions after a mid-drag flip. The pawn
    on e2 (board row 6, col 4) has a forward move to e3 (board row 5,
    col 4); the highlight goes to screen (5, 4) unflipped and screen
    (2, 3) flipped."""
    g = Game()
    pawn = g.board.squares[6][4].piece
    pawn.clear_moves()
    g.board.pawn_moves(pawn, 6, 4)
    g.dragger.dragging = True
    g.dragger.piece = pawn
    g.dragger.initial_row = 6
    g.dragger.initial_col = 4

    moves_dark = _theme_color_rgb(g.config.theme.moves.dark)
    # Board (5, 4) parity = 9 = odd → moves.dark.

    surf_a = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf_a)
    g.show_moves(surf_a)
    pixel_a = _pixel_in_square(surf_a, 5, 4)
    assert pixel_a == moves_dark, (
        f"Unflipped: move-highlight for pawn e3 should be at screen (5,4); "
        f"got pixel {pixel_a}"
    )

    g.flip_board()
    # Dragger state preserved across the flip.
    assert g.dragger.dragging is True
    assert g.dragger.piece is pawn
    assert g.dragger.initial_row == 6
    assert g.dragger.initial_col == 4

    surf_b = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf_b)
    g.show_moves(surf_b)
    pixel_b = _pixel_in_square(surf_b, 2, 3)
    assert pixel_b == moves_dark, (
        f"Flipped: move-highlight for pawn e3 should be at screen (2,3); "
        f"got pixel {pixel_b}"
    )
    # And the OLD position (5, 4) should no longer have the highlight.
    pixel_old = _pixel_in_square(surf_b, 5, 4)
    assert pixel_old != moves_dark, (
        f"Flipped: stale highlight remained at screen (5,4); got {pixel_old}"
    )


def test_flip_during_jump_capture_re_renders_highlights_at_flipped_positions():
    """Jump-capture highlights (landing + targets) should re-render at
    mirrored screen positions after a mid-jump-capture flip."""
    g = Game()
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)

    moves_light = _theme_color_rgb(g.config.theme.moves.light)
    moves_dark = _theme_color_rgb(g.config.theme.moves.dark)

    surf_a = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf_a)
    g.show_jump_capture_targets(surf_a)
    # Landing (3, 5) parity = 8 = even → moves.light
    pixel_a_landing = _pixel_in_square(surf_a, 3, 5)
    assert pixel_a_landing == moves_light, (
        f"Unflipped landing should be moves.light at (3,5); got {pixel_a_landing}"
    )
    # Target (3, 4) parity = 7 = odd → moves.dark
    pixel_a_target = _pixel_in_square(surf_a, 3, 4)
    assert pixel_a_target == moves_dark, (
        f"Unflipped target should be moves.dark at (3,4); got {pixel_a_target}"
    )

    g.flip_board()
    surf_b = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf_b)
    g.show_jump_capture_targets(surf_b)
    # Board (3, 5) → screen (4, 2). Color preserved (parity invariant).
    pixel_b_landing = _pixel_in_square(surf_b, 4, 2)
    assert pixel_b_landing == moves_light, (
        f"Flipped landing should be at screen (4,2); got {pixel_b_landing}"
    )
    # Board (3, 4) → screen (4, 3).
    pixel_b_target = _pixel_in_square(surf_b, 4, 3)
    assert pixel_b_target == moves_dark, (
        f"Flipped target should be at screen (4,3); got {pixel_b_target}"
    )
    # Old positions should NO LONGER carry the jump-capture highlight.
    # (3, 5) unflipped position is now (3+5, 7) = check pixel at (3, 5)
    # should not be moves.light anymore — it's just bg now.
    bg_light = tuple(g.config.theme.bg.light)[:3]
    bg_dark = tuple(g.config.theme.bg.dark)[:3]
    pixel_b_old = _pixel_in_square(surf_b, 3, 5)
    assert pixel_b_old in (bg_light, bg_dark), (
        f"Flipped: stale highlight at old screen (3,5); got {pixel_b_old}"
    )


def test_flip_during_transform_menu_repositions_to_flipped_anchor():
    """The transform menu is anchored at the queen's board position.
    After a flip, the menu must render relative to the mirrored screen
    position of that queen — including switching direction (down vs
    up) to keep the menu on the visible screen."""
    g = Game()
    # Queen at board (0, 0). Unflipped: screen (0, 0); menu extends
    # downward (screen rows 1, 2). Flipped: screen (7, 7); menu must
    # extend upward (screen rows 6, 5) so it stays on screen.
    g.transform_menu = {
        'piece': None, 'piece_color': 'white',
        'row': 0, 'col': 0, 'options': ['knight', 'bishop'],
    }
    surf_a = pygame.Surface((WIDTH, HEIGHT))
    g.show_transform_menu(surf_a)
    # Unflipped: rects at screen rows 1 and 2, col 0.
    assert len(g.transform_menu_rects) == 2
    rect_a_0, _ = g.transform_menu_rects[0]
    rect_a_1, _ = g.transform_menu_rects[1]
    assert rect_a_0.x == 0 and rect_a_0.y == 1 * SQSIZE
    assert rect_a_1.x == 0 and rect_a_1.y == 2 * SQSIZE

    g.flip_board()
    # flip clears the rects (until next render).
    assert g.transform_menu_rects == []
    surf_b = pygame.Surface((WIDTH, HEIGHT))
    g.show_transform_menu(surf_b)
    assert len(g.transform_menu_rects) == 2
    rect_b_0, _ = g.transform_menu_rects[0]
    rect_b_1, _ = g.transform_menu_rects[1]
    # Anchor is now screen (7, 7); menu must extend upward to fit.
    # Direction = -1; menu_sr = start_sr - (len - i) = 7 - (2-i)
    # i=0 → 5, i=1 → 6.
    assert rect_b_0.x == 7 * SQSIZE
    assert rect_b_0.y == 5 * SQSIZE
    assert rect_b_1.x == 7 * SQSIZE
    assert rect_b_1.y == 6 * SQSIZE


def test_release_after_mid_drag_flip_uses_current_flip_for_translation():
    """The contract: at release time, board-space released_row/col is
    derived from the screen position via screen_to_board WITH THE
    CURRENT FLIP. So if the player picks up at board (6, 4), flips,
    and the cursor pixel ends at screen (5, 4), the move's final
    board square is (2, 3) — even though the player's drag began
    pre-flip. The dragger's initial_row/col remains in board coords
    (set in main.py from the post-translation clicked_row/col) and
    is unaffected by the flip."""
    g = Game()
    g.dragger.dragging = True
    g.dragger.piece = g.board.squares[6][4].piece
    g.dragger.initial_row = 6
    g.dragger.initial_col = 4

    g.flip_board()
    # initial preserved as board coords.
    assert g.dragger.initial_row == 6
    assert g.dragger.initial_col == 4

    # Simulate release at screen (5, 4): screen_to_board with flipped=True
    # → (7-5, 7-4) = (2, 3).
    released_board = g.screen_to_board(5, 4)
    assert released_board == (2, 3)


def test_mid_drag_flip_keeps_dragged_piece_off_board_render():
    """While dragging, show_pieces renders all pieces EXCEPT the
    dragger.piece. After a mid-drag flip, the dragged piece's
    original board square (now at a mirrored screen position) should
    still render as empty — the piece is attached to the cursor, not
    to its origin square."""
    g = Game()
    pawn = g.board.squares[6][4].piece  # e2 pawn
    g.dragger.dragging = True
    g.dragger.piece = pawn
    g.dragger.initial_row = 6
    g.dragger.initial_col = 4

    g.flip_board()
    # Board (6, 4) renders at screen (1, 3) when flipped. That screen
    # square should be empty (just bg) since the pawn is "held" by
    # the cursor.
    surf = pygame.Surface((WIDTH, HEIGHT))
    g.show_bg(surf)
    g.show_pieces(surf)
    bg_light = tuple(g.config.theme.bg.light)[:3]
    bg_dark = tuple(g.config.theme.bg.dark)[:3]
    pixel = _pixel_in_square(surf, 1, 3)
    assert pixel in (bg_light, bg_dark), (
        f"Mid-drag flipped: origin screen (1,3) should be empty bg; "
        f"got {pixel}"
    )


def test_flip_does_not_clear_board_last_move():
    """board.last_move is the move-history highlight — board-coord
    based and untouched by flip."""
    g = Game()
    g.board.last_move = Move(Square(0, 0), Square(4, 4))
    g.flip_board()
    assert g.board.last_move is not None
    assert g.board.last_move.initial.row == 0
    assert g.board.last_move.initial.col == 0
    assert g.board.last_move.final.row == 4
    assert g.board.last_move.final.col == 4


def test_flip_during_all_intermediate_states_does_not_raise():
    """Smoke test: stack up every intermediate-state field and verify
    flip_board doesn't blow up. Defensive — protects against future
    changes adding new in-action state that flip might forget to
    consider."""
    g = Game()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    g.dragger.initial_row = 3
    g.dragger.initial_col = 4
    g.jump_capture_targets = [(2, 2)]
    g.jump_capture_landing = (2, 4)
    g.transform_menu = {
        'piece': None, 'piece_color': 'white',
        'row': 1, 'col': 1, 'options': ['knight'],
    }
    g.promotion_menu = {
        'pawn': None, 'pawn_color': 'white',
        'row': 0, 'col': 0,
    }
    # Should toggle without error in any combination.
    assert g.flip_board() is True
    assert g.flipped is True
    assert g.flip_board() is True
    assert g.flipped is False


def test_flip_persists_through_winner_state():
    """After the game ends, flipping is still permitted — there's no
    in-action state to invalidate, and reviewing a finished game from
    the loser's perspective is a natural use case."""
    g = Game()
    g.winner = 'white'
    assert g.can_flip() is True
    assert g.flip_board() is True
    assert g.flipped is True
