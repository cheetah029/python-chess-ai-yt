# LGREF Phase 2 — Strategic function inference

**Rules → strategic functions.** For each rule identified in Phase 1,
what job might it be doing — and what does that commit us to observing
when the rule is ablated?

Issue [#208].

## The point is that the labels can be wrong

Phase 3 measures what removing each rule does. A function label assigned
*after* seeing those numbers would fit whatever they turned out to be,
and the exercise would prove nothing. So every label here is written
down, hashed and frozen **before any ablation runs**.

A class is therefore not a name attached to a cluster. It is a
**structural signature** — detectable from the clause graph alone —
paired with a **causal signature**, a committed claim about what
ablation will show:

| class | predicted ablation effect | metric | detector |
|---|---|---|---|
| `termination_pressure` | games end differently — sooner, later, or not at all | termination rate and length | **strong** |
| `move_generation` | *fewer* legal moves; an action type may vanish | legal moves at sampled positions | **strong** |
| `turn_structure` | alternation breaks; expect unplayable | playable | **strong** |
| `move_restriction` | *more* legal moves | legal moves at sampled positions | weak |
| `cross_turn_memory` | behaviour changes only where the state was set | conditional action frequency | weak |
| `state_conversion` | that action type disappears | action type counts | weak |
| `capture_regime` | captures per game change | captures per game | weak |

**Detector strength is declared, not hidden.** Three read directly off
GDL's reserved words (`legal`, `terminal`, `goal`, the control fluent);
four rest on proxies that can misfire. A weak detector making a
falsifiable claim is worth keeping — that is what pre-registration is
for — but presenting it as firm would misrepresent the evidence.

**Confidence is evidence strength, not probability.** It reports how
much of a cluster matches a signature. Whether the label is *correct* is
decided by the ablation, in Phase 4. Reading it as a probability of
being right would be a claim this phase cannot support.

## Game-agnostic by construction

Detectors use GDL's own reserved words and the action names derived from
the description under analysis. The "dominant fluent" — a game's board —
is found as the one most clauses write (`cell` in Royal Chess, `pile` in
nim), never named. The control fluent is found as the one nearly every
`legal` clause reads.

A test asserts no Royal Chess concept appears anywhere in Phase 2, and
`test_label_isolation.py` fails the build if the designer's held-out
labels in `lgref/reference/` are reached at all.

Run on tic-tac-toe and nim as well as Royal Chess; both produce
`termination_pressure` and `turn_structure` as they should.

## Language clusters are never labelled

Coordinate arithmetic has no strategic function. Asking what job
`file_delta_1` does is the error that held this phase up, and it is now
excluded automatically rather than by remembering ([#202]).

## Result on Royal Chess

55 clusters: **16 language** (skipped), **39 labelled**, of which 5
carried no signature.

| function | clusters |
|---|---|
| `move_restriction` | 29 |
| `move_generation` | 17 |
| `cross_turn_memory` | 9 |
| `state_conversion` | 6 |
| `termination_pressure` | 2 |
| `turn_structure` | 1 |
| `capture_regime` | **0 — unattributed** |

`move_restriction` at 29 of 39 is the weak detector over-collecting, as
declared. Phase 4 will have plenty of opportunity to falsify it.

### `capture_regime` matches nothing, and that is a finding

All 36 clauses carrying the capture signature are **generic-effect**:
held out of the partition and attached as *shared* members, so they
belong to no single rule. Capture in this description is not one rule's
business — it is the board-update machinery every movement rule routes
through.

A detector that fires on nothing looks broken, so the frozen record
names unattributed functions explicitly. It is a claim about the
description, not a gap in the tooling.

## The frozen artefact

`lgref/report/phase2_predictions.json` carries a SHA-256 over the
predictions, the code hash, the resolution and seed that produced the
clusters, and the timestamp — so a later claim to have predicted
something can be checked rather than taken on trust. Writing refuses to
overwrite an existing file: a pre-registration that can be quietly
rewritten is not one.

```bash
python3 -m lgref functions --gdl docs/gdl/integrated.gdl
```
