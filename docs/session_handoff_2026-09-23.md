# Session handoff — 2026-09-23

State at the end of a long working session. **Read
`docs/spec/README.md` first**: it points at the execution brief and the
project outline, and says which is authoritative for what.

## Where the project is

| phase | state |
|---|---|
| 0.5 cross-validation | done — GDL reproduces the engine, 1200/1200, ratcheted |
| 1 rule identification | done and reproducible |
| 1b ablation operations | done — relax, remove, replace (parameter perturbation) |
| 2 function inference | done — 40-function ontology, 39 of 40 predicted |
| 3 contribution measurement | pilot done; 1440-game sweep finished |
| 4 analysis | built; run on the full 1440-game sweep |
| 5–7 | not built |

## The sweep, and what it answered

The 1440-game sweep finished (`lgref/config/phase4_sweep.yaml`, run id
`phase4-sweep`, in `results/lgref/phase4-sweep/`):

```bash
.venv/bin/python -m lgref.analysis.run --results results/lgref/phase4-sweep
```

**The question was:** at 18 games per variant, **33 of 49 profile
cells came back `seed-dominated`**. Does collecting more resolve them?

**It did not.** At 1440 games: **14 effect, 4 inconclusive, 31
seed-dominated**. Ten times the data moved two cells.

**READ THE DESIGN BEFORE READING THAT NUMBER.** The sweep is 8 variants
× **3 seed groups** × 60 games. It scaled games *within* a group from 6
to 60; it did **not** add seed groups. `variance_share` computes its
between-seed term as the variance of the SEED-GROUP MEANS, so:

- growing games per group shrinks that term (each group mean is an
  average of 60 independent games rather than 6), and it still did not
  rescue the cells — so for those 31, the ablation's effect on that
  metric is genuinely small beside the run-to-run spread, not
  under-sampled;
- the term is nevertheless estimated from **three numbers**, which is
  two degrees of freedom however many games back them. The share is
  therefore noisy in a way more games cannot fix. **More seed groups,
  not more games**, is what would tighten it — `seeds: [0, 1, 2]` in
  the config is the line to change.

`control_inert` is seed-dominated on every dimension, which is the
control behaving exactly as it should. `control_double_move` ranks
[1, 1, 3, 7] across the four objectives — the rank instability the
design predicted would appear.

## Commands

```bash
.venv/bin/python -m lgref status
.venv/bin/python -m lgref functions  --gdl docs/gdl/integrated.gdl
.venv/bin/python -m lgref ablations  --gdl docs/gdl/integrated.gdl
.venv/bin/python -m lgref all        --gdl docs/gdl/integrated.gdl
.venv/bin/python -m lgref.identify.gate     --config lgref/config/phase1_gate.yaml
.venv/bin/python -m lgref.experiments.pilot --config lgref/config/phase3_pilot.yaml
.venv/bin/python -m lgref.analysis.run      --results results/lgref/phase4-data
```

**Always `.venv/bin/python`.** A bare `python3` resolves to the system
interpreter on this machine, which has none of the project's packages.

Tests: `pytest lgref/tests -m "not slow"` (285 passing) and
`pytest tests/` (1525 passing, ~12 min). The full `tests/` run only
became possible this session; it used to die during collection.

## Things that are true and easy to get wrong

- **This variant has NO draw condition.** An unfinished game is
  *censored*, not drawn. Earlier runs at turn cap 100 reported agents
  "mostly drawing" when 0 of 40 games had finished. Outcome metrics
  require cap ≥ 800; `require_outcome_safe_cap` enforces it.
- **The mobility agent approximates MATERIAL, not the loss conditions.**
  An earlier claim that it tracks the mobility-exhaustion losses was
  wrong — all games end by `royals_captured`. It is a game-specific
  proxy, and effects measured with it are agent-conditional.
- **MCTS is sound but unaffordable here.** It scores 89% against exact
  play on tic-tac-toe, yet on Royal Chess a 68-wide root and 40
  simulations give 0.59 visits per move, so it round-robins. Not a bug.
- **Clustering resolution is calibrated on coverage, not mean cluster
  size.** Targeting mean size rewards ejecting clauses into singletons.
- **Language clusters are never labelled** — coordinate arithmetic has
  no strategic function.
- **The seed labels in `lgref/reference/` must stay unreachable** from
  `identify/` and `functions/`; a test enforces it.

## Open issues worth picking up

- **#196** — structural recombination for the `replace` mode ("what if
  the knight moved like a rook?"). A movement *shape* is language, which
  is what makes this mechanical.
- **Phase 5–7** — recommendation engine, evidence-constrained
  explanation, results package.
- **17 ontology functions have no operational definition**, so Phase 4
  will not score them. They ARE predicted structurally, and the
  distinction matters: an earlier gap report treated unfalsifiable as
  unpredictable and used it to explain away nine functions this game
  has (#215). `lgref functions` now reports only two reasons for a
  function going unpredicted, and only one of them is a shortcoming.
- **The 1440-game parquet predates three metrics the sweep now
  records** — `mean_policy_branching`, `mean_move_entropy`,
  `mean_action_types` (#216). Old and new parts read together, and the
  columns stay empty until a sweep runs with the current code, so
  anything that turns on near-optimal action count needs a rerun:

  ```bash
  .venv/bin/python -u -m lgref.experiments.pilot \
      --config lgref/config/phase4_sweep.yaml --run-id phase4-sweep-v2
  ```

  `mean_policy_branching` against `mean_branching` is the whole
  distinction between `tactical_flexibility` and
  `complexity_without_depth`; nothing consumes it until Phase 5.
- **Royal Chess has no hand-labelled ground truth.** Identification
  accuracy is reported on tic-tac-toe and nim only. Labelling the real
  case study was offered and not taken up; it is the difference between
  "ARI on two toy games" and accuracy on the subject.

## Recurring mistakes, recorded so they stop recurring

See `memory/feedback_measurement_discipline.md`. The short version:
never extrapolate a schedule from one timing sample; always run long
jobs unbuffered with progress; and **mutate the fix back to prove a
regression test actually fails** — several tests here passed against
known-broken builds until they were moved to where the bug lived.

Two more from this session: a loop that looks like it advances state
often does not (three separate harness bugs), and a comparison taken at
the opening position is not a comparison, because that is exactly where
nothing differs.
