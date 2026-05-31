"""GGP Resolver — backward-chaining query with unification +
negation-as-failure.

A QUERY is a goal term (with or without variables) such as
('role', '?x') or ('legal', 'white', ('move', 'king', 'g', '1',
'f', '1')).

The resolver returns a generator over BINDINGS — each binding is
a dict mapping variable name → atom (or nested-tuple). An empty
dict means the ground query succeeded with no variables.

Body operators supported:
  - `(not <goal>)`           — negation-as-failure (closed world)
  - `(or <g1> <g2> ...)`     — disjunction
  - `(and <g1> <g2> ...)`    — conjunction (equivalent to listing)
  - `(distinct ?x ?y)`       — builtin inequality
  - `(= ?x ?y)`              — builtin equality (unification)
  - anything else            — recursive query against the KB
"""

from .parser import is_variable


# ---- substitution + unification ------------------------------------------

def _walk(term, subst):
    """Follow variable bindings until we hit a non-variable or
    an unbound variable."""
    while is_variable(term) and term in subst:
        term = subst[term]
    return term


def _substitute(term, subst):
    """Recursively apply a substitution to a term, returning the
    resulting (partially or fully) ground term."""
    term = _walk(term, subst)
    if isinstance(term, tuple):
        return tuple(_substitute(c, subst) for c in term)
    return term


def _occurs(var, term, subst):
    """Occurs check — prevents x = (f x) infinite expansion."""
    term = _walk(term, subst)
    if term == var:
        return True
    if isinstance(term, tuple):
        return any(_occurs(var, c, subst) for c in term)
    return False


def _unify(a, b, subst):
    """Try to unify two terms under the existing substitution.
    Returns the extended substitution (a copy), or None on
    failure."""
    a = _walk(a, subst)
    b = _walk(b, subst)
    if a == b:
        return subst
    if is_variable(a):
        if _occurs(a, b, subst):
            return None
        new = dict(subst)
        new[a] = b
        return new
    if is_variable(b):
        if _occurs(b, a, subst):
            return None
        new = dict(subst)
        new[b] = a
        return new
    if isinstance(a, tuple) and isinstance(b, tuple):
        if len(a) != len(b):
            return None
        for sa, sb in zip(a, b):
            subst = _unify(sa, sb, subst)
            if subst is None:
                return None
        return subst
    return None


# ---- variable renaming for rule heads/bodies ----------------------------

_counter = [0]


def _rename_vars(term, mapping):
    """Walk the term and rename every variable using `mapping`
    (mutated as we go). Used to give each rule clause fresh
    variable names per invocation so they don't collide with the
    caller's variables."""
    if is_variable(term):
        if term not in mapping:
            _counter[0] += 1
            mapping[term] = f'?_v{_counter[0]}'
        return mapping[term]
    if isinstance(term, tuple):
        return tuple(_rename_vars(c, mapping) for c in term)
    return term


# ---- the Resolver --------------------------------------------------------

def _freeze(term):
    """Convert a term to a hashable canonical form."""
    if isinstance(term, tuple):
        return tuple(_freeze(c) for c in term)
    return term


def _collect_variables(term):
    """Walk a term and yield each unique variable name."""
    seen = set()

    def _walk_term(t):
        if is_variable(t):
            if t not in seen:
                seen.add(t)
                yield t
        elif isinstance(t, tuple):
            for c in t:
                yield from _walk_term(c)
    return list(_walk_term(term))


class Resolver:
    """Backward-chaining resolver over a KnowledgeBase."""

    def __init__(self, kb):
        self.kb = kb

    def query(self, goal):
        """Public query: yields a binding dict for each DISTINCT
        successful derivation. The dict's keys are the variables
        that appeared in the ORIGINAL goal; the values are the
        fully-resolved bindings (renamed-internal variables walked
        out).

        DEDUPLICATION: pure backward chaining can derive the same
        answer many times via different proof paths (especially in
        the presence of symmetric rules like `(file_adj ?x ?y) :-
        (file_adj ?y ?x)`). The public API yields each unique
        binding once.

        This is the API the GGP engine + tests should call.
        """
        original_vars = _collect_variables(goal)
        seen = set()
        for subst in self._query(goal):
            clean = {}
            for v in original_vars:
                clean[v] = _substitute(v, subst)
            # Hash via a stable freeze: tuples of (var, value) sorted.
            key = tuple(sorted(
                (v, _freeze(clean[v])) for v in original_vars))
            if key in seen:
                continue
            seen.add(key)
            yield clean

    def _query(self, goal, subst=None, depth=0):
        """Internal: yields raw substitutions (may contain renamed
        internal variables in the values). Callers in resolver.py
        chain into this directly; external callers should use
        the public `query` method which cleans up bindings.
        """
        if subst is None:
            subst = {}
        # Resolve any already-bound variables.
        goal = _substitute(goal, subst)

        if depth > 200:
            # Recursion guard — GDL programs CAN have deep
            # recursion but step-1 / step-2 should bottom out
            # quickly. Subsequent steps may need this lifted.
            return

        # Handle the special body operators first.
        if isinstance(goal, tuple) and goal:
            op = goal[0]
            if op == 'not':
                # Negation-as-failure.
                inner = goal[1]
                solutions = self._query(inner, subst, depth + 1)
                if next(solutions, None) is None:
                    yield subst
                return
            if op == 'or':
                for alt in goal[1:]:
                    yield from self._query(alt, subst, depth + 1)
                return
            if op == 'and':
                yield from self._query_conjunction(
                    list(goal[1:]), subst, depth + 1)
                return
            if op == 'distinct':
                a = _walk(goal[1], subst)
                b = _walk(goal[2], subst)
                if a != b:
                    yield subst
                return
            if op == '=':
                # Unification operator.
                new_subst = _unify(goal[1], goal[2], subst)
                if new_subst is not None:
                    yield new_subst
                return

        # Otherwise: query against the KB.
        pred = goal[0] if isinstance(goal, tuple) and goal else goal

        # 1) Try matching facts.
        for fact in self.kb.facts_for(pred):
            new_subst = _unify(goal, fact, subst)
            if new_subst is not None:
                yield new_subst

        # 2) Try matching rules (with fresh variable renaming).
        for head, body in self.kb.rules_for(pred):
            rename_map = {}
            renamed_head = _rename_vars(head, rename_map)
            renamed_body = [_rename_vars(b, rename_map) for b in body]
            new_subst = _unify(goal, renamed_head, subst)
            if new_subst is None:
                continue
            yield from self._query_conjunction(
                renamed_body, new_subst, depth + 1)

    def _query_conjunction(self, goals, subst, depth):
        """Solve a sequence of goals as a conjunction. Each
        binding extends the substitution."""
        if not goals:
            yield subst
            return
        head, *rest = goals
        for new_subst in self._query(head, subst, depth):
            yield from self._query_conjunction(rest, new_subst, depth)
