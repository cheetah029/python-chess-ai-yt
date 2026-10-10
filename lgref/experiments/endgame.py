"""Outcome claims from the one regime where the search demonstrably works.

WHY A REDUCED DOMAIN. Outcome metrics -- win rate, decisiveness, game
length -- are properties of PLAY, so unlike the structural metrics they
cannot be freed from the agent by sampling positions (#242). They can
only be trusted where the agent is competent, and on the full game it is
not: self-agreement in the midgame is 0.0% at every budget tried, from 10
to 2000 simulations, against a chance baseline of 1/58 = 1.7%. Two
searches of the same position never choose the same move.

WHERE IT DOES WORK, measured rather than assumed:

    regime         branching   chance   160 sims   800 sims
    thin endgame        11.8     8.5%      14.3%      42.9%
    midgame             ~58      1.7%       0.0%       0.0%

At 800 simulations in the thin endgame the search agrees with itself five
to six times above chance. That is the regime this module measures in,
and it is the only one.

THE DOMAIN IS NARROWER THAN "ENDGAME" SUGGESTS, and not for the reason
one would guess. Thin material does NOT lower the branching factor -- it
raises it. The bishop teleports to any safe empty square, so fewer pieces
means more empty squares and more moves:

    4 royals only      9        K+Q+N     28.2
    K+Q vs K+Q      13.4        K+Q+R     43.3
    K+Q+P           16.4        K+Q+B     78.0

So the searchable region is K+Q vs K+Q and nothing richer.

WHICH RULES THAT CAN AND CANNOT COVER, which is the honest cost of the
route. In K+Q vs K+Q the only enemy pieces are a king and a base-form
queen, and manipulation's Restriction 3 forbids both as targets, so
manipulation is never legal. No knights means invulnerability is never
granted; no bishops means reactive capture never arms.

    COVERED       boulder, repetition, tiny endgame
    NOT COVERED   queen manipulation, knight invulnerability,
                  knight redesign, bishop reactive

The two rules the gate reports as NOT EXERCISED across 200 plies of play
-- repetition and tiny endgame -- are exactly the two this domain
reaches. That is the route's main value, not a consolation.

PAIRED ON IDENTICAL START POSITIONS. Every variant plays the same
sampled position with the same agent seeds, so the only difference
between two arms is the RULE. Position variance cancels within the pair
rather than being averaged away with more games, which is #241 and is
what makes a handful of expensive games informative.
"""

import collections
import random

#: Variants this domain can and cannot exercise, with the reason. An
#: effect reported for an uncovered variant would be an absence of
#: measurement dressed as a zero, which is #259's mistake.
COVERED = ('full', 'control_inert', 'no_boulder', 'no_repetition_rule',
           'no_tiny_endgame')

NOT_COVERED = {
    'no_queen_manipulation':
        'manipulation is never legal here: the only enemy pieces are a '
        'king and a base-form queen, and Restriction 3 forbids both as '
        'targets',
    'no_knight_invulnerability':
        'no knights, so the leap grant never fires',
    'no_knight_redesign':
        'no knights, so neither movement nor jump-capture is exercised',
    'no_bishop_reactive':
        'no bishops, so the reactive capture never arms',
    'baseline':
        'strips several rules at once, so an effect here could not be '
        'attributed to any one of them',
    'control_double_move':
        'a turn-order control; it changes who moves, not the legal set, '
        'and the paired design holds the position fixed',
}

#: The budget at which the search was measured competent in this regime:
#: 42.9% self-agreement against 8.5% chance. Below it the instrument is
#: not validated here either -- 160 simulations gave 14.3%, which is
#: barely above chance.
VALIDATED_SIMULATIONS = 800

#: A CENSORED GAME IS NOT A DRAW, and this domain is where that bites
#: hardest. `no_tiny_endgame` removes the rule that forces drifting
#: endgames to end, so it is the arm whose games run longest and the one
#: most likely to hit the cap -- exactly the arm whose length we are
#: measuring. Recording a capped game as `decisive=False` would conflate
#: "ran out of patience" with "no winner" and bias the comparison toward
#: the effect we are looking for. That is #260's defect, fixed once in
#: the sweep pipeline and reintroduced here.
Outcome = collections.namedtuple(
    'Outcome', 'variant seed winner plies decisive censored '
               'repetition_blocks tiny_activated')


def thin_position(engine, rng):
    """Put a K+Q vs K+Q position on `engine`'s board.

    The boulder is left in place only if the variant has one, so
    `no_boulder` is a real ablation here rather than a relabelling --
    the same discipline `positions.apply_layout` follows.
    """
    from piece import Boulder, King, Queen

    board = engine.board
    had_boulder = board.boulder is not None or any(
        isinstance(board.squares[r][c].piece, Boulder)
        for r in range(8) for c in range(8))
    for row in range(8):
        for col in range(8):
            board.squares[row][col].piece = None
    board.boulder = None

    squares = [(r, c) for r in range(8) for c in range(8)]
    rng.shuffle(squares)
    used = 0
    for colour in ('white', 'black'):
        for cls in (King, Queen):
            row, col = squares[used]
            used += 1
            piece = cls(colour)
            piece.is_royal = True
            board.squares[row][col].piece = piece
    if had_boulder:
        row, col = squares[used]
        boulder = Boulder()
        boulder.on_intersection = False
        boulder.first_move = False
        board.squares[row][col].piece = boulder

    board.turn_number = 4
    engine.turn_number = 4
    engine.current_player = 'white'
    return engine


def play_endgame(make_engine, variant, seed, simulations=None,
                 max_turns=3000, agent_kwargs=None):
    """One paired endgame game. Returns an `Outcome`.

    `seed` fixes BOTH the position and the agents, so calling this with
    the same seed under two variants plays the same position with the
    same search randomness -- common random numbers.
    """
    from lgref.experiments.mcts import MCTSPlayer

    simulations = (VALIDATED_SIMULATIONS if simulations is None
                   else simulations)
    kwargs = dict(agent_kwargs or {})
    engine = thin_position(make_engine(variant, max_turns=max_turns),
                           random.Random(seed))
    white = MCTSPlayer(n_simulations=simulations,
                       rng=random.Random(seed * 2 + 1), **kwargs)
    black = MCTSPlayer(n_simulations=simulations,
                       rng=random.Random(seed * 2 + 2), **kwargs)
    plies = 0
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        mover = white if engine.current_player == 'white' else black
        engine.execute_turn(mover.choose_turn(turns, engine))
        plies += 1
    record = engine.get_game_record().to_dict()
    censored = engine.winner is None and engine.turn_number >= max_turns
    return Outcome(
        variant=variant, seed=seed, winner=engine.winner, plies=plies,
        decisive=engine.winner is not None, censored=censored,
        repetition_blocks=record.get('repetition_blocks', 0),
        tiny_activated=bool(record.get('tiny_endgame_activated')))


def paired_outcomes(make_engine, variants, seeds, simulations=None,
                    agent_kwargs=None, progress=None):
    """{variant: [Outcome]} over the same seeds for every variant."""
    out = {}
    for variant in variants:
        if variant in NOT_COVERED:
            raise ValueError(
                '{} is not measurable in this domain: {}'.format(
                    variant, NOT_COVERED[variant]))
        rows = []
        for seed in seeds:
            rows.append(play_endgame(make_engine, variant, seed,
                                     simulations, agent_kwargs=agent_kwargs))
            if progress is not None:
                progress(variant, rows[-1])
        out[variant] = rows
    return out


def summarise(by_variant, baseline='full'):
    """Paired differences against the baseline, as text."""
    import statistics as st

    lines = [
        'ENDGAME OUTCOME EFFECTS (reduced domain)',
        '',
        'The only regime where the search is measured competent: thin',
        'endgame, branching ~12, {} simulations, self-agreement 42.9%'
        .format(VALIDATED_SIMULATIONS),
        'against 8.5% chance. In the midgame it is 0.0% at every budget,',
        'so no outcome claim is made there.',
        '',
        'Paired on identical start positions with identical agent seeds,',
        'so the only difference between two arms is the RULE.',
        '',
        '{:<24} {:>6} {:>9} {:>9} {:>11} {:>10} {:>8}'.format(
            'variant', 'games', 'decisive', 'censored', 'mean plies',
            'rep blocks', 'tiny on'),
    ]
    base = by_variant.get(baseline, [])
    for variant in sorted(by_variant):
        rows = by_variant[variant]
        if not rows:
            continue
        decisive = sum(1 for r in rows if r.decisive) / float(len(rows))
        censored = sum(1 for r in rows if r.censored)
        plies = st.mean([r.plies for r in rows])
        blocks = st.mean([r.repetition_blocks for r in rows])
        tiny = sum(1 for r in rows if r.tiny_activated) / float(len(rows))
        lines.append(
            '{:<24} {:>6} {:>8.0%} {:>9} {:>11.1f} {:>10.2f} {:>7.0%}'
            .format(variant, len(rows), decisive, censored, plies, blocks,
                    tiny))

    if base:
        lines += ['', 'PAIRED DIFFERENCES vs {} (same positions):'
                  .format(baseline)]
        by_seed = {r.seed: r for r in base}
        for variant in sorted(by_variant):
            if variant == baseline:
                continue
            pairs = [(by_seed[r.seed], r) for r in by_variant[variant]
                     if r.seed in by_seed]
            if not pairs:
                continue
            # A censored game's length is a LOWER bound, so a pair
            # containing one understates the difference. Counted and
            # reported rather than silently averaged in.
            capped = sum(1 for a, b in pairs if a.censored or b.censored)
            d_plies = st.mean([b.plies - a.plies for a, b in pairs])
            d_dec = st.mean([float(b.decisive) - float(a.decisive)
                             for a, b in pairs])
            note = ('  ({} pair(s) censored, so the plies difference is '
                    'a LOWER bound)'.format(capped) if capped else '')
            lines.append(
                '   {:<24} plies {:+8.1f}   decisive {:+6.0%}   n={}{}'
                .format(variant, d_plies, d_dec, len(pairs), note))

    uncovered = sorted(NOT_COVERED)
    lines += ['', 'NOT MEASURABLE IN THIS DOMAIN, and why:']
    for variant in uncovered:
        lines.append('   {:<26} {}'.format(variant, NOT_COVERED[variant]))
    return '\n'.join(lines)


def _job(args):
    import os
    import sys
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'src'))
    from experiments.variants import make_engine

    variant, seed, simulations, kwargs, max_turns = args
    return play_endgame(make_engine, variant, seed, simulations,
                        max_turns=max_turns, agent_kwargs=kwargs)


def main(argv=None):
    """Run the paired endgame measurement.

    Parallel over (variant, seed) jobs. Unbuffered progress per game,
    because a run whose output is buffered is a run you cannot manage --
    and a probe of this very module lost its output that way.
    """
    import argparse
    import concurrent.futures
    import os
    import sys
    import time

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'src'))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', default=','.join(COVERED))
    parser.add_argument('--seeds', type=int, default=12)
    parser.add_argument('--simulations', type=int,
                        default=VALIDATED_SIMULATIONS)
    parser.add_argument('--workers', type=int, default=8)
    # A DOMAIN-APPROPRIATE CAP. 3000 was inherited and is wildly loose
    # here: under search play a `full` endgame runs ~43 plies and
    # `no_tiny_endgame` ~85, so 400 is roughly ten times the baseline
    # length. It bounds the cost of the arm that has no termination rule
    # while leaving the length effect room to show, and every game that
    # hits it is recorded as CENSORED rather than as a draw.
    parser.add_argument('--max-turns', type=int, default=400)
    parser.add_argument('--rave', action='store_true',
                        help='the GGP configuration, which measured 50.0% '
                             'self-agreement here against 42.9% plain')
    args = parser.parse_args(argv)

    variants = args.variants.split(',')
    for variant in variants:
        if variant in NOT_COVERED:
            parser.error('{} is not measurable in this domain: {}'.format(
                variant, NOT_COVERED[variant]))
    kwargs = ({'use_rave': True, 'use_mast': True} if args.rave else {})
    jobs = [(variant, seed, args.simulations, kwargs, args.max_turns)
            for variant in variants
            for seed in range(args.seeds)]

    print('{} variants x {} seeds = {} games at {} simulations'.format(
        len(variants), args.seeds, len(jobs), args.simulations),
        file=sys.stderr, flush=True)
    results = collections.defaultdict(list)
    started = time.time()
    done = 0
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=max(args.workers, 1)) as pool:
        # AS COMPLETED, not `map`. `pool.map` yields in SUBMISSION order,
        # so a slow first job hides every finished one behind it -- this
        # run showed 0 of 60 for minutes while eight workers were busy.
        # Order does not matter: the summary pairs by seed.
        futures = [pool.submit(_job, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            outcome = future.result()
            results[outcome.variant].append(outcome)
            done += 1
            elapsed = time.time() - started
            print('[endgame] {:>3}/{} {:<22} {:>4} plies  winner={:<6} '
                  '{}~{:.0f} min left'.format(
                      done, len(jobs), outcome.variant, outcome.plies,
                      str(outcome.winner),
                      'CENSORED  ' if outcome.censored else '',
                      (elapsed / done) * (len(jobs) - done) / 60),
                  file=sys.stderr, flush=True)
    print()
    print(summarise(dict(results)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
