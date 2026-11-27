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

# Checkout, merging and git pull — how changes reach the user

The user watches the repository in their checkout,
`/Users/ag/Code/python-chess-ai-yt`, and wants every change to the repo's
files to show up there in real time, as if all work were edited directly
in it.

- **Claude's own work is edited directly in the checkout**, on a feature
  branch: one issue, one branch, one PR. No git worktrees. Never rename or
  move the checkout: `git clone --shared` copies borrow its `.git`.
- **`LIVE-STATUS.md`** (untracked, listed in `.git/info/exclude`) at the
  checkout root always says **STABLE** (safe to launch the game) or
  **EDITING: don't launch**, and what is in progress. At every STABLE point,
  save a player version (`src/player_versions.py save`) and rebuild
  `python3 src/compiled.py build`.
- **Full test suites run in a `git clone --shared` scratch copy** of the
  committed tree, so edits in the checkout cannot disturb them.
- **Background agents edit in their own clones inside the repo, in
  `.agents/<name>/`**, so the user sees their in-progress edits in the same
  window. `.agents/` is local only (listed in `.git/info/exclude`), and its
  dot prefix keeps pytest and the repository's file walks out of it. Agents
  never touch the checkout's own files or branch. Run directories and logs
  may stay in the scratchpad.
- **Merging:** when a PR's tests pass, merge it without asking
  (`gh pr merge --merge --delete-branch`), check that main's tree equals the
  tested tree, close the issue, then `git checkout main && git pull` in the
  checkout. Never ask the user to pull; just do it.
- **Other agents' merges:** pull them into the checkout as soon as you hear
  of the merge. On a feature branch, that means merging `origin/main` into
  it. **A sync loop does this every 2 seconds** (the user approved it on
  2026-11-27). It is `sync_main.sh` in the session scratchpad: it skips
  while git is busy, and git refuses to merge over uncommitted edits. If it
  is not running, as in a new session, restart it, or pull by hand right
  after every merge.

# Chess Rule Handling — MANDATORY procedure

This codebase implements a chess **variant** with rules that deliberately
differ from standard chess. Pretrained chess intuition leaks in and
produces wrong answers unless explicitly suppressed. Follow this
procedure on every rule-related task without exception:

1. **Read `RULEBOOK.md` fully, top to bottom**, before responding to
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
   familiar from regular chess, verify against `RULEBOOK.md` first.
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
   (`RULEBOOK.md`) may not match what's been verbally discussed in
   recent conversations. Treat the rulebook as authoritative for the
   _current_ state; treat proposals as in-progress.

# GDL dialect — infix is official, prefix is outdated

`docs/gdl/integrated.gdl` is written in **infix HRF**
(ggp.stanford.edu / Epilog dialect) and is the **official** game
description:

```
legal(P, move(boulder, FF, FR, TF, TR)) :- true(control(P)) & ...
```

`docs/gdl/integrated_prefix.gdl` says exactly the same thing in
**prefix KIF**, an outdated dialect that is hard to read:

```
(<= (legal ?p (move boulder ?ff ?fr ?tf ?tr)) (true (control ?p)) ...)
```

Rules:

- **Read, quote and explain using the infix file only.** Never put
  prefix KIF in a document, a commit message, or an explanation to the
  user. The prefix file exists only because the 11 step fragments are
  still authored in that dialect and some older tooling reads them.
- **The LGREF framework takes infix as input.** `lgref.identify.load`
  refuses a prefix file with a message naming the converter.
- **After changing any step file, rebuild BOTH**, in this order:

  ```bash
  python3 docs/gdl/build_integrated_prefix.py > docs/gdl/integrated_prefix.gdl
  python3 docs/gdl/build_integrated.py
  ```

  `tests/test_gdl_dialect_consistency.py` fails the build if the two
  files drift, and also checks that both give the same legal moves.
- Statement counts differ **by design**: a prefix `(or A B)` body
  becomes one rule per branch in infix, so 534 prefix forms are 567
  infix statements. That is the expansion, not a discrepancy.

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
- Whenever the context window is almost full (80% or above), create and prepare
  a session handoff and update it in real time as you go so that the next
  session is ready to go at any time after a context compaction occurs. Context
  compaction may occur at any time in the middle of a response so make sure to
  be ready for it when it comes.
- **Read the session handoff FIRST after every context compaction**, before
  doing anything else. That means the newest `docs/session_handoff_*.md`, plus
  a live, uncommitted copy in the session scratchpad if one exists. A
  compaction summary is not a substitute for it. Keep the handoff current all
  the time, not only near 80%: compaction can happen at any moment, even in the
  middle of a response.

# Validate every implementation immediately after finishing it

This applies to absolutely everything: code, tests, scripts, experiments,
docs, data. **Right after finishing an implementation, before moving on, do
an overall check of the whole thing.** Read through all of it for hidden
bugs, inconsistencies and wrong assumptions: logic, edge cases, flags and
labels, numbers quoted in docs against what the code does, and leftovers such
as generated files. Add plenty of test cases, including small hand-built cases
whose right answer is known. The goal is to catch bugs while the work is
fresh, not later while building something else on top of it.

An **old bug** found along the way, one that predates the current work, is
fixed as soon as possible in its own change. It is never left for later or
silently worked around.
