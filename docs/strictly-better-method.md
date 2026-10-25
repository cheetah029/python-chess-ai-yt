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
| 13x13 clean | the endgame band has **no samples at all**; a smaller board found a 0.9-point loss |
| +7.0 opening placement | measured while the change had crippled the search to depth 1 |

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

- **Measurement runs fix the depth** (`budget=float('inf')`), so phases
  are comparable. Both gate tools now do.
- **The player should run at constant depth too.** Setting sec/move to
  `0` already does this — it removes the clock and the depth is exactly
  the depth. Making that the *default* is a behaviour change and needs
  its own justification; it is not smuggled in under a speed fix.
- A per-move clock and a per-game constant depth are different
  products. Choose one deliberately and record which.

### Why "deeper" can be worse, concretely

Two mechanisms, and only the second is exotic:

- **The clock.** Under a budget, "increasing max depth" does not
  deepen the search; it spends the same seconds differently, and the
  final iteration is partial. *(Checked here: on 13x13 the hurried
  answer matched the complete search at the depth it reached in 14 of
  14 positions, so the partial-iteration guard is NOT the mechanism —
  recorded as a negative result rather than a suspicion.)*
- **Minimax pathology.** With an evaluation whose errors are largely
  independent across leaves, deeper minimax can amplify error rather
  than cancel it. That is a property of the evaluation, not a bug in
  the search, and the remedy is a better evaluation — not more plies.
