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
    'Agreement', 'budget positions agreed branching')


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


def self_agreement(make_engine, budget, positions=8, seed=0, variant='full',
                   repeats=2, every=12):
    """How often repeated searches of one position choose the same move.

    A WEAK PROXY, and the docstring says so where the number is produced:
    a search can agree with itself and be consistently wrong. Its only
    sound use is as an upper bound -- disagreement proves non-convergence.

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
                    rng=random.Random(seed * 1000 + ply * 10 + repeat))
                picks.add(describe(player.choose_turn(turns, engine)))
            agreed += (len(picks) == 1)
            branching.append(len(turns))
            sampled += 1
        mover = white if engine.current_player == 'white' else black
        engine.execute_turn(mover.choose_turn(turns, engine))
        ply += 1
    if not sampled:
        return Agreement(budget, 0, float('nan'), float('nan'))
    return Agreement(budget, sampled, agreed / float(sampled),
                     sum(branching) / float(len(branching)))


def report(make_engine, budgets=(10, 40, 160), positions=40,
           agreement_positions=6, seed=0, repeats=2):
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
        '{:>8} {:>10} {:>14} {:>11}'.format(
            'sims', 'positions', 'self-agreement', 'branching'),
    ]
    for budget in budgets:
        got = self_agreement(make_engine, budget, agreement_positions, seed,
                             repeats=repeats)
        lines.append('{:>8} {:>10} {:>13.1%} {:>11.1f}'.format(
            got.budget, got.positions, got.agreed, got.branching))
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
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args(argv)

    print(report(make_engine,
                 tuple(int(x) for x in args.budgets.split(',')),
                 args.positions, args.agreement_positions, args.seed,
                 args.repeats))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
