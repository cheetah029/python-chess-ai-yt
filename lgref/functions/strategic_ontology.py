"""The project's strategic-function ontology, as specified.

Layer 3 of the five-layer representation. Hierarchical and multi-label:
a rule may perform several functions, and different rules may perform
the same one, which is what lets a function generalise across games
even when rule names do not.

THIS REPLACES AN EARLIER, MUCH NARROWER ONTOLOGY OF MINE. That one had
six classes -- complexity, tempo, decisiveness, initiative, closure,
space_control -- and was operational rather than strategic: it described
what a rule does to the move set, which is mechanism. It also could not
express most of what the specification requires.

A FUNCTION IS NOT A DESIGN CHARACTERISTIC. "Neutral", "shared",
"persistent" describe how a rule is built, not what it does to the
decision system. They live in `characteristics.py` and are stored
separately, because collapsing them is how "shared neutral influence"
gets mistaken for a strategic effect.

OPERATIONAL DEFINITIONS. A function may only be asserted where it has
measurable evidence. `evidence` names what would have to move under
ablation. Where the specification gives an operational definition, it is
recorded verbatim in spirit; where it does not, `evidence` is None and
the function is marked NOT YET OPERATIONAL -- it can be predicted
structurally but cannot yet be confirmed or falsified, and saying so is
better than inventing a metric to make the table look complete.
"""

import collections

Function = collections.namedtuple(
    'Function', 'name category definition evidence metrics')

CATEGORIES = collections.OrderedDict((
    ('A', 'Mobility and access'),
    ('B', 'Threat and capture'),
    ('C', 'Space and control'),
    ('D', 'Survival and protection'),
    ('E', 'Transformation and resource configuration'),
    ('F', 'Time, history, and persistence'),
    ('G', 'Termination and outcome structure'),
    ('H', 'Choice structure'),
))


def _f(name, category, definition, evidence=None, metrics=()):
    return Function(name, category, definition, evidence, tuple(metrics))


ONTOLOGY = (
    # ---- A: mobility and access -------------------------------------
    _f('mobility_expansion', 'A',
       'increases reachable destinations or legal movement options',
       'reachable squares, legal destinations, escape paths or effective '
       'branching all increase',
       ('mean_reachable_mover', 'mean_branching')),
    _f('mobility_restriction', 'A',
       'reduces reachable destinations or constrains movement paths',
       'opponent legal moves and reachable-state volume fall; blocked-piece '
       'rate rises',
       ('mean_branching', 'mean_reachable_mover')),
    _f('repositioning', 'A',
       'lets a piece change strategic location without ordinary movement',
       'displacement per move rises without a matching path traversal',
       ('mean_reachable_mover',)),
    _f('escape_facilitation', 'A',
       'increases the ability to leave threatened or blocked positions',
       'capture probability falls and escape-route count rises',
       ('mean_reachable_mover',)),
    _f('penetration', 'A',
       'allows movement through or beyond defensive structures',
       'reach past occupied lines increases',
       ('mean_attack_coverage',)),

    # ---- B: threat and capture --------------------------------------
    _f('threat_projection', 'B',
       'expands the set of locations or pieces that can be attacked',
       'attack-map coverage, capturable targets and forced-reply rate rise',
       ('mean_attack_coverage',)),
    _f('threat_concentration', 'B',
       'concentrates attack power in a region or direction',
       'squares covered more than once fall while the number of '
       'attacking pieces does not: the same force spread thinner',
       ('mean_attack_overlap', 'mean_attack_coverage')),
    _f('threat_redistribution', 'B',
       'changes where threats occur without changing total capacity',
       'turns relocating a piece the mover does not own fall, while '
       'captures hold: threats stop moving, capacity never changed',
       ('foreign_turns', 'total_captures')),
    _f('capture_enablement', 'B',
       'creates new ways to remove opposing resources',
       'captures per game rise', ('total_captures',)),
    _f('retaliation', 'B',
       'allows a response conditioned on the opponent\'s preceding action',
       'replies that only the opponent\'s preceding action made legal '
       'fall, and so does the standing count of armed responses',
       ('response_turns', 'mean_armed_responses')),
    _f('pinning_immobilization', 'B',
       'restricts an opponent because moving would trigger a penalty',
       'opponent effective branching falls without a legal-move change',
       ('mean_branching',)),

    # ---- C: space and control ---------------------------------------
    _f('space_control', 'C',
       'changes which regions can be safely occupied or traversed',
       'safe occupancy for the opponent falls; controlled-region coverage '
       'and spatial bottlenecks rise',
       ('mean_attack_coverage', 'mean_reachable_mover')),
    _f('area_denial', 'C',
       'prevents or discourages occupation of a region',
       'empty squares the mover may not enter fall while its piece '
       'count does not',
       ('mean_denied_squares', 'mean_reachable_mover')),
    _f('path_obstruction', 'C',
       'changes routes through persistent or temporary blocking',
       'empty squares the mover may not enter fall and reachable '
       'destinations rise (shares evidence with area_denial)',
       ('mean_denied_squares', 'mean_reachable_mover')),
    _f('shared_object_influence', 'C',
       'lets multiple players control the same neutral element',
       'turns acting on an element owned by neither side fall to zero, '
       'and both players lose them',
       ('shared_entity_turns',)),

    # ---- D: survival and protection ---------------------------------
    _f('survivability', 'D',
       'reduces the probability of immediate or forced capture',
       'capture probability falls; expected survival time and escape-route '
       'count rise; forced-loss probability falls',
       ('total_captures', 'total_turns')),
    _f('temporary_protection', 'D',
       'provides protection for a limited duration or condition',
       'pieces that cannot be captured this turn fall to zero and '
       'captures rise',
       ('mean_protected_pieces', 'total_captures')),
    _f('royal_preservation', 'D',
       'protects a piece whose loss contributes to termination',
       'games ending by royal capture become less frequent or later',
       ('loss_reason', 'total_turns')),
    _f('sacrificial_clearance', 'D',
       'removes friendly material to create opportunity',
       'turns that take the mover\'s own material off the board fall',
       ('self_removal_turns',)),

    # ---- E: transformation and resource configuration ---------------
    _f('piece_transformation', 'E',
       'changes a piece\'s legal abilities or identity',
       'the transforming action type disappears from the legal set',
       ('mean_action_types',)),
    _f('tactical_reconfiguration', 'E',
       'changes the available tactical role of an existing piece',
       'turns changing a piece\'s abilities without moving it fall, and '
       'the kinds of turn available fall with them',
       ('mode_change_turns', 'mean_action_types')),
    _f('power_preservation', 'E',
       'maintains aggregate capability while changing its form',
       'changing form again after having changed once stops happening: '
       'form becomes one-way, so it is spent rather than kept',
       ('mode_reentry_turns', 'mean_action_types')),
    _f('piece_type_balancing', 'E',
       'prevents excessive accumulation or loss of one type',
       'the largest holding of any one kind rises and the number of '
       'surviving kinds falls',
       ('mean_max_same_type', 'mean_distinct_types')),
    _f('resource_conversion', 'E',
       'exchanges one form of game resource for another',
       'turns replacing one kind of resource with another fall to zero '
       'and the spread of kinds stops shifting',
       ('conversion_turns', 'mean_distinct_types')),

    # ---- F: time, history, and persistence --------------------------
    _f('cycle_prevention', 'F',
       'prevents repeated-state loops',
       'repeated-state frequency falls; probability of indefinite or '
       'maximum-turn play falls',
       ('repeated_state_frequency', 'turn_cap_reached')),
    _f('historical_dependency', 'F',
       'makes legality or effects depend on previous states or actions',
       'decisions removed by a record of earlier turns fall, and so do '
       'the conditions that record leaves standing',
       ('repetition_blocks', 'endgame_blocks', 'mean_restrained_pieces')),
    _f('cooldown_regulation', 'F',
       'temporarily prevents immediate reuse or reversal',
       'entities barred from acting because they acted recently fall to '
       'zero (shares evidence with state_persistence)',
       ('mean_restrained_pieces',)),
    _f('state_persistence', 'F',
       'creates a condition that remains active across turns',
       'conditions still in force from an earlier turn fall to zero',
       ('mean_restrained_pieces', 'mean_protected_pieces',
        'mean_armed_responses')),
    _f('anti_drift_control', 'F',
       'limits prolonged play without irreversible progress',
       'non-progress intervals and upper-tail game length fall',
       ('total_turns',)),

    # ---- G: termination and outcome structure -----------------------
    _f('termination_guarantee', 'G',
       'ensures all legal play sequences eventually terminate',
       'games reaching the turn cap fall to zero',
       ('turn_cap_reached', 'decisive')),
    _f('termination_acceleration', 'G',
       'reduces expected or tail game duration',
       'median and upper-tail game length fall',
       ('total_turns',)),
    _f('draw_suppression', 'G',
       'reduces the occurrence of draw outcomes',
       'draw rate falls',
       ('decisive',)),
    _f('outcome_balancing', 'G',
       'reduces first-player, side, or role advantage',
       'side-specific win disparity falls',
       ('white_win', 'black_win')),
    _f('delayed_victory', 'G',
       'requires additional objectives before a win is awarded',
       'time from first decisive advantage to termination rises',
       ('total_turns', 'loss_reason')),
    _f('objective_salience', 'G',
       'raises the importance of a particular piece, region or resource',
       'endings attributable to losing it fall as a share, and distance '
       'to it stops governing where play happens',
       ('loss_reason', 'mean_objective_distance')),

    # ---- H: choice structure ----------------------------------------
    _f('tactical_flexibility', 'H',
       'increases the number of meaningfully different short-term choices',
       'near-optimal action count and policy-effective branching rise',
       ('mean_policy_branching', 'mean_move_entropy')),
    _f('strategic_diversity', 'H',
       'expands distinct long-horizon plans',
       'the kinds of turn available across a game fall, and using more '
       'than one form stops happening',
       ('mean_action_types', 'mode_change_turns')),
    _f('forced_choice_creation', 'H',
       'reduces the number of viable responses',
       'policy-effective branching falls',
       ('mean_policy_branching',)),
    _f('decision_compression', 'H',
       'removes ineffective or dominated alternatives',
       'legal branching falls while effective branching holds',
       ('mean_branching', 'mean_policy_branching')),
    _f('complexity_without_depth', 'H',
       'increases legal actions without increasing meaningful alternatives',
       'raw legal-action count rises while effective branching, the '
       'optimal-action set and minimax values barely move',
       ('mean_branching', 'mean_policy_branching')),
)

BY_NAME = {f.name: f for f in ONTOLOGY}
BY_CATEGORY = collections.OrderedDict(
    (key, [f for f in ONTOLOGY if f.category == key]) for key in CATEGORIES)

#: Functions with no operational definition yet. They can be predicted
#: from structure but not confirmed or falsified, and Phase 4 must not
#: score them as though they could be.
#:
#: NOT A REASON NOT TO PREDICT ONE. Unfalsifiable is not unpredictable,
#: and the two were conflated here: the gap report used to explain
#: every unpredicted function with no operational definition as being
#: beyond any channel, while ten functions on this same list were being
#: predicted structurally without trouble. What it was really reporting
#: was missing detectors (#215).
NOT_YET_OPERATIONAL = tuple(f.name for f in ONTOLOGY if not f.evidence)

#: Functions that are the NULL RESULT of another, not a separate thing
#: to look for. `complexity_without_depth` is what `tactical_flexibility`
#: turns out to be when the measurement disagrees with the structure:
#: identical shape -- an action carrying a chosen parameter, a piece
#: with several repertoires -- and the opposite outcome, raw legal
#: actions up while effective branching and the optimal-action set
#: stand still. Predicting it from structure would mean predicting the
#: failure of a prediction, so it is listed here instead of being
#: reported as a detector that is missing.
MEASURED_NULLS = {
    'complexity_without_depth': 'tactical_flexibility',
}


def operational():
    return tuple(f for f in ONTOLOGY if f.evidence)


def shared_evidence():
    """Groups of functions the measurements cannot tell apart.

    Every function now names quantities that would have to move under
    ablation, and for a few of them those quantities are THE SAME
    quantities. Denying an area and blocking a path both show up as
    squares the mover may not enter; a cooldown and any other condition
    left standing from an earlier turn are both restrained pieces.

    What separates them is not the measurement. For some pairs it is
    the DIRECTION the quantity moves -- expansion from restriction,
    compression from clutter -- and that direction lives in the
    `evidence` prose rather than as data, so nothing checks it. For the
    rest it is the ABLATION: which rule was taken out to make the
    number move.

    This over-reports on purpose. A pair separable by direction is
    listed here anyway, because the thing that would separate them is
    not yet machine-readable, and a limitation that flags one case too
    many is the right way round.
    """
    groups = collections.defaultdict(list)
    for f in ONTOLOGY:
        if f.metrics:
            groups[tuple(sorted(f.metrics))].append(f.name)
    return collections.OrderedDict(
        (metrics, names) for metrics, names in sorted(groups.items())
        if len(names) > 1)


def _wrap(text, width):
    words, line, out = text.split(), '', []
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = '{} {}'.format(line, word).strip()
    if line:
        out.append(line)
    return out


def describe(width=112, name_column=30):
    """The ontology as a readable listing.

    One line per function. The default width clears the longest
    definition in the ontology (66 characters against 78 available), so
    nothing wraps in practice; wrapping remains only so a future longer
    definition degrades into an aligned continuation rather than being
    cut, which is what it used to do.
    """
    indent = 4 + name_column
    lines = []
    for key, title in CATEGORIES.items():
        lines.append('')
        lines.append('{}. {}'.format(key, title.upper()))
        for f in BY_CATEGORY[key]:
            mark = ' ' if f.evidence else '*'
            chunks = _wrap(f.definition, max(width - indent, 30))
            lines.append('  {} {:<{}}{}'.format(
                mark, f.name, name_column, chunks[0] if chunks else ''))
            for chunk in chunks[1:]:
                lines.append('{}{}'.format(' ' * indent, chunk))
    lines.append('')
    if NOT_YET_OPERATIONAL:
        lines.append('* = no operational definition yet: predictable from '
                     'structure, not yet falsifiable ({} of {}).'.format(
                         len(NOT_YET_OPERATIONAL), len(ONTOLOGY)))
    else:
        lines.append('All {} name what would have to move under ablation '
                     'to contradict them.'.format(len(ONTOLOGY)))
    shared = shared_evidence()
    if shared:
        lines.append('')
        lines.append('WHERE THE RESOLUTION ENDS. These are read off the '
                     'SAME quantities.')
        lines.append('Some are separated by the DIRECTION of the movement '
                     '-- expansion from')
        lines.append('restriction, compression from clutter -- and that '
                     'direction is stated in')
        lines.append('prose, not held as data, so nothing checks it. The '
                     'rest are separated')
        lines.append('only by which rule was ablated to make the number '
                     'move:')
        for metrics, names in shared.items():
            lines.append('  {:<38} {}'.format(
                ' + '.join(names), ', '.join(metrics)))
    return '\n'.join(lines)
