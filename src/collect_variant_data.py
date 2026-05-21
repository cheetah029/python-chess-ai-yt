"""
Collect game data from trained AI models for each manipulation variant.

Plays N decisive games with each variant's trained model and saves
the game records as JSON for comparison analysis.

Usage:
    python3 collect_variant_data.py --games 50 --max-turns 1000
"""

import sys
import os
import json
import random
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from engine import GameEngine
from network import ValueNetwork
from trainer import NeuralPlayer, play_training_game


def collect_games(model_path, manipulation_mode, n_games, max_turns, epsilon=0.05):
    """Play n_games decisive games and return game records.

    Args:
        model_path: path to trained model checkpoint
        manipulation_mode: 'original', 'freeze', or 'exclusion_zone'
        n_games: number of decisive (non-draw) games to collect
        max_turns: max turns per game
        epsilon: exploration rate (low = mostly network-guided)

    Returns:
        list of game record dicts
    """
    network = ValueNetwork.load(model_path, 'cpu')
    network.eval()

    records = []
    draw_records = []
    total_played = 0

    while len(records) < n_games:
        states, outcomes, info = play_training_game(
            network, 'cpu', max_turns, epsilon, manipulation_mode)
        total_played += 1

        if info['winner'] is not None:
            records.append(info['game_record'])
            print(f"  [{manipulation_mode}] Game {len(records)}/{n_games}: "
                  f"winner={info['winner']}, turns={info['total_turns']}", flush=True)
        else:
            draw_records.append(info['game_record'])
            print(f"  [{manipulation_mode}] Draw (game {total_played}, "
                  f"{info['total_turns']} turns) — not counted toward target", flush=True)

    return records, draw_records, total_played


def main():
    parser = argparse.ArgumentParser(description='Collect variant comparison data')
    parser.add_argument('--games', type=int, default=50,
                        help='Number of decisive games per variant')
    parser.add_argument('--max-turns', type=int, default=1000,
                        help='Max turns per game')
    parser.add_argument('--epsilon', type=float, default=0.05,
                        help='Exploration rate')
    parser.add_argument('--output-dir', type=str, default='data',
                        help='Output directory for JSON files')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    variants = {
        'original': 'models/variant_original/model_final.pt',
        'freeze': 'models/variant_freeze/model_final.pt',
        'exclusion_zone': 'models/variant_exclusion_zone/model_final.pt',
        'freeze_invulnerable': 'models/variant_freeze_invulnerable/model_final.pt',
        'freeze_invulnerable_no_repeat': 'models/variant_freeze_invulnerable_no_repeat/model_final.pt',
    }

    for mode, model_path in variants.items():
        if not os.path.exists(model_path):
            print(f"Skipping {mode}: model not found at {model_path}")
            continue

        print(f"\n{'='*60}")
        print(f"Collecting {args.games} games for: {mode}")
        print(f"{'='*60}")

        start = time.time()
        records, draw_records, total = collect_games(
            model_path, mode, args.games, args.max_turns, args.epsilon)
        elapsed = time.time() - start

        output_path = os.path.join(args.output_dir, f'variant_{mode}_{args.games}_games.json')
        with open(output_path, 'w') as f:
            json.dump(records, f, indent=2)

        # Save draw records separately if any occurred
        if draw_records:
            draw_path = os.path.join(args.output_dir, f'variant_{mode}_{args.games}_draws.json')
            with open(draw_path, 'w') as f:
                json.dump(draw_records, f, indent=2)

        n_draws = len(draw_records)
        print(f"\n  {mode}: {args.games} decisive + {n_draws} draws = {total} total")
        print(f"  Time: {elapsed:.1f}s ({total/elapsed:.1f} games/s)")
        print(f"  Saved to {output_path}")
        if draw_records:
            print(f"  Draws saved to {draw_path}")


if __name__ == '__main__':
    main()
