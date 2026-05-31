"""Quick sanity checks for steps 8-11 via the INTEGRATED GDL.

These are smoke-tests, not exhaustive validation. Each step adds
cross-turn state machinery (spatial_move_last_turn for jump-capture
and bishop reactive; state_repetition_count for repetition;
distance_count for tiny endgame). Comprehensive validation
requires constructing specific positions and verifying derived
rule behavior — deferred to a dedicated cross-validation harness
that compares GGP's legal_moves to engine.get_all_legal_turns().

What these tests verify NOW:
- integrated.gdl PARSES (no syntax errors)
- step-specific rules are PRESENT in the integrated file
- Legal-move enumeration runs to completion without crashing
- A few specific rule-presence assertions per step
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from ggp.game import GGPGame


INTEGRATED = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'integrated.gdl')


def _gdl_text():
    with open(INTEGRATED) as f:
        return f.read()


# ---- Step 8 (knight jump-capture + invulnerability) ---------------------

def test_step8_jump_capture_rule_in_integrated():
    text = _gdl_text()
    assert 'jump_capture' in text, (
        'integrated.gdl must contain the jump_capture legal rule '
        '(step 8 mechanism)')


def test_step8_knight_jumped_square_helper_present():
    text = _gdl_text()
    assert 'knight_jumped_square' in text


def test_step8_invulnerable_concept_present():
    text = _gdl_text()
    assert 'invulnerable' in text or 'invuln' in text


def test_step8_legal_moves_does_not_crash():
    """End-to-end: enumerate legal moves on a state and don't crash
    on the jump_capture / invulnerable machinery."""
    g = GGPGame.from_file(INTEGRATED)
    moves = g.legal_moves('white')
    assert isinstance(moves, list)


# ---- Step 9 (bishop reactive capture) -----------------------------------

def test_step9_reactive_capture_rule_in_integrated():
    text = _gdl_text()
    assert 'reactive_capture' in text


def test_step9_reactive_armed_helper_present():
    text = _gdl_text()
    assert 'reactive_armed' in text


def test_step9_spatial_move_origin_tracking_present():
    """Step 9 introduces spatial_move_origin (in addition to
    spatial_move_last_turn from step 7) so the bishop's
    source-based reactive trigger can match an enemy's origin
    square against the bishop's diagonal LoS."""
    text = _gdl_text()
    assert 'spatial_move_origin' in text


# ---- Step 10 (repetition rule) ------------------------------------------

def test_step10_state_repetition_count_tracking():
    text = _gdl_text()
    assert 'state_repetition_count' in text


def test_step10_would_repeat_third_time_predicate():
    text = _gdl_text()
    assert 'would_repeat_third_time' in text


def test_step10_repetition_filter_present():
    """The legal-move filter that excludes 3rd-repetition moves
    is encoded via legal_after_repetition_filter (or similar)."""
    text = _gdl_text()
    assert 'legal_after_repetition_filter' in text or \
        'no_legal_after_repetition_filter' in text


# ---- Step 11 (tiny endgame rule) ----------------------------------------

def test_step11_tiny_endgame_active_predicate():
    text = _gdl_text()
    assert 'tiny_endgame_active' in text


def test_step11_distance_count_tracking():
    text = _gdl_text()
    assert 'distance_count' in text


def test_step11_pawnless_check_present():
    text = _gdl_text()
    assert 'pawnless' in text or 'any_pawn' in text


def test_step11_tiny_endgame_limit_filter_present():
    """The non-capture-distance-count > 3 filter on legal moves."""
    text = _gdl_text()
    assert 'tiny_endgame_limit_exceeded' in text or \
        'legal_after_tiny_filter' in text
