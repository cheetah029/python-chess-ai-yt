"""Inferring what matters, instead of being told.

THE QUESTION. Royal Chess is won by capturing both royals, and that
objective is flat almost everywhere -- equal royal counts in 100% of
opening positions. Material is what actually separates midgame moves, and
material is nowhere in the declared objective: nothing in the rules says
a rook is worth keeping. So either a researcher supplies that fact, which
fails the cross-game constraint, or the agent INFERS it.

It can be inferred, and the method is general because every step reads
the game rather than the game designer:

  1. ENUMERATE candidate features from the game's own vocabulary, via
     an INJECTED extractor (`lgref/experiments/features.py`). This
     module once walked an 8x8 board, imported a Royal Chess piece
     class and listed three piece names by hand, while its docstring
     claimed that no piece name was hard-coded. The estimator now never
     learns what a bishop is; `features.mnk` is a second extractor that
     exists so generality is tested rather than asserted.
  2. PLAY games and record, for every sampled state, the features and
     the outcome that eventually followed.
  3. MEASURE which features predict the outcome. A feature that carries
     information about winning is one the game makes matter, whatever
     the rules say about it explicitly.

Step 3 is the whole claim: "material matters" is not an axiom but a
MEASURABLE relationship between a cheap feature and the win condition,
and the same procedure would discover pile size in nim or progress along
the corridor in the race game.

WHERE DOMAIN KNOWLEDGE IS ALLOWED TO LIVE. In the extractor, which is
one named function behind a documented protocol, and nowhere else. The
weights come from observed outcomes. Nothing in THIS module states that
a rook beats a knight, that the centre is good, or that material is
worth more than activity -- and nothing in it mentions a rook.

THREE DEFECTS THIS MODULE HAD, all found by reading its own output and
all of which manufactured signal rather than losing it:

  FORM COUNTED AS MATERIAL.  `type(piece).__name__` is the queen's FORM,
      not its identity. A royal queen transformed to knight form stops
      being `Queen*royal` and becomes `Knight*royal`, so a
      Transformation action -- which captures nothing and changes no
      material -- swung the feature vector by two units, and NO feature
      measured the quantity the declared objective depends on ("is my
      royal queen alive"). Queen-kind pieces are now counted by identity
      (`RoyalQueen`, `PromotedQueen`) with form carried separately
      (`RoyalQueenForm:*`), so material and capability are separable.
      The queen-kind test is the codebase's own
      (`isinstance(p, Queen) or p.is_transformed`, src/game.py:256).

  THE NEUTRAL BOULDER COUNTED AS AN ENEMY OF BOTH SIDES.  `Board` spells
      the boulder's colour as the STRING `'none'`, so the `is None`
      guard here missed it and `differentials` scored it -1 for whoever
      was to move -- the same sign for both players, which is not a
      differential at all. Neutral pieces are now excluded by
      `NEUTRAL_COLOURS`, which lists the engine's sentinel rather than
      guessing at it.

  THE SAMPLE WAS COUNTED IN THE WRONG UNIT.  States are sampled every
      few plies and every state in a game carries that game's single
      outcome, so traces are CLUSTERED: 880 traces came from 14 games.
      Gating on trace count let a feature through on 4 games (`Queen`,
      n=20 traces) and let Cohen's d be computed as though the sample
      were 63x larger than it is. `Finding` now carries `games` and the
      gate is `min_games`; `Trace` carries the game it came from so the
      clustering is visible instead of implicit.

THE LIMIT THIS MODULE CANNOT PASS AT ALL. An outcome regression over
self-play is OBSERVATIONAL. Where two features cannot vary
independently in play -- live bishops and bishop-form availability move
together, because one capture does both -- their marginal coefficients
are not separately interpretable at any sample size, and more data does
not help. `conditional()` detects it and declines; `factorial.py`
answers it by intervention. Treat a ranking from this module as a
HYPOTHESIS GENERATOR, and make causal claims with an intervention.

THE HONEST LIMIT THAT REMAINS. Predictive power measured under one
policy is a statement about that policy's games. Features that predict
the outcome of RANDOM play need not predict the outcome of good play --
this is the same agent-dependence that voided three sweeps (#231), and
it applies to a discovered evaluation exactly as it applies to a
measured effect. The discovery procedure therefore reports which policy
produced its traces, and a feature set is only worth trusting where it
has been checked under more than one.
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
#:
#: `game` is carried because traces are CLUSTERED. Every state sampled
#: from one game shares that game's outcome, so the independent unit is
#: the game and a trace count overstates the sample by however often
#: states were sampled. `None` means "unknown provenance", and `rank`
#: then treats the trace as its own cluster rather than silently pooling
#: it with others.
Trace = collections.namedtuple('Trace', 'features winner mover ply game')
Trace.__new__.__defaults__ = (None,)

Finding = collections.namedtuple(
    'Finding',
    'feature n games mean_when_won mean_when_lost separation se auc')

#: Owners belonging to no player, from the extractor protocol. Royal
#: Chess's boulder arrives as the STRING 'none', not `None`, and an
#: `is None` test here scored it as an enemy of both sides at once.
#: `NEUTRAL_COLOURS` is kept as the old name.
from lgref.experiments.features import NEUTRAL_OWNERS

NEUTRAL_COLOURS = NEUTRAL_OWNERS


def differentials(features, mover):
    """Features as (mover - opponent), which is what a score needs.

    A raw count cannot order positions between players; the difference
    can. Keyed by kind alone, so the same feature means the same thing
    whichever side is to move.

    NEUTRAL PIECES ARE EXCLUDED. A piece belonging to neither player
    cannot have a mover-relative value: scoring it against the mover
    gives the same sign to both players, which is a constant dressed as
    a feature. The boulder reached this function as colour `'none'` and
    was scored -1 for whoever was to move.
    """
    out = collections.defaultdict(int)
    for (colour, kind), count in features.items():
        if colour in NEUTRAL_OWNERS:
            continue
        out[kind] += count if colour == mover else -count
    return dict(out)


def collect(make_engine, extractor, games=40, variant='full',
            agent='random', simulations=0, sample_every=4,
            max_turns=3000, seed=0):
    """Traces of (feature differentials, eventual winner) from self-play.

    `extractor` supplies the game's vocabulary -- see
    `lgref/experiments/features.py` for the protocol. It is a parameter
    rather than a hard-coded board walk because this module had become a
    Royal Chess module while claiming not to be.
    """
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
                pending.append((differentials(extractor(engine), mover),
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
                                ply=at_ply, game=(seed, game_index)))
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


def rank(traces, min_count=30, ply_window=None, min_games=8,
         cluster=True):
    """Which features carry information about winning, strongest first.

    `ply_window` restricts to a (low, high) phase band so the comparison
    is within-phase. A feature that only marks the clock loses its
    apparent power once phase is held fixed, which is the point.

    CLUSTER-AGGREGATED BY DEFAULT, and this is not a refinement -- it is
    the difference between a real effect size and a manufactured one.
    States sampled from one game are not independent observations: the
    game has ONE outcome and its material trajectory is autocorrelated,
    so 163 traces from 10 games carry about 10 games' worth of
    information. Computing Cohen's d on the traces divides by a spread
    estimated from pseudo-replicates and inflates every effect.

    The cluster unit is (game, side), which is the finest unit that has
    a single outcome: within one game the mover alternates, so some
    sampled states belong to the eventual winner and some to the
    eventual loser. Each game therefore contributes at most one won-side
    observation and one lost-side observation, each the mean of that
    side's sampled states. `min_games` then gates on a count that means
    what it says.

    `cluster=False` recovers the old trace-level numbers, kept only so
    the inflation can be measured rather than asserted.
    """
    # (feature -> cluster -> [values]), split by whether the mover of
    # those states eventually won.
    grouped = collections.defaultdict(
        lambda: (collections.defaultdict(list), collections.defaultdict(list)))
    counts = collections.Counter()
    for index, trace in enumerate(traces):
        if ply_window is not None and not (
                ply_window[0] <= trace.ply < ply_window[1]):
            continue
        mover_won = (trace.winner == trace.mover)
        # An unknown provenance is its own cluster: pooling traces whose
        # game is unrecorded would re-create the defect this guards.
        key = trace.game if trace.game is not None else ('?', index)
        for name, value in trace.features.items():
            won, lost = grouped[name]
            (won if mover_won else lost)[key].append(value)
            counts[name] += 1

    findings = []
    for name, (won_by, lost_by) in grouped.items():
        n = counts[name]
        n_games = len(set(won_by) | set(lost_by))
        if cluster:
            won = [sum(v) / float(len(v)) for v in won_by.values()]
            lost = [sum(v) / float(len(v)) for v in lost_by.values()]
        else:
            won = [v for values in won_by.values() for v in values]
            lost = [v for values in lost_by.values() for v in values]
        if n < min_count or n_games < min_games or not won or not lost:
            continue
        mean_won = sum(won) / float(len(won))
        mean_lost = sum(lost) / float(len(lost))
        spread = _pooled_sd(won, lost)
        separation = _separation(mean_won, mean_lost, spread)
        findings.append(Finding(
            feature=name, n=n, games=n_games, mean_when_won=mean_won,
            mean_when_lost=mean_lost, separation=separation,
            se=_se_of_d(len(won), len(lost), separation),
            auc=_auc(won, lost)))
    findings.sort(key=lambda f: -abs(f.separation))
    return findings


def _separation(mean_won, mean_lost, spread):
    """Cohen's d, with the zero-variance case handled rather than hidden.

    The guard this replaces read `diff / spread if spread else 0.0`,
    which reported a PERFECTLY SEPARATING feature as carrying no
    information: if every won-state scores above every lost-state and
    neither group varies, the pooled spread is zero, so the feature was
    assigned d = 0.000 and dropped -- while its AUC read 1.000. That is
    the opposite of the inflation the rest of this module guards
    against, and it was found by a test that happened to construct the
    degenerate case.

    With no within-group spread the standardised difference is
    unbounded, so that is what is returned. `_se_of_d` reports no
    uncertainty for it and `min_games` is what keeps a perfect
    separation on three games from being believed.
    """
    diff = mean_won - mean_lost
    if spread:
        return diff / spread
    if diff:
        return math.copysign(float('inf'), diff)
    return 0.0


def _se_of_d(n_won, n_lost, d):
    """Standard error of Cohen's d, so an effect size carries its own
    uncertainty instead of being read as though it were precise.

    The usual large-sample expression. It exists because a gate on
    effect size alone cannot distinguish a large effect from a small
    sample, and the largest numbers this module produces have always
    come from its smallest groups: d = -1.685 on ten games, d = +2.12 on
    a dozen. Dividing by this turns "biggest" into "best supported".
    """
    if n_won < 2 or n_lost < 2:
        return float('inf')
    if math.isinf(d):
        # Perfect separation with no within-group spread. The effect is
        # not uncertain in this statistic's terms; whether it is
        # BELIEVABLE is a question about the cluster count, which
        # `min_games` asks separately.
        return 0.0
    total = n_won + n_lost
    return math.sqrt(total / float(n_won * n_lost) + (d * d) / (2.0 * total))


def conditional(traces, feature, given, min_games=8, min_stratum=4):
    """`feature`'s effect measured WITHIN strata of `given`, then pooled.

    WHY A MARGINAL EFFECT IS NOT ENOUGH. Two features that move together
    in play each absorb the other's influence, and a marginal ranking
    reports both at full strength without saying so. `Bishop` and
    `FormAvailable:bishop` are the worked case: a capture decrements one
    and sets the other in the same event, so in played games they are
    almost perfectly confounded and their marginal coefficients are
    uninterpretable individually.

    Holding `given` fixed and measuring `feature` inside each stratum
    removes that overlap for whatever variation survives conditioning.
    If the conditional estimate collapses or changes sign relative to
    the marginal one, the marginal number was carried by the confound --
    which is a conclusion the marginal ranking cannot reach on its own.

    THE LIMIT. Conditioning can only use variation that EXISTS. Where
    two quantities never vary independently, no stratum contains the
    contrast and this returns `None` rather than a number -- correctly,
    because the data cannot answer it. That is the signal to run an
    intervention instead (`lgref/experiments/factorial.py`).
    """
    strata = collections.defaultdict(list)
    for trace in traces:
        if given not in trace.features or feature not in trace.features:
            continue
        strata[trace.features[given]].append(trace)

    pieces = []
    for value, group in sorted(strata.items()):
        found = [f for f in rank(group, min_count=min_stratum,
                                 min_games=min_stratum)
                 if f.feature == feature]
        if not found or math.isinf(found[0].separation):
            continue
        finding = found[0]
        if finding.se and finding.se > 0:
            pieces.append((finding, value))

    if not pieces:
        return None
    # Inverse-variance pooling: a stratum with a tighter estimate should
    # count for more, which a plain mean would ignore.
    weights = [1.0 / (f.se ** 2) for f, _v in pieces]
    total = sum(weights)
    pooled = sum(w * f.separation for w, (f, _v) in zip(weights, pieces))
    pooled /= total
    se = math.sqrt(1.0 / total)
    games = sum(f.games for f, _v in pieces)
    n = sum(f.n for f, _v in pieces)
    return Finding(feature=feature, n=n, games=games,
                   mean_when_won=float('nan'),
                   mean_when_lost=float('nan'),
                   separation=pooled, se=se, auc=float('nan'))


def confound_report(traces, pairs, min_games=8):
    """Marginal vs conditional, for pairs suspected of moving together.

    `pairs` is [(feature, given)]. A row where the two estimates differ
    materially is a row whose marginal number should not be quoted on
    its own.
    """
    marginal = {f.feature: f for f in rank(traces, min_count=30,
                                           min_games=min_games)}
    lines = [
        'MARGINAL vs CONDITIONAL -- which findings survive conditioning',
        '',
        'A feature that moves with another in play absorbs its',
        'influence. Where the conditional estimate collapses, the',
        'marginal one was carried by the confound. Where no stratum',
        'holds the contrast at all, the data cannot answer it and an',
        'intervention is required instead.',
        '',
        '{:<24} {:<26} {:>10} {:>12} {:>9}'.format(
            'feature', 'conditioned on', 'marginal d', 'conditional d',
            'verdict'),
    ]
    out = []
    for feature, given in pairs:
        base = marginal.get(feature)
        cond = conditional(traces, feature, given, min_games=min_games)
        if base is None:
            continue
        if cond is None:
            verdict = 'NO CONTRAST'
            shown = '        --'
        else:
            shown = '{:>+12.3f}'.format(cond.separation)
            if base.separation * cond.separation < 0:
                verdict = 'SIGN FLIP'
            elif abs(cond.separation) < 0.5 * abs(base.separation):
                verdict = 'COLLAPSES'
            else:
                verdict = 'survives'
        lines.append('{:<24} {:<26} {:>+10.3f} {} {:>9}'.format(
            feature, given, base.separation, shown, verdict))
        out.append((feature, given, base, cond, verdict))
    return '\n'.join(lines), out


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
        'Features come from the extractor this run was given, and are',
        'scored by how well they separate states whose mover eventually',
        'won from states whose mover eventually lost. Nothing here',
        'states which features ought to matter; if one did not predict',
        'winning, the table would say so.',
        '',
        'THIS IS A CORRELATION OVER WHOLE GAMES, so it is a hypothesis',
        'generator and not an evaluation. A feature can separate',
        'outcomes strongly while the argmax of a score built from it is',
        'a bad move. Check an evaluation with',
        '`validate.optimal_action_rate` against exact play.',
        '',
        'GAMES, not traces, is the sample size. Every state sampled from',
        'one game shares that game\'s outcome, so d computed on traces is',
        'as precise as the game count allows and no more.',
        '',
        'POLICY: {} ({} games). Predictive power measured under one'.format(
            policy, games),
        'policy is a statement about that policy -- the same',
        'agent-dependence that voided three sweeps (#231).',
        '',
        'd is reported with its standard error and z = |d|/SE. A row',
        'with z below about 2 is not distinguishable from zero, however',
        'large its d -- which is the state every one of this module\'s',
        'biggest numbers has been in.',
        '',
        '{:<26} {:>7} {:>6} {:>9} {:>9} {:>10} {:>7} {:>6} {:>7}'.format(
            'feature', 'n', 'games', 'won', 'lost', "Cohen's d", 'SE', 'z',
            'AUC'),
    ]
    for f in findings:
        z = (abs(f.separation) / f.se) if f.se else float('inf')
        lines.append(
            '{:<26} {:>7} {:>6} {:>9.3f} {:>9.3f} {:>10.3f} {:>7.3f} '
            '{:>6.1f} {:>7.3f}'.format(
                f.feature, f.n, f.games, f.mean_when_won, f.mean_when_lost,
                f.separation, f.se, z, f.auc))
    return '\n'.join(lines)
