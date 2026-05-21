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

**2. Invulnerability after non-capture jump (with adjacent-enemy condition):**
- Trigger: non-capture jump over a piece AND landing chebyshev-1 adjacent to an enemy OTHER than the jumped piece.
- Adjacent enemy CAN itself be invulnerable (engagement check, not capturability — uses `has_enemy_piece`, the broad helper).
- Duration: 1 opponent turn.
- Universal protection: no piece (including king) can capture an invulnerable piece during its invulnerability turn.
- Manipulated knights don't get functional invulnerability (cleared at start of knight owner's next turn).

The adjacent-enemy condition was added 2026-05-12 to prevent the degenerate "perpetual invulnerability via friendly-piece bouncing" cycle that the original "any jump grants invulnerability" rule enabled. The new rule encodes a "cavalry charge into engagement" thematic: invulnerability rewards committing to close-range engagement, not stalling in safe space.

Movement: radius-2 pattern (16 destinations: 2-orthogonal, 2-diagonal, L-shape 2+1). NOT just L-shape like standard chess.

Implementation: `Board.move()` (v2 knight branch), `Board._can_jump_capture()`, `Board._has_adjacent_enemy_other_than_jumped()`, `Board.set_invulnerable_after_jump_decline()`.

Tests: `tests/test_v2_knight.py`, especially Section 6b (adjacent-enemy condition) and the late-file engagement-checks section.
