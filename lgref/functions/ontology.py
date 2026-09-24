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


def describe():
    """The ontology as text, for the frozen artefact and the report."""
    lines = ['{:<22} {:<46} {}'.format('class', 'predicted ablation effect',
                                       'metric')]
    lines.append('-' * 100)
    for f in ONTOLOGY:
        lines.append('{:<22} {:<46} {} ({})'.format(
            f.name, f.prediction[:46], f.metric, f.direction))
    return '\n'.join(lines)
