# Project execution brief — LGREF

> Verbatim as supplied, with two standing notes:
>
> - The brief was written as **LGMEF** and says *mechanic*. The project
>   later renamed these: **LGREF**, and *rule* in place of *mechanic*,
>   with **RCI** in place of MCI. The substance is unchanged.
> - "Train matched self-play agents" in Phase 3 was superseded: neural
>   self-play was dropped as too slow, and measurement now uses a
>   deterministic one-ply agent with random play as a contrast. The
>   matched-budget requirement still holds — any difference between
>   variants must come from the rules, not from the compute.

---

PROJECT EXECUTION BRIEF — LGMEF (Logic-Based Game Mechanic
Evaluation Framework)

You are helping me implement and run a complete research project. The
final output is a paper submitted to IEEE CoG. Right now the goal is a
working, reproducible pipeline with real results — not prose.

SYSTEM UNDER CONSTRUCTION
Input: a game in GDL. Output, per discovered mechanic:
  1. Which rule clauses constitute it (automatic discovery)
  2. What strategic functions it performs (the main claim)
  3. Measured gameplay effects from ablation (the verification)
  4. A retain / revise / remove recommendation, conditioned on a
     stated design objective
  5. A grounded natural-language summary of its impact

Case study: Royal Chess. Ablated mechanics: Boulder, Tiny Endgame,
Queen Manipulation, Knight Redesign. Comparisons: full game, each
single-ablation variant, and a baseline chess-like variant.

NON-NEGOTIABLE ENGINEERING RULES
- Everything config-driven and seeded. Any run reproducible from a
  single config file + seed. No hardcoded paths, no notebook-only
  logic.
- Every experiment writes a run manifest: git SHA, config hash, seed,
  wall-clock, machine, engine version, full metric output. Raw
  per-game records in Parquet or JSONL; never only aggregates.
- Nothing is deleted and recomputed. Results accumulate; analysis
  reads from stored raw data.
- Cost logging from day one — GPU-hours and dollars per experiment,
  printed at the end of every run.
- Tests: every metric function has a unit test on a hand-constructed
  game trace where I can verify the answer by hand.

PHASE 0 — AUDIT AND PLAN  [GATE]
Read the existing repo. Report: what exists, what's stubbed, what's
broken. Then propose the module layout and the data schema for game
records and metric outputs. Estimate compute per experiment BEFORE
writing pipeline code, and tell me if the plan exceeds my budget. Stop
for my approval.

PHASE 1 — RULE DISCOVERY FROM GDL CLAUSES  [GATE]
Build the typed rule-dependency graph:
- Normalize GDL clauses into rule nodes with: head predicate, body
  predicates, state variables read/written, action types, piece types,
  spatial scope, temporal scope, terminal dependency.
- Typed edges: predicate dependency, shared-state dependency,
  legality→transition, temporal (state created then consumed),
  terminal dependency, dynamic co-activation (from traces).
- Cluster into candidate mechanics using static cohesion + dynamic
  co-activation + intervention coherence. Allow soft/overlapping
  membership; a clause may belong to two mechanics.
- Intervention-coherence test: for each candidate cluster, generate an
  interface-preserving ablated GDL variant, verify it compiles, verify
  legal-move generation still works, verify no unrelated behavior
  disappeared. A cluster that fails this is not a mechanic.

Validation before proceeding: run discovery on 2–3 tiny games with
mechanic boundaries I can verify by hand, plus a chess-like baseline.
Report pairwise precision/recall/F1 and ARI against those known
boundaries. Compare against three baselines: predicate-name
similarity, static-graph-only clustering, trace-only clustering.
Stop and show me the clusters found in Royal Chess as clause lists.

PHASE 2 — FUNCTION INFERENCE  [GATE]
Implement the function ontology as code, not prose: each function is a
class with (a) structural signature predicates over the rule graph and
(b) a causal signature — the direction and rough magnitude of change
expected in specific metrics when the mechanic is ablated.

Required functions, each with an operational definition and at least
one metric that measures it:
  space control, mobility expansion, mobility restriction, escape
  facilitation, threat projection, tactical flexibility, cycle
  prevention, termination acceleration, draw suppression, outcome
  balancing, survivability, piece transformation, complexity-without-
  depth.

Assign multi-label functions with confidence scores. Structural
inference runs first and produces a PREDICTION; Phase 3 tests it.
Write predictions to disk and freeze them before running ablations —
this is the pre-registration, and it's what makes the result a finding
rather than a post-hoc story.

CRITICAL: my seed ontology labels for Royal Chess (Boulder = space
control, etc.) are development annotations. They must be withheld from
the discovery and inference code and used only as held-out reference
labels at evaluation time. Enforce this with code structure, not
discipline — the labels live in a file the pipeline cannot import.

PHASE 3 — ABLATION EXPERIMENTS AND DATA COLLECTION  [GATE]
For each variant (full, 4 single-ablations, baseline):
- Train matched self-play agents under IDENTICAL budgets: same
  architecture, same training steps, same MCTS simulation count, same
  hyperparameters. Any difference between variants must come from the
  rules, not the compute.
- Minimum 3 independent training seeds per variant. If budget forces a
  choice between more seeds and bigger models, choose more seeds —
  seed variance is the thing that kills these results.
- Evaluation: fixed-seed tournament games, agents cross-played where
  meaningful, plus a fixed-strength MCTS evaluator as a common yardstick
  so variants are comparable on a shared scale.

Metrics collected per game and per position:
  win/loss/draw by side, game length, draw and degeneracy rate, legal
  branching factor, policy-effective branching (near-optimal action
  count under a defined threshold), move entropy, repeated-state
  frequency, mechanic usage frequency, per-mechanic outcome sensitivity,
  attack-map coverage, reachable-square counts, MCTS value swing.

Run a pilot first: one variant, one seed, smallest viable budget.
Report per-game cost and projected total. Stop for approval before the
full sweep.

PHASE 4 — ANALYSIS  [GATE]
- Effect sizes with bootstrap confidence intervals, not p-values alone.
  Report Cohen's d or equivalent for every metric change.
- Variance decomposition: how much of the metric difference is
  between-variant vs between-seed? If seed variance swamps the ablation
  effect, say so plainly and do not report the effect as real.
- Multiple-comparison correction across the metric × mechanic grid.
- Build the Mechanic Contribution Profile: the full vector of
  standardized effects per mechanic, with intervals. This is the
  primary result.
- MCI(m) = αΔW + βΔL + γΔH + δΔU is a SUMMARY of that profile under a
  stated objective, not a discovered constant. Report it under at least
  three weightings (competitive balance, anti-stagnation, tactical
  richness) and show the sensitivity of each mechanic's ranking to the
  weights. If a mechanic's rank flips under reasonable reweighting,
  that is a finding to report, not to hide.
- Score Phase 2's frozen predictions against the measured causal
  signatures: per-function precision/recall, direction accuracy,
  calibration. This is the central evidence for the project's main
  claim.

PHASE 5 — RECOMMENDATION ENGINE
Rule-based, not LLM-generated. Output retain / revise / simplify /
merge / investigate, conditioned on an explicit objective. Gate on
uncertainty: wide intervals must force "investigate." "Remove" only
when the objective is stated, the effect is consistently near-zero or
negative, and the interval excludes meaningful effect.

PHASE 6 — EVIDENCE-CONSTRAINED EXPLANATION
Two-step: a structured evidence record is generated from the stored
results, then a template or tightly constrained LLM call turns only
that record into prose. Every sentence must be traceable to a field in
the record. Include a check that flags any claim in the generated text
not backed by a field.

PHASE 7 — RESULTS PACKAGE
- Figures: contribution profile heatmap across mechanics × metrics;
  per-metric effect plots with CIs; MCI rank sensitivity under
  reweighting; discovery accuracy vs baselines.
- Tables: discovery metrics vs baselines, function inference scores,
  ablation effect table.
- A results.md summarizing what was found, including what failed or
  came out null.
- A reproduction script that regenerates every figure from stored raw
  data.

WORKING PROTOCOL
- Stop at every [GATE] and report before continuing. Do not chain
  phases unsupervised.
- When a result looks too clean, suspect a bug and verify before
  celebrating. Leakage between ablated variants and shared caches is
  the most likely failure mode.
- Null results are results. If Knight Redesign shows no measurable
  effect, report that; do not tune until something appears.
- If you must cut scope for compute, cut the number of metrics, not
  the number of seeds, and tell me what you cut.
- Flag anything that would not survive a reviewer asking "how do you
  know that?"
