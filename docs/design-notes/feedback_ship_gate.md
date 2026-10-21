---
name: feedback-ship-gate
description: Never ship an agent change on a race win alone — a race is an aggregate and hides per-phase regressions; establish strictly better first.
metadata:
  type: feedback
---

**Winning a race does not mean the player is strictly better.** Do not
ship a change to the agent because it won a self-play race. The user
has said this after three changes shipped on a race and were worse in
play, and once with "I am very disappointed in you now."

**Why:** a race reports one aggregate number over positions. A change
can win overall and be much worse at one kind of position. Worked
example on this project: `Reach:j` in m,n,k fixed the OPENING (on a
large board the plain line count saturates and ties across every cell
of the middle, so nothing in the evaluation could prefer the centre)
and made the MIDGAME worse (tempo spent on moves that neither attacked
nor defended). Both true; one number reports whichever is larger.
Worse, the rejected Royal Chess build won its race 25–7 at depth 2
*and* was raced at the wrong depth entirely — the window plays at
`Game.TD_DEPTH`.

**How to apply:**
- Check `lgref/weights/APPROVED.md` before touching the shipped
  weights. It names the approved build and its sha; a test fails if
  what ships is not what is approved.
- Race at the depth the window plays, and make the log state its own
  terms (both files, both payload hashes, depth, games). A log that
  cannot be attributed is not evidence and gets thrown away.
- Measure per phase with `tools/phase_rates.py` and gate on
  `validate.strictly_better` — a change clears only by losing nothing.
  Its tolerance is sampling noise, not zero, and an underpowered
  sample is reported as such rather than passed.
- Archive every shipped payload so a revert is a copy. See
  [[feedback-measurement-discipline]] for the run-it-properly rules
  and [[feedback-analysis-rigor]] for the don't-conclude-early ones.
