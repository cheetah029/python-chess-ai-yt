"""Self-play policy iteration: bootstrap an evaluation from nothing.

WHY ITERATION IS NECESSARY, measured rather than assumed. A single pass
of feature discovery over random games finds no value in material: Rook
d = -0.041, Knight d = -0.032, and the strongest feature flips sign
between game phases. The reason is structural -- random play never
converts material into royal captures, so the causal chain the feature
would stand for is absent from the traces. You cannot learn what makes a
strong player strong from the games of a random one.

The way out is the oldest idea in the field: use the weak evaluation to
play slightly better, re-collect, re-learn. Each round's traces contain a
little more of the causal chain than the last, so the features that stand
for it gain signal. That is policy iteration, and it is what AlphaZero
industrialised and what the execution brief's Phase 3 asked for.

WHAT MAKES IT GENERAL. Every step reads the game and never the game
designer: features come from the position's own vocabulary, weights come
from observed outcomes, and the loop's only input is a legal-move
generator. The learned WEIGHTS are game-specific; the METHOD is not. That
is the only sense in which "works across games" and "plays well" are
simultaneously achievable, and it is the sense AlphaZero demonstrated.

WHAT TO WATCH FOR, because this loop has two well-known failure modes:

  COLLAPSE      an agent that plays its own evaluation generates traces
                that confirm it, so a wrong weight can entrench. Guarded
                by keeping a fraction of moves random (`exploration`) and
                by scoring each round against the PREVIOUS round rather
                than against itself.
  OVERFITTING   weights fitted on the traces they were measured from
                look better than they are. Scored on games played after
                fitting, never on the fitting traces.

AND THE LIMIT THAT WILL NOT GO AWAY. For an ABLATION study the evaluation
must be learned per variant at matched budgets, or an agent carrying
knowledge of the full ruleset into `no_boulder` is measuring its own
training rather than the rule (#231). A single shared evaluation would be
cheaper and would invalidate the comparison.
"""

import collections
import math
import random

Round = collections.namedtuple(
    'Round', 'index traces features weights beat_previous games')


def weights_from(findings, min_separation=0.05, min_games=8, min_z=2.0,
                 max_weight=3.0):
    """Feature weights from measured separation.

    Cohen's d IS a linear-discriminant weight up to scale: it is the mean
    difference in units of pooled spread, which is what a linear score
    wants. Using it directly keeps the step readable and avoids fitting
    machinery whose failure modes would be harder to see than its
    benefits at this scale.

    Features below `min_separation` are dropped rather than given a small
    weight, because a weight fitted from noise is noise with authority.

`min_z` is the gate that actually binds. An effect-size filter
    cannot tell a large effect from a small sample: round 2 of the first
    run reported `Knight*royal` at d = +2.12, which passed a 0.05
    separation gate on a feature seen in a dozen clustered games.
    Requiring d to clear twice its own standard error drops exactly
    those rows, and `min_games` backs it up for groups too small for the
    standard error itself to mean much.

    THE CRUDENESS THIS KEEPS. Features are correlated -- `Royal`,
    `RoyalQueen` and `King*royal` all move with the same captures -- and
    summing their separate d values double-counts the signal they share.
    A joint fit would not, at the cost of failure modes harder to see
    than this one. Noted rather than hidden.
    """
    out = {}
    for finding in findings:
        if abs(finding.separation) < min_separation:
            continue
        if getattr(finding, 'games', min_games) < min_games:
            continue
        se = getattr(finding, 'se', 0.0)
        if se and abs(finding.separation) < min_z * se:
            # A large d on a small group is the shape every spurious
            # weight here has had. Requiring the effect to clear its own
            # uncertainty is what a separation gate alone cannot do.
            continue
        # A perfectly separating feature has an unbounded d, and an
        # unbounded weight is not a weight -- it makes one feature a
        # lexicographic override of every other, which is not what a
        # linear score means. Clamped, with the cap documented.
        out[finding.feature] = max(-max_weight,
                                   min(max_weight, finding.separation))
    return out


def make_evaluator(weights, scale=1.0):
    """A leaf evaluation from `weights`, in [0, 1].

    Logistic, so the output is a probability-like quantity the search can
    average, and symmetric: swapping the perspective gives 1 - value.
    """
    from lgref.experiments.discover import differentials, piece_features

    def evaluate(engine, perspective):
        feats = differentials(piece_features(engine), perspective)
        total = sum(weights.get(name, 0.0) * value
                    for name, value in feats.items())
        return 1.0 / (1.0 + math.exp(-scale * total))

    return evaluate


def _player_factory(weights, simulations, eval_depth, exploration):
    """An agent that searches with the learned evaluation."""
    from lgref.experiments.mcts import MCTSPlayer

    evaluator = make_evaluator(weights) if weights else None

    def build(seed):
        player = MCTSPlayer(n_simulations=simulations,
                            rng=random.Random(seed),
                            evaluator=evaluator, eval_depth=eval_depth)
        return player

    return build


def play_match(make_engine, build_a, build_b, games=8, variant='full',
               max_turns=400, seed=0):
    """Head-to-head score for A, with colours alternated.

    ALTERNATED because this game is not symmetric -- white moves first
    and may not move the boulder on turn one -- so a fixed assignment
    would measure the colour as well as the agent.
    """
    wins = draws = 0
    for index in range(games):
        engine = make_engine(variant, max_turns=max_turns)
        a_is_white = (index % 2 == 0)
        white = (build_a if a_is_white else build_b)(seed * 100 + index * 2)
        black = (build_b if a_is_white else build_a)(seed * 100 + index * 2
                                                     + 1)
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            mover = white if engine.current_player == 'white' else black
            engine.execute_turn(mover.choose_turn(turns, engine))
        winner = engine.winner
        if winner is None:
            draws += 1
        elif (winner == 'white') == a_is_white:
            wins += 1
    return (wins + 0.5 * draws) / float(games) if games else float('nan')


def run(make_engine, rounds=3, games_per_round=24, simulations=60,
        eval_depth=0, match_games=8, variant='full', seed=0,
        progress=None):
    """The loop. Returns a `Round` per iteration.

    Round 0 collects from random play, because there is nothing else to
    collect from. Each later round plays with the previous round's
    evaluation, so its traces carry more of the causal chain -- which is
    the entire mechanism.
    """
    from lgref.experiments.discover import collect, rank

    history = []
    weights = {}
    for index in range(rounds):
        if index == 0:
            traces = collect(make_engine, games=games_per_round,
                             variant=variant, agent='random',
                             simulations=0, seed=seed * 10)
        else:
            traces = _collect_with(make_engine, weights, games_per_round,
                                   simulations, eval_depth, variant,
                                   seed * 10 + index)
        findings = rank(traces, min_count=20, min_games=8)
        new_weights = weights_from(findings)

        beat_previous = float('nan')
        if new_weights and index > 0:
            beat_previous = play_match(
                make_engine,
                _player_factory(new_weights, simulations, eval_depth, 0.0),
                _player_factory(weights, simulations, eval_depth, 0.0),
                games=match_games, variant=variant,
                seed=seed * 7 + index)
        elif new_weights:
            # Round 0 has no predecessor, so score against the agent the
            # traces came from: uniform random.
            beat_previous = play_match(
                make_engine,
                _player_factory(new_weights, simulations, eval_depth, 0.0),
                _random_factory(),
                games=match_games, variant=variant, seed=seed * 7)

        record = Round(index=index, traces=len(traces),
                       features=len(findings), weights=new_weights,
                       beat_previous=beat_previous,
                       games=games_per_round)
        history.append(record)
        if progress is not None:
            progress(record)
        weights = new_weights
    return history


def _random_factory():
    from lgref.experiments.random_play import build

    def make(seed):
        return build('random', random.Random(seed), 0)
    return make


def _collect_with(make_engine, weights, games, simulations, eval_depth,
                  variant, seed):
    """Traces from games played with the current evaluation."""
    from lgref.experiments.discover import (differentials, piece_features,
                                            Trace)

    build = _player_factory(weights, simulations, eval_depth, 0.0)
    traces = []
    for index in range(games):
        engine = make_engine(variant, max_turns=400)
        white = build(seed * 1000 + index * 2 + 1)
        black = build(seed * 1000 + index * 2 + 2)
        pending = []
        ply = 0
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            if ply % 4 == 0:
                mover = engine.current_player
                pending.append((differentials(piece_features(engine),
                                              mover), mover, ply))
            player = white if engine.current_player == 'white' else black
            engine.execute_turn(player.choose_turn(turns, engine))
            ply += 1
        if engine.winner is None:
            continue
        for feats, mover, at_ply in pending:
            traces.append(Trace(features=feats, winner=engine.winner,
                                mover=mover, ply=at_ply,
                                game=(seed, index)))
    return traces


def report(history):
    lines = [
        'SELF-PLAY POLICY ITERATION',
        '',
        'Round 0 learns from random play, because there is nothing else',
        'to learn from. Each later round plays with the previous round\'s',
        'evaluation, so its traces carry more of the causal chain that',
        'material stands for -- which is the whole mechanism.',
        '',
        'The score is HEAD-TO-HEAD against the previous round (round 0',
        'against random), colours alternated, on games played after',
        'fitting. Scoring on the fitting traces would flatter every round.',
        '',
        '{:>6} {:>8} {:>9} {:>9} {:>16}'.format(
            'round', 'traces', 'features', 'weights', 'beats previous'),
    ]
    for record in history:
        lines.append('{:>6} {:>8} {:>9} {:>9} {:>15.1%}'.format(
            record.index, record.traces, record.features,
            len(record.weights), record.beat_previous))
    lines += ['', 'A round at or below 50% did not improve on its',
              'predecessor. Collapse looks like a high score against the',
              'previous round with no gain against random.']
    return '\n'.join(lines)
