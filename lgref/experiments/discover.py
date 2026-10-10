"""Inferring what matters, instead of being told.

THE QUESTION. Royal Chess is won by capturing both royals, and that
objective is flat almost everywhere -- equal royal counts in 100% of
opening positions. Material is what actually separates midgame moves, and
material is nowhere in the declared objective: nothing in the rules says
a rook is worth keeping. So either a researcher supplies that fact, which
fails the cross-game constraint, or the agent INFERS it.

It can be inferred, and the method is general because every step reads
the game rather than the game designer:

  1. ENUMERATE candidate features from the game's own vocabulary. For a
     piece game that is the count of each (player, piece type); the
     vocabulary comes from the state, not from a list someone wrote.
  2. PLAY games and record, for every sampled state, the features and
     the outcome that eventually followed.
  3. MEASURE which features predict the outcome. A feature that carries
     information about winning is one the game makes matter, whatever
     the rules say about it explicitly.

Step 3 is the whole claim: "material matters" is not an axiom but a
MEASURABLE relationship between a cheap feature and the win condition,
and the same procedure would discover pile size in nim or progress along
the corridor in the race game.

WHY THIS IS NOT SMUGGLING IN DOMAIN KNOWLEDGE. The features are
generated from whatever piece types the position contains, and their
weights come from observed outcomes. Nothing here states that a rook
beats a knight, that the centre is good, or that material is worth more
than activity. If material turned out not to predict winning in this
game, the procedure would say so.

THE HONEST LIMIT. Predictive power measured under one policy is a
statement about that policy's games. Features that predict the outcome of
RANDOM play need not predict the outcome of good play -- this is the same
agent-dependence that voided three sweeps (#231), and it applies to a
discovered evaluation exactly as it applies to a measured effect. The
discovery procedure therefore reports which policy produced its traces,
and a feature set is only worth trusting where it has been checked under
more than one.
"""

import collections
import math
import random

#: `ply` is carried so PHASE can be controlled for. Without it the
#: ranking is confounded: pawn count tracks how early the game is, and
#: how early it is tracks who is about to win, so a feature can look
#: predictive purely by marking the clock. The first run of this module
#: reported `Pawn` at d = -0.547 -- more pawns predicting defeat -- which
#: is what that confound looks like.
Trace = collections.namedtuple('Trace', 'features winner mover ply')

Finding = collections.namedtuple(
    'Finding', 'feature n mean_when_won mean_when_lost separation auc')


def piece_features(engine):
    """{(colour, type): count} from whatever the position contains.

    GENERATED, NOT LISTED. The vocabulary is read off the board, so a
    game with different pieces yields different features and no name is
    hard-coded. Royal pieces are distinguished because the state marks
    them, not because this module knows what they are for.
    """
    counts = collections.Counter()
    board = engine.board
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            colour = getattr(piece, 'color', None)
            kind = type(piece).__name__
            if getattr(piece, 'is_royal', False):
                kind += '*royal'
            counts[(colour, kind)] += 1
    return dict(counts)


def differentials(features, mover):
    """Features as (mover - opponent), which is what a score needs.

    A raw count cannot order positions between players; the difference
    can. Keyed by type alone, so the same feature means the same thing
    whichever side is to move.
    """
    out = collections.defaultdict(int)
    for (colour, kind), count in features.items():
        if colour is None:
            continue
        out[kind] += count if colour == mover else -count
    return dict(out)


def collect(make_engine, games=40, variant='full', agent='random',
            simulations=0, sample_every=4, max_turns=3000, seed=0):
    """Traces of (feature differentials, eventual winner) from self-play."""
    from lgref.experiments.random_play import build

    traces = []
    for game_index in range(games):
        engine = make_engine(variant, max_turns=max_turns)
        white = build(agent, random.Random(seed * 1000 + game_index * 2 + 1),
                      simulations)
        black = build(agent, random.Random(seed * 1000 + game_index * 2 + 2),
                      simulations)
        pending = []
        ply = 0
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            if ply % sample_every == 0:
                mover = engine.current_player
                pending.append((differentials(piece_features(engine), mover),
                                mover, ply))
            player = white if engine.current_player == 'white' else black
            engine.execute_turn(player.choose_turn(turns, engine))
            ply += 1
        winner = engine.winner
        if winner is None:
            # A censored game has no outcome to label traces with, and
            # labelling them a draw would teach the opposite of #260's
            # lesson.
            continue
        for feats, mover, at_ply in pending:
            traces.append(Trace(features=feats, winner=winner, mover=mover,
                                ply=at_ply))
    return traces


def _auc(won, lost):
    """Probability a random won-state scores above a random lost-state.

    Rank-based, so it needs no distributional assumption and is readable:
    0.5 is no information, 1.0 is perfect separation.
    """
    if not won or not lost:
        return float('nan')
    wins = ties = 0
    for a in won:
        for b in lost:
            if a > b:
                wins += 1
            elif a == b:
                ties += 1
    return (wins + 0.5 * ties) / float(len(won) * len(lost))


def rank(traces, min_count=30, ply_window=None):
    """Which features carry information about winning, strongest first.

    `ply_window` restricts to a (low, high) phase band so the comparison
    is within-phase. A feature that only marks the clock loses its
    apparent power once phase is held fixed, which is the point.
    """
    by_feature = collections.defaultdict(lambda: ([], []))
    for trace in traces:
        if ply_window is not None and not (
                ply_window[0] <= trace.ply < ply_window[1]):
            continue
        mover_won = (trace.winner == trace.mover)
        for name, value in trace.features.items():
            won, lost = by_feature[name]
            (won if mover_won else lost).append(value)

    findings = []
    for name, (won, lost) in by_feature.items():
        n = len(won) + len(lost)
        if n < min_count or not won or not lost:
            continue
        mean_won = sum(won) / float(len(won))
        mean_lost = sum(lost) / float(len(lost))
        spread = _pooled_sd(won, lost)
        separation = ((mean_won - mean_lost) / spread) if spread else 0.0
        findings.append(Finding(
            feature=name, n=n, mean_when_won=mean_won,
            mean_when_lost=mean_lost, separation=separation,
            auc=_auc(won, lost)))
    findings.sort(key=lambda f: -abs(f.separation))
    return findings


def _pooled_sd(a, b):
    def var(xs):
        if len(xs) < 2:
            return 0.0
        mean = sum(xs) / float(len(xs))
        return sum((x - mean) ** 2 for x in xs) / float(len(xs) - 1)
    na, nb = len(a), len(b)
    if na + nb < 3:
        return 0.0
    pooled = ((na - 1) * var(a) + (nb - 1) * var(b)) / float(na + nb - 2)
    return math.sqrt(pooled) if pooled > 0 else 0.0


def report(findings, policy, games):
    lines = [
        'DISCOVERED FEATURES -- what predicts winning, inferred not told',
        '',
        'Features are generated from the piece types the position',
        'contains and scored by how well they separate states whose',
        'mover eventually won from states whose mover eventually lost.',
        'Nothing here states that material matters; if it did not',
        'predict winning, the table would say so.',
        '',
        'POLICY: {} ({} games). Predictive power measured under one'.format(
            policy, games),
        'policy is a statement about that policy -- the same',
        'agent-dependence that voided three sweeps (#231).',
        '',
        '{:<22} {:>7} {:>10} {:>10} {:>11} {:>7}'.format(
            'feature', 'n', 'won', 'lost', "Cohen's d", 'AUC'),
    ]
    for f in findings:
        lines.append('{:<22} {:>7} {:>10.3f} {:>10.3f} {:>11.3f} {:>7.3f}'
                     .format(f.feature, f.n, f.mean_when_won,
                             f.mean_when_lost, f.separation, f.auc))
    return '\n'.join(lines)
