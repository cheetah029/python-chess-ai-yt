# Session Summary: Fine-Tuning and Rule Design

**Date:** 2026-05-06
**Branch:** `claude/sweet-morse`
**Focus:** Fine-tune the original-rules AI with a 1000-turn cap to address endgame weakness, then analyze tiny endgame rule robustness and Freeze vs Freeze+NR variant design.

---

## Starting Point

This session continued from a prior conversation. We had just completed:

- A 50-iteration AI training run with original rules (300-turn training cap)
- Collection of 1000 decisive test games with the trained model
- Strategy analysis revealing 0.20% draw rate (2 draws / 1002 games)
- Identification that all draws were "bishop deadlock" or capture-drought patterns
- Comprehensive test cases for data integrity, draw preservation, and decisive-game collection

The open question was whether the AI's endgame weakness (e.g., failing to convert 4 queens vs 2 pieces into a win in 1000 turns) was caused by the 300-turn training cap limiting endgame learning.

---

## What Was Accomplished

### 1. Diagnosed Root Cause of Endgame Weakness

Confirmed the 300-turn training cap was the primary culprit:

- Average training game length was only 151 turns by iteration 50
- The AI never received reward signals for games beyond 300 turns
- Long endgames were being discarded as draws with empty outcomes during training
- The value network had no training data for the back half of long games, so it produced near-random evaluations there

### 2. Fine-Tuned AI With 1000-Turn Cap

Set up a fine-tuning run that preserved the original model:

- **Resumed from:** `models/original_full/model_final.pt` (50-iter base)
- **Iterations:** 20 additional
- **Max turns:** 1000 (up from 300)
- **Epsilon:** 0.10 → 0.05 (low exploration to refine, not destabilize)
- **Learning rate:** 0.0005 (halved for fine-tuning stability)
- **Architecture:** Same 64ch / 3 res / 128 fc
- **Output:** `models/original_finetuned_1000/` (separate from original)

Training completed in ~28 minutes with **zero draws across all 400 training games**.

### 3. Collected 1000 Test Games With Fine-Tuned Model

Wrote a new collection script (`src/collect_finetuned_data.py`) and ran 10 batches of 100 games each:

- **Total: 1000 decisive games, 0 draws**
- 19 games exceeded 300 turns (max 483) — these would have been potential draws under the original training cap
- Average game length dropped to 131 turns (vs 145 with original model)

### 4. Compared Original vs Fine-Tuned Strategy

| Metric | Original | Fine-tuned |
|---|---|---|
| Draw rate | 0.20% | **0.00%** |
| Win balance | 52/48 | 51.4/48.6 |
| Avg game length | 144.9 | 131.3 |
| #1 King killer | knight (49%) | rook (46%) |
| Winner's king dead | 48.0% | 30.8% |
| Manipulations/game | 6.4 | 3.7 |
| Top manipulation target | pawns | bishops |
| Bishop transforms (% of all) | 11.0% | 21.1% |

Key strategic shifts:

- **Rook surpassed knight as primary king-killer** (more chess-like endgame technique)
- **Less king sacrifice** — fine-tuned AI protects its king as a resource
- **Higher-quality manipulations** — fewer per game but targeting bishops over pawns
- **More bishop transformations** — doubling down on the bishop-rush opening

### 5. Analyzed Tiny Endgame Rule Behavior

The original tiny endgame rule activated in **36 of 1000 fine-tuned games** (3.6%) and resolved every one decisively (avg 16 turns post-activation, range 1-45). The rule worked correctly when given a chance — the original 2 draws were AI training failures, not rule failures.

### 6. Discussed Freeze vs Freeze+NR From Human Player Perspective

Established that the NR (no-repeat) restriction is essential because:

- Without it, the queen player will discover a "pin-and-shuffle" trick that locks down a single enemy piece indefinitely
- Game 2 from the freeze-only data showed an actual 28-turn shuffle of the same bishop
- The opponent has no real counterplay, leading to player frustration
- NR adds minimal cognitive load (one item, one turn back) while preventing the dominant degenerate strategy
- The "feels fair" test clearly favors Freeze+NR

### 7. Designed a Foolproof Tiny Endgame Rule

Identified 7 weaknesses in the current rule and proposed a comprehensive redesign:

**Three activation paths (any triggers it):**

1. ≤4 non-king, non-pawn, non-neutral pieces
2. ≤6 non-king pieces AND no knights or rooks remain (bishop deadlock fix)
3. **N consecutive turns with no captures** (NEW — capture-drought catch-all)

**Persistence model:** Activation is permanent once triggered. Distance counts reset only on captures. Royal queen always counts as "queen" for piece-type checks.

**Backstop:** Hard turn limit as final safety net.

The capture-drought rule (path 3) is the single most valuable addition because it catches the worst-case observed stall (the 14-piece, 542-turn no-capture drift in original Draw 2).

---

## Files Changed This Session

### Created

- `src/collect_finetuned_data.py` — batch collection script for fine-tuned model

### Modified

- `docs/potential-rule-changes.md` — added fine-tuning results to Section 1

### Generated (gitignored)

- `models/original_finetuned_1000/` — fine-tuned model + 20 checkpoints + history
- `data/finetuned_1000_100_games_batch1.json` through `batch10.json` — 1000 test games

### Commits

- `f2fa09a` — "Fine-tune AI with 1000-turn cap, eliminate draws in 1000 test games" (pushed to `claude/sweet-morse`)

---

## Current Project State

**Working:**

- Original-rules AI training pipeline (verified across 50 + 20 iterations)
- 6 manipulation variants implemented (`original`, `freeze`, `exclusion_zone`, `freeze_invulnerable`, `freeze_invulnerable_no_repeat`, `freeze_no_repeat`, `freeze_invulnerable_cooldown`)
- Draw record preservation (separate `*_draws.json` files)
- Decisive-game-count collection (continues until N decisive games rather than N total)
- Comprehensive test suite (489 passing, 3 skipped)

**Preserved (unchanged per user instruction):**

- `RULEBOOK.md` — original rules intact
- Original AI model (`models/original_full/`) untouched
- Existing code paths support `manipulation_mode='original'` as default

**Recommended changes (not yet implemented):**

- Freeze + No-Repeat manipulation variant
- Tiny endgame rule expansion (bishop deadlock fix + capture-drought rule + persistence semantics)

---

## What Is Remaining

### Documentation Updates Needed

1. **Update `docs/potential-rule-changes.md`:**
   - Add the capture-drought rule proposal to Section 1
   - Document the activation/deactivation analysis (Option B: stay active, reset on captures)
   - Update the 7 weaknesses analysis as design rationale
2. **Document the fine-tuning approach** in a new section or training-strategy doc — curriculum training (low cap → high cap fine-tune) is now a validated technique for this game

### Implementation Tasks (When Ready to Finalize)

1. **Implement the foolproof tiny endgame rule:**
   - Add capture-drought activation path (`turns_since_last_capture >= N`)
   - Convert activation to permanent flag (set once, never unset)
   - Reset distance counts on captures only (already partially in place)
   - Verify royal-queen-as-queen invariant across all activation paths
   - Tune the N parameter (initial guess: 30-50 turns)

2. **Implement Freeze+NR variant in RULEBOOK and code:**
   - Update `RULEBOOK.md` with the modified manipulation restrictions
   - Promote `freeze_no_repeat` from variant mode to default behavior (or keep both with `manipulation_mode` flag)
   - Update test expectations
   - Preserve original-rules code path per user's "preserve all versions" instruction

3. **Add new test cases for:**
   - Tiny endgame activation paths (each path independently and combined)
   - Persistence behavior (capture-drought activation in mid-piece-count games)
   - Capture-based distance reset (verify counts don't reset on non-capture moves)
   - Queen-transformation invariance (rule state doesn't change when royal queen transforms)

### Validation Tasks

1. **Retrain and re-test Freeze+NR with deeper training:**
   - The current variant data used only 5 iterations
   - Apply curriculum training (300-cap → 1000-cap fine-tune) like we did for original rules
   - Collect 1000-game sample to confirm trends hold under stronger play
2. **Test capture-drought rule:**
   - Run games with the new rule active
   - Confirm it catches stall scenarios without disrupting normal play
   - Verify N=30/40/50 doesn't kick in during legitimate maneuvering

### Deferred (From Earlier in Project)

- Human vs AI play mode
- UI updates for variant selection
- Production-scale data collection (10,000+ games)
- Possible further AI architecture improvements (more channels, deeper network)

---

## Plan for Next Steps

Suggested order of operations:

### Phase A: Document the Findings (low risk, captures session knowledge)

1. Update `docs/potential-rule-changes.md` with the capture-drought rule and persistence model design
2. Add a brief "training strategy" note documenting curriculum training as the validated approach
3. Commit and push

### Phase B: Implement the Tiny Endgame Improvements (medium risk, well-specified)

1. Create a GitHub issue for the tiny endgame rule expansion
2. Branch from `claude/sweet-morse` (or new branch)
3. Add capture-drought tracking to engine (`turns_since_last_capture`)
4. Add second activation path (no knights/rooks)
5. Convert activation to permanent flag
6. Add tests for each activation path and the persistence behavior
7. Run full test suite + collect a small validation game set
8. PR + merge + close issue

### Phase C: Validate Freeze+NR With Deep Training (medium risk, time-intensive)

1. Apply curriculum training to Freeze+NR variant (50 iters at 300-cap, then 20 at 1000-cap)
2. Collect 1000 decisive games
3. Compare draw rate, balance, manipulation patterns to fine-tuned original model
4. If results hold, proceed to Phase D; otherwise iterate on the variant design

### Phase D: Promote Freeze+NR to Default (high risk, locks in design choice)

1. Update `RULEBOOK.md` with the modified manipulation restrictions
2. Update default `manipulation_mode` in code (preserve original via `--manipulation-mode original`)
3. Update tests
4. Final integration testing with all three improvements active simultaneously (Freeze+NR + bishop deadlock fix + capture-drought rule + persistence)

### Phase E: Production Data Collection (time-intensive, generates final dataset)

1. Train production AI on final ruleset using curriculum training
2. Collect 5,000-10,000 games for final analysis
3. Document final game characteristics
4. Move on to Phase 11 (human vs AI mode, UI, etc.)

---

## Key Insights From This Session

1. **Curriculum training works.** Starting with a fast/short cap and fine-tuning with a longer cap produces stronger AI than either approach alone, at a fraction of the compute cost of training from scratch with the long cap.

2. **AI weakness can mimic rule problems.** The 2 original draws looked like structural deadlocks but were actually AI training gaps. Better training resolved them without any rule changes. Lesson: validate with a strong AI before adding rules to fix weaknesses.

3. **Rule design should assume adversarial play.** The Freeze-only variant is technically functional but contains a degenerate "pin-and-shuffle" strategy that ruins the player experience. NR is a tiny addition that closes the exploit. Design for the worst-case strategy, not the average one.

4. **Persistence beats dynamic state for safety rules.** "Once activated, stays active" is more robust than "activates and deactivates with conditions" because it's immune to gaming via state oscillation. Reset internal counters (distance counts) on genuine progress (captures), but don't reset the activation itself.

5. **Capture-drought is the universal stall detector.** Any stall, regardless of piece count or composition, eventually shows up as "no captures for N turns." This is the cleanest, most general anti-stalemate mechanism.
