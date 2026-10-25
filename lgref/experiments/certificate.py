"""A change ships on a PROOF, not on a measurement that failed to object.

THE ERROR THIS CORRECTS, in the reviewer's words: "using gates to test
for strict improvement is wrong in and of itself. What needs to be done
from the start is to design the methodology of building the change so
that it is certainly strictly better, not to throw spaghetti on the
wall and see if it works."

They are right, and the reason is in what a gate can do. A gate is a
DETECTOR. It reports a regression it can see, at the power it happens
to have, on the phases it happens to reach. An empty result means "no
regression detected by this run", which is not "no regression". This
project has three worked examples of that gap being real rather than
theoretical:

  - a 0.8-point tempo loss sat INSIDE the noise floor and was down on
    all four training seeds anyway;
  - a "clean" 13x13 gate was clean because its endgame band has NO
    SAMPLES AT ALL -- the run reported 0.0% on zero positions and the
    verdict read as a pass;
  - a +7.0-point opening gain was measured while the change being
    measured had crippled the search to depth 1.

So a gate may REFUSE a change. It may never LICENSE one. What licenses
a change is an argument made BEFORE the measurement, of a shape whose
premise can be checked mechanically. Four are admissible here:

  IDENTICAL   The new code computes the same values as the old, and
              costs less. Strict improvement is then arithmetic: same
              decisions, fewer resources. Checked by comparing outputs
              against the previous implementation over a wide sample.

  CONFINED    The change has NO effect outside a region fixed by the
              rules. Everything outside is bit-identical, so nothing
              there can regress, and the argument reduces to the
              region. Checked by sampling outside and asserting
              equality.

  MONOTONE    A quantity can only move one way by construction -- for
              instance, preferring a move with a property means the
              rate of that property cannot fall. Checked as a property
              over random cases.

  UNSOUND     The change removes an operation whose PREMISE IS FALSE
              for this game. Nothing correctly gained is lost, because
              the gain was never sound. Checked by asserting the
              premise fails.

A change that fits none of these is not ready to ship. That is not a
counsel of perfection: it is the difference between "I could not find
a problem" and "there cannot be one", and only the second survives the
next reviewer's game.
"""

import collections

Certificate = collections.namedtuple(
    'Certificate', ('kind', 'subject', 'checked', 'detail'))


class NotCertified(AssertionError):
    """The premise of a claimed argument does not hold."""


def identical(subject, before, after, cases):
    """IDENTICAL: `after` returns exactly what `before` does.

    `cases` is an iterable of arguments. The comparison is equality,
    not closeness: a change that moves a value by a little is not this
    kind of change and must make a different argument.
    """
    checked = 0
    for case in cases:
        was = before(case)
        now = after(case)
        if was != now:
            raise NotCertified(
                '{0}: outputs differ on case {1}\n  before: {2}\n  '
                'after:  {3}'.format(subject, checked, was, now))
        checked += 1
    if not checked:
        raise NotCertified(
            '{0}: no cases were compared, so nothing was '
            'proved'.format(subject))
    return Certificate('IDENTICAL', subject, checked,
                       'equal outputs on every case')


def confined(subject, effect, outside, expected=0):
    """CONFINED: the change has no effect outside its region.

    `effect(case)` returns the change's contribution; `outside` yields
    cases drawn from beyond the region. Anything other than `expected`
    there means the change is NOT confined and cannot borrow this
    argument.
    """
    checked = 0
    for case in outside:
        value = effect(case)
        if value != expected:
            raise NotCertified(
                '{0}: effect {1!r} outside the region, so it is not '
                'confined'.format(subject, value))
        checked += 1
    if not checked:
        raise NotCertified(
            '{0}: no outside cases were sampled, so confinement was '
            'not tested'.format(subject))
    return Certificate('CONFINED', subject, checked,
                       'no effect outside the region')


def monotone(subject, score, before, after, cases):
    """MONOTONE: the measured quantity can only move one way.

    `before(case)` and `after(case)` give the old and new choices;
    `score` ranks them. A single case where the new choice scores lower
    refutes the argument -- which is the point, since the claim is
    about every case and not about an average.
    """
    checked = moved = 0
    for case in cases:
        was, now = before(case), after(case)
        if score(case, now) < score(case, was):
            raise NotCertified(
                '{0}: the new choice scores lower on case {1}'.format(
                    subject, checked))
        if was != now:
            moved += 1
        checked += 1
    if not checked:
        raise NotCertified('{0}: no cases'.format(subject))
    return Certificate('MONOTONE', subject, checked,
                       '{0} choices changed, none for the '
                       'worse'.format(moved))


def unsound(subject, premise, cases):
    """UNSOUND: the removed operation's premise is false here.

    `premise(case)` says whether the assumption the operation rests on
    holds. If it ever holds, removing the operation costs something
    real and this argument does not apply.
    """
    checked = 0
    for case in cases:
        if premise(case):
            raise NotCertified(
                '{0}: the premise HOLDS on case {1}, so removing the '
                'operation is not free'.format(subject, checked))
        checked += 1
    if not checked:
        raise NotCertified('{0}: no cases'.format(subject))
    return Certificate('UNSOUND', subject, checked,
                       'premise fails on every case')


def gate_may_only_refuse(findings):
    """A gate result, read correctly.

    Returns the findings unchanged. It exists to be the one place that
    says what an empty result means: NOTHING WAS DETECTED. It is not a
    licence, and a change with no certificate does not become shippable
    because a run came back quiet.
    """
    return list(findings)
