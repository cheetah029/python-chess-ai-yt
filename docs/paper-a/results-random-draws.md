# Paper A: the random baseline, checked over 30 draws (#396)

The user questioned the test-set result "matched random groups beat
LGREF: 4/20 exact against 0/20, ownership". This page checks it.

## What the baseline is

`random_matched` starts from LGREF's own grouping at seed 0, then
randomly permutes which statements sit in it (a seeded shuffle). The
number of groups, each group's size, the overlap pattern and the number
of ungrouped statements are kept exactly. Only *which* statements go
together is random.

The same intervention builder and the same closest-ablation selection
are applied to LGREF and to every draw:
- the intervention builder: the production ownership split, or deleting
  the whole group;
- the closest ablation: the valid, changing intervention with the fewest
  rule changes, i.e. atoms differing from the reference ablation.

## Re-derivation

An independent script, which does not use the report code, recomputed
the published numbers from `runs/exp1_test.json`:

- ownership: random 4/20, LGREF 0/20;
- delete-group: random 0/20, LGREF 2/20.

**The published 4/20 is one draw** (permutation seed 0), not the best of
several. It is the same permutation the new code reproduces: all 180 of
its interventions are identical in what they remove, in validity and in
rule changes to draw 0 of the 30-draw run.

## Thirty draws

There are 30 draws (permutation seeds 0–29), all of the same LGREF
grouping. For each draw, the count is the number of rules whose closest
ablation is exact (0 rule changes), computed on that draw alone. Draws
are never merged, because merging would take the best of 30. The
interval is a 95% bootstrap over draws.

| set | procedure | LGREF | random, mean over 30 draws [95% CI] | draws matching or beating LGREF | draws beating LGREF | min–max over draws |
|---|---|---|---|---|---|---|
| dev (12 rules) | ownership | 1 | 0.33 [0.17, 0.50] | 33% | 0% | 0–1 |
| dev (12 rules) | delete-group | 1 | 0.27 [0.13, 0.43] | 27% | 0% | 0–1 |
| test (20 rules) | ownership | 0 | 0.87 [0.50, 1.30] | 100% | 47% | 0–4 |
| test (20 rules) | delete-group | 2 | 0.13 [0.00, 0.30] | 3% | 0% | 0–2 |

What this says:

- **The 4/20 was a lucky draw.** Draw 0 happens to be the maximum of the
  30. The expected value is 0.87.
- **On the test set under ownership, random still beats LGREF on
  average** (0.87 against 0). LGREF has no exact ownership ablation
  there, so every draw matches or beats it.
- **Everywhere else LGREF beats random:** development under both
  procedures, and test under delete-group, where 97% of draws do worse
  than LGREF.
- **How random wins when it does:** a random group happens to hold a
  rule's one key statement and little else that can be deleted, and the
  ownership split does the rest. The four rules of draw 0 are walked
  through in the stage-5 report.

## Seeing the groupings

```bash
python3 -m lgref identify --gdl lgref/bench/games/checkers_4x4.gdl --show-groups --compare random --groups-out docs/paper-a/groupings
python3 -m lgref.bench.show_groups --compare random_matched     # every game
```

There is one file per game in `docs/paper-a/groupings/<game>.md`. It
lists every statement with its line in the `.gdl` file, side by side
with its LGREF group and its random group, then each method's groups in
full. The random grouping shown is exactly the one scored (seed 0).

## Reproducing

```bash
python -m lgref.bench.experiments interventions --split test --methods random_matched --draws 30 --workers 2 --out docs/paper-a/runs/draws_exp1_test.json
python -m lgref.bench.experiments interventions --split dev  --methods random_matched --draws 30 --workers 2 --out docs/paper-a/runs/draws_exp1_dev.json
```

The two records are stored gzipped (`draws_exp1_*.json.gz`, 20 MB
uncompressed). `report.draws_summary(record, procedure)` gives the
per-draw counts,
mean and interval. Game records are in the session scratchpad
(`paper-a/run8/results/game-records/paper-a/random-draws-396/`).
