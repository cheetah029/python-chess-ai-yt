"""Run the Phase 1 gate and record it as an experiment.

    python3 -m lgref.identify.gate --config lgref/config/phase1_gate.yaml

Reproducible from one config plus a seed, per the project's engineering
rules: the description path, the clustering resolution and the probe
budget are stated in the config rather than defaulted in code. Every run
writes a manifest (git SHA and dirty flag, config hash, seed, wall-clock,
machine, engine hash) and prints its measured cost at the end.

Reports ACCUMULATE. Each run writes `phase1_<run_id>.txt`; nothing is
overwritten, so an earlier gate result stays readable next to a later
one and a regression is visible rather than erased.
"""

import argparse
import os
import sys
import time

from lgref.core.config import load_config
from lgref.core.cost import CostTracker
from lgref.core.manifest import RunManifest
from lgref.identify.report import build_report

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..'))


def _resolve(path):
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def run(config, run_id=None):
    """Build the gate report, with a manifest and measured cost."""
    ident = config['identification']
    seed = config.get('seed', 0)
    # No 'phase1-' prefix: the report file is already named
    # phase1_<run_id>.txt, and the default produced
    # phase1_phase1-20260922T173210.txt.
    run_id = run_id or time.strftime('%Y%m%dT%H%M%S')
    report_dir = _resolve(config.get('report_dir', 'lgref/report'))

    from lgref.core.manifest import DEFAULT_CODE_INPUTS
    manifest = RunManifest.start(
        run_id=run_id, config=config, seed=seed,
        out_dir=os.path.join(report_dir, run_id), repo_root=REPO_ROOT,
        # The description is an input to this run as much as the code is,
        # and it changes independently of it.
        code_inputs=tuple(DEFAULT_CODE_INPUTS) + (ident['gdl'],))

    tracker = CostTracker(
        n_workers=config.get('cost', {}).get('n_workers', 1),
        venue=config.get('cost', {}).get('venue', 'local'))

    def progress(stage, index, total, seconds):
        """One line per cluster, to stderr, as the sweep runs.

        The report itself goes to stdout, so progress must not pollute
        it. A silent multi-minute run is indistinguishable from a hung
        one; after the first cluster this gives a measured rate and a
        projected finish instead of a guess.
        """
        if index == 0:
            # Restart the clock here. The baseline probe is a one-off
            # that costs as much as a cluster, so including it in the
            # rate makes the first few projections wildly pessimistic.
            sweep_started[0] = time.monotonic()
            print('[gate] baseline in {:.1f}s; {} clusters to check'
                  .format(seconds, total), file=sys.stderr, flush=True)
            return
        # Completions, not positions, when the sweep runs in parallel --
        # and the rate has to account for the probes still in flight.
        # Dividing elapsed by completions alone treats 8 concurrent
        # workers as one, so the first projections read several times
        # too long and then collapse as a batch lands together.
        done = time.monotonic() - sweep_started[0]
        in_flight = min(workers, total - index)
        rate = done / max(index, 1)
        remaining = rate * max(total - index - in_flight, 0) + (
            rate if in_flight else 0)
        print('[gate] {:>3}/{} {:<13} {:5.1f}s   ~{:.1f} min left'
              .format(index, total, stage, seconds, remaining / 60.0),
              file=sys.stderr, flush=True)

    sweep_started = [time.monotonic()]
    workers = max(config.get('cost', {}).get('n_workers', 1), 1)
    try:
        with tracker:
            text = build_report(
                _resolve(ident['gdl']),
                ident['games'],
                _resolve(ident['game_dir']),
                resolution=ident.get('resolution', 1.0),
                seed=seed,
                probe_plies=ident.get('probe_plies', 20),
                probe_seeds=tuple(range(ident.get('probe_seeds', 10))),
                progress=progress,
                n_workers=config.get('cost', {}).get('n_workers', 1))
            tracker.add_units(1, unit_name='gate_run')
    except Exception as exc:                      # noqa: BLE001 - recorded
        manifest.finish(status='error', error=repr(exc),
                        cost=tracker.as_dict())
        raise

    out_path = os.path.join(report_dir, 'phase1_{}.txt'.format(run_id))
    with open(out_path, 'w') as handle:
        handle.write(text + '\n')

    manifest.finish(status='ok', cost=tracker.as_dict(),
                    metrics={'report': out_path})
    return text, out_path, tracker


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-id', default=None)
    args = parser.parse_args(argv)

    config = load_config(_resolve(args.config))
    text, out_path, tracker = run(config, run_id=args.run_id)

    print(text)
    print()
    print('-' * 72)
    print('report: {}'.format(out_path))
    cost = tracker.as_dict()
    print('cost:   {:.1f}s wall, {:.4f} core-hours, {} worker(s), venue {}'
          .format(cost['wall_clock_s'], cost['core_hours'],
                  cost['n_workers'], cost['venue']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
