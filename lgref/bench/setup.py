"""Which statements are not ablation candidates, and how well LGREF
tells (Paper A, #358: the user's setup instruction).

Not every statement is a rule one could ablate. The report separates
three kinds, counted per game:

  (a) language   board geometry, coordinate and counting arithmetic
  (b) init       the initial position
  (c) role / outcome   role declarations; terminal and goal statements

(b) and (c) are read from the syntax. (a) is the hard one, and the one
where a mistake matters: a real rule wrongly marked "setup" would never
be ablated, and nothing would report it. So LGREF's language verdict
(`lgref.identify.language`, #202) is scored against the provisional
reference in `references/kinds.yaml` -- precision and recall for "not an
ablation candidate", with every false "language" listed by statement.

Two LGREF verdicts are scored, because the user's order of decision
puts the DEFINITIVE indicator first:

  statement  the statement's head predicate depends on no game state at
             any depth (`state_dependent_predicates`) -- the definitive
             indicator, applied statement by statement
  cluster    production #202: a statement is language when the LGREF
             group that owns it is classified LANGUAGE

Everything not marked language by the definitive indicator is ATTEMPTED
as an ablation (Experiment 1 does), and a failed ablation is reported as
a failed candidate, never relabelled as setup.
"""

import collections
import os

import yaml

from lgref.bench.catalog import game_path
from lgref.identify import language as _language

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS_PATH = os.path.join(HERE, 'references', 'kinds.yaml')

GDL_OUTPUTS = frozenset({'legal', 'next', 'init', 'terminal', 'goal',
                         'role'})


def _syntactic(node):
    if node.head_kind == 'role':
        return 'role'
    if node.head_kind == 'fluent_init':
        return 'init'
    if node.head_kind in ('terminal', 'goal'):
        return 'outcome'
    return None


def reference_kinds(game, nodes):
    """{node id: role | init | outcome | language | rule}."""
    with open(KINDS_PATH) as handle:
        table = yaml.safe_load(handle)['game_kinds'][game]
    language = set(table['language'])
    out = {}
    for node in nodes:
        kind = _syntactic(node)
        if kind is None:
            kind = ('language' if node.head_predicate in language
                    else 'rule')
        out[node.node_id] = kind
    return out


def statement_verdict(nodes):
    """{node id: kind} by the definitive indicator alone."""
    stateful = _language.state_dependent_predicates(nodes)
    out = {}
    for node in nodes:
        kind = _syntactic(node)
        if kind is None:
            static = (node.head_kind in ('fact', 'derived')
                      and node.head_predicate not in stateful)
            kind = 'language' if static else 'rule'
        out[node.node_id] = kind
    return out


def cluster_verdict(nodes, rules):
    """{node id: kind} by production #202 on LGREF's own groups."""
    verdicts = _language.classify_all(nodes, rules)
    language = set()
    for rule in rules:
        if verdicts[rule.rule_id] == _language.LANGUAGE:
            language |= set(rule.clause_ids)
    out = {}
    for node in nodes:
        kind = _syntactic(node)
        if kind is None:
            kind = 'language' if node.node_id in language else 'rule'
        out[node.node_id] = kind
    return out


def score(predicted, reference, nodes):
    """Precision and recall for 'language' (not an ablation candidate),
    over the statements that are neither role, init nor outcome -- those
    are syntactic and cannot be wrong. Lists every rule statement marked
    language: the error the user asked to rule out."""
    pool = [n.node_id for n in nodes if reference[n.node_id]
            in ('language', 'rule')]
    tp = sum(1 for i in pool if predicted[i] == 'language'
             and reference[i] == 'language')
    fp = [i for i in pool if predicted[i] == 'language'
          and reference[i] == 'rule']
    fn = [i for i in pool if predicted[i] == 'rule'
          and reference[i] == 'language']
    return {'precision': (tp / float(tp + len(fp)) if tp + len(fp)
                          else None),
            'recall': tp / float(tp + len(fn)) if tp + len(fn) else None,
            'rules_marked_language': fp, 'language_missed': fn,
            'n_pool': len(pool)}


def counts(kinds):
    return dict(collections.Counter(kinds.values()))


def report(games):
    from lgref.identify.clauses import load
    from lgref.identify.cluster import calibrate_resolution, cluster
    from lgref.identify.graph import ClauseGraph

    rows = []
    for game in games:
        nodes = load(game_path(game))
        graph = ClauseGraph(nodes)
        rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
        ref = reference_kinds(game, nodes)
        by_statement = statement_verdict(nodes)
        by_cluster = cluster_verdict(nodes, rules)
        rows.append({'game': game, 'reference': counts(ref),
                     'statement': score(by_statement, ref, nodes),
                     'cluster': score(by_cluster, ref, nodes),
                     'statement_counts': counts(by_statement),
                     'cluster_counts': counts(by_cluster)})
    return rows


def format_report(rows):
    def fmt(value):
        return 'n/a' if value is None else '{:.2f}'.format(value)

    lines = ['| game | statements: language / init / role / outcome / '
             'rule (reference) | definitive indicator: P / R for '
             '"language" | rules it marks language | #202 cluster '
             'verdict: P / R | rules it marks language |',
             '|---|---|---|---|---|---|']
    for row in rows:
        ref = row['reference']
        lines.append('| {} | {} / {} / {} / {} / {} | {} / {} | {} | '
                     '{} / {} | {} |'.format(
                         row['game'], ref.get('language', 0),
                         ref.get('init', 0), ref.get('role', 0),
                         ref.get('outcome', 0), ref.get('rule', 0),
                         fmt(row['statement']['precision']),
                         fmt(row['statement']['recall']),
                         ', '.join(row['statement']['rules_marked_language'])
                         or 'none',
                         fmt(row['cluster']['precision']),
                         fmt(row['cluster']['recall']),
                         ', '.join(row['cluster']['rules_marked_language'])
                         or 'none'))
    return '\n'.join(lines)


def main(argv=None):
    import sys
    from lgref.bench.catalog import in_split
    games = (argv if argv else sys.argv[1:]) or in_split('dev')
    print(format_report(report(games)))


if __name__ == '__main__':
    main()
