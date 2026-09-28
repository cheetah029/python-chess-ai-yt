"""Two arms, and rules the games never reach.

Both exist because a single number hid something. One arm cannot tell an
agent's bias from a rule's effect; one figure cannot tell a dormant rule
from a harmless one.
"""

import collections

from lgref.analysis import arms, reachability
from lgref.analysis.effects import Effect


def _effect(metric, variant, d, verdict='effect'):
    return Effect(metric, variant, 90, 90, 1.0, 1.0 + d, d, d,
                  d - 0.1, d + 0.1, 0.9, verdict)


def _rows(agent, variant, metric, value, groups=4):
    return [{'agent': agent, 'variant': variant, metric: value + i * 0.01,
             'seed': group * 1000 + i, 'seed_group': group}
            for group in range(groups) for i in range(4)]


# ---- two arms ------------------------------------------------------------

def test_a_sign_flip_between_agents_is_reported_as_one():
    """The boulder case. Under one agent removing it raised branching by
    6.6 turns; under a player with no objective it LOWERED it by 3.4.

    Nothing in a single-arm run could say so, and the number looked
    perfectly reasonable.
    """
    rows = (_rows('mcts', 'full', 'mean_branching', 50.0)
            + _rows('mcts', 'no_boulder', 'mean_branching', 57.0)
            + _rows('random', 'full', 'mean_branching', 70.0)
            + _rows('random', 'no_boulder', 'mean_branching', 66.0))
    got = arms.compare(rows)
    flips = [c for c in got if c.verdict == arms.DISAGREES]
    assert flips, [c.verdict for c in got]
    assert flips[0].variant == 'no_boulder'
    assert flips[0].dimension == 'choice_diversity'


def test_agreement_across_arms_is_reported_as_agreement():
    rows = (_rows('mcts', 'full', 'mean_branching', 50.0)
            + _rows('mcts', 'no_boulder', 'mean_branching', 57.0)
            + _rows('random', 'full', 'mean_branching', 50.0)
            + _rows('random', 'no_boulder', 'mean_branching', 57.0))
    got = arms.compare(rows)
    assert any(c.verdict == arms.AGREES for c in got)
    assert not any(c.verdict == arms.DISAGREES for c in got)


def test_an_effect_in_one_arm_only_is_not_counted_as_agreement():
    """Silence in the other arm is not corroboration."""
    rows = (_rows('mcts', 'full', 'mean_branching', 50.0)
            + _rows('mcts', 'no_boulder', 'mean_branching', 57.0)
            + [{'agent': 'random', 'variant': v, 'seed': g * 1000,
                'seed_group': g, 'mean_branching': 50.0}
               for v in ('full', 'no_boulder') for g in range(4)])
    got = arms.compare(rows)
    assert not any(c.verdict == arms.AGREES for c in got)


def test_both_arms_are_required():
    import pytest

    with pytest.raises(SystemExit):
        arms.compare(_rows('mcts', 'full', 'mean_branching', 50.0))


def test_rows_without_an_agent_are_separated_not_assumed():
    """Every row from before the provenance column had no agent.

    Guessing which arm they belong to would silently mix a nullified
    sweep into a good one.
    """
    split = arms.split_by_agent([{'variant': 'full'}, {'agent': 'mcts'}])
    assert 'unrecorded' in split and 'mcts' in split


# ---- reachability --------------------------------------------------------

def test_never_observed_is_a_bound_not_a_zero():
    """"We did not see it" is not "it cannot happen".

    The rule-of-three bound is what makes the difference reportable: no
    tiny-endgame activation in 1440 games puts the rate below 0.0021,
    not at zero.
    """
    bound = reachability.upper_bound_zero(1440)
    assert 0.001 < bound < 0.003, bound
    assert reachability.upper_bound_zero(0) == 1.0


def test_a_dormant_rule_says_how_many_games_it_would_take():
    rows = [{'variant': 'no_tiny_endgame', 'tiny_endgame_activated': False}
            for _ in range(200)]
    got = reachability.assess(rows)
    assert len(got) == 1
    assert got[0].verdict == reachability.DORMANT
    assert got[0].needed > 1000, got[0].needed


def test_a_rule_that_fires_often_enough_is_called_measurable():
    rows = [{'variant': 'no_tiny_endgame',
             'tiny_endgame_activated': i % 2 == 0} for i in range(120)]
    got = reachability.assess(rows)
    assert got[0].verdict == reachability.MEASURABLE
    assert got[0].activated == 60


def test_a_rule_that_fires_rarely_is_called_underpowered_not_measurable():
    """Between dormant and measurable there is a third state.

    Two activations is not zero and is not enough. Calling it measurable
    would put a contribution figure on two events.
    """
    rows = [{'variant': 'no_tiny_endgame',
             'tiny_endgame_activated': i < 2} for i in range(200)]
    got = reachability.assess(rows)
    assert got[0].verdict == reachability.UNDERPOWERED


def test_the_report_names_the_decomposition():
    """A dormant rule and a harmless rule must not read alike."""
    rows = [{'variant': 'no_tiny_endgame', 'tiny_endgame_activated': False}
            for _ in range(200)]
    text = reachability.report(reachability.assess(rows))
    assert 'P(condition arises)' in text
    assert 'NEVER' in text
