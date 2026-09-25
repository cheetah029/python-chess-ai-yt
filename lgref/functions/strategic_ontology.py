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
ablation, and `EXPECTED` says WHICH WAY, as data rather than as prose.

THE FRAME IS ABLATION, EVERYWHERE. Every evidence sentence describes
the game with the rule TAKEN OUT, because taking it out is the
experiment. Half of these once described the rule while PRESENT, which
inverted their apparent direction and went unnoticed for as long as
direction was only a sentence (#220). Where the specification gives an operational definition, it is
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
       'reachable squares and legal destinations fall',
       ('mean_reachable_mover', 'mean_branching')),
    _f('mobility_restriction', 'A',
       'reduces reachable destinations or constrains movement paths',
       'legal moves and reachable-state volume rise',
       ('mean_branching', 'mean_reachable_mover')),
    _f('repositioning', 'A',
       'lets a piece change strategic location without ordinary movement',
       'reachable destinations fall, the unusual ones first',
       ('mean_reachable_mover',)),
    _f('escape_facilitation', 'A',
       'increases the ability to leave threatened or blocked positions',
       'reachable destinations fall, so there is less to escape to',
       ('mean_reachable_mover',)),
    _f('penetration', 'A',
       'allows movement through or beyond defensive structures',
       'attack coverage falls where occupancy used to be passed',
       ('mean_attack_coverage',)),

    # ---- B: threat and capture --------------------------------------
    _f('threat_projection', 'B',
       'expands the set of locations or pieces that can be attacked',
       'attack-map coverage falls',
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
       'captures per game fall', ('total_captures',)),
    _f('retaliation', 'B',
       'allows a response conditioned on the opponent\'s preceding action',
       'replies that only the opponent\'s preceding action made legal '
       'fall, and so does the standing count of armed responses',
       ('response_turns', 'mean_armed_responses')),
    _f('pinning_immobilization', 'B',
       'restricts an opponent because moving would trigger a penalty',
       'the opponent\'s near-optimal action count RISES while the legal '
       'count holds: options come back that were never illegal',
       ('mean_policy_branching', 'mean_branching')),

    # ---- C: space and control ---------------------------------------
    _f('space_control', 'C',
       'changes which regions can be safely occupied or traversed',
       'controlled-region coverage falls and more of the board becomes '
       'traversable',
       ('mean_attack_coverage', 'mean_reachable_mover')),
    _f('area_denial', 'C',
       'prevents or discourages occupation of a region',
       'empty squares the mover may not enter fall and reachable '
       'destinations rise',
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
       'captures per game rise and games end sooner',
       ('total_captures', 'total_turns')),
    _f('temporary_protection', 'D',
       'provides protection for a limited duration or condition',
       'pieces that cannot be captured this turn fall to zero and '
       'captures rise',
       ('mean_protected_pieces', 'total_captures')),
    _f('royal_preservation', 'D',
       'protects a piece whose loss contributes to termination',
       'endings shift towards the loss of that piece, and come sooner',
       ('loss_reason', 'total_turns')),
    _f('sacrificial_clearance', 'D',
       'removes friendly material to create opportunity',
       'turns that take the mover\'s own material off the board fall',
       ('self_removal_turns',)),

    # ---- E: transformation and resource configuration ---------------
    _f('piece_transformation', 'E',
       'changes a piece\'s legal abilities or identity',
       'the kinds of turn available fall by one',
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
       'turns replacing one kind of resource with another fall to zero, '
       'and fewer kinds appear',
       ('conversion_turns', 'mean_distinct_types')),

    # ---- F: time, history, and persistence --------------------------
    _f('cycle_prevention', 'F',
       'prevents repeated-state loops',
       'repeated-state frequency rises, and so does the share of games '
       'stopped by the cap',
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
       'game length rises, in the upper tail first',
       ('total_turns',)),

    # ---- G: termination and outcome structure -----------------------
    _f('termination_guarantee', 'G',
       'ensures all legal play sequences eventually terminate',
       'games reach the cap again, and the decisive share falls',
       ('turn_cap_reached', 'decisive')),
    _f('termination_acceleration', 'G',
       'reduces expected or tail game duration',
       'game length rises',
       ('total_turns',)),
    _f('draw_suppression', 'G',
       'reduces the occurrence of draw outcomes',
       'the decisive share falls',
       ('decisive',)),
    _f('outcome_balancing', 'G',
       'reduces first-player, side, or role advantage',
       'the win split moves away from parity, in either direction',
       ('white_win', 'black_win')),
    _f('delayed_victory', 'G',
       'requires additional objectives before a win is awarded',
       'games end sooner, and the ending kind shifts',
       ('total_turns', 'loss_reason')),
    _f('objective_salience', 'G',
       'raises the importance of a particular piece, region or resource',
       'endings attributable to losing it fall as a share, and distance '
       'to it stops governing where play happens',
       ('loss_reason', 'mean_objective_distance')),

    # ---- H: choice structure ----------------------------------------
    _f('tactical_flexibility', 'H',
       'increases the number of meaningfully different short-term choices',
       'the near-optimal action count falls, and the policy flattens',
       ('mean_policy_branching', 'mean_move_entropy')),
    _f('strategic_diversity', 'H',
       'expands distinct long-horizon plans',
       'the kinds of turn available across a game fall, and using more '
       'than one form stops happening',
       ('mean_action_types', 'mode_change_turns')),
    _f('forced_choice_creation', 'H',
       'reduces the number of viable responses',
       'the near-optimal action count rises',
       ('mean_policy_branching',)),
    _f('decision_compression', 'H',
       'removes ineffective or dominated alternatives',
       'legal branching RISES while the near-optimal count holds: the '
       'pruned-away options come back and none of them matter',
       ('mean_branching', 'mean_policy_branching')),
    _f('complexity_without_depth', 'H',
       'increases legal actions without increasing meaningful alternatives',
       'the legal count FALLS while the near-optimal count holds: what '
       'goes away was never worth choosing',
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

#: WHICH WAY A METRIC MUST MOVE, and the frame it is read in.
#:
#: THE FRAME IS ABLATION. Every `evidence` sentence and every entry
#: below describes what happens when the rule is TAKEN OUT, because
#: taking it out is the experiment. That convention was stated in this
#: module from the start and half the ontology did not follow it: a
#: dozen entries described what the rule does while PRESENT, so their
#: apparent direction was inverted. `mobility_expansion` read "reachable
#: squares ... all increase" -- true of the rule, backwards as a
#: prediction about its ablation. Nothing caught it because direction
#: lived in prose (#220).
UP, DOWN, FLAT, SHAPE = 'up', 'down', 'flat', 'shape'
DIRECTIONS = (UP, DOWN, FLAT, SHAPE)

#: FLAT is a prediction, not an absence of one. "Threats move while
#: capacity holds" is falsified by capacity moving, and a rule whose
#: control clause fails is not doing what was claimed.
#:
#: SHAPE marks a metric that is not a level: a categorical ending
#: reason, or a win split whose prediction is "away from parity" in
#: either direction. Phase 5 has to test those differently rather than
#: compare means, and saying so beats coercing them into a sign.
EXPECTED = {
    'mobility_expansion': {'mean_reachable_mover': DOWN,
                           'mean_branching': DOWN},
    'mobility_restriction': {'mean_branching': UP,
                             'mean_reachable_mover': UP},
    'repositioning': {'mean_reachable_mover': DOWN},
    'escape_facilitation': {'mean_reachable_mover': DOWN},
    'penetration': {'mean_attack_coverage': DOWN},
    'threat_projection': {'mean_attack_coverage': DOWN},
    'threat_concentration': {'mean_attack_overlap': DOWN,
                             'mean_attack_coverage': FLAT},
    'threat_redistribution': {'foreign_turns': DOWN,
                              'total_captures': FLAT},
    'capture_enablement': {'total_captures': DOWN},
    'retaliation': {'response_turns': DOWN, 'mean_armed_responses': DOWN},
    'pinning_immobilization': {'mean_policy_branching': UP,
                               'mean_branching': FLAT},
    'space_control': {'mean_attack_coverage': DOWN,
                      'mean_reachable_mover': UP},
    'area_denial': {'mean_denied_squares': DOWN,
                    'mean_reachable_mover': UP},
    'path_obstruction': {'mean_denied_squares': DOWN,
                         'mean_reachable_mover': UP},
    'shared_object_influence': {'shared_entity_turns': DOWN},
    'survivability': {'total_captures': UP, 'total_turns': DOWN},
    'temporary_protection': {'mean_protected_pieces': DOWN,
                             'total_captures': UP},
    'royal_preservation': {'loss_reason': SHAPE, 'total_turns': DOWN},
    'sacrificial_clearance': {'self_removal_turns': DOWN},
    'piece_transformation': {'mean_action_types': DOWN},
    'tactical_reconfiguration': {'mode_change_turns': DOWN,
                                 'mean_action_types': DOWN},
    'power_preservation': {'mode_reentry_turns': DOWN,
                           'mean_action_types': FLAT},
    'piece_type_balancing': {'mean_max_same_type': UP,
                             'mean_distinct_types': DOWN},
    'resource_conversion': {'conversion_turns': DOWN,
                            'mean_distinct_types': DOWN},
    'cycle_prevention': {'repeated_state_frequency': UP,
                         'turn_cap_reached': UP},
    'historical_dependency': {'repetition_blocks': DOWN,
                              'endgame_blocks': DOWN,
                              'mean_restrained_pieces': DOWN},
    'cooldown_regulation': {'mean_restrained_pieces': DOWN},
    'state_persistence': {'mean_restrained_pieces': DOWN,
                          'mean_protected_pieces': DOWN,
                          'mean_armed_responses': DOWN},
    'anti_drift_control': {'total_turns': UP},
    'termination_guarantee': {'turn_cap_reached': UP, 'decisive': DOWN},
    'termination_acceleration': {'total_turns': UP},
    'draw_suppression': {'decisive': DOWN},
    'outcome_balancing': {'white_win': SHAPE, 'black_win': SHAPE},
    'delayed_victory': {'total_turns': DOWN, 'loss_reason': SHAPE},
    'objective_salience': {'loss_reason': SHAPE,
                           'mean_objective_distance': UP},
    'tactical_flexibility': {'mean_policy_branching': DOWN,
                             'mean_move_entropy': DOWN},
    'strategic_diversity': {'mean_action_types': DOWN,
                            'mode_change_turns': DOWN},
    'forced_choice_creation': {'mean_policy_branching': UP},
    'decision_compression': {'mean_branching': UP,
                             'mean_policy_branching': FLAT},
    'complexity_without_depth': {'mean_branching': DOWN,
                                 'mean_policy_branching': FLAT},
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

    Grouped on (metric, DIRECTION) rather than on the metric alone,
    which is what makes the list mean something. Expansion and
    restriction name the same two quantities and predict opposite
    movements; so do compression and clutter. Keyed on names they read
    as indistinguishable, and both pairs used to appear here. Keyed on
    the prediction they do not, and two genuine collisions that were
    hidden behind them do -- `repositioning` with `escape_facilitation`,
    `anti_drift_control` with `termination_acceleration`.

    What is left is separated only by the ABLATION: which rule was
    taken out to make the number move. That is a real limit on the
    resolution of this instrument, and it is smaller and truer than the
    one the name-keyed version reported.
    """
    groups = collections.defaultdict(list)
    for f in ONTOLOGY:
        if f.metrics:
            groups[tuple(sorted(EXPECTED[f.name].items()))].append(f.name)
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
        lines.append('WHERE THE RESOLUTION ENDS. These predict the SAME '
                     'movement of the')
        lines.append('same quantities, so nothing in the measurement '
                     'separates them -- only')
        lines.append('which rule was ablated to make the number move. '
                     'Directions are read')
        lines.append('in the ABLATION frame: what happens when the rule '
                     'is taken out.')
        for pairs, names in shared.items():
            lines.append('  {:<38} {}'.format(
                ' + '.join(names),
                ', '.join('{} {}'.format(m, d) for m, d in pairs)))
    return '\n'.join(lines)
