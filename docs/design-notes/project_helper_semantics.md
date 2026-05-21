---
name: has_enemy_piece vs has_capturable_enemy_piece semantics
description: Two Square helpers with distinct semantics. Using the wrong one has caused several bugs (manipulation freeze, rook blocker, etc.).
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
Two `Square` helper methods that are easy to confuse:

**`has_enemy_piece(color)`** — BROAD
- Returns True iff: opposing colour, not the boulder.
- Does NOT filter invulnerable enemies.
- Use for: engagement / presence / threat / blocker queries. Anything where "is there an enemy here?" is the right question.

**`has_capturable_enemy_piece(color)`** — NARROW
- Returns True iff: opposing colour, not boulder, AND not currently invulnerable.
- Use for: capture-decision queries. "Can I capture this piece right now?"

**Rule of thumb:** capture move generation → narrow. Everything else → broad.

**Bugs this distinction has caused:**

1. **Manipulation freeze setter (fixed `f611bd8`):** main.py used narrow, which dropped invulnerable manipulated knights from getting the freeze flag. Changed to broad.

2. **Rook blocker (fixed `c7d8204`):** rook's step-1 and step-2 sweep had no branch for "uncapturable occupant" — invulnerable enemies fell through and were treated as empty, letting the rook capture them OR pass through them. Fix added explicit `has_piece() → continue/break` branches.

3. **Adjacent-enemy invulnerability check (fixed earlier):** check originally used narrow, dropping invulnerable adjacent enemies — the v2 invulnerability condition wouldn't trigger if the only adjacent enemy was itself invulnerable. Changed to broad (engagement is engagement).

4. **queen_moves_enemy find-friendly-queen (fixed `c257a16`):** the check for the manipulator's queen used narrow, which would silently drop an invulnerable queen. Latent bug today (no normal mechanism makes base-form queens invulnerable), but brittle. Changed to broad for robustness.

**Comprehensive audit completed 2026-05-13** (commit `c257a16`). Every call site of either helper documented with the correct semantic. Tests pin each piece's invulnerability contract in `tests/test_v2_knight.py` (section "Invulnerability interaction with every move generator").
