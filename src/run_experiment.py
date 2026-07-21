"""LGMEF experiment entry point (issue #168).

One headless command per (variant, seed) training run, designed for
Kaggle/Colab sessions:

    python src/run_experiment.py --variant no_boulder --seed 2 --iters 50
    python src/run_experiment.py --variant full --check          # gate only

Outputs land in models/experiments/<variant>/seed<k>/:
    experiment.json          — variant spec, seed, CLI config (provenance)
    wellformedness.json      — the pre-run gate report
    model_iter_*.pt, training_history.json, games/iter_*.jsonl
                             — from trainer.training_loop (per-game
                               JSONL rows carry the LGMEF 'metrics'
                               dict: branching factor, mechanic-usage
                               turn-type counts, captures)

The well-formedness gate ALWAYS runs before training and aborts the run
if it fails — a degenerate ablation must never produce data.
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from experiments.variants import VARIANTS, get_variant
from experiments.wellformedness import check_variant


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Run one LGMEF training run for a named variant.')
    parser.add_argument('--variant', required=True, choices=sorted(VARIANTS),
                        help='Named ablation variant (see experiments/variants.py)')
    parser.add_argument('--seed', type=int, default=0,
                        help='Run seed (seeds python/numpy/torch RNGs)')
    parser.add_argument('--iters', type=int, default=50,
                        help='Training iterations')
    parser.add_argument('--decisive-games', type=int, default=100,
                        help='Decisive games per iteration')
    parser.add_argument('--max-turns', type=int, default=1000,
                        help='Turn cap per game')
    parser.add_argument('--workers', type=int, default=4,
                        help='Parallel self-play workers')
    parser.add_argument('--epochs', type=int, default=10,
                        help='Training epochs per iteration')
    parser.add_argument('--save-dir', type=str, default=None,
                        help='Output dir (default models/experiments/'
                             '<variant>/seed<k>/)')
    parser.add_argument('--resume', type=str, default=None,
                        help='Checkpoint to resume from')
    parser.add_argument('--check', action='store_true',
                        help='Run ONLY the well-formedness gate and exit')
    parser.add_argument('--check-games', type=int, default=20,
                        help='Random playouts for the gate')
    args = parser.parse_args(argv)

    spec = get_variant(args.variant)
    save_dir = args.save_dir or os.path.join(
        'models', 'experiments', args.variant, f'seed{args.seed}')
    os.makedirs(save_dir, exist_ok=True)

    # --- Well-formedness gate (always) ---
    print(f'Well-formedness gate: {args.variant} '
          f'({args.check_games} random playouts)...')
    report = check_variant(args.variant, n_games=args.check_games,
                           max_turns=min(args.max_turns, 300),
                           seed=args.seed)
    with open(os.path.join(save_dir, 'wellformedness.json'), 'w') as f:
        json.dump(report, f, indent=2)
    if not report['ok']:
        print('GATE FAILED:')
        for a in report['anomalies']:
            print(f'  - {a}')
        return 1
    decisive = sum(1 for g in report['games'] if g['winner'])
    print(f'  ok: {decisive}/{report["n_games"]} decisive, '
          f'avg branching '
          f'{sum(g["avg_branching"] for g in report["games"]) / len(report["games"]):.1f}')
    if args.check:
        return 0

    # --- Seed everything, record provenance, train ---
    import numpy as np
    import torch
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    with open(os.path.join(save_dir, 'experiment.json'), 'w') as f:
        json.dump({
            'variant': spec.name,
            'description': spec.description,
            'engine_kwargs': spec.engine_kwargs,
            'is_control': spec.is_control,
            'seed': args.seed,
            'config': vars(args),
        }, f, indent=2)

    from trainer import training_loop
    training_loop(
        n_iterations=args.iters,
        decisive_games=args.decisive_games,
        max_turns=args.max_turns,
        epochs_per_iteration=args.epochs,
        save_dir=save_dir,
        resume_from=args.resume,
        n_workers=args.workers,
        engine_kwargs=spec.engine_kwargs,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
