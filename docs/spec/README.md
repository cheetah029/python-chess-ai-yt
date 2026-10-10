# Project specification

The governing documents for this project, kept here so they can be
referred to directly rather than reconstructed from conversation.

| file | what it is | precedence |
|---|---|---|
| [`project-overview.md`](project-overview.md) | the current framework description: terminology, five-layer representation, statement graph, function ontology, operational definitions, Phases A–G, metrics and hypotheses | **authoritative for TERMINOLOGY and the research programme** (supplied 2026-10-09) |
| [`project-execution-brief.md`](project-execution-brief.md) | the phase-by-phase execution plan and the non-negotiable engineering rules | authoritative for PROCESS |
| [`project-outline.md`](project-outline.md) | the older Rule–Mechanic–Function framework | SUPERSEDED on terminology; kept because the code's ontology was built from it |

## Which document wins

**`project-overview.md` is the current statement of what the project is.**
It replaces the outline's vocabulary throughout:

| older wording | current wording |
|---|---|
| mechanic / MCI | **identified game rule** / measured gameplay effect |
| clause | **computer-readable statement** |
| strategic function (only) | **gameplay role**, with *strategic function* the technical term for a role involving choices, threats, resources, history or outcomes |
| contribution as a score | a **measured gameplay effect** — direction and magnitude of a change in a predefined statistic under a stated intervention, explicitly NOT a universal score of a rule's value |

Two substantive points the overview makes that the implementation must
keep honouring, and currently does:

- **A rule exists even when its measured effect is small, redundant or
  never used.** "An unused teleport ability remains a game rule even if
  the tested agents never select it." This is why the pipeline reports
  `not exercised` rather than `no effect` (#242, #259).
- **Recommendations are an optional extension requiring a stated
  objective**: "a small competitive effect alone does not justify
  removing a rule that may serve thematic, aesthetic, accessibility, or
  educational purposes." Phase 5 is therefore objective-indexed, never a
  single verdict.

## How to read them together

**The outline is authoritative for the ontologies**, and the code follows
it: `lgref/functions/strategic_ontology.py` implements its 40 strategic
functions across eight categories, and `lgref/functions/characteristics.py`
implements its eleven design-characteristic dimensions as a **separate**
layer — a characteristic describes how a rule is built, a function
describes what it does to the decision system.

The brief is authoritative for **process**: config-driven and seeded runs,
run manifests, raw per-game records, cost logging, pre-registration
before ablation, and the gates.

## Known differences between the two, and how they are resolved

- **Terminology.** Settled by `project-overview.md` — see the table
  above. The pipeline reads: computer-readable statements → identified
  game rules → gameplay roles → measured gameplay effects → optional
  objective-indexed recommendations.
- **Scope.** The brief's phases 0–7 are the build order. The overview's
  Phases A–G are the research programme those phases serve, and
  `docs/spec/phase-map.md` maps one onto the other. The overview drops
  the expert-review and physiological-sensing elements the older outline
  carried: "The current procedure does not require expert judgment,
  expert review time, human playtesting, or physiological sensing."
- **Output detail.** The outline's sample outputs are illustrative
  minimums. The implementation deliberately reports more — including
  seed-dominated and inconclusive results that a tidier table would
  omit.

## ISEF

Both the outline and the overview were written with an ISEF submission in
mind, and the overview has a "Minimum viable ISEF scope" section. **That
is not a concern for this work.** The target is a full paper for IEEE
CoG, and nothing in the implementation should be shaped by competition
requirements, categories or judging criteria. Where either document
mentions ISEF, read past it — the scientific content of that section
still applies, the framing does not.
