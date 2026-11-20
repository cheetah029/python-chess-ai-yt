"""The validation protocol: tune on dev, decide on validation, report test
(#315).

WHY THIS EXISTS. A reviewer's two points about how identification was
validated:

  1. The resolution was picked by a COVERAGE rule -- the finest one whose
     coverage stays within three points of the coarse end -- and coverage
     is not rule quality: a method can keep every statement in some
     cluster while breaking coherent rules into fragments.
  2. Three games had reference labels, one of them the development game,
     and one held-out game is not evidence about generalisation.

So the choice of granularity is made the way any hyperparameter should
be, and on more games:

  TUNE on the `dev` split only, against reference ARI.
  DECIDE on the `validation` split, once, by a rule fixed in advance: a
      tuned setting replaces the production default only if it scores
      strictly higher there. Validation is never tuned on.
  REPORT the `test` split. Nothing is chosen from it.

THE CANDIDATES ARE SIZE-AWARE. Louvain's resolution is measured against
the graph's total weight, so a raw value tuned on 35-statement games does
not transfer to the 522-statement Royal Chess description (at the
transferred 1.0 it produced an 80-statement cluster holding every piece's
movement). Raw resolutions are therefore REPORTED, as the sensitivity
curve, but are not candidates for production. The candidates are:

  coverage(t)  the coverage rule with tolerance t; t = 0.03 is the
               production default and the BASELINE every candidate is
               compared with
  scaled(k)    k times the coverage-calibrated resolution -- the coverage
               rule's scale, then a tuned step finer or coarser

Nothing here reads Royal Chess's labels (there are none outside the
quarantined designer labels) or names a Royal Chess concept.
"""

import collections
import os

from lgref.identify.clauses import load
from lgref.identify.cluster import (COVERAGE_TOLERANCE, calibrate_resolution,
                                    cluster)
from lgref.identify.graph import ClauseGraph
from lgref.identify.testgames.ground_truth import (SPLITS,
                                                   expected_partition)
from lgref.identify.validate import baseline_name_similarity, pairwise_scores

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, 'testgames')

#: The production default, and the baseline of every comparison.
DEFAULT = ('coverage', COVERAGE_TOLERANCE)

#: Candidates, in the order ties are broken (earlier wins after DEFAULT).
CANDIDATES = (
    [('coverage', t) for t in (0.0, 0.01, 0.03, 0.05, 0.1, 0.2)]
    + [('scaled', k) for k in (0.5, 0.75, 1.25, 1.5, 2.0)])

#: Raw resolutions for the sensitivity curve. Reported, never chosen.
SENSITIVITY_GRID = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0)


def _nodes(game):
    return load(os.path.join(GAME_DIR, game + '.gdl'))


def resolution_for(procedure, graph, seed=0):
    """The resolution a procedure picks for one description."""
    kind, value = procedure
    if kind == 'fixed':
        return value
    if kind == 'coverage':
        return calibrate_resolution(graph, tolerance=value, seed=seed)
    if kind == 'scaled':
        return value * calibrate_resolution(graph, seed=seed)
    raise ValueError('unknown procedure {!r}'.format(procedure))


def _assignment(rules):
    out = collections.defaultdict(set)
    for rule in rules:
        for clause_id in rule.all_clause_ids:
            out[clause_id].add(rule.rule_id)
    return dict(out)


def score(game, procedure, seed=0):
    """Pairwise agreement of one procedure with one game's reference."""
    nodes = _nodes(game)
    graph = ClauseGraph(nodes)
    resolution = resolution_for(procedure, graph, seed=seed)
    rules, dropped = cluster(graph, resolution=resolution, seed=seed)
    scores = pairwise_scores(_assignment(rules),
                             expected_partition(game, nodes),
                             [n.node_id for n in nodes])
    scores.update(game=game, procedure=procedure, resolution=resolution,
                  n_groups=len(rules), n_unclustered=len(dropped))
    return scores


def mean_ari(games, procedure, seed=0):
    return sum(score(g, procedure, seed)['ari'] for g in games) / len(games)


def select(dev_games=None, candidates=CANDIDATES, seed=0):
    """The candidate with the highest mean ARI on the dev games.

    Ties keep the DEFAULT if it is among the tied, else the earliest in
    `candidates`: a change has to earn its place, not win a coin toss.
    """
    dev_games = tuple(dev_games or SPLITS['dev'])
    table = [(procedure, mean_ari(dev_games, procedure, seed))
             for procedure in candidates]
    best = max(value for _p, value in table)
    tied = [p for p, value in table if abs(value - best) < 1e-9]
    chosen = DEFAULT if DEFAULT in tied else tied[0]
    return chosen, table


def decide(chosen, validation_games=None, seed=0):
    """Adopt `chosen` only if it beats DEFAULT on the validation games.

    STRICTLY: a tie keeps the default. This is the protocol's one use of
    the validation split, and its rule is fixed here, in code, before any
    result is seen.
    """
    validation_games = tuple(validation_games or SPLITS['validation'])
    ours = mean_ari(validation_games, chosen, seed)
    base = mean_ari(validation_games, DEFAULT, seed)
    adopted = chosen if (chosen != DEFAULT and ours > base) else DEFAULT
    return adopted, ours, base


def sensitivity(game, grid=SENSITIVITY_GRID, seed=0):
    """ARI against raw resolution, for one game. Descriptive only."""
    return [(r, score(game, ('fixed', r), seed)['ari']) for r in grid]


def failure_modes(game, procedure=DEFAULT, seed=0):
    """How the partition disagrees with the reference, by kind.

      fragmented  a reference rule whose statements land in more than one
                  predicted rule (the method split it)
      merged      a predicted rule whose own statements belong to more
                  than one reference rule (the method joined rules a
                  reader keeps apart, or holds a statement the reference
                  shares between rules)
      dropped     labelled statements in no predicted rule at all
      shared_lost statements the reference puts in two or more rules that
                  the method puts in at most one
    """
    nodes = _nodes(game)
    graph = ClauseGraph(nodes)
    rules, dropped = cluster(
        graph, resolution=resolution_for(procedure, graph, seed), seed=seed)
    expected = expected_partition(game, nodes)
    predicted = _assignment(rules)

    by_reference = collections.defaultdict(set)
    for node_id, names in expected.items():
        for name in names:
            by_reference[name].add(node_id)

    fragmented = {}
    for name, members in sorted(by_reference.items()):
        groups = {g for m in members for g in predicted.get(m, ())}
        if len(groups) > 1:
            fragmented[name] = len(groups)

    merged = {}
    for rule in rules:
        names = collections.Counter(
            name for c in rule.clause_ids for name in expected.get(c, ()))
        distinct = sorted(names)
        if len(distinct) > 1:
            merged[rule.rule_id] = distinct

    labelled = {c for c, names in expected.items() if names}
    shared = {c for c, names in expected.items() if len(names) > 1}
    return {
        'game': game,
        'fragmented': fragmented,
        'merged': merged,
        'dropped': sorted(c for c in labelled if not predicted.get(c)),
        'shared_lost': sorted(c for c in shared
                              if len(predicted.get(c, ())) < 2),
        'n_shared': len(shared),
    }


def baseline(game):
    nodes = _nodes(game)
    return pairwise_scores(baseline_name_similarity(nodes),
                           expected_partition(game, nodes),
                           [n.node_id for n in nodes])


def run(seed=0):
    """The whole protocol, as data: what was chosen, what was adopted,
    and every split's scores under the adopted procedure and the
    default."""
    chosen, table = select(seed=seed)
    adopted, chosen_val, default_val = decide(chosen, seed=seed)
    splits = {}
    for split, games in sorted(SPLITS.items()):
        rows = []
        for game in games:
            ours = score(game, adopted, seed)
            base = score(game, DEFAULT, seed)
            rows.append({'game': game, 'adopted': ours, 'default': base,
                         'name_baseline': baseline(game)['ari']})
        splits[split] = rows
    return {'table': table, 'chosen': chosen, 'adopted': adopted,
            'validation': (chosen_val, default_val), 'splits': splits}


def format_report(result, sensitivities=None, failures=None):
    lines = ['TUNING on dev {} -- mean ARI per candidate'.format(
        list(SPLITS['dev']))]
    for procedure, value in result['table']:
        mark = '  <- default' if procedure == DEFAULT else ''
        lines.append('  {:<10} {:<6} {:.3f}{}'.format(
            procedure[0], procedure[1], value, mark))
    lines.append('chosen on dev: {}'.format(result['chosen']))
    chosen_val, default_val = result['validation']
    lines.append('validation {}: chosen {:.3f} vs default {:.3f} -> '
                 'adopted {}'.format(list(SPLITS['validation']), chosen_val,
                                     default_val, result['adopted']))
    lines.append('')
    lines.append('{:<11} {:<14} {:>8} {:>8} {:>9} {:>7}'.format(
        'split', 'game', 'adopted', 'default', 'name-tok', 'groups'))
    for split in ('dev', 'validation', 'test'):
        for row in result['splits'][split]:
            lines.append('{:<11} {:<14} {:>8.3f} {:>8.3f} {:>9.3f} {:>7}'
                         .format(split, row['game'], row['adopted']['ari'],
                                 row['default']['ari'], row['name_baseline'],
                                 row['adopted']['n_groups']))
    if sensitivities:
        lines.append('')
        lines.append('SENSITIVITY: ARI at raw resolution (descriptive)')
        lines.append('  {:<14} '.format('game') + ' '.join(
            '{:>5}'.format(r) for r in SENSITIVITY_GRID))
        for game, curve in sensitivities.items():
            lines.append('  {:<14} '.format(game) + ' '.join(
                '{:>5.2f}'.format(a) for _r, a in curve))
    if failures:
        lines.append('')
        lines.append('FAILURE MODES under the adopted procedure')
        for f in failures:
            lines.append('  {}: fragmented {} | merged {} | dropped {} | '
                         'shared kept {}/{}'.format(
                             f['game'], f['fragmented'] or '-',
                             {k: len(v) for k, v in f['merged'].items()}
                             or '-', len(f['dropped']),
                             f['n_shared'] - len(f['shared_lost']),
                             f['n_shared']))
    return '\n'.join(lines)


def main():
    result = run()
    sens = {g: sensitivity(g) for split in ('dev', 'validation', 'test')
            for g in SPLITS[split]}
    fails = [failure_modes(g, result['adopted'])
             for split in ('dev', 'validation', 'test')
             for g in SPLITS[split]]
    print(format_report(result, sens, fails))


if __name__ == '__main__':
    main()
