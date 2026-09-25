"""Turning measured effects into retain / revise / remove.

A recommendation is an ARGUMENT, not a score. Each one here carries the
objective it was made under, the evidence it rests on, and the rule
that turned one into the other, so a reader who disagrees can point at
the step they disagree with rather than at the conclusion.

THE SIGN CONVENTION, because everything downstream depends on it.
Effects are measured on the ABLATED variant relative to the intact
game. A positive index therefore means the game scored HIGHER on that
objective WITHOUT the rule. That is an argument for removing it, and
the opposite is an argument for keeping it.

WHY `REVISE` IS NOT A MIDDLE POSITION. It is not "between" retain and
remove and it is not a hedge. It is the specific finding that a rule
has a measurable effect which CONTRADICTS WHAT THE RULE IS FOR: it
does something, and not the thing it was written to do.

WHICH MEANS IT NEEDS A DECLARED INTENT, and mostly there is not one.
An earlier version of this fired `revise` whenever ANY of the forty
ontology functions was contradicted by the measured signature, which
made every measurable rule a candidate for revision -- of course a
boulder ablation contradicts `anti_drift_control`; the boulder was
never for that. Matching a signature against the whole ontology says
which functions the evidence rules out. It says nothing about whether
the rule failed, because it does not know what the rule was trying to
do. Only the designer's annotation knows that, and the annotation file
is a template with one rule filled in.

So `revise` fires only against a DECLARED intent, and where no intent
is declared this reports that revision could not be assessed rather
than reporting that the rule is fine.
"""

import collections

from lgref.recommend.verdicts import CONTRADICTED

RETAIN = 'retain'
REVISE = 'revise'
REMOVE = 'remove'
INSUFFICIENT = 'insufficient evidence'

#: Below this, a weighted sum of standardised effects is not worth
#: acting on. Cohen's conventional "small" is 0.2 for a single d, and
#: an index is a weighted sum of several, so this is deliberately
#: lenient about calling something negligible.
NEGLIGIBLE = 0.2

#: An objective whose dimensions mostly could not be measured has not
#: been evaluated. Reporting a confident recommendation from two usable
#: cells out of seven is how seed noise becomes design advice.
MIN_USABLE_SHARE = 0.5

Recommendation = collections.namedtuple(
    'Recommendation',
    'variant objective verdict index usable total reason intent_checked')


def recommend(variant, objective, weights, profile_row, index_value,
              function_verdicts=(), intended=None):
    """One recommendation, with the reasoning that produced it."""
    usable = sum(1 for dimension in weights
                 if profile_row.get(dimension) is not None
                 and profile_row[dimension].verdict == 'effect')
    total = len(weights)

    outcomes = {v.function: v.outcome for v in function_verdicts}
    if intended:
        failed = sorted(f for f in intended
                        if outcomes.get(f) == CONTRADICTED)
        if failed:
            return Recommendation(
                variant, objective, REVISE, index_value, usable, total,
                'the measurements contradict what it is for: {}'.format(
                    ', '.join(failed)), True)

    if total and usable < MIN_USABLE_SHARE * total:
        return Recommendation(
            variant, objective, INSUFFICIENT, index_value, usable, total,
            '{} of {} weighted dimensions produced a usable effect; the '
            'rest were swamped by seed variance or spanned zero'.format(
                usable, total), bool(intended))

    if index_value > NEGLIGIBLE:
        return Recommendation(
            variant, objective, REMOVE, index_value, usable, total,
            'the game scores higher on this objective without it '
            '({:+.2f})'.format(index_value), bool(intended))
    if index_value < -NEGLIGIBLE:
        return Recommendation(
            variant, objective, RETAIN, index_value, usable, total,
            'removing it costs this objective ({:+.2f})'.format(index_value),
            bool(intended))
    return Recommendation(
        variant, objective, REMOVE, index_value, usable, total,
        'measured, and it moves this objective by {:+.2f} -- removing it '
        'costs nothing the objective values'.format(index_value),
        bool(intended))


def disagreements(recommendations):
    """Rules whose recommendation depends on the objective.

    Reported rather than resolved. A rule that should be kept for one
    stated goal and dropped for another is the finding; picking a
    winner would bury the judgement this framework exists to expose.
    """
    by_variant = collections.defaultdict(dict)
    for entry in recommendations:
        by_variant[entry.variant][entry.objective] = entry.verdict
    out = collections.OrderedDict()
    for variant in sorted(by_variant):
        verdicts = by_variant[variant]
        decided = {v for v in verdicts.values() if v != INSUFFICIENT}
        if len(decided) > 1:
            out[variant] = verdicts
    return out
