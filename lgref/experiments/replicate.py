"""Which learned weights are findings, and which are one run's noise.

THE PROBLEM THIS EXISTS FOR, stated with the measurement that forced it.
Two trainings differing only in seed put `King` at +0.281 against
`RoyalQueen` +0.236, and then at +0.100 against +0.160 -- the ordering
REVERSED. The first run was reported as a per-piece valuation. It was
not one; it was a draw from a distribution whose spread nobody had
measured. A human reasonably objected that the king should not outrank
the queen, and the truthful answer was that the model had never
consistently held that view.

So no weight is reported as a value until the SAME training, varied only
by seed, has been run more than once and the feature has been shown to
survive that variation. Features that do not survive are reported as
UNMEASURED, which is different from "zero" and different from "small":
it means this procedure, at this sample size, cannot say.

Two criteria, deliberately both:

  SIGN AGREEMENT    every run must agree on the direction. A feature
                    that is positive in one run and negative in another
                    has no sign to report, whatever its mean.
  SEPARATION        |mean| must exceed `min_t` standard errors of the
                    mean. A feature can agree on sign across runs and
                    still be indistinguishable from zero.

Sign agreement alone is too weak -- with two runs it fires half the time
by chance on a feature worth nothing -- and separation alone is too weak
because the standard error of two samples is itself badly estimated.
Requiring both is what makes a small number of seeds usable at all, and
`n` is reported with every row so the reader can discount accordingly.

NOTHING HERE KNOWS ANY GAME. The input is a list of {name: value}
mappings and the output is the same names, sorted.
"""

import collections
import math

#: Default separation threshold, in standard errors of the mean. Two is
#: the conventional "distinguishable from zero" line and is NOT a
#: significance test: with a handful of seeds the standard error is
#: itself a rough estimate, which is why sign agreement is required
#: alongside it rather than instead of it.
MIN_T = 2.0

Summary = collections.namedtuple(
    'Summary', 'feature mean sd se t runs sign_agreement replicated')


def _mean(values):
    return sum(values) / float(len(values))


def _sd(values):
    """Sample standard deviation, with the n-1 denominator.

    The n denominator understates the spread of a small sample, and a
    small sample is the whole situation here.
    """
    if len(values) < 2:
        return float('inf')
    average = _mean(values)
    variance = sum((v - average) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def summarise(runs, min_t=MIN_T):
    """One `Summary` per feature, over `runs` mappings of {name: value}.

    A feature ABSENT from a run counts as zero for that run, not as
    missing. That is the right reading here and the reason is the same
    one that keeps biting elsewhere: the extractors return a feature
    only where it is non-zero, so treating absence as missing would
    average each feature over the subset of runs that happened to
    produce it, which is a biased subsample of exactly the runs where it
    was large.
    """
    names = set()
    for run in runs:
        names.update(run)
    out = []
    for name in sorted(names):
        values = [float(run.get(name, 0.0)) for run in runs]
        average = _mean(values)
        spread = _sd(values)
        error = (spread / math.sqrt(len(values))
                 if len(values) > 1 and spread != float('inf')
                 else float('inf'))
        separation = (abs(average) / error if error not in (0.0, float('inf'))
                      else (float('inf') if average and error == 0.0
                            else 0.0))
        positives = sum(1 for v in values if v > 0)
        negatives = sum(1 for v in values if v < 0)
        agreement = max(positives, negatives) / float(len(values))
        replicated = bool(agreement == 1.0 and separation >= min_t)
        out.append(Summary(name, average, spread, error, separation,
                           len(values), agreement, replicated))
    return out


def gate(runs, min_t=MIN_T):
    """`(replicated, unmeasured)` -- two dicts of {name: mean}.

    The second is NOT a set of zeros. It is the set of features this
    procedure cannot speak about at this sample size, and a reader who
    needs them has to run more seeds rather than read the mean.
    """
    kept, dropped = {}, {}
    for row in summarise(runs, min_t=min_t):
        (kept if row.replicated else dropped)[row.feature] = row.mean
    return kept, dropped


def report(runs, min_t=MIN_T, limit=None):
    """A table, most separated first, with the unmeasured rows shown.

    They are shown rather than hidden on purpose: a reader who sees only
    the surviving features cannot tell whether two features survived out
    of three or out of forty, and that ratio is the main thing to know
    about a run.
    """
    rows = summarise(runs, min_t=min_t)
    rows.sort(key=lambda r: (-r.replicated, -abs(r.t), -abs(r.mean)))
    if limit is not None:
        rows = rows[:limit]
    lines = ['{0} runs, gate = sign agreement AND |mean| >= {1:g} SE'
             .format(len(runs), min_t),
             '{0:<30} {1:>9} {2:>9} {3:>7} {4:>6}  {5}'.format(
                 'feature', 'mean', 'sd', 't', 'sign', 'verdict')]
    for row in rows:
        separation = ('inf' if row.t == float('inf')
                      else '{0:.1f}'.format(row.t))
        lines.append('{0:<30} {1:>+9.4f} {2:>9.4f} {3:>7} {4:>5.0%}  {5}'
                     .format(row.feature, row.mean,
                             0.0 if row.sd == float('inf') else row.sd,
                             separation, row.sign_agreement,
                             'replicated' if row.replicated
                             else 'UNMEASURED'))
    kept = sum(1 for r in rows if r.replicated)
    lines.append('{0} of {1} features replicated'.format(kept, len(rows)))
    return '\n'.join(lines)


def effective(payload):
    """`weight / scale` for a saved run, which is the per-unit value.

    The raw weights are in normalised units and their magnitudes do not
    mean what they look like, so comparing two runs' raw vectors
    compares two different scalings.
    """
    if 'effective' in payload:
        return dict(payload['effective'])
    weights = payload.get('weights', {})
    scales = payload.get('scales', {})
    return {name: weights[name] / (scales.get(name, 1.0) or 1.0)
            for name in weights}
