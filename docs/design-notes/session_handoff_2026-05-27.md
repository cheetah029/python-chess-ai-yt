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

## What the user keeps reminding you

- "honest" / "honest reassessment" is a tell that you're about to be wrong. The user calls this out. Verify EVERYTHING carefully.
- Don't randomly pick any sub-choices — every full Turn must be a single distinct option, evaluated as such. (PR #86 nailed this; do NOT regress.)
- Work directly on the main repo at `/Users/ag/Code/python-chess-ai-yt/`. Feature branches OK; do NOT use worktrees.
- Mirror memory files to `docs/design-notes/` whenever you change them, and commit.
