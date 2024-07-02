from const import *
from square import Square
from piece import *
from move import Move
from sound import Sound
import copy
import os

class Board:

    def __init__(self):
        self.squares = [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)]
        self.last_move = None
        self._create()
        self._add_pieces('white')
        self._add_pieces('black')

    def move(self, piece, move, testing=False):
        initial = move.initial
        final = move.final

        final_square_empty = self.squares[final.row][final.col].isempty()

        # console board move update
        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece

        if isinstance(piece, Pawn):
            # # en passant capture
            # diff = final.col - initial.col
            # if diff != 0 and final_square_empty: # Previously en_passant_empty
            #     # console board move update
            #     self.squares[initial.row][initial.col + diff].piece = None
            #     self.squares[final.row][final.col].piece = piece
            #     if not testing:
            #         sound = Sound(
            #             os.path.join('assets/sounds/capture.wav'))
            #         sound.play()

            # # pawn promotion
            # else:
            self.check_promotion(piece, final)

        if isinstance(piece, Knight):
            row = initial.row
            col = initial.col
            diff_row = final.row - initial.row
            diff_col = final.col - initial.col

            diffs = [
                (-3, 0),  # 3 up
                (-3, 1),  # 3 up, 1 right
                (-2, 2),  # 2 up, 2 right
                (-1, 3),  # 3 right, 1 up
                (0, 3),   # 3 right
                (1, 3),   # 3 right, 1 down
                (2, 2),   # 2 down, 2 right
                (3, 1),   # 3 down, 1 right
                (3, 0),   # 3 down
                (3, -1),  # 3 down, 1 left
                (2, -2),  # 2 down, 2 left
                (1, -3),  # 3 left, 1 down
                (0, -3),  # 3 left
                (-1, -3), # 3 left, 1 up
                (-2, -2), # 2 up, 2 left
                (-3, -1), # 3 up, 1 left
            ]

            squares_behind_moves = [
                (row-2, col+0), # 2 up
                (row-2, col+1), # 2 up, 1 right
                (row-1, col+1), # 1 up, 1 right
                (row-1, col+2), # 2 right, 1 up
                (row+0, col+2), # 2 right
                (row+1, col+2), # 2 right, 1 down
                (row+1, col+1), # 1 down, 1 right
                (row+2, col+1), # 2 down, 1 right
                (row+2, col+0), # 2 down
                (row+2, col-1), # 2 down, 1 left
                (row+1, col-1), # 1 down, 1 left
                (row+1, col-2), # 2 left, 1 down
                (row+0, col-2), # 2 left
                (row-1, col-2), # 2 left, 1 up
                (row-1, col-1), # 1 up, 1 left
                (row-2, col-1), # 2 up, 1 left
            ]

            two_squares_behind_moves = [
                (row-1, col+0), # 1 up
                (row+0, col+1), # 1 right
                (row+1, col+0), # 1 down
                (row+0, col-1), # 1 left
            ]

            move_index = 0

            for i in range(len(diffs)):
                if diffs[i] == (diff_row, diff_col):
                    move_index = i
                    break

            possible_capture_row, possible_capture_col = squares_behind_moves[move_index]

            if final_square_empty:
                if self.squares[possible_capture_row][possible_capture_col].has_enemy_piece(piece.color):
                    self.squares[possible_capture_row][possible_capture_col].piece = None
                    if not testing:
                        sound = Sound(
                            os.path.join('assets/sounds/capture.wav'))
                        sound.play()
                elif diffs[move_index] == (-3, 0) or diffs[move_index] == (0, 3) or diffs[move_index] == (3, 0) or diffs[move_index] == (0, -3):
                    if self.squares[possible_capture_row][possible_capture_col].isempty():
                        second_possible_capture_row, second_possible_capture_col = two_squares_behind_moves[move_index // 4]
                        if self.squares[second_possible_capture_row][second_possible_capture_col].has_enemy_piece(piece.color):
                            self.squares[second_possible_capture_row][second_possible_capture_col].piece = None
                            if not testing:
                                sound = Sound(
                                    os.path.join('assets/sounds/capture.wav'))
                                sound.play()

        # king castling
        if isinstance(piece, King):
            if self.castling(initial, final) and not testing:
                diff = final.col - initial.col
                rook = piece.left_rook if (diff < 0) else piece.right_rook
                self.move(rook, rook.moves[-1])

        # move
        piece.moved = True

        # clear valid moves
        piece.clear_moves()

        # set last move
        self.last_move = move

    def valid_move(self, piece, move):
        return move in piece.moves

    def check_promotion(self, piece, final):
        if final.row == 0 or final.row == 7:
            self.squares[final.row][final.col].piece = Queen(piece.color)

    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    def set_true_en_passant(self, piece):
        
        if not isinstance(piece, Pawn):
            return

        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    self.squares[row][col].piece.en_passant = False
        
        piece.en_passant = True

    def in_check(self, piece, move):
        temp_piece = copy.deepcopy(piece)
        temp_board = copy.deepcopy(self)
        temp_board.move(temp_piece, move, testing=True)
        
        for row in range(ROWS):
            for col in range(COLS):
                if temp_board.squares[row][col].has_enemy_piece(piece.color):
                    p = temp_board.squares[row][col].piece
                    temp_board.calc_moves(p, row, col, bool=False)
                    for m in p.moves:
                        if isinstance(m.final.piece, King):
                            return True
        
        return False

    def clear_pieces_moved_by_queen(self):
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_piece():
                    self.squares[row][col].piece.moved_by_queen = False

    def straightline_squares(self, piece, row, col, incrs):
        squares = []

        for incr in incrs:
            row_incr, col_incr = incr
            possible_square_row = row + row_incr
            possible_square_col = col + col_incr

            while True:
                if Square.in_range(possible_square_row, possible_square_col):
                    # has team piece = break
                    if self.squares[possible_square_row][possible_square_col].has_team_piece(piece.color):
                        break

                    # TODO: Need to implement boulder here to add square + break, also blocks diagonals in the middle intersection

                    # append possible squares
                    final_piece = self.squares[possible_square_row][possible_square_col].piece
                    squares.append(Square(possible_square_row, possible_square_col, final_piece))

                    # has enemy piece = break, empty = continue looping
                    if self.squares[possible_square_row][possible_square_col].has_enemy_piece(piece.color):
                        break

                # not in range
                else: break

                # incrementing incrs
                possible_square_row += row_incr
                possible_square_col += col_incr

        # after looping through all incrs, return the list of squares
        return squares

    def straightline_of_sight_squares(self, row, col, incrs):
        squares = []

        for incr in incrs:
            row_incr, col_incr = incr
            possible_square_row = row + row_incr
            possible_square_col = col + col_incr

            while True:
                if Square.in_range(possible_square_row, possible_square_col):
                    # append possible squares
                    final_piece = self.squares[possible_square_row][possible_square_col].piece
                    squares.append(Square(possible_square_row, possible_square_col, final_piece))

                    # has piece = break
                    # TODO: Need to implement boulder here to block diagonals in the middle intersection
                    if self.squares[possible_square_row][possible_square_col].has_piece():
                        break

                # not in range
                else: break

                # incrementing incrs
                possible_square_row += row_incr
                possible_square_col += col_incr

        # after looping through all incrs, return the list of squares
        return squares

    def update_assassin_squares(self, color):
        for r in self.squares:
            for sq in r:
                if sq.has_team_piece(color):
                    piece = sq.piece

                    if isinstance(piece, Bishop):
                        piece.assassin_squares = []

                        squares = self.straightline_of_sight_squares(sq.row, sq.col, incrs=[
                            (-1, 1), # up-right
                            (1, 1), # down-right
                            (1, -1), # down-left
                            (-1, -1), # up-left
                        ])

                        for square in squares:
                            if square.has_enemy_piece(piece.color):
                                piece.assassin_squares.append(square)

    def update_lines_of_sight(self):
        for r in self.squares:
            for sq in r:
                if sq.has_piece():
                    piece = sq.piece
                    piece.line_of_sight = []
                    row = sq.row
                    col = sq.col

                    if isinstance(piece, Pawn):
                        line_of_sight = [
                            (row-1, col+0), # up
                            (row-1, col+1), # up-right
                            (row+0, col+1),  # right
                            (row+0, col-1), # left
                            (row-1, col-1) # up-left
                        ] if piece.dir == -1 else [
                            (row+1, col+0), # down
                            (row+1, col-1), # down-left
                            (row+0, col-1),  # left
                            (row+0, col+1), # right
                            (row+1, col+1) # down-right
                        ]

                        for square in line_of_sight:
                            square_row, square_col = square
                            if Square.in_range(square_row, square_col):
                                piece.line_of_sight.append(Square(square_row, square_col))

                    elif isinstance(piece, Knight):
                        line_of_sight = [
                            (row-3, col+0), # 3 up
                            (row-3, col+1), # 3 up, 1 right
                            (row-2, col+2), # 2 up, 2 right
                            (row-1, col+3), # 3 right, 1 up
                            (row+0, col+3), # 3 right
                            (row+1, col+3), # 3 right, 1 down
                            (row+2, col+2), # 2 down, 2 right
                            (row+3, col+1), # 3 down, 1 right
                            (row+3, col+0), # 3 down
                            (row+3, col-1), # 3 down, 1 left
                            (row+2, col-2), # 2 down, 2 left
                            (row+1, col-3), # 3 left, 1 down
                            (row+0, col-3), # 3 left
                            (row-1, col-3), # 3 left, 1 up
                            (row-2, col-2), # 2 up, 2 left
                            (row-3, col-1), # 3 up, 1 left
                            (row-2, col+0), # 2 up
                            (row-2, col+1), # 2 up, 1 right
                            (row-1, col+1), # 1 up, 1 right
                            (row-1, col+2), # 2 right, 1 up
                            (row+0, col+2), # 2 right
                            (row+1, col+2), # 2 right, 1 down
                            (row+1, col+1), # 1 down, 1 right
                            (row+2, col+1), # 2 down, 1 right
                            (row+2, col+0), # 2 down
                            (row+2, col-1), # 2 down, 1 left
                            (row+1, col-1), # 1 down, 1 left
                            (row+1, col-2), # 2 left, 1 down
                            (row+0, col-2), # 2 left
                            (row-1, col-2), # 2 left, 1 up
                            (row-1, col-1), # 1 up, 1 left
                            (row-2, col-1), # 2 up, 1 left
                            (row-1, col+0), # 1 up
                            (row+0, col+1), # 1 right
                            (row+1, col+0), # 1 down
                            (row+0, col-1), # 1 left
                        ]

                        for square in line_of_sight:
                            square_row, square_col = square
                            if Square.in_range(square_row, square_col):
                                piece.line_of_sight.append(Square(square_row, square_col))

                    elif isinstance(piece, Bishop):
                        incrs = [
                            (-1, 1), # up-right
                            (1, 1),  # down-right
                            (1, -1), # down-left
                            (-1, -1) # up-left
                        ]

                        piece.line_of_sight = self.straightline_of_sight_squares(row, col, incrs)

                    elif isinstance(piece, Rook):
                        initial_squares = [
                            (row-1, col+0), # up
                            (row+0, col+1), # right
                            (row+1, col+0), # down
                            (row+0, col-1)  # left
                        ]

                        incr_pairs = [
                            [(0, 1), (0, -1)], # up: right, left
                            [(1, 0), (-1, 0)], # right: down, up
                            [(0, -1), (0, 1)], # down: left, right
                            [(-1, 0), (1, 0)]  # left: up, down
                        ]

                        indices_to_remove = []

                        for i in range(len(initial_squares)):
                            initial_row, initial_col = initial_squares[i]
                            if Square.in_range(initial_row, initial_col) and self.squares[initial_row][initial_col].isempty():
                                piece.line_of_sight.append(Square(initial_row, initial_col))
                            else:
                                indices_to_remove.append(i)

                        indices_to_remove.sort(reverse=True)

                        for i in range(len(indices_to_remove)):
                            index_to_remove = indices_to_remove[i]
                            initial_squares.remove(initial_squares[index_to_remove])
                            incr_pairs.remove(incr_pairs[index_to_remove])

                        for i in range(len(initial_squares)):
                            initial_row, initial_col = initial_squares[i]
                            incr_pair = incr_pairs[i]
                            squares = self.straightline_of_sight_squares(initial_row, initial_col, incr_pair)
                            piece.line_of_sight[len(piece.line_of_sight):] = squares[:]

                    elif isinstance(piece, Queen):
                        incrs = [
                            (-1, 0), # up
                            (-1, 1), # up-right
                            (0, 1),  # right
                            (1, 1),  # down-right
                            (1, 0),  # down
                            (1, -1), # down-left
                            (0, -1), # left
                            (-1, -1) # up-left
                        ]

                        piece.line_of_sight = self.straightline_of_sight_squares(row, col, incrs)

                    elif isinstance(piece, King):
                        line_of_sight = [
                            (row-1, col+0), # up
                            (row-1, col+1), # up-right
                            (row+0, col+1),  # right
                            (row+1, col+1),  # down-right
                            (row+1, col+0),  # down
                            (row+1, col-1), # down-left
                            (row+0, col-1), # left
                            (row-1, col-1) # up-left
                        ]

                        for square in line_of_sight:
                            square_row, square_col = square
                            if Square.in_range(square_row, square_col):
                                piece.line_of_sight.append(Square(square_row, square_col))

    def calc_moves_v0(self, piece, row, col, bool=True):

        '''
            Calculate all the possible (valid) moves of an specific piece on a specific position
        '''
        
        def pawn_moves():
            # steps
            steps = 1 if piece.moved else 2

            # vertical moves
            start = row + piece.dir
            end = row + (piece.dir * (1 + steps))
            for possible_move_row in range(start, end, piece.dir):
                if Square.in_range(possible_move_row):
                    if self.squares[possible_move_row][col].isempty():
                        # create initial and final move squares
                        initial = Square(row, col)
                        final = Square(possible_move_row, col)
                        # create a new move
                        move = Move(initial, final)

                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                        else:
                            # append new move
                            piece.add_move(move)
                    # blocked
                    else: break
                # not in range
                else: break

            # diagonal moves
            possible_move_row = row + piece.dir
            possible_move_cols = [col-1, col+1]
            for possible_move_col in possible_move_cols:
                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                        # create initial and final move squares
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a new move
                        move = Move(initial, final)
                        
                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                        else:
                            # append new move
                            piece.add_move(move)

            # en passant moves
            r = 3 if piece.color == 'white' else 4
            fr = 2 if piece.color == 'white' else 5
            # left en pessant
            if Square.in_range(col-1) and row == r:
                if self.squares[row][col-1].has_enemy_piece(piece.color):
                    p = self.squares[row][col-1].piece
                    if isinstance(p, Pawn):
                        if p.en_passant:
                            # create initial and final move squares
                            initial = Square(row, col)
                            final = Square(fr, col-1, p)
                            # create a new move
                            move = Move(initial, final)
                            
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)
            
            # right en pessant
            if Square.in_range(col+1) and row == r:
                if self.squares[row][col+1].has_enemy_piece(piece.color):
                    p = self.squares[row][col+1].piece
                    if isinstance(p, Pawn):
                        if p.en_passant:
                            # create initial and final move squares
                            initial = Square(row, col)
                            final = Square(fr, col+1, p)
                            # create a new move
                            move = Move(initial, final)
                            
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)


        def knight_moves():
            # 8 possible moves
            possible_moves = [
                (row-2, col+1),
                (row-1, col+2),
                (row+1, col+2),
                (row+2, col+1),
                (row+2, col-1),
                (row+1, col-2),
                (row-1, col-2),
                (row-2, col-1),
            ]

            for possible_move in possible_moves:
                possible_move_row, possible_move_col = possible_move

                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        # create squares of the new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create new move
                        move = Move(initial, final)
                        
                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                            else: break
                        else:
                            # append new move
                            piece.add_move(move)

        def straightline_moves(incrs):
            for incr in incrs:
                row_incr, col_incr = incr
                possible_move_row = row + row_incr
                possible_move_col = col + col_incr

                while True:
                    if Square.in_range(possible_move_row, possible_move_col):
                        # create squares of the possible new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a possible new move
                        move = Move(initial, final)

                        # empty = continue looping
                        if self.squares[possible_move_row][possible_move_col].isempty():
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)

                        # has enemy piece = add move + break
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)
                            break

                        # has team piece = break
                        elif self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color):
                            break
                    
                    # not in range
                    else: break

                    # incrementing incrs
                    possible_move_row = possible_move_row + row_incr
                    possible_move_col = possible_move_col + col_incr

        def king_moves():
            adjs = [
                (row-1, col+0), # up
                (row-1, col+1), # up-right
                (row+0, col+1), # right
                (row+1, col+1), # down-right
                (row+1, col+0), # down
                (row+1, col-1), # down-left
                (row+0, col-1), # left
                (row-1, col-1), # up-left
            ]

            # normal moves
            for possible_move in adjs:
                possible_move_row, possible_move_col = possible_move

                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        # create squares of the new move
                        initial = Square(row, col)
                        final = Square(possible_move_row, possible_move_col) # piece=piece
                        # create new move
                        move = Move(initial, final)
                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                            else: break
                        else:
                            # append new move
                            piece.add_move(move)

            # castling moves
            if not piece.moved:
                # queen castling
                left_rook = self.squares[row][0].piece
                if isinstance(left_rook, Rook):
                    if not left_rook.moved:
                        for c in range(1, 4):
                            # castling is not possible because there are pieces in between ?
                            if self.squares[row][c].has_piece():
                                break

                            if c == 3:
                                # adds left rook to king
                                piece.left_rook = left_rook

                                # rook move
                                initial = Square(row, 0)
                                final = Square(row, 3)
                                moveR = Move(initial, final)

                                # king move
                                initial = Square(row, col)
                                final = Square(row, 2)
                                moveK = Move(initial, final)

                                # check potencial checks
                                if bool:
                                    if not self.in_check(piece, moveK) and not self.in_check(left_rook, moveR):
                                        # append new move to rook
                                        left_rook.add_move(moveR)
                                        # append new move to king
                                        piece.add_move(moveK)
                                else:
                                    # append new move to rook
                                    left_rook.add_move(moveR)
                                    # append new move king
                                    piece.add_move(moveK)

                # king castling
                right_rook = self.squares[row][7].piece
                if isinstance(right_rook, Rook):
                    if not right_rook.moved:
                        for c in range(5, 7):
                            # castling is not possible because there are pieces in between ?
                            if self.squares[row][c].has_piece():
                                break

                            if c == 6:
                                # adds right rook to king
                                piece.right_rook = right_rook

                                # rook move
                                initial = Square(row, 7)
                                final = Square(row, 5)
                                moveR = Move(initial, final)

                                # king move
                                initial = Square(row, col)
                                final = Square(row, 6)
                                moveK = Move(initial, final)

                                # check potencial checks
                                if bool:
                                    if not self.in_check(piece, moveK) and not self.in_check(right_rook, moveR):
                                        # append new move to rook
                                        right_rook.add_move(moveR)
                                        # append new move to king
                                        piece.add_move(moveK)
                                else:
                                    # append new move to rook
                                    right_rook.add_move(moveR)
                                    # append new move king
                                    piece.add_move(moveK)

        if isinstance(piece, Pawn): 
            pawn_moves()

        elif isinstance(piece, Knight): 
            knight_moves()

        elif isinstance(piece, Bishop): 
            straightline_moves([
                (-1, 1), # up-right
                (-1, -1), # up-left
                (1, 1), # down-right
                (1, -1), # down-left
            ])

        elif isinstance(piece, Rook): 
            straightline_moves([
                (-1, 0), # up
                (0, 1), # right
                (1, 0), # down
                (0, -1), # left
            ])

        elif isinstance(piece, Queen): 
            straightline_moves([
                (-1, 1), # up-right
                (-1, -1), # up-left
                (1, 1), # down-right
                (1, -1), # down-left
                (-1, 0), # up
                (0, 1), # right
                (1, 0), # down
                (0, -1) # left
            ])

        elif isinstance(piece, King): 
            king_moves()

    # Status:
    # King: Need to implement sword
    # Pawn (Swordsman): Fully Functional
    # Rook (Chariot): Fully Functional
    # Knight (Hippogriff): Fully Functional
    # Bishop (Assassin): Fully Functional
    # Queen: Spells done, need to implement transformation

    # def calc_moves(self, piece, row, col, bool=True):
    def king_moves(self, piece, row, col):
        # not todo: Implement saving the queen after she is captured
        # TODO: Implement the king's sword
        adjs = [
            (row-1, col+0), # up
            (row-1, col+1), # up-right
            (row+0, col+1), # right
            (row+1, col+1), # down-right
            (row+1, col+0), # down
            (row+1, col-1), # down-left
            (row+0, col-1), # left
            (row-1, col-1), # up-left
        ]

        # normal moves
        for possible_move in adjs:
            possible_move_row, possible_move_col = possible_move

            if Square.in_range(possible_move_row, possible_move_col):
                # if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                # create squares of the new move
                initial = Square(row, col)
                final = Square(possible_move_row, possible_move_col) # piece=piece
                # create new move
                move = Move(initial, final)
                # append new move
                piece.add_move(move)

    def queen_moves(self, piece, row, col):
        # not todo: Implement jail after queen is captured, if in jail cannot move or be captured
        # TODO: Implement transformation
        adjs = [
            (row-1, col+0), # up
            (row-1, col+1), # up-right
            (row+0, col+1), # right
            (row+1, col+1), # down-right
            (row+1, col+0), # down
            (row+1, col-1), # down-left
            (row+0, col-1), # left
            (row-1, col-1), # up-left
        ]

        # normal moves
        for possible_move in adjs:
            possible_move_row, possible_move_col = possible_move

            if Square.in_range(possible_move_row, possible_move_col):
                if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                    # create squares of the new move
                    initial = Square(row, col)
                    final = Square(possible_move_row, possible_move_col) # piece=piece
                    # create new move
                    move = Move(initial, final)
                    # append new move
                    piece.add_move(move)

    def queen_moves_enemy(self, enemy_piece, row, col):
        queen = None
        enemy_queen = None

        for r in self.squares:
            for sq in r:
                if sq.has_enemy_piece(enemy_piece.color) and isinstance(sq.piece, Queen):
                    queen = sq.piece
                elif sq.has_team_piece(enemy_piece.color) and isinstance(sq.piece, Queen):
                    enemy_queen = sq.piece

        if queen and self.squares[row][col] in queen.line_of_sight:
            if enemy_queen:
                if isinstance(enemy_piece, Queen) or self.squares[row][col] in enemy_queen.line_of_sight:
                    return

            args = [enemy_piece, row, col]

            if (isinstance(enemy_piece, King)):
                self.king_moves(*args)
            elif (isinstance(enemy_piece, Rook)):
                self.rook_moves(*args)
            elif (isinstance(enemy_piece, Bishop)):
                self.bishop_moves(*args)
            elif (isinstance(enemy_piece, Knight)):
                self.knight_moves(*args)
            elif (isinstance(enemy_piece, Pawn)):
                self.pawn_moves(*args)

    def rook_moves(self, piece, row, col):
        inits = [
            (-1, 0), # up
            (0, 1), # right
            (1, 0), # down
            (0, -1), # left
        ]

        for i in range(len(inits)):
            init = inits[i]
            row_init, col_init = init
            possible_init_row = row + row_init
            possible_init_col = col + col_init

            if Square.in_range(possible_init_row, possible_init_col):
                if self.squares[possible_init_row][possible_init_col].has_team_piece(piece.color):
                    continue

                if self.squares[possible_init_row][possible_init_col].has_enemy_piece(piece.color):
                    # create squares of the possible new move
                    initial = Square(row, col)
                    final_piece = self.squares[possible_init_row][possible_init_col].piece
                    final = Square(possible_init_row, possible_init_col, final_piece)
                    # create a possible new move
                    move = Move(initial, final)
                    # append a new move
                    piece.add_move(move)
                    continue

                # create squares of the possible new move
                initial = Square(row, col)
                final = Square(possible_init_row, possible_init_col)
                # create a possible new move
                init_move = Move(initial, final)
                # append a new move
                piece.add_move(init_move)

                incrs = [inits[(i + 1) % 4], inits[(i + 3) % 4]]
                # incrs = [x if condition else y, a if condition else b]

                for incr in incrs:
                    row_incr, col_incr = incr
                    possible_move_row = possible_init_row + row_incr
                    possible_move_col = possible_init_col + col_incr

                    while True:
                        if not(Square.in_range(possible_move_row, possible_move_col)):
                            # not in range
                            break

                        # create squares of the possible new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a possible new move
                        move = Move(initial, final)

                        # empty = continue looping
                        if self.squares[possible_move_row][possible_move_col].isempty():
                            # # check potencial checks
                            # if bool:
                            #     if not self.in_check(piece, move):
                            #         # append new move
                            #         piece.add_move(move)
                            # else:
                            #     # append new move
                            piece.add_move(move)

                        # has enemy piece = add move + break
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                            # # check potencial checks
                            # if bool:
                            #     if not self.in_check(piece, move):
                            #         # append new move
                            #         piece.add_move(move)
                            # else:
                            #     # append new move
                            piece.add_move(move)
                            break

                        # has team piece = break
                        elif self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color):
                            break

                        # incrementing incrs
                        possible_move_row = possible_move_row + row_incr
                        possible_move_col = possible_move_col + col_incr

    def bishop_moves(self, piece, row, col):
        # Temporarily removing the piece from the board
        # to update new lines of sight, then put it back
        self.squares[row][col].piece = None

        self.update_lines_of_sight()

        # Putting the piece back here
        self.squares[row][col].piece = piece

        enemy_squares = []

        for r in self.squares:
            for sq in r:
                if sq.has_enemy_piece(piece.color):
                    enemy_piece = sq.piece
                    enemy_squares[len(enemy_squares):] = enemy_piece.line_of_sight[:]

        for r in self.squares:
            for sq in r:
                if sq.isempty():
                    if sq not in enemy_squares:
                        # create initial and final move squares
                        initial = Square(row, col)
                        final = Square(sq.row, sq.col)
                        # create a new move
                        move = Move(initial, final)
                        piece.add_move(move)

        if self.last_move:
            last_move_initial = self.last_move.initial
            last_move_final = self.last_move.final
            last_move_piece = self.squares[last_move_final.row][last_move_final.col].piece

            if last_move_initial in piece.assassin_squares and last_move_initial != last_move_final:
                # create initial and final move squares
                initial = Square(row, col)
                final_piece = last_move_piece
                final = Square(last_move_final.row, last_move_final.col, final_piece)
                # create a new move
                move = Move(initial, final)
                piece.add_move(move)

    def knight_moves(self, piece, row, col):
        moves = [
            (row-3, col+0), # 3 up
            (row-3, col+1), # 3 up, 1 right
            (row-2, col+2), # 2 up, 2 right
            (row-1, col+3), # 3 right, 1 up
            (row+0, col+3), # 3 right
            (row+1, col+3), # 3 right, 1 down
            (row+2, col+2), # 2 down, 2 right
            (row+3, col+1), # 3 down, 1 right
            (row+3, col+0), # 3 down
            (row+3, col-1), # 3 down, 1 left
            (row+2, col-2), # 2 down, 2 left
            (row+1, col-3), # 3 left, 1 down
            (row+0, col-3), # 3 left
            (row-1, col-3), # 3 left, 1 up
            (row-2, col-2), # 2 up, 2 left
            (row-3, col-1), # 3 up, 1 left
        ]

        # normal moves
        for i in range(len(moves)):
            possible_move_row, possible_move_col = moves[i]

            if Square.in_range(possible_move_row, possible_move_col):
                if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                    # create squares of the new move
                    initial = Square(row, col)
                    final = Square(possible_move_row, possible_move_col) # piece=piece
                    # create new move
                    move = Move(initial, final)
                    # append new move
                    piece.add_move(move)

    def pawn_moves(self, piece, row, col):
        # steps
        steps = 1

        # vertical moves
        start = row + piece.dir
        end = row + (piece.dir * (1 + steps))
        for possible_move_row in range(start, end, piece.dir):
            if Square.in_range(possible_move_row):
                if self.squares[possible_move_row][col].isempty_or_enemy(piece.color):
                    # create initial and final move squares
                    initial = Square(row, col)

                    if self.squares[possible_move_row][col].isempty():
                        final = Square(possible_move_row, col)
                    else:
                        final_piece = self.squares[possible_move_row][col].piece
                        final = Square(possible_move_row, col, final_piece)
                    # create a new move
                    move = Move(initial, final)

                    # # check potencial checks
                    # if bool:
                    #     if not self.in_check(piece, move):
                    #         # append new move
                    #         piece.add_move(move)
                    # else:
                    #     # append new move
                    piece.add_move(move)
                # blocked
                else: break
            # not in range
            else: break

        # horizontal moves
        possible_move_cols = [col-1, col+1]
        for possible_move_col in possible_move_cols:
            if Square.in_range(row, possible_move_col):
                if self.squares[row][possible_move_col].isempty():
                    # create initial and final move squares
                    initial = Square(row, col)
                    final = Square(row, possible_move_col)
                    # create a new move
                    move = Move(initial, final)

                    # # check potencial checks
                    # if bool:
                    #     if not self.in_check(piece, move):
                    #         # append new move
                    #         piece.add_move(move)
                    # else:
                    #     # append new move
                    piece.add_move(move)

        # diagonal moves
        possible_move_row = row + piece.dir
        possible_move_cols = [col-1, col+1]
        for possible_move_col in possible_move_cols:
            if Square.in_range(possible_move_row, possible_move_col):
                if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                    # create initial and final move squares
                    initial = Square(row, col)
                    final_piece = self.squares[possible_move_row][possible_move_col].piece
                    final = Square(possible_move_row, possible_move_col, final_piece)
                    # create a new move
                    move = Move(initial, final)

                    # # check potencial checks
                    # if bool:
                    #     if not self.in_check(piece, move):
                    #         # append new move
                    #         piece.add_move(move)
                    # else:
                    #     # append new move
                    piece.add_move(move)

    # possible_move_rows = [0, 1, 2, 3, 4, 5, 6, 7]
    # possible_move_cols = [0, 1, 2, 3, 4, 5, 6, 7]
    # for possible_move_row in possible_move_rows:
    #     for possible_move_col in possible_move_cols:
    #         if Square.in_range(possible_move_row, possible_move_col):
    #             if row != possible_move_row or col != possible_move_col:
    #                 if not(self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color)):
    #                     # create initial and final move squares
    #                     initial = Square(row, col)

    #                     final_piece = None

    #                     if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
    #                         final_piece = self.squares[possible_move_row][possible_move_col].piece

    #                     if final_piece:
    #                         final = Square(possible_move_row, possible_move_col, final_piece)
    #                     else:
    #                         final = Square(possible_move_row, possible_move_col)

    #                     # create a new move
    #                     move = Move(initial, final)
    #                     piece.add_move(move)

    def _create(self):
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[row][col] = Square(row, col)

    def _add_pieces(self, color):
        row_pawn, row_other = (6, 7) if color == 'white' else (1, 0)

        # pawns
        for col in range(COLS):
            self.squares[row_pawn][col] = Square(row_pawn, col, Pawn(color))

        # knights
        self.squares[row_other][3] = Square(row_other, 3, Knight(color))
        self.squares[row_other][4] = Square(row_other, 4, Knight(color))

        # bishops
        self.squares[row_other][0] = Square(row_other, 0, Bishop(color))
        self.squares[row_other][7] = Square(row_other, 7, Bishop(color))

        # rooks
        self.squares[row_other][2] = Square(row_other, 2, Rook(color))
        self.squares[row_other][5] = Square(row_other, 5, Rook(color))

        # white queen/black king
        self.squares[row_other][1] = Square(row_other, 1, Queen(color)) if color == 'white' else Square(row_other, 1, King(color))

        # white king/black queen
        self.squares[row_other][6] = Square(row_other, 6, King(color)) if color == 'white' else Square(row_other, 6, Queen(color))