"""Phase 3 measurement, and the ways a results table can lie.

Issue #210. Each test here guards a way a number could look reasonable
while meaning nothing.
"""

import os

import pytest

from lgref.experiments.metrics import TurnCapTooLow, require_outcome_safe_cap
from lgref.experiments.sweep import (MIN_DECISIVE_RATE, _mean,
                                     decisive_report, play_one,
                                     require_usable)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _row(variant, decisive, turns=50, white=False):
    return {'variant': variant, 'decisive': decisive, 'total_turns': turns,
            'white_win': white, 'black_win': decisive and not white}


# ------------------------------------------------- the decisive-rate gate ----

def test_a_mostly_censored_variant_is_marked_unusable():
    """The gate that stops a turn cap being reported as a win rate.

    This game has no draw condition, so a censored game carries no
    outcome. Earlier runs at cap 100 reported agents "mostly drawing"
    when 0 of 40 games had finished (#204).
    """
    rows = [_row('bad', False) for _ in range(9)] + [_row('bad', True)]
    report = decisive_report(rows)
    assert report[0]['decisive_rate'] == 0.1
    assert report[0]['usable'] is False
    assert require_usable(report) == ['bad']


def test_a_finishing_variant_is_usable():
    rows = [_row('good', True) for _ in range(10)]
    report = decisive_report(rows)
    assert report[0]['usable'] is True
    assert require_usable(report) == []


def test_mean_turns_counts_only_finished_games():
    """A censored game has no length to average -- it was cut off."""
    rows = [_row('v', True, turns=40), _row('v', False, turns=1000)]
    report = decisive_report(rows)
    assert report[0]['mean_turns'] == 40.0


def test_the_threshold_is_not_a_tuning_knob():
    assert MIN_DECISIVE_RATE >= 0.8


# --------------------------------------------------- silent-zero metrics ----

def test_a_missing_metric_reports_none_not_zero():
    """The bug this found in its own first version.

    `play_one` read `branching_factor`; the key is `legal_branching`. So
    `.get(key, 0)` made every game report a mean branching factor of
    0.0 -- a missing measurement wearing the clothes of a real one,
    which is what reaches a results table unnoticed.
    """
    assert _mean([{'other': 3}], 'legal_branching') is None
    assert _mean([], 'legal_branching') is None
    assert _mean([{'legal_branching': 4}, {'legal_branching': 6}],
                 'legal_branching') == 5.0


# ------------------------------------------------------------ turn cap ----

def test_the_pilot_refuses_a_censoring_cap():
    with pytest.raises(TurnCapTooLow):
        require_outcome_safe_cap(100)


# ------------------------------------------------- the harness itself ----

@pytest.mark.slow
def test_the_inert_control_reproduces_the_baseline_exactly():
    """The control that validates the harness rather than the game.

    `control_inert` is configured identically to `full`, so the same
    seed must give the same game. If it did not, variant differences
    elsewhere could not be attributed to the ablation.
    """
    a, _ = play_one('full', 7, 1000, sample_every=0)
    b, _ = play_one('control_inert', 7, 1000, sample_every=0)
    assert (a['winner'], a['total_turns']) == (b['winner'], b['total_turns'])


@pytest.mark.slow
def test_an_ablation_actually_changes_the_game():
    """The complement: the harness must propagate a real difference.

    Without this, every variant agreeing would be indistinguishable
    from the ablations never being applied.
    """
    base, _ = play_one('full', 3, 1000, sample_every=0)
    ablated, _ = play_one('no_boulder', 3, 1000, sample_every=0)
    assert (base['winner'], base['total_turns']) != \
        (ablated['winner'], ablated['total_turns'])
