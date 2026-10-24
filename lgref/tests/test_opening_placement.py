"""Where the agent opens, measured without anyone saying where good is.

A reviewer's complaint about the m,n,k agent is that its first moves
are "weird and off the center". Nothing measured that. `tie_rate` asks
whether the evaluation can TELL ITS MOVES APART, which is a different
question, and it reported 97.7% for two feature sets that play visibly
differently.

THE OBVIOUS INSTRUMENT IS THE WRONG ONE. Distance from the middle of
the board is hand-written geometry: a researcher's opinion about m,n,k
smuggled into the measurement layer, and meaningless in the case study,
where the strong squares are not the middle ones. The whole claim of
this project is that the quantities come from the rules.

So the strong moves are LEARNED FROM THE RULES: play at random, see
which moves keep turning up on the winning side. Nothing in
`outcome_weights` knows what a board is, what a line is, or that games
have middles. On m,n,k it recovers the centre anyway, which is what
these tests check -- and it reads the case study with no changes at
all, which is what makes it an instrument rather than a special case.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from lgref.experiments.mnk import MNK
from lgref.experiments.validate import choice_rank, outcome_weights


def board(m=9, n=9, k=5):
    def make(_variant='full', max_turns=None):
        return MNK(m=m, n=n, k=k)
    return make


def prior(m=9, n=9, k=5, trials=400, seed=1):
    return outcome_weights(board(m, n, k), trials=trials, seed=seed)


def test_the_prior_recovers_the_centre_without_being_told_where_it_is():
    """THE VALIDATION, and note which way round it runs: the distance
    from the middle is computed HERE, in the test, to check that the
    instrument found it. The instrument itself never sees it."""
    weights = prior()
    points = []
    for cell, (wins, seen) in weights.items():
        if seen < 10:
            continue
        row, col = divmod(cell, 9)
        points.append((((row - 4) ** 2 + (col - 4) ** 2) ** 0.5,
                       wins / float(seen)))
    assert len(points) > 60, len(points)

    mean_x = sum(x for x, _y in points) / len(points)
    mean_y = sum(y for _x, y in points) / len(points)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in points)
    spread_x = sum((x - mean_x) ** 2 for x, _y in points) ** 0.5
    spread_y = sum((y - mean_y) ** 2 for _x, y in points) ** 0.5
    correlation = covariance / (spread_x * spread_y)
    assert correlation < -0.3, (
        'the rule-derived weights do not track centrality at all '
        '(correlation {0:+.2f}), so they are not measuring what this '
        'instrument claims'.format(correlation))


def test_it_separates_a_centre_seeker_from_a_corner_seeker():
    """POSITIVE AND NEGATIVE CONTROL. An instrument that cannot tell
    these two apart is measuring nothing."""
    weights = prior()
    make = board()

    def distance(turn):
        row, col = divmod(turn, 9)
        return abs(row - 4) + abs(col - 4)

    def centre_seeking(game, _rng):
        return min(game.get_all_legal_turns(), key=distance)

    def corner_seeking(game, _rng):
        return max(game.get_all_legal_turns(), key=distance)

    middle, _n = choice_rank(make, centre_seeking, weights, trials=60,
                             seed=3, min_setup=0, max_setup=2)
    corner, _n2 = choice_rank(make, corner_seeking, weights, trials=60,
                              seed=3, min_setup=0, max_setup=2)
    assert middle > 0.9, middle
    assert corner < 0.45, corner
    assert middle - corner > 0.4


def test_a_random_player_scores_the_indifference_value():
    """A PERCENTILE MUST BE UNBIASED or every number it produces is
    shifted. Averaged over sampling seeds, because one is a sample."""
    weights = prior()
    make = board()

    def coin(game, rng):
        return rng.choice(game.get_all_legal_turns())

    scores = []
    for seed in (3, 11, 29, 47):
        rank, asked = choice_rank(make, coin, weights, trials=60,
                                  seed=seed, min_setup=0, max_setup=4)
        assert asked > 30, asked
        scores.append(rank)
    average = sum(scores) / len(scores)
    assert 0.44 < average < 0.56, (
        'a random player should score 50%, not {0:.1%}'.format(average))


def test_the_prior_is_built_from_random_play_not_from_the_agent():
    """THE CIRCULARITY THIS AVOIDS. Judging a change by games against
    the thing it replaces, or against a prior learned from its own
    play, proves only that it differs. `outcome_weights` takes no
    policy -- it cannot be handed one."""
    import inspect

    signature = inspect.signature(outcome_weights)
    assert 'policy' not in signature.parameters
    assert 'agent' not in signature.parameters
    source = inspect.getsource(outcome_weights)
    assert 'rng.choice(turns)' in source, (
        'the prior is no longer built from random play')


def test_it_reads_a_different_game_with_no_changes():
    """THE GENERALITY CLAIM DOING WORK. The case study's moves are not
    cells: they carry a piece, an origin, a destination and four more
    fields. The instrument neither knows nor cares."""
    from experiments.variants import make_engine

    def make(_variant='full', max_turns=None):
        return make_engine('full', max_turns=400)

    weights = outcome_weights(make, trials=8, seed=2)
    assert weights, 'the instrument produced nothing for the case study'
    assert any(seen >= 2 for _wins, seen in weights.values())
    # The descriptions are the case study's, untouched.
    sample = next(iter(weights))
    assert isinstance(sample, tuple) and len(sample) > 3, sample


def test_a_big_move_space_can_be_coarsened_and_must_match():
    """60 case-study playouts give 6400 distinct descriptions of which
    814 are seen five times: a table that sparse is noise. `key`
    coarsens it -- and the SAME key has to be used when reading, or
    every lookup misses and the instrument silently reports nothing at
    all rather than failing."""
    from experiments.variants import make_engine

    def make(_variant='full', max_turns=None):
        return make_engine('full', max_turns=400)

    def destination(described):
        return described[3]

    fine = outcome_weights(make, trials=6, seed=2)
    coarse = outcome_weights(make, trials=6, seed=2, key=destination)
    assert len(coarse) < len(fine) / 4, (len(coarse), len(fine))
    assert max(seen for _w, seen in coarse.values()) > max(
        seen for _w, seen in fine.values())

    def coin(game, rng):
        return rng.choice(game.get_all_legal_turns())

    matched, asked = choice_rank(make, coin, coarse, trials=8, seed=4,
                                 min_setup=0, max_setup=4,
                                 key=destination)
    mismatched, _n = choice_rank(make, coin, coarse, trials=8, seed=4,
                                 min_setup=0, max_setup=4)
    assert asked > 0 and matched == matched, 'the matched key measured nothing'
    assert mismatched != mismatched, (
        'reading a coarsened table with the fine key should measure '
        'nothing, not quietly return a number')


def test_the_comparison_tool_builds_the_prior_once_before_either_arm():
    """If the prior were rebuilt per arm with a different seed, the two
    arms would be scored against different rulers."""
    source = open(os.path.join(os.path.dirname(__file__), '..', '..',
                               'tools', 'phase_rates.py')).read()
    before_loop = source.split("for label, use_reach in")[0]
    assert 'outcome_weights(' in before_loop, (
        'the prior is built inside the per-arm loop')
    assert 'opening (placement)' in source
