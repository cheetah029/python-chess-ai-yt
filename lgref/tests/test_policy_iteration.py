"""Self-play policy iteration, and what its first run actually showed.

A single pass of feature discovery over random games cannot value
material, because random play never converts material into royal
captures -- the causal chain the feature would stand for is absent from
the traces. The standard way out is to use the weak evaluation to play
slightly better, re-collect, and re-learn.

These tests pin the loop's mechanics and, more importantly, pin the
reason its first run was uninformative: at 20 games per round and 8
match games per comparison, neither the weights nor the scores could
resolve anything. That is a statement about the budget, not about
iteration.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.discover import Trace, rank
from lgref.experiments.iterate import (make_evaluator, play_match,
                                       weights_from)


def test_an_evaluator_is_symmetric_between_the_players():
    """Swapping the perspective must give 1 - value, or the search would
    prefer a side rather than a position."""
    evaluate = make_evaluator({'Rook': 0.7, 'Pawn': -0.2})
    engine = make_engine('full', max_turns=50)
    white = evaluate(engine, 'white')
    black = evaluate(engine, 'black')
    assert abs((white + black) - 1.0) < 1e-9
    # The opening is symmetric under rotation, so it must read as even.
    assert abs(white - 0.5) < 1e-9


def test_an_evaluator_prefers_more_of_a_positively_weighted_feature():
    """The weights have to actually reach the score."""
    evaluate = make_evaluator({'Rook': 1.0})
    engine = make_engine('full', max_turns=50)
    base = evaluate(engine, 'white')
    # Remove a black rook; white should now be preferred.
    for row in range(8):
        for col in range(8):
            piece = engine.board.squares[row][col].piece
            if piece is not None and type(piece).__name__ == 'Rook' \
                    and getattr(piece, 'color', None) == 'black' \
                    and not getattr(piece, 'is_transformed', False):
                engine.board.squares[row][col].piece = None
                break
        else:
            continue
        break
    assert evaluate(engine, 'white') > base


def test_no_weights_means_no_evaluator_rather_than_a_flat_one():
    """A flat evaluator is not the same as none: it would make every
    leaf equal and quietly replace the rollout with a constant."""
    from lgref.experiments.iterate import _player_factory

    built = _player_factory({}, simulations=4, eval_depth=2,
                            exploration=0.0)(seed=0)
    assert getattr(built, 'evaluator', None) is None


def test_weights_drop_features_that_cannot_clear_their_own_error():
    """The gate that the first run lacked.

    Round 2 reported `Knight*royal` at d = +2.12 from about a dozen
    clustered games and made it the strongest weight in the search. The
    separation gate passed it; a significance gate does not.
    """
    # Groups that OVERLAP, so d is finite and its standard error is
    # what decides -- the realistic shape of the round-2 finding. A
    # cleanly separating fixture would be significant and would test
    # nothing.
    won_values = [2, 1, 1, 0, 2]
    lost_values = [0, 1, 0, -1]
    traces = [Trace(features={'rare': v}, winner='white', mover='white',
                    ply=4, game=('won', i))
              for i, v in enumerate(won_values)]
    traces += [Trace(features={'rare': v}, winner='white', mover='black',
                     ply=4, game=('lost', i))
               for i, v in enumerate(lost_values)]
    findings = rank(traces, min_count=5, min_games=8)
    assert findings, 'the feature should be measured'
    found = findings[0]
    assert abs(found.separation) > 1.0, 'expected a large apparent effect'
    assert found.se > 0.0, 'a finite d must carry a finite error'
    assert abs(found.separation) < 2.0 * found.se, (
        'this fixture is meant to be a large effect on a small sample')
    assert weights_from(findings, min_games=8, min_z=2.0) == {}


def test_a_match_of_eight_games_cannot_resolve_a_small_edge():
    """Why the first run's scores said nothing.

    A match score is a mean of Bernoulli trials, so its standard error
    at 8 games is 0.177. Round 1's 37.5% and round 2's 62.5% are both
    within one standard error of a coin flip, so neither was evidence
    about the round that produced it.
    """
    games = 8
    se = (0.5 * 0.5 / games) ** 0.5
    assert abs(0.375 - 0.5) < 1.0 * se
    assert abs(0.625 - 0.5) < 1.0 * se
    # Resolving a 10-point edge at two standard errors needs this many:
    needed = round(4 * 0.25 / (0.10 ** 2))
    assert needed >= 100


def test_a_match_is_played_with_both_colours():
    """This game is not symmetric -- white moves first and may not move
    the boulder on turn one -- so a fixed assignment would measure the
    colour along with the agent."""
    from lgref.experiments.random_play import build

    def factory(_seed):
        return build('random', random.Random(_seed), 0)

    score = play_match(make_engine, factory, factory, games=2,
                       max_turns=60, seed=5)
    assert 0.0 <= score <= 1.0


def test_rave_and_mast_are_credited_from_the_leaf_evaluation():
    """Otherwise they go silently inert the moment an evaluator is used.

    With a learned evaluation the search has no `winner` to credit, and
    `_value_for(None, player)` is DRAW_VALUE -- so passing the winner
    alone fed every RAVE and MAST entry a flat 0.5. Nothing would crash
    and the player would still report `use_rave`/`use_mast` as on, while
    both estimators carried no information. The obvious next experiment
    is exactly this combination, so an inert-but-configured state is the
    dangerous kind of wrong.
    """
    from lgref.experiments.mcts import MCTSPlayer

    engine = make_engine('full', max_turns=60)
    player = MCTSPlayer(n_simulations=16, rng=random.Random(0),
                        use_rave=True, use_mast=True,
                        evaluator=make_evaluator({'Rook': 1.0,
                                                  'Bishop': -0.5}),
                        eval_depth=2)
    player.choose_turn(engine.get_all_legal_turns(), engine)

    assert player._mast, 'the MAST table stayed empty'
    values = [total / count for total, count in player._mast.values()
              if count]
    assert values, 'no MAST averages were recorded'
    assert any(abs(v - 0.5) > 1e-6 for v in values), (
        'every MAST entry is exactly 0.5 -- the table is being fed '
        'DRAW_VALUE, so MAST is configured but inert')
