---
name: Tiny endgame rule fix for bishop deadlock
description: Planned rule change to activate tiny endgame when no knights or rooks remain, fixing bishop-only stalling endgames
type: project
---

Add a third activation clause to the tiny endgame rule to fix "bishop deadlock" draws.

**Current rule:** No pawns AND (≤4 pieces OR ≤6 pieces with same types ignoring kings)

**New clause:** OR ≤6 non-neutral pieces AND no actual knights or rooks remain on either side.

Key details:
- A royal queen counts as "queen" even while transformed (use same logic as `_get_piece_type_for_comparison`). This prevents the exploit where transforming queen→knight toggles the rule on/off to reset distance counts.
- A promoted queen also counts as "queen", not whatever it transforms into.
- Only actual (non-royal, non-promoted) knights and rooks count. If even one exists, the clause doesn't apply.
- This targets bishop-only endgames where no piece can proactively capture — bishops only capture reactively (diagonal sight mechanic).

**Why:** All 4 observed draws across random and trained AI data follow the same "bishop deadlock" pattern: 5-6 pieces, asymmetric composition, only bishops as non-royal attackers. The symmetry check prevents activation.

**How to apply:** Implement in `board.py` `is_tiny_endgame()` method after initial data collection with original rules is complete. The fix is intentionally narrow — it doesn't affect endgames with rooks/knights where asymmetric material creates real winning chances.
