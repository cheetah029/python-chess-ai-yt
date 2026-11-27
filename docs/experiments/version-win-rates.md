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
| V7 | V7.0 V4's player one ply deeper: Royal Chess depth 4, m,n,k `DEPTH_BY_CELLS` + 1 (see ※) | d98c09c |

**Status (2026-11-27):** filling to **n = 100** in every fillable cell
(breadth before depth; see "Measured cost per game"). Cells already
above 100 were measured before that rule and keep their larger `n`.

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

### How the perfect-information cells are played (#349)

The runner is `lgref/experiments/versions.py` (tests:
`lgref/tests/test_versions_match.py`). It adds four rules to the ones
above, each forced by the players being measured:

- **Each version runs at its own commit.** A side of a match is a
  `version_worker.py` process started inside a `git clone --shared`
  checkout of that version's commit, so V4 is V4.15's own search and
  weights, not today's code under an old name. Where a column's
  decision code is byte-identical on today's main, it runs there
  instead, and the record table says so (V1: `mcts.py` has no commit
  since 96dfbd8; V2: `GenericPlayer`, `make_evaluation` and `fastcopy`
  are unchanged since dcee4b4). V3 on m,n,k is `play_mnk --o td1`,
  the run path `agent-versions.md` names, because V3.1 had no m,n,k
  build. Today's engine is the **referee**: it decides legality and
  the result, and every move is sent to both sides as plain data.
- **A random opening per pair of games.** V2–V5 are deterministic, so
  without one every game in a seat would be the same game and a
  400-game cell would be two games repeated. Games `2j` and `2j+1`
  start from the same few uniformly random plies (Royal Chess 4–14, as
  `tools/race_agents.py` does; m,n,k 3,3,3 0–2, 5,5,4 0–4, 13,13,5 0–6;
  Nim 0–1), drawn from the match seed and `j`, and the seats are
  swapped between them. So every opening is played once from each
  side, and the seat split still reads as first-player bias.
- **Diverged games are kept out of the score, like truncated ones.**
  A commit older than a rules fix can disagree with the referee about
  whether a move is legal (Royal Chess: the boulder's diagonal line of
  sight, e50a3a4 and 470273e, postdates V1.4–V3.1; #330 postdates
  every version). The game is then stopped, recorded as diverged with
  the move, and counted in the record table's truncated column.
- **One match fills two cells.** A match between Vi and Vj is the Vi
  cell of Vj's table and the Vj cell of Vi's table, scored from each
  side; the record table lists both rows and marks the second as the
  same games. A diagonal cell (a version against itself) is a real
  match between two copies.
- **Settings per version, fixed:** V1 200 simulations (the budget of
  its recorded evidence, "MCTS-200"), rollout cap 200; V2 depth 2,
  quiescence 2; V3 one ply; V4 depth 3 on Royal Chess (`Game.TD_DEPTH`)
  and `DEPTH_BY_CELLS` on m,n,k; V5 depth 4 on Nim (V5.0's setting) and
  `DEPTH_BY_CELLS` on m,n,k, trained from zero as
  `test_unseen_gdl._train_and_race` trains it. V5 plays m,n,k from a
  generated GDL (`versions.mnk_gdl`), tested to give the same legal
  moves and results as the engine.

**No ply cap on Royal Chess** (reviewer, 2026-11-27). Royal Chess has
no draw: its rules end every game in a win or a loss, and the
repetition rule makes every game finite. A capped game would be an
artefact of the harness, and scoring it as half distorts a cell as much
as leaving it out. So every Royal Chess game runs to its real end, and
its truncated column is expected to stay **0**. A watchdog logs any
game that passes 20,000 plies, so that a bug that loops can be seen; it
never stops a game. Two V0 against V0 games played before this rule had
stopped at ply 1000 (games 22 and 88); they were replayed from the same
seed and opening without the cap, ended by the rules at plies 1,471 and
1,179, and replaced the truncated rows. No other game could have been changed by
the old cap: every one either finished before ply 800, so no search and
no 200-ply rollout reached ply 1000, or involved no player that looks
ahead that far (V0 against V0 up to 887 plies; V3 against V0 at 963,
where V3's one-ply look first reaches ply 1000 at ply 999). Those games
stand unchanged.

**Draws elsewhere are real.** m,n,k, Krieg and the card games have
draws in their rules, and a draw counts as half. m,n,k ends when the
board is full and Nim within five plies, so no cap binds there: on
27 November the logs held 0 truncated games out of 8,400 (3,3,3),
6,290 (5,5,4), 1,131 (13,13,5) and 4,000 (Nim), and the record table's
truncated column checks it for every cell.

In the record table's commands, `v4@<6307d97>` means a `git clone
--shared` of this repository checked out at 6307d97, with the project's
`.venv` linked into it, and the runner run from 591414c or later. Every
player is seeded from the match seed and the game index, and a rerun in
a new process reproduces each game exactly (checked by the tests, and
again in passing: 303 games of the 5,5,4 V1 diagonal were played twice
by accident in separate processes and all 303 agreed).

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

### Measured cost per game (#349)

Wall seconds for one game, both sides included, measured by the runner
on this machine under `nice` while two other tracks shared its ten
cores. `n` is the number of games behind each figure; the range is the
cheapest and dearest of them. A 400-game cell costs `400 x mean`, and
four games run at once.

| Game | Match | n | Mean s/game | Range | 400 games, CPU-hours | on 4 processes |
|---|---|---:|---:|---|---:|---:|
| m,n,k 3,3,3 | any pair without V5 | 400 each | < 0.1 | — | < 0.1 | minutes |
| m,n,k 3,3,3 | V5 against anything | 400 each | 0.8–2.0 | 0.2–3.7 | 0.1–0.2 | minutes |
| m,n,k 5,5,4 | any pair without V5 | 400 each | 0.0–1.5 | 0.0–2.6 | < 0.2 | minutes |
| m,n,k 5,5,4 | V5 vs V0 | 47 | 118 | 20–331 | 13 | 3.3 h |
| Nim | any pair | 400 each | < 0.1 | — | < 0.1 | minutes |
| m,n,k 13,13,5 | V0 vs V0 / V3 vs V0 | 4 | 0.1 / 0.7 | — | < 0.1 | minutes |
| m,n,k 13,13,5 | V4 vs V0 / V1 vs V0 | 4 | 58 / 103 | 42–75 / 62–118 | 6 / 11 | 1.6 h / 2.9 h |
| m,n,k 13,13,5 | V4 vs V1 / V4 vs V3 | 4 | 77 / 89 | 62–103 / 66–120 | 9 / 10 | 2.1 h / 2.5 h |
| m,n,k 13,13,5 | V4 vs V4 / V1 vs V1 | 4 | 134 / 156 | 83–184 / 115–194 | 15 / 17 | 3.7 h / 4.3 h |
| m,n,k 13,13,5 | V2 against anything | 3 moves | **620 s a move** | 595–670 | 1,400–2,800 | **cost** |
| Royal Chess | V0 vs V0 / V3 vs V3 / V3 vs V0 | 4–6 | 3 / 15 / 20 | 1–7 / 14–16 / 1–73 | 0.4 / 1.6 / 2.2 | under 1 h |
| Royal Chess | V4 vs V0 / V1 vs V0 | 4 | 65 / 210 | 19–130 / 149–285 | 7 / 23 | 1.8 h / 5.8 h |
| Royal Chess | V4 vs V1 / V4 vs V3 | 4 | 273 / 361 | 157–369 / 307–469 | 30 / 40 | 7.6 h / 10 h |
| Royal Chess | V1 vs V1 / V3 vs V1 | 3 | 1,220 / 1,414 | 1,176–1,288 / 89–3,893 | 136 / 157 | **34 h / 39 h** |
| Royal Chess | V4 vs V4 | 4 | 1,707 | 329–3,895 | 190 | **47 h** |
| Royal Chess | V2 against anything | 1 move | **over 3,500 s a move** | — | — | **cost** |
| Royal Chess | V7 against the same player at depth 3 (`depth4-race.md`, not this runner) | 40 | 633 CPU-s, about 14 s a move | — | about 70 per cell | about 18 h |
| m,n,k 13,13,5 | V5 (GDL interpreter) | 4 listings | 0.3–0.6 s to list the 166–169 legal moves once; training had not finished after 8 h | — | — | **cost** |
| Royal Chess | V5 (GDL interpreter) | 4 listings | **1.5–1.7 s to list the legal moves once** | — | — | **cost** (‡) |

**What this decides: breadth before depth** (reviewer, 2026-11-27).
Every fillable cell in every table is brought to **n = 100** before any
cell goes further; then every cell to 200, then 300, then 400, and so
on. The doc is published at each level, and every cell carries its own
`n` and interval, so a cell above the current level (the cheap rows
were run straight to 400 before this rule) is simply more precise. A
higher level only extends a cell: the same commit, the same settings
and the same seeding (match seed 282, game index `i`), so games
`0..99` of a 400-game cell are exactly the 100-game cell. The three
dearest Royal Chess cells (V1 vs V1, V3 vs V1, V4 vs V4, 34–47 h each
at 400) climb with the rest. **V2.2 on Royal Chess and on 13,13,5 is
marked "cost".** Its search is full width at depth 2 plus quiescence 2, and its
evaluation lists every legal move at every leaf: one move took 595–670 s
on 13,13,5 (three moves measured), and the first Royal Chess move had
not finished after an hour. At 20 to 40 of its own moves a game (an
assumption, since no game finished), one 13,13,5 game is 3.5 to 7 hours
and a 400-game cell 1,400 to 2,800 CPU-hours. This is a cost, not a
defect: V2.2 was built and measured on boards of tens of moves.

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

**Which Krieg-m,n,k?** **3,3,3** (Krieg-TicTacToe) and **5,5,4**, the
twins of the two smaller m,n,k rows. Add **13,13,5** only once a first
measurement shows it is affordable. The hidden board there is enormous,
and V6 already takes about 18 s per game on 5,5,4.

## Development games and test games

Every change to a player has to be general, so the games are split.
**Development** games are the ones whose results may be looked at while
a player is being changed. **Test** games are never used to tune
anything; they only measure. If a test game's result ever drives a
change, that game becomes a development game, and a fresh test game is
needed. Measuring a version on a test game does not spend it. Changing
the player because of what it showed does.

| | Develop on | Test on (held out) |
|---|---|---|
| **Perfect information** | **Royal Chess** and **m,n,k 3,3,3 / 5,5,4 / 13,13,5**. The players were already built and approved on these, so they cannot be held out. | **Nim** and **corridor** (`testgames/`). Nothing was written for either, and `test_unseen_gdl` already uses them as "a game it was never written for". Later, brand-new held-out games such as Connect Four or Breakthrough. |
| **Imperfect information** | **Kuhn poker**: tiny and exactly solved, so each change is graded precisely in seconds. **Krieg-TicTacToe**: cheap hidden-board play. **Monty Hall**: a quick check that the belief is right. | **Leduc Hold'em**: the same family as Kuhn but bigger, with two rounds, raises and a public card. **Krieg 5,5,4**: the same check for hidden boards. A fix tuned on Kuhn or Krieg-TicTacToe either carries over to these or it does not. |

The references that grade a player (`experiments/kuhn.py`,
`experiments/leduc.py`) are never read by any player. They are not
"development data" either: they say how good a strategy is, not what to
play.

**Imperfect information**

| Row | Why it is here |
|---|---|
| **Krieg-TicTacToe / Krieg-m,n,k 3,3,3** (GDL-II) | The recommended imperfect-information row. It is tic-tac-toe where you do **not** see the opponent's marks and are told only whether your own move succeeded. It is a long-standing GDL-II benchmark game (the Dresden GGP server hosts variants of it). Because it is the 3,3,3 row with only the information changed, the difference between the two rows is the cost of hidden information and nothing else. GDL: `testgames/kriegtictactoe.gdl` (#286). A failed mark uses up the turn, so whose move it is never depends on hidden information. |
| **Krieg 5,5,4** (GDL-II, `testgames/kriegmnk_5_5_4.gdl`) | The hidden-information twin of the m,n,k 5,5,4 row: the same board and the same win condition, with the opponent's marks hidden and only `ok` / `taken` reported (#294). It is generated by `testgames/kriegmnk.py`, which writes Krieg-m,n,k for any board; at 3,3,3 the generated game is tested to play identically to Krieg-TicTacToe. On 3×3 the hidden board has few possibilities, while on 5×5 it has thousands, so this is the row where V6's belief has to estimate rather than enumerate. |
| **Kuhn poker** (GDL-II, `testgames/kuhnpoker.gdl`) | The smallest game in which the **opponent** holds hidden information and uses it: three cards, one each, ante 1, one bet. It is solved, so a strategy can be scored exactly and not only by its record (#288). Each player sees its own card and the other's bets; a showdown shows both cards. The cell is the share of hands won; chips and exploitability are reported under Table 7. |
| **Leduc Hold'em** (GDL-II, `testgames/leducholdem.gdl`) | The standard mid-sized poker benchmark (Southey et al. 2005) and the next size up from Kuhn poker: six cards (two each of J, Q, K), two betting rounds with bets of 2 then 4, at most one bet and one raise per round, and a public card before round 2 that makes pairs (#292). Each player sees its own card's rank, the public card's rank and the other's bets; a showdown shows the other's card. There is no closed-form equilibrium, so one is computed (CFR+). The cell is the share of hands won; chips and exploitability are reported under Table 7. |
| **Monty Hall** (GDL-II, `testgames/montyhall.gdl`) | A **single-player** game against nature, so it goes in its own table below. It is the sanity check with a known optimum: always switching wins 2/3, never switching 1/3, and a uniform player ½. |

Full Kriegspiel is too large to be a first row.

**V6 scores higher on Krieg 5,5,4 than on Krieg-TicTacToe** (84.6%
against 70.4%, both against V0). The seat split differs: on 3×3 V6
scores 84.8% as xplayer but 56.0% as oplayer, while on 5×5 it scores
87.0% and 82.3%. V0 against V0 shows a smaller first-player edge on
5×5 (60.3% as xplayer, against 70.0% on 3×3). Why V6 gains is not yet
established; the row shows that its belief keeps working when it
must sample a hidden board with thousands of possibilities.

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

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess |  |  | cost |  |  | ‡ cost | ◊ |  |
| m,n,k 3,3,3 | 54.9% [50.0, 59.7] n=400 | 94.5% [91.8, 96.3] n=400 | 67.2% [62.5, 71.7] n=400 | 94.8% [92.1, 96.5] n=400 | 95.9% [93.5, 97.4] n=400 | 87.0% [83.3, 89.9] n=400 | ◊ |  |
| m,n,k 5,5,4 | 53.5% [48.6, 58.3] n=400 | 98.4% [96.6, 99.2] n=400 | 76.6% [72.2, 80.5] n=400 | 100.0% [99.0, 100.0] n=400 | 100.0% [99.0, 100.0] n=400 |  | ◊ |  |
| m,n,k 13,13,5 |  |  | cost |  |  | cost | ◊ |  |
| Nim (GDL) | 50.0% [45.1, 54.9] n=400 | 81.2% [77.1, 84.8] n=400 | 46.0% [41.2, 50.9] n=400 | § | § | 82.5% [78.5, 85.9] n=400 | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | 50.6% [45.7, 55.5] n=400 | † | † | † | † | † | 70.4% [65.7, 74.6] n=400 | † |
| Krieg 5,5,4 (GDL-II) | 50.3% [45.4, 55.1] n=400 | † | † | † | † | † | 84.6% [80.8, 87.8] n=400 | † |
| Kuhn poker (GDL-II) | 50.0% [45.1, 54.9] n=400 | † | † | † | † | † | 61.0% [56.1, 65.7] n=400 | † |
| Leduc Hold'em (GDL-II) | 49.0% [44.1, 53.9] n=400 | † | † | † | † | † | 61.3% [56.4, 65.9] n=400 | † |

## Table 2 — baseline V1 (V1.4 MCTS)

Expected: V1 ≈ 50%. Use this table once a version saturates Table 1.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess |  |  | cost |  |  | ‡ cost | ◊ |  |
| m,n,k 3,3,3 | 5.5% [3.7, 8.2] n=400 | 51.0% [46.1, 55.9] n=400 | 31.5% [27.1, 36.2] n=400 | 48.4% [43.5, 53.3] n=400 | 56.9% [52.0, 61.6] n=400 | 42.4% [37.6, 47.3] n=400 | ◊ |  |
| m,n,k 5,5,4 | 1.6% [0.8, 3.4] n=400 | 51.4% [46.5, 56.2] n=400 | 19.9% [16.3, 24.1] n=400 | 86.5% [82.8, 89.5] n=400 | 92.8% [89.8, 94.9] n=400 |  | ◊ |  |
| m,n,k 13,13,5 |  |  | cost |  |  | cost | ◊ |  |
| Nim (GDL) | 18.8% [15.2, 22.9] n=400 | 50.0% [45.1, 54.9] n=400 | 2.8% [1.5, 4.9] n=400 | § | § | 50.0% [45.1, 54.9] n=400 | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | † | † | † | † | † | † | † | † |
| Krieg 5,5,4 (GDL-II) | † | † | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | † | † | † | † | † | † | † | † |
| Leduc Hold'em (GDL-II) | † | † | † | † | † | † | † | † |

## Table 3 — baseline V2 (V2.2 hand-specified evaluation)

Expected: V2 ≈ 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess | cost | cost | cost | cost | cost | ‡ cost | ◊ | cost |
| m,n,k 3,3,3 | 32.8% [28.3, 37.5] n=400 | 68.5% [63.8, 72.9] n=400 | 50.0% [45.1, 54.9] n=400 | 54.4% [49.5, 59.2] n=400 | 65.1% [60.3, 69.6] n=400 | 75.4% [70.9, 79.3] n=400 | ◊ |  |
| m,n,k 5,5,4 | 23.4% [19.5, 27.8] n=400 | 80.1% [75.9, 83.7] n=400 | 50.0% [45.1, 54.9] n=400 | 89.1% [85.7, 91.8] n=400 | 99.1% [97.6, 99.7] n=400 |  | ◊ |  |
| m,n,k 13,13,5 | cost | cost | cost | cost | cost | cost | ◊ | cost |
| Nim (GDL) | 54.0% [49.1, 58.8] n=400 | 97.2% [95.1, 98.5] n=400 | 50.0% [45.1, 54.9] n=400 | § | § | 89.5% [86.1, 92.1] n=400 | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | † | † | † | † | † | † | † | † |
| Krieg 5,5,4 (GDL-II) | † | † | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | † | † | † | † | † | † | † | † |
| Leduc Hold'em (GDL-II) | † | † | † | † | † | † | † | † |

## Table 4 — baseline V3 (V3.1 TD, one ply)

Expected: V3 ≈ 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess |  |  | cost |  |  | ‡ cost | ◊ |  |
| m,n,k 3,3,3 | 5.2% [3.5, 7.9] n=400 | 51.6% [46.7, 56.5] n=400 | 45.6% [40.8, 50.5] n=400 | 50.0% [45.1, 54.9] n=400 | 60.4% [55.5, 65.0] n=400 | 42.9% [38.1, 47.8] n=400 | ◊ |  |
| m,n,k 5,5,4 | 0.0% [0.0, 1.0] n=400 | 13.5% [10.5, 17.2] n=400 | 10.9% [8.2, 14.3] n=400 | 50.0% [45.1, 54.9] n=400 | 59.0% [54.1, 63.7] n=400 |  | ◊ |  |
| m,n,k 13,13,5 |  |  | cost |  |  | cost | ◊ |  |
| Nim (GDL) | § | § | § | § | § | § | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | † | † | † | † | † | † | † | † |
| Krieg 5,5,4 (GDL-II) | † | † | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | † | † | † | † | † | † | † | † |
| Leduc Hold'em (GDL-II) | † | † | † | † | † | † | † | † |

## Table 5 — baseline V4 (V4.15)

Expected: V4 ≈ 50%. V7 is V4 one ply deeper, so its column here is the
direct comparison; Table 8 has the same games from V7's side.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess |  |  | cost |  |  | ‡ cost | ◊ |  |
| m,n,k 3,3,3 | 4.1% [2.6, 6.5] n=400 | 43.1% [38.4, 48.0] n=400 | 34.9% [30.4, 39.7] n=400 | 39.6% [35.0, 44.5] n=400 | 50.0% [45.1, 54.9] n=400 | 34.5% [30.0, 39.3] n=400 | ◊ |  |
| m,n,k 5,5,4 | 0.0% [0.0, 1.0] n=400 | 7.3% [5.1, 10.2] n=400 | 0.9% [0.3, 2.4] n=400 | 41.0% [36.3, 45.9] n=400 | 50.0% [45.1, 54.9] n=400 |  | ◊ |  |
| m,n,k 13,13,5 |  |  | cost |  |  | cost | ◊ |  |
| Nim (GDL) | § | § | § | § | § | § | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | † | † | † | † | † | † | † | † |
| Krieg 5,5,4 (GDL-II) | † | † | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | † | † | † | † | † | † | † | † |
| Leduc Hold'em (GDL-II) | † | † | † | † | † | † | † | † |

## Table 6 — baseline V5 (V5.1, GDL-only features)

Expected: V5 ≈ 50%. Comparing V4 against V5 isolates the value of
hand-written features over GDL-derived ones, because the learner and the
search are the same.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess | ‡ cost | ‡ cost | ‡ cost | ‡ cost | ‡ cost | ‡ cost | ◊ | ‡ cost |
| m,n,k 3,3,3 | 13.0% [10.1, 16.7] n=400 | 57.6% [52.7, 62.4] n=400 | 24.6% [20.7, 29.1] n=400 | 57.1% [52.2, 61.9] n=400 | 65.5% [60.7, 70.0] n=400 | 50.0% [45.1, 54.9] n=400 | ◊ |  |
| m,n,k 5,5,4 |  |  |  |  |  |  | ◊ |  |
| m,n,k 13,13,5 | cost | cost | cost | cost | cost | cost | ◊ | cost |
| Nim (GDL) | 17.5% [14.1, 21.5] n=400 | 50.0% [45.1, 54.9] n=400 | 10.5% [7.9, 13.9] n=400 | § | § | 50.0% [45.1, 54.9] n=400 | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | † | † | † | † | † | † | † | † |
| Krieg 5,5,4 (GDL-II) | † | † | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | † | † | † | † | † | † | † | † |
| Leduc Hold'em (GDL-II) | † | † | † | † | † | † | † | † |

## Table 7 — single-player imperfect information (against nature)

There is no opponent, so the cell is the version's **win rate**. Known
values: optimal (always switch) 66.7%, never switch 33.3%, uniform
random 50%.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Monty Hall (GDL-II) | 46.5% [41.7, 51.4] n=400 | † | † | † | † | † | 66.3% [61.5, 70.7] n=400 | † |

## Table 8 — baseline V7 (V7.0, V4 one ply deeper; see ※)

Expected: V7 ≈ 50%. Read against Table 5: V7 is V4's player one ply
deeper, so V7's column in Table 5 and V4's column here are the same
games scored from each side.

| Game | V0 | V1 | V2 | V3 | V4 | V5 | V6 | V7 |
|---|---|---|---|---|---|---|---|---|
| Royal Chess |  |  | cost |  |  | ‡ cost | ◊ |  |
| m,n,k 3,3,3 |  |  |  |  |  |  | ◊ |  |
| m,n,k 5,5,4 |  |  |  |  |  |  | ◊ |  |
| m,n,k 13,13,5 |  |  | cost |  |  | cost | ◊ |  |
| Nim (GDL) | § | § | § | § | § | § | ◊ | § |
| Krieg-TicTacToe / Krieg-m,n,k 3,3,3 (GDL-II) | † | † | † | † | † | † | † | † |
| Krieg 5,5,4 (GDL-II) | † | † | † | † | † | † | † | † |
| Kuhn poker (GDL-II) | † | † | † | † | † | † | † | † |
| Leduc Hold'em (GDL-II) | † | † | † | † | † | † | † | † |

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

| V6.0 (ab792e8), defaults | as player1 | as player2 | † |
|---|---|---|
| Chips per hand vs V0, sampled (n=1000 per seat) | +0.316 | +0.229 | † |
| Chips per hand vs Nash, sampled (n=1000 per seat) | −0.162 | −0.038 | † |
| Chips per hand vs Nash, exact from its strategy | **−0.153** | **−0.084** | † |
| Equilibrium value of the seat | −0.056 | +0.056 | † |
| **Exploitability** (best response's gain over the value) | **0.198** | **0.307** | † |

What V6 plays, as the probability of the aggressive move (bet, or call
when facing a bet). 0.51 is a tie that V6 breaks with its seeded coin,
read from 400 players.

| Information set | V6 | Equilibrium | † |
|---|---|---|
| player1 J, open | 0.51 | α (0 to 1/3) | † |
| player1 Q, open | 1 | 0 | † |
| player1 K, open | 1 | 3α | † |
| player1 J, check–bet | 0.51 | 0 | † |
| player1 Q, check–bet | 1 | α + 1/3 | † |
| player2 J, after check | 0.51 | 1/3 | † |
| player2 Q, after check | 1 | 0 | † |
| player2 K, after check | 0.51 | 1 | † |
| player2 J, facing bet | 0.51 | 0 | † |
| player2 Q, facing bet | 1 | 1/3 | † |

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

## Leduc Hold'em in chips (#292)

Measured the same way as Kuhn poker. Leduc has no closed-form
equilibrium, so the reference (`lgref/experiments/leduc.py`, hand-written
for this game; nothing in V6 reads it) computes one by **CFR+**. After
1,000 iterations it is worth **−0.0856** chips per hand to player1. That
matches the published value. A best response gains only **0.0004** (as
player1) and **0.0001** (as player2) against it, so it is an
equilibrium to well within the sampling error of anything below. V6's
strategy is read by showing each of the 288 information sets (144 per
seat: a card rank, the public card's rank once it is up, and the betting
so far) to 200 freshly seeded V6 players. A uniform random strategy is
given for scale.

| V6.0 (ab792e8), defaults | as player1 | as player2 | † |
|---|---|---|
| Chips per hand vs V0, sampled (n=1000 per seat, se ≈ 0.18 / 0.14) | +1.037 | −0.067 | † |
| Chips per hand vs CFR+, sampled (n=1000 per seat, se ≈ 0.19 / 0.11) | −1.047 | −0.579 | † |
| Chips per hand vs CFR+, exact from its strategy | **−0.755** | **−0.496** | † |
| Uniform random, exact vs CFR+ | −0.823 | −0.592 | † |
| Equilibrium value of the seat | −0.086 | +0.086 | † |
| **Exploitability** of V6 | **2.233** | **1.552** | † |
| Exploitability of uniform random | 2.574 | 2.173 | † |

**V6 is barely better than uniform random against the equilibrium here.**
Against the equilibrium it loses 0.755 and 0.496 chips per hand, where a
uniform player loses 0.823 and 0.592. Its exploitability is 87% and 71%
of a uniform player's. The sampled "vs CFR+" row agrees with the exact
one to within 1.6 standard errors.

What V6 plays, averaged over information sets (probability of each
move). The rows are pooled over cards, so the equilibrium averages hide
a lot of card-dependence, but the V6 pattern needs no unpooling:

| Seat, round, situation | V6 | CFR+ | † |
|---|---|---|
| player1, facing a bet (any round) | **never folds**; calls | folds 0–55% | † |
| player2, facing a bet (any round) | **never folds**, never raises; always calls | folds 0–47%, raises 34% | † |
| player2, may bet (any round) | **never bets**; always checks | bets 53–72% | † |
| player1, may bet | bets 62–67% | bets 43–52% | † |
| player1, share of information sets where the choice is a coin flip | 67% | — | † |

**This is V6's limit, not a bug.** Two causes can be stated with
confidence:

1. **A fold is always the worst move inside a sample.** It ends the
   sample at once in a loss, while any other move reaches a position
   the depth-2 search, with its flat 0.5 evaluation, scores as a tie.
   So V6 calls everything. Leduc hands are longer than Kuhn's (two
   rounds plus nature's two moves), so depth 2 rarely reaches the end,
   and most of V6's values are the flat 0.5.
2. **Ties go to the seeded coin.** Most of player1's choices are ties,
   so it plays them at random. That is why its exploitability is close
   to a uniform player's.

Why V6 as player2 never bets is **not established**. It is observed, at
every such information set and with every seed read, and has not been
traced to a cause. Against V0, player2's never-fold, never-bet play is
roughly break-even (−0.07 ± 0.14 chips per hand), while player1 wins
+1.04.

Commands:
- `python -m lgref.experiments.leduc 2000 292 1000 200` (seed 292; games
  292–2291 for the sampled rows; CFR+ 1,000 iterations; 200 reads per
  information set).
- `python -m lgref.experiments.hidden
  lgref/identify/testgames/leducholdem.gdl v6 v0 400 292` and `... v0 v0
  400 292` for the win-rate cells.

**Cell notes**

- **†** Unfair, not reported. V1–V5 read the true state through
  `GdlGame` (see the caveat above). The fair players on these rows are
  V0 and V6.
- **‡ cost** V5 plays Royal Chess only through the GDL interpreter.
  Measured at 70c2044 on `docs/gdl/integrated.gdl`: listing the legal
  moves costs 1.5–1.7 s at each of the first four plies (71–76 moves).
  A depth-1 decision alone lists about seventy positions, about two
  minutes, and V5's training (120 self-play games of a game that runs
  hundreds of plies) would take about a day before its first move. Even
  n=100 is out of reach, so these cells stay unfilled. In Table 6 the
  whole row has V5 as the baseline, so it is "cost" too.
- **◊** Not applicable. V6 plays from a GDL-II/III view, and a
  perfect-information game has nothing hidden: its belief would be the
  true state, so it would be a flat depth-2 search and not a version.
  The V4/V5 cells are the ones to read on these rows.
- **† in the V0 and V6 columns** (Tables 2–6, Krieg-TicTacToe, Krieg 5,5,4, Kuhn poker and Leduc Hold'em): the BASELINE is
  unfair there, not V0 or V6. V1–V5 cannot be a fair opponent on this row.
- **cost** Not played, and not going to be. V5.1 on m,n,k 13,13,5 plays
  through the GDL interpreter: listing the legal moves costs 0.3–0.6 s
  (four plies measured at 70c2044), so a depth-3 decision lists
  thousands of positions, and its training from zero (120 games) had
  not finished after 8 hours, before its first move. V2.2 on Royal
  Chess and m,n,k 13,13,5 costs ten minutes to over an hour a move (see
  "Measured cost per game"), so even n=100 is out of reach there: about
  140 to 280 CPU-hours a cell on 13,13,5 and more on Royal Chess. In
  Table 3 the whole row has V2 as the baseline, so it is "cost" too.
- **※ V7 column and Table 8:** measured on V7.0 (d244ba4); V7.1
  differs only inside the tiny endgame (CONFINED certificate in #393).
  V7's games run compiled from a checkout at d244ba4 (#362's IDENTICAL
  build; four seeded games replayed pure and compiled gave the same
  moves), and the column keeps that checkout as V7.1 lands, so it
  stays one player at every level. #399 (engine bug #391, the tiny
  endgame filter) also changes play only in saturated tiny-endgame
  positions, and does not reach any column: every version runs its own
  checkout, and the referee is the engine at 591414c for every level.
- **¶** More than 5% of the cell's games were truncated or diverged
  (see the record table); they are not in the score.
- **A diagonal cell of a deterministic version is 50.0% by
  construction.** V2–V5 against themselves play each pair's opening
  twice with the same two copies, so the two games are one game with
  the labels swapped. What such a match measures is the per-seat split
  in the record table: the game's first-player bias at that strength.
  V0 and V1 are seeded, so their diagonal is a real sample; V0 against
  V0 on m,n,k 3,3,3 reads 54.9% [50.0, 59.7] where symmetry says 50%,
  which is a sampling deviation at the edge of the interval.
- **§** Nim has no hand-written feature set, so V3/V4's features do
  not exist for it: **n/a, no extractor**, and V5 is that column's GDL
  equivalent. Tables 4 and 5 have no Nim baseline for the same reason.
  V2.2's loss-condition evaluation does read the GDL game (with no
  extractor it is mobility and repetition pressure, both read through
  the protocol), so V2 is measured. It scores 46.0% [41.2, 50.9] against
  V0, not distinguishable from 50%; why its evaluation gives it no
  edge on this game is not established here.
  V1 and V5 against each other, and each against itself, split every
  one of the 200 pairs of games the same way (in 155 pairs the first
  mover wins both games, in the other 45 the second mover does), so the
  position after the opening decides each game and those cells are
  50.0% by construction.

---

## Record — one row per measured cell

Fill one row per cell. The tables above are summaries of this.

| Table (baseline) | Game | Version (sub-version, SHA) | W | D | L | Truncated | n | Score | 95% CI | Seat 1st / 2nd | Depth / sims | Seeds | Date | Command |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 (V0) | Krieg-TicTacToe | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 186 | 33 | 181 | 0 | 400 | 50.6% | [45.7, 55.5] | 70.0% / 31.3% | — | match seed 286 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/kriegtictactoe.gdl v0 v0 400 286` |
| 1 (V0) | Krieg-TicTacToe | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 256 | 51 | 93 | 0 | 400 | 70.4% | [65.7, 74.6] | 84.8% / 56.0% | depth 2, 16 particles | match seed 286 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/kriegtictactoe.gdl v6 v0 400 286` |
| 1 (V0) | Kuhn poker | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 55.0% / 45.0% | — | match seed 288 | 2026-10-28 | `python -m lgref.experiments.hidden lgref/identify/testgames/kuhnpoker.gdl v0 v0 400 288` |
| 1 (V0) | Kuhn poker | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 244 | 0 | 156 | 0 | 400 | 61.0% | [56.1, 65.7] | 64.0% / 58.0% | depth 2, 16 particles | match seed 288 | 2026-10-28 | `python -m lgref.experiments.hidden lgref/identify/testgames/kuhnpoker.gdl v6 v0 400 288` |
| 1 (V0) | Leduc Hold'em | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 180 | 32 | 188 | 0 | 400 | 49.0% | [44.1, 53.9] | 53.3% / 44.8% | — | match seed 292 | 2026-10-29 | `python -m lgref.experiments.hidden lgref/identify/testgames/leducholdem.gdl v0 v0 400 292` |
| 1 (V0) | Leduc Hold'em | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 209 | 72 | 119 | 0 | 400 | 61.3% | [56.4, 65.9] | 74.8% / 47.8% | depth 2, 16 particles | match seed 292 | 2026-10-29 | `python -m lgref.experiments.hidden lgref/identify/testgames/leducholdem.gdl v6 v0 400 292` |
| 1 (V0) | Krieg 5,5,4 | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 194 | 14 | 192 | 0 | 400 | 50.3% | [45.4, 55.1] | 60.3% / 40.3% | — | match seed 293 | 2026-10-29 | `python -m lgref.experiments.hidden lgref/identify/testgames/kriegmnk_5_5_4.gdl v0 v0 400 293` |
| 1 (V0) | Krieg 5,5,4 | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 328 | 21 | 51 | 0 | 400 | 84.6% | [80.8, 87.8] | 87.0% / 82.3% | depth 2, 16 particles | match seed 293 | 2026-10-29 | `python -m lgref.experiments.hidden lgref/identify/testgames/kriegmnk_5_5_4.gdl v6 v0 400 293` |
| 7 (nature) | Monty Hall | V6.0 (ab792e8), defaults: 16 particles, depth 2 | 265 | — | 135 | 0 | 400 | 66.3% | [61.5, 70.7] | — | depth 2, 16 particles | games 10000–10399 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/montyhall.gdl v6 400 10000` |
| 7 (nature) | Monty Hall | V0.1 (3ce1e41), as `hidden.UniformPlayer` on its view | 186 | — | 214 | 0 | 400 | 46.5% | [41.7, 51.4] | — | — | games 10000–10399 | 2026-10-27 | `python -m lgref.experiments.hidden lgref/identify/testgames/montyhall.gdl v0 400 10000` |
| 1 (V0) | m,n,k 3,3,3 | V0.1 as uniform random, run at 591414c | 199 | 41 | 160 | 0 | 400 | 54.9% | [50.0, 59.7] | 66.0% / 43.8% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v0@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 3,3,3 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 364 | 28 | 8 | 0 | 400 | 94.5% | [91.8, 96.3] | 99.0% / 90.0% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v1@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 3,3,3 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 210 | 118 | 72 | 0 | 400 | 67.2% | [62.5, 71.7] | 82.0% / 52.5% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v2@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 3,3,3 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 365 | 28 | 7 | 0 | 400 | 94.8% | [92.1, 96.5] | 98.2% / 91.2% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 3,3,3 | V4.15 (6307d97), its own checkout | 371 | 25 | 4 | 0 | 400 | 95.9% | [93.5, 97.4] | 99.5% / 92.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 3,3,3 | V5.1 (70c2044), its own checkout | 312 | 72 | 16 | 0 | 400 | 87.0% | [83.3, 89.9] | 99.8% / 74.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v0@<591414c> 400 282` |
| 2 (V1) | m,n,k 3,3,3 | V0.1 as uniform random, run at 591414c | 8 | 28 | 364 | 0 | 400 | 5.5% | [3.7, 8.2] | 10.0% / 1.0% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v1@<591414c> v0@<591414c> 400 282` (same games as the V1 vs V0 cell) |
| 2 (V1) | m,n,k 3,3,3 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 84 | 240 | 76 | 0 | 400 | 51.0% | [46.1, 55.9] | 68.5% / 33.5% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v1@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 3,3,3 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 2 | 248 | 150 | 0 | 400 | 31.5% | [27.1, 36.2] | 35.0% / 28.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v2@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 3,3,3 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 51 | 285 | 64 | 0 | 400 | 48.4% | [43.5, 53.3] | 61.8% / 35.0% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 3,3,3 | V4.15 (6307d97), its own checkout | 92 | 271 | 37 | 0 | 400 | 56.9% | [52.0, 61.6] | 71.8% / 42.0% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 3,3,3 | V5.1 (70c2044), its own checkout | 83 | 173 | 144 | 0 | 400 | 42.4% | [37.6, 47.3] | 65.0% / 19.8% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v1@<591414c> 400 282` |
| 3 (V2) | m,n,k 3,3,3 | V0.1 as uniform random, run at 591414c | 72 | 118 | 210 | 0 | 400 | 32.8% | [28.3, 37.5] | 47.5% / 18.0% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v2@<591414c> v0@<591414c> 400 282` (same games as the V2 vs V0 cell) |
| 3 (V2) | m,n,k 3,3,3 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 150 | 248 | 2 | 0 | 400 | 68.5% | [63.8, 72.9] | 72.0% / 65.0% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v2@<591414c> v1@<591414c> 400 282` (same games as the V2 vs V1 cell) |
| 3 (V2) | m,n,k 3,3,3 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 124 | 152 | 124 | 0 | 400 | 50.0% | [45.1, 54.9] | 78.0% / 22.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v2@<591414c> v2@<591414c> 400 282` |
| 3 (V2) | m,n,k 3,3,3 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 38 | 359 | 3 | 0 | 400 | 54.4% | [49.5, 59.2] | 57.0% / 51.7% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v2@<591414c> 400 282` |
| 3 (V2) | m,n,k 3,3,3 | V4.15 (6307d97), its own checkout | 121 | 279 | 0 | 0 | 400 | 65.1% | [60.3, 69.6] | 70.5% / 59.8% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v2@<591414c> 400 282` |
| 3 (V2) | m,n,k 3,3,3 | V5.1 (70c2044), its own checkout | 215 | 173 | 12 | 0 | 400 | 75.4% | [70.9, 79.3] | 70.2% / 80.5% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v2@<591414c> 400 282` |
| 4 (V3) | m,n,k 3,3,3 | V0.1 as uniform random, run at 591414c | 7 | 28 | 365 | 0 | 400 | 5.2% | [3.5, 7.9] | 8.8% / 1.7% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v0@<591414c> 400 282` (same games as the V3 vs V0 cell) |
| 4 (V3) | m,n,k 3,3,3 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 64 | 285 | 51 | 0 | 400 | 51.6% | [46.7, 56.5] | 65.0% / 38.2% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v1@<591414c> 400 282` (same games as the V3 vs V1 cell) |
| 4 (V3) | m,n,k 3,3,3 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 3 | 359 | 38 | 0 | 400 | 45.6% | [40.8, 50.5] | 48.3% / 43.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v2@<591414c> 400 282` (same games as the V3 vs V2 cell) |
| 4 (V3) | m,n,k 3,3,3 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 30 | 340 | 30 | 0 | 400 | 50.0% | [45.1, 54.9] | 57.0% / 43.0% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v3@<591414c> v3@<591414c> 400 282` |
| 4 (V3) | m,n,k 3,3,3 | V4.15 (6307d97), its own checkout | 103 | 277 | 20 | 0 | 400 | 60.4% | [55.5, 65.0] | 75.5% / 45.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v3@<591414c> 400 282` |
| 4 (V3) | m,n,k 3,3,3 | V5.1 (70c2044), its own checkout | 51 | 241 | 108 | 0 | 400 | 42.9% | [38.1, 47.8] | 62.0% / 23.8% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v3@<591414c> 400 282` |
| 5 (V4) | m,n,k 3,3,3 | V0.1 as uniform random, run at 591414c | 4 | 25 | 371 | 0 | 400 | 4.1% | [2.6, 6.5] | 7.8% / 0.5% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v0@<591414c> 400 282` (same games as the V4 vs V0 cell) |
| 5 (V4) | m,n,k 3,3,3 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 37 | 271 | 92 | 0 | 400 | 43.1% | [38.4, 48.0] | 58.0% / 28.2% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v1@<591414c> 400 282` (same games as the V4 vs V1 cell) |
| 5 (V4) | m,n,k 3,3,3 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 0 | 279 | 121 | 0 | 400 | 34.9% | [30.4, 39.7] | 40.2% / 29.5% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v2@<591414c> 400 282` (same games as the V4 vs V2 cell) |
| 5 (V4) | m,n,k 3,3,3 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 20 | 277 | 103 | 0 | 400 | 39.6% | [35.0, 44.5] | 54.8% / 24.5% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v3@<591414c> 400 282` (same games as the V4 vs V3 cell) |
| 5 (V4) | m,n,k 3,3,3 | V4.15 (6307d97), its own checkout | 47 | 306 | 47 | 0 | 400 | 50.0% | [45.1, 54.9] | 61.8% / 38.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v4@<6307d97> v4@<6307d97> 400 282` |
| 5 (V4) | m,n,k 3,3,3 | V5.1 (70c2044), its own checkout | 34 | 208 | 158 | 0 | 400 | 34.5% | [30.0, 39.3] | 56.8% / 12.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v4@<6307d97> 400 282` |
| 6 (V5) | m,n,k 3,3,3 | V0.1 as uniform random, run at 591414c | 16 | 72 | 312 | 0 | 400 | 13.0% | [10.1, 16.7] | 25.7% / 0.2% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v0@<591414c> 400 282` (same games as the V5 vs V0 cell) |
| 6 (V5) | m,n,k 3,3,3 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 144 | 173 | 83 | 0 | 400 | 57.6% | [52.7, 62.4] | 80.2% / 35.0% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v1@<591414c> 400 282` (same games as the V5 vs V1 cell) |
| 6 (V5) | m,n,k 3,3,3 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 12 | 173 | 215 | 0 | 400 | 24.6% | [20.7, 29.1] | 19.5% / 29.8% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v2@<591414c> 400 282` (same games as the V5 vs V2 cell) |
| 6 (V5) | m,n,k 3,3,3 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 108 | 241 | 51 | 0 | 400 | 57.1% | [52.2, 61.9] | 76.2% / 38.0% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v3@<591414c> 400 282` (same games as the V5 vs V3 cell) |
| 6 (V5) | m,n,k 3,3,3 | V4.15 (6307d97), its own checkout | 158 | 208 | 34 | 0 | 400 | 65.5% | [60.7, 70.0] | 87.8% / 43.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v4@<6307d97> 400 282` (same games as the V5 vs V4 cell) |
| 6 (V5) | m,n,k 3,3,3 | V5.1 (70c2044), its own checkout | 93 | 214 | 93 | 0 | 400 | 50.0% | [45.1, 54.9] | 70.8% / 29.2% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:3,3,3 v5@<70c2044> v5@<70c2044> 400 282` |
| 1 (V0) | Nim | V0.1 as uniform random, run at 591414c | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 42.0% / 58.0% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v0@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | Nim | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 325 | 0 | 75 | 0 | 400 | 81.2% | [77.1, 84.8] | 86.5% / 76.0% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v1@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | Nim | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 184 | 0 | 216 | 0 | 400 | 46.0% | [41.2, 50.9] | 47.5% / 44.5% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v2@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | Nim | V5.1 (70c2044), its own checkout | 330 | 0 | 70 | 0 | 400 | 82.5% | [78.5, 85.9] | 86.5% / 78.5% | depth 4 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v0@<591414c> 400 282` |
| 2 (V1) | Nim | V0.1 as uniform random, run at 591414c | 75 | 0 | 325 | 0 | 400 | 18.8% | [15.2, 22.9] | 24.0% / 13.5% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v1@<591414c> v0@<591414c> 400 282` (same games as the V1 vs V0 cell) |
| 2 (V1) | Nim | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 77.5% / 22.5% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v1@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | Nim | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 11 | 0 | 389 | 0 | 400 | 2.8% | [1.5, 4.9] | 5.5% / 0.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v2@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | Nim | V5.1 (70c2044), its own checkout | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 77.5% / 22.5% | depth 4 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v1@<591414c> 400 282` |
| 3 (V2) | Nim | V0.1 as uniform random, run at 591414c | 216 | 0 | 184 | 0 | 400 | 54.0% | [49.1, 58.8] | 55.5% / 52.5% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v2@<591414c> v0@<591414c> 400 282` (same games as the V2 vs V0 cell) |
| 3 (V2) | Nim | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 389 | 0 | 11 | 0 | 400 | 97.2% | [95.1, 98.5] | 100.0% / 94.5% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v2@<591414c> v1@<591414c> 400 282` (same games as the V2 vs V1 cell) |
| 3 (V2) | Nim | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 79.0% / 21.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v2@<591414c> v2@<591414c> 400 282` |
| 3 (V2) | Nim | V5.1 (70c2044), its own checkout | 358 | 0 | 42 | 0 | 400 | 89.5% | [86.1, 92.1] | 100.0% / 79.0% | depth 4 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v2@<591414c> 400 282` |
| 6 (V5) | Nim | V0.1 as uniform random, run at 591414c | 70 | 0 | 330 | 0 | 400 | 17.5% | [14.1, 21.5] | 21.5% / 13.5% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v0@<591414c> 400 282` (same games as the V5 vs V0 cell) |
| 6 (V5) | Nim | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 77.5% / 22.5% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v1@<591414c> 400 282` (same games as the V5 vs V1 cell) |
| 6 (V5) | Nim | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 42 | 0 | 358 | 0 | 400 | 10.5% | [7.9, 13.9] | 21.0% / 0.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v2@<591414c> 400 282` (same games as the V5 vs V2 cell) |
| 6 (V5) | Nim | V5.1 (70c2044), its own checkout | 200 | 0 | 200 | 0 | 400 | 50.0% | [45.1, 54.9] | 77.5% / 22.5% | depth 4 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play nim v5@<70c2044> v5@<70c2044> 400 282` |
| 1 (V0) | m,n,k 5,5,4 | V0.1 as uniform random, run at 591414c | 201 | 26 | 173 | 0 | 400 | 53.5% | [48.6, 58.3] | 56.8% / 50.2% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v0@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 5,5,4 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 393 | 1 | 6 | 0 | 400 | 98.4% | [96.6, 99.2] | 98.8% / 98.0% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v1@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 5,5,4 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 260 | 93 | 47 | 0 | 400 | 76.6% | [72.2, 80.5] | 81.2% / 72.0% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v2@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 5,5,4 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 400 | 0 | 0 | 0 | 400 | 100.0% | [99.0, 100.0] | 100.0% / 100.0% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v0@<591414c> 400 282` |
| 1 (V0) | m,n,k 5,5,4 | V4.15 (6307d97), its own checkout | 400 | 0 | 0 | 0 | 400 | 100.0% | [99.0, 100.0] | 100.0% / 100.0% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v0@<591414c> 400 282` |
| 2 (V1) | m,n,k 5,5,4 | V0.1 as uniform random, run at 591414c | 6 | 1 | 393 | 0 | 400 | 1.6% | [0.8, 3.4] | 2.0% / 1.2% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v1@<591414c> v0@<591414c> 400 282` (same games as the V1 vs V0 cell) |
| 2 (V1) | m,n,k 5,5,4 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 198 | 15 | 187 | 0 | 400 | 51.4% | [46.5, 56.2] | 61.3% / 41.5% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v1@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 5,5,4 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 51 | 57 | 292 | 0 | 400 | 19.9% | [16.3, 24.1] | 22.5% / 17.2% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v2@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 5,5,4 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 338 | 16 | 46 | 0 | 400 | 86.5% | [82.8, 89.5] | 92.2% / 80.8% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v1@<591414c> 400 282` |
| 2 (V1) | m,n,k 5,5,4 | V4.15 (6307d97), its own checkout | 363 | 16 | 21 | 0 | 400 | 92.8% | [89.8, 94.9] | 96.0% / 89.5% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v1@<591414c> 400 282` |
| 3 (V2) | m,n,k 5,5,4 | V0.1 as uniform random, run at 591414c | 47 | 93 | 260 | 0 | 400 | 23.4% | [19.5, 27.8] | 28.0% / 18.8% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v2@<591414c> v0@<591414c> 400 282` (same games as the V2 vs V0 cell) |
| 3 (V2) | m,n,k 5,5,4 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 292 | 57 | 51 | 0 | 400 | 80.1% | [75.9, 83.7] | 82.8% / 77.5% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v2@<591414c> v1@<591414c> 400 282` (same games as the V2 vs V1 cell) |
| 3 (V2) | m,n,k 5,5,4 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 70 | 260 | 70 | 0 | 400 | 50.0% | [45.1, 54.9] | 40.5% / 59.5% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v2@<591414c> v2@<591414c> 400 282` |
| 3 (V2) | m,n,k 5,5,4 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 348 | 17 | 35 | 0 | 400 | 89.1% | [85.7, 91.8] | 91.5% / 86.8% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v2@<591414c> 400 282` |
| 3 (V2) | m,n,k 5,5,4 | V4.15 (6307d97), its own checkout | 393 | 7 | 0 | 0 | 400 | 99.1% | [97.6, 99.7] | 98.8% / 99.5% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v2@<591414c> 400 282` |
| 4 (V3) | m,n,k 5,5,4 | V0.1 as uniform random, run at 591414c | 0 | 0 | 400 | 0 | 400 | 0.0% | [0.0, 1.0] | 0.0% / 0.0% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v0@<591414c> 400 282` (same games as the V3 vs V0 cell) |
| 4 (V3) | m,n,k 5,5,4 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 46 | 16 | 338 | 0 | 400 | 13.5% | [10.5, 17.2] | 19.2% / 7.8% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v1@<591414c> 400 282` (same games as the V3 vs V1 cell) |
| 4 (V3) | m,n,k 5,5,4 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 35 | 17 | 348 | 0 | 400 | 10.9% | [8.2, 14.3] | 13.2% / 8.5% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v2@<591414c> 400 282` (same games as the V3 vs V2 cell) |
| 4 (V3) | m,n,k 5,5,4 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 138 | 124 | 138 | 0 | 400 | 50.0% | [45.1, 54.9] | 49.5% / 50.5% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v3@<591414c> v3@<591414c> 400 282` |
| 4 (V3) | m,n,k 5,5,4 | V4.15 (6307d97), its own checkout | 159 | 154 | 87 | 0 | 400 | 59.0% | [54.1, 63.7] | 63.5% / 54.5% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v3@<591414c> 400 282` |
| 5 (V4) | m,n,k 5,5,4 | V0.1 as uniform random, run at 591414c | 0 | 0 | 400 | 0 | 400 | 0.0% | [0.0, 1.0] | 0.0% / 0.0% | — | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v0@<591414c> 400 282` (same games as the V4 vs V0 cell) |
| 5 (V4) | m,n,k 5,5,4 | V1.4 MCTS-200, `mcts.py` byte-identical to 96dfbd8, run at 591414c | 21 | 16 | 363 | 0 | 400 | 7.3% | [5.1, 10.2] | 10.5% / 4.0% | 200 sims | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v1@<591414c> 400 282` (same games as the V4 vs V1 cell) |
| 5 (V4) | m,n,k 5,5,4 | V2.2 `GenericPlayer` d2 q2, protocol-only evaluation; `GenericPlayer` unchanged since dcee4b4, run at 591414c | 0 | 7 | 393 | 0 | 400 | 0.9% | [0.3, 2.4] | 0.5% / 1.2% | depth 2, quiescence 2 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v2@<591414c> 400 282` (same games as the V4 vs V2 cell) |
| 5 (V4) | m,n,k 5,5,4 | V3 as `play_mnk --o td1` at 591414c (today's one-ply player; V3.1 had no m,n,k build) | 87 | 154 | 159 | 0 | 400 | 41.0% | [36.3, 45.9] | 45.5% / 36.5% | 1 ply | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v3@<591414c> 400 282` (same games as the V4 vs V3 cell) |
| 5 (V4) | m,n,k 5,5,4 | V4.15 (6307d97), its own checkout | 155 | 90 | 155 | 0 | 400 | 50.0% | [45.1, 54.9] | 71.2% / 28.7% | depth 3 | match seed 282, games 0–399 | 2026-11-26 | `python -m lgref.experiments.versions play mnk:5,5,4 v4@<6307d97> v4@<6307d97> 400 282` |
