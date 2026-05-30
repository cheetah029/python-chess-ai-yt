---
name: Session handoff (2026-05-27 early AM)
description: Complete state at end of long session. Training is RUNNING in background (PID 68135). Read this first when picking up the project.
metadata:
  node_type: memory
  type: project
  originSessionId: e3b1db7b-ec7f-4a43-9b69-568c3971b17d
---

# Session Handoff — 2026-05-27 (early AM)

This file captures the full state at the end of a multi-hour session covering Goal 1 finalization, Goal 3 training kickoff + multiple iterations + state-hash refinements, rulebook editorial work, AI mode UI, and engine architecture refactors. Use this as the FIRST READ when resuming the project. The training is still running.

## Active state: Training

- **Process: PID 68135** running `src/trainer.py` with `--resume models/variant_freeze_v3/model_iter_0025.pt` and `--iterations 50` (so total target is iter 75 from THIS launch; could be extended to iter 100 with another resume).
- **At handoff: iteration 33/75 in self-play** (32 iterations fully complete with checkpoints saved at `models/variant_freeze_v3/model_iter_XXXX.pt` for XXXX = 0001 … 0032).
- **0 draws, 0 repetitions across all 3200+ games.** Avg game length ~200-225 turns. Loss settling around 0.010-0.020 as buffer grows.
- **The training process loaded the OLD CODE at startup** (pre-refactor). It will continue using the multi-step jump-capture / promotion API in-memory until restarted. The new engine refactor (PR #86, every Turn fully specified) will only be picked up by the next `--resume` invocation.
- VS Code can be safely restarted — training survives because of `nohup` (separate process).

## Goals state

### Goal 1 — Ruleset finalization (CLOSED)
- ≤6 non-king threshold confirmed (over multiple analyses).
- Queen valuation TIGHTENED from 1-to-3 to 1-to-2 (`PR #74`).
- Rulebook substantially rewritten into a CONCISE format (`PR #80`), with elaborated version preserved in `docs/RULEBOOK_v2_elaborated.md`.
- All editorial refinements landed: rulebook acknowledges 2 zero-bishop compositions (2R+N and 2N+R), K+2N+R example layout, knight section's manipulation-eligibility framing matches the bishop section's clarity, boulder no-return memory has conditional state-hash treatment.

### Goal 2 — Human vs AI mode (LIVE)
- In-UI mode menu (M key) with side + opponent selection.
- Opponent options: Human, Random, AI Easy, AI Medium, AI Hard (last two grayed out until their checkpoints exist).
- AI Easy currently maps to `model_iter_0032.pt` (was 10 → 20 → 27 over the session, user kept saying easy was too easy).
- Medium maps to `model_iter_0060.pt` (not yet trained — will become available when training crosses iter 60).
- Hard maps to `model_iter_0100.pt` (will become available at iter 100).
- AI sound effects fire on AI's turn (`PR #75`).
- Mode menu layout vertical for opponents (PR #84).

### Goal 3 — Training (IN PROGRESS, iter 33/75)
- Manipulation mode: `freeze` (active v2 rule).
- Per-game JSONL preserved for analysis (decisive + draws), with `loss_reason_counts` aggregated into `training_history.json`.
- Per-iteration model checkpoints saved (`model_iter_XXXX.pt`).
- User wants to push to **iteration 100** total. After current run finishes at iter 75, do another `--resume model_iter_0075.pt --iterations 25` to reach 100. ~10,000 games of training data total.
- 0 repetitions, 0 draws so far — no game ever hit the 1500 turn cap.

### Goal 4 — GDL/GGP research direction
- Long-horizon; not active.

## Major code-architecture state

### State hash (final design, PR #79 + #81)
Refined three times in this session:
1. (PR #77) Originally was "positional only" — bug: missed `moved_by_queen` and last-move flags.
2. (PR #78) Added last_move.final/.initial conditionally (only if some rule consults).
3. (PR #79) Replaced literal last-move coordinates with DERIVED per-piece flags:
   - `moved_last_turn` (per-piece flag, True iff this piece moved on the preceding turn AND some rule actually consults it via queen LoS or knight chebyshev-1)
   - `reactive_armed` (per-bishop flag, True iff this bishop has unblocked diagonal LoS to last_move.initial AND is enemy of moved piece)
4. (PR #81) Boulder `last_square` (no-return memory) conditionally hashed — only when the square is adjacent + empty + boulder not on cooldown.

Final invariant: **same legal-move set ⇒ same hash, regardless of how the position was reached.** See `docs/design-notes/project_state_hash_design.md` and `src/board.py get_state_hash()` for the full mapping.

### Engine architecture (PR #86 — every Turn fully specified)
**No more sub-choices anywhere.** The engine enumerates each (move + jump_choice + promo_choice) combination as a separate Turn. Each fully-specified Turn is counted exactly once for AI evaluation, training, and random selection.

- `Turn` fields: `jump_choice` (target or None), `promo_choice` (form string or None), `has_jump_offer` (True/False).
- `engine.get_all_legal_turns()` enumerates combinations.
- `engine.execute_turn(turn)` reads choices from Turn directly (no separate args).
- `NeuralPlayer.choose_turn(turns, engine)` is the ONLY decision method. No `choose_jump_capture` / `choose_promotion`.
- `RandomPlayer.choose_turn(turns, engine)` — same. Each combination is one option in the random sample.
- `AIController._apply_spatial` branches on `turn.has_jump_offer` / `turn.promo_choice`.

This was the user's last major architectural request. **CRITICAL: do NOT add back sub-choice methods to players.** The user was explicit: "all turns should count as a single possible legal turn option and should all be evaluated by the AI normally. Nothing should be left random or only sometimes decided."

### Analysis tools (built in this session)
- `tools/analyze_long_games.py` — find/inspect games over a turn threshold; snapshot positions at a specific turn.
- `tools/compare_models.py` — head-to-head between two checkpoints, alternating colors. "Is iter X stronger than iter Y?"
- `tools/benchmark_checkpoint.py` — one checkpoint vs RandomPlayer. Measure absolute strength.
- `tools/analyze_random_draws.py` (pre-existing) — random self-play stats.

All three new tools use CPU device (don't compete with MPS training).

## Open questions / next steps

1. **Easy difficulty calibration.** User said iter 27 was "slightly better than random but far from being a viable playable opponent." Bumped to iter 32 (latest at handoff). May need iter 40-50 for the user's threshold. **Use `tools/benchmark_checkpoint.py --checkpoint models/variant_freeze_v3/model_iter_0032.pt --num-games 20` to verify strength.** If net-vs-random win rate is still ~50/50, bump higher.

2. **Training extension to iter 100.** After current 75-iter run completes, resume from `model_iter_0075.pt` with `--iterations 25` to reach 100.

3. **Medium / Hard auto-enable.** `Game._AI_CHECKPOINTS` already maps Medium=iter 60, Hard=iter 100. They'll become available automatically when those checkpoints exist on disk (the mode menu grays them out / unblocks via `_ai_checkpoint_available`).

4. **Long-game investigation.** User was curious about the 7 long games (>1000 turns) in training. Analysis showed: at iter 2 with epsilon=0, games are deterministic 64 turns; long games come from EPSILON-GREEDY exploration (98% random at iter 2). The 7 long games in training data emerged at iters 2-19 (high exploration phase). All ended via royals_captured — no game hit the 1500 turn cap. Tool exists (`tools/analyze_long_games.py`) for further investigation; running with `--epsilon 1.0 --num-games 500` would statistically catch a few.

## File layout summary (for next-session orientation)

```
src/
├── board.py            # state hash with conditional last_move flags + boulder last_square
├── engine.py           # Turn class (fully-specified), get_all_legal_turns enumerates combinations
├── trainer.py          # NeuralPlayer with single choose_turn; play_training_game simplified
├── ai_controller.py    # _apply_spatial branches on Turn fields, no sub-method calls
├── players.py          # RandomPlayer with single choose_turn
├── game.py             # _AI_CHECKPOINTS dict, vertical opponent menu layout
└── main.py             # active v2 mainloop with mode menu, AI sounds, AI undo/redo skip

tests/
├── test_piece_movement.py  # 32 state hash tests (+ tiny endgame, repetition)
├── test_ai.py              # TestCombinationEvaluation (6 tests), TestTrainingData (5)
├── test_ai_controller.py   # 5 tests
└── test_mode_selection.py  # 33 tests (incl. 5 for AI difficulty UI)

tools/
├── analyze_long_games.py     # find/inspect long games via self-play
├── compare_models.py         # head-to-head checkpoint comparison
├── benchmark_checkpoint.py   # checkpoint vs random baseline
├── analyze_random_draws.py   # (pre-existing) random self-play stats
└── trace_shields.py          # (pre-existing) shield visualization helper

docs/
├── RULEBOOK_v2_elaborated.md  # full elaborated rules + rationale (archive)
├── key-rule-differences.md    # cheat sheet vs standard chess
├── design-notes/              # mirror of memory files
└── potential-rule-changes.md  # design backlog

models/variant_freeze_v3/
├── model_iter_0001.pt … model_iter_0032.pt  # per-iteration checkpoints (~7MB each)
├── games/iter_XXXX.jsonl                    # per-game summaries (incl. draws)
├── training_history.json                    # aggregate per-iter stats incl loss_reason_counts
├── training.log                              # stdout/stderr (append mode across resumes)
└── (final model will land here as model_final.pt when training completes)

RULEBOOK_v2.md          # CONCISE current rulebook (207 lines vs 520-line elaborated)
CLAUDE.md               # codebase + user instructions
```

## Recent PRs (this session, all merged)
- #74 — 1-to-2 valuation + trainer draw preservation
- #75 — AI move sounds
- #76 — Rulebook editorial fixes (knight section etc.)
- #77 — State hash includes per-piece flags + last_move (first attempt)
- #78 — Conditional inclusion of last_move
- #79 — Derived per-piece/per-bishop flags (final hash design)
- #80 — Concise rulebook rewrite; elaborated → docs/
- #81 — Boulder no-return-memory conditional
- #82 — Long boulder clarification → elaborated; tight rule → concise
- #83 — Easy/Medium/Hard AI mode UI
- #84 — Combination eval (interim); menu vertical
- #85 — All-turns-evaluated tests; easy → iter 20; long-game analyzer
- #86 — Engine refactor: every Turn fully specified; tools; easy → iter 27 (now iter 32)

## UPDATE (2026-05-27, later in session)

### Training progress
- At this update: **iter 49 complete, iter 50 in training phase.** `model_iter_0050.pt` imminent. Game lengths dropped to ~155 turns (network strengthening). Buffer near 500k cap. Loss ~0.04 (rose as buffer grew — normal).

### Easy AI now AUTO-RESOLVES (no manual bump needed)
- `Game._AI_CHECKPOINTS` (hardcoded dict) REPLACED with `Game._AI_DIFFICULTY` (target iteration + mode) and a `_resolve_ai_checkpoint(key)` classmethod.
- **Easy = 'capped' at iter 50**: auto-picks the highest existing checkpoint ≤ 50. So it tracks the strongest available model up to iter 50, then stops. When `model_iter_0050.pt` lands, easy auto-uses it. NO manual update needed — this directly answers the user's "does easy auto-update?" (now: YES, capped at 50).
- **Medium = 'exact' iter 75**, **Hard = 'exact' iter 100**: stay grayed-out until their exact checkpoint exists (no weak fallback).
- To change caps: edit `Game._AI_DIFFICULTY` targets in `src/game.py`.

### Pause/resume improvements (trainer.py) — NOT yet active on running process
The user noted resume resets epsilon, optimizer, AND buffer. Implemented (applies to NEXT trainer launch/resume, NOT the currently-running PID 68135 which loaded old code):
- **Optimizer state preserved**: saved to `<save_dir>/optimizer_state.pt` each iteration; restored on `--resume` (graceful skip if absent). Avoids Adam cold-start bump.
- **Epsilon schedule made resume-stable**: new `--epsilon-decay-iters` arg (default 100). Epsilon now decays over a FIXED horizon (absolute iteration / decay_iters, clamped), so resuming at iteration K always gives the same epsilon regardless of `--iterations`. Previously the denominator was `start_iteration + n_iterations`, which shifted on each resume.
- **Buffer NOT preserved** (decision): the replay buffer is up to 500k positions × 21×8×8 floats — too heavy to serialize each iteration (many GB). It rebuilds within a few iterations after resume. Documented trade-off; revisit only if buffer-reset proves to hurt.
- **When resuming to iter 100**: use `python3 src/trainer.py ... --resume models/variant_freeze_v3/model_iter_0075.pt --iterations 25 --epsilon-decay-iters 100`. The optimizer_state.pt + epsilon-decay-iters=100 keep continuity.

### Computer sleep wastes training time — SOLUTION
- A sleeping Mac SUSPENDS all processes (you can't run during sleep — the CPU halts). The fix is to PREVENT sleep while training runs.
- **Started `caffeinate -i -s -w 68135 &`** this session — prevents idle + system sleep until training PID 68135 exits (requires AC power for `-s`).
- For LID-CLOSED operation (clamshell): connect power + (external display OR `sudo pmset -c disablesleep 1`, re-enable later with `... disablesleep 0`). Closing the lid otherwise sleeps regardless of caffeinate.
- For future training launches, wrap in caffeinate directly: `caffeinate -i -s nohup python3 src/trainer.py ... &` so sleep-prevention is tied to the run automatically.
- NOTE: the caffeinate started this session only lasts while PID 68135 lives; if the user restarts training, re-run caffeinate with the new PID.

## What the user keeps reminding you

- "honest" / "honest reassessment" is a tell that you're about to be wrong. The user calls this out. Verify EVERYTHING carefully.
- Don't randomly pick any sub-choices — every full Turn must be a single distinct option, evaluated as such. (PR #86 nailed this; do NOT regress.)
- Work directly on the main repo at `/Users/ag/Code/python-chess-ai-yt/`. Feature branches OK; do NOT use worktrees.
- Mirror memory files to `docs/design-notes/` whenever you change them, and commit.

## UPDATE (2026-05-29 — reset confirmation + bishop rationale)

### Training progress at this update
- **iter 57/75 complete** (process still PID 68135, started 2026-05-25). `model_iter_0050.pt` landed → Easy AI auto-resolved to it (per the auto-resolve mechanic from PR #88). Latest iter 57: W=44 B=56, avg_len ~172 turns, loss ~0.048 (loss is in normal "buffer-full + harder positions" range). 0 draws/0 repetitions still hold across all 5700+ games. caffeinate (separate PID, this session's) still holding off sleep.
- After current run completes at iter 75, plan resume to iter 100: `python3 src/trainer.py ... --resume models/variant_freeze_v3/model_iter_0075.pt --iterations 25 --epsilon-decay-iters 100` (resume-stable optimizer + epsilon kick in here).

### Reset-game confirmation (PR pending — this branch)
- Branch: `claude/reset-confirm-bishop-rationale`. PR not yet opened at the time of this writing — open at end of session.
- Problem: pressing 'R' immediately reset the in-progress game — user lost games to accidental keystrokes.
- Fix: 'R' now opens a confirmation overlay. Y/Enter confirms the reset; N/Esc cancels. While the overlay is up, `Game.is_any_menu_open()` is True, so the main loop gates other interactions exactly like the mode/promo menus.
- New `Game.reset_confirm_pending: bool` flag (default False) + `Game.show_reset_confirm(surface)` render method. Hooked into the main render order between `show_winner` and the next frame.
- Tests in `tests/test_reset_confirm.py` (5 tests, all pass): flag default, gating via `is_any_menu_open`, `reset()` clears the flag, overlay no-op when not pending, overlay visibly draws when pending. Pygame headless via SDL dummy drivers.
- Files touched: `src/game.py`, `src/main.py`, `tests/test_reset_confirm.py`.

### Bishop teleport-safety rationale added to elaborated rulebook
- Added to `docs/RULEBOOK_v2_elaborated.md` two new subsections under "Bishop":
  1. **"Why teleport-safety reads move *or* capture (design rationale)"** — frames the broad rule as a single principle ("the bishop hides on squares no enemy can directly reach this turn") rather than capture-safety + pawn exception. The pawn-sideways block is the rule working as intended — sideways-adjacent to a pawn is reachable, so it's not hidden ground. Reinforces the bishop's **rear-line sniper / overwatch** identity in deliberate contrast with the knight's overt cavalry infiltration. The bishop only exposes itself when (a) it captures (safety-check ignored on the capturing teleport — the sniper reveals position by firing) or (b) it's pinned by an enemy bishop and chooses to break cover.
  2. **"Why enemy bishops (and queens-as-bishop) are excluded — destination vs. source"** — distinguishes destination-based threats (knight jump-capture; depends on the square X itself, so INCLUDED in safety check) from source-based threats (enemy bishop reactive capture; depends on where the bishop came from, not on X, so EXCLUDED). Boulder excluded for the same reason (no proactive capture range). Plus: the exclusion is what makes mutual bishop pins / standoffs possible and what keeps a pinned bishop's agency (it may still choose to move and accept the reactive shot, rather than being mechanically locked).
- This is a **clarification / "keep and articulate"** change — the implemented behavior already matches. No code change. The concise `RULEBOOK_v2.md` is intentionally unchanged (the "why" lives in the elaborated copy by design — split established in PR #80).
- This decision came out of a long side-chat where the user weighed broad ("move + capture") vs narrow ("capture only") teleport-safety. **Final user lean: REAR-LINE SNIPER (broad rule, keep current).** Direct quote from the user that grounds it: *"The bishop essentially 'hides' itself from enemies - it doesn't want to be easily seen or exposed, like an assassin. It hides out of enemy sight and strikes when they least expect it, punishing their movement when they are least attentive."*

### Bishop strategic-strength notes (from same side-chat — read before any tiny-endgame work)
- This variant's R / N / B are MUCH closer in value than standard chess (consistent with 1-unit-each tiny-endgame valuation):
  - Rook: nerfed vs standard (1-step + 90° + sweep, not unlimited single-axis). Proactive captures, forking, more blockable.
  - Knight: buffed vs standard (24 squares of influence = 16 movement + 8 jump-capture, plus reactive jump-capture + supported invulnerability).
  - Bishop: midgame situationally weaker (reactive-only capture — depends on opponent cooperating), endgame strong (global teleport + the key piece for leashing an enemy queen-as-bishop; 0-bishop endgames like 2R+N / 2N+R were exactly the hardest tiny-endgame compositions).
- Rough parity in aggregate (R ≈ N ≈ B) but DIFFERENT shapes: rook = direct firepower, knight = area control + dual capture, bishop = positional control + endgame mobility.
- Future work flagged for after training matures: build an endgame-matchup harness (K+R vs K+B, K+N vs K+B, etc.) using the trained checkpoints + `tools/compare_models.py` style code to get empirical relative-value numbers.

### Roadmap-aware reading order for next session
1. This handoff file (top to bottom).
2. `RULEBOOK_v2.md` (concise, current rules).
3. `docs/key-rule-differences.md` (cheat sheet).
4. `docs/RULEBOOK_v2_elaborated.md` — has the new bishop rationale.
5. `git log --oneline -20` for recent design context.

## UPDATE (2026-05-29 — second update of the same calendar day)

### Training progress at this update
- **iter 58/75 complete.** Latest iter 58: W=49 B=51 avg_len=152 loss=0.0479. Training/caffeinate both alive (PID 68135 ELAPSED 2d 17h; PID 25876 caffeinate ELAPSED ~17h). Game lengths continue to shorten (172 → 152), still 0 draws / 0 repetitions.

### Easy AI cap raised from 50 → 75 (`_AI_DIFFICULTY` in src/game.py)
- User played Easy at iter 50, found it still too weak. Bumped target to 75 (still 'capped' mode — auto-tracks the strongest available checkpoint up to the cap). Once `model_iter_0075.pt` lands, Easy and Medium will resolve to the SAME checkpoint (Medium is exact-75). User accepts this and will re-tune Easy downward if it's then too strong after observing it — likely by introducing a temperature / blunder-rate knob rather than another iteration step.
- The `_AI_DIFFICULTY` literal in game.py now carries a comment explaining the design (capped vs exact + the iter-75 overlap caveat).

### Reset-confirm overlay — bugfix + scope tightening
The first-cut reset-confirm dispatch (PR #89) lived at the BOTTOM of the KEYDOWN handler and was being shadowed:
- **Esc** was eaten by the jump-capture / mode-menu close branch at the top (it `continue`s).
- **Y** was eaten by the redo branch (it `continue`s and treats Y as "redo a turn").
- **N** and **Enter** had no earlier handlers → they fell through and worked.

Fix moves the entire reset-confirm intercept to the TOP of KEYDOWN. While the overlay is up only a tight whitelist passes:
- **Y / Enter** → confirm reset.
- **N / Esc / R** → cancel. (User asked for "press R again to cancel" — natural toggle.)
- **T** → theme change passes through (viewing pref).
- **F** → flip board passes through (viewing pref).
- **All other keys** (U undo, Y-as-redo, M mode-menu, mouse drags via the implicit `is_any_menu_open`-based guarding) → suppressed.

This satisfies the user's spec: "undo/redo and game mode selection should be disabled. Theme and flip board can still be enabled. Y and Esc should work. Press R again cancels."

The R handler at the bottom of KEYDOWN now only OPENS the prompt — it does not handle the close path (that moved to the top intercept).

### Boulder exclusion rationale corrected in elaborated rulebook
User flagged that the previous wording ("boulder is excluded because it has no proactive capture range") was the wrong reason. Correct rationale: **the boulder is treated as a friendly piece for almost every rule purpose**, so it doesn't enter the *enemy-reach* check at all. The cooldown is incidental.

For completeness: even hypothetically treating the boulder as an enemy here, the bishop can never be CAPTURED by the boulder (boulder captures pawns only). So the bishop's restriction against the boulder would reduce to a "move-but-not-capture" reachability block (analogous to the pawn-sideways case) — but this hypothetical doesn't fire because friendly-piece treatment removes the boulder entirely.

This is text-only in `docs/RULEBOOK_v2_elaborated.md`; no code change.

### Branch
`claude/reset-confirm-bishop-rationale` (this branch) — open PR after committing.
PR #89 (the earlier reset-confirm + bishop-rationale first cut) is already merged. This new commit goes on a fresh branch since #89's branch is deleted.
