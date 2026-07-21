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
        """Select the best Turn from the legal-turns list using one batched
        network evaluation.

        The engine enumerates each fully-specified combination (move +
        jump_choice + promo_choice) as a separate Turn, so this method
        just evaluates every Turn in the list and picks the highest-
        win-probability option. No sub-choices remain after this call —
        the returned Turn is complete.

        Args:
            turns: list of fully-specified Turn objects from
                engine.get_all_legal_turns()
            engine: GameEngine instance (used to simulate each Turn for
                state encoding)

        Returns:
            chosen Turn object (already includes its jump_choice and
            promo_choice, ready for execute_turn).
        """
        if not turns:
            return None

        # Epsilon-greedy exploration.
        if random.random() < self.epsilon:
            return random.choice(turns)

        # Batch-evaluate every Turn.
        board = engine.board
        opponent = 'black' if engine.current_player == 'white' else 'white'
        next_turn_num = engine.turn_number + 1
        states = []
        for turn in turns:
            if turn.turn_type == 'transformation':
                state = self._simulate_transformation(
                    board, turn, opponent, next_turn_num)
            else:
                state = self._simulate_move(
                    board, turn, opponent, next_turn_num,
                    jump_choice=turn.jump_choice,
                    promo_choice=turn.promo_choice)
            states.append(state)

        opp_win_probs = self.network.predict_batch(np.array(states))
        our_win_probs = 1.0 - opp_win_probs
        best_idx = np.argmax(our_win_probs)
        return turns[best_idx]

    def _collect_turn_states(self, turns, engine):
        """Simulate all turns and collect encoded board states.

        Uses lightweight make/unmake instead of deep copy — saves only the
        affected squares and piece attributes, applies the turn, encodes,
        then restores. ~30-50× faster than copy.deepcopy per turn.

        Returns:
            list of numpy arrays, each shape (21, 8, 8)
        """
        from piece import Boulder

        board = engine.board
        opponent = 'black' if engine.current_player == 'white' else 'white'
        next_turn_num = engine.turn_number + 1
        states = []

        for turn in turns:
            if turn.turn_type == 'transformation':
                state = self._simulate_transformation(
                    board, turn, opponent, next_turn_num)
            elif turn.move_obj:
                state = self._simulate_move(
                    board, turn, opponent, next_turn_num)
            else:
                continue
            states.append(state)

        return states

    def _simulate_move(self, board, turn, opponent, next_turn_num,
                       jump_choice=None, promo_choice=None):
        """Simulate a spatial move (plus optional sub-choices) with
        lightweight save/restore.

        Args:
            jump_choice: (row, col) of a jump-capture target to remove, or
                None to decline / no jump-capture available.
            promo_choice: piece-type string ('queen' / 'rook' / 'bishop' /
                'knight') for pawn promotion, or None if not promoting.
                None when the move is not a promotion.
        """
        from piece import Boulder

        move = turn.move_obj
        piece = turn.piece
        initial = move.initial
        final = move.final

        # --- Save affected state ---
        is_boulder_from_intersection = isinstance(piece, Boulder) and piece.on_intersection

        saved_initial_piece = None
        if initial.row >= 0 and initial.col >= 0:
            saved_initial_piece = board.squares[initial.row][initial.col].piece
        saved_final_piece = board.squares[final.row][final.col].piece
        saved_board_boulder = board.boulder
        saved_last_move = board.last_move
        saved_last_action = board.last_action

        # Save piece attributes that move() modifies
        saved_piece_moved = piece.moved
        saved_piece_forbidden = piece.forbidden_square

        # Save boulder-specific attributes
        saved_boulder_attrs = None
        if isinstance(piece, Boulder):
            saved_boulder_attrs = (
                piece.cooldown, piece.last_square,
                piece.first_move, piece.on_intersection,
            )

        # Save captured_pieces length to undo append
        captured_color = None
        captured_len = None
        if saved_final_piece and hasattr(saved_final_piece, 'color') and \
                saved_final_piece.color in board.captured_pieces:
            captured_color = saved_final_piece.color
            captured_len = len(board.captured_pieces[captured_color])

        # --- Apply move (minimal simulation) ---
        if is_boulder_from_intersection:
            board.squares[final.row][final.col].piece = piece
            board.boulder = None
        else:
            if initial.row >= 0 and initial.col >= 0:
                board.squares[initial.row][initial.col].piece = None
            board.squares[final.row][final.col].piece = piece

        if isinstance(piece, Boulder):
            piece.cooldown = 2
            piece.last_square = (initial.row, initial.col) if initial.row >= 0 else None
            piece.first_move = False
            piece.on_intersection = False

        # Handle jump-capture sub-choice: remove the jumped enemy piece
        # if `jump_choice` is a (row, col) target. None = decline (or no
        # jump-capture available).
        saved_jump_target_piece = None
        saved_jump_target_pos = None
        if jump_choice is not None:
            jr, jc = jump_choice
            saved_jump_target_pos = (jr, jc)
            saved_jump_target_piece = board.squares[jr][jc].piece
            board.squares[jr][jc].piece = None

        # Handle promotion. promo_choice (either from the parameter or
        # from turn.promo_choice) carries the chosen form. If the move is
        # to a promotion rank, board.promote replaces the pawn with the
        # chosen piece type.
        saved_promoted_piece = None
        if promo_choice is not None:
            saved_promoted_piece = piece  # save the pawn
            board.promote(piece, turn.to_sq[0], turn.to_sq[1], promo_choice)

        # --- Encode ---
        state = encode_board_for_player(board, opponent, next_turn_num)

        # --- Restore ---
        # Undo promotion (restore pawn)
        if saved_promoted_piece is not None:
            board.squares[turn.to_sq[0]][turn.to_sq[1]].piece = saved_promoted_piece

        # Undo jump-capture (restore the jumped piece)
        if saved_jump_target_pos is not None:
            jr, jc = saved_jump_target_pos
            board.squares[jr][jc].piece = saved_jump_target_piece

        # Undo move
        board.squares[final.row][final.col].piece = saved_final_piece
        if is_boulder_from_intersection:
            board.boulder = saved_board_boulder
        elif initial.row >= 0 and initial.col >= 0:
            board.squares[initial.row][initial.col].piece = saved_initial_piece

        # Restore piece attributes
        piece.moved = saved_piece_moved
        piece.forbidden_square = saved_piece_forbidden

        if saved_boulder_attrs is not None:
            piece.cooldown, piece.last_square, \
                piece.first_move, piece.on_intersection = saved_boulder_attrs

        # Undo captured_pieces append
        if captured_color is not None:
            board.captured_pieces[captured_color] = \
                board.captured_pieces[captured_color][:captured_len]

        board.boulder = saved_board_boulder
        board.last_move = saved_last_move
        board.last_action = saved_last_action

        return state

    def _simulate_transformation(self, board, turn, opponent, next_turn_num):
        """Simulate a transformation with lightweight save/restore."""
        row, col = turn.from_sq
        saved_piece = board.squares[row][col].piece
        saved_last_action = board.last_action

        # Apply transformation
        board.transform_queen(saved_piece, row, col, turn.transform_target)

        # Encode
        state = encode_board_for_player(board, opponent, next_turn_num)

        # Restore original piece
        board.squares[row][col].piece = saved_piece
        board.last_action = saved_last_action

        return state

def play_training_game(network, device, max_turns=1000, epsilon=0.1,
                       manipulation_mode='freeze', engine_kwargs=None):
    """Play a single self-play game and collect training data.

    Args:
        network: ValueNetwork to use for move selection
        device: torch device
        max_turns: maximum turns before stopping
        epsilon: exploration rate
        manipulation_mode: defaults to 'freeze' (v2 rulebook semantics).
            'original' selects v1 (forbidden-square) semantics; other
            modes are variants used for rule research.
        engine_kwargs: optional dict of extra GameEngine kwargs — the
            LGMEF ablation switches (knight_mode, enable_boulder,
            enable_tiny_endgame, enable_manipulation, extra_move_every)
            from experiments.variants. None = full v2 game.

    Returns:
        states: list of encoded board states (numpy arrays)
        outcomes: list of outcomes (1.0 = win, 0.0 = loss) for the player at each state
        game_info: dict with game metadata (incl. a compact 'metrics'
            dict: branching factor, executed turn-type counts, captures
            — the LGMEF per-game measurements)
    """
    engine = GameEngine(max_turns=max_turns, manipulation_mode=manipulation_mode,
                        **(engine_kwargs or {}))
    player = NeuralPlayer(network, device, epsilon)

    states = []
    players_at_state = []  # track whose perspective each state was encoded from
    branching = []         # legal-turn count per ply
    turn_type_counts = {}  # executed turn types (mechanic-usage frequency)

    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        branching.append(len(turns))

        # Record current position
        state = encode_board_for_player(
            engine.board, engine.current_player, engine.turn_number)
        states.append(state)
        players_at_state.append(engine.current_player)

        # The engine enumerates each combination as a fully-specified
        # Turn; player picks one and we execute it directly. No sub-choice
        # method calls are needed.
        turn = player.choose_turn(turns, engine)
        turn_type_counts[turn.turn_type] = \
            turn_type_counts.get(turn.turn_type, 0) + 1
        engine.execute_turn(turn)

    # Finalize and determine outcomes
    game_record = engine.get_game_record()
    winner = engine.winner
    game_info = {
        'winner': winner,
        'loss_reason': engine.loss_reason,
        'total_turns': engine.turn_number,
        'turn_cap': engine.turn_number >= max_turns,
        'metrics': {
            'avg_branching': (sum(branching) / len(branching)) if branching else 0.0,
            'max_branching': max(branching) if branching else 0,
            'turn_type_counts': turn_type_counts,
            'captures': game_record.total_captures,
            'tiny_endgame_activated': game_record.tiny_endgame_activated,
            'repetition_blocks': game_record.repetition_blocks,
            'endgame_blocks': game_record.endgame_blocks,
        },
        'game_record': game_record.to_dict(),
    }

    # For draws/timeouts, return states but no training outcomes.
    # The turn cap is artificial — labeling those positions as 0.5 would
    # teach incorrect evaluations. The states are still available for
    # data collection and analysis.
    if winner is None:
        return states, [], game_info

    outcomes = []
    for p in players_at_state:
        if p == winner:
            outcomes.append(1.0)  # this player won
        else:
            outcomes.append(0.0)  # this player lost

    return states, outcomes, game_info


# ---- Parallel self-play worker -------------------------------------------
#
# Top-level function (NOT closed over training_loop's locals) so it can be
# pickled by multiprocessing.Pool. Workers receive a serialized state_dict
# of the current iteration's network + the play config; each builds its
# own CPU model copy and plays one game. Quality-equivalent to sequential
# self-play (same model, same epsilon, same rules) — only the specific
# positions sampled differ (each worker has independent RNG state).

def _play_one_game_worker(args):
    """Worker entry point for multiprocessing.Pool.

    `args` is a tuple:
      (state_dict, model_config, max_turns, epsilon, manipulation_mode,
       seed, engine_kwargs)

    Returns (states, outcomes, game_info) — identical shape to
    play_training_game()'s return value.
    """
    import random as _random
    import torch as _torch
    (state_dict, model_config, max_turns, epsilon, manipulation_mode,
     seed, engine_kwargs) = args
    if seed is not None:
        _random.seed(seed)
        _torch.manual_seed(seed)
    # Rebuild the network in this worker process and load weights.
    net = ValueNetwork(
        conv_channels=model_config['conv_channels'],
        num_res_blocks=model_config['num_res_blocks'],
        fc_size=model_config['fc_size'],
    )
    net.load_state_dict(state_dict)
    net.eval()
    return play_training_game(
        net, 'cpu', max_turns, epsilon, manipulation_mode, engine_kwargs)


def train_epoch(network, optimizer, dataloader, device):
    """Train the network for one epoch.

    Returns:
        average loss for the epoch
    """
    network.train()
    total_loss = 0.0
    n_batches = 0
    # Pre-create loss module ONCE per epoch instead of per batch
    # (was a small but constant per-batch allocation).
    loss_fn = nn.MSELoss()

    for states, outcomes in dataloader:
        states = states.to(device, non_blocking=True)
        outcomes = outcomes.to(device, non_blocking=True)

        # set_to_none=True saves a memset by leaving grads as None
        # rather than zeroing in-place; PyTorch handles None grads
        # correctly downstream. ~5%% per-step speedup.
        optimizer.zero_grad(set_to_none=True)
        predictions = network(states)
        loss = loss_fn(predictions, outcomes)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


def training_loop(
    n_iterations=50,
    decisive_games=100,
    max_turns=1000,
    epsilon_start=1.0,
    epsilon_end=0.1,
    epsilon_decay_iters=100,
    epochs_per_iteration=10,
    batch_size=256,
    learning_rate=0.001,
    conv_channels=128,
    num_res_blocks=6,
    fc_size=256,
    save_dir='models/',
    resume_from=None,
    device=None,
    manipulation_mode='freeze',
    n_workers=1,
    engine_kwargs=None,
):
    """Main training loop.

    Plays self-play games until a target number of decisive (non-draw) games
    are collected per iteration. Draw/timeout games are discarded — the turn
    cap is artificial and would teach incorrect evaluations.

    Args:
        n_iterations: number of self-play + train cycles
        decisive_games: number of decisive (win/loss) games to collect per iteration
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
        resume_from: path to checkpoint to resume training from
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

    # Initialize or resume network
    if resume_from:
        print(f"Resuming from {resume_from}")
        network = ValueNetwork.load(resume_from, device)
    else:
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

    # Resume-state file paths.
    history_path = os.path.join(save_dir, 'training_history.json')
    optimizer_path = os.path.join(save_dir, 'optimizer_state.pt')

    # Load existing history if resuming
    start_iteration = 0
    if resume_from and os.path.exists(history_path):
        with open(history_path) as f:
            history = json.load(f)
        start_iteration = len(history)
        print(f"Resuming from iteration {start_iteration + 1}")

        # Restore optimizer state (Adam momentum/variance estimates) if a
        # saved optimizer file exists. Without this, resuming resets the
        # optimizer to a cold start, discarding accumulated moments and
        # causing a brief training-instability bump after each resume.
        # Gracefully skip if absent (older runs) or incompatible.
        if os.path.exists(optimizer_path):
            try:
                opt_state = torch.load(optimizer_path, map_location=device)
                optimizer.load_state_dict(opt_state)
                print(f"Restored optimizer state from {optimizer_path}")
            except Exception as exc:  # noqa: BLE001 - defensive: never block resume
                print(f"WARNING: could not restore optimizer state "
                      f"({exc}); continuing with a fresh optimizer.")

    # Buffer size: keep last N positions for training (sliding window)
    max_buffer_size = 500000

    for iteration in range(start_iteration, start_iteration + n_iterations):
        iter_start = time.time()

        # Decay epsilon linearly over a FIXED horizon (epsilon_decay_iters),
        # NOT over (start_iteration + n_iterations). Using the absolute
        # iteration against a fixed denominator makes the epsilon schedule
        # CONTINUOUS across pause/resume — resuming at iteration K always
        # yields the same epsilon regardless of how many iterations this
        # particular run was configured for. Clamped so epsilon never
        # overshoots epsilon_end once past the decay horizon.
        total_iters = start_iteration + n_iterations
        decay_frac = min(iteration / max(epsilon_decay_iters - 1, 1), 1.0)
        epsilon = epsilon_start + (epsilon_end - epsilon_start) * decay_frac

        print(f"\n{'='*60}")
        print(f"Iteration {iteration + 1}/{total_iters} | epsilon={epsilon:.3f}")
        print(f"{'='*60}")

        # --- Self-play phase ---
        print(f"  Playing until {decisive_games} decisive games...", end='', flush=True)
        play_start = time.time()

        iter_states = []
        iter_outcomes = []
        iter_wins = {'white': 0, 'black': 0, 'draw': 0}
        iter_lengths = []
        # Per-game summaries (preserved for analysis — includes draws).
        # Each entry: {winner, loss_reason, total_turns, turn_cap, game_index_in_iter}.
        # Captures BOTH decisive and draw games. Not used for training; used for
        # post-hoc statistical analysis (stall-pattern detection, loss-reason
        # distribution, draw-rate trends, etc.).
        iter_game_summaries = []
        # Loss-reason breakdown for the iteration log line.
        loss_reason_counts = {}

        # Move network to CPU for self-play (avoids GPU contention)
        network_cpu = ValueNetwork(
            conv_channels=conv_channels,
            num_res_blocks=num_res_blocks,
            fc_size=fc_size,
        )
        network_cpu.load_state_dict(network.state_dict())
        network_cpu.eval()

        n_decisive = 0
        total_games = 0
        # Helper to ingest one game's results into the iteration's
        # accumulators. Shared between sequential + parallel paths.
        def _ingest_game(states, outcomes, info):
            nonlocal n_decisive, total_games
            total_games += 1
            iter_lengths.append(info['total_turns'])
            if info['winner'] == 'white':
                iter_wins['white'] += 1
                n_decisive += 1
            elif info['winner'] == 'black':
                iter_wins['black'] += 1
                n_decisive += 1
            else:
                iter_wins['draw'] += 1
            iter_game_summaries.append({
                'game_index_in_iter': total_games - 1,
                'winner': info['winner'],
                'loss_reason': info.get('loss_reason'),
                'total_turns': info['total_turns'],
                'turn_cap': info['turn_cap'],
                # LGMEF per-game measurements (branching factor,
                # mechanic-usage counts, captures) — see
                # play_training_game's game_info['metrics'].
                'metrics': info.get('metrics'),
            })
            reason = info.get('loss_reason') or 'decisive'
            loss_reason_counts[reason] = (
                loss_reason_counts.get(reason, 0) + 1)
            if outcomes:
                iter_states.extend(states)
                iter_outcomes.extend(outcomes)

        if n_workers > 1:
            # Parallel self-play. Each worker plays games concurrently
            # with its own CPU model copy. We use Pool's imap_unordered
            # so results stream back as they finish (rather than waiting
            # for an entire batch). Workers loop until decisive_games
            # met.
            import multiprocessing as _mp
            model_config = {
                'conv_channels': conv_channels,
                'num_res_blocks': num_res_blocks,
                'fc_size': fc_size,
            }
            state_dict = network_cpu.state_dict()
            # Use spawn context for macOS portability (fork copies the
            # whole memory image including the parent's torch state,
            # which can deadlock on MPS-backed models).
            ctx = _mp.get_context('spawn')
            # Per-iteration seed prefix avoids RNG cross-iteration
            # repetition while staying within deterministic-given-seed
            # per game.
            seed_base = (iteration + 1) * 1_000_000
            with ctx.Pool(n_workers) as pool:
                # Submit games in batches; check decisive count after
                # each batch returns. Batch size = workers so the pool
                # is always saturated.
                batch_idx = 0
                while n_decisive < decisive_games:
                    args_list = [
                        (state_dict, model_config, max_turns,
                         epsilon, manipulation_mode,
                         seed_base + batch_idx * n_workers + i,
                         engine_kwargs)
                        for i in range(n_workers)
                    ]
                    batch_idx += 1
                    for states, outcomes, info in pool.imap_unordered(
                            _play_one_game_worker, args_list):
                        _ingest_game(states, outcomes, info)
                        if n_decisive >= decisive_games:
                            break  # graceful stop; let the pool drain
        else:
            # Sequential self-play (original behaviour). Preserved as the
            # default so existing training runs aren't disturbed.
            while n_decisive < decisive_games:
                states, outcomes, info = play_training_game(
                    network_cpu, 'cpu', max_turns, epsilon,
                    manipulation_mode, engine_kwargs)
                _ingest_game(states, outcomes, info)

        play_elapsed = time.time() - play_start
        n_positions = len(iter_states)
        decisive_lengths = [l for l, info_len in zip(iter_lengths, range(total_games))
                           if info_len < total_games]
        print(f" {play_elapsed:.1f}s ({n_positions} positions from {n_decisive} decisive / "
              f"{total_games} total, {total_games/play_elapsed:.1f} games/s)")
        print(f"  Results: W={iter_wins['white']} B={iter_wins['black']} "
              f"D={iter_wins['draw']} | avg_len={sum(iter_lengths)/len(iter_lengths):.0f}")
        # Print loss-reason breakdown (useful for spotting unusual patterns).
        if loss_reason_counts:
            reasons_str = ', '.join(f'{k}={v}' for k, v in sorted(loss_reason_counts.items()))
            print(f"  Loss-reason breakdown: {reasons_str}")

        # Persist per-game summaries for THIS iteration (includes draws).
        # File format: JSON Lines (one game per line). Read by analysis tools
        # via `[json.loads(l) for l in open(path)]`.
        games_dir = os.path.join(save_dir, 'games')
        os.makedirs(games_dir, exist_ok=True)
        games_path = os.path.join(games_dir, f'iter_{iteration + 1:04d}.jsonl')
        with open(games_path, 'w') as f:
            for game_summary in iter_game_summaries:
                f.write(json.dumps(game_summary) + '\n')

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
        # DataLoader speedups (2026-05-31):
        #   - num_workers=2 parallelises batch preparation with the
        #     training step (CPU prepares the next batch while MPS
        #     trains on the current one). 2 is a safe default that
        #     doesn't compete with the parallel-self-play workers (a
        #     separate phase).
        #   - pin_memory=True asks PyTorch to put tensors in
        #     pinned-memory pages, which speeds up the CPU->GPU
        #     transfer. Helpful on CUDA; the cost on MPS-only setups
        #     is negligible.
        #   - persistent_workers=True keeps DataLoader's worker
        #     processes alive across epochs (default tears them down
        #     and re-spawns them every epoch). Saves ~hundreds of
        #     ms per epoch.
        #
        # No quality impact — these only change how training data
        # is moved between CPU and GPU; gradients are unchanged.
        dataloader = DataLoader(
            dataset, batch_size=batch_size, shuffle=True,
            num_workers=2, pin_memory=True, persistent_workers=True)

        avg_loss = 0
        for epoch in range(epochs_per_iteration):
            avg_loss = train_epoch(network, optimizer, dataloader, device)

        train_elapsed = time.time() - train_start
        print(f" {train_elapsed:.1f}s (loss={avg_loss:.4f})")

        # Save checkpoint
        checkpoint_path = os.path.join(save_dir, f'model_iter_{iteration + 1:04d}.pt')
        network.save(checkpoint_path)

        # Save optimizer state alongside, so a later --resume can restore
        # the Adam moments and continue without a cold-start bump. This is
        # a single small file overwritten each iteration (not per-iter).
        torch.save(optimizer.state_dict(), optimizer_path)

        # Record history (incl. per-iteration loss-reason breakdown for
        # post-hoc analysis without re-reading per-game JSONL).
        iter_info = {
            'iteration': iteration + 1,
            'epsilon': epsilon,
            'decisive_games': n_decisive,
            'total_games': total_games,
            'positions': n_positions,
            'buffer_size': len(all_states),
            'loss': avg_loss,
            'white_wins': iter_wins['white'],
            'black_wins': iter_wins['black'],
            'draws': iter_wins['draw'],
            'loss_reason_counts': dict(loss_reason_counts),
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
    parser.add_argument('--decisive-games', type=int, default=100,
                        help='Decisive (non-draw) games to collect per iteration')
    parser.add_argument('--max-turns', type=int, default=1000,
                        help='Max turns per game')
    parser.add_argument('--epsilon-start', type=float, default=1.0,
                        help='Initial exploration rate')
    parser.add_argument('--epsilon-end', type=float, default=0.1,
                        help='Final exploration rate')
    parser.add_argument('--epsilon-decay-iters', type=int, default=100,
                        help='Fixed horizon (in absolute iterations) over '
                             'which epsilon decays from start to end. Using a '
                             'fixed horizon keeps the schedule continuous '
                             'across pause/resume. Default 100.')
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
    parser.add_argument('--resume', type=str, default=None,
                        help='Path to checkpoint to resume training from')
    parser.add_argument('--manipulation-mode', type=str, default='freeze',
                        choices=['original', 'freeze', 'exclusion_zone',
                                 'freeze_invulnerable', 'freeze_invulnerable_no_repeat',
                                 'freeze_no_repeat', 'freeze_invulnerable_cooldown'],
                        help='Manipulation rule variant (default: v2 freeze)')
    parser.add_argument('--workers', type=int, default=1,
                        help='Parallel self-play workers (default 1 = '
                             'sequential, original behaviour). With N > 1, '
                             'self-play games run in parallel via '
                             'multiprocessing.Pool — each worker has its own '
                             'CPU model copy + own RNG. Training-data quality '
                             'is statistically equivalent to sequential '
                             '(same distribution, different specific positions). '
                             'Recommended: 2-4 workers on Apple Silicon for '
                             '~30-50%% wall-clock speedup. Higher values may '
                             'thrash on memory.')

    args = parser.parse_args()

    training_loop(
        n_iterations=args.iterations,
        decisive_games=args.decisive_games,
        max_turns=args.max_turns,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epsilon_decay_iters=args.epsilon_decay_iters,
        epochs_per_iteration=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        conv_channels=args.channels,
        num_res_blocks=args.res_blocks,
        fc_size=args.fc_size,
        save_dir=args.save_dir,
        resume_from=args.resume,
        manipulation_mode=args.manipulation_mode,
        n_workers=args.workers,
    )
