---
name: feedback-general-evaluation
description: "Any evaluation or tie-break change must be derived from the game's rules (GDL), never Royal-Chess-specific, so it stays sensible on modified rules and unseen games."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 252cea8a-14f9-463b-9e1e-3eb11c31618d
  modified: 2026-11-27T18:22:49.278Z
---

Every evaluation, feature or tie-break added to the player must be GENERAL: derived
from the structure of the game's rules (the GDL), so each game gets its own
evaluation. Tuning on Royal Chess's Tiny Endgame or repetition rule is allowed, but
the result must not be specific to Royal Chess: it must still make sense if the Tiny
Endgame Rule is modified, and on a different game with a similar counter-limited rule.

**Why:** (user, 2026-11-27) an evaluation learned on one game and applied unchanged to a
game where it is useless or harmful is not general, and over-fits the development
games. LGREF's player is meant for unseen games.

**How to apply:** describe a rule by its SHAPE in the GDL (e.g. a counter fluent such
as `state_repetition_count(H,N)` / `distance_count(D,N)` capped by a legality filter,
with `lost(P)` when no turn survives), never by its name or by Royal Chess constants.
Weights are learned per game. Before shipping, check the change on a second game and
on a modified rule (e.g. a different cap). Pairs with [[feedback-design-strictly-better]]
and [[feedback-ship-gate]].
