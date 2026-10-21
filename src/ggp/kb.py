"""GGP Knowledge Base — indexes facts + rules by predicate name.

A FACT is a ground (variable-free) tuple like ('role', 'white').
A RULE is parsed from `(<= head body1 body2 ...)` and stored as
(head, body_list).

Index: facts are stored in a dict keyed by predicate name (first
atom of the tuple) so the resolver can quickly enumerate
candidates for a query like ('role', '?x').

Note: in GDL many facts are stored under a wrapping predicate
like `init` or `true` — we index by the OUTER head, since that's
what the resolver queries.
"""

from .parser import is_variable


# Keywords whose single argument is itself a predicate.
_PREDICATE_ARG = ('true', 'next', 'init')


def canonical(term):
    """One shape for a 0-arity predicate, whatever dialect wrote it.

    GDL sources are inconsistent here and so are callers. Prefix writes
    `(a_capture_turn)` in one place and bare `terminal` in another;
    infix writes both bare; `board_to_gdl_facts` emits one-tuples; and
    `GGPGame.is_terminal` queries the bare string `'terminal'`. As long
    as each side happened to agree the mismatch stayed hidden, and when
    it stopped agreeing the symptom was a rule that silently never
    fired -- engine/GGP agreement fell from 100% to 56% with no error
    anywhere.

    Canonicalising in the KB and at query time makes the shapes
    interchangeable, so no source and no caller has to get it right.
    """
    if isinstance(term, str) and not term.startswith('?'):
        return (term,)
    if isinstance(term, tuple) and term:
        if term[0] == 'not' and len(term) == 2:
            return ('not', canonical(term[1]))
        if term[0] in _PREDICATE_ARG:
            return tuple([term[0]] + [canonical(a) for a in term[1:]])
    return term


def _head_predicate(term):
    """The predicate name of a fact / goal — the first atom in
    a non-empty tuple, else the term itself if atomic."""
    if isinstance(term, tuple) and term:
        return term[0]
    if isinstance(term, str):
        return term
    return None


def _has_variables(term):
    if isinstance(term, str):
        return is_variable(term)
    if isinstance(term, tuple):
        return any(_has_variables(c) for c in term)
    return False


class KnowledgeBase:
    """Holds facts and rules. Facts are ground tuples; rules are
    (head, body) where head and body terms may contain variables.

    Indexed by predicate name for fast candidate lookup. The
    resolver still has to UNIFY each candidate against the query
    — the index just narrows the search."""

    def __init__(self):
        self._facts_by_pred = {}   # pred -> list of fact tuples
        self._rules_by_pred = {}   # pred -> list of (head, body)
        #: (pred, inner head) -> facts. See `_add_fact`.
        self._facts_by_arg = {}

    # ---- ingestion ------------------------------------------------------

    def add_clause(self, form):
        """Add a parsed form. Rules have head '<='; everything
        else is a fact."""
        if isinstance(form, tuple) and form and form[0] == '<=':
            if len(form) < 2:
                raise ValueError('<=-rule with no head')
            head = canonical(form[1])
            body = [canonical(g) for g in form[2:]]
            self._add_rule(head, body)
        else:
            self._add_fact(canonical(form))

    def _add_fact(self, fact):
        if _has_variables(fact):
            # Treat a "fact" with variables as a rule with an
            # empty body (universal). E.g. `(file_eastward ?x ?y)`
            # would behave the same as `(<= (file_eastward ?x ?y))`.
            self._add_rule(fact, [])
            return
        pred = _head_predicate(fact)
        if pred is None:
            raise ValueError(f'cannot index fact {fact!r}')
        self._facts_by_pred.setdefault(pred, []).append(fact)
        # SECOND-LEVEL INDEX on the first argument's own head. GDL wraps
        # the whole state in one predicate -- every state fact is
        # `true(something)` -- so indexing by predicate alone leaves
        # EVERY state fact a candidate for every `true` goal, and the
        # resolver then unifies each one. Profiling a legal-move query
        # on the case study counted 4.2 million unifications.
        #
        # Keyed on the inner head, so `true(cell(...))` only ever meets
        # `cell` facts. Falls back to the flat list whenever the goal's
        # argument is not a tuple with a ground head, so nothing is
        # ever missed -- the index narrows, it does not decide.
        inner = fact[1] if len(fact) > 1 else None
        if isinstance(inner, tuple) and inner and type(inner[0]) is str:
            self._facts_by_arg.setdefault((pred, inner[0]),
                                          []).append(fact)

    def _add_rule(self, head, body):
        pred = _head_predicate(head)
        if pred is None:
            raise ValueError(f'cannot index rule head {head!r}')
        self._rules_by_pred.setdefault(pred, []).append((head, body))

    # ---- query helpers --------------------------------------------------

    def facts_for(self, pred):
        return self._facts_by_pred.get(pred, [])

    def candidate_facts(self, goal):
        """Facts that could unify with `goal`, narrowed when possible.

        Returns the same facts `facts_for` would, or a subset that is
        guaranteed to contain every match -- a fact whose inner head
        differs from the goal's cannot unify with it, because both are
        ground constants in that position.
        """
        pred = _head_predicate(goal)
        if pred is None:
            return []
        if isinstance(goal, tuple) and len(goal) > 1:
            inner = goal[1]
            if (isinstance(inner, tuple) and inner
                    and type(inner[0]) is str
                    and not inner[0].startswith('?')):
                narrowed = self._facts_by_arg.get((pred, inner[0]))
                if narrowed is not None:
                    return narrowed
                # Nothing indexed under that head: either no such fact
                # exists, or every fact of this predicate has a
                # non-tuple argument. Fall through rather than claim
                # emptiness.
                if (pred, inner[0]) not in self._facts_by_arg:
                    flat = self._facts_by_pred.get(pred, [])
                    if all(isinstance(f[1], tuple) for f in flat
                           if len(f) > 1):
                        return []
        return self._facts_by_pred.get(pred, [])

    def rules_for(self, pred):
        return self._rules_by_pred.get(pred, [])

    def fact_count(self):
        return sum(len(v) for v in self._facts_by_pred.values())

    def rule_count(self):
        return sum(len(v) for v in self._rules_by_pred.values())

    def all_predicates(self):
        return set(self._facts_by_pred.keys()) | \
            set(self._rules_by_pred.keys())
