"""Collect test games from the fine-tuned (1000-turn cap) model."""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from collect_variant_data import collect_games


def main():
    model_path = '../models/original_finetuned_1000/model_final.pt'
    n_games = 100
    max_turns = 1000
    epsilon = 0.05
    output_dir = '../data'

    total_decisive = 0
    total_draws = 0
    total_played = 0

    for batch in range(1, 11):
        print(f"\n{'='*60}")
        print(f"Batch {batch}/10: Collecting {n_games} decisive games")
        print(f"{'='*60}")

        start = time.time()
        records, draw_records, played = collect_games(
            model_path, 'original', n_games, max_turns, epsilon)
        elapsed = time.time() - start

        output_path = os.path.join(output_dir, f'finetuned_1000_100_games_batch{batch}.json')
        with open(output_path, 'w') as f:
            json.dump(records, f, indent=2)

        if draw_records:
            draw_path = os.path.join(output_dir, f'finetuned_1000_100_draws_batch{batch}.json')
            with open(draw_path, 'w') as f:
                json.dump(draw_records, f, indent=2)
            print(f"  Draws saved to {draw_path}")

        total_decisive += len(records)
        total_draws += len(draw_records)
        total_played += played

        print(f"  Batch {batch}: {n_games} decisive + {len(draw_records)} draws = {played} total")
        print(f"  Time: {elapsed:.1f}s ({played/elapsed:.1f} games/s)")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_decisive} decisive + {total_draws} draws = {total_played} games")
    print(f"Draw rate: {total_draws/total_played*100:.2f}%")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
