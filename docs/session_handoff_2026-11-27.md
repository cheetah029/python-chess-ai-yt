# Session handoff — 2026-11-27 (live; updated as work goes)

Read this first after a context compaction. Supersedes
`session_handoff_2026-10-24.md` for the search-speed / depth-4 arc.

SC = /private/tmp/claude-502/-Users-ag-Code-python-chess-ai-yt/252cea8a-14f9-463b-9e1e-3eb11c31618d/scratchpad
(the session scratchpad. It may be wiped; everything that matters is
also listed here.)

## Standing rules (from the user)

- No git worktrees. **Since 2026-11-27 I edit my track DIRECTLY in the
  user's checkout `/Users/ag/Code/python-chess-ai-yt`** (its live view),
  on feature branches:
  - Keep `LIVE-STATUS.md` (untracked) at EDITING or STABLE.
  - Save a player version and rebuild `src/compiled.py build` at each
    STABLE point.
  - Never rename the checkout.
  - Full suites still run in scratch clones. Agents never touch the
    checkout.
  - `git pull` after every merge, without asking.
- Merge finished PRs without asking. One issue, one branch, one PR.
  Tests and docs go in the same commit. Run the full suites
  (`tests/` and `lgref/tests`) in a `git clone --shared` scratch clone
  with a `.venv` symlink. Run flake8 and bandit.
- Commit with `bash $SC/plumb.sh <tree> <branch> <msgfile> <paths...>`.
  It builds on origin/main. Commit messages end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; PR bodies
  end with the Claude Code line.
- Strictly-better method: declare in DECLARED
  (`lgref/tests/test_method.py`) BEFORE writing the code, prove with
  `certificate.identical`, add the proof to the roll-call,
  mutation-test, and measure last. Save each player version with
  `src/player_versions.py save`.
- Keep this handoff current all the time (CLAUDE.md).

## Three parallel tracks the user asked for (2026-11-26)

1. **Paper A experiments.** Background agent `paper-a`
   (SendMessage to "paper-a").
   - Done: stage 1 (#352), stage 2 (#355), stage 3 (#357).
   - Now: stage 4 (#358), Experiments 1–3 on dev, then the freeze.
   - User instructions given 2026-11-27:
     - A blind Claude review of every method's grouping, as a
       SUBJECTIVE secondary metric.
     - The objective metrics are primary.
     - Exactly two sets, dev and test. Games seen before Paper A are
       assigned to one of them.
2. **Version win-rate tables** (`docs/experiments/version-win-rates.md`,
   #349). Background agent `version-table`.
   - Done: #353, #356.
   - User instructions given 2026-11-27:
     - Breadth first: every fillable cell to n=100, then 200, 300, 400.
     - Rename the Krieg-TicTacToe row to also say Krieg-m,n,k 3,3,3.
     - Add a V7 column and a V7 baseline table once V7 has a SHA.
   - Its scheduler is in `$SC/version-table/` (`queue.txt`, `slots`,
     `logs/cells/`).
3. **Depth 4** (issue #279). Me.
   - Changes 13–17 are merged (#344, #345, #346, #348, #354).
   - Change 18 (three more turn walks, about 2.8%) is committed on branch
     `claude/turn-walks-279` (e895b06, tree bb135a4). The recheck on
     the merged tree is task byqdaynqa, running in `$SC/m18`. Then:
     PR, merge, pull, comment on #279.
   - Depth race (rule declared beforehand in
     `$SC/depth4_race_plan.md`): depth 4 vs depth 3, 40 games:
     **34 wins, 6 draws, 0 losses, score 92.5%, Wilson about
     [80, 97]**. It passes the rule (≥60% and lower bound >50%).
   - Verification:
     - The race script's `truncated` flag was wrong: it compared plies
       after the opening, not `engine.turn_number`. All 6 draws are
       turn-cap draws (opening plies + game plies = 150).
     - Null control running, depth 3 vs depth 3 with the same harness,
       20 games: `$SC/race_null_{0,10}.log`, task b8l0o67g9.
     - Reproducing game 2 on the merged tree: task bsayedhuf.
   - User decision: **depth 4 is a new major version**. V5 and V6 are
     taken, so it is **V7**. To do: add it to `docs/agent-versions.md`,
     record the race, send the SHA to version-table.
   - User decision: **proceed with "fewer positions searched, designed
     so the moves don't change"**.
     - Note: Searcher already has iterative deepening, a transposition
       table, killers, history, and (for Royal Chess) LMR. Read
       `lgref/experiments/search.py` before designing.
     - The design must be declared IDENTICAL (same move, root values
       and ties at the played depth) before any code.

## Status updates (newest last)

- Change 18 merged as #359 (checkout pulled to d98c09c, later to
  ad83864 after #360). #279 has a comment with the race result.
- Race verification: game 2 replayed on today's code gives exactly the
  same game (d4 wins at 59 plies), so the race reproduces and changes
  17/18 kept the moves. Null control (d3 vs d3) still running.
- Version-table agent: #360 merged (breadth-first, Krieg row renamed).
  The scheduler takes about 2 days to bring every cell to n=100. It is
  waiting for the V7 SHA.
- Paper A agent: stage 3 #357 merged. Stage 4 #358 is in progress with
  the user's two instructions. Dev and test sets are listed in the
  message relayed to the user.
- The scratchpad lost plumb.sh, bench279.py and bench_abc.sh (cause
  unknown). plumb.sh is recreated with the same content.
- FEWER-POSITIONS design, measured over 12 depth-4 moves
  (`$SC/nodes_where.py`):
  - 238k nodes in all; 104k `_search` calls, 91k of them at depth 0.
  - 240k quiescence calls. Iteration 4 is 75% of the nodes, iteration
    3 24%.
  - Horizon nodes are almost all tactical: 44,366 tactical vs 32
    quiet (`$SC/horizon_cost.py`).
  - Searcher ALREADY has a TT, ID, killers, history, PVS, LMR,
    futility and quiescence. Aspiration windows and an eval cache
    were tried before and failed (documented in search.py).
  - The tables persist across moves, so any change to which nodes
    are visited can change later moves.
  - Result: no IDENTICAL node reduction of size was found. Options
    were taken back to the user (compile hot paths, which is
    IDENTICAL; or delta pruning in quiescence, which changes moves
    and needs the ship gate).

- User chose COMPILED HOT PATHS (2026-11-27).
  - Pilot: Cython 3.0.11, no source edits, gave 67.3 s -> 37.2 s CPU on
    six depth-4 decisions, with the same moves and node counts.
  - Change 19 in `$SC/tc`:
    - `src/compiled.py`: build into build/compiled, with a SHA-256
      freshness loader.
    - `src/main.py` and `tools/race_agents.py` activate it only when
      run as main.
    - `.gitignore` gets `build/`; `requirements.txt` gets
      Cython==3.0.11, which is installed in .venv.
    - Declared in DECLARED as 'the hot modules compiled by Cython play
      identically'. Its test is
      `test_the_hot_modules_compiled_by_cython_play_identically`, in
      the roll-call; it passes in 96 s.
    - Mutants running (task bwqzn0osz). docs/search-speed.md §19 has
      MUTATION_19 and MEASURED_19 placeholders.
  - Still to do: measure with interleaved pairs (`$SC/d4bench.py ROOT`,
    pure m18 vs tc with the build), flake8/bandit, full suites, PR.
- V7 PR in `$SC/tv7`:
  - `docs/agent-versions.md` V7 section, `docs/experiments/depth4-race.md`
    and the test update.
  - Message `$SC/msg_v7.txt`, PR body `$SC/pr_v7.md`, TESTS_V7
    placeholder; suites are task biv0swv4w.
  - Branch to use: `claude/v7-depth4-279`.
  - Null control finished: 8.5/20 for the "d4" label (42.5%).
  - Version-table agent has been given V7 = d98c09c; it is told not to
    merge its V7-column PR before mine.

- Change 19 status:
  - Mutants: 3 of 3 fail. Measured 67.96 -> 37.55 s, 1.81x.
  - build() now compiles COPIES, so no .c files land in the tree, and
    the test's temp build is removed at exit.
  - Full suites: task bsk1x7c1o.
  - Message `$SC/msg_compiled.txt`, PR body `$SC/pr_compiled.md`
    (TESTS_19 placeholder). Branch `claude/compiled-hot-paths-279`.
  - Paths to commit: src/compiled.py src/main.py tools/race_agents.py
    .gitignore requirements.txt lgref/tests/test_method.py
    docs/search-speed.md.
  - After merge: message version-table (compiled build landed);
    install of Cython in .venv is already done.

- MERGED:
  - #361: V7 docs and the race record.
  - #362: change 19, the compiled build; player version 856c785773f3.
  - Checkout pulled to d244ba4. #279 has comments for both.
- User (2026-11-27):
  - "V7 is fine; switch to depth 4 after the speedups."
  - No turn caps in Royal Chess strength data (memory
    feedback_offline_accuracy_over_speed).
  - Ablation correctness ideas were relayed to paper-a.
  - Open question to the user: should a piece's initial placement
    belong to its rule group?
- Uncapped replay of the 6 capped race games: task bd0gto5v1, logs
  `$SC/race_nocap_{a,b}.log` (games 7,17,32 and 14,19,36).
- Version-table agent:
  - Told to remove the Royal Chess cap and replay its 2 truncated
    games.
  - Told #361 merged, and that the compiled build is for V7 only.
- Per-phase gate before setting TD_DEPTH=4:
  - Rule declared in `$SC/depth4_phase_plan.md`.
  - Script `$SC/phase_race.py`, run in clone `$SC/ph` (d244ba4,
    compiled build).
  - Finding positions: task bkjxz6xcn, `$SC/phase_positions.json`.
  - Then play 20 midgame and 20 endgame games:
    `phase_race.py . play $SC/phase_positions.json midgame 0,...,19`.
  - If both phases PASS: PR setting `Game.TD_DEPTH = 4` (and
    TD_DEPTH_LABEL), plus tests and docs (agent-versions: window plays
    V7), plus an approval record citing the user's words.
- Nit to fix later: `compiled.build` prints compiler warnings
  noisily. Capture them, and show them only on failure.

- User decisions (2026-11-27, later):
  - A piece's starting placement belongs to its rule group.
  - Setup/geometry statements are LANGUAGE, the ideal case.
  - Paper A must report the full ablation metric set (exactness,
    collateral, shortfall, breakage rate, fragility, rejections by
    reason, scatter severity, repair, termination discrepancies,
    stability, setup precision/recall), with objective metrics first.
    All of this was relayed to paper-a.
  - CLAUDE.md: read the handoff first after every compaction, and
    validate every implementation right after finishing it.
  - Phase map: the tracks are mapped onto Phases 0–7 / A–G in
    `docs/spec/phase-map.md`.

- LIVE HANDOFF NOW LIVES IN THE CHECKOUT (branch
  claude/session-process-docs, #365), not in $SC/th.
- Docs PR #365 (in the checkout, uncommitted):
  - CLAUDE.md: read the handoff after compaction; validate after
    implementing; the checkout, merge and pull workflow; `.agents/`;
    the sync loop.
  - Also the phase map, this handoff and the design-notes mirror.
  - The suite for the first version is task bh2k0syar (tests/ 1788
    passed; lgref still running). Commit from the checkout, then
    PR/merge.
- Sync loop `$SC/sync_main.sh` is running, user-approved (task
  b4ztqnrul), log `$SC/sync.log`.
- Agents edit in `.agents/<name>` inside the checkout
  (`.git/info/exclude`). version-table has switched; paper-a was told
  to.
- Per-phase gate:
  - Positions are in `$SC/phase_positions.json` (47 mid, 30 end).
  - Midgame 20 games: task bggq3ftyh, logs `$SC/phase_mid_{a,b}.log`.
  - Endgame 20 games: task bh8ilg6hw, logs `$SC/phase_end_{a,b}.log`.
- Uncapped replays of the race's capped games:
  - 7: d4 win (197 plies)
  - 17: d4 win (156)
  - 14: d4 win (146)
  - 19: **d3 win (221)**
  - 32 and 36 still running.
  - Corrected race so far: 37 d4 wins, 1 d3 win, 2 pending. Update
    docs/experiments/depth4-race.md when done.

- 2026-11-27, later:
  - #367 (process docs) and #368 (uncapped race, 38-0-2, 95.0%) merged.
  - Sync loop now every 2 s with a SHARED LOCK. Run my git commands in
    the checkout via `$SC/gitlock.sh git ...`. Loop task bq5aq8svl.
  - Tracing why depth 3 won games 19 and 36: task b34vjru1j, outputs
    `$SC/trace{19,36}.jsonl` (per-move value and material).

- Why depth 3 won race games 19 and 36 (traces in `$SC/trace{19,36}.jsonl`;
  depth-5 judge in `$SC/judge.py`):
  - Game 19: decided by the Tiny Endgame distance counts (active from
    played turn 183). Both sides evaluated exactly 0.500 from 172 to
    211; depth 4 ran out of options and lost with no_legal_moves.
  - Game 36: queen trade at 51-53, then a rook recapture into a
    bishop's reactive capture at 55-56, then the boulder ate pawns.
    Depth 3 and depth 4 without LMR would have chosen THE SAME moves at
    51, 53, 55 and 57.
  - So neither loss was depth 4 being worse.
  - Recommended order, sent to the user and awaiting OK:
    1. A Tiny Endgame tie-break inside exact ties (MONOTONE).
    2. Guarantee 1 (limit LMR so no move is searched shallower than
       depth 3 would search it).
    3. Guarantee 2 (fallback to depth 3) on hold.
- Per-phase pair rule:
  - Endgame: 2 D4, 8 split, 0 D3, so an extension is running (games
    20-39, task bba3bmeom, logs `$SC/phase_endx_{a,b}.log`, records in
    results/game-records/depth4-phase/endgame/).
  - Midgame: pairs 5-9 give 2 D4, 3 split, 0 D3. Games 0-9 are still
    running; game 0 had used 2.6 CPU-hours (a very long uncapped game).

- ENDGAME phase: PASS under the pair rule after one extension (20
  pairs: 3 D4, 17 split, 0 D3). There are 21 records in
  results/game-records/depth4-phase/endgame/. Midgame still waits on
  games 0-9.
- Paper A: the stage 1-4 agent finished (#366, #369 merged). A fresh
  agent is running stage 5 in `.agents/paper-a`. Two decisions are open
  with the user (the post-freeze terminal-edge variant; whether fixed
  tables count as rules).

- MIDGAME phase: PASS (10 pairs: 4 D4, 6 split, 0 D3). Opening,
  midgame and endgame have all passed. One midgame game ran 702 plies.
  These midgame games predate the recorder, so they have no saved
  records.
- Next for depth 4: the user's fix order (Tiny Endgame tie-break, then
  guarantee 1), then the window switch PR (TD_DEPTH=4), which cites the
  per-phase result and the user's approval.

## Open questions for the user

- None open. (Answered: the window switches to V7 after the speed-ups,
  gated per phase. Starting placement belongs to its rule group.)

## 2026-11-27, after the second compaction

- #383 and #385 merged (two old bugs: untracked symlink in run diffs;
  worker test vs compiled build). Run `gh pr merge` with
  `-R cheetah029/python-chess-ai-yt` from OUTSIDE the checkout.
- USER DECISIONS:
  - Depth 4: do the fixes IN ORDER: Tiny Endgame tie-break, then
    guarantee 1 (limit LMR), then the window switch (TD_DEPTH=4).
  - Paper A: YES to the post-freeze terminal-edge-off variant, YES to
    fixed tables counting as rules (kinds.yaml), YES to investigating
    the argument-permutation anomaly. Relayed to `paper-a`.
  - Ablation by substitution: user asked what it is (explained); still
    unbuilt.
  - NEW REQUIREMENT (generality): any evaluation or tie-break work must
    be GENERAL. It must be derived from the game's rules (the GDL), not
    from Royal Chess knowledge, so it still makes sense if the Tiny
    Endgame Rule changes or on an unseen game with a similar
    counter-limited rule. Tuning on development games must never bake
    in a Royal-Chess-only evaluation.
  - User asked: can the player see the repetition rule? Answer so far:
    the SEARCH sees both history rules inside its horizon (the engine
    filters illegal turns, and make/unmake carries `state_history` and
    `distance_counts`), but the EVALUATION sees neither, and the TT key
    leaves both out (known soundness caveat in search.py).
- In the GDL both rules have one shape: a counter fluent
  (`state_repetition_count(HASH,N)`, `distance_count(D,N)`) that a
  legality filter caps, plus `lost(P)` when no turn survives the
  filter. A general design should read that shape, not the rule names.
- Game 19 (the depth-3 win): from ply 183 it was lone royal queen vs
  lone royal queen (both in rook form), all values exactly 0.500 until
  ply 212; depth 4 lost on no_legal_moves at ply 221. Exact solve of
  depth 4's late decisions: `$SC/solve19.py`, task bevq35bgz.
