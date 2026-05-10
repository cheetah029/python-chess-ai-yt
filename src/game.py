import copy

import pygame

from const import *
from board import Board
from dragger import Dragger
from config import Config
from square import Square
from piece import Queen

class Game:

    def __init__(self):
        self.next_player = 'white'
        self.hovered_sqr = None
        self.board = Board()
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

    # blit methods

    def show_bg(self, surface):
        theme = self.config.theme
        
        for row in range(ROWS):
            for col in range(COLS):
                # color
                color = theme.bg.light if (row + col) % 2 == 0 else theme.bg.dark
                # rect
                rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, color, rect)

                # row coordinates
                if col == 0:
                    # color
                    color = theme.bg.dark if row % 2 == 0 else theme.bg.light
                    # label
                    lbl = self.config.font.render(str(ROWS-row), 1, color)
                    lbl_pos = (5, 5 + row * SQSIZE)
                    # blit
                    surface.blit(lbl, lbl_pos)

                # col coordinates
                if row == 7:
                    # color
                    color = theme.bg.dark if (row + col) % 2 == 0 else theme.bg.light
                    # label
                    lbl = self.config.font.render(Square.get_alphacol(col), 1, color)
                    lbl_pos = (col * SQSIZE + SQSIZE - 20, HEIGHT - 20)
                    # blit
                    surface.blit(lbl, lbl_pos)

    def show_pieces(self, surface):
        for row in range(ROWS):
            for col in range(COLS):
                # piece ?
                if self.board.squares[row][col].has_piece():
                    piece = self.board.squares[row][col].piece

                    # all pieces except dragger piece
                    if piece is not self.dragger.piece:
                        piece.set_texture(size=80)
                        img = pygame.image.load(piece.texture)
                        img_center = col * SQSIZE + SQSIZE // 2, row * SQSIZE + SQSIZE // 2
                        piece.texture_rect = img.get_rect(center=img_center)

                        surface.blit(img, piece.texture_rect)

                        # Overlay (bottom-right): one icon max per piece
                        # Royal transformed: queen icon (distinguishes from normal pieces)
                        # Non-royal (promoted): pawn icon (distinguishes from royal)
                        overlay_path = None
                        if piece.is_transformed and piece.is_royal:
                            overlay_path = f'assets/images/imgs-80px/{piece.color}_queen.png'
                        elif not piece.is_royal and (isinstance(piece, Queen) or piece.is_transformed):
                            overlay_path = f'assets/images/imgs-80px/{piece.color}_pawn.png'

                        if overlay_path:
                            overlay = pygame.image.load(overlay_path)
                            overlay = pygame.transform.scale(overlay, (30, 30))
                            icon_pos = (col * SQSIZE + SQSIZE - 32, row * SQSIZE + SQSIZE - 32)
                            surface.blit(overlay, icon_pos)

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
                # rect
                rect = (move.final.col * SQSIZE, move.final.row * SQSIZE, SQSIZE, SQSIZE)
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
                rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, color, rect)

    def show_last_move(self, surface):
        theme = self.config.theme

        if self.board.last_action:
            # Non-spatial action highlight (e.g. transformation) — single square
            pos = self.board.last_action
            color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark
            rect = (pos.col * SQSIZE, pos.row * SQSIZE, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, color, rect)
        elif self.board.last_move:
            initial = self.board.last_move.initial
            final = self.board.last_move.final

            for pos in [initial, final]:
                # color
                color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark
                # rect
                rect = (pos.col * SQSIZE, pos.row * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, color, rect)

    def show_transform_menu(self, surface):
        """Draw the vertical strip transformation menu."""
        if not self.transform_menu:
            return

        menu = self.transform_menu
        row, col = menu['row'], menu['col']
        options = menu['options']
        color = menu['piece_color']

        self.transform_menu_rects = []

        # Determine direction: extend downward, or upward if near bottom
        if row + len(options) < ROWS:
            direction = 1
            start_row = row
        else:
            direction = -1
            start_row = row

        for i, option in enumerate(options):
            menu_row = start_row + (i + 1) * direction if direction == 1 else start_row - (len(options) - i)
            x = col * SQSIZE
            y = menu_row * SQSIZE

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

        # Extend downward or upward depending on position
        if row + len(options) < ROWS:
            direction = 1
            start_row = row
        else:
            direction = -1
            start_row = row

        for i, option in enumerate(options):
            menu_row = start_row + (i + 1) * direction if direction == 1 else start_row - (len(options) - i)
            x = col * SQSIZE
            y = menu_row * SQSIZE

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
            # rect
            rect = (self.hovered_sqr.col * SQSIZE, self.hovered_sqr.row * SQSIZE, SQSIZE, SQSIZE)
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
        - active drag (`dragger.dragging`) — the dragger holds a piece
          reference; restoring would orphan it (the piece would no longer
          exist on the post-restore board's squares array, but the
          dragger would still try to render and place it on release).
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
        """Roll back to the state at the start of the current turn (i.e.,
        the result of the previous turn). Pushes the current state onto
        the redo stack. Returns True on success, False if there's nothing
        to undo or we're in an intermediate state."""
        if not self.can_undo():
            return False
        self._redo_stack.append(self._history.pop())
        self._restore(self._history[-1])
        return True

    def redo(self):
        """Re-apply a turn that was just undone. Returns True on success,
        False if the redo stack is empty or we're in an intermediate state."""
        if not self.can_redo():
            return False
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

    def change_theme(self):
        self.config.change_theme()

    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()

    def reset(self):
        self.__init__()