"""How strong is the search, measured against exact answers (Phase C).

WHY THIS EXISTS. The overview's Phase C says to validate the evaluator
against exact solutions and then "document which games and positions the
evaluator can handle reliably BEFORE using it as the measurement
instrument for larger games". Royal Chess is the larger game and the
evaluator has been pointed at it without that envelope being established.

WHAT IS ALREADY KNOWN, and it is not reassuring:

  * #206 measured the search on Royal Chess as a UNIFORM SAMPLER -- 0%
    self-agreement, identical visit counts across all 65 root children;
  * after the fixes, self-agreement is 2 of 4 at 2000 simulations:
    better than uniform, nowhere near converged;
  * the agent ladder showed an effect CHANGE SIGN between random play and
    a 40-simulation search, which is what an unconverged instrument does.

TWO MEASUREMENTS, because only one of them is available on both games.

1. OPTIMAL-ACTION RATE AND EXACT VALUE LOSS, on a game small enough to
   solve. This is the real thing: the search is scored against ground
   truth. Phase C's wording matters -- "any equally optimal action counts
   as correct" -- so it is scored against the SET of optimal moves, not
   against one arbitrary member of it. Value loss is reported separately
   because picking a losing move when a drawing one existed is a
   different failure from picking a slower win.

2. SELF-AGREEMENT, on a game too large to solve. It is a WEAK proxy and
   is labelled as one: a search can agree with itself and be
   consistently wrong. It can only ever establish an upper bound on
   strength -- a search that disagrees with itself cannot be converged --
   which is exactly the use #206 put it to.

WHAT NEITHER MEASURES: agreement on actions does not validate a gameplay
STATISTIC. The overview is explicit about that too, which is why the
effect estimates are checked against exact references separately.
"""

import collections
import random

Accuracy = collections.namedtuple(
    'Accuracy', 'budget positions optimal mean_loss worst_loss')
Agreement = collections.namedtuple(
    'Agreement', 'budget positions agreed branching chance')


def exact_accuracy(budget, positions=60, seed=0, repeats=1):
    """Optimal-action rate and exact value loss on the solvable game.

    `repeats` searches each position more than once, because a search with
    a random component is a DISTRIBUTION over moves and one sample per
    position measures it badly.
    """
    from lgref.experiments.mcts import MCTSPlayer
    from lgref.experiments.solvable import optimal_moves, reachable_positions

    chosen_well = 0
    total = 0
    losses = []
    for index, game in enumerate(reachable_positions(positions, seed)):
        best, value = optimal_moves(game)
        if not best:
            continue
        legal = game.get_all_legal_turns()
        if len(legal) < 2:
            # A forced move measures nothing about choosing.
            continue
        for repeat in range(repeats):
            player = MCTSPlayer(n_simulations=budget,
                                rng=random.Random(seed * 1000 + index * 10
                                                  + repeat))
            move = player.choose_turn(legal, game)
            total += 1
            if move in best:
                chosen_well += 1
                losses.append(0)
            else:
                losses.append(_value_loss(game, move, value))
    if not total:
        return Accuracy(budget, 0, float('nan'), float('nan'), float('nan'))
    return Accuracy(budget, total, chosen_well / float(total),
                    sum(losses) / float(len(losses)), max(losses))


def _value_loss(game, move, value):
    """Exact value given up by playing `move`, in {0, 1, 2}.

    Values are +1/0/-1 from the mover's perspective, so throwing a win
    away for a draw costs 1 and for a loss costs 2. A rate alone cannot
    tell those apart.
    """
    from lgref.experiments.solvable import TicTacToe, _solve

    child = TicTacToe(tuple(game.cells), game.current_player)
    child.execute_turn(move)
    got = -_solve(tuple(child.cells), child.current_player)
    return value - got


def config_curve(budgets, branchings, configs, positions=8, seed=0,
                 repeats=4, board=None):
    """Optimal-action rate for several AGENT CONFIGURATIONS at once.

    The comparison the strength problem needs: same positions, same
    budget, same exact answers, only the estimator changes. `configs` is
    {label: kwargs for MCTSPlayer}.
    """
    from lgref.experiments.mcts import MCTSPlayer
    from lgref.experiments.mnk import (DISCRIMINATING, decision_density,
                                       optimal_moves,
                                       positions_at_branching)

    m, n, k = board or DISCRIMINATING
    rows = []
    for branching in branchings:
        games = positions_at_branching(branching, m, n, k, positions, seed)
        if not games:
            continue
        density = decision_density(games)
        for budget in budgets:
            for label, kwargs in configs.items():
                good = total = 0
                for index, game in enumerate(games):
                    best, _value = optimal_moves(game)
                    legal = game.get_all_legal_turns()
                    for repeat in range(repeats):
                        player = MCTSPlayer(
                            n_simulations=budget,
                            rng=random.Random(seed * 997 + index * 13
                                              + repeat),
                            **kwargs)
                        if player.choose_turn(legal, game) in best:
                            good += 1
                        total += 1
                rows.append((branching, budget, label, total,
                             good / float(total) if total else
                             float('nan'), density))
    return rows


def branching_curve(budgets, branchings, positions=8, seed=0, repeats=2,
                    board=None):
    """Optimal-action rate as a function of BUDGET and BRANCHING.

    THE QUESTION THIS ANSWERS: is one search enough for narrow, medium and
    wide games, or are three needed? Two points 6x apart cannot say --
    tic-tac-toe at branching 9 and Royal Chess at ~58 -- so this fills in
    between on a game whose branching factor is chosen.

    Scored against the exact optimal SET, with the decision density
    reported beside it: if nearly every move is optimal the accuracy is a
    property of the benchmark, not of the search.
    """
    from lgref.experiments.mcts import MCTSPlayer
    from lgref.experiments.mnk import (DISCRIMINATING, decision_density,
                                       optimal_moves,
                                       positions_at_branching)

    m, n, k = board or DISCRIMINATING
    rows = []
    for branching in branchings:
        games = positions_at_branching(branching, m, n, k, positions, seed)
        if not games:
            continue
        density = decision_density(games)
        for budget in budgets:
            good = total = 0
            for index, game in enumerate(games):
                best, _value = optimal_moves(game)
                legal = game.get_all_legal_turns()
                for repeat in range(repeats):
                    player = MCTSPlayer(
                        n_simulations=budget,
                        rng=random.Random(seed * 997 + index * 13 + repeat))
                    if player.choose_turn(legal, game) in best:
                        good += 1
                    total += 1
            rows.append((branching, budget, total,
                         good / float(total) if total else float('nan'),
                         density))
    return rows


def self_agreement(make_engine, budget, positions=8, seed=0, variant='full',
                   repeats=2, every=12, **agent_kwargs):
    """How often repeated searches of one position choose the same move.

    A WEAK PROXY, and the docstring says so where the number is produced:
    a search can agree with itself and be consistently wrong. Its only
    sound use is as an upper bound -- disagreement proves non-convergence.

    THE CHANCE BASELINE IS RETURNED WITH IT. Two uniform picks from b
    moves agree with probability 1/b, which at branching 58 is 1.7%. A
    bare 16.7% reads like progress; beside a 1.7% baseline and a sample
    of six positions it reads like what it is -- one hit, consistent with
    a search that still disagrees with itself five times in six.

    Positions are taken from a random-play game rather than constructed,
    because this question is about the positions the search actually
    faces.
    """
    from lgref.experiments.mcts import MCTSPlayer, describe
    from lgref.experiments.random_play import build

    engine = make_engine(variant, max_turns=3000)
    white = build('random', random.Random(seed * 2 + 1), 0)
    black = build('random', random.Random(seed * 2 + 2), 0)
    agreed = 0
    sampled = 0
    branching = []
    ply = 0
    while sampled < positions and not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        if ply and ply % every == 0:
            picks = set()
            for repeat in range(repeats):
                player = MCTSPlayer(
                    n_simulations=budget,
                    rng=random.Random(seed * 1000 + ply * 10 + repeat),
                    **agent_kwargs)
                picks.add(describe(player.choose_turn(turns, engine)))
            agreed += (len(picks) == 1)
            branching.append(len(turns))
            sampled += 1
        mover = white if engine.current_player == 'white' else black
        engine.execute_turn(mover.choose_turn(turns, engine))
        ply += 1
    if not sampled:
        return Agreement(budget, 0, float('nan'), float('nan'),
                         float('nan'))
    mean_branching = sum(branching) / float(len(branching))
    # WHAT CHANCE LOOKS LIKE. Two uniform picks from b moves agree with
    # probability 1/b, so at branching 58 chance is 1.7% -- and without
    # that number beside it a reader cannot tell whether 16.7% means the
    # search is converging or merely that it is not quite a coin.
    return Agreement(budget, sampled, agreed / float(sampled),
                     mean_branching,
                     1.0 / mean_branching if mean_branching else
                     float('nan'))


def report(make_engine, budgets=(10, 40, 160), positions=40,
           agreement_positions=6, seed=0, repeats=2,
           branchings=(6, 9, 12)):
    """The Phase C table: exact accuracy where possible, a proxy elsewhere."""
    lines = [
        'SEARCH STRENGTH (Phase C)',
        '',
        'Phase C: validate the evaluator against exact solutions, then',
        'document which games and positions it handles reliably BEFORE',
        'using it as the measurement instrument for larger games.',
        '',
        'AGAINST EXACT SEARCH -- tic-tac-toe, branching <= 9, solved.',
        'Scored against the SET of optimal moves, because any equally',
        'optimal action counts as correct. Value loss is in {0,1,2}: a',
        'win thrown away for a draw costs 1, for a loss 2.',
        '',
        '{:>8} {:>10} {:>14} {:>12} {:>11}'.format(
            'sims', 'decisions', 'optimal-action', 'mean loss', 'worst'),
    ]
    for budget in budgets:
        got = exact_accuracy(budget, positions, seed, repeats)
        lines.append('{:>8} {:>10} {:>13.1%} {:>12.3f} {:>11}'.format(
            got.budget, got.positions, got.optimal, got.mean_loss,
            got.worst_loss))

    lines += [
        '',
        'SELF-AGREEMENT -- Royal Chess, branching ~68, NOT solvable.',
        'A WEAK PROXY: a search can agree with itself and be consistently',
        'wrong, so this bounds strength from above rather than measuring',
        'it. Disagreement proves non-convergence; agreement proves little.',
        '',
        '{:>8} {:>10} {:>14} {:>11} {:>8}'.format(
            'sims', 'positions', 'self-agreement', 'branching', 'chance'),
    ]
    for budget in budgets:
        got = self_agreement(make_engine, budget, agreement_positions, seed,
                             repeats=repeats)
        lines.append('{:>8} {:>10} {:>13.1%} {:>11.1f} {:>7.1%}'.format(
            got.budget, got.positions, got.agreed, got.branching,
            got.chance))
    lines += [
        '',
        'ACCURACY vs BRANCHING -- m,n,k games, exactly solved, branching',
        'chosen rather than inherited. `chance` is what a uniform picker',
        'scores: a benchmark where most moves are optimal cannot tell a',
        'search from a coin, so it is printed beside the accuracy.',
        '',
        '{:>10} {:>7} {:>10} {:>14} {:>9}'.format(
            'branching', 'sims', 'decisions', 'optimal-action', 'chance'),
    ]
    for branching, budget, total, rate, density in branching_curve(
            budgets, branchings, positions=8, seed=seed, repeats=repeats):
        lines.append('{:>10} {:>7} {:>10} {:>13.1%} {:>9.0%}'.format(
            branching, budget, total, rate, density))

    lines += [
        '',
        'WHAT THIS DOES NOT SAY: agreement on ACTIONS does not validate a',
        'gameplay STATISTIC. Effect estimates need checking against exact',
        'references separately, which is why the agent-free structural',
        'route exists (#242).',
    ]
    return '\n'.join(lines)


def main(argv=None):
    import argparse
    import os
    import sys

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'src'))
    from experiments.variants import make_engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budgets', default='10,40,160')
    parser.add_argument('--positions', type=int, default=40)
    parser.add_argument('--agreement-positions', type=int, default=6)
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--branchings', default='6,9,12',
                        help='branching factors for the m,n,k curve')
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args(argv)

    print(report(make_engine,
                 tuple(int(x) for x in args.budgets.split(',')),
                 args.positions, args.agreement_positions, args.seed,
                 args.repeats,
                 tuple(int(x) for x in args.branchings.split(','))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
