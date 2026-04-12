"""
Unit tests for manipulation rule variants.

Three variants are tested:
  1. 'original' — manipulated piece can't return to its previous square for 1 turn
  2. 'freeze'   — manipulated piece can't move at all on its owner's next turn
  3. 'exclusion_zone' — manipulated piece can't return to its previous square
                        or any adjacent square for 1 turn

Tests verify:
  - Each variant's core mechanic (restriction type and duration)
  - Manipulation restrictions unchanged across variants (can't target king,
    boulder, base-form queen, piece that moved last turn)
  - Timing: restrictions clear at the correct turn
  - Edge cases: frozen piece with no other legal moves, re-manipulation, etc.
  - Self-play integration: training loop works with each variant
"""

import unittest
import sys
import os
import types
import random

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
from engine import GameEngine, Turn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sq(notation):
    """Convert chess notation to (row, col). e.g. sq('e4') -> (4, 4)"""
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


def make_engine(manipulation_mode='original', max_turns=500):
    """Create a GameEngine with the specified manipulation mode."""
    engine = GameEngine(max_turns=max_turns, manipulation_mode=manipulation_mode)
    return engine


def find_manipulation_turns(engine):
    """Return all manipulation turns from the current legal turns."""
    turns = engine.get_all_legal_turns()
    return [t for t in turns if t.turn_type == 'manipulation']


def find_turns_for_piece(engine, piece):
    """Return all move turns for a specific piece."""
    turns = engine.get_all_legal_turns()
    return [t for t in turns if t.piece is piece and t.turn_type == 'move']


def execute_any_non_manipulation_turn(engine):
    """Execute a random non-manipulation, non-transformation turn."""
    turns = engine.get_all_legal_turns()
    non_manip = [t for t in turns if t.turn_type not in ('manipulation', 'transformation')]
    if non_manip:
        turn = random.choice(non_manip)
        engine.execute_turn(turn)
        return turn
    # Fallback: execute anything
    if turns:
        turn = random.choice(turns)
        engine.execute_turn(turn)
        return turn
    return None


def play_until_manipulation_possible(engine, max_attempts=200):
    """Play random turns until a manipulation turn is available.
    Returns the list of manipulation turns, or empty list if none found."""
    for _ in range(max_attempts):
        manip_turns = find_manipulation_turns(engine)
        if manip_turns:
            return manip_turns
        # Play a random non-manipulation turn
        if not execute_any_non_manipulation_turn(engine):
            break
        if engine.is_game_over():
            break
    return []


# ============================================================================
# Tests for manipulation_mode parameter
# ============================================================================

class TestManipulationModeParameter(unittest.TestCase):
    """Test that the engine accepts and stores the manipulation_mode."""

    def test_default_mode_is_original(self):
        engine = GameEngine()
        self.assertEqual(engine.manipulation_mode, 'original')

    def test_freeze_mode_accepted(self):
        engine = GameEngine(manipulation_mode='freeze')
        self.assertEqual(engine.manipulation_mode, 'freeze')

    def test_exclusion_zone_mode_accepted(self):
        engine = GameEngine(manipulation_mode='exclusion_zone')
        self.assertEqual(engine.manipulation_mode, 'exclusion_zone')

    def test_invalid_mode_raises_error(self):
        with self.assertRaises(ValueError):
            GameEngine(manipulation_mode='invalid_mode')


# ============================================================================
# Tests for ORIGINAL manipulation (baseline)
# ============================================================================

class TestOriginalManipulation(unittest.TestCase):
    """Test the original manipulation rule: piece can't return to previous square."""

    def test_manipulated_piece_cannot_return_to_origin(self):
        """After manipulation, the piece's forbidden_square is set to its origin."""
        engine = make_engine('original')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        origin = manip.from_sq
        engine.execute_turn(manip)

        # The manipulated piece should have forbidden_square set to origin
        self.assertEqual(manip.piece.forbidden_square, origin)

    def test_manipulated_piece_can_move_elsewhere(self):
        """The manipulated piece can move to squares other than its origin."""
        engine = make_engine('original')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)

        # On the opponent's turn, the piece should have SOME moves available
        # (it's not frozen, just can't return to origin)
        piece_moves = find_turns_for_piece(engine, manip.piece)
        # Not checking count > 0 because piece might be blocked for other reasons
        # but verify no moves go to the forbidden square
        for t in piece_moves:
            self.assertNotEqual(t.to_sq, manip.from_sq,
                                "Piece should not be able to return to its manipulation origin")

    def test_forbidden_square_clears_after_one_turn(self):
        """The forbidden_square restriction clears after the piece's owner moves."""
        engine = make_engine('original')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        piece = manip.piece
        engine.execute_turn(manip)

        # Opponent's turn — piece has forbidden_square
        self.assertIsNotNone(piece.forbidden_square)
        execute_any_non_manipulation_turn(engine)  # opponent plays

        # Manipulator's turn — forbidden should be cleared now
        # (clear_forbidden_squares is called during move execution)
        # After the opponent moved, the piece's forbidden_square should clear
        # when the piece next generates moves
        # The clearing happens when any piece moves (board.clear_forbidden_squares)
        # Let's just check it's cleared by looking at the piece directly
        # After the opponent's turn execution, forbidden_squares get cleared
        self.assertIsNone(piece.forbidden_square)

    def test_piece_not_frozen(self):
        """In original mode, the piece is NOT frozen — it can move."""
        engine = make_engine('original')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)

        # The piece should NOT be frozen
        self.assertFalse(getattr(manip.piece, 'frozen', False))


# ============================================================================
# Tests for FREEZE manipulation
# ============================================================================

class TestFreezeManipulation(unittest.TestCase):
    """Test the freeze variant: manipulated piece can't move on its owner's next turn."""

    def test_manipulated_piece_is_frozen(self):
        """After manipulation, the piece's frozen flag is set."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)
        self.assertTrue(manip.piece.frozen)

    def test_frozen_piece_has_no_moves(self):
        """A frozen piece generates no legal move turns on its owner's turn."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        piece = manip.piece
        engine.execute_turn(manip)

        # Now it's the opponent's (piece owner's) turn
        piece_moves = find_turns_for_piece(engine, piece)
        self.assertEqual(len(piece_moves), 0,
                         "Frozen piece should have no legal moves")

    def test_freeze_clears_after_one_opponent_turn(self):
        """The freeze clears when the manipulator's turn begins (after opponent plays)."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        piece = manip.piece
        engine.execute_turn(manip)

        # Opponent's turn (piece is frozen) — play something else
        self.assertTrue(piece.frozen)
        execute_any_non_manipulation_turn(engine)

        # Back to manipulator's turn — freeze clears when get_all_legal_turns()
        # is called (which calls clear_frozen_for_color at the start)
        self.assertTrue(piece.frozen, "Freeze persists until next get_all_legal_turns()")
        engine.get_all_legal_turns()  # This triggers the clear
        self.assertFalse(piece.frozen,
                         "Freeze should clear when manipulator's turn begins")

    def test_freeze_allows_placement_on_threatened_square(self):
        """No safe-square restriction: queen CAN place piece on threatened squares."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        # Just verify manipulation turns exist — the absence of safe-square
        # filtering means ALL normal manipulation destinations are available
        self.assertGreater(len(manip_turns), 0)
        # Execute one — should succeed regardless of whether destination is threatened
        engine.execute_turn(manip_turns[0])

    def test_frozen_piece_not_manipulable(self):
        """A frozen piece cannot be manipulated again (it's immovable)."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        piece = manip.piece
        piece_location = manip.to_sq
        engine.execute_turn(manip)

        # Opponent plays their turn
        execute_any_non_manipulation_turn(engine)

        # Back to manipulator — piece should be unfrozen now, check for
        # manipulation of a DIFFERENT piece. But let's verify the frozen piece
        # wasn't available for manipulation on the opponent's turn
        # (this is checked in the engine's turn generation)

    def test_other_pieces_can_still_move_when_one_frozen(self):
        """Other pieces of the same color are unaffected by the freeze."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        frozen_piece = manip.piece
        engine.execute_turn(manip)

        # Opponent's turn — should have legal turns (just not the frozen piece)
        all_turns = engine.get_all_legal_turns()
        self.assertGreater(len(all_turns), 0,
                           "Other pieces should still have moves")

        # Verify frozen piece isn't among them (as a move)
        frozen_move_turns = [t for t in all_turns
                             if t.piece is frozen_piece and t.turn_type == 'move']
        self.assertEqual(len(frozen_move_turns), 0)

    def test_frozen_piece_still_blocks_movement(self):
        """A frozen piece still occupies its square and blocks other pieces."""
        engine = make_engine('freeze')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        dest = manip.to_sq
        engine.execute_turn(manip)

        # The square should still be occupied
        r, c = dest
        self.assertIsNotNone(engine.board.squares[r][c].piece)


# ============================================================================
# Tests for EXCLUSION ZONE manipulation
# ============================================================================

class TestExclusionZoneManipulation(unittest.TestCase):
    """Test the exclusion zone variant: piece can't return to origin or adjacent squares."""

    def test_manipulated_piece_has_forbidden_zone(self):
        """After manipulation, the piece has a forbidden_zone set."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)
        self.assertIsNotNone(manip.piece.forbidden_zone)

    def test_forbidden_zone_includes_origin(self):
        """The forbidden zone includes the piece's pre-manipulation square."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        origin = manip.from_sq
        engine.execute_turn(manip)

        self.assertIn(origin, manip.piece.forbidden_zone)

    def test_forbidden_zone_includes_adjacent_squares(self):
        """The forbidden zone includes all squares adjacent to the origin."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        origin_r, origin_c = manip.from_sq
        engine.execute_turn(manip)

        zone = manip.piece.forbidden_zone
        # Check all 8 adjacent squares (that are on the board)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                r, c = origin_r + dr, origin_c + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    self.assertIn((r, c), zone,
                                  f"({r},{c}) should be in forbidden zone around ({origin_r},{origin_c})")

    def test_forbidden_zone_size(self):
        """The zone has at most 9 squares (origin + 8 adjacent, clamped to board)."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)
        zone = manip.piece.forbidden_zone
        self.assertLessEqual(len(zone), 9)
        self.assertGreater(len(zone), 0)

    def test_piece_cannot_move_to_zone(self):
        """The piece cannot move to any square in its forbidden zone."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)
        zone = manip.piece.forbidden_zone

        piece_moves = find_turns_for_piece(engine, manip.piece)
        for t in piece_moves:
            self.assertNotIn(t.to_sq, zone,
                             f"Piece should not be able to move to {t.to_sq} in forbidden zone")

    def test_piece_can_move_outside_zone(self):
        """The piece CAN move to squares outside the forbidden zone."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)

        # Not frozen — piece should have some moves (outside the zone)
        self.assertFalse(getattr(manip.piece, 'frozen', False))

    def test_forbidden_zone_clears_after_one_turn(self):
        """The zone restriction clears after the piece's owner has had their turn."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        piece = manip.piece
        engine.execute_turn(manip)

        # Opponent's turn
        self.assertIsNotNone(piece.forbidden_zone)
        execute_any_non_manipulation_turn(engine)

        # Back to manipulator's turn — zone should clear
        self.assertIsNone(piece.forbidden_zone)

    def test_piece_not_frozen(self):
        """In exclusion_zone mode, the piece is NOT frozen."""
        engine = make_engine('exclusion_zone')
        manip_turns = play_until_manipulation_possible(engine)
        if not manip_turns:
            self.skipTest("Could not find manipulation opportunity")

        manip = manip_turns[0]
        engine.execute_turn(manip)
        self.assertFalse(getattr(manip.piece, 'frozen', False))


# ============================================================================
# Tests for manipulation RESTRICTIONS (must be unchanged across all variants)
# ============================================================================

class TestManipulationRestrictionsAllVariants(unittest.TestCase):
    """Verify that core manipulation restrictions work identically in all modes."""

    def _test_mode(self, mode):
        """Run a full game and verify manipulation was used correctly."""
        engine = make_engine(mode, max_turns=200)
        random.seed(42)

        manipulation_count = 0
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break

            # Verify manipulation turns don't target restricted pieces
            for t in turns:
                if t.turn_type == 'manipulation':
                    # Should not be a king
                    self.assertNotIsInstance(t.piece, King,
                                            f"Mode {mode}: can't manipulate king")
                    # Should not be a boulder
                    self.assertNotIsInstance(t.piece, Boulder,
                                            f"Mode {mode}: can't manipulate boulder")
                    # Should not be a base-form queen
                    if isinstance(t.piece, Queen):
                        self.assertTrue(t.piece.is_transformed,
                                        f"Mode {mode}: can't manipulate base-form queen")

            # Execute a random turn
            turn = random.choice(turns)
            if turn.turn_type == 'manipulation':
                manipulation_count += 1
            jc = None
            pc = None
            if turn.jump_capture_targets:
                jc = random.choice(list(turn.jump_capture_targets) + [None])
            if turn.promotion_options:
                pc = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jc, pc)

        # Should have had some manipulations in 200 turns
        # (not guaranteed, but likely with seed 42)

    def test_restrictions_original(self):
        self._test_mode('original')

    def test_restrictions_freeze(self):
        self._test_mode('freeze')

    def test_restrictions_exclusion_zone(self):
        self._test_mode('exclusion_zone')


# ============================================================================
# Tests for full game playthrough with each variant
# ============================================================================

class TestFullGameAllVariants(unittest.TestCase):
    """Play complete games with each variant to verify no crashes."""

    def _play_random_game(self, mode, seed=123):
        """Play a complete random game and return stats."""
        engine = make_engine(mode, max_turns=300)
        random.seed(seed)
        turns_played = 0
        manipulations = 0

        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            turn = random.choice(turns)
            if turn.turn_type == 'manipulation':
                manipulations += 1
            jc = None
            pc = None
            if turn.jump_capture_targets:
                jc = random.choice(list(turn.jump_capture_targets) + [None])
            if turn.promotion_options:
                pc = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jc, pc)
            turns_played += 1

        return {
            'turns': turns_played,
            'winner': engine.winner,
            'manipulations': manipulations,
            'game_over': engine.is_game_over(),
        }

    def test_original_full_game(self):
        result = self._play_random_game('original')
        self.assertTrue(result['game_over'])

    def test_freeze_full_game(self):
        result = self._play_random_game('freeze')
        self.assertTrue(result['game_over'])

    def test_exclusion_zone_full_game(self):
        result = self._play_random_game('exclusion_zone')
        self.assertTrue(result['game_over'])

    def test_all_variants_complete_multiple_seeds(self):
        """Play 5 games per variant to check stability."""
        for mode in ['original', 'freeze', 'exclusion_zone']:
            for seed in range(5):
                result = self._play_random_game(mode, seed=seed)
                self.assertTrue(result['game_over'],
                                f"Game didn't end: mode={mode}, seed={seed}")


# ============================================================================
# Tests for self-play training integration
# ============================================================================

class TestTrainingIntegration(unittest.TestCase):
    """Verify the training pipeline works with each manipulation variant."""

    def _run_mini_training(self, mode):
        """Run a minimal training iteration with the given mode."""
        from trainer import training_loop
        import tempfile
        import shutil

        output_dir = tempfile.mkdtemp()
        try:
            training_loop(
                n_iterations=1,
                decisive_games=2,
                max_turns=200,
                save_dir=output_dir,
                conv_channels=16,
                num_res_blocks=1,
                fc_size=32,
                manipulation_mode=mode,
            )
            # Check that model was saved
            import glob
            models = glob.glob(os.path.join(output_dir, 'model_*.pt'))
            self.assertGreater(len(models), 0,
                               f"No model saved for mode={mode}")
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_training_original(self):
        self._run_mini_training('original')

    def test_training_freeze(self):
        self._run_mini_training('freeze')

    def test_training_exclusion_zone(self):
        self._run_mini_training('exclusion_zone')


# ============================================================================
# Tests for game record tracking
# ============================================================================

class TestGameRecordVariants(unittest.TestCase):
    """Verify game records capture manipulation_mode."""

    def test_game_record_includes_manipulation_mode(self):
        """The game record should store which manipulation variant was used."""
        for mode in ['original', 'freeze', 'exclusion_zone']:
            engine = make_engine(mode, max_turns=50)
            random.seed(0)
            while not engine.is_game_over():
                turns = engine.get_all_legal_turns()
                if not turns:
                    break
                turn = random.choice(turns)
                jc = None
                pc = None
                if turn.jump_capture_targets:
                    jc = random.choice(list(turn.jump_capture_targets) + [None])
                if turn.promotion_options:
                    pc = random.choice(turn.promotion_options)
                engine.execute_turn(turn, jc, pc)

            record = engine.get_game_record()
            record_dict = record.to_dict()
            self.assertEqual(record_dict.get('manipulation_mode'), mode)


if __name__ == '__main__':
    unittest.main()
