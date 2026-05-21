## python-chess-ai-yt — project memory

> **WORKFLOW RULE (user directive, 2026-05-21): DO NOT create or work on git worktrees.**
> Work directly on the user's MAIN repo at `/Users/ag/Code/python-chess-ai-yt/`, using
> FEATURE BRANCHES for development (then PR → main). The harness may reset the shell cwd
> back to a `.claude/worktrees/...` folder after each Bash command — IGNORE that worktree;
> target the main repo explicitly: `git -C /Users/ag/Code/python-chess-ai-yt/ <cmd>` and
> edit files via absolute paths under `/Users/ag/Code/python-chess-ai-yt/`. The main repo
> stays on a real branch (`main` between features, a feature branch during work) — never
> leave it in detached HEAD. The leftover `tender-haibt-45bbac` worktree (branch
> claude/v2-knight-rule-refinement-45, already merged via PR #46) is harmless and can be
> pruned with `git worktree remove`.

> **AGENT REMINDER (keep the in-repo mirror in sync):** A point-in-time copy of
> these memory files is mirrored into the repo at `docs/design-notes/` so the
> user can see them in VS Code. **Whenever you change ANY memory file in this
> directory, you MUST re-copy it (and this MEMORY.md) into `docs/design-notes/`
> and commit, so the snapshot doesn't go stale.** Mirror command:
> `cp ~/.claude/projects/-Users-ag-Code-python-chess-ai-yt/memory/*.md <repo>/docs/design-notes/`
> (preserve the existing `docs/design-notes/README.md`).

For any rule-related work, read these files in order:

1. **`RULEBOOK_v2.md`** (in repo) — authoritative rules. Read top to bottom.
2. **`docs/key-rule-differences.md`** (in repo) — fast cheat sheet of differences from standard chess + common misconceptions.
3. **`CLAUDE.md`** (in repo) — mandatory procedure for rule-related tasks.

Then `git log --oneline -20` for recent design context (commit bodies contain rationale).

### Quick orientation

- [Project roadmap & goals](project_roadmap.md) — the 4 goals: (1) finish >6 stall analysis, (2) human-vs-AI game mode, (3) train AI on new rules (finalize rules first!), (4) ambitious GDL/GGP research (aimed at ISEF, ROBO category). Read for "what are we building toward."
- [Chess variant overview](project_chess_variant_overview.md) — one-page summary of the variant. Read this if you've forgotten what kind of project this is.

### Topic-specific notes

- [Helper semantics: `has_enemy_piece` vs `has_capturable_enemy_piece`](project_helper_semantics.md) — broad-vs-narrow Square helpers; using the wrong one has caused several bugs.
- [V2 knight redesign](project_v2_knight_redesign.md) — radius-2 movement, jump-capture, invulnerability with adjacent-enemy condition.
- [State hash design](project_state_hash_design.md) — repetition is positional + invulnerability only; deliberately excludes last-move history.
- [Piece strategic dynamics](project_piece_strategic_dynamics.md) — **READ FIRST for any tiny-endgame analysis.** Bishop is an ACTIVE piece (global teleport + pin power). Queens lock down via mutual bishop pin. Queens escape via bishop-form teleport when opponent's coverage < 64. Action stalling avoids reactive capture.
- [Tiny endgame analysis methodology](project_tiny_endgame_analysis_methodology.md) — **READ FIRST for any tiny-endgame analysis.** Operational stall definition (assume repetition rule absent). Required analysis steps. Anti-pattern checklist of mistakes to avoid.
- [Tiny endgame status](project_tiny_endgame_status.md) — current rulebook version + proposed variants (cancel-queens, Pattern A/B/C) under active discussion. Includes corrected strategic facts (K+Q vs K+R+R+N is drift-prone).
- [Tiny endgame fix (older proposal)](project_tiny_endgame_fix.md) — earliest proposal to activate when no knights/rooks remain. Superseded by later discussions but kept for history.

### Active branch

`claude/v2-knight-rule-refinement-45` (or similar). Do not commit to main.

### Snapshot mainloops (frozen)

- `main.py` — active v2 game.
- `main_v1.py` — v2 freeze + LEGACY knight (no invulnerability).
- `main_v0.py` — v1 manipulation + LEGACY knight.

Snapshots receive only cross-cutting UI/mechanical bug fixes, never rule changes.
