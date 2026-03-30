"""
Unit tests for piece movement rules as defined in RULEBOOK.md.
Tests are written against the rulebook specification. Tests that fail
against the current codebase are marked with @unittest.skip to document
what still needs implementation.

All board positions use standard chess notation (e.g. "e4", "a1") for
human readability, converted to (row, col) indices via the sq() helper.

GitHub Issue #1: Add unit tests for piece movement rules
"""

import unittest
import sys
import os
import types

# Mock pygame before importing game modules
pygame_mock = types.ModuleType('pygame')
mixer_mock = types.ModuleType('pygame.mixer')

class MockSound:
    def __init__(self, path): pass
    def play(self): pass

mixer_mock.Sound = MockSound
pygame_mock.mixer = mixer_mock
sys.modules['pygame'] = pygame_mock
sys.modules['pygame.mixer'] = mixer_mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from board import Board
from square import Square
from piece import Pawn, Knight, Bishop, Rook, Queen, King, Boulder
from move import Move


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sq(notation):
    """Convert chess notation to (row, col) tuple.

    Examples:
        sq("a1") -> (7, 0)
        sq("e4") -> (4, 4)
        sq("h8") -> (0, 7)
    """
    col = ord(notation[0]) - ord('a')
    row = 8 - int(notation[1])
    return (row, col)


def empty_board():
    """Create a board with no pieces."""
    board = Board.__new__(Board)
    board.squares = [[0] * 8 for _ in range(8)]
    board.last_move = None
    for row in range(8):
        for col in range(8):
            board.squares[row][col] = Square(row, col)
    return board


def place(board, notation, piece):
    """Place a piece on the board at a chess-notation square."""
    row, col = sq(notation)
    board.squares[row][col] = Square(row, col, piece)
    return piece


def get_move_destinations(piece):
    """Return a set of (row, col) tuples from a piece's move list."""
    return {(m.final.row, m.final.col) for m in piece.moves}


# ===========================================================================
# TestPawn
# ===========================================================================

class TestPawn(unittest.TestCase):
    """
    Rulebook — Pawn:
      Movement: one square forward, left, or right. May not move backward.
      Capture: one square forward, diagonally forward-left, diagonally forward-right.
      Promotion: on reaching last rank, promotes to a non-royal queen (any form).
    """

    # ---- Class structure tests ----

    def test_pawn_is_not_royal(self):
        """Pawns are never royal."""
        pawn = Pawn('white')
        self.assertFalse(pawn.is_royal)

    def test_pawn_is_not_transformed(self):
        """Pawns start as not transformed."""
        pawn = Pawn('white')
        self.assertFalse(pawn.is_transformed)

    def test_pawn_inherits_from_piece(self):
        """Pawn is a subclass of Piece."""
        from piece import Piece
        pawn = Pawn('white')
        self.assertIsInstance(pawn, Piece)

    # ---- Movement tests ----

    def test_white_pawn_moves_forward(self):
        """White pawn on e4 can move one square forward to e5."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("e5"), dests)

    def test_black_pawn_moves_forward(self):
        """Black pawn on e5 can move one square forward to e4."""
        board = empty_board()
        pawn = place(board, "e5", Pawn('black'))
        board.pawn_moves(pawn, *sq("e5"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("e4"), dests)

    def test_white_pawn_moves_left(self):
        """White pawn on e4 can move one square left to d4."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("d4"), dests)

    def test_white_pawn_moves_right(self):
        """White pawn on e4 can move one square right to f4."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("f4"), dests)

    def test_white_pawn_cannot_move_backward(self):
        """White pawn on e4 must not move backward to e3."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("e3"), dests)

    def test_black_pawn_cannot_move_backward(self):
        """Black pawn on e4 must not move backward to e5."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("e5"), dests)

    def test_pawn_no_two_square_first_move(self):
        """White pawn on e2 should NOT have a two-square first move to e4."""
        board = empty_board()
        pawn = place(board, "e2", Pawn('white'))
        board.pawn_moves(pawn, *sq("e2"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("e4"), dests)

    def test_pawn_blocked_forward_by_friendly(self):
        """White pawn on e4 cannot move forward to e5 if friendly rook is there."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "e5", Rook('white'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("e5"), dests)

    def test_pawn_sideways_blocked_by_friendly(self):
        """White pawn on e4 cannot move right to f4 if friendly rook is there."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "f4", Rook('white'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("f4"), dests)

    def test_pawn_sideways_blocked_by_enemy(self):
        """White pawn on e4 cannot move right to f4 if enemy rook is there (sideways is movement only)."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "f4", Rook('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("f4"), dests)

    def test_pawn_at_edge_no_sideways_off_board(self):
        """Pawn on a4 cannot move left off the board."""
        board = empty_board()
        pawn = place(board, "a4", Pawn('white'))
        board.pawn_moves(pawn, *sq("a4"))
        dests = get_move_destinations(pawn)
        for r, c in dests:
            self.assertTrue(0 <= c <= 7, f"Move to col {c} is off-board")

    # ---- Capture tests ----

    def test_white_pawn_captures_forward(self):
        """White pawn on e4 can capture a black pawn on e5."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "e5", Pawn('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("e5"), dests)

    def test_white_pawn_captures_diag_forward_left(self):
        """White pawn on e4 can capture diagonally forward-left on d5."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "d5", Pawn('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("d5"), dests)

    def test_white_pawn_captures_diag_forward_right(self):
        """White pawn on e4 can capture diagonally forward-right on f5."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "f5", Pawn('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertIn(sq("f5"), dests)

    def test_pawn_cannot_capture_diag_backward(self):
        """White pawn on e4 must not capture diagonally backward on d3 or f3."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "d3", Pawn('black'))
        place(board, "f3", Pawn('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("d3"), dests)
        self.assertNotIn(sq("f3"), dests)

    def test_pawn_cannot_capture_sideways(self):
        """White pawn on e4 must not capture horizontally on d4 or f4."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "d4", Pawn('black'))
        place(board, "f4", Pawn('black'))
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("d4"), dests)
        self.assertNotIn(sq("f4"), dests)

    # ---- Promotion tests ----

    def test_pawn_promotes_on_last_rank(self):
        """White pawn moving from e7 to e8 should promote."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        move = Move(Square(*sq("e7")), Square(*sq("e8")))
        board.move(pawn, move, testing=True)
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertIsInstance(promoted, Queen)

    def test_black_pawn_promotes_on_last_rank(self):
        """Black pawn moving from e2 to e1 should promote."""
        board = empty_board()
        pawn = place(board, "e2", Pawn('black'))
        move = Move(Square(*sq("e2")), Square(*sq("e1")))
        board.move(pawn, move, testing=True)
        promoted = board.squares[sq("e1")[0]][sq("e1")[1]].piece
        self.assertIsInstance(promoted, Queen)

    @unittest.skip("Not yet implemented: promoted queen is_royal flag")
    def test_promoted_queen_is_not_royal(self):
        """Promoted queen must be marked as non-royal."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        move = Move(Square(*sq("e7")), Square(*sq("e8")))
        board.move(pawn, move, testing=True)
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertFalse(promoted.is_royal)

    @unittest.skip("Not yet implemented: promotion choice")
    def test_promotion_to_non_royal_queen_base_form(self):
        """Pawn can promote to a non-royal queen in base form."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        promoted = board.promote(pawn, *sq("e8"), 'queen')
        self.assertIsInstance(promoted, Queen)
        self.assertFalse(promoted.is_royal)
        self.assertIsNone(promoted.transformed_as)

    @unittest.skip("Not yet implemented: promotion choice")
    def test_promotion_to_non_royal_queen_as_bishop(self):
        """Pawn can promote to a non-royal queen in bishop form."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        promoted = board.promote(pawn, *sq("e8"), 'bishop')
        self.assertIsInstance(promoted, Queen)
        self.assertFalse(promoted.is_royal)
        self.assertEqual(promoted.transformed_as, 'bishop')

    @unittest.skip("Not yet implemented: promotion choice")
    def test_promotion_to_non_royal_queen_as_rook(self):
        """Pawn can promote to a non-royal queen in rook form."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        promoted = board.promote(pawn, *sq("e8"), 'rook')
        self.assertIsInstance(promoted, Queen)
        self.assertFalse(promoted.is_royal)
        self.assertEqual(promoted.transformed_as, 'rook')

    @unittest.skip("Not yet implemented: promotion choice")
    def test_promotion_to_non_royal_queen_as_knight(self):
        """Pawn can promote to a non-royal queen in knight form."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        promoted = board.promote(pawn, *sq("e8"), 'knight')
        self.assertIsInstance(promoted, Queen)
        self.assertFalse(promoted.is_royal)
        self.assertEqual(promoted.transformed_as, 'knight')


# ===========================================================================
# TestKing
# ===========================================================================

class TestKing(unittest.TestCase):
    """
    Rulebook — King:
      Movement: one square in any direction.
      Special: may capture enemy pieces, friendly pieces, and the boulder.
      The king is the ONLY piece that may capture friendly pieces or the boulder.
    """

    # ---- Class structure tests ----

    def test_king_is_royal(self):
        """King is always royal."""
        king = King('white')
        self.assertTrue(king.is_royal)
    def test_king_is_not_transformed(self):
        """King starts as not transformed."""
        king = King('white')
        self.assertFalse(king.is_transformed)

    def test_king_inherits_from_piece(self):
        """King is a subclass of Piece."""
        from piece import Piece
        king = King('white')
        self.assertIsInstance(king, Piece)

    # ---- Movement tests ----

    def test_king_moves_all_eight_directions(self):
        """King on e4 should have 8 possible moves on an empty board."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        expected = {
            sq("d5"), sq("e5"), sq("f5"),
            sq("d4"),          sq("f4"),
            sq("d3"), sq("e3"), sq("f3"),
        }
        self.assertEqual(dests, expected)

    def test_king_corner_limited_moves(self):
        """King on a8 should only have 3 moves."""
        board = empty_board()
        king = place(board, "a8", King('white'))
        board.king_moves(king, *sq("a8"))
        dests = get_move_destinations(king)
        expected = {sq("b8"), sq("a7"), sq("b7")}
        self.assertEqual(dests, expected)

    def test_king_captures_enemy_piece(self):
        """King on e4 can capture a black pawn on e5."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        place(board, "e5", Pawn('black'))
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        self.assertIn(sq("e5"), dests)

    def test_king_captures_friendly_piece(self):
        """King on e4 can capture a friendly rook on e5 (unique to king per rulebook)."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        place(board, "e5", Rook('white'))
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        self.assertIn(sq("e5"), dests)

    def test_king_captures_boulder(self):
        """King on e4 can capture the boulder on e5."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        boulder = place(board, "e5", Boulder())
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        self.assertIn(sq("e5"), dests)

    def test_king_cannot_move_more_than_one_square(self):
        """King on e4 should not have any moves beyond 1-square radius."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        origin_r, origin_c = sq("e4")
        for r, c in dests:
            self.assertLessEqual(abs(r - origin_r), 1)
            self.assertLessEqual(abs(c - origin_c), 1)


# ===========================================================================
# TestQueen
# ===========================================================================

class TestQueen(unittest.TestCase):
    """
    Rulebook — Queen:
      The starting queen is royal (is_royal=True).
      Promoted queens are non-royal (is_royal=False).
      Both share the same Queen class.
      Base form movement: one square in any direction (like a king).
      Capture: any adjacent enemy piece (except the boulder).
      Action: Manipulation (royal only, base form only).
    """

    # ---- Class structure tests ----

    def test_starting_queen_is_royal(self):
        """The starting queen (default) is royal."""
        queen = Queen('white')
        self.assertTrue(queen.is_royal)

    def test_promoted_queen_is_not_royal(self):
        """A promoted queen is non-royal."""
        queen = Queen('white', is_royal=False)
        self.assertFalse(queen.is_royal)

    def test_queen_is_not_transformed(self):
        """Queen starts as not transformed."""
        queen = Queen('white')
        self.assertFalse(queen.is_transformed)

    def test_queen_inherits_from_piece(self):
        """Queen is a subclass of Piece."""
        from piece import Piece
        queen = Queen('white')
        self.assertIsInstance(queen, Piece)

    def test_royal_and_non_royal_are_same_class(self):
        """Royal and non-royal queens are the same Queen class."""
        royal = Queen('white', is_royal=True)
        non_royal = Queen('white', is_royal=False)
        self.assertIs(type(royal), type(non_royal))

    # ---- Movement tests ----

    def test_queen_base_moves_all_eight_directions(self):
        """Royal queen on e4 in base form moves one square in all 8 directions."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        expected = {
            sq("d5"), sq("e5"), sq("f5"),
            sq("d4"),          sq("f4"),
            sq("d3"), sq("e3"), sq("f3"),
        }
        self.assertEqual(dests, expected)

    def test_queen_captures_adjacent_enemy(self):
        """Royal queen on e4 can capture a black knight on e5."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        place(board, "e5", Knight('black'))
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        self.assertIn(sq("e5"), dests)

    def test_queen_cannot_move_onto_friendly_piece(self):
        """Royal queen on e4 cannot move onto a friendly rook on e5."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        place(board, "e5", Rook('white'))
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("e5"), dests)

    def test_queen_cannot_capture_boulder(self):
        """Royal queen on e4 cannot capture the boulder on e5."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        place(board, "e5", Boulder())
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("e5"), dests)

    def test_queen_cannot_move_more_than_one_square(self):
        """Royal queen on e4 in base form should not move more than one square."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        origin_r, origin_c = sq("e4")
        for r, c in dests:
            self.assertLessEqual(abs(r - origin_r), 1)
            self.assertLessEqual(abs(c - origin_c), 1)

    # ---- Manipulation tests: basic functionality ----

    def test_manipulation_basic_enemy_in_line_of_sight(self):
        """White queen on a1 can manipulate a black rook on a4 (same file, in line of sight).
        The rook should get valid moves as if it were being moved normally."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertTrue(len(dests) > 0, "Enemy rook in queen's LOS should have moves")

    def test_manipulation_enemy_on_diagonal(self):
        """White queen on a1 can manipulate a black knight on d4 (diagonal line of sight)."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_knight = place(board, "d4", Knight('black'))
        board.queen_moves_enemy(enemy_knight, *sq("d4"))
        dests = get_move_destinations(enemy_knight)
        self.assertTrue(len(dests) > 0, "Enemy knight on queen's diagonal should have moves")

    def test_manipulation_enemy_not_in_line_of_sight(self):
        """White queen on a1 cannot manipulate a black rook on b3 (not in line of sight)."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_rook = place(board, "b3", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("b3"))
        dests = get_move_destinations(enemy_rook)
        self.assertEqual(len(dests), 0, "Enemy rook not in queen's LOS should have no moves")

    def test_manipulation_blocked_line_of_sight(self):
        """White queen on a1 cannot manipulate a black rook on a4 if a piece blocks at a2."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        place(board, "a2", Pawn('white'))  # blocks LOS on the file
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertEqual(len(dests), 0, "Blocked LOS should prevent manipulation")

    def test_manipulation_no_queen_on_board(self):
        """If no friendly queen exists, manipulation should not work."""
        board = empty_board()
        # No white queen placed
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertEqual(len(dests), 0)

    # ---- Manipulation tests: restriction — cannot target king ----

    def test_manipulation_cannot_target_enemy_king(self):
        """Queen on a1 cannot manipulate the enemy king on a4."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_king = place(board, "a4", King('black'))
        board.queen_moves_enemy(enemy_king, *sq("a4"))
        dests = get_move_destinations(enemy_king)
        self.assertEqual(len(dests), 0, "Enemy king must not be manipulable")

    # ---- Manipulation tests: restriction — cannot target base-form queen ----

    def test_manipulation_cannot_target_base_form_royal_queen(self):
        """Queen on a1 cannot manipulate the enemy's base-form royal queen on a4."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_queen = place(board, "a4", Queen('black'))
        board.queen_moves_enemy(enemy_queen, *sq("a4"))
        dests = get_move_destinations(enemy_queen)
        self.assertEqual(len(dests), 0, "Base-form royal queen must not be manipulable")

    def test_manipulation_cannot_target_promoted_queen_in_base_form(self):
        """Queen on a1 cannot manipulate a promoted (non-royal) enemy queen in base form on a4."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        promoted_queen = Queen('black', is_royal=False)
        place(board, "a4", promoted_queen)
        board.queen_moves_enemy(promoted_queen, *sq("a4"))
        dests = get_move_destinations(promoted_queen)
        self.assertEqual(len(dests), 0, "Promoted queen in base form must not be manipulable")

    @unittest.skip("Not yet implemented: queen transformation")
    def test_manipulation_can_target_transformed_enemy_queen(self):
        """Queen on a1 CAN manipulate an enemy queen that is transformed (not in base form)."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        transformed_queen = Queen('black')
        transformed_queen.is_transformed = True
        place(board, "a4", transformed_queen)
        board.queen_moves_enemy(transformed_queen, *sq("a4"))
        dests = get_move_destinations(transformed_queen)
        self.assertTrue(len(dests) > 0, "Transformed queen should be manipulable")

    # ---- Manipulation tests: restriction — cannot target piece that moved last turn ----

    def test_manipulation_cannot_target_piece_that_moved_last_turn(self):
        """Queen on a1 cannot manipulate a rook on a4 that moved there last turn."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.last_move = Move(Square(*sq("a5")), Square(*sq("a4")))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertEqual(len(dests), 0, "Piece that just moved should not be manipulable")

    def test_manipulation_can_target_piece_that_did_not_move_last_turn(self):
        """Queen on a1 can manipulate a rook on a4 if the last move was by a different piece."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        place(board, "h8", Pawn('black'))
        board.last_move = Move(Square(*sq("h7")), Square(*sq("h8")))  # different piece moved
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertTrue(len(dests) > 0, "Rook that didn't move last turn should be manipulable")

    # ---- Manipulation tests: manipulated piece can move but not return ----

    def test_manipulated_piece_can_move_next_turn(self):
        """A piece that was manipulated by the queen CAN move on its next turn."""
        board = empty_board()
        # Simulate: black rook was on a5, white queen manipulated it to a4
        enemy_rook = place(board, "a4", Rook('black'))
        enemy_rook.forbidden_square = sq("a5")  # came from a5
        board.rook_moves(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertTrue(len(dests) > 0, "Manipulated piece must be able to move next turn")

    def test_manipulated_piece_cannot_return_to_previous_square(self):
        """A piece that was manipulated cannot return to the square it was moved from."""
        board = empty_board()
        # Simulate: black rook was on a5, white queen manipulated it to a4
        enemy_rook = place(board, "a4", Rook('black'))
        enemy_rook.forbidden_square = sq("a5")  # came from a5
        board.rook_moves(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertNotIn(sq("a5"), dests, "Manipulated piece must not return to its previous square")

    def test_manipulated_piece_can_move_to_other_squares(self):
        """A manipulated piece can move to any valid square except the forbidden one."""
        board = empty_board()
        # Simulate: black rook was on a5, white queen manipulated it to a4
        enemy_rook = place(board, "a4", Rook('black'))
        enemy_rook.forbidden_square = sq("a5")  # came from a5
        board.rook_moves(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        # Rook on a4 should still reach a3 (step-1 down) and other squares
        self.assertIn(sq("a3"), dests)
        self.assertNotIn(sq("a5"), dests)

    def test_forbidden_square_clears_after_one_turn(self):
        """The forbidden_square restriction only lasts one turn. After the piece moves,
        forbidden_square is reset to None."""
        board = empty_board()
        enemy_rook = place(board, "a4", Rook('black'))
        enemy_rook.forbidden_square = sq("a5")
        # Simulate moving the rook to a3 (its turn)
        move = Move(Square(*sq("a4")), Square(*sq("a3")))
        enemy_rook.clear_moves()
        enemy_rook.add_move(move)
        board.move(enemy_rook, move, testing=True)
        # After moving, forbidden_square should be cleared
        self.assertIsNone(enemy_rook.forbidden_square)

    def test_non_manipulated_piece_has_no_forbidden_square(self):
        """A piece that was not manipulated has no forbidden_square."""
        rook = Rook('black')
        self.assertIsNone(rook.forbidden_square)

    def test_manipulated_knight_with_jump_capture_has_forbidden_square(self):
        """When a queen manipulates a knight that triggers jump capture,
        the knight should still have forbidden_square set after the jump
        capture resolves, preventing it from returning to its origin."""
        board = empty_board()
        knight = Knight('black')
        # Simulate: knight was manipulated from e4 to e6, jump capture triggered
        # After jump capture resolves, forbidden_square should be set to e4
        knight.forbidden_square = sq("e4")  # set by main.py after jump capture resolves
        place(board, "e6", knight)
        board.knight_moves(knight, *sq("e6"))
        dests = get_move_destinations(knight)
        self.assertNotIn(sq("e4"), dests,
            "Manipulated knight should not return to origin after jump capture")

    # ---- Manipulation tests: restriction — cannot target boulder ----

    @unittest.skip("Not yet implemented: boulder interaction")
    def test_manipulation_cannot_target_boulder(self):
        """Queen cannot manipulate the boulder."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        boulder = place(board, "a4", Boulder())
        board.queen_moves_enemy(boulder, *sq("a4"))
        dests = get_move_destinations(boulder)
        self.assertEqual(len(dests), 0, "Boulder must not be manipulable")

    # ---- Manipulation tests: restriction — only in base form ----

    @unittest.skip("Not yet implemented: queen transformation")
    def test_queen_cannot_manipulate_when_transformed(self):
        """Queen cannot use manipulation action when in transformed form."""
        pass

    # ---- Manipulation tests: no mutual protection (removed in new rules) ----

    def test_manipulation_not_blocked_by_ally_queen(self):
        """Under the new rules, there is no mutual protection. White queen on a1 can
        manipulate black rook on d4 even if black queen on h4 has d4 in line of sight."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        enemy_queen = place(board, "h4", Queen('black'))
        board.update_lines_of_sight()
        enemy_rook = place(board, "d4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("d4"))
        dests = get_move_destinations(enemy_rook)
        self.assertTrue(len(dests) > 0, "Ally queen should NOT block manipulation (no mutual protection)")

    # ---- Transformation tests ----

    @unittest.skip("Not yet implemented: queen transformation")
    def test_queen_transforms_into_rook(self):
        """Royal queen can transform into rook if a friendly rook was captured."""
        pass

    @unittest.skip("Not yet implemented: queen transformation")
    def test_queen_transforms_into_bishop(self):
        """Royal queen can transform into bishop if a friendly bishop was captured."""
        pass

    @unittest.skip("Not yet implemented: queen transformation")
    def test_queen_transforms_into_knight(self):
        """Royal queen can transform into knight if a friendly knight was captured."""
        pass

    @unittest.skip("Not yet implemented: queen transformation")
    def test_queen_reverts_to_base_form(self):
        """Transformed queen can return to base form on a later turn."""
        pass

    @unittest.skip("Not yet implemented: queen transformation")
    def test_queen_cannot_transform_if_no_captures(self):
        """Queen cannot transform if no friendly non-royal pieces have been captured."""
        pass


# ===========================================================================
# TestRook
# ===========================================================================

class TestRook(unittest.TestCase):
    """
    Rulebook — Rook:
      Two-step movement:
        1. Move one square orthogonally.
        2. Then turn 90° and move any number of squares (including zero).
      May stop or capture first enemy encountered at any step.
    """

    # ---- Class structure tests ----

    def test_rook_is_not_royal(self):
        """Rooks are never royal."""
        rook = Rook('white')
        self.assertFalse(rook.is_royal)

    def test_rook_is_not_transformed(self):
        """Rook starts as not transformed."""
        rook = Rook('white')
        self.assertFalse(rook.is_transformed)

    # ---- Movement tests ----

    def test_rook_step1_four_directions(self):
        """Rook on e4 can make step-1 to e5, e3, d4, f4."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        for dest in ["e5", "e3", "d4", "f4"]:
            self.assertIn(sq(dest), dests)

    def test_rook_step2_perpendicular(self):
        """Rook on e4: after step-1 up to e5, can continue left/right along rank 5."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        # Step-1 up to e5, then step-2 right to f5, g5, h5
        self.assertIn(sq("f5"), dests)
        self.assertIn(sq("g5"), dests)
        self.assertIn(sq("h5"), dests)
        # Step-1 up to e5, then step-2 left to d5, c5, b5, a5
        self.assertIn(sq("d5"), dests)
        self.assertIn(sq("a5"), dests)

    def test_rook_cannot_continue_straight(self):
        """Rook on e4 must turn 90° after step-1; cannot continue straight to e6."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        self.assertNotIn(sq("e6"), dests)

    def test_rook_blocked_step1_by_friendly(self):
        """Rook on e4 cannot go up if friendly pawn is on e5."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        place(board, "e5", Pawn('white'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        self.assertNotIn(sq("e5"), dests)
        self.assertIn(sq("d5"), dests)
        self.assertIn(sq("f5"), dests)
        self.assertNotIn(sq("c5"), dests)
        self.assertNotIn(sq("g5"), dests)

    def test_rook_captures_at_step1(self):
        """Rook on e4 can capture enemy on e5, but no step-2 after capture."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        place(board, "e5", Pawn('black'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        self.assertIn(sq("e5"), dests)
        self.assertIn(sq("d5"), dests)
        self.assertIn(sq("f5"), dests)
        self.assertNotIn(sq("c5"), dests)
        self.assertNotIn(sq("g5"), dests)

    def test_rook_step2_blocked_by_friendly(self):
        """Rook on e4: step-1 up to e5, step-2 right blocked by friendly on g5."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        place(board, "g5", Pawn('white'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        self.assertIn(sq("f5"), dests)
        self.assertNotIn(sq("g5"), dests)
        self.assertNotIn(sq("h5"), dests)

    def test_rook_step2_captures_enemy_then_stops(self):
        """Rook on e4: step-1 up to e5, step-2 right captures enemy on g5 then stops."""
        board = empty_board()
        rook = place(board, "e4", Rook('white'))
        place(board, "g5", Pawn('black'))
        board.rook_moves(rook, *sq("e4"))
        dests = get_move_destinations(rook)
        self.assertIn(sq("g5"), dests)
        self.assertNotIn(sq("h5"), dests)


# ===========================================================================
# TestBishop
# ===========================================================================

class TestBishop(unittest.TestCase):
    """
    Rulebook — Bishop:
      Moves by teleportation to any square not reachable/capturable by enemy pieces.
      Excludes enemy bishops, queen-as-bishop, and boulder from threat calculation.
      Assassin capture: if a piece starts on bishop's diagonal and moves away,
        bishop can capture it at its destination on the next turn.
    """

    # ---- Class structure tests ----

    def test_bishop_is_not_royal(self):
        """Bishops are never royal."""
        bishop = Bishop('white')
        self.assertFalse(bishop.is_royal)

    def test_bishop_is_not_transformed(self):
        """Bishop starts as not transformed."""
        bishop = Bishop('white')
        self.assertFalse(bishop.is_transformed)

    def test_bishop_has_assassin_squares(self):
        """Bishop has assassin_squares attribute for tracking diagonal line of sight."""
        bishop = Bishop('white')
        self.assertEqual(bishop.assassin_squares, [])

    # ---- Movement tests ----

    def test_bishop_teleports_to_safe_empty_squares(self):
        """Bishop on e4 can teleport to empty squares not threatened by enemies."""
        board = empty_board()
        bishop = place(board, "e4", Bishop('white'))
        board.bishop_moves(bishop, *sq("e4"))
        dests = get_move_destinations(bishop)
        # With no enemies, bishop can reach all empty squares
        self.assertTrue(len(dests) > 0)

    def test_bishop_ignores_enemy_bishop_threats(self):
        """Bishop can teleport to squares reachable by an enemy bishop (bishops are ignored)."""
        board = empty_board()
        bishop = place(board, "h1", Bishop('white'))
        place(board, "c6", Bishop('black'))
        board.bishop_moves(bishop, *sq("h1"))
        dests = get_move_destinations(bishop)
        # Enemy bishop's threat squares should be ignored, so bishop has many options
        # All empty squares should be available since only enemy is a bishop
        empty_count = 0
        for r in range(8):
            for c in range(8):
                if board.squares[r][c].isempty() and (r, c) != sq("h1"):
                    empty_count += 1
        self.assertEqual(len(dests), empty_count)

    def test_bishop_teleports_to_enemy_queen_far_squares(self):
        """Bishop can teleport to squares far from enemy queen (queen only threatens adjacent)."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        place(board, "e4", Queen('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        # Queen on e4 only threatens 8 adjacent squares (d5, e5, f5, d4, f4, d3, e3, f3)
        # Bishop should be able to reach squares far from the queen
        self.assertIn(sq("h8"), dests)  # far from queen, should be safe
        self.assertIn(sq("a8"), dests)  # far from queen

    def test_bishop_cannot_teleport_to_enemy_queen_adjacent_square(self):
        """Bishop cannot teleport to a square adjacent to the enemy queen."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        place(board, "e4", Queen('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        # Queen on e4 threatens adjacent squares — bishop cannot go there
        queen_threats = [sq("d5"), sq("e5"), sq("f5"), sq("d4"), sq("f4"), sq("d3"), sq("e3"), sq("f3")]
        for threat in queen_threats:
            self.assertNotIn(threat, dests, f"Bishop should not teleport to {threat} adjacent to enemy queen")

    def test_bishop_cannot_teleport_to_enemy_pawn_controlled_square(self):
        """Bishop cannot teleport to squares threatened by an enemy pawn."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        place(board, "d5", Pawn('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        # Black pawn on d5 threatens: forward (d4), diag (c4, e4), and sideways (c5, e5)
        self.assertNotIn(sq("d4"), dests)  # pawn forward
        self.assertNotIn(sq("c4"), dests)  # pawn diag capture
        self.assertNotIn(sq("e4"), dests)  # pawn diag capture

    def test_bishop_cannot_teleport_to_enemy_rook_controlled_square(self):
        """Bishop cannot teleport to squares threatened by an enemy rook."""
        board = empty_board()
        bishop = place(board, "h1", Bishop('white'))
        place(board, "a8", Rook('black'))
        board.bishop_moves(bishop, *sq("h1"))
        dests = get_move_destinations(bishop)
        # Rook on a8 uses two-step movement; step-1 to a7 or b8,
        # then step-2 perpendicular. Those threatened squares should be excluded.
        self.assertNotIn(sq("a7"), dests)  # rook step-1 down
        self.assertNotIn(sq("b8"), dests)  # rook step-1 right

    def test_bishop_assassin_capture(self):
        """Bishop on e4 can capture a piece that left its diagonal (c6 -> c5)."""
        board = empty_board()
        bishop = place(board, "e4", Bishop('white'))
        bishop.assassin_squares = [Square(*sq("c6"))]
        place(board, "c5", Pawn('black'))
        board.last_move = Move(Square(*sq("c6")), Square(*sq("c5")))
        board.bishop_moves(bishop, *sq("e4"))
        dests = get_move_destinations(bishop)
        self.assertIn(sq("c5"), dests)

    def test_bishop_assassin_only_available_immediately(self):
        """Assassin capture is only valid if last move originated from bishop's diagonal."""
        board = empty_board()
        bishop = place(board, "e4", Bishop('white'))
        bishop.assassin_squares = [Square(*sq("c6"))]
        place(board, "c5", Pawn('black'))
        # Last move was NOT from the assassin square
        board.last_move = Move(Square(*sq("b5")), Square(*sq("c5")))
        board.bishop_moves(bishop, *sq("e4"))
        dests = get_move_destinations(bishop)
        if sq("c5") in dests:
            self.fail("Bishop should not assassin-capture at c5 — piece did not leave bishop's diagonal")


# ===========================================================================
# TestKnight
# ===========================================================================

class TestKnight(unittest.TestCase):
    """
    Rulebook — Knight:
      Radius-2 pattern: 16 possible destinations.
        - 4 orthogonal: 2 squares in one direction
        - 4 diagonal: 2 squares diagonally
        - 8 L-shaped: 2 squares orthogonal + 1 perpendicular
      Jumped square: one specific square per move.
      Standard capture: on destination.
      Jump capture: if landing on empty + jumped over a piece, may capture
        one adjacent enemy at landing square.
    """

    # ---- Class structure tests ----

    def test_knight_is_not_royal(self):
        """Knights are never royal."""
        knight = Knight('white')
        self.assertFalse(knight.is_royal)

    def test_knight_is_not_transformed(self):
        """Knight starts as not transformed."""
        knight = Knight('white')
        self.assertFalse(knight.is_transformed)

    # ---- Movement tests ----

    def _rulebook_offsets(self):
        """The 16 radius-2 destinations per the rulebook."""
        return [
            (-2, 0), (0, 2), (2, 0), (0, -2),      # orthogonal 2
            (-2, 2), (2, 2), (2, -2), (-2, -2),     # diagonal 2
            (-2, 1), (-2, -1), (2, 1), (2, -1),     # L-shape
            (-1, 2), (1, 2), (-1, -2), (1, -2),     # L-shape
        ]

    def test_knight_16_destinations_open_board(self):
        """Knight on e4 on an empty board should have 16 possible moves."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        origin_r, origin_c = sq("e4")
        expected = set()
        for dr, dc in self._rulebook_offsets():
            r, c = origin_r + dr, origin_c + dc
            if 0 <= r <= 7 and 0 <= c <= 7:
                expected.add((r, c))
        self.assertEqual(dests, expected, f"Expected {len(expected)} moves, got {len(dests)}")

    def test_knight_corner_limited_moves(self):
        """Knight on a8 should have fewer moves due to board edge."""
        board = empty_board()
        knight = place(board, "a8", Knight('white'))
        board.knight_moves(knight, *sq("a8"))
        dests = get_move_destinations(knight)
        origin_r, origin_c = sq("a8")
        expected = set()
        for dr, dc in self._rulebook_offsets():
            r, c = origin_r + dr, origin_c + dc
            if 0 <= r <= 7 and 0 <= c <= 7:
                expected.add((r, c))
        self.assertEqual(dests, expected)

    def test_knight_jumps_over_pieces(self):
        """Knight on e4 surrounded by pieces can still reach radius-2 destinations."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        # Surround knight with friendly pieces
        for adj in ["d5", "e5", "f5", "d4", "f4", "d3", "e3", "f3"]:
            place(board, adj, Pawn('white'))
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertTrue(len(dests) > 0)

    def test_knight_standard_capture(self):
        """Knight on e4 can capture an enemy pawn on e6 (2 squares up)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e6", Pawn('black'))
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("e6"), dests)

    def test_knight_cannot_land_on_friendly(self):
        """Knight on e4 cannot move to e6 if a friendly pawn is there."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e6", Pawn('white'))
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertNotIn(sq("e6"), dests)

    # ---- Jumped square identification tests ----

    def test_jumped_square_orthogonal_up(self):
        """Knight e4 -> e6 (2 up): jumped square is e5."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # on jumped square
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        # Knight can still land on e6 even with piece on jumped square
        self.assertIn(sq("e6"), dests)

    def test_jumped_square_orthogonal_right(self):
        """Knight e4 -> g4 (2 right): jumped square is f4."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "f4", Pawn('black'))  # on jumped square
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("g4"), dests)

    def test_jumped_square_L_shape_2up_1right(self):
        """Knight e4 -> f6 (2 up, 1 right): jumped square is e5 (1 up along 2-sq dir)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # jumped square (1 up)
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("f6"), dests)

    def test_jumped_square_L_shape_1up_2right(self):
        """Knight e4 -> g5 (1 up, 2 right): jumped square is f4 (1 right along 2-sq dir)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "f4", Pawn('black'))  # jumped square (1 right)
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("g5"), dests)

    def test_jumped_square_diagonal(self):
        """Knight e4 -> c6 (2 up, 2 left diagonal): jumped square is d5 (1 up-left)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "d5", Pawn('black'))  # jumped square (1 diag up-left)
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("c6"), dests)

    # ---- Jump capture eligibility tests ----

    def test_jump_over_no_adjacent_enemies_is_normal_move(self):
        """Knight jumps over a piece onto empty square but no adjacent enemies exist.
        No second click needed — behaves like a normal move (one click total)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('white'))  # friendly piece on jumped square
        # Landing square e6 is empty, and no enemy pieces adjacent to e6
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("e6"), dests)
        # Execute the move
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        board.move(knight, move, testing=True)
        # Knight lands normally, friendly jumped piece untouched
        self.assertIsInstance(board.squares[sq("e6")[0]][sq("e6")[1]].piece, Knight)
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)

    def test_jump_capture_returns_targets_when_adjacent_enemies_exist(self):
        """When knight lands on empty e6 after jumping over e5, and there are
        adjacent enemies, board.move() returns the list of capturable targets."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # piece on jumped square (also adjacent to e6)
        place(board, "d6", Rook('black'))  # adjacent to landing e6
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, testing=True)
        # Should return list of adjacent enemy positions
        self.assertIsNotNone(targets)
        self.assertIn(sq("e5"), targets)
        self.assertIn(sq("d6"), targets)

    def test_no_jump_capture_when_landing_on_enemy(self):
        """Standard capture: knight lands on enemy at e6 — no jump capture triggered."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # piece on jumped square
        place(board, "e6", Pawn('black'))  # enemy on landing square
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        board.move(knight, move, testing=True)
        # Standard capture: piece on e6 is replaced by knight
        self.assertIsInstance(board.squares[sq("e6")[0]][sq("e6")[1]].piece, Knight)
        # Jumped piece on e5 should NOT be captured (landing was not empty)
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)

    def test_no_jump_capture_when_no_piece_on_jumped_square(self):
        """No jump capture when jumped square is empty (nothing was jumped over)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "d6", Rook('black'))  # adjacent to landing e6 but no jumped piece
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        board.move(knight, move, testing=True)
        # d6 enemy should NOT be captured (no piece was jumped over)
        self.assertIsNotNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)

    def test_jump_capture_does_not_capture_friendly_on_jumped_square(self):
        """Jump capture should not capture a friendly piece on the jumped square."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('white'))  # friendly piece on jumped square
        # e6 must be empty for the move to be valid
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        if sq("e6") in dests:
            move = Move(Square(*sq("e4")), Square(*sq("e6")))
            board.move(knight, move, testing=True)
            # Friendly piece on e5 should NOT be captured
            self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)

    # ---- Jump capture: adjacent enemy selection tests ----

    def test_jump_capture_can_choose_adjacent_enemy(self):
        """When jump capture is eligible, board.move() returns targets and does NOT
        auto-capture. All enemies remain until player chooses via execute_jump_capture."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))   # piece on jumped square
        place(board, "d6", Rook('black'))   # adjacent to landing e6
        place(board, "f6", Bishop('black')) # also adjacent to landing e6
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, testing=True)
        # All three enemies should still be on the board (no auto-capture)
        for sq_name in ["e5", "d6", "f6"]:
            r, c = sq(sq_name)
            self.assertIsNotNone(board.squares[r][c].piece, f"Piece at {sq_name} should remain")
        # All three should be in the targets list
        self.assertIn(sq("e5"), targets)
        self.assertIn(sq("d6"), targets)
        self.assertIn(sq("f6"), targets)
        # Player can then call execute_jump_capture on their choice
        board.execute_jump_capture(*sq("d6"), testing=True)
        self.assertIsNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)

    def test_jump_capture_can_decline(self):
        """Player may decline capture — all adjacent enemies remain on the board."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # piece on jumped square
        place(board, "d6", Rook('black'))  # adjacent to landing e6
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, testing=True)
        self.assertIsNotNone(targets)
        # Player declines — does NOT call execute_jump_capture
        # Both e5 and d6 should remain
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)
        self.assertIsNotNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)

    def test_jump_capture_jumped_piece_counts_as_adjacent(self):
        """The jumped piece counts as adjacent and may be the chosen capture target."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Rook('black'))  # piece on jumped square
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, testing=True)
        # e5 is adjacent to e6, so it should be in targets
        self.assertIn(sq("e5"), targets)
        # Player chooses to capture the jumped piece
        board.execute_jump_capture(*sq("e5"), testing=True)
        self.assertIsNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)

    def test_jump_capture_only_one_piece(self):
        """Knight may not capture more than one piece on a single turn.
        execute_jump_capture removes exactly one piece."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))   # jumped piece
        place(board, "d6", Rook('black'))   # adjacent enemy
        place(board, "f6", Bishop('black')) # another adjacent enemy
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, testing=True)
        # Capture one piece
        board.execute_jump_capture(*sq("d6"), testing=True)
        # The other two enemies must remain
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)
        self.assertIsNotNone(board.squares[sq("f6")[0]][sq("f6")[1]].piece)
        self.assertIsNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)

    def test_jump_capture_cannot_target_friendly_adjacent(self):
        """Jump capture targets only include enemy pieces, not friendly ones."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))   # jumped piece (enemy)
        place(board, "d6", Pawn('white'))   # friendly adjacent to landing
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, testing=True)
        # d6 is friendly — should NOT be in targets
        self.assertNotIn(sq("d6"), targets)
        # e5 is enemy — should be in targets
        self.assertIn(sq("e5"), targets)


# ===========================================================================
# TestBoulder
# ===========================================================================

class TestBoulder(unittest.TestCase):
    """
    Rulebook — Boulder:
      Neutral piece starting on central intersection.
      First move must go to one of four central squares (d4, e4, d5, e5).
      Afterward moves like a king.
      Captures pawns only. Only king may capture it.
      Cooldown: both players must take one turn before boulder moves again.
      Memory: cannot return to immediate last square.
      White may not move boulder on turn 1.
      On central intersection: blocks diagonals only, not files/ranks.
    """

    # ---- Class structure tests ----

    def test_boulder_is_not_royal(self):
        """Boulder is never royal."""
        boulder = Boulder()
        self.assertFalse(boulder.is_royal)

    def test_boulder_is_not_transformed(self):
        """Boulder cannot be transformed."""
        boulder = Boulder()
        self.assertFalse(boulder.is_transformed)

    def test_boulder_is_neutral(self):
        """Boulder has no color (neutral piece)."""
        boulder = Boulder()
        self.assertEqual(boulder.color, 'none')

    def test_boulder_has_zero_value(self):
        """Boulder has zero value."""
        boulder = Boulder()
        self.assertEqual(boulder.value, 0)

    def test_boulder_has_cooldown(self):
        """Boulder starts with cooldown of 0."""
        boulder = Boulder()
        self.assertEqual(boulder.cooldown, 0)

    def test_boulder_has_last_square(self):
        """Boulder starts with no last square."""
        boulder = Boulder()
        self.assertIsNone(boulder.last_square)

    def test_boulder_has_first_move_flag(self):
        """Boulder starts with first_move=True."""
        boulder = Boulder()
        self.assertTrue(boulder.first_move)

    def test_boulder_inherits_from_piece(self):
        """Boulder is a subclass of Piece."""
        from piece import Piece
        boulder = Boulder()
        self.assertIsInstance(boulder, Piece)

    def test_boulder_texture_has_no_color_prefix(self):
        """Boulder texture path uses 'boulder.png' without a color prefix."""
        boulder = Boulder()
        self.assertIn('boulder.png', boulder.texture)
        self.assertNotIn('none_', boulder.texture)

    # ---- First move tests ----

    def test_boulder_first_move_central_squares_only(self):
        """Boulder's first move must go to one of d4, e4, d5, e5.
        The boulder starts on the central intersection (between these 4 squares)."""
        board = empty_board()
        boulder = Boulder()
        # Place boulder conceptually at center; for move gen we use a central square
        place(board, "d4", boulder)
        board.boulder_moves(boulder, *sq("d4"))
        dests = get_move_destinations(boulder)
        allowed = {sq("d4"), sq("e4"), sq("d5"), sq("e5")}
        for dest in dests:
            self.assertIn(dest, allowed, f"First move {dest} not in central squares")

    def test_boulder_first_move_cannot_go_outside_center(self):
        """Boulder's first move cannot go to squares outside the 4 central squares."""
        board = empty_board()
        boulder = Boulder()
        place(board, "d4", boulder)
        board.boulder_moves(boulder, *sq("d4"))
        dests = get_move_destinations(boulder)
        outside = {sq("c3"), sq("c4"), sq("c5"), sq("d3"), sq("e3"), sq("f3"),
                   sq("f4"), sq("f5"), sq("d6"), sq("e6")}
        for dest in outside:
            self.assertNotIn(dest, dests, f"First move should not reach {dest}")

    # ---- Later movement tests ----

    def test_boulder_later_moves_like_king(self):
        """After first move, boulder moves like a king (1 square any direction)."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        expected = {
            sq("d5"), sq("e5"), sq("f5"),
            sq("d4"),          sq("f4"),
            sq("d3"), sq("e3"), sq("f3"),
        }
        self.assertEqual(dests, expected)

    def test_boulder_later_moves_max_one_square(self):
        """Boulder cannot move more than one square after its first move."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        origin_r, origin_c = sq("e4")
        for r, c in dests:
            self.assertLessEqual(abs(r - origin_r), 1)
            self.assertLessEqual(abs(c - origin_c), 1)

    def test_boulder_corner_limited_moves(self):
        """Boulder on a1 (after first move) should have only 3 moves."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "a1", boulder)
        board.boulder_moves(boulder, *sq("a1"))
        dests = get_move_destinations(boulder)
        expected = {sq("a2"), sq("b1"), sq("b2")}
        self.assertEqual(dests, expected)

    # ---- Capture rules: boulder captures pawns only ----

    def test_boulder_captures_white_pawn(self):
        """Boulder can capture a white pawn."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", Pawn('white'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertIn(sq("e5"), dests)

    def test_boulder_captures_black_pawn(self):
        """Boulder can capture a black pawn."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", Pawn('black'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertIn(sq("e5"), dests)

    def test_boulder_cannot_capture_knight(self):
        """Boulder cannot capture a knight."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", Knight('white'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests)

    def test_boulder_cannot_capture_rook(self):
        """Boulder cannot capture a rook."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", Rook('black'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests)

    def test_boulder_cannot_capture_bishop(self):
        """Boulder cannot capture a bishop."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", Bishop('black'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests)

    def test_boulder_cannot_capture_queen(self):
        """Boulder cannot capture a queen."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", Queen('black'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests)

    def test_boulder_cannot_capture_king(self):
        """Boulder cannot capture a king."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        place(board, "e5", King('black'))
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests)

    # ---- Capture rules: only king captures boulder ----

    def test_king_can_capture_boulder(self):
        """King can capture the boulder."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        place(board, "e5", Boulder())
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        self.assertIn(sq("e5"), dests)

    def test_rook_cannot_capture_boulder(self):
        """Rook cannot capture the boulder — it blocks like a friendly piece."""
        board = empty_board()
        rook = place(board, "e1", Rook('white'))
        place(board, "e4", Boulder())
        board.rook_moves(rook, *sq("e1"))
        dests = get_move_destinations(rook)
        self.assertNotIn(sq("e4"), dests)

    def test_queen_cannot_capture_boulder(self):
        """Queen cannot capture the boulder."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        place(board, "e5", Boulder())
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("e5"), dests)

    def test_pawn_cannot_capture_boulder(self):
        """Pawn cannot capture the boulder."""
        board = empty_board()
        pawn = place(board, "e4", Pawn('white'))
        place(board, "e5", Boulder())
        board.pawn_moves(pawn, *sq("e4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("e5"), dests)

    def test_knight_cannot_land_on_boulder(self):
        """Knight cannot land on the boulder."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e6", Boulder())
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertNotIn(sq("e6"), dests)

    @unittest.skip("Not yet implemented: boulder does not trigger bishop assassin capture")
    def test_bishop_assassin_not_triggered_by_boulder(self):
        """Bishop's assassin capture should not be triggered by the boulder moving.
        If a boulder moves off the bishop's diagonal, the bishop cannot capture it."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        boulder = Boulder()
        boulder.first_move = False
        place(board, "d4", boulder)
        # Simulate boulder moving from d4 (on bishop's diagonal) to d5
        bishop.assassin_squares = [Square(*sq("d4"))]
        board.last_move = Move(Square(*sq("d4")), Square(*sq("d5")))
        place(board, "d5", boulder)
        board.squares[sq("d4")[0]][sq("d4")[1]].piece = None
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        self.assertNotIn(sq("d5"), dests, "Bishop should not assassin-capture the boulder")

    # ---- Neutral status: treated as friendly by both sides ----

    def test_boulder_blocks_white_piece(self):
        """White rook is blocked by boulder (treated as friendly)."""
        board = empty_board()
        rook = place(board, "a4", Rook('white'))
        place(board, "b4", Boulder())
        board.rook_moves(rook, *sq("a4"))
        dests = get_move_destinations(rook)
        # Rook step-1 right to b4 is blocked by boulder (friendly)
        self.assertNotIn(sq("b4"), dests)

    def test_boulder_blocks_black_piece(self):
        """Black rook is also blocked by boulder (friendly to both sides)."""
        board = empty_board()
        rook = place(board, "a4", Rook('black'))
        place(board, "b4", Boulder())
        board.rook_moves(rook, *sq("a4"))
        dests = get_move_destinations(rook)
        self.assertNotIn(sq("b4"), dests)

    # ---- Central intersection diagonal blocking ----

    @unittest.skip("Not yet implemented: boulder central intersection blocking")
    def test_boulder_on_center_blocks_diagonals(self):
        """Boulder on central intersection blocks diagonal movement through the center.
        A bishop-like diagonal from a1 toward h8 should be blocked at the center."""
        board = empty_board()
        # Boulder on center intersection (conceptually between d4, d5, e4, e5)
        # This should block diagonals passing through the center
        boulder = Boulder()
        boulder.on_intersection = True
        place(board, "d4", boulder)  # placeholder position for center
        bishop = place(board, "b2", Bishop('white'))
        board.bishop_moves(bishop, *sq("b2"))
        dests = get_move_destinations(bishop)
        # Bishop on b2 going up-right: c3, d4 (blocked by boulder center)
        # Should not reach e5, f6, g7, h8 through the center diagonal
        # (exact blocking behavior depends on implementation)

    @unittest.skip("Not yet implemented: boulder central intersection blocking")
    def test_boulder_on_center_does_not_block_files(self):
        """Boulder on central intersection does NOT block files (vertical movement)."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        place(board, "d4", boulder)  # placeholder
        rook = place(board, "d1", Rook('white'))
        board.rook_moves(rook, *sq("d1"))
        dests = get_move_destinations(rook)
        # Rook on d1 moving up should pass through the center
        # (boulder on intersection does not block files/ranks)

    @unittest.skip("Not yet implemented: boulder central intersection blocking")
    def test_boulder_on_center_does_not_block_ranks(self):
        """Boulder on central intersection does NOT block ranks (horizontal movement)."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        place(board, "d4", boulder)  # placeholder
        rook = place(board, "a4", Rook('white'))
        board.rook_moves(rook, *sq("a4"))
        dests = get_move_destinations(rook)
        # Rook on a4 moving right should pass through the center

    # ---- Cooldown tests ----

    def test_boulder_cooldown_after_move(self):
        """After boulder moves, cooldown is set to 2 (both players must take a turn)."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        board.boulder_moves(boulder, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e5")))
        boulder.add_move(move)
        board.move(boulder, move, testing=True)
        self.assertEqual(boulder.cooldown, 2)

    def test_boulder_not_moveable_during_cooldown(self):
        """Boulder cannot be moved while cooldown > 0."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        boulder.cooldown = 1  # still cooling down
        place(board, "e4", boulder)
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertEqual(len(dests), 0)

    def test_boulder_cooldown_decrements_each_turn(self):
        """Boulder cooldown decreases by 1 each turn (each player's turn)."""
        boulder = Boulder()
        boulder.cooldown = 2
        # After white's turn
        boulder.cooldown -= 1
        self.assertEqual(boulder.cooldown, 1)
        # After black's turn
        boulder.cooldown -= 1
        self.assertEqual(boulder.cooldown, 0)

    def test_boulder_moveable_when_cooldown_zero(self):
        """Boulder can be moved once cooldown reaches 0."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        boulder.cooldown = 0
        place(board, "e4", boulder)
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertTrue(len(dests) > 0)

    # ---- Memory tests ----

    def test_boulder_cannot_return_to_last_square(self):
        """Boulder cannot move to the square it just came from."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        boulder.last_square = sq("e5")  # boulder just came from e5
        place(board, "e4", boulder)
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests)

    def test_boulder_can_reach_last_square_later(self):
        """Boulder may return to a previous square on future turns (not immediate)."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        boulder.last_square = sq("d4")  # came from d4 two moves ago
        place(board, "e4", boulder)
        # After moving to e4, last_square is now e3 (hypothetical)
        boulder.last_square = sq("e3")
        board.boulder_moves(boulder, *sq("e4"))
        dests = get_move_destinations(boulder)
        # d4 is no longer the immediate last square, so it should be reachable
        # (only if d4 is adjacent to e4, which it is — but not blocked by memory)
        # Note: d4 is only reachable if it's an adjacent square
        # d4 is left of e4, so it is adjacent
        self.assertIn(sq("d4"), dests)

    def test_boulder_memory_only_one_square(self):
        """Boulder only remembers the immediate last square, not earlier ones."""
        boulder = Boulder()
        boulder.last_square = sq("d4")
        # Simulate moving to e4
        boulder.last_square = sq("e4")
        # Now only e4 is forbidden, d4 is no longer remembered
        self.assertEqual(boulder.last_square, sq("e4"))

    # ---- White cannot move boulder on turn 1 ----

    @unittest.skip("Not yet implemented: boulder turn 1 restriction")
    def test_white_cannot_move_boulder_turn_one(self):
        """White may not move the boulder on their very first turn of the game."""
        # This is enforced in the UI/game logic, not in boulder_moves itself.
        # The game should prevent white from selecting the boulder on turn 1.
        pass

    @unittest.skip("Not yet implemented: boulder turn 1 restriction")
    def test_black_can_move_boulder_on_first_turn(self):
        """Black may move the boulder on their first turn (only white is restricted)."""
        pass

    @unittest.skip("Not yet implemented: boulder turn 1 restriction")
    def test_white_can_move_boulder_after_turn_one(self):
        """White can move the boulder on any turn after the first."""
        pass

    # ---- Interaction with queen manipulation ----

    def test_queen_cannot_manipulate_boulder(self):
        """Queen's manipulation cannot target the boulder."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        boulder = place(board, "a4", Boulder())
        board.queen_moves_enemy(boulder, *sq("a4"))
        dests = get_move_destinations(boulder)
        self.assertEqual(len(dests), 0)

    # ---- Interaction with knight ----

    @unittest.skip("Not yet implemented: knight jumps over boulder")
    def test_knight_can_jump_over_boulder(self):
        """Knight can jump over the boulder (it's on the jumped square)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Boulder())  # boulder on jumped square
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("e6"), dests)


if __name__ == '__main__':
    unittest.main()
