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
