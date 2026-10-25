# Every planned change, run through the design procedure

Applying `docs/strictly-better-method.md` to the candidates. Step 2 is
the one that decides: **choose a certificate class and name the premise
that discharges it, before writing code. If no class fits, there is no
change yet.**

The honest result is that **most of these are inadmissible as designed**
— and that is not a disappointment, it is the explanation. Each of them
was built and then measured, and each was refused. The procedure
refuses them earlier and more cheaply, before the work.

---

## 1. m,n,k opening tie-break — SPLIT: one half admissible, one not

**Defect, measured:** opening placement 15.5% on 13x13 where a random
player scores 50%. (Measured against the crippled search; being
re-measured.)

The change has two levels, and they are not the same kind of thing.

### 1a. The threat level — ADMISSIBLE (CONFINED + MONOTONE)

Among moves the search values identically, prefer one that makes a
threat or removes one.

| | |
|---|---|
| **CONFINED premise** | where root values differ, the chosen move is unchanged — mechanically checkable per position |
| **MONOTONE premise** | a tie that previously picked an active move by chance now picks one whenever the tie contains one, so the active-move rate cannot fall |

Both discharge. This half can ship.

### 1b. The centrality level — **NOT ADMISSIBLE**

Among tied moves, prefer the one with higher rule-derived centrality.

CONFINED discharges (it only fires on ties). **MONOTONE does not.**
There is no invariant saying the more central of two tied moves is
never worse — the evaluation says they are equal, and the claim that
one is better comes from outside it. Replacing an arbitrary choice
(move-generator order) with a principled one is *probably* better and
cannot be *proven* not worse.

**A dominance redesign was considered and rejected on measurement:**
prefer a tied move whose set of winning configurations is a strict
superset of the alternative's. That *is* a dominance argument — more
ways to win, none fewer. But on 19x19 k=5 the centre participates in 20
lines and so does every cell four from an edge; the sets are
*different*, not *nested*, so it would almost never fire and would not
fix the opening.

**Status: off.** The defect stays open. A certifiable fix needs a
criterion under which the preferred move *dominates* rather than merely
scores higher.

---

## 2. `Reach:j` as a feature — **NOT ADMISSIBLE**

A feature changes every value in every position. No class applies:
not IDENTICAL (values change), not CONFINED (no region), not MONOTONE
(no invariant), not UNSOUND (removes nothing).

Measured cost when it was built and raced anyway: 2.4 points of midgame
tempo across four training seeds, down in every one.

**Status: off, permanently, in this form.** The quantity it computes is
correct — it finds the exact centre on 9x9, 19x19 and 20x20 — which is
why it survives as the tie-break's prior, where confinement is at least
arguable. As a feature it is not admissible.

---

## 3. Intersection boulder — ADMISSIBLE (CONFINED), and pointless

**CONFINED premise, discharged:** the extractor's output is identical
unless the boulder is on the central intersection *and* a pawn stands
on one of the four central squares. Verified on 60 positions outside
the region: zero effect. The region is 1.8% of live positions.

So it is admissible. But inside the region it was measured to change
**nothing**: identical moves in 20 of 20 positions, because `Attacked`
weighs −0.0004 and `Hanging` is absent from the shipped vocabulary.

**Status: off.** A certified change that does nothing is not an
improvement. It ships if and when the threat columns carry weight.

---

## 4. `EndgamePinned` — ADMISSIBLE (CONFINED), benefit unproven

**CONFINED premise, discharged:** absent outside the rulebook's own
tiny-endgame regime (`Board.is_tiny_endgame`), verified on 60 positions
before fitting; the fitter refuses to fit otherwise.

Fitted alone with all nineteen other weights frozen: **−0.0187**, about
30% of a pawn, sign as the rules imply. Inside the region it does
change behaviour — 2 of 25 moves.

Raced from identical thin positions, both colours: **30–30**.

**Status: off.** Confinement proves it cannot regress anything outside
the regime. It does not prove it helps inside, and the race could not
resolve 8% of moves in a rare regime. Shipping would need a benefit
argument inside the region, which a race at this effect size cannot
supply.

---

## 5. `BoulderPressure` — **NOT ADMISSIBLE**

**Defect, measured and real:** pawns lost within twelve plies by the
boulder's Chebyshev distance — 44% at 1, 35% at 2, 29% at 3, 25% at 5,
0% at 7. Everything from distance 2 outwards is past a depth-3 horizon,
because the boulder's cooldown means it advances once per three plies.

**No class applies.** The column is zero only at distance ≤ 1; at
distance ≥ 2 it speaks, and the boulder is usually ≥ 2 from a pawn. So
it changes nearly every position: not CONFINED. Not IDENTICAL, not
MONOTONE, not UNSOUND.

It was fitted alone anyway (−0.0213, with `--unconfined` stating the
absence of an argument out loud) and raced. **That was the old
workflow, and the procedure would have stopped it at step 2.**

**Status: off.** The defect is real and the fix is not certifiable as
an evaluation term. A certifiable attack on it would have to be
confined to a rule-defined region — and the rules do not supply one
here, because the boulder is relevant almost everywhere.

---

## What this leaves — and it is the productive finding

Two classes discharge easily and both buy the same thing: **search
depth**.

**IDENTICAL — speedups.** Already shipped: the extraction rewrite
(1.32 ms → 0.23 ms, output identical across 120 positions on six
boards), the board copy (0.70 → 0.18 ms), the jump (flat in game
length). Each is strict improvement by arithmetic.

**UNSOUND — removing heuristics whose premise is false here.** Already
shipped: futility pruning in a game with no captures, which was pruning
the blocking move. **Candidates not yet examined:** late-move
reduction, `reduce_turns`, and quiescence — each rests on a
quiet/forcing distinction that m,n,k does not have, and each should be
checked against the same premise.

**Why this is the productive direction, measured:** depth is what fixed
the reviewer's blunder. Going from depth 1 to depth 2 on 19x19 turned
`8,12` (loses) into `11,14` (blocks). Nothing in the evaluation
changed. Every certifiable speedup buys more of that, and every unsound
heuristic removed buys honest depth instead of fake depth.

---

## 6. The per-move wall clock — ADMISSIBLE (UNSOUND), and shipped

**Defect, measured.** The shipped players were clock-driven, not
depth-driven:

| player | configured | actually delivered |
|---|---|---|
| m,n,k window | depth 3, `--budget 5.0` | depth 3 on 5x5, **2** on 13x13, **1** on a busy 13x13 |
| Royal Chess `td` | depth 3, 30 s | depth 3 — the clock never fired |

So the m,n,k player was silently playing one to two plies shallower
than it was asked to, and *which* ply it dropped depended on what else
the machine was running. Measured across nine positions and three
budgets: every clocked run reached a depth less than or equal to the
unclocked one, and three of nine were strictly shallower.

### The class, and why it is not "deeper is better"

**UNSOUND.** A per-move wall clock is an operation — *stop deepening
and answer with what you have* — and its premise is that **the game
imposes a real-time constraint**, so a completed shallower answer is
the right trade when the seconds run out.

**Neither game here imposes one.** Both are bounded in **plies**:
m,n,k ends when the board fills, Royal Chess when both royals fall or
the turn cap is reached (`turn_number >= max_turns`). The official game
description contains no time term — no `clock`, `elapsed`, `deadline`
or `seconds` predicate in `docs/gdl/integrated.gdl` — and neither
engine's termination predicate reads a clock. A number of seconds is
therefore **hand-supplied**, and a hand-supplied number that changes
what the agent plays is this project's own definition of bias.

This is the same shape as futility pruning, and it is removed the same
way: by **detecting the capability** rather than deleting the code,
because a timed match is a real context and the clock is sound there.
It now has to be asked for.

**It is emphatically NOT the inadmissible argument** that
`strictly-better-method.md` refuses. The configured depth does not
change. Every deadline test in the search is a `break`, a `raise` or a
`complete = False` — never an extension of `range(1, max_depth + 1)` —
so **a clock can only ever take depth away**, and the iterations a
clocked search completes are a prefix of those it completes without
one. Removing it makes the player deliver the depth it was asked for
instead of a load-dependent fraction of it. No ply is added that the
settings did not already request.

### The premise, discharged — and the two false positives it caught

`test_the_move_clock_is_an_unsound_premise` checks three cases: the
game description, and each engine's termination predicate. The check
itself was wrong twice, and the certifier refused both times rather
than waving them through:

- a bare `time(` matched `would_repeat_third_time(`, which is the
  repetition rule's **count**;
- a bare `time.` matched the comment *"no implicit branching at
  execution time"*.

Both are now word-boundary / call-shaped, and the positive half is
asserted too: what the rules bound the game by instead.

### What it costs, measured

On Royal Chess at the shipped depth the change is **free**: over five
positions from 0 to 40 plies the clocked and unclocked searches visited
**identical node counts** and chose the **identical move**, at 1.5 s to
9.4 s a move. What is removed is the busy-machine behaviour — a budget
comfortable at 9.4 s is not comfortable when the machine is four jobs
deep, and then the clock fires and the agent plays a different move for
a reason that has nothing to do with the position.

On m,n,k the change is not free, it is deeper: depth 3 everywhere
instead of 1–3, costing 1.8–2.1 s a move on 13x13 at depth 3 against
0.5 s under the old clock.

**The residual, stated rather than hidden — and it is only on one of
the two games.** Royal Chess already thinks off the UI thread
(`tests/test_async_thinking.py`, written after a reviewer found that
flip, theme, pause, undo and redo all did nothing until the computer
finished), so there the longer search costs **no responsiveness at
all**. The m,n,k window does not: it draws "thinking..." and then
blocks until the move returns, so a longer search is a longer freeze.
That is inside the one place lag is permitted — *when the computer is
thinking* — and it is bounded by a depth stepper the user controls.

**So the next change is already specified, with a precedent in the
repo:** give the m,n,k window the same treatment Royal Chess has. That
is not claimed here, and it is the one place this change leaves
something worse than it could be.

### Side effect worth naming

With no clock, `complete` is always true, so the partial-iteration
guard never fires and `abandoned` is always 0. The failure mode its
comment describes — *"a good move turned bad between two moves that
looked the same"* — is now unreachable rather than merely guarded. And
the move becomes a pure function of (position, depth, weights): the
same position gives the same move on an idle machine and a busy one.

---

## 7. The m,n,k window's blocking think — ADMISSIBLE (IDENTICAL), and shipped

**Defect, measured.** `advance()` chose and applied in one call and the
event loop called it directly, so for the whole search **no event was
read**: undo, redo, the mode buttons and the close box all did nothing
until the move landed. Royal Chess had exactly this defect and fixed it
(`src/ai_controller.py`, `tests/test_async_thinking.py`) after a
reviewer reported it; this window never got the same treatment, and §6
made its freeze **longer**.

**Class: IDENTICAL.** The same searcher runs on the same position and
returns the same move, graded by the same grader. Only *when* the loop
reads events changes. Premise discharged by comparing the two routes
move-for-move and note-for-note over several plies, with the exact
grader both switched off and switched on.

`advance()` is kept as the *composition* of begin/poll/land rather than
as a second implementation, so there is one search path and the routes
cannot drift. They are compared anyway: "they share code" is not the
same claim as "they agree".

### The order of §6 and §7 is not arbitrary, and the test proved it

Before `play_window`'s own `move_budget` default was changed from 5 to
0, the comparison **failed**: same move, `depth 2` on the blocking
route and `depth 1` in the background. The drawing loop competes for
the interpreter lock, so the clock fired a ply earlier. **Under a wall
clock this certificate does not exist** — moving the search off the UI
thread would have been a behaviour change with no admissible argument.

That is the clearest example so far of why the procedure is worth
following: the clock removal was not a prerequisite anybody reasoned
out in advance, it was a prerequisite the certificate *discovered*.

### Two slow parts, not one

The search is the obvious one. The other is `grade`, which runs an
exact solver and ran on the UI thread straight after the move. Both are
on the worker now.

### Found while doing this: GRADE_CELL_LIMIT is set past tractable

The grader's own switch is `GRADE_CELL_LIMIT = 20` empty cells.
Measured cost of one exact grade:

| board | empty cells | seconds |
|---|---|---|
| 4x4 k=3 | 12 | 0.01 |
| 4x4 k=3 | 14 | 0.41 |
| 4x4 k=3 | **16 (a full board)** | **8.98** |
| 5x5 k=4 | 14 | 2.00 |
| 5x5 k=4 | 15 | 7.72 |
| 5x5 k=4 | 16 | **over 20** |

So on the window's own default board the first agent move pays **nine
seconds** for an annotation, and on 5x5 the limit admits positions that
take minutes. The switch exists precisely to prevent this and is set to
a value where it does not. Note also that the cost depends on the board
and on `k`, not only on the cell count — 15 empty is 0.22 s on 4x4 k=3
and 7.72 s on 5x5 k=4 — so a single cell-count threshold is the wrong
*shape* of switch.

**And it was NOT "lower the number".** Lowering it removes a verdict
the window used to show, which is a trade, not a strict improvement.

## 8. The exact grade on the move's critical path — ADMISSIBLE (IDENTICAL), and shipped

**Class: IDENTICAL.** The grade is an **annotation**, not part of
choosing a move. So: compute the move, land it, show it, and fill the
verdict in when it arrives. The move played and the note *once the
verdict has landed* are the same strings as before; only the moment the
label appears changes.

Discharged by comparing the two routes on a position where the grader
actually fires — seeded down to eleven empty cells on 4x4, where a
grade costs 0.01 s against 8.98 s on a full board — and by asserting
that the verdict is **absent** from the note the instant the move
lands. Without that second assertion the test would pass just as well
if nothing had moved off the critical path.

A late verdict is spliced into the note only while the note is still
the one it is about; an undo or another ply drops it by generation,
exactly as a stale move is dropped. `advance()` still joins both
workers, so the blocking route remains the reference the certificate
compares against.

**`GRADE_CELL_LIMIT` is left at 20 on purpose.** With the annotation
off the critical path the threshold only has to stop a *runaway*
rather than hide a freeze, and leaving it alone means nothing is taken
away. It is still the wrong *shape* of switch — the cost depends on the
board and on `k`, not just the cell count — and that is recorded above
rather than fixed by guesswork.
