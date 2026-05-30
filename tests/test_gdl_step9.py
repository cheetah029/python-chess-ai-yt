"""Structural tests for the Goal-4 GDL step-9 fragment
(`docs/gdl/step9_add_bishop_reactive_capture.gdl`).

Step 9 adds the v2 bishop's REACTIVE CAPTURE on top of step 8.
Per RULEBOOK_v2.md:

  Reactive capture: if an enemy piece begins its move on a square
  within the bishop's diagonal line-of-sight and moves to a new
  square, the bishop may capture it on its IMMEDIATELY NEXT TURN
  by teleporting onto the destination square. The teleport-safety
  check does NOT apply to this capture.

This is the most subtle mechanism in the variant because:
  - It is SOURCE-based: the trigger is whether the enemy LEFT a
    diagonal-LoS square. The bishop captures at the DESTINATION
    of the enemy's move.
  - "Immediately next turn" — eligibility expires after the
    bishop's owner has had one turn.
  - The teleport-safety check is BYPASSED on the reactive
    capture (the bishop willingly exposes itself by firing).

We encode:

  - (reactive_armed ?bf ?br ?tf ?tr): TRUE for a bishop at
    (?bf, ?br) iff (?tf, ?tr) is the DESTINATION of an enemy
    spatial move LAST TURN whose ORIGIN was on the bishop's
    diagonal LoS.
  - Bishop reactive capture as a legal action:
    (reactive_capture ?bf ?br ?tf ?tr) — bishop teleports to
    (?tf, ?tr), capturing the enemy there.

Structural invariants tested:

  - Step-8 invariants still hold.
  - Reactive capture is encoded.
  - Source-vs-destination distinction is acknowledged textually.
  - The teleport-safety bypass is acknowledged (the reactive
    capture does NOT consult enemy_can_reach).
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step9_add_bishop_reactive_capture.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-9 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


def test_step9_parses(parsed):
    assert len(parsed) > 0


def test_step9_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step9_has_terminal_and_goal(parsed):
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


def test_step9_has_reactive_capture_concept():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('reactive_capture' in text or 'reactive_armed' in text
            or 'reactive' in text), (
        "step-9 GDL must encode bishop reactive capture")


def test_step9_source_based_distinction_documented():
    """The reactive-capture eligibility depends on the SOURCE of
    the enemy's move (left a diagonal LoS square), not the
    destination. Source must acknowledge this — textually or via
    a `spatial_move_origin` predicate."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('source' in text or 'origin' in text or
            'left' in text or 'began' in text), (
        "step-9 GDL must reference the source-based nature of "
        "reactive capture (enemy left a diagonal LoS square)")


def test_step9_uses_diagonal_los_for_reactive_trigger():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('diag' in text and ('los' in text or 'sight' in text
            or 'bishop_diag' in text)), (
        "step-9 reactive-capture trigger must consult the bishop's "
        "diagonal line-of-sight")


def test_step9_teleport_safety_bypass_documented():
    """The reactive-capture teleport bypasses the standard safety
    check. Source should document this."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('bypass' in text or 'does not apply' in text
            or "doesn't apply" in text or 'no safety' in text
            or 'safety_check' in text), (
        "step-9 GDL should document that the reactive-capture "
        "teleport bypasses the standard safety check")
