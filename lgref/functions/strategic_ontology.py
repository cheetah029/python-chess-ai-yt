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
       'concentrates attack power in a region or direction', None),
    _f('threat_redistribution', 'B',
       'changes where threats occur without changing total capacity', None),
    _f('capture_enablement', 'B',
       'creates new ways to remove opposing resources',
       'captures per game rise', ('total_captures',)),
    _f('retaliation', 'B',
       'allows a response conditioned on the opponent\'s preceding action',
       None),
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
       'prevents or discourages occupation of a region', None),
    _f('path_obstruction', 'C',
       'changes routes through persistent or temporary blocking', None),
    _f('shared_object_influence', 'C',
       'lets multiple players control the same neutral element',
       None),

    # ---- D: survival and protection ---------------------------------
    _f('survivability', 'D',
       'reduces the probability of immediate or forced capture',
       'capture probability falls; expected survival time and escape-route '
       'count rise; forced-loss probability falls',
       ('total_captures', 'total_turns')),
    _f('temporary_protection', 'D',
       'provides protection for a limited duration or condition', None),
    _f('royal_preservation', 'D',
       'protects a piece whose loss contributes to termination',
       'games ending by royal capture become less frequent or later',
       ('loss_reason', 'total_turns')),
    _f('sacrificial_clearance', 'D',
       'removes friendly material to create opportunity', None),

    # ---- E: transformation and resource configuration ---------------
    _f('piece_transformation', 'E',
       'changes a piece\'s legal abilities or identity',
       'the transforming action type disappears from the legal set',
       ('action_type_counts',)),
    _f('tactical_reconfiguration', 'E',
       'changes the available tactical role of an existing piece', None),
    _f('power_preservation', 'E',
       'maintains aggregate capability while changing its form', None),
    _f('piece_type_balancing', 'E',
       'prevents excessive accumulation or loss of one type', None),
    _f('resource_conversion', 'E',
       'exchanges one form of game resource for another', None),

    # ---- F: time, history, and persistence --------------------------
    _f('cycle_prevention', 'F',
       'prevents repeated-state loops',
       'repeated-state frequency falls; probability of indefinite or '
       'maximum-turn play falls',
       ('repeated_state_frequency', 'turn_cap_reached')),
    _f('historical_dependency', 'F',
       'makes legality or effects depend on previous states or actions',
       None),
    _f('cooldown_regulation', 'F',
       'temporarily prevents immediate reuse or reversal', None),
    _f('state_persistence', 'F',
       'creates a condition that remains active across turns', None),
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
       None),

    # ---- H: choice structure ----------------------------------------
    _f('tactical_flexibility', 'H',
       'increases the number of meaningfully different short-term choices',
       'near-optimal action count and policy-effective branching rise',
       ('policy_effective_branching', 'move_entropy')),
    _f('strategic_diversity', 'H',
       'expands distinct long-horizon plans', None),
    _f('forced_choice_creation', 'H',
       'reduces the number of viable responses',
       'policy-effective branching falls',
       ('policy_effective_branching',)),
    _f('decision_compression', 'H',
       'removes ineffective or dominated alternatives',
       'legal branching falls while effective branching holds',
       ('mean_branching', 'policy_effective_branching')),
    _f('complexity_without_depth', 'H',
       'increases legal actions without increasing meaningful alternatives',
       'raw legal-action count rises while effective branching, the '
       'optimal-action set and minimax values barely move',
       ('mean_branching', 'policy_effective_branching')),
)

BY_NAME = {f.name: f for f in ONTOLOGY}
BY_CATEGORY = collections.OrderedDict(
    (key, [f for f in ONTOLOGY if f.category == key]) for key in CATEGORIES)

#: Functions with no operational definition yet. They can be predicted
#: from structure but not confirmed or falsified, and Phase 4 must not
#: score them as though they could be.
NOT_YET_OPERATIONAL = tuple(f.name for f in ONTOLOGY if not f.evidence)


def operational():
    return tuple(f for f in ONTOLOGY if f.evidence)


def describe():
    lines = []
    for key, title in CATEGORIES.items():
        lines.append('')
        lines.append('{}. {}'.format(key, title.upper()))
        for f in BY_CATEGORY[key]:
            mark = ' ' if f.evidence else '*'
            lines.append('  {} {:<28} {}'.format(mark, f.name,
                                                 f.definition[:44]))
    lines.append('')
    lines.append('* = no operational definition yet: predictable from '
                 'structure, not yet falsifiable ({} of {}).'.format(
                     len(NOT_YET_OPERATIONAL), len(ONTOLOGY)))
    return '\n'.join(lines)
