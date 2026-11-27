---
name: project-v7-depth4
description: V7 = the V4 player at depth 4 (major version by user decision); the window switches to depth 4 after the speed-ups.
metadata:
  type: project
---

**V7** is the V4-family player at max_depth 4 with quiescence 2 on
Royal Chess, and `DEPTH_BY_CELLS` + 1 on m,n,k. Its representative is
V7.0 at d98c09c. It is a major version by the user's decision
(2026-11-27), not by the numbering rule.

Evidence: a 40-game race against depth 3, with the rule declared
beforehand, gave 34 wins, 6 draws (all at the 150-ply cap) and 0
losses: 92.5% [80.1, 97.4]. A null control and a replay were also
run. The record is in `docs/experiments/depth4-race.md`.

The user said (2026-11-27): **"V7 is fine; switch to depth 4 after the
speedups."** The window (`Game.TD_DEPTH`, `src/game.py`) goes to 4 once
the speed work lands. Change 19, the Cython build at 1.81×, is the main
one. The ship-gate memory still asks for a per-phase check at the
played depth (`tools/phase_rates.py`) before switching, so run it and
record the user's approval with it.

**How to apply:** don't switch the window before the speed-up PRs
merge. When switching, cite this approval and the phase check. See
[[feedback-ship-gate]] and [[feedback-design-strictly-better]].
