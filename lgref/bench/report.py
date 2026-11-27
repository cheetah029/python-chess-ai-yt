"""Tables for Paper A, built from the JSON rows the runners write.

Nothing here computes a score; it aggregates rows, and every aggregate
says what it is over. Means across games carry a bootstrap interval over
GAMES (`lgref.bench.metrics.bootstrap_interval`); spreads over seeds are
reported as (min-max), never as an interval.

    python -m lgref.bench.report groupings docs/paper-a/runs/exp2_dev.json
    python -m lgref.bench.report interventions \
        docs/paper-a/runs/exp1_dev.json
"""

import collections
import json
import sys

from lgref.bench import metrics


def _fmt(value, digits=3):
    if value is None:
        return 'n/a'
    return '{:.{}f}'.format(value, digits)


def _ci(values):
    mean, low, high = metrics.bootstrap_interval(values)
    if mean is None:
        return 'n/a'
    if low is None:
        return _fmt(mean)
    return '{} [{}, {}]'.format(_fmt(mean), _fmt(low), _fmt(high))


# ---- groupings ----------------------------------------------------------

def grouping_summary(rows, key='f1', by='method'):
    """{method (or variant): {game: (mean, min, max) over seeds}}."""
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in rows:
        cells[row[by]][row['game']].append(row[key])
    return {m: {g: metrics.seed_spread(v) for g, v in games.items()}
            for m, games in cells.items()}


def grouping_table(rows, key='f1', baseline='lgref', by='method'):
    summary = grouping_summary(rows, key, by)
    games = sorted({r['game'] for r in rows})
    methods = list(dict.fromkeys(r[by] for r in rows))
    lines = ['| {} | '.format(by) + ' | '.join(games)
             + ' | mean over games [95% CI] | paired vs {} [95% CI] |'
             .format(baseline),
             '|---' * (len(games) + 3) + '|']
    base = {g: summary.get(baseline, {}).get(g, (None,))[0] for g in games}
    for method in methods:
        cells, means = [], {}
        for game in games:
            mean, low, high = summary[method].get(game, (None, None, None))
            means[game] = mean
            if mean is None:
                cells.append('n/a')
            elif low == high:
                cells.append(_fmt(mean))
            else:
                cells.append('{} ({}-{})'.format(_fmt(mean), _fmt(low, 2),
                                                 _fmt(high, 2)))
        diffs = metrics.paired(means, base)
        lines.append('| {} | {} | {} | {} |'.format(
            method, ' | '.join(cells), _ci([means[g] for g in games]),
            '-' if method == baseline else _ci(list(diffs.values()))))
    return '\n'.join(lines)


# ---- interventions -------------------------------------------------------

def _reproduces(row, change_id, kind, ref_touched):
    agree = row['changes_by_ref'][change_id]
    if not row['valid']:
        return False
    if kind == 'no_effect':
        return (set(ref_touched) <= set(row['touched'])
                and agree['changed_cand'] == 0)
    return agree['all_probes']


def intervention_summary(record, procedure='ownership'):
    """Per (game, method): counts, and per change: reproduced, the best
    behavioural F1 among VALID interventions, and its unintended
    changes."""
    out = collections.OrderedDict()
    for row in record['rows']:
        if row['procedure'] != procedure:
            continue
        key = (row['game'], row['method'])
        cell = out.setdefault(key, {'attempted': 0, 'empty': 0,
                                    'valid': 0, 'changes': 0,
                                    'by_change': {}})
        cell['attempted'] += 1
        cell['empty'] += row['empty']
        cell['valid'] += row['valid']
        cell['changes'] += bool(row['valid'] and row['changes'])
        setup = record['setup'][row['game']]['changes']
        for change_id, agree in row['changes_by_ref'].items():
            kind = setup[change_id]['kind']
            entry = cell['by_change'].setdefault(change_id, {
                'kind': kind, 'reproduced': 0, 'best_f1': None,
                'best_unintended': None, 'best_precision': None,
                'best_recall': None})
            if _reproduces(row, change_id, kind,
                           setup[change_id]['touched']):
                entry['reproduced'] += 1
            f1 = agree['f1'] if row['valid'] else None
            if f1 is not None and (entry['best_f1'] is None
                                   or f1 > entry['best_f1']):
                entry.update(best_f1=f1,
                             best_unintended=agree['unintended'],
                             best_precision=agree['precision'],
                             best_recall=agree['recall'])
    return out


def intervention_table(record, procedure='ownership'):
    summary = intervention_summary(record, procedure)
    methods = list(dict.fromkeys(m for _g, m in summary))
    changes = []
    games = [g for g in record['games'] if g in record['setup']]
    for game in games:
        for change_id, info in sorted(
                record['setup'][game]['changes'].items()):
            changes.append((game, change_id, info['kind']))
    targeted = [c for c in changes if c[2] != 'no_effect']
    lines = ['| method | targeted changes reproduced | attempted | '
             'empty | valid rate | valid and changing | no-effect '
             'controls reproduced |',
             '|---|---|---|---|---|---|---|']
    for method in methods:
        cells = [summary[(g, method)] for g in games
                 if (g, method) in summary]
        attempted = sum(c['attempted'] for c in cells)
        valid = sum(c['valid'] for c in cells)
        changing = sum(c['changes'] for c in cells)
        empty = sum(c['empty'] for c in cells)
        got = sum(1 for g, cid, _k in targeted
                  if summary[(g, method)]['by_change'][cid]['reproduced'])
        nulls = [(g, cid) for g, cid, k in changes if k == 'no_effect']
        null_got = sum(1 for g, cid in nulls
                       if summary[(g, method)]['by_change'][cid]
                       ['reproduced'])
        lines.append('| {} | {} / {} | {} | {} | {} | {} | {} / {} |'
                     .format(method, got, len(targeted), attempted, empty,
                             _fmt(valid / float(attempted))
                             if attempted else 'n/a',
                             changing, null_got, len(nulls)))
    lines.append('')
    lines.append('Per change: R = reproduced by some valid intervention '
                 '(count), F1 = best behavioural F1 among valid '
                 'interventions (unintended atoms at that one).')
    lines.append('')
    lines.append('| change | ' + ' | '.join(methods) + ' |')
    lines.append('|---' * (len(methods) + 1) + '|')
    for game, change_id, kind in changes:
        cells = []
        for method in methods:
            entry = summary[(game, method)]['by_change'][change_id]
            mark = 'R{}'.format(entry['reproduced']) \
                if entry['reproduced'] else '-'
            if kind == 'no_effect':
                cells.append(mark)
            else:
                cells.append('{} {} ({})'.format(
                    mark, _fmt(entry['best_f1'], 2),
                    entry['best_unintended']
                    if entry['best_unintended'] is not None else '-'))
        lines.append('| {}:{}{} | {} |'.format(
            game, change_id, ' (no effect)' if kind == 'no_effect' else '',
            ' | '.join(cells)))
    return '\n'.join(lines)


def best_per_change(record, procedure='ownership'):
    """{(game, method, change): row agreement} of the intervention each
    method offers that comes CLOSEST to the reference ablation: the
    valid one with the highest behavioural F1, ties broken by fewer
    differing atoms. None where no valid intervention changes anything.
    Choosing by the reference is deliberate: the question is whether the
    method's grouping CONTAINS an exact ablation, not whether it can
    pick it blind."""
    best = {}
    for row in record['rows']:
        if row['procedure'] != procedure or not row['valid']:
            continue
        for change_id, agree in row['changes_by_ref'].items():
            if agree.get('f1') is None:
                continue
            key = (row['game'], row['method'], change_id)
            rank = (agree['f1'], -(agree.get('differ_total') or 0))
            if key not in best or rank > best[key][0]:
                best[key] = (rank, dict(agree, n_relaxed=row.get(
                    'n_relaxed', 0)))
    return {k: v[1] for k, v in best.items()}


def exactness_table(record, procedure='ownership'):
    """Per method: how many targeted changes it has an EXACT ablation
    for, and the differing and collateral atoms at its closest one."""
    from lgref.bench.methods import METHODS

    best = best_per_change(record, procedure)
    targeted = [(g, cid) for g in record['games'] if g in record['setup']
                for cid, info in sorted(
                    record['setup'][g]['changes'].items())
                if info['kind'] != 'no_effect']
    lines = ['| method | exact (of {}) | none valid and changing | '
             'differing atoms at the closest: legal / terminal+goal / '
             'next, summed over changes | collateral atoms: legal / '
             'terminal+goal / next | closest used a relaxation (exact) |'
             .format(len(targeted)), '|---|---|---|---|---|---|']
    for method in METHODS:
        exact = missing = relaxed = relaxed_exact = 0
        differ = collections.Counter()
        collateral = collections.Counter()
        for game, change_id in targeted:
            agree = best.get((game, method, change_id))
            if agree is None:
                missing += 1
                continue
            exact += bool(agree['exact'])
            differ.update(agree['differ'])
            collateral.update(agree['collateral'])
            if agree['n_relaxed']:
                relaxed += 1
                relaxed_exact += bool(agree['exact'])
        lines.append('| {} | {} | {} | {} / {} / {} | {} / {} / {} | '
                     '{} ({}) |'.format(
                         method, exact, missing, differ['legal'],
                         differ['terminal'] + differ['goal'],
                         differ['next'], collateral['legal'],
                         collateral['terminal'] + collateral['goal'],
                         collateral['next'], relaxed, relaxed_exact))
    return '\n'.join(lines)


def relaxation_usage(record):
    """How often the ownership split MODIFIED another rule (relaxed a
    guard at its call site) instead of deleting it, and how those
    interventions fared."""
    out = collections.defaultdict(collections.Counter)
    for row in record['rows']:
        if row['procedure'] != 'ownership' or row['empty']:
            continue
        cell = out[row['method']]
        cell['non-empty'] += 1
        if row.get('n_relaxed'):
            cell['relaxing'] += 1
            cell['relaxing and valid'] += row['valid']
            cell['relaxing and exact for some change'] += any(
                a.get('exact') for a in row['changes_by_ref'].values())
    return out


def invalid_reasons(record, procedure='ownership'):
    """{method: Counter of the first words of each invalid reason}."""
    out = collections.defaultdict(collections.Counter)
    for row in record['rows']:
        if row['procedure'] == procedure and not row['valid']:
            reason = row['invalid_reason'] or ''
            if reason.startswith('state'):
                reason = reason.split(': ', 1)[1].split(' has ')[1] \
                    if ' has ' in reason else reason
            out[row['method']][reason.split(':')[0][:40]] += 1
    return out


def main(argv=None):
    argv = argv or sys.argv[1:]
    what, path = argv[0], argv[1]
    with open(path) as handle:
        record = json.load(handle)
    if what == 'sensitivity':
        for key in ('f1', 'precision', 'recall', 'shared_recovery'):
            print('\n### {}\n'.format(key))
            print(grouping_table(record['rows'], key, baseline='production',
                                 by='variant'))
    elif what == 'groupings':
        for key in ('f1', 'precision', 'recall', 'shared_recovery',
                    'coverage', 'ari'):
            print('\n### {}\n'.format(key))
            print(grouping_table(record['rows'], key))
    else:
        for procedure in ('ownership', 'delete_group'):
            print('\n### procedure: {}\n'.format(procedure))
            print(intervention_table(record, procedure))
            print('\n#### exactness and collateral damage\n')
            print(exactness_table(record, procedure))
        print('\n### relaxation usage (ownership)\n')
        for method, cell in relaxation_usage(record).items():
            print('- {}: {}'.format(method, ', '.join(
                '{} {}'.format(k, v) for k, v in sorted(cell.items()))))


if __name__ == '__main__':
    main()
