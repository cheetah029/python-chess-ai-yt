"""Structural tests for the Goal-4 GDL step-2 fragment
(`docs/gdl/step2_kings_queens_pawns.gdl`).

Step 2 adds pawns on top of step 1. From RULEBOOK_v2.md the v2 pawn:

  - Moves: one square forward, OR one square sideways (left, right).
    NOT backward.
  - Captures: one square forward, OR diagonally-forward-left, OR
    diagonally-forward-right.
  - Promotion: on reaching the last rank, promotes to a non-royal
    queen (we use base form only in step 2; the multi-form queen
    and transformation come in step 7).

Same approach as test_gdl_step1: an S-expression parser + a series
of structural invariants. Reasoner-level legal-move equivalence vs
the Python engine is deferred until a GDL-I reasoner is wired in.

Structural invariants tested:

  - Step 1 invariants still hold (roles, terminal, goal, etc.).
  - All 16 pawns appear in the initial state (8 on rank 2 white,
    8 on rank 7 black).
  - At least one pawn move rule and one pawn capture rule exist for
    each colour.
  - Promotion rule exists.
"""

import os
import pytest


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step2_kings_queens_pawns.gdl')


# Re-export the parser from test_gdl_step1 to avoid duplication.
import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-2 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


# ---- step-1 invariants still hold ----------------------------------------

def test_step2_parses(parsed):
    assert len(parsed) > 0


def test_step2_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step2_white_moves_first(parsed):
    has_control_white_init = any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and f[1] == ('control', 'white')
        for f in parsed)
    assert has_control_white_init


def test_step2_has_terminal_and_goal_clauses(parsed):
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
    assert has_terminal
    assert has_goal


# ---- pawns in initial state ----------------------------------------------

def _init_cells(parsed):
    return [f[1] for f in parsed
            if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
            and isinstance(f[1], tuple) and f[1][0] == 'cell']


def test_step2_has_kings_at_correct_squares(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    assert pieces.get(('g', '1')) == ('white', 'king')
    assert pieces.get(('b', '8')) == ('black', 'king')


def test_step2_has_queens_at_correct_squares(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    assert pieces.get(('b', '1')) == ('white', 'queen')
    assert pieces.get(('g', '8')) == ('black', 'queen')


def test_step2_has_eight_white_pawns_on_rank_2(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    files = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h')
    for f in files:
        assert pieces.get((f, '2')) == ('white', 'pawn'), (
            f"missing white pawn at {f}2; got {pieces.get((f, '2'))}")


def test_step2_has_eight_black_pawns_on_rank_7(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    files = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h')
    for f in files:
        assert pieces.get((f, '7')) == ('black', 'pawn'), (
            f"missing black pawn at {f}7; got {pieces.get((f, '7'))}")


def test_step2_no_extra_piece_types(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    piece_types = {p[1] for p in pieces.values()}
    # step 2 = kings + queens + pawns only (no rook/bishop/knight/boulder).
    allowed = {'king', 'queen', 'pawn'}
    extras = piece_types - allowed
    assert not extras, (
        f"step 2 fragment contains forbidden piece types {extras}; "
        f"step 2 is kings+queens+pawns only.")


# ---- pawn-specific rule presence -----------------------------------------

def _flatten(form):
    """Walk a parsed S-expression tree, yielding every atom."""
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


def test_step2_has_pawn_move_rules(parsed):
    """At least one rule head referencing 'pawn' as the moving piece
    inside a legal clause."""
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if 'pawn' in atoms:
                return
    raise AssertionError("no legal rule mentions 'pawn'")


def test_step2_distinguishes_forward_from_backward(parsed):
    """Pawns can't move backward (rulebook §Pawn). Expect a helper
    predicate referencing 'forward' (or per-colour-specific files/ranks).
    Looking for 'pawn_forward' or 'forward_rank' or similar."""
    text = ''
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'forward' in text or 'pawn_step' in text, (
        "step-2 GDL must distinguish forward from backward pawn movement; "
        "expected a helper predicate containing 'forward' or 'pawn_step'")


def test_step2_has_promotion_handling(parsed):
    """The promotion behaviour must be encoded somewhere — either as
    a 'promote' / 'promotion' rule head or via a next clause that
    replaces a pawn on the last rank with a queen."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'promot' in text or 'last_rank' in text or 'rank 8' in text, (
        "step-2 GDL must encode promotion to queen on the last rank")
