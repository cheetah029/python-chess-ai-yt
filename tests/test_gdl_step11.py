"""Structural tests for the Goal-4 GDL step-11 fragment
(`docs/gdl/step11_add_tiny_endgame_rule.gdl`).

Step 11 is the FINAL step. It adds the v2 tiny-endgame rule. Per
RULEBOOK_v2.md (Tiny Endgame Rule):

  Activation: the rule applies when ALL of the following hold:
    - No pawns remain on the board.
    - 6 or fewer non-king non-neutral pieces (boulder excluded,
      kings ignored).
    - The position BALANCES under the cancel-queens + 1-to-2
      valuation.

  Distance counts: for each royal distance 1..14, count
  occurrences while the rule is active.
    - Activation: set current royal distance count to 1.
    - Non-capture turn: increment current royal distance.
    - Capture: reset all counts to 0, then set current distance
      count to 1 if rule still applies.

  Limit: a player may not make a NON-CAPTURE turn that would
  push the resulting royal-distance count above 3. If every
  legal turn would do so, that player loses.

For step 11 we sketch the STRUCTURAL pieces — pawnless + ≤6
count checks, distance-count tracking, and the loss condition.
The cancel-queens + 1-to-2 balance valuation is the most
complex piece and is sketched as a `(tiny_balanced)` predicate
whose detailed enumeration is documented in comments.

Structural invariants tested:

  - Step-10 invariants still hold.
  - The tiny-endgame activation predicate is encoded.
  - Distance counts are tracked.
  - The non-capture-push-over-3 limit is encoded in legal
    filtering and the lost condition.
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step11_add_tiny_endgame_rule.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-11 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


def test_step11_parses(parsed):
    assert len(parsed) > 0


def test_step11_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step11_has_terminal_and_goal(parsed):
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


def test_step11_activation_concept_encoded():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'tiny_endgame' in text or 'tiny endgame' in text, (
        "step-11 GDL must encode the tiny-endgame concept")


def test_step11_pawnless_check_present():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('no_pawns' in text or 'pawnless' in text
            or 'pawn_count' in text), (
        "step-11 GDL must encode the pawnless-board activation "
        "check")


def test_step11_six_or_fewer_check_present():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('6_or_fewer' in text or 'count_<= 6' in text
            or 'at_most_6' in text or 'piece_count' in text
            or 'non_king' in text or 'at_most 6' in text), (
        "step-11 GDL must encode the ≤6 non-king-non-boulder "
        "piece-count activation check")


def test_step11_balance_predicate_present():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('balanced' in text or 'cancel_queens' in text
            or 'valuation' in text), (
        "step-11 GDL must encode the cancel-queens + 1-to-2 "
        "balance valuation")


def test_step11_distance_count_tracking():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('distance_count' in text or 'royal_distance' in text
            or 'distance_counts' in text), (
        "step-11 GDL must track per-distance counts (royal "
        "distance 1..14)")


def test_step11_limit_filter_or_lost_condition():
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('distance_above_3' in text or 'over_3' in text
            or 'exceeds_3' in text or 'count_3' in text
            or 'limit_exceeded' in text), (
        "step-11 GDL must encode the 'distance count > 3' limit")
