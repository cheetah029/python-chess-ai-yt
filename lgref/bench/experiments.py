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
from lgref.bench import wellformed
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


# ---- saving every random game a measurement plays (#374) ---------------

def write_records(path, texts, games, tag=None, mode='at'):
    """Append games to a gzipped JSON-lines file: one line per
    description played ({'description': id, 'text': ...}), then one per
    game, each carrying `tag` (method, procedure, group, ...)."""
    import gzip
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with gzip.open(path, mode, encoding='utf-8') as handle:
        for did in sorted(texts):
            handle.write(json.dumps({'description': did,
                                     'text': texts[did]}) + '\n')
        for game in games:
            line = dict(game)
            line.update(tag or {})
            handle.write(json.dumps(line, sort_keys=True) + '\n')


def read_records(path):
    """(texts, games) from a records file written by `write_records`."""
    import gzip
    texts, games = {}, []
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        for line in handle:
            item = json.loads(line)
            if 'text' in item:
                texts[item['description']] = item['text']
            else:
                games.append(item)
    return texts, games


def _state_set(game, base_text, records):
    """behaviour.state_set, with its random games saved when asked."""
    with wellformed.recording() as rec:
        states, how = behaviour.state_set(game, base_text)
    if records:
        write_records(os.path.join(records, game, 'state_set.jsonl.gz'),
                      rec.texts, rec.games, mode='wt')
    return states, how


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


# ---- metric 10: ablation metrics under rewrites ---------------------------

def _symbol_inverse(forms, states):
    """{renamed symbol: original} for the scramble rewrite."""
    from lgref.identify.robustness import rename_symbols
    found = set()

    def walk(term):
        if isinstance(term, tuple):
            for child in term:
                walk(child)
        elif isinstance(term, str):
            found.add(term)
    for form in forms:
        walk(form)
    for state in states:
        for fact in state:
            walk(fact)
    return {rename_symbols([s])[0]: s for s in found}


def _unmap(term, inverse):
    """Undo the scramble renaming in an atom. Successor atoms hold a
    whole state, a frozenset of facts -- missing that case made every
    successor atom of a scrambled description look changed (#363's own
    validation: metric 10 first showed 0 of 10 changes stable under
    scramble, against an identical grouping)."""
    if isinstance(term, tuple):
        return tuple(_unmap(t, inverse) for t in term)
    if isinstance(term, frozenset):
        return frozenset(_unmap(t, inverse) for t in term)
    return inverse.get(term, term)


_REWRITE_SHARED = {}


def _rewrite_share(states, mapped, inverse, base_atoms, ref_atoms, owners,
                   rewritten_base, records=False):
    _REWRITE_SHARED.update(states=states, mapped=mapped, inverse=inverse,
                           base_atoms=base_atoms, ref_atoms=ref_atoms,
                           owners=owners, rewritten_base=rewritten_base,
                           records=records)


def _evaluate_rewritten(job):
    """Metrics 1-3 of one intervention built on a REWRITTEN description,
    against the ORIGINAL reference ablations, in original names."""
    with wellformed.recording() as rec:
        row = _evaluate_rewritten_inner(job)
    if _REWRITE_SHARED.get('records'):
        row['_records'] = {'texts': rec.texts, 'games': rec.games}
    return row


def _evaluate_rewritten_inner(job):
    from lgref.bench import ablation_metrics as am
    game, rewrite, procedure, index, text, empty = job
    sh = _REWRITE_SHARED
    cand = behaviour.behaviour(text, sh['mapped'])
    row = {'game': game, 'rewrite': rewrite, 'procedure': procedure,
           'group': index, 'empty': empty, 'valid': False, 'by_ref': {}}
    if empty or not cand.loads or cand.error:
        return row
    valid, _reason = behaviour.validity(text, sh['mapped'], cand,
                                        base=sh['rewritten_base'])
    row['valid'] = valid
    inverse = sh['inverse']
    # A joint move is ordered by the description's roles, and scrambled
    # role names sort differently: put each joint back in the order of
    # the original (unscrambled, sorted) roles.
    roles = [_unmap(r, inverse) for r in cand.roles]
    order = [roles.index(r) for r in sorted(roles)]

    def canonical(atom):
        atom = _unmap(atom, inverse)
        if atom[0] == 'next':
            atom = (atom[0], atom[1], tuple(atom[2][i] for i in order),
                    atom[3])
        return atom
    cand_atoms = frozenset(canonical(a) for a in am.atoms(cand))
    row['changes'] = bool(am.changed(cand_atoms, sh['base_atoms']))
    for cid, ref in sh['ref_atoms'].items():
        row['by_ref'][cid] = am.compare(cand_atoms, ref, sh['base_atoms'],
                                        sh['owners'], cid)
    return row


def _pop_records(rows, records, game, name, keys):
    """Move each row's saved games into the game's records file."""
    for row in rows:
        saved = row.pop('_records', None)
        if saved and records:
            write_records(os.path.join(records, game, name + '.jsonl.gz'),
                          saved['texts'], saved['games'],
                          tag={k: row.get(k) for k in keys})


def rewrite_ablation_rows(games, method='lgref', seed=0, workers=1,
                          records=None):
    """Metric 10: for every behaviour-preserving rewrite, `method`'s
    ablations of the REWRITTEN description scored against the original
    reference ablations on the original state set (mapped through the
    renaming for `scramble`)."""
    import concurrent.futures

    from ggp.infix import parse_infix

    from lgref.bench import ablation_metrics as am
    from lgref.bench import rewrites
    from lgref.identify.clauses import normalize

    rows = []
    with_variants = set(probes.games_with_variants())
    for game in games:
        if game not in with_variants:
            continue
        with open(catalog.game_path(game)) as handle:
            base_text = handle.read()
        states, _how = _state_set(game, base_text, records)
        base_atoms = am.atoms(behaviour.behaviour(base_text, states))
        ref_atoms = {}
        for change in probes.load_variants(game)[1]:
            text = probes.variant_text(base_text, change)
            ref_atoms[change.id] = am.atoms(
                behaviour.behaviour(text, states))
        owners = {c: am.changed(a, base_atoms)
                  for c, a in ref_atoms.items()}
        forms = parse_infix(base_text)
        for name in rewrites.REWRITES:
            new_forms, _prov = rewrites.rewrite(name, forms, seed=0)
            mapping = rewrites.state_map(name, forms)
            mapped = [mapping(s) for s in states]
            inverse = (_symbol_inverse(forms, states)
                       if name == 'scramble' else {})
            nodes = normalize(new_forms)
            grouping = grouping_for(method, nodes, seed)
            jobs = []
            for procedure in _iv.PROCEDURES:
                for item in _iv.build(nodes, grouping, procedure):
                    jobs.append((game, name, procedure, item.group,
                                 item.text, item.empty))
            rewritten_base = behaviour.behaviour(
                rewrites.to_text(new_forms), mapped)
            args = (states, mapped, inverse, base_atoms, ref_atoms, owners,
                    rewritten_base, bool(records))
            if workers <= 1:
                _rewrite_share(*args)
                got = [_evaluate_rewritten(j) for j in jobs]
            else:
                with concurrent.futures.ProcessPoolExecutor(
                        max_workers=workers, initializer=_rewrite_share,
                        initargs=args) as pool:
                    got = list(pool.map(_evaluate_rewritten, jobs))
            _pop_records(got, records, game, 'rewrite_ablations',
                         ('rewrite', 'procedure', 'group'))
            rows.extend(got)
            _progress('{} {}: {} interventions'.format(game, name,
                                                       len(jobs)))
    return rows


# ---- #402: play-out agreement of each method's closest ablation ---------

def trace_rows(record, games=20, max_plies=60, procedures=_iv.PROCEDURES):
    """For every method, procedure and targeted rule in an Experiment 1
    `record`, rebuild the closest ablation (`report.closest_ablation`)
    and play it out against the
    reference ablation (`lgref.bench.traces.play_out`). The grouping
    and intervention builders are deterministic, so the rebuilt text is
    the one the record scored; each row says which group it is."""
    from lgref.bench import report, traces
    from lgref.identify.clauses import load

    seed = record.get('seed', 0)
    rows, built = [], {}
    for procedure in procedures:
        closest = report.closest_ablation(record, procedure)
        for (game, method, change_id), (row, _ab) in sorted(
                closest.items()):
            kind = record['setup'][game]['changes'][change_id]['kind']
            if kind == 'no_effect':
                continue
            key = (game, method, procedure)
            if key not in built:
                nodes = load(catalog.game_path(game))
                built[key] = _iv.build(nodes, grouping_for(
                    method, nodes, seed), procedure)
            cand = built[key][row['group']].text
            with open(catalog.game_path(game)) as handle:
                base_text = handle.read()
            change = {c.id: c for c in probes.load_variants(game)[1]}[
                change_id]
            ref = probes.variant_text(base_text, change)
            got = traces.play_out(ref, cand, games=games,
                                  max_plies=max_plies)
            got.update(game=game, method=method, procedure=procedure,
                       change=change_id, group=row['group'],
                       exact=traces.exact(got))
            rows.append(got)
        _progress('traces: {} done'.format(procedure))
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


def _share(states, base_beh, refs, records=False):
    """Per-process copy of what every job of one game needs, set once by
    the pool initializer instead of pickled into every job. The atom
    sets of the base and of each reference ablation, and each reference
    rule's changed atoms (its OWNERSHIP), are computed here once."""
    from lgref.bench import ablation_metrics as am
    base_atoms = am.atoms(base_beh)
    ref_atoms = {cid: am.atoms(ref_beh)
                 for cid, (_c, ref_beh, _t) in refs.items()}
    owners = {cid: am.changed(a, base_atoms)
              for cid, a in ref_atoms.items()}
    _SHARED.update(states=states, base=base_beh, refs=refs,
                   base_atoms=base_atoms, ref_atoms=ref_atoms,
                   owners=owners, records=records)


def _evaluate(job):
    """Every measurement of one intervention. Module-level for a pool.
    The random games its validity check plays are kept with the row when
    the run saves records (#374)."""
    with wellformed.recording() as rec:
        row = _evaluate_inner(job)
    if _SHARED.get('records'):
        row['_records'] = {'texts': rec.texts, 'games': rec.games}
    return row


def _evaluate_inner(job):
    (game, method, procedure, index, text, touched, empty, n_relaxed,
     n_protected, draw) = job
    from lgref.bench import ablation_metrics as am
    states, base_beh, refs = (_SHARED['states'], _SHARED['base'],
                              _SHARED['refs'])
    base_atoms, ref_atoms, owners = (_SHARED['base_atoms'],
                                     _SHARED['ref_atoms'],
                                     _SHARED['owners'])
    started = time.time()
    cand = behaviour.behaviour(text, states)
    valid, reason = (False, 'empty') if empty else behaviour.validity(
        text, states, cand, base=base_beh)
    row = {'game': game, 'method': method, 'procedure': procedure,
           'draw': draw, 'group': index, 'empty': empty, 'valid': valid,
           'invalid_reason': None if valid else reason,
           'changes': (not empty) and behaviour.changes_anything(base_beh,
                                                                 cand),
           'touched': sorted(touched), 'n_relaxed': n_relaxed,
           'n_protected': n_protected, 'changes_by_ref': {}}
    cand_atoms = am.atoms(cand)
    row['scatter'] = (am.scatter(am.changed(cand_atoms, base_atoms),
                                 owners)
                      if cand_atoms is not None else None)
    row['n_changed_atoms'] = (len(am.changed(cand_atoms, base_atoms))
                              if cand_atoms is not None else None)
    for change_id, (change, ref_beh, ref_touched) in refs.items():
        results = probes.run_probes(text, change)
        passed = sorted(p for p, (ok, _r) in results.items() if ok)
        agree = behaviour.agreement(base_beh, ref_beh, cand)
        union = set(touched) | ref_touched
        agree.update(
            probes_passed=passed, n_probes=len(results),
            all_probes=len(passed) == len(results),
            edit_jaccard=(len(set(touched) & ref_touched) / float(len(union))
                          if union else None),
            ablation=(am.compare(cand_atoms, ref_atoms[change_id],
                                 base_atoms, owners, change_id)
                      if cand_atoms is not None else None))
        row['changes_by_ref'][change_id] = agree
    row['seconds'] = round(time.time() - started, 2)
    return row


def _reference_fragility(base_beh, refs):
    """{rule: [other rules whose reference ablation changes an atom
    this rule's reference ablation also changes]}."""
    from lgref.bench import ablation_metrics as am
    base = am.atoms(base_beh)
    owned = {cid: am.changed(am.atoms(ref_beh), base)
             for cid, (_c, ref_beh, _t) in refs.items()}
    return {cid: sorted(o for o in owned if o != cid
                        and owned[cid] & owned[o])
            for cid in owned}


def intervention_rows(games, methods=None, seed=0,
                      procedures=_iv.PROCEDURES, workers=1, records=None,
                      draws=0):
    """Every intervention of every method, measured on each game.

    `draws` > 0 replaces the single random_matched grouping with that
    many independent DRAWS (#396): permutation seeds seed .. seed +
    draws - 1, every one permuting the SAME LGREF grouping (at `seed`).
    Each row then carries its `draw`, so a report can give the expected
    value over draws instead of one draw's luck."""
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
        states, how = _state_set(game, base_text, records)
        base_beh = behaviour.behaviour(base_text, states)
        refs = {}
        for change in probes.load_variants(game)[1]:
            text = probes.variant_text(base_text, change)
            refs[change.id] = (change, behaviour.behaviour(text, states),
                               edited_statements(base_text, text))
        setup[game] = {'state_set': how, 'n_states': len(states),
                       'changes': {cid: {'kind': c.kind,
                                         'touched': sorted(t)}
                                   for cid, (c, _b, t) in refs.items()},
                       'reference_fragility':
                           _reference_fragility(base_beh, refs)}
        _progress('{}: S = {} states ({})'.format(game, len(states), how))
        jobs = []
        for method in methods:
            if method == 'random_matched' and draws:
                reference = _methods.lgref(nodes, seed=seed)
                plan = [(d, _methods.random_matched(
                    nodes, seed=seed + d, reference=reference))
                    for d in range(draws)]
            else:
                plan = [(None, grouping_for(method, nodes, seed))]
            for draw, grouping in plan:
                for procedure in procedures:
                    for item in _iv.build(nodes, grouping, procedure):
                        touched = {int(n.split('#')[1])
                                   for n in item.removed}
                        touched |= {int(n.split('#')[1])
                                    for n in item.relaxed}
                        jobs.append((
                            game, method, procedure, item.group, item.text,
                            touched, item.empty,
                            sum(len(p) for p in item.relaxed.values()),
                            len(item.protected), draw))
        _progress('{}: {} interventions'.format(game, len(jobs)))
        started = time.time()
        _share(states, base_beh, refs, bool(records))
        keys = ('method', 'procedure', 'group')
        if workers <= 1:
            for done, job in enumerate(jobs, 1):
                row = _evaluate(job)
                _pop_records([row], records, game, 'interventions', keys)
                rows.append(row)
                if done % 10 == 0 or done == len(jobs):
                    _progress('  {}/{} {:.0f}s'.format(
                        done, len(jobs), time.time() - started))
        else:
            out = [None] * len(jobs)
            with concurrent.futures.ProcessPoolExecutor(
                    max_workers=workers, initializer=_share,
                    initargs=(states, base_beh, refs,
                              bool(records))) as pool:
                futures = {pool.submit(_evaluate, job): i
                           for i, job in enumerate(jobs)}
                for done, future in enumerate(
                        concurrent.futures.as_completed(futures), 1):
                    row = future.result()
                    _pop_records([row], records, game, 'interventions',
                                 keys)
                    out[futures[future]] = row
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
                 'invariance', 'rewrite_ablations', 'traces'):
        p = sub.add_parser(name)
        p.add_argument('--split', default='dev')
        p.add_argument('--games', default='')
        p.add_argument('--methods', default='')
        p.add_argument('--out', required=True)
    sub.choices['groupings'].add_argument('--seeds', type=int, default=30)
    sub.choices['sensitivity'].add_argument('--seeds', type=int, default=30)
    sub.choices['traces'].add_argument(
        '--from', dest='source', required=True,
        help='an Experiment 1 record whose closest ablations to play out')
    sub.choices['invariance'].add_argument('--seeds', type=int, default=5)
    sub.choices['interventions'].add_argument('--seed', type=int,
                                              default=0)
    sub.choices['interventions'].add_argument('--workers', type=int,
                                              default=1)
    sub.choices['interventions'].add_argument(
        '--draws', type=int, default=0,
        help='random_matched: this many independent permutation draws of '
             'the same LGREF grouping (#396)')
    sub.choices['rewrite_ablations'].add_argument('--workers', type=int,
                                                  default=1)
    for name in ('interventions', 'rewrite_ablations'):
        sub.choices[name].add_argument(
            '--records', default=None,
            help='directory for the gzipped records of every random game '
                 'played (#374); one folder per game')
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
    elif args.what == 'traces':
        with open(args.source) as handle:
            source = json.load(handle)
        record['source'] = args.source
        record['rows'] = trace_rows(source)
    elif args.what == 'rewrite_ablations':
        record['method'] = methods[0] if methods else 'lgref'
        record['rows'] = rewrite_ablation_rows(games,
                                               method=record['method'],
                                               workers=args.workers,
                                               records=args.records)
        record['records'] = args.records
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
                                        workers=args.workers,
                                        records=args.records,
                                        draws=args.draws)
        record['draws'] = args.draws
        record['records'] = args.records
        record['rows'], record['setup'] = rows, setup
    record['seconds'] = round(time.time() - started, 1)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w') as handle:
        json.dump(record, handle, indent=1, sort_keys=True, default=list)
    _progress('wrote {} ({:.0f}s)'.format(args.out, record['seconds']))


if __name__ == '__main__':
    main()
