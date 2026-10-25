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
