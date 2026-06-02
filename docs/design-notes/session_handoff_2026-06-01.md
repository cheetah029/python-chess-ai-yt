---
name: Session handoff (2026-06-01)
description: Active project state at end of multi-session GGP + training arc. Read FIRST when resuming. Training PID 33597 still running iter 139/500 → 500 under --workers 4.
metadata:
  node_type: memory
  type: project
  originSessionId: e3b1db7b-ec7f-4a43-9b69-568c3971b17d
---

# Session handoff — 2026-06-01

Active training process is alive. GGP work has progressed through multiple major milestones since the 2026-05-27 handoff. This file captures the active state for the NEXT session. Read `session_handoff_2026-05-27.md` for the earlier arc; this file picks up from there.

## Active processes (alive at time of writing)

- **Training PID 33597** (`python3 src/trainer.py --workers 4 --iterations 408 --resume model_iter_0092.pt ...`) — running since 2026-05-31 ~4:45pm. ELAPSED ~1d 1h 46m. At iter 139/500.
- **caffeinate PID 33621** (`caffeinate -d -i -s -w 33597`) — blocking system + display sleep until training exits.
- **4 worker processes** spawned via multiprocessing.Pool (spawn context) for parallel self-play.

## Training progress + current per-iter timing

- **iter 139/500 complete**. Latest iter 139: W=55 B=45, avg_len=222, loss=0.0419, play_time=334s, train_time=2053s.
- **Per-iter wall-clock: ~33-40 min**. Play dropped from 553s → 334s (parallel workers, ~40% reduction); train rose from 1449s → 2053s (workers + DataLoader contention). Total marginally similar but with much smaller variance in self-play time.
- **47 iterations completed since the resume** (iter 93 onward).
- 0 draws across all 4700+ games. Game lengths trending DOWN (network plays more decisively as epsilon decays from 0.85 toward 0.1).
- Will reach iter 500 at ~33 min/iter × 361 remaining = ~8 days. Worth re-evaluating around iter 250 (mid-training) for quality stabilization.

## Difficulty bumps (2026-06-01)

User raised Easy + Medium caps in `Game._AI_DIFFICULTY`:
- **Easy**: target 200 (was 100), mode 'capped'
- **Medium**: target 300 (was 150), mode 'capped'
- **Hard**: target 500, mode 'capped' (unchanged)

All three auto-track the latest available checkpoint up to their cap. Once iter 200 lands, Easy upgrades; once iter 300 lands, Medium upgrades.

## Speedups landed for the resume

All zero-quality-loss optimizations now active in the running training:

| PR | Optimization |
|---|---|
| #107 | `--workers N` parallel self-play (running with N=4) |
| #109 | DataLoader: `num_workers=2` + `pin_memory=True` + `persistent_workers=True` |
| #109 | `torch.inference_mode()` instead of `no_grad()` |
| #110 | `optimizer.zero_grad(set_to_none=True)` |
| #110 | Pre-create `nn.MSELoss()` once per epoch (was per batch) |
| #110 | `non_blocking=True` on `.to(device)` transfers |

## GGP — current state of the art

### Skeleton (`src/ggp/`)
- `parser.py` — S-expression / GDL parser
- `kb.py` — KnowledgeBase (facts + rules indexed by predicate)
- `resolver.py` — Backward-chaining query with:
  - Unification + occurs check
  - Variable renaming per rule invocation
  - Builtins: `not`, `or`, `and`, `distinct`, `=`
  - Cycle detection via `_cycle_key` (collapses vars to `?`)
  - Public `query()` dedups output bindings
  - **Critical fix: `distinct` now FAILS on unbound operands** (was vacuously succeeding pre-PR #106)
- `game.py` — `GGPGame` state machine + `RandomGGPPlayer` + `play_game`
- `mcts.py` — `MCTSPlayer` (UCB1 + lazy expansion + uniform rollouts)
- `cross_validation.py` — `board_to_gdl_facts` + `turn_to_gdl_move` + `compare_legal_moves`

### End-to-end validation
- **Step 1** (kings+queens): 10 white init moves ✓
- **Step 2** (+pawns, +promotion): 12 white init moves ✓
- **Step 3** (+rook 2-segment): 12 white init moves ✓
- **Step 4** (+knight radius-2): 20 white init moves ✓
- **Step 5** (+bishop teleport): 66 white init moves ✓ — found + fixed scaffold bug
- **Step 6** (+boulder): 66 white init moves ✓ — found + fixed boulder persistence bug
- **Step 7** (queen actions, via integrated.gdl): ≥60 moves ✓
- **Steps 8-11**: smoke-tested via integrated.gdl

### Goal 4 milestone: cross-validation at init
**At init position: engine 71 = GGP 71 = common 71, 0 discrepancies**. The GDL fragments 1-7 faithfully encode v2's full legal-move set at the standard starting state. Mid-game shows 2-3 move diffs per position (gap dashboard in `tests/test_ggp_cross_validation_midgame.py`).

### Bugs surfaced via end-to-end GGP testing
1. Step 5 GDL: leftover scaffold rule allowed any occupied cell as bishop destination — fixed
2. Step 6 GDL: `(boulder_at intersection)` not persisted after first turn — fixed
3. Resolver: `distinct` silently succeeded on unbound operands — fixed
4. Step 6 GDL: boulder cell persisted even when king captured it — fixed
5. Step 7 GDL: transform rule body order had `distinct ?nf base` before `allowed_form` bound `?nf` — fixed
6. Step 7 GDL: `captured_friendly` was placeholder, transformation never unlocked — encoded
7. Step 7 GDL: queen-as-bishop teleport was sketch-only — encoded

## Repetition rule bugs (also fixed earlier this arc, pre-GGP audit)

Two real bugs in `Board.would_cause_repetition`:
1. Didn't simulate `moved_by_queen=True` on manipulated piece (PR #103)
2. Didn't update `last_move` + `last_move_turn_number` + `turn_number` during simulation; derived hash flags consulted stale last_move (PR #104) — this was the actual cause of the user's "queens bouncing forever" report

## Outstanding GDL audit gaps (deferred, see `docs/gdl_audit_against_rulebook.md`)

| Gap | Status |
|---|---|
| Invulnerability blocks captures by all attackers | ⚠️ Only step 8's KING rule patched; queen/rook/knight/pawn/bishop still missing |
| Pawn promotion form choice | ⚠️ Always to base queen; rulebook says player chooses |
| Bishop manipulation | ⚠️ Sketched only |
| Manipulation freeze "next OWN turn" timing | ⚠️ Cleared by absence; not strictly per-turn-counted |

## Continuous-GGP plan when next session resumes

1. **Address deferred audit gaps** (invuln on non-king captures is highest priority — requires editing each step file)
2. **Mid-game cross-validation debug** — investigate the 2-3 move diffs in `test_ggp_cross_validation_midgame.py`; likely from `spatial_move_last_turn` derived-flag drift
3. **NN-guided MCTS** — replace random rollouts with trained ValueNetwork evaluations
4. **GGP for other games** — proof-of-concept by loading a Tic-Tac-Toe or Connect Four GDL into our same engine (demonstrates the "G" in GGP for ISEF)
5. **Cost-curve experiment design** — capstone ISEF measurement: rule changes vs GGP-edit-cost vs NN-retraining-cost

## PRs from this arc (#100-#112)

- #100: Integrated GDL + GGP skeleton + step-1 validation
- #101: Fix CvC view-pref pause (inline re-render)
- #102: GGP Game class + difficulty bumps + 6000x resolver speedup (cycle detection)
- #103: Fix repetition manipulation bug + GGP step-2 validation
- #104: Fix repetition last_move/turn_number bug (the user's "queens bouncing forever" root cause)
- #105: R3 rulebook explanation + GGP steps 3+4+5 + step-5 GDL bug fix
- #106: GGP steps 6+7 + step-6 GDL bug fix + resolver distinct fix
- #107: Parallel self-play training + GGP steps 8-11 sanity tests
- #108: GDL audit doc against rulebook
- #109: captured_friendly + queen-as-bishop + more training speedups
- #110: Step-6 boulder fix + MCTS player + final training speedups
- #111: Cross-validation harness — 71/71 init parity (Goal 4 milestone)
- #112: Extended 20-ply mid-game cross-validation

## Test counts
- **549+ focused tests across 44+ files; all pass** at end of arc
- All GGP tests run in ~30s total

## Memory mirror reminder
Per the rule: when memory files change, mirror to `docs/design-notes/` in the repo.

## Restart command (if training process dies)

```bash
nohup python3 src/trainer.py --workers 4 \
  --iterations <remaining> \
  --resume models/variant_freeze_v3/model_iter_<latest>.pt \
  --epsilon-decay-iters 500 --decisive-games 100 --max-turns 1500 \
  --epochs 10 --batch-size 256 --channels 128 --res-blocks 6 \
  --fc-size 256 --lr 0.001 --manipulation-mode freeze \
  --save-dir models/variant_freeze_v3/ \
  >> models/variant_freeze_v3/training.log 2>&1 &
disown
TRAIN_PID=$(pgrep -f "trainer.py.*--workers 4")
caffeinate -d -i -s -w $TRAIN_PID &
disown
```

(Set `<remaining>` to 500 - current_iter.)
