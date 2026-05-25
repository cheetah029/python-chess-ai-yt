---
name: V2 knight redesign (jump-capture + invulnerability with adjacent-enemy condition)
description: The v2 knight has radius-2 movement, jump-capture (only the jumped piece, only if it moved on the immediately preceding turn), and conditional invulnerability after non-capture jumps that land adjacent to a non-jumped enemy.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
The v2 knight differs from V0/V1 in two major ways:

**1. Jump-capture replaces V0/V1's "capture any adjacent enemy after jump":**
- Only the JUMPED piece can be captured (not adjacent pieces to landing).
- **Proactive** (as of 2026-05-25): any enemy on the jumped square is capturable, no timing condition. The earlier reactive constraint ("piece must have moved on the immediately preceding turn") was removed because the resulting hybrid mechanic (reactive jump + proactive standard capture) created a counterintuitive inversion — a sitting enemy at chebyshev-1 was safer than a sitting enemy at chebyshev-2, even though the chebyshev-1 enemy is closer. Proactive jump-capture gives the knight a single coherent threat zone (chebyshev-1 jump + chebyshev-2 standard = 24 squares), matching natural player intuition.
- The landing square must still be empty (otherwise it's a standard capture, not a jump-capture).
- Knight's other capture modes unchanged: standard capture at chebyshev-2 (radius-2) landings.

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
