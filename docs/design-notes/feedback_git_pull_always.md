---
name: feedback-git-pull-always
description: "Pull the user's checkout after every merge, without asking; also merge finished PRs without asking."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 252cea8a-14f9-463b-9e1e-3eb11c31618d
  modified: 2026-11-27T08:03:40.518Z
---

After every PR merges (mine or a subagent's), run `git pull` in the user's
checkout `/Users/ag/Code/python-chess-ai-yt` right away. Don't ask first and
don't wait to be told. Merge finished PRs without asking, too.

**Why:** the user said on 2026-11-27: "You don't have to ask me to git pull,
just do it yourself all the time." Earlier they also said "merge and pull them
whenever you are done". They kept having to type "git pull" by hand.

**How to apply:** after `gh pr merge`, run `git -C <checkout> pull -q`. Check
`git status` first, and stop if the checkout has local changes or is on a
branch other than main. Tell subagents that this permission is standing. See
[[feedback-merge-when-finished]].
