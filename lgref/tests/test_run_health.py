"""The run must notice its own failures while it is still running.

The pre-flight gate checks what would invalidate a run before it starts.
These are the checks that run DURING it, because a 40-hour run found
void at the end costs 40 hours and one that aborts at game 3 costs
twenty minutes.

Every test here asserts a violation is CAUGHT, not merely that a clean
row passes -- a monitor that never fires is indistinguishable from no
monitor at all.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from experiments.variants import make_engine

from lgref.experiments.health import (RunHealth, canary_fingerprint,
                                      variant_flags)

VARIANTS = ('full', 'no_boulder')


def _row(**over):
    row = {'variant': 'full', 'seed': 0, 'agent': 'mcts',
           'agent_simulations': 800, 'total_turns': 212,
           'turn_cap_reached': False, 'winner': 'white', 'decisive': True}
    row.update(over)
    return row


def _health(**over):
    kwargs = dict(expected_agent='mcts', expected_variants=VARIANTS,
                  expected_simulations=800, canary_every=0, report_every=0)
    kwargs.update(over)
    return RunHealth(make_engine, **kwargs)


# ---- the row is a measurement -------------------------------------------

def test_a_sound_row_raises_nothing():
    assert _health().observe(_row()) == []


def test_one_censored_game_is_reported_but_not_fatal():
    """First-occurrence was wrong, and cost 435 valid games (#260).

    It aborted a 528-game study at game 436 because one random game
    passed the cap. No finite cap can be promised to censor nothing --
    over 400 uncapped games the median is 312 and the max 1775 -- and the
    analysis now excludes censored games from the metrics they do not
    observe, so a small share costs power and nothing else.
    """
    health = _health()
    problems = health.observe(_row(turn_cap_reached=True, winner=None))
    assert problems == [], 'one censored game must not kill the run'
    assert health.censored == 1


def test_censoring_above_the_bound_is_fatal():
    """Loud about each one, fatal when too many are missing."""
    health = _health(max_censored=0.02, censored_floor=5)
    for seed in range(5):
        health.observe(_row(seed=seed))
    problems = health.observe(_row(seed=99, turn_cap_reached=True,
                                   winner=None))
    assert problems and 'above the 2% bound' in problems[0]


def test_a_share_is_not_judged_before_it_means_anything():
    """1 of 1 is 100% and says nothing about the cap."""
    health = _health(max_censored=0.02, censored_floor=20)
    assert health.observe(_row(turn_cap_reached=True, winner=None)) == []


def test_an_agent_object_in_the_agent_column_is_caught():
    """The provenance field held a player OBJECT for 1440 rows (#230)."""
    class Player:
        pass

    problems = _health().observe(_row(agent=Player()))
    assert problems and 'not a name' in problems[0]


def test_the_wrong_agent_is_caught():
    """A run whose rows were played by something else than the config says."""
    problems = _health().observe(_row(agent='mobility'))
    assert problems and 'mobility' in problems[0]


def test_the_wrong_simulation_budget_is_caught():
    problems = _health().observe(_row(agent_simulations=40))
    assert problems and '40 simulations' in problems[0]


def test_a_missing_column_is_caught():
    row = _row()
    del row['total_turns']
    problems = _health().observe(row)
    assert any('total_turns' in p for p in problems)


def test_an_unlisted_variant_is_caught():
    problems = _health().observe(_row(variant='no_queen_manipulation'))
    assert problems and 'does not list' in problems[0]


def test_a_zero_length_game_is_caught():
    problems = _health().observe(_row(total_turns=0))
    assert any('turns' in p for p in problems)


# ---- the engine has not changed under the run ---------------------------

def test_the_canary_reproduces_within_a_process():
    assert canary_fingerprint(make_engine) == canary_fingerprint(make_engine)


def test_the_canary_catches_an_engine_that_changed():
    """Mutate what the canary watches, or the canary proves nothing."""
    health = _health(canary_every=1)
    health.reference = 'deadbeefdeadbeef'
    problems = health.observe(_row())
    assert any('ENGINE CHANGED MID-RUN' in p for p in problems)


def test_the_canary_catches_a_variant_switch_that_leaked():
    """The pool reuses workers, so `no_boulder` and `full` share one.

    The switches are instance attributes with True defaults, which is
    what makes that safe. This is what would notice if one became a
    class attribute a previous job had set.
    """
    health = _health(canary_every=1)
    leaked = dict(health.reference_flags)
    leaked['full'] = (False, False, False, False)
    health.reference_flags = leaked
    problems = health.observe(_row())
    assert any('leaking between jobs' in p for p in problems)


def test_variants_do_not_leak_across_sequential_engines():
    """The real property, checked against the real engine."""
    order = ('no_knight_invulnerability', 'full', 'no_bishop_reactive',
             'full', 'no_repetition_rule', 'full', 'no_boulder', 'full')
    flags = [variant_flags(make_engine, (name,))[name] for name in order]
    full = [f for name, f in zip(order, flags) if name == 'full']
    assert all(f == (True, True, True, True) for f in full), (
        'a variant leaked into a later `full` engine: {}'.format(full))


# ---- running aggregates -------------------------------------------------

def test_a_constant_column_is_reported_but_rare_ones_are_not():
    health = _health()
    for seed in range(4):
        health.observe(_row(seed=seed, total_turns=200 + seed,
                            endgame_blocks=0, mean_branching=60 + seed,
                            stuck=0))
    constant = health.constant_columns()
    assert 'stuck' in constant, 'a column that never varies must be named'
    assert 'endgame_blocks' not in constant, (
        'a column measured to be rare must not be reported as broken')
    assert 'total_turns' not in constant, (
        'a column that did vary must not be named')


def test_the_summary_counts_decisive_games_per_variant():
    health = _health()
    health.observe(_row(variant='full', winner='white'))
    health.observe(_row(variant='full', winner=None, turn_cap_reached=True))
    text = health.summary()
    assert '2 games, 1 censored' in text
    assert 'full' in text


# ---- the runner actually stops ------------------------------------------

def test_the_runner_raises_on_a_violation():
    from lgref.experiments.health import HealthViolation
    from lgref.experiments.pilot import _guard

    health = _health()
    with pytest.raises(HealthViolation) as excinfo:
        _guard(health, _row(agent='mobility'))
    assert 'run stopped after 1 games' in str(excinfo.value)


def test_the_runner_passes_a_sound_row_through():
    from lgref.experiments.pilot import _guard

    _guard(_health(), _row())          # must not raise


def test_success_is_not_reported_as_a_constant_column():
    """The defect this check itself shipped once (#253), here too.

    With nothing censored, `turn_cap_reached` and `draw_or_censored` are
    uniformly False BECAUSE no game was cut off, and `decisive`
    uniformly True because every game reached a result. Naming those
    teaches the reader to skim the one report that must be read.
    """
    health = _health()
    for seed in range(4):
        health.observe(_row(seed=seed, total_turns=200 + seed,
                            draw_or_censored=False, decisive=True))
    constant = health.constant_columns()
    assert 'turn_cap_reached' not in constant
    assert 'draw_or_censored' not in constant
    assert 'decisive' not in constant


def test_a_censored_run_does_report_those_columns():
    """The exemption is conditional: once censoring happens they matter."""
    health = _health()
    health.observe(_row(turn_cap_reached=True, winner=None))
    health.observe(_row(turn_cap_reached=True, winner=None))
    assert 'turn_cap_reached' in health.constant_columns()
