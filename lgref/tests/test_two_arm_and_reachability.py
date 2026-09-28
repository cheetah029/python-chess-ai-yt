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


# ---- choosing the agent (#231) -------------------------------------------

def test_every_named_agent_can_be_built():
    import random as _random

    from lgref.experiments.random_play import AGENTS, build

    for name in AGENTS:
        player = build(name, _random.Random(1), simulations=5)
        assert hasattr(player, 'choose_turn'), name


def test_an_unknown_agent_names_the_ones_that_exist():
    import random as _random

    import pytest

    from lgref.experiments.random_play import build

    with pytest.raises(ValueError, match='mcts'):
        build('nonsense', _random.Random(1))


def test_the_superseded_agent_is_refused_for_a_new_run():
    """`mobility` stays only so withdrawn runs reproduce.

    Configuring a new run with it would repeat the failure that cost
    this project every statistic it had: its objective is the
    opponent's legal-turn count and `mean_branching` counts legal
    turns.
    """
    from lgref.verify.checks import check_agent_is_not_superseded

    assert not check_agent_is_not_superseded('mobility').passed
    assert check_agent_is_not_superseded('mcts').passed
    assert check_agent_is_not_superseded('random').passed


def test_the_search_budget_is_recorded_on_the_row():
    """Two runs of the same agent at different budgets are not the same
    instrument, and rows that do not say which cannot be pooled.
    """
    from lgref.experiments.sweep import play_one

    row, _samples = play_one('full', 3, 40, agent='mcts', simulations=5)
    assert row['agent'] == 'mcts'
    assert row['agent_simulations'] == 5

    other, _ = play_one('full', 3, 40, agent='random')
    assert other['agent_simulations'] is None, (
        'a budget on an agent that does not search would imply a '
        'setting that did nothing')


# ---- the ladder (#243) ---------------------------------------------------

def _ladder_rows(agent, variant, value, groups=4):
    return [{'agent': agent, 'variant': variant, 'mean_branching': value + i,
             'seed': g * 1000 + i, 'seed_group': g}
            for g in range(groups) for i in range(4)]


def test_the_ladder_keeps_the_arms_in_the_order_given():
    """Weakest first, by measured accuracy against exact play."""
    rows = []
    for agent, value in (('random', 50.0), ('mcts', 55.0)):
        rows += _ladder_rows(agent, 'full', value)
        rows += _ladder_rows(agent, 'no_boulder', value + 6)
    present, _cells = arms.ladder(rows, ['random', 'mcts'])
    assert present == ['random', 'mcts']


def test_an_arm_absent_from_the_data_is_skipped_not_assumed():
    rows = _ladder_rows('mcts', 'full', 50.0) + \
        _ladder_rows('mcts', 'no_boulder', 56.0)
    present, _cells = arms.ladder(rows, ['random', 'mcts', 'mcts2000'])
    assert present == ['mcts']


def test_a_shrinking_step_is_called_settling():
    assert arms.trend([('a', 1.0), ('b', 1.6), ('c', 1.8)]) == 'settling'


def test_a_growing_step_is_called_unstable():
    """Instability across the ladder is the finding, not noise to smooth."""
    assert arms.trend([('a', 1.0), ('b', 1.1), ('c', 2.5)]) == 'unstable'


def test_two_points_are_never_a_trend():
    """Two points always look like a line."""
    assert arms.trend([('a', 1.0), ('b', 2.0)]) == 'too few'
    assert arms.trend([('a', 1.0), ('b', None), ('c', 2.0)]) == 'too few'


# ---- the classes of defect, guarded (#245 audit) -------------------------

def test_every_agent_supplies_what_the_metrics_read():
    """`MCTSPlayer` exposed `last_root_values`; the metrics read
    `last_scores`, through a getattr with a default. Four columns went
    blank, one of them a profile dimension, and nothing raised.
    """
    import os as _os
    import sys as _sys

    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..',
                                      'src'))
    from experiments.variants import make_engine

    from lgref.verify.checks import (
        check_agents_expose_the_metric_contract)

    assert check_agents_expose_the_metric_contract(make_engine).passed


def test_near_optimal_is_counted_in_the_agents_own_units():
    """A tolerance is meaningless beside the wrong scale.

    1.0 is one legal turn to the mobility heuristic and the entire
    range of a win rate to the search. Sharing one constant made the
    same column mean different things in different runs.
    """
    import random as _random

    from lgref.experiments.random_play import build

    tolerances = {name: build(name, _random.Random(1), 5).score_tolerance
                  for name in ('mcts', 'mobility', 'random')}
    assert tolerances['mcts'] < tolerances['mobility'], tolerances
    assert tolerances['random'] == 0.0, (
        'a player that cannot tell its moves apart rates them all equal')


def test_the_subcommands_report_one_partition():
    """`identify` gave 20 rules and `functions` 55, under the SAME ids.

    `R00` named a 223-clause cluster in one output and a 44-clause
    cluster in the other, so any cross-reference between them compared
    different objects.
    """
    import argparse
    import os as _os

    from lgref.identify.graph import ClauseGraph
    from lgref.identify.clauses import load as _load
    from lgref.main import _cluster_for

    repo = _os.path.join(_os.path.dirname(__file__), '..', '..')
    graph = ClauseGraph(_load(_os.path.join(repo, 'docs', 'gdl',
                                            'integrated.gdl')))
    args = argparse.Namespace(resolution=1.0, seed=0)
    first = _cluster_for(graph, args)
    second = _cluster_for(graph, args)
    assert len(first[0]) == len(second[0])
    assert first[2] == second[2]
    assert first[2] != 1.0, (
        'the default resolution must calibrate, which is what the two '
        'subcommands disagreed about')


# ---- the pilot's own turn cap (#231) -------------------------------------

def test_a_pilot_where_every_game_is_capped_is_refused():
    """No draw condition, so a capped game is CENSORED, not drawn.

    This caught its own author. The pilot cap was lowered to 120 to make
    the gate cheap, and at that cap every game was capped — four of
    four, `winner=None` — so `white_win`, `black_win` and `decisive`
    were all False for reasons unrelated to the rules. The
    constant-column check reported `white_win` and could not say why.
    """
    from lgref.verify.checks import check_pilot_games_finish

    capped = [{'turn_cap_reached': True} for _ in range(4)]
    got = check_pilot_games_finish(capped)
    assert not got.passed
    assert 'censored' in got.detail


def test_a_partly_censored_pilot_is_flagged_but_allowed():
    """Some censoring thins the outcome columns without voiding them."""
    from lgref.verify.checks import check_pilot_games_finish

    rows = [{'turn_cap_reached': i < 2} for i in range(4)]
    got = check_pilot_games_finish(rows)
    assert got.passed
    assert 'thinner' in got.detail


def test_the_constant_check_defers_when_every_game_was_censored():
    """Otherwise the real cause is buried under its own consequences.

    With every game capped the outcome columns are constant BY
    CONSTRUCTION. Reporting them as suspect constants points at the
    wrong thing.
    """
    from lgref.verify.checks import check_no_constant_columns

    capped = [{'turn_cap_reached': True, 'white_win': False, 'x': i}
              for i in range(4)]
    assert check_no_constant_columns(capped).passed


def test_a_weaker_pilot_agent_needs_a_LONGER_cap_not_a_shorter_one():
    """The intuition runs backwards and it cost a gate run to learn.

    A cheap search plays on longer than a strong one, so the gate
    cannot borrow the run's cap by scaling it down.
    """
    import inspect

    from lgref.verify import run as run_module

    source = inspect.getsource(run_module.main)
    assert 'default=400' in source, (
        'the pilot cap must leave room for the weaker agent to finish')


# ---- simulation must not write through to the live board (#247) ----------

def test_no_agent_mutates_the_board_while_choosing():
    """The worst defect this project has had.

    A `Turn` references a piece on the board that produced it, and
    `Board.move` writes `cooldown`, `moved` and `last_square` onto that
    piece. Agents simulated by deepcopying the engine and executing the
    CALLER'S turns on the copy, so every simulation wrote through to
    the live game: one simulated boulder move took the real cooldown
    0 -> 2 and the real legal-turn count 73 -> 69.
    """
    import os as _os
    import sys as _sys

    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..',
                                      'src'))
    from experiments.variants import make_engine

    from lgref.verify.checks import (
        check_agents_do_not_mutate_the_live_game)

    got = check_agents_do_not_mutate_the_live_game(make_engine)
    assert got.passed, got.detail


def test_a_turn_carrying_no_piece_is_its_own_description():
    """The solvable game's turns are plain ints.

    Only a turn carrying a piece can write through to the board that
    produced it, so a turn that is already plain data needs no
    translation — and demanding one broke every accuracy test.
    """
    from lgref.experiments.mcts import describe

    assert describe(3) == 3
    assert describe((1, 2)) == (1, 2)


def test_the_search_returns_a_turn_the_caller_offered():
    """The tree holds descriptions; the caller needs an executable turn."""
    import os as _os
    import random as _random
    import sys as _sys

    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..',
                                      'src'))
    from experiments.variants import make_engine

    from lgref.experiments.mcts import MCTSPlayer

    engine = make_engine('full', max_turns=40)
    turns = engine.get_all_legal_turns()
    chosen = MCTSPlayer(n_simulations=15,
                        rng=_random.Random(1)).choose_turn(turns, engine)
    assert chosen in turns


def test_a_pilot_where_every_game_finished_is_not_a_defect():
    """The censoring columns are constant at BOTH extremes.

    If every game was capped, every outcome column is False for reasons
    unrelated to the rules. If every game FINISHED, `turn_cap_reached`
    and `draw_or_censored` are False throughout precisely because
    nothing was cut off — and flagging that as a suspect constant
    reports success as a defect, which is what it did on the run that
    finally had uncensored games.
    """
    from lgref.verify.checks import check_no_constant_columns

    finished = [{'turn_cap_reached': False, 'draw_or_censored': False,
                 'white_win': i % 2 == 0, 'x': i} for i in range(4)]
    assert check_no_constant_columns(finished).passed


def test_a_real_constant_still_fails_when_games_finished():
    """The exemption must not swallow everything else.

    Only the two censoring columns are excused; a genuinely constant
    outcome column is still a defect.
    """
    from lgref.verify.checks import check_no_constant_columns

    rows = [{'turn_cap_reached': False, 'draw_or_censored': False,
             'white_win': False, 'x': i} for i in range(4)]
    got = check_no_constant_columns(rows)
    assert not got.passed
    assert 'white_win' in got.detail
