# Paper A: the POST-FREEZE variant, terminal edge off (#394)

**POST-FREEZE.** This is not the frozen method. The frozen method is
production LGREF at `ab7b33b` (`freeze.md`). Its numbers are not
replaced here, only shown beside the variant's.

**Why the variant exists.** On the revised development reference
sheets, turning off the terminal edge beat production beyond its
interval: +0.045 BCubed F1 [0.003, 0.090]. That metric is subjective,
and the result appeared only after the freeze. The user decided on
2026-11-27 that it should be run and reported.

**What it is.** `lgref.bench.methods.lgref_postfreeze_noterminal`:
production LGREF with the terminal edge weight set to 0 and nothing
else changed. The resolution rule, overlap step and intervention
procedure are as frozen. The variant is kept outside `METHODS`, so no
default run, and no frozen result, includes it.

**Definitions** (as in `protocol.md`):
- Each rule is scored on its closest ablation: the valid, changing
  intervention with the fewest atoms differing from the reference
  ablation.
- *Exact*: 0 differing atoms.
- *Breakage*: collateral > 0.
- *Fragility*: other reference rules damaged, per ablation.
- *Consistency*: BCubed F1 between the grouping of a description and of
  each behaviour-preserving rewrite.
- *Metric 10*: the closest ablations rebuilt on each rewrite.

## Development set

| metric | procedure | FROZEN lgref | POST-FREEZE terminal-edge-off |
|---|---|---|---|
| rules with a valid ablation | ownership | 10 / 12 | 10 / 12 |
| exact (all atom kinds) | ownership | 1 | 1 |
| breakage: collateral > 0 | ownership | 9/10 | 9/10 |
| fragility: rules broken per ablation | ownership | 0.40 | 0.30 |
| rules with a valid ablation | delete_group | 7 / 12 | 7 / 12 |
| exact (all atom kinds) | delete_group | 1 | 1 |
| breakage: collateral > 0 | delete_group | 6/7 | 6/7 |
| fragility: rules broken per ablation | delete_group | 0.43 | 0.43 |
| BCubed F1 vs reference sheets (SUBJECTIVE), mean over games | - | 0.702 [0.616, 0.779] | 0.747 [0.672, 0.820] |
| paired difference, post-freeze minus frozen | - | - | 0.045 [0.003, 0.090] |
| consistency over rewrites, mean BCubed F1 | - | 0.956 [0.935, 0.978] | 0.965 [0.947, 0.980] |

Metric 10, procedure `ownership`. FROZEN:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 10 -> 10 of 12 | 10 | 1 -> 1 |
| reorder | 10 -> 8 of 12 | 8 | 1 -> 0 |
| extract | 10 -> 8 of 12 | 3 | 1 -> 0 |
| inline | 10 -> 4 of 12 | 2 | 1 -> 1 |
| duplicate | 10 -> 12 of 12 | 1 | 1 -> 0 |
| permute | 10 -> 10 of 12 | 10 | 1 -> 1 |

POST-FREEZE:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 10 -> 10 of 12 | 10 | 1 -> 1 |
| reorder | 10 -> 8 of 12 | 8 | 1 -> 0 |
| extract | 10 -> 8 of 12 | 3 | 1 -> 0 |
| inline | 10 -> 7 of 12 | 3 | 1 -> 1 |
| duplicate | 10 -> 12 of 12 | 1 | 1 -> 0 |
| permute | 10 -> 10 of 12 | 10 | 1 -> 1 |

Metric 10, procedure `delete_group`. FROZEN:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 7 -> 7 of 12 | 7 | 1 -> 1 |
| reorder | 7 -> 7 of 12 | 7 | 1 -> 1 |
| extract | 7 -> 7 of 12 | 6 | 1 -> 2 |
| inline | 7 -> 7 of 12 | 5 | 1 -> 1 |
| duplicate | 7 -> 7 of 12 | 4 | 1 -> 1 |
| permute | 7 -> 7 of 12 | 7 | 1 -> 1 |

POST-FREEZE:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 7 -> 7 of 12 | 7 | 1 -> 1 |
| reorder | 7 -> 5 of 12 | 5 | 1 -> 0 |
| extract | 7 -> 7 of 12 | 6 | 1 -> 2 |
| inline | 7 -> 7 of 12 | 7 | 1 -> 1 |
| duplicate | 7 -> 9 of 12 | 2 | 1 -> 0 |
| permute | 7 -> 7 of 12 | 7 | 1 -> 1 |

## Test set

| metric | procedure | FROZEN lgref | POST-FREEZE terminal-edge-off |
|---|---|---|---|
| rules with a valid ablation | ownership | 17 / 20 | 13 / 20 |
| exact (all atom kinds) | ownership | 0 | 0 |
| breakage: collateral > 0 | ownership | 17/17 | 13/13 |
| fragility: rules broken per ablation | ownership | 0.59 | 0.46 |
| rules with a valid ablation | delete_group | 17 / 20 | 15 / 20 |
| exact (all atom kinds) | delete_group | 2 | 2 |
| breakage: collateral > 0 | delete_group | 15/17 | 13/15 |
| fragility: rules broken per ablation | delete_group | 0.65 | 0.67 |
| BCubed F1 vs reference sheets (SUBJECTIVE), mean over games | - | 0.603 [0.568, 0.638] | 0.625 [0.589, 0.665] |
| paired difference, post-freeze minus frozen | - | - | 0.023 [0.004, 0.043] |
| consistency over rewrites, mean BCubed F1 | - | 0.940 [0.930, 0.949] | 0.948 [0.939, 0.957] |

Metric 10, procedure `ownership`. FROZEN:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 17 -> 17 of 20 | 17 | 0 -> 0 |
| reorder | 17 -> 17 of 20 | 17 | 0 -> 0 |
| extract | 17 -> 17 of 20 | 12 | 0 -> 0 |
| inline | 17 -> 15 of 20 | 7 | 0 -> 0 |
| duplicate | 17 -> 15 of 20 | 6 | 0 -> 0 |
| permute | 17 -> 17 of 20 | 17 | 0 -> 0 |

POST-FREEZE:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 13 -> 13 of 20 | 13 | 0 -> 0 |
| reorder | 13 -> 16 of 20 | 13 | 0 -> 0 |
| extract | 13 -> 8 of 20 | 5 | 0 -> 0 |
| inline | 13 -> 19 of 20 | 8 | 0 -> 0 |
| duplicate | 13 -> 16 of 20 | 4 | 0 -> 0 |
| permute | 13 -> 13 of 20 | 13 | 0 -> 0 |

Metric 10, procedure `delete_group`. FROZEN:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 17 -> 17 of 20 | 17 | 2 -> 2 |
| reorder | 17 -> 17 of 20 | 17 | 2 -> 2 |
| extract | 17 -> 17 of 20 | 10 | 2 -> 1 |
| inline | 17 -> 19 of 20 | 13 | 2 -> 3 |
| duplicate | 17 -> 17 of 20 | 9 | 2 -> 1 |
| permute | 17 -> 17 of 20 | 17 | 2 -> 2 |

POST-FREEZE:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 15 -> 15 of 20 | 15 | 2 -> 2 |
| reorder | 15 -> 15 of 20 | 15 | 2 -> 2 |
| extract | 15 -> 17 of 20 | 9 | 2 -> 1 |
| inline | 15 -> 16 of 20 | 7 | 2 -> 3 |
| duplicate | 15 -> 16 of 20 | 9 | 2 -> 1 |
| permute | 15 -> 15 of 20 | 15 | 2 -> 2 |


## Reading

**Objective metrics first.**
- **Ablations: the variant is no better.** It has exact ablations for
  the same number of rules on both sets and under both procedures:
  1/12 and 1/12 on development, 0/20 and 2/20 on test. On the test set
  it has a valid ablation for **fewer** rules: 13 against 17 under
  ownership, and 15 against 17 under delete-group.
- **Consistency over rewrites is about the same.**
- **Metric 10 is about as stable**, up to how many rules have an
  ablation after each rewrite.

**Subjective metric.** BCubed against the provisional reference sheets
improves by +0.045 [0.003, 0.090] on development, the set it was chosen
on, and by +0.023 [0.004, 0.043] on test. The gain holds on unseen
games, but it is a gain in a subjective metric. The objective ablation
metrics do not move.

## Reproducing

```bash
M=lgref_postfreeze_noterminal
python -m lgref.bench.experiments interventions --split test --methods $M --workers 2 --out docs/paper-a/runs/pf_exp1_test.json
python -m lgref.bench.experiments groupings --split test --methods $M --seeds 30 --out docs/paper-a/runs/pf_exp2_test.json
python -m lgref.bench.experiments invariance --split test --methods $M --seeds 5 --out docs/paper-a/runs/pf_exp4_test.json
python -m lgref.bench.experiments rewrite_ablations --split test --methods $M --workers 1 --out docs/paper-a/runs/pf_exp10_test.json
```

The same commands with `--split dev` give the development rows. Game
records are in the session scratchpad
(`paper-a/run7/results/game-records/paper-a/postfreeze-394/` and
`run9/...`). Metric 10 was run after the #386 rewrite fix.
