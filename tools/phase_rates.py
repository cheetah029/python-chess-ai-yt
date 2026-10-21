"""How good a feature set is AT EACH PHASE of an m,n,k game.

WHY THIS IS NOT A RACE. A race reports an aggregate over positions, and
a change can win overall while being much worse at one kind of
position. `Reach:j` is the worked example: it fixed the opening -- on a
large board the plain line count saturates and ties across every cell
of the middle, so nothing in the evaluation could prefer the centre --
and a reviewer who played with it found the MIDGAME worse, tempo spent
on moves that neither attacked nor defended. Both are true. One number
would have reported one of them.

THREE INSTRUMENTS, because one does not reach every phase:

  opening   the share of moves the evaluation cannot tell apart. Exact
            minimax costs 88 seconds at 14 empty cells against 0.75 at
            12 -- measured on this project's own boards -- so nothing
            grades an opening exactly. What can be measured is whether
            the evaluation is choosing at all: on 19x19 k=5 the plain
            line count gives 121 cells the same value. Lower is
            sharper, and it is a necessary condition, never
            sufficient.

  midgame   the share of forced positions answered: a win taken, or a
            loss blocked. Decided in two plies from the rules alone --
            no search, no evaluation, nothing the agent can flatter.
            It is a FLOOR on competence: an agent can answer every
            threat and still play aimlessly, which is the other thing
            the reviewer reported.

  endgame   the optimal-action rate against exact minimax, over the
            band the solver can actually reach.

    python3 tools/phase_rates.py 9 9 5 --trials 150

The verdict is `validate.strictly_better`: a change clears it only by
losing nothing anywhere.
"""
import argparse
import sys
import time

sys.path[:0] = ['.', 'src']


def main():
    from lgref.experiments.bootstrap import normalise, run, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import mnk as mnk_features
    from lgref.experiments.features import with_threshold
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher
    from lgref.experiments.validate import (forced_move_rate,
                                            initiative_rate,
                                            optimal_rate,
                                            strictly_better, tie_rate)

    parser = argparse.ArgumentParser()
    parser.add_argument('m', type=int)
    parser.add_argument('n', type=int)
    parser.add_argument('k', type=int)
    parser.add_argument('--rounds', type=int, default=6)
    parser.add_argument('--games', type=int, default=60)
    parser.add_argument('--trials', type=int, default=150)
    parser.add_argument('--depth', type=int, default=2)
    parser.add_argument('--seed', type=int, default=11)
    parser.add_argument('--cap', type=int, default=12,
                        help='largest number of empty cells the exact '
                             'solver is asked for; 88s at 14, 0.75s '
                             'at 12')
    args = parser.parse_args()
    cells = args.m * args.n

    def make(_variant='full', max_turns=None):
        return MNK(m=args.m, n=args.n, k=args.k)

    # THE BANDS COME FROM WHAT EACH INSTRUMENT CAN REACH, not from a
    # hand-picked table. A position is solvable at `cells - cap` plies
    # and later; the opening is the first few plies, where a tie is the
    # only thing there is to measure; the midgame is everything
    # between.
    solvable = max(0, cells - args.cap)
    opening = (0, max(1, min(2, cells // 8)))
    midgame = (opening[1] + 1, max(opening[1] + 2, solvable - 1))
    endgame = (solvable, max(solvable, cells - 2))

    print('{0}x{1} k={2}   trained {3} games   depth {4}'.format(
        args.m, args.n, args.k, args.rounds * args.games, args.depth))
    print('plies of random setup:  opening {0}-{1}   midgame {2}-{3}   '
          'endgame {4}-{5} (solver, cap {6} empty)'.format(
              opening[0], opening[1], midgame[0], midgame[1],
              endgame[0], endgame[1], args.cap))
    print()
    print('   {0:<16}{1:>10}{2:>10}{3:>10}{4:>6}'.format(
        'feature set', 'phase', 'score', 'baseline', 'n'))

    measured = {}
    activity = {}
    for label, use_reach in (('without Reach', False),
                             ('with Reach', True)):
        extractor = with_threshold(
            lambda game, flag=use_reach: mnk_features(game,
                                                      use_reach=flag))
        scales = {}
        started = time.time()
        history = run(make, extractor, rounds=args.rounds,
                      games_per_round=args.games, alpha=0.08,
                      epsilon=0.3, seed=args.seed, max_turns=cells,
                      scales=scales)
        weights = history[-1].weights

        def evaluate(game, perspective, weights=weights, scales=scales,
                     extractor=extractor):
            return value(weights, normalise(
                differentials(extractor(game), perspective),
                dict(scales), update=False))

        def pick(game, _rng, evaluate=evaluate):
            searcher = Searcher(evaluate, max_depth=args.depth,
                                budget=5.0, quiescence=0, use_tt=False)
            return searcher.choose_turn(game.get_all_legal_turns(), game)

        def score(game, turn, evaluate=evaluate):
            nxt = game.copy()
            nxt.execute_turn(turn)
            if nxt.is_game_over():
                return (1.0 if nxt.winner == game.current_player
                        else 0.5 if nxt.winner is None else 0.0)
            return 1.0 - evaluate(nxt, nxt.current_player)

        tied, tied_n = tie_rate(make, score, trials=args.trials, seed=5,
                                min_setup=opening[0],
                                max_setup=opening[1])
        forced, forced_n = forced_move_rate(
            make, pick, trials=args.trials, seed=5,
            min_setup=midgame[0], max_setup=midgame[1])
        active, active_n = initiative_rate(
            make, pick, trials=args.trials, seed=5,
            min_setup=midgame[0], max_setup=midgame[1])
        exact, chance, exact_n = optimal_rate(
            make, pick, trials=args.trials, seed=5, cap=args.cap,
            min_setup=endgame[0], max_setup=endgame[1])
        # The opening score is inverted so that MORE IS BETTER in every
        # row: a sharper evaluation ties fewer moves.
        measured[label] = {
            'opening (sharpness)': (1.0 - tied, float('nan'), tied_n),
            'midgame (forced)': (forced, float('nan'), forced_n),
            'endgame (exact)': (exact, chance, exact_n),
        }
        for phase in ('opening (sharpness)', 'midgame (forced)',
                      'endgame (exact)'):
            rate, baseline, asked = measured[label][phase]
            print('   {0:<16}{1:>10}{2:>9.1%}{3:>10}{4:>6}'.format(
                label, phase.split()[0], rate,
                '--' if baseline != baseline else
                '{0:.1%}'.format(baseline), asked), flush=True)
        # REPORTED, NOT GATED. "Wastes tempo" is a claim about the
        # positions where nothing is forced, and a quiet move is not
        # automatically a bad one -- building towards a double threat
        # is quiet until it is not. So this describes the style and
        # does not decide anything.
        activity[label] = (active, active_n)
        print('   {0:<16}{1:>10}{2:>9.1%}{3:>10}{4:>6}   '
              '(descriptive)'.format(label, 'tempo', active, '--',
                                     active_n), flush=True)
        print('   ({0}: trained and measured in {1:.0f}s)'.format(
            label, time.time() - started), flush=True)

    worse = strictly_better(measured['without Reach'],
                            measured['with Reach'])
    print()
    print('tempo (moves that make a threat or remove one): '
          '{0:.1%} without Reach, {1:.1%} with it'.format(
              activity['without Reach'][0], activity['with Reach'][0]))
    if worse:
        print('REACH IS NOT STRICTLY BETTER. Worse or unmeasured at: '
              + '; '.join('{0} ({1})'.format(*item) for item in worse))
    else:
        print('Reach loses nothing on any phase measured here.')


if __name__ == '__main__':
    main()
