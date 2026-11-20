---
name: save-every-player-version
description: Save each distinct version of the playable agent, even uncommitted in-progress ones, so any version the user liked can be replayed
metadata:
  type: feedback
---

Save every version of the player that differs, including in-progress
ones, "in case I would like it" (user, 2026-10-28).

**Why:** a version the user once played (`1... Ne8-f6`) existed only as
a half-finished working copy and could not be recovered. The variance
itself is fine; losing a version they might prefer is not.

**How to apply:** `src/player_versions.py` (commit 7189afd on
`claude/objective-extraction-268`) keeps versions under
`refs/players/<id>` in the main repo; the id hashes src/ and lgref/
Python (tests excluded) plus the shipped weights. The window saves
itself at launch and shows the id in its title bar. When working in a
scratch export, run
`PLAYER_VERSIONS_GIT_DIR=<repo>/.git python src/player_versions.py save --root <tree> --note "..."`
after every player-affecting change and before every race or
measurement. `list` and `play <id>` replay one. Related:
[[reviewer-plays-from-checkout]], [[feedback-design-strictly-better]].
