# Paper A: rule changes by kind, and play-outs (#402)

**The user's decision (2026-11-27): EXACT stays the primary metric.**
The user calls it **functional differences in game rules**, or **rule
changes**: the number of atoms in which two descriptions' rules differ.

It is not a legal-move count, for two reasons:
- endings and successors affect legal moves later in the game;
- a payoff difference changes a rule without changing any legal move.

Next to it, this document reports:

- the per-kind breakdown, for every method: rule changes in legal
  moves, endings, payoffs and successors;
- a precise statement of how moves and fluents are mapped;
- the equivalent-representation tests;
- a play-out check, as an additional measure.

Exactness, the closest-ablation selection and every earlier table are
unchanged.

## Definitions

- **Atoms over S** (`lgref.bench.ablation_metrics`):
  `legal(s, role, move)`, `terminal(s)`, `goal(s, role, value)` and
  `next(s, joint move, s')`, at every state s of the fixed state set S.
- **Exactness, or rule changes** ("functional differences in game
  rules") = |atoms(A) Δ atoms(R)| over all four kinds, for a method's
  ablation A and the reference ablation R. This is the primary metric,
  and is unchanged. 0 means functionally identical rules on S.
- **Differences by kind**: the same count split into four parts:
  - legal-move: (state, role, move) triples legal in one description and
    not the other;
  - terminal: states that end the game in exactly one of the two;
  - goal: (state, role, value) payoffs present in one and not the other;
  - successor: (state, joint move, next state) triples present in one
    and not the other.

  The parts add up to exactness.
- **Closest ablation**: unchanged, `report.closest_ablation`. It is the
  valid, non-empty, changing intervention with the smallest exactness.
  Ties are broken by smaller collateral, then by group order.
- **Play-out** (`lgref.bench.traces.play_out`), 20 seeded traces of up to
  60 plies per rule:
  - Both descriptions start from their own initial state.
  - At each step the legal moves of every role are compared, then
    whether each description says the game has ended, then (at a step
    both call terminal) each role's payoff.
  - A joint move legal in both is drawn and played in both.
  - States are never compared.
  - "No difference of any kind in play" means 0 legal-move differences,
    0 terminal disagreements and 0 payoff disagreements.

## How moves and fluents are mapped

**Within one game.** The base, every intervention A and every reference
variant R are cut from one file. They share the action and fluent
vocabulary, so atoms are compared term for term with no mapping.

**Under each rewrite** (Experiments 4 and 10):

| rewrite | move terms | roles | state fluents (including the states in successor atoms) |
|---|---|---|---|
| scramble | renamed; mapped back through the exact inverse renaming | renamed; mapped back; joint moves re-ordered to the original role order | renamed; every fact of every state mapped back |
| permute | unchanged (since #386 it rotates helper literals only, never action terms) | unchanged | unchanged (fluents are never helpers) |
| reorder, extract, inline, duplicate | unchanged | unchanged | unchanged |

A description that wrote the same moves with *different* action terms
would need a move mapping. `play_out` accepts one (`move_map`), but no
comparison in the benchmark needs it.

**Are successor atoms representation-dependent in the ablation
comparison?**
- Not across encodings: A, R and the base share one vocabulary.
- **They are sensitive to state that no rule reads.** Deleting checkers'
  `tick` counter, which is written and never read, changes every
  successor atom, and no legal move, ending or payoff in any play-out
  (`test_dropping_an_unused_fluent_changes_nothing_logically`).
- An ablation that removes such a fluent is therefore counted as
  different by the successor atoms while the game is the same. Group 9
  of checkers in Experiment 10 is one: it removes `tick`.
- So the successor count can overstate a difference. It is reported in
  its own column for that reason.

**Tests** (`lgref/tests/test_paper_a_traces.py`):
- A description agrees with itself.
- On checkers, Othello and Kalah, each of `permute`, `reorder`, `extract`,
  `inline`, `duplicate` and `scramble` gives 0 differences in play.
  These are descriptions that are logically identical but written with
  arguments permuted, statements reordered, helpers extracted, inlined
  or duplicated, and every name renamed.
- Dropping the unused fluent gives 0 differences in play.
- A real rule change shows differences.
- The rebuilt ablation is the one the record scored.

## Results

### Development set, procedure `ownership`

Differences by kind at the closest ablation, over S:

| method | rules with a valid ablation | exact in legal moves | legal-move collateral > 0 | legal-move shortfall > 0 | median legal-move differences | terminal differences | goal differences | successor differences (representation-dependent) |
|---|---|---|---|---|---|---|---|---|
| lgref | 10 / 12 | 1 | 8/10 | 5/10 | 29782 | 2529 | 7006 | 246464 |
| louvain_hard | 10 / 12 | 1 | 8/10 | 5/10 | 2297 | 2538 | 7024 | 166408 |
| leiden | 8 / 12 | 0 | 7/8 | 5/8 | 32888 | 2529 | 7002 | 246458 |
| leiden_hard | 8 / 12 | 0 | 7/8 | 5/8 | 5672 | 2538 | 7020 | 166402 |
| link_communities | 10 / 12 | 2 | 6/10 | 5/10 | 1172 | 2323 | 6562 | 110287 |
| dependency_louvain | 10 / 12 | 4 | 1/10 | 5/10 | 44 | 940 | 2924 | 227842 |
| components | 2 / 12 | 0 | 0/2 | 2/2 | 44 | 64 | 64 | 225 |
| name_tokens | 12 / 12 | 7 | 0/12 | 5/12 | 0 | 2408 | 13702 | 69917 |
| singletons | 12 / 12 | 7 | 0/12 | 5/12 | 0 | 2408 | 4129 | 69946 |
| one_group | 0 / 12 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| random_matched | 7 / 12 | 3 | 0/7 | 4/7 | 41 | 2136 | 8253 | 93018 |

The same ablations, played out (20 seeded play-outs per rule):

| method | rules played out | no difference of any kind in play | no legal-move difference in play | legal-move differences | terminal differences | goal differences | traces diverged |
|---|---|---|---|---|---|---|---|
| lgref | 10 / 12 | 1 | 1 | 15496 | 79 | 20 | 28 |
| louvain_hard | 10 / 12 | 1 | 1 | 12625 | 79 | 20 | 28 |
| leiden | 8 / 12 | 0 | 0 | 15416 | 79 | 0 | 28 |
| leiden_hard | 8 / 12 | 0 | 0 | 12545 | 79 | 0 | 28 |
| link_communities | 10 / 12 | 1 | 2 | 5127 | 110 | 20 | 40 |
| dependency_louvain | 10 / 12 | 0 | 5 | 2872 | 159 | 28 | 0 |
| components | 2 / 12 | 0 | 0 | 104 | 40 | 0 | 0 |
| name_tokens | 12 / 12 | 1 | 6 | 4778 | 49 | 134 | 28 |
| singletons | 12 / 12 | 1 | 6 | 4656 | 49 | 67 | 32 |
| one_group | 0 / 12 | 0 | 0 | n/a | n/a | n/a | n/a |
| random_matched | 7 / 12 | 0 | 0 | 7931 | 68 | 32 | 0 |
### Development set, procedure `delete-group`

Differences by kind at the closest ablation, over S:

| method | rules with a valid ablation | exact in legal moves | legal-move collateral > 0 | legal-move shortfall > 0 | median legal-move differences | terminal differences | goal differences | successor differences (representation-dependent) |
|---|---|---|---|---|---|---|---|---|
| lgref | 7 / 12 | 4 | 0/7 | 3/7 | 0 | 901 | 2336 | 19393 |
| louvain_hard | 9 / 12 | 5 | 1/9 | 3/9 | 0 | 901 | 2340 | 19399 |
| leiden | 7 / 12 | 4 | 0/7 | 3/7 | 0 | 901 | 2336 | 19393 |
| leiden_hard | 7 / 12 | 4 | 0/7 | 3/7 | 0 | 901 | 2336 | 19393 |
| link_communities | 12 / 12 | 8 | 1/12 | 3/12 | 0 | 336 | 1316 | 7175 |
| dependency_louvain | 7 / 12 | 3 | 2/7 | 3/7 | 41 | 3407 | 11095 | 78423 |
| components | 2 / 12 | 0 | 0/2 | 2/2 | 44 | 64 | 64 | 225 |
| name_tokens | 12 / 12 | 9 | 0/12 | 3/12 | 0 | 272 | 738 | 7017 |
| singletons | 12 / 12 | 9 | 2/12 | 3/12 | 0 | 272 | 554 | 7035 |
| one_group | 0 / 12 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| random_matched | 10 / 12 | 5 | 2/10 | 5/10 | 60 | 2432 | 9249 | 110218 |

The same ablations, played out (20 seeded play-outs per rule):

| method | rules played out | no difference of any kind in play | no legal-move difference in play | legal-move differences | terminal differences | goal differences | traces diverged |
|---|---|---|---|---|---|---|---|
| lgref | 7 / 12 | 1 | 3 | 1467 | 62 | 19 | 28 |
| louvain_hard | 9 / 12 | 2 | 4 | 1547 | 62 | 39 | 28 |
| leiden | 7 / 12 | 1 | 3 | 1467 | 62 | 19 | 28 |
| leiden_hard | 7 / 12 | 1 | 3 | 1467 | 62 | 19 | 28 |
| link_communities | 12 / 12 | 7 | 8 | 1115 | 52 | 34 | 12 |
| dependency_louvain | 7 / 12 | 0 | 3 | 3824 | 80 | 18 | 16 |
| components | 2 / 12 | 0 | 0 | 104 | 40 | 0 | 0 |
| name_tokens | 12 / 12 | 7 | 9 | 1035 | 12 | 62 | 12 |
| singletons | 12 / 12 | 7 | 9 | 1129 | 12 | 20 | 12 |
| one_group | 0 / 12 | 0 | 0 | n/a | n/a | n/a | n/a |
| random_matched | 10 / 12 | 0 | 1 | 9044 | 80 | 44 | 28 |
### Test set, procedure `ownership`

Differences by kind at the closest ablation, over S:

| method | rules with a valid ablation | exact in legal moves | legal-move collateral > 0 | legal-move shortfall > 0 | median legal-move differences | terminal differences | goal differences | successor differences (representation-dependent) |
|---|---|---|---|---|---|---|---|---|
| lgref | 17 / 20 | 10 | 1/17 | 7/17 | 0 | 7 | 191 | 196505 |
| louvain_hard | 19 / 20 | 13 | 3/19 | 6/19 | 0 | 7 | 22 | 197939 |
| leiden | 17 / 20 | 10 | 1/17 | 7/17 | 0 | 7 | 191 | 196505 |
| leiden_hard | 19 / 20 | 13 | 2/19 | 6/19 | 0 | 7 | 22 | 205385 |
| link_communities | 20 / 20 | 13 | 5/20 | 6/20 | 0 | 8 | 4000 | 66292 |
| dependency_louvain | 12 / 20 | 6 | 3/12 | 5/12 | 260 | 7 | 3004 | 104678 |
| components | 0 / 20 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| name_tokens | 20 / 20 | 9 | 0/20 | 11/20 | 32 | 7 | 2976 | 38459 |
| singletons | 20 / 20 | 15 | 1/20 | 5/20 | 0 | 7 | 3419 | 32214 |
| one_group | 0 / 20 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| random_matched | 16 / 20 | 10 | 0/16 | 6/16 | 0 | 7 | 4641 | 122856 |

The same ablations, played out (20 seeded play-outs per rule):

| method | rules played out | no difference of any kind in play | no legal-move difference in play | legal-move differences | terminal differences | goal differences | traces diverged |
|---|---|---|---|---|---|---|---|
| lgref | 17 / 20 | 5 | 6 | 3057 | 39 | 14 | 56 |
| louvain_hard | 19 / 20 | 6 | 8 | 2324 | 79 | 20 | 36 |
| leiden | 17 / 20 | 5 | 6 | 3057 | 39 | 14 | 56 |
| leiden_hard | 19 / 20 | 6 | 8 | 2468 | 87 | 20 | 36 |
| link_communities | 20 / 20 | 5 | 9 | 2549 | 84 | 23 | 44 |
| dependency_louvain | 12 / 20 | 1 | 4 | 3198 | 55 | 80 | 22 |
| components | 0 / 20 | 0 | 0 | n/a | n/a | n/a | n/a |
| name_tokens | 20 / 20 | 1 | 5 | 2848 | 22 | 238 | 49 |
| singletons | 20 / 20 | 7 | 10 | 1396 | 30 | 104 | 36 |
| one_group | 0 / 20 | 0 | 0 | n/a | n/a | n/a | n/a |
| random_matched | 16 / 20 | 5 | 6 | 2676 | 96 | 58 | 35 |
### Test set, procedure `delete-group`

Differences by kind at the closest ablation, over S:

| method | rules with a valid ablation | exact in legal moves | legal-move collateral > 0 | legal-move shortfall > 0 | median legal-move differences | terminal differences | goal differences | successor differences (representation-dependent) |
|---|---|---|---|---|---|---|---|---|
| lgref | 17 / 20 | 12 | 4/17 | 4/17 | 0 | 2751 | 5510 | 53734 |
| louvain_hard | 19 / 20 | 15 | 1/19 | 4/19 | 0 | 7 | 22 | 94850 |
| leiden | 17 / 20 | 13 | 3/17 | 4/17 | 0 | 7 | 22 | 43926 |
| leiden_hard | 19 / 20 | 16 | 2/19 | 3/19 | 0 | 7 | 22 | 41164 |
| link_communities | 20 / 20 | 14 | 6/20 | 4/20 | 0 | 1422 | 6864 | 62413 |
| dependency_louvain | 14 / 20 | 8 | 4/14 | 4/14 | 0 | 366 | 3738 | 97314 |
| components | 0 / 20 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| name_tokens | 20 / 20 | 12 | 1/20 | 7/20 | 0 | 1372 | 4989 | 28484 |
| singletons | 20 / 20 | 19 | 0/20 | 1/20 | 0 | 0 | 2988 | 21571 |
| one_group | 0 / 20 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| random_matched | 15 / 20 | 1 | 13/15 | 9/15 | 545 | 70 | 248 | 59653 |

The same ablations, played out (20 seeded play-outs per rule):

| method | rules played out | no difference of any kind in play | no legal-move difference in play | legal-move differences | terminal differences | goal differences | traces diverged |
|---|---|---|---|---|---|---|---|
| lgref | 17 / 20 | 6 | 9 | 1619 | 95 | 20 | 22 |
| louvain_hard | 19 / 20 | 8 | 9 | 1872 | 99 | 20 | 38 |
| leiden | 17 / 20 | 7 | 8 | 2370 | 56 | 20 | 22 |
| leiden_hard | 19 / 20 | 9 | 10 | 1994 | 60 | 20 | 38 |
| link_communities | 20 / 20 | 7 | 11 | 1889 | 103 | 24 | 20 |
| dependency_louvain | 14 / 20 | 0 | 3 | 2651 | 74 | 84 | 39 |
| components | 0 / 20 | 0 | 0 | n/a | n/a | n/a | n/a |
| name_tokens | 20 / 20 | 6 | 10 | 1249 | 20 | 209 | 20 |
| singletons | 20 / 20 | 13 | 16 | 429 | 3 | 56 | 20 |
| one_group | 0 / 20 | 0 | 0 | n/a | n/a | n/a | n/a |
| random_matched | 15 / 20 | 0 | 1 | 3006 | 151 | 0 | 46 |

## What the breakdown shows

- **Most of every method's inexactness is in successor atoms**, both
  sets and both procedures. The legal-move column is often 0 where
  exactness is not.
  - On the test set under ownership, LGREF's closest ablation has no
    difference of any kind in play for 5 of 20
    rules, and no legal-move difference in play for
    6.
  - The matched random grouping's single draw: 5 and
    6.
- **Part of the successor count is state no rule reads**, as above.
  Whether the rest is a real rule (what a move does) or an encoding
  artefact differs ablation by ablation. The play-out separates the two:
  a difference in what a move does shows up later as a legal-move,
  ending or payoff difference.
- **Under delete-group, LGREF has no difference in play for
  6 of 20 test rules.** The random draw has
  0, and singletons
  13.

## Reproducing

```bash
python -m lgref.bench.report interventions docs/paper-a/runs/exp1_test.json
python -m lgref.bench.experiments traces --split test --from docs/paper-a/runs/exp1_test.json --out docs/paper-a/runs/traces_test.json
python -m lgref.bench.experiments traces --split dev  --from docs/paper-a/runs/exp1_dev.json  --out docs/paper-a/runs/traces_dev.json
```

The random baseline's 30 draws (#396) and the post-freeze variant
(#394) are played out the same way, for the grouping-version tables
(#410). A `--draws` record is played draw by draw: each draw's closest
ablations come from its own rows, its grouping is rebuilt as it was
drawn, and each row says which draw it is. Draw 0 gives the
`random_matched` rows above exactly.

```bash
python -m lgref.bench.experiments traces --split test --from docs/paper-a/runs/draws_exp1_test.json.gz --out docs/paper-a/runs/traces_draws_test.json.gz
python -m lgref.bench.experiments traces --split test --from docs/paper-a/runs/pf_exp1_test.json --out docs/paper-a/runs/pf_traces_test.json
python -m lgref.bench.version_tables > docs/paper-a/grouping-version-tables.md
```

(`--split dev` with the `_dev` files likewise.)
