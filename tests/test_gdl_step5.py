"""Structural tests for the Goal-4 GDL step-5 fragment
(`docs/gdl/step5_add_bishop.gdl`).

Step 5 adds the v2 bishop's TELEPORT MOVEMENT to step 4's
kings+queens+pawns+rooks+knights base. The bishop's reactive
capture is deferred to step 9; queen-as-bishop transformation is
deferred to step 7; the boulder (which the safety check excludes)
arrives in step 6.

From RULEBOOK_v2.md (Bishop section):

  Movement: teleport to any empty square that is NOT currently
  moveable to or capturable by any enemy piece. Enemy bishops,
  queen-as-bishop, and the boulder are EXCLUDED from this safety
  check. Capturable squares include squares reachable by the
  knight's jump capture.

For step 5 the exclusions reduce to "enemy bishops" only (queen-as-
bishop and boulder are absent). The destination-vs-source
distinction (why enemy bishops are excluded — their reactive
capture depends on where the moving piece *came from*, not on
where it goes) is documented in the elaborated rulebook but isn't
mechanically tested here — that's step 9 territory.

What we DO test structurally in step 5:

  - Step-4 invariants still hold (roles, white-moves-first, terminal,
    goal, no extra piece types beyond king/queen/pawn/rook/knight/
    bishop).
  - 4 bishops in init at rulebook-correct squares (a1, h1 / a8, h8).
  - At least one legal rule mentions 'bishop'.
  - The safety check excludes enemy bishops (textually: the source
    contains a comment OR a predicate name acknowledging the
    exclusion).
  - Knight jump-capture destination is INCLUDED in the safety
    check (per rulebook: "capturable squares include knight
    jump-capture").
  - NO reactive-capture / NO queen-as-bishop constructs yet
    (positive scope assertion).
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step5_add_bishop.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-5 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


# ---- step-4 invariants still hold ----------------------------------------

def test_step5_parses(parsed):
    assert len(parsed) > 0


def test_step5_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step5_white_moves_first(parsed):
    has_init = any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and f[1] == ('control', 'white')
        for f in parsed)
    assert has_init


def test_step5_has_terminal_and_goal(parsed):
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


# ---- bishops in initial state --------------------------------------------

def _init_cells(parsed):
    return [f[1] for f in parsed
            if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
            and isinstance(f[1], tuple) and f[1][0] == 'cell']


def test_step5_bishops_at_rulebook_squares(parsed):
    """Per RULEBOOK_v2.md back rank
    (Bishop-Queen-Rook-Knight-Knight-Rook-King-Bishop):

      White: a1=B, ..., h1=B
      Black: a8=B, ..., h8=B   (rotational symmetric)
    """
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    assert pieces.get(('a', '1')) == ('white', 'bishop'), (
        f"expected white bishop at a1; got {pieces.get(('a', '1'))}")
    assert pieces.get(('h', '1')) == ('white', 'bishop'), (
        f"expected white bishop at h1; got {pieces.get(('h', '1'))}")
    assert pieces.get(('a', '8')) == ('black', 'bishop'), (
        f"expected black bishop at a8; got {pieces.get(('a', '8'))}")
    assert pieces.get(('h', '8')) == ('black', 'bishop'), (
        f"expected black bishop at h8; got {pieces.get(('h', '8'))}")


def test_step5_all_step4_pieces_still_present(parsed):
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
    # knights
    assert pieces.get(('d', '1')) == ('white', 'knight')
    assert pieces.get(('e', '1')) == ('white', 'knight')
    assert pieces.get(('d', '8')) == ('black', 'knight')
    assert pieces.get(('e', '8')) == ('black', 'knight')
    # pawns
    for f in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'):
        assert pieces.get((f, '2')) == ('white', 'pawn')
        assert pieces.get((f, '7')) == ('black', 'pawn')


def test_step5_no_extra_piece_types(parsed):
    """step 5 = kings + queens + pawns + rooks + knights + bishops.
    No boulder yet (step 6)."""
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in _init_cells(parsed)
              if len(p) == 5}
    piece_types = {p[1] for p in pieces.values()}
    allowed = {'king', 'queen', 'pawn', 'rook', 'knight', 'bishop'}
    extras = piece_types - allowed
    assert not extras, (
        f"step 5 fragment contains forbidden piece types {extras}; "
        f"step 5 is kings+queens+pawns+rooks+knights+bishops only.")


# ---- bishop rule presence + structure ------------------------------------

def _flatten(form):
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


def test_step5_has_bishop_legal_rule(parsed):
    """At least one legal rule references 'bishop' as the moving
    piece."""
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if 'bishop' in atoms:
                return
    raise AssertionError("no legal rule mentions 'bishop'")


def test_step5_excludes_enemy_bishops_from_safety_check():
    """Per RULEBOOK_v2.md: enemy bishops are EXCLUDED from the
    teleport-safety check. The source must acknowledge this — either
    via a comment (textual: 'exclud') or via a predicate that
    distinguishes 'enemy non-bishop' from 'enemy bishop'."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('exclud' in text or 'non_bishop' in text or
            'except.*bishop' in text or 'not.*bishop' in text), (
        "step-5 GDL must document/encode the enemy-bishop exclusion "
        "from the teleport-safety check")


def test_step5_includes_knight_jump_capture_in_safety():
    """Per RULEBOOK_v2.md: 'Capturable squares include squares
    reachable by the knight's jump capture.' The source must
    acknowledge this — either textually or via a predicate that
    treats chebyshev-1-of-enemy-knight squares as capturable."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('jump' in text and ('knight' in text or 'chebyshev' in text)), (
        "step-5 GDL must include knight jump-capture squares in the "
        "teleport-safety check")


def test_step5_mentions_teleport_or_safety_concept():
    """Bishop's defining feature: teleport with safety filter.
    Source must reference 'teleport' or 'safety' or 'safe'."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('teleport' in text or 'safety' in text or
            'safe_square' in text or 'enemy_can_reach' in text), (
        "step-5 GDL must reference the teleport-safety concept")


def test_step5_no_reactive_capture_yet():
    """Sanity guard: step 5 is teleport-only. Reactive capture is
    explicitly deferred to step 9. The string 'reactive' should
    appear only in deferral comments, not in active legal rules."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    # No 'legal' rule should mention 'reactive' — only comments may.
    # Check by removing comments first and looking for 'reactive' in
    # the code.
    code_only = '\n'.join(
        ln.split(';')[0] for ln in text.split('\n'))
    assert 'reactive' not in code_only, (
        "step 5 must NOT encode bishop reactive capture (deferred to "
        "step 9)")


def test_step5_no_queen_as_bishop_yet():
    """Sanity: queen transformation is step 7."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    code_only = '\n'.join(
        ln.split(';')[0] for ln in text.split('\n'))
    assert 'transform' not in code_only, (
        "step 5 must NOT encode queen transformation (deferred to step 7)")
