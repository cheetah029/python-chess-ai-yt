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
| V6 | V6.0 percept-only: a belief over its view, `Searcher` on each sample | ab792e8 |

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
| **Krieg-TicTacToe** (GDL-II) | The recommended imperfect-information row. It is tic-tac-toe where you do **not** see the opponent's marks and are told only whether your own move succeeded. It is a long-standing GDL-II benchmark game (the Dresden GGP server hosts variants of it). Because it is the 3,3,3 row with only the information changed, the difference between the two rows is the cost of hidden information and nothing else. GDL: `testgames/kriegtictactoe.gdl` (#286). A failed mark uses up the turn, so whose move it is never depends on hidden information. |
| **Kuhn poker** (GDL-II, `testgames/kuhnpoker.gdl`) | The smallest game in which the **opponent** holds hidden information and uses it: three cards, one each, ante 1, one bet. It is solved, so a strategy can be scored exactly and not only by its record (#288). Each player sees its own card and the other's bets; a showdown shows both cards. The cell is the share of hands won; chips and exploitability are reported under Table 7. |
| **Monty Hall** (GDL-II, `testgames/montyhall.gdl`) | A **single-player** game against nature, so it goes in its own table below. It is the sanity check with a known optimum: always switching wins 2/3, never switching 1/3, and a uniform player ½. |

Krieg-TicTacToe could later be scaled to a phantom 5,5,4 for a harder
row. Full Kriegspiel is too large to be a first row.

**An important caveat for the imperfect-information rows.** V1–V5
cannot play them *fairly*:

- They search `GdlGame` itself, whose `state` is the true state, so they
  would see the hidden marks.
- `current_player` names the `random` role at nature's steps. A player
  that searches `GdlGame` therefore treats nature as an opponent.

**What #286 fixed in the host, and what it did not.** `GdlGame` used to
give `random` its *first* legal move whenever it was not the mover, so
the Monty Hall car was always behind door 1. It now draws nature
uniformly from a seed, and `nature_turn()` is the host's draw when
nature is the mover. It also records each role's **view**, meaning its
own moves and `sees` percepts, and `hidden.play` hands a player only
that. A role with several real moves that is not the mover still gets
its first legal move, so a genuinely simultaneous game is still not
supported. Neither test game has one.

**Who is fair here.** V0 is: `hidden.UniformPlayer` chooses uniformly
from the legal moves in its view, which a well-formed GDL-II game makes
knowable (`test_hidden.py` checks that Krieg-TicTacToe is well-formed).
**V6** is the percept-only player (`hidden.DeterminizedPlayer`, #286). It
keeps a belief over the play sequences consistent with its view and
searches each one. V1–V5 stay **†**. Making them fair means wrapping
their search in V6's belief, and the result is V6 with another
evaluation, not V1–V5.

---

## Table 1 — baseline V0 (uniform random) · the primary table

Expected: V0 ≈ 50%, rising to the right.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ | ◊ |
| m,n,k 3,3,3 | | | | | | | ◊ |
| m,n,k 5,5,4 | | | | | | | ◊ |
| m,n,k 13,13,5 | | | | | | | ◊ |
| Nim (GDL) | | | §| § | § | | ◊ |
| Krieg-TicTacToe (GDL-II) | 50.6% [45.7, 55.5] n=400 | † | † | † | † | † | 70.4% [65.7, 74.6] n=400 |
| Kuhn poker (GDL-II) | 50.0% [45.1, 54.9] n=400 | † | † | † | † | † | 61.0% [56.1, 65.7] n=400 |

## Table 2 — baseline V1 (V1.4 MCTS)

Expected: V1 ≈ 50%. Use this table once a version saturates Table 1.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ | ◊ |
| m,n,k 3,3,3 | | | | | | | ◊ |
| m,n,k 5,5,4 | | | | | | | ◊ |
| m,n,k 13,13,5 | | | | | | | ◊ |
| Nim (GDL) | | | § | § | § | | ◊ |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | | † | † | † | † | † | † |

## Table 3 — baseline V2 (V2.2 hand-specified evaluation)

Expected: V2 ≈ 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ | ◊ |
| m,n,k 3,3,3 | | | | | | | ◊ |
| m,n,k 5,5,4 | | | | | | | ◊ |
| m,n,k 13,13,5 | | | | | | | ◊ |
| Nim (GDL) | | | § | § | § | | ◊ |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | | † | † | † | † | † | † |

## Table 4 — baseline V3 (V3.1 TD, one ply)

Expected: V3 ≈ 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ | ◊ |
| m,n,k 3,3,3 | | | | | | | ◊ |
| m,n,k 5,5,4 | | | | | | | ◊ |
| m,n,k 13,13,5 | | | | | | | ◊ |
| Nim (GDL) | | | § | § | § | | ◊ |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | | † | † | † | † | † | † |

## Table 5 — baseline V4 (V4.15, the current player)

Expected: V4 ≈ 50%. This is the table on which a new version has to win.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ | ◊ |
| m,n,k 3,3,3 | | | | | | | ◊ |
| m,n,k 5,5,4 | | | | | | | ◊ |
| m,n,k 13,13,5 | | | | | | | ◊ |
| Nim (GDL) | | | § | § | § | | ◊ |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | | † | † | † | † | † | † |

## Table 6 — baseline V5 (V5.1, GDL-only features)

Expected: V5 ≈ 50%. Comparing V4 against V5 isolates the value of
hand-written features over GDL-derived ones, because the learner and the
search are the same.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Royal Chess | | | | | | ‡ | ◊ |
| m,n,k 3,3,3 | | | | | | | ◊ |
| m,n,k 5,5,4 | | | | | | | ◊ |
| m,n,k 13,13,5 | | | | | | | ◊ |
| Nim (GDL) | | | § | § | § | | ◊ |
| Krieg-TicTacToe (GDL-II) | | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | | † | † | † | † | † | † |

## Table 7 — single-player imperfect information (against nature)

There is no opponent, so the cell is the version's **win rate**. Known
values: optimal (always switch) 66.7%, never switch 33.3%, uniform
random 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|---|
| Monty Hall (GDL-II) | 46.5% [41.7, 51.4] n=400 | † | † | † | † | † | 66.3% [61.5, 70.7] n=400 |

## Kuhn poker in chips, and where V6 breaks (#288)

A share of hands won is the wrong unit for poker: winning one chip
and winning two count the same. Kuhn poker is solved, so V6's
strategy can be read and scored **exactly** instead. The game is worth
**−1/18 ≈ −0.056** chips per hand to player1 at equilibrium, and
+0.056 to player2.

The reference is `lgref/experiments/kuhn.py`. It is hand-written for
this one game, it grades V6, and nothing in V6 reads it. It reads V6's
strategy by showing each of the twelve information sets (a card plus
the betting so far) to 400 freshly seeded V6 players. Two numbers are
needed. Against a fixed equilibrium many strategies earn exactly the
game value, so payoff against Nash can hide a large leak.
**Exploitability** is what a best response to the strategy wins above
the game value; 0 means the strategy is an equilibrium. The Nash
opponent is the α = 1/3 member of player1's family; player2's
equilibrium is unique.

| V6.0 (ab792e8), defaults | as player1 | as player2 |
|---|---|---|
| Chips per hand vs V0, sampled (n=1000 per seat) | +0.316 | +0.229 |
| Chips per hand vs Nash, sampled (n=1000 per seat) | −0.162 | −0.038 |
| Chips per hand vs Nash, exact from its strategy | **−0.153** | **−0.084** |
| Equilibrium value of the seat | −0.056 | +0.056 |
| **Exploitability** (best response's gain over the value) | **0.198** | **0.307** |

What V6 plays, as the probability of the aggressive move (bet, or call
when facing a bet). 0.51 is a tie that V6 breaks with its seeded coin,
read from 400 players.

| Information set | V6 | Equilibrium |
|---|---|---|
| player1 J, open | 0.51 | α (0 to 1/3) |
| player1 Q, open | 1 | 0 |
| player1 K, open | 1 | 3α |
| player1 J, check–bet | 0.51 | 0 |
| player1 Q, check–bet | 1 | α + 1/3 |
| player2 J, after check | 0.51 | 1/3 |
| player2 Q, after check | 1 | 0 |
| player2 K, after check | 0.51 | 1 |
| player2 J, facing bet | 0.51 | 0 |
| player2 Q, facing bet | 1 | 1/3 |

(A king facing a bet always calls, in V6 and at equilibrium.)

**This is V6's limit, not a bug.** It has two causes, and they can be
separated:

1. **Determinization.** Each sample is searched as if both hands were
   face up. Inside a sample a bluff is always called by a better card,
   so a bluff never pays. Calling with a queen is right against every
   card the face-up opponent would bet, so V6 always calls with one. A
   king that has been checked to is indifferent, because a face-up loser
   folds a bet anyway. This is strategy fusion (Frank & Basin 1998).
2. **Win/loss values.** V6 values a finished sample by `GdlGame.winner`,
   so losing one chip and losing two are the same loss. With a jack
   every sample is a loss whatever V6 does, so every jack decision is a
   tie and goes to the coin. That is why V6 "bluffs" half its jacks:
   the coin decides, not a reason.

A **diagnostic** with V6's belief, but with each sample searched to the
end on the goal value, removes cause 2 and keeps cause 1
(`kuhn.goal_searched`; it is not a version and nothing else plays it).
It **never bluffs a jack** in either seat and always calls with a queen.
Its exploitability is **1/9 ≈ 0.111** as player1 and **2/9 ≈ 0.222** as
player2. That is the cost of determinization alone. As player1 it
still earns exactly −1/18 against the Nash opponent, which is the case
where payoff against Nash hides a leak. V6 as shipped adds about 0.09 of
exploitability per seat for cause 2.

Against V0, V6 is ahead: 61.0% of hands and +0.27 chips per hand. Its
leaks only cost it against an opponent that bluffs and calls at the
right rates. ISMCTS (or a search that samples the opponent's hand from
the opponent's own belief) and goal-valued leaves are the known fixes.
Neither is made here.

Command: `python -m lgref.experiments.kuhn 2000 288` (seed 288; games
288–2287 for the sampled rows).

**Cell notes**

- **†** Unfair, not reported. V1–V5 read the true state through
  `GdlGame` (see the caveat above). The fair players on these rows are
  V0 and V6.
- **‡** V5 plays Royal Chess only through the GDL interpreter, at seconds
  per legal-move query. Fill it with a smaller `n` and say so, or mark
  "cost".
- **◊** Not applicable. V6 plays from a GDL-II/III view, and a
  perfect-information game has nothing hidden: its belief would be the
  true state, so it would be a flat depth-2 search and not a version.
  The V4/V5 cells are the ones to read on these rows.
- **† in the V6 column** (Tables 2–6, Krieg-TicTacToe and Kuhn poker): the BASELINE is
  unfair there, not V6. V1–V5 cannot be a fair opponent on this row.
- **§** Nim has no hand-written feature set, so V2's evaluation and
  V3/V4's features do not exist for it. Run V2.2 if its loss-condition
  evaluation can read the GDL game. Otherwise mark these "n/a: no
  extractor"; V5 is that column's GDL equivalent.

---

## Record — one row per measured cell

Fill one row per cell. The tables above are summaries of this.

| Table (baseline) | Game | Version (sub-version, SHA) | W | D | L | Truncated | n | Score | 95% CI | Seat 1st / 2nd | Depth / sims | Seeds | Date | Command |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 (V0) | Krieg-TicTacToe | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 186 | 33 | 181 | 0 | 400 | 50.6% | [45.7, 55.5] | 70.0% / 31.3% | — | match seed 286 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/kriegtictactoe.gdl v0 v0 400 286` |
| 1 (V0) | Krieg-TicTacToe | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 256 | 51 | 93 | 0 | 400 | 70.4% | [65.7, 74.6] | 84.8% / 56.0% | depth 2, 16 particles | match seed 286 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/kriegtictactoe.gdl v6 v0 400 286` |
| 1 (V0) | Kuhn poker | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 55.0% / 45.0% | — | match seed 288 | 2026-10-28 | `python -m lgref.experiments.hidden lgref/identify/testgames/kuhnpoker.gdl v0 v0 400 288` |
| 1 (V0) | Kuhn poker | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 244 | 0 | 156 | 0 | 400 | 61.0% | [56.1, 65.7] | 64.0% / 58.0% | depth 2, 16 particles | match seed 288 | 2026-10-28 | `python -m lgref.experiments.hidden lgref/identify/testgames/kuhnpoker.gdl v6 v0 400 288` |
| 7 (nature) | Monty Hall | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 265 | — | 135 | 0 | 400 | 66.3% | [61.5, 70.7] | — | depth 2, 16 particles | games 10000–10399 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/montyhall.gdl v6 400 10000` |
| 7 (nature) | Monty Hall | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 186 | — | 214 | 0 | 400 | 46.5% | [41.7, 51.4] | — | — | games 10000–10399 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/montyhall.gdl v0 400 10000` |
