"""The V2 proposal's accounting tables (#411), from the development runs.

    python -m lgref.bench.v2_evidence

For every grouping method: the development rules it gets exact under
each procedure, and its consistency. For every rule some method gets
exact: which component of the proposal (C1-C6 in
docs/paper-a/lgref-v2-proposal.md) reaches it. Development data only;
`lgref/tests/test_paper_a_v2_proposal.py` checks that the proposal
contains exactly these tables.
"""

import collections
import gzip
import json
import os
import sys

from lgref.bench import report
from lgref.bench.methods import METHODS

RUNS = os.path.join(os.path.dirname(__file__), '..', '..', 'docs',
                    'paper-a', 'runs')

PROCEDURES = ('ownership', 'delete_group')

LABELS = {'lgref': 'V1 (`lgref`)', 'random_matched': 'V0 (30 draws)'}


def _read(runs, name):
    path = os.path.join(runs, name)
    if name.endswith('.gz'):
        with gzip.open(path, 'rt') as handle:
            return json.load(handle)
    with open(path) as handle:
        return json.load(handle)


def load(runs=RUNS):
    return (_read(runs, 'exp1_dev.json'),
            _read(runs, 'draws_exp1_dev.json.gz'),
            _read(runs, 'exp4_dev.json'))


def closest(record, procedure):
    """{method: {(game, change): rule changes}} at the closest ablation,
    over the targeted rules."""
    targeted = {tuple(r) for r in report._targeted(record)}
    out = collections.defaultdict(dict)
    for (game, method, change), (_row, ab) in report.closest_ablation(
            record, procedure).items():
        if (game, change) in targeted:
            out[method][(game, change)] = ab['exactness']
    return out


def exact_rules(record):
    """{(method, procedure): set of exact rules}. V0 is excluded here:
    its draws are summarised by their mean (`v0_means`)."""
    out = {}
    for procedure in PROCEDURES:
        for method, values in closest(record, procedure).items():
            if method != 'random_matched':
                out[(method, procedure)] = {r for r, x in values.items()
                                            if x == 0}
    return out


def v0_means(draws):
    return {p: report.draws_summary(draws, p)[1] for p in PROCEDURES}


def consistency(exp4):
    """{method: mean over games of the per-game mean BCubed F1 over
    rewrites and seeds}."""
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in exp4['rows']:
        per[row['method']][row['game']].append(row['f1'])
    return {m: sum(sum(v) / len(v) for v in g.values()) / len(g)
            for m, g in per.items()}


def component(rule, exact):
    """Which proposed component reaches an exact rule, from the methods
    the components keep. C1 with C4: single statements, deleted. C3 with
    C4: name-token groups, ablated by the ownership split. None if no
    kept component reaches it."""
    if rule in exact.get(('singletons', 'delete_group'), ()):
        return 'C1 + C4 (single statement, deleted)'
    if rule in exact.get(('name_tokens', 'ownership'), ()):
        return 'C3 + C4 (name-token group, ownership split)'
    if rule in exact.get(('name_tokens', 'delete_group'), ()):
        return 'C3 (name-token group, deleted)'
    return None


def _rule(rule):
    return '{} `{}`'.format(*rule)


def method_table(record, draws, exp4):
    exact = exact_rules(record)
    means = v0_means(draws)
    cons = consistency(exp4)
    lines = ['| method | exact, ownership | exact, delete-group | '
             'consistency | its exact rules reached by V2 |',
             '|---|---|---|---|---|']
    for method in METHODS:
        if method == 'random_matched':
            lines.append('| {} | {:.2f} | {:.2f} | {:.3f} | none to reach '
                         '(a mean over draws) |'.format(
                             LABELS[method], means['ownership'],
                             means['delete_group'], cons[method]))
            continue
        own = exact.get((method, 'ownership'), set())
        dele = exact.get((method, 'delete_group'), set())
        rules = own | dele
        missed = [r for r in sorted(rules) if component(r, exact) is None]
        reached = ('none to reach' if not rules else
                   'all {}'.format(len(rules)) if not missed else
                   'NOT: ' + ', '.join(map(_rule, missed)))
        lines.append('| {} | {} | {} | {:.3f} | {} |'.format(
            LABELS.get(method, method), len(own), len(dele), cons[method],
            reached))
    return '\n'.join(lines)


def rule_table(record):
    exact = exact_rules(record)
    rules = sorted(set().union(*exact.values()))
    lines = ['| rule | exact for (method: procedure) | reached in V2 by |',
             '|---|---|---|']
    for rule in rules:
        who = ['{}: {}'.format(LABELS.get(m, m),
                               'own' if p == 'ownership' else 'del')
               for m in METHODS for p in PROCEDURES
               if rule in exact.get((m, p), ())]
        lines.append('| {} | {} | {} |'.format(
            _rule(rule), '; '.join(who),
            component(rule, exact) or 'NOT REACHED'))
    return '\n'.join(lines)


def overlap_check(record):
    """[(procedure, rule, link, singletons)] where link communities have
    FEWER rule changes than singletons, or a valid ablation singletons
    lack. Empty means the overlap gains nothing on any dev rule."""
    out = []
    for procedure in PROCEDURES:
        c = closest(record, procedure)
        for rule in sorted({tuple(r) for r in report._targeted(record)}):
            link = c['link_communities'].get(rule)
            single = c['singletons'].get(rule)
            if link is not None and (single is None or link < single):
                out.append((procedure, rule, link, single))
    return out


def build(runs=RUNS):
    record, draws, exp4 = load(runs)
    return method_table(record, draws, exp4) + '\n\n' + rule_table(record)


def main():
    sys.stdout.write(build() + '\n')


if __name__ == '__main__':
    main()
