"""Structural metrics over positions drawn WITHOUT a policy (#242).

WHY THIS EXISTS. Every number this project has produced came from played
games, so every number carried the agent that played them. #231 withdrew
three sweeps because the agent's objective was one of the metrics, and the
agent ladder then showed the boulder's branching effect changing SIGN
between random play and a 40-simulation search -- the second agent for
which it did so. Strengthening the agent is one answer; removing it is a
better one where the question allows.

IT DOES ALLOW, for a large part of the profile. `position_metrics` reads
branching, attack coverage, reachability, denial, overlap and material
variety off a POSITION. Its own docstring says as much: "each is a
property of the position, so a cheap agent measures it as well as a strong
one." An agent is needed to REACH positions, not to measure them.

TWO THINGS THIS BUYS.

1. NO AGENT AT ALL. Positions are constructed by placement, so no policy
   chose them and no objective is smuggled in. What is lost is
   reachability: a constructed position may not arise in real play, and
   that limitation is stated rather than hidden. `docs/spec/objectivity.md`
   is explicit that outcome metrics (win rate, decisiveness, length) are
   properties of PLAY and cannot be freed this way.

2. A PAIRED DESIGN, which is #241 arriving for free. The same layout is
   measured under the full rules and under each ablation, so the only
   difference between the two readings is the RULE. Position variance --
   which is what left 17 of 22 cells `inconclusive` in the play-based
   ladder -- cancels exactly, instead of having to be averaged away with
   more games.
"""

import collections
import random

#: Material drawn per side, as (class name, count) weights. Kings and
#: royal queens are always present because the win condition is defined
#: on them and a position missing one is already decided. The rest is
#: sampled to span thin endgames through crowded midgames rather than to
#: imitate any particular opening.
MATERIAL = ('Pawn', 'Pawn', 'Pawn', 'Rook', 'Rook', 'Bishop', 'Bishop',
            'Knight', 'Knight', 'Queen')

Layout = collections.namedtuple('Layout', 'pieces boulder mover')


#: Material for the tiny-endgame regime, which the rule's own
#: precondition defines: no pawns, at most six non-king non-neutral
#: pieces, and a position that balances under cancel-queens + 1-to-2.
#: Sampling EQUAL non-queen counts per side is what makes it balance --
#: with one royal queen each they cancel, leaving r = 0, which balances
#: iff the sides' non-queen counts are equal (RULEBOOK.md).
ENDGAME_MATERIAL = ('Rook', 'Bishop', 'Knight')


def sample_layout(rng, min_extra=2, max_extra=8, endgame=False):
    """One random position as data, independent of any engine or variant.

    A LAYOUT, NOT A BOARD, so the identical position can be built under
    several rule sets. That is what makes the comparison paired.

    Pawns are kept off the last rank in either direction: arriving there
    forces promotion, so a pawn sitting on it is not a position the rules
    admit.
    """
    squares = [(r, c) for r in range(8) for c in range(8)]
    rng.shuffle(squares)
    pieces, used = [], 0

    for colour in ('white', 'black'):
        for name, royal in (('King', True), ('Queen', True)):
            pieces.append((colour, name, royal) + squares[used])
            used += 1

    if endgame:
        # THE SAME COUNT ON BOTH SIDES, drawn once. The rule activates
        # only on a balanced position, and independent draws per colour
        # almost never balance -- which is why the first attempt measured
        # the tiny endgame as "no structural difference" when it had
        # simply never activated.
        count = rng.randint(min_extra, max_extra)
        for colour in ('white', 'black'):
            for name in [rng.choice(ENDGAME_MATERIAL) for _ in range(count)]:
                pieces.append((colour, name, False) + squares[used])
                used += 1
    else:
        for colour in ('white', 'black'):
            for name in rng.sample(MATERIAL,
                                   rng.randint(min_extra, max_extra)):
                row, col = squares[used]
                used += 1
                if name == 'Pawn' and row in (0, 7):
                    # Promotion is forced on the last rank, so a pawn
                    # cannot be standing on one.
                    name = 'Knight'
                pieces.append((colour, name, False, row, col))

    boulder = squares[used]
    return Layout(tuple(pieces), boulder, rng.choice(('white', 'black')))


def apply_layout(engine, layout, saturate=False):
    """Put `layout` on `engine`'s board, respecting the variant.

    THE BOULDER IS PLACED ONLY IF THE VARIANT HAS ONE. `no_boulder`
    builds an engine whose `board.boulder` is None, and placing one here
    would quietly undo the ablation being measured -- the same class of
    mistake as a variant flag leaking between jobs.
    """
    from piece import Bishop, Boulder, King, Knight, Pawn, Queen, Rook

    classes = {'Pawn': Pawn, 'Knight': Knight, 'Bishop': Bishop,
               'Rook': Rook, 'Queen': Queen, 'King': King}
    board = engine.board
    has_boulder = board.boulder is not None or any(
        isinstance(board.squares[r][c].piece, Boulder)
        for r in range(8) for c in range(8))

    for row in range(8):
        for col in range(8):
            board.squares[row][col].piece = None
    board.boulder = None

    for colour, name, royal, row, col in layout.pieces:
        piece = classes[name](colour)
        if royal:
            piece.is_royal = True
        board.squares[row][col].piece = piece

    if has_boulder:
        row, col = layout.boulder
        if board.squares[row][col].piece is None:
            boulder = Boulder()
            boulder.on_intersection = False
            boulder.first_move = False
            board.squares[row][col].piece = boulder

    engine.current_player = layout.mover
    engine.winner = None
    engine.loss_reason = None
    board.turn_number = 2          # past White's first-turn boulder ban
    engine.turn_number = 2

    # ACTIVATE THE TINY ENDGAME RULE IF THIS POSITION QUALIFIES, exactly
    # as `GameEngine.execute_turn` does. Without this the flag is never
    # evaluated on a constructed board and the rule cannot be measured at
    # all -- the sampler reported "no structural difference" for
    # `no_tiny_endgame` when it had simply never activated. The ablated
    # variant sets `enable_tiny_endgame=False`, so the same layout
    # activates under `full` and not under it, which is the comparison.
    board.tiny_endgame_active = False
    if getattr(engine, 'enable_tiny_endgame', False) \
            and board.is_tiny_endgame():
        board.init_tiny_endgame()
        if saturate:
            # THE RULE'S RESTRICTION NEEDS HISTORY, not just activation.
            # A freshly activated position has one distance seen once, and
            # the limit forbids a non-capture turn whose RESULTING
            # distance would exceed a count of 3 -- so nothing is
            # forbidden until a distance has occurred three times. Setting
            # the current distance's count to 3 puts the position in the
            # regime where the rule actually restricts, which is the only
            # regime in which it can be measured.
            #
            # This is constructing a state the rules permit, not inventing
            # one: three occurrences of a distance is a legal history, and
            # reaching a rule's activation predicate directly is what #237
            # asks for. Play does not get here -- the gate reports this
            # rule NOT EXERCISED across 200 plies of four lines.
            distance = board.get_royal_distance()
            if 1 <= distance <= 14:
                board.distance_counts[distance] = 3
    return engine


def usable(engine):
    """Is this a position the metrics can be read from?

    A position with no legal turn is a LOSS, not a sample: its branching
    is zero for a reason that belongs to the position rather than to the
    rules being compared.
    """
    if engine.is_game_over():
        return False
    return bool(engine.get_all_legal_turns())


def paired_positions(make_engine, variants, n, seed=0,
                     min_extra=2, max_extra=8, endgame=False,
                     saturate=False):
    """Yield (layout_index, {variant: metrics}) over identical layouts.

    A layout is skipped ONLY if it is unusable under every variant
    compared -- dropping it for one and keeping it for another would
    break the pairing and reintroduce exactly the selection the design
    removes.
    """
    from lgref.experiments.metrics import position_metrics

    rng = random.Random(seed)
    index = 0
    produced = 0
    while produced < n:
        layout = sample_layout(rng, min_extra, max_extra,
                               endgame=endgame)
        index += 1
        engines = {}
        for variant in variants:
            engine = apply_layout(make_engine(variant, max_turns=1000),
                                  layout, saturate=saturate)
            if not usable(engine):
                engines = None
                break
            engines[variant] = engine
        if not engines:
            continue
        yield index, {name: position_metrics(engine)
                      for name, engine in engines.items()}
        produced += 1


def paired_differences(make_engine, variant, n, baseline='full', seed=0,
                       min_extra=2, max_extra=8, endgame=False,
                       saturate=False):
    """Per-metric list of (variant - baseline) on identical positions.

    THE DIFFERENCE IS TAKEN WITHIN A POSITION, so position variance
    cancels rather than being averaged away. In the play-based ladder 17
    of 22 cells were `inconclusive` because the between-game spread
    swamped the difference; here the spread is not in the comparison at
    all.
    """
    out = collections.defaultdict(list)
    for _index, by_variant in paired_positions(
            make_engine, (baseline, variant), n, seed, min_extra,
            max_extra, endgame, saturate):
        base, other = by_variant[baseline], by_variant[variant]
        for metric, value in base.items():
            if isinstance(value, bool) or not isinstance(
                    value, (int, float)):
                continue
            theirs = other.get(metric)
            if theirs is None or isinstance(theirs, bool) or not isinstance(
                    theirs, (int, float)):
                continue
            out[metric].append(theirs - value)
    return dict(out)


#: Variants whose mechanism needs per-piece state that only PLAY sets,
#: so a constructed position cannot exercise them and an exact zero here
#: is an absence of measurement rather than a measured zero (#259's
#: distinction, arriving in a second place).
#:
#: A knight's invulnerability is granted by a qualifying jump; the
#: manipulation freeze is set on a piece that was just manipulated;
#: reactive-arming depends on where the previous move began; the boulder's
#: cooldown and no-return memory are written by its last move; the
#: repetition rule consults a history of states. None of that exists in a
#: position built by placement, so these ablations have nothing to remove.
#:
#: `no_boulder` is NOT here: it removes the boulder from the position
#: itself, which is static, and it measures t = -11.1 on branching.
DYNAMIC_ONLY = frozenset((
    'no_knight_invulnerability',
    'no_bishop_reactive',
    'no_repetition_rule',
))

#: Variants that are rule-identical to the baseline by construction. An
#: exact zero for these is the instrument's noise floor and the one case
#: where zero is the right answer and means what it says.
RULE_IDENTICAL = frozenset(('control_inert',))

#: Variants that measure as zero under the DEFAULT sampling regime and
#: non-zero under a targeted one, so a zero from the default regime says
#: nothing about them.
#:
#: `no_tiny_endgame` is the case that proved this. The rule needs no
#: pawns, at most six non-king pieces and a balanced position to activate,
#: and then its restriction only bites once a royal distance has occurred
#: three times. Under default sampling it activated in 0 of 150 positions
#: and measured "no structural difference". Under `endgame=True,
#: saturate=True` it activates in 150 of 150 and removes FIFTY-THREE legal
#: turns per position -- and the gate reports this same rule NOT EXERCISED
#: across 200 plies of four lines, so play never measures it at all.
REGIME_GATED = frozenset(('no_tiny_endgame',))

NOT_EXERCISED = 'not exercised by static positions'
WRONG_REGIME = 'not exercised by this sampling regime'
NO_DIFFERENCE = 'no structural difference'
STRUCTURAL = 'structural effect'


def classify(variant, diffs):
    """What an all-zero paired difference means for THIS variant.

    THREE READINGS OF THE SAME ZERO, and only declared knowledge tells
    them apart:

      * `control_inert` is rule-identical, so zero is correct and is the
        noise floor that validates the method;
      * an ablation of a dynamic mechanism has nothing to remove from a
        constructed position, so zero is an absence of measurement;
      * an ablation whose rule has a PRECONDITION the default material
        never meets is also an absence of measurement, and needs the
        regime that meets it -- `no_tiny_endgame` measures zero by
        default and +52.8 legal turns under `endgame=True,
        saturate=True`;
      * anything else genuinely did not change the structure.

    Reporting the second as "no effect" would repeat #259 -- an index of
    0.0 printed as a measured result when it meant nothing was measured.
    """
    changed = sorted(metric for metric, xs in diffs.items()
                     if any(x != 0 for x in xs))
    if changed:
        return STRUCTURAL, changed
    if variant in RULE_IDENTICAL:
        return NO_DIFFERENCE, []
    if variant in DYNAMIC_ONLY:
        return NOT_EXERCISED, []
    if variant in REGIME_GATED:
        return WRONG_REGIME, []
    return NO_DIFFERENCE, []


def report(make_engine, variants, n=200, baseline='full', seed=0,
           endgame=False, saturate=False, min_extra=2, max_extra=8):
    """A paired, agent-free structural table as text."""
    import math
    import statistics as st

    regime = ('endgame, saturated' if endgame and saturate
              else 'endgame' if endgame else 'default')
    lines = [
        'STRUCTURAL PROFILE WITHOUT AN AGENT (#242)',
        '',
        'Positions are CONSTRUCTED, so no policy chose them, and each is',
        'measured under the baseline and the ablation so only the RULE',
        'differs. Position variance cancels within the pair instead of',
        'being averaged away with more games.',
        '',
        'WHAT THIS CANNOT DO: outcome metrics -- win rate, decisiveness,',
        'game length -- are properties of PLAY, not of a position, and',
        'are absent here by construction rather than by omission. A',
        'constructed position may also be unreachable in real play.',
        '',
        'regime: {}   positions: {}   baseline: {}'.format(regime, n, baseline),
        '']
    for variant in variants:
        diffs = paired_differences(make_engine, variant, n, baseline, seed,
                                   min_extra, max_extra, endgame, saturate)
        verdict, changed = classify(variant, diffs)
        lines.append('  {:<28} {}'.format(variant, verdict))
        for metric in changed:
            xs = diffs[metric]
            mean = st.mean(xs)
            sd = st.stdev(xs) if len(xs) > 1 else 0.0
            t = mean / (sd / math.sqrt(len(xs))) if sd else float('inf')
            lines.append('      {:<28} {:+9.3f}  sd {:7.3f}  t {}'.format(
                metric, mean, sd,
                '{:+.1f}'.format(t) if sd else 'exact'))
        lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    import argparse
    import os
    import sys

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'src'))
    from experiments.variants import VARIANTS, make_engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', default=None,
                        help='comma-separated; default every non-baseline')
    parser.add_argument('--positions', type=int, default=200)
    parser.add_argument('--baseline', default='full')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--endgame', action='store_true',
                        help="sample the tiny-endgame rule's own regime")
    parser.add_argument('--saturate', action='store_true',
                        help='put the distance counts at the limit, where '
                             'the tiny-endgame restriction actually bites')
    parser.add_argument('--min-extra', type=int, default=2)
    parser.add_argument('--max-extra', type=int, default=8)
    args = parser.parse_args(argv)

    names = (args.variants.split(',') if args.variants
             else [v for v in sorted(VARIANTS) if v != args.baseline])
    print(report(make_engine, names, args.positions, args.baseline,
                 args.seed, args.endgame, args.saturate,
                 args.min_extra, args.max_extra))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
