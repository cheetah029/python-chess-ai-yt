# Session handoff, 2026-10-24

Supersedes `session_handoff_2026-10-20.md` for issue #278.

---

# READ THIS FIRST: a change ships on a proof, not on a quiet gate

**`docs/strictly-better-method.md` is the procedure. Follow it before
writing any code.** `docs/candidate-designs.md` applies it to every
planned change. `lgref/experiments/certificate.py` is the machinery and
`lgref/tests/test_method.py` enforces it.

The reviewer's correction, and it is right at the root:

> "I am asking for strict improvement, not overall improvement. If even
> a single thing is worse, the change cannot be shipped. So using gates
> to 'test' for strict improvement is wrong in and of itself. What
> needs to be done from the start is to design the methodology of
> building the change so that it is certainly strictly better."

**A gate is a detector.** It reports what it can see, at the power it
has, on the phases it reaches. An empty result means *nothing was
detected*, never *nothing is there*. Three times this week the gap was
real:

| the gate said | the truth |
|---|---|
| tempo loss inside the noise floor | down on all four training seeds |
| 13x13 clean | its endgame band has **no samples at all**; 5x5 found a 0.9-point loss |
| +7.0 opening placement | measured while the change had crippled the search to depth 1 |

**A gate may refuse a change. It may never licence one.**

What licenses one: a certificate, **declared before the code and proven
after**, in one of four classes — IDENTICAL (same values, less cost),
CONFINED (no effect outside a rule-defined region), MONOTONE (a
quantity can only move one way), UNSOUND (removes an operation whose
premise is false here). **A proven class that differs from the declared
one is a failure, not a relabelling**, and a test enforces that.

---

## What is shipped, and its certificate

| change | class | premise discharged against |
|---|---|---|
| `features.mnk` extraction | IDENTICAL | the pre-rewrite code recovered from git; 60 positions, six boards |
| `Game._deep_copy_board` | IDENTICAL | state hash over 12 snapshots |
| `Game.jump_to_start/end` | IDENTICAL | stepping all the way |
| futility via `has_tactics` | UNSOUND | premise false in m,n,k, true in the case study |

**Off, each with an entry rather than silence:** the m,n,k tie-break
(`TIE_BREAK_ENABLED = False`), `Reach`, the intersection boulder,
`EndgamePinned`, `BoulderPressure`.

---

## The three bugs fixed this session, and why they mattered

**1. Futility pruning in a game with no captures.** It assumes a quiet
move cannot change the score. m,n,k turns are plain integers with no
`is_capture`, so *every* move counted as quiet: the guard pruned 305
moves **including the block**, and a "complete" depth-2 search in 1131
nodes chose to lose a mate-in-one. This predates all of this week's
work. Now detected, the way undo support is.

**2. The extractor built a `Counter` per winning line** — 1,020 per
evaluation on 19x19, 70% of the cost. 1.32 ms → 0.23 ms, output
identical.

**3. My own tie-break was a 20× slowdown** — `threat_count` rescans
every legal move, so ranking one candidate cost 0.108 s and a root
sweep 9.74 s against 0.47 s. The search could not finish one ply, so
the agent played the best of an arbitrary partial set and stopped
opening in the centre. **The fix for the opening was breaking the
opening.**

| the reviewer's position | before | after |
|---|---|---|
| plays | 8,12 (loses) | **11,14 (blocks)** |
| depth reached | 1 | **2** |
| nodes in 5 s | 641 | **8032** |

**Depth is the lever.** Nothing in the evaluation changed.

---

## Open defects, measured

**m,n,k**
- **Opening placement 15.5% on 13x13** where random scores 50%. The
  only known fix (centrality tie-break) is **not certifiable** — see
  `candidate-designs.md` §1b.
- **`Line:1` ≈ `Line:2`** (+0.1199 vs +0.1249): the evaluation values
  touching many lines as much as building along one. Refitting `Line:2`
  alone against random playouts gives +0.0012 — *worse* — because
  random play neither builds nor punishes failing to build. The signal
  is absent from the distribution, not mis-weighted.
- **`Marks` = −0.1283 is a disguised turn indicator**, not a claim that
  stones are bad: the mark differential is fixed by whose turn it is,
  so the column is collinear with side-to-move.
- 19x19 runs on 7x7-trained weights.

**Royal Chess**
- **Boulder long-term pressure.** Pawns lost within 12 plies by
  distance: 44% / 35% / 29% / 28% / 25% / 11% / 0%. Everything from
  distance 2 is past the horizon (cooldown = one boulder move per three
  plies). `BoulderPressure` is **not certifiable** as an evaluation
  term.
- **The bishop pin.** Three attempts, three refusals: inert feature,
  worthless retrain, real-but-too-small term (−0.0187, raced 30–30).
  `Pinned` trains to ±0.00 on 9,706 observations because self-play
  never converts a pin.
- **Blunders at the reviewer's moves 14–15** (knight for pawn, bishop
  for pawn) — not yet diagnosed.

---

## The productive direction

Two classes discharge easily and both buy **depth**, which is what
measurably fixed the blunder:

- **IDENTICAL speedups.** Three shipped. More available.
- **UNSOUND removals.** One shipped. **Not yet checked: late-move
  reduction, `reduce_turns`, quiescence** — each rests on a
  quiet/forcing distinction m,n,k does not have. These are the next
  thing to examine.

---

## Runs in flight at handoff

- **Re-gate** of the tie-break on 5x5 and 13x13 against the repaired
  search. Every earlier m,n,k gate number was measured on the crippled
  search and is void. Note that even a clean result **cannot licence**
  the tie-break — see §1b.
- **Boulder race** at depth 3, `current 3 – 4 rival, 2 drawn` after 9
  of 24 games.

## Hygiene fixed

- Test runs no longer write weight caches into the repository
  (`MNK_CACHE_DIR` + a session fixture). A test-written file had been
  picked up by a tool and produced a **published wrong diagnosis**
  (`Line:2 = −0.0347` from an agent nobody plays).
- Tools ask the `Brain` for its cache key instead of globbing.
- Git has no configured identity on this machine; commits use
  `-c user.name/user.email` matching the existing history.

---

## Later the same day: the three heuristics, and the depth answer

**Late move reduction — UNSOUND, removed for m,n,k.** Declared before
the code, proven after. Its premise is a claim about the ordering, and
measured on 9x9 k=5 over 116 positions the ordering carries no
information: the best move sits at mean position **0.528** (0.5 = none),
reaches the first quarter **6.0%** of the time against a 25% baseline,
and falls in the reduced region **97.4%** of the time. The case study
still reduces — nothing removed there.

**`reduce_turns` and quiescence — INERT, not unsound.** `reduce_turns`
is injected and the window never injects it; quiescence is passed 0 and
returns immediately with no tactical turns. Neither needs removing
because neither runs.

**Depth: the puzzle is solved, and it was the clock.** At constant
depth, deeper is reliably better on 5x5 — depth 1 vs 2 is **0–24**,
depth 1 vs 3 is **1–36**. Depth 1 never beat depth 2 in forty games.

**But under a clock the depth varies by phase**: on 13x13 in five
seconds it is 3 at two marks, 6 at twenty, 10 at sixty. That makes the
player a different player in each phase **and confounds every
per-phase number in this handoff** — the endgame band was searched
seven plies deeper than the opening band. Both gate tools now fix the
depth; the earlier per-phase readings (including "placement declines
late in the game") partly measured the search.

**Constant depth costs**, worst observed move time with no clock:

| board | depth 2 | depth 3 |
|---|---|---|
| 9x9 | 0.1 s | 1.0 s |
| 13x13 | 0.3 s | 11.4 s |
| 19x19 | 2.0 s | 73 s |

So the standard going forward is a **fixed depth chosen per board
size**, not a fixed number of seconds. Making that the player's default
is a behaviour change and needs its own justification — it has not been
done, and is the next decision to take.

**A negative result kept on purpose:** the partial-iteration guard was
suspected and cleared — on 13x13 the hurried answer matched the
complete search at the depth it reached in 14 of 14 positions.


---

# 2026-10-25: the clock had no premise, and the runs reported

## Shipped: the move clock is gone from both players

`candidate-designs.md` §6 has the full argument. In short: a per-move
wall clock is an operation whose premise is that the GAME constrains
move time, and neither game here does — both are bounded in plies, the
game description has no time term, and neither engine's termination
predicate reads a clock. **UNSOUND**, declared before the code.

| player | was | now |
|---|---|---|
| m,n,k window | depth 3, 5 s clock → delivered 3 / 2 / 1 | depth 3, always |
| Royal Chess `td` | depth 3, 30 s clock → never fired | depth 3, always |
| `race_agents.py` | 30 s clock | no clock |
| `race_endgames.py` | 10 s clock | no clock |

**It is not the "deeper is better" argument.** The configured depth is
untouched. Every deadline test in the search is a `break`, a `raise` or
a `complete = False` — never an extension of `range(1, max_depth + 1)`
— so a clock can only ever take depth *away*. Checked as a property.

**Royal Chess measurement: identical node counts and identical moves**
in 5 of 5 positions from 0 to 40 plies, 1.5–9.4 s a move. The clock
never fired on an idle machine; what is removed is the busy-machine
behaviour. **And this machine has been busy for seven days** — two
stale scratchpad jobs from earlier arcs (`mnk_sizes.py`, 7 d;
`mnk_optimal.py`, 4 d) have been holding two cores at 95%. So the
move-14/15 blunders now have a concrete candidate mechanism: a 30 s
budget on a position that needs 9 s idle will fire under 4× load, the
search drops a ply, and the agent plays a knight-for-pawn for a reason
that has nothing to do with the board. **Not yet confirmed** — it needs
the position, and it is the next diagnostic.

**One residual, on one game only.** Royal Chess already thinks off the
UI thread (`tests/test_async_thinking.py`). The m,n,k window blocks, so
its permitted thinking-freeze got longer. **Giving m,n,k the same
treatment is the next change, and removing the clock is what makes it
certifiable as IDENTICAL** — with a clock, moving the search to a
worker would have changed its timing, hence its depth, hence its move.

## The two runs, reported

**Boulder race, 21 of 24** (`depth 3`, 30 s clock, so confounded by the
above): base **3 – 13** base+`BoulderPressure`, 5 drawn. Verified
attributable: the two weight files differ in exactly one column
(`BoulderPressure = −0.021285`), all 19 shared weights and all scales
identical.

**A 13–3 win does not ship it.** §5 stands: no certificate class
applies, because the column speaks at every distance ≥ 2 and the
boulder is almost always ≥ 2 from a pawn. What the race does establish
is that the defect is worth a *certifiable* attack — it is the largest
single-column effect measured in this arc. It stays off.

**Re-gate of the tie-break against an independent ruler** — and this is
the number that matters, because the earlier 13x13 run shared its prior
with the agent:

| | plain | tie-break |
|---|---|---|
| 13x13 seed 11 | 11.6% | 13.2% |
| 13x13 seed 23 | 27.2% | 50.4% |
| 13x13 pooled (plain) | **15.5%** | 2 of 4 seeds in |
| 5x5 seed 11 | 95.0% | pending |
| 5x5 seed 23 | 90.8% | pending |

Seed 11 gains **1.6 points**, inside a 2-SE floor of about 1.7 on
n=1500. Seed 23 gains **23.2**. That spread across training seeds is
the variance this handoff already records as swamping feature-set
differences — and it is why §1b's refusal does not depend on the
result: the centrality level has no MONOTONE invariant, so a clean
re-gate still could not licence it. It stays off.

**Both runs were measured on a contended machine**, and the boulder
race's game 12 alone took 20,000 s against ~450 s for games 1–11. Game
results are unaffected by load; every TIMING number in this handoff is
an upper bound.

---

# 2026-10-25, later: the GUI lag, and both gates complete

## Shipped, each on a certificate declared before the code

| change | class | §  |
|---|---|---|
| the move clock removed from both players | UNSOUND | 6 |
| m,n,k window thinks off the UI thread | IDENTICAL | 7 |
| the exact grade off the move's critical path | IDENTICAL | 8 |

**The order of §6 and §7 was discovered by the certificate, not
reasoned out in advance** — and this is the best evidence yet that the
procedure earns its cost. The §7 comparison *failed* at first: same
move, `depth 2` blocking and `depth 1` in the background, because
`play_window` still had its own `move_budget=5` default and the drawing
loop competes for the interpreter lock, so the clock fired a ply
earlier. **Under a wall clock the §7 certificate does not exist.**

**Two lag defects found, both pre-existing, both measured:**

1. The window read no events for the whole search — undo, redo, the
   mode buttons and the close box all dead. Royal Chess fixed this
   after a reviewer reported it; m,n,k never got the same treatment.
2. `grade` runs an exact solver *after the move is already chosen*, so
   the move could not appear until the label did: **8.98 s on a full
   4x4 board, which is the board the window opens at**; 7.72 s at 15
   empty cells on 5x5 and over 20 s at 16. `GRADE_CELL_LIMIT = 20`
   exists to prevent exactly this and is set well past tractable — and
   it is the wrong *shape* of switch, since 15 empty costs 0.22 s on
   4x4 k=3 against 7.72 s on 5x5 k=4.

   It is **left at 20 on purpose**: lowering it removes a verdict the
   window used to show, which is a trade. With the annotation off the
   critical path the threshold only has to stop a runaway.

**Still blocking, and the next candidate:** `rebuild()` trains on
Start. It is cached per board size, so this is a first-time cost, but
its own comment records twenty seconds on a 10x10 — and that is lag
*outside* thinking, which is the one thing the reviewer ruled out.

## The boulder race, final

**base 4 – 14 base+`BoulderPressure`, 6 drawn, of 24.** Of 18 decisive
games that is 14–4, p ≈ 0.015 one-sided. Attribution verified: the two
weight files differ in exactly one column
(`BoulderPressure = −0.021285`), with all 19 shared weights and all
scales identical.

**It does not ship.** §5 stands — the column speaks at every distance
≥ 2 and the boulder is almost always ≥ 2 from a pawn, so it is not
CONFINED, and no other class applies. A race win is not a certificate.
What the race establishes is that this is **the largest single-column
effect measured in the arc**, so the defect deserves a certifiable
attack rather than being dropped.

**And the race itself was confounded**: it ran under a 30-second clock,
so it compared two agents at depths that varied by position and by
machine load, and games 12–16 ran while the machine was several jobs
deep. Both race tools now race with no clock.

## The re-gate, complete

Against an **independent** ruler, which is the number that counts —
the earlier 13x13 run shared its prior with the agent and reported
66.7%:

| 13x13 k=5 | plain | tie-break |
|---|---|---|
| seed 11 | 11.6% | 13.2% |
| seed 23 | 27.2% | 50.4% |
| seed 37 | 11.6% | 13.2% |
| seed 53 | 11.6% | 13.2% |
| **POOLED** | **15.5%** | **22.5%** |

`sharp`, `forced` and `tempo` are **identical** to the decimal
(94.8 / 100.0 / 71.3 both ways). The endgame band has **no samples at
all** on this board, and the gate's verdict is therefore
**NOT STRICTLY BETTER — endgame unmeasured**, which is the gate
correctly refusing to treat "could not look" as "nothing there".

The pooled +7.0 is almost entirely one training seed: three seeds move
11.6 → 13.2 (1.6 points, inside a ~1.7-point 2-SE floor) and seed 23
moves 27.2 → 50.4.

On 5x5, where the endgame *is* measurable, plain pools to 61.2% and the
tie-break's first seed comes in at **94.9% against plain's 95.0%** —
slightly down, where the circular prior had reported 98.9%.

**Both roads end in the same place, which is the useful part:** §1b
refuses the tie-break on design grounds (the centrality level has no
MONOTONE invariant), and the gate refuses it on measurement grounds.
It stays off.

---

# 2026-10-25, end of session: the depth default, and a table that was wrong

## §10 shipped: the board chooses the depth

**§6 created this defect and §10 closes it.** Removing the move clock
made the player deliver its configured depth — and that was **3 on
every board**. On 19x19 k=5 depth 3 is **46.70 s a move**, where the
5-second clock had been delivering depth 2 at about 1.35 s.

**MONOTONE on two quantities at once**, against the pre-session player
(`--depth 3`, `--budget 5.0`): the depth is `≥` what the clock
delivered (an *equality* on every board measured) and the worst move
time is `≤` the clock's own budget. Capped at the old `max_depth` on
purpose — depth 4 fits to 9x9 and taking it would be the "deeper is
obviously better" claim the method refuses.

`DEPTH_BY_CELLS` is keyed on the **cell count**, which *is* the
branching factor in this game, so an unmeasured board still lands in a
band. The depth stops following the board once the stepper is touched.

| board | depth chosen |
|---|---|
| 4x4 → 13x13 | 3 |
| 15x15 → 20x20 | 2 |

**The test asserts the certificate FAILS against the wrong baseline** —
the depth that was *configured* (3 everywhere) rather than *delivered*
— because 19x19 goes 3 → 2 on that reading. The whole argument turns on
which baseline is honest.

## The cost table in the method doc was contention, and is replaced

Every number in the old table was **2–3× too high**: 13x13 depth 3 was
published as 11.4 s and is **4.02 s**. Re-measured on a quiet machine
(the reviewer killed two stale multi-day jobs) with the **shipped**
evaluation and the shipped search settings — futility and LMR both off
now, which makes the tree *bigger*, so this is not the old table
scaled:

| board | depth 2 | depth 3 | depth 4 |
|---|---|---|---|
| 5x5 k=4 | 0.00 s | 0.03 s | 0.07 s |
| 7x7 k=4 | 0.01 s | 0.17 s | 0.88 s |
| 9x9 k=5 | 0.04 s | 0.48 s | 2.76 s |
| 13x13 k=5 | 0.15 s | 4.02 s | 17.03 s |
| 19x19 k=5 | 1.35 s | 46.70 s | 218.83 s |

**Any timing number in this arc taken before 2026-10-25 is suspect.**
The machine had been several jobs deep for a week.

## The pattern this session established

**A wall clock anywhere in the pipeline blocks every change that alters
timing.** Found three times, each time by a certificate refusing to
discharge rather than by foresight:

| § | where | what it blocked |
|---|---|---|
| 6 | the move | the player delivering its configured depth |
| 7 | the search thread | moving the search off the UI thread |
| 9 | training | moving training off the UI thread |

§9 is still **refused**: training on a worker roughly doubles its wall
time (10.7 s → ~21 s), which crosses the 20 s training budget and
silently truncates it. The training clock is not simply removed with
the others, because its premise is real — somebody is at a setup screen
— and it does work at large `k`, where `training_board()` stops
shrinking. The certifiable design is §6's pattern applied to training:
a game count per training-board size, from a measurement.

## Where the gates stand

**5x5 re-gate, against the independent ruler** (two of four seeds):

| 5x5 k=4 | plain | tie-break |
|---|---|---|
| seed 11 | 95.0% | **94.9%** |
| seed 23 | 90.8% | **91.2%** |

Flat — ±0.4 either way, both inside the floor. The circular prior had
reported these same two seeds as 98.9% and 98.1%, which is the clearest
single measurement of how much that confound was inflating.

## Next, in order

1. **Royal Chess moves 14–15.** The load-plus-clock mechanism is now a
   concrete candidate (a 30 s budget on a position needing 9 s idle
   fires under 4× load and drops a ply) but it needs the position.
2. **`BoulderPressure`** — 14–4 in the race, the largest single-column
   effect in the arc, and still uncertifiable. Needs a rule-defined
   region, and the rules do not obviously supply one.
3. **§9**, with the training clock replaced by a per-board game count.
4. **m,n,k opening placement 15.5%** on 13x13, still open; the only
   known fix is still not certifiable (§1b).
