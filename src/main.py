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
        pygame.display.set_caption('Chess')
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

                    # Block normal interaction during jump capture selection
                    if game.jump_capture_targets is not None:
                        pass  # handled on MOUSEBUTTONUP
                    elif clicked_row >= 0 and clicked_row <= 7 and clicked_col >= 0 and clicked_col <= 7:
                        # if clicked square has a piece ?
                        if board.squares[clicked_row][clicked_col].has_piece():
                            piece = board.squares[clicked_row][clicked_col].piece
                            args = [piece, clicked_row, clicked_col]

                            # clear valid moves
                            piece.clear_moves()

                            # valid piece (color) ?
                            if isinstance(piece, Boulder):
                                # Boulder is neutral — either player can move it
                                board.boulder_moves(*args)
                            elif piece.color == game.next_player:
                                # board.calc_moves(piece, clicked_row, clicked_col, bool=True)

                                if (isinstance(piece, King)):
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
                                board.queen_moves_enemy(*args)

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

                    released_row = event.pos[1] // SQSIZE
                    released_col = event.pos[0] // SQSIZE

                    # Handle jump capture second click
                    if game.jump_capture_targets is not None:
                        if 0 <= released_row <= 7 and 0 <= released_col <= 7:
                            clicked = (released_row, released_col)
                            if clicked in game.jump_capture_targets:
                                # Player chose to capture this adjacent enemy
                                board.execute_jump_capture(released_row, released_col)
                                game.play_sound(captured=True)
                            elif clicked == game.jump_capture_landing:
                                # Player declined capture (clicked landing square)
                                game.play_sound(captured=False)
                            else:
                                # Clicked elsewhere — ignore, wait for valid click
                                continue
                            # Clear jump capture state and end turn
                            board.clear_forbidden_squares()
                            # If the knight was manipulated (enemy piece), set forbidden_square
                            if game.jump_capture_piece and game.jump_capture_piece.color != game.next_player:
                                game.jump_capture_piece.forbidden_square = game.jump_capture_origin
                            game.jump_capture_targets = None
                            game.jump_capture_landing = None
                            game.jump_capture_piece = None
                            game.jump_capture_origin = None
                            board.update_assassin_squares(game.next_player)
                            board.decrement_boulder_cooldown()
                            game.next_turn()

                    elif dragger.dragging:
                        dragger.update_mouse(event.pos)

                        released_row = dragger.mouseY // SQSIZE
                        released_col = dragger.mouseX // SQSIZE

                        if released_row >= 0 and released_row <= 7 and released_col >= 0 and released_col <= 7:
                            # create possible move
                            initial = Square(dragger.initial_row, dragger.initial_col)
                            final = Square(released_row, released_col)
                            move = Move(initial, final)

                            # valid move ?
                            if board.valid_move(dragger.piece, move):
                                # normal capture
                                captured = board.squares[released_row][released_col].has_piece()
                                jump_targets = board.move(dragger.piece, move)

                                if jump_targets:
                                    # Knight jump capture — enter second click state
                                    game.jump_capture_targets = jump_targets
                                    game.jump_capture_landing = (released_row, released_col)
                                    game.jump_capture_piece = dragger.piece
                                    game.jump_capture_origin = (dragger.initial_row, dragger.initial_col)
                                    game.play_sound(captured=False)
                                    # show methods (highlights will be drawn by show_jump_capture_targets)
                                    game.show_bg(screen)
                                    game.show_last_move(screen)
                                    game.show_jump_capture_targets(screen)
                                    game.show_pieces(screen)
                                    dragger.undrag_piece()
                                    continue

                                board.set_true_en_passant(dragger.piece)

                                board.clear_forbidden_squares()

                                # If an enemy piece was moved by manipulation, set its forbidden square
                                if board.squares[released_row][released_col].has_enemy_piece(game.next_player):
                                    board.squares[released_row][released_col].piece.forbidden_square = (dragger.initial_row, dragger.initial_col)

                                # sounds
                                game.play_sound(captured)
                                # show methods
                                game.show_bg(screen)
                                game.show_last_move(screen)
                                game.show_pieces(screen)
                                # update assassin squares
                                board.update_assassin_squares(game.next_player)
                                # decrement boulder cooldown
                                board.decrement_boulder_cooldown()
                                # next turn
                                game.next_turn()

                    dragger.undrag_piece()

                # key press
                elif event.type == pygame.KEYDOWN:

                    # changing themes
                    if event.key == pygame.K_t:
                        game.change_theme()

                     # changing themes
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
