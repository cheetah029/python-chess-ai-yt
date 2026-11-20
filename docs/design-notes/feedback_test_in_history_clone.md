---
name: feedback-test-in-history-clone
description: "Run full test suites in a `git clone --shared` scratch clone (has history), never in a `git archive` export — exports make git-history tests fail falsely."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 252cea8a-14f9-463b-9e1e-3eb11c31618d
  modified: 2026-11-20T01:53:32.572Z
---

Run the full suite in a scratch CLONE that has history (`git clone --shared /Users/ag/Code/python-chess-ai-yt <scratch>/hist`, then fetch and check out the commit under test). Never call failures "environmental" because a `git archive` export lacks `.git`.

**Why:** On 2026-11-19 I had reported `test_every_sha_in_the_numbering_is_a_commit`, `test_untracked_files_reach_the_saved_diff` and `test_every_shipped_version_is_kept_and_the_index_matches` as failures needing "the repository's git history, which my scratch copies don't have". The user rightly pushed back: the history is right there in the main repo. In a clone with history all 24 tests in those files pass. A clone is not a worktree, so it respects [[MEMORY]]'s no-worktree rule and leaves the user's checkout untouched.

**How to apply:** For a trial merge, check it out in the clone and `git merge` the PR head there. Run the suite in the clone. Before committing via plumbing, `diff -rq` the archive of the combined branch tree against the tested clone, so what ships is byte-identical to what was tested.
