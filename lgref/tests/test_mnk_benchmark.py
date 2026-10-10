"""A solvable benchmark at a CHOSEN branching factor (Phase B/C rung).

Phase C validates the evaluator against exact solutions and documents the
envelope in which it can be trusted. There were two points on that curve,
6x apart: tic-tac-toe at branching <= 9 and Royal Chess at ~58. The shape
in between is what decides whether one search serves narrow, medium and
wide games or whether three are needed, and it cannot be read off the
ends.
"""

from lgref.experiments.mnk import (DISCRIMINATING, MNK, decision_density,
                                   optimal_moves, positions_at_branching,
                                   solve, win_lines)


def test_it_agrees_with_the_existing_tic_tac_toe_solver():
    """3x3 k=3 IS tic-tac-toe, so the two solvers must give one answer.

    Cross-validating a new solver against the established one is cheaper
    than trusting it.
    """
    from lgref.experiments.solvable import TicTacToe
    from lgref.experiments.solvable import optimal_moves as tt_optimal

    mine = optimal_moves(MNK(3, 3, 3))
    theirs = tt_optimal(TicTacToe())
    assert mine == theirs


def test_win_lines_are_only_full_length_lines():
    lines = win_lines(4, 4, 4)
    assert lines
    assert all(len(line) == 4 for line in lines)
    # Four rows, four columns, two long diagonals.
    assert len(lines) == 10


def test_a_won_position_is_scored_from_the_mover_s_view():
    cells = ['x', 'x', 'x', None, None, None, None, None, None]
    assert solve(tuple(cells), 'x', 3, 3, 3) == 1, 'x has three in a row'
    assert solve(tuple(cells), 'o', 3, 3, 3) == -1, 'o is the one losing'


def test_sampled_positions_are_reachable_and_undecided():
    """An arbitrary fill can give four in a row to a player who never had
    four turns, so positions are reached by legal play."""
    m, n, k = DISCRIMINATING
    for game in positions_at_branching(9, m, n, k, count=5, seed=1):
        assert game.branching == 9
        assert game.winner is None
        assert not game.is_game_over()
        xs = sum(1 for c in game.cells if c == 'x')
        os_ = sum(1 for c in game.cells if c == 'o')
        assert abs(xs - os_) <= 1, 'turns must alternate'


def test_positions_where_every_move_is_optimal_are_rejected():
    """They cannot tell a search from a coin.

    On 4x4 k=4 at branching 12 every one of the twelve moves held the
    draw, so an accuracy figure from it measured nothing.
    """
    kept = positions_at_branching(12, 4, 4, 4, count=6, seed=2,
                                  require_decision=True)
    for game in kept:
        best, _value = optimal_moves(game)
        assert len(best) < game.branching


def test_the_default_board_actually_discriminates():
    """If most moves are optimal, accuracy is a property of the benchmark."""
    m, n, k = DISCRIMINATING
    games = positions_at_branching(9, m, n, k, count=8, seed=3)
    assert games
    density = decision_density(games)
    assert density < 0.5, (
        'a benchmark where {:.0%} of moves are optimal is weak'.format(
            density))


def test_a_wider_board_needs_a_bigger_budget():
    """The curve the whole module exists to produce.

    The same search reaches optimal play at a small branching factor and
    falls well short at a larger one, which is why the answer to "is one
    search enough" is about the BUDGET rather than the algorithm.
    """
    from lgref.experiments.strength import branching_curve

    rows = branching_curve((160,), (6, 12), positions=6, seed=0, repeats=2)
    by_branching = {row[0]: row[3] for row in rows}
    assert by_branching[6] > by_branching[12], (
        'branching 6 scored {:.0%}, branching 12 scored {:.0%}'.format(
            by_branching[6], by_branching[12]))


def test_more_simulations_help_at_a_fixed_branching():
    from lgref.experiments.strength import branching_curve

    rows = branching_curve((10, 160), (12,), positions=6, seed=0, repeats=2)
    by_budget = {row[1]: row[3] for row in rows}
    assert by_budget[160] >= by_budget[10]
