"""Refit ONE m,n,k weight against game outcomes, freezing the rest.

THE DEFECT THIS ANSWERS. The shipped m,n,k evaluation gives `Line:2` a
weight of -0.0347 and `Marks` -0.0918: it believes that making a
two-in-a-row is BAD and that having more stones is BAD. So it scatters.
Measured on 19x19 after the agent opened in the centre and the opponent
replied beside it, 88 of 359 replies tie at the top and the adjacent
blocking move is EXCLUDED from that tie -- it scores lower. The agent's
second move is then the best of a bad set.

WHY THE WEIGHT IS WRONG RATHER THAN THE FEATURE. `Line:1`, `Line:2` and
`Marks` move together -- every stone placed converts some `Line:1` into
`Line:2` and adds a mark -- so TD can fit almost any split between them
and reproduce the same values. A weight from a collinear set is not a
price, which is the oldest lesson in this project's notes, and it is
why the sign can come out backwards without the evaluation being much
worse overall.

SO ONE WEIGHT MOVES AND NOTHING ELSE DOES. Retraining would move all
ten and put the whole game at risk to answer a question about one
column. The fit is closed-form least squares on the residual:
w = sum(x * (outcome - base_without_x)) / sum(x * x), where `base` is
the frozen evaluation with this column's contribution removed, so the
other nine weights keep exactly the values they were trained with.

    python3 tools/refit_mnk_weight.py Line:2 --board 9 9 5

Outcomes come from RANDOM playouts, never from the agent's own games.
"""
import argparse
import json
import random
import sys
import time

sys.path[:0] = ['.', 'src']


def main():
    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import mnk as mnk_features
    from lgref.experiments.features import with_threshold
    from lgref.experiments.mnk import MNK

    parser = argparse.ArgumentParser()
    parser.add_argument('column')
    parser.add_argument('--board', nargs=3, type=int,
                        default=[9, 9, 5], metavar=('M', 'N', 'K'))
    parser.add_argument('--weights', default=None,
                        help='a cached m,n,k weight file; by default '
                             'the one the player would load')
    parser.add_argument('--samples', type=int, default=600)
    parser.add_argument('--seed', type=int, default=23)
    parser.add_argument('--out', default=None)
    args = parser.parse_args()
    m, n, k = args.board

    if args.weights is None:
        # THE BRAIN'S OWN KEY, not a glob. A first version globbed the
        # directory and picked a file a TEST had written -- rounds=1,
        # games=2 -- whose `Line:2` is +0.0531 where the player's is
        # -0.0347. It refitted the wrong agent entirely and reported a
        # change of +0.0003.
        import lgref.play_mnk as play
        brain = play.Brain(rounds=6, games=60, seed=17,
                           use_td_leaf=False, depth=10, train_budget=1.0)
        rows, cols = brain.training_board(m, n, k)
        args.weights = brain._cache_path((rows, cols, k))
        import os
        if not os.path.exists(args.weights):
            print('the player has no cached weights for {0}x{1} k{2} '
                  'yet; start that board once first'.format(
                      rows, cols, k))
            return 1
    payload = json.load(open(args.weights))
    weights = dict(payload['weights'])
    scales = payload.get('scales', {})
    assert args.column in weights, (
        '{0} is not in {1}; this REFITS an existing weight'.format(
            args.column, args.weights))
    print('{0}: {1} weights, refitting {2} (currently {3:+.4f})'.format(
        args.weights, len(weights), args.column,
        weights[args.column]), flush=True)

    reading = with_threshold(mnk_features)
    frozen = dict(weights)
    frozen[args.column] = 0.0          # the column's own contribution out

    rng = random.Random(args.seed)
    numerator = denominator = 0.0
    used = 0
    started = time.time()
    while used < args.samples:
        game = MNK(m=m, n=n, k=k)
        for _ply in range(rng.randint(1, m * n - 2)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        mover = game.current_player
        raw = differentials(reading(game), mover)
        scaled = normalise(raw, dict(scales), update=False)
        x = scaled.get(args.column, 0.0)
        if not x:
            continue
        base = value(frozen, scaled)
        while not game.is_game_over():
            turns = game.get_all_legal_turns()
            if not turns:
                break
            game.execute_turn(rng.choice(turns))
        winner = getattr(game, 'winner', None)
        if winner is None:
            outcome = 0.5
        else:
            outcome = 1.0 if winner == mover else 0.0
        numerator += x * (outcome - base)
        denominator += x * x
        used += 1

    fitted = numerator / denominator if denominator else float('nan')
    print('refitted {0} = {1:+.4f} (was {2:+.4f}) from {3} positions '
          'in {4:.0f}s'.format(args.column, fitted,
                               weights[args.column], used,
                               time.time() - started))
    for name in sorted(weights, key=lambda key: -abs(weights[key]))[:5]:
        print('   frozen: {0:<16}{1:+.4f}'.format(name, weights[name]))
    if args.out:
        weights[args.column] = fitted
        payload = dict(payload)
        payload['weights'] = weights
        payload['refitted_alone'] = {
            'column': args.column, 'samples': used,
            'was': json.load(open(args.weights))['weights'][args.column],
            'note': 'every other weight frozen at its trained value'}
        json.dump(payload, open(args.out, 'w'))
        print('saved', args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
