"""Score rule identification against hand-verified boundaries.

The Phase 1 gate (issue #187). Identification must be validated on games
whose rule boundaries a human can state with certainty BEFORE it is
trusted on Royal Chess, where nobody knows the right answer and a
plausible-looking cluster list is indistinguishable from a correct one.

WHY PAIRWISE SCORING

Cluster labels are arbitrary — "R03" means nothing — so accuracy cannot
be computed per clause. Pairwise scoring asks a label-free question
instead: for every PAIR of clauses, do the two partitions agree on
whether they belong together?

    precision  of the pairs we grouped, how many truly belong together
    recall     of the pairs that truly belong together, how many we found
    F1         their harmonic mean
    ARI        Adjusted Rand Index: the same agreement corrected for
               chance, so a method that merges everything into one
               cluster (perfect recall, terrible precision) cannot look
               good

ARI matters most. Recall alone is trivially maximised by one giant
cluster, and precision alone by all singletons; only chance-corrected
agreement penalises both.

THE BASELINES ARE THE POINT

A method must beat alternatives that are obviously cheaper, or its
complexity is unjustified:

  name_similarity  group clauses by shared head-predicate name tokens.
                   Beats it only if structure carries information that
                   naming does not.
  static_only      the typed graph minus co-activation. Isolates what
                   observing real games adds.
  trace_only       co-activation alone. Isolates what static structure
                   adds.

Reporting a method that loses to a baseline is the point of having them.
"""

import collections
import itertools

from lgref.identify.cluster import cluster
from lgref.identify.graph import ClauseGraph


def _pairs(assignment, node_ids):
    """Pairs of clauses that share at least one group.

    Membership is soft, so two clauses count as together when their
    group sets intersect — consistent with a clause serving two rules.
    """
    together = set()
    for a, b in itertools.combinations(sorted(node_ids), 2):
        if assignment.get(a) and assignment.get(b) \
                and (assignment[a] & assignment[b]):
            together.add((a, b))
    return together


def pairwise_scores(predicted, expected, node_ids):
    """Precision, recall, F1 and ARI between two soft partitions."""
    pred = _pairs(predicted, node_ids)
    true = _pairs(expected, node_ids)
    total = len(list(itertools.combinations(sorted(node_ids), 2)))

    tp = len(pred & true)
    fp = len(pred - true)
    fn = len(true - pred)
    tn = total - tp - fp - fn

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)

    # ARI via the pair-counting form: (index - expected) / (max - expected).
    index = tp
    exp_index = ((tp + fp) * (tp + fn) / total) if total else 0.0
    max_index = ((tp + fp) + (tp + fn)) / 2.0
    ari = ((index - exp_index) / (max_index - exp_index)
           if (max_index - exp_index) else 0.0)

    return {'precision': precision, 'recall': recall, 'f1': f1, 'ari': ari,
            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}


# ---- the method under test ----------------------------------------------

def lgref_assignment(nodes, **kw):
    graph = ClauseGraph(nodes)
    rules, _dropped = cluster(graph, **kw)
    out = collections.defaultdict(set)
    for rule in rules:
        for clause_id in rule.all_clause_ids:
            out[clause_id].add(rule.rule_id)
    return dict(out)


# ---- baselines -----------------------------------------------------------

def baseline_name_similarity(nodes, **_kw):
    """Group by shared head-predicate name tokens.

    The cheapest plausible method: `boulder_cooldown` and `boulder_at`
    share "boulder" and are probably related. If structure cannot beat
    this, the graph is not earning its complexity.
    """
    out = collections.defaultdict(set)
    for node in nodes:
        name = node.head_predicate or ''
        for token in name.split('_'):
            if len(token) > 2:
                out[node.node_id].add('N:' + token)
    return dict(out)


def baseline_static_only(nodes, **kw):
    """The typed graph with co-activation removed."""
    graph = ClauseGraph(nodes)
    graph.edges['co_activation'] = set()
    rules, _ = cluster(graph, **kw)
    out = collections.defaultdict(set)
    for rule in rules:
        for clause_id in rule.all_clause_ids:
            out[clause_id].add(rule.rule_id)
    return dict(out)


def baseline_trace_only(nodes, traces=None, **kw):
    """Co-activation alone, with every static edge type removed.

    Returns None when no traces are supplied, so the report says
    "not measured" rather than 0.000. A zero would read as "this
    baseline was tried and failed", which is a different and much more
    flattering claim than "this baseline has not been run yet".
    """
    if not traces:
        return None
    graph = ClauseGraph(nodes)
    for kind in list(graph.edges):
        if kind != 'co_activation':
            graph.edges[kind] = set()
    graph.add_co_activation(traces)
    rules, _ = cluster(graph, **kw)
    out = collections.defaultdict(set)
    for rule in rules:
        for clause_id in rule.all_clause_ids:
            out[clause_id].add(rule.rule_id)
    return dict(out)


METHODS = {
    'lgref': lgref_assignment,
    'name_similarity': baseline_name_similarity,
    'static_only': baseline_static_only,
    'trace_only': baseline_trace_only,
}


def evaluate(game, nodes, expected, methods=None, **kw):
    """Score every method on one game."""
    methods = methods or METHODS
    node_ids = [n.node_id for n in nodes]
    rows = []
    for name, fn in methods.items():
        predicted = fn(nodes, **kw)
        if predicted is None:
            rows.append({'method': name, 'game': game, 'not_measured': True})
            continue
        scores = pairwise_scores(predicted, expected, node_ids)
        scores['method'] = name
        scores['game'] = game
        scores['n_groups'] = len({g for gs in predicted.values() for g in gs})
        rows.append(scores)
    return rows


def format_table(rows):
    header = ('{:<14} {:<16} {:>7} {:>7} {:>7} {:>7} {:>8}'
              .format('game', 'method', 'prec', 'recall', 'F1', 'ARI',
                      'groups'))
    lines = [header, '-' * len(header)]
    for row in rows:
        if row.get('not_measured'):
            lines.append('{:<14} {:<16} {:>7} {:>7} {:>7} {:>7} {:>8}'
                         .format(row['game'], row['method'], '-', '-', '-',
                                 'n/m', '-'))
            continue
        lines.append('{:<14} {:<16} {:>7.3f} {:>7.3f} {:>7.3f} {:>7.3f} {:>8}'
                     .format(row['game'], row['method'], row['precision'],
                             row['recall'], row['f1'], row['ari'],
                             row['n_groups']))
    return '\n'.join(lines)
