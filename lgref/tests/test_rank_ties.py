"""Ranks must not be manufactured out of ties or out of absence (#259).

The framework's headline finding type is "a rank that moves between
objectives is a finding". On the first valid dataset -- the 132-game
random control arm -- it produced eight of them and every one was the
order in which exact ties happened to be sorted.

Two defects, one symptom:

  * `rank_sensitivity` sorted and enumerated, so an identical index took
    dict insertion order and received 1, 2, 3, and the instability
    detector then reported the tie GROUP shifting as a rank flip;
  * an index of 0.0 was treated as a measurement, when for those eight
    every weighted dimension had come back seed-dominated -- absence of
    measurement, printed as `+0.00 (rank 3)`.

It fired hardest exactly when the data was weakest, because that is when
everything ties at zero.
"""

from lgref.analysis.effects import Effect
from lgref.analysis.profile import OBJECTIVES, rank_sensitivity, unranked

USABLE = 'effect'


def _effect(metric, variant, d, verdict=USABLE):
    return Effect(metric=metric, variant=variant, n_base=12, n_variant=12,
                  base_mean=1.0, variant_mean=1.0 + d, difference=d,
                  cohens_d=d, ci_low=d - 0.1, ci_high=d + 0.1,
                  seed_share=0.1, verdict=verdict)


def _row(variant, **dims):
    """A profile row: {dimension: Effect or None}."""
    return {metric: _effect(metric, variant, d)
            for metric, d in dims.items()}


def _dims_of(objective):
    return list(OBJECTIVES[objective])


def test_a_variant_with_no_usable_dimension_is_not_ranked():
    """`+0.00 (rank 3)` read as a measured zero in a measured position."""
    objective = next(iter(OBJECTIVES))
    dim = _dims_of(objective)[0]
    table = {
        'measured': _row('measured', **{dim: 0.9}),
        'unmeasured': {d: _effect(d, 'unmeasured', 0.9,
                                  verdict='seed-dominated')
                       for d in _dims_of(objective)},
    }
    _rankings, positions, _unstable = rank_sensitivity(table)
    assert positions['measured'][objective] == 1
    assert objective not in positions.get('unmeasured', {}), (
        'a variant whose every dimension was excluded has no position')
    assert objective in unranked(table)['unmeasured']


def test_ties_share_a_rank_instead_of_taking_insertion_order():
    objective = next(iter(OBJECTIVES))
    dim = _dims_of(objective)[0]
    table = {
        'a': _row('a', **{dim: 0.5}),
        'b': _row('b', **{dim: 0.5}),
        'c': _row('c', **{dim: 0.9}),
    }
    _rankings, positions, _unstable = rank_sensitivity(table)
    assert positions['c'][objective] == 1
    assert positions['a'][objective] == positions['b'][objective] == 2, (
        'equal index must mean equal rank')


def test_a_tie_group_shifting_is_not_reported_as_instability():
    """The eight false findings, reduced to their mechanism.

    Two variants tie at zero under both objectives while a third moves.
    Under the old sequential ranking the tied pair took 1 and 2 under one
    objective and 2 and 3 under the other, and both were reported as
    having moved.
    """
    first, second = list(OBJECTIVES)[:2]
    first_dim, second_dim = _dims_of(first)[0], _dims_of(second)[0]
    table = {
        'tied_one': _row('tied_one', **{first_dim: 0.0, second_dim: 0.0}),
        'tied_two': _row('tied_two', **{first_dim: 0.0, second_dim: 0.0}),
        'mover': _row('mover', **{first_dim: -0.9, second_dim: 0.9}),
    }
    _rankings, positions, unstable = rank_sensitivity(table)
    assert positions['tied_one'][first] == positions['tied_two'][first]
    assert 'tied_one' not in unstable and 'tied_two' not in unstable, (
        'a tie group cannot be unstable: neither member moved relative to '
        'the other'
    )


def test_a_genuine_rank_flip_is_still_reported():
    """The fix must not silence the finding the framework exists for.

    Weight SIGNS are not assumed: `anti_stagnation` weights
    `game_length` at -1.0, so a variant with the larger effect there
    ends up with the smaller index. The property under test is that a
    real reordering is still reported, not which end a given variant
    lands on.
    """
    first, second = list(OBJECTIVES)[:2]
    first_dim, second_dim = _dims_of(first)[0], _dims_of(second)[0]
    table = {
        'one_way': _row('one_way', **{first_dim: 0.9, second_dim: -0.9}),
        'middle': _row('middle', **{first_dim: 0.5, second_dim: 0.0}),
        'other_way': _row('other_way', **{first_dim: -0.9, second_dim: 0.9}),
    }
    _rankings, positions, unstable = rank_sensitivity(table)

    # The two extremes occupy opposite ends under the first objective,
    # and each reaches both ends somewhere across the four.
    assert positions['one_way'][first] == 1
    assert positions['other_way'][first] == 3
    for variant in ('one_way', 'other_way'):
        places = positions[variant]
        assert max(places.values()) - min(places.values()) >= 2, (
            '{} spans ranks {}'.format(variant, sorted(places.values())))
        assert variant in unstable, (
            'a rule that is first under one objective and last under '
            'another is the finding this framework is for')
    # And the variant that never moves is not reported.
    assert 'middle' not in unstable


def test_one_objective_alone_cannot_be_unstable():
    """Movement needs two objectives to move between."""
    objective = next(iter(OBJECTIVES))
    dim = _dims_of(objective)[0]
    other_dims = set()
    for name, weights in OBJECTIVES.items():
        if name != objective:
            other_dims |= set(weights)
    table = {
        'only_here': {**_row('only_here', **{dim: 0.9}),
                      **{d: _effect(d, 'only_here', 0.9,
                                    verdict='seed-dominated')
                         for d in other_dims if d != dim}},
        'also_only_here': {**_row('also_only_here', **{dim: -0.9}),
                           **{d: _effect(d, 'also_only_here', 0.9,
                                         verdict='inconclusive')
                              for d in other_dims if d != dim}},
    }
    _rankings, positions, unstable = rank_sensitivity(table)
    assert all(len(places) == 1 for places in positions.values())
    assert unstable == {}
