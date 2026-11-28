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


def relaxation_usage(record):
    """How often the ownership split MODIFIED another rule (relaxed a
    guard at its call site) instead of deleting it, and how those
    interventions fared. "Exact" counts only TARGETED changes, and only
    for valid interventions that change something: an inert one is
    trivially "exact" for a no-effect control."""
    out = collections.OrderedDict()
    for method in _methods_in(record):
        out[method] = collections.Counter()
    for row in record['rows']:
        if row['procedure'] != 'ownership' or row['empty']:
            continue
        cell = out[row['method']]
        cell['non-empty'] += 1
        if row.get('n_relaxed'):
            cell['relaxing'] += 1
            cell['relaxing and valid'] += row['valid']
            kinds = record['setup'][row['game']]['changes']
            cell['relaxing, valid, and exact for a targeted change'] += (
                row['valid'] and row['changes'] and any(
                    (a.get('ablation') or {}).get('exactness') == 0
                    for cid, a in row['changes_by_ref'].items()
                    if kinds[cid]['kind'] != 'no_effect'))
    return out


def _methods_in(record):
    """The methods the record actually ran, in METHODS order: a method
    that was never run must not print as measured zeros."""
    from lgref.bench.methods import METHODS, POSTFREEZE, RATING_ONLY
    present = {row['method'] for row in record['rows']}
    return [m for m in list(METHODS) + list(POSTFREEZE) + list(RATING_ONLY)
            if m in present]


# ---- the ablation-based grouping metrics (#363) -------------------------

#: Below this share of an ablation's changed atoms in one action type, its
#: changes are SCATTERED: intervention.py's focus criterion.
FOCUS = 0.6


def rejection(row):
    """Why an intervention is rejected as an ablation, or 'accepted'.
    Every attempted intervention gets exactly one of these."""
    if row['empty']:
        return 'empty (nothing removable)'
    if not row['valid']:
        reason = row['invalid_reason'] or ''
        if reason.startswith('does not load'):
            return 'does not compile'
        if reason.startswith('roles changed') or reason == 'no roles':
            return 'roles removed'
        if reason.startswith('the start state is already terminal'):
            return 'unplayable at the start'
        if reason.startswith('no legal move for') and 'start' in reason:
            return 'unplayable at the start'
        if reason.startswith('own play'):
            return 'ill-formed in its own play'
        if 'two goal values' in reason:
            return 'two goal values'
        if 'no legal move' in reason:
            return 'stuck state'
        return 'other invalid: ' + reason[:40]
    if not row['changes']:
        return 'inert (no change)'
    scatter = row.get('scatter') or {}
    if scatter.get('concentration') is not None \
            and scatter['concentration'] < FOCUS:
        return 'unfocused (scattered)'
    return 'accepted'


def closest_ablation(record, procedure='ownership'):
    """{(game, method, change): (row, ablation metrics)}: each method's
    ablation closest to the reference ablation -- the VALID one with the
    smallest exactness count (metric 1), ties broken by smaller
    collateral, then by group order, among valid interventions that
    change something. Absent where there is none."""
    best = {}
    for row in record['rows']:
        # An inert or empty intervention is no ablation at all: it would
        # always score exactness |changed(R)| with collateral 0, and win.
        if row['procedure'] != procedure or not row['valid'] \
                or row['empty'] or not row['changes']:
            continue
        for change_id, agree in row['changes_by_ref'].items():
            ablation = agree.get('ablation')
            if ablation is None:
                continue
            key = (row['game'], row['method'], change_id)
            rank = (ablation['exactness'], ablation['collateral'],
                    row['group'])
            if key not in best or rank < best[key][0]:
                best[key] = (rank, row, ablation)
    return {k: (v[1], v[2]) for k, v in best.items()}


def legal_move_table(record, procedure='ownership'):
    """The per-kind breakdown (#402) at each method's closest ablation
    (`closest_ablation`, by exactness over all kinds). Legal-move
    differences are (state, role, move) triples legal in one
    description and not the other, over S; terminal, goal and successor
    differences are separate columns. Which of these is primary is the
    user's open decision; the table reports all four apart."""
    closest = closest_ablation(record, procedure)
    targeted = _targeted(record)
    lines = ['| method | rules with a valid ablation | exact in legal moves '
             '| legal-move collateral > 0 | legal-move shortfall > 0 | '
             'median legal-move differences | terminal differences | '
             'goal differences | successor differences (representation-'
             'dependent) |', '|---' * 9 + '|']
    for method in _methods_in(record):
        found = [closest[(g, method, c)][1] for g, c in targeted
                 if (g, method, c) in closest]
        if not found:
            lines.append('| {} | 0 / {} | 0 | n/a | n/a | n/a | n/a | n/a | '
                         'n/a |'.format(method, len(targeted)))
            continue
        legal = [a['exactness_by_kind']['legal'] for a in found]
        lines.append('| {} | {} / {} | {} | {}/{} | {}/{} | {} | {} | {} | '
                     '{} |'.format(
                         method, len(found), len(targeted),
                         sum(1 for x in legal if x == 0),
                         sum(1 for a in found
                             if a['collateral_by_kind']['legal'] > 0),
                         len(found),
                         sum(1 for a in found
                             if a['shortfall_by_kind']['legal'] > 0),
                         len(found), _fmt(_median(legal), 0),
                         sum(a['exactness_by_kind']['terminal']
                             for a in found),
                         sum(a['exactness_by_kind']['goal'] for a in found),
                         sum(a['exactness_by_kind'].get('next', 0)
                             for a in found)))
    return '\n'.join(lines)


def _targeted(record):
    return [(g, cid) for g in record['games'] if g in record['setup']
            for cid, info in sorted(record['setup'][g]['changes'].items())
            if info['kind'] != 'no_effect']


def ablation_summary(record, procedure='ownership'):
    """Metrics 1-5, 8 and 9 per method, over the targeted changes."""
    closest = closest_ablation(record, procedure)
    targeted = _targeted(record)
    out = collections.OrderedDict()
    for method in _methods_in(record):
        found = [(g, c, closest[(g, method, c)]) for g, c in targeted
                 if (g, method, c) in closest]
        cell = {'n_changes': len(targeted), 'n_found': len(found),
                'exact': 0, 'broken': 0, 'short': 0,
                'rules_broken': [], 'collateral': [], 'shortfall': [],
                'exactness': [], 'end_discrepancy': 0,
                'repaired': 0, 'repaired_exact': 0,
                'unrepaired': 0, 'unrepaired_exact': 0,
                'by_game': collections.defaultdict(lambda: [0, 0])}
        for game, _c, (row, ab) in found:
            cell['exact'] += ab['exactness'] == 0
            cell['broken'] += ab['collateral'] > 0
            cell['short'] += ab['shortfall'] > 0
            cell['rules_broken'].append(len(ab.get('rules_broken', ())))
            cell['collateral'].append(ab['collateral'])
            cell['shortfall'].append(ab['shortfall'])
            cell['exactness'].append(ab['exactness'])
            kinds = ab['exactness_by_kind']
            cell['end_discrepancy'] += kinds['terminal'] + kinds['goal']
            repaired = bool(row.get('n_relaxed') or row.get('n_protected'))
            key = 'repaired' if repaired else 'unrepaired'
            cell[key] += 1
            cell[key + '_exact'] += ab['exactness'] == 0
            cell['by_game'][game][0] += 1
            cell['by_game'][game][1] += ab['collateral'] > 0
        out[method] = cell
    return out


def _median(values):
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    return (values[mid] if len(values) % 2
            else (values[mid - 1] + values[mid]) / 2.0)


def ablation_table(record, procedure='ownership'):
    summary = ablation_summary(record, procedure)
    n = next(iter(summary.values()))['n_changes'] if summary else 0
    lines = ['| method | rules with a valid ablation | exact (1) | '
             'breakage rate: collateral > 0 (4) | rules broken per '
             'ablation, mean = fragility (2, 5) | shortfall > 0 (3) | '
             'median collateral / shortfall atoms | ending or payoff '
             'atoms wrong (9) | repaired: exact / unrepaired: exact (8) |',
             '|---' * 9 + '|']
    for method, c in summary.items():
        found = c['n_found']
        lines.append(
            '| {} | {} / {} | {} | {} | {} | {} | {} / {} | {} | '
            '{}: {} / {}: {} |'.format(
                method, found, n, c['exact'],
                '{}/{}'.format(c['broken'], found) if found else 'n/a',
                '{:.2f}'.format(sum(c['rules_broken']) / float(found))
                if found else 'n/a',
                '{}/{}'.format(c['short'], found) if found else 'n/a',
                _fmt(_median(c['collateral']), 0)
                if found else 'n/a',
                _fmt(_median(c['shortfall']), 0) if found else 'n/a',
                c['end_discrepancy'], c['repaired'], c['repaired_exact'],
                c['unrepaired'], c['unrepaired_exact']))
    return '\n'.join(lines)


def breakage_by_game(record, procedure='ownership'):
    """Metric 4 per game: ablations with collateral > 0 / ablations."""
    summary = ablation_summary(record, procedure)
    games = [g for g in record['games'] if g in record['setup']]
    lines = ['| method | ' + ' | '.join(games) + ' |',
             '|---' * (len(games) + 1) + '|']
    for method, c in summary.items():
        cells = []
        for game in games:
            found, broken = c['by_game'].get(game, (0, 0))
            cells.append('{}/{}'.format(broken, found) if found else 'n/a')
        lines.append('| {} | {} |'.format(method, ' | '.join(cells)))
    return '\n'.join(lines)


def rejection_table(record, procedure='ownership'):
    """Metric 6: every attempted intervention by verdict, per method."""
    counts = collections.defaultdict(collections.Counter)
    for row in record['rows']:
        if row['procedure'] == procedure:
            counts[row['method']][rejection(row)] += 1
    verdicts = sorted({v for c in counts.values() for v in c},
                      key=lambda v: (v == 'accepted', v))
    lines = ['| method | attempted | ' + ' | '.join(verdicts) + ' |',
             '|---' * (len(verdicts) + 2) + '|']
    for method in _methods_in(record):
        c = counts.get(method, collections.Counter())
        total = sum(c.values())
        lines.append('| {} | {} | {} |'.format(method, total, ' | '.join(
            '{} ({:.0%})'.format(c[v], c[v] / float(total))
            if total and c[v] else '-' for v in verdicts)))
    return '\n'.join(lines)


def rejected_rules(record, sheets, procedure='ownership', method='lgref'):
    """Metric 6's list: for each rejected intervention of `method`, the
    reference rules of the statements it would have removed or
    relaxed. `sheets` is {game: Sheet}."""
    out = []
    for row in record['rows']:
        if row['procedure'] != procedure or row['method'] != method:
            continue
        verdict = rejection(row)
        if verdict == 'accepted':
            continue
        membership = sheets[row['game']].membership()
        rules = sorted({r for i in row['touched']
                        for r in membership.get(i, ())})
        out.append((row['game'], row['group'], verdict, rules))
    return out


def scatter_table(record, procedure='ownership'):
    """Metric 7, mean over each method's valid, changing ablations."""
    lines = ['| method | ablations | action types touched | reference '
             'rules touched | concentration | normalised entropy |',
             '|---|---|---|---|---|---|']
    for method in _methods_in(record):
        rows = [r for r in record['rows'] if r['procedure'] == procedure
                and r['method'] == method and r['valid'] and r['changes']
                and r.get('scatter')]
        if not rows:
            lines.append('| {} | 0 | n/a | n/a | n/a | n/a |'.format(method))
            continue

        def mean(key):
            values = [r['scatter'][key] for r in rows
                      if r['scatter'][key] is not None]
            return sum(values) / float(len(values)) if values else None
        lines.append('| {} | {} | {} | {} | {} | {} |'.format(
            method, len(rows), _fmt(mean('n_action_types'), 2),
            _fmt(mean('n_rules'), 2), _fmt(mean('concentration'), 2),
            _fmt(mean('entropy'), 2)))
    return '\n'.join(lines)


def reference_fragility(record):
    """Metric 5 for the REFERENCE ablations themselves: how many other
    reference rules each one's changes reach -- the game's own coupling,
    the floor no grouping can go below."""
    lines = ['| game | rule | other reference rules its changes reach |',
             '|---|---|---|']
    for game in record['games']:
        frag = record['setup'].get(game, {}).get('reference_fragility')
        for rule, others in sorted((frag or {}).items()):
            lines.append('| {} | {} | {} |'.format(
                game, rule, ', '.join(others) or 'none'))
    return '\n'.join(lines)


def rewrite_stability(record, original, procedure='ownership',
                      method=None):
    """Metric 10: for each rewrite, the closest ablation's exactness /
    collateral / shortfall per targeted change, next to the original
    description's (from the Experiment 1 record `original`), and how
    many changes kept exactly the same three numbers."""
    before = closest_ablation(original, procedure)
    best = {}
    for row in record['rows']:
        if row['procedure'] != procedure or not row['valid'] \
                or row['empty'] or not row.get('changes'):
            continue
        for cid, ab in row['by_ref'].items():
            key = (row['game'], row['rewrite'], cid)
            rank = (ab['exactness'], ab['collateral'], row['group'])
            if key not in best or rank < best[key][0]:
                best[key] = (rank, ab)
    rewrites = list(dict.fromkeys(r['rewrite'] for r in record['rows']))
    targeted = _targeted(original)
    lines = ['| rewrite | changes with an ablation (original -> rewritten) '
             '| same exactness/collateral/shortfall | exact: original -> '
             'rewritten |', '|---|---|---|---|']
    for name in rewrites:
        had = got = same = exact_a = exact_b = 0
        for game, cid in targeted:
            a = before.get((game, method or record.get('method', 'lgref'),
                            cid))
            a = a[1] if a is not None else None
            b = best.get((game, name, cid))
            b = b[1] if b is not None else None
            had += a is not None
            got += b is not None
            exact_a += a is not None and a['exactness'] == 0
            exact_b += b is not None and b['exactness'] == 0
            if a is not None and b is not None:
                same += all(a[k] == b[k] for k in
                            ('exactness', 'collateral', 'shortfall'))
        lines.append('| {} | {} -> {} of {} | {} | {} -> {} |'.format(
            name, had, got, len(targeted), same, exact_a, exact_b))
    return '\n'.join(lines)


def draws_summary(record, procedure='ownership', method='random_matched'):
    """#396: the random baseline over its DRAWS. For each draw, the number
    of targeted rules with an exact closest ablation, computed on that
    draw's rows alone (merging draws would take the best of many, which
    is not a baseline). Returns (per-draw counts, mean, (low, high)
    bootstrap interval over draws, n targeted)."""
    from lgref.bench import metrics
    draws = sorted({r.get('draw') for r in record['rows']
                    if r['method'] == method and r.get('draw') is not None})
    counts = []
    for draw in draws:
        sub = dict(record, rows=[r for r in record['rows']
                                 if r['method'] == method
                                 and r.get('draw') == draw])
        cell = ablation_summary(sub, procedure).get(method)
        counts.append(cell['exact'] if cell else 0)
    mean, low, high = metrics.bootstrap_interval(counts)
    return counts, mean, (low, high), len(_targeted(record))


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
        print('\n## Ablation metrics (objective)')
        for procedure in ('ownership', 'delete_group'):
            print('\n### procedure: {}\n'.format(procedure))
            print(ablation_table(record, procedure))
            print('\n#### differences by kind at the closest ablation\n')
            print(legal_move_table(record, procedure))
            print('\n#### breakage rate per game\n')
            print(breakage_by_game(record, procedure))
            print('\n#### rejections\n')
            print(rejection_table(record, procedure))
            print('\n#### scatter\n')
            print(scatter_table(record, procedure))
        print('\n### reference fragility\n')
        print(reference_fragility(record))
        print('\n## Reproduction and behavioural agreement')
        for procedure in ('ownership', 'delete_group'):
            print('\n### procedure: {}\n'.format(procedure))
            print(intervention_table(record, procedure))
        print('\n### relaxation usage (ownership)\n')
        for method, cell in relaxation_usage(record).items():
            print('- {}: {}'.format(method, ', '.join(
                '{} {}'.format(k, v) for k, v in sorted(cell.items()))))


if __name__ == '__main__':
    main()
