"""Outcome metrics need a cap where games actually finish.

Issue #204. This variant has NO draw condition: one win condition and
four loss conditions, none of them a draw. Every game that terminates is
decisive, so a game stopped by the turn cap is CENSORED, not drawn.

Earlier runs at cap 100 reported that agents "mostly drew". Measured on
40 seeded random-play games, **not one game in forty had finished** --
the reported draws were entirely the cap. A win rate computed over that
is not a noisy estimate of the real one; it is a measurement of the cap,
and it looks perfectly reasonable in a results table.
"""

import os

import pytest

from lgref.core.config import load_config
from lgref.experiments.metrics import (OUTCOME_SAFE_TURN_CAP, TurnCapTooLow,
                                       outcome_row, require_outcome_safe_cap)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def test_the_rulebook_has_no_draw_condition():
    """The premise everything here rests on, checked against the text."""
    with open(os.path.join(REPO, 'RULEBOOK.md')) as handle:
        rulebook = handle.read().lower()
    objective = rulebook[rulebook.index('## **objective**'):][:1200]
    assert 'draw' not in objective, (
        'the objective section now mentions a draw; if a draw condition '
        'has been added, #204 and these tests need revisiting')


def test_a_censored_game_is_not_reported_as_a_draw():
    censored = outcome_row(
        {'winner': None, 'total_turns': 100, 'turn_cap_reached': True},
        max_turns=100)
    assert censored['decisive'] is False
    assert censored['turn_cap_reached'] is True, (
        'censoring must be recorded, not folded into the draw column')

    # A rule-decided ending is distinguishable from a censored one --
    # which is the whole point, since in this variant there are no
    # draws and `draw_or_censored` can only ever mean censored.
    decided = outcome_row(
        {'winner': 'white', 'total_turns': 300}, max_turns=1000)
    assert decided['decisive'] is True
    assert not decided['turn_cap_reached']


def test_outcome_metrics_refuse_a_censoring_cap():
    with pytest.raises(TurnCapTooLow) as excinfo:
        require_outcome_safe_cap(100)
    message = str(excinfo.value)
    assert 'no draw condition' in message
    assert '1000' in message, 'the refusal must name the cap to use'


def test_the_safe_cap_admits_the_configured_default():
    config = load_config(os.path.join(REPO, 'lgref', 'config', 'base.yaml'))
    assert config['max_turns'] >= OUTCOME_SAFE_TURN_CAP
    require_outcome_safe_cap(config['max_turns'])


def test_the_floor_sits_where_termination_actually_is():
    """Pinned to the measurement, not to a round number.

    0% of games terminate at cap 100 and 8% at 200, so a floor anywhere
    below 400 would admit a cap that censors most games.
    """
    assert OUTCOME_SAFE_TURN_CAP >= 400


@pytest.mark.slow
def test_games_really_do_finish_at_the_configured_cap():
    """The measurement itself, at reduced sample size.

    Cheap random play, because the question is about the rules' own
    termination machinery -- repetition, tiny endgame, no-legal-turn --
    and not about skill.
    """
    import random
    import sys

    sys.path.insert(0, os.path.join(REPO, 'src'))
    import pygame
    pygame.init()
    from experiments.variants import make_engine

    finished = 0
    trials = 8
    for seed in range(trials):
        rng = random.Random(2000 + seed)
        engine = make_engine('full', max_turns=1000)
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            engine.execute_turn(turns[rng.randrange(len(turns))])
        finished += engine.winner is not None
    assert finished >= trials - 1, (
        '{}/{} finished at cap 1000; termination has regressed'.format(
            finished, trials))
