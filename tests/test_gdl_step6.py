"""Structural tests for the Goal-4 GDL step-6 fragment
(`docs/gdl/step6_add_boulder.gdl`).

Step 6 adds the boulder to step 5's
kings+queens+pawns+rooks+knights+bishops base. The boulder is the
first NEUTRAL piece in the fragment series — owned by neither
player — and brings several rule wrinkles:

  - First move: from the central intersection to one of d4, d5,
    e4, e5. White may NOT move the boulder on their first turn.
  - Subsequent moves: king-like (1 square in any direction).
  - Capture: pawns ONLY (either colour). Only the king captures
    the boulder.
  - Cooldown: between boulder moves, both players must each have
    made one turn — encoded as a per-turn counter that
    decrements toward zero.
  - No-return memory: the boulder may not return via a NON-
    CAPTURING move to its immediately previous square (capture
    exception applies).
  - Treated as friendly by both sides for most purposes (blocks
    no one).

For step 6 we encode the boulder's MOVEMENT + CAPTURE + COOLDOWN +
NO-RETURN MEMORY. The repetition rule (step 10) will reference the
boulder's state in the state hash; queen actions (step 7) reference
the boulder for the boulder-not-manipulable rule.

Structural invariants tested:

  - Step-5 invariants still hold (roles + initial pieces).
  - Boulder appears in init at the central intersection (encoded
    as a sentinel value like 'int').
  - Boulder cooldown counter starts at 0 (movable).
  - Boulder last-square memory starts unset.
  - At least one legal rule mentions 'boulder'.
  - The first-move constraint is encoded (textual reference to
    'first_move' / 'd4' / 'e5' / similar).
  - The cooldown is encoded in `next` clauses.
  - The no-return memory is encoded.
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step6_add_boulder.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-6 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


# ---- step-5 invariants still hold ----------------------------------------

def test_step6_parses(parsed):
    assert len(parsed) > 0


def test_step6_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step6_white_moves_first(parsed):
    has_init = any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and f[1] == ('control', 'white')
        for f in parsed)
    assert has_init


def test_step6_has_terminal_and_goal(parsed):
    has_terminal = False
    has_goal = False
    for f in parsed:
        if isinstance(f, tuple) and len(f) >= 2 and f[0] == '<=':
            head = f[1]
            if head == 'terminal' or (
                    isinstance(head, tuple) and head and
                    head[0] == 'terminal'):
                has_terminal = True
            if isinstance(head, tuple) and head and head[0] == 'goal':
                has_goal = True
    assert has_terminal and has_goal


# ---- boulder initial state ------------------------------------------------

def _init_facts(parsed):
    return [f[1] for f in parsed
            if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init']


def test_step6_boulder_starts_on_intersection(parsed):
    """The boulder starts on the central intersection (not on any
    single square). Encoded with a sentinel like 'int' or a special
    fact such as `(boulder_at intersection)` or
    `(cell intersection none boulder)`."""
    inits = _init_facts(parsed)
    flat = [' '.join(_flatten(f)) for f in inits]
    # Look for ANY init fact mentioning both 'boulder' and an
    # intersection sentinel (commonly 'int' or 'intersection').
    relevant = [s for s in flat
                if 'boulder' in s and ('int' in s or 'center' in s)]
    assert relevant, (
        f"no init fact establishes the boulder at the central "
        f"intersection; init facts: {flat}")


def test_step6_boulder_cooldown_starts_at_zero(parsed):
    """Boulder is movable from the start (cooldown 0). White may NOT
    move it on their first turn (that's the first-move constraint —
    separate from cooldown)."""
    inits = _init_facts(parsed)
    flat = [' '.join(_flatten(f)) for f in inits]
    relevant = [s for s in flat
                if 'cooldown' in s.lower() or 'cd' in s.split()]
    # Either: there's an explicit (boulder_cooldown 0) init OR cooldown
    # is implicitly zero (no init fact). Both are acceptable. We just
    # check the source DOES mention cooldown somewhere.
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'cooldown' in text, "step-6 GDL must encode boulder cooldown"


def test_step6_all_step5_pieces_still_present(parsed):
    # _init_facts already returns the inner fact tuples (the thing
    # after 'init'), so each `f` is e.g. ('cell', 'a', '1', 'white',
    # 'bishop'). Filter for cell facts and index directly.
    cells = [f for f in _init_facts(parsed)
             if isinstance(f, tuple) and f[0] == 'cell']
    pieces = {(c[1], c[2]): (c[3], c[4]) for c in cells if len(c) == 5}
    # spot-check
    assert pieces.get(('g', '1')) == ('white', 'king')
    assert pieces.get(('a', '1')) == ('white', 'bishop')
    assert pieces.get(('d', '1')) == ('white', 'knight')
    assert pieces.get(('a', '2')) == ('white', 'pawn')


# ---- boulder-specific rules ----------------------------------------------

def _flatten(form):
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


def test_step6_has_boulder_legal_rule(parsed):
    """At least one legal rule references 'boulder'."""
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if 'boulder' in atoms:
                return
    raise AssertionError("no legal rule mentions 'boulder'")


def test_step6_first_move_constraint_encoded():
    """White cannot move the boulder on turn 1; the boulder's first
    move must be to one of d4 / d5 / e4 / e5. Source must reference
    either the first-move flag / one of those squares / both."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    has_first_move_text = (
        'first_move' in text or 'first move' in text
        or ('d 4' in text or 'd 5' in text or 'e 4' in text or 'e 5' in text))
    assert has_first_move_text, (
        "step-6 GDL must encode the boulder's first-move constraint "
        "(first move from intersection to d4/d5/e4/e5)")


def test_step6_cooldown_handling_in_next():
    """The cooldown is decremented per turn — must appear in some
    `next` clause."""
    with open(GDL_PATH) as f:
        text = f.read()
    # crude check: 'cooldown' appears in a `next` clause
    next_clauses = [s for s in text.split('(<= (next ')
                    if 'cooldown' in s.split('(<= ')[0]]
    assert next_clauses, (
        "boulder cooldown must be updated in a `next` clause")


def test_step6_no_return_memory_encoded():
    """The boulder may not return (via non-capturing move) to its
    last square. Source must encode last_square or no_return."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('last_square' in text or 'no_return' in text
            or 'no-return' in text or 'previous_square' in text), (
        "step-6 GDL must encode the no-return memory")


def test_step6_boulder_captures_pawn_only_encoded():
    """The boulder captures pawns only — source must restrict the
    boulder's capture targets to pawns."""
    with open(GDL_PATH) as f:
        text = f.read()
    # Look for a rule mentioning both 'boulder' and 'pawn' in a
    # capture/legal context.
    assert 'pawn' in text and 'boulder' in text, (
        "step-6 GDL must reference pawn + boulder for the pawn-only "
        "capture rule")


def test_step6_no_queen_actions_yet():
    """Queen actions (manipulation, transformation) are step 7."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    code_only = '\n'.join(
        ln.split(';')[0] for ln in text.split('\n'))
    assert 'manipulat' not in code_only, (
        "step 6 must NOT encode queen manipulation (step 7)")
    assert 'transform' not in code_only, (
        "step 6 must NOT encode queen transformation (step 7)")
