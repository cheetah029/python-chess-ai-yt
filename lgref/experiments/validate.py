"""Does a discovered evaluation actually PLAY well? Checked against exact
play, on games small enough to solve.

WHY THIS IS THE MISSING PIECE. Every claim about a discovered evaluation
so far rested on how strongly its features correlated with winning --
Cohen's d, AUC, a z score. None of that is the quantity of interest. A
feature can be strongly predictive while the ARGMAX of the score it
builds is a bad move, because a correlation measured over whole games
says nothing about which of two sibling positions is better. The only
honest test of an evaluation is the quality of the policy it induces,
and on a solvable game that can be measured exactly rather than
estimated.

So this module answers "is the inference accurate?" with ground truth
instead of a significance level. It is also fast: a 4x4 board resolves
in seconds, where the same question on the case study needs hours and
still cannot be checked against truth.

GAME-INDEPENDENT BY CONSTRUCTION. It needs a game exposing the protocol
the rest of the project uses (`get_all_legal_turns`, `execute_turn`,
`is_game_over`, `winner`, `current_player`, `copy`) and an `optimal`
function returning the value-preserving moves. Nothing here knows what
any game contains.

THREE WAYS THIS MEASUREMENT WENT WRONG BEFORE IT WENT RIGHT, all caught
by the uniform control and all recorded because each produced a
confident, wrong, publishable-looking number:

  THE SOLVER RETURNS A PAIR.  `mnk.optimal_moves` returns
      `(best_set, value)`. Treating it as the set made `pick in best`
      true only when a move index happened to equal the exact value
      (-1, 0 or 1), pinning every policy at about 6% and making the
      learned evaluation look WORSE THAN RANDOM. The weighting
      experiments that followed all returned ~6% regardless of their
      weights, which is the signature of a broken comparison rather
      than a weak evaluation.

  TIES WERE BROKEN BY LIST ORDER.  `max()` returns the first maximum, so
      a score with many ties collapses to "lowest cell index" -- a fixed
      positional bias that a uniform baseline does not share. Ties are
      now broken uniformly at random.

  THE CONTROL IS NOT OPTIONAL.  A uniform random policy must score the
      chance baseline, by definition. When it did not -- 6.1% against a
      15.7% baseline -- that was proof the harness was broken, not that
      random play is bad. Any run whose control misses its baseline
      should be discarded, so `report` prints them side by side.
"""

import collections

Accuracy = collections.namedtuple('Accuracy', 'rate chance n label')


def optimal_action_rate(make_game, optimal, policy, trials=400, seed=0,
                        max_setup=6, label=''):
    """How often `policy` picks a value-preserving move.

    Positions are reached by random play, then filtered: a position
    where EVERY move is optimal measures nothing, because any policy
    scores 100% on it. `chance` is the share of optimal moves averaged
    over the positions actually scored, which is exactly what a uniform
    policy achieves -- so it doubles as the control's expected value.
    """
    import random

    rng = random.Random(seed)
    hit = total = 0
    chance = 0.0
    for _ in range(trials):
        game = make_game()
        for _ in range(rng.randint(0, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if len(turns) < 2:
            continue
        best, _value = optimal(game)
        if not best or len(best) == len(turns):
            continue                   # no decision to get right
        total += 1
        chance += len(best) / float(len(turns))
        if policy(game, rng) in best:
            hit += 1
    if not total:
        return Accuracy(rate=float('nan'), chance=float('nan'), n=0,
                        label=label)
    return Accuracy(rate=hit / float(total), chance=chance / float(total),
                    n=total, label=label)


def evaluator_policy(evaluate):
    """A policy that plays the argmax of `evaluate`, one ply.

    TERMINAL STATES USE THE TRUE OUTCOME, because a learned estimate of
    a decided position is strictly worse than the decision -- and
    because a feature set sampled from non-terminal states can be blind
    to winning outright. Measured: completing a line converts a
    `Line:k-1` feature into `Line:k`, which never appears in traces
    sampled before the final move, so the learned score of a winning
    move equalled that of a quiet one exactly.

    TIES BREAK UNIFORMLY, for the reason in the module docstring.
    """
    def policy(game, rng):
        turns = game.get_all_legal_turns()
        mover = game.current_player
        scores = []
        for turn in turns:
            nxt = game.copy()
            nxt.execute_turn(turn)
            if nxt.is_game_over():
                if nxt.winner == mover:
                    scores.append(float('inf'))
                elif nxt.winner is None:
                    scores.append(0.5)
                else:
                    scores.append(float('-inf'))
            else:
                scores.append(evaluate(nxt, mover))
            continue
        top = max(scores)
        tied = [turn for turn, score in zip(turns, scores)
                if score >= top - 1e-12]
        return rng.choice(tied)
    return policy


def uniform_policy(game, rng):
    """The control. It must score the chance baseline, or the harness is
    wrong -- which is how three separate harness defects were found."""
    return rng.choice(game.get_all_legal_turns())


def report(results):
    lines = [
        'OPTIMAL-ACTION RATE AGAINST EXACT PLAY',
        '',
        'The question is not whether a feature correlates with winning.',
        'It is whether the evaluation built from it CHOOSES well, which',
        'is measurable exactly on a solvable game and is the only test',
        'that bears on playing strength.',
        '',
        'The uniform control must land on the chance baseline. If it',
        'does not, the harness is broken and every other row in the',
        'table is meaningless -- which has happened three times.',
        '',
        '{:<42} {:>9} {:>9} {:>7} {:>7}'.format(
            'policy', 'optimal', 'chance', 'ratio', 'n'),
    ]
    for item in results:
        ratio = (item.rate / item.chance) if item.chance else float('nan')
        lines.append('{:<42} {:>8.1%} {:>9.1%} {:>7.2f} {:>7}'.format(
            item.label, item.rate, item.chance, ratio, item.n))
    return '\n'.join(lines)
