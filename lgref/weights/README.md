# Learned weights

Evaluation weights produced by `lgref/experiments/bootstrap.py` and
loaded at runtime by the playable `td` agent.

These are checked in deliberately, and they are small (about 1.5 KB) --
they are not a data artifact of the kind `.gitignore`'s `data/` rule is
for. They are the only reason the agent can be played without retraining
it first.

## `td_royal_chess.json`

Temporal-difference bootstrapping, 320 self-play games, weights
initialised to **exactly zero**. No feature, sign or magnitude was
supplied; the only label used was the outcome at terminal states.

`weights` are in NORMALISED units and must be used with the `scales`
saved beside them, since the normaliser divides each feature by a
running estimate of its own magnitude (without which the mobility
differential, spanning about +/-70 against +/-2 for piece counts,
swamps every other gradient).

Reproduce with `lgref.experiments.bootstrap.run`, and grade a result
against exact play with `lgref.experiments.validate` on a solvable game
-- never by the significance of its features, which says nothing about
whether the induced policy chooses well.
