# Designing a change so it is strictly better

> "Any change must be extremely carefully designed in a way that
> ensures it is 100% absolutely and certainly strictly better BEFORE it
> is implemented or tested. Because relying on testing or measuring
> gates after the fact is essentially ineffective and the same as not
> making it strictly better, because you failed to design the change
> that way in the first place."
> — the reviewer, 2026-10-24

## The error this replaces

The previous workflow was: build a change, run a gate, read the result.
That is backwards, and not by a little.

**A gate is a detector.** It reports what it can see, at the power it
has, on the phases it reaches. An empty result means *nothing was
detected*, never *nothing is there*. Three times in this arc the gap
was real:

| what the gate said | what was true |
|---|---|
| tempo loss inside the noise floor | down on all four training seeds |
| 13x13 clean | the endgame band has **no samples at all**, so "clean" there means "not looked at" |
| +7.0 opening placement | measured while the change had crippled the search to depth 1 |

**ONE OF THESE EXAMPLES WAS LATER WITHDRAWN, and saying so is part
of the method.** The middle row used to read "a smaller board found a
0.9-point endgame loss", and that loss was real in the run but not
caused by the change: the tie-break's own 20x slowdown had crippled the
search, and on the repaired search the same gate reports the endgame
**identical** both ways. The lesson it was cited for survives
untouched -- a band with no samples cannot refuse on that band -- but
the instance does not, and a worked example that turns out to be an
artefact has to be corrected rather than left standing because it
argued the right way.

So: **a gate may refuse a change. A gate may never licence one.**

## The procedure, in order

Steps 1–3 happen **before any code is written**. If step 2 fails, there
is no change yet — there is an idea that needs redesigning.

**1. State the defect as a measurement.** Not "the opening is weak" but
"opening placement is 15.5% where a random player scores 50%". A defect
you cannot measure is one you cannot know you fixed.

**2. Choose the certificate class, and say how its premise will be
discharged.** One of four, and *name the premise*:

| class | the argument | the premise to discharge |
|---|---|---|
| **IDENTICAL** | same values, less cost | the outputs are equal on a wide sample of the old implementation |
| **CONFINED** | no effect outside a region fixed by the rules | the effect is exactly zero outside that region |
| **MONOTONE** | a quantity can only move one way | the invariant holds on every case, not on average |
| **UNSOUND** | removes an operation whose premise is false here | the premise fails on every case in this game |

If no class fits, **stop**. Redesign until one does, or drop it. "I
will build it and measure" is not a fourth option — it is the thing
that failed.

**3. Write the declaration down** in `DECLARED` in
`lgref/tests/test_method.py`, before implementing. The class is then
fixed, and the code has to earn it.

**4. Implement, then discharge the premise** with
`lgref/experiments/certificate.py`. Each function raises on a
counterexample rather than returning a score, because an argument with
a counterexample is not a weaker argument — it is not that argument.

**5. Only now, measure.** The gate can still refuse: a certificate
proves the change does not regress *what the certificate covers*, and a
CONFINED change still has to be good inside its region. A quiet gate
adds nothing.

## Why the declaration is separate from the proof

Checking a certificate after the code exists still lets the argument be
chosen to fit whatever the code turned out to do — *"I meant CONFINED,
I could only prove MONOTONE, so it is MONOTONE now."* That is the same
error as reading a quiet gate as a licence, one level up: the
conclusion fitted to the result instead of the work fitted to the
conclusion.

`test_every_proven_certificate_matches_the_class_it_was_designed_for`
fails on a mismatch. A change that proves a weaker argument than it was
designed for has not earned a relabelling — it has failed, and belongs
back at step 2.

## What this rules out

- Retraining a vocabulary to fix one column. Every weight moves; no
  class applies. (Tried: gained nothing, risked everything.)
- Adding a feature and racing it. No class applies. (Tried three times;
  refused three times.)
- Shipping on a gate that came back quiet. Not a licence.

## What it permits

- Speedups with equal output (IDENTICAL) — the extraction rewrite, the
  board copy, the jump.
- A term that is absent outside a rule-defined regime (CONFINED) —
  `EndgamePinned`.
- A preference that can only raise a rate (MONOTONE) — the threat level
  of the tie-break.
- Deleting an unsound optimisation (UNSOUND) — futility pruning in a
  game with no captures.

---

## Search depth is a change like any other, and a harder one

**A depth change is not admissible on its own.** It alters the move
chosen in a great many positions, so none of the four classes applies:
not IDENTICAL, not CONFINED, not MONOTONE, not UNSOUND. "Deeper is
obviously better" is an intuition, not a certificate, and this project
has measured it failing — the handoff records a change that helped at
depth 2 and hurt at depth 3, and a reviewer position where depth 2
saved a bishop that depth 3 gave away.

What *is* admissible is removing a heuristic whose premise is false
(UNSOUND) or making the same search cheaper (IDENTICAL). Both buy
depth as a *consequence* rather than claiming it as an argument.

### Depth must be constant within a game

**Measured on 13x13 k=5 under a five-second clock:**

| board state | legal moves | depth reached |
|---|---|---|
| 2 marks (opening) | 167 | **3** |
| 20 marks (midgame) | 149 | **6** |
| 60 marks (endgame) | 109 | **10** |

Iterative deepening under a wall clock gives a depth that rises as the
branching falls. That is not a tuning detail, it has two consequences:

1. **The player is a different player in each phase.** An agent that
   searches three plies in the opening and ten in the endgame cannot be
   reasoned about as one thing, and "it got worse" cannot be localised.

2. **It confounds every per-phase measurement.** A gate that reports
   opening, midgame and endgame numbers under a clock is comparing an
   agent at three different depths. The endgame band was searched seven
   plies deeper than the opening band — so any phase-to-phase reading
   from those runs, including "placement declines toward indifference
   late in the game", partly measures the search and not the agent.

**The standard, from here:**

- **Measurement runs fix the depth**, so phases are comparable. There
  is nothing left to set: the per-move clock was removed from the
  searcher outright on 2026-10-25 (`candidate-designs.md` §12), so the
  depth is the depth everywhere.
- **The player runs at constant depth too, and this is now the
  default** — with a certificate, not with "constant is nicer". The
  justification it needed turned out to be an UNSOUND one, and it is in
  `candidate-designs.md` §6: a wall clock is an operation whose premise
  is that the GAME constrains move time, and neither game here does.
  Both are bounded in plies and the game description carries no time
  term, so a number of seconds is hand-supplied — bias, by this
  project's own definition.
- **A clock can only ever take depth away.** Every deadline test in the
  search is a `break`, a `raise` or a `complete = False`, never an
  extension of `range(1, max_depth + 1)`. So the iterations a clocked
  search completes are a PREFIX of the iterations it completes without
  one, at every position, on every board, under every load. That is
  what makes removing it admissible while *raising* the depth would not
  be: the configured depth is untouched.
- A per-move clock and a per-game constant depth are different
  products. Choose one deliberately and record which. The clock is
  kept, not deleted — a timed match is a real context — but it has to
  be asked for.

### Deeper IS better here — at constant depth

The puzzle was real and the answer is not exotic. Measured on 5x5 k=4,
fixed depth, forty paired games each with colours alternating:

| matchup | result |
|---|---|
| depth 1 vs depth 2 | **0 – 24**, 16 drawn |
| depth 2 vs depth 3 | 5 – 11, 24 drawn |
| depth 1 vs depth 3 | **1 – 36**, 3 drawn |

Depth 1 did not beat depth 2 once in forty games. **So the worsenings
were never about depth — they were about the clock**, which turns
"raise max_depth" into "spend the same seconds differently and leave
the last iteration partial", with the depth actually reached varying by
phase.

### What constant depth costs

Worst observed move time with no clock:

| board | depth 2 | depth 3 |
|---|---|---|
| 9x9 | 0.1 s | 1.0 s |
| 13x13 | 0.3 s | **11.4 s** |
| 19x19 | **2.0 s** | **73 s** |

So constant depth is affordable, but the depth has to be chosen per
board rather than left to a clock: depth 3 is comfortable to 9x9,
marginal at 13x13 and unusable at 19x19. The honest configuration is a
fixed depth per board size, not a fixed number of seconds.

**THAT TABLE IS SUPERSEDED.** It was taken while this machine was
running four jobs at 95% CPU on ten cores, and every number in it is
2–3× too high. Re-measured on a quiet machine with the **shipped**
evaluation and the shipped search settings — futility and late-move
reduction are both off for m,n,k now, which makes the tree *bigger*, so
this is not simply the old table scaled:

| board | depth 2 | depth 3 | depth 4 |
|---|---|---|---|
| 5x5 k=4 | 0.00 s | 0.03 s | 0.07 s |
| 7x7 k=4 | 0.01 s | 0.17 s | 0.88 s |
| 9x9 k=5 | 0.04 s | **0.48 s** | 2.76 s |
| 13x13 k=5 | 0.15 s | **4.02 s** | 17.03 s |
| 19x19 k=5 | 1.35 s | **46.70 s** | 218.83 s |

Worst case over five positions per board, from an empty board to 30
marks. The medians are lower (13x13 depth 3 is 3.42 s, 19x19 depth 3 is
36.07 s) but a product limit has to be built on the worst case.

**So depth 3 is comfortable through 13x13 and unusable on 19x19**, and
depth 4 is affordable up to 9x9 — none of which could be said from the
contended table, which had 13x13 depth 3 at 11.4 s. The lesson is the
one `feedback_measurement_discipline.md` already carries: a timing
number taken on a loaded machine is not a timing number.

**WHY A SINGLE CONSTANT DEPTH CANNOT DOMINATE A CLOCK.** This bounds
what can ever be claimed here, so it belongs in writing. A clock spends
its seconds where they are cheap, so it reaches its *greatest* depth in
the LATEST positions, where the branching has collapsed. A constant `D`
that is at least as deep as the clock everywhere must therefore be at
least the clock's endgame depth — 10 on 13x13 — and paying that in the
opening is unaffordable. So "constant depth beats the clock at every
position" is **false for any affordable D**, and that is not the
argument. The admissible argument is that the clock had no premise in
the first place: it was reducing the configured depth, and removing it
delivers the configured depth. Two different claims, and only the
second is certifiable.

### Why "deeper" can be worse, concretely

Two mechanisms, and only the second is exotic:

- **The clock, now removed.** Under a budget, "increasing max depth"
  did not deepen the search; it spent the same seconds differently and
  left the final iteration partial. That mechanism no longer exists —
  but it is kept here because it is the one that actually explained the
  worsenings, and because the lesson generalises: **an implicit
  resource bound anywhere in the pipeline makes every timing-sensitive
  change uncertifiable, and silently changes what is being measured.** *(Checked here: on 13x13 the hurried
  answer matched the complete search at the depth it reached in 14 of
  14 positions, so the partial-iteration guard is NOT the mechanism —
  recorded as a negative result rather than a suspicion.)*
- **Minimax pathology.** With an evaluation whose errors are largely
  independent across leaves, deeper minimax can amplify error rather
  than cancel it. That is a property of the evaluation, not a bug in
  the search, and the remedy is a better evaluation — not more plies.
