"""Strategic-function classes, each carrying a prediction that can fail.

Phase 2. A class here is not a name attached to a cluster. It is a
STRUCTURAL SIGNATURE -- detectable from the clause graph, before any
game is played -- paired with a CAUSAL SIGNATURE, a committed claim
about what ablating that rule will do.

The pairing is what makes the phase worth running. Phase 3 measures the
effect of removing each rule. A label assigned after seeing those
numbers would fit whatever they were; a label written first can turn out
wrong, and only then is it evidence.

GAME-AGNOSTIC BY CONSTRUCTION. Detectors use GDL's own reserved words
(`legal`, `next`, `true`, `does`, `terminal`, `goal`) and the action
names derived from the description under analysis. Nothing names a
Royal Chess concept -- the framework has to do this for any GDL game,
and `lgref/tests/test_label_isolation.py` fails the build if the
designer's held-out labels are reached from here.

CONFIDENCE IS EVIDENCE STRENGTH, NOT PROBABILITY. It reports how much
of a cluster matches a signature. Whether the label is CORRECT is
decided by the ablation, in Phase 4. Reading it as a probability of
being right would be a claim this phase cannot support.
"""

import collections

FunctionClass = collections.namedtuple(
    'FunctionClass', 'name question prediction metric direction')

StrategicClass = collections.namedtuple(
    'StrategicClass', 'name question signature metric scope')

#: Each class states the question it answers about a rule, the effect
#: ablation is predicted to have, the Phase 3 metric that measures it,
#: and the direction expected. `direction` is 'increase', 'decrease' or
#: 'change' -- 'change' where the sign is not predictable in advance,
#: which is weaker evidence and is marked as such rather than dressed up.
ONTOLOGY = (
    FunctionClass(
        'termination_pressure',
        'does this rule push the game towards ending?',
        'games end differently: sooner, later, or stop ending at all',
        'termination_rate_and_length', 'change'),
    FunctionClass(
        'move_restriction',
        'does this rule take options away?',
        'removing it leaves MORE legal moves',
        'legal_moves_at_sampled_positions', 'increase'),
    FunctionClass(
        'move_generation',
        'does this rule provide a way to act?',
        'removing it leaves FEWER legal moves, perhaps none of its action',
        'legal_moves_at_sampled_positions', 'decrease'),
    FunctionClass(
        'cross_turn_memory',
        'does this rule carry information between turns?',
        'behaviour changes only where the remembered state was set',
        'conditional_action_frequency', 'change'),
    FunctionClass(
        'state_conversion',
        'does this rule change what a piece IS?',
        'that action type disappears from the legal set',
        'action_type_counts', 'decrease'),
    FunctionClass(
        'capture_regime',
        'does this rule govern pieces being removed?',
        'captures per game change',
        'captures_per_game', 'change'),
    FunctionClass(
        'turn_structure',
        'does this rule govern whose turn it is?',
        'alternation breaks; expect the ablation to be unplayable',
        'playable', 'decrease'),
)

BY_NAME = {f.name: f for f in ONTOLOGY}


# ---------------------------------------------------------------------------
# The STRATEGIC layer.
#
# The classes above are OPERATIONAL: they describe what a rule does to the
# legal-move set and to stored state. Those are mechanisms, and running
# inference produces them repetitively because most rules are built from a
# handful of mechanisms.
#
# A strategic function is about how a rule shapes PLAY -- the designer's own
# seed vocabulary has `space_control`, which no operational class can express.
# Strategy is a claim about behaviour, so it cannot be read off a clause graph;
# it needs the measured effect of ablation, which Phase 3 now produces.
#
# So these are still PRE-REGISTERED -- Phase 2 states which strategic function
# a rule is predicted to serve and by what measured signature -- but they are
# CONFIRMED in Phase 4 against the numbers. Assigning them after seeing the
# numbers is the failure this whole design exists to avoid.
#
# `scope` is honest about genericity. `core` classes rest on metrics any GDL
# game has: branching, length, decisiveness, balance. `board` classes rest on
# spatial metrics, and apply only to games that expose them -- calling a board
# concept universal would be false.
# ---------------------------------------------------------------------------

STRATEGIC = (
    StrategicClass(
        'complexity',
        'does this rule change how many options players face?',
        'branching factor shifts materially',
        'mean_branching', 'core'),
    StrategicClass(
        'tempo',
        'does this rule change how quickly the game resolves?',
        'game length shifts materially',
        'total_turns', 'core'),
    StrategicClass(
        'decisiveness',
        'does this rule change whether games reach a result?',
        'decisive rate shifts',
        'decisive_rate', 'core'),
    StrategicClass(
        'initiative',
        'does this rule favour one side?',
        'the winner balance shifts between sides',
        'white_win', 'core'),
    StrategicClass(
        'closure',
        'does this rule make endings predictable or erratic?',
        'the spread of game lengths tightens or widens',
        'total_turns_variance', 'core'),
    StrategicClass(
        'space_control',
        'does this rule govern which squares can be used?',
        'reachable squares or attack coverage shift materially',
        'mean_reachable_mover', 'board'),
)

STRATEGIC_BY_NAME = {s.name: s for s in STRATEGIC}


def strategic_scope(metrics_available):
    """Which strategic classes this game can actually support.

    A board class is dropped when the game does not expose the metric
    rather than being scored against a missing column, because a
    silently absent measurement is how a null result gets manufactured.
    """
    usable = []
    for entry in STRATEGIC:
        if entry.scope == 'core' or entry.metric in metrics_available:
            usable.append(entry)
    return usable


def describe_strategic():
    """The strategic layer as text."""
    lines = ['{:<16} {:<48} {:<24} {}'.format(
        'function', 'signature under ablation', 'metric', 'scope')]
    lines.append('-' * 100)
    for s in STRATEGIC:
        lines.append('{:<16} {:<48} {:<24} {}'.format(
            s.name, s.signature[:48], s.metric, s.scope))
    return '\n'.join(lines)


def describe():
    """The operational ontology as text.

    OPERATIONAL, and labelled so. These classes say what a rule does to
    the move set and to state -- mechanism, not strategy. The strategic
    layer is `describe_strategic()`, and is confirmed from measurement
    rather than from structure.
    """
    lines = ['{:<22} {:<46} {}'.format('class', 'predicted ablation effect',
                                       'metric')]
    lines.append('-' * 100)
    for f in ONTOLOGY:
        lines.append('{:<22} {:<46} {} ({})'.format(
            f.name, f.prediction[:46], f.metric, f.direction))
    return '\n'.join(lines)
