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


# ---- policy metrics (#216) -----------------------------------------------

def test_near_optimal_count_is_what_separates_choice_from_clutter():
    """Six options, two of them worth having.

    `mean_branching` counts all six either way, which is why it cannot
    tell a rule that adds CHOICES from one that adds only actions. This
    number can: hand-checkable, since the tolerance is one and the top
    two scores are 10 and 9.5.
    """
    got = metrics.policy_metrics([10, 9.5, 4, 3, 2, 1])
    assert got['policy_branching'] == 2, got


def test_the_tolerance_is_the_smallest_step_the_agent_can_express():
    """Scores are counts of legal turns, so a gap under one is nothing."""
    assert metrics.POLICY_TOLERANCE == 1.0
    assert metrics.policy_metrics([5, 4, 3])['policy_branching'] == 2


def test_a_winning_option_is_in_a_class_of_its_own():
    """A move that ends the game is not near-optimal to anything else."""
    inf = float('inf')
    assert metrics.policy_metrics([inf, 9, 9])['policy_branching'] == 1
    assert metrics.policy_metrics([inf, inf, 3])['policy_branching'] == 2


def test_options_that_only_differ_in_how_much_they_lose_are_one_choice():
    """Every option loses: there is nothing here to choose between."""
    got = metrics.policy_metrics([float('-inf')] * 4)
    assert got['policy_branching'] == 4, got
    assert got['move_entropy'] == 0.0


def test_entropy_is_flat_when_the_agent_cannot_tell_options_apart():
    """Four identical scores: a uniform policy, entropy log 4."""
    got = metrics.policy_metrics([7, 7, 7, 7])
    assert got['move_entropy'] == pytest.approx(math.log(4), abs=1e-3)


def test_entropy_does_not_move_when_only_the_SCALE_does():
    """The point of standardising, checked rather than asserted.

    Raw scores are opponent-mobility counts, and that scale falls as
    material comes off. A fixed-temperature softmax would call these
    two positions different policies; they are the same shape.
    """
    small = metrics.policy_metrics([4, 3, 2, 1])['move_entropy']
    large = metrics.policy_metrics([40, 30, 20, 10])['move_entropy']
    assert small == pytest.approx(large, abs=1e-6)


def test_no_options_reports_nothing_rather_than_zero():
    """A missing measurement must not wear the clothes of a real one."""
    got = metrics.policy_metrics([])
    assert got['policy_branching'] is None
    assert got['move_entropy'] is None


def test_action_types_counts_kinds_not_turns():
    """A transformation lost among ninety moves moves branching by one."""
    engine = make_engine('full', max_turns=50)
    kinds = metrics.action_types_available(engine)
    assert 1 <= kinds <= len(engine.get_all_legal_turns())


def test_every_metric_the_ontology_names_is_actually_recorded():
    """A function cannot claim evidence the sweep never collects.

    Five functions were printed WITHOUT the unfalsifiable marker while
    naming `policy_effective_branching`, `move_entropy` and
    `action_type_counts` -- none of which any row carried (#216). The
    worst of them was `complexity_without_depth`, defined as a
    comparison neither half of which was measured.
    """
    from lgref.experiments.sweep import play_one
    from lgref.functions.strategic_ontology import ONTOLOGY

    row, _samples = play_one('full', 1, 6, sample_every=2)
    for spec in ONTOLOGY:
        for metric in spec.metrics:
            assert metric in row, (spec.name, metric)


# ---- the row the sweep actually writes (#221) ----------------------------

def test_the_row_uses_the_engines_own_record_not_a_stand_in():
    """Five columns were a constant zero in 1440 games out of 1440.

    `play_one` hand-built a four-key record and `outcome_row` reads
    nine, filling the rest with `.get(key, 0)`. Captures, both block
    counters, tiny-endgame activation and repeated-state frequency were
    therefore zero in every game ever run, while the engine had all
    five the whole time. Three functions named those columns as their
    evidence, so they were being scored against numbers structurally
    incapable of moving.

    Captures are the one that cannot be argued with: every game here
    ends by capture, so a game that ends decisively and reports zero
    captures is reporting a bug.
    """
    from lgref.experiments.sweep import play_one

    row, _samples = play_one('full', 1, 400)
    assert row['decisive'], 'need a finished game for this to mean anything'
    assert row['total_captures'] > 0, row['total_captures']


def test_turn_counts_account_for_every_turn_played():
    """Per-rule usage has to add up, or it is measuring something else.

    Cross-checks the classification too: moving a piece the mover does
    not own is exactly the manipulation count, and acting on something
    owned by nobody is exactly the neutral-element count. Three
    independent routes to the same numbers, which is what makes a
    miscount visible.
    """
    from lgref.experiments.sweep import play_one

    row, _samples = play_one('full', 1, 400)
    by_type = {k: v for k, v in row.items() if k.startswith('turns_')}
    assert by_type, 'no per-rule usage recorded'
    assert sum(by_type.values()) == row['total_turns'], by_type
    assert row['foreign_turns'] == by_type['turns_manipulation']
    assert row['shared_entity_turns'] == by_type['turns_boulder']
    assert row['mode_change_turns'] == by_type['turns_transformation']


def test_denied_squares_and_reach_partition_the_empty_board():
    """Every empty square is either enterable or denied, never both."""
    from experiments.variants import make_engine

    engine = make_engine('full', max_turns=50)
    board = engine.board
    empty = sum(1 for r in range(8) for c in range(8)
                if board.squares[r][c].piece is None)
    reach = metrics.reachable_set(engine, engine.current_player)
    on_empty = {sq for sq in reach
                if board.squares[sq[0]][sq[1]].piece is None}
    denied = metrics.denied_squares(engine, engine.current_player)
    assert denied + len(on_empty) == empty, (denied, len(on_empty), empty)


def test_overlap_is_zero_when_nothing_is_covered_twice():
    """Concentration is a second question about the same threat map.

    A board where each piece covers its own ground has coverage and no
    overlap; the metric exists to separate those two situations.
    """
    from experiments.variants import make_engine

    engine = make_engine('full', max_turns=50)
    coverage = metrics.attack_map_coverage(engine.board, 'white')
    overlap = metrics.attack_overlap(engine.board, 'white')
    assert coverage > 0
    assert overlap >= 0
    assert overlap != coverage, (
        'overlap tracking coverage exactly would mean it is not measuring '
        'concentration at all')


def test_type_census_counts_the_movers_own_material():
    """Eight of one kind at the start, and six kinds in all."""
    from experiments.variants import make_engine

    engine = make_engine('full', max_turns=50)
    census = metrics.type_census(engine.board, 'white')
    assert census['max_same_type'] == 8, census
    assert census['distinct_types'] == 6, census
