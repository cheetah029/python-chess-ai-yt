---
name: feedback-save-game-records
description: Save every measured game's full record (gzipped JSON) as it is played; never replay games just to study them.
metadata:
  type: feedback
---

Save the full record of every game a measurement plays: races, phase
checks and version-table cells. For Royal Chess that means
`engine.get_game_record().to_dict()`, plus each side's root value per
move and the run's settings. Write it gzipped JSON to
`results/game-records/<experiment>/...`. `results/` is git-ignored and
bundled to GitHub Releases through `lgref/core/release.py`; uploading
is a step the user approves.

**Why:** the user said on 2026-11-27: "Rerunning entire games is very
inefficient; why not just record the pgn of each game". Studying why
depth 3 won two race games had needed full replays. Measured cost: a
200-turn record is 135 KB raw and 3.5 KB gzipped.

**How to apply:** build the recorder into every new measurement script
from the start. Don't rerun old games ahead of time: every player is
deterministic or seeded, so regenerate an old game only when it is
actually needed. The user also chose a PAIR measure for paired-position
races (depth 4 won both / split / depth 3 won both; split pairs say
nothing about the players). See [[project-v7-depth4]].
