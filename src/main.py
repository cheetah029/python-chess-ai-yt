"""Main game entry point — Version 2 (queen-freeze + knight redesign).

Differences from v0 (preserved as `main_v0.py`):

- **Queen manipulation now freezes the manipulated piece in place** (rather than
  forbidding it from returning to its previous square). A piece moved by the
  queen sets its `moved_by_queen` flag to True, which prevents that piece from
  making any spatial move on its immediate next (owner's) turn. Actions such as
  the queen's transformation are still allowed while frozen.

- **No-repeat restriction removed.** The queen may manipulate the same piece on
  consecutive queen turns. Combined with the freeze, this enables a "reeling-in"
  tactic where the queen drags an enemy piece across the board and eventually
  pulls it adjacent for capture. (The existing rulebook restriction "queen may
  not move a piece that moved on the immediately preceding turn" is unaffected
  — under freeze, the manipulated piece doesn't make a spatial move on its
  owner's turn, so the queen can re-target it on her next turn.)

- **No-legal-moves loss rule.** Since manipulation now prevents a piece from
  making a spatial move on its next turn, it is possible for the manipulated
  player to have no legal moves at all (if the manipulated piece is their only
  piece capable of acting and they cannot do an action either). When this
  happens, the player with no legal moves loses. This is enforced in
  `Game.next_turn` via `Board.has_legal_moves`.

Differences from the queen-freeze-only intermediate (preserved as `main_v1.py`):

- **Knight reactive jump-capture.** The knight may capture the piece it jumped
  over only if that piece (a) is an enemy and (b) made a spatial move on the
  immediately preceding turn. The old "capture any adjacent enemy to the
  landing square after a jump" behavior is removed entirely. Implemented in
  `Board._can_jump_capture` / `Board.move()` knight branch via
  `last_move_turn_number` tracking.

- **Knight post-jump invulnerability.** When the knight makes a non-capture
  spatial move that jumps over a piece (friendly, enemy, or the boulder),
  the knight becomes invulnerable to capture for the immediately following
  opponent turn. Captures of any kind — standard capture at the landing
  square OR jump-capture of the jumped piece — do NOT grant invulnerability.
  Invulnerability expires at the start of the knight-owner's next turn.
  Implemented by setting the existing `Piece.invulnerable` flag (also used
  by the invulnerable-manipulation engine variants), with capture filtering
  in `Square.has_capturable_enemy_piece` and per-turn clearing in `Game.next_turn` via
  `Board.clear_invulnerable_for_color`. A small shield icon is rendered on
  any invulnerable piece via `game.compute_piece_overlays`, occupying the
  bottom-left corner so it doesn't collide with the bottom-right queen/pawn
  marker.

UI conveniences (independent of game rules):

- **Esc / right-click / click outside the two highlighted squares** during
  the knight's jump-capture second click cancels the in-progress turn and
  restores the knight to its origin square.
- **U** undoes the most recent completed turn (full history; can step back
  to the start of the game). **Y** redoes. Undo/redo are blocked while any
  in-progress turn UI state is active (jump-capture pending, transform
  menu, promotion menu) to avoid capturing partial state.

The tiny endgame rule changes from `docs/potential-rule-changes.md` Section 4
are NOT included in this version. They remain deferred until the rule design
is finalized.
"""

import pygame
import sys

from const import *
from game import Game
from square import Square
from piece import *
from move import Move

class Main:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode( (WIDTH, HEIGHT) )
        pygame.display.set_caption('Chess (v2)')
        self.game = Game()

    def mainloop(self):

        screen = self.screen
        game = self.game
        board = self.game.board
        dragger = self.game.dragger

        while True:
            # show methods
            game.show_bg(screen)
            game.show_last_move(screen)
            game.show_moves(screen)
            game.show_jump_capture_targets(screen)
            game.show_pieces(screen)
            game.show_hover(screen)
            game.show_transform_menu(screen)
            game.show_promotion_menu(screen)
            game.show_winner(screen)
            board.update_lines_of_sight()
            board.update_threat_squares()

            if dragger.dragging:
                dragger.update_blit(screen)

            for event in pygame.event.get():

                # click
                if event.type == pygame.MOUSEBUTTONDOWN:
                    dragger.update_mouse(event.pos)

                    clicked_row = dragger.mouseY // SQSIZE
                    clicked_col = dragger.mouseX // SQSIZE

                    # Block all interactions when game is over
                    if game.winner:
                        continue

                    # Handle transform menu clicks (left-click on menu option)
                    if game.transform_menu and event.button == 1:
                        mx, my = event.pos
                        selected = None
                        for rect, option in game.transform_menu_rects:
                            if rect.collidepoint(mx, my):
                                selected = option
                                break
                        if selected:
                            menu = game.transform_menu
                            board.transform_queen(
                                board.squares[menu['row']][menu['col']].piece,
                                menu['row'], menu['col'], selected
                            )
                            game.transform_menu = None
                            game.transform_menu_rects = []
                            board.update_assassin_squares(game.next_player)
                            board.decrement_boulder_cooldown()
                            # tiny endgame rule (unchanged from v0)
                            if board.tiny_endgame_active:
                                board.update_distance_count(captured=False)
                            if not board.tiny_endgame_active and board.is_tiny_endgame():
                                board.init_tiny_endgame()
                            game.next_turn()
                        else:
                            # Clicked outside menu — close it
                            game.transform_menu = None
                            game.transform_menu_rects = []
                        continue

                    # Handle promotion menu clicks (left-click on menu option)
                    if game.promotion_menu and event.button == 1:
                        mx, my = event.pos
                        selected = None
                        for rect, option in game.promotion_menu_rects:
                            if rect.collidepoint(mx, my):
                                selected = option
                                break
                        if selected:
                            menu = game.promotion_menu
                            board.promote(
                                menu['pawn'], menu['row'], menu['col'], selected
                            )
                            game.promotion_menu = None
                            game.promotion_menu_rects = []
                            board.update_assassin_squares(game.next_player)
                            board.decrement_boulder_cooldown()
                            promotion_captured = menu.get('captured', False)
                            # check win condition after promotion (if it was a capture)
                            if promotion_captured:
                                game.winner = board.check_winner()
                            # tiny endgame: can't be active before promotion (pawn existed),
                            # but may activate after if last pawn was just promoted
                            if board.is_tiny_endgame():
                                board.init_tiny_endgame()
                            game.next_turn()
                        # Don't close on outside click — promotion is mandatory
                        continue

                    # Block all other interactions during promotion menu
                    if game.promotion_menu:
                        continue

                    # Right-click: open transformation menu for queen/transformed piece
                    if event.button == 3:  # right-click
                        if 0 <= clicked_row <= 7 and 0 <= clicked_col <= 7:
                            piece = board.squares[clicked_row][clicked_col].piece
                            if piece and piece.color == game.next_player:
                                # Check if this is a queen or transformed queen
                                is_queen_or_transformed = isinstance(piece, Queen) or piece.is_transformed
                                if is_queen_or_transformed:
                                    options = board.get_transformation_options(piece)
                                    options = board.filter_transformation_options(
                                        piece, clicked_row, clicked_col, options, game.next_player)
                                    if options:
                                        game.transform_menu = {
                                            'piece': piece,
                                            'piece_color': piece.color,
                                            'row': clicked_row,
                                            'col': clicked_col,
                                            'options': options,
                                        }
                        continue

                    # Left-click: close any open transform menu
                    if game.transform_menu:
                        game.transform_menu = None
                        game.transform_menu_rects = []

                    # Intersection click region for boulder: bounded by midpoints of d4/d5/e4/e5
                    boulder_intersection_clicked = False
                    if board.boulder and board.boulder.on_intersection:
                        mid_left = 3 * SQSIZE + SQSIZE // 2
                        mid_right = 4 * SQSIZE + SQSIZE // 2
                        mid_top = 3 * SQSIZE + SQSIZE // 2
                        mid_bottom = 4 * SQSIZE + SQSIZE // 2
                        mx, my = dragger.mouseX, dragger.mouseY
                        boulder_intersection_clicked = (mid_left <= mx <= mid_right and mid_top <= my <= mid_bottom)

                    # Block normal interaction during jump capture selection
                    if game.jump_capture_targets is not None:
                        pass  # handled on MOUSEBUTTONUP

                    # Check if clicking the boulder on the central intersection
                    elif boulder_intersection_clicked:
                        # White cannot move boulder on turn 1 (turn_number == 0)
                        if not (game.next_player == 'white' and board.turn_number == 0):
                            piece = board.boulder
                            piece.clear_moves()
                            board.boulder_moves(piece)
                            board.filter_repetition_moves(piece, game.next_player)
                            board.filter_endgame_moves(piece, game.next_player)
                            dragger.save_initial(event.pos)
                            dragger.drag_piece(piece)
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)

                    elif clicked_row >= 0 and clicked_row <= 7 and clicked_col >= 0 and clicked_col <= 7:
                        # if clicked square has a piece ?
                        if board.squares[clicked_row][clicked_col].has_piece():
                            piece = board.squares[clicked_row][clicked_col].piece
                            args = [piece, clicked_row, clicked_col]

                            # clear valid moves
                            piece.clear_moves()

                            # valid piece (color) ?
                            if isinstance(piece, Boulder):
                                # Boulder on a square (after first move) — either player can move
                                # White cannot move boulder on turn 1
                                if game.next_player == 'white' and board.turn_number == 0:
                                    pass
                                else:
                                    board.boulder_moves(*args)
                            elif piece.color == game.next_player:
                                # v2 freeze: pieces with moved_by_queen=True cannot make spatial
                                # moves on their immediate next turn. The queen's transformation
                                # action is still allowed and is initiated via right-click.
                                if piece.moved_by_queen:
                                    pass  # no spatial moves available — only actions (right-click)
                                elif (isinstance(piece, King)):
                                    board.king_moves(*args)
                                elif (isinstance(piece, Queen)):
                                    board.queen_moves(*args)
                                elif (isinstance(piece, Rook)):
                                    board.rook_moves(*args)
                                elif (isinstance(piece, Bishop)):
                                    board.bishop_moves(*args)
                                elif (isinstance(piece, Knight)):
                                    board.knight_moves(*args)
                                elif (isinstance(piece, Pawn)):
                                    board.pawn_moves(*args)
                            else:
                                # enemy piece (color) — queen manipulation
                                # Note: existing restriction "queen may not move a piece that
                                # moved on the immediately preceding turn" is enforced inside
                                # queen_moves_enemy via board.last_move tracking.
                                board.queen_moves_enemy(*args)

                            # Filter out moves that would cause third repetition or exceed distance limit
                            board.filter_repetition_moves(piece, game.next_player)
                            board.filter_endgame_moves(piece, game.next_player)

                            dragger.save_initial(event.pos)
                            dragger.drag_piece(piece)
                            # show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)

                # mouse motion
                elif event.type == pygame.MOUSEMOTION:
                    motion_row = event.pos[1] // SQSIZE
                    motion_col = event.pos[0] // SQSIZE

                    if motion_row >= 0 and motion_row <= 7 and motion_col >= 0 and motion_col <= 7:
                        game.set_hover(motion_row, motion_col)

                        if dragger.dragging:
                            dragger.update_mouse(event.pos)
                            # show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)
                            game.show_hover(screen)
                            dragger.update_blit(screen)

                # click release
                elif event.type == pygame.MOUSEBUTTONUP:

                    if game.winner:
                        continue

                    released_row = event.pos[1] // SQSIZE
                    released_col = event.pos[0] // SQSIZE

                    # Handle jump capture second click
                    if game.jump_capture_targets is not None:
                        # Right-click during jump-capture state cancels the
                        # in-progress turn entirely (knight returns to origin).
                        if event.button == 3:
                            game.cancel_jump_capture()
                            game.play_sound(captured=False)
                            continue
                        # Click outside the board area — also cancels.
                        if not (0 <= released_row <= 7 and 0 <= released_col <= 7):
                            game.cancel_jump_capture()
                            game.play_sound(captured=False)
                            continue
                        clicked = (released_row, released_col)
                        if clicked in game.jump_capture_targets:
                            # Player chose to capture the jumped piece (v2:
                            # only the jumped piece is ever a target).
                            board.execute_jump_capture(released_row, released_col)
                            game.play_sound(captured=True)
                        elif clicked == game.jump_capture_landing:
                            # Player declined capture (clicked landing square).
                            # v2 knight: jumped piece survives → knight is
                            # invulnerable for one opponent turn.
                            board.set_invulnerable_after_jump_decline(game.jump_capture_piece)
                            game.play_sound(captured=False)
                        else:
                            # Clicked outside both red highlights — cancel
                            # the in-progress turn (knight returns to origin).
                            game.cancel_jump_capture()
                            game.play_sound(captured=False)
                            continue
                        # Resolved (capture or decline). The pre-jump-capture
                        # snapshot was only needed for cancel — drop it now.
                        game._pre_jump_capture_snapshot = None
                        # Clear jump capture state and end turn
                        board.clear_forbidden_squares()
                        # v2: if the knight was manipulated (enemy piece), set its
                        # moved_by_queen flag so it cannot make a spatial move next turn
                        if game.jump_capture_piece and game.jump_capture_piece.color != game.next_player:
                            game.jump_capture_piece.moved_by_queen = True
                        jump_captured = clicked in game.jump_capture_targets
                        game.jump_capture_targets = None
                        game.jump_capture_landing = None
                        game.jump_capture_piece = None
                        game.jump_capture_origin = None
                        board.update_assassin_squares(game.next_player)
                        board.decrement_boulder_cooldown()
                        # check win condition after jump capture
                        if jump_captured:
                            game.winner = board.check_winner()
                        # tiny endgame rule (unchanged from v0)
                        if board.tiny_endgame_active:
                            board.update_distance_count(captured=jump_captured)
                        if not board.tiny_endgame_active and board.is_tiny_endgame():
                            board.init_tiny_endgame()
                        game.next_turn()

                    elif dragger.dragging:
                        dragger.update_mouse(event.pos)

                        released_row = dragger.mouseY // SQSIZE
                        released_col = dragger.mouseX // SQSIZE

                        if released_row >= 0 and released_row <= 7 and released_col >= 0 and released_col <= 7:
                            # create possible move
                            # Boulder from intersection uses sentinel (-1,-1) as initial
                            if isinstance(dragger.piece, Boulder) and dragger.piece.on_intersection:
                                initial = Square(-1, -1)
                            else:
                                initial = Square(dragger.initial_row, dragger.initial_col)
                            final = Square(released_row, released_col)
                            move = Move(initial, final)

                            # valid move ?
                            if board.valid_move(dragger.piece, move):
                                # normal capture
                                captured = board.squares[released_row][released_col].has_piece()
                                # Snapshot the pre-move state so the player can
                                # cancel the second click if a knight jump-capture
                                # is offered. We capture before board.move() runs
                                # because we don't yet know whether jump-capture
                                # state will be entered.
                                pre_move_snapshot = game._snapshot()
                                jump_targets = board.move(dragger.piece, move)

                                if jump_targets:
                                    # Knight jump capture — enter second click state
                                    game.jump_capture_targets = jump_targets
                                    game.jump_capture_landing = (released_row, released_col)
                                    game.jump_capture_piece = dragger.piece
                                    game.jump_capture_origin = (dragger.initial_row, dragger.initial_col)
                                    # Retain the pre-move snapshot so cancel can
                                    # restore the state if the player aborts.
                                    game._pre_jump_capture_snapshot = pre_move_snapshot
                                    game.play_sound(captured=False)
                                    # show methods (highlights will be drawn by show_jump_capture_targets)
                                    game.show_bg(screen)
                                    game.show_last_move(screen)
                                    game.show_jump_capture_targets(screen)
                                    game.show_pieces(screen)
                                    dragger.undrag_piece()
                                    continue

                                # Check for pawn promotion
                                if board.check_promotion(dragger.piece, final):
                                    game.promotion_menu = {
                                        'pawn': dragger.piece,
                                        'pawn_color': dragger.piece.color,
                                        'row': released_row,
                                        'col': released_col,
                                        'captured': captured,
                                    }
                                    game.play_sound(captured)
                                    game.show_bg(screen)
                                    game.show_last_move(screen)
                                    game.show_pieces(screen)
                                    game.show_promotion_menu(screen)
                                    dragger.undrag_piece()
                                    continue

                                board.set_true_en_passant(dragger.piece)

                                board.clear_forbidden_squares()

                                # v2: if an enemy piece was moved by manipulation, set its
                                # moved_by_queen flag (the freeze applies to the owner's
                                # immediate next turn). Replaces the v0 forbidden_square logic.
                                if board.squares[released_row][released_col].has_capturable_enemy_piece(game.next_player):
                                    board.squares[released_row][released_col].piece.moved_by_queen = True

                                # sounds
                                game.play_sound(captured)
                                # show methods
                                game.show_bg(screen)
                                game.show_last_move(screen)
                                game.show_pieces(screen)
                                # update assassin squares
                                board.update_assassin_squares(game.next_player)
                                # decrement boulder cooldown (skip if boulder was the piece moved)
                                board.decrement_boulder_cooldown(moved_piece=dragger.piece)
                                # check win condition
                                if captured:
                                    game.winner = board.check_winner()
                                # tiny endgame rule (unchanged from v0)
                                if board.tiny_endgame_active:
                                    board.update_distance_count(captured=captured)
                                if not board.tiny_endgame_active and board.is_tiny_endgame():
                                    board.init_tiny_endgame()
                                # next turn (Game.next_turn clears moved_by_queen for opponent
                                # and checks the no-legal-moves loss condition)
                                game.next_turn()

                    dragger.undrag_piece()

                # key press
                elif event.type == pygame.KEYDOWN:

                    # Esc: cancel an in-progress jump-capture second click.
                    # If no jump-capture state is active, Esc does nothing
                    # (we don't want it to also close menus or quit).
                    if event.key == pygame.K_ESCAPE:
                        if game.jump_capture_targets is not None:
                            game.cancel_jump_capture()
                            game.play_sound(captured=False)
                        continue

                    # U: undo the most recent completed turn. Disallowed
                    # mid-action (jump-capture pending, transform/promotion
                    # menu open) — Game.can_undo enforces the guard.
                    if event.key == pygame.K_u:
                        game.undo()
                        continue

                    # Y: redo a previously-undone turn. Same intermediate-
                    # state guard as undo.
                    if event.key == pygame.K_y:
                        game.redo()
                        continue

                    # changing themes
                    if event.key == pygame.K_t:
                        game.change_theme()

                     # reset the game
                    if event.key == pygame.K_r:
                        game.reset()
                        game = self.game
                        board = self.game.board
                        dragger = self.game.dragger

                # quit application
                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()

if __name__ == '__main__':
    main = Main()
    main.mainloop()
