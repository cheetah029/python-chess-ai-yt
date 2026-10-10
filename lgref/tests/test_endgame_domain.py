"""Outcome claims only where the search is measured competent.

Outcome metrics are properties of PLAY, so unlike the structural metrics
they cannot be freed from the agent by sampling positions. They can only
be trusted where the agent discriminates, and that was measured:

    regime         branching   chance   160 sims   800 sims
    thin endgame        11.8     8.5%      14.3%      42.9%
    midgame             ~58      1.7%       0.0%       0.0%

So this domain exists, it is narrow, and the module must be honest about
which rules it cannot reach.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import VARIANTS, make_engine

from lgref.experiments.endgame import (COVERED, NOT_COVERED,
                                       VALIDATED_SIMULATIONS,
                                       paired_outcomes, play_endgame,
                                       summarise, thin_position)


def test_every_variant_is_either_covered_or_explained():
    """No variant may be silently absent.

    A rule missing from the output with no reason is indistinguishable
    from a rule measured at zero, which is #259's mistake.
    """
    accounted = set(COVERED) | set(NOT_COVERED)
    missing = sorted(set(VARIANTS) - accounted)
    assert not missing, (
        'these variants are neither covered nor explained: {}'.format(
            missing))


def test_the_uncovered_reasons_are_specific():
    for variant, reason in NOT_COVERED.items():
        assert len(reason) > 20, '{} has a stub reason'.format(variant)


def test_asking_for_an_uncovered_variant_is_refused():
    """Loudly, rather than returning an empty list that reads as zero."""
    with pytest.raises(ValueError) as excinfo:
        paired_outcomes(make_engine, ['no_queen_manipulation'], [0])
    assert 'not measurable' in str(excinfo.value)


def test_manipulation_really_is_impossible_here():
    """The reason given for excluding it, verified against the engine.

    Restriction 3 forbids manipulating the enemy king, the boulder, or an
    enemy base-form queen -- and in K+Q vs K+Q those are the only enemy
    pieces there are.
    """
    import random

    engine = thin_position(make_engine('full', max_turns=200),
                           random.Random(4))
    for _ in range(12):
        if engine.is_game_over():
            break
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        assert not any(getattr(t, 'turn_type', None) == 'manipulation'
                       for t in turns), (
            'manipulation was offered, so the exclusion reason is wrong')
        engine.execute_turn(turns[0])


def test_the_position_is_thin_and_inside_the_envelope():
    """Branching must be near 12, not near 58.

    Thin material does NOT lower branching in general -- the bishop
    teleports to any safe empty square, so K+Q+B averages 78. This
    position excludes bishops for exactly that reason.
    """
    import random
    import statistics as st

    widths = []
    for seed in range(8):
        engine = thin_position(make_engine('full', max_turns=200),
                               random.Random(seed))
        widths.append(len(engine.get_all_legal_turns()))
    assert st.mean(widths) < 20, 'mean branching {:.1f}'.format(
        st.mean(widths))


def test_the_boulder_is_placed_only_where_the_variant_has_one():
    """Otherwise `no_boulder` would be a relabelling, not an ablation."""
    import random

    from piece import Boulder

    for variant, expected in (('full', True), ('no_boulder', False)):
        engine = thin_position(make_engine(variant, max_turns=200),
                               random.Random(2))
        board = engine.board
        present = any(isinstance(board.squares[r][c].piece, Boulder)
                      for r in range(8) for c in range(8))
        assert present is expected, variant


def test_the_pairing_uses_the_same_position_for_every_variant():
    """The only difference between two arms must be the RULE."""
    import random

    first = thin_position(make_engine('full', max_turns=200),
                          random.Random(9))
    second = thin_position(make_engine('no_tiny_endgame', max_turns=200),
                           random.Random(9))

    def layout(engine):
        return sorted(
            (r, c, type(engine.board.squares[r][c].piece).__name__)
            for r in range(8) for c in range(8)
            if engine.board.squares[r][c].piece is not None)

    assert layout(first) == layout(second)


def test_a_game_terminates_and_reports_an_outcome():
    got = play_endgame(make_engine, 'full', seed=1, simulations=40,
                       max_turns=400)
    assert got.plies > 0
    assert got.winner in ('white', 'black', None)
    assert isinstance(got.tiny_activated, bool)


def test_the_validated_budget_is_the_one_that_was_measured():
    """160 simulations gave 14.3% here, barely above 8.5% chance."""
    assert VALIDATED_SIMULATIONS == 800


def test_the_summary_states_where_it_does_not_apply():
    from lgref.experiments.endgame import Outcome

    rows = {'full': [Outcome('full', 0, 'white', 20, True, False, 0,
                             True)]}
    text = summarise(rows)
    assert 'midgame it is 0.0%' in text
    assert 'NOT MEASURABLE IN THIS DOMAIN' in text


def test_a_capped_game_is_recorded_as_censored_not_as_a_draw():
    """#260's defect, which this module reintroduced and now guards.

    `no_tiny_endgame` removes the rule that forces drifting endgames to
    end, so it is the arm whose games run longest and the one most likely
    to hit the cap -- exactly the arm whose length is being measured.
    Recording a capped game as merely non-decisive would bias the
    comparison toward the effect we are looking for.
    """
    got = play_endgame(make_engine, 'no_tiny_endgame', seed=3,
                       simulations=10, max_turns=8)
    assert got.censored is True
    assert got.decisive is False
    assert got.winner is None


def test_an_ordinary_game_is_not_marked_censored():
    got = play_endgame(make_engine, 'full', seed=1, simulations=20,
                       max_turns=400)
    assert got.censored is False


def test_the_summary_flags_censored_pairs_as_a_lower_bound():
    from lgref.experiments.endgame import Outcome

    rows = {
        'full': [Outcome('full', 0, 'white', 20, True, False, 0, True)],
        'no_tiny_endgame': [Outcome('no_tiny_endgame', 0, None, 400,
                                    False, True, 0, False)],
    }
    text = summarise(rows)
    assert 'LOWER bound' in text
    assert 'censored' in text
