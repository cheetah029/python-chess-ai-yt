"""
Self-play training pipeline for the neural network.

Training loop:
  1. Play N games using current network to choose moves
  2. Record every (board_state, game_outcome) pair
  3. Train the network on this data
  4. Repeat — better network → better games → better data

The network starts random and learns entirely from self-play outcomes.
"""

import os
import sys
import time
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from engine import GameEngine
from encoding import encode_board_for_player
from network import ValueNetwork


class PositionDataset(Dataset):
    """Dataset of (board_state, outcome) pairs from self-play games."""

    def __init__(self, states, outcomes):
        """
        Args:
            states: numpy array of shape (N, 21, 8, 8)
            outcomes: numpy array of shape (N,) with values in [0, 1]
                      1.0 = current player won, 0.0 = current player lost
        """
        self.states = torch.FloatTensor(states)
        self.outcomes = torch.FloatTensor(outcomes).unsqueeze(1)

    def __len__(self):
        return len(self.states)

    def __getitem__(self, idx):
        return self.states[idx], self.outcomes[idx]


class NeuralPlayer:
    """AI player that uses the neural network to choose moves.

    For each legal turn, simulates the resulting position, evaluates it
    with the network, and picks the turn with the highest win probability.

    Uses epsilon-greedy exploration: with probability epsilon, picks a
    random turn instead of the best one. This ensures the training data
    covers diverse positions.
    """

    def __init__(self, network, device='cpu', epsilon=0.1):
        self.network = network
        self.device = device
        self.epsilon = epsilon

    def choose_turn(self, turns, engine):
        """Select the best turn using network evaluation.

        Args:
            turns: list of Turn objects from engine.get_all_legal_turns()
            engine: GameEngine instance (needed to simulate moves)

        Returns:
            chosen Turn object
        """
        if not turns:
            return None

        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            return random.choice(turns)

        # Evaluate each turn by simulating and scoring the result
        best_turn = None
        best_score = -1.0

        for turn in turns:
            score = self._evaluate_turn(turn, engine)
            if score > best_score:
                best_score = score
                best_turn = turn

        return best_turn

    def _evaluate_turn(self, turn, engine):
        """Evaluate a turn by simulating it and running the network.

        Returns the win probability for the current player after this turn.
        """
        import copy

        # Deep copy the board to simulate
        saved_board = copy.deepcopy(engine.board)
        saved_player = engine.current_player
        saved_turn_num = engine.turn_number
        saved_winner = engine.winner

        # Simulate the turn
        if turn.turn_type == 'transformation':
            row, col = turn.from_sq
            piece = engine.board.squares[row][col].piece
            engine.board.transform_queen(piece, row, col, turn.transform_target)
        elif turn.move_obj:
            engine.board.move(turn.piece, turn.move_obj)
            # Handle promotion (pick best option later, for now just queen)
            if turn.promotion_options:
                engine.board.promote(turn.piece, turn.to_sq[0], turn.to_sq[1], 'queen')

        # Encode the resulting position from opponent's perspective
        # (after our move, it's the opponent's turn)
        opponent = 'black' if saved_player == 'white' else 'white'
        state = encode_board_for_player(engine.board, opponent, saved_turn_num + 1)

        # Get opponent's win probability, invert for ours
        opp_win_prob = self.network.predict(state)
        our_win_prob = 1.0 - opp_win_prob

        # Restore board state
        engine.board = saved_board
        engine.current_player = saved_player
        engine.turn_number = saved_turn_num
        engine.winner = saved_winner

        return our_win_prob

    def choose_jump_capture(self, targets, engine):
        """Choose jump capture by evaluating each option."""
        if random.random() < self.epsilon:
            options = list(targets) + [None]
            return random.choice(options)

        # For simplicity, randomly choose for now
        # (full evaluation would require simulating each capture)
        options = list(targets) + [None]
        return random.choice(options)

    def choose_promotion(self, options, engine):
        """Choose promotion piece."""
        if random.random() < self.epsilon:
            return random.choice(options)
        # Default to queen (strongest in most games)
        return 'queen' if 'queen' in options else random.choice(options)


def play_training_game(network, device, max_turns=1000, epsilon=0.1):
    """Play a single self-play game and collect training data.

    Args:
        network: ValueNetwork to use for move selection
        device: torch device
        max_turns: maximum turns before stopping
        epsilon: exploration rate

    Returns:
        states: list of encoded board states (numpy arrays)
        outcomes: list of outcomes (1.0 = win, 0.0 = loss) for the player at each state
        game_info: dict with game metadata
    """
    engine = GameEngine(max_turns=max_turns)
    player = NeuralPlayer(network, device, epsilon)

    states = []
    players_at_state = []  # track whose perspective each state was encoded from

    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break

        # Record current position
        state = encode_board_for_player(
            engine.board, engine.current_player, engine.turn_number)
        states.append(state)
        players_at_state.append(engine.current_player)

        # Choose and execute turn
        turn = player.choose_turn(turns, engine)

        jump_choice = None
        if turn.jump_capture_targets:
            jump_choice = player.choose_jump_capture(turn.jump_capture_targets, engine)

        promo_choice = None
        if turn.promotion_options:
            promo_choice = player.choose_promotion(turn.promotion_options, engine)

        engine.execute_turn(turn, jump_choice, promo_choice)

    # Determine outcomes
    winner = engine.winner
    outcomes = []
    for p in players_at_state:
        if winner is None:
            outcomes.append(0.5)  # draw/timeout
        elif p == winner:
            outcomes.append(1.0)  # this player won
        else:
            outcomes.append(0.0)  # this player lost

    game_info = {
        'winner': winner,
        'loss_reason': engine.loss_reason,
        'total_turns': engine.turn_number,
        'turn_cap': engine.turn_number >= max_turns,
    }

    return states, outcomes, game_info


def train_epoch(network, optimizer, dataloader, device):
    """Train the network for one epoch.

    Returns:
        average loss for the epoch
    """
    network.train()
    total_loss = 0.0
    n_batches = 0

    for states, outcomes in dataloader:
        states = states.to(device)
        outcomes = outcomes.to(device)

        optimizer.zero_grad()
        predictions = network(states)
        loss = nn.MSELoss()(predictions, outcomes)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


def training_loop(
    n_iterations=50,
    games_per_iteration=100,
    max_turns=1000,
    epsilon_start=1.0,
    epsilon_end=0.1,
    epochs_per_iteration=10,
    batch_size=256,
    learning_rate=0.001,
    conv_channels=128,
    num_res_blocks=6,
    fc_size=256,
    save_dir='models/',
    device=None,
):
    """Main training loop.

    Args:
        n_iterations: number of self-play + train cycles
        games_per_iteration: games to play per iteration
        max_turns: max turns per game
        epsilon_start: initial exploration rate (1.0 = fully random)
        epsilon_end: final exploration rate
        epochs_per_iteration: training epochs per batch of games
        batch_size: training batch size
        learning_rate: optimizer learning rate
        conv_channels: network conv layer width
        num_res_blocks: number of residual blocks
        fc_size: dense layer size
        save_dir: directory to save model checkpoints
        device: torch device (auto-detected if None)
    """
    if device is None:
        if torch.backends.mps.is_available():
            device = torch.device('mps')
        elif torch.cuda.is_available():
            device = torch.device('cuda')
        else:
            device = torch.device('cpu')

    print(f"Device: {device}")
    os.makedirs(save_dir, exist_ok=True)

    # Initialize network
    network = ValueNetwork(
        conv_channels=conv_channels,
        num_res_blocks=num_res_blocks,
        fc_size=fc_size,
    ).to(device)

    optimizer = optim.Adam(network.parameters(), lr=learning_rate, weight_decay=1e-4)

    # Training history
    history = []
    all_states = []
    all_outcomes = []

    # Buffer size: keep last N positions for training (sliding window)
    max_buffer_size = 500000

    for iteration in range(n_iterations):
        iter_start = time.time()

        # Decay epsilon linearly
        epsilon = epsilon_start + (epsilon_end - epsilon_start) * (iteration / max(n_iterations - 1, 1))

        print(f"\n{'='*60}")
        print(f"Iteration {iteration + 1}/{n_iterations} | epsilon={epsilon:.3f}")
        print(f"{'='*60}")

        # --- Self-play phase ---
        print(f"  Playing {games_per_iteration} games...", end='', flush=True)
        play_start = time.time()

        iter_states = []
        iter_outcomes = []
        iter_wins = {'white': 0, 'black': 0, 'draw': 0}
        iter_lengths = []

        # Move network to CPU for self-play (avoids GPU contention)
        network_cpu = ValueNetwork(
            conv_channels=conv_channels,
            num_res_blocks=num_res_blocks,
            fc_size=fc_size,
        )
        network_cpu.load_state_dict(network.state_dict())
        network_cpu.eval()

        for g in range(games_per_iteration):
            states, outcomes, info = play_training_game(
                network_cpu, 'cpu', max_turns, epsilon)

            iter_states.extend(states)
            iter_outcomes.extend(outcomes)
            iter_lengths.append(info['total_turns'])

            if info['winner'] == 'white':
                iter_wins['white'] += 1
            elif info['winner'] == 'black':
                iter_wins['black'] += 1
            else:
                iter_wins['draw'] += 1

        play_elapsed = time.time() - play_start
        n_positions = len(iter_states)
        print(f" {play_elapsed:.1f}s ({n_positions} positions, "
              f"{games_per_iteration/play_elapsed:.1f} games/s)")
        print(f"  Results: W={iter_wins['white']} B={iter_wins['black']} "
              f"D={iter_wins['draw']} | avg_len={sum(iter_lengths)/len(iter_lengths):.0f}")

        # Add to buffer
        all_states.extend(iter_states)
        all_outcomes.extend(iter_outcomes)

        # Trim buffer if too large
        if len(all_states) > max_buffer_size:
            all_states = all_states[-max_buffer_size:]
            all_outcomes = all_outcomes[-max_buffer_size:]

        # --- Training phase ---
        print(f"  Training on {len(all_states)} positions "
              f"({epochs_per_iteration} epochs)...", end='', flush=True)
        train_start = time.time()

        dataset = PositionDataset(np.array(all_states), np.array(all_outcomes))
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        avg_loss = 0
        for epoch in range(epochs_per_iteration):
            avg_loss = train_epoch(network, optimizer, dataloader, device)

        train_elapsed = time.time() - train_start
        print(f" {train_elapsed:.1f}s (loss={avg_loss:.4f})")

        # Save checkpoint
        checkpoint_path = os.path.join(save_dir, f'model_iter_{iteration + 1:04d}.pt')
        network.save(checkpoint_path)

        # Record history
        iter_info = {
            'iteration': iteration + 1,
            'epsilon': epsilon,
            'games': games_per_iteration,
            'positions': n_positions,
            'buffer_size': len(all_states),
            'loss': avg_loss,
            'white_wins': iter_wins['white'],
            'black_wins': iter_wins['black'],
            'draws': iter_wins['draw'],
            'avg_game_length': sum(iter_lengths) / len(iter_lengths),
            'play_time': play_elapsed,
            'train_time': train_elapsed,
        }
        history.append(iter_info)

        # Save history
        with open(os.path.join(save_dir, 'training_history.json'), 'w') as f:
            json.dump(history, f, indent=2)

        iter_elapsed = time.time() - iter_start
        print(f"  Total: {iter_elapsed:.1f}s")

    # Save final model
    final_path = os.path.join(save_dir, 'model_final.pt')
    network.save(final_path)
    print(f"\nTraining complete. Final model saved to {final_path}")

    return network, history


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Train AI via self-play')
    parser.add_argument('--iterations', type=int, default=50,
                        help='Number of self-play + train cycles')
    parser.add_argument('--games', type=int, default=100,
                        help='Games per iteration')
    parser.add_argument('--max-turns', type=int, default=1000,
                        help='Max turns per game')
    parser.add_argument('--epsilon-start', type=float, default=1.0,
                        help='Initial exploration rate')
    parser.add_argument('--epsilon-end', type=float, default=0.1,
                        help='Final exploration rate')
    parser.add_argument('--epochs', type=int, default=10,
                        help='Training epochs per iteration')
    parser.add_argument('--batch-size', type=int, default=256,
                        help='Training batch size')
    parser.add_argument('--lr', type=float, default=0.001,
                        help='Learning rate')
    parser.add_argument('--channels', type=int, default=128,
                        help='Conv layer channels')
    parser.add_argument('--res-blocks', type=int, default=6,
                        help='Number of residual blocks')
    parser.add_argument('--fc-size', type=int, default=256,
                        help='Dense layer size')
    parser.add_argument('--save-dir', type=str, default='models/',
                        help='Directory to save models')

    args = parser.parse_args()

    training_loop(
        n_iterations=args.iterations,
        games_per_iteration=args.games,
        max_turns=args.max_turns,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epochs_per_iteration=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        conv_channels=args.channels,
        num_res_blocks=args.res_blocks,
        fc_size=args.fc_size,
        save_dir=args.save_dir,
    )
