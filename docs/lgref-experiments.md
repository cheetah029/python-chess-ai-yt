# LGREF experiment harness

Infrastructure for the ISEF study "Quantifying Strategic Impact of Game
Rules Using a Logic-Based Game Rule Evaluation Framework"
(issue #168).

## Vocabulary

LGREF distinguishes four levels. The paper defines this convention once and
then uses it consistently; "mechanic" is not part of the framework's core
vocabulary, and stays available for ordinary game-design discussion.

| Term | Meaning | Example |
|---|---|---|
| **Formal clause** | One statement in the game's formal representation (a GDL fact or implication). | The condition specifying when promotion is legal. |
| **Rule** | A gameplay provision implemented by one or more formal clauses. | Pawn promotion, bishop teleportation, repetition control. |
| **Strategic function** | The strategic role the rule may serve. | Tactical flexibility, cycle prevention. |
| **Contribution** | Its measured effect under a specified comparison. | Change in game duration when the rule is disabled. |

Pipeline: **formal clauses → rules → strategic functions → measured
contributions → recommendations.**

A rule may be implemented by several formal clauses, and one clause may support
several rules. Rules are grouped by the behaviour their clauses jointly
implement — *not* by a shared strategic function. Two rules that both aid escape
remain two rules.

The task is therefore **rule identification**, not rule discovery: the rules
already exist in the game description, and the system identifies their
constituent clauses and boundaries.

Three distinctions the pipeline encodes explicitly:

1. **Intended vs hypothesized vs supported functions.** A designer's intended
   function is an annotation; an inferred function is a hypothesis; a supported
   function has evidence. These are never treated as interchangeable — the seed
   ontology labels are annotations and are held out from inference.
2. **Operational properties vs strategic functions.** *Historical dependency*,
   *state persistence* and *piece transformation* describe how a rule operates.
   *Cycle prevention*, *escape facilitation* and *tactical flexibility* describe
   what role it may serve. Only the latter are strategic functions.
3. **Effect vs value.** A rule increasing game length is a measured effect.
   Whether that is desirable depends on the stated design objective, so
   contribution profiles report direction and magnitude without treating a
   positive number as an improvement.

The summary index over a Rule Contribution Profile is the **Rule Contribution
Index (RCI)**, reported under several stated weightings rather than as a
discovered constant.


## Architecture

- **GDL step files** (`docs/gdl/`) are the formal *specification* of
  each ablation (e.g. *No Boulder* ≈ building without
  `step6_add_boulder.gdl`).
- **The Python engine** is the *execution substrate*: ~35× faster than
  the GDL resolver (measured 196 vs 5.7 moves/s), and already
  cross-validated against the GDL (`src/ggp/cross_validation.py`).
- **`src/experiments/variants.py`** defines variant *identity*: one
  named `VariantSpec` per ablation, expressed as `GameEngine` kwargs.

## Variants

| Name | Ablation |
|---|---|
| `full` | Complete v2 rule set |
| `no_boulder` | Boulder removed from the initial position |
| `no_tiny_endgame` | Tiny-endgame rule never activates |
| `no_queen_manipulation` | Manipulation turns not generated |
| `no_knight_redesign` | Legacy knight (no radius-2/jump-capture/invulnerability) |
| `baseline` | All four ablations at once |
| `control_inert` | Negative control — identical to `full`; RCI must read ~0 |
| `control_double_move` | Positive control — mover repeats every 10th turn; RCI must flag it |

## Running

```bash
# Well-formedness gate only (random playouts, no training):
python src/run_experiment.py --variant no_boulder --check

# One (variant, seed) training run — gate runs first, then training:
python src/run_experiment.py --variant no_boulder --seed 2 --iters 50
```

Outputs land in `models/experiments/<variant>/seed<k>/`:
`experiment.json` (provenance), `wellformedness.json`,
`model_iter_*.pt`, `training_history.json`, and `games/iter_*.jsonl`
whose rows carry a `metrics` dict (avg/max branching factor, executed
turn-type counts = rule usage, captures, tiny-endgame activation,
repetition/endgame blocks).

## Notes

- `no_queen_manipulation` semantics: the no-legal-moves loss check
  still uses full rules, so a position whose only legal turns are
  manipulations surfaces as an empty turn list → treated as a draw.
- Move entropy of the trained policy is an analysis-time metric
  (evaluate checkpoints on a fixed position set), not logged per game.
- ISEF logistics: Forms 1/1A/1B and the research plan must be approved
  before data-collection runs; the gate and infrastructure tests are
  fine to run now.
