"""The case study's per-phase gate: two extractor settings, compared.

THE COUNTERPART OF `phase_rates.py`, which does this for m,n,k. The
instruments are the same general ones; what differs is WHICH OF THEM
REACH THIS GAME, and that is worth stating rather than working around:

    optimal_rate        no solver gets near a 64-square game
    forced_move_rate    ports, and is useless -- 237 seconds found ONE
                        qualifying position, because this game ends
                        only when both royals are captured, so "the
                        win in front of it" is almost never the
                        question
    initiative_rate     needs a game whose side to move can be set on
                        a copy; this engine's cannot

What is left is real: `tie_rate`, whether the evaluation tells its
moves apart, and `choice_rank`, where it plays against a prior learned
from random play under the rules.

READ `choice_rank` CAREFULLY HERE. The prior comes from RANDOM games,
so it is most informative in the opening -- where which squares are
structurally strong still shows through the noise -- and least
informative in the endgame, where concrete tactics decide and random
statistics say little. A placement score that falls toward 50% late in
the game may be the PRIOR weakening rather than the agent. It is
reported per phase for that reason and must not be summed.

    python3 tools/rc_phase_rates.py --trials 120

Usage is the same shape as the m,n,k tool: the verdict is
`validate.strictly_better`, and a change clears it only by losing
nothing.
"""
import argparse
import json
import sys
import time

sys.path[:0] = ['.', 'src']


def main():
    from experiments.variants import make_engine
    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import (capture_ranker, royal_chess,
                                            with_threshold)
    from lgref.experiments.fastcopy import clone
    from lgref.experiments.search import Searcher
    from lgref.experiments.validate import (choice_rank, outcome_weights,
                                            strictly_better, tie_rate)

    parser = argparse.ArgumentParser()
    parser.add_argument('--weights',
                        default='lgref/weights/td_royal_chess.json')
    parser.add_argument('--trials', type=int, default=120)
    parser.add_argument('--prior-games', type=int, default=200)
    parser.add_argument('--depth', type=int, default=None,
                        help='defaults to the depth the window plays')
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args()

    # THE DEPTH THE WINDOW PLAYS, for the same reason the race takes
    # it: a change raced at one depth and shipped for another is how a
    # worse agent got shipped once already.
    if args.depth is None:
        from game import Game
        args.depth = Game.TD_DEPTH

    payload = json.load(open(args.weights))
    weights = payload['weights']
    scales = payload.get('scales', {})

    def make(_variant='full', max_turns=None):
        return make_engine('full', max_turns=400)

    destination = lambda described: described[3]

    print('{0}: {1} weights, depth {2}, sampling seed {3}'.format(
        args.weights, len(weights), args.depth, args.seed), flush=True)
    started = time.time()
    # ONE PRIOR, BUILT FROM RANDOM PLAY BEFORE EITHER ARM EXISTS, so
    # the two arms are scored against the same ruler and the ruler is
    # not made of the thing being measured.
    prior = outcome_weights(make, trials=args.prior_games, seed=5,
                            key=destination)
    print('prior: {0} destinations from {1} random games in {2:.0f}s'
          .format(len(prior), args.prior_games, time.time() - started),
          flush=True)
    print()
    print('   {0:<22}{1:>10}{2:>12}{3:>7}'.format(
        'setting / phase', 'sharpness', 'placement', 'n'), flush=True)

    BANDS = (('opening', 0, 6), ('midgame', 14, 40),
             ('endgame', 50, 90))
    measured = {}
    for label, see_boulder in (('boulder unseen', False),
                               ('boulder seen', True)):
        def extractor(engine, flag=see_boulder):
            return royal_chess(engine, see_intersection_boulder=flag)

        reading = with_threshold(extractor)

        def evaluate(engine, perspective, reading=reading):
            return value(weights, normalise(
                differentials(reading(engine), perspective),
                dict(scales), update=False))

        def agent(engine, _rng, evaluate=evaluate):
            # FIXED DEPTH, NOT A CLOCK -- otherwise the endgame band is
            # searched deeper than the opening band and the phases are
            # not comparable. Measured on m,n,k: 3, 6 and 10 plies for
            # the same five seconds.
            searcher = Searcher(evaluate, capture_ranker(weights, scales),
                                max_depth=args.depth, quiescence=2)
            return searcher.choose_turn(engine.get_all_legal_turns(),
                                        engine)

        def score(engine, turn, evaluate=evaluate):
            nxt, cloned = clone((engine, [turn]))
            nxt.execute_turn(cloned[0])
            return 1.0 - evaluate(nxt, nxt.current_player)

        measured[label] = {}
        for name, low, high in BANDS:
            tied, tied_n = tie_rate(make, score, trials=args.trials,
                                    seed=args.seed, min_setup=low,
                                    max_setup=high)
            placed, placed_n = choice_rank(
                make, agent, prior, trials=args.trials, seed=args.seed,
                min_setup=low, max_setup=high, key=destination)
            measured[label]['{0} (sharpness)'.format(name)] = (
                1.0 - tied, float('nan'), tied_n)
            measured[label]['{0} (placement)'.format(name)] = (
                placed, float('nan'), placed_n)
            print('   {0:<22}{1:>9.1%}{2:>12.1%}{3:>7}'.format(
                '{0} / {1}'.format(label, name), 1.0 - tied, placed,
                placed_n), flush=True)
        print('   ({0}: {1:.0f}s)'.format(label, time.time() - started),
              flush=True)

    # Four points, the same size of regression the m,n,k gate is told
    # to care about; a run that cannot see one that big is underpowered
    # and does not clear the gate.
    worse = strictly_better(measured['boulder unseen'],
                            measured['boulder seen'], detectable=0.04)
    print()
    if worse:
        print('SEEING THE BOULDER IS NOT STRICTLY BETTER. Worse or '
              'unmeasured at: '
              + '; '.join('{0} ({1})'.format(*item) for item in worse))
    else:
        print('Seeing the boulder loses nothing on any phase measured '
              'here.')


if __name__ == '__main__':
    main()
