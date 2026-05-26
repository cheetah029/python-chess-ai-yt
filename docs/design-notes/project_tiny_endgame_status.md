---
name: Tiny endgame rule — current status and design directions
description: Active rulebook version + cancel-queens + 1-to-3 valuation as the leading proposal. Operational stall definition + corrected strategic facts (K+Q vs K+R+R+N is drift-prone). Read project_tiny_endgame_analysis_methodology.md and project_piece_strategic_dynamics.md before any analysis.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---

## CURRENT ADOPTED RULE (commit 1c7cdec, 2026-05-18) — supersedes everything below

**Activation: no pawns AND ≤6 NON-KING non-neutral pieces (boulder excluded) AND the position balances under cancel-queens + 1-to-3 valuation.** The old "≤4 total OR ≤6 same-multiset" rule and the separate ≤4-total catch-all were BOTH removed. Balance check: cancel queens (q=min(Q_W,Q_B)); then `r ≤ N_L−N_M ≤ 3r` for r≥1, or `N_M==N_L` for r=0. Implemented in `src/board.py is_tiny_endgame()`, documented in `RULEBOOK_v2.md`.

(NOTE: some sections BELOW in this file are from earlier sessions and describe the rule's DESIGN EVOLUTION — including a ≤4-total catch-all that was later removed. They are kept for rationale/history. The SESSION HANDOFF section at the BOTTOM of this file + this top block are the authoritative current state. Distance count: each Manhattan royal distance 1–14 capped at 3; non-capture move pushing a count over 3 is illegal; all-illegal = loss. Unchanged.)

## Critical framing — the rule's purpose

**Tiny endgame must produce a winner under optimal play within a practical turn count.** Drawing the game (running out the turn cap, infinite drift, etc.) is the failure mode the rule exists to prevent.

The repetition rule is a *theoretical* termination guarantor but in practice takes a practically unreasonable number of turns. The tiny endgame rule's job is to provide *practical* termination via the distance-count cap.

## Operational stall-vs-forceable test

**To classify a position objectively, assume the repetition rule does NOT exist.** Then ask: does optimal play stall infinitely?

- **Stall-prone** = stalls infinitely under no-repetition optimal play → rule MUST activate.
- **Forceable** = forced-win sequence exists in finite turns under no-repetition optimal play → rule doesn't strictly need to activate (over-coverage acceptable but minimize).

Full methodology: `project_tiny_endgame_analysis_methodology.md`. Required reading before any pressure-test or rule-design discussion.

## Categories of known stall-prone positions

### Trivially stall-prone

- **Any symmetric position** (same piece composition on both sides, reasonable non-attacking starting squares): K+R+R vs K+R+R, K+B+B vs K+B+B, K+Q+R vs K+Q+R, K+R+N vs K+R+N, K+Q+B vs K+Q+B, K+N+N vs K+N+N, K+B+N vs K+B+N, etc.

### Likely stall-prone (single piece-type swap)

- **Near-symmetric** positions with one piece-type swap (rook ↔ knight ↔ bishop): K+B+B vs K+B+N, K+R+B vs K+R+N, K+Q+R vs K+Q+N, K+R+N vs K+B+N. Disadvantaged side holds via comparable material power.

### Drift-prone via queen-as-bishop escape

- **K+Q vs K+R+R+N**: queen transforms to bishop; K+R+R+N attacks at most 63 squares; queen-as-bishop always has at least 1 safe teleport destination; cannot be cornered.
- Generalizes: any position where the lone-queen side can transform to bishop AND the opposing side cannot achieve 64-square attack coverage.

## Design principles (full text in `docs/potential-rule-changes.md` Section 7)

1. **Primary purpose:** 100% guaranteed decisive outcome under optimal play. Every covered position must end in {win, loss}, never a practical draw.

2. **Optimality is self-referential.** Both players play with full knowledge of all rules, INCLUDING the tiny endgame rule itself. Activation conditions must be analyzed under this assumption.

3. **Optimality tiebreakers:** winning side minimizes moves to win; losing side maximizes moves to lose.

4. **Coverage trade-off (priority order):**
   - Under-coverage = blocker (a stall-prone position not covered = potential draw = failure mode).
   - Over-coverage = acceptable (forced position covered = winner just wins faster, same outcome).
   - Simplicity preferred when coverage is equivalent.
   - **When in doubt, err toward activating.**

5. **Anti-goal:** "fairness" via under-coverage.

6. **Activation is positional only.**

## Leading proposal: Cancel-Queens + 1-to-3 Valuation (in active discussion, not yet adopted)

Full spec in `docs/potential-rule-changes.md` Section 8.

**Algorithm (refined 2026-05-16):**

1. No pawns required.
2. If ≤4 **total** non-neutral pieces → activate (catch-all). Boulder neutral, excluded.
3. Else if ≤6 **non-king** non-neutral pieces (boulder still excluded; kings ignored): cancel queens, then check 1-to-3 valuation balance.

**Key refinement from prior version:** the balance-check scope changed from "≤6 total pieces" to "≤6 non-king pieces." This adds coverage of symmetric/near-symmetric 7–8-piece positions with extra kings, which are trivially stall-prone (Category 1 / Category 2) but were previously under-covered.

**Critical clarification (added 2026-05-16):** the ≤6 non-king threshold is a SCOPE for the balance check, not unconditional activation. So:
- ≤6 non-king AND balance check passes → activate.
- ≤6 non-king AND balance check fails → DON'T activate.

This means ≤6 non-king introduces NO over-coverage at all. Asymmetric positions with diff ≠ 0 in non-king count (like K+RQ+R+B vs K+RQ+R, 7 pieces, 5 non-king, r=0, N_W=2 vs N_B=1, diff=1) still have balance check fail (2 ≠ 1) → still don't activate. Only positions where the balance check naturally passes (symmetric and near-balanced) get the new coverage, and those are precisely the stall-prone positions Category 1 and 2 identify.

**Crucially, the catch-all clause remains ≤4 TOTAL, NOT ≤4 non-king.** The catch-all skips the balance check entirely (unconditional activation), so expanding it to ≤4 non-king would pick up forceable 5-piece positions like K+RQ+B vs K+RQ that the king-pin tactic resolves (W's bishop pins K_B; K has no actions; K_B must move on its turn; W's bishop reactive-captures K_B; position simplifies).

**Net effect of refinement:** ≤6 non-king is a PURE improvement — gains coverage of stall-prone symmetric/near-symmetric 7–8-piece positions, zero over-coverage cost (balance check filters out asymmetric forceable cases). Keeping ≤4 total avoids the king-pin-forceable over-coverage on 5-piece 2-king positions.

## Why ≤4 total catch-all IS necessary (added 2026-05-17)

Question revisited: is the ≤4 total catch-all (clause 1) necessary, or does the ≤6 non-king balance clause (clause 2) cover everything?

**Conclusion: clause 1 is necessary.** Removing it introduces under-coverage on small-piece-count stall-prone positions where the balance check fails.

### Concretely stall-prone uncovered cases (if clause 1 removed) — REVISED 2026-05-17

**RETRACTION (2026-05-17 user correction):** my previous claims that RQ vs RQ+B (3 pieces) and K+R vs RQ (3 pieces) were stall-prone were INCORRECT. The user identified those as forceable; my analysis missed the optimal forcing strategies. **Only the K+non-Q vs RQ+non-Q (4-piece, both kings/both royal-queens alive) category is potentially stall-prone or borderline.** All other ≤4 cases I previously enumerated are forceable for the +material side under optimal play, NOT stall-prone.

The key strategic tools I missed in over-classifying as stall-prone (the meta-error pattern):

- **Manipulation-of-A's-non-Q forcing tactic.** When A has K + non-queen and B has RQ + (anything), B's RQ in base form can manipulate A's non-Q piece (since A's non-Q is not a king or queen, R3 doesn't protect it). B times manipulation around Restriction 2 windows (A's non-Q is stale when A moved K on the immediately preceding turn). Manipulation moves A's non-Q to a vulnerable square + freezes it for A's next turn. With A's non-Q frozen, A can only move K, and B can capture A's non-Q with B's other piece (or via reactive capture if A's non-Q's manipulation start-square was on B's bishop's LOS). Once A's non-Q is captured, A has only K vs B's larger force — forceable.

- **B's R approaching A's lone RQ in the queen-side defender case (RQ vs RQ+B).** B's bishop pins A's RQ; A stalls via actions on the pinned square. But B's RQ-as-knight or RQ-as-rook can approach to standard-capture A's RQ at the pinned square (standard capture bypasses A's bishop pin since pin only protects A's RQ's own movement). A cannot prevent this with action-stalling alone — B's offensive piece eventually arrives at the capture square. (Wait — this case is RQ vs RQ + B, no kings. A has only RQ — there's no A bishop to pin B's pieces. So B's RQ + bishop work together to attack A's RQ. A's RQ can transform to bishop and teleport-escape, but B's RQ + bishop coverage doesn't constrain A's RQ-as-bishop because B's bishop is excluded from teleport-safety check, and B's RQ in any form has limited coverage. The complication is more subtle — see in-repo docs for the full corrected analysis.) Forceable for B.

### The remaining potentially-stall-prone category: K+non-Q vs RQ+non-Q

This is the only ≤4 category the user has identified as potentially borderline. 9 sub-cases (3 options for A's non-Q × 3 options for B's non-Q):

1. K+R vs RQ+R
2. K+R vs RQ+B
3. K+R vs RQ+N
4. K+B vs RQ+R
5. K+B vs RQ+B
6. K+B vs RQ+N
7. K+N vs RQ+R
8. K+N vs RQ+B
9. K+N vs RQ+N

Each sub-case has different defensive/offensive dynamics. Active analysis: which are forceable for B (queen-side) under optimal play, which are genuinely stall-prone?

**Initial hypothesis (under refinement):**
- Sub-cases where B has 2 active offensive pieces (R or N): B's offense + manipulation tactic forces win. Likely forceable.
- Sub-cases where B's non-Q is a bishop (reactive only): B's offense relies on RQ alone. Manipulation + queen transformation might still force, but more uncertain.

If only a subset of the 9 sub-cases is actually stall-prone, the ≤4 catch-all could potentially be tightened to cover just those (e.g., "≤4 total AND specific composition pattern"). But the catch-all's simplicity may be worth keeping even if it over-covers some forceable cases.

### Final refined rule (still valid as of 2026-05-17)

Activates iff no pawns AND one of:
- **Clause 1 (catch-all):** ≤4 TOTAL non-neutral pieces.
- **Clause 2 (balance):** ≤6 NON-KING non-neutral pieces AND cancel-queens + 1-to-3 valuation balances.

### Counter-cases (forceable, would not cause under-coverage)

**K vs K + RQ (3 pieces).** B's RQ-as-knight chases A's slow K alone. A has no defense. Forceable for B.

**K vs K + R/B/N (3 pieces).** Similar — A's K alone can't escape B's active attacker. Forceable for B.

But these forceable cases don't justify removing clause 1 — they would still be activated by clause 1 (over-coverage acceptable), and removing clause 1 would leave the stall-prone cases (RQ vs RQ+B, K+R vs RQ+R, K+R vs RQ) under-covered.

### Why clause 1 uses ≤4 total, not ≤4 non-king

If catch-all were ≤4 non-king (instead of ≤4 total), it would pick up 5-piece 2-king positions like K+RQ+B vs K+RQ (5 total, 3 non-king). These are forceable via king-pin tactic (W's bishop pins K_B; K has no actions per `RULEBOOK_v2.md` lines 153-172; K_B must move on its turn and gets reactive-captured by W's bishop). Activating the rule on forceable positions is acceptable over-coverage but should be minimized — so catch-all stays at ≤4 total.

### Final refined rule (2026-05-17)

The tiny endgame rule activates iff no pawns AND one of:
- **Clause 1 (catch-all):** ≤4 TOTAL non-neutral pieces.
- **Clause 2 (balance):** ≤6 NON-KING non-neutral pieces AND cancel-queens + 1-to-3 valuation balances.

The asymmetry (total vs non-king) is principled: catch-all skips analysis (small piece counts are stall-prone often, even when balance fails); balance check applies the analytical filter (only activates genuinely-balanced larger compositions).

**Cancel queens.** `q = min(Q_W, Q_B)`. Reduce both sides' queen counts by `q`. One side M has `r = |Q_W − Q_B|` remaining queens; the other side L has 0.

**Valuation balance.** Each of M's `r` queens is independently assigned a value in `{1, 2, 3}`. Each non-king non-queen piece = 1. Activate iff there exists an assignment such that `(Σv_i) + N_M == N_L`. Equivalent numerical form: `r ≤ N_L − N_M ≤ 3r` (for `r ≥ 1`), or `N_M == N_L` (for `r == 0`).

**Strategic basis — why cancel-queens makes sense:**

Queens "cancel" via **mutual bishop pin** (see `project_piece_strategic_dynamics.md`): when both sides have queens, they can transform to bishop form and pin each other on diagonal LOS. Neither can spatial-move without being captured by the other. The pin is incomplete because queens have actions (no-spatial-move stalling), but actions don't make offensive progress. Net effect: queens largely neutralize each other.

The 1-to-3 valuation captures the fact that a queen is **flexible material** worth somewhere between 1 piece (when locked into a single role) and 3 pieces (when its full toolkit — transformation, manipulation, teleport-escape — applies). Each queen gets a free-choice value in this range.

## Strategic facts requiring re-verification

The following claims were stated in earlier memory but were NOT established under the operational stall-vs-forceable test described above. They need re-verification using the methodology in `project_tiny_endgame_analysis_methodology.md` before being treated as authoritative.

- **"K+Q vs K+B+2-attackers: forced for B."** Suspect — needs verification under queen-as-bishop escape and queen lock-down dynamics. May be drift-prone, not forced. (e.g., K+Q vs K+B+R: queen transforms to bishop, K+B+R coverage is much less than 64, queen-as-bishop escapes.)

- **"K+RQ vs K+RQ+non-Q: forced for B (the larger side)."** Probably still forced under queen lock-down (mutual bishop pin cancels queens, +non-Q decides), but the reasoning needs concrete tactical demonstration, not material-count hand-waving.

- **"K+RQ+RQ vs K+RQ: forced for B."** Probably still forced (more material, no good defense for the lone-RQ side), but verify under no-repetition assumption.

## Corrected strategic facts

**K+Q vs K+R+R+N is DRIFT-PRONE** (previously misclassified). The queen transforms to bishop. K+R+R+N can attack at most 63 of 64 squares. Queen-as-bishop always has at least 1 safe teleport destination. K+R+R+N cannot cornering the queen-as-bishop. Position is drift-prone for the K+R+R+N side.

This is one of the motivating cases for adding lone-queen coverage to the tiny endgame rule.

**K+RQ+B+B vs RQ+B is FORCEABLE for the K+RQ+B+B side** (case 3b, 6 pieces). Verified via extra-piece-conversion technique (see `project_piece_strategic_dynamics.md`): the side with 2 bishops (A) pins B's RQ and bishop with the 2 bishops. A keeps the pinning bishops R2-protected by alternating moves (manipulation Restriction 2 prevents B from manipulating just-moved pieces). B is forced into transformation-stalling (B's pieces can't safely spatial-move because they're pinned). A's RQ transforms to knight or rook and gets free turns to standard-capture pinned B pieces (standard capture works because pins only protect the pinned piece against its OWN movement, not against enemy captures). Position simplifies to ≤4 pieces; catch-all activates. Cancel-queens rule correctly does NOT activate this position (no over-coverage). Active rule over-covers it.

**Generalization**: similar extra-piece-conversion arguments likely apply to other r=0 diff=1 6-piece cases (3a, 3c, 3d, 3e, 3f) where the +material side has resources to pin the lone-RQ side's pieces and exploit R2-window timing.

## King-pin tactic (FORCING TECHNIQUE — verified)

When a position has 2 royals on the smaller side (both K and RQ alive) AND the larger side has a bishop or queen-as-bishop:

1. W (the +material side) positions a bishop with diagonal LOS to K_B's current square. K_B is pinned.
2. Kings have NO actions (per `RULEBOOK_v2.md` lines 153-172, kings only move). They MUST take a spatial move when it's their turn.
3. K_B's owner cannot "stall" K_B via actions — only the queens have actions.
4. When B's K must move (because all other B pieces are also constrained or moved, or simply because B chooses to move K), the move triggers reactive capture by W's bishop. K_B captured.
5. Position simplifies; remaining royals or pieces can be captured by overwhelming-material followup.

**Example: K+RQ+B vs K+RQ (5 pieces, both K alive) is FORCEABLE via king-pin.** Cancel-queens correctly does not activate (r=0, N_W=1, N_B=0, not balanced). Active rule correctly does not activate (B's non-king = 1, fails ≥2).

The king-pin tactic is the main reason why expanding the catch-all from ≤4 total to ≤4 non-king would be wrong: many 5-piece positions with 2 kings + 3 non-king pieces are forceable via king-pin, so they don't need (and shouldn't get) the catch-all's unconditional activation.

## Meta-lesson on over-classification (added 2026-05-14)

The previous session's analysis was systematically biased toward declaring positions stall-prone whenever a quick forced-win argument wasn't visible. This produces FAKE under-coverage findings for the cancel-queens rule that are not real problems. The over-classification pattern is the OPPOSITE error from the earlier surface-level "forceable everywhere" bias — both directions are mistakes.

**Before concluding under-coverage of the cancel-queens rule, multiple verification passes are required.** No fix is needed for nonexistent problems. The verification checklist in `project_tiny_endgame_analysis_methodology.md` enumerates the forcing tactics to check before defaulting to stall-prone.

## Older proposals (in `docs/potential-rule-changes.md`)

- **Section 1:** Bishop-deadlock fix (add "≤6 AND no knights/rooks remain" activation clause). Narrow targeted fix for the 4 originally-observed draws. Note: those AI-training "draws" need re-classification under the operational stall test — under stronger AI play the same compositions resolve decisively, suggesting they may be either forceable or stall-prone via cancellation-resistant dynamics. Pressure-test pending.

- **Section 4:** Pattern A/B/C with bishop-specific carve-outs. More precise in some scenarios but more complex; ad-hoc composition exclusions.

Both kept on file as fallbacks if cancel-queens proves inadequate.

## Pressure-testing plan (active focus)

Per `docs/potential-rule-changes.md` Section 7 methodology + Section 8 checklist:

1. Re-classify the §1 "bishop-deadlock draws" using the operational stall test (no-repetition optimal play). Are they actually stall-prone, or were they undertrained-AI artifacts?
2. Verify K+Q vs K+R+R+N drift status using full queen-as-bishop escape analysis.
3. Verify suspect strategic facts (K+Q vs K+B+2-attackers, K+RQ vs K+RQ+non-Q, K+RQ+RQ vs K+RQ) under the operational test.
4. Enumerate stall-prone positions systematically (start from Category 1 symmetric + Category 2 near-symmetric + Category 3 escape-by-bishop-form).
5. For each, check cancel-queens activation vs active-rule activation.
6. Tabulate coverage outcomes (correct activation, under-coverage, over-coverage).

## ADOPTED RULE (commit 1c7cdec, 2026-05-18)

The tiny endgame rule was REDESIGNED and is now in `RULEBOOK_v2.md` + `src/board.py`:

**Activates iff ALL of:**
- no pawns remain,
- at most **6 NON-KING** non-neutral pieces remain (boulder excluded, kings ignored),
- the position **balances** under cancel-queens + 1-to-3 valuation.

The ≤4-total catch-all was REMOVED (all ≤4 positions shown forceable for the +material side). Balance check: cancel queens (q = min(Q_W,Q_B)), then `r ≤ N_L − N_M ≤ 3r` for r≥1, or `N_M == N_L` for r=0.

## Open question: are there stall-prone >6-non-king positions? (in progress 2026-05-19)

The rule only applies at ≤6 non-king. Question: do >6 positions always resolve under optimal play (so the ≤6 scope is sufficient)?

**Key reframing (user, 2026-05-19):** the relevant question is whether a TRADE/CAPTURE can be forced that drops the position to ≤6 non-king (where the rule activates). A trade happens under optimal play only if it is materially equal/favorable for the initiator AND the resulting position favors them.

**Candidate stall-prone >6 case under analysis: K+RQ+PQ+B+B vs K+RQ+PQ+B+B (8 non-king, symmetric).**
- Queen-for-bishop trades are unfavorable (queen worth more) → not initiated.
- Only equal trades: PQ-for-PQ (non-royal) or bishop-for-bishop. Royal-queen trades lose a royal → unfavorable.
- Possible mutual queen lock-down (both sides transform RQ+PQ to bishop form, pin each other). Then only kings are free.
- If the locked bishops form a fixed LOS barrier the slow kings can't penetrate (king must avoid starting turns on enemy bishop LOS), the position may STALL.
- **Tentative: possibly stall-prone.** Not yet confirmed. Needs careful geometric analysis of whether the barrier is constructible AND a king can/can't penetrate. User flagged: manipulation/transformation can disturb bishop pins, but since manipulation can't move a just-moved piece (R2), forcing relationships are complex. Analysis ongoing.

**If confirmed stall-prone:** the ≤6 non-king scope under-covers, and we'd need to consider expansion (no clean predicate yet).

## CORRECTED claim (2026-05-19): manipulation does NOT chain into a friendly bishop reactive-capture

Earlier I claimed a queen could manipulate an enemy piece off a friendly bishop's LOS to force a reactive capture. WRONG — reactive-capture timing requires the trigger move to be on the turn IMMEDIATELY before the bishop's turn. A manipulation by the bishop's own side is on that side's turn, so an opponent turn always intervenes before the bishop can act, expiring the window. See `project_piece_strategic_dynamics.md`. The only timing-valid manipulation→bishop scenario is self-capture (opponent manipulates the bishop-owner's own piece off the LOS).

## Methodology + insights (still valid)

- **Operational no-repetition stall test** (2026-05-14): assume repetition rule absent, check whether optimal play stalls infinitely.
- Bishop is an ACTIVE piece (global teleport + pin power).
- Queens lock-down each other via mutual bishop pin.
- Queens escape via bishop-form teleport when opponent's coverage < 64.
- K+Q vs K+R+R+N is drift-prone.
- All ≤4-total positions are forceable for the +material side (so ≤4 catch-all was removed).

Treat `RULEBOOK_v2.md` as authoritative for the current rule. Do not assume any proposed variant is adopted without checking the rulebook + recent commits.

## ===== SESSION HANDOFF 2026-05-20 (read this first after a context reset) =====

**Branch:** `claude/v2-knight-rule-refinement-45` (worktree at .claude/worktrees/tender-haibt-45bbac). Recent commits pushed to origin through 511d2bd; later commits (10498a5, 17cb52b, and anything after) may be local — run `git log --oneline -15` and `git status`.

**DONE and committed:**
- Repetition rule invulnerability-cycle fix (commit c7e0ffd) + end-to-end test (457c849). VERIFIED working; user's earlier bug reports were from running pre-fix code (commit c8b3c20).
- Tiny endgame rule REDESIGNED (commit 1c7cdec): now "no pawns AND ≤6 NON-KING pieces AND cancel-queens + 1-to-3 balance." The ≤4-total catch-all was REMOVED (all ≤4 positions shown forceable). In RULEBOOK_v2.md + src/board.py is_tiny_endgame().
- .gitignore broadened to silence __pycache__/.pyc noise (511d2bd).
- Corrected manipulation→bishop reactive-capture docs: single manipulation by bishop's own side does NOT trigger reactive capture (timing); only the DOUBLE-manip is valid (10498a5, 17cb52b).

**IN PROGRESS (do these next):**
1. **Bishop double-manipulation reactive-capture code fix.** The nuance: White manipulates Black's piece off White's bishop's LOS (turn N); Black manipulates White's bishop to reactive-capture that Black piece on turn N+1 (the immediate next turn, target moved on immediately preceding turn). Parallels the knight double-manip (rulebook line 311). Code currently BLOCKS it (user verified: White manip Black bishop b6→d6, Black cannot manip White d4-bishop to capture d6). FIX = rulebook clarification + failing test + code change (tests-first). NOT a same-color capture (capturing piece is enemy-colored). See project_piece_strategic_dynamics.md "Double-manipulation bishop nuance — CORRECTED 2026-05-19" + "Self-capture terminology".
2. **Stall analysis part (a):** is mutual queen lock-down even CONSTRUCTIBLE + MAINTAINABLE by both sides in K+RQ+PQ+B+B vs K+RQ+PQ+B+B (8 non-king, symmetric)? This is the leading candidate >6 stall-prone position. If lock-down can't be maintained, position is forceable and rule's ≤6 scope is sufficient. If it holds + kings can't penetrate the bishop-LOS barrier, position is stall-prone → rule under-covers >6.

**KEY open question:** Are there stall-prone >6-non-king positions? If yes, the rule's ≤6 scope under-covers. The reframing (user): a position is NOT stall-prone if a trade/capture can be forced that drops it to ≤6 (rule activates). Trades happen under optimal play only if equal/favorable AND post-trade position favors initiator.

## Stall analysis part (a) findings — K+RQ+PQ+B+B vs same (2026-05-20)

Question: is the mutual queen lock-down CONSTRUCTIBLE + MAINTAINABLE? And, bigger picture, is this 8-non-king symmetric position stall-prone?

**Constructibility: YES.** Both sides transform RQ+PQ to bishop form (each side then has 4 bishop-form pieces + K) and teleport them onto shared diagonals with the opponent's bishops (mutual pins). Bishops teleport freely to any safe square; the only non-bishop threat is the slow king, so safe squares are abundant. In a symmetric position both sides build it symmetrically (mirror).

**Maintainability: UNCERTAIN but plausibly stable.** Disturbing a pin requires un-transforming a queen-as-bishop to base form (to regain manipulation) — but that frees the opponent's correspondingly-pinned piece, AND the un-transformed queen is still pinned (base form on the enemy bishop's diagonal, can act but not spatial-move). Net effect of disturbance is unclear: it's a trade of "gain manipulation ability" for "free an opponent piece." User's hint: a pinned enemy bishop can't refresh its R2-immunity (moving it = captured), so it stays manipulable — but exploiting that requires breaking your own pin first.

**BIGGER-PICTURE ARGUMENT (the likely decider) — mirror strategy:** In a fully symmetric position, white moves, black mirrors (180° rotation, since the variant is rotationally symmetric). Symmetry is restored after each move-pair. Crucially in THIS variant: capturing ONE royal does NOT win (must capture BOTH K and RQ). So even if white forces a capture, black mirror-captures, and after a symmetric exchange the position is symmetric again (both down the same material). The first-mover advantage does NOT obviously convert, because no single capture is decisive and symmetry self-restores.

**Tentative conclusion: K+RQ+PQ+B+B vs same is LIKELY STALL-PRONE** (mirror strategy maintains symmetry indefinitely; no side forces the BOTH-royal capture needed to win). If correct, the rule's ≤6-non-king scope UNDER-COVERS this >6 position.

**The open hole in the argument:** the mirror strategy BREAKS if the first-mover can force an ASYMMETRIC capture — one where white's move both captures AND prevents black's mirror-capture (so symmetry isn't restored). Central-square interactions (the board center, where rotational images collide, plus the boulder on the central intersection) are where mirroring is most likely to break. I could NOT determine whether such a symmetry-breaking forcing line exists. This is THE unresolved question for whether >6 has genuine stall-prone positions.

**If confirmed stall-prone:** need to decide whether to expand the rule beyond ≤6 non-king (no clean predicate found yet — "≤8 non-king with ≥2 bishops + ≥1 queen each" is ad-hoc), accept the gap, or rely on the repetition rule for these rare dense-symmetric cases (slow but eventually terminating). NOTE: a symmetric position under the repetition rule is also parity-decided eventually, so it's not a true infinite draw — just impractically long, which is exactly what the tiny endgame rule was meant to bound.

**NEXT STEP for a future session:** try to construct (or rule out) a symmetry-breaking forced capture for the first-mover in K+RQ+PQ+B+B vs same, focusing on central-square / boulder interactions where the 180° mirror collides. This decides whether >6 symmetric positions are stall-prone.

## Symmetry-breaking forced-capture analysis — K+RQ+PQ+B+B vs same (2026-05-20, COMPREHENSIVE)

GOAL: decide whether the first-mover can force a symmetry-breaking WIN, OR whether the position is a true infinite stall (under the no-repetition operational test). This decides whether the rule's ≤6-non-king scope is SUFFICIENT or UNDER-COVERS dense symmetric >6 positions.

### Two competing arguments

**ARG 1 — stall-prone (mirror-shuffle).** Black mirrors white via 180° rotation (variant is rotationally symmetric). KEY: capturing ONE royal does NOT win (must capture BOTH K and RQ). So a forced capture gets mirror-captured, and a symmetric exchange self-restores symmetry. Under the no-repetition test, if both sides can shuffle while avoiding forced captures, the game stalls infinitely → stall-prone → rule under-covers.

**ARG 2 — forceable via FORCED TRADE-DOWN (the strong argument).** If forks/captures are FORCEABLE in dense positions (user's stated intuition: "it's easy to make a fork with that many >6 non-king pieces"), then: white forks two black pieces → black's best response is to mirror-fork (declining loses a piece outright = material disadvantage) → mutual symmetric trade → piece count drops by 2 → repeat → eventually reaches ≤6 non-king → the RULE ACTIVATES and guarantees a decisive result. So the position does NOT stall infinitely; it reduces to a rule-covered ≤6 position. NOT stall-prone → rule SUFFICIENT.

Symmetric non-king counts are even (8,10,12...), so trades by −2 land exactly on 6. ✓ Any 4-non-king-per-side composition must include forking power (max 2 bishops/side, so the other 2 are queens [transform→knight] / rooks [L-step fork] / knights). ✓

### THE CRUX (unresolved by hand)

Are forks/captures FORCEABLE in symmetric dense positions, or can BOTH sides avoid them indefinitely (pure mirror-shuffle)?
- Forceable → trade-down → ≤6 → **rule SUFFICIENT** (not stall-prone).
- Avoidable → mirror-shuffle → infinite stall under no-repetition test → **rule UNDER-COVERS**.

### Symmetry-breakers that aid the first-mover (support ARG 2 / forceable)

1. **The boulder.** Single SHARED neutral piece + cooldown ("after the boulder moves, both players must take one turn before it can move again"). When white moves the boulder, black CANNOT mirror (only one boulder; it's on cooldown). This breaks the literal mirror and gives white a tempo/zugzwang-like lever. (Counter: black abandons pure mirroring for a direct defense — queen-as-bishop lock + king hiding behind bishop-LOS barriers.) Boulder also blocks central diagonals while on the intersection; moving it off opens central bishop LOS asymmetrically.
2. **Central-square collisions.** Under 180° rotation, central squares (around d4/d5/e4/e5) map near each other; white's central move and black's rotational image can collide/block, breaking clean mirroring. This is where a symmetry-breaking forced capture is most likely to exist.

### CURRENT BEST ASSESSMENT (2026-05-20)

**LIKELY rule-SUFFICIENT (lean: NOT stall-prone), via the forced-trade-down mechanism.** Reasoning: (a) dense positions make forks hard to avoid (user's intuition, plausible); (b) forced trades reduce ANY symmetric >6 position to ≤6 where the rule guarantees decisiveness; (c) the boulder + central collisions give the first-mover concrete symmetry-breaking levers. The "infinite mirror-shuffle stall" requires that NO capture can EVER be forced — unlikely in a dense board with forking pieces.

**This REVISES the earlier (2026-05-19/20) tentative lean toward "stall-prone."** The forced-trade-down argument (reduce to ≤6, where the rule takes over) is the key insight that was under-weighted before. The mirror strategy maintains symmetry but does NOT prevent trades; trades reduce piece count to the rule-covered range.

**RESIDUAL RISK (the open question to settle):** does there exist a dense symmetric position where both sides can avoid ALL forced captures indefinitely (true mirror-shuffle, no forceable fork)? If NO such position exists, the rule is provably sufficient. If one exists, the rule under-covers it. NOT ruled out by hand.

**NEXT STEP (post-reset):** verify computationally (or by a rigorous fork-forceability argument) whether symmetric dense positions (e.g., K+RQ+PQ+B+B vs same) admit indefinite fork-avoidance. Equivalent question: in a symmetric dense position, can the side-to-move always FORCE a capture within a bounded number of turns? If yes → rule sufficient. Focus on whether a careful defender can keep all pieces mutually un-forkable while mirroring.

### Practical bottom line for the rule

Even in the worst case (a fork-avoidable dense symmetric position exists), such positions are RARE and would still terminate under the repetition rule (just slowly). The forced-trade-down argument strongly suggests the ≤6 scope is sufficient for the overwhelming majority of (likely all) >6 positions. Recommendation: treat the ≤6 rule as sufficient pending computational verification; do NOT expand the rule's scope without a concrete demonstrated stall-prone >6 position (none found yet).

## Fork-forceability — user's insight (2026-05-20)

The user notes: a FORCEABLE fork in dense symmetric positions would likely come from a **pawn-promoted queen transformed (e.g., to knight)** threatening MULTIPLE enemy pieces at once — the opponent's royal queen, promoted queen, and/or bishop(s). This is the concrete mechanism for the forced-trade-down argument: PQ-as-knight forks two enemy pieces; the opponent saves the more valuable (RQ) and loses the other, OR mirror-forks → symmetric trade. Either way a capture is forced, reducing toward ≤6. This SUPPORTS the "rule-sufficient" lean (forks are forceable via transformed promoted queens in dense positions). Analysis can continue from here: verify that the PQ-as-knight fork is actually FORCEABLE (opponent can't keep all forkable pieces mutually un-forkable while defending both royals).

## Fork mechanisms (2026-05-20): both knight AND rook can fork
- **Knight (or queen-as-knight):** SHORT-range forks (radius-2 pattern).
- **Rook (or queen-as-rook):** LONG-range forks (1-orth + 0-7-perp L-step reaches distant pieces).
Both support the forced-trade-down argument in dense positions. The forceable-fork that reduces symmetric >6 positions to ≤6 can come from either a transformed promoted-queen-as-knight (short-range) or a rook / queen-as-rook (long-range).

## User clarifications on the symmetry / stall analysis (2026-05-20, continued) — AUTHORITATIVE

These correct/sharpen the >6 symmetric stall framework. The clarifications are authoritative; my incorrect intermediate analysis is not recorded.

**Stall-prone definition (reaffirmed):** a position is stall-prone iff, under optimal play by both players and WITHOUT the repetition rule, the game goes on **forever**. If the game does NOT go on forever, a forced win must be possible for some side.

**Royals are captured ONE AT A TIME — do NOT assume simultaneous capture.** Flawed assumption I made: that a symmetric trade of royals keeps the defender safe because "both royals must be captured." WRONG. From both-royals-each, a symmetric capture of one royal from each side → each side has ONE royal left → then a further capture can take a side to ZERO royals, ending the game. So the **mirror/copycat strategy does NOT guarantee safety** — captured one at a time, both royals can eventually fall.

**Any trade reducing to ≤6 non-king activates the tiny endgame rule → the position is no longer stall-prone.** A trade dropping the non-king count to ≤6 hands the position to the (active) tiny endgame rule, which forces a decisive result. So when checking whether a >6 position stalls, a forced trade into ≤6 is a **RESOLUTION**, not a continuation of the stall.

**Three ways symmetry can be broken (C):**
1. **Capture across the center** — the EASIEST and most often available; a piece captures the opponent's 180°-image piece near the center where a square and its image are close. The defender then cannot mirror (its mirror-piece is gone).
2. **Boulder move** — single shared boulder + cooldown makes the mirror move unavailable. BUT the boulder's presence is NOT guaranteed: a king may have captured it earlier (only kings capture the boulder). So this lever may not exist in a given endgame.
3. **Capturing the opponent's LAST royal** — ends the game immediately, before the opponent can capture your last royal in reply. Inherently asymmetric and **turn-order dependent** (the side to move gets there first).

Since the boulder may be absent, the two reliable symmetry-breakers are **capture-across-the-center** (easiest, often possible) and **last-royal capture**.

**Where this leaves the lean:** the corrected framework REMOVES the defender's main stall tool (mirror is not safe) and notes symmetry is often breakable, which leans toward **forceable** (≤6 scope likely sufficient) — re-affirming the prior recorded lean, NOT reversing it. The residual unproven step: whether the defender can keep EVERY available reduction *unfavorable for the initiator* (see [[Piece strategic dynamics — bishop active-pin, queen lock-down, queen-as-bishop escape, action stalling]] "Forks, pinning ... trade-favorability"), which routes through the parity of symmetric ≤6 rule-active positions — a geometry-dependent combinatorial question not cleanly settled by hand.

## DECISION (2026-05-20): ≤6 non-king scope ACCEPTED as SUFFICIENT — >6 stall question CLOSED

**User decision:** the tiny endgame rule's **≤6 non-king scope is accepted as sufficient; the rule will NOT be expanded beyond ≤6 non-king.** The >6 dense-symmetric stall question is CLOSED for rule-design purposes.

Rationale (leans forceable): the mirror/copycat does NOT save the defender (royals fall one at a time; any trade to ≤6 activates the rule); symmetry is breakable, easiest via capture-across-center (often available); and the last-royal asymmetry favors the side to move at the decisive one-royal-each stage.

**Documented residual (known, unproven edge — do not re-litigate without new evidence):** whether the side-to-move is advantaged in a symmetric rule-active position is a geometry-dependent zugzwang / distance-count combinatorial question that does NOT reduce to a clean parity (verified by working the simplest case, K vs K, which is already a non-trivial distance-count game) and is not provable by hand. Engine verification is impractical (engine not near-optimal; training to optimality too costly). In the worst case a rare dense-symmetric >6 position could be stall-prone; if so it would still terminate (slowly) under the repetition rule, and no clean predicate exists to expand the rule cleanly. **Decision: accept ≤6 as the practical, sufficient scope; do not expand. Re-open only if a concrete stall-prone >6 position is ever demonstrated.**

## Stall residual is in Category A, NOT Category C — correction 2026-05-25

A 2026-05-25 analysis attempt placed the ~5% stall residual in Category C (queen-asymmetric balanced, r ≥ 1). **That was wrong** — user-verified, see below.

**Why Category C is mostly FORCEABLE (not stall-prone):**

- In an asymmetric balanced position like K+RQ+PQ+B vs K+RQ+R+B+N (r=1, N_M=1, N_L=3, diff=2, 7 non-king), the +non-queen side has concrete attackers (rook, knight) that convert the diff-2 material advantage by **standard-capturing the queen-side's pinned queens-as-bishop**. (Standard captures bypass pins — a pinned piece is only protected from its OWN movement, not from being captured by an enemy.)
- The mutual-bishop-pin lockdown that the queen-side would construct requires ALL of its bishop-form pieces to participate as pinners — leaving none free to defend each other. Since the +material side has more free pieces (per the diff), it has at least one unpinned attacker that picks off pinned queens-as-bishop.
- Additionally, any single capture from a 7-non-king position drops to ≤6 (rule territory). Most single-capture outcomes preserve balance, so they land in covered territory. To stall at 7 you'd need both sides to find EVERY available capture unfavorable — which doesn't hold in asymmetric positions where the +material side has favorable conversions.

**The actual stall residual is Category A (truly symmetric, r=0, same piece types each side).**

In symmetric positions, every threat by one side is mirror-counterable by the other; every defensive move is mirror-applicable. Captures only happen with mutual agreement (symmetric pair-trades). Both sides refuse to initiate captures — if the disfavored side would lose the trade-down sub-game, they DEFEND the attacked piece instead (a defense that the symmetric mirror automatically supports). Pure tempo waste → stall under the operational test.

**Canonical example:** K + 3Q + B  vs  K + 3Q + B (8 non-king, r=0, N=1 each, balanced).
- Both sides have 3 queens + 1 bishop. With enough captured-pawn / captured-bishop / captured-knight history, queens can transform into all forms. Mutual bishop-pin lockdown is trivially constructible (many bishop-form pieces per side, lots of diagonals to pin on).
- Each side's real bishop can mutual-pin the other's. All queens-as-bishop pair-pin each other. Action-stalling preserves every locked queen indefinitely.
- No single capture gains either side anything: the +material side can't get a free piece (every threat is mirror-defended), and equal trades just shrink the symmetric position by 2.

**Other symmetric 8-piece candidates** (all r=0, all balanced, all potentially stall-prone):
- K+RQ+R+B+N vs same.
- K+RQ+PQ+R+B vs same.
- K+RQ+PQ+PQ+B vs same.
- K+RQ+PQ+PQ+PQ vs same.
- K+R+R+B+N vs same (no queens; trivial mutual material symmetry).

**Revised category table:**

| Category | Stall-prone share (revised) |
|---|---|
| A (truly symmetric)                 | ~10–20% — the real residual |
| B (near-symmetric)                  | ~0–5%  |
| C (queen-asymmetric balanced, r ≥ 1) | ~0–5% — +material side has the conversion edge |

Total residual size is similar (~5% of all newly-covered compositions if ≤6 were dropped), but it lives in A, not C.

**Implication for any future rule-extension discussion:**

- Extending to ≤8 catches the dominant symmetric 8-piece stalls.
- Asymmetric balanced 7-8 (Category C) is over-coverage, but harmless — captures happen organically before distance counts saturate.
- Extending past ≤8 catches symmetric 10+ candidates (rarer) at additional over-coverage cost.

The earlier "Decision: accept ≤6 as the practical, sufficient scope" stands as a recorded user decision (2026-05-20), but this correction sharpens the picture if it's ever re-opened: the right next step would be **≤8**, not removing the cap entirely.

## FURTHER refinement (2026-05-25, same session) — Category A residual is essentially negligible

After deeper user-led analysis the ~10–20% estimate for Category A above is also overstated. The actual residual across all categories is essentially **0%**. Reasoning chain (user-confirmed):

**The K-race + first-mover-tempo + last-royal-asymmetry chain forces all symmetric balanced positions:**

1. In symmetric 3Q+B vs 3Q+B (or any Category-A composition), the first mover (W) can maneuver to threaten Black's RQ. Each maneuvering step (un-pin a queen via manipulation, reposition to threaten the RQ) is symmetrically mirrored by Black — leading to *mutual* RQ threats.
2. At the mutual-threat point, W captures B's RQ on W's turn. B mirror-recaptures W's RQ. **Mutual RQ trade**: both sides reduced to one royal (K only). Material reduced by 2 non-king (the two RQs).
3. Now in the K-only sub-game (with all other pieces still present), every subsequent royal capture is a *last*-royal capture that ends the game immediately — mirror cannot save the defender because the game ends *before* the mirror move.
4. W as the first mover gets there first via tempo, either via direct king-capture-on-adjacency or via budget exhaustion forcing B into an illegal-move loss.

**Reinforcing factors:**

- **Central captures are geometrically easy** in symmetric positions: a piece at d4 is diagonal-adjacent to its mirror at e5. Capture-across-center is a natural symmetry-breaker that mutual trade-down can leverage.
- **Manipulation breaks pins**: a base-form queen manipulates the pinning bishop away. To stay un-manipulable, the pinner must move every turn (R2), costing tempo and disrupting its own attacks. Lockdowns aren't free.
- **More pieces ⇒ less stall-prone** (the principle): mirror defense requires perfect coordination across N pieces; threat combinations grow combinatorially; central interaction grows; mirror breaks somewhere. So at 7-8 non-king, the conditions for stall are *harder* to maintain than at ≤6.

**Empirical confirmation of the K-race argument:**

Attempted to construct a stall-prone 3Q+B vs 3Q+B position. Tried diagonal-clustered lockdowns, spread mutual-pin layouts, back-rank static setups. In every case the configuration was either brittle (one bishop move triggers a reactive-capture cascade), or had free attackers that broke the engagement-refusal, or admitted manipulation-breaks that costs tempo to defend. **No stall-prone construction found.**

**FINAL revised table (this is the authoritative version; supersedes the ~10-20% estimate above):**

| Category | Stall-prone share (final) |
|---|---|
| A (truly symmetric)        | ~0% — K-race + first-mover-tempo + last-royal asymmetry forces |
| B (near-symmetric)         | ~0% — slight material asymmetry usually decides |
| C (queen-asymmetric balanced) | ~0% — +material side converts via standard capture of pinned queens-as-bishop |

**Total residual: essentially negligible.** ≤6 is sufficient because the threshold matches where stalls cluster (low piece counts where mirror defense is easier and forcing patterns are rare). Extending to ≤8 or beyond catches positions that are already forceable — pure over-coverage. The 2026-05-20 user decision to keep ≤6 stands and is now well-supported analytically. **Do not re-open without a concretely-demonstrated stall-prone >6 position with a worked-out optimal-play line showing W cannot force.**

## First-mover analysis under the active rule (2026-05-25, revised after user correction)

User raised whether the rule's *local* constraint disadvantage (W is the first forced to change royal distance after count[d₀] = 3) might cancel W's global parity advantage. Initial analysis leaned too heavily on a "Black mirrors perfectly" assumption — **that was wrong.** Black's optimal strategy is almost never strict mirror: mirror requires perfect rotational symmetry, is rare in practice, and is only one of many possible defenses. Black's real best play involves selecting from {recapture, retreat the threatened piece, counter-threat, allow capture}, not blindly mirroring.

**Corrected forceability argument** (does NOT rely on B mirroring):

The first-mover advantage in symmetric >6 positions rests on four levers:

1. **Tempo asymmetry.** W moves first; W's threats are one move ahead of B's. In any race (royal-attack setup, central capture maneuvering, etc.), W gets there first.

2. **Captures across center — broad definition.** ANY capture where W's piece lands at the *rotational image* (180° symmetric position) of its starting position is unmirrorable. This is NOT limited to adjacent central pairs (d4↔e5 etc.) — it includes long-range captures via rook's 2-step pattern, knight's radius-2 + jump-capture, queens-as-rook/knight, king at chebyshev-1 of a mirror piece. Example: W rook at d2 captures B piece at e7 (1-orth east + 5-sweep north). B can't mirror-respond because B's mirror piece (the one at e7) is gone after the capture. B must pick a different response.

3. **Last-royal-capture asymmetry — the decisive endpoint.** Once position reduces to 1-royal-each (typically K-only after mutual RQ trade), W's *first* royal capture *ends the game immediately*. B never responds. First-mover tempo + game-ending capture = W wins the K-race.

4. **Squeezing under retreat.** If B's defense is to retreat threatened pieces (avoiding engagement), B's pieces get pushed back over time. Eventually B has nowhere to retreat; either accepts capture or counter-attacks (mutual trade → W's tempo wins). Under the active rule (when ≤6), budget exhaustion forces B's hand. Under the repetition rule, repetition forces a 3rd-recurrence loss — and W's tempi mean B faces that endpoint first.

**B's defense options analyzed:**
- **Recapture** (after a capture by W): mutual trade, material reduces, parity preserved (W still to move at the smaller position). Eventually K-only, W wins.
- **Retreat the threatened piece**: avoids immediate capture, costs B a tempo. By symmetry, W's pieces are symmetrically threatened by B's counter-threats; W also defends, but W is one tempo ahead. B is gradually squeezed.
- **Counter-threat**: mutual threats → mutual trade → W's tempo wins.
- **Allow the capture** (no recapture): B is down a piece, asymmetric position with W's material advantage. W presses, wins.

In every branch, W wins. None of these rely on B mirroring.

**Local constraint disadvantage revisited:**

The local "W is first forced to change distance" cost is a marginal positional disruption — W has to spend a turn on a royal move when count[d₀] = 3 and W wants a non-capture turn at d₀. But this is just one move, and W has tempo to spare. The four levers above swamp this marginal cost.

**Verdict (conclusion unchanged, reasoning sharpened):** symmetric >6 positions are forceable for the first mover under optimal play. The argument rests on tempo + captures-across-center (broad) + last-royal-asymmetry + endpoint dynamics, NOT on Black mirroring. ≤6 scope remains sufficient. Goal 1 closed.

**Residual uncertainty:**

If a position exists where B's defensive resources EXACTLY match W's offensive potential — no trade forceable, no royal-threat setup possible, no central-capture geometry available — it could in principle stall. Attempts to construct such a position have failed. Random self-play data shows 100% decisive outcomes at sufficient max-turns. **Practical residual is essentially zero**, though the theoretical possibility cannot be eliminated by hand analysis. If a concrete stall-prone >6 position is ever demonstrated (with a worked-out optimal-play line showing W cannot force), re-open the rule scope question.

## Why more pieces ⇒ LARGER first-mover advantage (2026-05-25)

The threshold ≤6 isn't arbitrary; it tracks where stall risk concentrates. Five compounding reasons more pieces increase W's edge:

1. **Combinatorial defensive coordination.** B's defenders scale linearly with N; two-piece threat combinations scale as ~N(N-1)/2; higher-order combinations grow even faster. At N=4 (≤6 zone), ~6 two-piece threats to defend; at N=8, ~28. B can't defend all; W finds an unguarded threat.
2. **Broader rotational-image geometry.** More (piece, mirror-square) pairs where W can geometrically reach its rotational mirror in one move ⇒ more unmirrorable captures.
3. **More spare pieces for diversion/sacrifice.** With ≤6, every piece is precious; with >6, W has slack to invest positionally.
4. **Fewer retreat squares.** B's "running away" defense needs empty safe squares; more pieces on the board ⇒ fewer empty squares ⇒ B can be squeezed into bad positions.
5. **Multiple simultaneous threat races.** W's tempo asymmetry compounds across N races; W needs to win one race, B needs to win all defensive races.

Stall risk is **inversely correlated with piece count.** ≤6 is precisely where defensive coordination becomes tractable; >6 is progressively MORE forceable, not less.

## Capture-initiation chain (full statement)

W initiates a capture in a >6 position only when all three requirements hold:

**(a) Favorable resulting position.** Whether B recaptures (mutual trade, symmetric reduction by 2 non-king, W to move) or B doesn't recapture (W +1 material, asymmetric, W to move) — both branches leave W to move at the post-capture position. W chooses captures meeting this bar.

**(b) Favorable timing at activation.** When the trade chain reduces material to ≤6 non-king, the tiny endgame rule activates. Parity preserved across mutual trades ⇒ W lands at ≤6 with W to move. At ≤6 with W to move under the active rule, the budget endpoint (41 non-capture turns, odd ⇒ B faces saturation turn 42) + K-race + last-royal-asymmetry all favor W. Activation timing is automatically favorable.

**(c) Local distance-count disadvantage is negligible.** W is the first forced to change distance after count[d₀]=3 — one tempo cost. W has tempi to spare from the four asymmetric levers (tempo, captures across center, last-royal, squeezing). One disrupted turn doesn't flip the outcome. W can also schedule trades so budget exhaustion timing lands favorably.

All three requirements are met for W in symmetric >6 positions. Hence W initiates captures, trade chain runs to ≤6, rule activates with W to move, W wins.

**Final verdict: ≤6 is sufficient. Goal 1 closed. Do not re-open without a concrete worked-out stall-prone >6 position.**
