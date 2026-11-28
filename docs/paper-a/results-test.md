# Paper A: test-set results, side by side with development

Stage 5 (#370, #373, #374, and this PR). The method is the frozen one,
**`ab7b33b`** (`freeze.md`). Nothing was tuned on any test result.
Since the freeze, `lgref/identify/`, `methods.py` and how an
intervention is built are unchanged. The only post-freeze changes on
the measurement path are the user's #363 decisions, which the
development results also use: successor atoms, the inert-exclusion
rule, and the rejection of a start state that is already terminal.
The test runs used the stage 5 tree (`exp*_test.json` names the
commit).

**How to read this.** Objective metrics come first, then subjective
ones. That is the user's rule (`protocol.md`).

**Everything here is provisional.** Claude wrote the test games, the
reference sheets, the variants and the probes. Claude is also the
author of the method. The reviewers are Claude agents of the same
model family. Intervals are 95% bootstrap intervals over **games**:
15 test games, and 10 of them have reference variants.

**The test set.** 15 games:

- 9 written after the freeze: kalah_mini, dotsboxes_2x2, hex_3x3,
  checkers_4x4, foxgeese_mini, chomp_3x3, synth_independent,
  synth_shared and synth_redundant;
- 6 seen before Paper A but never used for a choice: skirmish, muddy
  children, Kuhn poker, Leduc hold'em, Russian cards and Cheryl's
  birthday.

There are 20 targeted reference changes and 1 no-effect control, on
the 10 perfect-information games. The development set has 12 targeted
changes and 1 control, on 5 games. Dev and test are never pooled.

## Primary (1): ablation metrics, development against test

Reading `n / N`: N is the number of targeted rules, and n is the number
of rules for which the method's closest valid ablation is **exact**
(|A Δ R| = 0). The "breakage" column counts closest ablations with
collateral damage > 0. Fragility is the mean number of other
reference rules broken.

| method | exact, ownership: dev / test | exact, delete-group: dev / test | breakage, ownership: dev / test | breakage, delete-group: dev / test | fragility, ownership: dev / test |
|---|---|---|---|---|---|
| lgref | 1/12 / 0/20 | 1/12 / 2/20 | 9/10 / 17/17 | 6/7 / 15/17 | 0.40 / 0.59 |
| louvain_hard | 1/12 / 0/20 | 2/12 / 3/20 | 9/10 / 19/19 | 7/9 / 16/19 | 0.30 / 0.68 |
| leiden | 0/12 / 0/20 | 1/12 / 3/20 | 8/8 / 17/17 | 6/7 / 14/17 | 0.38 / 0.59 |
| leiden_hard | 0/12 / 0/20 | 1/12 / 6/20 | 8/8 / 19/19 | 6/7 / 13/19 | 0.25 / 0.74 |
| link_communities | 1/12 / 5/20 | 7/12 / 7/20 | 9/10 / 15/20 | 5/12 / 13/20 | 0.40 / 0.45 |
| dependency_louvain | 0/12 / 0/20 | 0/12 / 0/20 | 10/10 / 10/12 | 7/7 / 12/14 | 0.90 / 0.58 |
| components | 0/12 / 0/20 | 0/12 / 0/20 | 2/2 / n/a | 2/2 / n/a | 0.00 / n/a |
| name_tokens | 1/12 / 1/20 | 7/12 / 7/20 | 10/12 / 17/20 | 4/12 / 11/20 | 0.58 / 0.05 |
| singletons | 1/12 / 7/20 | 7/12 / 13/20 | 9/12 / 9/20 | 4/12 / 3/20 | 0.17 / 0.10 |
| one_group | 0/12 / 0/20 | 0/12 / 0/20 | n/a | n/a | n/a |
| random_matched | 0/12 / 4/20 | 0/12 / 0/20 | 6/7 / 10/16 | 9/10 / 14/15 | 0.29 / 0.25 |

The full test tables are in `results-test-tables.md`, built by
`lgref.bench.report` from `runs/exp1_test.json`. They cover metrics 1–9
per method and procedure, breakage per game, rejections, scatter,
repair, and the reference ablations' own reach.

What the test set says:

- **LGREF's closest ablation is never exact under ownership on the test
  set (0 of 20).** It is exact for 2 of 20 under delete-group. On the
  development set it was 1 of 12 under each procedure. Every closest
  ownership ablation does collateral damage (17 of 17).
- **The finest grouping does best, as on the development set.**
  Singletons are exact for 13 of 20 under delete-group, and name tokens
  and link communities for 7 of 20 each. The caveat from development
  still holds: singletons attempt 547 interventions, LGREF 90.
- **The matched-size random baseline beats LGREF under ownership on
  the test set**: exact for 4 of 20 rules against 0, with the same 90
  attempts. This was checked as a possible bug, and it is not one. In
  every case a random group happened to hold a rule's one key
  statement, and the ownership split did the rest:
  - checkers: the forced-capture test, `canjump`, is deleted and its
    guard relaxed;
  - synth: the `light` or `add(2)` permission is deleted alone, with
    the group's other statements protected.

  LGREF's groups never isolate such a statement. Under delete-group
  the random baseline is exact for 0 of 20.
- **LGREF's two exact delete-group ablations** are Kalah's
  `no_capture` and skirmish's `no_lancer`. The Kalah one works by
  deleting a whole group that holds the `opposite` table together with
  `capture`. The table is language under the user's convention, yet
  deleting it switches capture off.
- **The rejection profile is the same.** Most of LGREF's ownership
  interventions are empty (33%), unplayable at the start (26%) or
  remove the roles (11%). 16% are accepted.
- **The test set's reference ablations are less coupled.** Only
  skirmish's and dots and boxes' rules reach one another. On every
  other test game a reference ablation touches only its own rule, so
  the collateral LGREF does there is not forced by the game.

## Primary (2): reproduction, validity, consistency, development against test

| method | reproduced by probes, ownership: dev / test | reproduced, delete-group: dev / test | valid rate, ownership: dev / test | valid rate, delete-group: dev / test | consistency over rewrites, mean BCubed F1 [95% CI]: dev / test |
|---|---|---|---|---|---|
| lgref | 1/12 / 5/20 | 1/12 / 7/20 | 0.28 / 0.16 | 0.33 / 0.27 | 0.96 [0.93, 0.98] / 0.94 [0.93, 0.95] |
| louvain_hard | 1/12 / 6/20 | 2/12 / 9/20 | 0.28 / 0.15 | 0.36 / 0.32 | 0.94 [0.91, 0.96] / 0.92 [0.91, 0.94] |
| leiden | 0/12 / 5/20 | 1/12 / 7/20 | 0.23 / 0.14 | 0.31 / 0.27 | 0.95 [0.93, 0.98] / 0.94 [0.92, 0.95] |
| leiden_hard | 0/12 / 6/20 | 1/12 / 10/20 | 0.24 / 0.15 | 0.32 / 0.34 | 0.94 [0.91, 0.96] / 0.93 [0.91, 0.94] |
| link_communities | 1/12 / 6/20 | 7/12 / 9/20 | 0.27 / 0.25 | 0.52 / 0.43 | 0.95 [0.93, 0.98] / 0.95 [0.94, 0.96] |
| dependency_louvain | 2/12 / 1/20 | 1/12 / 0/20 | 0.53 / 0.24 | 0.53 / 0.36 | 0.95 [0.92, 0.98] / 0.94 [0.92, 0.96] |
| components | 0/12 / 0/20 | 0/12 / 0/20 | 0.06 / 0.00 | 0.06 / 0.00 | 0.99 [0.98, 1.00] / 1.00 [0.99, 1.00] |
| name_tokens | 1/12 / 1/20 | 7/12 / 8/20 | 0.20 / 0.25 | 0.62 / 0.50 | 0.96 [0.95, 0.98] / 0.96 [0.95, 0.97] |
| singletons | 2/12 / 7/20 | 7/12 / 15/20 | 0.31 / 0.23 | 0.76 / 0.70 | 0.98 [0.97, 0.98] / 0.98 [0.97, 0.98] |
| one_group | 0/12 / 0/20 | 0/12 / 0/20 | 0.00 / 0.00 | 0.00 / 0.00 | 1.00 / 1.00 |
| random_matched | 0/12 / 4/20 | 1/12 / 2/20 | 0.12 / 0.26 | 0.23 / 0.14 | 0.62 [0.57, 0.69] / 0.61 [0.58, 0.64] |

- **The no-effect control** (synth_redundant's redundant rule) is
  reproduced only by singletons. No other method isolates the single
  redundant statement.
- **Probes overstate again.** LGREF reproduces 5 of 20 changes by
  probes under ownership, but none exactly. That is the same gap the
  development set showed (8 interventions passed every probe without
  being exact).
- **Consistency carries over** (0.94 on test against 0.96 on dev). The
  random floor is the same, 0.61 against 0.62.

### Metric 10 on the test set

Procedure `ownership`:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 17 -> 17 of 20 | 17 | 0 -> 0 |
| reorder | 17 -> 17 of 20 | 17 | 0 -> 0 |
| extract | 17 -> 17 of 20 | 12 | 0 -> 0 |
| inline | 17 -> 15 of 20 | 7 | 0 -> 0 |
| duplicate | 17 -> 15 of 20 | 6 | 0 -> 0 |
| permute | 17 -> 17 of 20 | 17 | 0 -> 0 |

Procedure `delete_group`:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 17 -> 17 of 20 | 17 | 2 -> 2 |
| reorder | 17 -> 17 of 20 | 17 | 2 -> 2 |
| extract | 17 -> 17 of 20 | 10 | 2 -> 1 |
| inline | 17 -> 19 of 20 | 13 | 2 -> 3 |
| duplicate | 17 -> 17 of 20 | 9 | 2 -> 1 |
| permute | 17 -> 17 of 20 | 17 | 2 -> 2 |

- **Renaming and reordering leave every number unchanged** on the test
  set, under both procedures. On the development set, reordering lost
  the one exact ablation. Here there is none to lose under ownership.
- **Argument permutation is neutral too.** Under `permute` all 17 rules
  keep the same exactness, collateral and shortfall, under both
  procedures.
  - *Corrected (#386).* The first version of this table showed 13 of 17
    under both procedures. Four ownership ablations had scored worse:
    checkers `no_forced_capture` and `no_promotion`, fox and geese
    `geese_no_sideways` and `no_fox_capture`.
  - The cause was a bug in the **benchmark rewrite**, not in the
    method. `permute` rotated every term named like a helper at any
    depth. Checkers' helpers `jump/5` and `step/5` share names with its
    actions `jump/4` and `step/4`, so the moves inside `legal` and
    `does` were rotated too. The "rewritten" game then had different
    moves: 9,490 atoms apart from the original on the state set before
    anything was ablated.
  - The rewrite now rotates predicate literals only, and `verify` runs
    on every test game.
  - **No frozen-method number changes.** The groupings and ablations of
    the frozen LGREF are as before. Only this row of metric 10 was
    re-scored, and it now shows what the method actually does.
  - Experiment 4 (grouping consistency) was re-run on both sets and is
    unchanged in every one of its 4,620 rows: groupings never depended
    on the rotated action terms. The development set's metric 10 is
    also unchanged.
  - The re-run's game records are in the session scratchpad
    (`paper-a/run6/results/game-records/paper-a/permute-386/`, 1.1 MB),
    not in the checkout.

## Setup statements and the language verdict (test set)

The reference is provisional: `kinds.yaml`, written by Claude.

| game | statements: language / init / role / outcome / rule (reference) | definitive indicator: P / R for "language" | rules it marks language | #202 cluster verdict: P / R | rules it marks language |
|---|---|---|---|---|---|
| skirmish | 19 / 6 / 2 / 3 / 33 | 0.86 / 1.00 | kingstep#15, kingstep#16, kingstep#17 | 0.85 / 0.89 | kingstep#15, kingstep#16, kingstep#17 |
| muddychildren | 4 / 1 / 3 / 4 / 20 | 0.67 / 1.00 | oneMuddy#9, oneMuddy#10 | n/a / 0.00 | none |
| kuhnpoker | 11 / 1 / 3 / 9 / 27 | 0.79 / 1.00 | higher#10, higher#11, higher#12 | 0.50 / 0.27 | higher#10, higher#11, higher#12 |
| leducholdem | 23 / 2 / 3 / 8 / 74 | 0.51 / 1.00 | higher#19, higher#20, higher#21, amount#27, amount#28, amount#29, amount#30, amount#31, amount#32, amount#33, amount#34, amount#35, amount#36, amount#37, amount#38, payoff#41, payoff#42, payoff#43, payoff#44, payoff#45, payoff#46, payoff#47 | 0.42 / 0.70 | higher#19, higher#20, higher#21, amount#27, amount#28, amount#29, amount#30, amount#31, amount#32, amount#33, amount#34, amount#35, amount#36, amount#37, amount#38, payoff#41, payoff#42, payoff#43, payoff#44, payoff#45, payoff#46, payoff#47 |
| russiancards | 80 / 1 / 4 / 8 / 40 | 1.00 / 1.00 | none | 1.00 / 0.88 | none |
| cherylsbirthday | 2 / 1 / 3 / 4 / 36 | 0.17 / 1.00 | date#4, date#5, date#6, date#7, date#8, date#9, date#10, date#11, date#12, date#13 | 0.00 / 0.00 | date#4, date#5, date#6, date#7, date#8, date#9, date#10, date#11, date#12, date#13 |
| kalah_mini | 33 / 9 / 2 / 4 / 44 | 0.67 / 1.00 | ring#35, ring#36, ring#37, ring#38, ring#39, ring#40, ring#41, ring#42, ring#43, ring#44, ring#45, ring#46, ring#47, ring#48, ahead#50, ahead#51 | 0.36 / 0.24 | ring#35, ring#36, ring#37, ring#38, ring#39, ring#40, ring#41, ring#42, ring#43, ring#44, ring#45, ring#46, ring#47, ring#48 |
| dotsboxes_2x2 | 31 / 3 / 2 / 4 / 15 | 1.00 / 1.00 | none | 1.00 / 0.68 | none |
| hex_3x3 | 13 / 1 / 2 / 3 / 15 | 0.76 / 1.00 | firstedge#23, firstedge#24, lastedge#25, lastedge#26 | 0.71 / 0.77 | firstedge#23, firstedge#24, lastedge#25, lastedge#26 |
| checkers_4x4 | 38 / 6 / 2 / 5 / 30 | 0.90 / 1.00 | heading#27, heading#28, farrow#41, farrow#42 | 0.96 / 0.58 | heading#27 |
| foxgeese_mini | 41 / 8 / 2 / 6 / 34 | 0.95 / 1.00 | waddle#26, waddle#27 | 1.00 / 0.68 | none |
| chomp_3x3 | 8 / 10 / 2 / 3 / 8 | 1.00 / 1.00 | none | 1.00 / 0.75 | none |
| synth_independent | 13 / 4 / 2 / 3 / 11 | 1.00 / 1.00 | none | 1.00 / 0.85 | none |
| synth_shared | 13 / 4 / 2 / 3 / 11 | 1.00 / 1.00 | none | 1.00 / 0.46 | none |
| synth_redundant | 13 / 4 / 2 / 3 / 12 | 1.00 / 1.00 | none | 1.00 / 0.85 | none |

- **The definitive indicator's recall is 1.00 on every test game.** It
  marks no rule statement as language except the fixed tables that
  `kinds.yaml` lists as `ambiguous`: skirmish's guard step, the card
  rankings, Leduc's stake and payoff tables, Cheryl's dates, Kalah's
  ring, Hex's edges, checkers' headings and promotion row, the geese's
  directions, and muddy children's "at least one muddy". The one
  exception is Kalah's `ahead`, which is derived only from the ring
  table. This is the open decision about fixed tables; switching it
  means moving those predicates between the two lists in `kinds.yaml`.
- **The #202 cluster verdict again under-calls language** (recall 0.00
  to 0.89).

## Secondary: subjective metrics

### Blind Claude review (15 fresh reviewer agents, same prompt, neutral labels)

| method | overall, dev [95% CI] | overall, test [95% CI] | group score, dev | group score, test |
|---|---|---|---|---|
| lgref | 3.57 [3.14, 3.86] | 3.00 [2.80, 3.20] | 4.15 | 3.88 |
| louvain_hard | 3.29 [3.00, 3.57] | 3.47 [3.20, 3.80] | 4.01 | 4.17 |
| leiden | 3.43 [3.14, 3.86] | 3.00 [2.80, 3.20] | 4.14 | 3.86 |
| leiden_hard | 2.71 [2.43, 3.00] | 3.53 [3.20, 3.87] | 4.02 | 4.21 |
| link_communities | 3.14 [3.00, 3.43] | 2.80 [2.40, 3.20] | 4.17 | 3.85 |
| dependency_louvain | 2.14 [2.00, 2.43] | 2.27 [2.00, 2.60] | 3.66 | 3.57 |
| components | 2.29 [1.43, 3.29] | 1.27 [1.00, 1.60] | 3.90 | 3.13 |
| name_tokens | 3.71 [3.43, 4.00] | 3.47 [3.13, 3.73] | 4.24 | 4.14 |
| singletons | 1.29 [1.00, 1.57] | 1.33 [1.13, 1.60] | 2.49 | 2.42 |
| one_group | 1.00 | 1.00 | 1.29 | 1.07 |
| random_matched | 1.00 | 1.00 | 1.11 | 1.15 |

Per-game cells are in `results-test-tables.md`. Two departures from the
review procedure are recorded:

- The Russian cards reviewer wrote its reply with a shell command
  instead of the Write tool, because the reply was long. It reports
  that it read no other file.
- The Cheryl's birthday reviewer made 7 tool calls where 2 were
  expected. Its prompt allowed reading only the packet, and nothing
  shows it read more, but this is not verified.

On the test set, LGREF (3.00) scores below Louvain without overlap
(3.47) and below name tokens (3.47), and the intervals barely touch. On
the development set it was 3.57. This is an opinion, not a verdict.

### BCubed F1 against the provisional test sheets

| method | dev, mean [95% CI] | test, mean [95% CI] | test, paired vs lgref [95% CI] |
|---|---|---|---|
| lgref | 0.702 [0.614, 0.780] | 0.603 [0.568, 0.639] | - |
| louvain_hard | 0.653 [0.578, 0.724] | 0.599 [0.543, 0.658] | -0.004 [-0.043, 0.037] |
| leiden | 0.704 [0.615, 0.783] | 0.604 [0.569, 0.642] | 0.002 [-0.001, 0.006] |
| leiden_hard | 0.655 [0.579, 0.727] | 0.601 [0.543, 0.662] | -0.002 [-0.042, 0.040] |
| link_communities | 0.692 [0.589, 0.784] | 0.576 [0.535, 0.621] | -0.027 [-0.071, 0.012] |
| dependency_louvain | 0.481 [0.398, 0.563] | 0.520 [0.481, 0.558] | -0.083 [-0.123, -0.039] |
| components | 0.637 [0.493, 0.780] | 0.448 [0.394, 0.509] | -0.154 [-0.215, -0.095] |
| name_tokens | 0.671 [0.591, 0.740] | 0.504 [0.449, 0.561] | -0.098 [-0.151, -0.046] |
| singletons | 0.276 [0.220, 0.334] | 0.295 [0.241, 0.351] | -0.308 [-0.354, -0.260] |
| one_group | 0.440 [0.386, 0.500] | 0.405 [0.373, 0.437] | -0.198 [-0.244, -0.154] |
| random_matched | 0.358 [0.328, 0.389] | 0.352 [0.323, 0.380] | -0.251 [-0.279, -0.218] |

- **LGREF drops from 0.702 to 0.603 on unseen games.** It stays above
  name tokens (paired +0.098), components and the trivial groupings.
- **The overlap step's advantage disappears.** LGREF against Louvain
  without overlap is −0.004 [−0.043, 0.037]. On the development set it
  was +0.049.

## Open decisions (not settled here)

- **A post-freeze variant (terminal edge off).** Run on both sets
  (#394) as a separate, post-freeze method, and reported beside the
  frozen numbers in `results-postfreeze.md`.
  - BCubed (subjective): +0.023 [0.004, 0.043] on test.
  - Objective ablation metrics: no better. The exact counts are the
    same, and fewer rules have a valid ablation.
- **Fixed tables**: decided by the user as option (c). It is applied as
  a labelled post-freeze amendment (#400). The per-game verdicts and the
  effect on metric 11 are in `fixed-tables.md`: only Kalah changes, with
  `ahead` and `opposite` becoming rules.
- **Ablation by substitution** is not a category. Removing a piece type
  with its starting placement, or a whole mechanism, is a REMOVE.
  Changing a constant is a RELAX or a REPLACE (`protocol.md`, "The
  taxonomy of changes").

## Game records

Every random game these measurements played is saved, gzipped (#374),
under `results/game-records/paper-a/stage5-test/` in the checkout:

- `exp1/<game>/state_set.jsonl.gz`: the random games that built *S*
  for skirmish and fox and geese. The other games' *S* is a full
  census, so no games were played for it.
- `exp1/<game>/interventions.jsonl.gz`: the 40 own-play games of every
  intervention that reached the validity check.
- `exp10/...`: the same, for metric 10.

## Reproducing

```bash
python -m lgref.bench.experiments groupings --split test --seeds 30 --out docs/paper-a/runs/exp2_test.json
python -m lgref.bench.experiments invariance --split test --seeds 5 --out docs/paper-a/runs/exp4_test.json
python -m lgref.bench.experiments interventions --split test --workers 3 --records results/game-records/paper-a/stage5-test/exp1 --out docs/paper-a/runs/exp1_test.json
python -m lgref.bench.experiments rewrite_ablations --split test --workers 3 --records results/game-records/paper-a/stage5-test/exp10 --out docs/paper-a/runs/exp10_test.json
python -m lgref.bench.report interventions docs/paper-a/runs/exp1_test.json
python -m lgref.bench.report groupings docs/paper-a/runs/exp2_test.json
python -m lgref.bench.review <the 15 test games>            # packets
python -m lgref.bench.review --table <the 15 test games>
python -m lgref.bench.setup <the 15 test games>
```
