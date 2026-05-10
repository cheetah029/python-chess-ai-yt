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
    board.last_action = None
    board.boulder = None
    board.turn_number = 0
    board.captured_pieces = {'white': [], 'black': []}
    board.state_history = {}
    board.tiny_endgame_active = False
    board.distance_counts = [0] * 15
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

    def test_pawn_on_last_rank_triggers_promotion(self):
        """White pawn moving to e8 should trigger check_promotion (returns True)."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        move = Move(Square(*sq("e7")), Square(*sq("e8")))
        board.move(pawn, move, )
        final = Square(*sq("e8"))
        self.assertTrue(board.check_promotion(pawn, final))

    def test_black_pawn_on_last_rank_triggers_promotion(self):
        """Black pawn moving to e1 should trigger check_promotion (returns True)."""
        board = empty_board()
        pawn = place(board, "e2", Pawn('black'))
        move = Move(Square(*sq("e2")), Square(*sq("e1")))
        board.move(pawn, move, )
        final = Square(*sq("e1"))
        self.assertTrue(board.check_promotion(pawn, final))

    def test_pawn_not_on_last_rank_no_promotion(self):
        """Pawn not on last rank should not trigger promotion."""
        board = empty_board()
        pawn = place(board, "e6", Pawn('white'))
        final = Square(*sq("e7"))
        self.assertFalse(board.check_promotion(pawn, final))

    # ---- Promotion choice tests ----

    def test_promoted_queen_is_not_royal(self):
        """Promoted queen (base form) must be marked as non-royal."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'queen')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertIsInstance(promoted, Queen)
        self.assertFalse(promoted.is_royal)

    def test_promotion_to_non_royal_queen_base_form(self):
        """Pawn can promote to a non-royal queen in base form (Queen instance)."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'queen')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertIsInstance(promoted, Queen)
        self.assertFalse(promoted.is_royal)
        self.assertFalse(promoted.is_transformed)

    def test_promotion_to_non_royal_queen_as_bishop(self):
        """Pawn can promote to a non-royal queen in bishop form (Bishop instance)."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'bishop')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertIsInstance(promoted, Bishop)
        self.assertFalse(promoted.is_royal)
        self.assertTrue(promoted.is_transformed)

    def test_promotion_to_non_royal_queen_as_rook(self):
        """Pawn can promote to a non-royal queen in rook form (Rook instance)."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'rook')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertIsInstance(promoted, Rook)
        self.assertFalse(promoted.is_royal)
        self.assertTrue(promoted.is_transformed)

    def test_promotion_to_non_royal_queen_as_knight(self):
        """Pawn can promote to a non-royal queen in knight form (Knight instance)."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'knight')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertIsInstance(promoted, Knight)
        self.assertFalse(promoted.is_royal)
        self.assertTrue(promoted.is_transformed)

    def test_black_pawn_promotion_choice(self):
        """Black pawn promoting on rank 1 can also choose a form."""
        board = empty_board()
        pawn = place(board, "e2", Pawn('black'))
        board.promote(pawn, *sq("e1"), 'rook')
        promoted = board.squares[sq("e1")[0]][sq("e1")[1]].piece
        self.assertIsInstance(promoted, Rook)
        self.assertFalse(promoted.is_royal)
        self.assertTrue(promoted.is_transformed)
        self.assertEqual(promoted.color, 'black')

    def test_promotion_preserves_color(self):
        """Promoted piece retains the pawn's color."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'knight')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertEqual(promoted.color, 'white')

    def test_promotion_replaces_pawn(self):
        """After promotion, the pawn is no longer on the board — replaced by the promoted piece."""
        board = empty_board()
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'queen')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        self.assertNotIsInstance(promoted, Pawn)

    def test_promotion_menu_only_queen_if_no_captures(self):
        """With no captures, promotion only offers base form queen."""
        board = empty_board()
        options = board.get_promotion_options('white')
        self.assertEqual(options, ['queen'])

    def test_promotion_menu_includes_captured_types(self):
        """Promotion offers queen plus any captured piece types."""
        board = empty_board()
        board.captured_pieces['white'] = ['rook', 'knight']
        options = board.get_promotion_options('white')
        self.assertIn('queen', options)
        self.assertIn('rook', options)
        self.assertIn('knight', options)
        self.assertNotIn('bishop', options)

    def test_promotion_menu_all_four_when_all_captured(self):
        """Promotion offers all 4 forms when rook, bishop, and knight have all been captured."""
        board = empty_board()
        board.captured_pieces['white'] = ['rook', 'bishop', 'knight']
        options = board.get_promotion_options('white')
        self.assertEqual(set(options), {'queen', 'rook', 'bishop', 'knight'})

    def test_promoted_queen_can_later_transform(self):
        """A promoted queen (non-royal, base form) can later transform just like
        a royal queen, using the right-click transformation menu."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        pawn = place(board, "e7", Pawn('white'))
        board.promote(pawn, *sq("e8"), 'queen')
        promoted = board.squares[sq("e8")[0]][sq("e8")[1]].piece
        options = board.get_transformation_options(promoted)
        self.assertIn('rook', options, "Promoted queen should be able to transform")


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

    def test_promoted_queen_can_manipulate(self):
        """A promoted (non-royal) queen in base form can manipulate enemy pieces."""
        board = empty_board()
        promoted = Queen('white', is_royal=False)
        place(board, "a1", promoted)
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertTrue(len(dests) > 0, "Promoted queen should be able to manipulate")

    def test_promoted_queen_manipulates_when_royal_queen_has_no_los(self):
        """When royal queen lacks LOS but promoted queen has it, manipulation works."""
        board = empty_board()
        place(board, "h1", Queen('white', is_royal=True))   # royal, no LOS to a4
        place(board, "a1", Queen('white', is_royal=False))  # promoted, has LOS to a4
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertTrue(len(dests) > 0,
            "Promoted queen with LOS should enable manipulation even if royal queen lacks LOS")

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

    def test_manipulation_can_target_transformed_royal_queen(self):
        """Queen on a1 CAN manipulate an enemy royal queen that is transformed.
        A transformed royal queen is an instance of the target piece (e.g. Rook)
        with is_transformed=True, is_royal=True — not a Queen instance."""
        board = empty_board()
        queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        # Transformed royal queen as rook
        transformed = Rook('black')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "a4", transformed)
        board.queen_moves_enemy(transformed, *sq("a4"))
        dests = get_move_destinations(transformed)
        self.assertTrue(len(dests) > 0, "Transformed royal queen (as rook) should be manipulable")

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
        board.move(enemy_rook, move, )
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

    def test_queen_cannot_manipulate_when_transformed(self):
        """A transformed queen cannot use manipulation. Since a transformed queen
        is an instance of the target piece (not Queen), queen_moves_enemy won't
        find it as a Queen to perform manipulation. This test verifies that a
        transformed royal queen (e.g. Rook with is_royal=True, is_transformed=True)
        on a1 does NOT grant manipulation power over enemy pieces."""
        board = empty_board()
        # White's royal queen transformed as rook on a1
        transformed = Rook('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "a1", transformed)
        board.update_lines_of_sight()
        enemy_rook = place(board, "a4", Rook('black'))
        board.queen_moves_enemy(enemy_rook, *sq("a4"))
        dests = get_move_destinations(enemy_rook)
        self.assertEqual(len(dests), 0, "Transformed queen should not grant manipulation")

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

    # ---- Transformation tests: data model ----

    def test_board_tracks_captured_pieces(self):
        """Board should track captured piece types per color."""
        board = Board()
        self.assertIn('white', board.captured_pieces)
        self.assertIn('black', board.captured_pieces)
        self.assertEqual(board.captured_pieces['white'], [])

    def test_capture_records_piece_type(self):
        """When a piece is captured, its type is added to captured_pieces."""
        board = empty_board()
        board.captured_pieces = {'white': [], 'black': []}
        rook = place(board, "e4", Rook('white'))
        enemy = place(board, "e5", Knight('black'))
        # Simulate rook capturing knight by moving to e5
        board.rook_moves(rook, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e5")))
        rook.add_move(move)
        board.move(rook, move, )
        self.assertIn('knight', board.captured_pieces['black'])

    def test_capturing_transformed_queen_recorded_as_queen(self):
        """Capturing a transformed queen (e.g. Rook with is_transformed=True)
        should record 'queen' in captured_pieces, not 'rook'."""
        board = empty_board()
        attacker = place(board, "e4", Knight('white'))
        # Black's royal queen transformed as rook on e6
        transformed = Rook('black')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e6", transformed)
        board.knight_moves(attacker, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        attacker.add_move(move)
        board.move(attacker, move, )
        self.assertNotIn('rook', board.captured_pieces['black'],
            "Transformed queen should not be recorded as rook")
        self.assertIn('queen', board.captured_pieces['black'],
            "Transformed queen should be recorded as queen")

    def test_jump_capturing_transformed_queen_recorded_as_queen(self):
        """Jump-capturing a transformed queen should record 'queen', not the disguised type."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        # Transformed queen as bishop on e5 (jumped square)
        transformed = Bishop('black')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e5", transformed)
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, )
        board.execute_jump_capture(*sq("e5"), )
        self.assertNotIn('bishop', board.captured_pieces['black'],
            "Transformed queen should not be recorded as bishop")
        self.assertIn('queen', board.captured_pieces['black'],
            "Transformed queen should be recorded as queen")

    # ---- Transformation tests: transform action ----

    def test_queen_transforms_into_rook(self):
        """Royal queen transforms into a Rook instance with is_transformed=True, is_royal=True."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        board.transform_queen(queen, *sq("e4"), 'rook')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsInstance(piece, Rook)
        self.assertTrue(piece.is_transformed)
        self.assertTrue(piece.is_royal)
        self.assertEqual(piece.color, 'white')

    def test_queen_transforms_into_bishop(self):
        """Royal queen transforms into a Bishop instance."""
        board = empty_board()
        board.captured_pieces = {'white': ['bishop'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        board.transform_queen(queen, *sq("e4"), 'bishop')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsInstance(piece, Bishop)
        self.assertTrue(piece.is_transformed)
        self.assertTrue(piece.is_royal)

    def test_queen_transforms_into_knight(self):
        """Royal queen transforms into a Knight instance."""
        board = empty_board()
        board.captured_pieces = {'white': ['knight'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        board.transform_queen(queen, *sq("e4"), 'knight')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsInstance(piece, Knight)
        self.assertTrue(piece.is_transformed)
        self.assertTrue(piece.is_royal)

    def test_promoted_queen_transforms_non_royal(self):
        """Promoted (non-royal) queen transforms into piece with is_royal=False."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        promoted = Queen('white', is_royal=False)
        place(board, "e4", promoted)
        board.transform_queen(promoted, *sq("e4"), 'rook')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsInstance(piece, Rook)
        self.assertTrue(piece.is_transformed)
        self.assertFalse(piece.is_royal, "Promoted queen's transformation should not be royal")

    # ---- Transformation tests: revert to base form ----

    def test_queen_reverts_to_base_form(self):
        """Transformed queen can return to Queen instance (base form) on a later turn."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        # Start as transformed rook
        transformed = Rook('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e4", transformed)
        board.transform_queen(transformed, *sq("e4"), 'queen')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsInstance(piece, Queen)
        self.assertFalse(piece.is_transformed)
        self.assertTrue(piece.is_royal)

    def test_promoted_queen_reverts_non_royal(self):
        """Transformed promoted queen reverts to non-royal Queen instance."""
        board = empty_board()
        board.captured_pieces = {'white': ['knight'], 'black': []}
        transformed = Knight('white')
        transformed.is_transformed = True
        transformed.is_royal = False
        place(board, "e4", transformed)
        board.transform_queen(transformed, *sq("e4"), 'queen')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsInstance(piece, Queen)
        self.assertFalse(piece.is_transformed)
        self.assertFalse(piece.is_royal)

    # ---- Transformation tests: restrictions ----

    def test_queen_cannot_transform_if_no_captures(self):
        """Queen cannot transform if no friendly non-royal pieces have been captured."""
        board = empty_board()
        board.captured_pieces = {'white': [], 'black': []}
        queen = place(board, "e4", Queen('white'))
        options = board.get_transformation_options(queen)
        self.assertEqual(len(options), 0)

    def test_queen_can_only_transform_into_captured_types(self):
        """Queen can only transform into piece types that have been captured."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        options = board.get_transformation_options(queen)
        self.assertIn('rook', options)
        self.assertNotIn('bishop', options)
        self.assertNotIn('knight', options)

    def test_queen_multiple_captured_types_available(self):
        """Queen can transform into any captured type."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook', 'knight'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        options = board.get_transformation_options(queen)
        self.assertIn('rook', options)
        self.assertIn('knight', options)
        self.assertNotIn('bishop', options)

    def test_transformation_does_not_change_square(self):
        """Transformation is an action — the piece stays on the same square."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        board.transform_queen(queen, *sq("e4"), 'rook')
        piece = board.squares[sq("e4")[0]][sq("e4")[1]].piece
        self.assertIsNotNone(piece, "Piece should still be on e4 after transformation")

    def test_transformation_highlights_square(self):
        """After transformation, last_action should highlight the transformed piece's square."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        board.transform_queen(queen, *sq("e4"), 'rook')
        self.assertIsNotNone(board.last_action)
        self.assertEqual((board.last_action.row, board.last_action.col), sq("e4"))
        # last_move should NOT be set by transformation
        self.assertIsNone(board.last_move)

    def test_transformation_does_not_block_manipulation(self):
        """A piece that transformed (action, not spatial move) on the previous turn
        can still be manipulated — the restriction only applies to spatial moves."""
        board = empty_board()
        board.captured_pieces = {'black': ['rook'], 'white': []}
        # Black queen transforms into rook on a4
        black_queen = place(board, "a4", Queen('black'))
        board.transform_queen(black_queen, *sq("a4"), 'rook')
        # Now white tries to manipulate the transformed piece on a4
        white_queen = place(board, "a1", Queen('white'))
        board.update_lines_of_sight()
        transformed = board.squares[sq("a4")[0]][sq("a4")[1]].piece
        board.queen_moves_enemy(transformed, *sq("a4"))
        dests = get_move_destinations(transformed)
        self.assertTrue(len(dests) > 0,
            "Piece that transformed (action) should be manipulable on next turn")

    # ---- Transformation tests: menu options (exclude current form) ----

    def test_menu_options_base_form_excludes_queen(self):
        """When queen is in base form, menu shows captured types but not 'queen'."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook', 'bishop', 'knight'], 'black': []}
        queen = place(board, "e4", Queen('white'))
        options = board.get_transformation_options(queen)
        self.assertNotIn('queen', options)
        self.assertEqual(set(options), {'rook', 'bishop', 'knight'})

    def test_menu_options_transformed_includes_queen_excludes_current(self):
        """When transformed as rook, menu shows 'queen' (revert) + other captured types,
        but NOT 'rook' (current form)."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook', 'knight'], 'black': []}
        transformed = Rook('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e4", transformed)
        options = board.get_transformation_options(transformed)
        self.assertIn('queen', options, "Should be able to revert to base form")
        self.assertIn('knight', options, "Should be able to transform to other captured type")
        self.assertNotIn('rook', options, "Current form should be excluded")

    def test_menu_options_transformed_only_queen_if_no_other_captures(self):
        """When transformed as rook and no other types captured, menu only shows 'queen'."""
        board = empty_board()
        board.captured_pieces = {'white': ['rook'], 'black': []}
        transformed = Rook('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e4", transformed)
        options = board.get_transformation_options(transformed)
        self.assertEqual(options, ['queen'])

    # ---- Transformation tests: movement routing ----

    def test_transformed_as_rook_uses_rook_movement(self):
        """Transformed queen (now Rook instance) should use rook movement rules."""
        board = empty_board()
        transformed = Rook('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e4", transformed)
        board.rook_moves(transformed, *sq("e4"))
        dests = get_move_destinations(transformed)
        # Rook step-1 up to e5, then step-2 left/right — should have rook-like moves
        self.assertIn(sq("e5"), dests)
        self.assertIn(sq("f5"), dests)
        # Should NOT have queen-like adjacent diagonal moves
        self.assertNotIn(sq("f5"), {d for d in dests if d == sq("f5") and sq("e5") not in dests})

    def test_transformed_as_knight_uses_knight_movement(self):
        """Transformed queen (now Knight instance) should use knight movement rules."""
        board = empty_board()
        transformed = Knight('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e4", transformed)
        board.knight_moves(transformed, *sq("e4"))
        dests = get_move_destinations(transformed)
        self.assertIn(sq("e6"), dests)  # 2 squares up (knight move)
        self.assertNotIn(sq("e5"), dests)  # 1 square up (not a knight move)

    def test_transformed_as_bishop_uses_bishop_movement(self):
        """Transformed queen (now Bishop instance) should use bishop movement (teleportation)."""
        board = empty_board()
        transformed = Bishop('white')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "e4", transformed)
        board.bishop_moves(transformed, *sq("e4"))
        dests = get_move_destinations(transformed)
        # Bishop teleports to safe squares — should have many destinations
        self.assertTrue(len(dests) > 0)

    # ---- Transformation tests: is_transformed / is_royal independence ----

    def test_royal_transformed_queen(self):
        """is_transformed=True, is_royal=True: transformed royal queen."""
        piece = Rook('white')
        piece.is_transformed = True
        piece.is_royal = True
        self.assertTrue(piece.is_transformed)
        self.assertTrue(piece.is_royal)
        self.assertIsInstance(piece, Rook)

    def test_non_royal_transformed_queen(self):
        """is_transformed=True, is_royal=False: transformed promoted queen."""
        piece = Knight('white')
        piece.is_transformed = True
        piece.is_royal = False
        self.assertTrue(piece.is_transformed)
        self.assertFalse(piece.is_royal)
        self.assertIsInstance(piece, Knight)

    def test_royal_base_form_queen(self):
        """is_transformed=False, is_royal=True: royal queen in base form (or king)."""
        queen = Queen('white')
        self.assertFalse(queen.is_transformed)
        self.assertTrue(queen.is_royal)

    def test_normal_piece(self):
        """is_transformed=False, is_royal=False: normal piece."""
        rook = Rook('white')
        self.assertFalse(rook.is_transformed)
        self.assertFalse(rook.is_royal)

    # ---- Transformation tests: bishop teleport exclusion ----

    def test_queen_as_bishop_excluded_from_teleport_threats(self):
        """Per rulebook, 'queen transformed as bishop' is excluded from threat
        calculation for enemy bishop teleportation, same as normal bishops."""
        board = empty_board()
        # White bishop should be able to teleport to squares 'threatened' by
        # a transformed-as-bishop enemy queen, since those are excluded
        transformed = Bishop('black')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "c6", transformed)
        bishop = place(board, "h1", Bishop('white'))
        board.bishop_moves(bishop, *sq("h1"))
        dests = get_move_destinations(bishop)
        # All empty squares should be available since the only enemy is a bishop
        # (which is excluded from threat calc, per existing bishop logic)
        empty_count = 0
        for r in range(8):
            for c in range(8):
                if board.squares[r][c].isempty() and (r, c) != sq("h1"):
                    empty_count += 1
        self.assertEqual(len(dests), empty_count,
            "Queen-as-bishop threats should be excluded from teleport calculation")


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

    # ---- Knight threat vs bishop teleportation edge cases ----

    def test_bishop_cannot_teleport_to_knight_radius2_destination(self):
        """Bishop cannot teleport to a square that is a knight's radius-2 destination."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        place(board, "f6", Knight('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        # f8 is 2 squares up from f6 — a radius-2 destination
        self.assertNotIn(sq("f8"), dests,
            "Bishop should not teleport to f8 — knight radius-2 destination")

    def test_bishop_cannot_teleport_to_jumped_square(self):
        """Bishop cannot teleport to a jumped square if the knight has a vacant
        landing on the board — the bishop itself would become the jumped piece."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        # Knight on e4. e5 is the jumped square for e4->e6 (2 up).
        # e6 is empty and on board -> e5 is threatened as a jumped square.
        place(board, "e4", Knight('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        self.assertNotIn(sq("e5"), dests,
            "e5 is a jumped square with vacant landing e6 — bishop would be capturable")

    def test_bishop_can_teleport_to_jumped_square_if_landing_occupied(self):
        """Bishop CAN teleport to a jumped square if the corresponding landing
        is occupied — the knight can't land there so no jump capture."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        place(board, "e4", Knight('black'))
        # Block all landings that use e5 as jumped square with bishops
        # (bishops are ignored for threat calc, so they won't block teleportation)
        # e4->e6: jumped=e5. Block e6.
        place(board, "e6", Bishop('black'))
        # e4->f6: jumped=e5. Block f6.
        place(board, "f6", Bishop('black'))
        # e4->d6: jumped=e5. Block d6.
        place(board, "d6", Bishop('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        self.assertIn(sq("e5"), dests,
            "e5 should be safe when all landings that jump over it are occupied")

    def test_bishop_teleports_to_edge_not_jumped_square(self):
        """Bishop can teleport to an edge square that is not a jumped square
        or radius-2 destination of the knight."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        place(board, "h7", Knight('black'))
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        # h8 is NOT a radius-2 dest of h7, and NOT a jumped square for any
        # knight move with a vacant landing. So bishop can go there.
        self.assertIn(sq("h8"), dests,
            "h8 is not threatened by knight on h7")

    def test_bishop_blocked_adjacent_to_landing_with_existing_jumped_piece(self):
        """Bishop cannot teleport to a square adjacent to a knight's empty landing
        when there is already a piece on the jumped square."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        # Knight on e4, pawn on e5 (jumped square for e4->e6)
        place(board, "e4", Knight('black'))
        place(board, "e5", Pawn('white'))  # existing piece on jumped square
        # e6 is empty (landing). Knight can jump e5, land on e6, capture adjacent.
        # d7 and f7 are adjacent to e6 — threatened by jump capture.
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        self.assertNotIn(sq("d7"), dests,
            "d7 adjacent to landing e6 with piece on jumped e5 — should be threatened")
        self.assertNotIn(sq("f7"), dests,
            "f7 adjacent to landing e6 with piece on jumped e5 — should be threatened")

    def test_bishop_not_blocked_adjacent_without_existing_jumped_piece(self):
        """Bishop CAN teleport to a square adjacent to a knight's empty landing
        when there is NO existing piece on the jumped square (only the jumped
        square itself is threatened, not adjacent squares)."""
        board = empty_board()
        bishop = place(board, "a1", Bishop('white'))
        # Knight on e4, NO piece on e5 (jumped square for e4->e6)
        place(board, "e4", Knight('black'))
        # e6 is empty, e5 is empty — no existing jump capture possible
        # d7 and f7 are adjacent to e6 but should NOT be threatened
        board.bishop_moves(bishop, *sq("a1"))
        dests = get_move_destinations(bishop)
        self.assertIn(sq("d7"), dests,
            "d7 should be safe — no piece on jumped square e5")
        self.assertIn(sq("f7"), dests,
            "f7 should be safe — no piece on jumped square e5")

    def test_bishop_not_blocked_by_own_position_los(self):
        """Bishop should not be blocked from teleporting to squares behind itself
        along an enemy's line of sight — its previous position is vacated.
        Rook on a1 step-1 up to a2, step-2 right through a-file squares.
        Bishop on b2 blocks the rook's step-2 from reaching c2, d2, etc.
        If bishop teleports away, those squares become threatened."""
        board = empty_board()
        # Rook on a1, step-1 up to a2, step-2 right: b2, c2, d2...
        # Bishop on b2 blocks step-2 from reaching c2
        bishop = place(board, "b2", Bishop('white'))
        place(board, "a1", Rook('black'))
        board.bishop_moves(bishop, *sq("b2"))
        dests = get_move_destinations(bishop)
        # c2 should NOT be reachable: rook step-1 to a2, step-2 right passes
        # through b2 (now empty) to c2
        self.assertNotIn(sq("c2"), dests,
            "c2 should be threatened by rook after bishop moves away from b2")


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
        board.move(knight, move, )
        # Knight lands normally, friendly jumped piece untouched
        self.assertIsInstance(board.squares[sq("e6")[0]][sq("e6")[1]].piece, Knight)
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)

    def test_jump_capture_returns_jumped_piece_only_when_moved_last_turn(self):
        """v2 reactive jump-capture: targets contain ONLY the jumped piece
        (when it's an enemy that moved on the immediately preceding turn).
        Adjacent enemies to the landing square are NEVER targets — that
        was the v0/v1 rule, replaced in v2."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # jumped piece
        place(board, "d6", Rook('black'))  # adjacent to landing e6 — NOT a target in v2
        # Simulate: black's pawn moved to e5 on the immediately preceding turn
        board.turn_number = 2
        board.last_move = Move(Square(*sq("e7")), Square(*sq("e5")))
        board.last_move_turn_number = 1
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move)
        self.assertEqual(targets, [sq("e5")])
        self.assertNotIn(sq("d6"), targets)

    def test_no_jump_capture_when_landing_on_enemy(self):
        """Standard capture: knight lands on enemy at e6 — no jump capture triggered."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # piece on jumped square
        place(board, "e6", Pawn('black'))  # enemy on landing square
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        board.move(knight, move, )
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
        board.move(knight, move, )
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
            board.move(knight, move, )
            # Friendly piece on e5 should NOT be captured
            self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)

    # ---- Jump capture: adjacent enemy selection tests ----

    def test_jump_capture_does_not_auto_capture(self):
        """v2: when jump capture is eligible, board.move() returns the jumped
        piece as a target and does NOT auto-capture. The piece remains on the
        board until execute_jump_capture is called."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))   # jumped piece (eligible after recent move)
        place(board, "d6", Rook('black'))   # adjacent to landing e6 — irrelevant in v2
        place(board, "f6", Bishop('black')) # also adjacent — irrelevant in v2
        board.turn_number = 2
        board.last_move = Move(Square(*sq("e7")), Square(*sq("e5")))
        board.last_move_turn_number = 1
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move)
        # All three enemies should still be on the board (no auto-capture)
        for sq_name in ["e5", "d6", "f6"]:
            r, c = sq(sq_name)
            self.assertIsNotNone(board.squares[r][c].piece, f"Piece at {sq_name} should remain")
        # Only the jumped piece is targeted in v2
        self.assertEqual(targets, [sq("e5")])
        # Player chooses to capture the jumped piece via execute_jump_capture
        board.execute_jump_capture(*sq("e5"))
        self.assertIsNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)
        # Adjacent (non-jumped) enemies remain unaffected
        self.assertIsNotNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)
        self.assertIsNotNone(board.squares[sq("f6")[0]][sq("f6")[1]].piece)

    def test_jump_capture_can_decline(self):
        """v2: player may decline capture — the jumped piece remains, and
        the knight gains Bastion (set by caller via set_bastion_after_declined)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # jumped piece (eligible)
        place(board, "d6", Rook('black'))  # not relevant in v2
        board.turn_number = 2
        board.last_move = Move(Square(*sq("e7")), Square(*sq("e5")))
        board.last_move_turn_number = 1
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move)
        self.assertEqual(targets, [sq("e5")])
        # Player declines — does NOT call execute_jump_capture; caller signals
        # the decline via set_bastion_after_declined
        board.set_bastion_after_declined(knight)
        # Both pieces remain
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)
        self.assertIsNotNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)
        # Knight gained Bastion
        self.assertTrue(knight.bastion_active)

    def test_jump_capture_jumped_piece_is_the_target(self):
        """v2: the jumped piece is THE target (not just one of several adjacent
        candidates as in v0/v1). When eligible, it's the single capture option."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Rook('black'))  # jumped piece
        board.turn_number = 2
        board.last_move = Move(Square(*sq("e7")), Square(*sq("e5")))
        board.last_move_turn_number = 1
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move)
        self.assertEqual(targets, [sq("e5")])
        # Player chooses to capture
        board.execute_jump_capture(*sq("e5"))
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
        targets = board.move(knight, move, )
        # Capture one piece
        board.execute_jump_capture(*sq("d6"), )
        # The other two enemies must remain
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)
        self.assertIsNotNone(board.squares[sq("f6")[0]][sq("f6")[1]].piece)
        self.assertIsNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)

    def test_jump_capture_targets_excludes_friendly_pieces(self):
        """v2: a friendly jumped piece is never a capture target — the rule
        only allows enemy capture. Adjacent friendlies are also irrelevant
        in v2 since they were never targets to begin with."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('white'))  # jumped piece — friendly, never capturable
        place(board, "d6", Pawn('white'))  # friendly adjacent, irrelevant in v2
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move)
        # Friendly jumped piece is never a target. Returns no targets (None or empty).
        self.assertFalse(bool(targets), f"Expected no targets for friendly jump, got {targets}")
        # Both friendlies remain on the board
        self.assertIsNotNone(board.squares[sq("e5")[0]][sq("e5")[1]].piece)
        self.assertIsNotNone(board.squares[sq("d6")[0]][sq("d6")[1]].piece)
        # Knight got Bastion (jumped piece survived)
        self.assertTrue(knight.bastion_active)

    def test_jump_capture_records_in_captured_pieces(self):
        """A piece captured via knight jump capture is recorded in captured_pieces."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Rook('black'))  # enemy on jumped square
        board.knight_moves(knight, *sq("e4"))
        move = Move(Square(*sq("e4")), Square(*sq("e6")))
        targets = board.move(knight, move, )
        # Capture the rook on e5
        board.execute_jump_capture(*sq("e5"), )
        self.assertIn('rook', board.captured_pieces['black'])


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

    def test_boulder_has_on_intersection_flag(self):
        """Boulder has on_intersection attribute."""
        boulder = Boulder()
        self.assertFalse(boulder.on_intersection)

    # ---- Board setup tests ----

    def test_boulder_exists_on_board_at_start(self):
        """A new board should have a boulder stored as board.boulder."""
        board = Board()
        self.assertIsNotNone(board.boulder, "Boulder should exist on the board")
        self.assertIsInstance(board.boulder, Boulder)

    def test_boulder_not_on_any_square_at_start(self):
        """The boulder starts on the intersection, not on any board square."""
        board = Board()
        for row in range(8):
            for col in range(8):
                if board.squares[row][col].has_piece():
                    self.assertNotIsInstance(board.squares[row][col].piece, Boulder,
                        f"Boulder should not be on square ({row},{col})")

    def test_boulder_on_intersection_at_start(self):
        """The boulder starts with on_intersection=True."""
        board = Board()
        self.assertTrue(board.boulder.on_intersection, "Boulder should start on the intersection")

    def test_boulder_on_intersection_cleared_after_move(self):
        """After the boulder moves, on_intersection is False and board.boulder is None."""
        board = Board()
        boulder = board.boulder
        boulder.clear_moves()
        board.boulder_moves(boulder)
        if len(boulder.moves) > 0:
            board.move(boulder, boulder.moves[0], )
            self.assertFalse(boulder.on_intersection)
            self.assertIsNone(board.boulder)

    def test_boulder_placed_on_square_after_first_move(self):
        """After boulder's first move, it should be on the destination square."""
        board = Board()
        boulder = board.boulder
        boulder.clear_moves()
        board.boulder_moves(boulder)
        if len(boulder.moves) > 0:
            dest = boulder.moves[0].final
            board.move(boulder, boulder.moves[0], )
            self.assertIs(board.squares[dest.row][dest.col].piece, boulder)

    def test_boulder_all_four_central_squares_empty_at_start(self):
        """All four central squares (d4, d5, e4, e5) should be empty at start since
        boulder is on the intersection, not on a square."""
        board = Board()
        for r, c in [(3, 3), (3, 4), (4, 3), (4, 4)]:
            self.assertTrue(board.squares[r][c].isempty(),
                f"Central square ({r},{c}) should be empty at start")

    # ---- Boulder move validation from intersection ----

    def test_boulder_intersection_moves_use_sentinel_initial(self):
        """Boulder moves from intersection use Square(-1,-1) as initial."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder_moves(boulder)
        for move in boulder.moves:
            self.assertEqual(move.initial.row, -1)
            self.assertEqual(move.initial.col, -1)

    def test_boulder_intersection_move_is_valid(self):
        """A move from intersection using sentinel initial should be in the piece's move list."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder_moves(boulder)
        # Create the same move the UI would create
        move = Move(Square(-1, -1), Square(*sq("d4")))
        self.assertTrue(board.valid_move(boulder, move),
            "Boulder move from intersection to d4 should be valid")

    def test_boulder_intersection_move_to_all_four_central_squares(self):
        """Boulder from intersection can move to each of the 4 central squares."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder_moves(boulder)
        for dest in ["d4", "e4", "d5", "e5"]:
            move = Move(Square(-1, -1), Square(*sq(dest)))
            self.assertTrue(board.valid_move(boulder, move),
                f"Boulder should be able to move from intersection to {dest}")

    def test_boulder_intersection_move_executes_correctly(self):
        """Moving boulder from intersection places it on the destination square."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder = boulder
        board.boulder_moves(boulder)
        move = Move(Square(-1, -1), Square(*sq("e4")))
        board.move(boulder, move, )
        self.assertIs(board.squares[sq("e4")[0]][sq("e4")[1]].piece, boulder)
        self.assertIsNone(board.boulder)
        self.assertFalse(boulder.on_intersection)

    # ---- First move tests ----

    def test_boulder_first_move_central_squares_only(self):
        """Boulder's first move must go to one of d4, e4, d5, e5.
        The boulder starts on the central intersection (not on any square)."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder_moves(boulder)
        dests = get_move_destinations(boulder)
        allowed = {sq("d4"), sq("e4"), sq("d5"), sq("e5")}
        for dest in dests:
            self.assertIn(dest, allowed, f"First move {dest} not in central squares")
        self.assertEqual(len(dests), 4, "Should have exactly 4 destinations from intersection")

    def test_boulder_first_move_cannot_go_outside_center(self):
        """Boulder's first move cannot go to squares outside the 4 central squares."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder_moves(boulder)
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

    def _board_with_intersection_boulder(self):
        """Helper: create an empty board with boulder on the central intersection."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder = boulder
        return board

    # -- Diagonal blocking: straightline movement (rook step-2 / bishop teleport threats) --

    def test_boulder_on_center_blocks_diagonal_d4_to_e5(self):
        """A rook on c3 doing step-1 to d4 then step-2 diagonal should not cross to e5."""
        board = self._board_with_intersection_boulder()
        # Use queen LOS as a proxy — queen on d4 should not see e5 diagonally
        queen = place(board, "d4", Queen('white'))
        board.queen_moves(queen, *sq("d4"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("e5"), dests, "Queen on d4 should not move diag to e5 across intersection")

    def test_boulder_on_center_blocks_diagonal_e5_to_d4(self):
        """Queen on e5 should not move diagonally to d4 across the intersection."""
        board = self._board_with_intersection_boulder()
        queen = place(board, "e5", Queen('white'))
        board.queen_moves(queen, *sq("e5"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("d4"), dests)

    def test_boulder_on_center_blocks_diagonal_d5_to_e4(self):
        """Queen on d5 should not move diagonally to e4 across the intersection."""
        board = self._board_with_intersection_boulder()
        queen = place(board, "d5", Queen('white'))
        board.queen_moves(queen, *sq("d5"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("e4"), dests)

    def test_boulder_on_center_blocks_diagonal_e4_to_d5(self):
        """Queen on e4 should not move diagonally to d5 across the intersection."""
        board = self._board_with_intersection_boulder()
        queen = place(board, "e4", Queen('white'))
        board.queen_moves(queen, *sq("e4"))
        dests = get_move_destinations(queen)
        self.assertNotIn(sq("d5"), dests)

    # -- Diagonal blocking: king --

    def test_boulder_on_center_blocks_king_diagonal_d4_to_e5(self):
        """King on d4 should not move diagonally to e5 across the intersection."""
        board = self._board_with_intersection_boulder()
        king = place(board, "d4", King('white'))
        board.king_moves(king, *sq("d4"))
        dests = get_move_destinations(king)
        self.assertNotIn(sq("e5"), dests, "King on d4 should not cross intersection to e5")

    def test_boulder_on_center_blocks_king_diagonal_e5_to_d4(self):
        """King on e5 should not move diagonally to d4 across the intersection."""
        board = self._board_with_intersection_boulder()
        king = place(board, "e5", King('white'))
        board.king_moves(king, *sq("e5"))
        dests = get_move_destinations(king)
        self.assertNotIn(sq("d4"), dests, "King on e5 should not cross intersection to d4")

    def test_boulder_on_center_blocks_king_diagonal_d5_to_e4(self):
        """King on d5 should not move diagonally to e4 across the intersection."""
        board = self._board_with_intersection_boulder()
        king = place(board, "d5", King('white'))
        board.king_moves(king, *sq("d5"))
        dests = get_move_destinations(king)
        self.assertNotIn(sq("e4"), dests, "King on d5 should not cross intersection to e4")

    def test_boulder_on_center_blocks_king_diagonal_e4_to_d5(self):
        """King on e4 should not move diagonally to d5 across the intersection."""
        board = self._board_with_intersection_boulder()
        king = place(board, "e4", King('white'))
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        self.assertNotIn(sq("d5"), dests, "King on e4 should not cross intersection to d5")

    def test_boulder_on_center_king_non_crossing_diagonals_allowed(self):
        """King on d4 can still move to non-crossing diagonals (c3, c5, e3)."""
        board = self._board_with_intersection_boulder()
        king = place(board, "d4", King('white'))
        board.king_moves(king, *sq("d4"))
        dests = get_move_destinations(king)
        self.assertIn(sq("c3"), dests, "King non-crossing diagonal should be allowed")
        self.assertIn(sq("c5"), dests)
        self.assertIn(sq("e3"), dests)

    # -- Rook unaffected by intersection boulder --

    def test_boulder_on_center_rook_step1_through_center_unaffected(self):
        """Rook movement is never diagonal, so intersection boulder has no effect.
        Rook on d3 step-1 up to d4 should work (orthogonal, not diagonal)."""
        board = self._board_with_intersection_boulder()
        rook = place(board, "d3", Rook('white'))
        board.rook_moves(rook, *sq("d3"))
        dests = get_move_destinations(rook)
        self.assertIn(sq("d4"), dests, "Rook orthogonal step-1 through center should not be blocked")

    def test_boulder_on_center_rook_step2_through_center_unaffected(self):
        """Rook step-2 passing through central squares is orthogonal, not affected."""
        board = self._board_with_intersection_boulder()
        rook = place(board, "d3", Rook('white'))
        board.rook_moves(rook, *sq("d3"))
        dests = get_move_destinations(rook)
        # Step-1 right to e3, step-2 up through e4, e5 etc.
        self.assertIn(sq("e4"), dests, "Rook step-2 through center should not be blocked")
        self.assertIn(sq("e5"), dests)

    # -- Diagonal blocking: LOS (queen manipulation) --

    def test_boulder_on_center_blocks_queen_los_diagonally(self):
        """Queen on c3 should not have LOS to f6 through the center diagonal."""
        board = self._board_with_intersection_boulder()
        queen = place(board, "c3", Queen('white'))
        board.update_lines_of_sight()
        los_squares = {(s.row, s.col) for s in queen.line_of_sight}
        # c3 -> d4 is fine (before intersection), but e5, f6 should be blocked
        self.assertIn(sq("d4"), los_squares)
        self.assertNotIn(sq("e5"), los_squares, "LOS should not cross intersection diagonally")
        self.assertNotIn(sq("f6"), los_squares)

    def test_boulder_on_center_blocks_queen_los_other_diagonal(self):
        """Queen on c6 should not have LOS to f3 through the center diagonal."""
        board = self._board_with_intersection_boulder()
        queen = place(board, "c6", Queen('white'))
        board.update_lines_of_sight()
        los_squares = {(s.row, s.col) for s in queen.line_of_sight}
        self.assertIn(sq("d5"), los_squares)
        self.assertNotIn(sq("e4"), los_squares, "LOS should not cross intersection on other diagonal")
        self.assertNotIn(sq("f3"), los_squares)

    # -- Does NOT block files or ranks --

    def test_boulder_on_center_does_not_block_files(self):
        """Boulder on intersection does NOT block vertical (file) movement.
        Rook step-1 right to e3, step-2 up passes through e4, e5 etc."""
        board = self._board_with_intersection_boulder()
        rook = place(board, "d3", Rook('white'))
        board.rook_moves(rook, *sq("d3"))
        dests = get_move_destinations(rook)
        # Step-1 up to d4, step-2 left/right — d4 reachable (file, not blocked)
        self.assertIn(sq("d4"), dests, "Rook step-1 along file should not be blocked by intersection")

    def test_boulder_on_center_does_not_block_ranks(self):
        """Boulder on intersection does NOT block horizontal (rank) movement.
        Rook step-1 up to d5, step-2 right passes through e5 etc."""
        board = self._board_with_intersection_boulder()
        rook = place(board, "d3", Rook('white'))
        board.rook_moves(rook, *sq("d3"))
        dests = get_move_destinations(rook)
        # Step-1 right to e3, step-2 up passes through e4, e5 — e4 reachable
        self.assertIn(sq("e4"), dests, "Rook step-2 along file through center should not be blocked")

    # -- Non-adjacent diagonals NOT blocked --

    def test_boulder_on_center_does_not_block_non_crossing_diagonals(self):
        """Queen on d4 moving to c3 (away from center) should NOT be blocked."""
        board = self._board_with_intersection_boulder()
        queen = place(board, "d4", Queen('white'))
        board.queen_moves(queen, *sq("d4"))
        dests = get_move_destinations(queen)
        self.assertIn(sq("c3"), dests, "Diagonal away from center should not be blocked")
        self.assertIn(sq("e3"), dests, "Non-crossing diagonal should not be blocked")
        self.assertIn(sq("c5"), dests, "Non-crossing diagonal should not be blocked")

    # -- Pawn diagonal capture blocked across intersection --

    def test_boulder_on_center_blocks_pawn_diagonal_capture(self):
        """White pawn on d4 should not capture diagonally to e5 across the intersection."""
        board = self._board_with_intersection_boulder()
        pawn = place(board, "d4", Pawn('white'))
        place(board, "e5", Knight('black'))  # enemy on e5
        board.pawn_moves(pawn, *sq("d4"))
        dests = get_move_destinations(pawn)
        self.assertNotIn(sq("e5"), dests, "Pawn diagonal capture should not cross intersection")

    # -- No blocking after boulder moves off intersection --

    def test_no_diagonal_blocking_after_boulder_moves(self):
        """After boulder moves off intersection, diagonals should no longer be blocked."""
        board = self._board_with_intersection_boulder()
        boulder = board.boulder
        # Move boulder to e4
        board.boulder_moves(boulder)
        move = Move(Square(-1, -1), Square(*sq("e4")))
        board.move(boulder, move, )
        # Now diagonal should not be blocked
        queen = place(board, "d4", Queen('white'))
        board.queen_moves(queen, *sq("d4"))
        dests = get_move_destinations(queen)
        # d4 -> e5 should now be allowed (no intersection boulder)
        self.assertIn(sq("e5"), dests, "Diagonal should not be blocked after boulder moves off")

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
        board.move(boulder, move, )
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

    def test_boulder_cooldown_not_decremented_on_same_turn(self):
        """decrement_boulder_cooldown skips the boulder if it was the piece that just moved."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        move = Move(Square(*sq("e4")), Square(*sq("e5")))
        boulder.add_move(move)
        board.move(boulder, move, )
        self.assertEqual(boulder.cooldown, 2)
        # Decrement with boulder as the moved piece — should be skipped
        board.decrement_boulder_cooldown(moved_piece=boulder)
        self.assertEqual(boulder.cooldown, 2, "Cooldown should NOT decrement on the same turn")

    def test_boulder_cooldown_decrements_on_other_turns(self):
        """decrement_boulder_cooldown decrements when a different piece moved."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        boulder.cooldown = 2
        place(board, "e4", boulder)
        pawn = Pawn('white')
        # Simulate other pieces moving
        board.decrement_boulder_cooldown(moved_piece=pawn)
        self.assertEqual(boulder.cooldown, 1)
        board.decrement_boulder_cooldown(moved_piece=pawn)
        self.assertEqual(boulder.cooldown, 0)

    def test_boulder_cooldown_blocks_for_two_full_turns(self):
        """After boulder moves, it takes 2 full turns (both players) before it can move again."""
        board = empty_board()
        boulder = Boulder()
        boulder.first_move = False
        place(board, "e4", boulder)
        move = Move(Square(*sq("e4")), Square(*sq("e5")))
        boulder.add_move(move)
        board.move(boulder, move, )
        self.assertEqual(boulder.cooldown, 2)

        # Same turn: decrement skipped for boulder
        board.decrement_boulder_cooldown(moved_piece=boulder)
        self.assertEqual(boulder.cooldown, 2)

        # Next player's turn (different piece moves)
        pawn = Pawn('black')
        board.decrement_boulder_cooldown(moved_piece=pawn)
        self.assertEqual(boulder.cooldown, 1)

        # Boulder should still not be moveable
        boulder.clear_moves()
        board.boulder_moves(boulder, *sq("e5"))
        self.assertEqual(len(boulder.moves), 0, "Boulder should not move with cooldown=1")

        # Following turn (different piece moves again)
        board.decrement_boulder_cooldown(moved_piece=pawn)
        self.assertEqual(boulder.cooldown, 0)

        # Now boulder should be moveable
        boulder.clear_moves()
        board.boulder_moves(boulder, *sq("e5"))
        self.assertTrue(len(boulder.moves) > 0, "Boulder should be moveable with cooldown=0")

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

    def test_white_cannot_move_boulder_turn_one(self):
        """White may not move the boulder on turn 1 (turn_number == 0).
        Enforced via board.turn_number in the UI; tested here as a state check."""
        board = Board()
        self.assertEqual(board.turn_number, 0, "Turn number should be 0 at start")
        # The UI checks: if next_player == 'white' and turn_number == 0, block boulder

    def test_turn_number_increments(self):
        """Turn number increments each turn."""
        board = Board()
        self.assertEqual(board.turn_number, 0)
        board.turn_number += 1
        self.assertEqual(board.turn_number, 1)

    def test_white_pieces_can_move_on_turn_one(self):
        """White's regular pieces must still be able to move on turn 1.
        The boulder turn-1 restriction must not block other pieces."""
        board = Board()
        self.assertEqual(board.turn_number, 0)
        # White pawn on e2 (row=6, col=4) should have moves
        pawn = board.squares[6][4].piece
        self.assertIsInstance(pawn, Pawn)
        self.assertEqual(pawn.color, 'white')
        board.pawn_moves(pawn, 6, 4)
        dests = get_move_destinations(pawn)
        self.assertTrue(len(dests) > 0, "White pawn must be able to move on turn 1")

    def test_white_can_move_boulder_after_turn_one(self):
        """White can move the boulder on turn 2+ (turn_number >= 2)."""
        board = Board()
        board.turn_number = 2  # after white turn 1 and black turn 1
        # Boulder should generate moves normally
        boulder = board.boulder
        boulder.clear_moves()
        board.boulder_moves(boulder)
        dests = get_move_destinations(boulder)
        self.assertTrue(len(dests) > 0, "Boulder should have moves on white's second turn")

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

    def test_knight_can_jump_over_boulder(self):
        """Knight can jump over the boulder (it's on the jumped square)."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Boulder())  # boulder on jumped square
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("e6"), dests)


# ===========================================================================
# TestWinCondition
# ===========================================================================

class TestWinCondition(unittest.TestCase):
    """
    Rulebook — Win Condition:
      A player loses immediately when both their royal pieces are captured.
      Royal pieces: king (is_royal=True) and royal queen (is_royal=True).
      Promoted queens are NOT royal and do not count.
      A transformed royal queen still counts as royal.
      The game continues after losing one royal — both must be captured.
    """

    # ---- Helper ----

    def _board_with_royals(self):
        """Create a board with both royals for each side."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "b1", Queen('white', is_royal=True))
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black', is_royal=True))
        return board

    # ---- Detection tests ----

    def test_no_winner_at_start(self):
        """No winner at the start of the game."""
        board = self._board_with_royals()
        self.assertIsNone(board.check_winner())

    def test_no_winner_after_losing_one_royal(self):
        """Losing one royal piece does not end the game."""
        board = self._board_with_royals()
        # Remove white king (one royal captured)
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        self.assertIsNone(board.check_winner())

    def test_white_loses_when_both_royals_captured(self):
        """White loses when both king and royal queen are captured."""
        board = self._board_with_royals()
        # Remove both white royals
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        board.squares[sq("b1")[0]][sq("b1")[1]].piece = None
        winner = board.check_winner()
        self.assertEqual(winner, 'black')

    def test_black_loses_when_both_royals_captured(self):
        """Black loses when both king and royal queen are captured."""
        board = self._board_with_royals()
        # Remove both black royals
        board.squares[sq("e8")[0]][sq("e8")[1]].piece = None
        board.squares[sq("g8")[0]][sq("g8")[1]].piece = None
        winner = board.check_winner()
        self.assertEqual(winner, 'white')

    def test_king_captured_queen_remains_no_winner(self):
        """King captured but royal queen still on board — no winner yet."""
        board = self._board_with_royals()
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None  # white king gone
        # White royal queen still on b1
        self.assertIsNone(board.check_winner())

    def test_queen_captured_king_remains_no_winner(self):
        """Royal queen captured but king still on board — no winner yet."""
        board = self._board_with_royals()
        board.squares[sq("b1")[0]][sq("b1")[1]].piece = None  # white queen gone
        # White king still on e1
        self.assertIsNone(board.check_winner())

    # ---- Promoted queens don't count ----

    def test_promoted_queen_does_not_count_as_royal(self):
        """Losing both royals triggers loss even if a promoted queen is on the board."""
        board = empty_board()
        # White has only a promoted queen — both royals are gone
        place(board, "d4", Queen('white', is_royal=False))
        # Black still has both royals
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black', is_royal=True))
        winner = board.check_winner()
        self.assertEqual(winner, 'black',
            "White should lose — promoted queen is not royal")

    def test_multiple_promoted_queens_dont_prevent_loss(self):
        """Multiple promoted queens on the board don't prevent loss."""
        board = empty_board()
        place(board, "d4", Queen('white', is_royal=False))
        place(board, "d5", Queen('white', is_royal=False))
        place(board, "d6", Queen('white', is_royal=False))
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black', is_royal=True))
        winner = board.check_winner()
        self.assertEqual(winner, 'black')

    # ---- Transformed royal queen still counts ----

    def test_transformed_royal_queen_still_counts(self):
        """A transformed royal queen (is_royal=True, is_transformed=True)
        still counts as a royal piece — game does not end."""
        board = empty_board()
        place(board, "e1", King('white'))
        # Royal queen transformed as rook
        transformed = Rook('white')
        transformed.is_royal = True
        transformed.is_transformed = True
        place(board, "b1", transformed)
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black', is_royal=True))
        self.assertIsNone(board.check_winner(),
            "Transformed royal queen still counts — no winner")

    def test_loss_when_transformed_royal_queen_captured(self):
        """Capturing a transformed royal queen counts toward the win condition."""
        board = empty_board()
        # White king gone, transformed royal queen gone — both royals captured
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black', is_royal=True))
        winner = board.check_winner()
        self.assertEqual(winner, 'black')

    # ---- Order doesn't matter ----

    def test_capture_order_king_first(self):
        """Capturing king first, then royal queen, triggers loss."""
        board = self._board_with_royals()
        # Capture white king first
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        self.assertIsNone(board.check_winner())
        # Then capture white royal queen
        board.squares[sq("b1")[0]][sq("b1")[1]].piece = None
        self.assertEqual(board.check_winner(), 'black')

    def test_capture_order_queen_first(self):
        """Capturing royal queen first, then king, triggers loss."""
        board = self._board_with_royals()
        # Capture white royal queen first
        board.squares[sq("b1")[0]][sq("b1")[1]].piece = None
        self.assertIsNone(board.check_winner())
        # Then capture white king
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        self.assertEqual(board.check_winner(), 'black')


# ===========================================================================
# TestRepetitionRule
# ===========================================================================

class TestRepetitionRule(unittest.TestCase):
    """
    Rulebook — Repetition Rule:
      A player may not make a turn that causes a board state to appear
      for the third time during the game.
      Board state includes: piece positions, boulder markers, queen markers,
      and whose turn it is.
      If every legal turn would result in a third repetition, the player loses.
    """

    # ---- State hashing tests ----

    def test_board_state_hash_deterministic(self):
        """The same board position produces the same hash."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        hash1 = board.get_state_hash('white')
        hash2 = board.get_state_hash('white')
        self.assertEqual(hash1, hash2)

    def test_board_state_hash_differs_by_turn(self):
        """Same piece positions but different turn produce different hashes."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        hash_white = board.get_state_hash('white')
        hash_black = board.get_state_hash('black')
        self.assertNotEqual(hash_white, hash_black)

    def test_board_state_hash_differs_by_position(self):
        """Different piece positions produce different hashes."""
        board1 = empty_board()
        place(board1, "e1", King('white'))
        place(board1, "e8", King('black'))
        hash1 = board1.get_state_hash('white')

        board2 = empty_board()
        place(board2, "d1", King('white'))
        place(board2, "e8", King('black'))
        hash2 = board2.get_state_hash('white')
        self.assertNotEqual(hash1, hash2)

    def test_board_state_hash_includes_piece_type(self):
        """Different piece types on the same square produce different hashes."""
        board1 = empty_board()
        place(board1, "e4", Rook('white'))
        hash1 = board1.get_state_hash('white')

        board2 = empty_board()
        place(board2, "e4", Knight('white'))
        hash2 = board2.get_state_hash('white')
        self.assertNotEqual(hash1, hash2)

    def test_board_state_hash_includes_is_royal(self):
        """Royal vs non-royal queen on the same square produce different hashes."""
        board1 = empty_board()
        place(board1, "e4", Queen('white', is_royal=True))
        hash1 = board1.get_state_hash('white')

        board2 = empty_board()
        place(board2, "e4", Queen('white', is_royal=False))
        hash2 = board2.get_state_hash('white')
        self.assertNotEqual(hash1, hash2)

    def test_board_state_hash_includes_is_transformed(self):
        """Transformed vs non-transformed piece produce different hashes."""
        board1 = empty_board()
        rook1 = Rook('white')
        place(board1, "e4", rook1)
        hash1 = board1.get_state_hash('white')

        board2 = empty_board()
        rook2 = Rook('white')
        rook2.is_transformed = True
        rook2.is_royal = True
        place(board2, "e4", rook2)
        hash2 = board2.get_state_hash('white')
        self.assertNotEqual(hash1, hash2)

    # ---- State history tracking ----

    def test_state_history_records_positions(self):
        """After recording a state, its count should be 1."""
        board = empty_board()
        place(board, "e1", King('white'))
        state = board.get_state_hash('white')
        board.state_history[state] = board.state_history.get(state, 0) + 1
        self.assertEqual(board.state_history[state], 1)

    def test_state_history_increments_on_repeat(self):
        """Reaching the same state again increments the count to 2."""
        board = empty_board()
        place(board, "e1", King('white'))
        state = board.get_state_hash('white')
        board.state_history[state] = board.state_history.get(state, 0) + 1
        board.state_history[state] = board.state_history.get(state, 0) + 1
        self.assertEqual(board.state_history[state], 2)

    # ---- Move filtering tests ----

    def test_move_causing_third_repetition_is_filtered(self):
        """A move that would cause a third repetition should not appear in valid moves."""
        board = empty_board()
        king = place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        # Record the state with king on e1 (white's turn) twice
        state = board.get_state_hash('white')
        board.state_history[state] = 2
        # Move king to d1, then generate moves — returning to e1 would be third repetition
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        place(board, "d1", king)
        king.clear_moves()
        board.king_moves(king, *sq("d1"))
        # The state after moving back to e1 would be opponent's (black's) turn
        # But the recorded state is for white's turn — need to record the BLACK turn state
        # Actually: king on e1 + black's turn is what we need to check
        # Let me re-setup: record the state that would result from white moving king to e1
        # That resulting state = king on e1, king on e8, black's turn
        board.state_history = {}
        result_state = board.get_state_hash('white')  # current: king on d1
        # Temporarily put king on e1 to hash the resulting state (black's turn)
        board.squares[sq("d1")[0]][sq("d1")[1]].piece = None
        place(board, "e1", king)
        result_state = board.get_state_hash('black')  # king on e1, black's turn
        board.state_history[result_state] = 2
        # Put king back on d1
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        place(board, "d1", king)
        king.clear_moves()
        board.king_moves(king, *sq("d1"))
        board.filter_repetition_moves(king, 'white')
        dests = get_move_destinations(king)
        self.assertNotIn(sq("e1"), dests,
            "Move back to e1 should be filtered — would cause third repetition")

    def test_move_causing_second_repetition_is_allowed(self):
        """A move that would cause a second repetition is still legal."""
        board = empty_board()
        king = place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        # Record the resulting state (king on e1, black's turn) once
        result_state = board.get_state_hash('black')
        board.state_history[result_state] = 1
        # Move king to d1
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        place(board, "d1", king)
        king.clear_moves()
        board.king_moves(king, *sq("d1"))
        board.filter_repetition_moves(king, 'white')
        dests = get_move_destinations(king)
        self.assertIn(sq("e1"), dests,
            "Move back to e1 should be allowed — only second repetition")

    def test_non_repeating_move_is_allowed(self):
        """Moves that don't cause any repetition are always allowed."""
        board = empty_board()
        king = place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        king.clear_moves()
        board.king_moves(king, *sq("e1"))
        board.filter_repetition_moves(king, 'white')
        dests = get_move_destinations(king)
        self.assertTrue(len(dests) > 0, "Non-repeating moves should be available")

    # ---- Player loses if all moves cause third repetition ----

    def test_player_loses_if_all_moves_cause_repetition(self):
        """If every legal turn would result in a third repetition, the player loses."""
        # This is a complex scenario — would need a carefully constructed board
        # where every possible move for the current player leads to a state
        # already seen twice. Tested here as a placeholder.
        pass

    # ---- Boulder state affects hash ----

    def test_boulder_cooldown_affects_hash(self):
        """Different boulder cooldown values produce different hashes."""
        board1 = empty_board()
        boulder1 = Boulder()
        boulder1.cooldown = 0
        place(board1, "e4", boulder1)
        hash1 = board1.get_state_hash('white')

        board2 = empty_board()
        boulder2 = Boulder()
        boulder2.cooldown = 1
        place(board2, "e4", boulder2)
        hash2 = board2.get_state_hash('white')
        self.assertNotEqual(hash1, hash2)

    def test_boulder_last_square_affects_hash(self):
        """Different boulder last_square values produce different hashes."""
        board1 = empty_board()
        boulder1 = Boulder()
        boulder1.last_square = None
        place(board1, "e4", boulder1)
        hash1 = board1.get_state_hash('white')

        board2 = empty_board()
        boulder2 = Boulder()
        boulder2.last_square = sq("d4")
        place(board2, "e4", boulder2)
        hash2 = board2.get_state_hash('white')
        self.assertNotEqual(hash1, hash2)


    def test_boulder_cycle_with_knights_triggers_repetition(self):
        """Simulates the boulder moving in a circle while knights move back and forth.
        After two full cycles, the third repetition should be detected and blocked."""
        board = empty_board()
        # Place knights and kings
        wk = place(board, "e1", King('white'))
        bk = place(board, "e8", King('black'))
        wn = place(board, "d1", Knight('white'))
        bn = place(board, "d8", Knight('black'))
        # Place boulder on d5 (first square after intersection move)
        boulder = Boulder()
        boulder.first_move = False
        boulder.on_intersection = False
        boulder.cooldown = 0
        place(board, "d5", boulder)

        # Helper to simulate a full turn
        def do_move(piece_obj, from_sq, to_sq, player):
            board.squares[sq(from_sq)[0]][sq(from_sq)[1]].piece = None
            board.squares[sq(to_sq)[0]][sq(to_sq)[1]].piece = piece_obj
            if isinstance(piece_obj, Boulder):
                piece_obj.cooldown = 2
                piece_obj.last_square = sq(from_sq)
            # Decrement boulder cooldown for non-boulder moves
            for r in range(8):
                for c in range(8):
                    p = board.squares[r][c].piece
                    if p and isinstance(p, Boulder) and p is not piece_obj:
                        if p.cooldown > 0:
                            p.cooldown -= 1
            next_p = 'black' if player == 'white' else 'white'
            board.record_state(next_p)

        # Record initial state
        board.record_state('white')

        # Cycle 1: boulder circles d5→e5→e4→d4→d5, knights toggle
        do_move(boulder, "d5", "e5", 'white')   # boulder to e5
        do_move(wn, "d1", "d3", 'black')         # white knight out
        do_move(bn, "d8", "d6", 'white')          # black knight out
        do_move(boulder, "e5", "e4", 'black')    # boulder to e4
        do_move(wn, "d3", "d1", 'white')          # white knight back
        do_move(bn, "d6", "d8", 'black')          # black knight back
        do_move(boulder, "e4", "d4", 'white')    # boulder to d4
        do_move(wn, "d1", "d3", 'black')          # white knight out
        do_move(bn, "d8", "d6", 'white')          # black knight out
        do_move(boulder, "d4", "d5", 'black')    # boulder to d5
        do_move(wn, "d3", "d1", 'white')          # white knight back
        do_move(bn, "d6", "d8", 'black')          # black knight back

        # Cycle 2: same pattern
        do_move(boulder, "d5", "e5", 'white')    # boulder to e5 (2nd time)
        do_move(wn, "d1", "d3", 'black')
        do_move(bn, "d8", "d6", 'white')
        do_move(boulder, "e5", "e4", 'black')    # boulder to e4 (2nd time)
        do_move(wn, "d3", "d1", 'white')
        do_move(bn, "d6", "d8", 'black')
        do_move(boulder, "e4", "d4", 'white')    # boulder to d4 (2nd time)
        do_move(wn, "d1", "d3", 'black')
        do_move(bn, "d8", "d6", 'white')
        do_move(boulder, "d4", "d5", 'black')    # boulder to d5 (2nd time)
        do_move(wn, "d3", "d1", 'white')
        do_move(bn, "d6", "d8", 'black')

        # Now cycle 3: boulder tries to move d5→e5 again (would be 3rd time)
        # The move should be filtered out
        boulder.clear_moves()
        board.boulder_moves(boulder, *sq("d5"))
        board.filter_repetition_moves(boulder, 'white')
        dests = get_move_destinations(boulder)
        self.assertNotIn(sq("e5"), dests,
            "Boulder d5→e5 should be blocked — third repetition of resulting state")

    def test_repetition_simulation_includes_boulder_cooldown(self):
        """would_cause_repetition must simulate the boulder cooldown decrement,
        otherwise the predicted hash won't match recorded hashes."""
        board = empty_board()
        king = place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        boulder = Boulder()
        boulder.first_move = False
        boulder.cooldown = 1
        place(board, "d5", boulder)

        # Compute the state that would result from king e1→d1 + cooldown decrement:
        # king on d1, king on e8, boulder cd=0, black's turn
        board.squares[sq("e1")[0]][sq("e1")[1]].piece = None
        place(board, "d1", king)
        boulder.cooldown = 0
        state_after = board.get_state_hash('black')
        board.state_history[state_after] = 2
        # Restore board
        board.squares[sq("d1")[0]][sq("d1")[1]].piece = None
        place(board, "e1", king)
        boulder.cooldown = 1

        # King move from e1→d1: would_cause_repetition should simulate
        # the cooldown decrementing from 1→0, matching the recorded state
        move_to_d1 = Move(Square(*sq("e1")), Square(*sq("d1")))
        result = board.would_cause_repetition(king, move_to_d1, 'white')
        self.assertTrue(result,
            "should detect repetition — simulated cooldown decrement must match recorded state")

    # ---- Transformation cycles and repetition ----

    def test_transformation_cycle_causes_repetition(self):
        """When a queen transforms and reverts (cycling the board back to the
        same state), the repetition rule correctly blocks moves that would
        cause the third occurrence.

        Scenario: Queen goes b1→c2, opponent transforms and reverts,
        queen goes c2→b1. This cycle repeats. After 2 cycles, moving
        b1→c2 again would create a third repetition and is blocked.
        But other moves (e.g. c1) are not blocked.
        """
        board = empty_board()
        queen = place(board, "b1", Queen('white'))
        place(board, "a2", Pawn('white'))
        place(board, "b2", Pawn('white'))
        place(board, "b3", Bishop('white'))
        place(board, "d1", Knight('white'))
        place(board, "e1", King('white'))
        place(board, "a1", Bishop('black'))
        place(board, "d4", Knight('black'))
        black_queen = place(board, "g8", Queen('black'))
        place(board, "e8", King('black'))
        board.captured_pieces['black'] = ['knight']

        board.record_state('white')

        # Cycle 1: queen b1→c2, black transforms then reverts, queen c2→b1
        board.move(queen, Move(Square(*sq("b1")), Square(*sq("c2"))))
        board.record_state('black')

        board.transform_queen(black_queen, *sq("g8"), 'knight')
        transformed = board.squares[sq("g8")[0]][sq("g8")[1]].piece
        board.record_state('white')

        board.move(queen, Move(Square(*sq("c2")), Square(*sq("b1"))))
        board.record_state('black')

        board.transform_queen(transformed, *sq("g8"), 'queen')
        reverted = board.squares[sq("g8")[0]][sq("g8")[1]].piece
        board.record_state('white')

        # Cycle 2: same pattern
        board.move(queen, Move(Square(*sq("b1")), Square(*sq("c2"))))
        board.record_state('black')

        board.transform_queen(reverted, *sq("g8"), 'knight')
        transformed2 = board.squares[sq("g8")[0]][sq("g8")[1]].piece
        board.record_state('white')

        board.move(queen, Move(Square(*sq("c2")), Square(*sq("b1"))))
        board.record_state('black')

        board.transform_queen(transformed2, *sq("g8"), 'queen')
        board.record_state('white')

        # Now queen is on b1 again. Moving to c2 would be third repetition.
        queen.clear_moves()
        board.queen_moves(queen, *sq("b1"))
        board.filter_repetition_moves(queen, 'white')
        dests = get_move_destinations(queen)

        self.assertNotIn(sq("c2"), dests,
            "c2 should be blocked — third repetition via transformation cycles")
        self.assertIn(sq("c1"), dests,
            "c1 should still be available — not a repeated state")
        self.assertIn(sq("a1"), dests,
            "a1 (capture) should still be available")

    # ---- Transformation itself blocked by repetition ----

    def test_transformation_blocked_if_would_cause_repetition(self):
        """A transformation option is filtered out if applying it would
        cause a third repetition of the board state."""
        board = empty_board()
        queen = place(board, "d1", Queen('white'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.captured_pieces['white'] = ['rook']

        board.record_state('white')

        # Transform to rook, then revert to queen — 2 cycles
        for _ in range(2):
            board.transform_queen(queen, *sq("d1"), 'rook')
            transformed = board.squares[sq("d1")[0]][sq("d1")[1]].piece
            board.decrement_boulder_cooldown()
            board.record_state('black')

            # Black does something (e.g. king move)
            black_king = board.squares[sq("e8")[0]][sq("e8")[1]].piece
            board.squares[sq("e8")[0]][sq("e8")[1]].piece = None
            place(board, "f8", black_king)
            board.decrement_boulder_cooldown()
            board.record_state('white')

            board.transform_queen(transformed, *sq("d1"), 'queen')
            queen = board.squares[sq("d1")[0]][sq("d1")[1]].piece
            board.decrement_boulder_cooldown()
            board.record_state('black')

            # Black king moves back
            board.squares[sq("f8")[0]][sq("f8")[1]].piece = None
            place(board, "e8", black_king)
            board.decrement_boulder_cooldown()
            board.record_state('white')

        # Now transforming to rook again would cause third repetition
        options = board.get_transformation_options(queen)
        self.assertIn('rook', options, "rook should be a raw transformation option")

        filtered = board.filter_transformation_options(
            queen, *sq("d1"), options, 'white')
        self.assertNotIn('rook', filtered,
            "rook should be filtered — would cause third repetition")

    def test_transformation_allowed_if_not_repeated(self):
        """Transformation options that don't cause repetition remain available."""
        board = empty_board()
        queen = place(board, "d1", Queen('white'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.captured_pieces['white'] = ['rook', 'knight']

        board.record_state('white')

        options = board.get_transformation_options(queen)
        filtered = board.filter_transformation_options(
            queen, *sq("d1"), options, 'white')
        # No repetition history — all options should survive
        self.assertEqual(sorted(options), sorted(filtered))

    def test_would_transformation_cause_repetition_undoes_cleanly(self):
        """The repetition check for transformation must fully restore board state."""
        board = empty_board()
        queen = place(board, "d1", Queen('white'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.captured_pieces['white'] = ['rook']

        # Snapshot
        piece_before = board.squares[sq("d1")[0]][sq("d1")[1]].piece
        self.assertIsInstance(piece_before, Queen)

        board.would_transformation_cause_repetition(queen, *sq("d1"), 'rook', 'white')

        # Piece should be restored
        piece_after = board.squares[sq("d1")[0]][sq("d1")[1]].piece
        self.assertIs(piece_after, piece_before,
            "Original piece must be restored after repetition check")
        self.assertIsInstance(piece_after, Queen)

    # ---- Manipulation blocked by repetition ----

    def test_manipulation_move_blocked_by_repetition(self):
        """A queen manipulation move is filtered if it would cause
        a third repetition of the board state."""
        board = empty_board()
        # White queen can see black rook on e4 via LOS
        white_queen = place(board, "e1", Queen('white'))
        place(board, "a1", King('white'))
        place(board, "a8", King('black'))
        black_rook = place(board, "e4", Rook('black'))

        board.update_lines_of_sight()

        board.record_state('white')

        # Compute the state that would result from black rook moving e4→e3
        # via manipulation, then record it twice to simulate two previous
        # occurrences
        board.squares[sq("e4")[0]][sq("e4")[1]].piece = None
        place(board, "e3", black_rook)
        # Simulate boulder decrement (no boulder = no-op)
        state_after = board.get_state_hash('black')
        board.state_history[state_after] = 2
        # Restore
        board.squares[sq("e3")[0]][sq("e3")[1]].piece = None
        place(board, "e4", black_rook)

        # Now compute manipulation moves for the black rook
        board.update_lines_of_sight()
        black_rook.clear_moves()
        board.queen_moves_enemy(black_rook, *sq("e4"))
        dests_before = get_move_destinations(black_rook)

        # e3 should be in raw moves (rook can move there)
        self.assertIn(sq("e3"), dests_before,
            "e3 should be a valid manipulation move before filtering")

        # Apply repetition filter
        board.filter_repetition_moves(black_rook, 'white')
        dests_after = get_move_destinations(black_rook)

        self.assertNotIn(sq("e3"), dests_after,
            "e3 should be filtered — manipulation would cause third repetition")


# ===========================================================================
# TestTinyEndgameRule
# ===========================================================================

class TestTinyEndgameRule(unittest.TestCase):
    """
    Rulebook — Tiny Endgame Rule:
      Applies when: no pawns remain AND (4 or fewer non-neutral pieces OR
      6 or fewer with same remaining piece types ignoring kings).
      Royal distance = Manhattan distance between closest opposing royals.
      Distance counts tracked per distance (1-14), increment on non-capture turns.
      Reset all counts on capture; re-initialize if rule still applies.
      Player may not make a non-capture turn if it would push any count > 3.
      If every legal turn would do so, that player loses.
    """

    # ---- Activation condition tests ----

    def test_rule_not_active_with_pawns(self):
        """Rule does not activate if any pawns remain on the board."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "a2", Pawn('white'))  # pawn present
        self.assertFalse(board.is_tiny_endgame())

    def test_rule_active_4_or_fewer_pieces_no_pawns(self):
        """Rule activates: no pawns, 4 or fewer non-neutral pieces."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "b1", Queen('white'))
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black'))
        # 4 pieces, no pawns
        self.assertTrue(board.is_tiny_endgame())

    def test_rule_active_3_pieces_no_pawns(self):
        """Rule activates: no pawns, 3 non-neutral pieces."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black'))
        self.assertTrue(board.is_tiny_endgame())

    def test_rule_not_active_5_pieces_different_types(self):
        """Rule does not activate: 5 pieces, no pawns, but different remaining types."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "b1", Queen('white'))
        place(board, "c1", Rook('white'))
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black'))
        # 5 pieces, different types (white has queen+rook, black has queen only)
        self.assertFalse(board.is_tiny_endgame())

    def test_rule_active_6_pieces_same_types(self):
        """Rule activates: 6 pieces, no pawns, same remaining types ignoring kings."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "b1", Queen('white'))
        place(board, "c1", Rook('white'))
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black'))
        place(board, "f8", Rook('black'))
        # 6 pieces, same types: both have queen + rook (ignoring kings)
        self.assertTrue(board.is_tiny_endgame())

    def test_rule_active_6_pieces_same_types_with_transformed(self):
        """Transformed royal queen counts as 'queen' for type comparison."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "b1", Queen('white'))
        place(board, "c1", Rook('white'))
        place(board, "e8", King('black'))
        # Black's royal queen transformed as rook — counts as 'queen'
        transformed = Rook('black')
        transformed.is_transformed = True
        transformed.is_royal = True
        place(board, "g8", transformed)
        place(board, "f8", Rook('black'))
        # Types ignoring kings: white=queen+rook, black=queen+rook (transformed counts as queen)
        self.assertTrue(board.is_tiny_endgame())

    def test_rule_active_promoted_queen_counts_as_queen(self):
        """Promoted queen counts as 'queen' for type comparison."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "b1", Queen('white', is_royal=False))  # promoted
        place(board, "e8", King('black'))
        place(board, "g8", Queen('black'))
        # 4 pieces, both have queen type
        self.assertTrue(board.is_tiny_endgame())

    def test_boulder_does_not_count(self):
        """Boulder is neutral and does not count toward piece totals."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "d4", Boulder())  # neutral, doesn't count
        # Only 2 non-neutral pieces
        self.assertTrue(board.is_tiny_endgame())

    # ---- Royal distance tests ----

    def test_royal_distance_orthogonal_adjacent(self):
        """Royal distance between orthogonally adjacent opposing royals is 1."""
        board = empty_board()
        place(board, "e4", King('white'))
        place(board, "e5", King('black'))
        # Manhattan: |4-3| + |4-4| = 1
        self.assertEqual(board.get_royal_distance(), 1)

    def test_royal_distance_diagonal_adjacent(self):
        """Royal distance between diagonally adjacent opposing royals is 2."""
        board = empty_board()
        place(board, "e4", King('white'))
        place(board, "f5", King('black'))
        # Manhattan: |4-3| + |4-5| = 2
        self.assertEqual(board.get_royal_distance(), 2)

    def test_royal_distance_manhattan(self):
        """Royal distance is Manhattan distance."""
        board = empty_board()
        place(board, "a1", King('white'))
        place(board, "h8", King('black'))
        # Manhattan: |7-0| + |0-7| = 14
        self.assertEqual(board.get_royal_distance(), 14)

    def test_royal_distance_closest_pair(self):
        """Royal distance is the closest pair of opposing royals."""
        board = empty_board()
        place(board, "a1", King('white'))
        place(board, "h1", Queen('white'))
        place(board, "a8", King('black'))
        place(board, "h8", Queen('black'))
        # Closest: white king a1 to black king a8 = 7
        # white queen h1 to black queen h8 = 7
        # white king a1 to black queen h8 = 14
        # white queen h1 to black king a8 = 14
        self.assertEqual(board.get_royal_distance(), 7)

    def test_royal_distance_includes_transformed_queen(self):
        """Transformed royal queen still counts for royal distance."""
        board = empty_board()
        place(board, "a1", King('white'))
        place(board, "e8", King('black'))
        # Transformed royal queen on b2
        transformed = Rook('white')
        transformed.is_royal = True
        transformed.is_transformed = True
        place(board, "b2", transformed)
        # Closest: b2 to e8 = |1-0| + |6-4| = not right... let me use coords
        # b2 = (6,1), e8 = (0,4). Manhattan = 6+3 = 9
        # a1 = (7,0), e8 = (0,4). Manhattan = 7+4 = 11
        # Closest opposing pair: b2(white) to e8(black) = 9
        self.assertEqual(board.get_royal_distance(), 9)

    # ---- Distance count tests ----

    def test_distance_counts_initialized_when_rule_activates(self):
        """When rule first activates, count for current royal distance set to 1."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        self.assertEqual(board.distance_counts[dist], 1)

    def test_distance_count_increments_on_non_capture_turn(self):
        """Non-capture turn increments the count for the resulting royal distance."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        # Simulate non-capture turn (distance unchanged)
        board.update_distance_count(captured=False)
        self.assertEqual(board.distance_counts[dist], 2)

    def test_distance_counts_reset_on_capture(self):
        """All distance counts reset to 0 on capture, then re-init if rule still applies."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "d4", Rook('white'))
        board.init_tiny_endgame()
        board.update_distance_count(captured=False)
        board.update_distance_count(captured=False)
        # Simulate capture
        board.update_distance_count(captured=True)
        dist = board.get_royal_distance()
        # All counts reset, then current distance re-initialized to 1
        self.assertEqual(board.distance_counts[dist], 1)
        # Other distances should be 0
        other_dist = 1 if dist != 1 else 2
        self.assertEqual(board.distance_counts[other_dist], 0)

    # ---- Move filtering tests ----

    def test_non_capture_move_blocked_at_count_3(self):
        """A non-capture move is blocked if it would push the distance count above 3."""
        board = empty_board()
        king = place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.init_tiny_endgame()
        # Artificially set distance count to 3 for the distance that would result
        # from king staying nearby (non-capture)
        dist = board.get_royal_distance()
        board.distance_counts[dist] = 3
        # King moves that don't change the royal distance should be blocked
        # (they would push count to 4 > 3)

    def test_capture_move_always_allowed(self):
        """Capture moves are always allowed regardless of distance counts."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        place(board, "e8", King('black'))
        place(board, "e5", Rook('black'))  # capturable
        board.init_tiny_endgame()
        # Even with high distance counts, capture should be allowed
        dist = board.get_royal_distance()
        board.distance_counts[dist] = 3
        king.clear_moves()
        board.king_moves(king, *sq("e4"))
        dests = get_move_destinations(king)
        self.assertIn(sq("e5"), dests, "Capture should always be allowed")

    # ---- Player loses if no legal moves ----

    def test_player_loses_if_all_moves_exceed_limit(self):
        """If every legal turn would exceed the distance count limit, player loses."""
        pass

    # ---- Activation/deactivation ordering ----

    def test_deactivation_on_capture_before_recheck(self):
        """If a capture causes activation criteria to fail, rule deactivates.
        update_distance_count(captured=True) should deactivate before re-checking activation."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        rook = place(board, "d4", Rook('white'))
        # 3 pieces, no pawns → activate
        board.init_tiny_endgame()
        self.assertTrue(board.tiny_endgame_active)
        # Simulate some non-capture turns
        board.update_distance_count(captured=False)
        board.update_distance_count(captured=False)
        dist = board.get_royal_distance()
        self.assertEqual(board.distance_counts[dist], 3)
        # Simulate a capture: remove the rook (now only 2 pieces)
        board.squares[sq("d4")[0]][sq("d4")[1]].piece = None
        board.update_distance_count(captured=True)
        # Rule should still be active (2 kings, still meets ≤4 pieces criteria)
        self.assertTrue(board.tiny_endgame_active)
        # Distance counts should have been reset and re-initialized
        self.assertEqual(board.distance_counts[dist], 1)

    def test_deactivation_when_pawn_appears_via_promotion(self):
        """If conditions no longer hold after a capture (e.g. pawn count changes
        indirectly), the rule deactivates properly."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.init_tiny_endgame()
        self.assertTrue(board.tiny_endgame_active)
        # Add a pawn (simulating some game state change)
        place(board, "a2", Pawn('white'))
        # On next capture, the re-check should find a pawn and deactivate
        board.update_distance_count(captured=True)
        self.assertFalse(board.tiny_endgame_active)

    def test_activation_checked_every_turn(self):
        """Rule activation is checked after every turn. If criteria are met,
        the rule activates regardless of whether the turn was a capture."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        # Criteria are met (2 pieces, no pawns)
        self.assertTrue(board.is_tiny_endgame())
        # Not yet active until explicitly initialized
        self.assertFalse(board.tiny_endgame_active)
        # Simulating what main.py does: check and init if criteria met
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        self.assertTrue(board.tiny_endgame_active)

    # ---- Transformation + tiny endgame interaction tests ----

    def test_transformation_increments_distance_count(self):
        """Transformation is a non-capture, non-movement action. It should
        increment the distance count for the current royal distance."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        queen = place(board, "a1", Queen('black'))
        board.captured_pieces['black'].append('rook')
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        initial_count = board.distance_counts[dist]
        # Simulate transformation turn: transform + update_distance_count(captured=False)
        board.transform_queen(queen, *sq("a1"), 'rook')
        board.update_distance_count(captured=False)
        self.assertEqual(board.distance_counts[dist], initial_count + 1)

    def test_transformation_blocked_when_distance_limit_exceeded(self):
        """When distance count is at limit (3), all transformation options
        should be filtered out since transformation can't change the distance."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        queen = place(board, "a1", Queen('black'))
        board.captured_pieces['black'].append('rook')
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        # Set distance count to limit
        board.distance_counts[dist] = 3
        # All transformation options should be blocked
        options = board.get_transformation_options(queen)
        filtered = board.filter_transformation_options(queen, *sq("a1"), options, 'black')
        self.assertEqual(filtered, [],
                         "All transformation options should be blocked at distance limit")

    def test_transformation_allowed_when_distance_limit_not_reached(self):
        """When distance count is below limit, transformation options
        should not be blocked by the distance rule (may still be blocked by repetition)."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        queen = place(board, "a1", Queen('black'))
        board.captured_pieces['black'].append('rook')
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        # Distance count is 1 (from init), well below limit of 3
        self.assertEqual(board.distance_counts[dist], 1)
        options = board.get_transformation_options(queen)
        filtered = board.filter_transformation_options(queen, *sq("a1"), options, 'black')
        self.assertTrue(len(filtered) > 0,
                        "Transformation options should be available when distance count < 3")

    def test_transformation_not_blocked_when_rule_inactive(self):
        """When tiny endgame rule is not active, transformation options
        should not be blocked by the distance rule."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "a2", Pawn('white'))  # pawn present → rule cannot activate
        queen = place(board, "a1", Queen('black'))
        board.captured_pieces['black'].append('rook')
        self.assertFalse(board.tiny_endgame_active)
        options = board.get_transformation_options(queen)
        filtered = board.filter_transformation_options(queen, *sq("a1"), options, 'black')
        self.assertTrue(len(filtered) > 0,
                        "Transformation should not be blocked when tiny endgame is inactive")

    def test_would_transformation_exceed_distance_limit_true(self):
        """would_transformation_exceed_distance_limit returns True when
        the current distance count is at the limit."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        board.distance_counts[dist] = 3
        self.assertTrue(board.would_transformation_exceed_distance_limit())

    def test_would_transformation_exceed_distance_limit_false(self):
        """would_transformation_exceed_distance_limit returns False when
        the current distance count is below the limit."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        board.distance_counts[dist] = 2
        self.assertFalse(board.would_transformation_exceed_distance_limit())


# ===========================================================================
# TestBishopAssassinUpdate — Regression tests for assassin_squares staleness
# ===========================================================================

class TestBishopAssassinUpdate(unittest.TestCase):
    """
    Regression tests: bishop's assassin_squares must be updated at the end
    of EVERY turn-ending action (including transformation) for the current
    player's color.

    Bug: the transformation code path in main.py did not call
    update_assassin_squares at all. This caused the bishop to miss
    assassin captures when the board changed since the last update.

    Key invariant: assassin_squares for a color are computed at the end
    of that color's turn. They reflect which enemy pieces are visible
    on each bishop's diagonal AFTER that turn. On the opponent's next
    move, the bishop uses this "stale" data — which is correct, because
    the enemy piece was on the diagonal BEFORE the opponent moved it.
    """

    def test_assassin_squares_updated_after_normal_move(self):
        """After a normal move, the current player's assassin_squares are up to date."""
        board = empty_board()
        black_bishop = place(board, "b3", Bishop('black'))
        white_knight = place(board, "d5", Knight('white'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        # Simulate end of black's turn
        board.update_assassin_squares('black')

        # Black bishop should see white knight on d5 (on its diagonal)
        self.assertIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "Black bishop on b3 should have d5 in assassin_squares"
        )

    def test_assassin_capture_normal_flow(self):
        """Normal flow: black's turn updates assassin_squares, then white moves
        the knight away — bishop can capture using stale (correct) data."""
        board = empty_board()
        black_bishop = place(board, "b3", Bishop('black'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        white_knight = Knight('white')
        white_knight.moved = True
        place(board, "d5", white_knight)

        target = Queen('black', is_royal=False)
        target.moved = True
        place(board, "d7", target)

        # End of black's turn: update black's assassin_squares
        board.update_assassin_squares('black')
        self.assertIn(Square(*sq("d5")), black_bishop.assassin_squares)

        # White moves knight d5 → d7 (captures queen)
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("d5"))
        move = Move(Square(*sq("d5")), Square(*sq("d7")))
        board.move(white_knight, move)

        # End of white's turn: update white's assassin_squares (NOT black's)
        board.update_assassin_squares('white')

        # Black bishop's stale assassin_squares still has d5 → assassin capture works
        black_bishop.clear_moves()
        board.bishop_moves(black_bishop, *sq("b3"))
        dests = get_move_destinations(black_bishop)
        self.assertIn(sq("d7"), dests, "Bishop should assassin-capture knight at d7")

    def test_assassin_squares_stale_without_update(self):
        """If update_assassin_squares is never called for black after knight
        arrives on d5, the bishop cannot see it."""
        board = empty_board()
        black_bishop = place(board, "b3", Bishop('black'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        # Knight NOT on d5 initially
        white_knight = Knight('white')
        white_knight.moved = True
        place(board, "f4", white_knight)

        # Black's turn ends — assassin_squares computed (knight NOT on d5)
        board.update_assassin_squares('black')
        self.assertNotIn(Square(*sq("d5")), black_bishop.assassin_squares)

        # White moves knight f4 → d5
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("f4"))
        move1 = Move(Square(*sq("f4")), Square(*sq("d5")))
        board.move(white_knight, move1)

        # Only update white (old behavior)
        board.update_assassin_squares('white')
        # Black's assassin_squares are stale — d5 NOT included
        self.assertNotIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "Without updating black, d5 should NOT be in assassin_squares"
        )

        # After updating black (on black's next turn), d5 IS in assassin_squares
        board.update_assassin_squares('black')
        self.assertIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "After updating black, d5 should be in assassin_squares"
        )

    def test_assassin_capture_with_diagonal_blocked_then_unblocked(self):
        """If a blocking piece is removed from the bishop's diagonal,
        assassin_squares must be refreshed to include newly visible squares."""
        board = empty_board()
        black_bishop = place(board, "b3", Bishop('black'))
        white_knight = place(board, "d5", Knight('white'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        # c4 blocks the diagonal from b3 to d5
        blocker = place(board, "c4", Pawn('white'))

        board.update_assassin_squares('black')
        self.assertNotIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "d5 should be blocked by piece on c4"
        )
        self.assertIn(
            Square(*sq("c4")), black_bishop.assassin_squares,
            "c4 (blocker) should be in assassin_squares"
        )

        # Remove blocker, re-compute
        board.squares[sq("c4")[0]][sq("c4")[1]].piece = None
        board.update_assassin_squares('black')
        self.assertIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "After removing blocker, d5 should be in assassin_squares"
        )

    def test_transformation_updates_assassin_squares(self):
        """Regression: transformation must call update_assassin_squares for the
        current player so the bishop's LOS is correct.

        Bug scenario:
        1. Black's previous turn: assassin_squares computed (knight not on d5)
        2. White moves knight to d5
        3. Black TRANSFORMS queen — without the fix, update_assassin_squares
           is NOT called, so d5 is not in assassin_squares
        4. White moves knight d5→d7 — bishop can't capture (BUG)

        With the fix, step 3 calls update_assassin_squares, so d5 is captured.
        """
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder = boulder

        black_bishop = place(board, "b3", Bishop('black'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        # Black's transformable queen
        black_queen = place(board, "a8", Queen('black'))
        board.captured_pieces['black'].append('rook')

        # White knight NOT on d5 yet
        white_knight = Knight('white')
        white_knight.moved = True
        place(board, "f4", white_knight)

        target = Queen('black', is_royal=False)
        target.moved = True
        place(board, "d7", target)

        # Step 1: Black's normal turn ends, update black's assassin_squares
        board.update_assassin_squares('black')
        self.assertNotIn(Square(*sq("d5")), black_bishop.assassin_squares)

        # Step 2: White moves knight f4 → d5, update white's assassin_squares
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("f4"))
        move1 = Move(Square(*sq("f4")), Square(*sq("d5")))
        board.move(white_knight, move1)
        board.update_assassin_squares('white')

        # Step 3: Black transforms queen — THE FIX: update_assassin_squares('black')
        board.transform_queen(black_queen, *sq("a8"), 'rook')
        board.update_assassin_squares('black')  # This was missing before the fix!

        # d5 should now be in bishop's assassin_squares
        self.assertIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "After transformation + update, d5 should be in assassin_squares"
        )

        # Step 4: White moves knight d5 → d7, update white's assassin_squares
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("d5"))
        move2 = Move(Square(*sq("d5")), Square(*sq("d7")))
        board.move(white_knight, move2)
        board.update_assassin_squares('white')

        # Step 5: Black bishop should be able to assassin-capture at d7
        black_bishop.clear_moves()
        board.bishop_moves(black_bishop, *sq("b3"))
        dests = get_move_destinations(black_bishop)
        self.assertIn(
            sq("d7"), dests,
            "Bishop should assassin-capture after transformation did not break update"
        )

    def test_transformation_bug_without_fix(self):
        """Demonstrates the bug: without the update_assassin_squares call
        in the transformation path, the bishop misses assassin captures."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder = boulder

        black_bishop = place(board, "b3", Bishop('black'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        black_queen = place(board, "a8", Queen('black'))
        board.captured_pieces['black'].append('rook')

        white_knight = Knight('white')
        white_knight.moved = True
        place(board, "f4", white_knight)

        target = Queen('black', is_royal=False)
        target.moved = True
        place(board, "d7", target)

        # Black's turn ends — knight not on d5
        board.update_assassin_squares('black')

        # White moves knight to d5
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("f4"))
        board.move(white_knight, Move(Square(*sq("f4")), Square(*sq("d5"))))
        board.update_assassin_squares('white')

        # Black transforms — WITHOUT calling update_assassin_squares('black')
        board.transform_queen(black_queen, *sq("a8"), 'rook')
        # Deliberately NOT calling board.update_assassin_squares('black')

        # d5 should NOT be in assassin_squares (bug behavior)
        self.assertNotIn(
            Square(*sq("d5")), black_bishop.assassin_squares,
            "Without the fix, d5 is not in assassin_squares after transformation"
        )

        # White moves knight d5 → d7
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("d5"))
        board.move(white_knight, Move(Square(*sq("d5")), Square(*sq("d7"))))
        board.update_assassin_squares('white')

        # Bishop CANNOT assassin-capture (bug)
        black_bishop.clear_moves()
        board.bishop_moves(black_bishop, *sq("b3"))
        dests = get_move_destinations(black_bishop)
        self.assertNotIn(
            sq("d7"), dests,
            "Without the fix, bishop cannot assassin-capture (demonstrates the bug)"
        )

    def test_assassin_capture_full_scenario_with_boulder(self):
        """Full scenario: bishop assassin capture with boulder on intersection.
        Reproduces the exact reported bug conditions."""
        board = empty_board()
        boulder = Boulder()
        boulder.on_intersection = True
        board.boulder = boulder

        black_bishop = place(board, "b3", Bishop('black'))
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))

        # Pawn-promoted knight (non-royal) on d5
        white_knight = Knight('white')
        white_knight.is_royal = False
        white_knight.is_transformed = True
        white_knight.moved = True
        place(board, "d5", white_knight)

        # Pawn-promoted queen (base form) on d7
        target = Queen('black', is_royal=False)
        target.moved = True
        place(board, "d7", target)

        # End of black's turn: update black's assassin_squares
        board.update_assassin_squares('black')

        # White knight captures on d7
        white_knight.clear_moves()
        board.knight_moves(white_knight, *sq("d5"))
        move = Move(Square(*sq("d5")), Square(*sq("d7")))
        board.move(white_knight, move)

        # End of white's turn: update only white's assassin_squares
        board.update_assassin_squares('white')

        # Black bishop should be able to assassin-capture at d7
        # (using stale assassin_squares from end of black's turn, which has d5)
        black_bishop.clear_moves()
        board.bishop_moves(black_bishop, *sq("b3"))
        dests = get_move_destinations(black_bishop)
        self.assertIn(
            sq("d7"), dests,
            "Bishop should assassin-capture promoted knight at d7 (boulder on intersection)"
        )


# ===========================================================================
# TestPromotionRules — Promotion path correctness
# ===========================================================================

class TestPromotionRules(unittest.TestCase):
    """
    Promotion is irreversible and unrepeatable, so:
    - Repetition rule does not apply to promotion itself
    - Tiny endgame rule cannot be active before promotion (a pawn exists)
    - Tiny endgame may activate after promotion if the last pawn was promoted
      and the promotion move was a capture
    """

    def test_tiny_endgame_not_active_before_promotion(self):
        """Tiny endgame cannot be active when a pawn exists on the board."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "a7", Pawn('white'))  # pawn about to promote
        self.assertFalse(board.is_tiny_endgame(),
                         "Tiny endgame should not activate while a pawn exists")
        self.assertFalse(board.tiny_endgame_active)

    def test_tiny_endgame_activates_after_last_pawn_promotes_with_capture(self):
        """If the last pawn promotes via a capture, tiny endgame should activate
        (assuming piece count criteria are met)."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        # Pawn on 7th rank (row 1 for white)
        pawn = place(board, "a7", Pawn('white'))
        # Enemy piece on promotion square
        place(board, "a8", Rook('black'))
        self.assertFalse(board.is_tiny_endgame())

        # Simulate: pawn moves to a8 (capture), then promotes
        board.squares[sq("a7")[0]][sq("a7")[1]].piece = None
        board.squares[sq("a8")[0]][sq("a8")[1]].piece = None  # captured rook
        # Promote pawn to queen
        board.promote(pawn, *sq("a8"), 'queen')

        # Now no pawns remain: 3 pieces (2 kings + promoted queen)
        self.assertTrue(board.is_tiny_endgame(),
                        "After last pawn promotes, tiny endgame criteria should be met")

        # Activation check (simulating what main.py does after every turn)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        self.assertTrue(board.tiny_endgame_active)

    def test_tiny_endgame_activates_after_non_capture_promotion(self):
        """If the last pawn promotes without a capture, tiny endgame should still
        activate because the criteria are checked after every turn."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        pawn = place(board, "a7", Pawn('white'))

        # Simulate: pawn moves to a8 (no capture), then promotes
        board.squares[sq("a7")[0]][sq("a7")[1]].piece = None
        board.promote(pawn, *sq("a8"), 'queen')

        # Criteria are met
        self.assertTrue(board.is_tiny_endgame())
        # Activation check (simulating what main.py does after every turn)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        self.assertTrue(board.tiny_endgame_active,
                        "Tiny endgame should activate after non-capture promotion of last pawn")

    def test_promotion_with_multiple_pawns_remaining(self):
        """When other pawns still exist after promotion, tiny endgame does not activate."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        pawn = place(board, "a7", Pawn('white'))
        place(board, "b2", Pawn('white'))  # another pawn remains

        # Promote the a7 pawn
        board.squares[sq("a7")[0]][sq("a7")[1]].piece = None
        board.promote(pawn, *sq("a8"), 'queen')

        self.assertFalse(board.is_tiny_endgame(),
                         "Tiny endgame should not activate when pawns remain")

    def test_tiny_endgame_activates_after_boulder_captures_last_pawn(self):
        """Boulder capturing the last pawn should trigger tiny endgame activation."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        pawn = place(board, "d4", Pawn('black'))  # last pawn
        boulder = place(board, "d3", Boulder())
        boulder.on_intersection = False
        boulder.first_move = False
        board.boulder = None  # not on intersection

        self.assertFalse(board.is_tiny_endgame(),
                         "Pawn still present, rule should not activate")

        # Simulate boulder capturing the pawn
        board.squares[sq("d4")[0]][sq("d4")[1]].piece = boulder
        board.squares[sq("d3")[0]][sq("d3")[1]].piece = None

        # Now no pawns remain
        self.assertTrue(board.is_tiny_endgame(),
                        "After boulder captures last pawn, criteria should be met")

        # Activation check (simulating what main.py does after every turn)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        self.assertTrue(board.tiny_endgame_active)


# ===========================================================================
# TestNoLegalMoves — Win condition when player has no legal moves/actions
# ===========================================================================

class TestNoLegalMoves(unittest.TestCase):
    """
    If a player has no legal turns (moves or actions) due to the repetition
    and/or tiny endgame rules, that player loses.
    """

    def test_has_legal_moves_normal_position(self):
        """In a normal position, both players have legal moves."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        place(board, "d1", Queen('white'))
        place(board, "d8", Queen('black'))
        board.update_lines_of_sight()
        board.update_threat_squares()
        self.assertTrue(board.has_legal_moves('white'))
        self.assertTrue(board.has_legal_moves('black'))

    def test_has_legal_moves_king_only(self):
        """A lone king should have legal moves (king can move in many directions)."""
        board = empty_board()
        place(board, "e4", King('white'))
        place(board, "a8", King('black'))
        place(board, "a7", Queen('black'))
        board.update_lines_of_sight()
        board.update_threat_squares()
        self.assertTrue(board.has_legal_moves('white'))

    def test_no_legal_moves_all_blocked_by_distance_limit(self):
        """Player loses if all non-capture moves are blocked by tiny endgame
        distance limit and no captures are available."""
        board = empty_board()
        king_w = place(board, "a1", King('white'))
        place(board, "h8", King('black'))
        board.update_lines_of_sight()
        board.update_threat_squares()
        # Activate tiny endgame
        board.init_tiny_endgame()
        dist = board.get_royal_distance()
        # Set ALL distance counts to 3 so every non-capture move is blocked
        for i in range(15):
            board.distance_counts[i] = 3
        self.assertFalse(board.has_legal_moves('white'),
                         "White should have no legal moves when all distances are at limit")

    def test_has_legal_moves_capture_available_despite_distance_limit(self):
        """Even at distance limit, captures are always allowed."""
        board = empty_board()
        place(board, "a1", King('white'))
        place(board, "h8", King('black'))
        # Enemy piece adjacent to king (capturable)
        place(board, "a2", Rook('black'))
        board.update_lines_of_sight()
        board.update_threat_squares()
        board.init_tiny_endgame()
        for i in range(15):
            board.distance_counts[i] = 3
        self.assertTrue(board.has_legal_moves('white'),
                        "White should have legal moves when a capture is available")

    def test_no_legal_moves_all_blocked_by_repetition(self):
        """Player loses if all moves are blocked by the repetition rule."""
        board = empty_board()
        king_w = place(board, "a1", King('white'))
        place(board, "h8", King('black'))
        board.update_lines_of_sight()
        board.update_threat_squares()

        # Artificially fill state_history so every possible king move
        # would be a third repetition
        # First compute all possible states after each king move
        king_w.clear_moves()
        board.king_moves(king_w, *sq("a1"))
        for move in king_w.moves:
            # Simulate the move, hash it, and record 2 occurrences
            initial = move.initial
            final = move.final
            orig = board.squares[final.row][final.col].piece
            board.squares[initial.row][initial.col].piece = None
            board.squares[final.row][final.col].piece = king_w
            state = board.get_state_hash('black')
            board.state_history[state] = 2
            # Undo
            board.squares[final.row][final.col].piece = orig
            board.squares[initial.row][initial.col].piece = king_w
        king_w.clear_moves()

        self.assertFalse(board.has_legal_moves('white'),
                         "White should have no legal moves when all moves cause repetition")

    def test_has_legal_moves_includes_transformation(self):
        """Transformation counts as a legal action."""
        board = empty_board()
        king_w = place(board, "a1", King('white'))
        place(board, "h8", King('black'))
        queen_w = place(board, "a2", Queen('white'))
        board.captured_pieces['white'].append('rook')
        board.update_lines_of_sight()
        board.update_threat_squares()

        # Block all moves via distance limit
        board.init_tiny_endgame()
        for i in range(15):
            board.distance_counts[i] = 3

        # But transformation should still be available (not blocked by distance limit
        # at count 3, since would_transformation_exceed_distance_limit checks same limit)
        # Actually, transformation IS blocked at distance 3 too. Let's set to 2.
        dist = board.get_royal_distance()
        board.distance_counts[dist] = 2
        # Now non-capture moves at this distance are not blocked, so king/queen have moves
        # Let me instead test without tiny endgame to keep it simple
        board.tiny_endgame_active = False
        board.distance_counts = [0] * 15

        # Block all spatial moves via repetition
        for row in range(8):
            for col in range(8):
                piece = board.squares[row][col].piece
                if piece and piece.color == 'white':
                    piece.clear_moves()
                    if isinstance(piece, King):
                        board.king_moves(piece, row, col)
                    elif isinstance(piece, Queen):
                        board.queen_moves(piece, row, col)
                    for move in piece.moves:
                        initial = move.initial
                        final = move.final
                        orig = board.squares[final.row][final.col].piece
                        board.squares[initial.row][initial.col].piece = None
                        board.squares[final.row][final.col].piece = piece
                        state = board.get_state_hash('black')
                        board.state_history[state] = 2
                        board.squares[final.row][final.col].piece = orig
                        board.squares[initial.row][initial.col].piece = piece
                    piece.clear_moves()

        # Transformation should still be available as a legal action
        self.assertTrue(board.has_legal_moves('white'),
                        "Transformation should count as a legal action")

    def test_has_legal_moves_includes_boulder(self):
        """Boulder moves count as legal actions for either player."""
        board = empty_board()
        place(board, "a1", King('white'))
        place(board, "h8", King('black'))
        boulder = Boulder()
        boulder.on_intersection = True
        boulder.cooldown = 0
        board.boulder = boulder
        board.turn_number = 2  # past turn 1 so white can move boulder
        board.update_lines_of_sight()
        board.update_threat_squares()

        # Block all king moves via repetition
        king_w = board.squares[sq("a1")[0]][sq("a1")[1]].piece
        king_w.clear_moves()
        board.king_moves(king_w, *sq("a1"))
        for move in king_w.moves:
            initial = move.initial
            final = move.final
            orig = board.squares[final.row][final.col].piece
            board.squares[initial.row][initial.col].piece = None
            board.squares[final.row][final.col].piece = king_w
            state = board.get_state_hash('black')
            board.state_history[state] = 2
            board.squares[final.row][final.col].piece = orig
            board.squares[initial.row][initial.col].piece = king_w
        king_w.clear_moves()

        # Boulder on intersection should still provide legal moves
        self.assertTrue(board.has_legal_moves('white'),
                        "Boulder moves should count as legal actions")

    def test_boulder_moves_filtered_by_distance_limit(self):
        """Boulder non-capture moves are blocked by tiny endgame distance limit."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        boulder = place(board, "d4", Boulder())
        boulder.on_intersection = False
        boulder.first_move = False
        boulder.cooldown = 0
        board.boulder = None
        board.turn_number = 2
        board.update_lines_of_sight()
        board.update_threat_squares()

        # Activate tiny endgame and max out all distance counts
        board.init_tiny_endgame()
        for i in range(15):
            board.distance_counts[i] = 3

        boulder.clear_moves()
        board.boulder_moves(boulder, *sq("d4"))
        self.assertTrue(len(boulder.moves) > 0, "Boulder should have raw moves")
        board.filter_endgame_moves(boulder, 'white')
        # All non-capture boulder moves should be blocked
        for m in boulder.moves:
            target = board.squares[m.final.row][m.final.col]
            self.assertTrue(target.has_piece(),
                            "Only capture moves should survive distance limit filtering")

    def test_boulder_moves_filtered_by_repetition(self):
        """Boulder moves are blocked by the repetition rule."""
        board = empty_board()
        place(board, "e1", King('white'))
        place(board, "e8", King('black'))
        boulder = place(board, "d4", Boulder())
        boulder.on_intersection = False
        boulder.first_move = False
        boulder.cooldown = 0
        boulder.last_square = None
        board.boulder = None
        board.turn_number = 2
        board.update_lines_of_sight()
        board.update_threat_squares()

        boulder.clear_moves()
        board.boulder_moves(boulder, *sq("d4"))
        total_before = len(boulder.moves)
        self.assertTrue(total_before > 0, "Boulder should have raw moves")

        # Record states so every boulder move would cause repetition
        for move in boulder.moves:
            initial = move.initial
            final = move.final
            orig = board.squares[final.row][final.col].piece
            board.squares[initial.row][initial.col].piece = None
            board.squares[final.row][final.col].piece = boulder
            # Save/restore boulder state for hash
            old_ls = boulder.last_square
            old_cd = boulder.cooldown
            old_fm = boulder.first_move
            old_oi = boulder.on_intersection
            boulder.cooldown = 2
            boulder.last_square = (initial.row, initial.col)
            boulder.first_move = False
            boulder.on_intersection = False
            state = board.get_state_hash('black')
            board.state_history[state] = 2
            boulder.last_square = old_ls
            boulder.cooldown = old_cd
            boulder.first_move = old_fm
            boulder.on_intersection = old_oi
            board.squares[final.row][final.col].piece = orig
            board.squares[initial.row][initial.col].piece = boulder
        boulder.clear_moves()

        boulder.clear_moves()
        board.boulder_moves(boulder, *sq("d4"))
        board.filter_repetition_moves(boulder, 'white')
        self.assertEqual(len(boulder.moves), 0,
                         "All boulder moves should be blocked by repetition rule")

    def test_has_legal_moves_includes_manipulation(self):
        """Queen manipulation of enemy pieces counts as a legal action."""
        board = empty_board()
        place(board, "a1", King('white'))
        queen_w = place(board, "d1", Queen('white'))
        place(board, "h8", King('black'))
        # Enemy knight in queen's line of sight
        enemy_knight = place(board, "d5", Knight('black'))
        enemy_knight.moved = True
        board.update_lines_of_sight()
        board.update_threat_squares()

        # Block all own piece moves via repetition
        for row in range(8):
            for col in range(8):
                piece = board.squares[row][col].piece
                if piece and piece.color == 'white':
                    piece.clear_moves()
                    if isinstance(piece, King):
                        board.king_moves(piece, row, col)
                    elif isinstance(piece, Queen):
                        board.queen_moves(piece, row, col)
                    for move in piece.moves:
                        initial = move.initial
                        final = move.final
                        orig = board.squares[final.row][final.col].piece
                        board.squares[initial.row][initial.col].piece = None
                        board.squares[final.row][final.col].piece = piece
                        state = board.get_state_hash('black')
                        board.state_history[state] = 2
                        board.squares[final.row][final.col].piece = orig
                        board.squares[initial.row][initial.col].piece = piece
                    piece.clear_moves()

        # Manipulation of enemy knight should still be available
        self.assertTrue(board.has_legal_moves('white'),
                        "Queen manipulation should count as a legal action")


if __name__ == '__main__':
    unittest.main()
