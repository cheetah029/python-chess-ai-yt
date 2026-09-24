"""Effect sizes with intervals, and the variance that can invalidate them.

Phase 4. The brief is specific: effect sizes with bootstrap confidence
intervals rather than p-values alone, variance decomposition between
variant and seed, and multiple-comparison correction across the
metric x rule grid.

THE VARIANCE DECOMPOSITION IS NOT A FORMALITY. If between-seed variance
swamps the between-variant difference, the effect is not real and must
be reported as such rather than presented with a tidy interval around
it. That check is what stops a sweep from manufacturing findings, and
it is why one seed per variant is not enough to analyse at all.
"""

import collections
import math
import random

Effect = collections.namedtuple(
    'Effect', 'metric variant n_base n_variant base_mean variant_mean '
              'difference cohens_d ci_low ci_high seed_share verdict')

#: Below this share of total variance attributable to the variant, the
#: effect is not reported as real. Seed noise dominating the signal is
#: the failure mode this phase exists to catch.
MIN_VARIANT_SHARE = 0.5

BOOTSTRAP_SAMPLES = 2000


def _mean(values):
    return sum(values) / len(values) if values else float('nan')


def _var(values):
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def cohens_d(a, b):
    """Standardised difference, pooled. NaN when it is undefined."""
    if len(a) < 2 or len(b) < 2:
        return float('nan')
    va, vb = _var(a), _var(b)
    pooled = ((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2)
    if pooled <= 0:
        # Identical, zero-variance samples. A difference of zero with no
        # spread is not an infinite effect, it is no effect.
        return 0.0 if _mean(a) == _mean(b) else float('inf')
    return (_mean(b) - _mean(a)) / math.sqrt(pooled)


def bootstrap_ci(a, b, samples=BOOTSTRAP_SAMPLES, alpha=0.05, seed=0):
    """Percentile interval for the difference in means."""
    if not a or not b:
        return float('nan'), float('nan')
    rng = random.Random(seed)
    diffs = []
    for _ in range(samples):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        diffs.append(_mean(rb) - _mean(ra))
    diffs.sort()
    lo = diffs[int(alpha / 2 * len(diffs))]
    hi = diffs[min(int((1 - alpha / 2) * len(diffs)), len(diffs) - 1)]
    return lo, hi


def variance_share(rows_by_seed_base, rows_by_seed_variant):
    """Share of variance attributable to the VARIANT rather than the seed.

    Between-seed variance is measured within each arm and pooled; the
    between-variant component is the squared difference of the arm
    means. A share below `MIN_VARIANT_SHARE` means seed noise dominates
    and the effect must not be reported as real.
    """
    seed_means = []
    for group in (rows_by_seed_base, rows_by_seed_variant):
        for values in group.values():
            if values:
                seed_means.append(_mean(values))
    if len(seed_means) < 2:
        return float('nan')

    base_all = [v for values in rows_by_seed_base.values() for v in values]
    var_all = [v for values in rows_by_seed_variant.values() for v in values]
    between_variant = (_mean(var_all) - _mean(base_all)) ** 2

    within = []
    for group in (rows_by_seed_base, rows_by_seed_variant):
        means = [_mean(v) for v in group.values() if v]
        if len(means) >= 2:
            within.append(_var(means))
    between_seed = _mean(within) if within else 0.0

    total = between_variant + between_seed
    if total <= 0:
        return float('nan')
    return between_variant / total


def effect(metric, baseline_rows, variant_rows, variant_name, seed_key='seed'):
    """One cell of the contribution profile."""
    def values(rows):
        return [r[metric] for r in rows
                if r.get(metric) is not None
                and isinstance(r[metric], (int, float))
                and not isinstance(r[metric], bool)]

    def by_seed(rows):
        out = collections.defaultdict(list)
        for row in rows:
            value = row.get(metric)
            if value is None or isinstance(value, bool) or \
                    not isinstance(value, (int, float)):
                continue
            out[row.get(seed_key)].append(value)
        return out

    base, var = values(baseline_rows), values(variant_rows)
    if not base or not var:
        return None

    lo, hi = bootstrap_ci(base, var)
    share = variance_share(by_seed(baseline_rows), by_seed(variant_rows))
    crosses_zero = lo <= 0 <= hi

    if not (share == share) or share < MIN_VARIANT_SHARE:
        verdict = 'seed-dominated'
    elif crosses_zero:
        verdict = 'inconclusive'
    else:
        verdict = 'effect'

    return Effect(metric, variant_name, len(base), len(var),
                  round(_mean(base), 3), round(_mean(var), 3),
                  round(_mean(var) - _mean(base), 3),
                  round(cohens_d(base, var), 3),
                  round(lo, 3), round(hi, 3),
                  None if share != share else round(share, 3), verdict)


def benjamini_hochberg(effects, alpha=0.05):
    """Flag which effects survive multiple comparison across the grid.

    The grid is metrics x variants, so some interval will exclude zero
    by chance. Ranking by |d| and applying a Benjamini-Hochberg-style
    step-up keeps the false-discovery rate bounded without pretending a
    bootstrap interval is a p-value.
    """
    usable = [e for e in effects if e.verdict == 'effect'
              and e.cohens_d == e.cohens_d and abs(e.cohens_d) != float('inf')]
    if not usable:
        return set()
    ranked = sorted(usable, key=lambda e: -abs(e.cohens_d))
    keep, m = set(), len(ranked)
    for index, entry in enumerate(ranked, start=1):
        if abs(entry.cohens_d) >= 0.2 and index <= max(1, int(alpha * m)) + \
                sum(1 for e in ranked if abs(e.cohens_d) >= 0.8):
            keep.add((entry.metric, entry.variant))
    return keep
