---
name: feedback-mnk-approved-version
description: The m,n,k player of 2026-10-22 is a version the user is proud of — later versions must be strictly better, and must never trade the midgame for the opening.
metadata:
  type: feedback
---

The user played the m,n,k agent on 2026-10-22 and asked for it to be
kept: *"the rest of its moves are getting increasingly more dangerous
and aggressive, making it a great player. I'm proud of this version -
save it as one I like and any future versions must be strictly better
than this one."*

**Why:** the previous attempt to improve it (`Reach:j`) fixed the
opening and cost 4.6 points of tempo in the midgame — measured, pooled
over two sampling seeds, z = 2.94. The user's verdict: *"Do not make
any later versions fix the opening moves while simultaneously
compromising everything else and all the good moves it makes
afterwards. Reach did exactly that and so it was overall more
ineffective than the original."* That is a value judgement about the
game and it is theirs, not the instrument's.

**How to apply:**
- The approved version is recorded in `lgref/weights/APPROVED.md` under
  "m,n,k". It is a FEATURE SET, not a weight file: `Line:1..k-1`,
  `Marks` and their `Missing:` halves, fingerprint `4701b7c3` on
  13x13 k=5, `Reach:j` off. A test pins the fingerprint.
- The known weakness is the opening — the first moves are off-centre.
  Fixing it is wanted; fixing it at the cost of the midgame is not.
- Gate with `tools/phase_rates.py`, which now puts TEMPO IN THE GATE
  on the user's instruction, and passes `detectable=0.04`: a run that
  cannot tell a four-point drop from noise is underpowered, not a
  pass. A single 1500-trial run cannot (floor 4.4); two sampling
  seeds pooled can (floor 3.1).
- `opening sharpness` is NOT the instrument for the opening claim — it
  measures whether moves are distinguished, not whether the centre is
  chosen. A distance-from-centre instrument still needs building.
- See [[feedback-ship-gate]] for the general rule this is an instance
  of.
