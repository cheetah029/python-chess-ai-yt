# Project specification

The two governing documents for this project, kept here so they can be
referred to directly rather than reconstructed from conversation.

| file | what it is |
|---|---|
| [`project-execution-brief.md`](project-execution-brief.md) | the phase-by-phase execution plan and the non-negotiable engineering rules |
| [`project-outline.md`](project-outline.md) | the Rule–Mechanic–Function framework: the conceptual model, the full strategic-function ontology, design characteristics, and the evaluation programme |

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

- **Terminology.** The outline says *mechanic*; this project renamed that
  to **rule**, and MCI to **RCI** (Rule Contribution Index), per a later
  decision. The pipeline reads: formal clauses → rules → strategic
  functions → measured contributions → recommendations. "Mechanic" is
  reserved for ordinary game-design discussion.
- **Scope.** The brief's phases 0–7 are what is being built. The
  outline's Phases A–G describe a wider programme; its Phase C (exact
  validation on solvable games) is implemented, and its E/F/G
  (external-game generalisation, expert and player validation) are not
  currently in scope.
- **Output detail.** The outline's sample outputs are illustrative
  minimums. The implementation deliberately reports more — including
  seed-dominated and inconclusive results that a tidier table would
  omit.

## ISEF

The outline was written with an ISEF submission in mind. **That is not a
concern for this work.** The target is a full paper for IEEE CoG, and
nothing in the implementation should be shaped by competition
requirements, categories or judging criteria. Where the outline mentions
ISEF, read past it.
