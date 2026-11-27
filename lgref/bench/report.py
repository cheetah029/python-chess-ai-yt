"""Tables for Paper A, built from the JSON rows the runners write.

Nothing here computes a score; it aggregates rows, and every aggregate
says what it is over. Means across games carry a bootstrap interval over
GAMES (`lgref.bench.metrics.bootstrap_interval`); spreads over seeds are
reported as (min-max), never as an interval.

    python -m lgref.bench.report groupings docs/paper-a/results/exp2_dev.json
    python -m lgref.bench.report interventions \
        docs/paper-a/results/exp1_dev.json
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
    for game in record['games']:
        for change_id, info in sorted(
                record['setup'][game]['changes'].items()):
            changes.append((game, change_id, info['kind']))
    targeted = [c for c in changes if c[2] != 'no_effect']
    lines = ['| method | targeted changes reproduced | attempted | '
             'empty | valid rate | valid and changing | no-effect '
             'controls reproduced |',
             '|---|---|---|---|---|---|---|']
    for method in methods:
        cells = [summary[(g, method)] for g in record['games']
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


if __name__ == '__main__':
    main()
