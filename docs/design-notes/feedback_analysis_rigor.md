---
name: feedback-analysis-rigor
description: "How to approach strategic/rule analysis on this project — do NOT jump to under-coverage/stall-prone conclusions, verify with the user before recording reversals, self-check assumptions against the rulebook many times, and never report an absence of measurement as a measured zero. Read before any tiny-endgame or rule-strategy analysis, and before reporting any zero or no-difference result."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e3b1db7b-ec7f-4a43-9b69-568c3971b17d
---

# Do not jump to conclusions from unverified strategic analysis

**Rule:** When strategic/rule analysis leads to a conclusion — especially one that **overturns a prior recorded conclusion** or claims **under-coverage / stall-prone** — present it to the user as **tentative** and get explicit verification **BEFORE** updating memory, docs, the rulebook, or code. Self-check every assumption and strategy against `RULEBOOK.md` and the optimal-play definition **many times** before presenting. Default to NOT claiming under-coverage.

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

## An absence of measurement is not a measured zero

**Rule:** before reporting any zero, near-zero, or "no difference", establish
which of THREE things it is: a real measured zero, a quantity nothing
measured, or a precondition that never held. They look identical in a
table and mean opposite things.

**Why (2026-09-29):** this cost four separate defects in one session, all
in the primary output.

- The contribution index printed `+0.00 (rank 3)` for eight of ten
  variants whose every weighted dimension had come back seed-dominated.
  Nothing was measured, and the framework's headline finding type — "a
  rank that moves between objectives" — then reported all eight as
  findings, because ties took sequential ranks by dict insertion order.
  It fired hardest exactly where the data was weakest, since ties at zero
  are what low power produces.
- A game stopped by the turn cap set `white_win=False`, and the analysis
  averaged that in as 0.0 — counting "we stopped watching" as evidence
  that white did not win. On a case whose true difference was zero it
  reported -0.5.
- "One arm only" in the two-arm comparison rested on ZERO games of the
  other arm in several cells, and read as a statement about the agent.
- Policy-free sampling reported "no structural difference" for the
  knight-invulnerability ablation (the flag is only set by play) and for
  the tiny-endgame rule (its precondition needs balanced pawn-free
  material, and its restriction needs a distance seen three times).

**How to apply:** for every zero, ask what would have had to happen for it
to be non-zero, and check that it could have. Name the three cases apart
in the output — the codebase now uses `not resolvable`, `not exercised by
static positions` and `not exercised by this sampling regime`. A rank,
index or verdict computed over ties must share the tie, never enumerate
it.

Related: [[feedback-measurement-discipline]].
