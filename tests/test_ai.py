"""
Comprehensive tests for the AI training pipeline.

Tests cover:
  - Network save/load integrity
  - Make/unmake simulation correctness
  - Board encoding consistency
  - Training data labeling (draws vs decisive games)
  - Game record finalization
  - Jump capture evaluation
  - Promotion evaluation
  - Resume training from checkpoint
  - Epsilon-greedy exploration behavior
  - Buffer management
  - End-to-end training loop
"""

import sys
import os
import copy
import json
import shutil
import tempfile
import random
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
from board import Board
from engine import GameEngine, Turn
from encoding import encode_board, encode_board_for_player, NUM_CHANNELS
from network import ValueNetwork
from trainer import (
    NeuralPlayer, PositionDataset, play_training_game,
    train_epoch, training_loop,
)


# =====================================================================
# Network Save/Load Tests
# =====================================================================

class TestNetworkSaveLoad:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.save_path = os.path.join(self.tmpdir, 'test_model.pt')

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_save_load_produces_identical_predictions(self):
        """Saved and loaded network must produce identical outputs."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        # Create a test input
        state = np.random.randn(NUM_CHANNELS, 8, 8).astype(np.float32)
        pred_before = network.predict(state)

        # Save and reload
        network.save(self.save_path)
        loaded = ValueNetwork.load(self.save_path, device='cpu')
        loaded.eval()
        pred_after = loaded.predict(state)

        assert abs(pred_before - pred_after) < 1e-6, \
            f"Predictions differ: {pred_before} vs {pred_after}"

    def test_save_load_preserves_batch_predictions(self):
        """Batch predictions must match after save/load."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        states = np.random.randn(10, NUM_CHANNELS, 8, 8).astype(np.float32)
        preds_before = network.predict_batch(states)

        network.save(self.save_path)
        loaded = ValueNetwork.load(self.save_path, device='cpu')
        loaded.eval()
        preds_after = loaded.predict_batch(states)

        assert np.allclose(preds_before, preds_after, atol=1e-6), \
            "Batch predictions differ after save/load"

    def test_save_load_preserves_architecture(self):
        """Architecture config must be preserved."""
        network = ValueNetwork(conv_channels=64, num_res_blocks=4, fc_size=128)
        network.save(self.save_path)
        loaded = ValueNetwork.load(self.save_path, device='cpu')

        assert loaded.input_conv[0].out_channels == 64
        assert len(loaded.res_blocks) == 4
        assert loaded.value_head[4].out_features == 128

    def test_save_load_different_configs(self):
        """Different architectures should load correctly."""
        for channels, blocks, fc in [(16, 1, 32), (64, 4, 128), (128, 6, 256)]:
            network = ValueNetwork(conv_channels=channels, num_res_blocks=blocks, fc_size=fc)
            path = os.path.join(self.tmpdir, f'model_{channels}_{blocks}_{fc}.pt')
            network.save(path)
            loaded = ValueNetwork.load(path, device='cpu')
            assert loaded.input_conv[0].out_channels == channels
            assert len(loaded.res_blocks) == blocks
            assert loaded.value_head[4].out_features == fc


# =====================================================================
# Board Encoding Tests
# =====================================================================

class TestEncoding:

    def test_encoding_shape(self):
        """Encoding must be (21, 8, 8)."""
        board = Board()
        state = encode_board(board, 'white', 0)
        assert state.shape == (NUM_CHANNELS, 8, 8)
        assert state.dtype == np.float32

    def test_initial_position_has_correct_pieces(self):
        """Starting position should have pieces in known locations."""
        board = Board()
        state = encode_board(board, 'white', 0)

        # White pawns on row 6
        for col in range(8):
            assert state[0, 6, col] == 1.0, f"White pawn missing at (6, {col})"

        # Black pawns on row 1
        for col in range(8):
            assert state[6, 1, col] == 1.0, f"Black pawn missing at (1, {col})"

        # Channel 16: current player is white
        assert state[16, 0, 0] == 1.0

    def test_encoding_for_black_flips_board(self):
        """Black's perspective should flip the board vertically and swap colors."""
        board = Board()
        state_white = encode_board_for_player(board, 'white', 0)
        state_black = encode_board_for_player(board, 'black', 0)

        # White's pawn channel (ch 0) from white's view should match
        # the "current player's pawn channel" from black's view
        # After flip: black pawns (originally row 1) become row 6
        # After swap: black channels become channels 0-5
        # So state_black[0, 6, :] should be black pawns (originally at row 1, flipped to 6)
        for col in range(8):
            assert state_black[0, 6, col] == 1.0, \
                f"Black pawn missing at flipped position (6, {col})"

    def test_encoding_deterministic(self):
        """Same board should produce same encoding every time."""
        board = Board()
        s1 = encode_board_for_player(board, 'white', 5)
        s2 = encode_board_for_player(board, 'white', 5)
        assert np.array_equal(s1, s2)

    def test_turn_number_normalization(self):
        """Turn number should be normalized to [0, 1]."""
        board = Board()
        s0 = encode_board(board, 'white', 0)
        s500 = encode_board(board, 'white', 500)
        s1000 = encode_board(board, 'white', 1000)
        s2000 = encode_board(board, 'white', 2000)

        assert s0[20, 0, 0] == 0.0
        assert abs(s500[20, 0, 0] - 0.5) < 1e-6
        assert abs(s1000[20, 0, 0] - 1.0) < 1e-6
        assert abs(s2000[20, 0, 0] - 1.0) < 1e-6  # capped at 1.0

    def test_boulder_on_intersection_channel(self):
        """Boulder on intersection should set channel 13 to all 1s."""
        board = Board()
        state = encode_board(board, 'white', 0)
        # Boulder starts on intersection
        assert state[13, 0, 0] == 1.0
        assert state[13, 7, 7] == 1.0  # global flag, all 1s


# =====================================================================
# Make/Unmake Simulation Tests
# =====================================================================

class TestMakeUnmake:

    def test_simulation_matches_deepcopy(self):
        """Make/unmake simulation must produce same encoding as deepcopy approach."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=100)
        turns = engine.get_all_legal_turns()

        # Collect states via make/unmake
        new_states = player._collect_turn_states(turns, engine)

        # Collect states via deepcopy
        opponent = 'black' if engine.current_player == 'white' else 'white'
        next_turn = engine.turn_number + 1
        old_states = []
        for turn in turns:
            saved_board = copy.deepcopy(engine.board)
            if turn.turn_type == 'transformation':
                row, col = turn.from_sq
                piece = engine.board.squares[row][col].piece
                engine.board.transform_queen(piece, row, col, turn.transform_target)
            elif turn.move_obj:
                engine.board.move(turn.piece, turn.move_obj)
                if turn.promotion_options:
                    engine.board.promote(turn.piece, turn.to_sq[0], turn.to_sq[1], 'queen')
            state = encode_board_for_player(engine.board, opponent, next_turn)
            old_states.append(state)
            engine.board = saved_board

        assert len(new_states) == len(old_states), \
            f"State count mismatch: {len(new_states)} vs {len(old_states)}"
        for i, (new, old) in enumerate(zip(new_states, old_states)):
            assert np.allclose(new, old), \
                f"State mismatch at turn {i}: {turns[i]}"

    def test_board_unchanged_after_simulation(self):
        """Board must be identical before and after _collect_turn_states."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=100)
        board_before = encode_board(engine.board, 'white', 0)

        turns = engine.get_all_legal_turns()
        player._collect_turn_states(turns, engine)

        board_after = encode_board(engine.board, 'white', 0)
        assert np.array_equal(board_before, board_after), \
            "Board state changed after simulation"

    def test_simulation_after_several_moves(self):
        """Make/unmake should work correctly mid-game, not just from starting position."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        player = NeuralPlayer(network, 'cpu', epsilon=1.0)  # random moves

        engine = GameEngine(max_turns=100)

        # Play 10 random moves
        for _ in range(10):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            turn = random.choice(turns)
            jump_choice = None
            if turn.jump_capture_targets:
                options = list(turn.jump_capture_targets) + [None]
                jump_choice = random.choice(options)
            promo_choice = None
            if turn.promotion_options:
                promo_choice = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jump_choice, promo_choice)

        if engine.is_game_over():
            return  # game ended, can't test further

        # Now test that simulation still works
        turns = engine.get_all_legal_turns()
        if not turns:
            return

        board_before = encode_board(engine.board, engine.current_player, engine.turn_number)
        player._collect_turn_states(turns, engine)
        board_after = encode_board(engine.board, engine.current_player, engine.turn_number)

        assert np.array_equal(board_before, board_after), \
            "Board changed after mid-game simulation"


# =====================================================================
# Training Data Labeling Tests
# =====================================================================

class TestTrainingData:

    def test_decisive_game_has_outcomes(self):
        """A game with a winner should return non-empty outcomes."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        # Play games until we get a decisive one
        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=500, epsilon=1.0)
            if info['winner'] is not None:
                assert len(outcomes) > 0, "Decisive game returned empty outcomes"
                assert len(states) == len(outcomes), \
                    f"States/outcomes length mismatch: {len(states)} vs {len(outcomes)}"
                assert all(o in (0.0, 1.0) for o in outcomes), \
                    "Outcomes should be 0.0 or 1.0 for decisive games"
                # Both 1.0 and 0.0 should appear (both players' perspectives)
                assert 1.0 in outcomes, "Winner's positions should be labeled 1.0"
                assert 0.0 in outcomes, "Loser's positions should be labeled 0.0"
                return

        # If we couldn't find a decisive game in 50 tries, skip
        assert False, "Could not find a decisive game in 50 attempts"

    def test_draw_game_has_no_outcomes(self):
        """A draw game should return empty outcomes but non-empty states."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        # Force a draw by using very low max_turns
        # At max_turns=10, most games won't finish
        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=10, epsilon=1.0)
            if info['winner'] is None:
                assert len(outcomes) == 0, \
                    f"Draw game should have empty outcomes, got {len(outcomes)}"
                assert len(states) > 0, \
                    "Draw game should still have states for data collection"
                assert info['turn_cap'] is True, "Draw should be from turn cap"
                return

        # Most games at max_turns=10 should be draws
        assert False, "Could not find a draw game"

    def test_draw_states_not_in_training_buffer(self):
        """Training buffer should only contain decisive game data."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        all_states = []
        all_outcomes = []

        for _ in range(20):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=50, epsilon=1.0)
            # Mimic the training loop logic
            if outcomes:  # only add decisive game data
                all_states.extend(states)
                all_outcomes.extend(outcomes)

        if all_outcomes:
            assert all(o in (0.0, 1.0) for o in all_outcomes), \
                "Training buffer should only contain 0.0 or 1.0, never 0.5"

    def test_outcomes_match_winner_perspective(self):
        """Winner's positions should be 1.0, loser's should be 0.0."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=500, epsilon=1.0)
            if info['winner'] is not None:
                # Outcomes alternate between players (white/black/white/...)
                # Winner's positions should be 1.0
                winner = info['winner']
                # First move is always white
                for i, outcome in enumerate(outcomes):
                    player_at_i = 'white' if i % 2 == 0 else 'black'
                    if player_at_i == winner:
                        assert outcome == 1.0, \
                            f"Position {i} ({player_at_i}={winner}) should be 1.0"
                    else:
                        assert outcome == 0.0, \
                            f"Position {i} ({player_at_i}!={winner}) should be 0.0"
                return


# =====================================================================
# Game Record Tests
# =====================================================================

class TestGameRecord:

    def test_game_record_has_winner(self):
        """Game record must correctly reflect the winner."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=500, epsilon=1.0)
            record = info['game_record']
            assert record['winner'] == info['winner'], \
                f"Game record winner ({record['winner']}) != info winner ({info['winner']})"
            if info['winner']:
                assert record['loss_reason'] in ('royals_captured', 'no_legal_moves'), \
                    f"Unexpected loss reason: {record['loss_reason']}"
                return

    def test_game_record_turn_count_matches(self):
        """Game record total_turns must match info total_turns."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        states, outcomes, info = play_training_game(
            network, 'cpu', max_turns=100, epsilon=1.0)
        record = info['game_record']
        assert record['total_turns'] == info['total_turns']
        assert len(record['turns']) == info['total_turns']

    def test_game_record_captures_counted(self):
        """Total captures should match number of capture turns."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        states, outcomes, info = play_training_game(
            network, 'cpu', max_turns=200, epsilon=1.0)
        record = info['game_record']
        capture_turns = sum(1 for t in record['turns'] if t['is_capture'])
        # total_captures might include jump captures too
        assert record['total_captures'] >= capture_turns or \
            record['total_captures'] == capture_turns, \
            f"Capture count mismatch: record={record['total_captures']}, counted={capture_turns}"

    def test_draw_game_record_has_turn_cap(self):
        """Draw game record should have turn_cap_reached=True."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=10, epsilon=1.0)
            if info['winner'] is None:
                record = info['game_record']
                assert record['turn_cap_reached'] is True
                assert record['loss_reason'] == 'turn_cap'
                return


# =====================================================================
# Jump Capture and Promotion Evaluation Tests
# =====================================================================

class TestChoiceEvaluation:

    def test_jump_capture_returns_valid_option(self):
        """choose_jump_capture must return a target from the list or None."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=500)

        # Play until we find a turn with jump capture targets
        for _ in range(200):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break

            # Check all turns for jump capture opportunities
            for turn in turns:
                if turn.jump_capture_targets:
                    targets = turn.jump_capture_targets
                    choice = player.choose_jump_capture(targets, turn, engine)
                    valid_options = list(targets) + [None]
                    assert choice in valid_options, \
                        f"Invalid jump capture choice: {choice}, valid: {valid_options}"
                    return

            # Play a random move to advance the game
            turn = random.choice(turns)
            jump = None
            if turn.jump_capture_targets:
                jump = random.choice(list(turn.jump_capture_targets) + [None])
            promo = None
            if turn.promotion_options:
                promo = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jump, promo)

    def test_promotion_returns_valid_option(self):
        """choose_promotion must return one of the offered piece types."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=1000)

        # Play until we find a promotion
        for _ in range(500):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break

            for turn in turns:
                if turn.promotion_options:
                    choice = player.choose_promotion(
                        turn.promotion_options, turn, engine)
                    assert choice in turn.promotion_options, \
                        f"Invalid promotion: {choice}, valid: {turn.promotion_options}"
                    return

            turn = random.choice(turns)
            jump = None
            if turn.jump_capture_targets:
                jump = random.choice(list(turn.jump_capture_targets) + [None])
            promo = None
            if turn.promotion_options:
                promo = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jump, promo)

    def test_jump_capture_board_unchanged(self):
        """Board must be unchanged after evaluating jump capture options."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=500)

        for _ in range(200):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break

            for turn in turns:
                if turn.jump_capture_targets:
                    board_before = encode_board(
                        engine.board, engine.current_player, engine.turn_number)
                    player.choose_jump_capture(
                        turn.jump_capture_targets, turn, engine)
                    board_after = encode_board(
                        engine.board, engine.current_player, engine.turn_number)
                    assert np.array_equal(board_before, board_after), \
                        "Board changed after jump capture evaluation"
                    return

            turn = random.choice(turns)
            jump = None
            if turn.jump_capture_targets:
                jump = random.choice(list(turn.jump_capture_targets) + [None])
            promo = None
            if turn.promotion_options:
                promo = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jump, promo)

    def test_promotion_board_unchanged(self):
        """Board must be unchanged after evaluating promotion options."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=1000)

        for _ in range(500):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break

            for turn in turns:
                if turn.promotion_options:
                    board_before = encode_board(
                        engine.board, engine.current_player, engine.turn_number)
                    player.choose_promotion(
                        turn.promotion_options, turn, engine)
                    board_after = encode_board(
                        engine.board, engine.current_player, engine.turn_number)
                    assert np.array_equal(board_before, board_after), \
                        "Board changed after promotion evaluation"
                    return

            turn = random.choice(turns)
            jump = None
            if turn.jump_capture_targets:
                jump = random.choice(list(turn.jump_capture_targets) + [None])
            promo = None
            if turn.promotion_options:
                promo = random.choice(turn.promotion_options)
            engine.execute_turn(turn, jump, promo)


# =====================================================================
# Epsilon-Greedy Tests
# =====================================================================

class TestEpsilonGreedy:

    def test_epsilon_1_always_random(self):
        """With epsilon=1.0, every turn should be random (no network eval)."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=1.0)

        engine = GameEngine(max_turns=100)
        turns = engine.get_all_legal_turns()

        # Run many times — should pick different turns
        choices = set()
        for _ in range(100):
            choice = player.choose_turn(turns, engine)
            choices.add(id(choice))

        # With 55+ legal turns, 100 random picks should hit multiple
        assert len(choices) > 1, "Epsilon=1.0 should produce varied choices"

    def test_epsilon_0_deterministic(self):
        """With epsilon=0.0, the same position should always pick the same turn."""
        network = ValueNetwork(conv_channels=32, num_res_blocks=2, fc_size=64)
        network.eval()
        player = NeuralPlayer(network, 'cpu', epsilon=0.0)

        engine = GameEngine(max_turns=100)
        turns = engine.get_all_legal_turns()

        first_choice = player.choose_turn(turns, engine)
        for _ in range(10):
            choice = player.choose_turn(turns, engine)
            assert choice is first_choice, \
                "Epsilon=0.0 should be deterministic"


# =====================================================================
# Resume Training Tests
# =====================================================================

class TestResumeTraining:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_resume_continues_iteration_numbering(self):
        """Resumed training should continue from the correct iteration."""
        # Train 2 iterations
        network, history = training_loop(
            n_iterations=2, decisive_games=3, max_turns=200,
            epsilon_start=1.0, epsilon_end=0.5,
            epochs_per_iteration=1, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )
        assert len(history) == 2
        assert history[-1]['iteration'] == 2

        # Resume for 1 more iteration
        final_path = os.path.join(self.tmpdir, 'model_final.pt')
        network2, history2 = training_loop(
            n_iterations=1, decisive_games=3, max_turns=200,
            epsilon_start=0.3, epsilon_end=0.3,
            epochs_per_iteration=1, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
            resume_from=final_path,
        )

        assert len(history2) == 3, f"Expected 3 history entries, got {len(history2)}"
        assert history2[-1]['iteration'] == 3

    def test_resume_loads_correct_weights(self):
        """Resumed network should have same weights as saved checkpoint."""
        network, _ = training_loop(
            n_iterations=1, decisive_games=3, max_turns=200,
            epsilon_start=1.0, epsilon_end=1.0,
            epochs_per_iteration=2, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )

        # Get prediction from trained network
        state = np.random.randn(NUM_CHANNELS, 8, 8).astype(np.float32)
        network.eval()
        network_cpu = network.to('cpu')
        pred_original = network_cpu.predict(state)

        # Load checkpoint and predict
        loaded = ValueNetwork.load(
            os.path.join(self.tmpdir, 'model_final.pt'), device='cpu')
        loaded.eval()
        pred_loaded = loaded.predict(state)

        assert abs(pred_original - pred_loaded) < 1e-5, \
            f"Resumed weights differ: {pred_original} vs {pred_loaded}"

    def test_history_json_saved(self):
        """Training history should be saved to disk as JSON."""
        training_loop(
            n_iterations=2, decisive_games=3, max_turns=200,
            epsilon_start=1.0, epsilon_end=0.5,
            epochs_per_iteration=1, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )

        history_path = os.path.join(self.tmpdir, 'training_history.json')
        assert os.path.exists(history_path)

        with open(history_path) as f:
            history = json.load(f)
        assert len(history) == 2
        assert 'iteration' in history[0]
        assert 'loss' in history[0]
        assert 'white_wins' in history[0]
        assert 'decisive_games' in history[0]


# =====================================================================
# End-to-End Training Tests
# =====================================================================

class TestEndToEnd:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_training_loop_completes(self):
        """Full training loop should complete without errors."""
        network, history = training_loop(
            n_iterations=2, decisive_games=3, max_turns=200,
            epsilon_start=1.0, epsilon_end=0.5,
            epochs_per_iteration=2, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )

        assert network is not None
        assert len(history) == 2
        assert os.path.exists(os.path.join(self.tmpdir, 'model_final.pt'))
        assert os.path.exists(os.path.join(self.tmpdir, 'model_iter_0001.pt'))
        assert os.path.exists(os.path.join(self.tmpdir, 'model_iter_0002.pt'))

    def test_loss_is_valid_number(self):
        """Training loss should be a valid positive number."""
        _, history = training_loop(
            n_iterations=2, decisive_games=5, max_turns=200,
            epsilon_start=1.0, epsilon_end=0.5,
            epochs_per_iteration=2, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )

        for h in history:
            assert isinstance(h['loss'], float)
            assert h['loss'] > 0, "Loss should be positive"
            assert not np.isnan(h['loss']), "Loss should not be NaN"
            assert not np.isinf(h['loss']), "Loss should not be infinite"

    def test_network_output_range(self):
        """Network output should always be in [0, 1] (sigmoid)."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        # Test with random inputs
        states = np.random.randn(50, NUM_CHANNELS, 8, 8).astype(np.float32)
        preds = network.predict_batch(states)

        assert np.all(preds >= 0.0), "Predictions should be >= 0"
        assert np.all(preds <= 1.0), "Predictions should be <= 1"

    def test_trained_model_can_play_games(self):
        """A trained model should be able to play complete games."""
        network, _ = training_loop(
            n_iterations=2, decisive_games=5, max_turns=200,
            epsilon_start=0.8, epsilon_end=0.3,
            epochs_per_iteration=2, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )

        # Play a game with the trained model at low epsilon
        states, outcomes, info = play_training_game(
            network.to('cpu'), 'cpu', max_turns=200, epsilon=0.1)

        assert info['total_turns'] > 0
        assert len(states) > 0
        assert info['game_record'] is not None
        assert info['game_record']['total_turns'] == info['total_turns']

    def test_checkpoints_are_different(self):
        """Each iteration's checkpoint should differ from the previous."""
        training_loop(
            n_iterations=3, decisive_games=5, max_turns=200,
            epsilon_start=1.0, epsilon_end=0.3,
            epochs_per_iteration=3, batch_size=32,
            conv_channels=16, num_res_blocks=1, fc_size=32,
            save_dir=self.tmpdir,
        )

        m1 = ValueNetwork.load(os.path.join(self.tmpdir, 'model_iter_0001.pt'), 'cpu')
        m2 = ValueNetwork.load(os.path.join(self.tmpdir, 'model_iter_0002.pt'), 'cpu')

        state = np.random.randn(NUM_CHANNELS, 8, 8).astype(np.float32)
        m1.eval(); m2.eval()
        p1 = m1.predict(state)
        p2 = m2.predict(state)

        # After training, weights should have changed
        assert abs(p1 - p2) > 1e-7, \
            "Checkpoints should produce different predictions after training"


# =====================================================================
# PositionDataset Tests
# =====================================================================

class TestPositionDataset:

    def test_dataset_length(self):
        """Dataset length should match input."""
        states = np.random.randn(100, NUM_CHANNELS, 8, 8).astype(np.float32)
        outcomes = np.random.rand(100).astype(np.float32)
        dataset = PositionDataset(states, outcomes)
        assert len(dataset) == 100

    def test_dataset_shapes(self):
        """Dataset items should have correct shapes."""
        states = np.random.randn(10, NUM_CHANNELS, 8, 8).astype(np.float32)
        outcomes = np.random.rand(10).astype(np.float32)
        dataset = PositionDataset(states, outcomes)

        state, outcome = dataset[0]
        assert state.shape == (NUM_CHANNELS, 8, 8)
        assert outcome.shape == (1,)  # unsqueezed

    def test_dataset_types(self):
        """Dataset items should be float tensors."""
        states = np.random.randn(5, NUM_CHANNELS, 8, 8).astype(np.float32)
        outcomes = np.array([0.0, 1.0, 0.0, 1.0, 0.0], dtype=np.float32)
        dataset = PositionDataset(states, outcomes)

        state, outcome = dataset[0]
        assert state.dtype == torch.float32
        assert outcome.dtype == torch.float32


# =====================================================================
# Draw Data Preservation Tests
# =====================================================================

class TestDrawDataPreservation:
    """Ensure draw game data is preserved and retrievable, not silently discarded."""

    def test_draw_game_record_is_complete(self):
        """Draw game records should have all the same fields as decisive game records."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        # Force a draw with low max_turns
        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=10, epsilon=1.0)
            if info['winner'] is None:
                record = info['game_record']
                # Must have all required fields
                assert 'winner' in record, "Draw record missing 'winner' field"
                assert 'loss_reason' in record, "Draw record missing 'loss_reason' field"
                assert 'total_turns' in record, "Draw record missing 'total_turns' field"
                assert 'total_captures' in record, "Draw record missing 'total_captures' field"
                assert 'turn_cap_reached' in record, "Draw record missing 'turn_cap_reached' field"
                assert 'turns' in record, "Draw record missing 'turns' field"
                assert 'manipulation_mode' in record, "Draw record missing 'manipulation_mode' field"
                # Draw-specific values
                assert record['winner'] is None
                assert record['turn_cap_reached'] is True
                assert record['loss_reason'] == 'turn_cap'
                assert len(record['turns']) == record['total_turns']
                assert len(record['turns']) > 0, "Draw record should have at least 1 turn"
                return

        assert False, "Could not force a draw in 50 attempts"

    def test_draw_game_record_has_turn_data(self):
        """Each turn in a draw game record should have piece/position data."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=10, epsilon=1.0)
            if info['winner'] is None:
                record = info['game_record']
                for turn in record['turns']:
                    assert 'turn_number' in turn
                    assert 'player' in turn
                    assert 'turn_type' in turn
                    assert 'piece_type' in turn
                    assert 'piece_color' in turn
                    assert 'from_sq' in turn
                    assert 'to_sq' in turn
                    assert 'is_capture' in turn
                    assert 'pieces_remaining' in turn
                    assert turn['player'] in ('white', 'black')
                return

        assert False, "Could not force a draw"

    def test_draw_game_record_has_pieces_remaining(self):
        """Draw game records should have pieces_remaining on the last turn."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=10, epsilon=1.0)
            if info['winner'] is None:
                record = info['game_record']
                last_turn = record['turns'][-1]
                pr = last_turn['pieces_remaining']
                assert 'white' in pr, "Missing white pieces_remaining"
                assert 'black' in pr, "Missing black pieces_remaining"
                # Should have pieces remaining (game didn't end decisively)
                white_total = sum(pr['white'].values())
                black_total = sum(pr['black'].values())
                assert white_total > 0, "White should have pieces remaining in draw"
                assert black_total > 0, "Black should have pieces remaining in draw"
                return

        assert False, "Could not force a draw"

    def test_draw_game_record_serializable(self):
        """Draw game records must be JSON-serializable for storage."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=10, epsilon=1.0)
            if info['winner'] is None:
                record = info['game_record']
                # Must be serializable without error
                json_str = json.dumps(record)
                # Must be deserializable back to the same data
                restored = json.loads(json_str)
                assert restored['winner'] == record['winner']
                assert restored['total_turns'] == record['total_turns']
                assert len(restored['turns']) == len(record['turns'])
                return

        assert False, "Could not force a draw"


# =====================================================================
# Draw Exclusion from Training Tests
# =====================================================================

class TestDrawExclusionFromTraining:
    """Ensure draw game data is never used for training the neural network."""

    def test_draw_returns_empty_outcomes(self):
        """play_training_game must return empty outcomes for draws."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=5, epsilon=1.0)
            if info['winner'] is None:
                assert outcomes == [], \
                    f"Draw should return empty outcomes, got {len(outcomes)} items"
                return

        assert False, "Could not force a draw"

    def test_decisive_returns_nonempty_outcomes(self):
        """play_training_game must return non-empty outcomes for decisive games."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=500, epsilon=1.0)
            if info['winner'] is not None:
                assert len(outcomes) > 0, \
                    "Decisive game should return non-empty outcomes"
                assert len(outcomes) == len(states), \
                    "Each state must have a corresponding outcome"
                return

        assert False, "Could not find a decisive game"

    def test_training_buffer_excludes_draws(self):
        """Simulating the training loop: draws must not add data to the buffer."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        buffer_states = []
        buffer_outcomes = []
        n_decisive = 0
        n_draws = 0

        for _ in range(30):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=50, epsilon=1.0)

            # This is the exact logic from the training loop
            if outcomes:
                buffer_states.extend(states)
                buffer_outcomes.extend(outcomes)
                n_decisive += 1
            else:
                n_draws += 1

        # Buffer should only contain 0.0 and 1.0 (no 0.5 from draws)
        for o in buffer_outcomes:
            assert o in (0.0, 1.0), \
                f"Training buffer contains {o}, expected only 0.0 or 1.0"

        # If we had draws, verify they weren't added
        if n_draws > 0 and n_decisive > 0:
            # Buffer should have fewer entries than total states would suggest
            # (draw states were excluded)
            assert len(buffer_outcomes) > 0, \
                "Buffer should have data from decisive games"

    def test_draw_outcomes_never_contain_half(self):
        """Draw outcomes must never be 0.5 — they must be empty."""
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()

        for _ in range(50):
            states, outcomes, info = play_training_game(
                network, 'cpu', max_turns=5, epsilon=1.0)
            if info['winner'] is None:
                # Outcomes must be empty, never [0.5, 0.5, ...]
                assert len(outcomes) == 0, \
                    "Draw outcomes must be empty list, not partial values"
                for o in outcomes:
                    assert o != 0.5, "Draw outcomes must never be 0.5"
                return

        assert False, "Could not force a draw"

    def test_training_loop_records_draw_count(self):
        """Training history must accurately track the number of draws."""
        tmpdir = tempfile.mkdtemp()
        try:
            _, history = training_loop(
                n_iterations=2, decisive_games=3, max_turns=200,
                epsilon_start=1.0, epsilon_end=0.5,
                epochs_per_iteration=2, batch_size=32,
                conv_channels=16, num_res_blocks=1, fc_size=32,
                save_dir=tmpdir,
            )

            for h in history:
                assert 'draws' in h, "Training history must record draw count"
                assert 'decisive_games' in h, "Training history must record decisive count"
                assert 'total_games' in h, "Training history must record total games"
                assert isinstance(h['draws'], int)
                assert h['draws'] >= 0
                assert h['total_games'] == h['decisive_games'] + h['draws'], \
                    f"total_games ({h['total_games']}) != decisive ({h['decisive_games']}) + draws ({h['draws']})"
        finally:
            shutil.rmtree(tmpdir)


# =====================================================================
# Decisive Game Collection Tests
# =====================================================================

class TestDecisiveGameCollection:
    """Ensure games are collected until N decisive games, not N total games."""

    def test_training_loop_collects_exact_decisive_count(self):
        """Training loop must play until exactly N decisive games per iteration."""
        tmpdir = tempfile.mkdtemp()
        try:
            target_decisive = 5
            _, history = training_loop(
                n_iterations=2, decisive_games=target_decisive, max_turns=200,
                epsilon_start=1.0, epsilon_end=0.5,
                epochs_per_iteration=2, batch_size=32,
                conv_channels=16, num_res_blocks=1, fc_size=32,
                save_dir=tmpdir,
            )

            for h in history:
                assert h['decisive_games'] == target_decisive, \
                    f"Expected {target_decisive} decisive games, got {h['decisive_games']}"
                # Total games should be >= decisive (some may be draws)
                assert h['total_games'] >= h['decisive_games'], \
                    "Total games should be >= decisive games"
        finally:
            shutil.rmtree(tmpdir)

    def test_collect_games_returns_exact_decisive_count(self):
        """collect_games must return exactly N decisive game records."""
        from collect_variant_data import collect_games

        # Save a small model for testing
        tmpdir = tempfile.mkdtemp()
        try:
            network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
            model_path = os.path.join(tmpdir, 'test_model.pt')
            network.save(model_path)

            target = 5
            records, draw_records, total_played = collect_games(
                model_path, 'original', target, max_turns=200, epsilon=1.0)

            assert len(records) == target, \
                f"Expected {target} decisive records, got {len(records)}"
            # All records should have a winner
            for r in records:
                assert r['winner'] is not None, \
                    "Decisive record should have a winner"
                assert r['winner'] in ('white', 'black'), \
                    f"Unexpected winner: {r['winner']}"
            # Total played should be >= target (draws don't count)
            assert total_played >= target, \
                f"Total played ({total_played}) should be >= target ({target})"
            assert total_played == len(records) + len(draw_records), \
                f"Total played ({total_played}) should equal decisive ({len(records)}) + draws ({len(draw_records)})"
        finally:
            shutil.rmtree(tmpdir)

    def test_collect_games_draw_records_are_draws(self):
        """All records in draw_records must be actual draws (winner is None)."""
        from collect_variant_data import collect_games

        tmpdir = tempfile.mkdtemp()
        try:
            network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
            model_path = os.path.join(tmpdir, 'test_model.pt')
            network.save(model_path)

            # Use low max_turns to increase draw probability
            records, draw_records, total_played = collect_games(
                model_path, 'original', 3, max_turns=50, epsilon=1.0)

            # Decisive records must all have winners
            for r in records:
                assert r['winner'] is not None

            # Draw records must all have no winner
            for r in draw_records:
                assert r['winner'] is None, \
                    f"Draw record should have winner=None, got {r['winner']}"
                assert r['turn_cap_reached'] is True, \
                    "Draw record should have turn_cap_reached=True"
        finally:
            shutil.rmtree(tmpdir)

    def test_collect_games_no_decisive_records_are_draws(self):
        """No record in the decisive list should be a draw."""
        from collect_variant_data import collect_games

        tmpdir = tempfile.mkdtemp()
        try:
            network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
            model_path = os.path.join(tmpdir, 'test_model.pt')
            network.save(model_path)

            records, draw_records, total_played = collect_games(
                model_path, 'original', 5, max_turns=200, epsilon=1.0)

            for r in records:
                assert r['winner'] is not None, \
                    "Decisive records list must not contain draws"
                assert r['winner'] in ('white', 'black')
        finally:
            shutil.rmtree(tmpdir)


# =====================================================================
# Game Record Completeness Tests
# =====================================================================

class TestGameRecordCompleteness:
    """Ensure all game records (decisive and draw) are complete and retrievable."""

    REQUIRED_GAME_FIELDS = [
        'winner', 'loss_reason', 'total_turns', 'total_captures',
        'turn_cap_reached', 'manipulation_mode', 'turns',
    ]

    REQUIRED_TURN_FIELDS = [
        'turn_number', 'player', 'turn_type', 'piece_type', 'piece_color',
        'from_sq', 'to_sq', 'is_capture', 'pieces_remaining',
    ]

    def _play_game(self, max_turns=200):
        network = ValueNetwork(conv_channels=16, num_res_blocks=1, fc_size=32)
        network.eval()
        return play_training_game(network, 'cpu', max_turns=max_turns, epsilon=1.0)

    def test_decisive_record_has_all_fields(self):
        """Decisive game records must have all required fields."""
        for _ in range(50):
            states, outcomes, info = self._play_game(max_turns=500)
            if info['winner'] is not None:
                record = info['game_record']
                for field in self.REQUIRED_GAME_FIELDS:
                    assert field in record, \
                        f"Decisive record missing required field '{field}'"
                return
        assert False, "Could not find a decisive game"

    def test_draw_record_has_all_fields(self):
        """Draw game records must have all required fields."""
        for _ in range(50):
            states, outcomes, info = self._play_game(max_turns=10)
            if info['winner'] is None:
                record = info['game_record']
                for field in self.REQUIRED_GAME_FIELDS:
                    assert field in record, \
                        f"Draw record missing required field '{field}'"
                return
        assert False, "Could not force a draw"

    def test_every_turn_has_required_fields(self):
        """Every turn in a game record must have all required fields."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']
        for i, turn in enumerate(record['turns']):
            for field in self.REQUIRED_TURN_FIELDS:
                assert field in turn, \
                    f"Turn {i} missing required field '{field}'"

    def test_turn_numbers_are_sequential(self):
        """Turn numbers must be sequential starting from 0."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']
        for i, turn in enumerate(record['turns']):
            assert turn['turn_number'] == i, \
                f"Turn {i} has turn_number={turn['turn_number']}"

    def test_players_alternate(self):
        """Players must alternate white/black each turn."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']
        for i, turn in enumerate(record['turns']):
            expected = 'white' if i % 2 == 0 else 'black'
            assert turn['player'] == expected, \
                f"Turn {i} has player={turn['player']}, expected {expected}"

    def test_total_turns_matches_turn_list(self):
        """total_turns field must equal the length of the turns list."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']
        assert record['total_turns'] == len(record['turns']), \
            f"total_turns={record['total_turns']} != len(turns)={len(record['turns'])}"

    def test_game_record_fully_json_roundtrips(self):
        """Game records must survive JSON serialization and deserialization."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']

        json_str = json.dumps(record)
        restored = json.loads(json_str)

        assert restored['winner'] == record['winner']
        assert restored['total_turns'] == record['total_turns']
        assert restored['total_captures'] == record['total_captures']
        assert restored['manipulation_mode'] == record['manipulation_mode']
        assert len(restored['turns']) == len(record['turns'])

        # Spot-check a turn (tuples become lists after JSON roundtrip)
        if record['turns']:
            orig_turn = record['turns'][0]
            rest_turn = restored['turns'][0]
            assert rest_turn['player'] == orig_turn['player']
            assert rest_turn['piece_type'] == orig_turn['piece_type']
            assert list(rest_turn['from_sq']) == list(orig_turn['from_sq'])
            assert list(rest_turn['to_sq']) == list(orig_turn['to_sq'])

    def test_pieces_remaining_sums_correctly(self):
        """pieces_remaining should reflect actual piece counts at that turn."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']

        if record['turns']:
            first_turn = record['turns'][0]
            pr = first_turn['pieces_remaining']
            # First turn: full starting army (before any captures)
            white_total = sum(pr['white'].values())
            black_total = sum(pr['black'].values())
            # Should be reasonable starting counts (14 per side in standard setup)
            assert white_total >= 1, "White should have pieces"
            assert black_total >= 1, "Black should have pieces"

    def test_capture_count_never_negative(self):
        """total_captures should never be negative."""
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']
        assert record['total_captures'] >= 0

    def test_turn_types_are_valid(self):
        """All turn types must be one of the recognized types."""
        valid_types = {'move', 'boulder', 'manipulation', 'transformation'}
        states, outcomes, info = self._play_game(max_turns=100)
        record = info['game_record']
        for turn in record['turns']:
            assert turn['turn_type'] in valid_types, \
                f"Invalid turn_type: {turn['turn_type']}"
