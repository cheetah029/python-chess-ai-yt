# Learned weights

Evaluation weights produced by `lgref/experiments/bootstrap.py` and
loaded at runtime by the playable `td` agent. Checked in deliberately
and small -- they are the only reason the agent can be played without
retraining it first.

## `td_royal_chess.json`

Temporal-difference bootstrapping from weights initialised to **exactly
zero**. No feature, sign or magnitude is supplied; the only label used
is the outcome at terminal states. **Averaged over five seeds**, 800
self-play games each.

Five rather than two because seed variance, not feature choice, turned
out to be the dominant error here -- see "Why averaging, not features"
below. The five-seed average beat the two-seed one 18-13 with 9 drawn
over 40 games, and played 2 self-captures against its 8.

| key | meaning |
|---|---|
| `weights` | the vector the agent plays with |
| `scales` | the normaliser's per-feature divisors, or `{}` |
| `effective` | `weight / scale`, the per-unit value -- the only form worth reading |
| `extractor` | which extractor the weights were trained with |
| `drop_prefixes` | feature families ablated at training time |
| `dropped` | individual columns the decorrelation pass removed |

**The last three are load-bearing.** The loader reconstructs the exact
feature set the weights were fitted on rather than assuming it. Every
one of those fields exists because the loader and the trainer diverged
at least once and the staleness guard caught it -- five times in one
session, including a case where the loader was evaluating a completely
different extractor.

## What it learned

Per-unit, averaged over five seeds, with the ratio to a pawn:

    Royal    +0.684   10.2 pawns      Bishop   +0.069    1.0 pawns
    Rook     +0.337    5.0 pawns      Pawn     +0.067    1.0 pawns
    Knight   +0.085    1.3 pawns

Every material count is positive in all five seeds and the knight lands
on 0.080, 0.088, 0.083, 0.091, 0.084 -- stable to the third decimal.

**The knight is stably LOW, and I believe that is wrong.** A radius-2
piece with jump-capture and invulnerability is not worth one and a
third pawns. But it is not noise, and the honest reading is that TD
self-play learns how much a piece correlates with winning GIVEN HOW
THIS POLICY USES IT -- and a weak policy does not exploit knights.
Training with search in the loop is what should move it.

## Why averaging, not features

The version before this one priced a knight at 4.3 pawns and a bishop
at -0.2, and a human reported it giving away bishops. This one prices a
bishop properly and a knight at 1.3, and the same human reported it
giving away knights. Over seventy games the two drew EXACTLY: 27-27
with 16 drawn.

Retraining the OLDER feature set at a fresh seed settled why:

    ratio to a pawn   old seed 71   old retrained   this, 5 seeds
    rook                     11.0             4.5             5.0
    knight                    4.3            -0.3             1.3
    bishop                   -0.2             0.6             1.0

The old set's sensible knight was a SEED ARTIFACT -- the same features
at another seed price a knight below zero. Neither feature set was
better; each was wrong about a different piece, by chance. That is why
seed variance is the thing being attacked here and not the feature
list.

## Measured strength

Exhaustive 2-ply material truth over 40 positions. `hangs` is moving so
material can be taken; `misses` is material that was winnable and was
not taken, out of the 28 positions where any was.

| | hangs | misses | mean regret |
|---|---|---|---|
| previous weights, depth 3 | 1/40 | 8/28 | 0.23 |
| **this, depth 2** | **0/40** | **3/28** | **0.07** |
| **this, depth 3** | **0/40** | **6/28** | **0.15** |

## The reported blunder

A human reported the agent trading bishops for pawns:
`5. Pe2-e3 Bh5xe3 6. Pd2xe3`. White's pawn began its move on e2, on the
h5 bishop's diagonal, which armed the reactive capture; the bishop
teleported onto e3, and reactive capture does not apply the
teleport-safety check, so it landed on a square the d2 pawn covered.

The search saw the recapture. The evaluation liked the result:

    give up a bishop, win a pawn      then      now
    one of two bishops (2 -> 1)     +0.047    -0.043
    your LAST bishop (1 -> 0)       +0.047    -0.043

`Bishop` was -0.0077 and is now +0.123, positive in both seeds. The
margin is thin -- a bishop is priced at about one and a half pawns,
which is low for a piece with global teleport and a pin -- but the sign
is right and it replicates.

## Three things that made it worse, and what they cost

Recorded because each looked like an improvement in a weight table and
was a regression in play.

1. **A threshold split that dropped the count.** Replacing each count
   with `Has:X` and `More:X` prices zero, and moves almost all the
   weight onto a feature that cannot change while you still hold one.
   Losing one of two rooks went from costing 0.552 to 0.171, a knight
   5.2x weaker. Misses 8/28 -> 14/28, regret 0.23 -> 0.47. The count is
   kept now, with `Missing:X` added beside it.

2. **Relational and flag families.** `Attacked:I`, `Hanging:I`,
   `Threatens:I` and `Flag:*` were added to fix "the agent misses
   winnable material" and were the reason it missed winnable material:
   42 of 67 weights, outvoting the material they were meant to support,
   with `Flag:moved_by_queen` at +0.217 against `Knight` at +0.180 and
   `Pawn` collapsed to +0.0007. Zeroing them at play time, changing
   nothing else, took regret from 0.47 to 0.28. They are ablated via
   `drop_prefixes` and remain available for research.

3. **Draws discarded as censored.** `winner is None` is true both for a
   game the ply cap cut off and for one that ended level, and both were
   thrown away. A truncation has no result to teach; a draw does. On a
   20x20 board needing 20 in a row the learner produced a weight vector
   with zero features in it. Telling them apart needs the legal-move
   set, since an engine reports itself over on its own turn cap too: a
   real draw has no legal turn left.

## Reproducing

    lgref.experiments.bootstrap.run(...)                  # TD-root
    lgref.experiments.bootstrap.run(..., searcher=...)    # TD-leaf

Grade against exact play with `lgref.experiments.validate` on a
solvable game -- never by the significance of a feature, which says
nothing about whether the induced policy chooses well. Royal Chess has
no exact reference, so use the hang/miss/regret harness instead, and
**run it before believing a weight table.** That is the lesson of all
three items above.
