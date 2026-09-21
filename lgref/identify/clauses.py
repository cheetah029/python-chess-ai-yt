"""Normalise GDL clauses into typed nodes for the dependency graph.

Phase 1 step one (issue #187): formal clauses -> rules. A *formal clause*
is one statement in `integrated.gdl`; a *rule* is a gameplay provision
implemented by one or more of them. This module builds the clause nodes;
clustering them into rules happens downstream.

Two structural facts from the GDL audit shape the node types, and getting
either wrong would distort identification before clustering even runs:

1. DERIVED PREDICATES AND FLUENTS ARE DIFFERENT THINGS. `(<= (foo) ...)`
   defines a predicate recomputed on demand; `(true (foo))` reads a fluent
   carried in game state, written by `(next (foo))`. They have different
   dependency semantics — a fluent creates a TEMPORAL edge from the clause
   that writes it to the clause that reads it, a derived predicate creates
   an immediate one. Conflating them was a real defect (#177 B4, the
   tiny-endgame rule), and would mistype that cluster regardless.

2. THE `_except` FAMILY IS MECHANICALLY DERIVED. The vacated-origin bishop
   fix added `occupied_except`, `sweep_path_except` and friends — same
   bodies as their bases with one extra excluded square. They are an
   encoding workaround for GDL's inability to evaluate in a hypothetical
   state, not separate game concepts, so they are canonicalised onto their
   base predicate. Left alone, the bishop-teleport rule would appear at
   twice its true size.

Nothing here reasons about strategic function. Clauses are grouped
downstream by the behaviour they implement, never by what that behaviour
might be FOR — otherwise identification would need to know a rule's
function before finding its boundaries, which is circular.
"""

import re


# GDL forms that are structural rather than game predicates.
CONTROL_FORMS = frozenset({
    '<=', 'not', 'or', 'and', 'distinct', 'true', 'next', 'does', 'init',
    'base', 'input',
})

# The keywords every GDL game defines, which carry fixed meaning.
ROLE_FORMS = frozenset({'role', 'legal', 'goal', 'terminal', 'init', 'next'})

# Piece vocabulary of this variant. Used to tag clauses by the pieces they
# mention, which is a behavioural signal (a clause about knights implements
# knight behaviour) and not a strategic one.
PIECE_TYPES = frozenset({
    'king', 'queen', 'rook', 'bishop', 'knight', 'pawn', 'boulder',
})

ACTION_TYPES = frozenset({
    'move', 'transform', 'manipulate', 'manipulate_promote', 'promote',
    'jump_capture', 'reactive_capture', 'noop',
})

_EXCEPT_SUFFIX = '_except'


def canonical_predicate(name):
    """Map a mechanically derived predicate onto its base.

    `occupied_except` -> `occupied`. These variants exist only because GDL
    cannot evaluate a body in a hypothetical state, so the vacated square
    has to be threaded through as extra arguments (see the bishop
    teleport-safety rules). Treating them as distinct concepts would
    double-count the rule that uses them.
    """
    if name.endswith(_EXCEPT_SUFFIX) and len(name) > len(_EXCEPT_SUFFIX):
        return name[:-len(_EXCEPT_SUFFIX)]
    return name


def is_variable(term):
    return isinstance(term, str) and term.startswith('?')


def head_predicate(term):
    """Predicate name of a head or goal term, or None."""
    if isinstance(term, tuple) and term:
        return term[0] if isinstance(term[0], str) else None
    if isinstance(term, str):
        return term
    return None


class ClauseNode(object):
    """One formal clause, typed for graph construction.

    Attributes describe WHAT THE CLAUSE DOES, never what it is for:

        index               position in the source file, for stable ids
        kind                'rule' | 'fact'
        head_predicate      predicate this clause defines
        head_kind           'derived' | 'fluent_write' | 'legal' | 'fact' ...
        body_predicates     derived predicates the body calls
        fluents_read        fluents read via (true (X ...))
        fluents_written     fluents written via (next (X ...))
        actions_read        actions inspected via (does ?p (X ...))
        action_type         action this clause makes legal, if any
        piece_types         piece names mentioned
        negated_goals       goals appearing under (not ...)
        terminal_dependency clause participates in terminal/goal/lost
        arity               head arity
    """

    __slots__ = ('index', 'kind', 'raw', 'head_predicate', 'head_kind',
                 'body_predicates', 'fluents_read', 'fluents_written',
                 'actions_read', 'action_type', 'piece_types',
                 'negated_goals', 'terminal_dependency', 'arity',
                 'generic_effect')

    def __init__(self, index, form):
        self.index = index
        self.raw = form
        self.kind = 'rule' if (isinstance(form, tuple) and form
                               and form[0] == '<=') else 'fact'
        head = form[1] if self.kind == 'rule' else form
        body = list(form[2:]) if self.kind == 'rule' else []

        self.body_predicates = set()
        self.fluents_read = set()
        self.fluents_written = set()
        self.actions_read = set()
        self.piece_types = set()
        self.negated_goals = set()
        self.action_type = None
        self.generic_effect = False

        self._classify_head(head)
        for goal in body:
            self._walk_goal(goal, negated=False)
        self._collect_pieces(form)
        self.terminal_dependency = self._is_terminal_related()

    # ---- head ------------------------------------------------------------

    def _classify_head(self, head):
        pred = head_predicate(head)
        self.arity = (len(head) - 1) if isinstance(head, tuple) else 0

        if pred == 'next' and isinstance(head, tuple) and len(head) > 1:
            inner = head[1]
            name = canonical_predicate(head_predicate(inner) or 'next')
            self.head_predicate = name
            self.head_kind = 'fluent_write'
            self.fluents_written.add(name)
            return
        if pred == 'init' and isinstance(head, tuple) and len(head) > 1:
            name = canonical_predicate(head_predicate(head[1]) or 'init')
            self.head_predicate = name
            self.head_kind = 'fluent_init'
            self.fluents_written.add(name)
            return
        if pred == 'legal' and isinstance(head, tuple) and len(head) > 2:
            self.head_predicate = 'legal'
            self.head_kind = 'legal'
            action = head[2]
            action_name = head_predicate(action)
            if action_name in ACTION_TYPES:
                self.action_type = action_name
            return
        if pred in ('terminal', 'goal', 'role'):
            self.head_predicate = pred
            self.head_kind = pred
            return

        self.head_predicate = canonical_predicate(pred) if pred else None
        self.head_kind = 'derived' if self.kind == 'rule' else 'fact'

    # ---- body ------------------------------------------------------------

    def _walk_goal(self, goal, negated):
        if not isinstance(goal, tuple) or not goal:
            return
        name = goal[0]

        if name == 'not':
            for sub in goal[1:]:
                self._walk_goal(sub, negated=True)
            return
        if name in ('or', 'and'):
            for sub in goal[1:]:
                self._walk_goal(sub, negated)
            return
        if name == 'true' and len(goal) > 1:
            fluent = canonical_predicate(head_predicate(goal[1]) or '')
            if fluent:
                self.fluents_read.add(fluent)
                if negated:
                    self.negated_goals.add(fluent)
            return
        if name == 'does' and len(goal) > 2:
            action = goal[2]
            action_name = head_predicate(action)
            if action_name:
                self.actions_read.add(action_name)
            # A `does` term whose discriminator slot holds a VARIABLE
            # applies to every value of it. `(does ?m (move ?piece ...))`
            # is the board-update machinery every piece's move rule
            # relies on; `(does ?m (move knight ...))` would be specific
            # to knights.
            #
            # This matters for clustering, not for legality: such a
            # clause is SHARED infrastructure, and letting it sit inside
            # one cluster merges every rule that produces the action.
            # Measured before this was recognised: a single community of
            # 88-91 clauses survived every resolution setting, spanning
            # five unrelated action types, anchored on these clauses
            # (weighted degree 262 against a median of 21).
            if isinstance(action, tuple) and len(action) > 1 \
                    and is_variable(action[1]):
                self.generic_effect = True
            return
        if name == 'distinct':
            return

        canonical = canonical_predicate(name)
        self.body_predicates.add(canonical)
        if negated:
            self.negated_goals.add(canonical)
        for sub in goal[1:]:
            if isinstance(sub, tuple):
                self._walk_goal(sub, negated)

    # ---- tagging ---------------------------------------------------------

    def _collect_pieces(self, form):
        def walk(term):
            if isinstance(term, str):
                if term in PIECE_TYPES:
                    self.piece_types.add(term)
            elif isinstance(term, tuple):
                for child in term:
                    walk(child)
        walk(form)

    def _is_terminal_related(self):
        if self.head_kind in ('terminal', 'goal'):
            return True
        if self.head_predicate in ('lost', 'terminal', 'goal'):
            return True
        return bool({'lost', 'terminal', 'goal'} & self.body_predicates)

    # ---- identity --------------------------------------------------------

    @property
    def node_id(self):
        """Stable id: predicate plus source index.

        The index is included because a predicate is defined by several
        clauses (the disjunction), and those clauses can belong to
        different rules — `legal` alone covers every piece's moves.
        """
        return '{}#{}'.format(self.head_predicate or '?', self.index)

    def __repr__(self):
        return '<ClauseNode {} kind={} pieces={}>'.format(
            self.node_id, self.head_kind, sorted(self.piece_types) or '-')


def normalize(forms):
    """Turn parsed GDL forms into ClauseNodes, source order preserved."""
    return [ClauseNode(i, form) for i, form in enumerate(forms)]


def load(path):
    """Parse a GDL file and normalise it."""
    from ggp.parser import parse
    with open(path) as handle:
        return normalize(parse(handle.read()))
