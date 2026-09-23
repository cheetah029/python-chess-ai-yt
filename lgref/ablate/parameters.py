"""Find a rule's numeric parameters, and vary them.

The `replace` mode, for the part of it that needs no designer. Many
rules are parameterised by a constant sitting in their own clauses --
the royal-distance cap, the repetition limit, the turn the boulder is
barred on -- and varying one turns a binary ablation into a
dose-response curve. "Removing the cap costs X" is weaker than
"contribution peaks at a cap of 2", and only the second is evidence for
a REVISE recommendation, which relax and remove cannot produce at all.

NOT EVERY CONSTANT IS A PARAMETER, and substituting the wrong one
produces a variant that loads, plays, and silently means something else.
Two encodings have to be told apart, which this module does structurally:

  THRESHOLD   a derived predicate reads a fluent at a fixed value:

                  tiny_endgame_limit_exceeded(D) :- true(distance_count(D,3))

              One comparison. Substituting 3 -> 2 really does mean "cap
              the count at two". Perturbable.

  COUNTER     a fluent's own transitions read the SAME fluent at another
              value, forming a chain:

                  next(boulder_cooldown(0)) :- true(boulder_cooldown(1)) & ...
                  next(boulder_cooldown(1)) :- true(boulder_cooldown(2)) & ...
                  next(boulder_cooldown(2)) :- boulder_moved_this_turn

              The cooldown's LENGTH is the length of that chain, not any
              constant in it. Substituting 2 -> 3 sets the counter to a
              value nothing decrements, so the fluent dies on the next
              turn and the cooldown gets SHORTER -- the opposite of the
              intended change, with no error anywhere. Refused.

Lengthening a counter means adding a link to the chain, which is a
structural edit rather than a substitution. It is left for the
structural-recombination work rather than smuggled in here.
"""

import collections
import re

from lgref.ablate.operations import (body_of, goal_predicate, head_of,
                                     head_predicate, is_negated, is_rule)

NUMERIC = re.compile(r'-?[0-9]+')

Parameter = collections.namedtuple(
    'Parameter', 'predicate value kind fluent')


def _is_numeric(term):
    return isinstance(term, str) and bool(NUMERIC.fullmatch(term))


def _fluent_reads(goal):
    """(fluent, args) if this goal reads a fluent, else None."""
    inner = goal[1] if is_negated(goal) else goal
    if not (isinstance(inner, tuple) and inner and inner[0] == 'true'):
        return None
    payload = inner[1] if len(inner) > 1 else None
    if isinstance(payload, tuple) and payload:
        return payload[0], list(payload[1:])
    return (payload, []) if payload is not None else None


def counters(forms):
    """Fluents whose own transitions step between their own values."""
    found = set()
    for form in forms:
        if not is_rule(form):
            continue
        head = head_of(form)
        if not (isinstance(head, tuple) and head and head[0] == 'next'):
            continue
        written = head_predicate(form)
        for goal in body_of(form):
            read = _fluent_reads(goal)
            if read and read[0] == written and any(
                    _is_numeric(a) for a in read[1]):
                found.add(written)
    return found


def parameters(forms):
    """Numeric parameters that can be varied by substitution.

    A parameter is a numeric constant in a DERIVED predicate's body,
    read from a fluent. Constants in a counter's own transitions are
    reported with kind `counter` and must not be substituted; constants
    in `init` facts and in action terms are not parameters at all.
    """
    chained = counters(forms)
    out = []
    for form in forms:
        if not is_rule(form):
            continue
        head = head_of(form)
        if isinstance(head, tuple) and head and head[0] in ('next', 'init'):
            continue                      # a transition, not a threshold
        predicate = head_predicate(form)
        for goal in body_of(form):
            read = _fluent_reads(goal)
            if not read:
                continue
            fluent, args = read
            for arg in args:
                if not _is_numeric(arg):
                    continue
                kind = 'counter' if fluent in chained else 'threshold'
                out.append(Parameter(predicate, arg, kind, fluent))
    return out


def perturb(forms, predicate, old, new):
    """Substitute `old` -> `new` in the clauses defining `predicate`.

    Only in that predicate's own clauses, and only in their BODIES. A
    constant like `3` occurs all over a board description, and a global
    substitution would redraw the board while claiming to have changed
    one rule. A derived predicate's head is its signature -- callers
    reference it -- so a threshold is read from the body, which is where
    these constants live.
    """
    old, new = str(old), str(new)
    changed = 0

    def swap(term):
        nonlocal changed
        if isinstance(term, tuple):
            return tuple(swap(part) for part in term)
        if term == old:
            changed += 1
            return new
        return term

    out = []
    for form in forms:
        if is_rule(form) and head_predicate(form) == predicate:
            head, body = head_of(form), body_of(form)
            out.append(tuple(['<=', head] + [swap(g) for g in body]))
        else:
            out.append(form)
    return out, changed


def _producer_values(forms, predicate, position):
    """Constants a predicate can put in one argument position.

    `succ(0,1) succ(1,2) ...` produces 1..N in position 1. Used to
    resolve a write whose value slot is a VARIABLE.
    """
    values = set()
    for form in forms:
        head = head_of(form) if is_rule(form) else form
        if not (isinstance(head, tuple) and head and head[0] == predicate):
            continue
        if len(head) > position + 1 and _is_numeric(head[position + 1]):
            values.add(head[position + 1])
    return values


def reachable_values(forms, fluent):
    """Values of `fluent` any clause can actually produce.

    A substituted threshold naming a value the fluent never takes is not
    a milder rule, it is a rule that never fires -- and it would be
    reported as a null contribution for a provision that was never
    varied.

    A write whose value slot is a CONSTANT contributes it directly. A
    write whose value slot is a VARIABLE contributes whatever the body
    goal binding that variable can produce: `distance_count` counts up
    through `succ(OLD,NEW)`, so its range is the range of `succ`, not
    the handful of literals in the `next` heads. Resolving only the
    direct binding is deliberate -- one level is enough for the counter
    idiom, and a full range analysis would be a solver.
    """
    values = set()
    for form in forms:
        head = head_of(form) if is_rule(form) else form
        if not (isinstance(head, tuple) and head
                and head[0] in ('next', 'init')):
            continue
        payload = head[1] if len(head) > 1 else None
        if not (isinstance(payload, tuple) and payload
                and payload[0] == fluent):
            continue
        for slot in payload[1:]:
            if _is_numeric(slot):
                values.add(slot)
            elif isinstance(slot, str) and slot.startswith('?'):
                for goal in body_of(form) if is_rule(form) else []:
                    inner = goal[1] if is_negated(goal) else goal
                    if not (isinstance(inner, tuple) and len(inner) > 1):
                        continue
                    if inner[0] in ('true', 'next', 'not'):
                        continue
                    for index, arg in enumerate(inner[1:]):
                        if arg == slot:
                            values |= _producer_values(
                                forms, inner[0], index)
    return values


def sweep(forms, parameter, span=1):
    """Values to try for one parameter, with the unsound ones refused.

    Range policy: the values the fluent can actually take, within `span`
    of the current setting. A cap of 50 on a counter that reaches 3 is
    not a gentler rule, it is no rule -- and it would be reported as a
    null contribution for a provision that was never varied.
    """
    if parameter.kind == 'counter':
        return []
    current = int(parameter.value)
    usable = {int(v) for v in reachable_values(forms, parameter.fluent)}
    if not usable:
        return []
    return sorted(v for v in usable
                  if v != current and abs(v - current) <= span)
