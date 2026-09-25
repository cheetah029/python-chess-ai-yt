"""Phase 4: analyse stored results. Reads raw rows, never recomputes them.

    python3 -m lgref.analysis.run --results results/lgref/phase4-data

Produces the Rule Contribution Profile -- the primary result -- then
summarises it under several stated design objectives, and reports where
those summaries disagree.
"""

import argparse
import collections
import glob
import os

from lgref.analysis import profile as profile_mod
from lgref.analysis.effects import benjamini_hochberg, effect

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASELINE_VARIANT = 'full'


def load_rows(results_dir):
    import pyarrow.parquet as pq

    rows = []
    for path in sorted(glob.glob(os.path.join(results_dir, '**', '*.parquet'),
                                 recursive=True)):
        rows += pq.read_table(path).to_pylist()
    for row in rows:
        # Seeds are encoded as seed*1000 + game so games stay distinct;
        # the analysis needs the SEED GROUP, which is what varies
        # between independent repetitions.
        row['seed_group'] = row.get('seed', 0) // 1000
        for key in ('decisive', 'white_win', 'black_win', 'turn_cap_reached'):
            if isinstance(row.get(key), bool):
                row[key] = 1.0 if row[key] else 0.0
    return rows


def analyse(rows, baseline=BASELINE_VARIANT):
    by_variant = collections.defaultdict(list)
    for row in rows:
        by_variant[row['variant']].append(row)
    if baseline not in by_variant:
        raise SystemExit('no baseline variant {!r} in the data'.format(
            baseline))

    base_rows = by_variant[baseline]
    metrics = sorted(set(profile_mod.DIMENSIONS.values()))
    effects_by_variant = collections.OrderedDict()
    everything = []
    for variant in sorted(by_variant):
        if variant == baseline:
            continue
        found = []
        for metric in metrics:
            got = effect(metric, base_rows, by_variant[variant], variant,
                         seed_key='seed_group')
            if got:
                found.append(got)
        effects_by_variant[variant] = found
        everything += found
    return effects_by_variant, everything


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', required=True)
    parser.add_argument('--baseline', default=BASELINE_VARIANT)
    args = parser.parse_args(argv)

    path = args.results if os.path.isabs(args.results) \
        else os.path.join(REPO, args.results)
    rows = load_rows(path)
    if not rows:
        raise SystemExit('no rows under {}'.format(path))

    seeds = len({r['seed_group'] for r in rows})
    print('=' * 92)
    print('PHASE 4 — ANALYSIS')
    print('=' * 92)
    print('{} games, {} seed groups, baseline `{}`'.format(
        len(rows), seeds, args.baseline))
    if seeds < 3:
        print()
        print('WARNING: fewer than 3 seed groups. Between-seed variance')
        print('cannot be separated from the ablation effect, so nothing')
        print('below should be read as a real effect.')
    print()

    effects_by_variant, everything = analyse(rows, args.baseline)
    survivors = benjamini_hochberg(everything)

    table = profile_mod.build(effects_by_variant)
    print('RULE CONTRIBUTION PROFILE — standardised effect (Cohen\'s d)')
    print('The primary result: in which dimensions is each rule influential?')
    print()
    print('A cell shows d only when the effect survives both checks:')
    print('  seed-dominated = between-seed variance swamps the variant')
    print('  inconclusive   = the bootstrap interval spans zero')
    print('Raw differences and intervals are in the per-effect records;')
    print('they are on a different scale from d and are not shown beside it.')
    print()
    print(profile_mod.format_profile(table))
    print()
    counts = collections.Counter(e.verdict for e in everything)
    absent = sum(1 for row in table.values()
                 for entry in row.values() if entry is None)
    if absent:
        print('{} cells not measured in this run: the metric behind them '
              'is'.format(absent))
        print('not in these rows. Absent, which is not the same as zero.')
    print('cells: {} effect, {} inconclusive, {} seed-dominated'.format(
        counts.get('effect', 0), counts.get('inconclusive', 0),
        counts.get('seed-dominated', 0)))
    print('{} survive multiple-comparison control across the grid.'.format(
        len(survivors)))
    print()

    print('-' * 92)
    print('CONTRIBUTION INDEX UNDER STATED OBJECTIVES')
    print('There is no universal index. Each objective weights different')
    print('dimensions; a rank that moves between them is a finding.')
    print()
    rankings, positions, unstable = profile_mod.rank_sensitivity(table)
    header = '{:<24}'.format('variant') + ''.join(
        '{:>22}'.format(name[:21]) for name in rankings)
    print(header)
    print('-' * len(header))
    for variant in table:
        cells = []
        for name, weights in profile_mod.OBJECTIVES.items():
            got = profile_mod.index(table[variant], weights)
            cells.append('{:>22}'.format('{:+.2f}  (rank {})'.format(
                got['index'], positions[variant][name])))
        print('{:<24}'.format(variant[:23]) + ''.join(cells))

    print()
    if unstable:
        print('RANK INSTABILITY — reported, not smoothed:')
        for variant, places in sorted(unstable.items()):
            print('   {:<24} ranks {} across objectives'.format(
                variant, sorted(places.values())))
    else:
        print('No rule\'s rank moves by 2 or more across objectives.')

    skipped = collections.Counter()
    for variant, row in table.items():
        got = profile_mod.index(row, profile_mod.OBJECTIVES[
            'competitive_balance'])
        for _, why in got['dimensions_skipped']:
            skipped[why] += 1
    if skipped:
        print()
        print('Dimensions excluded from the indices (contributing zero, not')
        print('their point estimate): {}'.format(dict(skipped)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
