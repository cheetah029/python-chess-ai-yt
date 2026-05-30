"""Structural tests for the Goal-4 GDL step-4 fragment
(`docs/gdl/step4_add_knight.gdl`).

Step 4 adds the v2 knight to step 3's kings+queens+pawns+rooks base.
This step covers ONLY the radius-2 movement; the reactive jump-capture
and the post-non-capture-jump invulnerability are deferred to step 8.

From RULEBOOK_v2.md (Knight, Movement section):

  Move (radius-2): to any of the 16 squares within a chebyshev-2
  pattern:
    - Two squares orthogonally,
    - Two squares diagonally, or
    - L-shape: two squares orthogonally then one square perpendicular.

  The knight may jump over other pieces.

  Standard capture: the knight captures any enemy piece on its
  landing square.

That's 16 destinations from any non-edge square. Step 4 enumerates
them as per-vector legal-move rules without any blocking constraint
(the knight jumps).

Structural invariants tested:

  - Step-3 invariants still hold (roles, white-moves-first, terminal,
    goal).
  - 4 knights in init at rulebook-correct squares (d1, e1 / d8, e8).
  - No extra piece types beyond king/queen/pawn/rook/knight (boulder
    deferred to step 6).
  - At least one legal rule mentions 'knight'.
  - A 'knight_step' / 'radius2' / 'chebyshev' / 'knight_move' helper
    exists distinguishing the 16-destination radius-2 pattern.
  - NO jump-capture / NO invulnerability constructs yet (those are
    step 8). This is a positive assertion that the fragment is the
    expected scope.
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step4_add_knight.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-4 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


# ---- step-3 invariants still hold ----------------------------------------

def test_step4_parses(parsed):
    assert len(parsed) > 0


def test_step4_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step4_white_moves_first(parsed):
    has_init = any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and f[1] == ('control', 'white')
        for f in parsed)
    assert has_init


def test_step4_has_terminal_and_goal(parsed):
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


# ---- knight in initial state ---------------------------------------------

def _init_cells(parsed):
    return [f[1] for f in parsed
            if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
            and isinstance(f[1], tuple) and f[1][0] == 'cell']


def test_step4_knights_at_rulebook_squares(parsed):
    """Per RULEBOOK_v2.md back rank: knights at d1, e1 / d8, e8.

    Back rank: Bishop-Queen-Rook-Knight-Knight-Rook-King-Bishop.

    White: a1=B, b1=Q, c1=R, d1=N, e1=N, f1=R, g1=K, h1=B
    Black: a8=B, b8=K, c8=R, d8=N, e8=N, f8=R, g8=Q, h8=B
    """
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    assert pieces.get(('d', '1')) == ('white', 'knight'), (
        f"expected white knight at d1; got {pieces.get(('d', '1'))}")
    assert pieces.get(('e', '1')) == ('white', 'knight'), (
        f"expected white knight at e1; got {pieces.get(('e', '1'))}")
    assert pieces.get(('d', '8')) == ('black', 'knight'), (
        f"expected black knight at d8; got {pieces.get(('d', '8'))}")
    assert pieces.get(('e', '8')) == ('black', 'knight'), (
        f"expected black knight at e8; got {pieces.get(('e', '8'))}")


def test_step4_all_step3_pieces_still_present(parsed):
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    # kings + queens
    assert pieces.get(('g', '1')) == ('white', 'king')
    assert pieces.get(('b', '1')) == ('white', 'queen')
    assert pieces.get(('b', '8')) == ('black', 'king')
    assert pieces.get(('g', '8')) == ('black', 'queen')
    # rooks
    assert pieces.get(('c', '1')) == ('white', 'rook')
    assert pieces.get(('f', '1')) == ('white', 'rook')
    assert pieces.get(('c', '8')) == ('black', 'rook')
    assert pieces.get(('f', '8')) == ('black', 'rook')
    # pawns
    for f in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'):
        assert pieces.get((f, '2')) == ('white', 'pawn')
        assert pieces.get((f, '7')) == ('black', 'pawn')


def test_step4_no_extra_piece_types(parsed):
    """step 4 = kings + queens + pawns + rooks + knights only.
    No bishop / boulder yet."""
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    piece_types = {p[1] for p in pieces.values()}
    allowed = {'king', 'queen', 'pawn', 'rook', 'knight'}
    extras = piece_types - allowed
    assert not extras, (
        f"step 4 fragment contains forbidden piece types {extras}; "
        f"step 4 is kings+queens+pawns+rooks+knights only.")


# ---- knight rule presence -----------------------------------------------

def _flatten(form):
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


def test_step4_has_knight_legal_rule(parsed):
    """At least one legal rule references 'knight' as the moving
    piece."""
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if 'knight' in atoms:
                return
    raise AssertionError("no legal rule mentions 'knight'")


def test_step4_mentions_radius2_or_knight_step_helper():
    """Step 4's defining feature is the 16-square radius-2 pattern.
    Source must encode it via a helper predicate or via direct
    enumeration documented in a comment."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('knight_step' in text or 'radius' in text or
            'chebyshev' in text or 'knight_move' in text), (
        "step-4 GDL should reference the radius-2 knight-step concept")


def test_step4_does_not_yet_have_jump_capture_or_invuln():
    """Sanity guard: step 4 is movement-only. jump_capture and
    invuln are explicitly deferred to step 8."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'jump_capture' not in text, (
        "step 4 should NOT contain jump_capture (deferred to step 8)")
    # We allow the word 'invuln' in COMMENT text describing what's
    # deferred, so we check for an actual `legal` clause involving
    # it. Coarse: ensure no `legal ... invuln` substring exists.
    assert ' invuln ' not in text or 'invulnerability' in text, (
        "step 4 should not encode invuln semantics (deferred to step 8)")
