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

**NOT hashed: literal `last_move.final` / `last_move.initial` coordinates.** Last-move relevance to legal moves is captured entirely by two DERIVED per-piece/per-bishop flags (above in per-piece section):

1. **`moved_last_turn` flag (per-piece):** True iff this piece moved on the immediately preceding turn AND some enemy base-form queen has queen-LoS (R2 relevance) OR some enemy knight is at chebyshev-1 (jump-capture relevance). Captures both R2 and knight-jump-capture eligibility consequences in one flag.
2. **`reactive_armed` flag (per-bishop):** True iff this bishop is enemy-of-moved-piece AND has unblocked diagonal LoS to `last_move.initial`. Captures bishop reactive eligibility per bishop.

Why these flags suffice (and the literal coords don't): the legal-move set depends only on whether each rule is "armed" at each relevant piece, not on the literal squares the last move involved. Two states with the same per-piece flags have the same legal-move set, hence the same hash. Two states with different `last_move.initial` that produce the same set of armed bishops (e.g., both initials on the same bishops' diagonals) hash IDENTICALLY — this was the over-differentiation the user caught in the prior design.

Edge cases handled:
- Boulder moves: boulder color is 'none', so `enemy_of_moved` is undefined → both flags are False for all pieces → hashed as if no last_move.
- Moved piece captured during resolution: `mp is None` at last_move.final → both flags False everywhere → hashed as if no last_move.
- Older-than-preceding-turn `last_move`: `last_move_turn_number != turn_number - 1` → flags False everywhere → hashed as if no last_move.

**Deliberately NOT hashed:**
- The repetition rule's own state-history counts.
- The tiny endgame rule's distance counts.
These are game-level rule-tracking, not properties of the current position. Including them would conflate the rule mechanisms with the positions they apply to.

## Why this redesign (2026-05-26)

The previous "positional only" design (2026-05-13) included only `is_royal`/`is_transformed` for queen markers and explicitly EXCLUDED `last_move` history. The user identified that this omits flags that materially change legal moves:

1. `moved_by_queen`: a frozen piece's legal-move set differs from an unfrozen one's.
2. `forbidden_square` / `forbidden_zone`: alternative manipulation-mode restrictions, same issue.
3. `last_move.final` + `last_move_turn_number == turn_number - 1`: gates Restriction 2 manipulation eligibility AND knight jump-capture eligibility. Additionally, `last_move.initial` gates bishop reactive-capture eligibility.

Two positions identical in piece arrangement but differing in any of these flags can have DIFFERENT legal-move sets. The old hash collided them, biasing repetition detection toward false positives. The new hash separates them — but ONLY when the difference actually changes the legal-move set, to avoid the opposite bias (over-differentiation that causes spurious misses). The new framing matches the user's principle exactly: same legal-move set ⇒ same state.

### Conditional inclusion of last-move info → derived per-piece flags

An initial fix (PR #77, committed earlier on 2026-05-26) included `last_move.final` unconditionally whenever it pointed to a piece that moved on the immediately preceding turn. User identified this over-differentiated: two states where `last_move.final` differs but neither difference affects ANY rule's eligibility would still hash differently.

A second fix (PR #78, same day) made inclusion of `last_move.final` and `last_move.initial` CONDITIONAL on whether some enemy queen/knight/bishop was positioned to consult them. But this STILL over-differentiated by including the LITERAL coordinates when the relevance check passed: two states with different initial squares that both happened to be on the same bishops' diagonals (producing the same armed-bishop set) would still hash differently.

The final fix (PR #79, same day) eliminates literal coordinates from the hash entirely. Last-move relevance is captured by two derived flags on the per-piece entry: `moved_last_turn` (per-piece, True iff some rule consults this piece's recent move) and `reactive_armed` (per-bishop, True iff this bishop has LoS to last_move.initial). Now two states with the same derived flags hash identically — matching the user's principle exactly.

## Impact on training (Goal 3)

Prior to the original "positional only" → "all legal-move-affecting state" fix on 2026-05-26, the training (`models/variant_freeze_v3/`) had completed 9 iterations with 0 repetition losses across 900 games (verified in per-game JSONL). The original bug never fired, so the network weights at `model_iter_0009.pt` are valid. Training was paused, the hash fix applied, training resumed from `model_iter_0009.pt`.

After PR #78's conditional-inclusion refinement, iter 10 had been completed. Iter 10 also produced 0 repetitions (per `iter_0010.jsonl`), so its data is fine. Training resumed from `model_iter_0010.pt`.

After PR #79's literal-coords → derived-flags refinement, iter 11 had completed (0 repetitions per `iter_0011.jsonl`). Training resumed from `model_iter_0011.pt` with the final correct hash. No data loss across all three fixes.

## Implementation

- `src/board.py get_state_hash()`: extended to include the per-piece manipulation flags + last-move-effective-info entry.
- `tests/test_piece_movement.py`: 5 new tests verify each new field changes the hash, including the "older last_move hashes as None" boundary case.
- `RULEBOOK_v2.md` Repetition Rule section: rewritten to state the governing principle and list each component explicitly.

## Historical note

The 2026-05-13 "positional only" framing was based on the user's "repetition is a positional rule" intuition at that time, which excluded last_move from the hash. The 2026-05-26 redesign reverses this decision in favor of the more rigorous "legal-move-determining state" framing. Future audits should not re-revert — the new framing is the correct one given the rules' dependence on these flags.
