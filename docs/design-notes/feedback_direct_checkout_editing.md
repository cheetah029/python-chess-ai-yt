---
name: feedback-direct-checkout-editing
description: Since 2026-11-27 I edit directly in the user's checkout again, as the live view, with LIVE-STATUS.md and a saved version at every stable point.
metadata:
  type: feedback
---

**I edit my own track directly in the user's checkout,
`/Users/ag/Code/python-chess-ai-yt`, on a feature branch.** The user
watches the work there as it happens. This replaces the earlier rule
"never edit the user's checkout except `git pull`".

**Why:** the user said on 2026-11-27 that they preferred the old
direct-checkout experience ("editable and not read-only") to a separate
live folder, and that seeing changes in real time matters to them. They
turned down renaming the checkout, which would have broken the
`--shared` clones and the memory path tied to it. The earlier scratch-copy
rule existed because of two problems: a game launched mid-edit played
half-finished code ([[reviewer-plays-from-checkout]]), and other sessions'
tests ran in this folder. Both are handled now as described below.

**How to apply:**
- Keep `LIVE-STATUS.md` at the checkout root current. It reads
  **EDITING: don't launch** while I'm mid-edit, and **STABLE** with a
  description at safe points. It is untracked, listed in
  `.git/info/exclude`.
- At each STABLE point, save a player version
  (`src/player_versions.py save`) and rebuild the compiled build
  (`src/compiled.py build`).
- Branches: create the feature branch in the checkout, commit there,
  push, open the PR, merge, then `git checkout main && git pull`.
- Long full-suite runs still go in a `git clone --shared` scratch clone
  of the committed tree, so my edits can't disturb them
  ([[feedback-test-in-history-clone]]).
- Subagents edit in their own clones inside the repo at
  `.agents/<name>/`, which is local-only (`.git/info/exclude`). The user
  sees their edits live there. They never touch the outer checkout's files
  or branch.
- A sync loop (`sync_main.sh`, approved 2026-11-27) merges `origin/main`
  into the checkout every 2 seconds (a light ls-remote check;
  a fetch only when main changed). It dies with the Claude session, so
  restart it in each new session. The user does NOT want a LaunchAgent;
  it runs only while this project is being worked on.
- Never rename or move the checkout.
- The user may edit too. They said they won't do it at the same time
  as me, but check `git status` before switching branches.
