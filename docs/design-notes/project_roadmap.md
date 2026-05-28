---
name: project-roadmap-goals-python-chess-ai-yt
description: "High-level goals for the chess-variant project — analysis, human-vs-AI mode, AI training with new rules, and the ambitious GDL/GGP research direction (aimed at ISEF, ROBO category). Read for project direction / \"what are we building toward.\""
metadata: 
  node_type: memory
  type: project
  originSessionId: e3b1db7b-ec7f-4a43-9b69-568c3971b17d
---

# Project roadmap (captured 2026-05-20)

The project is a custom chess VARIANT (see project_chess_variant_overview.md, RULEBOOK_v2.md). Beyond rule design, it is aimed at RESEARCH — notably a future ISEF entry, potentially in the **ROBO (Robotics and Intelligent Machines)** category.

## Current main goals (in order)

### Goal 1 — Finalize the ruleset (incl. the >6 symmetric stall question)
Goal 1 has two parts: (1) confirm the tiny endgame rule's ≤6-non-king scope is sufficient, and (2) the broader ruleset-finalization sweep (rare clarifications/edge cases) so rules don't churn mid-training (Goal 3).
- **STATUS (2026-05-20): part (1) CLOSED — the ≤6 non-king scope is ACCEPTED as SUFFICIENT** (user decision). The rule will NOT be expanded beyond ≤6 non-king. Lean: forceable — the mirror does NOT save the defender (royals fall one at a time; any trade to ≤6 activates the rule), symmetry is breakable (capture-across-center is often available), and the last-royal asymmetry favors the side to move. Documented residual: whether the side-to-move is advantaged in a symmetric rule-active position is a geometry-dependent zugzwang question, not provable by hand (engine impractical); worst case a rare dense-symmetric position is stall-prone but still terminates (slowly) under the repetition rule, and no clean expansion predicate exists. See project_tiny_endgame_status.md "DECISION (2026-05-20)". Re-open only if a concrete stall-prone >6 position is demonstrated.
- **Goal 1 part (2) — DONE (2026-05-22):** the ruleset-finalization sweep is COMPLETE. Swept pawn-capture, manipulation restrictions, boulder, knight-invuln, reactive-capture timing, repetition state, promotion, win-condition/royal-capture. Genuine clarifications were RARE (as expected): boulder counts as a legal turn for the No-Legal-Moves loss (PR #54, +test PR #56); repetition state includes the boulder's cooldown + no-return memory (PR #57). Plus stale-TODO/comment hygiene (PR #54/#55/#56). **GOAL 1 FULLY DONE; rules finalized for training.**

### Goal 2 — New game mode: human vs AI player — DONE (2026-05-22, PR #59; in-UI menu PR #62; undo/redo skip AI PR #64; UX fix PR #63)
Implemented via `src/ai_controller.py` (`AIController`) + in-UI mode menu (M key). The menu picks **side** (white/black) and **opponent** (human/random) independently — see `Game.SIDE_OPTIONS` and `Game.OPPONENT_OPTIONS`. Future Easy/Medium/Hard AI plugs in by appending to `OPPONENT_OPTIONS` and adding a branch in `Game._make_ai_player`. **Design = Option A:** reuse `GameEngine` ONLY to enumerate legal turns; apply via the human UI path; advance with `Game.next_turn()` (single turn-lifecycle authority). Baseline AI = `RandomPlayer`. Undo/redo skips back/forward to the user's previous/next turn in AI mode. Headless tests in `tests/test_ai_controller.py` and `tests/test_mode_selection.py` (28+5 tests).

### Goal 3 — Train AI with the new rules (IN PROGRESS — iter 33/75 as of 2026-05-27 early AM session handoff)

**Status: ACTIVE.** Training process (PID 68135) running in background, resuming from model_iter_0025.pt with --iterations 50. 32 iterations complete with checkpoints saved. 0 repetitions, 0 draws across 3200+ games. Avg game length ~200-225 turns. After current run finishes at iter 75, plan another --resume to reach iter 100 (user's stated goal: ~10,000 games of training).

See `session_handoff_2026-05-27.md` for full state + restart instructions.

The original "READY TO START" guidance below is kept for historical reference:

---

### Goal 3 — Train an AI with the NEW updated game rules (READY TO START — next session)

**Status: ALL PRECONDITIONS MET as of 2026-05-25.** Goal 1 (rules finalization) is fully closed. The ruleset is locked: no pawns + ≤6 non-king + cancel-queens balance (tiny endgame); knight = radius-2 + reactive jump-capture + supported (friendly/boulder) invuln; boulder counts as legal turn for no-legal-moves loss; repetition state hash includes boulder cooldown + no-return memory. Training pipeline verified end-to-end on this ruleset (2026-05-22 dry-run, exit 0).

**Recommended starting command** (for the real training run, NOT a dry-run):
```
python3 src/trainer.py \
  --iterations 50 \
  --decisive-games 100 \
  --max-turns 1500 \
  --epochs 10 \
  --batch-size 256 \
  --channels 128 \
  --res-blocks 6 \
  --fc-size 256 \
  --lr 0.001 \
  --manipulation-mode freeze \
  --save-dir models/variant_freeze_v3/
```

Rationale for the args:
- `--max-turns 1500` — empirically, random self-play at this cap is 100% decisive (vs ~2% at max_turns=120). Avoids the cold-start "all draws" issue.
- `--save-dir models/variant_freeze_v3/` — fresh directory; do NOT reuse existing `models/variant_freeze/` (those models were trained on OLD rules).
- Default hyperparameters (128 channels, 6 res-blocks, 256 fc, 0.001 lr) — these are the trainer's defaults, validated on the prior training runs.

**Caveats:**
- Random cold-start is slow at producing decisive games. Iteration 1 will be the slowest; later iterations speed up as the network learns and produces more decisive play.
- ~1-2 hours per iteration at iteration 1 with the recommended args (dry-run was 406s for 2 decisive games at max_turns=120; scaling to 100 decisive games at max_turns=1500 = much longer, but per-game faster as proportion of decisive games rises).
- Use Apple MPS if available (the dry-run used MPS automatically); CPU fallback works but slower.
- Monitor `training_history.json` in the save-dir for loss curves.

**Data collection scripts** (for later, after training): `collect_variant_data.py`, `collect_finetuned_data.py`, `analyze_variants.py`. Use them to evaluate the trained model.

**Plugging the trained model into Goal 2's UI:** once `models/variant_freeze_v3/model_final.pt` exists, swap RandomPlayer → NeuralPlayer in `Game._make_ai_player` (in src/game.py), adding an 'easy'/'medium'/'hard' branch. Existing infrastructure (engine.py NeuralPlayer-aware) is ready.

**Next session checklist:**
1. Verify on `main` branch, clean, no uncommitted changes.
2. Run `git log --oneline -20` for context on recent design decisions.
3. Read `RULEBOOK_v2.md` + `docs/key-rule-differences.md` to confirm the rules are as expected.
4. Run the training command above (consider `tmux` or `nohup` for long-running session).
5. Monitor progress; expect iteration 1 to be the slowest.

### Goal 4 (ambitious, research) — GDL + GGP
- **GDL (Game Description Language):** formalize the written game rules into a logical/declarative GDL representation. Converts RULEBOOK_v2.md prose into machine-readable formal logic.
- **GGP (General Game Player):** build/use a general game player that takes the GDL as input. A GGP can adapt to rule modifications WITHOUT full re-training each time — a huge advantage given how often this variant's rules change.
- This variant could serve as a **benchmark for GGPs** (it's a novel, non-trivial game with unusual mechanics: reactive captures, manipulation, transformation, boulder, tiny-endgame rule).
- This is the heavy-research direction, aligned with ISEF / ROBO ambitions.

## Sequencing note
Goals 1 → (finalize rules) → 3 (train) is the dependency chain: don't train (Goal 3) until rules are finalized (which Goal 1 + a rules-finalization pass support). Goal 2 (human-vs-AI mode) can proceed in parallel since it doesn't depend on rule finalization (it uses whatever rules + whatever trained/untrained AI exists). Goal 4 (GDL/GGP) is the long-horizon research payoff.

## Rules-finalization checklist (before Goal 3 training)
Resolved recently: repetition-rule invuln cycle (c7e0ffd), tiny endgame redesign (1c7cdec), bishop double-manip reactive capture (9d60689), boulder capture-return (60a2e4d). **(a) Goal 1's >6 stall question — RESOLVED 2026-05-20: ≤6 scope accepted as sufficient (see Goal 1 STATUS above).** **(b) Ruleset sweep — DONE 2026-05-22.** Swept manipulation/reactive-capture timing, repetition state, boulder, knight-invuln, promotion, win-condition/royal-capture. Clarifications were rare (as expected): boulder counts as a legal turn for the No-Legal-Moves loss (PR #54, +test PR #56); repetition state includes the boulder's cooldown + no-return memory (PR #57); plus stale-TODO/comment hygiene (PR #54/#55/#56). RULEBOOK_v2.md authoritative; docs/key-rule-differences.md kept in sync. **CHECKLIST COMPLETE — rules finalized for Goal 3 training.**
