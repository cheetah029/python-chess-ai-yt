---
name: Repetition state hash design (positional only)
description: The repetition state hash is positional + invulnerability, deliberately excluding last-move / move history.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
The state hash used for repetition detection (`Board.get_state_hash`) is **positional only**, with one current-status addition for invulnerability:

**Included:**
- Piece positions (with name, color, is_royal, is_transformed)
- Boulder markers (cooldown, last_square, on-intersection flag)
- Whose turn it is
- Currently-invulnerable pieces (sorted (row, col) tuple)

**Deliberately excluded:**
- `last_move` and `last_move_turn_number`. Repetition is a positional rule, not a move-history rule. Two positions that look identical and have identical invulnerability status count as the same state.

Knight jump-capture eligibility and bishop reactive-capture eligibility are gated by separate move-time checks (`_can_jump_capture`, etc.) that read `last_move` and `last_move_turn_number` directly. The repetition hash doesn't need to track these.

**Decision date:** 2026-05-13. Original audit added last_move to the hash; user pushed back ("repetition is a positional rule") and we reverted.

**Why invulnerability stays:** an invulnerable knight on a square is a meaningfully different position than a non-invulnerable knight on the same square — opposing captures are filtered differently. This IS a per-piece status, just temporary.

Rulebook reference: `RULEBOOK_v2.md` Repetition Rule section.
