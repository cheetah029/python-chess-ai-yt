"""TD-root training for the case study. THE SCRIPT THAT MAKES A BUILD.

IN THE REPOSITORY ON PURPOSE, for the same reason `race_agents.py` is:
this produced the shipped weights while living in a scratch directory,
which meant the thing that makes a candidate was untracked, untested,
and free to drift from the gate that judges it. A build nobody can
reproduce is a build nobody can check.

    python3 tools/train_royal_chess.py <seed> <out.json> [rounds] [per] [--lean]

`--lean` applies the measured ablation in `LEAN` (overridable with
`ABLATE`). Note what it does NOT drop: the aggregate `Pinned`. A piece
standing on an enemy bishop's clear diagonal is not attacked by
anything, and cannot make a spatial move without being captured on the
bishop's next turn -- and regular pieces have no actions, so they must
move. That constraint is structural and persistent, which is exactly
the kind of thing a depth-3 search cannot see for itself.

THAT DISTINCTION IS THE LESSON OF THIS ARC. Features for IMMEDIATE
threats are worth nothing: the shipped build weighs `Attacked` at
-0.0004 and carries no `Hanging` column at all, and it plays well,
because a one-ply threat is resolved by the search. The evaluation's
job is what the search cannot reach.

Nothing trained here ships without the gate -- `tools/race_agents.py`
at the depth the window plays, and `tools/rc_phase_rates.py` per
phase. See `lgref/weights/APPROVED.md`.
"""
import json
import sys
import time

sys.path[:0] = ['.', 'src']


def main():
    from experiments.variants import make_engine
    from lgref.experiments.bootstrap import run
    from lgref.experiments.features import (decorrelate, drop_prefixes,
                                            royal_chess, with_threshold)

    seed, out = int(sys.argv[1]), sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    per = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    #: The ablation: dropping the per-identity relational families and
    #: the flag counts leaves the vocabulary the 0.23-regret baseline
    #: had, plus the zero flags that fix the bishop.
    #: THE ABLATION, every item of it chosen by measurement.
    #:
    #: `Attacked:`, `Hanging:`, `Threatens:` and `Flag:` -- the
    #: per-identity relational families and the per-piece flag counts.
    #: Measured: 42 relational columns outvote material and mean
    #: material regret went 0.23 -> 0.47 with them.
    #:
    #: `RoyalForm:` and `PromotedQueenForm:` -- added after a reviewer
    #: found nine blunders. These are FREE LEVERS: the opponent flips
    #: them with a transformation, which captures nothing, and
    #: `RoyalForm:Rook` at +0.1467 made that phantom threat cost more
    #: than a pawn. They also fail to replicate across seeds
    #: (|mean|/SE 1.2-2.1, two with mixed signs).
    #:
    #: `Pinned:` -- the per-identity breakdown only. The AGGREGATE is
    #: kept, because it is the one thing the evaluation could not see:
    #: a piece on an enemy bishop's clear diagonal is not attacked and
    #: cannot move without being captured.
    import os as _os
    LEAN = tuple(_os.environ.get(
        'ABLATE',
        'Attacked:,Hanging:,Threatens:,Flag:,RoyalForm:,'
        'PromotedQueenForm:,Pinned:').split(','))
    base = with_threshold(royal_chess)
    if '--lean' in sys.argv:
        base = drop_prefixes(base, LEAN)
    ext, dropped = decorrelate(base, make_engine)
    print('decorrelation dropped {0} columns: {1}'.format(
        len(dropped), ', '.join(dropped)), flush=True)
    scales = {}
    support = {}
    t0 = time.time()

    def show(record):
        top = sorted(record.weights.items(), key=lambda kv: -abs(kv[1]))[:6]
        print('[tdroot seed {0} round {1}] {2} games {3:.0f}s  {4}'.format(
            seed, record.round, record.games, time.time() - t0,
            ', '.join('{0}={1:+.3f}'.format(k, v) for k, v in top)),
            flush=True)

    # A FRACTION OF GAMES STARTING FROM A THIN POSITION, because the
    # learner never otherwise sees the regime where some of these
    # features mean anything. Measured: in 11,384 positions from random
    # full games, only 83 had six pieces or fewer -- and the pin
    # correlates +0.22 with winning in thin positions (replicated at
    # three sampling seeds, SE 0.063) while showing nothing at all in
    # the full game. A feature whose regime the training distribution
    # does not contain is priced at zero, and `Pinned` duly trains to
    # +0.0005 at one seed and -0.0026 at another, on 9706 observations.
    #
    # `run` takes `make_engine` as an injection point, so this needs no
    # change to the learner: a fraction of games simply start somewhere
    # else.
    share = float(_os.environ.get('ENDGAMES', '0.0'))
    if share:
        from lgref.experiments.positions import (apply_layout,
                                                 sample_layout, usable)
        import random as _random
        picker = _random.Random(seed * 7919 + 13)
        plain_engine = make_engine

        def make_engine(variant='full', max_turns=400):
            engine = plain_engine(variant, max_turns=max_turns)
            if picker.random() >= share:
                return engine
            for _try in range(20):
                candidate = plain_engine(variant, max_turns=max_turns)
                apply_layout(candidate,
                             sample_layout(picker, min_extra=1,
                                           max_extra=3, endgame=True))
                if usable(candidate):
                    return candidate
            return engine
        print('mixing in {0:.0%} thin-position starts'.format(share),
              flush=True)

    history = run(make_engine, ext, rounds=rounds, games_per_round=per,
                  alpha=0.06, epsilon=0.25, seed=seed, max_turns=250,
                  progress=show, scales=scales,
                  support=support)
    final = history[-1].weights
    eff = {k: final[k] / (scales.get(k, 1.0) or 1.0) for k in final}
    print('\nEFFECTIVE, TD-root seed {0}:'.format(seed))
    for k, v in sorted(eff.items(), key=lambda kv: -abs(kv[1])):
        print('   {0:<28} {1:+.4f}'.format(k, v))
    # BUILT BY `record`, which refuses to write the boolean this file
    # used to carry. `lean: True` is a true statement about the run in a
    # field no loader reads, and it stood in for evidence that the
    # ablation had been replayed -- it had not, once, and the race that
    # followed was reported as a verdict.
    from lgref.experiments.record import record
    payload = {'weights': final, 'scales': scales, 'effective': eff,
               'support': support}
    payload.update(record('with_threshold(royal_chess)',
                          drop_prefixes=(LEAN if '--lean' in sys.argv
                                         else ()),
                          dropped=dropped))
    json.dump(payload, open(out, 'w'))
    print('saved', out)


if __name__ == '__main__':
    main()
