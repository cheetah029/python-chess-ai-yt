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
    parser.add_argument('--seed', type=int, default=11,
                        help='the TRAINING seed (use --train-seeds for '
                             'more than one)')
    # SEVERAL TRAINING SEEDS, POOLED. Training once per arm measures
    # the training RUN, not the feature set, and on this game the
    # difference between runs swamps the difference between feature
    # sets: at seed 11, Reach was 4.6 points of tempo WORSE and
    # identical elsewhere; at seed 23 it was 13.1 points of opening
    # sharpness and 4.5 points of forced-move answering BETTER, with
    # tempo inside the floor. Same comparison, opposite verdict. A gate
    # that trains once would have reported whichever run it happened to
    # draw.
    parser.add_argument('--train-seeds', default=None,
                        help='comma-separated training seeds, pooled; '
                             'one seed measures the training run '
                             'rather than the feature set')
    # THE SAMPLING SEED, SEPARATELY. It was fixed at 5, so running the
    # same comparison with more trials drew a LARGER SAMPLE OF THE SAME
    # SEQUENCE -- the small run nested inside the big one. Three such
    # runs agreeing is one run agreeing with itself, not a replication.
    parser.add_argument('--measure-seed', type=int, default=5,
                        help='the seed the POSITIONS are sampled with; '
                             'change it for an independent replication')
    parser.add_argument('--cap', type=int, default=12,
                        help='largest number of empty cells the exact '
                             'solver is asked for; 88s at 14, 0.75s '
                             'at 12')
    args = parser.parse_args()
    cells = args.m * args.n
    train_seeds = ([int(one) for one in args.train_seeds.split(',')]
                   if args.train_seeds else [args.seed])

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

    print('{0}x{1} k={2}   trained {3} games   depth {4}   '
          'train seeds {5}   sampling seed {6}'.format(
              args.m, args.n, args.k, args.rounds * args.games,
              args.depth, ','.join(str(one) for one in train_seeds),
              args.measure_seed))
    print('plies of random setup:  opening {0}-{1}   midgame {2}-{3}   '
          'endgame {4}-{5} (solver, cap {6} empty)'.format(
              opening[0], opening[1], midgame[0], midgame[1],
              endgame[0], endgame[1], args.cap))
    print()
    print('   {0:<16}{1:>8}{2:>9}{3:>9}{4:>9}{5:>9}{6:>7}'.format(
        'feature set', 'run', 'opening', 'forced', 'tempo', 'endgame',
        'time'))

    PHASES = ('opening (sharpness)', 'midgame (forced)',
              'midgame (tempo)', 'endgame (exact)')

    measured = {}
    activity = {}
    for label, use_reach in (('without Reach', False),
                             ('with Reach', True)):
        # POOLED OVER TRAINING SEEDS. Each seed contributes its own
        # COUNT, and a phase's rate is the weighted mean -- summing
        # counts rather than averaging rates, so a seed that happened
        # to sample few qualifying positions does not carry the same
        # weight as one that sampled many.
        hits = dict((phase, 0.0) for phase in PHASES)
        asked = dict((phase, 0) for phase in PHASES)
        chances = 0.0
        for train_seed in train_seeds:
            extractor = with_threshold(
                lambda game, flag=use_reach: mnk_features(
                    game, use_reach=flag))
            scales = {}
            started = time.time()
            history = run(make, extractor, rounds=args.rounds,
                          games_per_round=args.games, alpha=0.08,
                          epsilon=0.3, seed=train_seed,
                          max_turns=cells, scales=scales)
            weights = history[-1].weights

            def evaluate(game, perspective, weights=weights,
                         scales=scales, extractor=extractor):
                return value(weights, normalise(
                    differentials(extractor(game), perspective),
                    dict(scales), update=False))

            def pick(game, _rng, evaluate=evaluate):
                searcher = Searcher(evaluate, max_depth=args.depth,
                                    budget=5.0, quiescence=0,
                                    use_tt=False)
                return searcher.choose_turn(
                    game.get_all_legal_turns(), game)

            def score(game, turn, evaluate=evaluate):
                nxt = game.copy()
                nxt.execute_turn(turn)
                if nxt.is_game_over():
                    return (1.0 if nxt.winner == game.current_player
                            else 0.5 if nxt.winner is None else 0.0)
                return 1.0 - evaluate(nxt, nxt.current_player)

            tied, tied_n = tie_rate(
                make, score, trials=args.trials,
                seed=args.measure_seed, min_setup=opening[0],
                max_setup=opening[1])
            forced, forced_n = forced_move_rate(
                make, pick, trials=args.trials,
                seed=args.measure_seed, min_setup=midgame[0],
                max_setup=midgame[1])
            active, active_n = initiative_rate(
                make, pick, trials=args.trials,
                seed=args.measure_seed, min_setup=midgame[0],
                max_setup=midgame[1])
            exact, chance, exact_n = optimal_rate(
                make, pick, trials=args.trials,
                seed=args.measure_seed, cap=args.cap,
                min_setup=endgame[0], max_setup=endgame[1])

            # The opening score is inverted so MORE IS BETTER in every
            # row: a sharper evaluation ties fewer moves.
            for phase, rate, count in (
                    ('opening (sharpness)', 1.0 - tied, tied_n),
                    ('midgame (forced)', forced, forced_n),
                    ('midgame (tempo)', active, active_n),
                    ('endgame (exact)', exact, exact_n)):
                if count and rate == rate:
                    hits[phase] += rate * count
                    asked[phase] += count
            if exact_n and chance == chance:
                chances += chance * exact_n
            print('   {0:<16}{1:>8}{2:>9.1%}{3:>9.1%}{4:>9.1%}'
                  '{5:>9.1%}{6:>6.0f}s'.format(
                      label, 'seed ' + str(train_seed), 1.0 - tied,
                      forced, active, exact if exact == exact else 0.0,
                      time.time() - started), flush=True)

        measured[label] = {}
        for phase in PHASES:
            rate = (hits[phase] / asked[phase] if asked[phase]
                    else float('nan'))
            baseline = (chances / asked['endgame (exact)']
                        if phase == 'endgame (exact)'
                        and asked['endgame (exact)'] else float('nan'))
            measured[label][phase] = (rate, baseline, asked[phase])
        activity[label] = measured[label]['midgame (tempo)'][:1] + (
            measured[label]['midgame (tempo)'][2],)
        pooled = measured[label]
        print('   {0:<16}{1:>8}{2:>9.1%}{3:>9.1%}{4:>9.1%}{5:>9.1%}'
              .format(label, 'POOLED',
                      pooled['opening (sharpness)'][0],
                      pooled['midgame (forced)'][0],
                      pooled['midgame (tempo)'][0],
                      pooled['endgame (exact)'][0]
                      if pooled['endgame (exact)'][0] ==
                      pooled['endgame (exact)'][0] else 0.0),
              flush=True)
        print('   {0:<16}{1:>8}{2:>9}{3:>9}{4:>9}{5:>9}'.format(
            '', 'n', asked['opening (sharpness)'],
            asked['midgame (forced)'], asked['midgame (tempo)'],
            asked['endgame (exact)']), flush=True)

    # `detectable` IS THE SIZE OF REGRESSION THAT MATTERS, and the
    # default of ten points is far too lax here. The regression this
    # gate exists to catch -- Reach's -- is 4.6 points of tempo, and a
    # single 1500-trial run has a noise floor of 4.4, so the gate would
    # have PASSED IT and only pooling two sampling seeds resolved it.
    #
    # Four points, therefore: a run that cannot tell a four-point drop
    # from noise is reported UNDERPOWERED and does not clear the gate.
    # "Run it again with another seed" is the right answer there; "ship
    # it" is not.
    worse = strictly_better(measured['without Reach'],
                            measured['with Reach'],
                            detectable=0.04)
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
