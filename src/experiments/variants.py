"""Named LGREF ablation variants of Royal Chess.

Each variant is the FULL v2 rule set minus exactly one RULE (or a
named combination), expressed as GameEngine keyword arguments. The GDL
step files in docs/gdl/ are the formal specification of the same
ablations (e.g. no_boulder ~ building without step6_add_boulder.gdl);
the engine is the fast execution substrate, and the GDL cross-validation
harness (src/ggp/cross_validation.py) is the bridge proving the two
agree. Training runs and metric collection always go through the
engine; variant IDENTITY is defined here so every tool (trainer,
well-formedness gate, analysis) names variants the same way.

Controls (feedback item: validate the RCI instrument before headline
results):
  control_inert       — identical to 'full'. A correct RCI pipeline
                        must measure ~0 impact for it (negative
                        control / noise floor).
  control_double_move — extra_move_every=10: the mover gets an
                        immediate second turn every 10th turn. A
                        deliberately broken, obviously impactful
                        rule that RCI must flag (positive
                        control). Never a real rule proposal.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VariantSpec:
    name: str
    description: str
    engine_kwargs: dict = field(default_factory=dict)
    is_control: bool = False


_SPECS = [
    VariantSpec(
        'full',
        'Full Royal Chess v2 rule set (all rules on).'),
    VariantSpec(
        'no_boulder',
        'Full rules minus the neutral boulder (removed from the '
        'initial position).',
        {'enable_boulder': False}),
    VariantSpec(
        'no_tiny_endgame',
        'Full rules minus the tiny-endgame rule (never activates).',
        {'enable_tiny_endgame': False}),
    VariantSpec(
        'no_queen_manipulation',
        'Full rules minus queen manipulation (manipulation turns are '
        'not generated).',
        {'enable_manipulation': False}),
    VariantSpec(
        'no_knight_redesign',
        'MISLEADING NAME, KEPT FOR CONTINUITY. It does NOT isolate the '
        'knight redesign. Measured against `full` at the initial '
        'position and over played games: knight destinations are '
        'IDENTICAL (radius-2 in both), the pre-v2 jump-capture it '
        'substitutes is BROADER than v2 (any capturable enemy adjacent '
        'to the landing square, not just the jumped piece), and leap '
        'invulnerability is granted MORE often, not less (40 '
        'occurrences against 7 over three matched games). The old '
        'description claimed the reverse of all three. See issue #228; '
        'nothing measured through this variant may be attributed to '
        'the redesign.',
        {'knight_mode': 'legacy'}),
    VariantSpec(
        'baseline',
        'All studied rules ablated at once: no boulder, no tiny '
        'endgame, no manipulation, legacy knight. The closest-to-'
        'standard-chess reference point of the study.',
        {'enable_boulder': False, 'enable_tiny_endgame': False,
         'enable_manipulation': False, 'knight_mode': 'legacy'}),
    VariantSpec(
        'control_inert',
        'Negative control: rule-identical to full. Measured RCI must '
        'be ~0 (noise floor of the instrument).',
        {}, is_control=True),
    VariantSpec(
        'control_double_move',
        'Positive control: the mover takes an immediate second turn '
        'every 10th turn — deliberately broken; RCI must flag it.',
        {'extra_move_every': 10}, is_control=True),
]

VARIANTS = {spec.name: spec for spec in _SPECS}


def get_variant(name):
    """Return the VariantSpec for `name`, raising with the valid list."""
    try:
        return VARIANTS[name]
    except KeyError:
        raise ValueError(
            f'Unknown variant {name!r}. Valid: {sorted(VARIANTS)}') from None


def make_engine(name, max_turns=1000, manipulation_mode='freeze'):
    """Construct a GameEngine configured for the named variant."""
    from engine import GameEngine
    spec = get_variant(name)
    return GameEngine(max_turns=max_turns,
                      manipulation_mode=manipulation_mode,
                      **spec.engine_kwargs)
