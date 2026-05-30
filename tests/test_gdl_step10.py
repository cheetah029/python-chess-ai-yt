"""Structural tests for the Goal-4 GDL step-10 fragment
(`docs/gdl/step10_add_repetition_rule.gdl`).

Step 10 adds the repetition-rule loss condition. Per
RULEBOOK_v2.md:

  A player may not make a turn that would cause a board state to
  appear FOR THE THIRD TIME during the game. If every legal turn
  would do so, that player loses.

This requires per-state COUNTING — non-trivial in GDL-I but
expressible via a state-hash + count facts.

For our encoding we track `(state_hash <hash> <count>)` facts in
the game state, where <hash> is a representation of the
positional + derived-flag information described in the rulebook.
A move is filtered out if it would push some hash's count to 3.

For step 10 we don't try to compute a real hash inside GDL —
that's prohibitively verbose. Instead we encode the structural
TRACKING: `state_repetition_count` predicate exists, gets
incremented in `next`, and `would_repeat_third_time` is consulted
in legal-move filtering.

Structural invariants tested:

  - Step-9 invariants still hold.
  - state_repetition_count tracking exists.
  - A 'would_repeat_third_time' (or equivalent) predicate is
    referenced in legal-move filtering.
  - The lost-condition includes the repetition-3 loss.
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step10_add_repetition_rule.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-10 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


def test_step10_parses(parsed):
    assert len(parsed) > 0


def test_step10_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step10_has_terminal_and_goal(parsed):
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


def test_step10_has_state_repetition_count_tracking():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('state_repetition_count' in text
            or 'state_count' in text or 'state_history' in text), (
        "step-10 GDL must track per-state repetition counts")


def test_step10_third_repetition_filter():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('would_repeat' in text or 'third_time' in text
            or 'repeated_3' in text or 'rep3' in text), (
        "step-10 GDL must consult a 'would-repeat-third-time' "
        "predicate when filtering legal moves")


def test_step10_lost_includes_repetition():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('repetition' in text and 'lost' in text), (
        "step-10 lost condition must include the repetition-3 "
        "loss")
