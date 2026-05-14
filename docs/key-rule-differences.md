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

**Bishop pin mechanics:**
- A bishop on an enemy piece's diagonal "pins" the enemy in the sense that any spatial move triggers reactive capture.
- The pin does NOT actively threaten the pinned piece — if the pinned piece stays still, the bishop can never capture it.
- Manipulation movements DO trigger the reactive capture (any spatial relocation counts).
- Knight jumps are spatial moves and trigger reactive capture (subject to knight invulnerability rules).

### Knight

| Aspect | Standard chess | This variant |
|---|---|---|
| Movement | L-shape only (8 squares) | **Radius-2 pattern (16 squares)**: 2-orthogonal, 2-diagonal, or L-shape (2+1). |
| Jumping | Yes (over any piece) | Same. |
| Standard capture | Any enemy at L-shape destination | Any enemy at radius-2 destination. |
| Jumped square | n/a (no concept) | Every knight move passes over **one specific square** (the "jumped square"). For 2-orthogonal: 1 square in that direction. For 2-diagonal: 1 square diagonally from origin. For L-shape: 1 square along the 2-square direction. |
| Jump capture | n/a | If an enemy piece moved on the immediately preceding turn into a square the knight can jump over, the knight may capture it by jumping over it on the knight's next turn. Only the jumped piece is captured — NOT adjacent pieces to landing. |
| Post-jump status | n/a | **Invulnerability** for 1 opponent turn after a non-capture jump, IF the landing square is adjacent (chebyshev 1) to at least one enemy piece OTHER than the jumped piece. |

**Knight invulnerability detailed:**
- Trigger: non-capture spatial move + jumps over a piece + lands adjacent to a non-jumped enemy.
- The jumped piece can be friendly, enemy, or boulder.
- The adjacent enemy CAN be invulnerable itself (engagement check, not capturability).
- **Manipulated knights do NOT get functional invulnerability.** The flag is set, but cleared at the start of the manipulated player's next own turn before they can benefit from it.
- Capture moves (standard at landing OR jump-capture of jumped piece) do NOT grant invulnerability.
- Declining an offered jump-capture is a non-capture move, so it CAN grant invulnerability (subject to the adjacent-enemy condition).
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
- **State hash includes**: piece positions, boulder markers, queen markers (is_royal / is_transformed), whose turn, and currently-invulnerable pieces.
- **State hash does NOT include**: last-move history. Repetition is a purely positional rule.
- If all legal turns produce a 3rd repetition, the player loses.

### Tiny Endgame Rule

The active rulebook version:
- Applies when no pawns AND (≤4 pieces OR ≤6 pieces with both sides ≥2 non-king AND diff ≤1).
- Uses a "distance count" mechanism (Manhattan distance between closest opposing royals; each value 1–14 has a count cap of 3).
- Non-capture move that would push the resulting royal distance count over 3 is illegal.
- If all legal turns would do so, player loses.

**Important framing:** Tiny endgame **NEVER causes a draw**. It's a "ticking time bomb" — when active, the game must resolve in finite turns with a winner. The player who runs out of legal moves first loses. The rule's PURPOSE is to prevent infinite drift.

**Important caveat:** This rule is under active design discussion. A "cancel-queens + 1-to-3 valuation" variant has been proposed but is NOT yet adopted in `RULEBOOK_v2.md`. Check `docs/potential-rule-changes.md` and recent commits for the latest.

### No Legal Moves Loss

- If a player has no legal turn (no move and no action) at the start of their turn, they lose.
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
- ❌ **`has_capturable_enemy_piece` is the right helper for engagement checks.** No — that filters invulnerable enemies. Use `has_enemy_piece` for presence/engagement/threat/blocker checks.
- ❌ **In a "double-manipulation" scenario (A manipulates B's piece next to A's knight, B manipulates the knight to jump over it), the jump-capture isn't offered.** No — it IS offered per the rulebook. Manipulated movements count as "moved on the immediately preceding turn" for jump-capture eligibility. The decision is by the player whose turn it is (the second manipulator), who would normally decline (since the jumped piece is their own).

---

## Recent major design decisions (reference timeline)

Listed by commit / date for quick git-log lookup.

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
- **K + Q vs K + B + 2-attackers**: forced for B. Bishop pin + off-line attacker corners the queen.
- **K + B + B + B vs K + Q**: impossible (only 2 bishops per side at game start; pawns promote to queens only, not bishops).
- **Tiny endgame purpose**: prevents infinite drift, never produces draws. When active, the player who runs out of legal moves first loses. The rule's existence justifies including positions that would otherwise stall.
