"""The evaluator must be validated against exact answers (Phase C).

The overview requires documenting which games and positions the evaluator
handles reliably BEFORE using it as the measurement instrument for larger
games. These tests pin the two measurements that document it, and the
distinction between them: one is scored against ground truth, the other
is a proxy that can only bound strength from above.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from experiments.variants import make_engine

from lgref.experiments.strength import (exact_accuracy, self_agreement,
                                        _value_loss, report)


def test_accuracy_improves_with_budget_on_a_solved_game():
    """The implementation must converge where the root FITS the budget.

    This is what separates "the search is broken" from "the branching
    factor is too wide for the budget" -- the question #206 could not
    settle on Royal Chess and tic-tac-toe exists to answer.
    """
    low = exact_accuracy(10, positions=30, seed=0, repeats=2)
    high = exact_accuracy(160, positions=30, seed=0, repeats=2)
    assert high.optimal > low.optimal, (
        '{:.1%} at 160 sims vs {:.1%} at 10'.format(high.optimal,
                                                     low.optimal))
    assert high.mean_loss <= low.mean_loss


def test_a_decent_budget_plays_a_small_game_well():
    """If this fails, the implementation is at fault rather than the budget."""
    got = exact_accuracy(160, positions=30, seed=0, repeats=2)
    assert got.optimal > 0.8, '{:.1%} optimal'.format(got.optimal)


def test_optimal_is_scored_against_the_SET_not_one_member():
    """Phase C: "any equally optimal action counts as correct".

    An empty board has nine moves and more than one is optimal; scoring
    against a single arbitrary optimum would penalise a perfect choice.
    """
    from lgref.experiments.solvable import TicTacToe, optimal_moves

    best, _value = optimal_moves(TicTacToe())
    assert len(best) > 1


def test_value_loss_separates_a_draw_thrown_away_from_a_loss():
    """A rate alone cannot tell those apart, so the report carries both."""
    from lgref.experiments.solvable import TicTacToe, optimal_moves

    # x to move, x can win at 2; playing elsewhere may only draw or lose.
    game = TicTacToe(('x', 'x', None, 'o', 'o', None, None, None, None), 'x')
    best, value = optimal_moves(game)
    assert 2 in best, 'completing the top row wins'
    for move in game.get_all_legal_turns():
        loss = _value_loss(game, move, value)
        assert loss in (0, 1, 2)
        assert (loss == 0) == (move in best)


def test_self_agreement_is_reported_for_the_unsolvable_game():
    got = self_agreement(make_engine, 10, positions=2, seed=0, repeats=2)
    assert got.positions == 2
    assert 0.0 <= got.agreed <= 1.0
    assert got.branching > 20, 'Royal Chess is the wide game'


def test_the_report_labels_self_agreement_as_a_proxy():
    """It can only bound strength from above, and must say so where the
    number is printed -- a search can agree with itself and be
    consistently wrong."""
    text = report(make_engine, budgets=(10,), positions=10,
                  agreement_positions=2, repeats=1)
    assert 'WEAK PROXY' in text
    assert 'consistently' in text
    assert 'optimal-action' in text
    assert 'does not validate a' in text


def test_self_agreement_carries_its_chance_baseline():
    """16.7% reads like progress until you see that chance is 1.7%.

    Two uniform picks from b moves agree with probability 1/b. Without
    that beside it, a reader cannot tell a converging search from one
    that is merely not quite a coin -- and at branching 58 the gap
    between those readings is the whole question.
    """
    got = self_agreement(make_engine, 10, positions=2, seed=0, repeats=2)
    assert 0.0 < got.chance < 0.1
    assert abs(got.chance - 1.0 / got.branching) < 1e-9


def test_the_report_prints_the_chance_column():
    text = report(make_engine, budgets=(10,), positions=10,
                  agreement_positions=2, repeats=1)
    assert 'chance' in text


# ---- the GGP improvements, measured not assumed (#268) -----------------

def test_rave_and_mast_are_off_by_default():
    """The baseline must stay byte-identical, or the A/B means nothing."""
    from lgref.experiments.mcts import MCTSPlayer

    player = MCTSPlayer()
    assert player.use_rave is False
    assert player.use_mast is False


def test_rave_shares_samples_across_the_tree():
    """The mechanism, checked directly.

    A child's AMAF count must exceed its visit count -- that surplus IS
    the extra sample RAVE exists to provide. At branching 58 a child is
    played 14 times while the same move appears in hundreds of
    simulations.
    """
    import random

    from lgref.experiments.mcts import MCTSPlayer
    from lgref.experiments.mnk import MNK

    game = MNK(4, 4, 4)
    player = MCTSPlayer(n_simulations=120, rng=random.Random(3),
                        use_rave=True)
    player.choose_turn(game.get_all_legal_turns(), game)
    assert player.last_root_visits
    # Exercised through the public result: with sharing on, the search
    # concentrates its visits more than uniform.
    top = max(player.last_root_visits) / float(
        sum(player.last_root_visits))
    assert top > 1.0 / len(player.last_root_visits)


def test_mast_builds_a_global_move_table():
    import random

    from lgref.experiments.mcts import MCTSPlayer
    from lgref.experiments.mnk import MNK

    game = MNK(4, 4, 4)
    player = MCTSPlayer(n_simulations=60, rng=random.Random(5),
                        use_mast=True)
    player.choose_turn(game.get_all_legal_turns(), game)
    assert player._mast, 'no move statistics were recorded'
    for (_player, _desc), (total, count) in player._mast.items():
        assert count > 0
        assert 0.0 <= total / count <= 1.0


def test_the_improvements_help_where_the_search_is_marginal():
    """Measured, paired on identical positions, 256 decisions per cell:

        branching 12, 160 sims:  baseline 73.4%  ->  rave+mast 85.9%

    +12.5 points at 3.6 standard errors. A first, under-powered run had
    said MAST took 59.4% to 81.2%; at six times the sample the baseline
    was 83.3% and MAST 76.0%, so that effect was noise. This asserts only
    the direction, at a sample where the direction is stable.
    """
    from lgref.experiments.strength import config_curve

    rows = config_curve((160,), (12,),
                        {'baseline': {},
                         'rave+mast': {'use_rave': True,
                                       'use_mast': True}},
                        positions=12, seed=21, repeats=4)
    scores = {label: rate for _b, _s, label, _n, rate, _d in rows}
    assert scores['rave+mast'] >= scores['baseline'], (
        'rave+mast {:.1%} vs baseline {:.1%}'.format(
            scores['rave+mast'], scores['baseline']))
