---
name: V2 knight redesign (jump-capture + invulnerability with adjacent-enemy condition)
description: The v2 knight has radius-2 movement, jump-capture (only the jumped piece, only if it moved on the immediately preceding turn), and conditional invulnerability after non-capture jumps that land adjacent to a non-jumped enemy.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
The v2 knight differs from V0/V1 in two major ways:

**1. Jump-capture replaces V0/V1's "capture any adjacent enemy after jump":**
- Only the JUMPED piece can be captured (not adjacent pieces to landing).
- The jumped piece must have moved on the IMMEDIATELY preceding turn.
- "Moved" means a spatial move; transformations (actions) don't count.
- Queen-manipulated movements DO count.

**2. Invulnerability after non-capture jump (friendly/boulder + adjacent-enemy):**
- Trigger (all required): non-capture jump + jumped piece is **friendly to the knight or the boulder** (NOT an enemy) + landing chebyshev-1 adjacent to an enemy OTHER than the jumped piece.
- Adjacent enemy CAN itself be invulnerable (engagement check, not capturability — uses `has_enemy_piece`, the broad helper).
- Duration: 1 opponent turn.
- Universal protection: no piece (including king) can capture an invulnerable piece during its invulnerability turn.
- Manipulated knights don't get functional invulnerability (cleared at start of knight owner's next turn).
- **Declined jump-capture never grants invulnerability** — jump-capture is only offered when the jumped piece is an enemy, and an enemy jumped piece is disqualified by the friendly/boulder-only rule.

Two refinements to the original "any jump grants invulnerability" idea:

1. **Adjacent-enemy condition** (2026-05-12): the landing must be next to a non-jumped enemy. Prevents the "perpetual invulnerability via friendly-piece bouncing in safe space" cycle.

2. **Friendly/boulder-only jumped piece** (2026-05-25): the jumped piece must be friendly or the boulder. Closes the "perpetual invulnerability via enemy-territory chain-leaps" loophole that the broader rule still allowed (a knight inside enemy lines could keep leaping over enemies indefinitely). Thematically: the cavalry-charge launches from your own lines, leaping past your own troops to engage the enemy — not weaving through the enemy itself.

Implementation: `Board._jumped_piece_grants_invulnerability` is the gate; called inside `move()` and `set_invulnerable_after_jump_decline()` plus the repetition-simulation mirror in `would_cause_repetition`.

Movement: radius-2 pattern (16 destinations: 2-orthogonal, 2-diagonal, L-shape 2+1). NOT just L-shape like standard chess.

Implementation: `Board.move()` (v2 knight branch), `Board._can_jump_capture()`, `Board._has_adjacent_enemy_other_than_jumped()`, `Board.set_invulnerable_after_jump_decline()`.

Tests: `tests/test_v2_knight.py`, especially Section 6b (adjacent-enemy condition) and the late-file engagement-checks section.

## Proactive jump-capture considered and rejected (2026-05-25)

A brief design experiment switched jump-capture from reactive to PROACTIVE
(any enemy at chebyshev-1 capturable regardless of timing) — PR #68 — then
reverted same day after user-led analysis. The reasons for keeping reactive:

1. **Queen base-form vulnerability.** Under proactive, a defended knight at
   chebyshev-1 of a base-form queen creates an immediate trap (queen
   captured next turn). Players would learn to avoid base form near enemy
   knights, atrophying manipulation — a CORE variant mechanic.
2. **King-trap geometry.** Under proactive, knight at chebyshev-1 of king
   creates an immediate trap because the king's chebyshev-1 escape squares
   are all in the knight's 24-square (chebyshev-1 + chebyshev-2) threat
   zone. Under reactive, the knight has to commit to a chebyshev-2 position
   first; the king's escape squares from chebyshev-1 of a chebyshev-2-
   positioned knight include multiple chebyshev-3 safe squares. The
   difference is qualitative, not just tempo.
3. **The "counterintuitive inversion" critique of reactive is overstated.**
   Reactive has a coherent thematic reading: "movement creates exposure."
   This parallels the bishop's reactive capture and forms a unified
   "interceptive captures" family in the variant. Players learn it once.

Alternatives considered before reverting:
- Royals immune to jump-capture: addressed king-trap and RQ base form,
  but left PQ base form and other non-royal pieces vulnerable.
- Royals + base-form queens immune: covered the user's stated concerns
  but introduced state-dependent rule complexity.
- Knight "settle" (knight cannot jump-capture from a square it just moved
  to): addressed the immediate-trap issue but punished knight mobility
  (knight must stagnate to maintain area control) and let opponents
  freely approach an active knight to chebyshev-1 (knight's threat
  reappears next turn, confusingly).

Reactive remains the cleanest comprehensive solution. PR was reverted.
