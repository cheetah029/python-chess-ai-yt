"""Structural metrics without an agent, paired on identical positions (#242).

Every number this project produced came from played games, so every
number carried the agent that played them. #231 withdrew three sweeps
because the agent's objective was one of the metrics, and the ladder then
showed the boulder's branching effect changing SIGN between random play
and a 40-simulation search. This route removes the agent instead of
strengthening it, for the metrics that are properties of a POSITION.

The tests that matter here are the controls. A method that reports
differences where none exist is worse than no method.
"""

import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from experiments.variants import make_engine

from lgref.experiments.positions import (NO_DIFFERENCE, NOT_EXERCISED,
                                         STRUCTURAL, WRONG_REGIME,
                                         apply_layout, classify,
                                         paired_differences, paired_positions,
                                         sample_layout, usable)


def _t(xs):
    if len(xs) < 2:
        return float('nan')
    sd = st.stdev(xs)
    if not sd:
        return float('inf') if st.mean(xs) else 0.0
    return st.mean(xs) / (sd / math.sqrt(len(xs)))


# ---- the controls ------------------------------------------------------

def test_a_rule_identical_control_shows_exactly_no_difference():
    """The noise floor. If this is not zero, nothing else here means much.

    `control_inert` is rule-identical to `full`, so every paired
    difference must be exactly 0 -- not small, zero. The positions are
    the same objects under two engines; any difference would be the
    instrument, not a rule.
    """
    diffs = paired_differences(make_engine, 'control_inert', 60, seed=1)
    assert diffs, 'no metrics were compared at all'
    for metric, xs in diffs.items():
        assert all(x == 0 for x in xs), (
            '{} differs under a rule-identical control: {}'.format(
                metric, [x for x in xs if x][:5]))
    assert classify('control_inert', diffs)[0] == NO_DIFFERENCE


def test_removing_the_boulder_lowers_branching_without_any_agent():
    """The effect whose SIGN differed between agents, measured agent-free.

    Under random play the difference was -5.22; under a 40-simulation
    search +2.17. With no policy at all it is negative, so the positive
    sign belongs to which positions the search visits rather than to the
    rule.
    """
    diffs = paired_differences(make_engine, 'no_boulder', 200, seed=1)
    branching = diffs['legal_branching']
    assert st.mean(branching) < 0, (
        'removing the boulder should remove the boulder-move options')
    assert abs(_t(branching)) > 5, 't = {:.1f}'.format(_t(branching))
    assert classify('no_boulder', diffs)[0] == STRUCTURAL


def test_pairing_is_exact_so_the_same_layout_is_measured_twice():
    """If the layouts differed, position variance would not cancel."""
    for _index, by_variant in paired_positions(
            make_engine, ('full', 'control_inert'), 12, seed=2):
        assert by_variant['full'] == by_variant['control_inert']


# ---- a zero has three meanings ----------------------------------------

def test_a_dynamic_rule_reports_absence_not_a_measured_zero():
    """Knight invulnerability is granted by a jump DURING play.

    A constructed position never has the flag set, so the ablation has
    nothing to remove. Reporting that as "no effect" would repeat #259 --
    an absence of measurement printed as a measured zero.
    """
    diffs = paired_differences(make_engine, 'no_knight_invulnerability',
                               40, seed=3)
    assert all(x == 0 for xs in diffs.values() for x in xs)
    assert classify('no_knight_invulnerability', diffs)[0] == NOT_EXERCISED


def test_a_precondition_gated_rule_says_which_regime_it_needs():
    diffs = paired_differences(make_engine, 'no_tiny_endgame', 40, seed=3)
    assert classify('no_tiny_endgame', diffs)[0] == WRONG_REGIME


def test_the_tiny_endgame_rule_is_measurable_in_its_own_regime():
    """A rule PLAY NEVER REACHES, measured.

    The gate reports `no_tiny_endgame` as NOT EXERCISED across 200 plies
    of four lines. Its precondition is no pawns, at most six non-king
    pieces and a balanced position; its restriction then bites only once a
    royal distance has occurred three times. Sampled in that regime it
    removes tens of legal turns per position.
    """
    diffs = paired_differences(make_engine, 'no_tiny_endgame', 80, seed=4,
                               min_extra=1, max_extra=2, endgame=True,
                               saturate=True)
    verdict, changed = classify('no_tiny_endgame', diffs)
    assert verdict == STRUCTURAL
    assert 'legal_branching' in changed
    branching = diffs['legal_branching']
    assert st.mean(branching) > 10, (
        'the rule forbids turns, so removing it must add them: {:+.2f}'
        .format(st.mean(branching)))


def test_the_endgame_regime_actually_activates_the_rule():
    """Otherwise the test above would be measuring something else."""
    active = 0
    total = 0
    for _index, by_variant in paired_positions(
            make_engine, ('full',), 40, seed=4, min_extra=1, max_extra=2,
            endgame=True, saturate=True):
        active += bool(by_variant['full'].get('tiny_endgame_active'))
        total += 1
    assert total and active == total, (
        'the rule was active in {} of {} endgame-regime positions'.format(
            active, total))


def test_the_default_regime_does_not_activate_it():
    """Which is why the default regime measures it as absent."""
    active = 0
    for _index, by_variant in paired_positions(make_engine, ('full',), 40,
                                               seed=4):
        active += bool(by_variant['full'].get('tiny_endgame_active'))
    assert active == 0


# ---- sampled positions must be positions -------------------------------

def test_every_sampled_position_is_legal_and_playable():
    for _index, by_variant in paired_positions(make_engine, ('full',), 40,
                                               seed=5):
        row = by_variant['full']
        assert row['legal_branching'] > 0


def test_both_royals_are_present_so_the_position_is_not_decided():
    layout = sample_layout(__import__('random').Random(6))
    royals = [(colour, name) for colour, name, royal, _r, _c in layout.pieces
              if royal]
    assert sorted(royals) == [('black', 'King'), ('black', 'Queen'),
                              ('white', 'King'), ('white', 'Queen')]


def test_pawns_are_never_placed_on_a_promotion_rank():
    """Arriving there forces promotion, so standing there is not legal."""
    import random as _random

    for seed in range(30):
        layout = sample_layout(_random.Random(seed))
        for _colour, name, _royal, row, _col in layout.pieces:
            if name == 'Pawn':
                assert row not in (0, 7)


def test_the_ablated_variant_does_not_get_a_boulder_placed():
    """Placing one would quietly undo the ablation being measured."""
    import random as _random

    from piece import Boulder

    layout = sample_layout(_random.Random(7))
    engine = apply_layout(make_engine('no_boulder', max_turns=1000), layout)
    board = engine.board
    assert board.boulder is None
    assert not any(isinstance(board.squares[r][c].piece, Boulder)
                   for r in range(8) for c in range(8))
    assert usable(engine)


def test_the_full_variant_does_get_one():
    import random as _random

    from piece import Boulder

    layout = sample_layout(_random.Random(7))
    engine = apply_layout(make_engine('full', max_turns=1000), layout)
    board = engine.board
    assert any(isinstance(board.squares[r][c].piece, Boulder)
               for r in range(8) for c in range(8))
