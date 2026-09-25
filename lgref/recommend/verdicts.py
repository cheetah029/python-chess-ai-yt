"""Did the rule do what its predicted functions said it would?

Phase 2 pre-registers, per rule, the functions its STRUCTURE suggests,
and each function names quantities and the direction they move when the
rule is taken out. This is where the two meet: a prediction made before
any game was played, checked against what the games did.

WHAT IS BEING MATCHED, AND WHAT IS NOT. The behavioural sweep measures
DESIGNER-SPECIFIED ENGINE VARIANTS -- "the game without the boulder" --
not the clause clusters Phase 1 discovers. Those clusters are ablated in
GDL and checked structurally, because playing a GDL description through
the resolver costs over a minute per move and a 1440-game sweep of it
would take months. The two rule vocabularies are not joined, and
pretending otherwise would be the most flattering error available to
this project. So the matching runs the other way round: given what an
ablation measurably did, which functions in the ontology predicted
exactly that? A function whose signature fits is evidence about the
rule that was removed, and a function whose signature is contradicted
is evidence against it.

A NULL RESULT CONFIRMS A FLAT PREDICTION. Most of the ontology predicts
movement, and for those an inconclusive interval means the test did not
run. But `FLAT` predicts that a quantity does NOT move -- "threats
relocate while capacity holds" -- and there an interval spanning zero is
the outcome the function asked for. It is the one place in this
framework where finding nothing is finding something, and it is worth
being explicit about because the opposite convention would silently
discard every control clause in the ontology.
"""

import collections

from lgref.functions.strategic_ontology import (BY_NAME, DOWN, EXPECTED,
                                                FLAT, SHAPE, UP)

CONFIRMED = 'confirmed'
CONTRADICTED = 'contradicted'
UNTESTED = 'untested'
NOT_COMPARABLE = 'not comparable'

MetricCheck = collections.namedtuple(
    'MetricCheck', 'metric expected observed outcome note')


def check_metric(metric, expected, entry):
    """One predicted movement against one measured effect."""
    if entry is None:
        return MetricCheck(metric, expected, None, UNTESTED,
                           'not recorded in this run')
    if expected == SHAPE:
        return MetricCheck(metric, expected, entry.verdict, NOT_COMPARABLE,
                           'a distribution, not a level: needs its own test')
    if expected == FLAT:
        if entry.verdict == 'inconclusive':
            return MetricCheck(metric, expected, entry.verdict, CONFIRMED,
                               'interval spans zero, which is the '
                               'prediction')
        if entry.verdict == 'effect':
            return MetricCheck(metric, expected, entry.cohens_d, CONTRADICTED,
                               'predicted to hold, and it moved')
        return MetricCheck(metric, expected, entry.verdict, UNTESTED,
                           'seed variance swamps it, so holding still '
                           'cannot be distinguished from not being seen')
    if entry.verdict != 'effect':
        return MetricCheck(metric, expected, entry.verdict, UNTESTED,
                           'no effect survived both checks')
    moved_up = entry.cohens_d > 0
    wanted_up = expected == UP
    outcome = CONFIRMED if moved_up == wanted_up else CONTRADICTED
    return MetricCheck(metric, expected, entry.cohens_d, outcome,
                       'moved {} and {} predicted'.format(
                           'up' if moved_up else 'down',
                           UP if wanted_up else DOWN))


FunctionVerdict = collections.namedtuple(
    'FunctionVerdict', 'function outcome checks')


def check_function(function, effects_by_metric):
    """Every predicted movement for one function.

    CONTRADICTED beats CONFIRMED on purpose. A function claiming two
    movements and getting one of them has not been half-confirmed; it
    has been shown to be the wrong description, and averaging the two
    outcomes would turn a refutation into a score.
    """
    checks = [check_metric(metric, expected, effects_by_metric.get(metric))
              for metric, expected in sorted(EXPECTED[function].items())]
    outcomes = {c.outcome for c in checks}
    # A CONTROL CLAUSE CANNOT CONFIRM ON ITS OWN. `FLAT` says a
    # quantity does not move, and a quantity failing to move is
    # corroboration for a function whose real claim was checked --
    # never a substitute for checking it. Without this,
    # `threat_concentration` came back supported for an ablation where
    # the only thing measurable was its control clause: one interval
    # spanning zero, standing in for a claim about concentration that
    # nothing had tested.
    directional = [c for c in checks if c.expected != FLAT]
    confirmed_directional = any(c.outcome == CONFIRMED for c in directional)
    if CONTRADICTED in outcomes:
        outcome = CONTRADICTED
    elif confirmed_directional:
        outcome = CONFIRMED
    elif not directional and CONFIRMED in outcomes:
        outcome = CONFIRMED          # nothing but control clauses to check
    elif NOT_COMPARABLE in outcomes:
        outcome = NOT_COMPARABLE
    else:
        outcome = UNTESTED
    return FunctionVerdict(function, outcome, checks)


def match_all(effects):
    """Every function in the ontology against one variant's effects.

    Returns the verdicts grouped by outcome. The confirmed set is not a
    claim that the removed rule performed those functions -- several
    functions predict the same movement, which the ontology reports
    rather than hides -- but it is the set the evidence is consistent
    with, and the contradicted set is the one it rules out.
    """
    by_metric = {e.metric: e for e in effects}
    verdicts = [check_function(name, by_metric) for name in sorted(BY_NAME)]
    grouped = collections.OrderedDict(
        (outcome, [v for v in verdicts if v.outcome == outcome])
        for outcome in (CONTRADICTED, CONFIRMED, NOT_COMPARABLE, UNTESTED))
    return grouped
