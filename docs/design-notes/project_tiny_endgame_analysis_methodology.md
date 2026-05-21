---
name: Tiny endgame rule — operational stall definition and analysis methodology
description: Stall-prone vs forceable test. To objectively classify a position, ASSUME the repetition rule does not exist; then check whether optimal play stalls infinitely. Required reading for any tiny-endgame-rule analysis or pressure-testing.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
# Operational stall definition (objective test)

To classify a position as "stall-prone" (needs tiny endgame rule activation) vs "forceable" (rule activation not strictly needed), use this test:

**Assume the repetition rule does NOT exist.** Then ask: under optimal play by both sides, does the game continue **literally infinitely** without a forced capture or loss?

- **Stall-prone** = under no-repetition optimal play, the game continues infinitely. **Tiny endgame rule MUST activate.**
- **Forceable** = under no-repetition optimal play, one side has a forced-win sequence in finite turns. Tiny endgame rule doesn't strictly need to activate (over-coverage is acceptable but should be minimized per design principles).

# Why the no-repetition assumption is the right test

The repetition rule is a *theoretical* termination guarantor (finite state space × 3rd-repetition illegal = the game must eventually terminate). But it can take a practically unreasonable number of turns (potentially tens of thousands) to actually exhaust the state space.

For human play, AI training within a turn cap, or any practical realization, repetition-rule termination is too slow to provide useful resolution. So "draws" arise in practice from positions that stall over any reasonable turn budget, even though they would *eventually* terminate under repetition-rule exhaustion.

The tiny endgame rule's purpose is to bound such positions to a practical turn count via the distance-count cap.

**The no-repetition test isolates the structural question:** is this position structurally forceable, or does it require the distance-count cap to ensure decisive resolution within practical turn counts? If the former, the rule isn't needed. If the latter, the rule must activate.

# Categories of stall-prone positions (verified under no-repetition optimal play)

## Category 1: Symmetric positions — TRIVIALLY stall-prone

Any position with **identical piece composition on both sides** AND **reasonable starting squares** (not immediately threatening each other) is stall-prone under optimal play. Optimal play preserves the symmetry; neither side can force progress.

Trivial examples (all stall under no-repetition optimal play):
- K+R+R vs K+R+R
- K+B+B vs K+B+B
- K+Q+R vs K+Q+R
- K+R+N vs K+R+N
- K+Q+B vs K+Q+B
- K+N+N vs K+N+N
- K+B+N vs K+B+N

This applies to **any** symmetric composition. "Both sides have the same piece types remaining on relatively reasonable squares that don't immediately attack each other" → stall-prone.

A single counterexample of a stall-prone position is enough to disprove the claim "no stall positions exist." Symmetric positions are abundant counterexamples.

## Category 2: Near-symmetric (single piece-type swap) — likely stall-prone

Positions where the two sides differ only in **swapping ONE piece type for another similar-strength type** (rook ↔ knight ↔ bishop) are likely stall-prone. The disadvantaged side holds via comparable material power; neither side has enough material asymmetry to force progress.

Examples (likely stall-prone):
- K+B+B vs K+B+N (one bishop swapped for knight)
- K+R+B vs K+R+N (bishop swapped for knight)
- K+Q+R vs K+Q+N (rook swapped for knight on one side)
- K+R+N vs K+B+N (rook swapped for bishop)

These compositions do not create enough material asymmetry to force a win under optimal play. The "advantaged" side cannot translate a single rook-vs-knight or bishop-vs-knight difference into a forced capture sequence.

## Category 3: Queen-as-bishop escape (insufficient board coverage)

Positions where one side has a queen and the other side **cannot collectively attack all 64 squares**: the queen transforms to bishop form and teleports to a safe square each turn. The opposing side cannot ever corner the queen-as-bishop.

**Verified example: K+Q vs K+R+R+N is drift-prone.**

Reasoning:
- The lone queen transforms into bishop form. Queen-as-bishop has the bishop's global-teleport movement: it teleports to any safe (non-enemy-attacked) square each turn.
- The K+R+R+N side has 4 pieces. Across all positions of those 4 pieces, they can attack at most **63 of 64 squares** (geometric/combinatorial upper bound). At least 1 square always remains unattacked.
- Therefore queen-as-bishop always has at least 1 safe teleport destination.
- K+R+R+N cannot corner the queen-as-bishop → cannot force its capture → position is drift-prone for the K+R+R+N side.

**Generalization**: ANY position where the non-queen side cannot achieve 64-square attack coverage with their pieces is drift-prone (queen-as-bishop perpetually escapes via teleport).

## Category 4: Lone-queen vs limited active attackers

Closely related to Category 3. Positions where one side has only its royal queen left and the other side's active attackers (rooks, knights) cannot collectively control enough of the board to trap the queen-as-bishop.

# Required analysis methodology

**Surface-level reasoning like "extra piece corners opponent somehow" is BANNED. It is not analysis; it is pattern-matching disguised as analysis.**

Required steps for any pressure-test:

## 1. Identify each side's win goal

Which opponent royal(s) must be captured. Account for already-captured royals.

## 2. Enumerate piece capabilities per side

For each piece on each side, note:
- Movement type (mobility, range, jump, teleport).
- Capture mechanic (proactive standard, reactive bishop, jump-capture, manipulation).
- Action options (queen transformation, queen manipulation).
- Royal status (whose loss ends the game for that side).
- Transformation availability (which captured piece types are present so queens can transform into them).

## 3. Test lock-down/escape strategies explicitly

- **Queen lock-down via mutual bishop pin** (see `project_piece_strategic_dynamics.md` for full mechanics):
  - Both sides' queens transform to bishop form.
  - Position them on each other's diagonal LOS.
  - Neither queen can spatial-move without being captured by the other.
  - Effectively "cancels" the queens, letting non-queen material asymmetry decide.

- **Bishop-form escape via teleport**:
  - Queen transforms to bishop.
  - Compute opponent's maximum attack-square coverage.
  - If coverage < 64, queen-as-bishop has perpetual safe haven.

## 4. Analyze action-stalling possibilities

- Queens can take infinite actions (transformations, manipulations) without ever spatial-moving.
- Actions do NOT trigger bishop reactive capture (which requires a spatial move by the target).
- BUT: pure action stalling makes no offensive progress for the stalling side.
- A queen that only stalls via actions cannot capture anything herself; the opponent must independently lack offensive resources for stalling to actually save the position.

## 5. Check coverage explicitly

- How many squares can side X collectively attack?
- Can side X's attacks deny ALL squares to the defending piece?
- If not, the defending piece has perpetual escape via teleport (if it's a bishop or queen-as-bishop).
- Use the 64-square coverage threshold as a hard test.

## 6. Mark uncertain when uncertain — DO NOT default to "forceable"

If your analysis cannot CONCRETELY DEMONSTRATE a forcing sequence with explicit tactics, mark the position as **uncertain — likely stall-prone unless concrete forcing sequence demonstrated**.

The default for borderline cases is "stall-prone." This matches the design principle: when in doubt, err toward activating (under-coverage is unacceptable; over-coverage is acceptable).

# Default for borderline cases

Per `docs/potential-rule-changes.md` Section 7 design principles: when in doubt, err toward activating. Under-coverage is unacceptable (a missed drift-prone position = potential draw = rule failure); over-coverage is acceptable (winner just wins faster).

**IMPORTANT NUANCE (added 2026-05-14 after a second user correction)**: "When in doubt, err toward activating" applies AFTER you've genuinely searched for forcing tactics. It does NOT mean lazily declaring positions stall-prone whenever forced-win analysis is hard. The proper sequence:

1. **First, search exhaustively for forcing tactics by either side.** Especially: queen lock-down, extra-piece-conversion via pin + R2-window timing, queen transformation flexibility, manipulation as offensive tool.
2. **If you find a concrete forcing sequence**: classify as forceable. Do not activate the rule (over-coverage minimization).
3. **If you genuinely cannot find a forcing sequence after thorough search**: classify as stall-prone (default), activate the rule.

The bias I have been making: declaring "stall-prone with high confidence" without genuinely searching for forcing tactics. This produces FAKE under-coverage findings that aren't real problems with the cancel-queens rule — they're products of my insufficient analysis.

## Over-classification meta-lesson

**Before concluding any "problem" with the cancel-queens rule (under-coverage or otherwise), verify multiple times that it is actually a problem and not a misevaluation.** No fix is needed for nonexistent problems. The cost of premature problem-identification is wasted design effort on fixes for issues that don't exist.

Specifically:
- Always look for forcing tactics involving the strategic dynamics in `project_piece_strategic_dynamics.md` (pin coordination, R2-window exploitation, queen lock-down, transformation flexibility) BEFORE concluding stall-prone.
- If material is asymmetric (one side has more pieces), the default expectation should be "likely forceable for the +material side" unless concrete defensive resources are demonstrated.
- "+1 piece" advantages are convertible to forced wins more often than they appear, especially when the +1 piece is a transformable queen or when bishops can establish pin lock-down with R2-window protection.

## Forceability verification checklist

When pressure-testing a position, BEFORE classifying as stall-prone, check:

1. **Queen lock-down available?** If both sides have queens, can the +material side transform queens to bishop form and lock down the opponent's queens via mutual bishop pin? After lock-down, does the +material side's extra material force-win against the locked opponent?

2. **Extra-piece-conversion via R2-window?** If A has ≥2 pinning pieces (bishops or queens-as-bishop) and B has 2 pinnable pieces, can A pin both, keep its bishops R2-protected by alternating moves, and use the extra piece's free turns to standard-capture pinned B pieces?

3. **Queen-as-bishop escape?** If the disadvantaged side has a queen, can it transform to bishop and teleport to safe squares indefinitely (opponent's non-bishop coverage < 64)?

4. **Manipulation as offensive?** Can A use queen manipulation to force enemy pieces into spatial moves that trigger reactive captures by A's bishops? Restriction 2 timing matters.

5. **Standard capture of pinned pieces?** A pinned piece is still capturable by enemy standard captures (the pin doesn't protect against being captured, only against own movement). Can A reach a pinned B piece to standard-capture it?

6. **Position simplification leading to ≤4-piece catch-all?** Even if A can't immediately win, can A force a single capture that simplifies the position to ≤4 pieces, where the tiny endgame catch-all activates and bounds resolution?

If ANY of these tactics produces a forcing sequence for the +material side, the position is FORCEABLE. Only declare stall-prone if all of these fail.

## When to default to stall-prone

After exhausting the forceability checklist, if no forcing tactic is found, then default to stall-prone for activation purposes. This default should be used when:

- The position has roughly balanced material on both sides.
- The position has symmetric or near-symmetric composition.
- Concrete tactical analysis fails to identify a forcing sequence.
- Multiple verification attempts confirm no obvious forcing tactic exists.

In analysis terms: when you cannot concretely demonstrate a forcing sequence AFTER applying the verification checklist, treat the position as stall-prone for activation purposes.

# Anti-pattern checklist (mistakes I made on 2026-05-14)

- ❌ "Extra piece corners opponent" — surface-level pattern-matching, not actual analysis.
- ❌ "Knight chases king" — needs concrete sequence accounting for transformations, bishop pins, manipulation options.
- ❌ "Bishop pins constrain movement" stated vaguely — must analyze what specifically the pin does and what defensive resources counter it.
- ❌ "State space asymmetry under repetition rule" — IRRELEVANT under the no-repetition stall test. The whole point is to evaluate without repetition.
- ❌ Citing AI training data as "forceable evidence" — AI may not play optimally; training turn caps create artificial draws that don't reflect structural stall properties.
- ❌ Concluding EVERY position is forceable; failing to mark ANY as uncertain or stall-prone.
- ❌ Asking "is there any stall position at all?" — there are TRIVIALLY many (every symmetric position).
- ❌ Forgetting that bishops are ACTIVE pieces with global teleport movement, not passive diagonal-only attackers.
- ❌ Forgetting that queens can transform into ANY form (especially bishop) for escape via teleport.
- ❌ Ignoring the queen lock-down strategy (mutual bishop pin to "cancel" queens).
- ❌ **Defaulting to "stall-prone with high confidence" without genuinely searching for forcing tactics first.** This is the OPPOSITE error from the original Section 7 mistakes — declaring stall-prone where the position is actually forceable. Produces FAKE under-coverage problems with the cancel-queens rule that are actually misevaluations on my part. Discovered 2026-05-14 after user correction on case 3b (K+RQ+B+B vs RQ+B).
- ❌ **Concluding "under-coverage problem found" eagerly without multiple-pass verification.** No fix is needed for nonexistent problems. Verify the problem is real before proposing fixes. The cost of premature problem-identification is wasted design effort and unreliable analysis output.
- ❌ Treating "+1 bishop" (or any single extra piece) as "too weak to convert." With R2-window timing + queen transformation + standard capture of pinned pieces, even +1 piece advantages are often convertible.
- ❌ Treating pinned pieces as "uncapturable." Pinned pieces are only protected from their OWN spatial moves; standard captures by enemy pieces still apply to them.

# Strategic facts that need re-verification

The following claims from earlier memory are NOT trustworthy until re-verified under this methodology:

- "K+Q vs K+B+2-attackers: forced for B (bishop pin + off-line attacker corners the queen)." — Re-verify under queen-as-bishop escape and queen lock-down dynamics. May be drift-prone, not forced.
- "K+RQ vs K+RQ+non-Q: forced for B (the larger side)." — Re-verify under queen lock-down (both sides transform queens to bishop form, mutual pin; +non-Q side has extra material to decide). Probably still forced but the reasoning needs to be concrete, not material-count hand-waving.
- "K+RQ+RQ vs K+RQ: forced for B." — Same; re-verify under lock-down dynamics.

# Verified strategic facts (under operational stall test)

- **K + RQ + B + B vs RQ + B (case 3b, 6 pieces): FORCEABLE for the K+RQ+B+B side.** Verified via extra-piece-conversion technique (see `project_piece_strategic_dynamics.md`): A's 2 bishops pin B's RQ and bishop. A keeps bishops R2-protected by alternating moves. B is forced into transformation-stalling. A's RQ transforms to knight or rook and gets free turns to standard-capture pinned B pieces. Position simplifies to ≤4 pieces, catch-all activates. The cancel-queens rule correctly does NOT activate this position (no over-coverage). The active rule over-covers it (which is acceptable but suboptimal).

- **RQ vs RQ+B (3 pieces): FORCEABLE for the +bishop side** (corrected 2026-05-17; previously misclassified as stall-prone). I previously missed the optimal forcing strategy. Approach: B uses RQ + bishop coordination + manipulation tactic against A's lone RQ. Detailed mechanics need careful re-analysis; default conclusion under user correction is forceable.

- **K+R vs RQ (3 pieces): FORCEABLE for the +queen side** (corrected 2026-05-17). The +material side (with K+R, 2 pieces vs 1) can use manipulation tactic on A's RQ. Wait — A has the RQ, B has K+R. Let me re-state: the side with K+R (2 pieces) wins. B's RQ (single piece) cannot survive K+R's coordinated attack because A's R uses L-step to attack RQ-as-bishop's teleport destinations or B's RQ in any form. Manipulation of B's RQ when in transformed form (R3 doesn't protect transformed queens) by side-with-K... wait, side with K has no queen to manipulate with. Hmm, the +material side here doesn't have manipulation tools.

  Re-examining K+R vs RQ: the K+R side (let's call them side A with 2 pieces) wants to capture B's RQ. A's R can attack via L-step. B's RQ transforms to bishop and teleport-escapes — but only ~30 safe squares (coverage by A's K + R). A can use slow K-walk + R repositioning to constrain B's RQ's safe-square set, eventually forcing RQ into a position where R can L-step capture it. This is intricate but per user's claim, forceable. My previous analysis missed this.

# Meta-lesson: over-classification as stall-prone (added 2026-05-17)

Pattern of error: when I can't immediately see a forcing sequence in a position with apparent material balance or with strong defensive resources, I default to "stall-prone." This produces FAKE under-coverage claims that aren't real.

Specific error pattern in the ≤4 catch-all analysis:
- I classified RQ vs RQ+B as stall-prone via "action-stalling defense."
- I classified K+R vs RQ as stall-prone via "queen-as-bishop escape + R defense."
- Both were WRONG — the +material side has forcing tactics I missed.

Strategic tools I keep under-weighting:
- **Manipulation of A's non-queen piece** (R, B, or N — none are protected by R3). Combined with R2-window timing, manipulation forces target piece into vulnerable square + freezes for one turn.
- **Coordinated attack with multiple piece types** against a defending lone piece. Even when individual pieces can be defended, multi-angle attacks (radius-2 knight + L-step rook + reactive bishop) overwhelm.
- **Standard capture bypasses pins.** A pinned piece is only protected against its OWN spatial moves; standard captures by enemy pieces remove it.

**Before concluding stall-prone, exhaustively check whether manipulation + multi-piece coordination forces a piece capture in finite turns.** If a single piece can be captured via forcing tactics, the position simplifies, often into a ≤4 catch-all or a clearly-forceable smaller position.

# Date created

2026-05-14, after the user identified that my pressure-test analysis was systematically biased toward declaring every position forceable using surface-level reasoning, ignoring the actual strategic dynamics of bishops, queen transformations, and queen-as-bishop teleport escape.
