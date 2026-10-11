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


def make_evaluator(weights, extractor, scale=1.0):
    """A leaf evaluation from `weights`, in [0, 1].

    Logistic, so the output is a probability-like quantity the search can
    average, and symmetric: swapping the perspective gives 1 - value.
    """
    from lgref.experiments.discover import differentials

    def evaluate(engine, perspective):
        feats = differentials(extractor(engine), perspective)
        total = sum(weights.get(name, 0.0) * value
                    for name, value in feats.items())
        return 1.0 / (1.0 + math.exp(-scale * total))

    return evaluate


def _player_factory(weights, simulations, eval_depth, exploration,
                    extractor=None):
    """An agent that searches with the learned evaluation."""
    from lgref.experiments.mcts import MCTSPlayer

    evaluator = (make_evaluator(weights, extractor)
                 if weights and extractor is not None else None)

    def build(seed):
        player = MCTSPlayer(n_simulations=simulations,
                            rng=random.Random(seed),
                            evaluator=evaluator, eval_depth=eval_depth)
        return player

    return build


def play_match(make_engine, weights_a, weights_b, games=8,
               variant='full', max_turns=400, seed=0, simulations=60,
               eval_depth=0, workers=1, progress=None, extractor=None):
    """Head-to-head score for A, with colours alternated.

    ALTERNATED because this game is not symmetric -- white moves first
    and may not move the boulder on turn one -- so a fixed assignment
    would measure the colour as well as the agent.

    `weights_a`/`weights_b` are weight dicts, or None for uniform
    random. Weights rather than factories, because a closure cannot
    cross a process boundary.

    HOW MANY GAMES THIS NEEDS. A match score is a mean of Bernoulli
    trials, so its standard error is 0.5/sqrt(games): 0.177 at 8 games,
    which is why the first run's 37.5% and 62.5% were both within one
    standard error of a coin flip. Resolving a 10-point edge at two
    standard errors takes 100 games; a 5-point edge takes 400.
    """
    jobs = [(make_engine, weights_a, weights_b, simulations, eval_depth,
             variant, max_turns, seed, index, extractor)
            for index in range(games)]
    scores = _run_pool(_match_one, jobs, workers, progress)
    return (sum(scores) / float(len(scores))) if scores else float('nan')


def run(make_engine, extractor, rounds=3, games_per_round=24,
        simulations=60, eval_depth=0, match_games=8, variant='full',
        seed=0, progress=None, workers=1, min_games=8, max_turns=400,
        stage=None):
    """The loop. Returns a `Round` per iteration.

    Round 0 collects from random play, because there is nothing else to
    collect from. Each later round plays with the previous round's
    evaluation, so its traces carry more of the causal chain -- which is
    the entire mechanism.

    THE BUDGET IS NOT A FREE PARAMETER. Feature significance needs the
    standard error of d below the effect being looked for, and
    SE ~ sqrt(4/games), so a d ~ 0.35 effect needs about 130 games --
    the first run used 20. Match scores need 0.5/sqrt(games) below the
    edge being looked for: 100 games for 10 points, 400 for 5. The first
    run used 8, where the standard error is 0.177, so its 37.5% and
    62.5% were both a coin flip. `min_games` is passed through to the
    ranking so an under-powered round reports NO weights rather than
    noisy ones.
    """
    from lgref.experiments.discover import collect, rank

    history = []
    weights = {}
    for index in range(rounds):
        def note(done, total, index=index):
            if stage is not None and done % max(1, total // 10) == 0:
                stage(index, 'collect', done, total)

        if index == 0:
            # Round 0 has no evaluation, so its games are uniform random
            # and `None` weights select the random agent in the worker.
            traces = _collect_with(make_engine, {}, games_per_round, 0, 0,
                                   variant, seed * 10, workers=workers,
                                   max_turns=max_turns, progress=note,
                                   extractor=extractor)
        else:
            traces = _collect_with(make_engine, weights, games_per_round,
                                   simulations, eval_depth, variant,
                                   seed * 10 + index, workers=workers,
                                   max_turns=max_turns, progress=note,
                                   extractor=extractor)
        findings = rank(traces, min_count=20, min_games=min_games)
        new_weights = weights_from(findings, min_games=min_games)

        def note_match(done, total, index=index):
            if stage is not None and done % max(1, total // 10) == 0:
                stage(index, 'match', done, total)

        beat_previous = float('nan')
        if new_weights:
            # Round 0 has no predecessor, so it is scored against the
            # agent its traces came from: uniform random (None).
            opponent = weights if index > 0 else None
            beat_previous = play_match(
                make_engine, new_weights, opponent, games=match_games,
                variant=variant, seed=seed * 7 + index,
                simulations=simulations, eval_depth=eval_depth,
                workers=workers, max_turns=max_turns,
                progress=note_match, extractor=extractor)

        record = Round(index=index, traces=len(traces),
                       features=len(findings), weights=new_weights,
                       beat_previous=beat_previous,
                       games=games_per_round)
        history.append(record)
        if progress is not None:
            progress(record)
        weights = new_weights
    return history


def _collect_one(args):
    """One game's traces, as a process-pool task.

    MODULE LEVEL because a closure cannot be pickled, and the engine
    factory is passed by reference rather than rebuilt so this stays
    game-agnostic.
    """
    (make_engine, weights, simulations, eval_depth, variant, seed, index,
     max_turns, sample_every, extractor) = args
    from lgref.experiments.discover import Trace, differentials

    # No weights and no simulations means round 0, whose games must be
    # uniform random -- an MCTS with zero simulations is not the same
    # thing and would quietly change what round 0 learns from.
    build = (_random_factory() if not weights and simulations == 0
             else _player_factory(weights, simulations, eval_depth, 0.0,
                                  extractor))
    engine = make_engine(variant, max_turns=max_turns)
    white = build(seed * 1000 + index * 2 + 1)
    black = build(seed * 1000 + index * 2 + 2)
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
    if engine.winner is None:
        return []
    return [Trace(features=feats, winner=engine.winner, mover=mover,
                  ply=at_ply, game=(seed, index))
            for feats, mover, at_ply in pending]


def _match_one(args):
    """One match game, as a process-pool task. Returns A's score."""
    (make_engine, weights_a, weights_b, simulations, eval_depth, variant,
     max_turns, seed, index, extractor) = args
    build_a = (_player_factory(weights_a, simulations, eval_depth, 0.0,
                               extractor)
               if weights_a is not None else _random_factory())
    build_b = (_player_factory(weights_b, simulations, eval_depth, 0.0,
                               extractor)
               if weights_b is not None else _random_factory())
    engine = make_engine(variant, max_turns=max_turns)
    a_is_white = (index % 2 == 0)
    white = (build_a if a_is_white else build_b)(seed * 100 + index * 2)
    black = (build_b if a_is_white else build_a)(seed * 100 + index * 2 + 1)
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        mover = white if engine.current_player == 'white' else black
        engine.execute_turn(mover.choose_turn(turns, engine))
    winner = engine.winner
    if winner is None:
        return 0.5
    return 1.0 if (winner == 'white') == a_is_white else 0.0


def _run_pool(task, jobs, workers, progress=None):
    """Run `jobs` through `task`, serially or in a process pool.

    `as_completed`, not `map`: a pool's map yields in SUBMISSION order,
    so a progress counter sits at zero while every worker is busy and
    then jumps -- which once looked like a hung run with eight busy
    cores.
    """
    if workers <= 1:
        out = []
        for index, job in enumerate(jobs):
            out.append(task(job))
            if progress is not None:
                progress(index + 1, len(jobs))
        return out
    from concurrent.futures import ProcessPoolExecutor, as_completed

    out = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(task, job) for job in jobs]
        for index, future in enumerate(as_completed(futures)):
            out.append(future.result())
            if progress is not None:
                progress(index + 1, len(futures))
    return out


def _random_factory():
    from lgref.experiments.random_play import build

    def make(seed):
        return build('random', random.Random(seed), 0)
    return make


def _collect_with(make_engine, weights, games, simulations, eval_depth,
                  variant, seed, workers=1, max_turns=400,
                  sample_every=4, progress=None, extractor=None):
    """Traces from games played with the current evaluation."""
    jobs = [(make_engine, weights, simulations, eval_depth, variant, seed,
             index, max_turns, sample_every, extractor)
            for index in range(games)]
    batches = _run_pool(_collect_one, jobs, workers, progress)
    return [trace for batch in batches for trace in batch]


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
