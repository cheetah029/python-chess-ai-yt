# Held-out reference labels — DO NOT IMPORT FROM THE PIPELINE

This directory holds the **designer's intended strategic functions** for
Royal Chess's rules: development annotations written by the game's
designer before any measurement.

Per the terminology decision (issue #175), these three things are not
interchangeable:

| | |
|---|---|
| **Intended** function | a designer's annotation — what lives here |
| **Hypothesized** function | Phase 2's structural inference — a prediction |
| **Supported** function | a hypothesis that survived Phase 3/4 measurement |

Treating an annotation as evidence would make the central result
circular: the system would be scored against labels it was allowed to
see. So these labels are **held out**. They are read at exactly two points,
both of them JUDGEMENTS about a prediction rather than inputs to one:

| | |
|---|---|
| Phase 4 | scoring Phase 2's frozen predictions |
| Phase 5 | deciding whether a rule did what it is FOR (`lgref/recommend/intent.py`) |

Phase 5 was added deliberately and is worth stating rather than
assuming. `revise` is the claim that a rule has a measurable effect
which contradicts its own purpose, and purpose is not derivable from
structure — only the designer knows it. An earlier version tried to do
without: it fired `revise` whenever any of the forty ontology functions
was contradicted by the measured signature, which made every measurable
rule a candidate for revision. Of course a boulder ablation contradicts
`anti_drift_control`; the boulder was never for that.

Reading the annotations here is not circular, because they never reach
the code that makes the prediction. The AST guard covers `identify/`
and `functions/` — the two packages that predict — and not
`recommend/`, which judges.

## Why this is a directory and not a module

`lgref/reference/` deliberately has **no `__init__.py`**. It is not a
Python package and cannot be imported. Evaluation code loads
`seed_labels.yaml` by explicit file path.

`lgref/tests/test_label_isolation.py` walks the AST of every module
under `lgref/identify/` and `lgref/functions/` and fails the build if any
of them so much as names this directory. The isolation is enforced by
code, not by discipline.

## Filling this in

`seed_labels.yaml` is a template. The designer fills it in; the pipeline
never writes to it. It may be completed at any time before Phase 4
evaluation — Phases 1-3 neither read it nor need it.
