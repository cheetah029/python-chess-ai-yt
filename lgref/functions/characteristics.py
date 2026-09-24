"""Design characteristics — stored separately from strategic functions.

A characteristic describes how a rule is BUILT; a strategic function
describes what it does to the decision system. The specification keeps
them apart deliberately, and the boulder is the reason why: "space
control" and "pawn mobility restriction" are functions, while "neutral"
and "shared" are characteristics. Collapsing them turns "shared neutral
influence" into an apparent strategic effect, which it is not.

Each dimension is detected from the description's own structure where
that is possible, and left UNKNOWN where it is not. An unknown
characteristic is recorded as unknown rather than guessed, because a
plausible default is indistinguishable from a measurement.
"""

import collections

Dimension = collections.namedtuple('Dimension', 'name values detectable')

UNKNOWN = 'unknown'

DIMENSIONS = (
    Dimension('ownership',
              ('player_owned', 'opponent_owned', 'neutral', 'shared'), True),
    Dimension('symmetry', ('symmetric', 'asymmetric'), True),
    Dimension('duration', ('instantaneous', 'temporary', 'persistent'), True),
    Dimension('activation',
              ('passive', 'proactive', 'reactive', 'conditional'), True),
    Dimension('scope', ('local', 'regional', 'global'), False),
    Dimension('phase', ('opening', 'midgame', 'endgame', 'universal'), False),
    Dimension('visibility',
              ('explicit', 'hidden', 'partially_observable'), False),
    Dimension('direction', ('enabling', 'constraining', 'mixed'), True),
    Dimension('target', ('self', 'opponent', 'both', 'environment'), False),
    Dimension('frequency', ('common', 'periodic', 'rare', 'one_time'), False),
    Dimension('dependency',
              ('independent', 'enabling', 'dependent', 'compensatory'), True),
)

BY_NAME = {d.name: d for d in DIMENSIONS}


def detect(own_clauses, context):
    """Characteristics readable from structure; the rest are UNKNOWN.

    `context` supplies description-wide facts (the dominant fluent, the
    control fluent, the role constants), so nothing here needs to know
    what game it is looking at.
    """
    result = collections.OrderedDict(
        (d.name, UNKNOWN) for d in DIMENSIONS)

    heads = [n.head_kind for n in own_clauses]
    writes = set()
    reads = set()
    for node in own_clauses:
        writes |= set(node.fluents_written)
        reads |= set(node.fluents_read)

    # DURATION: a fluent carried by a `next` rule outlives its turn.
    if any(h == 'fluent_write' for h in heads):
        persists = any(node.fluents_written & node.fluents_read
                       for node in own_clauses
                       if node.head_kind == 'fluent_write')
        result['duration'] = 'persistent' if persists else 'temporary'
    elif heads:
        result['duration'] = 'instantaneous'

    # ACTIVATION: responding to `does` is reactive; gating a `legal`
    # clause without reading an action is passive.
    if any(node.actions_read for node in own_clauses):
        result['activation'] = 'reactive'
    elif any(h == 'legal' for h in heads):
        result['activation'] = 'proactive'
    elif heads:
        result['activation'] = 'passive'

    # DIRECTION: a clause that grants an action enables; one that only
    # guards constrains.
    grants = any(h == 'legal' for h in heads)
    guards = any(node.negated_goals for node in own_clauses)
    if grants and guards:
        result['direction'] = 'mixed'
    elif grants:
        result['direction'] = 'enabling'
    elif guards:
        result['direction'] = 'constraining'

    # OWNERSHIP: whether the rule's state is tied to a role constant.
    roles = set(context.get('roles', ()))
    if roles:
        mentions_role = any(
            any(_mentions_any(node.raw, roles) for node in own_clauses)
            for _ in (0,))
        result['ownership'] = 'player_owned' if mentions_role else 'neutral'

    # SYMMETRY: a rule naming exactly one role is asymmetric.
    if roles:
        named = {r for r in roles
                 if any(_mentions_any(node.raw, {r}) for node in own_clauses)}
        if named:
            result['symmetry'] = 'symmetric' if len(named) == len(roles) \
                else 'asymmetric'

    # DEPENDENCY: whether it rests on state something else must write.
    external = reads - writes
    if heads:
        result['dependency'] = 'dependent' if external else 'independent'

    return result


def _mentions_any(term, names):
    if isinstance(term, tuple):
        return any(_mentions_any(part, names) for part in term)
    return term in names


def describe():
    lines = ['{:<14} {:<52} {}'.format('dimension', 'values', 'detectable')]
    lines.append('-' * 88)
    for d in DIMENSIONS:
        lines.append('{:<14} {:<52} {}'.format(
            d.name, ', '.join(d.values)[:52],
            'yes' if d.detectable else 'no — recorded as unknown'))
    return '\n'.join(lines)
