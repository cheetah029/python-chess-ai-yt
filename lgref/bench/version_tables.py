"""Grouping-version tables (#410): every metric, against each baseline
version, generated from the saved Paper A runs and never by hand.

    python -m lgref.bench.version_tables > \\
        docs/paper-a/grouping-version-tables.md

The columns are LGREF's identification versions (`docs/lgref-versions.md`)
played by their representatives, the labelled post-freeze variant, and
the baseline methods. A table with baseline version Vk compares every
column at or above Vk against Vk; the baseline methods and the variant
appear only in the baseline-V0 tables.

Two kinds of cell, both a paired comparison with the baseline:

- **count metrics** (one number per targeted rule, lower is better):
  wins / ties / losses over the rules of a game, at each method's closest
  ablation (`report.closest_ablation`). A rule where a method has no
  valid ablation counts as worse than any value, and two missing values
  tie.
- **continuous metrics** (one rate or score per game): the difference
  column - baseline, with a 95% percentile bootstrap interval. Within a
  game the two sides' units are resampled independently; a total row is
  the mean of the per-game differences with a bootstrap over games
  (`metrics.bootstrap_interval`).

V0 is measured over its 30 draws (#396). A count cell against V0 is the
mean over draws of the wins, ties and losses; a continuous cell pools the
draws' units, so its point estimate is the 30-draw mean.
"""

import collections
import gzip
import json
import os
import sys

from lgref.bench import metrics, report

RUNS = os.path.join(os.path.dirname(__file__), '..', '..', 'docs',
                    'paper-a', 'runs')

#: (major version, representative sub-version, method name, SHA). The
#: doc test checks these against docs/lgref-versions.md.
VERSIONS = (('V0', 'V0.0', 'random_matched', '8d8a0ed'),
            ('V1', 'V1.8', 'lgref', 'ab7b33b'))

#: Labelled post-freeze variants: columns, never versions.
VARIANTS = (('lgref_postfreeze_noterminal',
             'V1.8 with the terminal edge off (#394), post-freeze, not '
             'adopted'),)

BASELINES = ('louvain_hard', 'leiden', 'leiden_hard', 'link_communities',
             'dependency_louvain', 'components', 'name_tokens',
             'singletons', 'one_group')

PROCEDURES = (('ownership', 'ownership (primary)'),
              ('delete_group', 'delete-group'))

SPLITS = ('dev', 'test')

MISSING = None


def _kind(name):
    return lambda ab, _trace: ab['exactness_by_kind'].get(name, 0)


#: (key, title, definition, value(ablation, trace row) -> number). Each
#: is a count per targeted rule; lower is better.
COUNT_METRICS = (
    ('exact', 'Rule changes (exactness), primary',
     'Functional differences in game rules: |atoms(A) Δ atoms(R)| over '
     'all four kinds of atom on the state set S, for the method\'s '
     'closest ablation A of a rule and the reference ablation R. '
     '0 means functionally exact.',
     lambda ab, _t: ab['exactness']),
    ('legal', 'Rule changes in legal moves',
     'The legal-move part of exactness: (state, role, move) triples '
     'legal in exactly one of A and R.', _kind('legal')),
    ('terminal', 'Rule changes in endings',
     'The terminal part of exactness: states that end the game in '
     'exactly one of A and R.', _kind('terminal')),
    ('goal', 'Rule changes in payoffs',
     'The goal part of exactness: (state, role, value) payoffs present '
     'in exactly one of A and R.', _kind('goal')),
    ('next', 'Rule changes in successors (representation-dependent)',
     'The successor part of exactness: (state, joint move, next state) '
     'triples present in exactly one of A and R. Sensitive to state no '
     'rule reads (`results-logic.md`), so it can overstate a difference.',
     _kind('next')),
    ('breakage', 'Breakage (collateral > 0)',
     '1 if the closest ablation changes any atom the reference ablation '
     'does not (collateral > 0), else 0.',
     lambda ab, _t: int(ab['collateral'] > 0)),
    ('fragility', 'Fragility (other rules broken)',
     'The number of other rules whose reference-owned atoms the closest '
     'ablation changes.',
     lambda ab, _t: len(ab.get('rules_broken', ()))),
    ('shortfall', 'Shortfall (atoms of the rule not removed)',
     '|changed(R) − changed(A)|: the part of the rule the closest '
     'ablation failed to remove.',
     lambda ab, _t: ab['shortfall']),
    ('playout', 'Play-out differences',
     'In 20 seeded play-outs of up to 60 plies in which A and R play the '
     'same joint moves (`lgref.bench.traces`): legal-move differences + '
     'terminal disagreements + payoff disagreements. States are never '
     'compared.',
     lambda _ab, t: None if t is None else (
         t['legal_differences'] + t['terminal_differences']
         + t['goal_differences'])),
)

CONTINUOUS_METRICS = (
    ('valid', 'Valid intervention rate',
     'valid / attempted interventions of the method on the game, under '
     'the procedure (`report.intervention_summary`). Higher is better.'),
    ('consistency', 'Consistency across equivalent encodings',
     'Extended BCubed F1 between the method\'s grouping of the original '
     'and of each behaviour-preserving rewrite (Experiment 4: scramble, '
     'reorder, extract, inline, duplicate, permute), averaged over '
     'rewrites and seeds. Higher is better. V0 and the seeded methods '
     'have 5 seeds per rewrite here, not 30 draws.'),
)


# ---- loading -------------------------------------------------------------

def _read(path):
    if path.endswith('.gz'):
        with gzip.open(path, 'rt') as handle:
            return json.load(handle)
    with open(path) as handle:
        return json.load(handle)


def load(runs=RUNS, split='dev'):
    """Everything one split's tables need, from the saved runs:
    {'games', 'setup', 'exp1': {method: [rows per draw]},
     'exp4': {method: rows}, 'traces': {(method, draw): rows}}."""
    def path(name):
        return os.path.join(runs, name)

    exp1 = _read(path('exp1_{}.json'.format(split)))
    draws = _read(path('draws_exp1_{}.json.gz'.format(split)))
    post = _read(path('pf_exp1_{}.json'.format(split)))
    by_method = collections.defaultdict(list)
    for row in exp1['rows'] + post['rows']:
        if row['method'] != 'random_matched':
            by_method[row['method']].append(row)
    per_draw = collections.defaultdict(list)
    for row in draws['rows']:
        per_draw[row['draw']].append(row)
    exp1_rows = {m: [rows] for m, rows in by_method.items()}
    exp1_rows['random_matched'] = [per_draw[d] for d in sorted(per_draw)]

    exp4 = collections.defaultdict(list)
    for name in ('exp4_{}.json', 'pf_exp4_{}.json'):
        for row in _read(path(name.format(split)))['rows']:
            exp4[row['method']].append(row)

    traces = collections.defaultdict(list)
    for name in ('traces_{}.json', 'pf_traces_{}.json'):
        for row in _read(path(name.format(split)))['rows']:
            if row['method'] != 'random_matched':
                traces[(row['method'], None)].append(row)
    drawn = _read(path('traces_draws_{}.json.gz'.format(split)))
    for row in drawn['rows']:
        traces[('random_matched', row['draw'])].append(row)
    return {'games': exp1['games'], 'setup': exp1['setup'],
            'exp1': exp1_rows, 'exp4': dict(exp4),
            'traces': dict(traces), 'n_draws': len(per_draw)}


def targeted(data):
    """[(game, change)] for every targeted rule, in record order."""
    return report._targeted({'games': data['games'],
                             'setup': data['setup']})


# ---- per-rule values -------------------------------------------------------

def rule_values(data, method, procedure, metric):
    """[{(game, change): value or MISSING}], one dict per draw (one dict
    for a method with no draws), at the method's closest ablation."""
    value = dict((m[0], m[3]) for m in COUNT_METRICS)[metric]
    rules = targeted(data)
    out = []
    for index, rows in enumerate(data['exp1'].get(method, [])):
        record = {'rows': rows, 'games': data['games'],
                  'setup': data['setup']}
        closest = report.closest_ablation(record, procedure)
        draw = index if method == 'random_matched' else None
        trace = {(r['game'], r['change']): r
                 for r in data['traces'].get((method, draw), ())
                 if r['procedure'] == procedure}
        cell = {}
        for game, change in rules:
            found = closest.get((game, method, change))
            if found is None:
                cell[(game, change)] = MISSING
                continue
            if metric == 'playout' and (game, change) not in trace:
                raise ValueError(
                    'no play-out of {} {} {} under {}: a missing trace must '
                    'not score as a loss'.format(method, game, change,
                                                 procedure))
            cell[(game, change)] = value(found[1],
                                         trace.get((game, change)))
        out.append(cell)
    return out


def _rank(value):
    return (1, 0) if value is MISSING else (0, value)


def outcome(column, baseline):
    """+1 if the column's value is better (smaller), 0 a tie, -1 worse.
    A missing value is worse than any value; two missing values tie."""
    a, b = _rank(column), _rank(baseline)
    return (a < b) - (a > b)


def wins_ties_losses(columns, baselines, rules):
    """Mean (wins, ties, losses) over the rules given, averaged over
    every (column draw, baseline draw) pair."""
    totals = [0.0, 0.0, 0.0]
    pairs = 0
    for col in columns:
        for base in baselines:
            pairs += 1
            for rule in rules:
                o = outcome(col[rule], base[rule])
                totals[0 if o > 0 else 1 if o == 0 else 2] += 1
    if not pairs:
        return None
    return tuple(t / pairs for t in totals)


# ---- continuous units ------------------------------------------------------

def units(data, method, metric, procedure, game):
    """The per-unit values whose mean is the game's rate or score,
    pooled over draws (V0) or seeds."""
    if metric == 'valid':
        return [int(row['valid']) for rows in data['exp1'].get(method, [])
                for row in rows
                if row['game'] == game and row['procedure'] == procedure]
    return [row['f1'] for row in data['exp4'].get(method, ())
            if row['game'] == game and row['f1'] is not None]


def difference_interval(column, baseline, n_resamples=2000, seed=0,
                        level=0.95):
    """(mean(column) - mean(baseline), low, high): a percentile bootstrap
    with the two samples resampled independently. (None, None, None) if
    either is empty; no interval if both have one unit."""
    import numpy as np
    if not column or not baseline:
        return None, None, None
    a = np.asarray(column, dtype=float)
    b = np.asarray(baseline, dtype=float)
    diff = a.mean() - b.mean()
    if len(a) == 1 and len(b) == 1:
        return float(diff), None, None
    rng = np.random.default_rng(seed)
    resampled = (a[rng.integers(0, len(a), (n_resamples, len(a)))]
                 .mean(axis=1)
                 - b[rng.integers(0, len(b), (n_resamples, len(b)))]
                 .mean(axis=1))
    tail = (1.0 - level) / 2.0
    low, high = np.quantile(resampled, [tail, 1.0 - tail])
    return float(diff), float(low), float(high)


def continuous_games(data, metric):
    if metric == 'valid':
        return [g for g in data['games'] if g in data['setup']]
    return list(data['games'])


# ---- tables --------------------------------------------------------------

def columns_for(baseline_version):
    """The columns of a table whose baseline is `baseline_version`: every
    version at or above it, and, for V0 only, the variants and baselines.
    [(label, method)]."""
    order = [v[0] for v in VERSIONS]
    start = order.index(baseline_version)
    cols = [('{} ({})'.format(v[0], v[1]), v[2])
            for v in VERSIONS[start + 1:]]
    if baseline_version == VERSIONS[0][0]:
        cols += [('{} †'.format(m), m) for m, _label in VARIANTS]
        cols += [(m, m) for m in BASELINES]
    return cols


def _fmt_wtl(cell, draws):
    if cell is None:
        return 'n/a'
    if draws:
        return '{:.1f} / {:.1f} / {:.1f}'.format(*cell)
    return '{:.0f} / {:.0f} / {:.0f}'.format(*cell)


def _fmt_diff(mean, low, high):
    if mean is None:
        return 'n/a'
    if low is None:
        return '{:+.3f}'.format(mean)
    return '{:+.3f} [{:+.3f}, {:+.3f}]'.format(mean, low, high)


def count_table(datasets, metric, procedure, baseline_version):
    base_method = dict((v[0], v[2]) for v in VERSIONS)[baseline_version]
    cols = columns_for(baseline_version)
    lines = ['| game | ' + ' | '.join(c[0] for c in cols) + ' |',
             '|---' * (len(cols) + 1) + '|']
    for split in SPLITS:
        data = datasets[split]
        base = rule_values(data, base_method, procedure, metric)
        draws = len(base) > 1
        values = {m: rule_values(data, m, procedure, metric)
                  for _l, m in cols}
        rules = targeted(data)
        games = list(dict.fromkeys(g for g, _c in rules))
        for game in games + ['**{} total**'.format(split)]:
            subset = ([r for r in rules if r[0] == game] if game in games
                      else rules)
            cells = [_fmt_wtl(wins_ties_losses(values[m], base, subset)
                              if values[m] else None, draws)
                     for _l, m in cols]
            label = ('{} · {}'.format(split, game) if game in games
                     else game)
            lines.append('| {} | '.format(label))
            lines[-1] += ' | '.join(cells) + ' |'
    return '\n'.join(lines)


def continuous_table(datasets, metric, procedure, baseline_version):
    base_method = dict((v[0], v[2]) for v in VERSIONS)[baseline_version]
    cols = columns_for(baseline_version)
    lines = ['| game | ' + ' | '.join(c[0] for c in cols) + ' |',
             '|---' * (len(cols) + 1) + '|']
    for split in SPLITS:
        data = datasets[split]
        games = continuous_games(data, metric)
        per_game = collections.defaultdict(list)
        for game in games:
            base = units(data, base_method, metric, procedure, game)
            cells = []
            for _label, method in cols:
                got = difference_interval(
                    units(data, method, metric, procedure, game), base)
                per_game[method].append(got[0])
                cells.append(_fmt_diff(*got))
            lines.append('| {} · {} | '.format(split, game)
                         + ' | '.join(cells) + ' |')
        cells = [_fmt_diff(*metrics.bootstrap_interval(per_game[m]))
                 for _l, m in cols]
        lines.append('| **{} total** | '.format(split)
                     + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


HEADER = """# Paper A: grouping-version tables

Issue #410. **Generated by `python -m lgref.bench.version_tables` from
the saved runs in `docs/paper-a/runs/`. Do not edit by hand**:
`lgref/tests/test_paper_a_version_tables.py` regenerates this file and
fails if it differs.

Built like the player tables (`docs/experiments/version-win-rates.md`),
for LGREF's identification versions (`docs/lgref-versions.md`).

- **One section per metric**, and in it one table per baseline version
  and intervention procedure. Objective metrics only; the subjective
  ones (BCubed against the sheets, the blind review) are in
  `results-dev.md` and `results-test.md`.
- **Columns.** A table with baseline Vk has a column for every version
  above Vk, played by its representative. The baseline-V0 tables also
  have the labelled post-freeze variant (†) and the baseline methods
  (`docs/lgref-versions.md`, "Baselines are not versions"). The
  baseline-V1 tables have no columns yet, because V1 is the latest
  version; they fill in when V2 exists.
- **Rows** are games, development (`dev`) and test (`test`) apart, each
  set with its total. Count metrics have a row per game with targeted
  rules (5 dev, 10 test); continuous metrics a row per game measured.
- **Count cells: wins / ties / losses over rules**, column against
  baseline, at each method's closest ablation (the valid, non-empty,
  changing intervention with the smallest exactness; ties by smaller
  collateral, then group order). A win is a smaller value. A rule with
  no valid ablation is worse than any value, and two such rules tie.
- **Continuous cells: column − baseline, with a 95% interval.** Within
  a game: a percentile bootstrap (2000 resamples, seed 0) with each
  side's units resampled independently. Total rows: the mean of the
  per-game differences, with a bootstrap over games.
- **V0 is the mean over its 30 draws** (#396). Against V0, a count cell
  is the mean over draws of wins / ties / losses (one decimal), and a
  continuous cell pools the draws' units. Play-outs were run for every
  draw (`traces_draws_*.json.gz`; draw 0 equals the published single
  draw) and for the post-freeze variant (`pf_traces_*.json`).
  Consistency is the exception: its Experiment 4 runs have 5 seeds, not
  30 draws.
- † `lgref_postfreeze_noterminal`: {variant}.
"""


def build(runs=RUNS):
    datasets = {split: load(runs, split) for split in SPLITS}
    out = [HEADER.format(variant=VARIANTS[0][1])]
    n = 0
    for key, title, definition, _fn in COUNT_METRICS:
        n += 1
        out.append('## Metric {}: {}\n\n{}\n'.format(n, title, definition))
        for procedure, label in PROCEDURES:
            out.append('### Baseline V0 · {}\n'.format(label))
            out.append(count_table(datasets, key, procedure, 'V0') + '\n')
        out.append(_empty_baselines())
    for key, title, definition in CONTINUOUS_METRICS:
        n += 1
        out.append('## Metric {}: {}\n\n{}\n'.format(n, title, definition))
        procedures = PROCEDURES if key == 'valid' else (
            ('ownership', 'groupings (no procedure)'),)
        for procedure, label in procedures:
            out.append('### Baseline V0 · {}\n'.format(label))
            out.append(continuous_table(datasets, key, procedure, 'V0')
                       + '\n')
        out.append(_empty_baselines())
    return '\n'.join(out)


def _empty_baselines():
    lines = []
    for version in VERSIONS[1:]:
        if not columns_for(version[0]):
            lines.append('### Baseline {}\n\nNo columns: no version above '
                         '{} exists yet.\n'.format(version[0], version[0]))
    return '\n'.join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    sys.stdout.write(build(argv[0] if argv else RUNS))


if __name__ == '__main__':
    main()
