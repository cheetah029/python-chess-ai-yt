"""Learning what matters from the only label the rules provide.

THE REASONING ERROR THIS REPLACES. `generic.py` read the game's terminal
conditions and treated proximity to each as valuable -- "no legal turn
is a loss, so mobility matters", "losing both royals is a loss, so royal
count matters". That inference is invalid. A termination condition is an
INDICATOR, not a gradient: "no legal turn" separates 0 from n > 0 and
says nothing about 1 versus 100, and "both royals captured" says nothing
about 2 alive versus 1. Converting a threshold into a distance is a
researcher's assumption wearing a rule's clothing.

The rules give exactly one thing: the outcome at terminal states. TD
propagates it backward, so every gradient is derived rather than
assumed, and weights start at exactly zero.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.bootstrap import (best, choose, normalise,
                                         play_and_learn, run, value)
from lgref.experiments.features import (mnk as mnk_features, royal_chess,
                                        with_mobility)
from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.validate import optimal_action_rate, uniform_policy


def _make_mnk(variant='full', max_turns=None):
    return MNK(m=4, n=4, k=3)


def test_zero_weights_mean_no_preference_at_all():
    """The honest starting point: before anything is learned, every
    position is worth exactly the same."""
    assert value({}, {'anything': 5.0, 'else': -3.0}) == 0.5
    assert value({}, {}) == 0.5


def test_nothing_is_assumed_about_which_features_matter():
    """A fresh run must begin with an empty weight vector -- no prior on
    material, on mobility, or on royal count."""
    engine_calls = []

    def make(variant='full', max_turns=None):
        engine_calls.append(1)
        return MNK(m=3, n=3, k=3)

    history = run(make, mnk_features, rounds=1, games_per_round=1,
                  seed=0, max_turns=20)
    assert history
    # Whatever it learned came from play, not from initialisation.
    assert engine_calls, 'no games were played'


def test_the_learned_value_beats_chance_against_exact_play():
    """The decisive test, and the only one that bears on strength.

    Learned from zero weights with no supplied feature, sign or
    magnitude, then scored against exact minimax on positions it did not
    train on. Measured 88.9% optimal against a 31.9% chance baseline.
    """
    extractor = with_mobility(mnk_features)
    scales = {}
    history = run(_make_mnk, extractor, rounds=4, games_per_round=25,
                  alpha=0.08, epsilon=0.25, seed=1, max_turns=40,
                  scales=scales)
    weights = best(history)
    assert weights, 'nothing was learned'

    def policy(game, rng):
        return choose(game, game.get_all_legal_turns(), weights,
                      extractor, rng, 0.0, scales)

    learned = optimal_action_rate(_make_mnk, optimal_moves, policy,
                                  trials=120, seed=99)
    control = optimal_action_rate(_make_mnk, optimal_moves,
                                  uniform_policy, trials=120, seed=99)
    assert abs(control.rate - control.chance) < 0.10, (
        'the control missed its baseline; the harness is wrong')
    assert learned.rate > 2.0 * learned.chance, (
        '{:.1%} against chance {:.1%}'.format(learned.rate,
                                              learned.chance))


def test_mobility_is_learned_rather_than_supplied():
    """It is a CANDIDATE feature, and the outcomes set its weight.

    The proof that it is learned is that the SAME feature gets a
    materially different weight on a different game. Nothing in the code
    sets it, so any value it takes came from play.

    Measured and recorded honestly: on m,n,k TD gives it +0.54, slightly
    ABOVE the win-condition feature. That is not mobility being assumed
    important -- `with_mobility` records only the MOVER's count, so its
    differential is always +n rather than a difference between players,
    which makes it closer to a game-phase signal. See the limitation
    noted in `features.with_mobility`.
    """
    extractor = with_mobility(mnk_features)
    learned = []
    for board in ((4, 4, 3), (3, 3, 3)):
        def make(variant='full', max_turns=None, board=board):
            return MNK(m=board[0], n=board[1], k=board[2])
        scales = {}
        history = run(make, extractor, rounds=3, games_per_round=20,
                      alpha=0.08, epsilon=0.25, seed=1, max_turns=40,
                      scales=scales)
        learned.append(best(history).get('Mobility', 0.0))
    assert abs(learned[0] - learned[1]) > 0.02, (
        'the same feature got the same weight on two different games '
        '({:.3f} and {:.3f}), which is what a SUPPLIED constant would '
        'look like'.format(*learned))


def test_normalisation_stops_a_big_feature_swamping_the_rest():
    """A linear model with one step size gives the largest-magnitude
    feature the largest gradient. Measured: the mobility differential
    spans about +/-70 in Royal Chess against about +/-2 for piece
    counts, and after ONE game mobility had reached -3.44 while every
    other weight sat near 0.1."""
    scales = {}
    raw = {'big': 70.0, 'small': 2.0}
    for _ in range(200):
        out = normalise(raw, scales)
    assert abs(out['big'] - out['small']) < 0.5, (
        'normalised features still differ by an order of magnitude')


def test_a_censored_game_teaches_nothing():
    """A game with no winner has no outcome to anchor on, and inventing
    one would teach the opposite of #260's lesson."""
    extractor = with_mobility(royal_chess)
    weights = {}
    scales = {}
    # A cap of two plies cannot finish a game of Royal Chess.
    updates = play_and_learn(make_engine, extractor, weights, {}.get
                             and random.Random(0), max_turns=2,
                             alpha=0.1, epsilon=0.0, scales=scales)
    assert updates == 0
    assert weights == {}, 'a censored game changed the weights'


def test_terminal_outcomes_are_read_not_estimated():
    """An immediate win must be taken regardless of what the value
    function says, because the outcome is known and the estimate is not.
    """
    game = _make_mnk()
    game.cells[0] = 'x'
    game.cells[1] = 'x'
    game.cells[5] = 'o'
    game.cells[6] = 'o'
    game.current_player = 'x'
    # A value function that hates every position; the win must still win.
    hostile = {name: -50.0 for name in ('Marks', 'Line:1', 'Line:2',
                                        'Line:3', 'Mobility')}
    pick = choose(game, game.get_all_legal_turns(), hostile,
                  with_mobility(mnk_features), random.Random(0), 0.0)
    assert pick == 2, 'declined an immediate win'


def test_it_runs_on_the_case_study_and_learns_something():
    extractor = with_mobility(royal_chess)
    weights = {}
    scales = {}
    updates = play_and_learn(make_engine, extractor, weights,
                             random.Random(0), max_turns=120, alpha=0.06,
                             epsilon=0.3, scales=scales)
    if updates:
        assert weights, 'a finished game produced no update'


def test_td_leaf_fits_the_leaf_rather_than_the_root():
    """The decisive property of TD-leaf, asserted on object identity.

    The value a search reports is the static evaluation of its PV LEAF.
    Fitting the evaluation at the ROOT aims the gradient at a quantity
    the search never reads, which is how the previous trainer taught
    itself that bishops are worthless: it chose actions one ply, so its
    data came from a policy that threw bishops away, and the games then
    said bishops do not matter.

    So every state the LEARNER records must come from the leaf clone and
    never from the live engine. The searcher's own evaluations are
    excluded by the `update` flag: only the trainer extracts with
    `update=True`.
    """
    import random

    import lgref.experiments.bootstrap as module
    from lgref.experiments.features import royal_chess, with_presence
    from lgref.experiments.search import Searcher

    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..',
                                      '..', 'src'))
    from experiments.variants import make_engine as make_royal

    ext = with_presence(royal_chess)
    factories = []
    live = []

    def make(variant='full', max_turns=None):
        engine = make_royal(variant, max_turns=max_turns)
        live.append(engine)
        return engine

    def searcher(weights, scales):
        factories.append(1)

        def evaluate(engine, perspective):
            return module.value(
                weights, module._features(ext, engine, perspective, None))

        return Searcher(evaluate, max_depth=2, quiescence=1)

    recorded = []
    original = module._features

    def spy(extractor, engine, mover, scales=None, update=False):
        if update:
            recorded.append(engine)
        return original(extractor, engine, mover, scales, update=update)

    module._features = spy
    try:
        module.play_and_learn(make, ext, {}, random.Random(5),
                              max_turns=12, alpha=0.06, epsilon=0.0,
                              scales={}, accumulator={},
                              searcher=searcher)
    finally:
        module._features = original

    assert len(factories) == 1, 'the factory must be called once per game'
    assert recorded, 'the learner recorded no states at all'
    assert len(live) == 1
    for engine in recorded:
        assert engine is not live[0], (
            'the learner read the LIVE position; TD-leaf must read the '
            'principal-variation leaf')


def test_without_a_searcher_the_trainer_is_unchanged():
    """TD-leaf is opt-in: the one-ply path must still work, so the two
    can be compared rather than swapped on faith."""
    import random

    from lgref.experiments.features import mnk as mnk_features

    weights, scales = {}, {}
    updates = play_and_learn(_make_mnk, mnk_features, weights,
                             random.Random(1), max_turns=20, alpha=0.08,
                             epsilon=0.0, scales=scales)
    assert updates > 0
    assert weights, 'the one-ply path learned nothing'
