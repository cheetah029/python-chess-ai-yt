"""Derive an ablated description from a base one.

Forms are the parsed representation shared with `ggp`: a fact is a term,
a rule is `('<=', head, goal, goal, ...)`, a negated goal is
`('not', term)`, and a variable is a string beginning with `?`.

Two operations, both fully general over GDL. Neither consults a game's
vocabulary, a predicate naming convention, or anything about Royal
Chess: what makes a clause die here is what the logic says about it.

RELAX drops a body conjunct. Dropping a conjunct from a conjunction can
only make the rule easier to satisfy, so the game becomes MORE
permissive -- the legal-move set grows or stays equal, never shrinks.
That is the operation that isolates a restriction living inside a clause
which does other work too. Deleting the whole clause would remove the
other work as well.

REMOVE deletes an entity. Relaxing every restriction on a piece does not
remove the piece: it leaves an UNRESTRICTED one, which is a different
and probably stronger piece, not an absent one. Removal is therefore a
separate operation rather than a point on the relaxation ladder.
"""

import collections

# GDL keywords whose own definitions are supplied by the game manager
# rather than the description, so they are never "undefined" here.
BUILTIN = frozenset((
    'does', 'true', 'distinct', 'role', 'init', 'next', 'legal',
    'goal', 'terminal', 'base', 'input'))


class UnsafeRelaxation(Exception):
    """A relaxation that would leave a head variable unbound.

    Refused rather than emitted. An unsafe clause does not mean "a more
    permissive game", it means a clause whose meaning is no longer
    defined, and a measurement taken on it would be measuring the
    breakage rather than the rule.
    """


# ---------------------------------------------------------------------------
# term inspection
# ---------------------------------------------------------------------------

def is_variable(term):
    return isinstance(term, str) and term.startswith('?')


def mentions(term, constant):
    """Does `term` contain `constant` anywhere, at any depth?"""
    if isinstance(term, tuple):
        return any(mentions(part, constant) for part in term)
    return term == constant


def variables(term, into=None):
    found = set() if into is None else into
    if isinstance(term, tuple):
        for part in term:
            variables(part, found)
    elif is_variable(term):
        found.add(term)
    return found


def is_rule(form):
    return isinstance(form, tuple) and len(form) > 1 and form[0] == '<='


def head_of(form):
    return form[1] if is_rule(form) else form


def body_of(form):
    return list(form[2:]) if is_rule(form) else []


def is_negated(goal):
    return isinstance(goal, tuple) and len(goal) == 2 and goal[0] == 'not'


def goal_predicate(goal):
    """The predicate a goal tests, seeing through `not` and `true`/`next`.

    `~true(boulder_last(TF,TR))` tests `boulder_last`, not `not` and not
    `true`. Callers asking "which clauses consult X" mean X.
    """
    inner = goal[1] if is_negated(goal) else goal
    if isinstance(inner, tuple) and inner and inner[0] in ('true', 'next'):
        inner = inner[1] if len(inner) > 1 else inner
    if isinstance(inner, tuple):
        return inner[0] if inner else None
    return inner


def head_predicate(form):
    head = head_of(form)
    if isinstance(head, tuple) and head and head[0] in ('true', 'next', 'init'):
        inner = head[1] if len(head) > 1 else head
        return inner[0] if isinstance(inner, tuple) else inner
    if isinstance(head, tuple):
        return head[0] if head else None
    return head


# ---------------------------------------------------------------------------
# safety
# ---------------------------------------------------------------------------

def bound_variables(body):
    """Variables a POSITIVE body goal binds.

    Negated goals bind nothing: `~p(X)` tests a value of X, it cannot
    produce one. This is the standard datalog safety condition and it is
    what makes an unsafe relaxation detectable rather than mysterious.
    """
    bound = set()
    for goal in body:
        if not is_negated(goal):
            variables(goal, bound)
    return bound


def unsafe_variables(head, body):
    """Head variables, and variables under negation, left unbound."""
    bound = bound_variables(body)
    needed = set(variables(head))
    for goal in body:
        if is_negated(goal):
            needed |= variables(goal)
    return needed - bound


# ---------------------------------------------------------------------------
# relax
# ---------------------------------------------------------------------------

RelaxResult = collections.namedtuple(
    'RelaxResult', 'forms dropped refused')


def relax(forms, predicates, strict=False):
    """Drop every body conjunct testing one of `predicates`, where safe.

    Returns `RelaxResult(forms, dropped, refused)`. The clause survives
    with a shorter body; nothing is deleted outright, which is the point
    -- the clause's other work is preserved.

    SAFETY IS THE DISCRIMINATOR, and it does real work here rather than
    being a formality. Relaxing `boulder_last` should drop the guard
    `~true(boulder_last(TF,TR))` out of the boulder's movement rule --
    that guard IS the no-return restriction. It should NOT touch
    `next(boulder_last(F,R)) :- true(boulder_last(F,R)) & ...`, whose
    positive goal is the only thing binding the head's `F` and `R`:
    dropping it there yields a clause whose meaning is undefined, not a
    more permissive game.

    Polarity does not separate these two cases -- the cooldown
    restriction is the POSITIVE goal `true(boulder_cooldown(0))`, and
    dropping it is exactly right because it binds nothing the head
    needs. What separates them is whether the head stays bound.

    `refused` lists (head predicate, unbound variables) for every clause
    skipped this way, so a partial relaxation can never be read as a
    complete one. With `strict=True` a refusal raises instead.
    """
    targets = frozenset(predicates)
    out, dropped, refused = [], 0, []
    for form in forms:
        if not is_rule(form):
            out.append(form)
            continue
        head, body = head_of(form), body_of(form)
        kept = [g for g in body if goal_predicate(g) not in targets]
        if len(kept) == len(body):
            out.append(form)
            continue
        loose = unsafe_variables(head, kept)
        if loose:
            detail = (head_predicate(form), tuple(sorted(loose)))
            if strict:
                raise UnsafeRelaxation(
                    'relaxing {} in `{}` leaves {} unbound'.format(
                        sorted(targets), detail[0], list(detail[1])))
            refused.append(detail)
            out.append(form)
            continue
        dropped += len(body) - len(kept)
        out.append(tuple(['<=', head] + kept))
    return RelaxResult(out, dropped, refused)


# ---------------------------------------------------------------------------
# remove an entity
# ---------------------------------------------------------------------------

def _is_structural_guard(goal):
    """`distinct(X, c)` -- true for every value X can still take.

    Polarity alone is the wrong test for "can this goal still hold". A
    POSITIVE `distinct(PIECE, boulder)` is not a requirement that the
    boulder exist; it is an exclusion, and with the boulder gone it is
    vacuously satisfied. Treating it as a requirement was catastrophic
    rather than merely wrong: `distinct(PIECE, boulder)` appears in the
    core `next(cell(...))` board-update clauses, so removing the boulder
    deleted the board update for every piece in the game and the variant
    silently became unplayable.
    """
    inner = goal[1] if is_negated(goal) else goal
    return isinstance(inner, tuple) and bool(inner) and inner[0] == 'distinct'


def _strip_dead(forms, dead_predicates, dead_constant=None):
    """One pass of: positive use kills the clause, negative use is dropped.

    A clause requiring something that can never hold can never fire, so
    it goes. A clause GUARDING against something that can never hold has
    a vacuously satisfied guard, so the guard goes and the clause stays.
    Deleting the clause instead would ablate an unrelated rule that
    merely happened to mention the removed entity.
    """
    out, changed = [], False
    for form in forms:
        if not is_rule(form):
            if dead_constant is not None and mentions(form, dead_constant):
                changed = True
                continue
            out.append(form)
            continue

        head, body = head_of(form), body_of(form)
        if head_predicate(form) in dead_predicates or (
                dead_constant is not None and mentions(head, dead_constant)):
            changed = True
            continue

        kept, doomed = [], False
        for goal in body:
            hits = goal_predicate(goal) in dead_predicates or (
                dead_constant is not None and mentions(goal, dead_constant))
            if not hits:
                kept.append(goal)
            elif is_negated(goal) or _is_structural_guard(goal):
                changed = True          # vacuously true: drop the guard
            else:
                doomed = True           # can never hold: drop the clause
                break
        if doomed:
            changed = True
            continue
        if len(kept) != len(body):
            form = tuple(['<=', head] + kept)
        out.append(form)
    return out, changed


def _undefined_predicates(forms):
    """Predicates consulted but no longer defined, and unread fluents.

    A predicate with no defining clause and no init fact cannot hold.
    Detected from the dependency structure -- never from a name. This is
    what reaches a removed entity's bookkeeping state: those predicates
    die because everything that wrote and read them died, not because
    they are spelled like the entity.
    """
    defined, consulted = set(), set()
    for form in forms:
        pred = head_predicate(form)
        if pred:
            defined.add(pred)
        for goal in body_of(form):
            pred = goal_predicate(goal)
            if pred:
                consulted.add(pred)
    return {p for p in consulted - defined
            if p not in BUILTIN and not is_variable(p)}


def _unread_fluents(forms):
    """Fluents still written and initialised, but read by nothing.

    Removing an entity leaves its bookkeeping behind: the clauses that
    CONSULTED the boulder's cooldown die with the boulder, but
    `next(boulder_cooldown(0)) :- true(boulder_cooldown(0))` still
    defines it, so an undefined-predicate check never notices. The state
    is carried from turn to turn and read by nobody.

    Inert state does not change the legal-move set, so leaving it in
    would not corrupt a measurement -- but it would put a rule's
    machinery in the variant's clause list long after the rule was
    removed, and every clause count taken from that variant would be
    wrong. Found by dependency again: written, never consulted.
    """
    written, read, protected = set(), set(), set()
    for form in forms:
        head = head_of(form)
        if isinstance(head, tuple) and head and head[0] in ('next', 'init'):
            pred = head_predicate(form)
            if pred:
                written.add(pred)
        else:
            # A derived predicate or a keyword head is not a fluent, and
            # anything it defines must not be dragged out from under it.
            pred = head_predicate(form)
            if pred:
                protected.add(pred)
        own = head_predicate(form) if (
            isinstance(head, tuple) and head and head[0] == 'next') else None
        for goal in body_of(form):
            inner = goal[1] if is_negated(goal) else goal
            if isinstance(inner, tuple) and inner and inner[0] == 'true':
                pred = goal_predicate(goal)
                # A fluent that only its OWN next-rule reads is carried
                # from turn to turn and consulted by nobody. Counting
                # that as a reader keeps every removed entity's
                # bookkeeping alive forever.
                if pred and pred != own:
                    read.add(pred)
    return {p for p in written - read - protected if p not in BUILTIN}


def _drop_fluents(forms, fluents):
    """Delete the `next` clauses and `init` facts of dead fluents."""
    out = []
    for form in forms:
        head = head_of(form)
        if isinstance(head, tuple) and head and head[0] in ('next', 'init'):
            if head_predicate(form) in fluents:
                continue
        out.append(form)
    return out


def _next_clauses(forms):
    """Map fluent -> list of its `next` clause bodies."""
    out = collections.defaultdict(list)
    for form in forms:
        head = head_of(form)
        if isinstance(head, tuple) and head and head[0] == 'next':
            pred = head_predicate(form)
            if pred:
                out[pred].append(tuple(body_of(form)))
    return out


def _only_persists(bodies):
    """Every remaining transition is unconditional self-persistence.

    `next(F(x)) :- true(F(x))` and nothing else means the fluent can
    never change again: it is frozen at whatever `init` gave it.
    """
    if not bodies:
        return False
    for body in bodies:
        if len(body) != 1:
            return False
        goal = body[0]
        if is_negated(goal):
            return False
        inner = goal[1] if (isinstance(goal, tuple) and len(goal) > 1
                            and goal[0] == 'true') else None
        if inner is None:
            return False
    return True


def _frozen_entity_state(before, after):
    """Fluents the removal froze -- the entity's own state.

    THE HARD CASE, and the one a syntactic scan misses entirely. The
    boulder's position on the central intersection is held in
    `boulder_at`, which never contains the constant `boulder` anywhere:
    it is written by `next(boulder_at(intersection)) :-
    true(boulder_at(intersection)) & ~boulder_moved_this_turn`. Remove
    the boulder, and `boulder_moved_this_turn` dies, and that guard is
    dropped as vacuously true -- leaving the fluent asserted forever.
    The removed boulder goes on blocking the central diagonals.

    The signature is that the removal changed how the fluent can
    change, and what is left can never change at all. A fluent that can
    no longer change is not state; it is a constant the ablation
    accidentally froze, and it belongs to the entity that used to move
    it. A fluent with writers untouched by the removal, or with any
    remaining conditional transition, is not affected.
    """
    frozen = set()
    for fluent, bodies in after.items():
        if fluent not in before or before[fluent] == bodies:
            continue                      # removal did not touch it
        if _only_persists(bodies):
            frozen.add(fluent)
    return frozen


def _unused_derived(forms):
    """Derived predicates no surviving clause consults.

    The counterpart of `_unread_fluents` for predicates that are
    recomputed rather than stored. They cannot change the legal-move
    set, so leaving them would not corrupt a measurement -- but they
    would sit in the variant's clause list as though the removed rule
    were still partly present, and every clause count taken from that
    variant would be wrong.

    They also chain: with the boulder's movement rules gone nothing
    consults `center_crossing_blocked`, which is the only consumer of
    `center_diag_pair`, which with `boulder_at` is the last thing
    keeping that fluent alive. One pass removes one layer, which is why
    the caller iterates to a fixpoint.
    """
    derived, consulted = set(), set()
    for form in forms:
        head = head_of(form)
        is_state = (isinstance(head, tuple) and head
                    and head[0] in ('next', 'init'))
        pred = head_predicate(form)
        if pred and not is_state and pred not in BUILTIN:
            derived.add(pred)
        for goal in body_of(form):
            got = goal_predicate(goal)
            if got:
                consulted.add(got)
    return derived - consulted


def _drop_definitions(forms, predicates):
    return [f for f in forms if head_predicate(f) not in predicates]


def undefined_in(forms):
    """Predicates a description consults but never defines.

    Exposed because it is a health check on the description itself, not
    only an internal step: Royal Chess has four, all pre-existing.
    """
    return _undefined_predicates(forms)


def remove_constant(forms, constant, max_passes=50):
    """Remove an entity named by `constant`, and everything that dies.

    Generic over any GDL game and any constant in it. The entity is
    identified by the constant itself, and the state that served it is
    found by iterating to a fixpoint:

      1. facts and clauses mentioning the constant go, except that a
         NEGATIVE mention is only a guard and is dropped on its own;
      2. whatever is left consulting a now-undefined predicate is
         treated the same way;
      3. repeat until nothing changes.

    No predicate-name matching anywhere. Removing `boulder` eliminates
    the cooldown and no-return state because their writers and readers
    died, which is a fact about the dependency graph rather than about
    the word "boulder".
    """
    # Predicates ALREADY undefined in the base description are not this
    # ablation's doing, and cascading from them attributes pre-existing
    # breakage to the removal. Royal Chess has four -- the unfinished
    # tiny-endgame arithmetic (`closest_royal_pair_distance`,
    # `cancel_queens_valuation_balanced`, `counts_at_least_7`) and
    # `next_state_hash`. Cascading from those deleted the entire tiny
    # endgame and repetition machinery when removing the BOULDER, which
    # would have been reported as the boulder's contribution.
    pre_existing = _undefined_predicates(forms)
    transitions_before = _next_clauses(forms)

    forms, _ = _strip_dead(forms, frozenset(), dead_constant=constant)
    for _ in range(max_passes):
        moved = False
        dead = _undefined_predicates(forms) - pre_existing
        if dead:
            forms, moved = _strip_dead(forms, dead)
        inert = _unread_fluents(forms) - pre_existing
        if inert:
            forms = _drop_fluents(forms, inert)
            moved = True
        unused = _unused_derived(forms) - pre_existing
        if unused:
            forms = _drop_definitions(forms, unused)
            moved = True
        frozen = _frozen_entity_state(
            transitions_before, _next_clauses(forms)) - pre_existing
        if frozen:
            forms = _drop_fluents(forms, frozen)
            moved = True
        if not moved:
            break
    return forms


def remove_clauses(forms, node_ids, id_of):
    """Delete whole clauses by id -- the coarse operation, kept explicit.

    This is what the Phase 1 intervention probe does. Naming it beside
    `relax` and `remove_constant` keeps the three from being confused
    with each other in a results table.
    """
    drop = set(node_ids)
    return [f for f in forms if id_of(f) not in drop]


def constants(forms):
    """Every constant appearing in the description, with a use count.

    The candidate entities for removal. Ranking is left to the caller:
    what counts as an "entity" is a question about the game, and
    answering it here would smuggle in an assumption about which games
    LGREF can read.
    """
    counts = collections.Counter()

    def walk(term):
        if isinstance(term, tuple):
            for part in term[1:] if term and term[0] == '<=' else term:
                walk(part)
        elif isinstance(term, str) and not is_variable(term):
            counts[term] += 1

    for form in forms:
        walk(form)
    return counts
