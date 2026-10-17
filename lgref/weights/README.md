# Learned weights

Evaluation weights produced by `lgref/experiments/bootstrap.py` and
loaded at runtime by the playable `td` agent.

These are checked in deliberately, and they are small (about 1.5 KB) --
they are not a data artifact of the kind `.gitignore`'s `data/` rule is
for. They are the only reason the agent can be played without retraining
it first.

## `td_royal_chess.json`

Temporal-difference bootstrapping, 800 self-play games, weights
initialised to **exactly zero**. No feature, sign or magnitude was
supplied; the only label used was the outcome at terminal states.

`weights` are in NORMALISED units and must be used with the `scales`
saved beside them, since the normaliser divides each feature by a
running estimate of its own magnitude (without which the mobility
differential, spanning about +/-70 against +/-2 for piece counts,
swamps every other gradient). `effective` holds `weight / scale`, which
is the per-unit value and the only form worth reading.

### What this run learned (seed 71, effective units)

    Rook                  +0.552      PromotedQueen         +0.118
    Royal                 +0.447      FormAvailable:knight  -0.116
    DownToOneRoyal        -0.447      Pawn                  +0.050
    Knight                +0.214      Bishop                -0.008
    RoyalForm:Rook        +0.157      Attacked              +0.006
                                      Covers                +0.005

**Read the pair, not the parts.** `Royal` counts king plus royal queen
together and `DownToOneRoyal` is the indicator that one of them is
gone, so holding both royals is worth `+0.894` over holding one. The
indicator is there because the terminal condition is a CONJUNCTION --
you lose when both royals are captured -- and a conjunction is a
threshold, not a gradient a linear count can express.

**The two royals are one feature on purpose.** They were separate until
two trainings differing only in seed put `King` at +0.281 against
`RoyalQueen` +0.236 and then at +0.100 against +0.160: the ordering
REVERSED, so there was no per-royal fact to report. The terminal
condition is symmetric in the two, and the merged count is what the
rule actually supports.

**`Attacked` and `Covers` look negligible and are not.** These are
per-unit values and the two features range far wider than a piece
count -- coverage spans tens of squares where a rook count spans about
two -- so a weight two orders of magnitude smaller still moves the
score by about a knight. They exist to break ties, and measured at
depth 3 over 20 random midgame positions they do: 20-40 distinct values
among 50-90 legal moves, with ONE move tied for best in most positions,
against 93.7% of moves tying at the top score before they were added.
A search cannot choose where every leaf scores the same, which is what
"plays tactics, otherwise drifts" looks like from the outside.

**`Bishop` sits at zero and that is the honest answer**, not a
discovery that bishops are worthless: in this variant a queen can take
bishop form, so the second bishop adds much less than the first and a
single linear count cannot represent the step.

### Staleness

`load_royal_chess_searcher` compares the saved names against the live
feature set on its first evaluation and raises if the file is missing
any of them. A renamed feature otherwise contributes nothing and the
agent plays on with part of its evaluation silently absent -- caught in
exactly that state once, with `Royal`, `Attacked` and `Covers` carrying
no weight at all. The only fix is to retrain; failing loudly is right.

Reproduce with `lgref.experiments.bootstrap.run`, and grade a result
against exact play with `lgref.experiments.validate` on a solvable game
-- never by the significance of its features, which says nothing about
whether the induced policy chooses well.
