# Agent player versions — V0 (random) to now

Issue #281. One numbering for every build of the **general game player**
(the GGP / LGREF agent), so that experiment tables, commit messages and
the paper can say "V4" and mean one thing.

**How the numbers are assigned.** A **major version** is a change in *how
the player decides* — random, then rollouts, then a hand-written
evaluation, then a learned one, then a learned one searched, then one
whose features come from the GDL alone. A **sub-version** is anything
smaller: a bug fix, a speed-up, a new feature set, a retrained weight
file. Major versions are *families*, so their dates can overlap: the
mobility agent (V2.0) predates the last MCTS changes (V1.2–V1.4).

**Reverted and withdrawn builds keep their number** and are marked. A
history with the failures removed cannot explain why the survivors look
the way they do, and every one of them is a commit someone could check
out.

**Every SHA below was checked against `git log`** on 2026-10-26. Dates
are the commit dates.

**Not in this numbering:** the AlphaZero-style neural player
(`src/encoding.py`, `src/network.py`, `src/trainer.py` `NeuralPlayer`;
6833a4c, 8f86185, 3ce1e41; played as `--ai-agent easy|medium|hard`). It
reads a 21-channel 8×8 Royal Chess tensor, so it is a Royal Chess
program, not a general game player. If it ever needs a label, call it
**NN-1**.

## Two meanings of "general"

| Tag | Meaning |
|---|---|
| **GDL** | Plays from a GDL file through `GGPGame` — needs nothing but the rules. |
| **protocol** | The agent code touches only the game protocol (`get_all_legal_turns`, `execute_turn`, `winner`), but Royal Chess runs on the fast Python engine and the **features** are hand-written per game (`features.royal_chess`, `features.mnk`). |
| **game-specific** | Assumes one game's concepts; crashes or is meaningless elsewhere. |

## Summary — major versions only

The **representative** of each major version is its **latest
sub-version**. These are the columns of the experiment tables in
[`docs/experiments/version-win-rates.md`](experiments/version-win-rates.md).

| Version | Representative | How it chooses a move | General? | Run it today |
|---|---|---|---|---|
| **V0** | V0.1 (3ce1e41) | uniform random legal move | GDL | `--ai-agent random`; `play_mnk --o random`; `RandomGGPPlayer` |
| **V1** | V1.4 (96dfbd8) | MCTS, UCB1, rollouts to the end (capture-preferring, optional RAVE/MAST), fast copy | protocol (V1.0 is GDL) | `--ai-agent mcts` / `mcts-ggp` |
| **V2** | V2.2 (dcee4b4) | alpha-beta over a **hand-specified** evaluation | protocol | `generic.GenericPlayer` (library only) |
| **V3** | V3.1 (76634da) | **TD(0)-learned** linear evaluation, one ply | protocol | `play_mnk --o td1` (current features); exact build needs `git checkout 76634da` |
| **V4** | V4.15 (6307d97) | TD-learned evaluation searched by the shared alpha-beta `Searcher` | protocol | `--ai-agent td` (Royal Chess, depth 3); `play_mnk --o td` |
| **V5** | V5.1 (70c2044) | the V4 learner and search, with **features named from the GDL's own fluents** | GDL | `lgref.experiments.gdl.load(path)` + `bootstrap.run` (library only, no CLI) |

V4 and V5 share the learner and the search; V5 differs only in where its
features come from. It is a major version because it is the first player
that needs **nothing but the rules** — the property the project claims.

**Two approved builds** are recorded in `lgref/weights/APPROVED.md`.
Every later version must be strictly better than both:

- **Royal Chess: V4.7** (09cb887, approved 2026-10-20, re-confirmed 2026-10-22).
- **m,n,k: V4.11** (b0db7da, approved 2026-10-22).

---

## V0 — uniform random

| | Date | SHA | What |
|---|---|---|---|
| **V0.0** | 2026-04-07 | b1de925 | `src/players.py` `RandomPlayer`, for the Python engine only. |
| **V0.1** | 2026-05-31 | 3ce1e41 | `src/ggp/game.py` `RandomGGPPlayer`. Seedable, reads any GDL. **Representative.** |

The baseline of every table. Its win rate against itself is ~50% only in a
seat-balanced match (see the protocol doc). Within one seat it is the
game's first-player bias, which is the number worth recording.

## V1 — Monte Carlo tree search with rollouts

| | Date | SHA | What changed |
|---|---|---|---|
| **V1.0** | 2026-05-31 | 4ebde61 | `src/ggp/mcts.py` `MCTSPlayer`: UCB1, lazy expansion, 200 rollouts, 80-ply cap. Plays from GDL. No strength recorded; about 35× slower than the engine, so impractical on Royal Chess. |
| **V1.1** | 2026-09-21 | 6662ef3 | `lgref/experiments/mcts.py` on the fast engine, cross-checked by `minimax.MonteCarloMinimaxPlayer`. A 20–50-ply rollout cap lost to random (0 of 32); at a cap of 200 it scored **0.90 vs random**. On tic-tac-toe vs exact play, 25 sims gave **84%** optimal and 200 sims **89%**, against 55% for random (a64718e). |
| **V1.2** | 2026-09-27 | 4f2fc57, b3f5aa0 | Capture-preferring playouts, whose objective is the win condition. 6.8× cheaper, and censoring fell from ⅓ to 0. On tic-tac-toe, 200 sims gave 0.867 and 800 sims 0.967. Became the configured run agent. |
| **V1.3** | 2026-10-10 | 238e243 | RAVE and MAST options. At branching 12 and 160 sims, optimal play rose from 73.4% to **85.9%**. |
| **V1.4** | 2026-10-13 | 96dfbd8 | Fast copy (pickle instead of deepcopy): the same tree at about 4× the simulations per second. **Representative.** On Royal Chess, MCTS-200 hangs material 42.5% of the time against random's 50%, which is **not distinguishable**. |

## V2 — search over a hand-specified evaluation

| | Date | SHA | What changed |
|---|---|---|---|
| **V2.0** | 2026-09-23 | 2985409 | `mobility.MobilityPlayer`: one ply, maximise own mobility. 12/12 vs random, 0.725 on tic-tac-toe. **Withdrawn as biased** (4f2fc57, b3f5aa0); the pre-flight refuses it. |
| **V2.1** | 2026-10-13 | 96dfbd8 | `strong.StrongPlayer`: alpha-beta at depth 2 with quiescence 2, over **hand-supplied material values**. Hangs material 0/40, but that result is largely circular, and 75% of its self-play moves were ties. **Royal Chess only**; it crashes on m,n,k (dcee4b4). `--ai-agent strong`. |
| **V2.2** | 2026-10-14 | dcee4b4 | `generic.GenericPlayer` (and `BeamPlayer`, 76634da): the same search, with the evaluation rebuilt from the protocol as proximity to the declared loss conditions (mobility, royal count, repetition, distance). Plays any protocol game. **Representative.** The reviewer rejected the premise the next day; it is kept because it is the only V2 that runs on every row of the table. |

## V3 — learned evaluation, one ply

| | Date | SHA | What changed |
|---|---|---|---|
| **V3.0** | 2026-10-14 | 7a55bc2 | `bootstrap.run` and `TDPlayer`: TD(0) from **zero weights**, with online normalisation. On m,n,k it played **49.2%** optimal at zero weights and **88.9%** after learning (chance is 31.9%). |
| **V3.1** | 2026-10-14 | 76634da | Relative quiescence gate, and the collinear `Royal` feature removed. **Representative.** The `archive/2026-10-14_*` weight files no longer load, so the exact build needs `git checkout 76634da`. `play_mnk --o td1` is today's one-ply player over today's features, which is close but not identical. |

## V4 — learned evaluation + alpha-beta `Searcher`

`lgref/experiments/search.py` `Searcher`, with per-game features. The
Royal Chess and m,n,k builds share this code. A sub-version that touched
only one game says so.

| | Date | SHA | Game | What changed |
|---|---|---|---|---|
| **V4.0** | 10-16 | b200394 | both | `Searcher`: iterative deepening, transposition table, killers/history, LMR, captures ordered by learned weights, 2.5 s clock. |
| **V4.1** | 10-16 | b485430 | both | Make/unmake, depth 4, and a **mover-sign bug** fixed. With the bug, depth 3 scored 30.6% on m,n,k; after the fix, depth 2 scored 91.8% and depth 3 89.8%. |
| **V4.2** | 10-16/17 | be22793, 8dccbf0 | Royal | `Attacked`/`Covers` features and one symmetric `Royal` count; fixed depth 3 under a 30 s clock. Ties fell from 93.7% to 1.9% and hangs from 10% to 2.5%. The 18-feature seed-71 weights later called "legacy". |
| **V4.3** | 10-17 | d60adbb | both | Quiescence fixed for every game except the case study. |
| **V4.4** | 10-17 | 535d5f6 | m,n,k | `play_mnk.py`: the same stack on m,n,k, every move graded against exact play. |
| **V4.5** | 10-17 | b29b70a … 2efb26f | Royal | TD-leaf option, presence indicators, then vocabulary churn (82 relational features, then a 25-feature lean set). The five-seed average shipped after winning 18–13. |
| **V4.6** | 10-18 | c112d16 | Royal | Legacy 18-feature seed-71 weights **restored**. |
| **V4.7** | 10-18 | **09cb887** | Royal | Seeds 71 and 601 blended, 19 weights, sha `986895d4b4220c85` (`archive/2026-10-18_09cb8872.json`). Beat the restore 13–6. **APPROVED Royal Chess build.** |
| **V4.8** | 10-18 | f8120ba | Royal | Quiescence and ordering made aware of jump captures (the second capture mechanic). Same weights. |
| **V4.9** | 10-19 | ccdb27c | Royal | Form ablation, which won 18–5 at depth 2. **Reverted** in 762a87f: worse at the played depth 3. |
| **V4.10** | 10-20 | ab06fcc | m,n,k | `Reach:j` on: it fixed the opening coin-flip. **Reverted** in 077fcbf: the midgame was worse (−2.4 tempo over four seeds). |
| **V4.11** | 10-22 | **b0db7da** | m,n,k | Vocabulary `Line:1..k-1`, `Marks` and their `Missing:` halves (10 features on 13×13 k=5, fingerprint `4701b7c3`); depth 3 with a 5 s clock; training rounds 6, games 60, seed 17. On 13×13: opening sharpness 94.8%, midgame forced 91.2%, tempo 72.9%; opening placement 15.5% is the known weakness. **APPROVED m,n,k build.** |
| **V4.12** | 10-24 | 4f1a376 | m,n,k | Tie-break (threat level, then opening prior) inside the player. **Reverted** in 226ff1c: a 20× slowdown that cut the search to depth 1. |
| **V4.13** | 10-24 | d072ecc, 2a6b6b6 | m,n,k | Futility pruning and LMR removed as UNSOUND for a game with no captures, which fixed a mate-in-one blunder. |
| **V4.14** | 10-25 | ff380ed, dc47920, 2c39c4b | both | Move clock removed, so depth no longer depends on machine load (0317e9d: a busy machine had silently got depth 2). m,n,k depth set by board (`DEPTH_BY_CELLS`: 3 at ≤200 cells, else 2). |
| **V4.15** | 10-26 | 6307d97 | Royal | Threat cache (IDENTICAL certificate: same moves, less cost). **Representative, and the current player on both games.** |

**Reproducing an old V4.** Weights alone are not enough, because the
search moved on. `git checkout <sha>` gives the exact build. Copying an
archived weight file over `lgref/weights/td_royal_chess.json` gives the
old weights under today's search, which is a different player.

## V5 — plays from the GDL alone

| | Date | SHA | What changed |
|---|---|---|---|
| **V5.0** | 2026-10-19 | 0327cba | `lgref/experiments/gdl.py`: `GdlGame` adapter, plus `features()` named from the game's own fluents (ownership, presence, magnitude), plus the V4 learner and search. 81% on corridor and 91.7% on nim vs uniform. **Caveat (1a666ef):** a flat all-zero evaluation also scores 81–82%, so these numbers mostly measure the search, and the sign of the learning's contribution is unresolved. |
| **V5.1** | 2026-10-20 | 70c2044 | GDL interpreter 3.5× faster (index narrowing). **Representative.** |

V5 runs Royal Chess only through the GDL interpreter, which costs seconds
per legal-move query. Its Royal Chess cell is therefore expensive to fill
(see the protocol doc).

---

## Adding a version

1. A change to how the player decides (move selection, learner, or
   feature source) is a **major** version. Anything else is a sub-version
   of the current major version.
2. Add a row here **in the same commit** as the change, with its SHA once
   it exists, its game scope, and its evidence.
3. A revert gets a row of its own; the reverted row is marked, not
   deleted.
4. When a major version gets a new latest sub-version, its
   representative changes, and **every table cell in that column that was
   measured on the old representative must be re-run or footnoted**.
