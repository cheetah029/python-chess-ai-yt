"""Two evaluations, the same thin positions, both colours each.

THE GATE FOR A CHANGE CONFINED TO A REGIME. When a column is absent
outside its regime the evaluation there is byte-identical, so there is
nothing to measure and nothing to risk; the whole question is what
happens inside. These are those positions, played out by both arms from
the SAME start, with the colours swapped so neither side gets the move
as a gift.

    python3 tools/race_endgames.py --rival candidate.json --games 60
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
    from lgref.experiments.features import (capture_ranker, royal_chess,
                                            with_threshold)
    from lgref.experiments.positions import (apply_layout, sample_layout,
                                             usable)
    from lgref.experiments.search import Searcher

    parser = argparse.ArgumentParser()
    parser.add_argument('--base',
                        default='lgref/weights/td_royal_chess.json')
    parser.add_argument('--rival', required=True)
    parser.add_argument('--games', type=int, default=60)
    parser.add_argument('--seed', type=int, default=11)
    parser.add_argument('--depth', type=int, default=None)
    args = parser.parse_args()
    if args.depth is None:
        from game import Game
        args.depth = Game.TD_DEPTH

    reading = with_threshold(royal_chess)

    def build(path):
        payload = json.load(open(path))
        weights = payload['weights']
        scales = payload.get('scales', {})

        def evaluate(engine, perspective):
            return value(weights, normalise(
                differentials(reading(engine), perspective),
                dict(scales), update=False))

        def make():
            return Searcher(evaluate, capture_ranker(weights, scales),
                            max_depth=args.depth, budget=10.0,
                            quiescence=2)
        return make, weights

    base, base_weights = build(args.base)
    rival, rival_weights = build(args.rival)
    extra = set(rival_weights) - set(base_weights)
    changed = [k for k in base_weights
               if rival_weights.get(k) != base_weights[k]]
    print('base {0} weights; rival adds {1} and changes {2}'.format(
        len(base_weights), sorted(extra) or 'nothing',
        sorted(changed) or 'nothing'), flush=True)
    print('depth {0}, {1} paired games'.format(args.depth, args.games),
          flush=True)

    rng = random.Random(args.seed)
    tally = {'base': 0, 'rival': 0, 'draw': 0}
    started = time.time()
    played = 0
    attempts = 0
    while played < args.games and attempts < args.games * 30:
        attempts += 1
        layout = sample_layout(rng, min_extra=1, max_extra=3,
                               endgame=True)
        probe = make_engine('full', max_turns=200)
        apply_layout(probe, layout)
        if not usable(probe):
            continue
        # BOTH COLOURS, same position, so neither arm is handed the
        # move as a gift.
        for swap in (False, True):
            engine = make_engine('full', max_turns=200)
            apply_layout(engine, layout)
            sides = ({'white': ('base', base), 'black': ('rival', rival)}
                     if not swap else
                     {'white': ('rival', rival), 'black': ('base', base)})
            agents = dict((colour, (name, factory()))
                          for colour, (name, factory) in sides.items())
            while not engine.is_game_over():
                turns = engine.get_all_legal_turns()
                if not turns:
                    break
                _name, searcher = agents[engine.current_player]
                engine.execute_turn(searcher.choose_turn(turns, engine))
            winner = getattr(engine, 'winner', None)
            if winner is None:
                tally['draw'] += 1
            else:
                tally[sides[winner][0]] += 1
            played += 1
        print('  {0} games: base {1} - {2} rival, {3} drawn  {4:.0f}s'
              .format(played, tally['base'], tally['rival'],
                      tally['draw'], time.time() - started), flush=True)

    total = tally['base'] + tally['rival']
    print()
    print('FINAL  base {0} - {1} rival, {2} drawn'.format(
        tally['base'], tally['rival'], tally['draw']))
    if total:
        share = tally['rival'] / float(total)
        floor = 2.0 * (0.25 / total) ** 0.5
        print('rival wins {0:.1%} of decisive games; two standard errors '
              'is {1:.1%}'.format(share, floor))
        print('RESOLVED' if abs(share - 0.5) > floor
              else 'INSIDE THE NOISE FLOOR -- not a result')


if __name__ == '__main__':
    main()
