"""Fit ONE new weight with every existing weight frozen.

THE DESIGN RULE THIS SERVES, in the reviewer's words:

    "If it turns out not strictly better, you need to avoid risking
    that in the first place and figure out a way to ensure that it is
    strictly better by improving something or a single
    feature/weight/stuff/etc. while leaving everything else the same."

Retraining a vocabulary moves every weight at once, so every position
in the game is in play and the gate can only tell you afterwards
whether you broke something. A change confined to ONE column, where
that column is ABSENT outside a regime, cannot alter any position
outside it -- the differential is identical, so the evaluation is
identical, so the move is identical. There is nothing to risk and
nothing to measure there, and the gate's whole job reduces to the
regime itself.

That is only sound when the column really is absent elsewhere, so the
caller must prove it rather than assert it; `--verify` samples
positions outside the regime and checks the column is zero in every
one.

    python3 tools/fit_one_weight.py EndgamePinned --samples 400

The fit is a closed-form least squares on the RESIDUAL: with the other
weights frozen, w = sum(x * (outcome - base)) / sum(x * x). Outcomes
come from RANDOM playouts, never from the agent's own play, because a
weight fitted on the agent's games would only prove the agent agrees
with itself.
"""
import argparse
import json
import random
import sys
import time

sys.path[:0] = ['.', 'src']


def main():
    from experiments.variants import make_engine
    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import royal_chess, with_threshold
    from lgref.experiments.positions import (apply_layout, sample_layout,
                                             usable)

    parser = argparse.ArgumentParser()
    parser.add_argument('column')
    parser.add_argument('--weights',
                        default='lgref/weights/td_royal_chess.json')
    parser.add_argument('--samples', type=int, default=400)
    parser.add_argument('--seed', type=int, default=23)
    parser.add_argument('--out', default=None)
    parser.add_argument('--verify', type=int, default=200,
                        help='positions OUTSIDE the regime to check the '
                             'column is absent from')
    args = parser.parse_args()

    payload = json.load(open(args.weights))
    weights = payload['weights']
    scales = payload.get('scales', {})
    assert args.column not in weights, (
        '{0} already has a weight; this fits a NEW one'.format(
            args.column))
    reading = with_threshold(royal_chess)

    def base_value(engine, perspective):
        return value(weights, normalise(
            differentials(reading(engine), perspective),
            dict(scales), update=False))

    def column_of(engine, perspective):
        return differentials(reading(engine), perspective).get(
            args.column, 0)

    # ---- the inertness proof ----------------------------------------
    rng = random.Random(args.seed)
    seen_outside = nonzero_outside = 0
    while seen_outside < args.verify:
        engine = make_engine('full', max_turns=400)
        for _ply in range(rng.randint(0, 60)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(rng.choice(turns))
        if engine.is_game_over():
            continue
        if getattr(engine.board, 'is_tiny_endgame', lambda: False)():
            continue            # inside the regime; not what this checks
        seen_outside += 1
        if column_of(engine, engine.current_player):
            nonzero_outside += 1
    print('inertness: {0} of {1} positions OUTSIDE the regime carry '
          '{2}'.format(nonzero_outside, seen_outside, args.column),
          flush=True)
    if nonzero_outside:
        print('REFUSING TO FIT: the column is not confined, so a weight '
              'on it would change positions this fit never looked at.')
        return 1

    # ---- the fit ----------------------------------------------------
    started = time.time()
    numerator = denominator = 0.0
    used = built = 0
    while used < args.samples and built < args.samples * 25:
        built += 1
        engine = make_engine('full', max_turns=200)
        apply_layout(engine, sample_layout(rng, min_extra=1, max_extra=3,
                                           endgame=True))
        if not usable(engine):
            continue
        mover = engine.current_player
        x = column_of(engine, mover)
        if not x:
            continue            # carries no information about this weight
        base = base_value(engine, mover)
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            engine.execute_turn(rng.choice(turns))
        winner = getattr(engine, 'winner', None)
        if winner is None:
            continue
        outcome = 1.0 if mover == winner else 0.0
        numerator += x * (outcome - base)
        denominator += x * x
        used += 1

    if not denominator:
        print('no usable samples')
        return 1
    fitted = numerator / denominator
    print('fitted {0} = {1:+.4f} from {2} positions ({3} built) in '
          '{4:.0f}s'.format(args.column, fitted, used, built,
                            time.time() - started))
    for name in ('Pawn', 'Knight', 'Rook'):
        if name in weights:
            print('   for scale, {0} = {1:+.4f}'.format(name,
                                                        weights[name]))
    if args.out:
        payload = dict(payload)
        payload['weights'] = dict(weights)
        payload['weights'][args.column] = fitted
        payload['fitted_alone'] = {
            'column': args.column, 'samples': used,
            'from': args.weights,
            'note': 'every other weight frozen; column absent outside '
                    'the tiny-endgame regime, verified on {0} '
                    'positions'.format(seen_outside)}
        json.dump(payload, open(args.out, 'w'))
        print('saved', args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
