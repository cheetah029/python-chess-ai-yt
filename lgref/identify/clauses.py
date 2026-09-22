"""Normalise GDL clauses into typed nodes for the dependency graph.

Phase 1 step one (issue #187): formal clauses -> rules. A *formal clause*
is one statement in a GDL file; a *rule* is a gameplay provision
implemented by one or more of them.

GAME-INDEPENDENCE IS A REQUIREMENT, NOT A NICETY

LGREF is a framework for evaluating rules in ANY GDL game. Royal Chess is
the case study, not the subject. So nothing in this module may name a
Royal Chess concept: no list of piece types, no list of action names, no
knowledge that `queen_form` or `boulder_cooldown` exist.

Everything game-specific is DERIVED from the description being analysed:

  action names        from the action terms of `legal(P, X(...))`
  action subjects     constants in an action term's discriminator slot
                      (Royal Chess puts piece names there; another game
                      might put card suits or unit classes)
  fluents             from `true(X(...))` and `next(X(...))`
  terminal predicates from `terminal` and `goal`, which ARE universal
                      GDL keywords, plus whatever feeds them transitively

The GDL keywords (`<=`, `true`, `next`, `does`, `init`, `legal`, `goal`,
`terminal`, `role`, `distinct`, `not`, `or`, `and`) are the only fixed
vocabulary, and they are fixed by the GDL specification rather than by
this game.

STRUCTURAL FACTS THAT SHAPE NODE TYPES

1. DERIVED PREDICATES AND FLUENTS ARE DIFFERENT THINGS. `foo() :- ...`
   defines a predicate recomputed on demand; `true(foo)` reads a
   fluent carried in game state, written by `next(foo)`. A fluent
   creates a TEMPORAL edge from writer to reader; a derived predicate an
   immediate one. Conflating them was a real defect in this project's
   GDL (#177 B4) and would mistype that cluster regardless.

2. SOME DESCRIPTIONS CONTAIN MECHANICALLY DERIVED PREDICATE VARIANTS.
   Royal Chess's GDL has `occupied_except` alongside `occupied` — same
   body with one extra excluded square, an encoding workaround for GDL's
   inability to evaluate in a hypothetical state. Treating such a variant
   as a separate concept doubles the apparent size of the rule using it.

   Rather than hardcoding that suffix, variants are DETECTED: a predicate
   whose name extends another's and whose clause bodies draw on the same
   predicates is an alias of it. The detection reports what it found so
   the decision is auditable rather than silent.

Nothing here reasons about strategic function. Clauses are tagged by what
they DO, never by what that behaviour might be FOR — grouping by function
would require knowing a rule's function before finding its boundaries,
and Phase 2 infers function FROM those boundaries.
"""

import re


# GDL's own reserved vocabulary. Fixed by the GDL specification, not by
# any particular game, so hardcoding these is not a game assumption.
CONTROL_FORMS = frozenset({
    '<=', 'not', 'or', 'and', 'distinct', 'true', 'next', 'does', 'init',
    'base', 'input',
})

# Keywords every GDL description must define. `terminal` and `goal` mark
# the ending condition in ANY game; `lost`, by contrast, is a Royal Chess
# predicate and is discovered transitively rather than named here.
ROLE_FORMS = frozenset({'role', 'legal', 'goal', 'terminal', 'init', 'next'})
UNIVERSAL_TERMINAL_FORMS = frozenset({'terminal', 'goal'})


def canonical_predicate(name, aliases=None):
    """Map a predicate onto its canonical form via a detected alias map.

    `aliases` comes from `detect_predicate_aliases`, which finds
    mechanically derived variants structurally rather than by matching a
    hardcoded suffix. With no alias map the name is returned unchanged,
    so a description without such variants is unaffected.
    """
    if not aliases:
        return name
    seen = set()
    while name in aliases and name not in seen:
        seen.add(name)
        name = aliases[name]
    return name


def detect_predicate_aliases(forms):
    """Find predicates that are mechanically derived variants of others.

    A variant extends another predicate's NAME and draws on the same
    predicates in its bodies, differing only by extra arguments. Royal
    Chess's `occupied_except` relative to `occupied` is the motivating
    case — an encoding workaround for GDL's inability to evaluate a body
    in a hypothetical state — but the test is structural, so a game using
    a different convention is handled the same way and a game using none
    is unaffected.

    Both conditions are required. Name extension alone would collapse
    `rank_adj` into `rank`, which are unrelated; body agreement alone
    would collapse predicates that merely share helpers.

    Returns {variant: base}.
    """
    bodies = {}
    arities = {}
    for form in forms:
        if not (isinstance(form, tuple) and form and form[0] == '<='):
            continue
        head = form[1]
        pred = head_predicate(head)
        if not pred:
            continue
        used = set()
        _collect_body_predicates(list(form[2:]), used)
        bodies.setdefault(pred, set()).update(used)
        arities.setdefault(pred, set()).add(
            len(head) - 1 if isinstance(head, tuple) else 0)

    aliases = {}
    names = sorted(bodies)
    for variant in names:
        for base in names:
            if variant == base or not variant.startswith(base + '_'):
                continue
            # A variant takes MORE arguments than its base (the extra
            # state threaded through), never fewer.
            if not (max(arities[variant]) > max(arities[base])):
                continue
            v_body = {n[:-len('_' + variant[len(base) + 1:])]
                      if False else n for n in bodies[variant]}
            # Compare after stripping the same extension from body names,
            # so occupied_except's body (which calls occupied_except)
            # lines up with occupied's.
            suffix = variant[len(base):]
            normalised = {n[:-len(suffix)] if n.endswith(suffix) else n
                          for n in v_body}
            if normalised and normalised >= bodies[base]:
                aliases[variant] = base
                break
    return aliases


def _collect_body_predicates(goals, out):
    """Predicate names a body calls, ignoring GDL control forms."""
    for goal in goals:
        if not isinstance(goal, tuple) or not goal:
            continue
        name = goal[0]
        if name in ('not', 'or', 'and'):
            _collect_body_predicates(list(goal[1:]), out)
        elif name in ('true', 'next', 'init'):
            if len(goal) > 1 and isinstance(goal[1], tuple):
                out.add(goal[1][0])
        elif name in ('does',):
            continue
        elif name == 'distinct':
            continue
        else:
            out.add(name)


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
        fluents_read        fluents read via true(X(...))
        fluents_written     fluents written via next(X(...))
        actions_read        actions inspected via does(P, X(...))
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
                 'generic_effect', '_context', 'action_subjects')

    def __init__(self, index, form, context=None):
        context = context or Vocabulary.empty()
        self._context = context
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
        self.action_subjects = set()
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
            name = canonical_predicate(head_predicate(inner) or 'next',
                                       self._context.aliases)
            self.head_predicate = name
            self.head_kind = 'fluent_write'
            self.fluents_written.add(name)
            return
        if pred == 'init' and isinstance(head, tuple) and len(head) > 1:
            name = canonical_predicate(head_predicate(head[1]) or 'init',
                                       self._context.aliases)
            self.head_predicate = name
            self.head_kind = 'fluent_init'
            self.fluents_written.add(name)
            return
        if pred == 'legal' and isinstance(head, tuple) and len(head) > 2:
            self.head_predicate = 'legal'
            self.head_kind = 'legal'
            action = head[2]
            action_name = head_predicate(action)
            # Any action name the description uses. Royal Chess happens
            # to use move/transform/manipulate; another game will use
            # something else entirely, and that is not this module's
            # business.
            if action_name:
                self.action_type = action_name
                # The discriminator slot: a CONSTANT there names the
                # action's subject (a piece in Royal Chess, a unit or
                # card elsewhere). A variable means the clause is generic
                # over subjects.
                if isinstance(action, tuple) and len(action) > 1 \
                        and not is_variable(action[1]) \
                        and isinstance(action[1], str):
                    self.action_subjects.add(action[1])
            return
        if pred in ('terminal', 'goal', 'role'):
            self.head_predicate = pred
            self.head_kind = pred
            return

        self.head_predicate = (
            canonical_predicate(pred, self._context.aliases)
            if pred else None)
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
            fluent = canonical_predicate(
                head_predicate(goal[1]) or '', self._context.aliases)
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
            # applies to every value of it. `does(M, move(PIECE, ...))`
            # is the board-update machinery every piece's move rule
            # relies on; `does(M, move(knight, ...))` would be specific
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

        canonical = canonical_predicate(name, self._context.aliases)
        self.body_predicates.add(canonical)
        if negated:
            self.negated_goals.add(canonical)
        for sub in goal[1:]:
            if isinstance(sub, tuple):
                self._walk_goal(sub, negated)

    # ---- tagging ---------------------------------------------------------

    def _collect_pieces(self, form):
        """Tag the clause with the action subjects it mentions.

        `piece_types` keeps its name for continuity but holds whatever
        constants the description uses as action discriminators —
        discovered from the game, never a hardcoded list. In Royal Chess
        these are piece names; in another game they might be unit
        classes or card suits.
        """
        subjects = self._context.action_subjects
        if not subjects:
            return

        def walk(term):
            if isinstance(term, str):
                if term in subjects:
                    self.piece_types.add(term)
            elif isinstance(term, tuple):
                for child in term:
                    walk(child)
        walk(form)

    def _is_terminal_related(self):
        """Does this clause feed the ending condition?

        `terminal` and `goal` are universal GDL keywords. Everything else
        is discovered: a predicate reaching them transitively is terminal
        too. Royal Chess's `lost` qualifies that way rather than by being
        named here.
        """
        terminal_preds = self._context.terminal_predicates
        if self.head_kind in UNIVERSAL_TERMINAL_FORMS:
            return True
        if self.head_predicate in terminal_preds:
            return True
        return bool(terminal_preds & self.body_predicates)

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


class Vocabulary(object):
    """Game vocabulary DERIVED from one GDL description.

    Every game-specific name LGREF uses comes from here, discovered by
    reading the description, so the same code analyses a different game
    without edits. Only GDL's own reserved words are fixed.
    """

    __slots__ = ('aliases', 'action_names', 'action_subjects',
                 'terminal_predicates')

    def __init__(self, aliases, action_names, action_subjects,
                 terminal_predicates):
        self.aliases = aliases
        self.action_names = action_names
        self.action_subjects = action_subjects
        self.terminal_predicates = terminal_predicates

    @classmethod
    def empty(cls):
        return cls({}, frozenset(), frozenset(), frozenset())

    @classmethod
    def derive(cls, forms):
        aliases = detect_predicate_aliases(forms)

        action_names = set()
        action_subjects = set()
        for form in forms:
            head = form[1] if (isinstance(form, tuple) and form
                               and form[0] == '<=') else form
            if not (isinstance(head, tuple) and len(head) > 2
                    and head[0] == 'legal'):
                continue
            action = head[2]
            name = head_predicate(action)
            if name:
                action_names.add(name)
            # A CONSTANT in the discriminator slot names the action's
            # subject. Royal Chess puts piece names there; another game
            # might put unit classes. A variable means generic.
            if isinstance(action, tuple) and len(action) > 1 \
                    and isinstance(action[1], str) \
                    and not is_variable(action[1]):
                action_subjects.add(action[1])

        terminal = cls._terminal_closure(forms, aliases)
        return cls(aliases, frozenset(action_names),
                   frozenset(action_subjects), frozenset(terminal))

    @staticmethod
    def _terminal_closure(forms, aliases, depth=1):
        """Predicates reaching `terminal` or `goal` transitively.

        `terminal` and `goal` are universal GDL keywords; everything that
        feeds them is game-specific and discovered. Royal Chess's `lost`
        is found this way rather than named.
        """
        callers = {}
        for form in forms:
            if not (isinstance(form, tuple) and form and form[0] == '<='):
                continue
            pred = head_predicate(form[1])
            if not pred:
                continue
            pred = canonical_predicate(pred, aliases)
            used = set()
            _collect_body_predicates(list(form[2:]), used)
            callers.setdefault(pred, set()).update(
                canonical_predicate(u, aliases) for u in used)

        # Walk downward from the universal keywords, but only `depth`
        # hops. The ending condition's DIRECT feeders identify it; the
        # unbounded closure does not, because in a connected ruleset it
        # reaches everything.
        #
        # Measured on Royal Chess: unbounded closure marked 451 of 488
        # clauses terminal-dependent, via
        # terminal -> lost -> legal_after_tiny_filter -> legal -> ...
        # A signal true of 92% of clauses distinguishes nothing.
        #
        # Depth 1 finds `lost` (because `terminal :- lost(P)`)
        # without naming it — which is exactly the game-specific
        # discovery this replaces a hardcoded list with.
        terminal = set(UNIVERSAL_TERMINAL_FORMS)
        frontier = set(terminal)
        for _ in range(depth):
            nxt = set()
            for pred in frontier:
                for used in callers.get(pred, ()):
                    if used not in terminal:
                        terminal.add(used)
                        nxt.add(used)
            frontier = nxt
            if not frontier:
                break
        return terminal


def normalize(forms, vocabulary=None):
    """Turn parsed GDL forms into ClauseNodes, source order preserved.

    The vocabulary is derived from `forms` unless supplied, so analysing
    a different game needs no configuration.
    """
    vocabulary = vocabulary or Vocabulary.derive(forms)
    return [ClauseNode(i, form, vocabulary) for i, form in enumerate(forms)]


def load(path):
    """Parse an infix-HRF GDL file and normalise it.

    Infix HRF is this project's OFFICIAL dialect (issue #190):

        legal(P, move(boulder, FF, FR, TF, TR)) :- true(control(P)) & ...

    Prefix KIF is an outdated dialect kept only as a generated
    artifact, and LGREF does not accept it. Handing this function a
    prefix file is a mistake worth naming loudly rather than parsing
    silently, because the two dialects differ in statement count --
    prefix `(or A B)` bodies expand to one rule per branch in infix --
    so a silent fallback would change every clause count in the report
    without saying so.
    """
    from ggp.infix import parse_infix
    with open(path) as handle:
        text = handle.read()
    if '(<=' in text:
        raise ValueError(
            '{} looks like prefix KIF, which LGREF does not accept. '
            'The official dialect is infix HRF; convert with '
            'docs/gdl/build_integrated.py (issue #190).'.format(path))
    return normalize(parse_infix(text))
