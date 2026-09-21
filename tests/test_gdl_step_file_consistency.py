"""Step files that redeclare a predicate must declare it IDENTICALLY.

The GDL step files are each self-contained: every file redeclares the
helper predicates it needs from earlier steps, and
`build_integrated.py` merges them by de-duplicating identical clauses.

That merge is a UNION, which makes stale copies silently dangerous:

  - If two files define the same predicate with DIFFERENT clauses, both
    survive into integrated.gdl. Since a predicate's clauses are a
    disjunction, the looser copy wins and any guard added to the other
    is defeated.
  - If one file's CALL SITE still passes the old arity after a
    predicate's signature widens, the goal becomes unsatisfiable — and
    under negation-as-failure `(not (unsatisfiable))` is vacuously TRUE,
    so the guard silently disappears instead of erroring.

Both have now happened three times during the Phase 0.5 audit:

  1. `can_capture_to ?atk queen` — step6 kept an unguarded copy that
     defeated the base-form guard added in step5 (#177 B3).
  2. `enemy_can_reach` — step6 kept the pre-`bishop_like` copies, so the
     queen-as-bishop exclusion never took effect.
  3. `legal (move bishop ...)` — step6 kept a call site at the old
     4-argument arity after `enemy_can_reach` widened to 5, which made
     its safety check vacuous and offered every empty square.

None of these failed a test at the time. Each was found by measuring
engine/GGP agreement and working backwards, which is far too slow a
feedback loop for a merge-by-union build.
"""

import os
import re
import sys
from collections import defaultdict

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.parser import parse

GDL_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl')
STEP_FILES = sorted(
    f for f in os.listdir(GDL_DIR)
    if f.startswith('step') and f.endswith('.gdl'))


def _head_predicate(term):
    if isinstance(term, tuple) and term:
        return term[0] if isinstance(term[0], str) else None
    return term if isinstance(term, str) else None


def _integrated_rules():
    """(head, body-goals) for every rule in integrated.gdl."""
    with open(os.path.join(GDL_DIR, 'integrated.gdl')) as f:
        forms = parse(f.read())
    rules = []
    for form in forms:
        if isinstance(form, tuple) and form and form[0] == '<=':
            rules.append((form[1], tuple(form[2:])))
    return rules


def test_no_clause_is_a_strict_weakening_of_another():
    """No rule may have the same head as another while carrying a
    STRICT SUBSET of its body goals.

    This is the exact signature of a stale copy. When a guard is added
    to one step file's copy of a rule and another file keeps the old
    copy, the merge keeps both; the unguarded one has strictly fewer
    body goals, and because a predicate's clauses form a disjunction it
    makes the guarded one redundant. The guard is silently defeated.

    Found this way during the audit: step6 kept
    `(can_capture_to ?atk queen ...) <- (king_step ...)` after step5
    gained `(true (queen_form ?ff ?fr base)) (king_step ...)`, so every
    queen was still treated as base form (#177 B3).

    A later step LEGITIMATELY adds new clauses for a predicate — that is
    how the step files build up — so this checks only the
    strict-weakening relation, never mere difference.
    """
    rules = _integrated_rules()
    offenders = []
    for i, (head_a, body_a) in enumerate(rules):
        for j, (head_b, body_b) in enumerate(rules):
            if i >= j or head_a != head_b:
                continue
            set_a, set_b = set(body_a), set(body_b)
            if set_b < set_a:
                weaker, stronger = body_b, body_a
            elif set_a < set_b:
                weaker, stronger = body_a, body_b
            else:
                continue
            dropped = sorted(map(str, set(stronger) - set(weaker)))
            offenders.append(
                f'{_head_predicate(head_a)}: one clause omits '
                f'{dropped} that another requires')

    assert not offenders, (
        'a rule is strictly weaker than another with the same head. '
        'Clauses are a DISJUNCTION, so the weaker one defeats the '
        "stronger one's guard:\n  " + '\n  '.join(sorted(set(offenders))))


def test_no_goal_is_called_at_an_arity_nothing_defines():
    """Every non-builtin goal must match some definition's arity.

    A goal whose arity nothing defines is unsatisfiable, and under
    negation-as-failure `(not (unsatisfiable))` is vacuously true — a
    guard that silently evaporates rather than failing loudly.
    """
    integrated = os.path.join(GDL_DIR, 'integrated.gdl')
    with open(integrated) as f:
        forms = parse(f.read())

    BUILTIN = {'<=', 'not', 'or', 'and', 'distinct', 'true', 'next',
               'does', 'init', 'legal', 'goal', 'terminal', 'role', 'base',
               'input'}

    defined = defaultdict(set)   # pred -> {arity}
    for form in forms:
        if isinstance(form, tuple) and form and form[0] == '<=':
            head = form[1]
            if isinstance(head, tuple) and head:
                defined[head[0]].add(len(head) - 1)
        elif isinstance(form, tuple) and form:
            defined[form[0]].add(len(form) - 1)

    called = set()

    def walk(term, inside_body):
        if not isinstance(term, tuple) or not term:
            return
        head = term[0]
        if inside_body and isinstance(head, str) and head not in BUILTIN:
            called.add((head, len(term) - 1))
        for child in term[1:]:
            walk(child, inside_body)

    for form in forms:
        if isinstance(form, tuple) and form and form[0] == '<=':
            for goal in form[2:]:
                walk(goal, True)

    missing = sorted(
        f'{pred}/{arity} called but defined only at arity '
        f'{sorted(defined[pred])}'
        for pred, arity in called
        if pred in defined and arity not in defined[pred])

    assert not missing, (
        'goals called at an arity nothing defines — these are '
        'unsatisfiable, and any (not ...) around them is vacuously '
        'true:\n  ' + '\n  '.join(missing))
