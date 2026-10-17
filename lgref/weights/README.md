# Learned weights

Evaluation weights produced by `lgref/experiments/bootstrap.py` and
loaded at runtime by the playable `td` agent.

These are checked in deliberately, and they are small -- they are not a
data artifact of the kind `.gitignore`'s `data/` rule is for. They are
the only reason the agent can be played without retraining it first.

## `td_royal_chess.json`

Temporal-difference bootstrapping from weights initialised to **exactly
zero**. No feature, sign or magnitude is supplied; the only label used
is the outcome at terminal states.

The payload carries four things:

| key | meaning |
|---|---|
| `weights` | the vector the agent plays with |
| `scales` | the normaliser's per-feature divisors, or `{}` |
| `effective` | `weight / scale`, the per-unit value -- the only form worth reading |
| `extractor` | which extractor the weights were trained with |

**`extractor` is load-bearing.** It drifted once and the staleness guard
caught it: the trainer moved to `with_threshold(royal_chess)`, which
renames every count to a `Has:`/`More:` pair, while the loader still
evaluated the raw extractor -- so not one weight name matched and the
agent would have played on a flat evaluation. The loader now reads this
field and refuses a file it cannot match.

## The feature parameterisation

Every count is split into two features and **the raw count is dropped**:

    Has:X     1 if there is at least one X
    More:X    how many beyond the first, max(0, X - 1)

`X == Has:X + More:X`, so nothing is lost and keeping all three would be
perfect multicollinearity.

**Why it is not a plain count.** A linear model over counts assumes
every unit is worth the same, and for a piece whose capability is gated
on having ANY of it that is false at exactly one place: zero. Going from
two bishops to one costs a little; going from one to none removes the
reactive-capture pin entirely, because no bishop is left to arm it. One
coefficient cannot be both. Measured, before the split: `Bishop`
-0.0077 per unit against `Pawn` +0.0501, so the evaluation scored "lose
a bishop, win a pawn" as **+0.047, a gain** -- and a human reported
exactly that trade as the agent's signature blunder.

The split also subsumes the old `DownToOneRoyal` indicator. For a count
over {0, 1, 2}, `Has:` and `More:` are a complete encoding, so the
conjunctive terminal condition -- the game ends when BOTH royals are
captured -- is expressible without an extra feature.

## What replicates, and what does not

**No weight is reported as a value until the same training, varied only
by seed, has produced it twice.** `experiments/replicate.py` gates on
sign agreement AND |mean| above two standard errors. Features that fail
are **UNMEASURED** -- not "zero", not "small": this procedure at this
sample size cannot say.

Two TD-root seeds, 360 games each, **37 of 82 features replicated**.
The largest that did:

    More:Royal                 +0.560     both royals alive
    Has:Rook                   +0.442
    Has:Knight                 +0.194
    Has:Flag:moved_by_queen    +0.182
    More:Rook                  +0.171
    Has:Flag:reactive_armed    +0.165     a bishop is armed to capture
    Has:Flag:moved_last_turn   -0.134
    Has:Attacked:Royal         -0.129     a royal of mine is reachable
    Has:Threatens:Knight       +0.102

**`Has:Bishop` did NOT replicate**, and this is the honest state of the
reported blunder. The two seeds came out at -0.1136 and +0.1925 -- a
sign flip, so no bishop value may be quoted at all. Yet
`Has:Flag:reactive_armed` is +0.170 and +0.160 across the same two
seeds, and `Has:Attacked:Royal` is -0.124 and -0.134. **The agent
reliably values what a bishop DOES and cannot measure what a bishop IS.**

That is consistent with two things already established: the board's
threat cache excludes bishops entirely by design, so a bishop
contributes nothing to `Covers` or `Attacked`; and under a weak policy
the value of a bishop depends on how it is used, so a trainer that
selects actions one ply generates data in which holding one does not
correlate with winning. The second is what TD-leaf addresses.

## Three dependencies that remain, by rule

    Has:FormAvailable:bishop  <->  More:Bishop      slope -1.00
    Has:FormAvailable:knight  <->  More:Knight      slope -1.00
    Has:FormAvailable:rook    <->  More:Rook        slope -1.00

A queen may take a form only once a friendly piece of that type has
been captured (RULEBOOK.md) and each side starts with two of each, so
"holds a second rook" and "has rook form available" are very nearly
complements. The learner can only ever see their difference, so
**neither weight of a pair may be quoted on its own.** Detected by
`replicate.dependent_columns`, which checks affine dependence and so
catches negation -- an identical-column check does not.

## Reproducing

    python3 <script> <seed> <out.json>      # see the run scripts
    lgref.experiments.bootstrap.run(..., searcher=...)   # TD-leaf

Grade a result against exact play with `lgref.experiments.validate` on
a solvable game -- never by the significance of its features, which says
nothing about whether the induced policy chooses well. For Royal Chess
there is no exact reference, so use the hang/miss/regret harness against
exhaustive 2-ply material truth instead.
