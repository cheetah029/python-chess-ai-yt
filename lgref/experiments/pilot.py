"""Run the Phase 3 pilot and decide whether the sweep is worth starting.

    python3 -m lgref.experiments.pilot --config lgref/config/phase3_pilot.yaml

Reports the DECISIVE-GAME RATE per variant before anything else. This
game has no draw condition, so a game stopped by the turn cap is
censored rather than drawn, and a win rate over censored games measures
the cap (#204). A variant whose games stop finishing is named as
unusable instead of contributing a number that looks fine.

Writes one row per game to Parquet -- raw records, never only
aggregates -- with a run manifest and the measured cost, and projects
that cost to the full sweep so an overrun is visible before it is paid.
"""

import argparse
import concurrent.futures
import os
import sys
import time

from lgref.core.config import load_config
from lgref.core.cost import CostTracker
from lgref.core.manifest import DEFAULT_CODE_INPUTS, RunManifest, code_hash
from lgref.core.storage import ParquetWriter
from lgref.experiments.metrics import require_outcome_safe_cap
from lgref.experiments.sweep import (decisive_report, format_decisive,
                                     play_one, require_usable)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _job(args):
    variant, seed, max_turns, sample_every = args
    row, _ = play_one(variant, seed, max_turns, sample_every)
    return row


def run(config, run_id=None, out_root=None):
    measurement = config['measurement']
    max_turns = config['max_turns']
    # Refuses a cap where games do not finish, rather than producing a
    # plausible-looking win rate over censored games.
    require_outcome_safe_cap(max_turns)

    run_id = run_id or 'pilot-{}'.format(time.strftime('%Y%m%dT%H%M%S'))
    out_root = out_root or os.path.join(REPO, 'results', 'lgref')
    out_dir = os.path.join(out_root, run_id)

    manifest = RunManifest.start(
        run_id=run_id, config=config, seed=config.get('seed', 0),
        out_dir=out_dir, repo_root=REPO,
        code_inputs=tuple(DEFAULT_CODE_INPUTS) + ('lgref/experiments',))

    workers = max(config.get('cost', {}).get('n_workers', 1), 1)
    tracker = CostTracker(n_workers=workers,
                          venue=config.get('cost', {}).get('venue', 'local'))

    jobs = [(variant, seed * 1000 + game, max_turns,
             measurement.get('position_sample_every', 10))
            for variant in measurement['variants']
            for seed in measurement.get('seeds', [0])
            for game in range(measurement['games_per_variant'])]

    writer = ParquetWriter(out_dir, run_id,
                           rows_per_part=config.get('storage', {})
                           .get('rows_per_part', 2000))
    rows = [None] * len(jobs)
    started = time.time()
    try:
        with tracker:
            if workers <= 1:
                for index, job in enumerate(jobs):
                    rows[index] = _job(job)
                    _tick(index + 1, len(jobs), rows[index], started)
            else:
                with concurrent.futures.ProcessPoolExecutor(
                        max_workers=workers) as pool:
                    futures = {pool.submit(_job, job): i
                               for i, job in enumerate(jobs)}
                    done = 0
                    for future in concurrent.futures.as_completed(futures):
                        index = futures[future]
                        # By SUBMISSION index: collecting by completion
                        # order would make the stored rows depend on
                        # scheduling, the same defect class as the
                        # hash-order dependence in clustering.
                        rows[index] = future.result()
                        done += 1
                        _tick(done, len(jobs), rows[index], started)
            writer.extend([r for r in rows if r])
            tracker.add_units(len(jobs), unit_name='game')
    except Exception as exc:                       # noqa: BLE001
        manifest.finish(status='error', error=repr(exc),
                        cost=tracker.as_dict())
        raise
    finally:
        writer.close()

    report = decisive_report(rows)
    unusable = require_usable(report)
    manifest.finish(status='ok', cost=tracker.as_dict(),
                    metrics={'games': len(rows),
                             'decisive_report': report,
                             'unusable_variants': unusable})
    return rows, report, tracker, out_dir


def _tick(done, total, row, started):
    elapsed = time.time() - started
    print('[pilot] {:>3}/{} {:<22} {:<8} {:>4} turns   ~{:.1f} min left'
          .format(done, total, row['variant'], row['winner'] or 'CENSORED',
                  row['total_turns'],
                  (elapsed / done) * (total - done) / 60),
          file=sys.stderr, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-id', default=None)
    args = parser.parse_args(argv)

    path = args.config if os.path.isabs(args.config) \
        else os.path.join(REPO, args.config)
    config = load_config(path)
    rows, report, tracker, out_dir = run(config, run_id=args.run_id)

    print('=' * 92)
    print('PHASE 3 PILOT — decisive-game rate')
    print('=' * 92)
    print()
    print('This game has no draw condition, so an unfinished game is')
    print('CENSORED, not drawn. A win rate over censored games measures the')
    print('turn cap, not the rules (#204) -- hence this table before any')
    print('win rate.')
    print()
    print(format_decisive(report))
    print()

    unusable = require_usable(report)
    if unusable:
        print('NOT USABLE for outcome metrics: {}'.format(
            ', '.join(unusable)))
        print('Their structural metrics remain valid; their win rates must')
        print('not be reported.')
    else:
        print('All variants finish their games: outcome metrics are usable.')

    cost = tracker.as_dict()
    projection = config.get('projection', {})
    total = (len(config['measurement']['variants'])
             * projection.get('sweep_games_per_variant', 60)
             * projection.get('sweep_seeds', 3))
    print()
    print('-' * 92)
    print('rows written : {} (Parquet, accumulate-only) -> {}'.format(
        len(rows), out_dir))
    print('cost         : {:.1f}s wall, {:.4f} core-hours, {} worker(s)'
          .format(cost['wall_clock_s'], cost['core_hours'],
                  cost['n_workers']))
    projected = tracker.project(total)
    if projected:
        print('full sweep   : {} games -> {:.2f} core-hours, '
              '{:.1f} wall-hours at this parallelism'.format(
                  total, projected['core_hours'],
                  projected['wall_hours_at_current_parallelism']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
