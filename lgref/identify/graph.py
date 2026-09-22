"""Typed clause dependency graph.

Phase 1 step two (issue #187). Nodes are normalised clauses
(`lgref.identify.clauses`); edges are the typed dependencies clustering
will use to find rule boundaries.

EDGE TYPES, and why each is separate rather than one "depends on"

  predicate     clause B's body calls the predicate clause A defines.
                The immediate, same-turn dependency.

  shared_state  A and B both read the same fluent. Not a direction — a
                mutual signal that two clauses consult the same piece of
                state, which is strong evidence they implement one rule
                even when neither calls the other.

  legality      a `legal` clause and the `next` clause that carries out
                the same action. Legality and transition are two halves
                of one provision, and nothing in the predicate graph
                connects them: they communicate through `does`, which is
                supplied by the game manager, not by either clause.

  temporal      A writes a fluent that B reads. This spans a TURN
                BOUNDARY, which is why it cannot be merged with the
                predicate edge. The boulder's cooldown, the manipulation
                freeze and the bishop's reactive arming are all rules
                whose two halves are separated in time; a graph without
                this edge type cannot see them as one rule.

  terminal      both clauses feed the terminal/goal/lost condition.

  co_activation added later from traces: clauses that fire together in
                real games. Static structure alone cannot distinguish a
                helper genuinely shared by two rules from one that merely
                could be.

Weights are deliberately NOT tuned here. Clustering reads the typed
graph and decides; baking a weighting in would hide the choice inside the
graph construction where nobody can vary it.
"""

import collections
import itertools


EDGE_TYPES = ('predicate', 'shared_state', 'legality', 'temporal',
              'terminal', 'co_activation')

# A fluent read by a large share of all clauses is infrastructure, not a
# rule signature: linking every reader would produce one giant component
# and destroy the partition before clustering starts. The cut is a
# FRACTION of clauses rather than a fixed name list, so it calibrates to
# whatever game is being analysed.
#
# Measured on Royal Chess (488 clauses): cell 95 readers (19%),
# control 48 (10%), queen_form 45 (9%), invulnerable 29 (6%),
# manipulation_freeze 21 (4%), then a sharp drop to 7 and below. A
# threshold of 8% isolates the three that are genuinely board-wide
# infrastructure. Another game's distribution will differ, and the
# fraction adapts.
UBIQUITOUS_READ_FRACTION = 0.08

# Below this many clauses there is no distribution to speak of, so the
# ubiquity cut is skipped entirely rather than applied to noise.
MIN_CLAUSES_FOR_UBIQUITY_CUT = 20


class ClauseGraph(object):
    """Typed multigraph over clause nodes.

    Edges are stored per type so clustering can weight them separately,
    and so a rule identified through temporal structure can be told apart
    from one identified through shared predicates.
    """

    def __init__(self, nodes):
        self.nodes = list(nodes)
        self.by_id = {n.node_id: n for n in self.nodes}
        self.edges = {t: set() for t in EDGE_TYPES}
        self._build()

    # ---- construction ----------------------------------------------------

    def _build(self):
        defines = collections.defaultdict(list)
        for node in self.nodes:
            if node.head_predicate:
                defines[node.head_predicate].append(node)

        writes = collections.defaultdict(list)
        reads = collections.defaultdict(list)
        for node in self.nodes:
            for fluent in node.fluents_written:
                writes[fluent].append(node)
            for fluent in node.fluents_read:
                reads[fluent].append(node)

        self._predicate_edges(defines)
        self._temporal_edges(writes, reads)
        self._shared_state_edges(reads)
        self._legality_edges()
        self._terminal_edges()

    def _add(self, kind, a, b, directed=True):
        if a.node_id == b.node_id:
            return
        if directed:
            self.edges[kind].add((a.node_id, b.node_id))
        else:
            pair = tuple(sorted((a.node_id, b.node_id)))
            self.edges[kind].add(pair)

    def _predicate_edges(self, defines):
        """A -> B when B's body calls the predicate A defines."""
        for node in self.nodes:
            for pred in node.body_predicates:
                for definer in defines.get(pred, ()):
                    self._add('predicate', definer, node)

    def _temporal_edges(self, writes, reads):
        """A -> B when A writes a fluent B reads — across a turn boundary.

        Excludes a clause's own read-then-write of the same fluent (the
        persistence pattern, `(<= (next (X)) (true (X)) ...)`), which is
        self-continuity rather than a dependency between two clauses.
        """
        for fluent, writers in writes.items():
            for writer in writers:
                for reader in reads.get(fluent, ()):
                    if reader.node_id == writer.node_id:
                        continue
                    self._add('temporal', writer, reader)

    def _shared_state_edges(self, reads):
        """Undirected: two clauses POSITIVELY consult the same fluent.

        Negated reads are excluded, and that distinction does real work.
        `invulnerable` is read by 29 clauses and `manipulation_freeze` by
        21, almost always as `(not (true (...)))` — a guard. A guard means
        one rule CONSTRAINING another, not two clauses implementing one
        rule together. Linking all 29 capture rules because each checks
        invulnerability would merge every capturing rule in the game into
        a single cluster.

        A positive read is different: two clauses that both require the
        same fluent to hold are reasoning about the same piece of state,
        which is genuine evidence of shared membership.

        This replaced an arbitrary "skip fluents with more than 40
        readers" cut-off. The negation criterion is principled rather
        than tuned, and it happens to separate the same infrastructure
        the threshold was groping for.
        """
        # The ubiquity cut needs enough clauses to estimate a
        # distribution. Below that it would exclude everything — in a
        # two-clause graph, any fluent both clauses read is "100% of
        # them" — so small descriptions keep all their shared-state
        # edges.
        cutoff = None
        if len(self.nodes) >= MIN_CLAUSES_FOR_UBIQUITY_CUT:
            cutoff = max(3, int(UBIQUITOUS_READ_FRACTION * len(self.nodes)))
        for fluent, readers in reads.items():
            if cutoff is not None and len(readers) >= cutoff:
                continue
            positive = [n for n in readers if fluent not in n.negated_goals]
            for a, b in itertools.combinations(positive, 2):
                self._add('shared_state', a, b, directed=False)

    def _legality_edges(self):
        """Undirected: `legal` clause <-> `next` clause for one action.

        These communicate only through `does`, which the game manager
        supplies, so no predicate edge ever links them — yet permitting an
        action and carrying it out are one provision.
        """
        legal_by_action = collections.defaultdict(list)
        next_by_action = collections.defaultdict(list)
        for node in self.nodes:
            if node.head_kind == 'legal' and node.action_type:
                legal_by_action[node.action_type].append(node)
            for action in node.actions_read:
                next_by_action[action].append(node)
        for action, legals in legal_by_action.items():
            for legal_node in legals:
                for effect in next_by_action.get(action, ()):
                    self._add('legality', legal_node, effect, directed=False)

    def _terminal_edges(self):
        """Undirected: clauses that both feed the ending condition."""
        terminal_nodes = [n for n in self.nodes if n.terminal_dependency]
        for a, b in itertools.combinations(terminal_nodes, 2):
            self._add('terminal', a, b, directed=False)

    # ---- traces ----------------------------------------------------------

    def add_co_activation(self, clause_id_sets):
        """Add co-activation edges from observed traces.

        `clause_id_sets` is an iterable of sets of node ids that fired
        together. Static structure cannot distinguish a helper genuinely
        shared between two rules from one that merely could be; only
        watching real games can.
        """
        for fired in clause_id_sets:
            known = [cid for cid in fired if cid in self.by_id]
            for a, b in itertools.combinations(sorted(known), 2):
                self.edges['co_activation'].add((a, b))

    # ---- inspection ------------------------------------------------------

    def edge_count(self, kind=None):
        if kind is not None:
            return len(self.edges[kind])
        return sum(len(v) for v in self.edges.values())

    def neighbours(self, node_id, kinds=None):
        """Every node connected to `node_id`, ignoring direction."""
        kinds = kinds or EDGE_TYPES
        out = set()
        for kind in kinds:
            for a, b in self.edges[kind]:
                if a == node_id:
                    out.add(b)
                elif b == node_id:
                    out.add(a)
        return out

    def summary(self):
        return {
            'nodes': len(self.nodes),
            'edges_total': self.edge_count(),
            'edges_by_type': {k: len(v) for k, v in self.edges.items()},
        }


def build(path='docs/gdl/integrated.gdl'):
    from lgref.identify.clauses import load
    return ClauseGraph(load(path))
