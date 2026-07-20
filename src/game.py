import base64
import copy
import os
import pickle
import re
import shutil
import subprocess
import sys
import zlib

import pygame
from pygame import gfxdraw
from PIL import Image


# Serialization markers + version. Bump SAVE_VERSION when the pickled
# payload's shape changes in a way that breaks back-compat.
_SAVE_BEGIN = '___VARIANT_SAVE_V1_BEGIN___'      # legacy (read-only)
_SAVE_END = '___VARIANT_SAVE_V1_END___'          # legacy (read-only)
_SAVE_V2_BEGIN = '___VARIANT_SAVE_V2_BEGIN___'   # zlib + base64 pickle
_SAVE_V2_END = '___VARIANT_SAVE_V2_END___'       #  (fallback writer)
_SAVE_V3_BEGIN = '___VARIANT_SAVE_V3_BEGIN___'   # current: royal-notation
_SAVE_V3_END = '___VARIANT_SAVE_V3_END___'       #  movetext (replay-based)
_SAVE_VERSION = 1   # inner payload schema (unchanged between V1/V2
                    # containers — only the encoding wrapper differs)


# ---- Clipboard fallback chain --------------------------------------------
#
# Bug reported 2026-05-30: pyperclip isn't installed in this env and
# pygame.scrap is flaky on macOS, so the old chain (pyperclip ->
# pygame.scrap) always failed and the dialog showed
# "Copy failed (clipboard unavailable)". The fix inserts a
# platform-native CLI tool (pbcopy / xclip / xsel / clip) as a middle
# fallback. pbcopy ships at /usr/bin/pbcopy on every Mac.
#
# Helpers are split so each is independently testable. Tests
# monkeypatch them per-layer.

_CLI_COPY_COMMANDS = {
    # platform -> ordered list of (binary_name, full_argv).
    'darwin':  [('pbcopy', ['pbcopy'])],
    'linux':   [('xclip', ['xclip', '-selection', 'clipboard']),
                ('xsel',  ['xsel',  '--clipboard', '--input'])],
    'linux2':  [('xclip', ['xclip', '-selection', 'clipboard']),
                ('xsel',  ['xsel',  '--clipboard', '--input'])],
    'win32':   [('clip',  ['clip'])],
}
_CLI_READ_COMMANDS = {
    'darwin': [('pbpaste', ['pbpaste'])],
    'linux':  [('xclip',   ['xclip', '-selection', 'clipboard', '-o']),
               ('xsel',    ['xsel',  '--clipboard', '--output'])],
    'linux2': [('xclip',   ['xclip', '-selection', 'clipboard', '-o']),
               ('xsel',    ['xsel',  '--clipboard', '--output'])],
    # Windows reads via PowerShell — uncommon; left here for future use.
    'win32':  [('powershell',
                ['powershell', '-NoProfile', '-Command', 'Get-Clipboard'])],
}


def _copy_via_pyperclip(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def _copy_via_cli_tool(text, platform=None):
    """Try a platform-native clipboard CLI tool (pbcopy / xclip /
    xsel / clip). Returns True on success.

    `platform` overrides sys.platform for testing. Linux supports
    both 'linux' and 'linux2' platform strings; older platforms like
    'linux2' (Python 2 era) map to the same commands.
    """
    if platform is None:
        platform = sys.platform
    candidates = _CLI_COPY_COMMANDS.get(platform)
    if not candidates:
        # Older linux2 / unknown — try linux family.
        if platform.startswith('linux'):
            candidates = _CLI_COPY_COMMANDS['linux']
        else:
            return False
    for binary, argv in candidates:
        if shutil.which(binary) is None:
            continue
        try:
            result = subprocess.run(
                argv, input=text, text=True, timeout=2.0, check=False)
            if result.returncode == 0:
                return True
        except Exception:
            continue
    return False


def _copy_via_pygame_scrap(text):
    """Last-resort: pygame.scrap (flaky on macOS, requires a real
    display)."""
    try:
        pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode('utf-8'))
        return True
    except Exception:
        return False


def _default_copy_to_clipboard(text):
    """Orchestrator. Returns True if ANY layer succeeded.

    Chain: pyperclip -> platform CLI tool -> pygame.scrap.
    """
    if _copy_via_pyperclip(text):
        return True
    if _copy_via_cli_tool(text):
        return True
    if _copy_via_pygame_scrap(text):
        return True
    return False


def _read_via_pyperclip():
    try:
        import pyperclip
        data = pyperclip.paste()
        return data if data else None
    except Exception:
        return None


def _read_via_cli_tool(platform=None):
    if platform is None:
        platform = sys.platform
    candidates = _CLI_READ_COMMANDS.get(platform)
    if not candidates:
        if platform.startswith('linux'):
            candidates = _CLI_READ_COMMANDS['linux']
        else:
            return None
    for binary, argv in candidates:
        if shutil.which(binary) is None:
            continue
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=2.0,
                check=False)
            if result.returncode == 0:
                return result.stdout if result.stdout else None
        except Exception:
            continue
    return None


def _read_via_pygame_scrap():
    try:
        pygame.scrap.init()
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
        if raw is None:
            return None
        return raw.decode('utf-8', errors='replace')
    except Exception:
        return None


def _default_read_clipboard():
    """Orchestrator. Returns the clipboard text or None.

    Chain: pyperclip -> platform CLI tool -> pygame.scrap.
    """
    result = _read_via_pyperclip()
    if result is not None:
        return result
    result = _read_via_cli_tool()
    if result is not None:
        return result
    result = _read_via_pygame_scrap()
    if result is not None:
        return result
    return None

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

    # Mode selector — per-side player choice. The in-UI menu renders the
    # SAME catalog twice (one column per side), and EACH side can
    # independently be set to any player type:
    #
    #     human  | random | easy | medium | hard
    #
    # Modes (derived):
    #     both 'human'              -> HvH (human_vs_human)
    #     exactly one 'human'       -> HvAI (human_vs_ai)
    #     neither 'human'           -> CvC (computer_vs_computer)
    #
    # Adding new player types: append here and add a matching branch in
    # _make_ai_player. Adding a new SIDE is not a meaningful operation in
    # 2-colour chess — the catalog is per-side, not per-slot.
    PLAYER_OPTIONS = [
        {'key': 'human',  'label': 'Human'},
        {'key': 'random', 'label': 'Random'},
        {'key': 'easy',   'label': 'AI Easy'},
        {'key': 'medium', 'label': 'AI Medium'},
        {'key': 'hard',   'label': 'AI Hard'},
    ]

    # AI difficulty → target training iteration. Difficulty is realised by
    # training depth: an under-trained network plays near-randomly ("easy"),
    # a fully-trained network is "hard".
    #
    # Resolution modes (see _resolve_ai_checkpoint):
    #   'capped' — use the checkpoint at `target` if it exists, else the
    #     HIGHEST existing checkpoint at or below `target`. So Easy
    #     automatically tracks the strongest available model up to its cap
    #     and stops there (no manual bump needed as training progresses).
    #   'exact'  — only use the exact `target` checkpoint; the option stays
    #     unavailable (grayed out) until that checkpoint exists. Used for
    #     Medium/Hard so they don't silently fall back to a weak model.
    # 2026-06-15: switched from variant_freeze_v3 to variant_freeze_v4.
    # v3 (through iter 0500) was trained on the PRE-remake knight-
    # invulnerability rule; v4 is the 100-iteration fine-tune of
    # v3-iter-0500 on the remade rule ("leap between friend and foe",
    # PR #116) and is the correct model for current gameplay. The
    # capped difficulty resolver below picks the highest existing
    # checkpoint <= target, so all difficulties resolve to v4's
    # latest (iter 0100) until further training lands.
    _CHECKPOINT_DIR = os.path.join(_REPO_ROOT, 'models/variant_freeze_v4')
    _AI_DIFFICULTY = {
        # 'capped' = use the strongest existing checkpoint with iter <= target
        # (auto-tracks training progress up to the cap). 'exact' = must match
        # the exact target iteration; otherwise the option is disabled in
        # the mode menu.
        #
        # 2026-06-02 bump: at iter 200+ the network is STILL too
        # easy in user testing. Bumping Easy + Medium to 500 (same
        # as Hard) so all three auto-track the latest available
        # checkpoint. This effectively collapses the three modes
        # into one until a different difficulty knob (action-
        # selection temperature, explicit blunder rate) is added —
        # iteration depth alone has stopped being a meaningful
        # difficulty discriminator at this training depth.
        'easy':   {'target': 500, 'mode': 'capped'},
        'medium': {'target': 500, 'mode': 'capped'},
        'hard':   {'target': 500, 'mode': 'capped'},
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
        # Mode-selector menu state (Goal 2 + CvC extension). Opened via M
        # in main.py. The menu lets the user pick the player type for EACH
        # side independently; each click applies that one side and leaves
        # the menu open (live-settings model) so the user can also change
        # the other side. The dict shape is {'white': [opts], 'black':
        # [opts]} — render-friendly. Rect tags are (rect, 'white'|'black',
        # player_key).
        self.mode_menu = None
        self.mode_menu_rects = []
        # Reset-game confirmation. True iff the user pressed 'R' and we are
        # waiting for them to confirm (Y / Enter) or cancel (N / Esc). The
        # overlay is rendered by show_reset_confirm; main.py treats it like
        # any other open menu (no interactions while up).
        self.reset_confirm_pending = False
        # Pause / PGN-FEN dialog. Opened via 'P', or implicitly when
        # undo/redo is pressed during CvC autoplay (the user-spec'd
        # "paused screen for undo/redo that doesn't interfere with CvC
        # playing"). The same dialog renders a serialized game string
        # with Copy / Load buttons (the user's "PGN/FEN + save/load"
        # ask). Mutually exclusive with mode_menu: opening either
        # closes the other (both are paused-game states; only one is
        # on screen at a time).
        self.pgn_dialog_open = False
        # Click rects for the dialog's buttons, populated on each
        # render and consumed by main.py's MOUSEBUTTONDOWN dispatch.
        # Three buttons: Copy (full save), Copy FEN (one-line
        # position summary), Load (paste a save from clipboard).
        self.pgn_dialog_copy_rect = None
        self.pgn_dialog_copy_fen_rect = None
        self.pgn_dialog_load_rect = None
        # Optional status message shown in the dialog (e.g. "Copied!"
        # after a successful Copy click). Cleared when the dialog is
        # closed.
        self.pgn_dialog_status = None
        # Transient 'Copied!' button-label feedback. Set when a Copy
        # button is clicked; cleared by the renderer reading via
        # copy_recent_button(now_ms) returning None after the window
        # expires. _copied_button is 'save' or 'fen'.
        self._copied_at_ms = None
        self._copied_button = None
        # Per-side player choice — the primary mode state. Both default to
        # 'human' (HvH). `user_side`, `opponent`, `ai_color`,
        # `ai_controller` are derived @property values kept for back-compat
        # with the pre-CvC API.
        self.white_player = 'human'
        self.black_player = 'human'
        # Legacy perspective. The original two-slot menu had an explicit
        # `user_side` that was kept even in HvH (where there's no unique
        # human side); some callers/tests still set `side=` via
        # apply_mode_selection. Stored here so the `user_side` property
        # can return a stable value across HvH calls. Defaults to 'white'.
        self._perspective_side = 'white'
        # Derived from (white_player, black_player) by `_refresh_ai`.
        self.mode = 'human_vs_human'      # string for display/logging
        self.ai_controllers = {'white': None, 'black': None}
        self.winner = None                # 'white', 'black', or None
        # Record initial board state for repetition rule
        self.board.record_state(self.next_player)
        # Undo/redo history. `_history` is a stack of full state snapshots
        # (one per turn boundary, plus the initial state at the bottom).
        # `_redo_stack` holds states that were undone — populated by undo,
        # consumed by redo, cleared whenever a new turn happens.
        # `_pre_jump_capture_snapshot` is set when entering the second-click
        # state of a knight jump-capture, so cancel can restore the state
        # to before the knight's leap. `_pre_promotion_snapshot` is the
        # same mechanism for the promotion menu: the pawn's spatial move
        # is already applied when the menu opens, so canceling the
        # promotion must revert the whole move (the rulebook mandates
        # that a pawn on the last rank promote — it may never stay
        # there unpromoted).
        self._history = []
        self._redo_stack = []
        self._pre_jump_capture_snapshot = None
        self._pre_promotion_snapshot = None
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

        # Corrected user spec 2026-07-20: after a transformation
        # COMPLETES, the highlight moves to the queen's square
        # (`last_action`, set only by the real-execution callers of
        # transform_queen via record_highlight=True — never by the
        # menu-open simulation). While an attempt is merely in
        # progress, or after a cancel, last_action is None and the
        # previous spatial move stays highlighted. The next spatial
        # move clears last_action (Board.move), handing the highlight
        # back to last_move.
        if self.board.last_action:
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
        """Open the mode-selection menu. Pure state change — no rendering.

        Menu shape is {'white': [PLAYER_OPTIONS], 'black': [PLAYER_OPTIONS]}.
        Each side renders the same catalog; selecting a button on one side
        only updates that side.

        Unified paused-state rule: opening the mode menu closes ANY
        other paused state (pgn dialog OR reset confirm) — they are
        mutually exclusive. Opening one is the implicit "no" / "switch"
        for the others. (User spec: "if something doesn't interfere ...
        it should be enabled"; for actions that DO interfere — opening
        a competing paused screen — the cleanest resolution is to
        cancel the previous one.)
        """
        if self.pgn_dialog_open:
            self.close_pgn_dialog()
        self.reset_confirm_pending = False
        self.mode_menu = {
            'white': list(self.PLAYER_OPTIONS),
            'black': list(self.PLAYER_OPTIONS),
        }

    def close_mode_menu(self):
        """Close the mode-selection menu and drop its click rects."""
        self.mode_menu = None
        self.mode_menu_rects = []

    # ---- PGN / FEN pause-and-save dialog -------------------------------

    def open_pgn_dialog(self):
        """Open the paused-game save/load dialog (the user's PGN/FEN
        screen + pause-screen, unified per spec). Idempotent. Closes
        any other paused state (mode menu OR reset confirm) for the
        unified mutual-exclusion rule — see open_mode_menu's docstring."""
        if self.mode_menu is not None:
            self.close_mode_menu()
        self.reset_confirm_pending = False
        self.pgn_dialog_open = True
        self.pgn_dialog_status = None  # fresh dialog: no stale "Copied!" etc.

    def close_pgn_dialog(self):
        """Close the dialog and drop its click rects + status message."""
        self.pgn_dialog_open = False
        self.pgn_dialog_copy_rect = None
        self.pgn_dialog_copy_fen_rect = None
        self.pgn_dialog_load_rect = None
        self.pgn_dialog_status = None

    # Constants controlling the side-panel layout. PANEL_WIDTH_FRAC is
    # the fraction of the surface width devoted to the panel; the rest
    # of the surface (the board) stays untouched while paused so the
    # user can see the position. (Original design covered the whole
    # surface with a near-opaque backdrop — see user feedback.)
    _PGN_PANEL_WIDTH_FRAC = 0.40
    # Max number of body lines shown as a preview; the FULL save is
    # always available via the Copy button regardless of this cap.
    _PGN_PREVIEW_BODY_LINES = 4

    def _pgn_dialog_preview_lines(self):
        """Return the truncated list of preview lines for the dialog
        body. Caps at _PGN_PREVIEW_BODY_LINES + 1 (the +1 is an
        ellipsis marker when truncation actually occurred).

        Lines are short enough to fit the panel without further wrapping
        in the typical 800-px-wide window. Wrapping under unusual sizes
        is handled visually by the renderer trimming each line."""
        text = self.serialize_to_text()
        # Keep first 3 header lines verbatim; then peek at the first
        # encoded line. The body is the base64 payload — a single very
        # long line. We show its prefix only.
        all_lines = text.split('\n')
        cap = self._PGN_PREVIEW_BODY_LINES
        if len(all_lines) <= cap:
            return list(all_lines)
        out = all_lines[:cap]
        # Replace the last visible line with a brief truncation marker
        # so the user knows there's more.
        out.append(
            f'... ({len(all_lines) - cap} more lines truncated — '
            f'use Copy)')
        return out

    # Panel dimensions for the centered dialog. The semi-transparent
    # panel sits in the middle of the surface with margins on all
    # sides so the board is visible around AND through it.
    _PGN_PANEL_WIDTH_FRAC = 0.50
    _PGN_PANEL_HEIGHT_FRAC = 0.65
    # Alpha for the semi-transparent panel background — high enough
    # to read the text against, low enough that the board remains
    # visible through the panel.
    _PGN_PANEL_ALPHA = 210

    def show_pgn_dialog(self, surface):
        """Render the paused/PGN-FEN dialog if open. No-op when closed.

        Layout: a CENTERED panel, semi-transparent so the board is
        visible THROUGH the panel (not just around it). No
        full-surface backdrop. All four edges of the surface remain
        untouched."""
        if not self.pgn_dialog_open:
            self.pgn_dialog_copy_rect = None
            self.pgn_dialog_copy_fen_rect = None
            self.pgn_dialog_load_rect = None
            return
        w, h = surface.get_size()
        panel_w = max(360, int(w * self._PGN_PANEL_WIDTH_FRAC))
        panel_h = max(320, int(h * self._PGN_PANEL_HEIGHT_FRAC))
        panel_left = (w - panel_w) // 2
        panel_top = (h - panel_h) // 2
        panel = pygame.Rect(panel_left, panel_top, panel_w, panel_h)

        # Semi-transparent panel: blit a SRCALPHA surface so the
        # underlying board pixels show through the alpha.
        panel_surf = pygame.Surface(
            (panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((28, 28, 32, self._PGN_PANEL_ALPHA))
        surface.blit(panel_surf, (panel_left, panel_top))
        pygame.draw.rect(
            surface, (180, 180, 180), panel, width=2)

        title_font = pygame.font.SysFont('arial', 20, bold=True)
        header_font = pygame.font.SysFont('arial', 14, bold=True)
        body_font = pygame.font.SysFont('couriernew', 11)
        button_font = pygame.font.SysFont('arial', 14, bold=True)
        hint_font = pygame.font.SysFont('arial', 12)

        pad_x = 16
        y = panel.top + 12

        title = title_font.render(
            'Pause / Save / Load', True, (255, 255, 255))
        surface.blit(title, (panel.left + pad_x, y))
        y += 30

        # Header summary.
        turn_label = (f'Turn {self.board.turn_number}  '
                      f'({self.next_player} to move)')
        header_lines = [
            f'Mode: {self.mode}',
            f'White: {self.white_player}   Black: {self.black_player}',
            turn_label,
        ]
        if self.winner:
            header_lines.append(f'Winner: {self.winner}')
        for line in header_lines:
            surf = header_font.render(line, True, (230, 230, 230))
            surface.blit(surf, (panel.left + pad_x, y))
            y += 18
        y += 6

        # FEN section.
        fen_label = header_font.render(
            'FEN (position summary):', True, (200, 220, 200))
        surface.blit(fen_label, (panel.left + pad_x, y))
        y += 18
        fen_text = self.to_fen()
        char_w = max(6, body_font.size('M')[0])
        fen_max_chars = max(
            10, (panel.width - pad_x * 2 - 8) // char_w)
        if len(fen_text) > fen_max_chars:
            fen_display = fen_text[:fen_max_chars - 3] + '...'
        else:
            fen_display = fen_text
        surf = body_font.render(fen_display, True, (200, 220, 200))
        surface.blit(surf, (panel.left + pad_x, y))
        y += body_font.get_height() + 12

        # Buttons row: three buttons stacked, each full-width.
        btn_h = 30
        btn_w = panel.width - pad_x * 2
        self.pgn_dialog_copy_rect = pygame.Rect(
            panel.left + pad_x, y, btn_w, btn_h)
        y += btn_h + 6
        self.pgn_dialog_copy_fen_rect = pygame.Rect(
            panel.left + pad_x, y, btn_w, btn_h)
        y += btn_h + 6
        self.pgn_dialog_load_rect = pygame.Rect(
            panel.left + pad_x, y, btn_w, btn_h)
        y += btn_h + 8
        # Transient 'Copied!' label state. After click, the button's
        # label flips to 'Copied!' for _COPIED_FEEDBACK_MS, then
        # reverts. copy_recent_button(None) reads current time
        # internally; in tests, callers pass an explicit now_ms.
        recently_copied = self.copy_recent_button()
        copy_label = ('Copied!' if recently_copied == 'save'
                      else 'Copy Save (full game)')
        copy_fen_label = ('Copied!' if recently_copied == 'fen'
                          else 'Copy FEN (position)')
        for rect, label in (
                (self.pgn_dialog_copy_rect, copy_label),
                (self.pgn_dialog_copy_fen_rect, copy_fen_label),
                (self.pgn_dialog_load_rect, 'Load from clipboard')):
            pygame.draw.rect(surface, (60, 100, 160), rect, border_radius=5)
            pygame.draw.rect(
                surface, (200, 200, 200), rect, width=2, border_radius=5)
            text_surf = button_font.render(label, True, (255, 255, 255))
            surface.blit(text_surf, text_surf.get_rect(center=rect.center))

        # Status line (e.g. "Loaded save (full game).").
        if self.pgn_dialog_status:
            status = hint_font.render(
                self.pgn_dialog_status, True, (180, 220, 180))
            surface.blit(status, (panel.left + pad_x, y))
            y += 18

        # Save preview — short, truncated.
        save_label = header_font.render(
            'Save preview:', True, (200, 200, 200))
        surface.blit(save_label, (panel.left + pad_x, y))
        y += 18
        preview = self._pgn_dialog_preview_lines()
        line_h = body_font.get_height() + 2
        max_chars = max(
            10, (panel.width - pad_x * 2 - 8) // char_w)
        for ln in preview:
            if y + line_h > panel.bottom - 28:
                break
            display = ln if len(ln) <= max_chars else (
                ln[:max_chars - 3] + '...')
            surf = body_font.render(display, True, (200, 220, 200))
            surface.blit(surf, (panel.left + pad_x, y))
            y += line_h

        # Hint footer pinned near the bottom of the panel.
        hint = hint_font.render(
            'U/Y undo/redo.  M mode menu.  T/F view prefs (always).',
            True, (160, 160, 160))
        surface.blit(hint, (panel.left + pad_x, panel.bottom - 22))

    # ---- FEN export ------------------------------------------------------

    # Single-char codes for the placement field. v2 doesn't standardise
    # codes for transformed-queen forms etc.; we use the natural single
    # letter for the piece's *current* runtime class. Royal vs promoted
    # queens both render as Q/q — the distinction is preserved in the
    # full save, not in the one-line FEN.
    _FEN_PIECE_CODES = {
        'Pawn':    'P',
        'King':    'K',
        'Queen':   'Q',
        'Rook':    'R',
        'Bishop':  'B',
        'Knight':  'N',
        'Boulder': 'O',
    }

    def to_fen(self):
        """Return a one-line FEN-style position summary.

        Format:
            <8 ranks of placement> <turn_color> turn:<n> boulder:<sq>:<cd>

        Where:
          - Placement: rank 8 first, rank 1 last; files a..h within a
            rank. Empty squares collapsed to digits (1..8). v2 pieces
            use standard single letters K/Q/R/B/N/P (uppercase = white,
            lowercase = black) plus 'O' for the neutral boulder.
          - turn_color: 'w' or 'b'.
          - turn: integer turn number (board.turn_number).
          - boulder: square ('a1'..'h8') OR 'int' for the central
            intersection (initial position), suffixed with the
            cooldown integer ticks remaining.

        Per-piece flags (manipulation freeze, knight invuln, queen
        transformation state), the no-return memory, repetition history
        and tiny-endgame counters are NOT encoded in the FEN — the
        full save (serialize_to_text) is the source of truth for
        perfect replay. The FEN is a compact human-shareable summary.
        """
        rank_strings = []
        for rank in range(8, 0, -1):
            # board's internal rows: row 0 == rank 8, row 7 == rank 1
            row = 8 - rank
            run = []
            empties = 0
            for col in range(8):
                sq = self.board.squares[row][col]
                if sq.has_piece():
                    if empties:
                        run.append(str(empties))
                        empties = 0
                    piece = sq.piece
                    code = self._FEN_PIECE_CODES.get(
                        type(piece).__name__, '?')
                    if piece.color == 'black':
                        code = code.lower()
                    run.append(code)
                else:
                    empties += 1
            if empties:
                run.append(str(empties))
            rank_strings.append(''.join(run))
        placement = '/'.join(rank_strings)

        turn_color = 'w' if self.next_player == 'white' else 'b'

        # Boulder annotation.
        boulder = self.board.boulder
        if boulder is not None and boulder.on_intersection:
            b_sq = 'int'
            b_cd = boulder.cooldown
        else:
            # Boulder lives on the board as a piece; scan for it.
            b_sq = '-'
            b_cd = 0
            found_boulder = None
            for r in range(8):
                for c in range(8):
                    p = self.board.squares[r][c].piece
                    if p is not None and type(p).__name__ == 'Boulder':
                        b_sq = f'{chr(ord("a") + c)}{8 - r}'
                        b_cd = getattr(p, 'cooldown', 0)
                        found_boulder = p
                        break
                if found_boulder is not None:
                    break

        return (
            f'{placement} {turn_color} '
            f'turn:{self.board.turn_number} '
            f'boulder:{b_sq}:{b_cd}'
        )

    def copy_fen_to_clipboard_action(self):
        """Compute the FEN and push it to the clipboard. Returns True
        on success. Updates pgn_dialog_status + records the transient
        'Copied!' button-label state."""
        text = self.to_fen()
        ok = Game._copy_to_clipboard(text)
        if ok:
            self.pgn_dialog_status = 'FEN copied to clipboard.'
            self._copied_at_ms = Game._now_ms()
            self._copied_button = 'fen'
        else:
            self.pgn_dialog_status = (
                'Copy FEN failed (clipboard unavailable).')
        return ok

    # ---- FEN load --------------------------------------------------------

    _FEN_CODE_TO_PIECE = {
        'P': ('Pawn',    'white'),
        'p': ('Pawn',    'black'),
        'K': ('King',    'white'),
        'k': ('King',    'black'),
        'Q': ('Queen',   'white'),
        'q': ('Queen',   'black'),
        'R': ('Rook',    'white'),
        'r': ('Rook',    'black'),
        'B': ('Bishop',  'white'),
        'b': ('Bishop',  'black'),
        'N': ('Knight',  'white'),
        'n': ('Knight',  'black'),
        'O': ('Boulder', 'none'),
    }

    def load_from_fen(self, text):
        """Parse `text` as a FEN-style position summary and replace
        this game's state with a fresh game at the encoded position.

        FEN is POSITION-ONLY: undo history, per-piece flags
        (manipulation freeze, knight invuln, queen transformation),
        repetition state-history counts, and tiny-endgame distance
        counts are NOT in the FEN and are RESET on load. For perfect
        replay use save/load (serialize_to_text / load_from_text)
        instead.

        Returns True on success, False on any parse error (game state
        is NOT mutated on failure).
        """
        try:
            new_board, next_player, turn_number = self._parse_fen(text)
        except Exception:
            return False
        # In-place mutation: preserve external references to self.board.
        self.board.__dict__.update(new_board.__dict__)
        self.next_player = next_player
        self.board.turn_number = turn_number
        self.winner = None
        # UI state reset before snapshot so the snapshot is clean.
        self.pgn_dialog_open = False
        self.pgn_dialog_copy_rect = None
        self.pgn_dialog_copy_fen_rect = None
        self.pgn_dialog_load_rect = None
        self.pgn_dialog_status = None
        self.mode_menu = None
        self.mode_menu_rects = []
        self.reset_confirm_pending = False
        if self.dragger is not None:
            self.dragger.dragging = False
            self.dragger.piece = None
        # Re-record the initial state for the repetition rule (the
        # state_history was cleared by the board reconstruction).
        self.board.state_history = {}
        self.board.record_state(self.next_player)
        # History is reset — the loaded position is the new origin.
        self._history = [self._snapshot()]
        self._redo_stack = []
        # Activate tiny endgame if the loaded position qualifies.
        if self.board.is_tiny_endgame():
            self.board.init_tiny_endgame()
        self._refresh_ai()
        return True

    @classmethod
    def _parse_fen(cls, text):
        """Parse a FEN-style string. Returns (Board, next_player,
        turn_number). Raises on any structural problem.

        Format mirrors to_fen():
            <8 ranks of placement> <w|b> [turn:N] [boulder:<sq>:<cd>]
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError('empty FEN')
        parts = text.split()
        if len(parts) < 2:
            raise ValueError('FEN must have at least placement and turn')
        placement = parts[0]
        turn = parts[1]
        if turn not in ('w', 'b'):
            raise ValueError(f"turn field must be 'w' or 'b'; got {turn!r}")
        ranks = placement.split('/')
        if len(ranks) != 8:
            raise ValueError(
                f"placement must have 8 ranks; got {len(ranks)}")
        new_board = Board(knight_mode=Board.KNIGHT_MODE_V2)
        # Clear out the standard starting position; we'll overwrite.
        for r in range(8):
            for c in range(8):
                new_board.squares[r][c].piece = None
        new_board.boulder = None

        from piece import (Pawn, King, Queen, Rook, Bishop, Knight,
                           Boulder)
        cls_map = {
            'Pawn': Pawn, 'King': King, 'Queen': Queen, 'Rook': Rook,
            'Bishop': Bishop, 'Knight': Knight, 'Boulder': Boulder,
        }
        for rank_idx, rank_str in enumerate(ranks):
            # rank_idx 0 = rank 8 (top of board, row 0 internally).
            row = rank_idx
            col = 0
            for ch in rank_str:
                if ch.isdigit():
                    col += int(ch)
                    continue
                if ch not in cls._FEN_CODE_TO_PIECE:
                    raise ValueError(
                        f"unknown FEN piece char {ch!r} in rank "
                        f"{rank_idx + 1}")
                if col >= 8:
                    raise ValueError(
                        f"rank {rank_idx + 1} overflows file h "
                        f"({rank_str!r})")
                piece_name, color = cls._FEN_CODE_TO_PIECE[ch]
                piece_cls = cls_map[piece_name]
                if piece_name == 'Boulder':
                    piece = piece_cls()
                    piece.on_intersection = False
                elif piece_name == 'Queen':
                    # FEN can't distinguish royal vs promoted queens.
                    # Heuristic: rulebook starting squares mark the
                    # royal queen; everywhere else is treated as a
                    # promoted queen. b1 (row=7, col=1) is white's
                    # royal start; g8 (row=0, col=6) is black's.
                    is_royal = (
                        (color == 'white' and row == 7 and col == 1)
                        or (color == 'black' and row == 0 and col == 6))
                    piece = piece_cls(color, is_royal=is_royal)
                else:
                    piece = piece_cls(color)
                new_board.squares[row][col].piece = piece
                col += 1
            if col != 8:
                raise ValueError(
                    f"rank {rank_idx + 1} did not fill 8 files: "
                    f"{rank_str!r} (got {col})")

        # Extras: turn:<n> and boulder:<sq>:<cd>.
        turn_number = 0
        boulder_sq = None
        boulder_cd = 0
        for ext in parts[2:]:
            if ext.startswith('turn:'):
                try:
                    turn_number = int(ext.split(':', 1)[1])
                except ValueError:
                    raise ValueError(f"bad turn:N extra {ext!r}")
            elif ext.startswith('boulder:'):
                sub = ext.split(':')
                if len(sub) >= 3:
                    boulder_sq = sub[1]
                    try:
                        boulder_cd = int(sub[2])
                    except ValueError:
                        raise ValueError(
                            f"bad boulder cooldown {sub[2]!r}")
        if boulder_sq == 'int':
            b = Boulder()
            b.cooldown = boulder_cd
            b.on_intersection = True
            b.first_move = True
            new_board.boulder = b
        elif boulder_sq and boulder_sq != '-':
            # Boulder already placed via the 'O' code in the placement
            # field; copy across the cooldown.
            for r in range(8):
                for c in range(8):
                    p = new_board.squares[r][c].piece
                    if p is not None and type(p).__name__ == 'Boulder':
                        p.cooldown = boulder_cd
                        p.on_intersection = False
                        p.first_move = False
                        break
        next_player = 'white' if turn == 'w' else 'black'
        return new_board, next_player, turn_number

    # ---- centralised KEYDOWN dispatch ----------------------------------

    def handle_keydown(self, key):
        """Public wrapper: dispatch the key + report whether a view
        pref (theme / flip) changed as a side-effect. The view_changed
        flag is consumed by main.py's CvC autoplay-wait loop so it
        can re-render immediately instead of waiting the full 600 ms
        before the next frame (the user reported T / F being laggy
        in CvC). All other dispatch logic lives in
        _handle_keydown_impl."""
        _pre_theme = self.config.idx
        _pre_flipped = self.flipped
        result = self._handle_keydown_impl(key)
        result['view_changed'] = (
            self.config.idx != _pre_theme
            or self.flipped != _pre_flipped)
        return result

    def _handle_keydown_impl(self, key):
        """Inner KEYDOWN dispatch. Returns a dict:

            {
              'consumed':       True if the key matched a handler,
              'reset_happened': True if Game.reset() ran (main.py must
                                refresh its local board/dragger refs),
            }

        This is the single source of truth for the game's key bindings
        — what was previously ~80 lines of nested if/else in main.py.
        Centralising it makes the table testable and removes the
        duplication between the reset-confirm-active branch and the
        normal branch (T / F / reset-toggle were duplicated).

        Unified principle (from user spec):
          - VIEW PREFS (T, F): always work, never affect other state.
          - ACTION KEYS (U, Y) that don't conflict with the current
            state: work everywhere.  Mode menu doesn't conflict with
            undo/redo (it just changes future player slots), so they
            work there too.
          - PAUSED-SCREEN TOGGLES (M, P, R): each opens its own
            paused state. Opening one auto-CANCELS the others (only
            one paused state on screen at a time).
          - reset_confirm_pending intercept (narrow): Y/Enter = yes,
            N = no, R = toggle off. Esc cancels via the Esc cascade.
            Everything else (T, F, U, M, P, ...) falls through to
            normal dispatch — opening M or P will then implicitly
            cancel the reset confirm via the unified mutual-exclusion
            rule in open_mode_menu / open_pgn_dialog.
          - jump_capture_targets active → Esc cancels the jump.

        Sounds and any post-key animations are caller responsibilities
        — this method only mutates Game state and returns the result
        flags.
        """
        # Capture view-pref state BEFORE dispatch so we can detect
        # changes after — used to set `view_changed` in the result,
        # which the autoplay wait loop in main.py reads to abort its
        # 600 ms pause and re-render immediately on T / F press.
        _pre_theme = self.config.idx
        _pre_flipped = self.flipped
        result = {
            'consumed': False, 'reset_happened': False,
            'view_changed': False,
        }

        # ------ reset-confirm intercept (narrow: only Y / N / R) -------
        # Y/Enter and N are exclusively reset-confirm answers while the
        # confirm is pending. Per the 2026-05-30 evening user feedback,
        # 'Y' is NO LONGER a confirm key — it collided with Y-as-redo,
        # making redo unusable while the confirm was open. ONLY Enter
        # confirms now; Y always means redo. R toggles the confirm off
        # (per spec). All other keys (T/F/U/Y/M/P/...) fall through to
        # the unified dispatch below; T/F still work as view prefs,
        # U undoes / Y redoes, M/P open their screens which
        # auto-cancel the reset.
        if self.reset_confirm_pending:
            if key == pygame.K_RETURN:
                self.reset_confirm_pending = False
                self.reset()
                result['consumed'] = True
                result['reset_happened'] = True
                return result
            if key == pygame.K_n:
                self.reset_confirm_pending = False
                result['consumed'] = True
                return result
            if key == pygame.K_r:
                self.reset_confirm_pending = False
                result['consumed'] = True
                return result
            # All other keys: FALL THROUGH to normal dispatch.

        # ------ normal dispatch (single table; works in every state) ---
        if key == pygame.K_ESCAPE:
            self._handle_escape()
            result['consumed'] = True
            return result
        if key == pygame.K_m:
            self._handle_mode_menu_toggle()
            result['consumed'] = True
            return result
        if key == pygame.K_p:
            self._handle_pgn_dialog_toggle()
            result['consumed'] = True
            return result
        if key == pygame.K_u:
            self._handle_undo_key()
            result['consumed'] = True
            return result
        if key == pygame.K_y:
            self._handle_redo_key()
            result['consumed'] = True
            return result
        if key == pygame.K_f:
            self.flip_board()
            result['consumed'] = True
            return result
        if key == pygame.K_t:
            self.change_theme()
            result['consumed'] = True
            return result
        if key == pygame.K_r:
            self._handle_reset_key()
            result['consumed'] = True
            return result
        # Unknown key — not consumed.
        return result

    # ---- per-key helpers (used by handle_keydown) ------------------------

    def _handle_escape(self):
        """Esc cascade. Closes ONE thing per press, in priority order:
        jump-capture > transform menu > promotion menu > mode menu >
        pgn dialog > reset confirm > no-op.
        (The three in-turn states — jump-capture, transform menu,
        promotion menu — are mutually exclusive in practice (knight
        vs queen vs pawn flows) and outrank the paused screens.)"""
        if self.jump_capture_targets is not None:
            self.cancel_jump_capture()
            return
        if self.transform_menu is not None:
            self.cancel_transformation()
            return
        if self.promotion_menu is not None:
            self.cancel_promotion()
            return
        if self.mode_menu is not None:
            self.close_mode_menu()
            return
        if self.pgn_dialog_open:
            self.close_pgn_dialog()
            return
        if self.reset_confirm_pending:
            self.reset_confirm_pending = False
            return

    def _handle_mode_menu_toggle(self):
        if self.mode_menu is None:
            self.open_mode_menu()    # auto-closes pgn dialog + reset confirm
        else:
            self.close_mode_menu()

    def _handle_pgn_dialog_toggle(self):
        if self.pgn_dialog_open:
            self.close_pgn_dialog()
        else:
            self.open_pgn_dialog()   # auto-closes mode menu + reset confirm

    def _handle_reset_key(self):
        """R: open reset-confirm. Closes other paused screens first
        (unified mutual-exclusion)."""
        if self.mode_menu is not None:
            self.close_mode_menu()
        if self.pgn_dialog_open:
            self.close_pgn_dialog()
        self.reset_confirm_pending = True

    def _handle_undo_key(self):
        """U: undo.

        Final 2026-07-20 spec (supersedes both the 2026-05-30 "no-op
        unless a paused screen is open" rule and the interim #129
        autoplay-halt flag, which was confusing — an invisible paused
        state the user had to know to Esc out of): in CvC mode, U
        with no paused screen open — mid-game OR on the win screen —
        performs the undo and then OPENS the pause (PGN) screen. This
        keeps the rule "undo/redo works only while a pause screen is
        open" consistent: the pause screen is the visible paused
        state, further U/Y work through the normal paused-screen
        gating, and closing it as usual (P / Esc) resumes autoplay.
        Undo order matters: undo FIRST, then open, so the dialog
        renders the post-undo position. With a paused screen already
        open, undo behaves as before (no extra screen is opened). In
        HvH / HvAI undo always works and never opens anything.
        """
        if (self.mode == 'computer_vs_computer'
                and not self.is_autoplay_paused()):
            self.undo()
            self.open_pgn_dialog()
            return
        self.undo()

    def _handle_redo_key(self):
        """Y as redo: same CvC undo-then-open-pause behavior as undo
        above."""
        if (self.mode == 'computer_vs_computer'
                and not self.is_autoplay_paused()):
            self.redo()
            self.open_pgn_dialog()
            return
        self.redo()

    # ---- serialization / save-load --------------------------------------

    _copy_to_clipboard = staticmethod(_default_copy_to_clipboard)
    _read_clipboard = staticmethod(_default_read_clipboard)

    def serialize_to_text(self):
        """Serialize the entire game state to text. Round-trips
        perfectly through `deserialize_from_text` / `load_from_text`.

        V3 format (2026-07-20 — royal-notation movetext): a
        human-readable header (Mode / players / CurrentTurn / Winner)
        plus a numbered movetext in royal chess notation between the
        V3 markers — like a standard chess PGN, only the per-turn
        differences are recorded, and loading replays them from the
        initial position. `CurrentTurn` is the position shown on
        load; the rest of the timeline stays reachable via
        undo/redo. The serializer SELF-VERIFIES by replaying the
        movetext and comparing every state hash against the live
        timeline, so a save is correct by construction; any
        mismatch — or a game whose timeline does not start at the
        standard initial position (e.g. loaded from a FEN or a
        truncated legacy save) — falls back to the V2 container
        below. ~10x smaller again than V2 on top of V2's ~40x.
        """
        try:
            return self._serialize_v3()
        except Exception:
            return self._serialize_v2()

    def _serialize_v3(self):
        """Royal-notation writer. Raises (notation.NotationError or
        anything else) when the game cannot be represented — the
        caller falls back to _serialize_v2."""
        import notation
        timeline = self._history + list(reversed(self._redo_stack))
        if not timeline:
            raise notation.NotationError('empty timeline')
        bottom = timeline[0]
        fresh = Board()
        if (bottom['next_player'] != 'white'
                or bottom['winner'] is not None
                or bottom['board'].turn_number != 0
                or bottom['board'].get_state_hash('white')
                != fresh.get_state_hash('white')):
            raise notation.NotationError(
                'timeline does not start at the initial position')

        tokens = notation.infer_timeline_tokens(timeline)

        # Self-verify: replay the movetext on a scratch game and
        # compare every resulting state against the live timeline.
        scratch = Game()
        for i, token in enumerate(tokens):
            notation.apply_token(scratch, token)
            expect = timeline[i + 1]
            if (scratch.next_player != expect['next_player']
                    or scratch.winner != expect['winner']
                    or scratch.board.turn_number
                    != expect['board'].turn_number
                    or scratch.board.get_state_hash(scratch.next_player)
                    != expect['board'].get_state_hash(
                        expect['next_player'])):
                raise notation.NotationError(
                    f'replay diverged at turn {i + 1} ({token})')

        header_lines = [
            '=== Chess Variant Save (v3 royal notation) ===',
            f'Mode: {self.mode}',
            f'White: {self.white_player}   Black: {self.black_player}',
            f'CurrentTurn: {len(self._history) - 1}',
            f'Timeline: {len(tokens)}',
        ]
        if self._perspective_side != 'white':
            header_lines.append(f'Perspective: {self._perspective_side}')
        # The LIVE winner at the current position (matches V2 payload
        # semantics — normally derivable from the replay, but kept
        # authoritative so a winner state always round-trips).
        if self.winner:
            header_lines.append(f'Winner: {self.winner}')
        return (
            '\n'.join(header_lines)
            + '\n\n'
            + _SAVE_V3_BEGIN + '\n'
            + notation.tokens_to_movetext(tokens)
            + ('\n' if tokens else '')
            + _SAVE_V3_END + '\n'
        )

    def _serialize_v2(self):
        """Serialize the entire game state to a human-prefixed text
        block (fallback writer; also the loader's V2/V1 format).

        V2 format (2026-06-15 — compressed):

            === Chess Variant Save (v2 ruleset) ===
            Mode: <mode>
            Turn: <n> (<color> to move)
            White: <player>   Black: <player>
            Winner: <winner>          (only present if a winner exists)

            ___VARIANT_SAVE_V2_BEGIN___
            <base64 of zlib-compressed pickle, wrapped ~76 chars/line>
            ___VARIANT_SAVE_V2_END___

        The payload pickles the full undo history (one board snapshot
        per turn), which is extremely repetitive — zlib collapses it
        ~40x (a 60-turn game: ~1.1 MB under the old V1 encoding,
        ~28 KB under V2). Legacy V1 saves (uncompressed, single-line
        base64) remain loadable via `_parse_save_payload`.

        The header is human-readable; the payload between the markers
        is the canonical record. Loaders read the payload only; the
        header is decorative."""
        payload = {
            'version': _SAVE_VERSION,
            'board': self.board,
            'next_player': self.next_player,
            'winner': self.winner,
            'white_player': self.white_player,
            'black_player': self.black_player,
            '_perspective_side': self._perspective_side,
            '_history': self._history,
            '_redo_stack': self._redo_stack,
        }
        # protocol=4 is the default since 3.8 and is stable / portable.
        pickled = pickle.dumps(payload, protocol=4)
        compressed = zlib.compress(pickled, 9)
        # encodebytes wraps at 76 chars/line — keeps the save file
        # friendly to editors, diffs, and clipboard paths.
        encoded = base64.encodebytes(compressed).decode('ascii')
        header_lines = [
            '=== Chess Variant Save (v2 ruleset) ===',
            f'Mode: {self.mode}',
            f'Turn: {self.board.turn_number} ({self.next_player} to move)',
            f'White: {self.white_player}   Black: {self.black_player}',
        ]
        if self.winner:
            header_lines.append(f'Winner: {self.winner}')
        return (
            '\n'.join(header_lines)
            + '\n\n'
            + _SAVE_V2_BEGIN + '\n'
            + encoded
            + _SAVE_V2_END + '\n'
        )

    @classmethod
    def deserialize_from_text(cls, text):
        """Reconstruct a Game from text produced by serialize_to_text
        (V3 royal-notation movetext, V2 compressed, or legacy V1
        uncompressed). Raises ValueError on any parse failure."""
        g = cls()
        if not g.load_from_text(text):
            raise ValueError('unrecognized or corrupt save text')
        return g

    def load_from_text(self, text):
        """Replace this game's state with the deserialized state from
        `text`. Accepts V3 (royal-notation replay), V2, and legacy V1
        saves. Returns True on success, False on any error (game
        state is NOT mutated on failure).

        Uses in-place mutation of `self.board` so external callers
        holding the board reference (main.py) stay valid — same
        contract as `_restore`.
        """
        if isinstance(text, str) and _SAVE_V3_BEGIN in text:
            try:
                self._load_v3(text)
            except Exception:
                return False
            return True
        try:
            payload = self._parse_save_payload(text)
        except Exception:
            return False
        try:
            self._apply_loaded_payload(payload)
        except Exception:
            return False
        return True

    def _load_v3(self, text):
        """Load a V3 royal-notation save: replay the movetext from the
        standard initial position on a scratch game (rebuilding the
        undo history, repetition state, and winner through the exact
        turn-lifecycle code paths), adopt the result, then step back
        to the header's CurrentTurn — later states stay reachable via
        redo, exactly as when the game was saved. Raises on any parse
        or replay failure (the caller reports load failure; self is
        only mutated after the replay fully succeeds)."""
        import notation
        begin = text.find(_SAVE_V3_BEGIN) + len(_SAVE_V3_BEGIN)
        end = text.find(_SAVE_V3_END)
        if end <= begin:
            raise ValueError('missing V3 end marker')
        tokens = notation.movetext_to_tokens(text[begin:end])

        header = text[:text.find(_SAVE_V3_BEGIN)]
        players = re.search(r'White:\s*(\S+)\s+Black:\s*(\S+)', header)
        current = re.search(r'CurrentTurn:\s*(\d+)', header)
        perspective = re.search(r'Perspective:\s*(white|black)', header)
        saved_winner = re.search(r'Winner:\s*(white|black)', header)
        white_player = players.group(1) if players else 'human'
        black_player = players.group(2) if players else 'human'
        valid_players = {opt['key'] for opt in self.PLAYER_OPTIONS}
        if (white_player not in valid_players
                or black_player not in valid_players):
            raise ValueError(f'unknown player keys in save header: '
                             f'{white_player!r} / {black_player!r}')
        current_turn = int(current.group(1)) if current else len(tokens)
        if not (0 <= current_turn <= len(tokens)):
            raise ValueError(f'CurrentTurn {current_turn} outside the '
                             f'{len(tokens)}-turn timeline')

        # Replay on a scratch game first — self is untouched until the
        # whole movetext replays cleanly.
        scratch = Game()
        for token in tokens:
            notation.apply_token(scratch, token)

        # Adopt (in-place board mutation — same contract as _restore).
        self.board.__dict__.update(
            copy.deepcopy(scratch.board).__dict__)
        self.next_player = scratch.next_player
        self.winner = scratch.winner
        self.white_player = white_player
        self.black_player = black_player
        self._perspective_side = (perspective.group(1) if perspective
                                  else 'white')
        self._history = scratch._history
        self._redo_stack = scratch._redo_stack

        # Step back to the saved current position (raw single-step
        # pops — undo()'s AI-skip must not apply here).
        while len(self._history) - 1 > current_turn:
            self._redo_stack.append(self._history.pop())
            self._restore(self._history[-1])

        # The header's Winner is the LIVE winner at the current
        # position (authoritative — normally identical to what the
        # replay derived, but it also covers winner states not
        # re-derivable from the movetext).
        self.winner = saved_winner.group(1) if saved_winner else self.winner

        # Reset dialog/menu UI state (not part of the saved data) and
        # rebuild the AI controllers — mirrors _apply_loaded_payload.
        self.pgn_dialog_open = False
        self.pgn_dialog_copy_rect = None
        self.pgn_dialog_load_rect = None
        self.pgn_dialog_status = None
        self.mode_menu = None
        self.mode_menu_rects = []
        self.reset_confirm_pending = False
        if self.dragger is not None:
            self.dragger.dragging = False
            self.dragger.piece = None
        self._refresh_ai()

    @staticmethod
    def _parse_save_payload(text):
        """Extract + validate the pickled payload dict from a save
        text. Accepts BOTH container formats:

          - V2 (current): zlib-compressed pickle between the
            ___VARIANT_SAVE_V2_...___ markers (line-wrapped base64;
            b64decode tolerates the embedded newlines).
          - V1 (legacy): uncompressed pickle between the
            ___VARIANT_SAVE_V1_...___ markers.

        Raises on any error."""
        if not isinstance(text, str) or not text:
            raise ValueError('empty input')
        try:
            if _SAVE_V2_BEGIN in text:
                begin = text.find(_SAVE_V2_BEGIN) + len(_SAVE_V2_BEGIN)
                end = text.find(_SAVE_V2_END)
                if end <= begin:
                    raise ValueError('missing V2 end marker')
                raw = base64.b64decode(
                    text[begin:end].encode('ascii'), validate=False)
                pickled = zlib.decompress(raw)
            elif _SAVE_BEGIN in text:
                begin = text.find(_SAVE_BEGIN) + len(_SAVE_BEGIN)
                end = text.find(_SAVE_END)
                if end <= begin:
                    raise ValueError('missing V1 end marker')
                pickled = base64.b64decode(
                    text[begin:end].strip().encode('ascii'))
            else:
                raise ValueError('missing save markers')
            payload = pickle.loads(pickled)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f'corrupt save payload: {e}')
        if not isinstance(payload, dict):
            raise ValueError('save payload not a dict')
        if payload.get('version') != _SAVE_VERSION:
            raise ValueError(
                f"unsupported save version {payload.get('version')!r}")
        return payload

    def _apply_loaded_payload(self, payload):
        """Internal: install a deserialized payload onto this Game.

        Mirrors `_restore` for the board (in-place mutation to preserve
        external references) and additionally restores the mode state
        and undo/redo stacks. Refreshes derived AI controllers so the
        loaded game is immediately playable in HvAI/CvC."""
        loaded_board = copy.deepcopy(payload['board'])
        self.board.__dict__.update(loaded_board.__dict__)
        self.next_player = payload['next_player']
        self.winner = payload['winner']
        self.white_player = payload.get('white_player', 'human')
        self.black_player = payload.get('black_player', 'human')
        self._perspective_side = payload.get('_perspective_side', 'white')
        # Re-deepcopy history/redo so the loaded game and the payload
        # don't alias.
        self._history = copy.deepcopy(payload.get('_history', []))
        self._redo_stack = copy.deepcopy(payload.get('_redo_stack', []))
        # Reset dialog/menu UI state on a loaded game — these are not
        # part of the saved data.
        self.pgn_dialog_open = False
        self.pgn_dialog_copy_rect = None
        self.pgn_dialog_load_rect = None
        self.pgn_dialog_status = None
        self.mode_menu = None
        self.mode_menu_rects = []
        self.reset_confirm_pending = False
        if self.dragger is not None:
            self.dragger.dragging = False
            self.dragger.piece = None
        # Rebuild ai_controllers + mode from the loaded per-side keys.
        self._refresh_ai()

    def copy_to_clipboard_action(self):
        """Serialize the game and push it to the clipboard. Returns
        True on success. Records the transient 'Copied!' button-label
        state for the dialog renderer."""
        text = self.serialize_to_text()
        ok = Game._copy_to_clipboard(text)
        if ok:
            self.pgn_dialog_status = 'Copied to clipboard.'
            self._copied_at_ms = Game._now_ms()
            self._copied_button = 'save'
        else:
            self.pgn_dialog_status = (
                'Copy failed (clipboard unavailable — '
                'select & copy manually).')
        return ok

    def load_from_clipboard_action(self):
        """Read text from the clipboard and load it. Tries first as a
        full save (serialize_to_text format) — if THAT fails, tries
        as a FEN-style position summary. Returns True on success.
        Updates pgn_dialog_status either way for UI feedback."""
        text = Game._read_clipboard()
        if not text:
            self.pgn_dialog_status = 'Clipboard empty or unavailable.'
            return False
        if self.load_from_text(text):
            self.pgn_dialog_status = 'Loaded save (full game).'
            return True
        if self.load_from_fen(text):
            self.pgn_dialog_status = (
                'Loaded FEN (position only; history reset).')
            return True
        self.pgn_dialog_status = 'Load failed (not a valid save or FEN).'
        return False

    # ---- transient 'Copied!' feedback ----------------------------------
    #
    # When the user clicks Copy / Copy FEN, the button label flips to
    # 'Copied!' for _COPIED_FEEDBACK_MS milliseconds, then reverts.
    # _now_ms is a staticmethod so tests can monkeypatch it for
    # deterministic timing.

    _COPIED_FEEDBACK_MS = 1500

    @staticmethod
    def _now_ms():
        return pygame.time.get_ticks()

    def copy_recent_button(self, now_ms=None):
        """Returns 'save' or 'fen' if THAT button's Copy click is
        still within the feedback window, else None. The renderer
        uses this to decide whether to swap a button label to
        'Copied!'."""
        if self._copied_at_ms is None or self._copied_button is None:
            return None
        if now_ms is None:
            now_ms = Game._now_ms()
        if now_ms - self._copied_at_ms < Game._COPIED_FEEDBACK_MS:
            return self._copied_button
        return None

    def apply_mode_selection(self, white_player=None, black_player=None,
                             side=None, opponent=None):
        """Apply a mode-menu selection.

        Primary API (CvC-aware): set `white_player` and/or `black_player`
        independently. Each is a key from PLAYER_OPTIONS.

        Backwards-compat API (pre-CvC): `side` ('white'|'black' — which
        colour the human plays) and `opponent` (a PLAYER_OPTIONS key) are
        also accepted and translated to the new per-side fields. Useful
        for tests and callers written against the original two-slot menu.

        Raises ValueError on unknown keys. Does NOT auto-close the menu
        (live-settings model — close via M / Esc / `close_mode_menu()`).
        """
        valid_players = {opt['key'] for opt in self.PLAYER_OPTIONS}

        # Resolve the legacy (side, opponent) pair to (white_player,
        # black_player) edits if either was passed. The legacy two-slot
        # model encoded "the human plays `side`; the OTHER side is
        # `opponent`." We translate that into the per-side fields, and
        # also record `side` into `_perspective_side` so the human's
        # preferred colour survives in HvH (where the per-side fields
        # alone can't express it).
        if side is not None or opponent is not None:
            if side is not None and side not in ('white', 'black'):
                raise ValueError(
                    f"Unknown side: {side!r}; valid: ['black', 'white']")
            if opponent is not None and opponent not in valid_players:
                raise ValueError(
                    f"Unknown opponent: {opponent!r}; "
                    f"valid: {sorted(valid_players)}")
            if side is not None:
                self._perspective_side = side
            # Compute the resulting (white, black) the legacy way: human
            # on the chosen side, opponent on the OTHER side. If only one
            # of (side, opponent) was given, the unspecified one comes
            # from current state.
            current_perspective = self._perspective_side
            current_opponent_key = (
                self.opponent if self.opponent is not None else 'human')
            new_perspective = side if side is not None \
                else current_perspective
            new_opponent_key = opponent if opponent is not None \
                else current_opponent_key
            if new_perspective == 'white':
                if white_player is None:
                    white_player = 'human'
                if black_player is None:
                    black_player = new_opponent_key
            else:
                if black_player is None:
                    black_player = 'human'
                if white_player is None:
                    white_player = new_opponent_key

        if white_player is not None:
            if white_player not in valid_players:
                raise ValueError(
                    f"Unknown white_player: {white_player!r}; "
                    f"valid: {sorted(valid_players)}")
            self.white_player = white_player
        if black_player is not None:
            if black_player not in valid_players:
                raise ValueError(
                    f"Unknown black_player: {black_player!r}; "
                    f"valid: {sorted(valid_players)}")
            self.black_player = black_player
        self._refresh_ai()

    def _refresh_ai(self):
        """Recompute `mode` + per-side `ai_controllers` from the current
        (white_player, black_player) selection. Called after every state
        change so the derived AI state stays in sync.

        Mode-string convention (kept for back-compat with pre-CvC code):
          - HvH    -> 'human_vs_human'
          - HvAI   -> f'human_vs_{ai_key}'  (e.g. 'human_vs_random')
          - CvC    -> 'computer_vs_computer'
        """
        humans = sum(1 for p in (self.white_player, self.black_player)
                     if p == 'human')
        if humans == 2:
            self.mode = 'human_vs_human'
        elif humans == 1:
            ai_key = (self.black_player if self.white_player == 'human'
                      else self.white_player)
            self.mode = f'human_vs_{ai_key}'
        else:
            self.mode = 'computer_vs_computer'

        # Build per-side AIController objects (None for human slots).
        from ai_controller import AIController
        new_controllers = {}
        for color, player_key in (('white', self.white_player),
                                  ('black', self.black_player)):
            if player_key == 'human':
                new_controllers[color] = None
            else:
                new_controllers[color] = AIController(
                    color, player=self._make_ai_player(player_key))
        self.ai_controllers = new_controllers

    # ---- derived back-compat properties --------------------------------

    @property
    def user_side(self):
        """The colour the human plays.

        - HvH: `_perspective_side` (defaults to 'white'; updated when
          `apply_mode_selection(side=...)` is used). Lets HvH retain
          a stable human-side perspective for UI/legacy callers.
        - HvAI: the human's colour.
        - CvC: None (no human side exists — callers must handle this).
        """
        if self.white_player == 'human' and self.black_player == 'human':
            return self._perspective_side
        if self.white_player == 'human' and self.black_player != 'human':
            return 'white'
        if self.black_player == 'human' and self.white_player != 'human':
            return 'black'
        return None  # CvC

    @property
    def opponent(self):
        """The 'opponent' player key in the legacy two-slot mental model.

        - HvH: 'human'.
        - HvAI: the AI's player key (e.g. 'random').
        - CvC: None (there is no single 'opponent' — both sides are AI).
        """
        if self.white_player == 'human' and self.black_player == 'human':
            return 'human'
        if self.white_player == 'human':
            return self.black_player
        if self.black_player == 'human':
            return self.white_player
        return None  # CvC

    @property
    def ai_color(self):
        """The single AI's colour in HvAI; None in HvH or CvC.

        Computed from the per-side keys directly (not from `self.mode`),
        so that even with the specific mode-string convention
        ('human_vs_random', etc.) this still works for any AI key.
        """
        white_is_ai = self.white_player != 'human'
        black_is_ai = self.black_player != 'human'
        if white_is_ai and not black_is_ai:
            return 'white'
        if black_is_ai and not white_is_ai:
            return 'black'
        return None  # HvH or CvC

    @property
    def ai_controller(self):
        """The single AIController in HvAI; None in HvH or CvC. CvC has TWO
        controllers — callers needing CvC support should use
        `ai_controllers[color]` or `current_ai_controller()` instead."""
        color = self.ai_color
        return self.ai_controllers[color] if color is not None else None

    def current_ai_controller(self):
        """The AIController for whichever colour is to move RIGHT NOW, or
        None if that side is human / the game is over. Drives the AI-takes-
        turn check in main.py uniformly across HvAI and CvC.
        """
        if self.winner is not None:
            return None
        return self.ai_controllers.get(self.next_player)

    @classmethod
    def _resolve_ai_checkpoint(cls, opponent_key):
        """Resolve an AI difficulty key to a concrete checkpoint path, or
        None if no suitable checkpoint exists yet.

        - 'capped' mode (Easy): returns the checkpoint at the target
          iteration if it exists, else the HIGHEST existing checkpoint at
          or below the target. So Easy auto-tracks the strongest available
          model up to its cap (no manual bump needed) and never exceeds it.
        - 'exact' mode (Medium/Hard): returns the exact target checkpoint
          only if it exists, else None (stays unavailable).
        """
        cfg = cls._AI_DIFFICULTY.get(opponent_key)
        if cfg is None:
            return None
        target = cfg['target']
        exact = os.path.join(cls._CHECKPOINT_DIR, f'model_iter_{target:04d}.pt')
        if os.path.exists(exact):
            return exact
        if cfg['mode'] == 'exact':
            return None
        # 'capped': pick the highest existing checkpoint with iter <= target.
        best_path, best_iter = None, -1
        if os.path.isdir(cls._CHECKPOINT_DIR):
            for fname in os.listdir(cls._CHECKPOINT_DIR):
                m = re.match(r'model_iter_(\d+)\.pt$', fname)
                if m:
                    it = int(m.group(1))
                    if it <= target and it > best_iter:
                        best_iter, best_path = it, os.path.join(
                            cls._CHECKPOINT_DIR, fname)
        return best_path

    def _make_ai_player(self, opponent_key):
        """Construct the AI player for a given opponent key.

        - 'random' → returns None, letting AIController default to its
          built-in RandomPlayer baseline.
        - 'easy' / 'medium' / 'hard' → resolves the difficulty to a
          checkpoint (see _resolve_ai_checkpoint), loads the network, and
          wraps it in a NeuralPlayer. CPU device keeps the UI network
          independent of any concurrently-running training on MPS/CUDA.

        Returns None (RandomPlayer fallback) for an AI key whose checkpoint
        can't be resolved — normally unreachable because the mode menu
        grays out and skips unavailable options.
        """
        if opponent_key == 'random':
            return None  # AIController defaults to RandomPlayer
        if opponent_key in self._AI_DIFFICULTY:
            ckpt = self._resolve_ai_checkpoint(opponent_key)
            if ckpt is None:
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
        """True iff the opponent key is a non-AI key, or its difficulty
        resolves to an existing checkpoint. Used by show_mode_menu to gray
        out and deactivate options that can't yet be played."""
        if opponent_key not in self._AI_DIFFICULTY:
            return True  # 'human', 'random' — always available
        return self._resolve_ai_checkpoint(opponent_key) is not None

    def is_any_menu_open(self):
        """True iff a UI selection menu is currently open. main.py uses this
        to gate input/interactions while a menu is up."""
        return (
            self.transform_menu is not None
            or self.promotion_menu is not None
            or self.mode_menu is not None
            or self.reset_confirm_pending
            or self.pgn_dialog_open
        )

    def is_autoplay_paused(self):
        """True iff CvC autoplay should hold off. Same as
        is_any_menu_open in current scope, but exposed as a separate
        predicate so callers reading "is autoplay paused?" don't have
        to think about whether menus block autoplay (they always do).

        (CvC undo/redo with no paused screen open auto-opens the pgn
        dialog — see _handle_undo_key — so stepping through a game
        always holds the AIs via this same predicate.)"""
        return self.is_any_menu_open()

    def show_reset_confirm(self, surface):
        """Render the reset-game confirmation overlay if pending."""
        if not self.reset_confirm_pending:
            return
        w, h = surface.get_size()
        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 170))
        surface.blit(backdrop, (0, 0))
        title_font = pygame.font.SysFont('arial', 28, bold=True)
        body_font = pygame.font.SysFont('arial', 20)
        title = title_font.render('Reset the game?', True, (255, 255, 255))
        body = body_font.render(
            'Press Enter to reset.   Press N or Esc to cancel.',
            True, (220, 220, 220))
        surface.blit(title, title.get_rect(center=(w // 2, h // 2 - 30)))
        surface.blit(body, body.get_rect(center=(w // 2, h // 2 + 20)))

    def show_mode_menu(self, surface):
        """Render the mode-selection menu, if open, and populate
        `mode_menu_rects` for click detection. No-op when closed.

        Renders two stacked sections — 'White player' and 'Black player' —
        each a vertical column of the PLAYER_OPTIONS catalog. The
        currently-selected button in each section is highlighted. Each
        entry pushed onto `mode_menu_rects` is a (pygame.Rect, side,
        player_key) tuple where side ∈ {'white', 'black'}. main.py
        dispatches clicks back via apply_mode_selection(
        white_player=...) or (black_player=...)."""
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
            'Choose player for each side  (M / Esc to close)', True,
            (255, 255, 255))
        surface.blit(title, title.get_rect(center=(w // 2, h // 12)))

        def render_section(label, opts, side, current_key, col_left,
                           section_top, btn_w):
            """Render one side's section: a header + a vertical column of
            player-type buttons. AI options whose checkpoint isn't on disk
            yet render dimmer and are NOT added to mode_menu_rects, so
            clicks on them are ignored."""
            section_label = section_font.render(label, True, (220, 220, 220))
            surface.blit(section_label, section_label.get_rect(
                center=(col_left + btn_w // 2, section_top)))
            btn_h = 40
            gap = 8
            top_y = section_top + 28
            for i, opt in enumerate(opts):
                rect = pygame.Rect(
                    col_left, top_y + i * (btn_h + gap), btn_w, btn_h)
                active = (opt['key'] == current_key)
                available = self._ai_checkpoint_available(opt['key'])
                if available:
                    bg = (80, 140, 200) if active else (60, 60, 60)
                    border = (200, 200, 200)
                    text_color = (255, 255, 255)
                else:
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
                    self.mode_menu_rects.append((rect, side, opt['key']))

        # Two vertical columns: White (left) and Black (right). Renders
        # the same PLAYER_OPTIONS catalog twice, one per side, so the user
        # can pick any combination including AI-vs-AI.
        btn_w = min(220, int(w * 0.30))
        gap_between_cols = min(40, int(w * 0.04))
        total_w = btn_w * 2 + gap_between_cols
        left_col_x = (w - total_w) // 2
        right_col_x = left_col_x + btn_w + gap_between_cols
        section_top = h // 6 + 30
        render_section(
            'White player', self.mode_menu['white'], 'white',
            self.white_player, left_col_x, section_top, btn_w)
        render_section(
            'Black player', self.mode_menu['black'], 'black',
            self.black_player, right_col_x, section_top, btn_w)

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
        """Return True if any in-between turn UI state would be
        violated by an undo / redo.

        Genuine intermediate states (undo/redo would orphan UI):
        - knight leap awaiting capture/decline (`jump_capture_targets`),
        - open transformation menu (`transform_menu`),
        - open promotion menu (`promotion_menu`),
        - active drag (`dragger.dragging`) — the dragger holds a piece
          reference; restoring would orphan it (the piece would no longer
          exist on the post-restore board's squares array, but the
          dragger would still try to render and place it on release).

        NOT intermediate states (undo/redo are safe — they just change
        board state, which these don't depend on):
        - mode_menu: selects future per-side player; orthogonal to
          board history (per user 2026-05-30 spec: "if something
          doesn't interfere ... it should be enabled").
        - pgn_dialog_open: it's the paused-for-undo dialog itself;
          undo from inside it is the EXPECTED action.
        - reset_confirm_pending: the user can still undo before
          deciding whether to reset; the reset overlay does not
          depend on or destabilise undo.
        """
        return (
            self.jump_capture_targets is not None
            or self.transform_menu is not None
            or self.promotion_menu is not None
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

    def point_in_transform_menu(self, pos):
        """True iff the screen-space point lies inside one of the open
        transform menu's option squares (the same rects used for
        left-click selection). Used by main.py to make a right-click
        on an option a NO-OP — it is more likely a mis-pressed left
        click than a cancel attempt — while a right-click outside the
        options cancels. False when no menu is open (rects cleared)."""
        return any(rect.collidepoint(pos)
                   for rect, _ in self.transform_menu_rects)

    def point_in_promotion_menu(self, pos):
        """Promotion-menu counterpart of point_in_transform_menu."""
        return any(rect.collidepoint(pos)
                   for rect, _ in self.promotion_menu_rects)

    def is_transform_menu_piece_square(self, row, col):
        """True iff (row, col) is the BOARD square of the piece whose
        transform menu is currently open. The piece's own square is
        not a menu option (the option strip anchors one square away),
        so a right-click there closes the menu WITHOUT the #137
        fall-through reopening it — right-clicking a queen twice
        opens then closes its menu. False when no menu is open."""
        if self.transform_menu is None:
            return False
        return (row, col) == (self.transform_menu['row'],
                              self.transform_menu['col'])

    def is_jump_choice_square(self, row, col):
        """Jump-capture counterpart of the point_in_*_menu helpers,
        in BOARD space (the jump-capture "options" are board squares,
        not screen rects): True iff (row, col) is one of the two
        highlighted choice squares — the jumped piece (capture) or
        the landing square (decline). main.py makes a right-click
        there a NO-OP (likely a mis-pressed left click; canceling
        would revert the knight's whole move) while a right-click
        elsewhere cancels. False when no jump-capture is pending."""
        if self.jump_capture_targets is None:
            return False
        return ((row, col) in self.jump_capture_targets
                or (row, col) == self.jump_capture_landing)

    def cancel_transformation(self):
        """Close an open transform menu without transforming. Used by
        Esc / right-click-away / left-click-outside in the UI.

        Unlike cancel_jump_capture / cancel_promotion there is no
        snapshot to restore: opening the menu only SIMULATES the
        options (transform_queen with record_highlight left False),
        so nothing has been applied yet — cancel is purely closing
        the menu. Returns True on success, False if no menu is open."""
        if self.transform_menu is None:
            return False
        self.transform_menu = None
        self.transform_menu_rects = []
        return True

    def cancel_promotion(self):
        """Abort an open promotion menu and restore the state to before
        the pawn's move. Used by Esc / out-of-menu click in the UI.

        The pawn's spatial move is already applied when the menu opens,
        and the rulebook mandates that a pawn reaching the last rank
        promote — so cancel means taking back the whole move (pawn
        returns to its origin, any captured piece is restored, the turn
        does not advance) and choosing a different turn instead.
        Mirrors cancel_jump_capture. Returns True on success, False if
        there's no promotion menu or no pre-move snapshot to restore."""
        if self.promotion_menu is None:
            return False
        if self._pre_promotion_snapshot is None:
            return False
        self._restore(self._pre_promotion_snapshot)
        self._pre_promotion_snapshot = None
        self.promotion_menu = None
        self.promotion_menu_rects = []
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