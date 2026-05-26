---
name: Repetition state hash design (legal-move-determining state)
description: The repetition state hash captures all information that determines the legal-move set at this position, except for the repetition rule's own state-history counts and the tiny endgame rule's distance counts.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---

## Current design (2026-05-26 redesign; supersedes 2026-05-13 "positional-only" design)

**Governing principle:** the state hash captures everything that determines the set of legal moves at this position, EXCEPT for the restrictions enforced by the repetition rule itself (state-history counts) and the tiny endgame rule (distance-count history). Those two rules track game-state history that accumulates over time; they aren't properties of the current position. Everything else that affects legal moves IS in the hash.

**Hashed per piece:**
- position (row, col)
- name, color
- `is_royal` (royal queen vs promoted queen) + `is_transformed` (form: base vs R/B/N)
- `moved_by_queen` — Restriction 1 freeze (freeze mode): a frozen piece may not make a spatial move on its next turn
- `forbidden_square` — original-mode restriction on the manipulated piece's next square
- `forbidden_zone` — exclusion-zone-mode restriction on the manipulated piece's next destination
- `invulnerable` — captureability filter for opposing pieces

**Hashed at game-state level:**
- boulder state (cooldown + last_square + intersection flag)
- whose turn it is
- **the square (if any) of a piece that moved on the immediately preceding turn.** Two rules consult this single fact: (a) manipulation Restriction 2 (queen may not manipulate a piece that moved on the immediately preceding turn), and (b) knight reactive jump-capture eligibility (jumped piece must have moved on the immediately preceding turn). Both depend on the EXACT condition `last_move_turn_number == turn_number - 1`. We collapse it to one field — either the final square of the just-moved piece, or `None` if the last spatial move was older than the immediately preceding turn.

**Deliberately NOT hashed:**
- The repetition rule's own state-history counts.
- The tiny endgame rule's distance counts.
These are game-level rule-tracking, not properties of the current position. Including them would conflate the rule mechanisms with the positions they apply to.

## Why this redesign (2026-05-26)

The previous "positional only" design (2026-05-13) included only `is_royal`/`is_transformed` for queen markers and explicitly EXCLUDED `last_move` history. The user identified that this omits flags that materially change legal moves:

1. `moved_by_queen`: a frozen piece's legal-move set differs from an unfrozen one's.
2. `forbidden_square` / `forbidden_zone`: alternative manipulation-mode restrictions, same issue.
3. `last_move.final` + `last_move_turn_number == turn_number - 1`: gates Restriction 2 manipulation eligibility AND knight jump-capture eligibility.

Two positions identical in piece arrangement but differing in any of these flags have DIFFERENT legal-move sets. The old hash collided them, biasing repetition detection toward false positives. The new hash separates them, matching the user's principle: same legal-move set ⇒ same state.

## Impact on training (Goal 3)

Prior to the fix, the running training (`models/variant_freeze_v3/`) had completed 9 iterations with 0 repetition losses across 900 games (verified in per-game JSONL). The bug never fired, so the network weights at `model_iter_0009.pt` are valid. Training was paused, the hash fix applied, and training resumed from `model_iter_0009.pt`. No data loss.

## Implementation

- `src/board.py get_state_hash()`: extended to include the per-piece manipulation flags + last-move-effective-info entry.
- `tests/test_piece_movement.py`: 5 new tests verify each new field changes the hash, including the "older last_move hashes as None" boundary case.
- `RULEBOOK_v2.md` Repetition Rule section: rewritten to state the governing principle and list each component explicitly.

## Historical note

The 2026-05-13 "positional only" framing was based on the user's "repetition is a positional rule" intuition at that time, which excluded last_move from the hash. The 2026-05-26 redesign reverses this decision in favor of the more rigorous "legal-move-determining state" framing. Future audits should not re-revert — the new framing is the correct one given the rules' dependence on these flags.
