"""Audit a saved training run BEFORE reading its result.

WHY THIS MODULE EXISTS. Three experiments in a row produced a
confident, wrong conclusion because the run was not the run I thought I
had launched. Each time the number was read first and the pipeline
checked afterwards, if at all:

  1. A trainer kept the feature set a patch was supposed to replace,
     because the patch's anchor text did not match. The race that
     followed measured the set that was already known to be bad and the
     verdict was recorded as a verdict about the new idea.
  2. A run recorded the fact of an ablation as a BOOLEAN, `lean: True`,
     while the loader replays an ablation from a LIST of prefixes. The
     boolean is not a field anything reads, so the saved weights were
     played back on a different feature set from the one they were
     fitted on.
  3. A feature added to fix a defect was never computed at all, because
     an unrelated speed optimisation short-circuited the loop that
     counted it. Three seeds agreed on a weight of exactly +0.000000
     and the agreement looked like a finding.

The common shape is that NOTHING IN THE ARTIFACT CONTRADICTED THE
MISTAKE. A payload that cannot be replayed looks exactly like one that
can; a feature that never varied looks exactly like a feature the
learner priced at zero. So the checks live here, in code, and run at
load time rather than in a procedure someone is supposed to remember.

THE TWO SIGNATURES, stated once so they are recognisable:

  * A FEATURE THAT NEVER VARIED has a normaliser scale of zero. The
    scale is a decaying maximum of the feature's own magnitude, so zero
    means the quantity was zero in every position of every game. Its
    weight is then necessarily zero too, and that zero is not a price
    the learner chose -- it is the absence of data. An experiment whose
    point was that feature tested nothing.
  * A PAYLOAD THAT CANNOT BE REPLAYED carries a claim about training in
    a field the loader does not read. The loader rebuilds the feature
    set from `REPLAY_FIELDS` and nothing else, so any other record of a
    transformation is decoration -- and worse than decoration, because
    it reads like evidence that the transformation was applied.

Nothing here knows anything about any game: a payload is a mapping of
names to numbers and the checks are about its internal consistency.
"""

#: The ONLY fields a loader replays, and therefore the only place a
#: training-time transformation of the feature set may be recorded. A
#: transformation recorded anywhere else does not happen at play time.
REPLAY_FIELDS = ('extractor', 'drop_prefixes', 'dropped')

#: A payload with a fatal complaint must not be played: the evaluation
#: it produces is not the one that was fitted.
FATAL = 'fatal'

#: Worth knowing and not worth refusing. A feature that never varied
#: makes a run look like a test of it, but playing the run is harmless.
SUSPECT = 'suspect'


def record(extractor, drop_prefixes=(), dropped=(), **extra):
    """The replay fields for a payload, built in one place.

    Two of the three failures above were a trainer recording its own
    pipeline by hand and getting it wrong. A trainer that calls this
    cannot describe an ablation it did not perform, because it passes
    the same values it built the extractor from.

    Booleans are REFUSED rather than ignored. `lean: True` is the exact
    shape of failure 2: a true statement about the run, in a field no
    loader reads, which then stood in for evidence that the ablation
    had been replayed.
    """
    if not isinstance(extractor, str) or not extractor:
        raise ValueError(
            'a payload must name the extractor its weights were fitted '
            'on; the loader has no way to guess it')
    for key, item in sorted(extra.items()):
        if isinstance(item, bool):
            raise ValueError(
                'refusing to record {0}={1!r}: a boolean describes the '
                'run in a field no loader reads. Record the thing '
                'itself -- an ablation goes in drop_prefixes, which is '
                'replayed.'.format(key, item))
    out = {'extractor': extractor,
           'drop_prefixes': list(drop_prefixes),
           'dropped': list(dropped)}
    out.update(extra)
    return out


def audit(payload):
    """Complaints about a saved payload, fatal ones first.

    Each returned pair is `(severity, message)` and every check here
    corresponds to a mistake that was actually made and not noticed.
    """
    complaints = []
    weights = payload.get('weights') or {}
    scales = payload.get('scales') or {}

    if not payload.get('extractor'):
        complaints.append((
            FATAL,
            'no extractor is named, so the feature set the weights were '
            'fitted on cannot be rebuilt'))

    # A BOOLEAN IS A CLAIM NOTHING ACTS ON. Whether that is fatal
    # depends on whether the transformation it claims is recorded
    # anywhere the loader reads. `lean: True` beside a populated
    # `drop_prefixes` is redundant; `lean: True` beside an empty one is
    # failure 2 exactly -- the run ablated, the artifact did not say
    # so in the field that matters, and the weights were replayed on
    # the unablated set.
    replayable = bool(payload.get('drop_prefixes')
                      or payload.get('dropped'))
    for key, item in sorted(payload.items()):
        if not isinstance(item, bool):
            continue
        if item and not replayable:
            complaints.append((
                FATAL,
                '{0}={1!r} claims a transformation of the feature set, '
                'and none of {2} records one; the weights were fitted '
                'on a set the loader cannot rebuild'.format(
                    key, item, ', '.join(REPLAY_FIELDS))))
        else:
            complaints.append((
                SUSPECT,
                '{0}={1!r} describes the run in a field no loader '
                'reads; it is not evidence that anything was replayed, '
                'and only {2} are'.format(key, item,
                                          ', '.join(REPLAY_FIELDS))))

    overlap = sorted(set(payload.get('dropped') or ()) & set(weights))
    if overlap:
        complaints.append((
            FATAL,
            'these columns are recorded as dropped yet carry weights, '
            'so the payload describes two different feature sets: '
            '{0}'.format(', '.join(overlap))))

    if weights and not any(weights.values()):
        complaints.append((
            FATAL,
            'every one of the {0} weights is exactly zero; the run '
            'learned nothing and the evaluation is flat'.format(
                len(weights))))

    if scales:
        flat = sorted(name for name in weights
                      if not scales.get(name, 0.0))
        if flat:
            complaints.append((
                SUSPECT,
                'these {0} features never varied in training (scale 0), '
                'so their weights are the absence of data rather than a '
                'price: {1}'.format(len(flat), ', '.join(flat))))

    complaints.sort(key=lambda pair: pair[0] != FATAL)
    return complaints


def fatal(complaints):
    """Just the complaints that make a payload unplayable."""
    return [text for severity, text in complaints if severity == FATAL]


def observed(features_of, states):
    """How often each feature was non-zero, and how far it ranged.

    The complement of `audit`: that reads the artifact, this reads the
    extractor against real positions. Use it to check that a feature an
    experiment is ABOUT actually fires before spending a training run on
    it -- the third failure above would have taken one call.

    Returns `{name: (times_non_zero, largest_magnitude)}` over however
    many states are supplied.
    """
    summary = {}
    for state in states:
        for name, amount in features_of(state).items():
            seen, largest = summary.get(name, (0, 0.0))
            summary[name] = (seen + (1 if amount else 0),
                             max(largest, abs(amount)))
    return summary


def silent(summary):
    """Features that were zero in every state they were extracted from.

    A feature in this list cannot have taught the learner anything, and
    a feature an experiment was designed around appearing in it means
    the experiment did not run.
    """
    return sorted(name for name, (seen, _largest) in summary.items()
                  if not seen)
