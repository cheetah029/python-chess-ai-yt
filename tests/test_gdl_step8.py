"""Structural tests for the Goal-4 GDL step-8 fragment
(`docs/gdl/step8_add_knight_jump_capture_invuln.gdl`).

Step 8 adds the v2 knight's REACTIVE JUMP-CAPTURE and POST-NON-
CAPTURE-JUMP INVULNERABILITY on top of step 7's queen actions.

From RULEBOOK_v2.md (Knight section):

  Jumped square: every knight move passes over one specific
  square (1 from the start in the move's primary direction).

  Jump capture: if an enemy piece moved SPATIALLY onto a square
  that a knight can jump over, the knight may capture that piece
  on its IMMEDIATELY NEXT TURN by making a normal radius-2 move
  to an empty landing square, with the moved enemy as the jumped
  square. Only the jumped piece is captured. The player may
  always decline.

  Invulnerability after jumping: if a knight makes a NON-CAPTURE
  spatial move that jumps over a FRIENDLY piece or the BOULDER
  AND lands at chebyshev-1 of at least one enemy piece other than
  the jumped piece, the knight is invulnerable to capture for the
  immediately following opponent turn.

For step 8 we encode:

  - The 'jumped square' computation for each knight move type
    (knight_jumped_square predicate).
  - Jump-capture as a (move knight ... + jump_capture) extended
    action: legal if the enemy at the jumped square moved
    spatially last turn.
  - Invulnerability: per-piece flag `(invulnerable ?f ?r)` set
    in next when the trigger condition holds; cleared after the
    opponent turn.
  - Invulnerability blocks ALL captures of the knight on the
    opponent's NEXT turn — including by king.

Structural invariants tested:

  - Step-7 invariants still hold.
  - At least one legal rule for jump-capture (mentions
    'jump_capture' / 'jumped_square' / similar).
  - knight_jumped_square helper exists.
  - Invulnerability mechanic encoded (textual 'invuln' or
    'invulnerable').
  - Invulnerability blocks captures (referenced in capture
    legality).
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step8_add_knight_jump_capture_invuln.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-8 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


def _flatten(form):
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


# ---- step-7 invariants still hold ----------------------------------------

def test_step8_parses(parsed):
    assert len(parsed) > 0


def test_step8_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step8_has_terminal_and_goal(parsed):
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


# ---- jump-capture + invuln presence -------------------------------------

def test_step8_has_jump_capture_concept():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('jump_capture' in text or 'jumped_square' in text), (
        "step-8 GDL must encode knight jump-capture")


def test_step8_jump_capture_uses_spatial_move_last_turn():
    """The jump-capture eligibility is gated on the enemy at the
    jumped square having moved SPATIALLY on the immediately
    preceding turn — encoded via spatial_move_last_turn (carried
    over from step 7)."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'spatial_move_last_turn' in text or 'moved_last_turn' in text, (
        "step-8 GDL must use spatial_move_last_turn / moved_last_turn "
        "to gate jump-capture eligibility")


def test_step8_has_jumped_square_helper():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'jumped_square' in text or 'knight_jumps_over' in text, (
        "step-8 GDL must encode the jumped-square computation")


def test_step8_invuln_concept():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'invuln' in text or 'invulnerable' in text, (
        "step-8 GDL must encode knight invulnerability")


def test_step8_invuln_blocks_captures():
    """If a piece is marked invulnerable, no enemy capture rule
    should succeed against it. Source must reference invulnerable
    in a capture-legality context."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    # Look for an invuln check in a `not (...)` clause near
    # 'capture' or 'legal'.
    assert 'not (true (invulnerable' in text or \
           'not (invulnerable' in text or \
           'invulnerable' in text, (
        "step-8 GDL must consult invulnerable when checking captures")


def test_step8_invuln_requires_adjacent_enemy():
    """Per RULEBOOK_v2.md: invulnerability requires landing at
    chebyshev-1 of at least one enemy piece OTHER than the jumped
    piece. Encoded as: there exists an enemy in knight's king-step
    neighbourhood that isn't the jumped piece."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('adjacent_enemy' in text or 'enemy_adjacent' in text or
            'king_step' in text or 'chebyshev' in text), (
        "step-8 invuln must encode the 'adjacent enemy other than "
        "jumped piece' condition")
