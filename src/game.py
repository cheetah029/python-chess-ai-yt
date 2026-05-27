import copy
import os

import pygame
from pygame import gfxdraw
from PIL import Image

from const import *
from board import Board
from dragger import Dragger
from config import Config
from square import Square
from piece import Queen, Boulder
from shield_polygons import SHIELD_POLYGONS


# Repo root used to resolve AI checkpoint paths.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# Corner positions for overlays placed on a piece's square. Each overlay
# kind chooses a corner so that multiple simultaneous overlays don't
# overlap.
OVERLAY_POSITION_BOTTOM_RIGHT = 'bottom_right'
OVERLAY_POSITION_BOTTOM_LEFT = 'bottom_left'
OVERLAY_POSITION_TOP_RIGHT = 'top_right'
OVERLAY_POSITION_TOP_LEFT = 'top_left'

# Pixel size of an overlay icon on the board. ~41% of SQSIZE — a bit
# bigger than the original 30 for readability, but slightly smaller
# than 36 so the overlay doesn't crowd the piece texture. Affects all
# overlay kinds equally (queen/pawn markers and the shield).
OVERLAY_SIZE = 33


def compute_piece_overlays(piece):
    """Return a list of overlay specs to render on top of a piece's square.

    Each spec is a dict with these keys:
      - 'kind': user-visible name. One of 'queen_marker', 'pawn_marker',
        or 'shield'.
      - 'render_kind': how the renderer should draw it. 'image' means
        load the PNG at 'asset' and blit. 'shield_vector' means draw the
        named entry in SHIELD_POLYGONS via pygame.gfxdraw — sharp at any
        size because the geometry is stored as polygon vertices rather
        than baked pixels.
      - 'asset' (image render_kind only): file path to the PNG.
      - 'shield_id' (shield_vector render_kind only): key into
        SHIELD_POLYGONS.
      - 'position': one of the OVERLAY_POSITION_* constants.

    Overlays produced:
      - 'queen_marker' (image, bottom-right): royal queens that have
        transformed into another piece type, so the player can see
        which piece "is really the royal queen".
      - 'pawn_marker' (image, bottom-right): any non-royal queen
        (promoted) — in base form or transformed — distinguishing from
        the royal queen.
      - 'shield' (shield_vector, top-right): any invulnerable piece. In
        v2, typically a knight that just made a non-capture jump and is
        invulnerable for one opponent turn. Skipped for boulders (they
        aren't capturable anyway, so the indicator would be meaningless).
        Drawn as a stack of antialiased polygons; immune to the scaling
        blur that a raster overlay would suffer at 30x30.

    Positions are guaranteed unique across the returned overlays for a
    given piece — bottom-right for the queen/pawn marker, top-right for
    the shield. They cannot collide visually.
    """
    overlays = []
    color = piece.color
    if piece.is_transformed and piece.is_royal:
        overlays.append({
            'kind': 'queen_marker',
            'render_kind': 'image',
            'asset': f'assets/images/imgs-80px/{color}_queen.png',
            'position': OVERLAY_POSITION_BOTTOM_RIGHT,
        })
    elif not piece.is_royal and (isinstance(piece, Queen) or piece.is_transformed):
        overlays.append({
            'kind': 'pawn_marker',
            'render_kind': 'image',
            'asset': f'assets/images/imgs-80px/{color}_pawn.png',
            'position': OVERLAY_POSITION_BOTTOM_RIGHT,
        })
    if piece.invulnerable and not isinstance(piece, Boulder):
        overlays.append({
            'kind': 'shield',
            'render_kind': 'shield_vector',
            'shield_id': f'{color}_shield',
            # Top-right keeps the shield on the opposite diagonal from the
            # queen/pawn marker (bottom-right), so the two never collide
            # and the shield reads as a temporary status indicator rather
            # than another identity marker.
            'position': OVERLAY_POSITION_TOP_RIGHT,
        })
    return overlays


def _hex_to_rgb(hexstr):
    """Convert '#rrggbb' to a 3-tuple of ints."""
    s = hexstr.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# Supersampling factor for vector shield rendering. The shield is drawn
# onto an off-screen surface at SHIELD_SUPERSAMPLE x the final size,
# then downsampled with PIL's LANCZOS filter — a sinc-windowed kernel
# that preserves edge sharpness much better than pygame's bilinear
# smoothscale. 8x supersampling means 64 samples per output pixel,
# which essentially eliminates aliasing for the polygon shapes we draw.
SHIELD_SUPERSAMPLE = 8


# Cache of fully-rendered shield surfaces, keyed by (shield_id, size).
# Rendering each shield involves several hundred polygon-vertex draws
# at SHIELD_SUPERSAMPLE^2 = 64x the pixel count, plus a pygame->PIL
# round-trip for the LANCZOS downsample. Caching makes the per-frame
# cost a single blit after the first render.
_shield_surface_cache = {}


def _render_shield_to_surface(shield_id, size):
    """Render the named shield into a pygame.Surface of (size, size).
    Result is cached, so subsequent calls with the same arguments
    return the same surface (and the expensive supersample render
    only happens once).

    Pipeline:
      1. Make a transparent off-screen Surface at SHIELD_SUPERSAMPLE x size.
      2. Paint each polygon layer in order (outermost first) via
         pygame.gfxdraw.filled_polygon + aapolygon.
      3. Convert the Surface to a PIL Image (via the raw RGBA byte
         buffer — fast, zero-copy in spirit).
      4. PIL LANCZOS resize down to (size, size). This is the key step
         for smooth edges: LANCZOS uses a sinc-windowed reconstruction
         kernel that beats bilinear filtering for high-frequency
         features like polygon edges.
      5. Convert the resized PIL Image back to a pygame.Surface.
    """
    key = (shield_id, size)
    cached = _shield_surface_cache.get(key)
    if cached is not None:
        return cached

    big = size * SHIELD_SUPERSAMPLE
    big_surf = pygame.Surface((big, big), pygame.SRCALPHA)
    for layer in SHIELD_POLYGONS[shield_id]:
        rgb = _hex_to_rgb(layer['color'])
        scaled = [
            (int(round(nx * big)), int(round(ny * big)))
            for (nx, ny) in layer['points']
        ]
        if len(scaled) < 3:
            continue
        gfxdraw.filled_polygon(big_surf, scaled, rgb)
        gfxdraw.aapolygon(big_surf, scaled, rgb)

    rgba_bytes = pygame.image.tobytes(big_surf, 'RGBA')
    pil_big = Image.frombytes('RGBA', (big, big), rgba_bytes)
    pil_small = pil_big.resize((size, size), Image.LANCZOS)
    small_surf = pygame.image.frombytes(pil_small.tobytes(), (size, size), 'RGBA')

    _shield_surface_cache[key] = small_surf
    return small_surf


def _draw_shield_vector(surface, x, y, size, shield_id):
    """Blit a vector-rendered, antialiased shield at pixel position (x, y)
    with side length `size`. The actual rendering is cached after the
    first call per (shield_id, size); subsequent calls are just a blit.

    Each shield is a stack of filled polygons drawn in order: the
    outermost layer (largest enclosed area) paints first, then smaller
    layers paint on top — so e.g. the black silhouette fills the whole
    shield, then a white interior paints over the inside.

    Because the polygon vertices are stored in unit-square coordinates
    they scale to any `size` with no resolution loss — vector geometry
    rather than a downscaled raster.
    """
    shield_surf = _render_shield_to_surface(shield_id, size)
    surface.blit(shield_surf, (x, y))


def _overlay_pixel_origin(row, col, position):
    """Return the (x, y) pixel coordinate where the overlay's
    top-left corner should be drawn for the given square + position."""
    base_x = col * SQSIZE
    base_y = row * SQSIZE
    margin = 2  # small inset from the square edge
    if position == OVERLAY_POSITION_BOTTOM_RIGHT:
        return (base_x + SQSIZE - OVERLAY_SIZE - margin,
                base_y + SQSIZE - OVERLAY_SIZE - margin)
    if position == OVERLAY_POSITION_BOTTOM_LEFT:
        return (base_x + margin,
                base_y + SQSIZE - OVERLAY_SIZE - margin)
    if position == OVERLAY_POSITION_TOP_RIGHT:
        return (base_x + SQSIZE - OVERLAY_SIZE - margin,
                base_y + margin)
    if position == OVERLAY_POSITION_TOP_LEFT:
        return (base_x + margin, base_y + margin)
    raise ValueError(f"Unknown overlay position: {position}")



class Game:

    # Mode selector — two INDEPENDENT dimensions, rendered as two button
    # rows in the in-UI menu. SIDE_OPTIONS is which colour the human plays;
    # OPPONENT_OPTIONS is what plays the other colour. Selecting one updates
    # only that dimension, leaving the other in place. Extensible: append
    # entries to OPPONENT_OPTIONS to plug in future difficulty levels
    # (Easy / Medium / Hard AI) and add a matching branch in `_make_ai_player`.
    SIDE_OPTIONS = [
        {'key': 'white', 'label': 'White'},
        {'key': 'black', 'label': 'Black'},
    ]
    OPPONENT_OPTIONS = [
        {'key': 'human',  'label': 'Human (2 players)'},
        {'key': 'random', 'label': 'Random'},
        {'key': 'easy',   'label': 'AI Easy'},
        {'key': 'medium', 'label': 'AI Medium'},
        {'key': 'hard',   'label': 'AI Hard'},
    ]

    # AI difficulty → checkpoint path. Difficulty is realised by training
    # depth: an under-trained network is "easy" because it still picks
    # near-random moves; a fully-trained network is "hard". Medium and
    # hard checkpoints become available as training progresses; the menu
    # grays out entries whose checkpoint does not exist on disk.
    _AI_CHECKPOINTS = {
        'easy':   os.path.join(_REPO_ROOT, 'models/variant_freeze_v3/model_iter_0020.pt'),
        'medium': os.path.join(_REPO_ROOT, 'models/variant_freeze_v3/model_iter_0050.pt'),
        'hard':   os.path.join(_REPO_ROOT, 'models/variant_freeze_v3/model_iter_0100.pt'),
    }

    def __init__(self, knight_mode=Board.KNIGHT_MODE_V2):
        """Construct a Game. `knight_mode` controls which knight rules
        the board uses:

          - `Board.KNIGHT_MODE_V2` (default): reactive jump-capture +
            post-non-capture-jump invulnerability. Active rule set.
          - `Board.KNIGHT_MODE_LEGACY`: pre-v2 rules. Used by the
            `main_v0.py` and `main_v1.py` snapshot mainloops so they
            continue to reflect their historical knight behaviour
            (capture any adjacent enemy to landing square after a jump;
            no invulnerability).
        """
        self.next_player = 'white'
        self.hovered_sqr = None
        self.board = Board(knight_mode=knight_mode)
        self.dragger = Dragger()
        self.config = Config()
        # Jump capture state: when a knight lands and has adjacent enemies to capture
        self.jump_capture_targets = None  # list of (row, col) or None
        self.jump_capture_landing = None  # (row, col) of the knight's landing square
        self.jump_capture_piece = None    # the knight piece (to set forbidden_square if manipulated)
        self.jump_capture_origin = None   # (row, col) the knight moved from (for forbidden_square)
        # Transformation menu state
        self.transform_menu = None        # dict with 'piece', 'row', 'col', 'options' or None
        self.transform_menu_rects = []    # list of (rect, option_name) for click detection
        # Promotion menu state
        self.promotion_menu = None        # dict with 'pawn', 'row', 'col' or None
        self.promotion_menu_rects = []    # list of (rect, option_name) for click detection
        # Mode-selector menu state (Goal 2). Opened via M in main.py. The
        # menu lets the user pick their side AND their opponent independently;
        # each click applies that one dimension and leaves the menu open
        # (live-settings model) so the user can also change the other.
        self.mode_menu = None             # dict with 'sides' + 'opponents', or None
        self.mode_menu_rects = []         # [(rect, 'side'|'opponent', key), ...]
        # User choices — the two dimensions the menu exposes.
        self.user_side = 'white'          # the colour the human plays
        self.opponent = 'human'           # 'human' or an AI key (e.g. 'random')
        # Derived from (user_side, opponent); kept in sync by `_refresh_ai`.
        self.mode = 'human_vs_human'      # string for display/logging
        self.ai_color = None              # opposite of user_side when AI is active
        self.ai_controller = None
        self.winner = None                # 'white', 'black', or None
        # Record initial board state for repetition rule
        self.board.record_state(self.next_player)
        # Undo/redo history. `_history` is a stack of full state snapshots
        # (one per turn boundary, plus the initial state at the bottom).
        # `_redo_stack` holds states that were undone — populated by undo,
        # consumed by redo, cleared whenever a new turn happens.
        # `_pre_jump_capture_snapshot` is set when entering the second-click
        # state of a knight jump-capture, so cancel can restore the state
        # to before the knight's leap.
        self._history = []
        self._redo_stack = []
        self._pre_jump_capture_snapshot = None
        self._history.append(self._snapshot())
        # Flip-board state. When True, the board is displayed rotated 180°:
        # the row and column of every square are mirrored on screen, so
        # black appears at the bottom. This is purely a viewing preference —
        # the underlying board.squares array is untouched. All show_*
        # methods translate (board_row, board_col) → (screen_row, screen_col)
        # via `board_to_screen`; all click handlers translate the other
        # direction via `screen_to_board`. The piece textures themselves
        # are NOT rotated (so a knight still faces its sprite's direction).
        # The flag persists across `reset()` because it's a UI preference,
        # not game state.
        self.flipped = False

    # ---- Flip board (viewing rotation) ------------------------------------

    def can_flip(self):
        """Always True. Flipping the board is purely visual and is
        therefore safe in any state, including mid-drag, mid-jump-
        capture, and with a menu open. The intermediate-state gate
        that applies to undo/redo (which mutate board state) is NOT
        applied here — undo/redo can't safely run during partial
        actions, but a 180° viewing rotation can.

        Kept as a method (rather than inlining True) so callers can
        ask the question explicitly and so future viewing-state
        preconditions (e.g. animation-in-progress) have a hook."""
        return True

    def flip_board(self):
        """Toggle the flipped state. Always succeeds (purely visual).

        Mid-action flips need a small amount of cleanup so that
        pixel-space artifacts captured BEFORE the flip don't drive
        actions AFTER the flip:

          - `hovered_sqr` records the BOARD square the cursor was
            over. After a 180° flip, the same pixel coordinate sits
            over a DIFFERENT board square, so the recorded hover is
            stale. We clear it; the next MOUSEMOTION re-fills it via
            `set_hover_screen` (which translates through the current
            flip state).
          - `transform_menu_rects` / `promotion_menu_rects` are stored
            in screen-pixel space, computed during the last
            `show_*_menu` blit. After a flip they reference pre-flip
            positions. We clear them so that any click landing before
            the next render frame rebuilds them can't trigger an
            unintended option. The next render rebuilds them at the
            mirrored screen positions, so the menu remains usable.

        The menu state itself (`transform_menu`, `promotion_menu` —
        which hold board-space row/col) is preserved across the flip,
        as are the dragger state, jump-capture targets/landing
        (board-space), board.last_move, and every other game-logic
        field.

        Returns True. (Kept as a return value for symmetry with the
        old gated version of this method, and so callers can write
        `if game.flip_board(): ...` for follow-on actions.)"""
        self.flipped = not self.flipped
        self.hovered_sqr = None
        self.transform_menu_rects = []
        self.promotion_menu_rects = []
        return True

    def board_to_screen(self, row, col):
        """Translate a board (row, col) to its screen (row, col).
        Identity when not flipped; mirrors both axes when flipped."""
        if self.flipped:
            return (ROWS - 1 - row, COLS - 1 - col)
        return (row, col)

    def screen_to_board(self, screen_row, screen_col):
        """Inverse of `board_to_screen`. Translate a screen (row, col)
        to its board (row, col). The two functions are involutions —
        applying either twice returns the original."""
        if self.flipped:
            return (ROWS - 1 - screen_row, COLS - 1 - screen_col)
        return (screen_row, screen_col)

    # blit methods

    def show_bg(self, surface):
        theme = self.config.theme

        for row in range(ROWS):
            for col in range(COLS):
                # color (depends on board (row, col) parity; the 180° flip
                # preserves parity, so the checker pattern looks identical
                # in screen space whether flipped or not)
                color = theme.bg.light if (row + col) % 2 == 0 else theme.bg.dark
                # rect (at flipped screen position)
                sr, sc = self.board_to_screen(row, col)
                rect = (sc * SQSIZE, sr * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, color, rect)

        # Draw labels at the bottom layer so the previous-snapshot
        # mainloops (`main_v0.py`, `main_v1.py`) that don't call
        # `show_coordinates` separately still see them. In the active
        # `main.py` the labels are redrawn after move highlights via
        # `show_coordinates`, which prevents the highlight rectangles
        # from erasing edge-square labels.
        self.show_coordinates(surface)

    def show_coordinates(self, surface):
        """Draw the row (1-8) and column (a-h) labels.

        Called twice from the active `main.py`'s render loop: once
        implicitly via `show_bg` (initial pass) and once explicitly
        after the move-highlight overlays so that highlighted edge
        squares don't lose their label to the highlight rectangle.
        The redraw is cheap (just font blits) and idempotent.
        """
        theme = self.config.theme
        for row in range(ROWS):
            for col in range(COLS):
                sr, sc = self.board_to_screen(row, col)
                # row coordinates — drawn at the leftmost SCREEN column
                # of each row. When flipped, the leftmost screen column
                # holds the highest board columns (col == 7), so iterating
                # in board order produces row labels '1','2',...,'8' top-
                # to-bottom (matching the player who's now at the bottom).
                if sc == 0:
                    color = theme.bg.dark if (row + col) % 2 == 0 else theme.bg.light
                    lbl = self.config.font.render(str(ROWS-row), 1, color)
                    lbl_pos = (5, 5 + sr * SQSIZE)
                    surface.blit(lbl, lbl_pos)
                # col coordinates — drawn along the bottom SCREEN row.
                # Flipped: bottom screen row is board row 0, so col labels
                # appear in board-col order across the flipped bottom row,
                # which visually reads 'h','g',...,'a' (since the leftmost
                # screen position holds the highest board column).
                if sr == 7:
                    color = theme.bg.dark if (row + col) % 2 == 0 else theme.bg.light
                    lbl = self.config.font.render(Square.get_alphacol(col), 1, color)
                    lbl_pos = (sc * SQSIZE + SQSIZE - 20, HEIGHT - 20)
                    surface.blit(lbl, lbl_pos)

    def show_pieces(self, surface):
        for row in range(ROWS):
            for col in range(COLS):
                # piece ?
                if self.board.squares[row][col].has_piece():
                    piece = self.board.squares[row][col].piece

                    # all pieces except dragger piece
                    if piece is not self.dragger.piece:
                        sr, sc = self.board_to_screen(row, col)
                        piece.set_texture(size=80)
                        img = pygame.image.load(piece.texture)
                        img_center = sc * SQSIZE + SQSIZE // 2, sr * SQSIZE + SQSIZE // 2
                        piece.texture_rect = img.get_rect(center=img_center)

                        surface.blit(img, piece.texture_rect)

                        # Render any overlays for this piece. The queen
                        # and pawn markers are PNG-backed (loaded and
                        # smoothscaled to OVERLAY_SIZE). The shield is
                        # drawn directly from vector polygon data via
                        # pygame.gfxdraw, so it stays sharp at any size.
                        # Overlay corner positions (top-right, bottom-
                        # right, etc.) are screen-space concepts — pass
                        # the screen (sr, sc) so e.g. BOTTOM_RIGHT stays
                        # at the visual bottom-right of the screen square.
                        for ov in compute_piece_overlays(piece):
                            ox, oy = _overlay_pixel_origin(sr, sc, ov['position'])
                            if ov['render_kind'] == 'image':
                                ov_img = pygame.image.load(ov['asset'])
                                ov_img = pygame.transform.smoothscale(
                                    ov_img, (OVERLAY_SIZE, OVERLAY_SIZE)
                                )
                                surface.blit(ov_img, (ox, oy))
                            elif ov['render_kind'] == 'shield_vector':
                                _draw_shield_vector(
                                    surface, ox, oy, OVERLAY_SIZE, ov['shield_id']
                                )

        # Render boulder on intersection (not on any square)
        if self.board.boulder and self.board.boulder is not self.dragger.piece:
            boulder = self.board.boulder
            boulder.set_texture(size=80)
            img = pygame.image.load(boulder.texture)
            # Center between d4, d5, e4, e5: at the corner where they meet
            img_center = 4 * SQSIZE, 4 * SQSIZE  # col=4 * SQSIZE, row=4 * SQSIZE = corner of d4/d5/e4/e5
            boulder.texture_rect = img.get_rect(center=img_center)
            surface.blit(img, boulder.texture_rect)

    def show_moves(self, surface):
        theme = self.config.theme

        if self.dragger.dragging:
            piece = self.dragger.piece

            # loop all valid moves
            for move in piece.moves:
                # color
                color = theme.moves.light if (move.final.row + move.final.col) % 2 == 0 else theme.moves.dark
                # rect (translated to screen position when flipped)
                sr, sc = self.board_to_screen(move.final.row, move.final.col)
                rect = (sc * SQSIZE, sr * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, color, rect)

    def show_jump_capture_targets(self, surface):
        """Highlight capturable squares and the landing square during jump capture selection."""
        theme = self.config.theme
        if self.jump_capture_targets and self.jump_capture_landing:
            # Highlight landing square (click to decline capture)
            lr, lc = self.jump_capture_landing
            all_squares = [self.jump_capture_landing] + self.jump_capture_targets
            for row, col in all_squares:
                color = theme.moves.light if (row + col) % 2 == 0 else theme.moves.dark
                sr, sc = self.board_to_screen(row, col)
                rect = (sc * SQSIZE, sr * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, color, rect)

    def show_last_move(self, surface):
        theme = self.config.theme

        if self.board.last_action:
            # Non-spatial action highlight (e.g. transformation) — single square
            pos = self.board.last_action
            color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark
            sr, sc = self.board_to_screen(pos.row, pos.col)
            rect = (sc * SQSIZE, sr * SQSIZE, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, color, rect)
        elif self.board.last_move:
            initial = self.board.last_move.initial
            final = self.board.last_move.final

            for pos in [initial, final]:
                # color
                color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark
                # rect (translated to screen position when flipped)
                sr, sc = self.board_to_screen(pos.row, pos.col)
                rect = (sc * SQSIZE, sr * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, color, rect)

    # ---- Mode selector (in-UI human-vs-AI menu) ---------------------------

    def open_mode_menu(self):
        """Open the mode-selection menu. Pure state change — no rendering."""
        self.mode_menu = {
            'sides': list(self.SIDE_OPTIONS),
            'opponents': list(self.OPPONENT_OPTIONS),
        }

    def close_mode_menu(self):
        """Close the mode-selection menu and drop its click rects."""
        self.mode_menu = None
        self.mode_menu_rects = []

    def apply_mode_selection(self, side=None, opponent=None):
        """Apply a mode-menu selection. Each argument is optional — pass only
        `side` to switch the human's colour, only `opponent` to switch the
        computer opponent, or both. Raises ValueError on unknown keys. Does
        NOT auto-close the menu (live-settings model — the user closes via
        M / Esc / `close_mode_menu()`)."""
        if side is not None:
            valid = {opt['key'] for opt in self.SIDE_OPTIONS}
            if side not in valid:
                raise ValueError(
                    f"Unknown side: {side!r}; valid: {sorted(valid)}")
            self.user_side = side
        if opponent is not None:
            valid = {opt['key'] for opt in self.OPPONENT_OPTIONS}
            if opponent not in valid:
                raise ValueError(
                    f"Unknown opponent: {opponent!r}; valid: {sorted(valid)}")
            self.opponent = opponent
        self._refresh_ai()

    def _refresh_ai(self):
        """Recompute `mode`, `ai_color`, `ai_controller` from the current
        (user_side, opponent) selection. Called after every state change so
        the derived AI state stays in sync."""
        if self.opponent == 'human':
            self.mode = 'human_vs_human'
            self.ai_color = None
            self.ai_controller = None
            return
        from ai_controller import AIController
        self.mode = f'human_vs_{self.opponent}'
        self.ai_color = 'black' if self.user_side == 'white' else 'white'
        self.ai_controller = AIController(
            self.ai_color, player=self._make_ai_player(self.opponent))

    def _make_ai_player(self, opponent_key):
        """Construct the AI player for a given opponent key.

        - 'random'         → returns None, letting AIController default to
          its built-in RandomPlayer baseline.
        - 'easy' / 'medium' / 'hard' → loads the corresponding network
          checkpoint and wraps it in a NeuralPlayer (with the network's
          training depth as the difficulty dial — see _AI_CHECKPOINTS).
          The CPU device is used to keep the UI's network independent of
          any concurrently-running training on MPS/CUDA.

        Raises ValueError for unknown keys. For AI keys whose checkpoint
        is missing, returns None and falls back to RandomPlayer so the
        game stays playable; this should not normally happen because the
        mode menu grays out unavailable options and skips their clicks.
        """
        if opponent_key == 'random':
            return None  # AIController defaults to RandomPlayer
        if opponent_key in self._AI_CHECKPOINTS:
            ckpt = self._AI_CHECKPOINTS[opponent_key]
            if not os.path.exists(ckpt):
                return None  # Falls back to RandomPlayer in AIController.
            # Lazy import: keep torch out of the import graph for the
            # non-AI code paths.
            from network import ValueNetwork
            from trainer import NeuralPlayer
            network = ValueNetwork.load(ckpt, device='cpu')
            return NeuralPlayer(network, device='cpu', epsilon=0.0)
        raise ValueError(
            f"No player implementation for opponent {opponent_key!r}")

    def _ai_checkpoint_available(self, opponent_key):
        """True iff the opponent key is either a non-AI key or has its
        checkpoint file on disk. Used by show_mode_menu to gray out and
        deactivate options whose checkpoint does not yet exist."""
        if opponent_key not in self._AI_CHECKPOINTS:
            return True  # 'human', 'random' — always available
        return os.path.exists(self._AI_CHECKPOINTS[opponent_key])

    def is_any_menu_open(self):
        """True iff a UI selection menu is currently open. main.py uses this
        to gate input/interactions while a menu is up."""
        return (
            self.transform_menu is not None
            or self.promotion_menu is not None
            or self.mode_menu is not None
        )

    def show_mode_menu(self, surface):
        """Render the mode-selection menu, if open, and populate
        `mode_menu_rects` for click detection. No-op when closed.

        Renders two button rows: 'Your side' and 'Opponent'. The currently-
        selected button in each row is highlighted. Each entry pushed onto
        `mode_menu_rects` is a (pygame.Rect, group_key, option_key) tuple
        where group_key is 'side' or 'opponent'."""
        if self.mode_menu is None:
            return
        self.mode_menu_rects = []
        w, h = surface.get_size()
        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 170))
        surface.blit(backdrop, (0, 0))
        title_font = pygame.font.SysFont('arial', 26, bold=True)
        section_font = pygame.font.SysFont('arial', 20, bold=True)
        option_font = pygame.font.SysFont('arial', 20)
        title = title_font.render(
            'Select side and opponent  (M / Esc to close)', True,
            (255, 255, 255))
        surface.blit(title, title.get_rect(center=(w // 2, h // 6)))

        def render_section(label, opts, group_key, current_key, section_top,
                           orientation='horizontal'):
            """Render a section title and a row (or column) of buttons.

            orientation='horizontal' is used for the 'Your side' row (2
            options fit easily). orientation='vertical' stacks buttons one
            per line — used for 'Opponent' so the menu doesn't overflow
            the screen width as AI difficulty entries are added.

            Returns the y-coordinate just below the last button (so the
            caller can stack the next section).
            """
            section_label = section_font.render(label, True, (220, 220, 220))
            surface.blit(section_label, section_label.get_rect(
                center=(w // 2, section_top)))
            btn_h = 40
            gap = 10
            top_y = section_top + 34

            if orientation == 'horizontal':
                btn_w = min(180, int(w * 0.22))
                n = len(opts)
                row_w = n * btn_w + (n - 1) * gap
                row_left = (w - row_w) // 2
                def rect_for(i):
                    return pygame.Rect(
                        row_left + i * (btn_w + gap), top_y, btn_w, btn_h)
                end_y = top_y + btn_h
            else:  # 'vertical'
                btn_w = min(240, int(w * 0.32))
                col_left = (w - btn_w) // 2
                def rect_for(i):
                    return pygame.Rect(
                        col_left, top_y + i * (btn_h + gap), btn_w, btn_h)
                n = len(opts)
                end_y = top_y + n * btn_h + (n - 1) * gap

            for i, opt in enumerate(opts):
                rect = rect_for(i)
                active = (opt['key'] == current_key)
                # AI opponents whose checkpoint isn't on disk yet render
                # dimmer and are NOT added to mode_menu_rects, so clicks
                # on them are ignored.
                available = (group_key != 'opponent'
                             or self._ai_checkpoint_available(opt['key']))
                if available:
                    bg = (80, 140, 200) if active else (60, 60, 60)
                    border = (200, 200, 200)
                    text_color = (255, 255, 255)
                else:
                    # Unavailable AI options: dim background + dim text.
                    bg = (40, 40, 40)
                    border = (100, 100, 100)
                    text_color = (130, 130, 130)
                pygame.draw.rect(surface, bg, rect, border_radius=6)
                pygame.draw.rect(
                    surface, border, rect, width=2, border_radius=6)
                label_surf = option_font.render(
                    opt['label'], True, text_color)
                surface.blit(label_surf, label_surf.get_rect(center=rect.center))
                if available:
                    self.mode_menu_rects.append(
                        (rect, group_key, opt['key']))
            return end_y

        # 'Your side' stays horizontal (2 options fit naturally).
        # 'Opponent' renders vertically so the menu doesn't overflow the
        # screen width as more difficulty entries are added.
        bottom = render_section(
            'Your side', self.mode_menu['sides'], 'side',
            self.user_side, h // 4, orientation='horizontal')
        render_section(
            'Opponent', self.mode_menu['opponents'], 'opponent',
            self.opponent, bottom + 32, orientation='vertical')

    def show_transform_menu(self, surface):
        """Draw the vertical strip transformation menu."""
        if not self.transform_menu:
            return

        menu = self.transform_menu
        row, col = menu['row'], menu['col']
        options = menu['options']
        color = menu['piece_color']

        self.transform_menu_rects = []

        # Anchor the menu in SCREEN space so it extends visually downward
        # (or upward when near the bottom of the SCREEN, regardless of
        # where the queen is on the underlying board). Without this
        # translation, a flipped board would expand the menu in the
        # wrong screen direction.
        anchor_sr, anchor_sc = self.board_to_screen(row, col)

        # Determine direction: extend downward, or upward if near bottom
        if anchor_sr + len(options) < ROWS:
            direction = 1
            start_sr = anchor_sr
        else:
            direction = -1
            start_sr = anchor_sr

        for i, option in enumerate(options):
            menu_sr = start_sr + (i + 1) * direction if direction == 1 else start_sr - (len(options) - i)
            x = anchor_sc * SQSIZE
            y = menu_sr * SQSIZE

            # Background
            bg_color = (220, 220, 220) if i % 2 == 0 else (200, 200, 200)
            rect = pygame.Rect(x, y, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, bg_color, rect)
            pygame.draw.rect(surface, (100, 100, 100), rect, 2)  # border

            # Piece icon
            texture_name = f'{color}_{option}.png'
            texture_path = f'assets/images/imgs-80px/{texture_name}'
            img = pygame.image.load(texture_path)
            img_center = x + SQSIZE // 2, y + SQSIZE // 2
            img_rect = img.get_rect(center=img_center)
            surface.blit(img, img_rect)

            self.transform_menu_rects.append((rect, option))

    def show_promotion_menu(self, surface):
        """Draw the vertical strip promotion menu (same style as transformation menu)."""
        if not self.promotion_menu:
            return

        menu = self.promotion_menu
        row, col = menu['row'], menu['col']
        color = menu['pawn_color']
        options = self.board.get_promotion_options(color)

        self.promotion_menu_rects = []

        # Anchor in SCREEN space (see show_transform_menu for why).
        anchor_sr, anchor_sc = self.board_to_screen(row, col)

        # Extend downward or upward depending on screen position
        if anchor_sr + len(options) < ROWS:
            direction = 1
            start_sr = anchor_sr
        else:
            direction = -1
            start_sr = anchor_sr

        for i, option in enumerate(options):
            menu_sr = start_sr + (i + 1) * direction if direction == 1 else start_sr - (len(options) - i)
            x = anchor_sc * SQSIZE
            y = menu_sr * SQSIZE

            # Background
            bg_color = (220, 220, 220) if i % 2 == 0 else (200, 200, 200)
            rect = pygame.Rect(x, y, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, bg_color, rect)
            pygame.draw.rect(surface, (100, 100, 100), rect, 2)

            # Piece icon
            texture_path = f'assets/images/imgs-80px/{color}_{option}.png'
            img = pygame.image.load(texture_path)
            img_center = x + SQSIZE // 2, y + SQSIZE // 2
            img_rect = img.get_rect(center=img_center)
            surface.blit(img, img_rect)

            self.promotion_menu_rects.append((rect, option))

    def show_winner(self, surface):
        """Display winner announcement overlay."""
        if not self.winner:
            return
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        surface.blit(overlay, (0, 0))
        # Winner text
        font = pygame.font.SysFont('monospace', 64, bold=True)
        text = f"{self.winner.upper()} WINS"
        lbl = font.render(text, True, (255, 255, 255))
        lbl_rect = lbl.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        surface.blit(lbl, lbl_rect)

    def show_hover(self, surface):
        if self.hovered_sqr:
            # color
            color = (180, 180, 180)
            # rect (translated to screen position when flipped)
            sr, sc = self.board_to_screen(self.hovered_sqr.row, self.hovered_sqr.col)
            rect = (sc * SQSIZE, sr * SQSIZE, SQSIZE, SQSIZE)
            # blit
            pygame.draw.rect(surface, color, rect, width=3)

    # other methods

    # ---- Undo / redo / cancel mechanics -----------------------------------

    def _snapshot(self):
        """Capture the full game state as a dict suitable for restoration.

        The board is deep-copied so subsequent mutations to the live board
        don't leak into the snapshot. Game-level scalar fields are copied
        by value (Python strings/None — immutable).
        """
        return {
            'board': copy.deepcopy(self.board),
            'next_player': self.next_player,
            'winner': self.winner,
        }

    def _restore(self, snapshot):
        """Restore the game state from a snapshot produced by `_snapshot`.

        The live `self.board` object's identity is preserved — its internal
        attributes are mutated in place to match the snapshot. This is
        critical because external callers (notably `main.py`'s mainloop)
        hold local references to `self.board` and `self.dragger` at startup;
        if we replaced `self.board` with a new object, those references
        would become stale and the UI would render the new board while the
        click handlers operated on the old board.

        We also deep-copy the snapshot's board on each restore so the live
        state does not share array/piece references with the snapshot —
        otherwise post-restore live mutations would silently contaminate
        the snapshot in history, breaking subsequent undo cycles.

        Defensive: also clear the dragger so any stale piece reference it
        might hold (from a drag in progress before this restore) cannot
        leak into the post-restore state. In normal flow, undo/redo are
        already gated on `dragger.dragging is False` via
        `_in_intermediate_state`, so this is a belt-and-suspenders measure.
        """
        snap_board_independent = copy.deepcopy(snapshot['board'])
        self.board.__dict__.update(snap_board_independent.__dict__)
        self.next_player = snapshot['next_player']
        self.winner = snapshot['winner']
        if self.dragger is not None:
            self.dragger.undrag_piece()

    def _in_intermediate_state(self):
        """Return True if any in-between turn UI state is active.

        Undo / redo are disallowed at these moments to prevent capturing
        a snapshot that includes a partial action OR restoring while a
        live UI element holds a stale piece reference. Specifically:

        - knight leap awaiting capture/decline (`jump_capture_targets`),
        - open transformation menu (`transform_menu`),
        - open promotion menu (`promotion_menu`),
        - open mode-selector menu (`mode_menu`),
        - active drag (`dragger.dragging`) — the dragger holds a piece
          reference; restoring would orphan it (the piece would no longer
          exist on the post-restore board's squares array, but the
          dragger would still try to render and place it on release).
        """
        return (
            self.jump_capture_targets is not None
            or self.transform_menu is not None
            or self.promotion_menu is not None
            or self.mode_menu is not None
            or (self.dragger is not None and self.dragger.dragging)
        )

    def can_undo(self):
        """True iff there is at least one completed turn to undo and we
        are not in an in-between state. The bottom of the history stack
        is the game's initial state and is never undone past."""
        return len(self._history) > 1 and not self._in_intermediate_state()

    def can_redo(self):
        return len(self._redo_stack) > 0 and not self._in_intermediate_state()

    def undo(self):
        """Roll back to the previous USER turn.

        Standard behavior (human-vs-human): pops one snapshot off the history
        so the game returns to the state at the start of the current turn.

        Human-vs-AI extension: when an AI is active (`ai_controller is not
        None`), continue popping while `next_player` is the AI's color, so
        undo always lands on the user's PREVIOUS turn (rolling back both the
        AI's most recent move and the user's own most recent move in one
        keypress). Stops if no further snapshots are available — in that
        case the game returns to the earliest reachable state (which may be
        the initial position even when it's the AI's turn there, e.g. when
        the user plays black and the AI moves first).
        """
        if not self.can_undo():
            return False
        self._redo_stack.append(self._history.pop())
        self._restore(self._history[-1])
        # Skip over the AI's turn so undo lands on the user's previous turn.
        # Guard with `len(...)>1` (not `can_undo()`) — we already passed the
        # intermediate-state check; we just need at least one earlier state.
        if self.ai_controller is not None:
            while (self.next_player != self.user_side
                   and len(self._history) > 1):
                self._redo_stack.append(self._history.pop())
                self._restore(self._history[-1])
        return True

    def redo(self):
        """Re-apply a previously-undone turn, advancing to the next USER turn.

        Standard behavior: pops one state off the redo stack.

        Human-vs-AI extension: keeps redoing while `next_player` is the AI's
        color, so redo symmetrically lands on the user's NEXT turn (re-
        applying both the user's move and the AI's response in one keypress).
        """
        if not self.can_redo():
            return False
        state = self._redo_stack.pop()
        self._history.append(state)
        self._restore(state)
        if self.ai_controller is not None:
            while (self.next_player != self.user_side
                   and len(self._redo_stack) > 0):
                state = self._redo_stack.pop()
                self._history.append(state)
                self._restore(state)
        return True

    def cancel_jump_capture(self):
        """Abort an in-progress jump-capture second-click and restore the
        state to before the knight's leap. Used by Esc / right-click /
        out-of-target click in the UI. Returns True on success, False if
        there's no jump-capture state or no pre-leap snapshot to restore."""
        if self.jump_capture_targets is None:
            return False
        if self._pre_jump_capture_snapshot is None:
            return False
        self._restore(self._pre_jump_capture_snapshot)
        self._pre_jump_capture_snapshot = None
        self.jump_capture_targets = None
        self.jump_capture_landing = None
        self.jump_capture_piece = None
        self.jump_capture_origin = None
        return True

    # ---- Turn lifecycle ---------------------------------------------------

    def next_turn(self):
        self.next_player = 'white' if self.next_player == 'black' else 'black'
        self.board.turn_number += 1
        # v2 (freeze) manipulation: a piece manipulated on the previous opponent's
        # turn was frozen for the just-ended owner's turn. Now that the manipulator's
        # turn has begun (or whoever's turn it is), clear the freeze on the opponent's
        # pieces so they can move again next time.
        self.board.clear_moved_by_queen_for_opponent(self.next_player)
        # v2 knight: a knight that gained invulnerability on its owner's
        # turn N stayed uncapturable through opponent's turn N+1. At the
        # start of the owner's turn N+2, that invulnerability expires.
        # Clearing on `next_player` here does exactly that: when
        # next_player's turn begins, any invulnerability they had set two
        # turns ago is cleared now.
        self.board.clear_invulnerable_for_color(self.next_player)
        # Record board state for repetition rule
        self.board.record_state(self.next_player)
        # Check if the new current player has any legal moves/actions
        if not self.winner and not self.board.has_legal_moves(self.next_player):
            # Player with no legal moves loses
            self.winner = 'white' if self.next_player == 'black' else 'black'
        # Push the new post-turn state onto the undo history and clear the
        # redo stack — making a new turn after an undo invalidates any
        # previously-undone states (the timeline diverges).
        self._history.append(self._snapshot())
        self._redo_stack.clear()

    def set_hover(self, row, col):
        self.hovered_sqr = self.board.squares[row][col]

    def set_hover_screen(self, screen_row, screen_col):
        """Set the hovered square from SCREEN coordinates. Translates
        through the flip and stores the underlying board square, so the
        rest of the game logic (highlight rendering, move validation)
        always sees a board-space square reference."""
        r, c = self.screen_to_board(screen_row, screen_col)
        self.hovered_sqr = self.board.squares[r][c]

    def change_theme(self):
        self.config.change_theme()

    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()

    def reset(self):
        # `flipped` is a viewing preference (which side is at the bottom
        # of the screen), not part of the game state, so it must survive
        # a reset. Capture it before reinitializing, then restore.
        flipped = self.flipped
        self.__init__()
        self.flipped = flipped