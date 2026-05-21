---
name: Chess variant — quick-reference overview
description: One-page summary of the chess variant rules that differ most from standard chess. Read this AND RULEBOOK_v2.md AND docs/key-rule-differences.md on any rule-related task.
type: project
originSessionId: 953deca3-9d3a-4d54-8ce6-5506efb26872
---
# Chess variant (python-chess-ai-yt) — quick overview

**Authoritative rulebook:** `RULEBOOK_v2.md` in repo.
**Full differences cheat sheet:** `docs/key-rule-differences.md` in repo.

This is a chess VARIANT with deliberate rule differences. Standard-chess intuition leaks in and produces wrong answers if not suppressed.

## Top mistakes to avoid (drilled in past conversations)

- ❌ Bishops directly attack on diagonal — NO, **reactive capture ONLY** (a piece must move while on the bishop's LOS to be capturable; bishop fires on its IMMEDIATE next turn).
- ❌ Queens move unlimited squares — NO, **base form is 1-square king-like**. Queen has manipulation + transformation actions.
- ❌ Knights move L-shape (8 squares) — NO, **radius-2 (16 squares)**: 2-orthogonal, 2-diagonal, L-shape.
- ❌ Pawns can't move sideways — NO, **pawns move forward / left / right**.
- ❌ Pawn promotes to base queen only — NO, **can promote to any queen form** (base or transformed).
- ❌ King doesn't capture friendlies — NO, **king captures enemies, friendlies, AND the boulder** (unique).
- ❌ Knight invulnerability is universal after any jump — NO, **requires adjacent-enemy condition** (land beside a non-jumped enemy).

## Piece quick-reference

| Piece | Movement | Capture |
|---|---|---|
| Pawn | Forward / left / right (1 sq) | Forward + diag-forward-left/right |
| King | 1 sq any direction | Enemies, friendlies, boulder |
| Queen base | 1 sq any direction | Adjacent enemy |
| Queen actions | n/a | Manipulation, Transformation |
| Rook | 1 orth + n perp (turn 90°) | Either step |
| Bishop | Teleport to safe square | Reactive (assassin) only |
| Knight | Radius-2 (16 squares) | At landing + jump-capture |

## Special mechanics

- **Boulder** at central intersection; first-move only to d4/e4/d5/e5; later king-like; pawns-only capture; king-only captured; cooldown both sides.
- **Manipulation freeze**: manipulated piece can't make a spatial move on its next turn (actions still allowed).
- **Manipulation restriction**: queen can't manipulate piece that made a SPATIAL move on the immediately preceding turn (actions in between clear the restriction).
- **No check/checkmate.** Win by capturing BOTH royals (king + royal queen).
- **Repetition rule**: state hash includes positions + invulnerability + whose turn. Excludes last-move. 3rd repetition is illegal.
- **No-legal-moves loss**: no move and no action available at start of turn → you lose.
- **Tiny endgame**: distance-count mechanism enforces decisive resolution; never produces draws.

## Implementation key conventions

- `has_enemy_piece(color)` — BROAD (engagement/threat/blocker; includes invulnerable).
- `has_capturable_enemy_piece(color)` — NARROW (capture decisions; filters invulnerable).
- Rule of thumb: capture moves → narrow; everything else → broad.

- `Board.KNIGHT_MODE_V2` (default, active) vs `KNIGHT_MODE_LEGACY` (`main_v0.py` / `main_v1.py` snapshots only).
- `GameEngine` default `manipulation_mode='freeze'` (matches v2 rulebook).

## Procedure for any rule-related session

1. Read `RULEBOOK_v2.md` fully.
2. Read `docs/key-rule-differences.md`.
3. List the differences from standard chess at the top of your response.
4. Run `git log --oneline -20` to see recent design context.
5. Check `docs/potential-rule-changes.md` for in-progress proposals (notably the Tiny Endgame Rule variants).
