"""Paper A experiment runners: grouping scores (Experiments 2 and 3) and
interventions against the reference variants (Experiments 1 and 5).

Every runner writes one JSON file of ROWS -- one row per (game, method,
seed) or per intervention -- plus the commit and the settings it ran
with, so a table can be rebuilt from the file and a file traced to the
code. Tables are made from rows by `lgref.bench.report`, never by hand.

    python -m lgref.bench.experiments groupings --split dev --seeds 30 \\
        --out docs/paper-a/runs/exp2_dev.json
    python -m lgref.bench.experiments interventions --split dev \\
        --seed 0 --workers 3 --out docs/paper-a/runs/exp1_dev.json

Progress goes to stderr, one line per unit, flushed, so a long run can
be watched (and is never mistaken for a hung one).
"""

import argparse
import collections
import json
import os
import subprocess  # nosec B404: reads the commit id only
import sys
import time

from lgref.bench import annotation, behaviour, catalog, metrics, probes
from lgref.bench import interventions as _iv
from lgref.bench import methods as _methods


def _progress(message):
    sys.stderr.write(message + '\n')
    sys.stderr.flush()


def commit():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        sha = subprocess.run(  # nosec B603 B607: fixed argv
            ['git', 'rev-parse', 'HEAD'], cwd=here, check=True,
            capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(  # nosec B603 B607: fixed argv
            ['git', 'status', '--porcelain', '--', ':/lgref'], cwd=here,
            check=True, capture_output=True, text=True).stdout.strip()
    except Exception:                              # noqa: BLE001
        return 'unknown'
    return sha + ('+uncommitted' if dirty else '')


def _nodes(game):
    from lgref.identify.clauses import load
    return load(catalog.game_path(game))


def grouping_for(method, nodes, seed, **kw):
    """One method's grouping. The random baseline is matched to LGREF's
    grouping AT THE SAME SEED."""
    if method == 'random_matched' and 'reference' not in kw:
        kw['reference'] = _methods.lgref(nodes, seed=seed)
    return _methods.run(method, nodes, seed=seed, **kw)


# ---- Experiments 2 and 3: groupings --------------------------------------

def grouping_rows(games, methods=None, seeds=(0,), variant='default',
                  **kw):
    methods = list(methods or _methods.METHODS)
    rows = []
    for game in games:
        if not annotation.has_reference(game):
            _progress('{}: no reference sheet, skipped'.format(game))
            continue
        nodes = _nodes(game)
        ids = [n.node_id for n in nodes]
        sheet = annotation.reference(game)
        for method in methods:
            these = seeds if method in _methods.SEEDED else seeds[:1]
            for seed in these:
                started = time.time()
                grouping = grouping_for(method, nodes, seed, **kw)
                row = metrics.score_grouping(grouping, sheet, ids)
                row.update(game=game, method=method, seed=seed,
                           variant=variant,
                           seconds=round(time.time() - started, 3),
                           resolution=grouping.info.get('resolution'))
                rows.append(row)
            _progress('{} {} {} seeds'.format(game, method, len(these)))
    return rows


# ---- Experiment 3: sensitivity of LGREF ----------------------------------

def sensitivity_variants():
    """{name: (kwargs for `methods.lgref`, ubiquity fraction or None)}.

    One factor at a time from the production setting, fixed here before
    any sensitivity score is seen: every edge type's weight halved,
    doubled and removed; the hub (ubiquitous-fluent) filter at half,
    double and off; fixed raw resolutions; the coverage tolerance; and
    the overlap threshold.
    """
    from lgref.identify.cluster import DEFAULT_WEIGHTS

    out = collections.OrderedDict()
    out['production'] = ({}, None)
    for kind in sorted(k for k, w in DEFAULT_WEIGHTS.items() if w > 0):
        for label, factor in (('x0.5', 0.5), ('x2', 2.0), ('off', 0.0)):
            weights = dict(DEFAULT_WEIGHTS)
            weights[kind] = DEFAULT_WEIGHTS[kind] * factor
            out['weight:{}:{}'.format(kind, label)] = (
                {'weights': weights}, None)
    for fraction in (0.04, 0.16, 1.01):
        out['hub_fraction:{}'.format(fraction)] = ({}, fraction)
    for resolution in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        out['resolution:{}'.format(resolution)] = (
            {'resolution': resolution}, None)
    for tolerance in (0.0, 0.1, 0.2):
        out['tolerance:{}'.format(tolerance)] = (
            {'tolerance': tolerance}, None)
    for threshold in (0.1, 0.15, 0.35, 0.5, 1.01):
        out['overlap:{}'.format(threshold)] = (
            {'overlap_threshold': threshold}, None)
    return out


class _hub_fraction(object):
    """Temporarily set the graph's ubiquitous-read fraction."""

    def __init__(self, fraction):
        self.fraction = fraction

    def __enter__(self):
        from lgref.identify import graph
        self.saved = graph.UBIQUITOUS_READ_FRACTION
        if self.fraction is not None:
            graph.UBIQUITOUS_READ_FRACTION = self.fraction

    def __exit__(self, *exc):
        from lgref.identify import graph
        graph.UBIQUITOUS_READ_FRACTION = self.saved


def sensitivity_rows(games, seeds=(0,), names=None):
    rows = []
    variants = sensitivity_variants()
    for name in names or variants:
        kw, fraction = variants[name]
        with _hub_fraction(fraction):
            got = grouping_rows(games, ['lgref'], seeds=seeds, variant=name,
                                **kw)
        rows.extend(got)
    return rows


# ---- Experiment 4: representation invariance -----------------------------

def _with_singletons(membership):
    """Unclustered statements as their own groups, so that consistency
    compares them too instead of dropping them."""
    return {n: (set(g) if g else {('alone', n)})
            for n, g in membership.items()}


def _partition(membership):
    """The groups of a membership map as a set of member sets -- label
    free, so two groupings that differ only in how their groups are
    numbered compare equal."""
    groups = collections.defaultdict(set)
    for item, labels in membership.items():
        for label in labels:
            groups[label].add(item)
    return frozenset(frozenset(g) for g in groups.values())


def project(grouping, provenance, n_original):
    """A rewrite's grouping as membership over ORIGINAL positions: each
    original statement takes the groups of every statement made from
    it."""
    out = {i: set() for i in range(n_original)}
    membership = grouping.membership()
    for position, node_id in enumerate(grouping.node_ids):
        for original in provenance.get(position, ()):
            out[original] |= {('g', g) for g in membership[node_id]}
    return out


def invariance_rows(games, methods=None, seeds=(0,), rewrite_seed=0):
    from ggp.infix import parse_infix

    from lgref.bench import rewrites
    from lgref.identify.clauses import normalize

    methods = list(methods or _methods.METHODS)
    rows = []
    for game in games:
        with open(catalog.game_path(game)) as handle:
            text = handle.read()
        forms = parse_infix(text)
        nodes = normalize(forms)
        for name in rewrites.REWRITES:
            new_forms, provenance = rewrites.rewrite(name, forms,
                                                     seed=rewrite_seed)
            new_nodes = normalize(new_forms)
            for method in methods:
                these = seeds if method in _methods.SEEDED else seeds[:1]
                for seed in these:
                    before = grouping_for(method, nodes, seed)
                    after = grouping_for(method, new_nodes, seed)
                    reference = _with_singletons({
                        i: {('g', g) for g in groups} for i, groups in
                        enumerate(before.membership()[n.node_id]
                                  for n in nodes)})
                    projected = _with_singletons(
                        project(after, provenance, len(nodes)))
                    score = metrics.bcubed(projected, reference,
                                           list(range(len(nodes))))
                    rows.append({'game': game, 'rewrite': name,
                                 'method': method, 'seed': seed,
                                 'f1': score['f1'],
                                 'precision': score['precision'],
                                 'recall': score['recall'],
                                 'identical': _partition(projected)
                                 == _partition(reference),
                                 'n_before': len(forms),
                                 'n_after': len(new_forms)})
            _progress('{} {}'.format(game, name))
    return rows


# ---- Experiments 1 and 5: interventions ----------------------------------

def edited_statements(base_text, variant_text):
    """Indices of the base statements a reference edit deletes or
    changes, compared as infix text."""
    from ggp.infix import forms_to_infix_lines, parse_infix

    def lines(text):
        return [' '.join(forms_to_infix_lines([f]))
                for f in parse_infix(text)]

    remaining = collections.Counter(lines(variant_text))
    out = set()
    for index, line in enumerate(lines(base_text)):
        if remaining[line]:
            remaining[line] -= 1
        else:
            out.add(index)
    return out


_SHARED = {}


def _share(states, base_beh, refs):
    """Per-process copy of what every job of one game needs, set once by
    the pool initializer instead of pickled into every job."""
    _SHARED.update(states=states, base=base_beh, refs=refs)


def _evaluate(job):
    """Every measurement of one intervention. Module-level for a pool."""
    game, method, procedure, index, text, touched, empty, n_relaxed = job
    states, base_beh, refs = (_SHARED['states'], _SHARED['base'],
                              _SHARED['refs'])
    started = time.time()
    cand = behaviour.behaviour(text, states)
    valid, reason = (False, 'empty') if empty else behaviour.validity(
        text, states, cand, base=base_beh)
    row = {'game': game, 'method': method, 'procedure': procedure,
           'group': index, 'empty': empty, 'valid': valid,
           'invalid_reason': None if valid else reason,
           'changes': (not empty) and behaviour.changes_anything(base_beh,
                                                                 cand),
           'touched': sorted(touched), 'n_relaxed': n_relaxed,
           'changes_by_ref': {}}
    for change_id, (change, ref_beh, ref_touched) in refs.items():
        results = probes.run_probes(text, change)
        passed = sorted(p for p, (ok, _r) in results.items() if ok)
        agree = behaviour.agreement(base_beh, ref_beh, cand)
        union = set(touched) | ref_touched
        agree.update(
            probes_passed=passed, n_probes=len(results),
            all_probes=len(passed) == len(results),
            edit_jaccard=(len(set(touched) & ref_touched) / float(len(union))
                          if union else None))
        row['changes_by_ref'][change_id] = agree
    row['seconds'] = round(time.time() - started, 2)
    return row


def intervention_rows(games, methods=None, seed=0,
                      procedures=_iv.PROCEDURES, workers=1):
    import concurrent.futures

    methods = list(methods or _methods.METHODS)
    rows, setup = [], {}
    with_variants = set(probes.games_with_variants())
    for game in games:
        if game not in with_variants:
            _progress('{}: no reference variants, skipped'.format(game))
            continue
        with open(catalog.game_path(game)) as handle:
            base_text = handle.read()
        nodes = _nodes(game)
        states, how = behaviour.state_set(game, base_text)
        base_beh = behaviour.behaviour(base_text, states)
        refs = {}
        for change in probes.load_variants(game)[1]:
            text = probes.variant_text(base_text, change)
            refs[change.id] = (change, behaviour.behaviour(text, states),
                               edited_statements(base_text, text))
        setup[game] = {'state_set': how, 'n_states': len(states),
                       'changes': {cid: {'kind': c.kind,
                                         'touched': sorted(t)}
                                   for cid, (c, _b, t) in refs.items()}}
        _progress('{}: S = {} states ({})'.format(game, len(states), how))
        jobs = []
        for method in methods:
            grouping = grouping_for(method, nodes, seed)
            for procedure in procedures:
                for item in _iv.build(nodes, grouping, procedure):
                    touched = {int(n.split('#')[1]) for n in item.removed}
                    touched |= {int(n.split('#')[1]) for n in item.relaxed}
                    jobs.append((game, method, procedure, item.group,
                                 item.text, touched, item.empty,
                                 sum(len(p) for p in item.relaxed.values())))
        _progress('{}: {} interventions'.format(game, len(jobs)))
        started = time.time()
        _share(states, base_beh, refs)
        if workers <= 1:
            for done, job in enumerate(jobs, 1):
                rows.append(_evaluate(job))
                if done % 10 == 0 or done == len(jobs):
                    _progress('  {}/{} {:.0f}s'.format(
                        done, len(jobs), time.time() - started))
        else:
            out = [None] * len(jobs)
            with concurrent.futures.ProcessPoolExecutor(
                    max_workers=workers, initializer=_share,
                    initargs=(states, base_beh, refs)) as pool:
                futures = {pool.submit(_evaluate, job): i
                           for i, job in enumerate(jobs)}
                for done, future in enumerate(
                        concurrent.futures.as_completed(futures), 1):
                    out[futures[future]] = future.result()
                    if done % 10 == 0 or done == len(jobs):
                        _progress('  {}/{} {:.0f}s'.format(
                            done, len(jobs), time.time() - started))
            rows.extend(out)
    return rows, setup


def _games(split, names):
    if names:
        return names.split(',')
    return catalog.existing(split)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='what', required=True)
    for name in ('groupings', 'interventions', 'sensitivity',
                 'invariance'):
        p = sub.add_parser(name)
        p.add_argument('--split', default='dev')
        p.add_argument('--games', default='')
        p.add_argument('--methods', default='')
        p.add_argument('--out', required=True)
    sub.choices['groupings'].add_argument('--seeds', type=int, default=30)
    sub.choices['sensitivity'].add_argument('--seeds', type=int, default=30)
    sub.choices['invariance'].add_argument('--seeds', type=int, default=5)
    sub.choices['interventions'].add_argument('--seed', type=int,
                                              default=0)
    sub.choices['interventions'].add_argument('--workers', type=int,
                                              default=1)
    args = parser.parse_args(argv)
    games = _games(args.split, args.games)
    methods = args.methods.split(',') if args.methods else None
    started = time.time()
    record = {'commit': commit(), 'split': args.split, 'games': games,
              'command': ' '.join(sys.argv)}
    if args.what == 'groupings':
        record['seeds'] = list(range(args.seeds))
        record['rows'] = grouping_rows(games, methods,
                                       seeds=tuple(range(args.seeds)))
    elif args.what == 'invariance':
        record['seeds'] = list(range(args.seeds))
        record['rows'] = invariance_rows(games, methods,
                                         seeds=tuple(range(args.seeds)))
    elif args.what == 'sensitivity':
        record['seeds'] = list(range(args.seeds))
        record['rows'] = sensitivity_rows(games,
                                          seeds=tuple(range(args.seeds)))
    else:
        record['seed'] = args.seed
        rows, setup = intervention_rows(games, methods, seed=args.seed,
                                        workers=args.workers)
        record['rows'], record['setup'] = rows, setup
    record['seconds'] = round(time.time() - started, 1)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w') as handle:
        json.dump(record, handle, indent=1, sort_keys=True, default=list)
    _progress('wrote {} ({:.0f}s)'.format(args.out, record['seconds']))


if __name__ == '__main__':
    main()
