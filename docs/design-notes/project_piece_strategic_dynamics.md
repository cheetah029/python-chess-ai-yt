---
name: Piece strategic dynamics — bishop active-pin, queen lock-down, queen-as-bishop escape, action stalling
description: Strategic capabilities of pieces beyond movement rules. Bishops are ACTIVE pieces with global teleport movement and diagonal pin power. Queens can lock down each other via mutual bishop pin. Queens can escape via bishop-form teleport. Actions stall turns without triggering reactive capture.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
# Bishop is an ACTIVE piece, not passive

**Common misconception (mine, repeatedly)**: bishops are weak/passive because they "only capture reactively along diagonals."

**Reality**: bishops are powerful active pieces with two distinct strengths.

## Movement: GLOBAL TELEPORT (not diagonal-only)

Bishops move by teleporting to ANY safe square on the board — NOT constrained to diagonals.

A "safe square" for bishop teleport is one that:
- Cannot currently be moved to by an enemy non-bishop, non-queen-as-bishop, non-boulder piece.
- Cannot currently be captured by an enemy non-bishop, non-queen-as-bishop, non-boulder piece.
- "Capturable" includes knight jump-capture targets.

Enemy bishops, queen-as-bishop, and boulder are EXCLUDED from the safety check. So a bishop CAN teleport into another bishop's diagonal LOS (the safety check doesn't block it).

This means: bishops have **maximum mobility** of any piece in the variant. They can repositioned anywhere safe in one turn.

## Capture: reactive but powerful as a pin

Bishop captures only via reactive mechanic: a piece P that begins its move on a square within the bishop's diagonal LOS, then makes a spatial move, can be captured by the bishop on the bishop's IMMEDIATE NEXT turn. The bishop teleports to P's destination square (teleport restrictions don't apply to this capture).

The "begins its move on the LOS" criterion is what makes the bishop's reactive capture an ACTIVE PIN: any piece on the bishop's diagonal at the start of its turn is effectively pinned — its next spatial move triggers capture.

## Pin power: teleport in to threaten

**A bishop teleporting onto an enemy's diagonal "pins" that enemy.** If the pinned piece spatial-moves, it gets reactive-captured. If it stays still (only available for queens, via actions), it must continue stalling, making no offensive progress.

Bishops are not passive. They proactively threaten by teleporting into pin positions, then waiting for the pinned piece to either move (capture) or stall (no progress).

## Mutual bishop pin: lock-down

Two bishops on each other's diagonal LOS = mutual pin. The first to spatial-move gets captured by the other.

For **regular bishops**, mutual pin is a complete lock-down: regular bishops have no actions available, so they MUST spatial-move when it's their turn (otherwise they violate "Players must make a turn"). Each bishop player faces a forced loss of their bishop when their turn comes.

For **queens-as-bishop**, the lock-down is incomplete: queens have actions (transform, manipulate) available, so they can stall on a pinned diagonal without spatial-moving. But they make no offensive progress while pinned.

# Queen lock-down strategy (KEY INSIGHT)

**Strategic principle**: when both sides have queens AND one side has extra non-queen material, the side with extra material can WIN by exploiting mutual bishop pin to neutralize the queens.

## The strategy

1. Both queens transform to bishop form (action turns).
2. Each side positions their queen-as-bishop on the other's diagonal LOS (typically a "staring" position).
3. Neither queen can spatial-move without being captured by the other queen-as-bishop.
4. The queens are effectively **canceled out** by the mutual pin.
5. The extra non-queen material on one side then decides the position.

## Why this works strategically

- Mutual bishop pin neutralizes both queens — neither can make offensive progress without being captured.
- The side with extra non-queen material can use that piece freely to threaten / capture / make progress while the opponent's queen is locked.
- The opponent's queen, being pinned, can only stall via actions or accept capture by moving.

## Caveat — queens stall via actions, complicating the lock-down

- Queens have actions (transformation, manipulation) that don't involve spatial movement.
- A pinned queen-as-bishop can take infinite actions on the same square WITHOUT triggering reactive capture.
- This means the pinned queen doesn't "lose" by being pinned — she can stall forever.
- BUT: actions cannot make offensive progress. The pinned queen-side cannot threaten the opponent's pieces via actions alone (manipulation can reach pieces in LOS, but the threats are weaker than free movement).
- Meanwhile the opponent makes progress with their extra material.

## Mechanism in detail — why the queen can't easily escape

- If the pinned queen transforms (action), she stays on the same square. The enemy bishop's LOS still includes her square. Stalling continues.
- If she takes another action, same situation.
- If she spatial-moves (in any form), the enemy reactively captures.
- Transformations cycle through 4 forms (base, rook, bishop, knight) — finite options but with no repetition rule there's no theoretical bound on cycling.
- BUT: in practice, the queen needs to spatial-move eventually to make any offensive progress. Pure action stalling is purely defensive.

## Implications for tiny endgame rule design

The queen lock-down dynamic is **why the cancel-queens framing of the proposed rule makes strategic sense**:

- When both sides have queens, their queens largely "cancel" via mutual bishop pin (or just by mutual threat).
- The remaining non-queen material decides the position.
- The cancel-queens algorithm computationally mirrors this strategic reality.

But the strategic reality is more nuanced than the simple "queens cancel" framing because of action stalling and queen-as-bishop teleport escape.

# Queen-as-bishop escape (KEY DEFENSIVE TOOL)

**Strategic principle**: a lone queen can defend by transforming to bishop form and teleporting indefinitely.

## The mechanism

- Queen transforms to bishop form (action).
- Queen-as-bishop has the bishop's global teleport movement.
- Each turn, queen-as-bishop teleports to a safe square.
- "Safe" = not attacked by enemy non-bishop pieces.

## When this fails: enemy covers 64 squares

The queen-as-bishop escape FAILS only if the enemy can collectively attack ALL 64 squares (no safe destination exists).

This is a HIGH bar. With 2-3 pieces, achieving 64-square coverage is geometrically infeasible.

## Verified example: K+Q vs K+R+R+N is drift-prone

- The K+R+R+N side has 4 pieces.
- Across all reachable positions of K+R+R+N, they can attack at most **63 of 64 squares**.
- At least 1 square always remains unattacked.
- Queen-as-bishop teleports to that safe square each turn.
- K+R+R+N cannot corner the queen-as-bishop → cannot force its capture → drift-prone for K+R+R+N side.

## Counter-strategy by the attacking side

If the queen-side relies on queen-as-bishop escape:
- The attacking side must achieve 64-square coverage (often impossible).
- The attacking side can manipulate the queen-as-bishop to relocate it, but note: manipulation does NOT chain into a friendly bishop reactive-capture (timing — see "Manipulation does NOT trigger a friendly bishop's reactive capture" below). The manipulated piece is also frozen for one turn (Restriction 1), which is a positional disruption but not a capture.
- OR the attacking side can pin the queen-as-bishop with a bishop, forcing her to stall via actions while attacking other pieces.

## Implication for piece-value framing

This is why queens are "flexible material worth 1-3 pieces" in the cancel-queens + 1-to-3 valuation framing. A queen that can transform to bishop and teleport-escape is much more valuable than a static piece — it gains the bishop's global mobility AND survives indefinitely against limited-coverage attackers.

# Transform availability depends on what was CAPTURED (verified 2026-05-20)

A queen can transform into a form (rook / bishop / knight) **only if a friendly piece of that type was captured earlier** (`RULEBOOK_v2.md` line 212/148). This is easy to forget and changes escape/lock-down analysis:

- If both of a side's **bishops are still on the board**, NO friendly bishop was captured → that side's queens **cannot take bishop form** → they **cannot use the queen-as-bishop teleport escape** (or queen-as-bishop pinning). Same logic for rook-form (needs a captured friendly rook) and knight-form (needs a captured friendly knight).
- **Worked example — K+RQ+PQ+B+B vs same:** both bishops survive ⇒ queens have NO bishop form ⇒ the RQ and PQ **cannot teleport-escape**; they are stuck as base / rook / knight (all catchable). This makes the **queens the vulnerable pieces** in this composition, not the bishops. (To reach this composition both rooks AND both knights were captured, so rook-form and knight-form ARE available to the queens.)
- **Rule for analysis:** before invoking queen-as-bishop escape, lock-down, or pinning in ANY position, first check the captured-piece history to confirm bishop-form is actually available. Do the same for rook/knight forms.

# Action stalling (queens-only mechanic)

Queens can take infinite actions (transformations, manipulations) on the same square without ever spatial-moving:

- **Transformation** is non-spatial: queen changes form (base ↔ rook ↔ bishop ↔ knight) without leaving her square.
- **Manipulation** is non-spatial for the queen herself (only moves the target enemy piece).
- Neither triggers bishop reactive-capture (which requires the queen's own spatial move).

## Practical implications

- A queen on a hostile bishop's LOS can survive indefinitely via actions.
- This is DEFENSIVE: actions don't make offensive progress.
- For action stalling to actually save the position, the queen's side must lack other offensive resources too (otherwise the opponent makes progress with their other pieces while the queen stalls).

## Limits of action stalling

- Manipulation requires a valid enemy target in the queen's LOS. If no enemy is in LOS or only the enemy king/boulder/base-form-queen is in LOS (Restriction 3), manipulation is unavailable.
- Transformations are unconstrained as long as the queen has captured-piece-types to transform into (which she usually does in late endgame).
- So action stalling is usually robustly available via transformation cycles.

# Extra-piece conversion via manipulation-timing window (KEY FORCING TECHNIQUE)

**Strategic principle**: when one side (A) has an extra piece beyond what's needed to lock down the opponent (B)'s pieces via bishop pins, A can convert the extra piece into a forced win by exploiting **manipulation Restriction 2** to create one-turn windows for offensive moves.

## The technique

Setup: A has K + RQ + B + B vs B has RQ + B (case 3b — A has 2 bishops, B has 1 bishop and 1 queen; A's extra piece is one bishop relative to B).

1. **Pin lock-down phase**: A maneuvers its 2 bishops so that each pins one of B's 2 pieces (B's RQ and B's bishop, both on A's bishops' diagonals). B's pieces can't spatial-move without being reactive-captured.

2. **R2-window phase**: A keeps its bishops "fresh" (recently moved) so B cannot manipulate them:
   - **Manipulation Restriction 2** (`RULEBOOK_v2.md` line 197): "The queen may not move a piece that moved on the immediately preceding turn."
   - A moves a bishop each A turn → on B's next turn, that bishop is unmanipulable.
   - With 2 bishops alternating, A can keep at least one bishop unmanipulable per B turn. B's manipulation options are constrained.

3. **B's stalling cost**: when B cannot manipulate A's pieces effectively, B is forced to spend turns on transformations (non-spatial actions that don't trigger reactive capture but also don't make offensive progress). Each transformation turn for B is a wasted turn defensively.

4. **A's extra-piece exploitation**: while B stalls via transformations, A's "extra piece" (the royal queen, which A can transform into a knight or rook) gets free turns to maneuver and threaten. A's RQ-as-knight (radius-2 active attacker) or RQ-as-rook (L-step active attacker) can chase B's pinned pieces and eventually standard-capture them.

5. **Why the pinned pieces are vulnerable to standard capture**: a pinned piece is only protected from MOVING (its own spatial move triggers reactive capture by the pinning bishop). It is NOT protected from being captured BY an enemy piece. When A's RQ-as-knight standard-captures a pinned B piece, the pinned piece is removed from the board; no reactive capture trigger fires (the pinned piece didn't move — it was captured in place).

6. **Position simplification**: each capture A makes simplifies the position. Once the position reaches ≤6 non-king pieces AND the cancel-queens + 1-to-3 balance check passes, the tiny endgame rule activates, bounding remaining turns. (NOTE: the ≤4 total catch-all was REMOVED in the 2026-05-18 redesign — see commit 1c7cdec. The rule is now solely "no pawns AND ≤6 non-king AND cancel-queens balance." Earlier versions of this note referenced a ≤4 catch-all that no longer exists.)

## Why this works (mechanics breakdown)

- **Pinning is active threat with low capture cost**: A's bishops apply pressure via LOS without committing to capture; they only fire if the pinned piece moves.
- **R2 window is asymmetric**: B can manipulate A's pieces only if (a) B's RQ is in base form and (b) the target piece didn't move on the previous A turn. A can systematically deny (b) by moving each piece A wants to protect on alternating turns.
- **Action stalling is purely defensive**: B's transformations (the only actions B can take when pieces are pinned) make no offensive progress. B loses tempo every transformation turn.
- **A's extra piece has free turns**: while B stalls, A uses every other A turn (or even most turns) to maneuver the extra piece toward a forcing capture.
- **Standard capture bypasses pins**: A pinned piece is uncapturable only by its own movement; any enemy piece can standard-capture it.

## Generalization

This technique applies whenever:
- A has 2+ pieces capable of pinning (bishops, queens-as-bishop).
- A has at least 1 additional active piece (queen or transformable queen) beyond the pinning pieces.
- B's defenders cannot break all of A's pins simultaneously.
- A can maintain R2-protection on its pinning pieces by moving them on alternating turns.

This generalizes the conversion of small material advantages (even +1 bishop) into forced wins. **The 'extra piece' need not be powerful by itself — bishops alone, properly coordinated with R2-window timing, can convert.**

## Implication for pressure-testing

Before classifying a position as stall-prone, **explicitly check for the extra-piece-conversion technique**:

1. Does side A (the side with more material) have ≥2 pieces that can pin?
2. Does A have at least 1 additional piece that can move freely while the pins hold?
3. Can A maintain R2-protection on its pinning pieces?
4. Can A's extra piece reach a standard-capture-attack on a pinned B piece?

If all 4 are yes, the position is **likely forceable for A**, even if A's material edge seems "weak" (e.g., only +1 bishop).

# King-pin tactic (FORCING TECHNIQUE)

**Strategic principle**: kings have NO actions (per `RULEBOOK_v2.md` lines 153-172, kings only spatial-move). This means a king CANNOT stall via actions when its turn comes — it MUST take a spatial move. If the king is on an enemy bishop's diagonal LOS, that spatial move triggers reactive capture.

## The technique

1. W (the +material side) positions a bishop with diagonal LOS to K_B's current square. K_B is pinned.
2. On B's turn, B can choose any legal turn:
   - Move K_B → triggers reactive capture by W's bishop. K_B captured.
   - Move a different B piece (if any). K_B stays put. Pin persists.
   - Take an action with a B queen (transformation/manipulation), if B has a queen. K_B stays put.
3. If B has no other pieces (or all other pieces are also constrained), B is forced to move K_B → K_B captured.
4. If B has other pieces, B can delay. W can use this time to constrain or capture B's other pieces, eventually forcing the king-pin to fire.

## Why this works

- Kings cannot take non-spatial actions. So a king on a bishop's LOS has no defensive option besides moving (and getting captured) or being defended by another piece (which requires another piece to move).
- Bishops can teleport globally, so W can establish the king-pin from any starting position by teleporting the bishop to a diagonal containing K_B.
- The teleport-safety rule allows W's bishop to land on B's bishop's LOS (enemy bishops are excluded from the safety check). So B's bishops don't directly stop W from establishing the pin.

## When this fails

- If B has multiple non-king pieces that can be moved indefinitely, B can keep K_B stationary forever (under no-repetition stall test). W must first constrain or capture B's non-king pieces to force K_B's move.
- If K_B can be defended by an adjacent friendly piece (so that capturing K_B exposes W's bishop to immediate capture by that defender). But bishops teleport to the destination — they can teleport to a safe square even if K_B was defended. Actually the bishop's reactive capture teleports specifically to K_B's destination — if that destination is attacked by a defender, the bishop might still capture but get captured back. Net trade: W loses bishop, gains K_B. If K_B is one of B's two royals (the other being RQ), the trade is favorable for W.

## Implication for pressure-testing

When analyzing a position where the smaller side has 2 kings worth of royals (K + RQ both alive) and the larger side has a bishop:

- Always check whether the king-pin tactic forces a capture.
- The king-pin tactic + queen-lock-down + extra-piece-conversion are the three primary forcing techniques in this variant's endgames.

## Example position where king-pin is decisive

**K+RQ+B vs K+RQ (5 pieces, both kings alive, W has +1 bishop):**

W's strategy:
1. W's bishop teleports to a square with diagonal LOS to K_B's current square.
2. K_B is pinned. K_B's owner has only K and RQ. RQ can transform/manipulate (non-spatial), so B can stall K_B's required move by moving RQ instead. But then RQ becomes the active piece, and W can pivot to pin RQ.
3. Eventually B runs out of non-K-moving options (RQ can transform indefinitely, but transformations don't make B's offensive progress; meanwhile W's K walks toward K_B).
4. When W's K reaches K_B's adjacency, W's K can capture K_B directly (or threaten to). B is forced to make a move that either captures W's K (mutual exchange that benefits W) or moves K_B into the bishop's pin (captured).

Forceable for W. Cancel-queens correctly does NOT activate this position (no over-coverage).

# Manipulation-of-A's-non-Q-piece forcing tactic (small-piece-count converter)

**Strategic principle**: in small piece-count endgames where one side (A) has K + non-queen piece (R, B, or N) and the other side (B) has RQ + (anything), B can use manipulation to capture A's non-Q piece, simplifying the position to K vs (B's stuff) where B forces K-capture.

## The technique

Setup: A = K + non-queen piece X. B = RQ + (anything).

1. **Place B's other piece (or B's bishop's LOS) to threaten X's destination.** B's other piece (R, N) at L-step or radius-2 reach of where A's X will be manipulated. Or B's bishop with LOS to A's X's current square.

2. **Wait for R2 window.** B can manipulate A's X only when A's X did NOT move on the immediately preceding turn. If A moved K on the previous A turn, A's X is "stale" and B can manipulate.

3. **Manipulate A's X to a vulnerable destination.** B's RQ in base form (since R3 doesn't protect A's X — X is not king, boulder, or base-form queen) manipulates X to a square where B's other piece can standard-capture it next turn. Restriction 1 freezes X on A's next turn (X can't escape).

4. **Force A into bad choices.** A's options on A's next turn:
   - Move K (only option since X is frozen). K's move doesn't save X.
   - Result: B captures X next B turn.

5. **Captured X simplifies position.** A now has only K vs B's RQ + non-Q (or B's RQ if B had RQ + B and B chose to advance with bishop only). The simplified position activates the ≤4 catch-all clause (or is forceable directly via K-chase).

## Why A cannot defend X

A's K is unmanipulable (R3). A's X is the only non-K piece A has. When X is manipulated and frozen, A has no other defenders.

A could try to keep X moving every turn (so it's never "stale"), denying B the manipulation window. But then K_A is stationary — and A's K is the only royal for A. With K_A stationary and B's pieces threatening it (B's RQ-as-knight at radius-2 etc.), K_A is captured by direct attack.

A's tradeoff:
- Move X every A turn → K_A stationary → B captures K_A via direct knight-chase.
- Move K_A every A turn → X stale → B manipulates X for capture.

Either path: A loses a critical piece.

## Why this is a real forcing technique, not just hand-waving

The technique is verified by the manipulation rule mechanics:
- Manipulation = action (no spatial move for the manipulating queen) — doesn't trigger reactive captures (rulebook lines 188-203).
- Restriction 1: target frozen next turn (rulebook line 195).
- Restriction 2: only blocks manipulation of just-moved pieces (line 197).
- Restriction 3: protects only king, boulder, base-form queen (line 199) — doesn't protect A's non-Q piece.

The combination converts material flexibility (B's RQ as manipulator) into forced piece capture in small piece counts.

## Implication for tiny endgame rule analysis

Previously I classified positions like RQ vs RQ+B (3 pieces) and K+R vs RQ (3 pieces) as stall-prone because I missed this technique. Both are actually forceable for the +material side using manipulation + coordinated attack.

The genuine stall-prone candidates at ≤4 pieces are restricted to **K+non-Q vs RQ+non-Q (4 pieces, both sides have a defender)**, where A's non-Q is symmetric to B's non-Q (both can attack/defend) and the manipulation technique alone may not suffice. Even there, B's transformation flexibility + manipulation tactics may still force a win in many sub-cases.

# Manipulation does NOT trigger a friendly bishop's reactive capture (CORRECTED 2026-05-19)

**PREVIOUS CLAIM WAS WRONG.** I previously asserted that A's queen could manipulate an enemy piece off A's bishop's LOS to force A's bishop to reactive-capture it. **This does not work because of reactive-capture timing.**

The bishop reactive-capture rule (`RULEBOOK_v2.md` lines 254-264): a piece that begins its move on the bishop's diagonal LOS and moves can be captured by the bishop **on the bishop's IMMEDIATE next turn** only.

Timing breakdown when A manipulates an enemy piece P off A's bishop's LOS:
- Turn N (A's turn): A's queen manipulates P. P moves from A's bishop's LOS.
- Turn N+1 (B's turn): B's turn intervenes. A's bishop cannot act (not A's turn).
- Turn N+2 (A's turn): A's bishop's actual next turn — but the "immediate next turn" window was N+1 (the turn right after the move). That window has passed. **A's bishop CANNOT reactive-capture.**

The intervening opponent turn always breaks the chain when the manipulation is by the bishop's own owner. So manipulation never enables a friendly bishop to reactive-capture an enemy piece. Retracted.

Two single-manipulation cases, both of which FAIL to produce a valid bishop reactive capture:
1. **Bishop-owner D manipulates enemy C's piece off D's LOS** (on D's turn N): timing fails — D's bishop's window is turn N+1 (C's turn), which D can't use; by D's own next turn N+2 the window has passed. No capture.
2. **Opponent C manipulates D's own piece off D's LOS** (on C's turn N): timing works (D's bishop's window is D's turn N+1), BUT D's bishop capturing D's own piece would be a SAME-COLOR capture, which is FORBIDDEN (only the king captures same-color pieces). No capture.

So NO single manipulation produces a valid bishop reactive capture.

**General lesson:** any reactive capture (bishop OR knight jump-capture) requires the triggering move to occur on the turn IMMEDIATELY BEFORE the capturing piece acts. A manipulation by the capturing piece's OWN side happens on that side's turn, so an opponent turn always intervenes before that side can act — breaking the timing.

# Double-manipulation bishop nuance — CORRECTED 2026-05-19

The valid scenario (parallel to the knight's documented double-manip jump-capture nuance, rulebook line 311) is a DOUBLE manipulation, NOT a single one:

- **Turn N (White):** White's queen manipulates BLACK's piece (e.g., a bishop) OFF White's bishop's diagonal LOS. (Screenshot example: White manipulates Black's bishop b6 → d6, off White's d4-bishop's diagonal.)
- **Turn N+1 (Black):** Black's queen manipulates WHITE's bishop to reactive-capture Black's piece (which moved on turn N, immediately preceding).
- **The capturing piece is White's bishop** (the opponent of the current player Black). **The captured piece is Black's own piece.** Different colors → NOT a same-color capture → allowed in principle.
- Eligibility holds because the captured piece moved on the immediately preceding turn (White's manipulation on turn N), and the reactive capture is triggered on turn N+1 (the immediate next turn).
- This is a "self-capture" only in the PLAYER'S-TURN sense (Black removes Black's own piece on Black's turn); the capturing piece is enemy-colored.

**Why a player would essentially never WANT this:** it captures their own piece. So the option is offered but virtually always declined. It matters only for rule consistency.

**Current code does NOT allow it** (verified by user: in the screenshot position, after White manipulates Black's bishop b6→d6, Black cannot manipulate White's d4-bishop to capture on d6). This is a genuine gap parallel to the knight nuance. Status: pending decision on whether to fix (low priority; rare; needs rulebook clarification + code + tests).

# "Self-capture" terminology (clarified 2026-05-19) — IMPORTANT

There are TWO distinct meanings of "self-capture." We use the **second (player's-turn) definition** to be inclusive:

1. **Same-color capture (narrow):** the capturing PIECE and the captured piece are the same color. This ONLY happens when the **king** captures its own friendly piece. No other piece can ever capture a piece of its own color.

2. **Self-capture (player's-turn / adopted definition):** the captured piece is the same color as the player whose turn it is, REGARDLESS of the capturing piece's color. This includes:
   - King capturing its own piece (also a same-color capture).
   - Queen manipulating an ENEMY piece (king/boulder/manipulated-enemy) to capture one of the manipulating player's OWN friendly pieces (the double-manip bishop/knight nuances). Here the capturing piece is enemy-colored, but the captured piece is friendly to the player whose turn it is.

**Key invariant:** the ONLY time a piece captures another piece of its own color is the king capturing its own piece. Everything else (manipulation-induced friendly captures) involves an enemy-colored capturing piece removing the current player's own piece.

# Lessons learned (don't make these mistakes again)

- ❌ Treating bishops as passive defenders. They are ACTIVE pieces with global teleport movement and pinning power.
- ❌ Assuming "extra piece corners opponent" without analyzing what the opponent's defensive resources are.
- ❌ Ignoring queen transformation as a defensive resource (especially queen-as-bishop teleport escape).
- ❌ Not counting attack coverage when analyzing teleport-escape positions.
- ❌ Not considering mutual bishop pin as a queen-lock-down mechanism.
- ❌ Confusing "AI training data drew" with "optimal play stalls."
- ❌ Asserting "K+Q vs K+B+2-attackers forced for B" without verifying under queen lock-down + queen-as-bishop escape dynamics.
- ❌ Claiming manipulation can force a spatial move that chains into a FRIENDLY bishop's reactive capture. WRONG — timing fails (the bishop owner's manipulation is on its own turn, so an opponent turn intervenes before the bishop can act, expiring the "immediate next turn" window). Manipulation IS a positional-disruption tool (relocates + freezes the target for one turn) but does NOT enable a friendly reactive capture. (Corrected 2026-05-19.)
- ❌ Defaulting to "stall-prone" when the position has an extra piece + pinning resources, WITHOUT first looking for extra-piece-conversion tactics (pin + R2-window + queen transformation).
- ❌ Treating "+1 bishop" as too weak to convert. With R2-window protection, even +1 bishop is convertible because A's queen-as-knight or queen-as-rook gets free attacking turns while B stalls via transformations.
- ❌ Assuming pinned pieces are safe from capture. Pins only protect against the pinned piece's OWN spatial moves; standard captures by enemy pieces still apply.

# Date created

2026-05-14, after the user pointed out these strategic dynamics I had been overlooking in my pressure-test analysis. The user specifically corrected:
- Bishops are active pieces (global teleport + pin power), not passive.
- Queens can lock down each other via mutual bishop pin.
- Queens can escape indefinitely via bishop-form teleport when opponent's coverage < 64.
- K+Q vs K+R+R+N is drift-prone (not forceable for the K+R+R+N side).
- Action stalling lets queens avoid reactive capture without spatial-moving.

# Bishop double-manip code bug — ROOT CAUSE + FIX APPROACH (2026-05-20)

**Bug:** code blocks the double-manip bishop reactive-capture (White manip Black's bishop b6→d6 off White's d4-bishop LOS on turn N; Black manip White's d4-bishop to capture d6 on turn N+1 → currently NOT offered).

**Root cause:** `src/main.py` (and engine.py) call `board.update_assassin_squares(game.next_player)` AFTER each move, where `next_player` = the player who JUST moved (next_turn() switches afterward). When the moving player (White) manipulates an enemy piece OFF the moving player's OWN bishop's LOS, this recomputes White's bishop `assassin_squares` against the post-move board — the vacated square (b6) no longer has an enemy, so it's DROPPED. Then on Black's turn, the assassin-capture check in `bishop_moves` (around line 2210: `if last_move_initial in piece.assassin_squares`) fails because b6 was dropped.

Standard reactive capture works because: when Black moves its OWN bishop, `update_assassin_squares(Black)` runs (the mover), leaving White's `assassin_squares` (the would-be captor) untouched and retaining b6.

**Fix approaches considered:**
- (A) After a MANIPULATION, don't recompute the manipulator's own assassin_squares for the vacated square (preserve it). Surgical but special-cases manipulation.
- (B) In `bishop_moves` assassin check, fall back to a GEOMETRIC check: is `last_move_initial` on the bishop's current clear diagonal LOS? Equivalent to the cache in the normal case, fixes the manip case, but changes core logic for all bishops (risk: LOS path could differ between the trigger move and capture; the cache intentionally snapshots LOS at trigger time).
- (C) Update assassin squares for BOTH players after a manipulation (or specifically preserve the captor's snapshot).

Leaning (A) or a careful (B). Whichever: gate the capture so it ONLY applies when target moved on the immediately preceding turn (last_move_turn_number == turn_number - 1, mirroring the knight) to avoid stale captures, AND it's a "self-capture" in the player's-turn sense (capturing piece enemy-colored, captured piece is current player's own) — which is fine, NOT a same-color capture.

**Status as of 2026-05-20:** rulebook clarification + failing test being added this session. Code fix may or may not land before context reset — if a failing test `test_bishop_double_manip_reactive_capture` exists and the suite is otherwise green, the fix is the remaining work.

# Boulder rule nuance: capture vs the "no-return" memory rule (OPEN, 2026-05-20)

Rulebook (Boulder): "Boulder Memory — the boulder may not move to the immediate last square it occupied." Also: boulder captures PAWNS ONLY; moves like a king (after first move); cooldown = both players take a turn before it can move again.

**Open question (user, 2026-05-20):** if a PAWN sits on the boulder's immediate-previous square, should the boulder be allowed to RETURN there to CAPTURE the pawn (vs. the no-return rule forbidding it)?

**My lean: ALLOW the capture-return.** Rationale: the no-return rule's intent is to prevent pointless oscillation (infinite back-and-forth shuffling with no progress). A CAPTURE is irreversible progress (removes a pawn, changes material) — not pointless oscillation — so it doesn't create a degenerate loop and shouldn't be forbidden by a rule aimed at loop-prevention. Strict reading of the current text forbids it (a capture is still a "move to that square"), so the rulebook is AMBIGUOUS and needs clarification.

**Scope note:** only matters in positions WITH pawns; irrelevant to the pawnless tiny-endgame analysis. STATUS: pending user decision; if "allow," update RULEBOOK_v2.md (carve-out: no-return rule does not apply to a capturing move) + check/fix code + add tests. Have NOT checked current code behavior yet.

# User clarifications: no-check, optimal-play declining, manipulation pin-breaking (2026-05-20) — AUTHORITATIVE

These three clarifications were given by the user to correct three INCORRECT arguments I made while wrongly attempting to reverse the "K+RQ+PQ+B+B vs same likely rule-sufficient" lean to "stall-prone." Treat the clarifications below as authoritative; the analysis they corrected was wrong and is not recorded. See [[feedback-analysis-rigor]].

## No-check is ONLY a legality difference — NOT a strategic shield
- The win condition (capture BOTH enemy royals) does NOT mean "one capture never wins." You capture one royal, then the other; the game ends on the **second** capture. Capturing the two royals one at a time still wins — **even from a symmetric position.**
- The absence of check is **purely a legality difference**: you are not FORCED to move a royal out of danger. There is **no significant strategic difference** — royals are still in danger when attacked, and saving them is almost always favorable (optimal).
- Consequence: any "mirror/copycat is un-loseable because one capture never wins" argument is **FALSE**. First-mover tempo can still convert to capturing both royals one at a time, exactly as a check-race converts in standard chess.

## Optimal play CANNOT simply "decline" a threat
- Optimal players **never** make a move that brings them into a worse position than their current one.
- Losing a non-royal piece without capturing back is almost never optimal. A defender facing a fork **cannot** just decline/ignore it and accept the loss — that worsens their position. They MUST address the threat (move, defend, block) or capture.
- Consequence: forks and threats **do** carry forcing power. "The defender can simply decline the fork" is **WRONG**.

## Manipulation can BREAK a pin
- A pinned queen can (be in / transform to) **base form** and **manipulate the pinning bishop away**: the pinning bishop sits on the queen's diagonal LOS, and manipulation Restriction 3 does not protect bishops. Manipulation is a non-spatial action, so it does NOT trigger the bishop's reactive capture. Pin broken.
- The bishop's only counter is to have **moved on the immediately preceding turn** (manipulation Restriction 2 forbids manipulating a just-moved piece). So to stay manipulation-immune the bishop must move **every** turn — which costs tempo, and during those turns other pieces can be manipulated / other dynamics arise.
- Consequence: a bishop pin is **NOT a stable trap** against a queen. Any pin/tempo "race" analysis that ignores manipulation pin-breaking is incomplete and unreliable.
