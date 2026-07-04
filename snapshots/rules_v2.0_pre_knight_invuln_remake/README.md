# Snapshot: v2.0 ruleset — BEFORE the knight-invulnerability remake

Frozen copies of every rules-bearing file as of 2026-06-14, immediately
before the knight-invulnerability rule change ("leap between friend and
foe" remake). The corresponding full-repo freeze is the annotated git
tag **`rules-v2.0-pre-knight-invuln-remake`**.

## The rule as frozen here (old rule)

> A knight gains invulnerability on a **non-capture** spatial move that
> jumps over a **friendly piece or the boulder** (never an enemy) and
> lands adjacent (chebyshev-1) to at least one enemy other than the
> jumped piece. Invulnerability lasts for the immediately following
> opponent turn only.

## What changed after this snapshot (new rule)

> A knight gains invulnerability on a **non-capturing** leap over **any
> piece** when it lands adjacent to a piece of the **opposite allegiance
> to the one it jumped**: jump a friendly/boulder → land beside an
> enemy (same as the old rule); jump an **enemy** → land beside a
> **friendly or the boulder** (new case). The boulder counts as
> friendly-side in both roles and never as an enemy.

## Model compatibility

`models/variant_freeze_v3/` (through `model_iter_0500.pt` /
`model_final.pt`) was trained ENTIRELY on the ruleset in this snapshot.
Post-remake fine-tuning continues in a separate models directory.

## Files

| File | Role |
|---|---|
| `RULEBOOK_v2.md` | Concise rulebook (authoritative) |
| `RULEBOOK_v2_elaborated.md` | Long-form rulebook with rationale |
| `key-rule-differences.md` | Cheat sheet vs standard chess |
| `board.py` | Rules engine (invuln grant + repetition simulation) |
| `engine.py` | Turn enumeration engine |
| `piece.py` | Piece definitions |
| `game.py` | Game/UI state machine |
| `step8_add_knight_jump_capture_invuln.gdl` | GDL step 8 (knight invuln) |
| `integrated.gdl` / `integrated_infix.gdl` | Full GDL (prefix + infix) |
