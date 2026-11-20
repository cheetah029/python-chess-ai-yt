---
name: feedback-design-strictly-better
description: Design every change to be strictly better BEFORE implementing it — gates can refuse a change but never licence one.
metadata:
  type: feedback
---

**Design the change so it is certainly strictly better before writing
it.** Do not build a change and then measure whether it regressed
something. The user, 2026-10-24: *"relying on testing or measuring
gates after the fact is essentially ineffective and the same as not
making it strictly better, because you failed to design the change that
way in the first place."*

**Why:** a gate is a DETECTOR — it reports what it can see, at the
power it has, on the phases it reaches. An empty result means "nothing
detected", never "nothing there". Three times in issue #278 that gap
was real: a tempo loss inside the noise floor but down on all four
seeds; an endgame loss invisible on 13x13 (its endgame band has no
samples) that a 5x5 run found; and a +7.0 opening gain measured while
the change had crippled the search to depth 1. **A gate may refuse a
change and may never licence one.**

**How to apply** — the full procedure is `docs/strictly-better-method.md`:
1. State the defect as a measurement.
2. Choose a certificate class and name the premise that will discharge
   it: IDENTICAL (same values, less cost), CONFINED (no effect outside
   a rule-defined region), MONOTONE (a quantity can only move one
   way), UNSOUND (removes an operation whose premise is false here).
   **If none fits, stop and redesign** — "build it and measure" is not
   a fourth option.
3. Write the class into `DECLARED` in `lgref/tests/test_method.py`
   BEFORE implementing, so the code has to earn it.
4. Discharge the premise with `lgref/experiments/certificate.py`; each
   function raises on a counterexample rather than scoring.
5. Measure last. The gate can still refuse; it cannot approve.

**Applies to tie-breaks too (2026-10-28).** "B needs to be strictly
better by design, otherwise it cannot be shipped": a tie-break that asks
the EVALUATION (even one ply deeper) is not certifiable, because
"deeper is better" is a measurement. Only facts about the GAME (forced
win / forced loss within a horizon) can break a tie with certainty —
`candidate-designs.md` §24.

A proven class that differs from the declared one is a FAILURE, not a
relabelling — the test enforces this. See [[feedback-ship-gate]] for
the approval record and [[feedback-mnk-approved-version]] for the m,n,k
baseline.
