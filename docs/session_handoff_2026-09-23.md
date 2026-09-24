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
| 2 function inference | done — 40-function ontology, pre-registered |
| 3 contribution measurement | pilot done; **1440-game sweep running** |
| 4 analysis | built, run on 144 games; needs rerun on the sweep |
| 5–7 | not built |

## The one thing in flight

A 1440-game sweep (`lgref/config/phase4_sweep.yaml`, run id
`phase4-sweep`) writing to `results/lgref/phase4-sweep/`. When it
finishes:

```bash
.venv/bin/python -m lgref.analysis.run --results results/lgref/phase4-sweep
```

**The open question it answers:** at 18 games per variant, **33 of 49
profile cells came back `seed-dominated`** — between-seed variance
swamping the ablation. At 180 games per variant, how many resolve? If
most remain seed-dominated, that is a finding about the agent's
variance, not a reason to loosen `MIN_VARIANT_SHARE`.

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
- **7 ontology functions have no operational definition**, so no channel
  can confirm them; 3 more are behavioural-only and need Phase 3
  evidence. `lgref functions` prints the breakdown by reason.
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
