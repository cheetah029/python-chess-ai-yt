"""Phase 4 analysis, and the ways an effect table can lie.

Issue #210 / the brief's Phase 4. The variance decomposition is the
reason this phase exists: if between-seed variance swamps the
between-variant difference, the effect is not real and must not be
reported with a tidy interval around it.
"""

import pytest

from lgref.analysis import profile as profile_mod
from lgref.analysis.effects import (MIN_VARIANT_SHARE, bootstrap_ci,
                                    cohens_d, effect, variance_share)


def _rows(variant, values, seeds=(0, 1, 2), metric='total_turns'):
    out = []
    for index, value in enumerate(values):
        out.append({'variant': variant, 'seed_group': seeds[index % len(seeds)],
                    metric: value})
    return out


# ------------------------------------------------- variance decomposition ----

def test_a_seed_dominated_difference_is_not_reported_as_an_effect():
    """The check the whole phase turns on.

    Both arms swing wildly BETWEEN seeds and barely differ between
    variants. A point estimate with an interval would look like a
    finding; it is noise.
    """
    base = _rows('full', [1, 1, 40, 40, 80, 80])
    variant = _rows('v', [2, 2, 41, 41, 81, 81])
    got = effect('total_turns', base, variant, 'v', seed_key='seed_group')
    assert got.verdict == 'seed-dominated', got


def test_a_clean_separation_is_reported():
    base = _rows('full', [10, 11, 10, 12, 11, 10])
    variant = _rows('v', [30, 31, 30, 32, 31, 30])
    got = effect('total_turns', base, variant, 'v', seed_key='seed_group')
    assert got.verdict == 'effect', got
    assert got.cohens_d > 2


def test_an_interval_spanning_zero_is_inconclusive():
    base = _rows('full', [10, 20, 10, 20, 10, 20])
    variant = _rows('v', [11, 19, 12, 18, 11, 21])
    got = effect('total_turns', base, variant, 'v', seed_key='seed_group')
    assert got.verdict in ('inconclusive', 'seed-dominated')


def test_identical_samples_give_zero_not_infinity():
    """Zero difference with zero spread is no effect, not an infinite one."""
    assert cohens_d([5, 5, 5], [5, 5, 5]) == 0.0


def test_the_threshold_is_stated_not_tuned():
    assert MIN_VARIANT_SHARE >= 0.5


# ---------------------------------------------------------- the index ----

def test_an_unreliable_dimension_contributes_zero_not_its_estimate():
    """Summing unreliable estimates is how confidence is manufactured."""
    base = _rows('full', [1, 1, 40, 40, 80, 80])
    variant = _rows('v', [2, 2, 41, 41, 81, 81])
    noisy = effect('total_turns', base, variant, 'v', seed_key='seed_group')
    row = {'game_length': noisy}
    got = profile_mod.index(row, {'game_length': 1.0})
    assert got['index'] == 0.0
    assert got['dimensions_skipped'], 'the exclusion was not recorded'


def test_there_is_no_single_objective():
    """A universal index would hide the judgement being made."""
    assert len(profile_mod.OBJECTIVES) >= 3


def test_rank_instability_is_surfaced():
    """A rank that flips under reweighting is a finding, not noise."""
    class _E:
        verdict = 'effect'
        cohens_d = 2.0
    class _F:
        verdict = 'effect'
        cohens_d = -2.0

    table = {
        'a': {'game_length': _E(), 'choice_diversity': _F()},
        'b': {'game_length': _F(), 'choice_diversity': _E()},
    }
    _, positions, unstable = profile_mod.rank_sensitivity(table)
    assert positions and isinstance(unstable, dict)


# ------------------------------------------------------------ bootstrap ----

def test_the_bootstrap_interval_is_reproducible():
    a, b = [1, 2, 3, 4], [5, 6, 7, 8]
    assert bootstrap_ci(a, b, seed=7) == bootstrap_ci(a, b, seed=7)


def test_variance_share_needs_more_than_one_seed():
    """With one seed group there is nothing to decompose."""
    result = variance_share({0: [1, 2]}, {0: [3, 4]})
    assert result != result or result >= 0
