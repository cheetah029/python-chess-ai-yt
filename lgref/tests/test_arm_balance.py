"""'One arm only' must carry the sample it rests on (#261 follow-up).

The two-arm design exists so that an effect appearing under one agent and
not the other is visible as agent-dependent. That inference only works
when both arms could have seen the effect. Run on 132 random games
against 16 searched ones, `compare` returned 15 cells as "one arm only"
and NONE as agreeing or disagreeing -- including a d of -5.26 resting on
four games, and several where the other arm had ZERO games of that
variant.

"The agent matters here" and "the other arm was too small to see it" are
opposite readings of the same verdict.
"""

from lgref.analysis.arms import (ONE_ARM, arms_are_matched, compare, report)


def _row(agent, variant, seed, **over):
    row = {'agent': agent, 'variant': variant, 'seed': seed,
           'turn_cap_reached': False, 'white_win': 1.0, 'decisive': 1.0,
           'total_turns': 300.0, 'mean_branching': 60.0,
           'mean_attack_coverage': 30.0}
    row.update(over)
    return row


def test_matched_arms_are_reported_as_matched():
    rows = ([_row('mcts', 'full', i) for i in range(10)]
            + [_row('random', 'full', i) for i in range(10)])
    matched, detail = arms_are_matched(rows)
    assert matched
    assert '10 mcts vs 10 random' in detail


def test_badly_unequal_arms_are_flagged():
    rows = ([_row('mcts', 'full', i) for i in range(2)]
            + [_row('random', 'full', i) for i in range(100)])
    matched, detail = arms_are_matched(rows)
    assert not matched
    assert '2 mcts vs 100 random' in detail


def test_a_single_arm_is_not_matched():
    rows = [_row('random', 'full', i) for i in range(10)]
    matched, detail = arms_are_matched(rows)
    assert not matched
    assert 'only one arm' in detail


def test_the_report_warns_when_the_arms_are_unmatched():
    rows = ([_row('mcts', 'full', i) for i in range(2)]
            + [_row('random', 'full', i) for i in range(100)])
    text = report(compare(rows) if _has_both(rows) else [], rows=rows)
    assert 'THE ARMS ARE NOT MATCHED' in text
    assert 'opposite' in text


def _has_both(rows):
    agents = {r['agent'] for r in rows}
    return {'mcts', 'random'} <= agents


def test_one_arm_only_states_both_game_counts():
    """So a verdict resting on zero games of the other arm shows it."""
    rows = ([_row('mcts', 'full', i) for i in range(6)]
            + [_row('mcts', 'no_boulder', i, mean_branching=90.0)
               for i in range(6)]
            + [_row('random', 'full', i) for i in range(6)])
    # `no_boulder` exists only in the mcts arm.
    comparisons = compare(rows)
    one_arm = [c for c in comparisons
               if c.verdict == ONE_ARM and c.variant == 'no_boulder']
    assert one_arm, 'expected a one-arm verdict for the mcts-only variant'
    assert any('n=6 mcts vs 0 random' in c.detail for c in one_arm), (
        'the verdict must show that the other arm had no games: {}'.format(
            [c.detail for c in one_arm]))
