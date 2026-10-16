"""Temporal-difference bootstrapping: learn what matters from the only
label the rules actually provide.

WHY THE PREVIOUS ROUTE WAS WRONG, stated plainly because the error was
mine and it was a reasoning error rather than a bug.

`generic.py` built features by reading the game's declared terminal
conditions and treating PROXIMITY to each as valuable: "no legal turn is
a loss, therefore mobility matters", "losing both royals is a loss,
therefore royal count matters". That inference is invalid. A termination
condition is an INDICATOR, not a gradient:

  * "No legal turn at the start of your turn" separates 0 legal moves
    from n > 0. It says NOTHING about 1 versus 100 -- every positive
    mobility is treated identically by the rule. (And in this game the
    condition is reached mainly through the tiny-endgame rule, which
    exists precisely to terminate, so it is rare besides.)
  * "Both royals captured" separates both-gone from at-least-one-alive.
    It says NOTHING about 2 alive versus 1 alive.

So neither a mobility gradient nor a material gradient -- nor even a
preference for two royals over one -- follows from the rules. Each has
to be INFERRED from the game's dynamics. Converting a threshold into a
distance is a researcher's assumption wearing a rule's clothing, and it
is the same class of error as hand-picking piece values, just better
disguised.

WHAT THE RULES DO GIVE. Exactly one thing: the outcome at terminal
states. Everything else must be derived from it.

WHAT BOOTSTRAPPING DOES ABOUT IT. Temporal difference learning
propagates that single label backward through the states that lead to
it. The value of a position is fitted toward the value of the position
that FOLLOWS it, with terminal states anchored at the true result:

    V(s_t)  <-  1 - V(s_{t+1})          (the opponent moves next)
    V(s_T)  <-  the actual outcome      (the only ground truth)

Nothing in that assumes which features matter, in which direction, or by
how much. Weights start at EXACTLY ZERO -- a uniformly 0.5 evaluation,
no prior of any kind -- and any structure that appears was derived from
the terminal signal. If material turns out to predict winning, that is a
discovery; if mobility turns out to be worth nothing, or negative, the
weights say so.

This is also the answer to "how would it know that preserving material
leads to the win condition?". It would not, and cannot, from the rules.
It can only learn it by observing that positions with more material tend
to precede positions that precede winning -- which is precisely the
chain TD walks backward.

WHY NOT JUST REGRESS ON OUTCOMES. That is TD with lambda = 1, which is
what `discover.py` does, and it needs the causal chain to be present in
the traces: random play never converts material into royal captures, so
the relationship is absent from the data and 240 games of it measured
ordinary material at z < 1.5. Bootstrapping does not need whole games to
be informative, because each step's target comes from the next step
rather than from a distant outcome, so credit travels one ply at a time
even when no trajectory is good.

THE TWO FAILURE MODES, guarded rather than hoped about:

  COLLAPSE      an agent trained on its own greedy games stops seeing
                alternatives. Guarded by epsilon-greedy exploration and
                by anchoring every terminal at the true outcome.
  DIVERGENCE    bootstrapping from a bad estimate can amplify it. Linear
                function approximation with a bounded target keeps this
                tractable, and the weights are inspectable so a runaway
                is visible rather than silent.

VALIDATION, not assertion. On an m,n,k game the result is checkable
against exact minimax (`validate.py`), so "did TD learn to play well
from zero" is answered by a number rather than by an argument.
"""

import collections
import math
import random

Snapshot = collections.namedtuple('Snapshot', 'round games weights score')


def normalise(features, scales, decay=0.01, update=True):
    """Features divided by a running estimate of their own RANGE.

    THE DIVISOR IS A DECAYING MAX, NOT A MEAN, and that correction
    matters more than anything else in this module. Dividing by a
    running mean of |value| looks reasonable until a feature is SPARSE:
    `King*royal` is zero in almost every state, because both kings are
    normally alive, so its mean |value| decays toward zero -- and
    dividing by a number approaching zero makes the normalised feature,
    and therefore its gradient, explode.

    Measured: two 800-game runs that differed only in seed produced
    effective values of +506.05 and +1.21 for `RoyalQueen`, and -0.875
    against +1.15e17 for `King*royal`. That is not sample noise, it is
    numerical divergence, and I spent three rounds attributing the
    resulting instability to sample size.

    A decaying maximum cannot collapse: it is bounded below by the
    largest magnitude the feature has actually shown, so normalised
    features stay inside roughly [-1, 1] whether the feature is dense
    or sparse. It still adapts, because the max decays when large
    values stop appearing.

    NECESSARY, not cosmetic. A linear model with one learning rate gives
    the largest-magnitude feature the largest gradient, so a feature
    measured in tens swamps features measured in ones. Measured: the
    mobility differential ranges about +/-70 in Royal Chess while piece
    counts range about +/-2, and after a SINGLE game mobility had reached
    -3.44 while every other weight sat near 0.1 -- it was not that
    mobility had been found important, it was that it was simply bigger.
    The same effect is the likely cause of the sign flips seen mid-run on
    m,n,k, where mobility spans 0-16.

    The scale is estimated online from the data, so no per-feature
    constant is supplied and nothing about any game is assumed.
    """
    out = {}
    for name, amount in features.items():
        magnitude = abs(amount)
        if update:
            previous = scales.get(name)
            if previous is None:
                scales[name] = magnitude
            elif magnitude >= previous:
                scales[name] = magnitude            # a new high: take it
            else:
                # Decay slowly toward the smaller value, so the scale
                # tracks a shrinking range without ever collapsing to a
                # sparse feature's long run of zeros.
                scales[name] = ((1.0 - decay) * previous
                                + decay * magnitude)
        scale = scales.get(name) or 0.0
        # A FLOOR OF ONE. Every feature here is a count or a count
        # difference, so one unit is the smallest meaningful step; a
        # feature that has only ever been zero must not be amplified.
        out[name] = amount / max(scale, 1.0)
    return out


def value(weights, features):
    """Logistic value in (0, 1) for the player to move.

    Zero weights give exactly 0.5 everywhere, which is the honest
    starting point: no position is preferred until something has been
    learned.
    """
    total = sum(weights.get(name, 0.0) * amount
                for name, amount in features.items())
    if total > 30:
        return 1.0
    if total < -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-total))


def _features(extractor, engine, mover, scales=None, update=False):
    from lgref.experiments.discover import differentials

    raw = differentials(extractor(engine), mover)
    if scales is None:
        return raw
    return normalise(raw, scales, update=update)


def choose(engine, turns, weights, extractor, rng, epsilon,
           scales=None):
    """One-ply greedy on the current value, with epsilon exploration.

    A one-ply lookahead is the cheapest policy improvement over a value
    function and is what TD-Gammon used. Terminal results are read, not
    estimated, because an estimate of a decided position is strictly
    worse than the decision.
    """
    from lgref.experiments.fastcopy import clone_with_turns

    if epsilon > 0 and rng.random() < epsilon:
        return rng.choice(turns)
    mover = engine.current_player
    best, best_value = None, float('-inf')
    for turn in turns:
        sim, sim_turns = clone_with_turns(engine, turns)
        sim.execute_turn(sim_turns[turns.index(turn)])
        if sim.is_game_over():
            if sim.winner == mover:
                scored = 1.0
            elif sim.winner is None:
                scored = 0.5
            else:
                scored = 0.0
        else:
            # The opponent moves next, so our value is one minus theirs.
            scored = 1.0 - value(weights,
                                 _features(extractor, sim,
                                           sim.current_player, scales))
        if scored > best_value:
            best_value, best = scored, turn
    return best if best is not None else turns[0]


def play_and_learn(make_engine, extractor, weights, rng, variant='full',
                   max_turns=400, alpha=0.05, epsilon=0.15, scales=None):
    """One self-play game, updating `weights` in place by TD(0).

    Returns the number of updates applied. The update is the logistic
    cross-entropy gradient, `(target - prediction) * feature`, which for
    a linear-logistic value is both correct and cheap.
    """
    engine = make_engine(variant, max_turns=max_turns)
    trajectory = []
    plies = 0
    while not engine.is_game_over() and plies < max_turns:
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        mover = engine.current_player
        feats = _features(extractor, engine, mover, scales, update=True)
        trajectory.append((feats, mover))
        engine.execute_turn(choose(engine, turns, weights, extractor, rng,
                                   epsilon, scales))
        plies += 1

    winner = engine.winner
    # Walk BACKWARD so a corrected later estimate informs the earlier
    # one within the same pass, which is what makes credit travel.
    following = None
    updates = 0
    for index in range(len(trajectory) - 1, -1, -1):
        feats, mover = trajectory[index]
        if following is None:
            # The last recorded state: anchor on the real outcome if the
            # game finished, and skip it entirely if it was cut off --
            # a censored game has no result to teach (#260).
            if winner is None:
                following = None
                continue
            target = 1.0 if winner == mover else 0.0
        else:
            next_feats, next_mover = trajectory[index + 1]
            next_value = value(weights, next_feats)
            # Perspectives alternate, so flip when the mover changed.
            target = (next_value if next_mover == mover
                      else 1.0 - next_value)
        prediction = value(weights, feats)
        error = target - prediction
        for name, amount in feats.items():
            weights[name] = weights.get(name, 0.0) + alpha * error * amount
        updates += 1
        following = index
    return updates


def run(make_engine, extractor, rounds=6, games_per_round=20,
        variant='full', max_turns=400, alpha=0.05, epsilon=0.15,
        seed=0, evaluate_round=None, progress=None, scales=None):
    """Rounds of TD self-play from ZERO weights.

    `evaluate_round(weights)` may return a score to record per round --
    on a solvable game that is the optimal-action rate against exact
    play, which is the only honest measure of whether learning worked.
    """
    rng = random.Random(seed)
    weights = {}
    if scales is None:
        scales = {}
    # AVERAGED WEIGHTS, and this is the stabiliser that matters. TD with
    # linear function approximation oscillates: measured on m,n,k the
    # validated score swung between 88.9% and 65.1% across rounds, and
    # on Royal Chess round 1 drove `King*royal` to -0.676, which cannot
    # be right since losing your king is half the loss condition.
    #
    # Averaging the iterates is the textbook answer and, crucially, it
    # needs NO validation signal -- which is the whole problem on the
    # case study, where there is nothing to early-stop on. The averaged
    # vector is what gets reported and played; the live vector keeps
    # learning.
    averaged = {}
    average_count = 0
    history = []
    for index in range(rounds):
        # DECAYED, because a constant step keeps overshooting once the
        # estimate is roughly right. Measured without it: the validated
        # score oscillated between 88.9% and 65.1% across rounds, which
        # is the divergence mode this module's docstring warns about,
        # not noise -- the standard error at that sample is under 3
        # points.
        step = alpha / (1.0 + 0.5 * index)
        spread = epsilon / (1.0 + 0.3 * index)
        for _game in range(games_per_round):
            play_and_learn(make_engine, extractor, weights, rng,
                           variant=variant, max_turns=max_turns,
                           alpha=step, epsilon=spread, scales=scales)
        average_count += 1
        for name, w in weights.items():
            previous = averaged.get(name, 0.0)
            averaged[name] = previous + (w - previous) / average_count
        score = (evaluate_round(dict(averaged))
                 if evaluate_round is not None else float('nan'))
        record = Snapshot(round=index, games=(index + 1) * games_per_round,
                          weights=dict(averaged), score=score)
        history.append(record)
        if progress is not None:
            progress(record)
    return history


def report(history, label=''):
    lines = [
        'TD BOOTSTRAPPING FROM ZERO WEIGHTS{}'.format(
            (' -- ' + label) if label else ''),
        '',
        'Weights start at exactly zero, so the evaluation is a flat 0.5',
        'and no feature is preferred. The only label is the outcome at',
        'terminal states; every gradient below was derived from it by',
        'fitting each position toward the one that follows it.',
        '',
        'Nothing here assumed that material matters, that mobility',
        'matters, or that two royals beat one. A termination condition',
        'separates 0 from n and says nothing about n versus n+1, so a',
        'proximity gradient cannot be read off the rules -- it has to be',
        'learned, which is what these numbers are.',
        '',
        '{:>6} {:>8} {:>10}  {}'.format('round', 'games', 'score',
                                        'strongest weights'),
    ]
    for record in history:
        top = sorted(record.weights.items(), key=lambda kv: -abs(kv[1]))[:4]
        shown = ', '.join('{}={:+.2f}'.format(name, w) for name, w in top)
        lines.append('{:>6} {:>8} {:>10}  {}'.format(
            record.round, record.games,
            ('{:.1%}'.format(record.score)
             if record.score == record.score else '--'),
            shown))
    return '\n'.join(lines)


def best(history):
    """The highest-scoring round's weights.

    EARLY STOPPING ON A VALIDATION SIGNAL, which is legitimate where one
    exists -- on a solvable game the score is the optimal-action rate
    against exact play, measured on positions the learner did not train
    on. Where no such signal exists, as on the case study, there is
    nothing to stop on and the final round is all you have; that is a
    real limitation and not something to paper over by picking the round
    whose weights look nicest.
    """
    scored = [r for r in history if r.score == r.score]
    if not scored:
        return history[-1].weights if history else {}
    return max(scored, key=lambda r: r.score).weights


class TDPlayer:
    """Plays one-ply greedy on a learned value, for human testing.

    Everything it knows was derived from terminal outcomes by TD: the
    weights started at zero and no feature, sign or magnitude was
    supplied. Terminal positions are read rather than estimated.
    """

    def __init__(self, weights, scales, extractor, epsilon=0.0, rng=None):
        self.weights = dict(weights)
        self.scales = dict(scales)
        self.extractor = extractor
        self.epsilon = epsilon
        self.rng = rng or random.Random()

    def choose_turn(self, turns, engine=None):
        if engine is None or not turns:
            return turns[0] if turns else None
        return choose(engine, turns, self.weights, self.extractor,
                      self.rng, self.epsilon, self.scales)


def load_player(path, extractor, epsilon=0.0, rng=None):
    """A `TDPlayer` from weights saved by a training run."""
    import json

    with open(path) as handle:
        payload = json.load(handle)
    return TDPlayer(payload['weights'], payload.get('scales', {}),
                    extractor, epsilon=epsilon, rng=rng)
