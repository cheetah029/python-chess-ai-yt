# LGREF — Logic-Based Game Rule Evaluation Framework

Identifies gameplay **rules** from the formal clauses of a GDL game
description, hypothesises their **strategic functions**, measures their
**contributions** by ablation, and turns the result into
objective-conditioned recommendations.

Target: IEEE CoG 2027 full paper (results complete by mid-December 2026).

## Vocabulary

**formal clause → rule → strategic function → measured contribution**

| Term | Meaning |
|---|---|
| Formal clause | One statement in the formal representation (a GDL fact or implication). |
| Rule | A gameplay provision implemented by one or more formal clauses. |
| Strategic function | The strategic role a rule may serve. |
| Contribution | Its measured effect under a stated comparison. |

Rules are grouped by the behaviour their clauses jointly implement, **not**
by shared strategic function. See `docs/lgref-experiments.md`.

## Trust order for the game's rules

1. `RULEBOOK.md` — authoritative
2. the playable implementation (`main.py` → `game.py` → `board.py`)
3. the GDL (`docs/gdl/`)
4. the GGP (`src/ggp/`)

`GameEngine` is not a fourth thing: `AIController` points it at the live
`Game` board, so the harness and the playable game share one move-generation
path. Phase 3 measures exactly the rules `main.py` enforces.

## Layout

```
config/      YAML experiment configs (base.yaml + per-experiment)
core/        manifests, cost accounting, Parquet storage, release integrity
identify/    Phase 1 — clause dependency graph, rule identification
functions/   Phase 2 — function ontology, frozen predictions
experiments/ Phase 3 — agents, matched training, metric collection
analysis/    Phase 4 — effect sizes, variance decomposition, RCI
recommend/   Phase 5 — objective-conditioned recommendations
explain/     Phase 6 — evidence records → constrained prose
report/      Phase 7 — figures, tables, reproduction
reference/   HELD-OUT seed labels — not a package, cannot be imported
```

## Storage

Raw per-game and per-position records are Parquet, written
**accumulate-only**: every flush is a new part file, nothing is
overwritten, and a re-run adds parts rather than replacing them.

Measured compression on real game records: **92×** (645 B/ply as JSON →
7.0 B/ply as Parquet). The full 24-run sweep is ~46,000 games ≈ **15.3 GB
as JSON, 0.17 GB as Parquet**.

Raw bundles are published as **GitHub Release assets**, and a small
`release_index.json` carrying a **SHA-256 and the run's provenance per
bundle is committed to git**. That checksum is the point: the reproduction
script can prove it is analysing the same bytes the published figures came
from. `verify_bundle` fails loudly on any mismatch.

Uploading is deliberately a human step — `release.upload_command()` prints
the `gh` command rather than running it, because publishing data outside the
machine should not be a side effect of a training run.

## Reproducing a run

Every run is reproducible from one config file plus a seed:

```bash
python -m lgref.run --config lgref/config/pilot.yaml --seed 0
```

Each run writes a `manifest.json` recording git SHA (and whether the tree
was dirty), config hash, seed, wall-clock, machine, engine fingerprint, and
measured cost in core-hours and dollars. The manifest is written at start
with status `running`, so a killed run still leaves evidence it was
attempted.

## Cost

This workload is **CPU-bound**: Apple MPS measured at 21.0 vs 21.6 plies/s
on CPU — no GPU benefit. The unit that matters is the **core-hour**, not the
GPU-hour. `CostTracker` records wall-clock and core-hours, converts via an
explicitly recorded rate, and `project()` extrapolates a pilot's measured
rate to the full sweep — which is how the Phase 3 pilot reports a projected
overrun before the sweep starts.

## Held-out labels

`lgref/reference/seed_labels.yaml` holds the designer's **intended**
functions. An intended function is an annotation, a Phase 2 output is a
hypothesis, and only a measured one is supported — these are never
interchangeable, and scoring predictions against labels the pipeline could
see would be circular.

Enforcement is structural: `reference/` has no `__init__.py`, and
`lgref/tests/test_label_isolation.py` walks the AST of every module under
`identify/` and `functions/`, failing the build on any import **or string
literal** naming it. All three leak routes are mutation-tested.
