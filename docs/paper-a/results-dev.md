# Paper A: development-set results (Experiments 1–4)

Issue #358. These results come from the **development set only**:
tic-tac-toe, Nim, Corridor, 5x5 Breakthrough, 4x4 Othello, drop-three
and Monty Hall (`protocol.md` explains why each game is in this set). No
test game has been scored. The method was frozen after these runs
(`freeze.md`).

**How to read this document.** The user's rule, recorded in
`protocol.md`:

- **Primary (objective):** the ablation-based grouping metrics
  (exactness, collateral, shortfall, breakage, fragility, rejections,
  scatter, repair, endings, stability under rewrites), then behavioural
  intervention agreement, valid intervention rate, grouping consistency
  across equivalent encodings, and later, performance on unseen games.
- **Secondary (subjective):** BCubed F1 against the reference sheets
  (provisional, and written by the method's author), and a blind Claude
  review of each method's actual grouping. The review stands in for
  human readability and agreement. It is not a factual or exact
  evaluation.

Every reference sheet, variant and probe was written by Claude, the
author of the method. Intervals are 95% bootstrap intervals over
**games**, not over statements. With seven games (five for the
intervention experiments) they are wide.

## Primary (1): ablation-based grouping metrics (development set)

These are the user's metrics of 2026-11-27 (#363), defined in
`protocol.md`: atoms over *S*, with A the closest valid ablation a
method offers for a rule and R the reference ablation.

- (1) exactness: |A Δ R|;
- (2) collateral: |changed(A) − changed(R)|, with "rules broken" the
  other reference rules that own the damaged atoms;
- (3) shortfall: |changed(R) − changed(A)|;
- (4) breakage rate;
- (5) fragility;
- (6) rejections;
- (7) scatter;
- (8) repair;
- (9) ending and payoff atoms, counted apart.

There are 12 targeted rules on the 5 development games that have
reference variants. Atom counts are summed or taken as medians over
those rules; Breakthrough and Othello dominate the sums. "n/a" means the
method has no valid, changing ablation for that rule or game.

### Procedure `ownership` (delete what a group owns, relax its guards)

| method | rules with a valid ablation | exact (1) | breakage rate: collateral > 0 (4) | rules broken per ablation, mean = fragility (2, 5) | shortfall > 0 (3) | median collateral / shortfall atoms | ending or payoff atoms wrong (9) | repaired: exact / unrepaired: exact (8) |
|---|---|---|---|---|---|---|---|---|
| lgref | 10 / 12 | 1 | 9/10 | 0.40 | 9/10 | 59626 / 5832 | 9535 | 7: 0 / 3: 1 |
| louvain_hard | 10 / 12 | 1 | 9/10 | 0.30 | 9/10 | 5524 / 5948 | 9562 | 7: 0 / 3: 1 |
| leiden | 8 / 12 | 0 | 8/8 | 0.38 | 8/8 | 59932 / 11966 | 9531 | 7: 0 / 1: 0 |
| leiden_hard | 8 / 12 | 0 | 8/8 | 0.25 | 8/8 | 5582 / 12212 | 9558 | 7: 0 / 1: 0 |
| link_communities | 10 / 12 | 1 | 9/10 | 0.40 | 9/10 | 5524 / 3207 | 8885 | 5: 0 / 5: 1 |
| dependency_louvain | 10 / 12 | 0 | 10/10 | 0.90 | 9/10 | 8964 / 1016 | 3864 | 6: 0 / 4: 0 |
| components | 2 / 12 | 0 | 2/2 | 0.00 | 2/2 | 140 / 80 | 128 | 0: 0 / 2: 0 |
| name_tokens | 12 / 12 | 1 | 10/12 | 0.58 | 11/12 | 455 / 984 | 16110 | 1: 1 / 11: 0 |
| singletons | 12 / 12 | 1 | 9/12 | 0.17 | 11/12 | 32 / 1106 | 6537 | 0: 0 / 12: 1 |
| one_group | 0 / 12 | 0 | n/a | n/a | n/a | n/a / n/a | 0 | 0: 0 / 0: 0 |
| random_matched | 7 / 12 | 0 | 6/7 | 0.29 | 7/7 | 2541 / 1362 | 10389 | 4: 0 / 3: 0 |

##### breakage rate per game

| method | tictactoe | nim | corridor | breakthrough5 | othello4 |
|---|---|---|---|---|---|
| lgref | n/a | 1/2 | 2/2 | 3/3 | 3/3 |
| louvain_hard | n/a | 1/2 | 2/2 | 3/3 | 3/3 |
| leiden | n/a | n/a | 2/2 | 3/3 | 3/3 |
| leiden_hard | n/a | n/a | 2/2 | 3/3 | 3/3 |
| link_communities | n/a | 1/2 | 2/2 | 3/3 | 3/3 |
| dependency_louvain | 2/2 | n/a | 2/2 | 3/3 | 3/3 |
| components | n/a | n/a | 2/2 | n/a | n/a |
| name_tokens | 2/2 | 1/2 | 1/2 | 3/3 | 3/3 |
| singletons | 2/2 | 0/2 | 2/2 | 2/3 | 3/3 |
| one_group | n/a | n/a | n/a | n/a | n/a |
| random_matched | 2/2 | n/a | 2/2 | 2/3 | n/a |

##### rejections

| method | attempted | empty (nothing removable) | ill-formed in its own play | inert (no change) | roles removed | stuck state | two goal values | unfocused (scattered) | unplayable at the start | accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| lgref | 40 | 7 (18%) | 1 (2%) | - | 5 (12%) | 2 (5%) | 1 (2%) | 4 (10%) | 14 (35%) | 6 (15%) |
| louvain_hard | 39 | 7 (18%) | 1 (3%) | - | 5 (13%) | 2 (5%) | 1 (3%) | 4 (10%) | 12 (31%) | 7 (18%) |
| leiden | 39 | 7 (18%) | 1 (3%) | - | 5 (13%) | 3 (8%) | 1 (3%) | 4 (10%) | 14 (36%) | 4 (10%) |
| leiden_hard | 38 | 7 (18%) | 1 (3%) | - | 5 (13%) | 3 (8%) | 1 (3%) | 4 (11%) | 12 (32%) | 5 (13%) |
| link_communities | 83 | 22 (27%) | 2 (2%) | 1 (1%) | 6 (7%) | 6 (7%) | 2 (2%) | 8 (10%) | 24 (29%) | 12 (14%) |
| dependency_louvain | 19 | - | 1 (5%) | - | 1 (5%) | 2 (11%) | 2 (11%) | 4 (21%) | 3 (16%) | 6 (32%) |
| components | 16 | - | - | - | 5 (31%) | 1 (6%) | - | 1 (6%) | 9 (56%) | - |
| name_tokens | 79 | 38 (48%) | 1 (1%) | 1 (1%) | 5 (6%) | 3 (4%) | 1 (1%) | 4 (5%) | 16 (20%) | 10 (13%) |
| singletons | 251 | 122 (49%) | 14 (6%) | 37 (15%) | 10 (4%) | 13 (5%) | - | 10 (4%) | 13 (5%) | 32 (13%) |
| one_group | 5 | - | - | - | 5 (100%) | - | - | - | - | - |
| random_matched | 40 | 3 (8%) | 6 (15%) | - | 9 (22%) | 8 (20%) | - | 2 (5%) | 10 (25%) | 2 (5%) |

##### scatter

| method | ablations | action types touched | reference rules touched | concentration | normalised entropy |
|---|---|---|---|---|---|
| lgref | 10 | 2.00 | 0.40 | 0.76 | 0.50 |
| louvain_hard | 11 | 2.09 | 0.45 | 0.77 | 0.50 |
| leiden | 8 | 2.12 | 0.38 | 0.74 | 0.51 |
| leiden_hard | 9 | 2.22 | 0.44 | 0.75 | 0.50 |
| link_communities | 20 | 2.15 | 0.65 | 0.76 | 0.54 |
| dependency_louvain | 10 | 2.30 | 1.30 | 0.75 | 0.50 |
| components | 1 | 4.00 | 0.00 | 0.31 | 0.99 |
| name_tokens | 14 | 2.00 | 0.93 | 0.82 | 0.37 |
| singletons | 42 | 1.57 | 0.67 | 0.88 | 0.24 |
| one_group | 0 | n/a | n/a | n/a | n/a |
| random_matched | 4 | 1.50 | 0.25 | 0.79 | 0.49 |

### Procedure `delete-group`

| method | rules with a valid ablation | exact (1) | breakage rate: collateral > 0 (4) | rules broken per ablation, mean = fragility (2, 5) | shortfall > 0 (3) | median collateral / shortfall atoms | ending or payoff atoms wrong (9) | repaired: exact / unrepaired: exact (8) |
|---|---|---|---|---|---|---|---|---|
| lgref | 7 / 12 | 1 | 6/7 | 0.43 | 6/7 | 352 / 932 | 3237 | 0: 0 / 7: 1 |
| louvain_hard | 9 / 12 | 2 | 7/9 | 0.44 | 7/9 | 140 / 84 | 3241 | 0: 0 / 9: 2 |
| leiden | 7 / 12 | 1 | 6/7 | 0.43 | 6/7 | 352 / 932 | 3237 | 0: 0 / 7: 1 |
| leiden_hard | 7 / 12 | 1 | 6/7 | 0.43 | 6/7 | 352 / 932 | 3237 | 0: 0 / 7: 1 |
| link_communities | 12 / 12 | 7 | 5/12 | 0.17 | 5/12 | 0 / 0 | 1652 | 0: 0 / 12: 7 |
| dependency_louvain | 7 / 12 | 0 | 7/7 | 0.86 | 5/7 | 812 / 76 | 14502 | 0: 0 / 7: 0 |
| components | 2 / 12 | 0 | 2/2 | 0.00 | 2/2 | 140 / 80 | 128 | 0: 0 / 2: 0 |
| name_tokens | 12 / 12 | 7 | 4/12 | 0.00 | 5/12 | 0 / 0 | 1010 | 0: 0 / 12: 7 |
| singletons | 12 / 12 | 7 | 4/12 | 0.00 | 5/12 | 0 / 0 | 826 | 0: 0 / 12: 7 |
| one_group | 0 / 12 | 0 | n/a | n/a | n/a | n/a / n/a | 0 | 0: 0 / 0: 0 |
| random_matched | 10 / 12 | 0 | 9/10 | 0.50 | 10/10 | 200 / 6163 | 11681 | 0: 0 / 10: 0 |

##### breakage rate per game

| method | tictactoe | nim | corridor | breakthrough5 | othello4 |
|---|---|---|---|---|---|
| lgref | 1/2 | n/a | 2/2 | n/a | 3/3 |
| louvain_hard | 1/2 | 1/2 | 2/2 | n/a | 3/3 |
| leiden | 1/2 | n/a | 2/2 | n/a | 3/3 |
| leiden_hard | 1/2 | n/a | 2/2 | n/a | 3/3 |
| link_communities | 0/2 | 1/2 | 2/2 | 0/3 | 2/3 |
| dependency_louvain | 2/2 | n/a | 2/2 | 3/3 | n/a |
| components | n/a | n/a | 2/2 | n/a | n/a |
| name_tokens | 0/2 | 0/2 | 2/2 | 0/3 | 2/3 |
| singletons | 0/2 | 0/2 | 2/2 | 0/3 | 2/3 |
| one_group | n/a | n/a | n/a | n/a | n/a |
| random_matched | 2/2 | n/a | 2/2 | 2/3 | 3/3 |

##### rejections

| method | attempted | ill-formed in its own play | inert (no change) | roles removed | stuck state | two goal values | unfocused (scattered) | unplayable at the start | accepted |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 40 | - | - | 5 (12%) | 2 (5%) | 1 (2%) | 8 (20%) | 23 (57%) | 1 (2%) |
| louvain_hard | 39 | - | - | 5 (13%) | 3 (8%) | 1 (3%) | 7 (18%) | 19 (49%) | 4 (10%) |
| leiden | 39 | - | - | 5 (13%) | 2 (5%) | 1 (3%) | 7 (18%) | 23 (59%) | 1 (3%) |
| leiden_hard | 38 | - | - | 5 (13%) | 4 (11%) | 1 (3%) | 7 (18%) | 19 (50%) | 2 (5%) |
| link_communities | 83 | - | - | 6 (7%) | 4 (5%) | 1 (1%) | 15 (18%) | 42 (51%) | 15 (18%) |
| dependency_louvain | 19 | - | - | 1 (5%) | 3 (16%) | - | 6 (32%) | 7 (37%) | 2 (11%) |
| components | 16 | - | - | 5 (31%) | 1 (6%) | - | 1 (6%) | 9 (56%) | - |
| name_tokens | 79 | - | - | 5 (6%) | 5 (6%) | 1 (1%) | 12 (15%) | 32 (41%) | 24 (30%) |
| singletons | 251 | 13 (5%) | 39 (16%) | 10 (4%) | 19 (8%) | 1 (0%) | 37 (15%) | 29 (12%) | 103 (41%) |
| one_group | 5 | - | - | 5 (100%) | - | - | - | - | - |
| random_matched | 40 | 2 (5%) | - | 12 (30%) | 6 (15%) | - | 3 (8%) | 14 (35%) | 3 (8%) |

##### scatter

| method | ablations | action types touched | reference rules touched | concentration | normalised entropy |
|---|---|---|---|---|---|
| lgref | 9 | 2.44 | 0.22 | 0.55 | 0.86 |
| louvain_hard | 11 | 2.27 | 0.45 | 0.62 | 0.77 |
| leiden | 8 | 2.38 | 0.25 | 0.56 | 0.85 |
| leiden_hard | 9 | 2.44 | 0.44 | 0.58 | 0.83 |
| link_communities | 30 | 2.17 | 0.63 | 0.72 | 0.57 |
| dependency_louvain | 8 | 2.62 | 1.25 | 0.60 | 0.77 |
| components | 1 | 4.00 | 0.00 | 0.31 | 0.99 |
| name_tokens | 36 | 1.97 | 0.78 | 0.80 | 0.40 |
| singletons | 140 | 1.99 | 1.10 | 0.84 | 0.33 |
| one_group | 0 | n/a | n/a | n/a | n/a |
| random_matched | 6 | 2.67 | 0.50 | 0.72 | 0.45 |

### The reference ablations' own reach (fragility floor)

Which other reference rules each reference ablation's changes also
touch. This is coupling in the game itself, and no grouping can go
below it.

| game | rule | other reference rules its changes reach |
|---|---|---|
| tictactoe | no_column_line | none |
| tictactoe | no_diagonal_line | none |
| nim | last_taker_wins | none |
| nim | take_one_only | none |
| corridor | no_blocking | none |
| corridor | no_boundary | none |
| corridor | no_tempo | none |
| breakthrough5 | no_capture | none |
| breakthrough5 | no_diagonal_move | none |
| breakthrough5 | no_far_row_win | none |
| othello4 | end_on_pass | place_anywhere |
| othello4 | no_flip | none |
| othello4 | place_anywhere | end_on_pass |

### What these say

- **LGREF has an exact ablation for 1 of 12 rules under each
  procedure.** Its closest ablations under ownership almost always do
  collateral damage (breakage rate 9/10). They also fall short (9/10):
  they remove part of the rule *and* parts of other behaviour.
  - Its accepted ablations are few: 6 of 40 are accepted, 14 are
    unplayable at the start, 7 are empty, 5 remove the roles, and 4 are
    unfocused.
- **Fine groupings give clean ablations by deletion.** Name tokens,
  singletons and link communities each have exact ablations for 7 of 12
  rules under delete-group, with median collateral and shortfall 0 and
  4–5 of 12 rules broken. These 7 are the same rules their probes
  reproduce.
  - This rewards having many small groups to try: 251 attempts for
    singletons against 40 for LGREF. The matched-size random baseline
    (40 attempts, 0 exact) shows that size alone does not do it.
- **Probes are weaker than exactness.** In 8 cases an intervention
  passed every probe of a change but was not exact. One is Breakthrough
  `no_far_row_win`, deleted by a single statement, with a shortfall of
  12,363 atoms: it removes the far-row win for one side only.
  Reproduction-by-probes overstates; exactness is the stricter count.
- **Repair rarely produced exactness.** Repaired ablations (a relaxed
  guard or a protected statement) were exact in 0 of LGREF's 7 cases.
  The one exact LGREF ablation was unrepaired.
- **Scatter (ownership).** LGREF's accepted-or-not changing ablations
  touch 2.0 action types on average, with concentration 0.76. Singletons
  are the most focused (concentration 0.88, entropy 0.24).
- **Four rules no method reaches, because they need a statement
  replaced:** Nim `last_taker_wins`, Corridor `no_tempo`, and Othello
  `place_anywhere` and `end_on_pass`.

### Metric 10: stability of the ablation metrics under rewrites

Metric 10 rebuilds LGREF's grouping and ablations on each
behaviour-preserving rewrite and scores them against the *original*
reference ablations; under `scramble` the comparison goes through the
renaming. For each rewrite the table shows how many of the 12 rules have
a closest ablation, how many keep exactly the same exactness, collateral
and shortfall, and how many are exact.

Procedure `ownership`:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 10 -> 10 of 12 | 10 | 1 -> 1 |
| reorder | 10 -> 8 of 12 | 8 | 1 -> 0 |
| extract | 10 -> 8 of 12 | 3 | 1 -> 0 |
| inline | 10 -> 4 of 12 | 2 | 1 -> 1 |
| duplicate | 10 -> 12 of 12 | 1 | 1 -> 0 |
| permute | 10 -> 10 of 12 | 10 | 1 -> 1 |

Procedure `delete-group`:

| rewrite | changes with an ablation (original -> rewritten) | same exactness/collateral/shortfall | exact: original -> rewritten |
|---|---|---|---|
| scramble | 7 -> 7 of 12 | 7 | 1 -> 1 |
| reorder | 7 -> 7 of 12 | 7 | 1 -> 1 |
| extract | 7 -> 7 of 12 | 6 | 1 -> 2 |
| inline | 7 -> 7 of 12 | 5 | 1 -> 1 |
| duplicate | 7 -> 7 of 12 | 4 | 1 -> 1 |
| permute | 7 -> 7 of 12 | 7 | 1 -> 1 |

- **Renaming and argument permutation change nothing**, under both
  procedures: every rule keeps the same three numbers.
- **Reordering statements loses LGREF's one exact ownership ablation**
  (1 → 0), because Louvain's tie-breaking by position changes the
  groups.
- **Extracting, inlining or duplicating helpers changes most of the
  numbers under ownership.** Only 3, 2 and 1 rules keep the same
  numbers, and inlining leaves only 4 rules with any valid ablation.
  The ownership split depends on which statements are helpers, and
  these rewrites change exactly that.
- **Delete-group is more stable** (4–7 of 7 the same).

## Validation pass (#363)

The user's standing rule is a thorough pass for hidden bugs after each
implementation. It was run over stages 3–4 and the new metrics, by an
independent reviewer agent and by the targeted tests it led to. Every
item below was fixed, and each fix has a test that fails on the old
code.

| found | effect | fix |
|---|---|---|
| The atom set had no successor atoms | Othello `no_flip` changes only `next`, so its reference changed nothing and every inert intervention scored as **exact** | successor atoms added as a fourth kind |
| The closest ablation could be inert | an inert intervention (exactness \|changed(R)\|, no collateral) beat every real attempt, biasing breakage and fragility down | inert and empty interventions excluded |
| Two definitions of "exact" (agreement's differing count vs the atom-set count) | the same report could call different interventions closest | one definition, the atom set; the agreement function keeps only P/R/F1 |
| A start state that is already terminal passed validity | an unplayable game counted as valid | rejected as unplayable at the start |
| "Relaxing and exact" counted inert rows and the no-effect control | overstated repair | targeted changes only, valid and changing |
| Methods never run printed as measured zeros | looked like results | tables list only the methods in the record |
| `verify` ignored GDL-II percepts | a rewrite dropping `sees` passed | percepts compared |
| Successor states were not un-renamed under `scramble`, and joint moves stayed in scrambled role order | metric 10 first showed 0 of 10 rules stable under scramble, against an identical grouping | both mapped back; scramble is now 10 of 10 |
| A weak test (`n/a` anywhere in a table) | would pass on a wrong cell | now checks the cell |

Checked and found correct: the extended BCubed formula; None vs 0 for
the not-measured cases; statement-index alignment across node ids,
sheets and provenance maps; determinism of the state set; the
reproduction rule; and the behaviour preservation of all six rewrites
(apart from percepts, now covered).

## Primary (2): reproduction, agreement, validity, consistency (development set)

Experiment 1 uses the 12 targeted reference changes on the five
development games that have reference variants. Drop-three and Monty
Hall have none. Each method offers one intervention per group, built in
two ways:

- `ownership` (the production split): delete what the group owns, relax
  its guards, keep what other groups need;
- `delete-group`: delete every statement of the group.

A change is **reproduced** when a *valid* intervention passes every one
of its probes. **Best behavioural F1** is the best agreement, over the
state set, between any valid intervention and the reference variant. It
is counted as 0 for a change where no valid intervention changes
anything, and the next column counts those changes, so a 0 that means
"not measurable" is never hidden. **Consistency** (Experiment 4) is
extended BCubed F1 between a method's grouping of a description and its
grouping of each of six behaviour-preserving rewrites. It is averaged
over the rewrites and 5 seeds, then over games.

| method | reproduced of 12, ownership / delete-group | mean best behavioural F1 over the 12, ownership / delete-group | changes with no valid, changing intervention, ownership / delete-group | valid rate, ownership / delete-group | consistency over rewrites, mean BCubed F1 [95% CI over games] |
|---|---|---|---|---|---|
| lgref | 1 / 1 | 0.12 / 0.09 | 2 / 5 | 0.28 / 0.33 | 0.96 [0.93, 0.98] |
| louvain_hard | 1 / 2 | 0.12 / 0.17 | 2 / 3 | 0.28 / 0.36 | 0.94 [0.91, 0.96] |
| leiden | 0 / 1 | 0.03 / 0.09 | 4 / 5 | 0.23 / 0.31 | 0.95 [0.93, 0.98] |
| leiden_hard | 0 / 1 | 0.03 / 0.09 | 4 / 5 | 0.24 / 0.32 | 0.94 [0.91, 0.96] |
| link_communities | 1 / 7 | 0.11 / 0.59 | 2 / 0 | 0.27 / 0.52 | 0.95 [0.93, 0.98] |
| dependency_louvain | 2 / 1 | 0.09 / 0.20 | 2 / 3 | 0.53 / 0.53 | 0.95 [0.92, 0.98] |
| components | 0 / 0 | 0.00 / 0.00 | 10 / 10 | 0.06 / 0.06 | 0.99 [0.98, 1.00] |
| name_tokens | 1 / 7 | 0.15 / 0.65 | 0 / 0 | 0.20 / 0.62 | 0.96 [0.95, 0.98] |
| singletons | 2 / 7 | 0.21 / 0.65 | 0 / 0 | 0.31 / 0.76 | 0.98 [0.97, 0.98] |
| one_group | 0 / 0 | 0.00 / 0.00 | 12 / 12 | 0.00 / 0.00 | 1.00 [1.00, 1.00] |
| random_matched | 0 / 1 | 0.01 / 0.01 | 3 / 2 | 0.12 / 0.23 | 0.62 [0.57, 0.69] |

What this says, plainly:

- **LGREF reproduces 1 of the 12 changes under each procedure:** Nim
  `take_one_only` under ownership, and tic-tac-toe `no_diagonal_line`
  under delete-group. On these games its groups rarely coincide with a
  single rule a change targets.
  - **Ownership:** its groups mostly protect what the target needs,
    because a helper the group would delete is also called from outside
    it. They come back empty or invalid.
  - **Delete-group:** removing a whole LGREF community removes several
    rules at once.
- **No method reproduces 4 of the 12 changes, under either
  procedure:** Nim `last_taker_wins`, Corridor `no_tempo`, and Othello
  `place_anywhere` and `end_on_pass`.
  - Three of the four replace a statement with a different one: a new
    payoff, a new terminal condition, a new placement condition.
    Deleting a group cannot express that, and relaxing a guard can only
    drop a conjunct.
  - Corridor's `no_tempo` is a conjunct drop, but no group makes the
    freshness test a relaxable guard of the 2-step permission. Its
    sibling `no_blocking` *is* reproduced exactly under ownership: name
    tokens relax `clear`.
  - The ceiling for these interventions on this benchmark is therefore
    8 of 12 targeted changes.
- **The groupings that reproduce the most changes are the finest ones.**
  Name tokens, singletons and link communities each reproduce 7 of 12
  under delete-group, with mean best F1 0.59–0.65.
  - This rewards having many small groups to try: singletons attempt
    251 interventions, LGREF 40. The matched-size random baseline (40
    attempts, 1 of 12) shows that size alone does not do it.
  - The comparison that isolates *grouping* rather than *number of
    tries* is still missing. It would need one intervention per method
    per change, chosen without the probes. Stage 5 designs it.
- **The infrastructure trap in Breakthrough works as intended.**
  Deleting only the capture permission (`legal … capture`) is invalid:
  black is left with no legal move in a non-terminal state. Deleting the
  `capture` definition reproduces `no_capture` exactly (F1 1.0, 0
  unintended atoms). No LGREF community isolates either one.
- **Validity is low for every method under ownership (0.06–0.53).** The
  invalid interventions are mostly empty (nothing removable), or leave a
  player with no legal move at the start or in a reachable state, or
  delete the role declarations. The second and third come from shared
  infrastructure (alternation, roles) inside the same group as a rule.
- **Consistency is high for every structural method (0.94–0.99), with
  two exceptions.** Scrambling names and permuting arguments change
  nothing, as the #314 design intended. Reordering statements changes
  LGREF's grouping in 11 of 35 runs (F1 0.98), because Louvain breaks
  ties by statement position. Extracting, inlining and duplicating
  helpers cost 0.05–0.11 F1. `components` and `one_group` are the most
  consistent, trivially so. The random baseline is the floor (0.62).

### Experiment 1 in full

Per change, `R` gives the number of valid interventions that reproduce
it. The number is the best behavioural F1 among valid interventions,
and the parenthesis gives the unintended atoms at that intervention.

Procedure `ownership`:

| method | targeted changes reproduced | attempted | empty | valid rate | valid and changing | no-effect controls reproduced |
|---|---|---|---|---|---|---|
| lgref | 1 / 12 | 40 | 7 | 0.275 | 11 | 0 / 1 |
| louvain_hard | 1 / 12 | 39 | 7 | 0.282 | 11 | 0 / 1 |
| leiden | 0 / 12 | 39 | 7 | 0.231 | 9 | 0 / 1 |
| leiden_hard | 0 / 12 | 38 | 7 | 0.237 | 9 | 0 / 1 |
| link_communities | 1 / 12 | 83 | 22 | 0.265 | 21 | 1 / 1 |
| dependency_louvain | 2 / 12 | 19 | 0 | 0.526 | 10 | 0 / 1 |
| components | 0 / 12 | 16 | 0 | 0.062 | 1 | 0 / 1 |
| name_tokens | 1 / 12 | 79 | 38 | 0.203 | 15 | 1 / 1 |
| singletons | 2 / 12 | 251 | 122 | 0.315 | 42 | 0 / 1 |
| one_group | 0 / 12 | 5 | 0 | 0.000 | 0 | 0 / 1 |
| random_matched | 0 / 12 | 40 | 3 | 0.125 | 5 | 0 / 1 |

Per change: R = reproduced by some valid intervention (count), F1 = best behavioural F1 among valid interventions (unintended atoms at that one).

| change | lgref | louvain_hard | leiden | leiden_hard | link_communities | dependency_louvain | components | name_tokens | singletons | one_group | random_matched |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tictactoe:no_column_line | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | R1 0.38 (565) | - n/a (-) | - 0.03 (615) | R1 0.46 (357) | - n/a (-) | - 0.00 (9987) |
| tictactoe:no_diagonal_line | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | - 0.34 (216) | - n/a (-) | - 0.04 (675) | - 0.36 (414) | - n/a (-) | - 0.00 (9987) |
| nim:last_taker_wins | - 0.00 (6) | - 0.00 (6) | - n/a (-) | - n/a (-) | - 0.00 (6) | - n/a (-) | - n/a (-) | - 0.67 (0) | - 0.67 (0) | - n/a (-) | - n/a (-) |
| nim:take_one_only | R1 1.00 (0) | R1 1.00 (0) | - n/a (-) | - n/a (-) | R1 1.00 (0) | - n/a (-) | - n/a (-) | - 0.00 (2) | R1 1.00 (0) | - n/a (-) | - n/a (-) |
| corridor:no_blocking | - 0.40 (84) | - 0.40 (84) | - 0.40 (84) | - 0.40 (84) | - 0.32 (123) | R1 0.28 (209) | - 0.00 (32) | R1 1.00 (0) | - 0.00 (151) | - n/a (-) | - 0.00 (341) |
| corridor:no_boundary (no effect) | - | - | - | - | R1 | - | - | R1 | - | - | - |
| corridor:no_tempo | - 0.00 (341) | - 0.00 (341) | - 0.00 (315) | - 0.00 (315) | - 0.00 (235) | - 0.00 (235) | - 0.00 (32) | - 0.00 (315) | - 0.00 (151) | - n/a (-) | - 0.00 (341) |
| breakthrough5:no_capture | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (53988) | - 0.00 (25791) | - n/a (-) | - 0.00 (3208) | - 0.00 (53988) | - n/a (-) | - 0.00 (2541) |
| breakthrough5:no_diagonal_move | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (53988) | - 0.00 (25791) | - n/a (-) | - 0.00 (3208) | - 0.00 (53988) | - n/a (-) | - 0.00 (2541) |
| breakthrough5:no_far_row_win | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (107640) | - 0.00 (53988) | - 0.12 (24209) | - n/a (-) | - 0.00 (102) | - 0.06 (0) | - n/a (-) | - 0.06 (0) |
| othello4:end_on_pass | - 0.00 (30024) | - 0.00 (2544) | - 0.00 (30024) | - 0.00 (2544) | - 0.00 (2544) | - 0.00 (5912) | - n/a (-) | - 0.00 (5482) | - 0.00 (14225) | - n/a (-) | - 0.09 (4594) |
| othello4:no_flip | - 0.00 (30024) | - 0.00 (2544) | - 0.00 (30024) | - 0.00 (2544) | - 0.00 (2544) | - 0.00 (6145) | - n/a (-) | - 0.00 (5715) | - 0.00 (14225) | - n/a (-) | - n/a (-) |
| othello4:place_anywhere | - 0.02 (29719) | - 0.02 (29719) | - 0.02 (29719) | - 0.02 (29719) | - 0.02 (29719) | - 0.00 (5834) | - n/a (-) | - 0.03 (13939) | - 0.03 (13939) | - n/a (-) | - 0.00 (4827) |

Procedure `delete-group`:

| method | targeted changes reproduced | attempted | empty | valid rate | valid and changing | no-effect controls reproduced |
|---|---|---|---|---|---|---|
| lgref | 1 / 12 | 40 | 0 | 0.325 | 13 | 0 / 1 |
| louvain_hard | 2 / 12 | 39 | 0 | 0.359 | 14 | 0 / 1 |
| leiden | 1 / 12 | 39 | 0 | 0.308 | 12 | 0 / 1 |
| leiden_hard | 1 / 12 | 38 | 0 | 0.316 | 12 | 0 / 1 |
| link_communities | 7 / 12 | 83 | 0 | 0.518 | 43 | 0 / 1 |
| dependency_louvain | 1 / 12 | 19 | 0 | 0.526 | 10 | 0 / 1 |
| components | 0 / 12 | 16 | 0 | 0.062 | 1 | 0 / 1 |
| name_tokens | 7 / 12 | 79 | 0 | 0.620 | 49 | 0 / 1 |
| singletons | 7 / 12 | 251 | 0 | 0.757 | 151 | 0 / 1 |
| one_group | 0 / 12 | 5 | 0 | 0.000 | 0 | 0 / 1 |
| random_matched | 1 / 12 | 40 | 0 | 0.225 | 9 | 0 / 1 |

Per change: R = reproduced by some valid intervention (count), F1 = best behavioural F1 among valid interventions (unintended atoms at that one).

| change | lgref | louvain_hard | leiden | leiden_hard | link_communities | dependency_louvain | components | name_tokens | singletons | one_group | random_matched |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tictactoe:no_column_line | - 0.00 (267) | - 0.00 (267) | - 0.00 (267) | - 0.00 (267) | R1 1.00 (0) | R1 0.76 (208) | - n/a (-) | R1 1.00 (0) | R3 1.00 (0) | - n/a (-) | - 0.00 (10120) |
| tictactoe:no_diagonal_line | R1 1.00 (0) | R1 1.00 (0) | R1 1.00 (0) | R1 1.00 (0) | R2 1.00 (0) | - 0.54 (459) | - n/a (-) | R1 1.00 (0) | R2 1.00 (0) | - n/a (-) | R1 0.03 (9987) |
| nim:last_taker_wins | - n/a (-) | - 0.00 (6) | - n/a (-) | - n/a (-) | - 0.00 (6) | - n/a (-) | - n/a (-) | - 0.67 (0) | - 0.67 (0) | - n/a (-) | - n/a (-) |
| nim:take_one_only | - n/a (-) | R1 1.00 (0) | - n/a (-) | - n/a (-) | R1 1.00 (0) | - n/a (-) | - n/a (-) | R1 1.00 (0) | R2 1.00 (0) | - n/a (-) | - n/a (-) |
| corridor:no_blocking | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (32) | - 0.00 (235) | - 0.00 (20) | - n/a (-) | - 0.00 (365) |
| corridor:no_boundary (no effect) | - | - | - | - | - | - | - | - | - | - | - |
| corridor:no_tempo | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (235) | - 0.00 (32) | - 0.00 (235) | - 0.00 (20) | - n/a (-) | - 0.00 (365) |
| breakthrough5:no_capture | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | R1 1.00 (0) | - 0.96 (1657) | - n/a (-) | R1 1.00 (0) | R1 1.00 (0) | - n/a (-) | - 0.00 (2541) |
| breakthrough5:no_diagonal_move | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | R2 1.00 (0) | - 0.00 (22756) | - n/a (-) | R1 1.00 (0) | R1 1.00 (0) | - n/a (-) | - 0.00 (2541) |
| breakthrough5:no_far_row_win | - n/a (-) | - n/a (-) | - n/a (-) | - n/a (-) | R1 1.00 (0) | - 0.13 (21150) | - n/a (-) | R2 1.00 (0) | R2 1.00 (0) | - n/a (-) | - 0.06 (0) |
| othello4:end_on_pass | - 0.04 (10076) | - 0.04 (10076) | - 0.04 (10076) | - 0.04 (10076) | - 0.04 (10076) | - 0.04 (10506) | - n/a (-) | - 0.09 (4594) | - 0.09 (4594) | - n/a (-) | - 0.08 (5078) |
| othello4:no_flip | - 0.00 (5715) | - 0.00 (430) | - 0.00 (5715) | - 0.00 (430) | R1 1.00 (0) | - n/a (-) | - n/a (-) | R2 1.00 (0) | R2 1.00 (0) | - n/a (-) | - 0.00 (144) |
| othello4:place_anywhere | - 0.00 (10725) | - 0.01 (7987) | - 0.00 (10725) | - 0.01 (7987) | - 0.01 (7987) | - 0.00 (10725) | - n/a (-) | - 0.03 (13939) | - 0.03 (13939) | - n/a (-) | - 0.00 (10725) |

### Experiment 4: consistency per rewrite

Mean BCubed F1 [95% CI over games]. In parentheses: runs whose groups
are exactly the same set of groups, out of game × seed runs. A
duplicated group collapses here but costs BCubed multiplicity, which is
why "identical" can exceed what F1 = 1 would suggest.

| method | scramble | reorder | extract | inline | duplicate | permute | mean over rewrites |
|---|---|---|---|---|---|---|---|
| lgref | 1.00 [1.00, 1.00] (35/35) | 0.98 [0.97, 1.00] (24/35) | 0.95 [0.92, 0.98] (5/35) | 0.89 [0.79, 0.97] (10/35) | 0.91 [0.88, 0.95] (5/35) | 1.00 [1.00, 1.00] (35/35) | 0.96 [0.93, 0.98] |
| louvain_hard | 1.00 [1.00, 1.00] (35/35) | 0.95 [0.90, 0.98] (12/35) | 0.93 [0.88, 0.97] (8/35) | 0.91 [0.87, 0.95] (6/35) | 0.86 [0.80, 0.91] (1/35) | 1.00 [1.00, 1.00] (35/35) | 0.94 [0.91, 0.96] |
| leiden | 1.00 [1.00, 1.00] (35/35) | 0.98 [0.97, 1.00] (21/35) | 0.96 [0.92, 0.98] (5/35) | 0.88 [0.79, 0.97] (10/35) | 0.90 [0.86, 0.95] (5/35) | 1.00 [1.00, 1.00] (35/35) | 0.95 [0.93, 0.98] |
| leiden_hard | 1.00 [1.00, 1.00] (35/35) | 0.94 [0.88, 0.98] (11/35) | 0.93 [0.87, 0.97] (6/35) | 0.90 [0.86, 0.95] (8/35) | 0.86 [0.81, 0.91] (2/35) | 1.00 [1.00, 1.00] (35/35) | 0.94 [0.91, 0.96] |
| link_communities | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 0.98 [0.96, 1.00] (1/7) | 0.85 [0.75, 0.93] (1/7) | 0.90 [0.84, 0.96] (1/7) | 1.00 [1.00, 1.00] (7/7) | 0.95 [0.93, 0.98] |
| dependency_louvain | 1.00 [1.00, 1.00] (35/35) | 0.96 [0.90, 1.00] (24/35) | 0.93 [0.89, 0.97] (5/35) | 0.90 [0.84, 0.96] (5/35) | 0.90 [0.85, 0.94] (0/35) | 1.00 [1.00, 1.00] (35/35) | 0.95 [0.92, 0.98] |
| components | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 0.95 [0.88, 0.99] (4/7) | 0.99 [0.98, 1.00] (6/7) | 1.00 [1.00, 1.00] (7/7) | 0.99 [0.98, 1.00] |
| name_tokens | 0.99 [0.97, 1.00] (5/7) | 1.00 [1.00, 1.00] (7/7) | 0.99 [0.98, 0.99] (2/7) | 0.95 [0.92, 0.97] (1/7) | 0.85 [0.77, 0.93] (2/7) | 1.00 [1.00, 1.00] (7/7) | 0.96 [0.95, 0.98] |
| singletons | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 0.98 [0.97, 0.99] (7/7) | 0.95 [0.93, 0.98] (1/7) | 0.92 [0.88, 0.95] (7/7) | 1.00 [1.00, 1.00] (7/7) | 0.98 [0.97, 0.98] |
| one_group | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] (7/7) | 1.00 [1.00, 1.00] |
| random_matched | 1.00 [1.00, 1.00] (35/35) | 0.46 [0.44, 0.49] (6/35) | 0.45 [0.34, 0.64] (5/35) | 0.47 [0.34, 0.66] (5/35) | 0.35 [0.31, 0.38] (0/35) | 1.00 [1.00, 1.00] (35/35) | 0.62 [0.57, 0.69] |

## Secondary: subjective metrics (development set)

### Blind Claude review of each method's grouping

One fresh reviewer agent per game saw every method's grouping under a
neutral label, in a seeded random order, with the same prompt
(`lgref.bench.review.PROMPT`). It never saw a method name or the
reference sheet. Each cell gives the overall score (1–5), with the mean
per-group score in parentheses. Identical groupings were shown once and
share a score: LGREF and Leiden coincide on several games. The
reviewers are Claude agents, the same model family as the method's
author. A human review would remove that limitation.

| method | tictactoe | nim | corridor | breakthrough5 | othello4 | dropthree | montyhall | overall, mean over games [95% CI] | group score, mean over games [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 4 (4.7) | 3 (4.0) | 4 (4.3) | 4 (4.2) | 3 (3.6) | 4 (4.3) | 3 (3.9) | 3.57 [3.14, 3.86] | 4.15 [3.91, 4.39] |
| louvain_hard | 3 (4.4) | 3 (3.4) | 4 (4.1) | 3 (4.2) | 3 (4.0) | 3 (3.8) | 4 (4.1) | 3.29 [3.00, 3.57] | 4.01 [3.76, 4.21] |
| leiden | 4 (4.7) | 3 (4.0) | 3 (4.2) | 4 (4.2) | 3 (3.6) | 4 (4.3) | 3 (3.9) | 3.43 [3.14, 3.86] | 4.14 [3.90, 4.37] |
| leiden_hard | 2 (4.2) | 2 (3.0) | 3 (4.3) | 3 (4.2) | 3 (4.0) | 3 (4.2) | 3 (4.2) | 2.71 [2.43, 3.00] | 4.02 [3.66, 4.25] |
| link_communities | 3 (4.6) | 3 (4.0) | 3 (4.1) | 3 (4.2) | 3 (3.6) | 4 (4.3) | 3 (4.3) | 3.14 [3.00, 3.43] | 4.17 [3.94, 4.38] |
| dependency_louvain | 2 (3.2) | 2 (3.3) | 2 (4.3) | 3 (4.2) | 2 (2.5) | 2 (4.0) | 2 (4.0) | 2.14 [2.00, 2.43] | 3.66 [3.18, 4.08] |
| components | 4 (4.8) | 3 (3.7) | 2 (4.2) | 1 (3.7) | 1 (3.0) | 4 (4.5) | 1 (3.5) | 2.29 [1.43, 3.29] | 3.90 [3.49, 4.33] |
| name_tokens | 4 (4.6) | 4 (4.2) | 3 (4.0) | 4 (4.5) | 3 (3.9) | 4 (4.1) | 4 (4.3) | 3.71 [3.43, 4.00] | 4.24 [4.07, 4.41] |
| singletons | 1 (2.7) | 2 (2.9) | 1 (2.2) | 2 (2.6) | 1 (2.3) | 1 (2.4) | 1 (2.4) | 1.29 [1.00, 1.57] | 2.49 [2.34, 2.66] |
| one_group | 1 (2.0) | 1 (1.0) | 1 (1.0) | 1 (1.0) | 1 (1.0) | 1 (1.0) | 1 (2.0) | 1.00 [1.00, 1.00] | 1.29 [1.00, 1.71] |
| random_matched | 1 (1.0) | 1 (1.6) | 1 (1.0) | 1 (1.0) | 1 (1.1) | 1 (1.0) | 1 (1.0) | 1.00 [1.00, 1.00] | 1.11 [1.00, 1.29] |

Reading:

- The trivial and random groupings score 1.0–1.3 overall, and every
  structural method scores above them. The review does discriminate.
- **LGREF scores 3.57 [3.14, 3.86] and the name-token baseline 3.71
  [3.43, 4.00].** Their intervals overlap. The reviewers' recurring
  criticisms of LGREF are "two end rules merged" and "setup merged with
  the board update". On Othello: "one huge group swallows most of the
  actual rules".
- On these games, readers find a grouping by predicate name about as
  readable as LGREF's. That is consistent with the reference-sheet
  result below.

### BCubed against the provisional reference sheets

The sheets were revised on 2026-11-27 (#363) under the user's convention
that geometry and arithmetic are language, not rules. 84 statements are
now unassigned, and so are not scored. The tables are F1, then
precision, recall and shared-statement recovery. Seed spread is shown as
(min–max) where it is not zero.

#### F1
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.683 (0.68-0.68) | 0.776 | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.702 [0.614, 0.780] | - |
| louvain_hard | 0.747 (0.74-0.75) | 0.779 (0.78-0.79) | 0.534 (0.53-0.53) | 0.707 (0.67-0.75) | 0.704 | 0.503 (0.50-0.52) | 0.598 (0.58-0.65) | 0.653 [0.578, 0.724] | -0.049 [-0.155, 0.057] |
| leiden | 0.682 (0.68-0.68) | 0.789 (0.78-0.80) | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.704 [0.615, 0.783] | 0.002 [-0.000, 0.006] |
| leiden_hard | 0.747 (0.74-0.75) | 0.780 (0.77-0.80) | 0.532 (0.53-0.53) | 0.719 (0.70-0.75) | 0.704 | 0.504 (0.50-0.52) | 0.602 (0.58-0.64) | 0.655 [0.579, 0.727] | -0.046 [-0.154, 0.061] |
| link_communities | 0.707 | 0.720 | 0.790 | 0.472 | 0.848 | 0.520 | 0.786 | 0.692 [0.589, 0.784] | -0.010 [-0.042, 0.030] |
| dependency_louvain | 0.429 (0.43-0.43) | 0.617 | 0.445 | 0.384 | 0.600 | 0.587 | 0.304 (0.30-0.30) | 0.481 [0.398, 0.563] | -0.221 [-0.344, -0.102] |
| components | 0.496 | 0.632 | 0.766 | 0.347 | 0.870 | 0.456 | 0.891 | 0.637 [0.493, 0.780] | -0.065 [-0.140, 0.016] |
| name_tokens | 0.621 | 0.751 | 0.786 | 0.627 | 0.699 | 0.472 | 0.744 | 0.671 [0.591, 0.740] | -0.030 [-0.072, 0.023] |
| singletons | 0.160 | 0.300 | 0.233 | 0.387 | 0.375 | 0.258 | 0.216 | 0.276 [0.220, 0.334] | -0.426 [-0.532, -0.302] |
| one_group | 0.447 | 0.367 | 0.465 | 0.347 | 0.568 | 0.368 | 0.520 | 0.440 [0.386, 0.500] | -0.261 [-0.325, -0.206] |
| random_matched | 0.303 (0.26-0.35) | 0.322 (0.27-0.40) | 0.375 (0.33-0.44) | 0.353 (0.30-0.41) | 0.422 (0.32-0.59) | 0.325 (0.29-0.37) | 0.405 (0.36-0.49) | 0.358 [0.328, 0.389] | -0.344 [-0.411, -0.267] |

#### Precision
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.643 (0.64-0.64) | 0.792 | 0.735 | 0.395 (0.39-0.40) | 0.639 | 0.482 | 0.785 | 0.639 [0.533, 0.738] | - |
| louvain_hard | 0.787 (0.78-0.80) | 0.897 | 0.774 (0.74-0.79) | 0.840 (0.83-0.89) | 0.769 | 0.502 (0.50-0.50) | 0.831 (0.80-0.83) | 0.771 [0.674, 0.843] | 0.132 [0.055, 0.245] |
| leiden | 0.643 (0.64-0.64) | 0.813 (0.79-0.82) | 0.735 | 0.395 (0.39-0.40) | 0.639 | 0.482 | 0.785 | 0.642 [0.534, 0.743] | 0.003 [0.000, 0.009] |
| leiden_hard | 0.787 (0.78-0.80) | 0.900 (0.90-0.91) | 0.785 (0.75-0.79) | 0.849 (0.83-0.89) | 0.769 | 0.503 (0.50-0.50) | 0.826 (0.80-0.83) | 0.774 [0.674, 0.845] | 0.135 [0.056, 0.250] |
| link_communities | 0.734 | 0.660 | 0.765 | 0.348 | 0.736 | 0.484 | 0.823 | 0.650 [0.527, 0.758] | 0.011 [-0.047, 0.062] |
| dependency_louvain | 0.912 (0.91-0.91) | 0.861 | 0.825 | 0.960 | 1.000 | 0.748 | 0.854 | 0.880 [0.821, 0.937] | 0.241 [0.128, 0.370] |
| components | 0.341 | 0.462 | 0.648 | 0.210 | 0.769 | 0.307 | 0.804 | 0.506 [0.347, 0.669] | -0.133 [-0.242, -0.020] |
| name_tokens | 0.803 | 1.000 | 0.965 | 0.741 | 0.875 | 0.822 | 1.000 | 0.887 [0.818, 0.957] | 0.248 [0.202, 0.296] |
| singletons | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 [1.000, 1.000] | 0.361 [0.262, 0.467] |
| one_group | 0.289 | 0.225 | 0.303 | 0.210 | 0.396 | 0.226 | 0.352 | 0.286 [0.241, 0.335] | -0.353 [-0.446, -0.265] |
| random_matched | 0.364 (0.32-0.41) | 0.364 (0.30-0.45) | 0.387 (0.33-0.48) | 0.292 (0.25-0.35) | 0.442 (0.33-0.59) | 0.311 (0.27-0.40) | 0.414 (0.36-0.47) | 0.368 [0.331, 0.404] | -0.271 [-0.351, -0.190] |

#### Recall
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.728 (0.72-0.73) | 0.759 | 0.839 | 0.743 | 0.934 | 0.667 | 0.893 | 0.795 [0.730, 0.862] | - |
| louvain_hard | 0.711 (0.71-0.71) | 0.689 (0.68-0.71) | 0.408 (0.40-0.42) | 0.611 (0.56-0.65) | 0.648 | 0.504 (0.50-0.53) | 0.468 (0.45-0.55) | 0.577 [0.495, 0.655] | -0.218 [-0.333, -0.107] |
| leiden | 0.726 (0.72-0.73) | 0.766 (0.75-0.78) | 0.839 | 0.743 | 0.934 | 0.667 | 0.893 | 0.795 [0.730, 0.862] | 0.001 [-0.001, 0.003] |
| leiden_hard | 0.711 (0.71-0.71) | 0.688 (0.67-0.72) | 0.402 (0.40-0.41) | 0.623 (0.61-0.65) | 0.648 | 0.506 (0.50-0.53) | 0.476 (0.45-0.54) | 0.579 [0.496, 0.656] | -0.216 [-0.332, -0.106] |
| link_communities | 0.682 | 0.793 | 0.816 | 0.730 | 1.000 | 0.561 | 0.752 | 0.762 [0.672, 0.858] | -0.033 [-0.083, 0.017] |
| dependency_louvain | 0.281 (0.28-0.28) | 0.481 | 0.305 | 0.240 | 0.429 | 0.483 | 0.185 (0.18-0.18) | 0.343 [0.263, 0.425] | -0.452 [-0.564, -0.331] |
| components | 0.909 | 1.000 | 0.937 | 1.000 | 1.000 | 0.885 | 1.000 | 0.962 [0.925, 0.991] | 0.167 [0.114, 0.218] |
| name_tokens | 0.506 | 0.602 | 0.663 | 0.543 | 0.582 | 0.331 | 0.592 | 0.546 [0.464, 0.610] | -0.249 [-0.304, -0.197] |
| singletons | 0.087 | 0.176 | 0.132 | 0.240 | 0.231 | 0.148 | 0.121 | 0.162 [0.125, 0.202] | -0.633 [-0.705, -0.563] |
| one_group | 0.986 | 1.000 | 1.000 | 1.000 | 1.000 | 0.984 | 1.000 | 0.996 [0.990, 1.000] | 0.201 [0.138, 0.261] |
| random_matched | 0.260 (0.21-0.32) | 0.290 (0.24-0.36) | 0.364 (0.32-0.41) | 0.447 (0.37-0.55) | 0.407 (0.30-0.59) | 0.343 (0.26-0.41) | 0.398 (0.35-0.51) | 0.358 [0.312, 0.402] | -0.436 [-0.493, -0.374] |

#### Shared-statement recovery
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.375 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.188 [0.000, 0.375] | - |
| louvain_hard | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| leiden | 0.375 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.188 [0.000, 0.375] | 0.000 [0.000, 0.000] |
| leiden_hard | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| link_communities | 0.875 | n/a | n/a | n/a | n/a | 0.800 | n/a | 0.838 [0.800, 0.875] | 0.650 [0.500, 0.800] |
| dependency_louvain | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| components | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| name_tokens | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| singletons | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| one_group | 0.000 | n/a | n/a | n/a | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.188 [-0.375, 0.000] |
| random_matched | 0.079 (0.00-0.25) | n/a | n/a | n/a | n/a | 0.120 (0.00-0.40) | n/a | 0.100 [0.079, 0.120] | -0.088 [-0.296, 0.120] |

#### Pair-counting ARI (for continuity with #315 only)
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.486 (0.49-0.49) | 0.521 | 0.681 | 0.208 | 0.508 | 0.116 | 0.711 | 0.462 [0.301, 0.609] | - |
| louvain_hard | 0.581 (0.58-0.58) | 0.537 (0.53-0.56) | 0.117 (0.10-0.13) | 0.458 (0.42-0.51) | 0.339 | 0.127 (0.13-0.13) | 0.170 (0.15-0.21) | 0.333 [0.197, 0.468] | -0.129 [-0.355, 0.071] |
| leiden | 0.488 (0.49-0.49) | 0.538 (0.52-0.55) | 0.681 | 0.208 | 0.508 | 0.116 | 0.711 | 0.464 [0.303, 0.610] | 0.003 [0.000, 0.007] |
| leiden_hard | 0.581 (0.58-0.58) | 0.528 (0.52-0.56) | 0.111 (0.09-0.11) | 0.471 (0.45-0.51) | 0.339 | 0.128 (0.13-0.13) | 0.162 (0.15-0.18) | 0.331 [0.193, 0.467] | -0.130 [-0.359, 0.075] |
| link_communities | 0.547 | 0.480 | 0.774 | 0.195 | 0.438 | 0.105 | 0.701 | 0.463 [0.292, 0.627] | 0.001 [-0.036, 0.041] |
| dependency_louvain | 0.014 (0.01-0.02) | 0.241 | 0.070 | -0.040 | 0.071 | 0.076 | 0.025 | 0.065 [0.015, 0.131] | -0.396 [-0.547, -0.240] |
| components | 0.016 | 0.142 | 0.516 | 0.040 | 0.266 | -0.000 | 0.838 | 0.260 [0.068, 0.491] | -0.202 [-0.329, -0.071] |
| name_tokens | 0.563 | 0.518 | 0.802 | 0.339 | 0.382 | 0.093 | 0.675 | 0.482 [0.316, 0.639] | 0.020 [-0.046, 0.082] |
| singletons | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 [0.000, 0.000] | -0.462 [-0.609, -0.301] |
| one_group | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 [0.000, 0.000] | -0.462 [-0.609, -0.301] |
| random_matched | -0.003 (-0.05-0.04) | -0.006 (-0.07-0.06) | 0.011 (-0.08-0.15) | -0.010 (-0.09-0.09) | -0.006 (-0.10-0.13) | -0.004 (-0.03-0.02) | 0.005 (-0.10-0.16) | -0.002 [-0.006, 0.003] | -0.464 [-0.606, -0.305] |

Reading:

- **With geometry and arithmetic out of the rules, LGREF scores 0.702
  [0.614, 0.780].** Before the revision it was 0.664.
- **The overlap step's advantage shrinks.** It is +0.049 [−0.057,
  0.155] (LGREF against Louvain without overlap), and the interval now
  includes 0. Leiden in place of Louvain still changes nothing.
- **Coarse groupings no longer score close.** Components drop to 0.637
  and one group to 0.440. Much of their earlier score came from the
  shared geometry statements.
- **Name tokens (0.671) and link communities (0.692) are within
  intervals of LGREF.** Name tokens have the highest precision (0.887);
  LGREF has recall 0.795.
- **LGREF keeps few shared statements shared** (recovery 0.19). Link
  communities keep most (0.84).

## Setup statements, and LGREF's language verdict (development set)

Statements are split into kinds per game: language (geometry and
arithmetic), init (the initial position), role and outcome (terminal,
goal), and rule. The reference language list is provisional and was
written by Claude (`lgref/bench/references/kinds.yaml`). P and R are
precision and recall for "language, not an ablation candidate", over
the statements that are language or rule. The rule statements each
verdict wrongly marks as language are named.

| game | statements: language / init / role / outcome / rule (reference) | definitive indicator: P / R for "language" | rules it marks language | #202 cluster verdict: P / R | rules it marks language |
|---|---|---|---|---|---|
| tictactoe | 0 / 10 / 2 / 5 / 18 | n/a / n/a | none | n/a / n/a | none |
| nim | 7 / 2 / 2 / 2 / 9 | 1.00 / 1.00 | none | 1.00 / 1.00 | none |
| corridor | 8 / 5 / 2 / 3 / 26 | 0.50 / 1.00 | inside#15, inside#16, inside#17, inside#18, inside#19, inside#20, inside#21, inside#22 | 0.50 / 1.00 | inside#15, inside#16, inside#17, inside#18, inside#19, inside#20, inside#21, inside#22 |
| breakthrough5 | 23 / 21 / 2 / 6 / 23 | 0.92 / 1.00 | goalrow#41, goalrow#42 | n/a / 0.00 | none |
| othello4 | 38 / 5 / 2 / 4 / 26 | 1.00 / 1.00 | none | 1.00 / 0.71 | none |
| dropthree | 5 / 13 / 2 / 5 / 20 | 1.00 / 1.00 | none | n/a / 0.00 | none |
| montyhall | 3 / 4 / 2 / 4 / 17 | 1.00 / 1.00 | none | n/a / 0.00 | none |

Reading:

- **The definitive indicator** (no state dependence at any depth) **marks
  real rules as setup in two games.** In Corridor it is the eight
  `inside` facts, which are the boundary rule. In Breakthrough it is the
  two `goalrow` facts, which are the far-row win. Both are fixed tables
  that *are* a rule, the case `lgref/identify/language.py` already
  names for Royal Chess's `boulder_first_dest`. Read strictly, the
  user's order ("no state dependence = language") would leave these
  rules un-ablated. This is recorded, not fixed.
- **The #202 cluster verdict never marks a rule as language here**, but
  it misses language: recall is 0 on Breakthrough, drop-three and Monty
  Hall, where the static helpers cluster with the rules that use them.
- Ablation by substitution is not a category. Removing a piece type or
  a whole mechanism is a REMOVE, and changing a constant is a RELAX or a
  REPLACE (`protocol.md`, #400).

## Experiment 3: sensitivity of LGREF (development set)

One factor at a time from production, 30 seeds, BCubed F1 against the
revised provisional sheets. This is a subjective metric, so read it with
that in mind.

| variant | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs production [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| production | 0.683 (0.68-0.68) | 0.776 | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.702 [0.614, 0.780] | - |
| weight:legality:x0.5 | 0.683 (0.68-0.68) | 0.771 (0.75-0.77) | 0.784 | 0.516 (0.52-0.52) | 0.791 | 0.560 | 0.836 | 0.706 [0.615, 0.786] | 0.004 [-0.002, 0.014] |
| weight:legality:x2 | 0.683 (0.68-0.68) | 0.746 (0.74-0.75) | 0.784 | 0.554 (0.55-0.55) | 0.717 | 0.560 | 0.836 | 0.697 [0.621, 0.767] | -0.005 [-0.022, 0.012] |
| weight:legality:off | 0.659 (0.66-0.66) | 0.759 (0.76-0.76) | 0.788 | 0.493 | 0.718 | 0.541 | 0.824 | 0.683 [0.594, 0.765] | -0.019 [-0.028, -0.009] |
| weight:predicate:x0.5 | 0.672 | 0.779 (0.77-0.78) | 0.784 | 0.549 | 0.681 | 0.551 (0.55-0.56) | 0.813 | 0.690 [0.618, 0.762] | -0.012 [-0.037, 0.009] |
| weight:predicate:x2 | 0.699 (0.69-0.70) | 0.757 (0.74-0.76) | 0.784 | 0.498 | 0.797 | 0.560 | 0.801 | 0.699 [0.610, 0.777] | -0.002 [-0.018, 0.015] |
| weight:predicate:off | 0.671 | 0.779 (0.71-0.80) | 0.799 | 0.549 | 0.606 | 0.506 | 0.801 | 0.673 [0.589, 0.755] | -0.029 [-0.075, 0.008] |
| weight:same_head:x0.5 | 0.691 (0.69-0.70) | 0.735 (0.73-0.75) | 0.784 | 0.482 | 0.797 | 0.560 | 0.791 | 0.691 [0.601, 0.770] | -0.010 [-0.030, 0.011] |
| weight:same_head:x2 | 0.683 (0.68-0.68) | 0.796 (0.73-0.81) | 0.784 | 0.551 | 0.796 | 0.554 (0.55-0.56) | 0.818 (0.81-0.84) | 0.712 [0.625, 0.788] | 0.010 [-0.004, 0.024] |
| weight:same_head:off | 0.566 | 0.555 (0.55-0.56) | 0.424 | 0.574 | 0.691 (0.63-0.70) | 0.557 (0.55-0.56) | 0.359 | 0.532 [0.457, 0.602] | -0.169 [-0.307, -0.043] |
| weight:shared_state:x0.5 | 0.683 (0.68-0.68) | 0.776 | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.702 [0.614, 0.780] | 0.000 [0.000, 0.000] |
| weight:shared_state:x2 | 0.683 (0.68-0.68) | 0.773 (0.77-0.77) | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.701 [0.614, 0.779] | -0.000 [-0.001, 0.000] |
| weight:shared_state:off | 0.683 (0.68-0.68) | 0.782 (0.78-0.78) | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.703 [0.614, 0.781] | 0.001 [0.000, 0.003] |
| weight:temporal:x0.5 | 0.683 (0.68-0.68) | 0.773 (0.77-0.77) | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.701 [0.614, 0.780] | -0.000 [-0.001, 0.000] |
| weight:temporal:x2 | 0.683 (0.68-0.68) | 0.794 (0.78-0.80) | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.704 [0.615, 0.784] | 0.003 [0.000, 0.008] |
| weight:temporal:off | 0.683 (0.68-0.68) | 0.771 (0.77-0.77) | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.701 [0.614, 0.779] | -0.001 [-0.002, 0.000] |
| weight:terminal:x0.5 | 0.686 (0.69-0.69) | 0.776 | 0.784 | 0.554 (0.55-0.55) | 0.759 | 0.551 | 0.836 (0.84-0.84) | 0.706 [0.623, 0.780] | 0.005 [-0.003, 0.016] |
| weight:terminal:x2 | 0.679 | 0.776 | 0.784 | 0.447 | 0.759 | 0.541 (0.54-0.56) | 0.834 (0.81-0.84) | 0.688 [0.585, 0.779] | -0.013 [-0.033, -0.001] |
| weight:terminal:off | 0.686 (0.69-0.69) | 0.776 | 0.784 | 0.669 (0.66-0.67) | 0.901 | 0.578 | 0.836 (0.84-0.84) | 0.747 [0.669, 0.821] | 0.045 [0.003, 0.090] |
| hub_fraction:0.04 | 0.683 (0.68-0.68) | 0.776 | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.702 [0.614, 0.780] | 0.000 [0.000, 0.000] |
| hub_fraction:0.16 | 0.634 | 0.776 | 0.784 | 0.519 (0.39-0.56) | 0.759 | 0.499 | 0.836 | 0.687 [0.588, 0.776] | -0.015 [-0.034, 0.001] |
| hub_fraction:1.01 | 0.634 | 0.730 (0.72-0.77) | 0.589 (0.50-0.62) | 0.454 | 0.482 | 0.499 | 0.528 (0.47-0.61) | 0.560 [0.498, 0.629] | -0.142 [-0.224, -0.072] |
| resolution:0.5 | 0.685 | 0.823 (0.82-0.83) | 0.784 (0.78-0.79) | 0.438 | 0.855 | 0.543 | 0.838 | 0.710 [0.593, 0.814] | 0.008 [-0.028, 0.046] |
| resolution:1.0 | 0.683 (0.68-0.68) | 0.821 (0.82-0.84) | 0.784 | 0.438 | 0.855 | 0.560 | 0.838 | 0.711 [0.597, 0.813] | 0.009 [-0.026, 0.048] |
| resolution:1.5 | 0.683 (0.68-0.68) | 0.793 | 0.784 | 0.493 (0.45-0.51) | 0.855 | 0.560 | 0.836 (0.84-0.84) | 0.715 [0.614, 0.806] | 0.013 [-0.007, 0.044] |
| resolution:2.0 | 0.484 (0.48-0.49) | 0.793 | 0.559 | 0.512 | 0.797 | 0.552 (0.55-0.55) | 0.679 | 0.625 [0.541, 0.720] | -0.076 [-0.154, -0.003] |
| resolution:3.0 | 0.463 | 0.776 | 0.559 | 0.534 | 0.759 | 0.551 (0.55-0.55) | 0.626 (0.62-0.67) | 0.610 [0.534, 0.695] | -0.092 [-0.183, -0.022] |
| resolution:4.0 | 0.446 | 0.776 | 0.550 | 0.643 | 0.730 | 0.553 (0.55-0.55) | 0.550 | 0.607 [0.532, 0.690] | -0.095 [-0.199, 0.012] |
| tolerance:0.0 | 0.683 (0.68-0.68) | 0.776 | 0.784 | 0.516 (0.52-0.52) | 0.759 | 0.560 | 0.836 | 0.702 [0.614, 0.780] | 0.000 [0.000, 0.000] |
| tolerance:0.1 | 0.683 (0.68-0.68) | 0.713 (0.71-0.71) | 0.784 | 0.534 | 0.759 | 0.560 | 0.836 | 0.695 [0.616, 0.770] | -0.006 [-0.027, 0.008] |
| tolerance:0.2 | 0.683 (0.68-0.68) | 0.734 (0.73-0.74) | 0.784 | 0.534 | 0.759 | 0.560 | 0.836 | 0.698 [0.617, 0.773] | -0.003 [-0.018, 0.008] |
| overlap:0.1 | 0.711 (0.70-0.72) | 0.738 (0.74-0.74) | 0.782 | 0.369 (0.37-0.37) | 0.655 | 0.549 | 0.832 | 0.662 [0.545, 0.759] | -0.039 [-0.085, -0.000] |
| overlap:0.15 | 0.693 (0.69-0.70) | 0.772 (0.77-0.77) | 0.786 | 0.389 (0.39-0.39) | 0.655 | 0.540 | 0.836 | 0.667 [0.553, 0.766] | -0.035 [-0.074, 0.000] |
| overlap:0.35 | 0.691 (0.69-0.69) | 0.775 (0.77-0.79) | 0.779 | 0.556 (0.56-0.56) | 0.756 | 0.555 | 0.813 | 0.704 [0.624, 0.773] | 0.002 [-0.010, 0.016] |
| overlap:0.5 | 0.698 (0.69-0.70) | 0.771 (0.77-0.78) | 0.779 | 0.548 (0.55-0.55) | 0.724 | 0.555 | 0.813 | 0.698 [0.621, 0.767] | -0.003 [-0.018, 0.012] |
| overlap:1.01 | 0.698 (0.69-0.70) | 0.779 (0.78-0.79) | 0.779 | 0.598 (0.60-0.60) | 0.704 | 0.557 | 0.813 | 0.704 [0.635, 0.767] | 0.002 [-0.024, 0.033] |

- **Removing the same-head edge or the hub filter costs 0.14–0.17.**
  Removing the legality edge costs 0.02. A raw resolution of 2–4 costs
  0.08–0.10.
- **One setting beats production beyond its interval: turning off the
  terminal edge, +0.045 [0.003, 0.090].** This is new with the revised
  sheets. On the original sheets it was +0.031 [−0.000, 0.066].
  - It is **not** adopted. The method was frozen at `ab7b33b` before
    the sheets were revised, and the protocol forbids tuning after the
    freeze.
  - It is also a subjective metric resting on Claude-written sheets.
  - It is recorded here as the one sensitivity result that would have
    mattered. Whether a post-freeze variant should be evaluated
    alongside (as a second, separately labelled method) is the user's
    call.
- Nothing was adopted (`freeze.md`).

## Reproducing

```bash
python -m lgref.bench.experiments interventions --split dev --workers 3 --out docs/paper-a/runs/exp1_dev.json
python -m lgref.bench.experiments groupings   --split dev --seeds 30 --out docs/paper-a/runs/exp2_dev.json
python -m lgref.bench.experiments sensitivity --split dev --seeds 30 --out docs/paper-a/runs/exp3_dev.json
python -m lgref.bench.experiments invariance  --split dev --seeds 5  --out docs/paper-a/runs/exp4_dev.json
python -m lgref.bench.experiments rewrite_ablations --split dev --workers 3 --out docs/paper-a/runs/exp10_dev.json
python -m lgref.bench.report interventions docs/paper-a/runs/exp1_dev.json
python -m lgref.bench.report groupings     docs/paper-a/runs/exp2_dev.json
python -m lgref.bench.report sensitivity   docs/paper-a/runs/exp3_dev.json
python -m lgref.bench.review tictactoe nim corridor breakthrough5 othello4 dropthree montyhall   # packets
python -m lgref.bench.review --table tictactoe nim corridor breakthrough5 othello4 dropthree montyhall
python -m lgref.bench.setup
```

**Commits.** Each JSON record names the commit it ran at:

- `exp1`, `exp2`, `exp3` and `exp10` ran on the #363 working tree, on
  top of `d244ba4` (`+uncommitted`).
- `exp4` ran on the #358 tree (`ab7b33b+uncommitted`). It reads only
  groupings, which #363 did not change.
- `exp1`–`exp3` ran before the two fixes to the rewritten-description
  evaluator (see "Validation pass" below), which only `exp10` uses.
  `exp10` was re-run after them. The final files of this PR give the
  same rows for every experiment.
