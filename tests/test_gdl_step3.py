"""Structural tests for the Goal-4 GDL step-3 fragment
(`docs/gdl/step3_add_rook.gdl`).

Step 3 adds the v2 rook to step 2's kings+queens+pawns base. From
RULEBOOK_v2.md the v2 rook moves in TWO STEPS within a single turn:

  1. One square orthogonally (up, down, left, or right).
  2. Then a 90° turn and any number of squares in the new
     direction (including zero).

The rook may stop on or capture the first enemy piece it encounters
during the sweep; it may not jump over pieces.

This is the first multi-segment move in the fragment series and is
where GDL's "enumerate every legal move atomically" model gets
verbose: we list every (segment-1, segment-2-direction, segment-2-
length) combination as a separate `legal` rule. The state-transition
clauses handle the 2-segment effect (origin clears; destination
fills; piece on the destination is captured; any piece on the swept
path before the destination must NOT exist or the move is illegal).

Same testing strategy as steps 1-2: an S-expression parser + a series
of structural invariants. Reasoner-level legal-move equivalence vs
the Python engine is deferred until a GDL reasoner is wired in.
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'step3_add_rook.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-3 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


# ---- step-2 invariants still hold ----------------------------------------

def test_step3_parses(parsed):
    assert len(parsed) > 0


def test_step3_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step3_white_moves_first(parsed):
    has_init = any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and f[1] == ('control', 'white')
        for f in parsed)
    assert has_init


def test_step3_has_terminal_and_goal(parsed):
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


# ---- rook in initial state ----------------------------------------------

def _init_cells(parsed):
    return [f[1] for f in parsed
            if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
            and isinstance(f[1], tuple) and f[1][0] == 'cell']


def test_step3_has_rooks_at_correct_squares(parsed):
    """Per RULEBOOK_v2.md back rank (Bishop-Queen-Rook-Knight-Knight-
    Rook-King-Bishop): White rooks at c1 and f1; Black rooks at c8
    and f8 (rotational symmetric setup)."""
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    assert pieces.get(('c', '1')) == ('white', 'rook'), (
        f"expected white rook at c1; got {pieces.get(('c', '1'))}")
    assert pieces.get(('f', '1')) == ('white', 'rook'), (
        f"expected white rook at f1; got {pieces.get(('f', '1'))}")
    assert pieces.get(('c', '8')) == ('black', 'rook'), (
        f"expected black rook at c8; got {pieces.get(('c', '8'))}")
    assert pieces.get(('f', '8')) == ('black', 'rook'), (
        f"expected black rook at f8; got {pieces.get(('f', '8'))}")


def test_step3_kings_and_queens_still_correct(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    assert pieces.get(('g', '1')) == ('white', 'king')
    assert pieces.get(('b', '1')) == ('white', 'queen')
    assert pieces.get(('b', '8')) == ('black', 'king')
    assert pieces.get(('g', '8')) == ('black', 'queen')


def test_step3_pawns_still_correct(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    for f in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'):
        assert pieces.get((f, '2')) == ('white', 'pawn'), (
            f"missing white pawn at {f}2")
        assert pieces.get((f, '7')) == ('black', 'pawn'), (
            f"missing black pawn at {f}7")


def test_step3_no_extra_piece_types(parsed):
    """step 3 = kings + queens + pawns + rooks. No bishop/knight/
    boulder yet."""
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    piece_types = {p[1] for p in pieces.values()}
    allowed = {'king', 'queen', 'pawn', 'rook'}
    extras = piece_types - allowed
    assert not extras, (
        f"step 3 fragment contains forbidden piece types {extras}; "
        f"step 3 is kings+queens+pawns+rooks only.")


# ---- rook-specific rules -------------------------------------------------

def _flatten(form):
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


def test_step3_has_rook_move_rules(parsed):
    """At least one legal rule references 'rook' as the moving piece."""
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if 'rook' in atoms:
                return
    raise AssertionError("no legal rule mentions 'rook'")


def test_step3_mentions_two_segment_move():
    """The rook's defining feature is the 2-segment move. Source must
    reference the concept somewhere — via a 'rook_segment' /
    'rook_step' / 'first_step' helper or a comment header."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('segment' in text or 'first_step' in text or
            'rook_step' in text or 'two-step' in text or
            '2-segment' in text or 'second_step' in text), (
        "step-3 GDL should reference the 2-segment rook move concept")


def test_step3_has_rook_blocking_rule():
    """Rook can't jump over pieces — there must be a 'path_clear' or
    similar predicate, or an explicit (not occupied) chain."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('path_clear' in text or 'not (occupied' in text or
            'blocked' in text or 'between' in text), (
        "step-3 GDL must encode the rook's no-jumping constraint")
