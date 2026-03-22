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
from piece import Pawn, Knight, Bishop, Rook, Queen, King
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

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_king_captures_boulder(self):
        """King on e4 can capture the boulder on e5."""
        board = empty_board()
        king = place(board, "e4", King('white'))
        # boulder = place(board, "e5", Boulder())
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
# TestRoyalQueen
# ===========================================================================

class TestRoyalQueen(unittest.TestCase):
    """
    Rulebook — Royal Queen (base form):
      Movement: one square in any direction (like a king).
      Capture: any adjacent enemy piece (except the boulder).
      Action: Manipulation.
    """

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

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_queen_cannot_capture_boulder(self):
        """Royal queen on e4 cannot capture the boulder on e5."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        # boulder = place(board, "e5", Boulder())
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

    # ---- Manipulation tests ----

    @unittest.skip("Not yet implemented: manipulation restriction — cannot manipulate enemy king")
    def test_manipulation_cannot_target_enemy_king(self):
        """Queen on e4 cannot manipulate the enemy king on g4."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        enemy_king = place(board, "g4", King('black'))
        board.update_threat_squares()
        board.queen_moves_enemy(enemy_king, *sq("g4"))
        dests = get_move_destinations(enemy_king)
        self.assertEqual(len(dests), 0)

    @unittest.skip("Not yet implemented: manipulation restriction — cannot manipulate base-form royal queen")
    def test_manipulation_cannot_target_base_form_royal_queen(self):
        """Queen on e4 cannot manipulate the enemy's base-form royal queen on g4."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        enemy_queen = place(board, "g4", Queen('black'))
        board.update_threat_squares()
        board.queen_moves_enemy(enemy_queen, *sq("g4"))
        dests = get_move_destinations(enemy_queen)
        self.assertEqual(len(dests), 0)

    @unittest.skip("Not yet implemented: manipulation restriction — cannot manipulate piece that moved last turn")
    def test_manipulation_cannot_target_piece_that_moved_last_turn(self):
        """Queen on e4 cannot manipulate a rook on g4 that moved there last turn."""
        board = empty_board()
        queen = place(board, "e4", Queen('white'))
        enemy_rook = place(board, "g4", Rook('black'))
        board.last_move = Move(Square(*sq("h4")), Square(*sq("g4")))
        board.update_threat_squares()
        board.queen_moves_enemy(enemy_rook, *sq("g4"))
        dests = get_move_destinations(enemy_rook)
        self.assertEqual(len(dests), 0)

    @unittest.skip("Not yet implemented: manipulation when transformed")
    def test_queen_cannot_manipulate_when_transformed(self):
        """Queen cannot use manipulation action when in transformed form."""
        pass

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

    @unittest.skip("Not yet implemented: jump capture in move generation (handled in board.move())")
    def test_knight_jump_capture_adjacent_enemy(self):
        """Knight on e4 lands on e6 (empty) + jumped over e5 → may capture adjacent enemy."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # piece on jumped square
        place(board, "d6", Rook('black'))  # adjacent to landing e6
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("e6"), dests)

    def test_jumped_square_orthogonal(self):
        """Knight on e4 moving to e6: jumped square is e5."""
        board = empty_board()
        knight = place(board, "e4", Knight('white'))
        place(board, "e5", Pawn('black'))  # on jumped square
        board.knight_moves(knight, *sq("e4"))
        dests = get_move_destinations(knight)
        self.assertIn(sq("e6"), dests)


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

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_first_move_central_squares_only(self):
        """Boulder's first move must go to one of d4, e4, d5, e5."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_later_moves_like_king(self):
        """After first move, boulder moves like a king (1 square any direction)."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_captures_pawns_only(self):
        """Boulder can capture pawns but not other pieces."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_cannot_capture_non_pawn(self):
        """Boulder cannot capture knights, bishops, rooks, queens, or kings."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_only_king_captures_boulder(self):
        """Only the king may capture the boulder; other pieces cannot."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_cooldown(self):
        """After boulder moves, both players must take a turn before it moves again."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_memory(self):
        """Boulder cannot return to its immediate last square."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_white_cannot_move_boulder_turn_one(self):
        """White may not move the boulder on their first turn."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_on_center_blocks_diagonals_not_files_ranks(self):
        """Boulder on central intersection blocks diagonals but not files or ranks."""
        pass

    @unittest.skip("Not yet implemented: Boulder piece class")
    def test_boulder_treated_as_friendly_by_both(self):
        """Boulder is treated as a friendly piece by both sides for most purposes."""
        pass


if __name__ == '__main__':
    unittest.main()
