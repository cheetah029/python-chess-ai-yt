"""Every metric tested on a trace whose answer is checkable by hand.

The project brief requires exactly this. The reason is specific to an
ablation study: a metric that is merely MISCALIBRATED still produces
plausible numbers, and a systematic error would appear as a rule
"contribution" that is really a bug in the measuring instrument. Such an
error cannot be caught downstream, because Phase 4 has nothing to
compare against.

So these tests use hand-built records where the expected value is
arithmetic anyone can redo, not fixtures captured from a run.
"""

import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from experiments.variants import make_engine
from lgref.experiments import metrics


# ---- hand-built game records --------------------------------------------

def _record(turns, **kw):
    rec = {
        'winner': None, 'loss_reason': None, 'total_turns': len(turns),
        'total_captures': 0, 'turn_cap_reached': False,
        'tiny_endgame_activated': False, 'repetition_blocks': 0,
        'endgame_blocks': 0, 'turns': turns,
    }
    rec.update(kw)
    return rec


def test_rule_usage_counts_each_turn_type():
    """3 moves, 2 boulder, 1 manipulation, 0 transformation — by hand."""
    turns = ([{'turn_type': 'move'}] * 3
             + [{'turn_type': 'boulder'}] * 2
             + [{'turn_type': 'manipulation'}])
    assert metrics.rule_usage(_record(turns)) == {
        'move': 3, 'boulder': 2, 'manipulation': 1, 'transformation': 0}


def test_rule_usage_reports_zero_not_missing_for_ablated_rules():
    """A no-boulder variant must yield boulder=0, not a missing key, or
    the Parquet schema differs between variants and analysis breaks."""
    usage = metrics.rule_usage(_record([{'turn_type': 'move'}]))
    assert usage['boulder'] == 0
    assert set(usage) == {'move', 'boulder', 'manipulation', 'transformation'}


def test_repeated_state_frequency_is_the_fraction_seen_before():
    """4 turns, 2 with repetition_count >= 2 -> exactly 0.5."""
    turns = [{'repetition_count': 1}, {'repetition_count': 2},
             {'repetition_count': 1}, {'repetition_count': 3}]
    assert metrics.repeated_state_frequency(_record(turns)) == 0.5


def test_repeated_state_frequency_is_zero_for_an_empty_game():
    assert metrics.repeated_state_frequency(_record([])) == 0.0


def test_turn_cap_is_recorded_separately_from_a_drawn_game():
    """A game stopped by the cap is CENSORED, not drawn. Collapsing the
    two would turn 'we ran out of patience' into a property of the
    rules."""
    capped = metrics.outcome_row(
        _record([{}] * 50, winner=None, total_turns=50), max_turns=50)
    assert capped['turn_cap_reached'] is True
    assert capped['draw_or_censored'] is True
    assert capped['decisive'] is False

    drawn = metrics.outcome_row(
        _record([{}] * 10, winner=None, loss_reason='repetition',
                total_turns=10), max_turns=50)
    assert drawn['turn_cap_reached'] is False
    assert drawn['loss_reason'] == 'repetition'


def test_outcome_row_marks_the_winning_side():
    row = metrics.outcome_row(
        _record([{}] * 7, winner='white', total_turns=7), max_turns=100)
    assert (row['white_win'], row['black_win'], row['decisive']) == (
        True, False, True)


# ---- policy-effective branching -----------------------------------------

def test_policy_effective_branching_counts_competitive_moves():
    """Best is 100; at a 10% threshold the cut is 10. Visits
    [100, 50, 10, 9, 1] -> 100, 50 and 10 qualify; 9 and 1 do not = 3."""
    assert metrics.policy_effective_branching([100, 50, 10, 9, 1], 0.10) == 3


def test_policy_effective_branching_is_one_when_search_is_decisive():
    assert metrics.policy_effective_branching([500, 1, 1, 1], 0.10) == 1


def test_policy_effective_branching_equals_width_when_search_is_flat():
    """All moves equal -> every one is competitive. This is the case
    that exposed the rollout-depth bug, where a signal-free search made
    every child identical."""
    assert metrics.policy_effective_branching([20] * 8, 0.10) == 8


def test_policy_effective_branching_handles_no_visits():
    assert metrics.policy_effective_branching([]) == 0
    assert metrics.policy_effective_branching([0, 0]) == 0


# ---- entropy -------------------------------------------------------------

def test_move_entropy_is_zero_when_all_visits_are_on_one_move():
    assert metrics.move_entropy([10, 0, 0]) == 0.0


def test_move_entropy_of_four_equal_moves_is_two_bits():
    """Uniform over 4 options = log2(4) = 2 bits, by hand."""
    assert metrics.move_entropy([5, 5, 5, 5]) == pytest.approx(2.0)


def test_move_entropy_of_two_equal_moves_is_one_bit():
    assert metrics.move_entropy([1, 1]) == pytest.approx(1.0)


def test_move_entropy_is_zero_for_empty_visits():
    assert metrics.move_entropy([]) == 0.0


# ---- value swing ---------------------------------------------------------

def test_value_swing_is_the_absolute_change():
    assert metrics.value_swing(0.8, 0.3) == pytest.approx(0.5)
    assert metrics.value_swing(0.3, 0.8) == pytest.approx(0.5)


def test_value_swing_is_none_when_not_measured():
    """None distinguishes 'no swing' from 'not measured' — collapsing
    them to 0.0 would silently bias the mean downwards."""
    assert metrics.value_swing(None, 0.5) is None
    assert metrics.value_swing(0.5, None) is None


# ---- position metrics on the real initial board -------------------------

def test_branching_factor_matches_the_engine_at_the_initial_position():
    engine = make_engine('full')
    assert (metrics.legal_branching_factor(engine)
            == len(engine.get_all_legal_turns()))


def test_reachable_squares_never_exceeds_the_board():
    engine = make_engine('full')
    for colour in ('white', 'black'):
        assert 0 < metrics.reachable_squares(engine, colour) <= 64


def test_reachable_squares_does_not_disturb_whose_turn_it_is():
    """The metric switches current_player to measure the other side and
    must restore it, or reading a metric would corrupt the game."""
    engine = make_engine('full')
    before = engine.current_player
    metrics.reachable_squares(engine, 'black')
    assert engine.current_player == before


def test_attack_coverage_is_within_the_board():
    engine = make_engine('full')
    for colour in ('white', 'black'):
        assert 0 <= metrics.attack_map_coverage(engine.board, colour) <= 64


def test_ablating_the_boulder_changes_no_boulder_usage():
    """End-to-end sanity: the no_boulder variant must record zero
    boulder turns. If it did not, the ablation switch is not working and
    every downstream contribution would be meaningless."""
    rng = random.Random(3)
    engine = make_engine('no_boulder', max_turns=80)
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        engine.execute_turn(rng.choice(turns))
    usage = metrics.rule_usage(engine.get_game_record().to_dict())
    assert usage['boulder'] == 0
    assert usage['move'] > 0


def test_full_variant_does_use_the_boulder():
    """Control for the test above: with the rule present the boulder
    fires, so the zero there is meaningful rather than vacuous."""
    rng = random.Random(3)
    engine = make_engine('full', max_turns=200)
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        engine.execute_turn(rng.choice(turns))
    usage = metrics.rule_usage(engine.get_game_record().to_dict())
    assert usage['boulder'] > 0, 'boulder never moved in 200 plies of the full game'
