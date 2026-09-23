"""Cluster formal clauses into candidate rules.

Phase 1 step three (issue #187). Takes the typed clause dependency graph
and proposes candidate RULES — groups of clauses that jointly implement
one gameplay provision.

GROUPING PRINCIPLE

Clauses are grouped by the BEHAVIOUR they jointly implement, never by a
shared strategic function. Two rules that both aid escape stay two rules.
This is not a stylistic preference: grouping by function would require
knowing a rule's function before finding its boundaries, and Phase 2
infers function FROM these boundaries. That would be circular, and the
resulting "discovery" would be an artefact of the assumption.

Nothing in this module may read the designer's labels. Enforced by
lgref/tests/test_label_isolation.py, which fails the build if anything
under identify/ so much as names that directory in a string.

OVERLAP IS EXPECTED

A clause may belong to several rules. `friend_at` is consulted by every
non-king move rule; `empty` by most. The audit found these shared helpers
directly. A partition that forces each clause into exactly one rule would
have to arbitrarily award such helpers to one owner, so membership here
is soft: a base partition plus explicit multi-assignment of connectors.

EDGE WEIGHTS ARE PARAMETERS, NOT CONSTANTS

The weights below are a stated starting point, exposed so they can be
varied and their influence reported. They are NOT tuned to make Royal
Chess come out nicely — that would fit the instrument to the answer.
Validation against games with hand-verifiable rule boundaries is what
justifies a weighting, and lives in the validation harness.

Rationale for the ordering:

  legality (3.0)  the strongest evidence available. A `legal` clause and
                  the `next` clause performing that action are two halves
                  of one provision by construction, and they are linked by
                  nothing else — they communicate through `does`, which
                  the game manager supplies.
  shared_state (2.5)  after the negation filter, these survive only for
                  rule-signature fluents (boulder_cooldown,
                  captured_friendly, reactive_armed), so they are highly
                  specific.
  temporal (1.5)  a real dependency across a turn boundary, but fluents
                  are read by many clauses, so it is less specific.
  predicate (1.0) the baseline relation; ubiquitous helpers make it the
                  least discriminating.
  terminal (0.5)  every ending condition touches it, so it says little
                  about which rule a clause belongs to.
  same_head (2.0) clauses defining one predicate are the disjunctive
                  cases of a single definition. Strong, but not
                  conclusive: Royal Chess defines `legal` across 44
                  clauses belonging to different rules, so the edge is
                  suppressed between subject-specific variants.
  co_activation (0.0) DISABLED BY DEFAULT, on measurement.

                  The brief asks for dynamic co-activation as a
                  clustering signal, so it was built and tested. Against
                  hand-verified boundaries it made identification WORSE
                  at every setting tried:

                      game        static only   + co-activation
                      tictactoe         0.687             0.663
                      nim               0.753             0.613

                  Raw co-occurrence was far worse still (0.301 and
                  0.251): every clause firing in a state forms a clique,
                  and with ~9 of 34 clauses satisfiable at once that
                  wires unrelated rules together wholesale. Requiring
                  consistent association (Jaccard >= 0.8) reduced the
                  damage without removing it.

                  The likely reason: in a well-formed game most clauses
                  are satisfiable in most states, so co-firing mostly
                  reports "the game is in a normal position" rather than
                  rule membership. The static graph already carries the
                  real relationships.

                  On Royal Chess the same filter still produced 3,737
                  edges from 16 states, and there is no ground truth
                  there to judge it against — which is exactly why the
                  validation games exist.

                  The machinery is kept, and the trace_only baseline
                  still runs, so the finding is reported rather than
                  hidden. Raise the weight only with evidence from a
                  game where it measurably helps.
"""

import collections

from lgref.core.deps import require
nx = require('networkx', 'community detection over the clause graph', 'networkx')


DEFAULT_WEIGHTS = {
    'legality': 3.0,
    'same_head': 2.0,
    'shared_state': 2.5,
    'co_activation': 0.0,   # measured to HURT -- see below
    'temporal': 1.5,
    'predicate': 1.0,
    'terminal': 0.5,
}

# A clause connected into several communities is a shared helper rather
# than a member of one rule. This is the fraction of a clause's weighted
# degree that must fall inside a community for it to be counted a member
# of that community too.
DEFAULT_OVERLAP_THRESHOLD = 0.25


class CandidateRule(object):
    """A proposed rule: the clauses believed to implement it together."""

    __slots__ = ('rule_id', 'clause_ids', 'shared_clause_ids', 'graph')

    def __init__(self, rule_id, clause_ids, shared_clause_ids, graph):
        self.rule_id = rule_id
        self.clause_ids = set(clause_ids)
        self.shared_clause_ids = set(shared_clause_ids)
        self.graph = graph

    @property
    def all_clause_ids(self):
        return self.clause_ids | self.shared_clause_ids

    def nodes(self):
        return [self.graph.by_id[c] for c in sorted(self.all_clause_ids)]

    def action_types(self):
        return sorted({n.action_type for n in self.nodes() if n.action_type})

    def piece_types(self):
        out = set()
        for node in self.nodes():
            out |= node.piece_types
        return sorted(out)

    def fluents(self):
        read, written = set(), set()
        for node in self.nodes():
            read |= node.fluents_read
            written |= node.fluents_written
        return sorted(read), sorted(written)

    def head_predicates(self):
        return sorted({n.head_predicate for n in self.nodes()
                       if n.head_predicate})

    def describe(self):
        """A behavioural summary — what these clauses DO.

        Deliberately not a name for what the rule is for. Naming it would
        smuggle in a functional claim that Phase 2 is supposed to infer
        and Phase 3 to test.
        """
        read, written = self.fluents()
        return {
            'rule_id': self.rule_id,
            'n_clauses': len(self.clause_ids),
            'n_shared': len(self.shared_clause_ids),
            'action_types': self.action_types(),
            'piece_types': self.piece_types(),
            'fluents_written': written,
            'fluents_read': read,
            'head_predicates': self.head_predicates()[:12],
        }

    def __repr__(self):
        return '<CandidateRule {} clauses={}+{} actions={}>'.format(
            self.rule_id, len(self.clause_ids),
            len(self.shared_clause_ids), self.action_types() or '-')


def weighted_graph(clause_graph, weights=None):
    """Collapse the typed multigraph into one weighted undirected graph.

    Edge types are summed: two clauses linked by BOTH a legality and a
    shared-state edge are more strongly related than by either alone.

    Nodes and edges are inserted in SORTED order. The typed edges are
    held in sets, so iterating them directly makes networkx's internal
    node and adjacency order depend on string hashing, which varies per
    process. Louvain then partitions the same graph differently from one
    run to the next -- measured at 18/19/20 clusters over five values of
    PYTHONHASHSEED on the same description. Sorting also fixes the order
    of the float additions below, so the weights themselves are
    bit-identical between runs.
    """
    weights = weights or DEFAULT_WEIGHTS
    g = nx.Graph()
    g.add_nodes_from(sorted(n.node_id for n in clause_graph.nodes))
    for kind in sorted(clause_graph.edges):
        edges = clause_graph.edges[kind]
        w = weights.get(kind, 0.0)
        if w <= 0:
            continue
        for a, b in sorted(edges):
            if g.has_edge(a, b):
                g[a][b]['weight'] += w
            else:
                g.add_edge(a, b, weight=w)
    return g


def _base_communities(g, resolution, seed):
    """Louvain partition of the weighted graph.

    Louvain maximises modularity, which asks whether a group is more
    densely connected internally than chance would predict — the right
    question for "do these clauses belong together". `resolution` trades
    cluster count against size and is exposed rather than fixed, because
    the right granularity is a research question: the boulder's movement,
    blocking and first-turn restriction could be one rule or three,
    depending on the declared analysis granularity.
    """
    communities = nx.community.louvain_communities(
        g, weight='weight', resolution=resolution, seed=seed)
    # Return sorted members in a TOTAL order. `seed` alone does not make
    # this reproducible: louvain returns a list of sets, and sorting by
    # size alone leaves ties broken by set iteration order.
    return sorted((sorted(c) for c in communities),
                  key=lambda c: (-len(c), c))


def _shared_members(g, communities, threshold):
    """Clauses that also belong to communities other than their own.

    A helper like `friend_at` is consulted by many rules. Assigning it to
    exactly one would misrepresent the structure and shrink every other
    rule that depends on it.
    """
    owner = {}
    for idx, comm in enumerate(communities):
        for node in comm:
            owner[node] = idx

    extra = collections.defaultdict(set)
    for node in sorted(g.nodes):
        total = sum(d['weight'] for _, _, d in g.edges(node, data=True))
        if total <= 0:
            continue
        per_comm = collections.Counter()
        for _, other, data in g.edges(node, data=True):
            per_comm[owner.get(other)] += data['weight']
        for comm_idx, w in sorted(per_comm.items(),
                                  key=lambda kv: (kv[0] is None, kv[0])):
            if comm_idx is None or comm_idx == owner.get(node):
                continue
            if w / total >= threshold:
                extra[comm_idx].add(node)
    return extra


# Mean clauses per rule at the resolution VALIDATED against
# hand-verified boundaries: tic-tac-toe 6.0, nim 5.2. A rule is a
# gameplay provision implemented by a handful of clauses, and that is
# roughly scale-free -- a bigger game has more rules, not bigger ones --
# so holding this constant is what "the same granularity" means across
# descriptions of different sizes.
TARGET_CLAUSES_PER_RULE = 5.6


def calibrate_resolution(clause_graph, target=TARGET_CLAUSES_PER_RULE,
                         lo=0.25, hi=64.0, steps=12, **kw):
    """Pick the Louvain resolution that holds mean cluster size at `target`.

    Louvain's `resolution` is a SCALE parameter measured against total
    graph weight, so a value tuned on a 22-34 clause game is
    systematically too coarse on a 522-clause one. Transferring it as a
    constant is a methodological error, not a judgement call: at the
    transferred 1.0, Royal Chess clustered at 20.3 clauses per rule
    against the validated 5.2-6.0, and produced an 80-clause
    `load_bearing` cluster holding the movement rules of every piece.

    Binary search rather than a formula because the relationship between
    resolution and granularity depends on the graph, and a formula would
    be a guess dressed as a derivation. Returns the resolution; the
    caller clusters with it.
    """
    best, best_gap = lo, float('inf')
    for _ in range(steps):
        mid = (lo * hi) ** 0.5            # geometric: resolution is a scale
        rules, _ = cluster(clause_graph, resolution=mid, **kw)
        if not rules:
            hi = mid
            continue
        mean = sum(len(r.clause_ids) for r in rules) / len(rules)
        gap = abs(mean - target)
        if gap < best_gap:
            best, best_gap = mid, gap
        if mean > target:                 # clusters too big -> cut finer
            lo = mid
        else:
            hi = mid
    return best


def cluster(clause_graph, weights=None, resolution=1.0, seed=0,
            overlap_threshold=DEFAULT_OVERLAP_THRESHOLD, min_size=2,
            hold_out_generic=True):
    """Propose candidate rules from the typed clause graph.

    `min_size` drops singletons: a lone clause with no strong tie to
    anything is more likely an isolated helper than a gameplay provision.
    They are still reported by `unclustered` so nothing vanishes silently.

    `hold_out_generic` removes GENERIC EFFECT clauses from the base
    partition and adds them back afterwards as shared members of every
    rule they serve.

    These are the board-update clauses whose `does` term carries a
    VARIABLE in its discriminator slot — `does(M, move(PIECE, ...))`
    applies to every piece, so it is machinery every movement rule relies
    on rather than a member of any one of them. Leaving them in merges
    every rule that produces the action: measured, a single community of
    88-91 clauses spanning five unrelated action types survived EVERY
    resolution setting from 0.5 to 16.0, anchored on clauses with
    weighted degree 262 against a median of 21.

    The criterion is structural, not a tuned degree cut-off: a constant
    in that slot (`(move knight ...)`) means piece-specific, a variable
    means generic. 65 of 488 clauses qualify.
    """
    g = weighted_graph(clause_graph, weights)

    generic = set()
    if hold_out_generic:
        generic = {n.node_id for n in clause_graph.nodes if n.generic_effect}
    partition_graph = g.subgraph(
        [n for n in g.nodes if n not in generic]).copy() if generic else g

    # ONE ordering, fixed before either attachment step. `extra` used to
    # be indexed against the raw louvain order and `served` against the
    # size-sorted one, so whenever sorting moved a community -- which is
    # almost always -- shared helpers were attached to the wrong rules.
    ordered = _base_communities(partition_graph, resolution, seed)
    extra = _shared_members(partition_graph, ordered, overlap_threshold)
    served = _generic_service(g, ordered, generic) if generic else {}

    rules, dropped = [], set()
    for idx, comm in enumerate(ordered):
        if len(comm) < min_size:
            dropped |= set(comm)
            continue
        shared = set(extra.get(idx, set())) | served.get(idx, set())
        rules.append(CandidateRule(
            'R{:02d}'.format(len(rules)), comm, shared, clause_graph))
    return rules, sorted(dropped)


def _generic_service(g, communities, generic_ids):
    """Attach each held-out generic clause to the rules it serves.

    A generic board-update clause belongs to every rule whose clauses it
    is connected to — it is shared machinery, so it appears in several
    rules rather than being awarded to one.
    """
    owner = {}
    for idx, comm in enumerate(communities):
        for node in comm:
            owner[node] = idx

    served = collections.defaultdict(set)
    for node in sorted(generic_ids):
        if node not in g:
            continue
        touched = {owner[other] for _, other in g.edges(node)
                   if other in owner}
        for idx in sorted(touched):
            served[idx].add(node)
    return served


def summarize(rules):
    return [r.describe() for r in rules]
