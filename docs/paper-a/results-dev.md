# Paper A: development-set results (Experiments 1–4)

Issue #358. These results come from the **development set only**:
tic-tac-toe, Nim, Corridor, 5x5 Breakthrough, 4x4 Othello, drop-three
and Monty Hall (`protocol.md` explains why each game is in this set). No
test game has been scored. The method was frozen after these runs
(`freeze.md`).

**How to read this document.** The user's rule, recorded in
`protocol.md`:

- **Primary (objective):** behavioural intervention agreement, valid
  intervention rate, grouping consistency across equivalent encodings,
  and later, performance on unseen games.
- **Secondary (subjective):** BCubed F1 against the reference sheets
  (provisional, and written by the method's author), and a blind Claude
  review of each method's actual grouping. The review stands in for
  human readability and agreement. It is not a factual or exact
  evaluation.

Every reference sheet, variant and probe was written by Claude, the
author of the method. Intervals are 95% bootstrap intervals over
**games**, not over statements. With seven games (five for the
intervention experiments) they are wide.

## Primary: objective metrics (development set)

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

### Exactness and collateral damage (development set)

These were added at the user's instruction. For each targeted change,
take the intervention each method offers that comes closest to the
reference ablation: the valid one with the highest behavioural F1, ties
broken by fewer differing atoms. Two counts are reported for it:

- **differing atoms**: atoms where it and the reference disagree, in
  either direction. 0 means functionally exact.
- **collateral atoms**: atoms it changes that the reference leaves as
  they were, i.e. damage to other rules.

Atoms are summed over the changes that have such an intervention. The
"none valid and changing" column counts the changes that are excluded,
so a method with few valid interventions shows a small sum: see
`components` and `one_group`.

Procedure `ownership`:

| method | exact (of 12) | none valid and changing | differing atoms at the closest: legal / terminal+goal / next, summed over changes | collateral atoms: legal / terminal+goal / next | closest used a relaxation (exact) |
|---|---|---|---|---|---|
| lgref | 1 | 2 | 202014 / 2149 / 11197 | 148253 / 238 / 5715 | 5 (0) |
| louvain_hard | 1 | 2 | 206608 / 2643 / 5482 | 152847 / 732 / 0 | 7 (0) |
| leiden | 0 | 4 | 202008 / 2145 / 11197 | 148247 / 238 / 5715 | 5 (0) |
| leiden_hard | 0 | 4 | 206602 / 2639 / 5482 | 152841 / 732 / 0 | 7 (0) |
| link_communities | 1 | 2 | 131909 / 2396 / 5838 | 78148 / 485 / 356 | 3 (0) |
| dependency_louvain | 0 | 2 | 126512 / 5919 / 16870 | 72492 / 5313 / 11388 | 4 (0) |
| components | 0 | 10 | 87 / 64 / 0 | 0 / 64 / 0 | 0 (0) |
| name_tokens | 1 | 0 | 67509 / 10669 / 5715 | 13733 / 8195 / 233 | 2 (1) |
| singletons | 1 | 0 | 67544 / 3165 / 5482 | 13733 / 1069 / 0 | 1 (0) |
| one_group | 0 | 12 | 0 / 0 / 0 | 0 / 0 / 0 | 0 (0) |
| random_matched | 0 | 3 | 58655 / 12163 / 20490 | 4594 / 9909 / 20490 | 2 (0) |

Procedure `delete-group`:

| method | exact (of 12) | none valid and changing | differing atoms at the closest: legal / terminal+goal / next, summed over changes | collateral atoms: legal / terminal+goal / next | closest used a relaxation (exact) |
|---|---|---|---|---|---|
| lgref | 1 | 5 | 14616 / 3346 / 5715 | 7779 / 2980 / 233 | 0 (0) |
| louvain_hard | 2 | 3 | 22401 / 3597 / 5482 | 15564 / 3266 / 0 | 0 (0) |
| leiden | 1 | 5 | 14616 / 3346 / 5715 | 7779 / 2980 / 233 | 0 (0) |
| leiden_hard | 1 | 5 | 22395 / 3593 / 5482 | 15558 / 3266 / 0 | 0 (0) |
| link_communities | 7 | 0 | 22401 / 2573 / 0 | 15564 / 2569 / 0 | 0 (0) |
| dependency_louvain | 0 | 3 | 90704 / 9779 / 0 | 57728 / 9683 / 0 | 0 (0) |
| components | 0 | 10 | 87 / 64 / 0 | 0 / 64 / 0 | 0 (0) |
| name_tokens | 7 | 0 | 22617 / 2572 / 0 | 16030 / 2567 / 0 | 0 (0) |
| singletons | 7 | 0 | 22639 / 2508 / 0 | 16052 / 2503 / 0 | 0 (0) |
| one_group | 0 | 12 | 0 / 0 / 0 | 0 / 0 / 0 | 0 (0) |
| random_matched | 0 | 2 | 56514 / 10447 / 25456 | 2453 / 8326 / 19974 | 0 (0) |

How often the ownership split **modified** a rule (relaxed a guard at
its call site) instead of deleting it, over the non-empty
interventions:

- lgref: non-empty 33, relaxing 9, relaxing and exact for some change 0, relaxing and valid 5
- louvain_hard: non-empty 32, relaxing 11, relaxing and exact for some change 0, relaxing and valid 6
- leiden: non-empty 32, relaxing 9, relaxing and exact for some change 0, relaxing and valid 5
- leiden_hard: non-empty 31, relaxing 11, relaxing and exact for some change 0, relaxing and valid 6
- link_communities: non-empty 61, relaxing 13, relaxing and exact for some change 1, relaxing and valid 8
- dependency_louvain: non-empty 19, relaxing 6, relaxing and exact for some change 0, relaxing and valid 3
- components: non-empty 16
- name_tokens: non-empty 41, relaxing 10, relaxing and exact for some change 2, relaxing and valid 6
- singletons: non-empty 129, relaxing 4, relaxing and exact for some change 0, relaxing and valid 3
- one_group: non-empty 5
- random_matched: non-empty 37, relaxing 5, relaxing and exact for some change 0, relaxing and valid 1

Reading:

- **Exactness agrees with the probes.** Under delete-group, the methods
  that reproduce 7 of 12 changes by probes have an exact ablation for
  the same 7 (checked change by change). LGREF has one.
- **LGREF's closest ablations do heavy collateral damage.** Under
  ownership: about 148,000 legal-move atoms the reference leaves alone,
  summed over 10 changes and dominated by Breakthrough and Othello.
  Its groups remove more than one rule.
- **Relaxation, the "modify, don't delete" step, was used by 9 of
  LGREF's 33 non-empty ownership interventions.** Five of those were
  valid, and none was exact for any change. Across all methods, the
  only relaxing interventions that were exact for some change came from
  name tokens (2) and link communities (1).

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

F1, then precision, recall and shared-statement recovery. Seed spread
is shown as (min–max) where it is not zero.

#### F1
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.643 (0.64-0.65) | 0.638 | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.566, 0.758] | - |
| louvain_hard | 0.649 (0.65-0.65) | 0.608 (0.61-0.62) | 0.568 (0.53-0.57) | 0.659 (0.63-0.67) | 0.663 | 0.317 (0.31-0.33) | 0.598 (0.58-0.65) | 0.580 [0.485, 0.643] | -0.084 [-0.162, -0.007] |
| leiden | 0.642 (0.64-0.65) | 0.643 (0.64-0.65) | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.665 [0.567, 0.759] | 0.001 [-0.001, 0.002] |
| leiden_hard | 0.649 (0.65-0.65) | 0.610 (0.60-0.62) | 0.568 (0.56-0.57) | 0.664 (0.66-0.67) | 0.663 | 0.317 (0.31-0.33) | 0.602 (0.58-0.64) | 0.582 [0.486, 0.645] | -0.083 [-0.160, -0.004] |
| link_communities | 0.627 | 0.653 | 0.784 | 0.528 | 0.812 | 0.435 | 0.786 | 0.661 [0.557, 0.755] | -0.004 [-0.027, 0.021] |
| dependency_louvain | 0.463 (0.46-0.47) | 0.495 | 0.493 | 0.413 | 0.567 | 0.402 | 0.304 (0.30-0.30) | 0.448 [0.389, 0.504] | -0.216 [-0.335, -0.121] |
| components | 0.551 | 0.724 | 0.734 | 0.355 | 0.667 | 0.687 | 0.891 | 0.659 [0.539, 0.764] | -0.006 [-0.105, 0.104] |
| name_tokens | 0.507 | 0.557 | 0.735 | 0.571 | 0.705 | 0.246 | 0.744 | 0.580 [0.445, 0.686] | -0.084 [-0.129, -0.042] |
| singletons | 0.097 | 0.221 | 0.208 | 0.308 | 0.333 | 0.097 | 0.216 | 0.211 [0.147, 0.274] | -0.453 [-0.541, -0.362] |
| one_group | 0.516 | 0.521 | 0.426 | 0.355 | 0.450 | 0.667 | 0.520 | 0.494 [0.426, 0.562] | -0.171 [-0.290, -0.013] |
| random_matched | 0.286 (0.26-0.31) | 0.319 (0.26-0.37) | 0.350 (0.30-0.41) | 0.340 (0.29-0.40) | 0.347 (0.28-0.42) | 0.336 (0.31-0.36) | 0.405 (0.36-0.49) | 0.340 [0.316, 0.365] | -0.324 [-0.401, -0.231] |

#### Precision
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.783 (0.78-0.78) | 0.833 | 0.735 | 0.478 (0.48-0.48) | 0.632 | 0.735 | 0.785 | 0.712 [0.624, 0.784] | - |
| louvain_hard | 0.866 (0.86-0.88) | 0.917 | 0.793 (0.74-0.80) | 0.857 (0.85-0.90) | 0.850 | 0.744 (0.74-0.74) | 0.831 (0.80-0.83) | 0.837 [0.797, 0.873] | 0.125 [0.049, 0.222] |
| leiden | 0.783 (0.78-0.78) | 0.850 (0.83-0.86) | 0.735 | 0.478 (0.48-0.48) | 0.632 | 0.735 | 0.785 | 0.714 [0.624, 0.789] | 0.002 [0.000, 0.007] |
| leiden_hard | 0.866 (0.86-0.88) | 0.919 (0.92-0.93) | 0.803 (0.75-0.80) | 0.865 (0.85-0.90) | 0.850 | 0.744 (0.74-0.74) | 0.826 (0.80-0.83) | 0.839 [0.799, 0.875] | 0.127 [0.050, 0.227] |
| link_communities | 0.843 | 0.724 | 0.788 | 0.434 | 0.684 | 0.725 | 0.823 | 0.717 [0.612, 0.797] | 0.005 [-0.041, 0.045] |
| dependency_louvain | 0.972 (0.97-0.97) | 0.887 | 0.814 | 0.986 | 0.747 | 0.856 | 0.854 | 0.874 [0.816, 0.930] | 0.162 [0.080, 0.283] |
| components | 0.402 | 0.577 | 0.601 | 0.217 | 0.500 | 0.628 | 0.804 | 0.533 [0.404, 0.653] | -0.179 [-0.271, -0.096] |
| name_tokens | 0.865 | 1.000 | 0.969 | 0.769 | 0.919 | 0.915 | 1.000 | 0.920 [0.860, 0.972] | 0.208 [0.155, 0.255] |
| singletons | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 [1.000, 1.000] | 0.288 [0.216, 0.376] |
| one_group | 0.358 | 0.356 | 0.271 | 0.217 | 0.290 | 0.568 | 0.352 | 0.345 [0.276, 0.428] | -0.367 [-0.440, -0.282] |
| random_matched | 0.405 (0.37-0.44) | 0.454 (0.37-0.51) | 0.347 (0.30-0.42) | 0.291 (0.25-0.34) | 0.319 (0.26-0.40) | 0.591 (0.57-0.63) | 0.414 (0.36-0.47) | 0.403 [0.340, 0.478] | -0.309 [-0.372, -0.235] |

#### Recall
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.546 (0.54-0.55) | 0.516 | 0.818 | 0.698 (0.70-0.70) | 0.957 | 0.306 | 0.893 | 0.676 [0.511, 0.829] | - |
| louvain_hard | 0.519 (0.52-0.52) | 0.455 (0.45-0.46) | 0.443 (0.41-0.45) | 0.536 (0.50-0.55) | 0.543 | 0.201 (0.20-0.21) | 0.468 (0.45-0.55) | 0.452 [0.359, 0.515] | -0.224 [-0.348, -0.107] |
| leiden | 0.543 (0.54-0.55) | 0.517 (0.51-0.53) | 0.818 | 0.698 (0.70-0.70) | 0.957 | 0.306 | 0.893 | 0.676 [0.511, 0.829] | -0.000 [-0.001, 0.000] |
| leiden_hard | 0.519 (0.52-0.52) | 0.456 (0.45-0.47) | 0.440 (0.44-0.44) | 0.539 (0.52-0.55) | 0.543 | 0.201 (0.20-0.21) | 0.476 (0.45-0.54) | 0.453 [0.360, 0.516] | -0.223 [-0.348, -0.106] |
| link_communities | 0.499 | 0.595 | 0.780 | 0.674 | 1.000 | 0.311 | 0.752 | 0.659 [0.504, 0.808] | -0.018 [-0.067, 0.030] |
| dependency_louvain | 0.304 (0.30-0.31) | 0.343 | 0.353 | 0.261 | 0.457 | 0.263 | 0.185 (0.18-0.18) | 0.310 [0.252, 0.372] | -0.367 [-0.515, -0.211] |
| components | 0.872 | 0.972 | 0.944 | 0.980 | 1.000 | 0.759 | 1.000 | 0.932 [0.867, 0.984] | 0.256 [0.144, 0.371] |
| name_tokens | 0.358 | 0.386 | 0.592 | 0.454 | 0.571 | 0.142 | 0.592 | 0.442 [0.317, 0.547] | -0.234 [-0.296, -0.178] |
| singletons | 0.051 | 0.124 | 0.116 | 0.182 | 0.200 | 0.051 | 0.121 | 0.121 [0.080, 0.160] | -0.555 [-0.685, -0.418] |
| one_group | 0.925 | 0.972 | 1.000 | 0.980 | 1.000 | 0.807 | 1.000 | 0.955 [0.899, 0.993] | 0.278 [0.160, 0.400] |
| random_matched | 0.221 (0.20-0.24) | 0.246 (0.21-0.29) | 0.353 (0.30-0.40) | 0.411 (0.32-0.50) | 0.383 (0.30-0.48) | 0.235 (0.21-0.26) | 0.398 (0.35-0.51) | 0.321 [0.259, 0.376] | -0.355 [-0.466, -0.233] |

#### Shared-statement recovery
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.115 | 0.000 | n/a | 0.000 | n/a | 0.077 | n/a | 0.048 [0.000, 0.096] | - |
| louvain_hard | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| leiden | 0.115 | 0.000 | n/a | 0.000 | n/a | 0.077 | n/a | 0.048 [0.000, 0.096] | 0.000 [0.000, 0.000] |
| leiden_hard | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| link_communities | 0.269 | 1.000 | n/a | 1.000 | n/a | 0.769 | n/a | 0.760 [0.452, 1.000] | 0.712 [0.365, 1.000] |
| dependency_louvain | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| components | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| name_tokens | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| singletons | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| one_group | 0.000 | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 [0.000, 0.000] | -0.048 [-0.096, 0.000] |
| random_matched | 0.063 (0.00-0.15) | 0.183 (0.00-0.50) | n/a | 0.356 (0.00-1.00) | n/a | 0.174 (0.08-0.26) | n/a | 0.194 [0.093, 0.310] | 0.146 [0.006, 0.291] |

#### Pair-counting ARI (for continuity with #315 only)
| method | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs lgref [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| lgref | 0.394 (0.39-0.40) | 0.387 | 0.707 | 0.285 | 0.838 | 0.120 | 0.711 | 0.492 [0.308, 0.673] | - |
| louvain_hard | 0.424 (0.42-0.43) | 0.363 (0.36-0.38) | 0.212 (0.19-0.22) | 0.467 (0.45-0.47) | 0.335 | 0.077 (0.08-0.08) | 0.170 (0.15-0.21) | 0.293 [0.192, 0.388] | -0.199 [-0.412, 0.002] |
| leiden | 0.391 (0.39-0.40) | 0.397 (0.39-0.40) | 0.707 | 0.285 | 0.838 | 0.120 | 0.711 | 0.493 [0.309, 0.674] | 0.001 [-0.001, 0.005] |
| leiden_hard | 0.424 (0.42-0.43) | 0.357 (0.35-0.38) | 0.209 (0.18-0.21) | 0.470 (0.46-0.49) | 0.335 | 0.077 (0.08-0.08) | 0.162 (0.15-0.18) | 0.291 [0.189, 0.387] | -0.201 [-0.415, 0.002] |
| link_communities | 0.416 | 0.472 | 0.788 | 0.233 | 0.715 | 0.195 | 0.701 | 0.503 [0.336, 0.665] | 0.011 [-0.043, 0.061] |
| dependency_louvain | 0.375 (0.37-0.38) | 0.283 | 0.174 | 0.190 | 0.254 | 0.228 | 0.025 | 0.218 [0.143, 0.289] | -0.273 [-0.493, -0.062] |
| components | 0.105 | 0.404 | 0.588 | 0.056 | 0.466 | 0.160 | 0.838 | 0.374 [0.189, 0.574] | -0.118 [-0.247, 0.008] |
| name_tokens | 0.317 | 0.316 | 0.747 | 0.314 | 0.525 | 0.103 | 0.675 | 0.428 [0.276, 0.591] | -0.063 [-0.154, 0.003] |
| singletons | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 [0.000, 0.000] | -0.492 [-0.673, -0.308] |
| one_group | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 [0.000, 0.000] | -0.492 [-0.673, -0.308] |
| random_matched | -0.002 (-0.04-0.04) | 0.003 (-0.08-0.07) | 0.012 (-0.06-0.13) | -0.002 (-0.10-0.14) | -0.009 (-0.11-0.11) | -0.003 (-0.08-0.06) | 0.005 (-0.10-0.16) | 0.001 [-0.004, 0.005] | -0.491 [-0.674, -0.310] |

Reading:

- **The overlap step is worth about +0.08 F1** (LGREF against Louvain
  without overlap). Leiden in place of Louvain changes nothing.
- **Connected components (0.659) and even one group (0.494) score
  close to LGREF.** The provisional sheets share many statements, and
  BCubed recall rewards coarse groupings. This is why the reference
  F1 is secondary.
- **LGREF almost never keeps a shared statement shared** (recovery
  0.05). Link communities do (0.76 [0.45, 1.00]), at no cost in F1.

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
- Ablation by substitution is not built.

## Experiment 3: sensitivity of LGREF (development set)

One factor at a time from production, 30 seeds, BCubed F1 against the
provisional sheets. A subjective metric, so read with that in mind.

| variant | breakthrough5 | corridor | dropthree | montyhall | nim | othello4 | tictactoe | mean over games [95% CI] | paired vs production [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| production | 0.643 (0.64-0.65) | 0.638 | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.566, 0.758] | - |
| weight:legality:x0.5 | 0.643 (0.64-0.65) | 0.641 (0.63-0.64) | 0.774 | 0.568 (0.57-0.57) | 0.721 | 0.432 | 0.836 | 0.659 [0.561, 0.748] | -0.005 [-0.017, 0.001] |
| weight:legality:x2 | 0.643 (0.64-0.65) | 0.621 (0.61-0.63) | 0.774 | 0.596 (0.60-0.60) | 0.737 (0.73-0.74) | 0.432 | 0.836 | 0.663 [0.565, 0.752] | -0.002 [-0.013, 0.010] |
| weight:legality:off | 0.634 (0.63-0.64) | 0.637 (0.64-0.64) | 0.780 | 0.531 | 0.686 | 0.423 | 0.824 | 0.645 [0.546, 0.738] | -0.020 [-0.040, -0.003] |
| weight:predicate:x0.5 | 0.627 | 0.627 (0.61-0.63) | 0.774 | 0.543 | 0.672 | 0.422 (0.42-0.43) | 0.813 | 0.640 [0.545, 0.729] | -0.025 [-0.048, -0.009] |
| weight:predicate:x2 | 0.662 (0.66-0.66) | 0.643 (0.64-0.65) | 0.774 | 0.533 | 0.800 | 0.429 (0.43-0.43) | 0.801 | 0.663 [0.559, 0.755] | -0.001 [-0.019, 0.017] |
| weight:predicate:off | 0.573 | 0.620 (0.60-0.64) | 0.759 | 0.543 | 0.634 | 0.301 | 0.801 | 0.604 [0.483, 0.708] | -0.060 [-0.097, -0.027] |
| weight:same_head:x0.5 | 0.660 (0.66-0.66) | 0.616 (0.62-0.62) | 0.774 | 0.520 | 0.800 | 0.429 (0.43-0.43) | 0.791 | 0.656 [0.554, 0.750] | -0.009 [-0.030, 0.012] |
| weight:same_head:x2 | 0.643 (0.64-0.65) | 0.641 (0.61-0.65) | 0.774 | 0.544 | 0.752 | 0.426 (0.42-0.43) | 0.818 (0.81-0.84) | 0.657 [0.554, 0.749] | -0.008 [-0.015, -0.001] |
| weight:same_head:off | 0.601 | 0.631 (0.62-0.63) | 0.476 | 0.612 | 0.643 (0.61-0.65) | 0.370 (0.33-0.38) | 0.359 | 0.528 [0.438, 0.608] | -0.137 [-0.274, -0.025] |
| weight:shared_state:x0.5 | 0.643 (0.64-0.65) | 0.638 | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.566, 0.758] | 0.000 [0.000, 0.000] |
| weight:shared_state:x2 | 0.643 (0.64-0.65) | 0.631 (0.63-0.64) | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.565, 0.757] | -0.001 [-0.003, 0.000] |
| weight:shared_state:off | 0.643 (0.64-0.65) | 0.644 (0.64-0.64) | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.665 [0.567, 0.759] | 0.001 [0.000, 0.003] |
| weight:temporal:x0.5 | 0.643 (0.64-0.65) | 0.633 (0.63-0.63) | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.565, 0.757] | -0.001 [-0.002, 0.000] |
| weight:temporal:x2 | 0.643 (0.64-0.65) | 0.640 (0.63-0.64) | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.665 [0.567, 0.759] | 0.000 [0.000, 0.001] |
| weight:temporal:off | 0.643 (0.64-0.65) | 0.638 (0.64-0.64) | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.665 [0.567, 0.758] | 0.000 [0.000, 0.000] |
| weight:terminal:x0.5 | 0.644 (0.64-0.65) | 0.638 | 0.774 | 0.596 (0.60-0.60) | 0.761 | 0.422 | 0.836 (0.84-0.84) | 0.667 [0.565, 0.758] | 0.003 [-0.004, 0.012] |
| weight:terminal:x2 | 0.632 | 0.638 | 0.774 | 0.473 | 0.761 | 0.424 (0.42-0.43) | 0.834 (0.81-0.84) | 0.648 [0.539, 0.750] | -0.016 [-0.043, -0.001] |
| weight:terminal:off | 0.645 (0.64-0.65) | 0.638 | 0.774 | 0.683 (0.68-0.68) | 0.861 | 0.430 | 0.836 (0.84-0.84) | 0.695 [0.587, 0.788] | 0.031 [-0.000, 0.066] |
| hub_fraction:0.04 | 0.643 (0.64-0.65) | 0.638 | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.566, 0.758] | 0.000 [0.000, 0.000] |
| hub_fraction:0.16 | 0.604 | 0.638 | 0.787 | 0.561 (0.42-0.61) | 0.761 | 0.448 | 0.836 | 0.662 [0.563, 0.755] | -0.003 [-0.016, 0.008] |
| hub_fraction:1.01 | 0.604 | 0.619 (0.62-0.63) | 0.580 (0.48-0.61) | 0.547 | 0.694 | 0.448 | 0.528 (0.47-0.61) | 0.574 [0.520, 0.627] | -0.090 [-0.177, -0.019] |
| resolution:0.5 | 0.669 | 0.710 (0.71-0.71) | 0.775 (0.77-0.78) | 0.457 | 0.834 | 0.476 | 0.838 | 0.680 [0.566, 0.784] | 0.015 [-0.031, 0.054] |
| resolution:1.0 | 0.643 (0.64-0.65) | 0.691 (0.69-0.71) | 0.774 | 0.461 | 0.834 | 0.429 (0.43-0.43) | 0.838 | 0.667 [0.548, 0.778] | 0.003 [-0.038, 0.039] |
| resolution:1.5 | 0.643 (0.64-0.65) | 0.660 | 0.774 | 0.513 (0.47-0.53) | 0.834 | 0.432 | 0.836 (0.84-0.84) | 0.670 [0.559, 0.774] | 0.006 [-0.020, 0.034] |
| resolution:2.0 | 0.439 (0.43-0.44) | 0.660 | 0.576 | 0.530 | 0.800 | 0.331 (0.33-0.33) | 0.679 | 0.573 [0.460, 0.679] | -0.091 [-0.158, -0.021] |
| resolution:3.0 | 0.420 | 0.638 | 0.576 | 0.535 | 0.715 | 0.331 (0.33-0.33) | 0.626 (0.62-0.67) | 0.549 [0.453, 0.635] | -0.116 [-0.181, -0.052] |
| resolution:4.0 | 0.412 | 0.638 | 0.567 | 0.597 | 0.655 | 0.328 (0.33-0.33) | 0.550 | 0.535 [0.446, 0.612] | -0.129 [-0.210, -0.048] |
| tolerance:0.0 | 0.643 (0.64-0.65) | 0.638 | 0.774 | 0.568 (0.57-0.57) | 0.761 | 0.432 | 0.836 | 0.664 [0.566, 0.758] | 0.000 [0.000, 0.000] |
| tolerance:0.1 | 0.643 (0.64-0.65) | 0.600 (0.59-0.61) | 0.774 | 0.535 | 0.784 | 0.432 | 0.836 | 0.658 [0.555, 0.758] | -0.007 [-0.021, 0.007] |
| tolerance:0.2 | 0.643 (0.64-0.65) | 0.609 (0.60-0.63) | 0.774 | 0.535 | 0.784 | 0.432 | 0.836 | 0.659 [0.556, 0.758] | -0.005 [-0.018, 0.007] |
| overlap:0.1 | 0.686 (0.68-0.69) | 0.669 (0.67-0.67) | 0.778 | 0.396 (0.40-0.40) | 0.487 | 0.522 | 0.832 | 0.624 [0.515, 0.731] | -0.040 [-0.136, 0.041] |
| overlap:0.15 | 0.663 (0.65-0.67) | 0.675 (0.67-0.68) | 0.775 | 0.414 (0.41-0.41) | 0.560 | 0.440 | 0.836 | 0.623 [0.515, 0.731] | -0.041 [-0.108, 0.016] |
| overlap:0.35 | 0.634 (0.63-0.64) | 0.626 (0.62-0.63) | 0.772 | 0.581 (0.58-0.58) | 0.827 | 0.416 | 0.813 | 0.667 [0.559, 0.762] | 0.003 [-0.014, 0.025] |
| overlap:0.5 | 0.629 (0.62-0.63) | 0.604 (0.60-0.61) | 0.772 | 0.570 (0.57-0.57) | 0.709 | 0.416 | 0.813 | 0.645 [0.548, 0.735] | -0.020 [-0.033, -0.008] |
| overlap:1.01 | 0.629 (0.62-0.63) | 0.608 (0.61-0.62) | 0.772 | 0.602 (0.60-0.60) | 0.663 | 0.346 | 0.813 | 0.633 [0.521, 0.728] | -0.031 [-0.063, -0.001] |

- Removing the predicate edge, the same-head edge or the hub filter
  costs 0.06–0.14.
- The shared-state, temporal and legality weights barely matter on
  these games.
- Raising the raw resolution to 2 or more costs about 0.1. No setting
  beats production by more than its interval: the best are terminal
  edge off, +0.031 [−0.000, 0.066], and resolution 0.5, +0.015
  [−0.031, 0.054].
- Nothing was adopted (`freeze.md`).

## Reproducing

```bash
python -m lgref.bench.experiments interventions --split dev --workers 3 --out docs/paper-a/runs/exp1_dev.json
python -m lgref.bench.experiments groupings   --split dev --seeds 30 --out docs/paper-a/runs/exp2_dev.json
python -m lgref.bench.experiments sensitivity --split dev --seeds 30 --out docs/paper-a/runs/exp3_dev.json
python -m lgref.bench.experiments invariance  --split dev --seeds 5  --out docs/paper-a/runs/exp4_dev.json
python -m lgref.bench.report interventions docs/paper-a/runs/exp1_dev.json
python -m lgref.bench.report groupings     docs/paper-a/runs/exp2_dev.json
python -m lgref.bench.report sensitivity   docs/paper-a/runs/exp3_dev.json
python -m lgref.bench.review tictactoe nim corridor breakthrough5 othello4 dropthree montyhall   # packets
python -m lgref.bench.review --table tictactoe nim corridor breakthrough5 othello4 dropthree montyhall
python -m lgref.bench.setup
```

**Commits.** Each JSON record names the commit it ran at:

- `exp2`–`exp4` ran at `ab7b33b+uncommitted`, the stage 4 working tree.
- `exp1` ran at `ad83864+uncommitted`: the same working tree, after main
  had moved by other tracks' files only. It was re-run with three
  workers to add the exactness and collateral counts, and its
  reproduction and validity numbers are identical to the first run.
- Since `ab7b33b`, this PR adds outputs to the agreement function and
  makes three fixes to the runner (skip games without variants, the
  commit stamp, Experiment 4's "identical"). How a grouping is made,
  how an intervention is built, and every pre-existing score are
  unchanged.
- An earlier `commit()` bug ran `git status` against a path relative
  to the wrong directory, so it never saw uncommitted code. It is fixed
  here, with a test.
