# Key Rule Differences From Standard Chess

This document is a fast-lookup reference. **`RULEBOOK_v2.md` is the
authoritative source of rules** — this file just enumerates the
differences from standard chess that I (Claude) keep getting wrong by
defaulting to pretrained chess knowledge. Read it alongside the full
rulebook on every rule-related task.

If a rule is the same as standard chess, it's not listed here. If
this document and `RULEBOOK_v2.md` ever disagree, `RULEBOOK_v2.md`
wins; update this file to match.

---

## Per-piece differences

### Pawn

| Aspect | Standard chess | This variant |
|---|---|---|
| Forward movement | 1 square (2 from start) | 1 square only |
| Sideways movement | Not allowed | **Allowed (1 square left or right)** |
| Backward movement | Not allowed | Not allowed |
| Capture | Diagonal forward only | Forward + diagonal forward-left + forward-right |
| En passant | Yes | (Currently disabled in code; commented out — see `Board.move`) |
| Promotion | To Q, R, B, or N | To a **non-royal queen** in any form (base or transformed rook/bishop/knight). Transformed forms require the corresponding non-queen friendly piece type to have been captured earlier. |

### King

| Aspect | Standard chess | This variant |
|---|---|---|
| Movement | 1 square any direction | Same |
| Capture | Enemy pieces only | **Also captures friendly pieces AND the boulder** (unique). Only the king can capture friendlies or the boulder. |
| Capture vs. invulnerability | n/a | King's special capture does NOT override invulnerability — invulnerable pieces are uncapturable by any piece, including the king. |
| Check / checkmate | Yes | **No check/checkmate concept.** Game ends when both royals are captured. |
| Castling | Yes | Not implemented as a special move in v2 (see code; vestigial). |

**"Self-capture" terminology (two meanings — use the player's-turn definition):**
1. **Same-color capture (narrow):** the capturing PIECE and captured piece are the same color. **ONLY the king does this** (capturing its own friendly piece). No other piece can ever capture a piece of its own color.
2. **Self-capture (player's-turn / adopted definition):** the captured piece is the same color as the player whose turn it is, regardless of the capturing piece's color. Includes (a) king capturing its own piece, and (b) a queen manipulating an ENEMY piece to capture one of the manipulating player's OWN friendly pieces (the double-manipulation knight/bishop reactive-capture nuances — here the capturing piece is enemy-colored but the captured piece is friendly to the current player).

**Invariant:** the only same-color capture is the king capturing its own piece. All manipulation-induced friendly captures use an enemy-colored capturing piece.

### Queen (royal or promoted)

| Aspect | Standard chess | This variant |
|---|---|---|
| Base-form movement | Unlimited rank/file/diagonal | **1 square king-like** (NOT unlimited). |
| Base-form capture | Anywhere on rank/file/diagonal | Adjacent enemy only (1-square king-like). |
| Actions | None | **Manipulation** (move an enemy piece in queen's LOS) and **Transformation** (become rook/bishop/knight if that type has been captured). |
| Royal queen | n/a | Captured = lose. |
| Promoted queen | n/a | Not royal — doesn't count for win condition. |

**Manipulation restrictions:**
1. The manipulated piece is **frozen** — cannot make a spatial move on its immediate next turn. (Actions like transformation are still allowed.)
2. The queen may not manipulate a piece that made a **spatial move on the immediately preceding turn**. Non-spatial actions on the preceding turn (e.g., transformations) DO NOT count and do not trigger this restriction.
3. The queen may not manipulate the enemy king, the boulder, or any enemy **base-form** queen (royal or promoted). Transformed queens CAN be manipulated.
4. Manipulation only works in base form (the queen must be in base form to perform it).

**Transformation:**
- Queen → rook / bishop / knight (only if that type has been captured friendly).
- **Availability depends on captures:** a form is available only if a friendly piece of that type was **captured earlier**. So if both bishops are still on the board, the queens **cannot** take bishop form (hence no queen-as-bishop teleport escape); likewise rook/knight forms require a friendly rook/knight to have been captured. (E.g. in K+RQ+PQ+B+B both bishops survive → queens have no bishop form → the queens cannot teleport-escape.)
- Queen can return to base form on a later turn.
- Transformation is a non-spatial action — doesn't change position, doesn't update `last_move`.
- A queen-transformed-to-knight is a `Knight` Python instance with `is_transformed=True`. NOT a `Queen` instance. Important for `isinstance` checks.

### Rook

| Aspect | Standard chess | This variant |
|---|---|---|
| Movement | Unlimited rank/file | **Two-step pattern**: 1 square orthogonal, then turn 90° and move any number of squares (including zero) perpendicular. |
| Capture | Anywhere along path | Either step. |
| Castling | Yes | Not in v2 (vestigial). |

The rook's perpendicular sweep is blocked by ANY piece, including invulnerable enemies (cannot capture them, cannot pass through).

### Bishop

| Aspect | Standard chess | This variant |
|---|---|---|
| Movement | Unlimited diagonal | **Teleportation** to any square that isn't reachable or captureable by an enemy piece (plus a few specific exclusions: enemy bishops, queens-transformed-as-bishops, boulder). |
| Capture | Anywhere along diagonal | **Reactive ("assassin") only**: if a piece begins its move on the bishop's diagonal LOS and then moves, the bishop may capture it by teleporting to its destination on the bishop's IMMEDIATE next turn. |
| Direct attack | Yes | **NO — the bishop has no direct capture mechanic.** It can only capture pieces that have just moved. A static piece on the bishop's diagonal is NOT capturable. |

**Bishop is an ACTIVE piece, not passive:**

Common misconception: "bishops are weak because they only capture reactively along diagonals." This is wrong. Bishops are powerful active pieces with two distinct strengths:

1. **Movement is GLOBAL TELEPORT, not diagonal-only.** Bishops teleport to ANY safe square on the board. "Safe" = not attacked by enemy non-bishop pieces (enemy bishops/queens-as-bishop/boulder are excluded from the safety check). This gives bishops maximum mobility in the variant.

2. **Reactive capture is a powerful PIN.** A bishop on an enemy's diagonal effectively pins that enemy — its next spatial move triggers capture.

**Bishop pin mechanics:**
- A bishop on an enemy piece's diagonal "pins" the enemy: any spatial move from that diagonal triggers reactive capture on the bishop's next turn.
- The pin does NOT directly capture the pinned piece if it stays still. But:
  - Regular pieces have no actions, so they MUST spatial-move on their turn (or face no-legal-move loss). So pinning a regular bishop, rook, knight, or king with another bishop forces capture.
  - Queens have actions (transformation, manipulation) so they can stall via action-only turns. Pinned queens-as-bishop can survive but cannot make offensive progress.
- **Bishops actively threaten by teleporting onto enemy diagonals.** Position pressure is a primary tool, not just incidental.
- Manipulation-induced movements count as "the piece moved" for reactive-capture eligibility, BUT the bishop captures only on its IMMEDIATE next turn — so the timing matters. No SINGLE manipulation produces a valid bishop reactive capture:
  - A manipulation by the bishop's OWN side (moving an enemy piece off the LOS) happens on that side's turn → an opponent turn intervenes → "immediate next turn" window expires → no capture. (Common misconception: you CANNOT manipulate an enemy piece off your own bishop's LOS to force your bishop to capture it.)
  - A manipulation by the OPPONENT moving the bishop-owner's OWN piece off the LOS has valid timing, but the bishop capturing its own piece would be a forbidden SAME-COLOR capture → no capture.
  - **The valid case is a DOUBLE manipulation** (parallels the knight double-manip nuance, rulebook line 311): White manipulates Black's piece off White's bishop's LOS (turn N); then Black manipulates White's bishop to reactive-capture that Black piece (turn N+1). The capturing piece is White's bishop (enemy of the current player Black); the captured piece is Black's own — different colors, NOT same-color, allowed in principle. It's a "self-capture" only in the player's-turn sense (Black removes its own piece). Virtually always declined; matters only for rule consistency. **Current code does NOT support this — a known gap.**
- Knight jumps are spatial moves and trigger reactive capture (subject to knight invulnerability rules).

**Mutual bishop pin = lock-down:**
- Two bishops on each other's diagonal mutually pin. First to spatial-move gets captured by the other.
- For regular bishops: this is a complete lock-down (no actions to stall with).
- For queens-as-bishop: incomplete lock-down (queens can stall via actions, but cannot make offensive progress while pinned).

**Strategic role of bishops in endgames:**
- Bishops have ~13 squares of diagonal LOS from a center square.
- Multiple bishops together can pin many key squares simultaneously.
- A bishop's teleport gives it the mobility to apply pressure where needed in 1 turn.
- Bishops constrain enemy piece positioning: enemies must avoid starting their turn on a bishop's LOS (or face capture).

**Queen lock-down strategy (key strategic insight):**
When both sides have queens AND one side has extra non-queen material, the side with extra material can WIN by:
1. Both queens transform to bishop form.
2. Position them on each other's diagonals (mutual pin).
3. Neither queen can spatial-move without being captured.
4. Queens are effectively "canceled out."
5. Extra non-queen material decides the position.

This is the strategic basis for the cancel-queens framing in the proposed tiny endgame rule variant.

**Queen-as-bishop escape (key defensive insight):**
A lone queen can defend indefinitely by transforming to bishop and teleporting:
- Queen-as-bishop teleports to safe squares globally.
- Cannot be captured as long as at least 1 safe square exists.
- Trapping requires the attacking side to attack ALL 64 squares simultaneously — typically infeasible with 2-3 pieces.
- Example: K+Q vs K+R+R+N — K+R+R+N attack at most 63 of 64 squares; queen-as-bishop always has at least 1 safe teleport destination; position is drift-prone for the K+R+R+N side.

### Knight

| Aspect | Standard chess | This variant |
|---|---|---|
| Movement | L-shape only (8 squares) | **Radius-2 pattern (16 squares)**: 2-orthogonal, 2-diagonal, or L-shape (2+1). |
| Jumping | Yes (over any piece) | Same. |
| Standard capture | Any enemy at L-shape destination | Any enemy at radius-2 destination. |
| Jumped square | n/a (no concept) | Every knight move passes over **one specific square** (the "jumped square"). For 2-orthogonal: 1 square in that direction. For 2-diagonal: 1 square diagonally from origin. For L-shape: 1 square along the 2-square direction. |
| Jump capture | n/a | If an enemy piece moved on the immediately preceding turn into a square the knight can jump over, the knight may capture it by jumping over it on the knight's next turn. Only the jumped piece is captured — NOT adjacent pieces to landing. |
| Post-jump status | n/a | **Invulnerability** for 1 opponent turn after a non-capture jump OVER A FRIENDLY PIECE OR THE BOULDER (not over an enemy), IF the landing square is adjacent (chebyshev 1) to at least one enemy piece OTHER than the jumped piece. |

**Knight invulnerability detailed:**
- Trigger (all required): non-capture spatial move + jumps over a **friendly piece or the boulder** (NOT an enemy) + lands adjacent to a non-jumped enemy.
- The jumped piece must be **friendly or the boulder**. Jumping over an enemy never grants invulnerability — this closes the "perpetual invuln by chain-leaping through enemy territory" loophole.
- The adjacent enemy CAN be invulnerable itself (engagement check, not capturability).
- **Manipulated knights do NOT get functional invulnerability.** The flag is set, but cleared at the start of the manipulated player's next own turn before they can benefit from it.
- Capture moves (standard at landing OR jump-capture of jumped piece) do NOT grant invulnerability.
- Declining an offered jump-capture **never** grants invulnerability under the friendly/boulder-only rule — the jumped piece in a jump-capture offer is always an enemy.
- Invulnerability is universal protection: no piece (including kings) can capture an invulnerable piece during its invulnerability turn.

### Boulder (unique to this variant)

A neutral piece, not present in standard chess.

- Starts on the central 4-square intersection (between d4/d5/e4/e5).
- Represented by two stacked markers.
- Either player can move it on their turn.
- **First move**: must go to one of d4/e4/d5/e5.
- **White cannot move the boulder on turn 1.**
- Later movement: like a king (1 square any direction).
- Captures: pawns only.
- Captured by: kings only.
- Cooldown: both players must take one turn before the boulder can move again.
- Memory: cannot return to its immediately previous square (can return later).
- On the central intersection: blocks diagonals only, not ranks/files.
- For most purposes, treated as friendly by both sides (e.g., `has_team_piece` returns True regardless of color).

---

## Mechanic-level differences

### State / turn structure

- A turn is **either a move or an action** (not both). Moves are spatial; actions are not.
- Transformation is an action.
- Manipulation is an action.
- All other piece movements are moves.

### Repetition rule

- A board state cannot occur 3 times during the game.
- **State hash includes**: piece positions, boulder state (position + cooldown + no-return last-square memory), queen markers (is_royal / is_transformed / current form), whose turn, and currently-invulnerable pieces.
- **State hash does NOT include**: last-move history. Repetition is a purely positional rule.
- If all legal turns produce a 3rd repetition, the player loses.

### Tiny Endgame Rule

The active rulebook version (in `RULEBOOK_v2.md`):
- Applies when no pawns AND (≤4 pieces OR ≤6 pieces with both sides ≥2 non-king AND diff ≤1).
- Uses a "distance count" mechanism (Manhattan distance between closest opposing royals; each value 1–14 has a count cap of 3).
- Non-capture move that would push the resulting royal distance count over 3 is illegal.
- If all legal turns would do so, player loses.

**Current adopted form (2026-05-26):**
- Activation: no pawns AND **≤6 non-king** pieces (boulder excluded, kings ignored) AND cancel-queens + **1-to-2** valuation balances.
- Balance check: cancel queens (q = min(Q_W, Q_B)); r = |Q_W − Q_B|; check `r ≤ N_L − N_M ≤ 2r` (for r≥1) or `N_M = N_L` (for r=0), where N is non-queen non-king count.

The 1-to-2 cap (vs the earlier 1-to-3) reflects the analysis that all r=1 surplus=3 positions (K+Q vs K + 3-non-queens) are forceable for the +material side under optimal play, so they don't need rule activation.

**Important framing:** Tiny endgame **NEVER causes a draw**. It's a "ticking time bomb" — when active, the game must resolve in finite turns with a winner. The player who runs out of legal moves first loses. The rule's PURPOSE is to prevent infinite drift.

**Design-goal one-liner for tiny endgame proposals:** under-coverage is unacceptable (drift-prone position → potential draw → rule failure); over-coverage of forced positions is acceptable (winner still wins, just faster); simpler rules preferred when coverage is equivalent. When in doubt, err toward activating. Optimality is self-referential — "optimal play" assumes both sides know all rules including this one.

### No Legal Moves Loss

- If a player has no legal turn (no move and no action) at the start of their turn, they lose.
- A "legal turn" **includes moving the boulder** (when the boulder is actually movable — not on cooldown, with a destination satisfying first-move/no-return rules). A player loses only when there is no piece move, no action, AND no legal boulder move. Implemented in `Board.has_legal_moves` (it checks boulder moves).
- Can arise from: manipulation freeze locking a piece, repetition exhausting all legal moves, tiny endgame distance-count exhausting options.

### Win conditions

- **Capture both royals** (king AND royal queen) of the opponent.
- Order doesn't matter.
- Promoted queens are NOT royal — they don't count toward victory.
- No check, no checkmate.

### Board setup

- Back rank: **Bishop – Queen – Rook – Knight – Knight – Rook – King – Bishop** (NOT the standard R-N-B-Q-K-B-N-R).
- Setup is **rotationally symmetric**, not mirror-symmetric.
- Pawns on the second rank as usual.

---

## Implementation-level conventions

### Square query helpers

These two methods are easy to confuse. They have specific contracts:

- **`has_enemy_piece(color)`** — BROAD. Returns True for any opposing-colour, non-boulder piece. Does NOT filter invulnerable. Use for engagement / presence / threat / blocker queries — anything where "is there an enemy here?" is the right question.

- **`has_capturable_enemy_piece(color)`** — NARROW. Like `has_enemy_piece` but ALSO returns False if the piece is currently invulnerable. Use for capture-decision queries — "can I capture this piece right now?".

**Rule of thumb**: capture move generation → narrow. Threat / engagement / blocker / presence → broad.

Audit verified (commit `c257a16`, 2026-05-12):
- Capture decisions: `_can_jump_capture`, `rook_moves`, `pawn_moves` diagonal capture, `queen_moves` (via `isempty_or_enemy`), `knight_moves` (via `isempty_or_enemy`), `bishop_moves` reactive capture — all narrow.
- Engagement/threat/presence: `_has_adjacent_enemy_other_than_jumped`, `update_assassin_squares`, `bishop_moves` enemy-threat scan, `queen_moves_enemy` find-friendly-queen, `main.py` manipulation freeze setter — all broad.

### Knight modes

- `Board.KNIGHT_MODE_V2`: current v2 rules (default, active).
- `Board.KNIGHT_MODE_LEGACY`: pre-v2 rules used by `main_v0.py` and `main_v1.py` snapshot mainloops only.

### Engine manipulation modes

- Default: `'freeze'` (matches v2 rulebook).
- `'original'` available for v1 (forbidden-square) semantics.
- Variant modes: `'freeze_invulnerable'`, `'freeze_invulnerable_no_repeat'`, `'freeze_no_repeat'`, `'freeze_invulnerable_cooldown'`, `'exclusion_zone'`.

### Mainloop versions

- `main.py` — active v2 game (queen freeze + v2 knight redesign + flip-board feature).
- `main_v1.py` — frozen snapshot: v2 freeze, LEGACY knight (no invulnerability).
- `main_v0.py` — frozen snapshot: v1 manipulation (forbidden_square), LEGACY knight.

Snapshots are not updated for rule changes, only for cross-cutting UI/mechanical bugs.

### Flip-board feature (main.py only)

- F key toggles a 180° visual flip.
- Pure visual rotation — board state untouched.
- Allowed mid-action (drag, jump-capture pending, menu open).
- `flipped` survives `reset()` (viewing preference, not game state).
- `Game.board_to_screen(r, c)` / `Game.screen_to_board(sr, sc)` are involutions.

---

## Common Misconceptions To Avoid

These are mistakes I (Claude) have made repeatedly. Re-read this list before any rule-related response.

- ❌ **Bishops can directly attack pieces on their diagonal.** No — captures only via reactive mechanic. A static piece on the bishop's diagonal cannot be captured by the bishop.
- ❌ **Queens move freely any number of squares.** No — base form is 1-square king-like. To get long range, the queen must transform to rook/bishop.
- ❌ **Knights move in L-shape only (8 destinations).** No — radius-2 pattern, 16 destinations.
- ❌ **Pawn promotion is always to a base-form queen.** No — promoting player can pick any queen form (base or transformed rook/bishop/knight, with the standard transformation capture-availability constraint).
- ❌ **Invulnerability blocks reactive captures mid-move (interrupting the opponent's turn).** No — reactive captures fire on the bishop's NEXT turn. The opponent's turn is never interrupted; reactive captures are deferred to the bishop's own turn.
- ❌ **Last-move tracking is in the state hash.** No — removed. State hash is positional + invulnerability only.
- ❌ **The "manipulated piece moved on preceding turn" restriction applies even after intervening actions.** No — only SPATIAL moves on the immediately preceding turn count. A transformation in between clears the restriction.
- ❌ **The king's special capture overrides invulnerability.** No — invulnerability is universal protection; even friendly or enemy kings cannot capture invulnerable pieces.
- ❌ **The repetition rule's state includes which piece just moved.** No (after the 2026-05-13 redesign) — only positional + invulnerability.
- ❌ **A manipulated knight that jumps gets invulnerability that protects it on the opponent's turn.** No — manipulated knight invulnerability is cleared at the start of the knight player's own next turn, before any opportunity to use it.
- ❌ **A knight jumping over ANY piece + adjacent enemy at landing grants invulnerability.** No — the jumped piece must be **friendly or the boulder**. Jumping over an enemy never grants invulnerability (closes the perpetual-invuln-via-enemy-territory-leap loophole). This was the rule prior to the refinement but no longer.
- ❌ **`has_capturable_enemy_piece` is the right helper for engagement checks.** No — that filters invulnerable enemies. Use `has_enemy_piece` for presence/engagement/threat/blocker checks.
- ❌ **In a "double-manipulation" scenario (A manipulates B's piece next to A's knight, B manipulates the knight to jump over it), the jump-capture isn't offered.** No — it IS offered per the rulebook. Manipulated movements count as "moved on the immediately preceding turn" for jump-capture eligibility. The decision is by the player whose turn it is (the second manipulator), who would normally decline (since the jumped piece is their own).
- ❌ **Bishops are passive pieces that only capture reactively.** Bishops are ACTIVE pieces. Their movement is GLOBAL TELEPORT (any safe square, not constrained to diagonals). Their reactive capture is a powerful pin: any enemy piece on their diagonal effectively cannot spatial-move. Bishops apply pressure proactively by teleporting onto enemy diagonals.
- ❌ **An extra piece automatically wins under optimal play.** False. Many positions are stall-prone despite material asymmetry. The disadvantaged side can hold via queen-as-bishop teleport escape (when opponent's coverage < 64), queen lock-down (mutual bishop pin cancels queens), action stalling (queens take infinite non-spatial-move turns), or symmetric defensive positioning.
- ❌ **No positions are stall-prone under optimal play.** Trivially false. Any symmetric position (K+R+R vs K+R+R, K+B+B vs K+B+B, etc.) with reasonable non-attacking starting squares is stall-prone under optimal play. Near-symmetric (single piece-type swap) positions are also likely stall-prone.
- ❌ **K+Q vs K+R+R+N is forced for the K+R+R+N side.** It is DRIFT-PRONE. The queen transforms to bishop; K+R+R+N attacks at most 63 of 64 squares; queen-as-bishop has perpetual safe teleport.
- ❌ **Surface-level "extra piece corners opponent" reasoning is valid analysis.** It is not. Real analysis requires enumerating piece capabilities, testing transformation escape strategies, computing attack coverage, and marking uncertainty when forcing sequences cannot be concretely demonstrated.

---

## Recent major design decisions (reference timeline)

Listed by commit / date for quick git-log lookup.

- **2026-05-14** — Operational stall test established (assume repetition rule absent, check for infinite stall under optimal play). Key strategic insights documented: bishop is ACTIVE piece (global teleport + pin power, not passive); queen lock-down via mutual bishop pin; queen-as-bishop escape via teleport when opponent coverage < 64. K+Q vs K+R+R+N corrected from previously-misclassified to drift-prone. Several earlier strategic claims (K+Q vs K+B+2-attackers etc.) flagged as needing re-verification. See `memory/project_tiny_endgame_analysis_methodology.md` and `memory/project_piece_strategic_dynamics.md`.
- **2026-05-16** — Cancel-queens proposal refined: threshold changes from ≤6 total to ≤6 non-king pieces (catch-all stays ≤4 total). The non-king-based threshold adds coverage of symmetric/near-symmetric 7–8-piece positions with extra kings (trivially stall-prone) without any over-coverage cost (balance check still filters out asymmetric forceable cases). The king-pin tactic and extra-piece-conversion-via-R2-window forcing techniques are formalized as key strategic mechanisms used in the operational stall test.
- **2026-05-13** — Tiny endgame design principles formalized; cancel-queens + 1-to-3 valuation added as leading proposal. See `docs/potential-rule-changes.md` Sections 7 (principles) and 8 (proposal). Rulebook line-11 changelog cleanup (drops stale "last-moved-piece tracking" claim).
- **2026-05-13** — Rulebook audit; state hash drops `last_move` (keeps invulnerability); promotion supports all queen forms; GameEngine default `manipulation_mode='freeze'`. Commits `8daa440` (audit fixes) and `808c2ef` (revert two of the fixes per design feedback).
- **2026-05-13** — Manipulation freeze setter uses `has_enemy_piece` (broad) so invulnerable manipulated knights still get frozen.
- **2026-05-13** — Queen manipulation restriction 2 now correctly gates on `last_move_turn_number == turn_number - 1` (transformations between turns clear the restriction).
- **2026-05-13** — Manipulated-pawn promotion preserves freeze on the new piece.
- **2026-05-13** — Rook properly treats invulnerable enemies as blockers (cannot capture, cannot pass through).
- **2026-05-13** — Comprehensive audit of `has_enemy_piece` vs `has_capturable_enemy_piece` usage; `queen_moves_enemy` find-queen check fixed for robustness.
- **2026-05-13** — Knight jump-capture eligibility under double-manipulation explicitly documented in rulebook.
- **2026-05-12** — Knight v2 invulnerability requires adjacent-enemy condition (replaces previous "universal protection after any jump"). Removes perpetual invulnerability cycles via friendly-piece bouncing.
- **2026-05-12** — Black shield mirrors white shield with colors inverted (same outer dimensions).
- **2026-05-12** — Adjacent-enemy check uses `has_enemy_piece` (engagement, not capturability).
- **2026-05-11** — Flip-board feature (F key, 180° visual rotation, mid-action allowed).
- **2026-05-10** — V2 knight rules: jump-capture + invulnerability replace V0/V1 "always capture adjacent enemy after jump".
- **2026-05-10** — King's special capture explicitly does not override invulnerability.

---

## Strategic-position notes (verified through prior analysis)

These came up in tiny endgame design discussions. Useful context for future endgame analysis.

- **K + royal-Q vs K + royal-Q + non-Q**: forced for B (the larger side) under optimal play. A's royal queen can be tethered as a perpetually-invulnerable knight, but A's tether constraint limits state-space variation, and B wins via legal-moves runout under tiny endgame distance count.
- **K + royal-Q vs K + PQ + non-Q** (worst case for B; A has royal-count advantage): also forced for B. A's queen-as-knight is geometrically tethered to A's K, restricting it to a small ring of squares; B's free movement on the rest of the board lets B push A's K and outlast A on legal-moves variation.
- **K + Q vs K + B + 2-attackers**: SUSPECT — previously stated as forced for B (bishop pin + off-line attacker corners the queen), but not verified under queen-as-bishop escape and queen lock-down dynamics. Likely drift-prone in many sub-cases (e.g., K+Q vs K+B+R where K+B+R coverage is much less than 64).
- **K + Q vs K + R + R + N**: **DRIFT-PRONE** (corrected 2026-05-14). Queen transforms to bishop; K+R+R+N attacks at most 63 of 64 squares; queen-as-bishop always has at least 1 safe teleport destination; cannot be cornered.
- **K + B + B + B vs K + Q**: impossible (only 2 bishops per side at game start; pawns promote to queens only, not bishops).
- **Symmetric positions**: TRIVIALLY stall-prone under optimal play. K+R+R vs K+R+R, K+B+B vs K+B+B, K+Q+R vs K+Q+R, etc. Counterexamples to "no stall positions exist."
- **Near-symmetric (single piece-type swap)**: likely stall-prone. Swapping rook ↔ knight ↔ bishop between sides doesn't create enough material asymmetry to force a win under optimal play.
- **Tiny endgame purpose**: provides PRACTICAL termination via the distance-count cap. The repetition rule is a theoretical termination guarantor but takes a practically unreasonable number of turns; tiny endgame bounds resolution to a practical turn count. When active, the player who runs out of legal moves first loses. Under optimal play, the rule ensures every covered position resolves decisively within practical turn budgets.

**Operational stall test (use this for any classification):**
- To classify a position objectively as stall-prone vs forceable, **assume the repetition rule does NOT exist**, then check whether optimal play stalls infinitely.
- Stall-prone = stalls infinitely under no-repetition optimal play → rule MUST activate.
- Forceable = forced-win in finite turns under no-repetition optimal play → rule doesn't strictly need to activate.
- Full methodology in `docs/potential-rule-changes.md` Section 7 and `memory/project_tiny_endgame_analysis_methodology.md`.

**Important meta-note for re-using these facts:** previously-stated forced-side classifications were NOT established under the operational stall test, and several have been corrected (K+Q vs K+R+R+N) or flagged as suspect (K+Q vs K+B+2-attackers). Re-verify any historical claim using the methodology in `docs/potential-rule-changes.md` Section 7. Default to "stall-prone" when concrete forcing sequence cannot be demonstrated.
