"""
Self-play runner with parallel execution and data collection.

Usage:
    python selfplay.py --games 1000 --workers 8 --output data/games/
"""

import json
import os
import sys
import time
import argparse
import multiprocessing
from engine import GameEngine
from players import RandomPlayer


def play_one_game(args):
    """Play a single game and return the game record dict.
    Called by multiprocessing workers."""
    game_id, max_turns, seed = args

    # Seed each game independently for reproducibility
    import random
    random.seed(seed)

    engine = GameEngine(max_turns=max_turns)
    white = RandomPlayer()
    black = RandomPlayer()

    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()

        if not turns:
            # No legal turns — should be caught by has_legal_moves in _next_turn
            # but handle defensively
            break

        player = white if engine.current_player == 'white' else black
        turn = player.choose_turn(turns)

        # Handle secondary choices
        jump_choice = None
        if turn.jump_capture_targets:
            jump_choice = player.choose_jump_capture(turn.jump_capture_targets)

        promo_choice = None
        if turn.promotion_options:
            promo_choice = player.choose_promotion(turn.promotion_options)

        # Record branching factor before executing
        n_turns = len(turns)
        record = engine.execute_turn(turn, jump_choice, promo_choice)
        record.legal_turn_count = n_turns
        # Update the stored dict in game_record (last entry)
        engine.game_record.turns[-1]['legal_turn_count'] = n_turns

    game_record = engine.get_game_record(game_id=game_id)
    return game_record.to_dict()


def run_batch(n_games, workers, max_turns, output_dir, base_seed=42):
    """Run a batch of self-play games in parallel.

    Args:
        n_games: Number of games to play
        workers: Number of parallel workers
        max_turns: Maximum turns per game before declaring timeout
        output_dir: Directory to save results
        base_seed: Base random seed for reproducibility
    """
    os.makedirs(output_dir, exist_ok=True)

    # Prepare game arguments
    game_args = [(i, max_turns, base_seed + i) for i in range(n_games)]

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'games_{timestamp}_{n_games}.jsonl')

    print(f"Running {n_games} games with {workers} workers (max {max_turns} turns each)")
    print(f"Output: {output_file}")
    print()

    start_time = time.time()
    completed = 0
    results_summary = {
        'white_wins': 0, 'black_wins': 0, 'turn_cap': 0,
        'royals_captured': 0, 'no_legal_moves': 0,
        'total_turns': 0, 'total_captures': 0,
        'tiny_endgame_activations': 0,
        'game_lengths': [],
    }

    with open(output_file, 'w') as f:
        if workers <= 1:
            # Single-process mode (easier to debug)
            for args in game_args:
                result = play_one_game(args)
                f.write(json.dumps(result) + '\n')
                completed += 1
                _update_summary(results_summary, result)
                _print_progress(completed, n_games, start_time, results_summary)
        else:
            # Parallel mode
            with multiprocessing.Pool(workers) as pool:
                for result in pool.imap_unordered(play_one_game, game_args, chunksize=max(1, n_games // (workers * 10))):
                    f.write(json.dumps(result) + '\n')
                    completed += 1
                    _update_summary(results_summary, result)
                    if completed % max(1, n_games // 20) == 0 or completed == n_games:
                        _print_progress(completed, n_games, start_time, results_summary)

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"COMPLETE: {n_games} games in {elapsed:.1f}s ({n_games/elapsed:.1f} games/sec)")
    print(f"Output: {output_file}")
    _print_final_summary(results_summary, n_games, elapsed)

    return output_file


def _update_summary(summary, result):
    """Update running summary statistics."""
    if result['winner'] == 'white':
        summary['white_wins'] += 1
    elif result['winner'] == 'black':
        summary['black_wins'] += 1
    else:
        summary['turn_cap'] += 1

    if result['loss_reason'] == 'royals_captured':
        summary['royals_captured'] += 1
    elif result['loss_reason'] == 'no_legal_moves':
        summary['no_legal_moves'] += 1

    summary['total_turns'] += result['total_turns']
    summary['total_captures'] += result['total_captures']
    summary['game_lengths'].append(result['total_turns'])

    if result.get('tiny_endgame_activated'):
        summary['tiny_endgame_activations'] += 1


def _print_progress(completed, total, start_time, summary):
    """Print progress bar and running statistics."""
    elapsed = time.time() - start_time
    rate = completed / elapsed if elapsed > 0 else 0
    eta = (total - completed) / rate if rate > 0 else 0
    pct = completed / total * 100

    avg_len = summary['total_turns'] / completed if completed > 0 else 0
    w_pct = summary['white_wins'] / completed * 100 if completed > 0 else 0
    b_pct = summary['black_wins'] / completed * 100 if completed > 0 else 0

    print(f"\r  [{completed:>{len(str(total))}}/{total}] {pct:5.1f}% | "
          f"{rate:.1f} games/s | ETA {eta:.0f}s | "
          f"W:{w_pct:.1f}% B:{b_pct:.1f}% Cap:{summary['turn_cap']} | "
          f"avg_len:{avg_len:.0f}",
          end='', flush=True)


def _print_final_summary(summary, n_games, elapsed):
    """Print final statistics."""
    print()
    print(f"  White wins:  {summary['white_wins']:>6} ({summary['white_wins']/n_games*100:.1f}%)")
    print(f"  Black wins:  {summary['black_wins']:>6} ({summary['black_wins']/n_games*100:.1f}%)")
    print(f"  Turn cap:    {summary['turn_cap']:>6} ({summary['turn_cap']/n_games*100:.1f}%)")
    print()
    print(f"  Loss by royals captured: {summary['royals_captured']}")
    print(f"  Loss by no legal moves:  {summary['no_legal_moves']}")
    print()

    avg_len = summary['total_turns'] / n_games if n_games > 0 else 0
    lengths = sorted(summary['game_lengths'])
    median_len = lengths[len(lengths)//2] if lengths else 0
    min_len = lengths[0] if lengths else 0
    max_len = lengths[-1] if lengths else 0

    print(f"  Game length: avg={avg_len:.0f} median={median_len} min={min_len} max={max_len}")
    print(f"  Total captures: {summary['total_captures']}")
    print(f"  Tiny endgame activations: {summary['tiny_endgame_activations']}")
    print(f"  Avg captures/game: {summary['total_captures']/n_games:.1f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run self-play games for data collection')
    parser.add_argument('--games', type=int, default=1000, help='Number of games to play')
    parser.add_argument('--workers', type=int, default=None, help='Number of parallel workers (default: CPU count)')
    parser.add_argument('--max-turns', type=int, default=1000, help='Maximum turns per game')
    parser.add_argument('--output', type=str, default='data/games/', help='Output directory')
    parser.add_argument('--seed', type=int, default=42, help='Base random seed')
    args = parser.parse_args()

    workers = args.workers or multiprocessing.cpu_count()

    run_batch(
        n_games=args.games,
        workers=workers,
        max_turns=args.max_turns,
        output_dir=args.output,
        base_seed=args.seed,
    )
