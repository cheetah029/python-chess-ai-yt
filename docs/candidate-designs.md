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

### 1a. The threat level — ADMISSIBLE, and STRUCTURALLY INERT

Among moves the search values identically, prefer one that makes a
threat or removes one.

| | |
|---|---|
| **CONFINED premise** | where root values differ, the chosen move is unchanged — mechanically checkable per position |
| **MONOTONE premise** | a tie that previously picked an active move by chance now picks one whenever the tie contains one, so the active-move rate cannot fall |

**Both premises discharge, and it still does not ship, because it can
never act.** This was found by trying to discharge it rather than by
measuring it afterwards, and the argument is structural.

A move is "active" only if some winning configuration already holds
**k−2** marks. A tie at the root happens only while the line counts
have not yet separated the candidates — the first few plies, *before*
any line can hold k−2. **The two conditions are disjoint, and the rules
make them so.** Measured with the real root values at the played depth,
full window:

| board | marks | tied at the max | active among them |
|---|---|---|---|
| 19x19 k=5 | 0 | **121** | **0** |
| 19x19 k=5 | 2 | 103 | 0 |
| 19x19 k=5 | 4 | 117 | 0 |
| 19x19 k=5 | 8+ | 1–2 | 0–1 |
| 13x13 k=5 | 0–2 | 24–25 | 0 |
| 13x13 k=5 | 24+ | 1–2 | 1–2 |

**Zero of 66 positions** across four boards had a tie containing both
an active move and an inactive one. A first attempt measured the tie
set with a one-ply proxy; backed-up minimax values are coarser, so the
proxy could have understated ties, and it was redone with the real
search values.

**A certified change that does nothing is not an improvement** — the
same conclusion §3 reached about the intersection boulder.
`test_the_threat_tie_break_is_structurally_inert` records it, and
fails if a multi-way tie ever does contain an active move.

### The record was wrong, and this corrects it

`tie_breaker`'s docstring credited the threat level with recovering the
0.8-point midgame tempo loss the centrality level caused:

> *"a tie that used to pick a threatening move by chance now picks one
> whenever the tie contains one. Re-measured, tempo came back
> IDENTICAL on every seed."*

The tempo did come back identical. **The threat level cannot be why,
because it never fires.** That movement was seed noise, and the
docstring says so now. This is the third claim in this arc that turned
out to attribute a measurement to the wrong cause, after the `Line:2`
weight read from a test-written cache and the 0.9-point endgame loss
that was the crippled search.

### A redesign was built and reverted

The tie-break runs inside the root sweep, so the move it picks at depth
*d* becomes the ordering hint for depth *d+1* — which looked like a
hole in the MONOTONE premise, since a diverged search is not comparing
the same tie. Moving it out of the root and applying it once after the
last iteration closes that path, and was built.

**It cannot diverge, and the reason is exact.** The tie-break only ever
promotes a move whose value *equals* the maximum, so whichever
maximum-valued move goes first drives alpha to the maximum after one
child, and every remaining child is searched with the same window.
Identical subtrees, identical windows, identical node count —
confirmed bit-identical on 63 positions across three boards and 22 mark
counts. So the existing placement already supports the premise, and the
redesign was reverted: it changed the most dangerous file in the
project to buy a proof that was already available.

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

---

## 9. Training off the UI thread — REFUSED AT STEP 2, and the reason is the same one twice

**Defect, real.** `rebuild()` trains on Start and blocks the event loop.
It is cached per board size, so this is a first-time cost, but it is
lag *outside* thinking — the one thing the reviewer ruled out.

**The obvious design is to put it on a worker, like §7. It is not
admissible, and the measurement says why.**

`Brain.budget` is a **wall clock on training**: `run(budget_seconds=)`
"stops starting new games once the wall clock is spent, returning
whatever rounds completed". So the number of training games — and
therefore the weights the agent plays with — depends on how fast the
machine is.

**Measured at the shipped settings:** the window asks for 6 rounds ×
60 games = **360 games, and they finish in 10.7 s against a 20 s
budget**. The clock is inert here, exactly as the Royal Chess move
clock was.

**And that is precisely what blocks the change.** Training on a worker
contends with the drawing loop for the interpreter lock, which roughly
doubles its wall time — 10.7 s becomes about 21 s, which **crosses the
20 s budget and silently truncates the training**. The weights would
change. The IDENTICAL certificate does not discharge.

This is the **third** time the same dependency has appeared, and the
pattern is now worth naming: *a wall clock anywhere in the pipeline
blocks every change that alters timing*. §6 found it for the move,
§7 found it for the search thread, §9 finds it for training.

### Why the training clock is not simply removed as well

Unlike the move clock, this one has a premise outside the rules that is
real: the person is sitting in front of a setup screen. And it is doing
work for large `k` — `training_board()` keeps the board at
`min(max(k+2, 6), max(m, n))`, so k=5 trains on 7x7 however large the
played board, but **k=20 on a 20x20 board trains on 20x20**, which was
measured at 229 s before the budget existed.

So removing it is a trade, not a strict improvement, and it does not
ship on that basis. The certifiable design — not yet built — is the §6
pattern applied to training: **a game count chosen per training-board
size from a measurement**, which is deterministic and bounded, instead
of a clock that truncates by however loaded the machine is.

### What did ship: the truncation is no longer silent

A run cut short reported the count it managed — *"trained 240 games"* —
with nothing saying it was short of the 360 asked for. That reads as a
fact about the board rather than about the clock. It now says so:

> `SHORT: the 20s budget stopped this at 240 of 360 games, so these
> weights are not the ones the settings describe`

No certificate is claimed: it changes no behaviour, it reports. Tested
in both directions, because a notice that fires on a complete run is
noise nobody reads when it matters.

---

## 10. The default depth read from the board — ADMISSIBLE (MONOTONE), and shipped

**Defect, measured, and it was created by §6.** Removing the move clock
made the player deliver the depth it was configured for — and the
configured depth was **3 on every board**. On 19x19 k=5 that is
**46.70 s a move**, where the 5-second clock had been quietly
delivering depth 2 at about 1.35 s. §6 was right and it left a
residual, which is a thing to fix rather than a thing to argue away.

**Class: MONOTONE, on two quantities at once**, both against the player
as it shipped *before this session* (`--depth 3`, `--budget 5.0`):

| quantity | invariant |
|---|---|
| depth completed | `D(board) ≥` the depth the clocked player delivered, at every position on that board |
| worst move time | `≤` the clock's own budget |

The first discharges from one control-flow fact plus a cap: the clocked
player could not exceed `min(3, whatever fits in 5 s)`, because every
deadline test is a `break` and `max_depth` capped it at 3. Choosing `D`
as exactly that maximum makes the invariant an **equality** on every
board measured. The second discharges from the table.

**The cap is what keeps the argument honest.** Depth 4 fits comfortably
to 9x9 (2.76 s) and is deliberately *not* taken: raising it there would
be the "deeper is obviously better" claim this document refuses. The
change says only that the same depth now arrives in less time, constant
across the phases of a game instead of varying with them.

### The test proves the baseline is doing the work

Against the depth that was **configured** (3 everywhere) rather than
the depth the clock **delivered**, the same certificate must *fail* —
19x19 goes 3 → 2. A test that could not tell those two baselines apart
would prove nothing, so it asserts the failure as well as the success.
The whole argument turns on which baseline is honest.

### General over the board, not a lookup

`DEPTH_BY_CELLS` is keyed on the **cell count**, because in m,n,k the
cell count *is* the branching factor — a quantity the rules give rather
than one anybody supplies — and cost goes as `b ** d`. So a board
nobody has measured still lands in the right band: 15x15 and 20x20 get
depth 2 without appearing in the table.

**Weakness, stated:** the thresholds are anchored on measurements from
one machine, and a slower machine affords less. The window reports the
depth it picked, the stepper overrides it, and the depth stops
following the board the moment somebody touches it. So the number is
visible and never binding.

---

## 11. Royal Chess input lag — ADMISSIBLE (IDENTICAL), and shipped

**Defect, measured.** Thinking off the main thread stopped the window
*freezing*, but the keys were still laggy while the computer thought —
and the cause was not the threading. `show_pieces` called
`pygame.image.load(piece.texture)` for **every piece on every frame**:
a PNG decode from disk, thirty-two times a frame, plus a load and a
`smoothscale` for every overlay.

| | frame cost |
|---|---|
| idle | 5.15 ms (of which `show_pieces` is 5.57 ms) |
| while a search runs | **47.75 ms** median, 54.83 ms worst |

A key press is only noticed once the frame it is waiting behind
finishes, so **the frame cost is the input latency**.

### The two obvious knobs were measured first, and both refused

| configuration | median | worst | search time |
|---|---|---|---|
| per-frame decode (before) | 47.7 ms | 54.1 ms | 7.1 s |
| + a 16 ms frame limiter | **69.0 ms** | 78.1 ms | 6.9 s |
| + a 0.2 ms switch interval | 14.7 ms | 78.6 ms | **10.0 s** |
| **textures cached (shipped)** | **5.2 ms** | **18.2 ms** | 7.1 s |

A frame limiter makes it **worse** — the wait is added to the frame and
does not change the interpreter-lock share. A shorter switch interval
buys the median but costs the search **41% of its wall time** and
worsens the tail. Neither is the fix; a cheap frame is. *Had the
limiter been implemented on the hypothesis that it would work, it would
have shipped a regression.*

**Class: IDENTICAL**, in the strongest form available — the rendered
frame is compared **pixel for pixel** against the uncached renderer,
over four different positions, and **rendered twice with the cache** as
well, which is the failure a cache of mutable objects actually has: if
anything drew on a cached surface, the second frame would differ from
the first.

**m,n,k was checked for the same defect and does not have it:** 0.38 ms
a frame both idle and while thinking, because its fonts are cached in a
dict and it draws shapes rather than loading images. Tested anyway —
"it does not have the defect today" is only worth something if it stays
true.

---

## 12. The move clock, removed outright — ADMISSIBLE (IDENTICAL)

§6 turned the clock off. The reviewer then asked for it **gone**:

> "the clock was never a good idea in the first place because it only
> took away from the depth and unnecessarily introduced lots of bias
> and error-prone bugs with the evaluation and whatnot. It should be
> off, so you should remove it now."

**Class: IDENTICAL**, and the premise is unusually clean: with no
finite budget anywhere, every deadline test was
`time.time() >= float('inf')`, which is never true. The branches were
**dead**, and removing dead branches cannot change a decision.
Discharged by comparing chosen moves, depths reached **and node counts**
against the pre-removal implementation loaded from git.

**What went with it:** the `budget` parameter, the deadline threaded
through `_root`, `_search` and `_quiesce`, the `_OutOfTime` exception, a
`time.time()` test every 32 nodes, the partial-iteration guard and its
`abandoned` counter, the `sec/move` stepper, the `SecondsPerMove` save
field and the `--budget` flag. `_root` returns two values instead of
three. **An older save still loads** — the field is parsed and ignored,
because a reviewer's saved game from last week is not allowed to stop
opening.

**Three tests were deleted and replaced by tests that the behaviour is
gone**, and that is the honest accounting: "a 1.5 s budget is honoured",
"a bigger budget never loses depth" and "a timed-out root iteration
reports itself incomplete" all **passed**. They were testing an
operation that should not have existed. The blunder shape the last one
guarded — a good move turning bad between two positions that looked the
same — is now unreachable rather than defended against.

**What this gives up, since it was argued the other way earlier in this
session:** a timed match now needs a clock putting back. That was
weighed and the removal chosen.

---

## 13. "How long does depth 10 take?" — normal, and now on the screen

The question was whether a depth-10 move taking forever had an abnormal
cause. It does not.

| board | deepest measured | measured multiplier per ply | `√b` |
|---|---|---|---|
| 5x5 k=4 (b=25) | depth 9, **1,305 s**, 26.2M nodes | **5.8×** | 5 |
| 9x9 k=5 (b=81) | depth 6, **375 s**, 3.4M nodes | **9.6×** | 9 |

Alpha-beta costs `b**d` with no move ordering and about `b**(d/2)` with
perfect ordering, so each extra ply multiplies the work by roughly the
**square root of the branching factor**. The measured multipliers sit
just above `√b`, which means the ordering is working close to
optimally. Extrapolated depth 10: about **2 hours on 5x5** and **37
days on 9x9**.

**The defect is not the cost, it is that the stepper offered it
silently.** `estimated_move_seconds` now shows what a depth will cost
beside the depth stepper, in the colour that means "warning" past a
minute.

**Deliberately not a cap.** Capping the stepper would take away a
setting somebody might want on a tiny board, which is a trade. Saying
what it costs takes nothing away. No certificate is claimed — it adds
information and changes no behaviour — but the estimate is tested
against measurement, within 3× at every anchor from 2.76 s to 1,305 s.

### A trap the removal opened, and closed

`Searcher`'s default was `max_depth=5` with `budget=3.0`, which meant
*"up to five plies, whatever fits in three seconds"* — so five was
rarely reached and an over-large default was harmless. **With the clock
gone the depth is the depth.** Found the hard way: a test that said
`max_depth=8, budget=2.0` ran for seven minutes once the budget was
removed, because depth 8 on the case study does not finish.

So the default is now **2**, and
`test_every_searcher_names_its_own_depth` walks the AST of everything
outside the tests and fails if any construction site omits `max_depth`.
No shipped caller did, so nothing that runs changed — it turns a hang
into a shallow answer for a careless one.

**This is the general shape of the risk in removing a clock**, and it
is worth stating once: a clock is also an implicit bound, and anything
that was relying on it to stop is now unbounded. Grepping for callers
is not enough; the bound has to be written down where it was assumed.

---

## 14. The uncapped redraw loop — ADMISSIBLE (MONOTONE), and shipped

**The reviewer, twice:** *"key presses are lagging again in Royal
Chess… the only thing that should take time is the computer thinking,
and it should not interrupt the response speed of anything else."*

**I had claimed this fixed and it was not.** §11 cached the textures,
which took a frame from 5.15 ms to 2.67 ms, and I reported the lag
solved on the strength of a frame-cost measurement. That was the wrong
measurement.

### The cause is not the frame, it is the tug of war

The loop redrew **as fast as it could — 353 fps on a static board** —
and a display refreshes about sixty times a second and discards the
rest. So the loop was spending a full core on pictures nobody sees, and
taking that core from the search thread through the interpreter lock.

Median of three depth-3 searches:

| UI behaviour | the computer's move takes | fps |
|---|---|---|
| no UI thread at all | **6.86 s** | — |
| spinning, uncapped | **14.92 s** | 353 |
| capped at 60 fps | **7.45 s** | 51 |
| capped at 30 fps | 6.91 s | 26 |

**Every move took 2.2× longer because the window was redrawing an
unchanged board.** "The keys lag while it is thinking" and "the
computer is slow" were the same fault.

### Why my headless measurement said 0.0 ms

It said 0.0 ms *because the drawing thread was winning that fight* —
which is exactly why the search took 2.2× longer in the same run. On a
real display a frame also pays vsync and a window-server round trip, so
the balance tips the other way and the UI loses. **A latency
measurement that does not also report what the other thread got is
measuring one side of a tug of war.**

### The control, and it is a good one

**The m,n,k window has always capped its loop** (`pygame.time.wait(16)`)
and its frame cost does not degrade while the computer thinks: 0.38 ms
idle *and* busy. Royal Chess did not cap, and its keys were reported
laggy. The two windows differed in exactly this respect and exactly
matched the two reports.

### Class: MONOTONE, on two quantities

| quantity | direction |
|---|---|
| frames the display can **show** | unchanged — 353 and 60 are the same picture |
| search wall time per move | **down, by half** |

The 293 frames a second the cap removes are not an improvement being
traded away; they are work whose output nobody can see.

**Not a free lunch, stated:** a key press now waits up to one frame
period, 16.7 ms, where before it waited up to 2.8 ms. Both are far
below what a person perceives in an input echo — and the 2.8 ms was
bought by making the computer twice as slow.

## 15. Pausing threw the search away — fixed with it

`is_autoplay_paused()` is `is_any_menu_open()`, and the paused branch
called `abort()`. So **opening any menu discarded a search in progress,
and closing it started again from nothing** — on a nine-second search,
nine seconds lost to looking at a menu. That is what "the pause key is
laggy" was.

Holding the move back is enough, and safe without the abort, because
`finish_turn` already resolves the chosen move against **freshly
enumerated** turns and refuses it when it no longer matches. An answer
computed before an undo cannot be applied after one.

**The test that guarded this asserted the opposite and passed for the
wrong reason — twice.** It checked for the word `abort` in the paused
branch; the comment that replaced the call still mentions it, so the
test went green on prose. It now strips comments before matching, which
is what its own docstring had been warning about since the first time
this happened.
