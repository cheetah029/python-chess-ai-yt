---
name: feedback-merge-when-finished
description: "Merge each issue's PR into main as soon as it is finished; never pile new issues onto an open PR's branch."
metadata:
  node_type: memory
  type: feedback
  originSessionId: dcdc89ce-e2d3-4d1c-b05b-e1156784efb1
  modified: 2026-10-30T03:25:03.357Z
---

One issue → one branch cut from **main** → one PR → merged into main once
it is finished and its tests pass. Then close the issue and delete the
branch. Do not commit the next issue onto a branch whose PR is still
open, and do not stack new PRs on an unmerged branch unless the user asks.

**Why:** PR #270 (branch `claude/objective-extraction-268`) was opened
2026-10-10 for #268. Issues #271, #272 and #278 were then committed onto the
same branch instead of getting their own PRs, and nobody merged it. By
2026-10-29 that was 153 commits, and main had no learned player at all
(no TD weights, Searcher or play_mnk). #283–#285 and the V6 stack
(#287→#289→#291) were then stacked on top. The user called this bad
practice: it was not intended, just forgotten. They froze it with one
big merge on 2026-10-29.

**How to apply:**
- At the start of a task, branch from an up-to-date main, not from whatever
  branch the checkout is on.
- When a PR is finished (tests pass, user has seen it), merge it, or ask
  to merge it in the wrap-up. Do not leave it open "for later".
- If work genuinely depends on an unmerged PR, say so to the user and get
  that PR merged first, rather than stacking.
- Before deleting a merged branch, retarget any PR based on it, or
  GitHub auto-closes those PRs (this happened to #284).
- Related: [[feedback-ship-gate]] (player changes still need the ship
  gate before they count as finished).
