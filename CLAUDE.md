# Software Development Best Practices

Use GitHub to track changes.

Make small commits each time.

When committing code, also create tests and update documentation in the same commit.

Run local tests and make sure the test cases pass before committing.

Use code review software to check formatting issues before committing.

Use security software to check for security issues before committing.

Create GitHub issues before making code changes.

Do not check in to main branch directly.

Always use Git branching and merge requests to merge commits to the main branch.

After merging, also close the GitHub issue and delete the Git branch.

# Chess Rule Handling — MANDATORY procedure

This codebase implements a chess **variant** with rules that deliberately
differ from standard chess. Pretrained chess intuition leaks in and
produces wrong answers unless explicitly suppressed. Follow this
procedure on every rule-related task without exception:

1. **Read `RULEBOOK_v2.md` fully, top to bottom**, before responding to
   any rule, move, gameplay, or rule-design question. Do not rely on
   prior conversation context (context-window compactions erase it)
   and do not rely on standard-chess pretrained knowledge.

2. **Read `docs/key-rule-differences.md`** alongside the full rulebook.
   This document is a fast cheat sheet of every rule that differs from
   standard chess, plus a "common misconceptions to avoid" list of
   mistakes Claude has previously made.

3. **State the differences from standard chess at the top of your
   response.** Before answering any rule question, explicitly list the
   differences from standard chess for every piece and mechanic
   involved. This forces the variant rules into working memory and lets
   the user catch misconceptions immediately. Example opening:

   > "Note: in this variant, queen base form moves 1 square (king-like,
   > not unlimited range), bishops capture only via reactive mechanic
   > (no direct attack), knights move radius-2 (16 squares, not L-only).
   > Rule under discussion: [...]"

4. **Never assume a standard-chess rule applies.** If something feels
   familiar from regular chess, verify against `RULEBOOK_v2.md` first.
   Common false-friend rules are listed in `docs/key-rule-differences.md`
   under "Common Misconceptions To Avoid".

5. **If the rulebook is ambiguous, silent, or seems to contradict
   intuition, ASK** before inferring or applying standard chess.

6. **Run `git log --oneline -20` on rule-related sessions** so recent
   design decisions (captured in commit messages) become visible. The
   git history contains rationale for many rule changes that aren't
   re-stated in the rulebook text.

7. **`docs/potential-rule-changes.md`** contains proposed but
   not-yet-adopted variants. The Tiny Endgame Rule there is under
   active design discussion, and the active rulebook
   (`RULEBOOK_v2.md`) may not match what's been verbally discussed in
   recent conversations. Treat the rulebook as authoritative for the
   _current_ state; treat proposals as in-progress.

# Common Workflow Notes

- Active branch convention: feature branches like
  `claude/v2-knight-rule-refinement-45`. Do not commit directly to main.
- Snapshot mainloops `main_v0.py` and `main_v1.py` are FROZEN — only
  cross-cutting UI/mechanical bugs get backported, never rule
  changes. The active mainloop is `main.py`.
- Test discipline: most new features get tests in `tests/test_v2_*.py`
  (real-pygame), `tests/test_piece_movement.py` (mocked-pygame), or
  `tests/test_manipulation_variants.py` (engine flow). Always run the
  affected test files before committing. The mocked-pygame tests
  replace `pygame` with a stub module via `sys.modules['pygame']` —
  test ordering across mocked vs real-pygame files can produce flaky
  results; use `--cache-clear` on suspicious runs.
- Commit message conventions: I (Claude) have been writing detailed
  multi-paragraph commit bodies that explain rationale, trade-offs,
  and test coverage. These are the primary persistent record of
  design decisions and should be the first thing consulted after a
  context-window compaction.
