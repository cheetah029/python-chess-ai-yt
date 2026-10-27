---
name: reviewer-plays-from-checkout
description: The user launches the Royal Chess / m,n,k windows from the main checkout, so uncommitted edits there become "a different version" of the player to them
metadata:
  type: project
---

The user plays the game windows (`src/main.py`, `lgref/play_mnk.py`) from
`/Users/ag/Code/python-chess-ai-yt/`, the same folder agents edit. Python
reads `search.py` / `features.py` / `game.py` once at launch, so a launch
during an in-progress edit plays half-finished code for that whole session.

**Why:** On 2026-10-26 the user saw `1... Ne8-f6` once, then `Nd8-c6`
again after relaunching. All 68 committed versions since 2026-10-16 play
`Nd8-c6`; there was no branch switch; warm-searcher routes (undo,
jump-to-start) did not flip it. The transient working copy is the most
likely source (`docs/candidate-designs.md` §21, corrected 2026-10-27).
Also, from 2026-10-27 other Claude sessions run tests on other branches in
that same checkout, so switching branches there breaks them.

**How to apply:** Do not leave player-affecting edits uncommitted in the
main checkout while the user may be playing. On 2026-10-27 the #278 work
was done in a scratch `git archive` export and committed with git plumbing
(temporary index, `commit-tree`, `update-ref`) — no worktree, no checkout
switch. Confirm with the user that this is acceptable alongside the
no-worktrees rule [[workflow-no-worktrees]]. When a player "changed",
ask when it was launched and check the working copy first.
