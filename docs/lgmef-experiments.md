# LGMEF experiment harness

Infrastructure for the ISEF study "Quantifying Strategic Impact of Game
Mechanics Using a Logic-Based Game Mechanic Evaluation Framework"
(issue #168).

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
| `control_inert` | Negative control — identical to `full`; MCI must read ~0 |
| `control_double_move` | Positive control — mover repeats every 10th turn; MCI must flag it |

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
turn-type counts = mechanic usage, captures, tiny-endgame activation,
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
