"""Grouping methods compared in Paper A (Experiment 2), on one footing.

Every method takes the statements of a description (`ClauseNode`s, from
`lgref.identify.clauses.load`) and returns a `Grouping`: a list of
groups, each a set of statement ids, possibly overlapping. Statements in
no group are unclustered. The scoring (`lgref.bench.metrics`) and the
intervention builder (`lgref.bench.interventions`) see nothing else, so
no method is scored or intervened on differently from another.

THE METHODS

  lgref               production LGREF (`lgref.identify.cluster.cluster`
                      at the coverage-calibrated resolution): Louvain on
                      the typed, weighted graph, generic board updates
                      held out and reattached to every rule they serve,
                      and the overlap step (a statement also joins a
                      community holding >= 25% of its edge weight).
  louvain_hard        the same graph, the same resolution, NO overlap:
                      no reattachment, no overlap step, generic updates
                      left in the partition. Isolates what overlap adds.
  leiden              Leiden (igraph) in place of Louvain: the same
                      graph, the same modularity objective and
                      resolution, the same hold-out and overlap step.
  leiden_hard         Leiden with no overlap, as louvain_hard.
  link_communities    Ahn, Bagrow & Lehmann (Nature 2010) on the SAME
                      weighted graph: edges are clustered, so a statement
                      belongs to the community of each of its edges.
                      Overlap is native, not a post-processing step.
                      Weighted Tanimoto edge similarity, single linkage,
                      cut at the maximum partition density.
  dependency_louvain  basic dependency clustering: Louvain at resolution
                      1.0 on the plain call graph (`predicate` edges,
                      unweighted). No typed edges, no overlap.
  components          connected components of the typed graph -- what
                      GGP factoring would find on a single game.
  name_tokens         `lgref.identify.validate.baseline_name_similarity`:
                      statements sharing a head-predicate name token.
  singletons          one group per statement.
  one_group           every statement in one group.
  random_matched      LGREF's own grouping with the statements randomly
                      permuted (seeded): the same number of groups, the
                      same sizes, the same overlap, no information.

The Louvain and Leiden methods and the random baseline depend
on a seed; the rest are deterministic, and `SEEDED` says which.

GROUP ORDER is deterministic and never depends on statement names: by
size, then by position in the description, as in `cluster`.
"""

import collections
import random

from lgref.core.deps import require
from lgref.identify import cluster as _cluster
from lgref.identify.graph import ClauseGraph
from lgref.identify.validate import baseline_name_similarity

nx = require('networkx', 'community detection over the clause graph',
             'networkx')


class Grouping(object):
    """A method's answer: groups of statement ids, possibly overlapping.

    `core` is, for each group, the part that came from the base partition
    (what an ablation may delete); `groups` adds the shared members. For
    a method with no core/shared distinction the two are equal.
    """

    __slots__ = ('method', 'groups', 'core', 'node_ids', 'info')

    def __init__(self, method, groups, node_ids, core=None, info=None):
        self.method = method
        self.groups = [frozenset(g) for g in groups]
        self.core = [frozenset(c) for c in (core or groups)]
        self.node_ids = list(node_ids)
        self.info = dict(info or {})

    def membership(self):
        """{statement id: frozenset of group indices}, every statement
        present -- unclustered ones with the empty set."""
        out = {n: set() for n in self.node_ids}
        for index, group in enumerate(self.groups):
            for node in group:
                out[node].add(index)
        return {n: frozenset(g) for n, g in out.items()}

    def unclustered(self):
        return [n for n, g in self.membership().items() if not g]

    def __len__(self):
        return len(self.groups)

    def __repr__(self):
        return '<Grouping {} {} groups>'.format(self.method,
                                                len(self.groups))


def _order(nodes):
    return {n.node_id: i for i, n in enumerate(nodes)}


def _sorted_groups(groups, order):
    groups = [sorted(g, key=order.__getitem__) for g in groups if g]
    return sorted(groups, key=lambda g: (-len(g), [order[n] for n in g]))


def _from_rules(method, rules, nodes, info=None):
    return Grouping(method, [r.all_clause_ids for r in rules],
                    [n.node_id for n in nodes],
                    core=[r.clause_ids for r in rules], info=info)


# ---- the community-detection pipeline, with the detector pluggable -------

def louvain_detector(g, resolution, seed):
    return _cluster._base_communities(g, resolution, seed)


def leiden_detector(g, resolution, seed):
    """Leiden with the modularity objective, on the same weighted graph.

    igraph draws from Python's `random` interface; it is given its own
    seeded generator, so the call neither depends on nor disturbs any
    other random state. Nodes enter igraph in description order.
    """
    ig = require('igraph', 'Leiden community detection (Paper A)', 'igraph')
    order = g.graph.get('order') or {n: i for i, n in enumerate(g.nodes)}
    names = sorted(g.nodes, key=order.__getitem__)
    index = {n: i for i, n in enumerate(names)}
    edges, weights = [], []
    for a, b, data in sorted(g.edges(data=True),
                             key=lambda e: (index[e[0]], index[e[1]])):
        edges.append((index[a], index[b]))
        weights.append(data['weight'])
    graph = ig.Graph(n=len(names), edges=edges)
    ig.set_random_number_generator(random.Random(seed))  # nosec B311
    try:
        parts = graph.community_leiden(objective_function='modularity',
                                       weights=weights or None,
                                       resolution=resolution,
                                       n_iterations=-1)
    finally:
        ig.set_random_number_generator(random)
    groups = [[names[i] for i in members] for members in parts]
    return _sorted_groups(groups, order)


def detect(graph, detector, resolution, seed, overlap=True, weights=None,
           overlap_threshold=_cluster.DEFAULT_OVERLAP_THRESHOLD,
           min_size=2):
    """`lgref.identify.cluster.cluster` with the community detector
    swappable and the overlap machinery switchable.

    overlap=True is exactly `cluster`'s pipeline (tested equal for the
    Louvain detector). overlap=False partitions the WHOLE graph, generic
    statements included, and attaches nothing afterwards.
    """
    g = _cluster.weighted_graph(graph, weights)
    generic = set()
    if overlap:
        generic = {n.node_id for n in graph.nodes if n.generic_effect}
    partition_graph = g.subgraph(
        [n for n in g.nodes if n not in generic]).copy() if generic else g
    if 'order' not in partition_graph.graph:
        partition_graph.graph['order'] = g.graph['order']
    ordered = detector(partition_graph, resolution, seed)
    extra, served = {}, {}
    if overlap:
        extra = _cluster._shared_members(partition_graph, ordered,
                                         overlap_threshold)
        served = (_cluster._generic_service(g, ordered, generic)
                  if generic else {})
    rules, dropped = [], set()
    for idx, comm in enumerate(ordered):
        if len(comm) < min_size:
            dropped |= set(comm)
            continue
        shared = set(extra.get(idx, set())) | served.get(idx, set())
        rules.append(_cluster.CandidateRule(
            'R{:02d}'.format(len(rules)), comm, shared, graph))
    _cluster.assign_ownership(rules, graph)
    return rules, sorted(dropped)


def production_resolution(graph, seed=0):
    """The resolution production LGREF uses: the coverage rule."""
    return _cluster.calibrate_resolution(graph, seed=seed)


# ---- the methods --------------------------------------------------------

def lgref(nodes, seed=0, resolution=None, tolerance=None, **kw):
    """Production LGREF. Keyword arguments (`weights`,
    `overlap_threshold`) reach both the clustering and the coverage rule
    that picks the resolution, so a sensitivity variant is calibrated on
    the graph it clusters, as production would be."""
    graph = ClauseGraph(nodes)
    if resolution is None:
        calibrate = {k: v for k, v in kw.items()
                     if k in ('weights', 'overlap_threshold')}
        if tolerance is not None:
            calibrate['tolerance'] = tolerance
        resolution = _cluster.calibrate_resolution(graph, seed=seed,
                                                   **calibrate)
    rules, _ = detect(graph, louvain_detector, resolution, seed, **kw)
    return _from_rules('lgref', rules, nodes, {'resolution': resolution})


def louvain_hard(nodes, seed=0, resolution=None, **kw):
    graph = ClauseGraph(nodes)
    if resolution is None:
        resolution = production_resolution(graph, seed)
    rules, _ = detect(graph, louvain_detector, resolution, seed,
                      overlap=False, **kw)
    return _from_rules('louvain_hard', rules, nodes,
                       {'resolution': resolution})


def leiden(nodes, seed=0, resolution=None, **kw):
    graph = ClauseGraph(nodes)
    if resolution is None:
        resolution = production_resolution(graph, seed)
    rules, _ = detect(graph, leiden_detector, resolution, seed, **kw)
    return _from_rules('leiden', rules, nodes, {'resolution': resolution})


def leiden_hard(nodes, seed=0, resolution=None, **kw):
    graph = ClauseGraph(nodes)
    if resolution is None:
        resolution = production_resolution(graph, seed)
    rules, _ = detect(graph, leiden_detector, resolution, seed,
                      overlap=False, **kw)
    return _from_rules('leiden_hard', rules, nodes,
                       {'resolution': resolution})


def _tanimoto_vectors(g):
    """Each node's weighted adjacency vector, INCLUSIVE: a node's entry
    for itself is the mean weight of its edges (Ahn et al., weighted
    variant)."""
    vectors = {}
    for node in g.nodes:
        row = {other: data['weight'] for other, data in g[node].items()}
        if row:
            row[node] = sum(row.values()) / len(row)
        vectors[node] = row
    return vectors


def _tanimoto(a, b):
    dot = sum(w * b.get(k, 0.0) for k, w in a.items())
    na = sum(w * w for w in a.values())
    nb = sum(w * w for w in b.values())
    denominator = na + nb - dot
    return dot / denominator if denominator > 0 else 0.0


def link_communities(nodes, seed=0, weights=None, **_kw):
    """Ahn et al.'s link communities on the weighted statement graph."""
    graph = ClauseGraph(nodes)
    g = _cluster.weighted_graph(graph, weights)
    order = _order(nodes)
    communities, density = link_communities_of(g, order)
    groups = _sorted_groups(communities, order)
    return Grouping('link_communities', groups,
                    [n.node_id for n in nodes],
                    info={'partition_density': density,
                          'n_link_communities': len(groups)})


def link_communities_of(g, order):
    """(node communities, partition density) of a weighted graph.

    Edges sharing a node k are compared through the Tanimoto similarity
    of their other ends' inclusive weight vectors, merged by single
    linkage from the most similar down, and the dendrogram is cut where
    the partition density D = (2/M) sum_c m_c (m_c - n_c + 1) /
    ((n_c - 2)(n_c - 1)) is highest. Pairs tied in similarity are merged
    together, so the cut never separates them. A community of edges is
    returned as the set of nodes those edges touch.
    """
    def edge(a, b):
        return tuple(sorted((a, b), key=order.__getitem__))

    edges = sorted((edge(a, b) for a, b in g.edges()),
                   key=lambda e: (order[e[0]], order[e[1]]))
    if not edges:
        return [], 0.0
    edge_index = {e: i for i, e in enumerate(edges)}
    vectors = _tanimoto_vectors(g)

    pairs = []
    for k in sorted(g.nodes, key=order.__getitem__):
        incident = sorted(g[k], key=order.__getitem__)
        for x in range(len(incident)):
            for y in range(x + 1, len(incident)):
                i, j = incident[x], incident[y]
                s = _tanimoto(vectors[i], vectors[j])
                e1, e2 = edge_index[edge(k, i)], edge_index[edge(k, j)]
                pairs.append((-round(s, 12), min(e1, e2), max(e1, e2)))
    pairs.sort()

    parent = list(range(len(edges)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    members = {i: {i} for i in range(len(edges))}
    nodes_of = {i: set(edges[i]) for i in range(len(edges))}

    def term(m, n):
        return 0.0 if n <= 2 else m * (m - (n - 1)) / ((n - 2) * (n - 1.0))

    density = 0.0  # every community a single edge: n = 2, term 0
    best = (density, {i: set(m) for i, m in members.items()})
    position = 0
    while position < len(pairs):
        level = pairs[position][0]
        while position < len(pairs) and pairs[position][0] == level:
            _s, e1, e2 = pairs[position]
            position += 1
            r1, r2 = sorted((find(e1), find(e2)))
            if r1 == r2:
                continue
            density -= term(len(members[r1]), len(nodes_of[r1]))
            density -= term(len(members[r2]), len(nodes_of[r2]))
            parent[r2] = r1
            members[r1] |= members.pop(r2)
            nodes_of[r1] |= nodes_of.pop(r2)
            density += term(len(members[r1]), len(nodes_of[r1]))
        if density > best[0] + 1e-12:
            best = (density, {i: set(m) for i, m in members.items()})
    communities = [{n for e in m for n in edges[e]}
                   for m in best[1].values()]
    return communities, 2.0 * best[0] / len(edges)


def dependency_louvain(nodes, seed=0, resolution=1.0, **_kw):
    """Louvain on the plain call graph: predicate edges, unit weight."""
    graph = ClauseGraph(nodes)
    for kind in list(graph.edges):
        if kind != 'predicate':
            graph.edges[kind] = set()
    rules, _ = detect(graph, louvain_detector, resolution, seed,
                      overlap=False, weights={'predicate': 1.0})
    return _from_rules('dependency_louvain', rules, nodes,
                       {'resolution': resolution})


def components(nodes, seed=0, weights=None, **_kw):
    graph = ClauseGraph(nodes)
    g = _cluster.weighted_graph(graph, weights)
    order = _order(nodes)
    parts = [c for c in nx.connected_components(g) if len(c) >= 2]
    return Grouping('components', _sorted_groups(parts, order),
                    [n.node_id for n in nodes])


def name_tokens(nodes, seed=0, **_kw):
    assignment = baseline_name_similarity(nodes)
    by_token = collections.defaultdict(set)
    for node_id, tokens in assignment.items():
        for token in tokens:
            by_token[token].add(node_id)
    order = _order(nodes)
    return Grouping('name_tokens', _sorted_groups(by_token.values(), order),
                    [n.node_id for n in nodes])


def singletons(nodes, seed=0, **_kw):
    return Grouping('singletons', [{n.node_id} for n in nodes],
                    [n.node_id for n in nodes])


def one_group(nodes, seed=0, **_kw):
    return Grouping('one_group', [{n.node_id for n in nodes}],
                    [n.node_id for n in nodes])


def random_matched(nodes, seed=0, reference=None, **_kw):
    """LGREF's grouping under a seeded random permutation of statements.

    Keeps the number of groups, their sizes, the overlap pattern and the
    number of unclustered statements; destroys any information about
    WHICH statements go together. `reference` is the grouping to permute
    (default: LGREF at seed 0, so the shape does not vary with `seed`).
    """
    reference = reference or lgref(nodes, seed=0)
    ids = [n.node_id for n in nodes]
    shuffled = list(ids)
    random.Random(seed).shuffle(shuffled)  # nosec B311: a baseline
    mapping = dict(zip(ids, shuffled))
    return Grouping('random_matched',
                    [{mapping[n] for n in g} for g in reference.groups],
                    ids, core=[{mapping[n] for n in c}
                               for c in reference.core])


METHODS = collections.OrderedDict([
    ('lgref', lgref),
    ('louvain_hard', louvain_hard),
    ('leiden', leiden),
    ('leiden_hard', leiden_hard),
    ('link_communities', link_communities),
    ('dependency_louvain', dependency_louvain),
    ('components', components),
    ('name_tokens', name_tokens),
    ('singletons', singletons),
    ('one_group', one_group),
    ('random_matched', random_matched),
])

#: Methods whose answer depends on the seed.
SEEDED = frozenset({'lgref', 'louvain_hard', 'leiden', 'leiden_hard',
                    'dependency_louvain',
                    'random_matched'})


# ---- POST-FREEZE (#394) ---------------------------------------------------
#
# Methods added AFTER the freeze at ab7b33b, at the user's instruction.
# They are kept out of METHODS, so no default run -- and no frozen
# result -- includes them; they run only when named, and every report
# labels them POST-FREEZE beside the frozen numbers, never in their place.

def lgref_postfreeze_noterminal(nodes, seed=0, **kw):
    """Production LGREF with the TERMINAL edge weight set to 0. On the
    revised development sheets (a subjective metric) this beat
    production beyond its interval, +0.045 BCubed F1 [0.003, 0.090],
    after the freeze; the user asked for it to be run and reported."""
    weights = dict(_cluster.DEFAULT_WEIGHTS)
    weights['terminal'] = 0.0
    grouping = lgref(nodes, seed=seed, weights=weights, **kw)
    grouping.method = 'lgref_postfreeze_noterminal'
    return grouping


POSTFREEZE = collections.OrderedDict([
    ('lgref_postfreeze_noterminal', lgref_postfreeze_noterminal),
])

SEEDED = SEEDED | frozenset(POSTFREEZE)


def run(method, nodes, seed=0, **kw):
    if method in POSTFREEZE:
        return POSTFREEZE[method](nodes, seed=seed, **kw)
    return METHODS[method](nodes, seed=seed, **kw)
