---
name: feedback-analysis-rigor
description: "How to approach strategic/rule analysis on this project — do NOT jump to under-coverage/stall-prone conclusions, verify with the user before recording reversals, self-check assumptions against the rulebook many times. Read before any tiny-endgame or rule-strategy analysis."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e3b1db7b-ec7f-4a43-9b69-568c3971b17d
---

# Do not jump to conclusions from unverified strategic analysis

**Rule:** When strategic/rule analysis leads to a conclusion — especially one that **overturns a prior recorded conclusion** or claims **under-coverage / stall-prone** — present it to the user as **tentative** and get explicit verification **BEFORE** updating memory, docs, the rulebook, or code. Self-check every assumption and strategy against `RULEBOOK_v2.md` and the optimal-play definition **many times** before presenting. Default to NOT claiming under-coverage.

**Why:** I make accuracy mistakes in strategic analysis **frequently**, and the errors compound into confidently-wrong conclusions. The user has corrected this pattern repeatedly:
- I have a recurring bias toward eagerly declaring positions "stall-prone" / the rule "under-covers," based on reasoning that turns out to be flawed.
- Concrete instance (2026-05-20): I tried to reverse the "K+RQ+PQ+B+B vs same likely rule-sufficient" lean to "stall-prone" using three arguments — **all three were wrong**:
  1. "No-check makes a mirror/copycat defense un-loseable because one capture never wins" — WRONG: no-check is only a legality difference; you capture both royals one at a time and win, even from symmetry; first-mover tempo converts.
  2. "Under no-check, a defender can simply decline a fork and accept the loss" — WRONG: optimal players never move into a worse position, so threats must be addressed/captured; forks DO force.
  3. "A bishop pin is a stable trap, and the pin/tempo race favors the defender" — WRONG/incomplete: a base-form queen can manipulate the pinning bishop away (R3 doesn't protect bishops; manipulation is non-spatial so no reactive trigger).
- The correct strategic facts are recorded in [[Piece strategic dynamics — bishop active-pin, queen lock-down, queen-as-bishop escape, action stalling]] ("User clarifications 2026-05-20"). The optimal-play definition is in [[Tiny endgame rule — operational stall definition and analysis methodology]].

**How to apply:**
- Treat the recorded leans (e.g. "dense symmetric >6 likely rule-sufficient") as the standing position. Do NOT silently overturn them.
- Before presenting any analytical conclusion: re-derive it, then try to BREAK it yourself (look for the holes), then check it against the rulebook and the optimal-play definition. Only present after it survives self-refutation.
- When presenting a conclusion that changes a recorded one, label it tentative, show the reasoning, and ask the user to verify before recording anything.
- Never record incorrect analysis into memory/docs, even as a foil — record only the verified correction/clarification.
