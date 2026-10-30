# Agent versions against a fixed baseline — results tables

Issue #282. **The tables are empty on purpose and are to be filled as
results come in.**

- **Rows** are games.
- **Columns** are the agent's major versions, each played by its
  representative sub-version as numbered in
  [`docs/agent-versions.md`](../agent-versions.md) (#281).
- **Cell:** the column version's score against **one fixed baseline**
  opponent per table.

| Column | Plays as | SHA |
|---|---|---|
| V0 | V0.1 uniform random | 3ce1e41 |
| V1 | V1.4 MCTS, capture-preferring rollouts, fast copy | 96dfbd8 |
| V2 | V2.2 alpha-beta over a hand-specified evaluation | dcee4b4 |
| V3 | V3.1 TD-learned evaluation, one ply | 76634da |
| V4 | V4.15 TD evaluation + `Searcher` (current player) | 6307d97 |
| V5 | V5.1 V4's learner and search, features from the GDL alone | 70c2044 |

If a column's representative changes, every cell measured on the old
representative is re-run or footnoted (`agent-versions.md`, "Adding a
version").

---

## Protocol — what one cell means

**Score, not raw wins.** A cell is

    score = (wins + ½·draws) / games

reported as a percentage with its 95% **Wilson** interval and `n`, for
example `71.5% [66.9, 75.7] n=400`. Draws count as half, so that V0
against V0 really is ≈ 50%. With draws excluded, tic-tac-toe between two
perfect players would read as 0%. The record table at the bottom keeps
W / D / L separately, because two cells can score 60% with very
different draw rates.

**Seats are balanced.** Half the games put the column version first and
half put it second, alternating game by game with the same seeds. Every
game here has a first-player advantage; an unbalanced cell measures the
seat, not the player. Record the per-seat score too: V0 against V0 in
one seat is the game's first-player bias, which is worth having.

**Truncated games are not losses.** A game stopped by a ply cap is
recorded as **truncated** and kept out of the score. Its count goes in
the record table, and a cell with more than 5% truncated is footnoted.
This is #260's lesson: a capped game counted as "not a win" manufactured
effects.

**Fixed depth, never a clock.** Search players run at their fixed
played depth (Royal Chess 3, m,n,k by board, from `DEPTH_BY_CELLS`).
Under a wall clock a busy machine silently plays a weaker player
(0317e9d), so cells measured at different times would not be comparable.

**Write down how each cell was made.** Record the SHA, seeds, depth and
command in the record table, so the cell can be re-run.

---

## How many games per cell

The interval on a score near 50% is about ±1.96·√(0.25/n):

| Games per cell | 95% interval at 50% | at 80% | at 95% |
|---:|---:|---:|---:|
| 100 | ±9.8 pts | ±7.8 | ±4.3 |
| 200 | ±6.9 | ±5.5 | ±3.0 |
| **400** | **±4.9** | **±3.9** | **±2.1** |
| 1000 | ±3.1 | ±2.5 | ±1.4 |

To tell two **adjacent columns** apart (two independent cells, two-sided
5% test, 80% power), each cell needs roughly:

| True gap between the two versions | Games per cell |
|---:|---:|
| 15 points (50 → 65) | ~170 |
| 10 points (50 → 60) | ~390 |
| 5 points (50 → 55) | ~1,570 |

**Recommendation:**

- **400 games per cell** as the standard (200 in each seat). That
  resolves a 10-point step between versions, and 10 points is about the
  smallest step worth a major version number.
- **100 games is a pilot, not a result.** Run it first to measure the
  cost per game and to see whether the cell is near 50% or saturated.
- **Where a cell is too expensive for 400**, use a sequential test
  (SPRT on "this version beats the previous one by ≥ 10 points") and stop
  when it decides. Report the `n` it stopped at. Do **not** stop at the
  first time the interval looks good: peeking without a sequential rule
  inflates the false-positive rate.
- **Measured costs that bound this:** on m,n,k the worst single move at
  depth 3 is 1.0 s on 9×9 and 11.4 s on 13×13 (7323e33). So a 13×13 cell
  is hours, not minutes. Measure Royal Chess's cost per game in the pilot
  before committing to `n`.

**Saturation.** Once a version scores more than ~95% against V0, the V0
table can no longer separate it from the next version: both sit at the
ceiling inside the same interval. That is why there is one table per
baseline. Show progress on the V0 table while it has room, then move to
the table whose baseline is the previous strong version.

---

## Which games are the rows

**Perfect information**

| Row | Why it is here |
|---|---|
| **Royal Chess** | The case study. Played on the fast engine, except V5, which only exists through GDL (see the cell notes). |
| **m,n,k 3,3,3** (tic-tac-toe) | Small enough to **solve exactly**, so it is the correctness row: a perfect player never loses, and every move can also be graded against exact play (`strength.exact_accuracy`). It saturates fast, which is expected and is itself a check. |
| **m,n,k 5,5,4** | Mid-size, and the board the depth evidence was measured on (7323e33: depth 1 vs 2 was 0–24, depth 2 vs 3 was 5–11). Cheap enough for 400-game cells. |
| **m,n,k 13,13,5** | The board the **approved** m,n,k build's floor was measured on (V4.11: opening, midgame, tempo). It is the large-branching row, and the expensive one. |
| **Nim** (GDL, `testgames/nim.gdl`) | A game no extractor was written for, with no board and no lines. It is the row that tests the generality claim, because only V0, V1.0 and V5 play it from the rules alone. |

**Which m,n,k?** Use **three**, because they answer different
questions. 3,3,3 asks "is it correct where the answer is known", 5,5,4
asks "does the search get stronger", and 13,13,5 asks "does it scale to
the board the approved player is judged on". If there is budget for only
one, use **13,13,5**: that is where the approved player's strengths and
its known weakness (opening placement, 15.5%) were measured. Leave out
19×19: at depth 3 a single move costs up to 73 s.

**Imperfect information**

| Row | Why it is here |
|---|---|
| **Krieg-TicTacToe** (GDL-II) | The recommended imperfect-information row. It is tic-tac-toe where you do **not** see the opponent's marks and are told only whether your own move succeeded. It is a long-standing GDL-II benchmark game (the Dresden GGP server hosts variants of it). Because it is the 3,3,3 row with only the information changed, the difference between the two rows is the cost of hidden information and nothing else. There is no GDL file for it in the repo yet. |
| **Monty Hall** (GDL-II, `testgames/montyhall.gdl`) | A **single-player** game against nature, so it goes in its own table below. It is the sanity check with a known optimum: always switching wins 2/3, never switching 1/3, and a uniform player ½. |

Krieg-TicTacToe could later be scaled to a phantom 5,5,4 for a harder
row. Full Kriegspiel is too large to be a first row.

**An important caveat for the imperfect-information rows.** V1–V5
cannot yet play them *fairly*:

- `GdlGame` reads the true state, so these players would see the hidden
  marks.
- It treats the `random` role as a player to move, not as nature.
- Its `execute_turn` gives a role with several real moves its first
  legal move when that role is not the mover.

Only V0 is fair here. It uses only its own legal moves, which a
well-formed GDL-II game makes knowable. Leave V1–V5's imperfect-information
cells as **†** until a percept-only player exists: one that samples
states consistent with what it has seen, such as determinization or
ISMCTS. That player would be a new major version, V6. The GDL-III reader
(#280) is a prerequisite: it gives the host the percepts and
indistinguishability that such a player needs.

---

## Table 1 — baseline V0 (uniform random) · the primary table

Expected: V0 ≈ 50%, rising to the right.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ |
| m,n,k 3,3,3 | | | | | | |
| m,n,k 5,5,4 | | | | | | |
| m,n,k 13,13,5 | | | | | | |
| Nim (GDL) | | | §| § | § | |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † |

## Table 2 — baseline V1 (V1.4 MCTS)

Expected: V1 ≈ 50%. Use this table once a version saturates Table 1.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ |
| m,n,k 3,3,3 | | | | | | |
| m,n,k 5,5,4 | | | | | | |
| m,n,k 13,13,5 | | | | | | |
| Nim (GDL) | | | § | § | § | |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † |

## Table 3 — baseline V2 (V2.2 hand-specified evaluation)

Expected: V2 ≈ 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ |
| m,n,k 3,3,3 | | | | | | |
| m,n,k 5,5,4 | | | | | | |
| m,n,k 13,13,5 | | | | | | |
| Nim (GDL) | | | § | § | § | |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † |

## Table 4 — baseline V3 (V3.1 TD, one ply)

Expected: V3 ≈ 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ |
| m,n,k 3,3,3 | | | | | | |
| m,n,k 5,5,4 | | | | | | |
| m,n,k 13,13,5 | | | | | | |
| Nim (GDL) | | | § | § | § | |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † |

## Table 5 — baseline V4 (V4.15, the current player)

Expected: V4 ≈ 50%. This is the table on which a new version has to win.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ |
| m,n,k 3,3,3 | | | | | | |
| m,n,k 5,5,4 | | | | | | |
| m,n,k 13,13,5 | | | | | | |
| Nim (GDL) | | | § | § | § | |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † |

## Table 6 — baseline V5 (V5.1, GDL-only features)

Expected: V5 ≈ 50%. Comparing V4 against V5 isolates the value of
hand-written features over GDL-derived ones, because the learner and the
search are the same.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ |
| m,n,k 3,3,3 | | | | | | |
| m,n,k 5,5,4 | | | | | | |
| m,n,k 13,13,5 | | | | | | |
| Nim (GDL) | | | § | § | § | |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † |

## Table 7 — single-player imperfect information (against nature)

There is no opponent, so the cell is the version's **win rate**. Known
values: optimal (always switch) 66.7%, never switch 33.3%, uniform
random 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| Monty Hall (GDL-II) | | † | † | † | † | † |

**Cell notes**

- **†** Not fair until a percept-only player exists. V1–V5 read the true
  state through `GdlGame` (see the caveat above). Leave blank or mark
  "unfair, not reported".
- **‡** V5 plays Royal Chess only through the GDL interpreter, at seconds
  per legal-move query. Fill it with a smaller `n` and say so, or mark
  "cost".
- **§** Nim has no hand-written feature set, so V2's evaluation and
  V3/V4's features do not exist for it. Run V2.2 if its loss-condition
  evaluation can read the GDL game. Otherwise mark these "n/a: no
  extractor"; V5 is that column's GDL equivalent.

---

## Record — one row per measured cell

Fill one row per cell. The tables above are summaries of this.

| Table (baseline) | Game | Version (sub-version, SHA) | W | D | L | Truncated | n | Score | 95% CI | Seat 1st / 2nd | Depth / sims | Seeds | Date | Command |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | | | |
