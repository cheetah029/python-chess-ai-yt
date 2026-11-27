# Paper A protocol: recovering game mechanics from GDL descriptions

Recorded on 2026-11-26 for issue #347, **before any Paper A result
existed**. Later stages may add to it, but they may not change what it
says about the split, the scoring, or the freeze. Any departure is
recorded under "Departures" at the end, with its date and reason.

The paper asks five questions about automatic rule identification from
a GDL description:

1. **Rule units.** Do the groups a method finds match the rules a reader
   would name?
2. **Shared dependencies.** Are statements that serve several rules
   recognised as shared, rather than awarded to one rule?
3. **Overlapping membership.** Is overlap scored correctly, rather than
   hidden by a metric made for hard partitions?
4. **Representation invariance.** Does the grouping survive rewrites that
   keep the game the same?
5. **Intervention validity.** When a group is switched off, is the result
   a valid game, and does it change what the targeted rule governs and
   nothing else?

## Who wrote what

The person who wrote the method also wrote the references. This is a
circularity, and the user must review it.

| artefact | author | status |
|---|---|---|
| LGREF (`lgref/identify/`) | Claude, across earlier sessions | the method under test |
| pilot games (`lgref/bench/games/`) | Claude, #347 | checked against a second implementation (below) |
| reference groupings (`lgref/bench/references/*.csv`) | Claude | **provisional**. Not human annotations |
| reference variants and probes (`lgref/bench/variants/*.yaml`) | Claude | executable specifications, derived from each game's stated rules |
| annotation packet (`docs/paper-a/annotation/`) | Claude | blank; for human annotators |

- **Reference groupings.** The controls' sheets are converted mechanically
  from `lgref/identify/testgames/ground_truth.py`. An earlier Claude
  session wrote those labels, and scores against them are already
  published. The pilots' sheets were written by hand for #347 before any
  grouping method was run on the pilots. All of them are provisional.
  Inter-annotator agreement is reported **only** once real human sheets
  exist: the user's, and a second annotator's. The packet asks each
  annotator to work independently, to choose their own rule names
  (BCubed compares groupings, not names), and not to open the `.gdl`
  files, whose comments group the statements.
- **Variants and probes.** They are kept in files separate from the
  method, and nothing under `lgref/identify/` reads them. The risk is
  that their author knows how the method groups statements, and could
  choose changes it handles well without meaning to. The mitigation is
  that the changes for the pilots were chosen from the plan's own
  description of each pilot ("disable diagonal captures", outflanking,
  passing) before any method was run on the pilots. The user should still
  review them.

## The benchmark: two sets, development and test

There are exactly **two** sets, development and test. Every game is in
one of them, or is excluded with a reason. The sets are recorded in
`lgref/bench/catalog.py` and pinned by
`lgref/tests/test_paper_a_benchmark.py`. A game's set never changes once
it is written, and every results table names its set. The sets are cut
by **family**: two encodings of one game, or a game and its variants,
are always in the same set.

**Development (7 games).** The method may be developed, tuned and
debugged on these.

| game | why it is in development |
|---|---|
| tic-tac-toe | the plan's control: placement vs line detection vs ending |
| Nim | the plan's control: taking objects vs turn alternation vs ending |
| Corridor | the plan's failure-analysis game: blocking and tempo merge into movement |
| 5x5 Breakthrough | a pilot that establishes the protocol |
| 4x4 Othello | a pilot that establishes the protocol |
| drop-three | used before Paper A to make a choice: a #315 tuning game. A game a choice was made on cannot be a test game |
| Monty Hall | used before Paper A to make a choice: the #315 adoption decision was decided on it |

**Test (15 games).** No choice is ever made on these. They are scored
only after the freeze.

| game | why it is in test |
|---|---|
| skirmish, muddy children | run through identification before Paper A, and their scores were published (#315). Never used for any choice: only reported |
| Kuhn poker, Leduc hold'em, Russian cards, Cheryl's birthday | in the repository before Paper A. Never scored against a grouping, never used for any choice |
| kalah_mini, dotsboxes_2x2, hex_3x3, checkers_4x4, foxgeese_mini, chomp_3x3, synth_independent, synth_shared, synth_redundant | written **after** the freeze. Named now, so the list cannot be chosen after the results are seen |

**Excluded (3 games).** These are relatives of a development game, so
they can be in neither set:

- 3x4 Breakthrough, which is in the 5x5 pilot's family;
- Kriegspiel tic-tac-toe and Kriegspiel 5,5,4, which are in
  tic-tac-toe's family.

Generalisation claims rest on games, not statements: many statements
inside one game are not independent evidence. The test games seen
before Paper A were never used for a choice, which is what qualifies
them as test games. The reports still mark which test games are fresh,
because only those are unseen descriptions in the strict sense.

**Corridor** is a dev game. The plan allows tuning the method on it, and
for that reason the test set excludes every game in its family. It is
the failure-analysis game. Blocking and tempo merge into movement there,
and the reason is recorded rather than tuned away.

### The pilots

Both pilots are infix HRF. Each is checked against a plain-Python
implementation (`lgref/bench/simulators.py`) in every visited state: the
legal moves of each role, the successor of each joint move, the ending,
and the payoff. The check fails on mutated descriptions (tested). Both
implementations were written by Claude, so agreement between them rules
out encoding slips, but not a misreading of the rules that both share.

| pilot | statements | check | result |
|---|---|---|---|
| 5x5 Breakthrough | 75 | 3,000 random games, 39,044 distinct states | 0 problems |
| 4x4 Othello | 75 | **exhaustive**: all 62,789 reachable states | 0 problems |

- **5x5 Breakthrough.** The straight move, the diagonal move onto an empty
  square, and the diagonal capture are one action, `move(X,Y,X2,Y2)`, with
  one board update. Nothing in an action name or a head predicate tells
  them apart. Either kind of move can end the game on the far row. The
  ending's mobility test repeats all three. (A derived fact: a player
  with pawns off the far row always has a move, because the rearmost
  pawn's diagonal squares are empty or hold an enemy. So "no legal move"
  means "no pawns" in the unmodified game, and a variant can change
  that.)
- **4x4 Othello.** One relation, `closes`, decides both which placements
  are legal and which discs flip. Another, `canplace`, decides both when
  a player passes and when the game ends. The disc count needs a
  recursive tally, which shares the successor table with the board
  geometry. That sharing is exactly the kind that tempts a method into
  merging scoring with movement.

## Reference variants and probes

Each dev game has prespecified changes, written as exact text edits.
Each edit must apply exactly once, so an edit can never silently miss.
Each change also has **probes**: a state, optionally a joint move played
from it, and the legal moves, ending, payoff or facts expected
afterwards.

- A `changed` probe must hold in the variant and **fail** in the
  unmodified game. Otherwise it does not test the change.
- An `unchanged` probe must hold in both. It guards against collateral
  damage.
- A `no_effect` change has only `unchanged` probes. Its correct effect is
  none at all, so it is a negative control.

`check_references` enforces all of this, and the tests run it. Every
reference variant must itself be a well-formed game.

| game | change | kind | probes (changed / unchanged) |
|---|---|---|---|
| breakthrough5 | `no_capture`: diagonal captures disabled | targeted | 3 / 5 |
| breakthrough5 | `no_diagonal_move`: no diagonal move onto an empty square | targeted | 2 / 3 |
| breakthrough5 | `no_far_row_win`: reaching the far row does not end the game | targeted | 2 / 3 |
| othello4 | `no_flip`: nothing flips; placements must still outflank | targeted | 1 / 3 |
| othello4 | `place_anywhere`: outflanking no longer required to place | targeted | 4 / 2 |
| othello4 | `end_on_pass`: the game ends when the player to move cannot place | targeted | 1 / 3 |
| tictactoe | `no_diagonal_line` | targeted | 1 / 3 |
| tictactoe | `no_column_line` | targeted | 1 / 2 |
| nim | `take_one_only` | targeted | 1 / 2 |
| nim | `last_taker_wins` | targeted | 1 / 2 |
| corridor | `no_blocking` | targeted | 2 / 1 |
| corridor | `no_tempo` | targeted | 1 / 2 |
| corridor | `no_boundary`: the redundant guard lifted | **no_effect** | 0 / 2 |

**The first experiment** is Breakthrough `no_capture`, with the plan's
three probes:

- (a) `a_capture_illegal`: with an enemy pawn on the diagonal
  destination, the capture is illegal.
- (b) `b_diagonal_move_still_legal`: with that destination empty, the
  ordinary diagonal move is still legal.
- (c) `c_far_rank_still_wins`: a legal move onto the far row still wins.

It has five more probes. The most telling is
`e_capture_only_means_no_move`: a pawn whose only forward options were
captures now has no move, so its player loses. That probe fails any
intervention that removes the capture permission but leaves the capture
in the ending's mobility test. Such an intervention also produces stuck
states, and so counts as invalid.

## How a grouping becomes an intervention (stage 2 builds this)

The same procedure is used for **every** grouping method, LGREF and
baselines alike:

1. For each group of a method's grouping, build one intervention. The
   group's statements are split by `lgref.identify.cluster.assign_ownership`
   into those it owns (deleted), guards (tests relaxed at their call
   sites), and statements others need (kept). This split is structural:
   it reads no names and no labels. It is applied to the baselines'
   groups too, so no method gets a better intervention builder than
   another. A second, cruder procedure deletes the whole group; it is
   reported alongside the first.
2. **Attempted** = number of groups. **Valid** = the description loads,
   the start state is playable, and no visited state is non-terminal
   with a role that has no legal move, or terminal with two goal values.
   This is checked on the state set below plus 40 seeded random games of
   the intervention itself. On the state set, a defect counts only where
   the unmodified game does not have the same defect at the same state:
   the set holds probe states the unmodified game never reaches, and it
   can be ill-formed there. An intervention that deletes and relaxes
   nothing is **empty**. It counts as attempted but not as valid,
   because it does not intervene. Otherwise a method could raise its
   valid rate by proposing groups from which nothing can be removed.
3. **Changes behaviour** = it differs from the unmodified game on the
   state set.
4. **Reproduces** a targeted change = it is valid **and** passes every
   probe of that change. A method reproduces the change if **any** of
   its interventions does. A `no_effect` change (the redundant guard)
   is reproduced by a valid intervention that touches every statement
   the reference edit touches and changes nothing on the state set.
   Passing its probes alone does not count, because an intervention
   that leaves the guard alone passes them too. The roles must be the
   unmodified game's: deleting the role declarations is not a valid
   intervention. Since more groups mean more tries, the number of
   attempts is always reported beside the count of reproduced changes,
   and the matched-size random baseline carries the same advantage.

## Metrics

### Objective and subjective metrics

The user set this division on 2026-11-27, and it decides how every
result is read.

**Objective metrics.** A grouping is judged primarily on these:

- **behavioural intervention agreement**: precision, recall and F1 of an
  intervention's change against a reference variant's, over the state
  set;
- **valid intervention rate**;
- **grouping consistency across equivalent encodings** (Experiment 4);
- **performance on unseen games**: the same measures on the test set.

These measure behaviour, or a method's agreement with itself, so they do
not depend on anyone's opinion of what the rules are. (The reference
variants and probes are executable specifications, and their author is
recorded above.)

**Subjective metrics.** These are secondary and are reported as such,
never as the verdict:

- **extended BCubed F1 against a reference sheet.** A reference grouping
  written beforehand cannot be definitive when several groupings of a
  game are acceptable. The sheets are also provisional, and were written
  by the method's author;
- **the blind Claude review** (below). It stands in for human
  accessibility, readability and general agreement. It is not a
  factual, empirical or exact evaluation.


**Extended BCubed** (Amigó et al., 2009) is the grouping metric. It
handles overlap natively, which pair-counting ARI does not. For a
statement *e*, let *C(e)* be the method's groups that contain it and
*L(e)* the reference rules that contain it. For a pair *e, e'*:

- multiplicity precision = min(|C(e)∩C(e')|, |L(e)∩L(e')|) / |C(e)∩C(e')|
- multiplicity recall = min(|C(e)∩C(e')|, |L(e)∩L(e')|) / |L(e)∩L(e')|

Precision averages over *e* and over the *e'* that share a group with
*e*. Recall averages over the *e'* that share a reference rule with *e*.
F1 is their harmonic mean. Representation choices, fixed now:

- **Unassigned in the reference** (role declarations, for example): not
  scored, and their count is reported. A method may put them anywhere.
- **Left unclustered by the method**: each counts as its own singleton
  group. That costs recall and nothing else. Coverage (the share of
  scored statements in a group of size two or more) is reported beside
  F1.
- **Shared statements**: appear in several groups. BCubed rewards them
  only when the reference also shares them. A shared-recovery rate is
  also reported: of the statements the reference shares, the share the
  method puts in two or more groups.
- **Generic effects**: LGREF holds out board-update statements and
  reattaches them as shared members of every rule they serve. They are
  scored as ordinary multi-membership, with no special case.
- The pair-counting ARI of `lgref/identify/validate.py` is reported for
  continuity with #315. It is **not** a primary metric, because it is
  defined for hard partitions only.

**Behavioural agreement** is used in Experiments 1 and 5. Over a fixed
state set *S*, the behaviour of a description is a set of **atoms**:

- `legal(s, role, move)` for every move legal in the base, the variant or
  the candidate;
- `next(s, joint move)` as the successor state, for every joint move
  legal in all three;
- `terminal(s)`;
- `goal(s, role)` at the states that are terminal in all three.

An atom is *changed* by a description if its value there differs from
the unmodified game. A candidate's change is *correct* if the candidate's
value equals the reference variant's. Precision = correct / changed by
the candidate. Recall = correct / changed by the reference. F1 is their
harmonic mean. For a `no_effect` change recall is undefined, and it is
reported as "n/a", never as 0. Its unintended changes are counted
instead.

**Exactness and collateral damage** (added 2026-11-27, at the user's
instruction). These two counts are reported beside the F1, not instead
of it: the counts say whether an ablation is exact, and the F1 says how
close it comes.

- **Differing atoms.** For every rule with a reference ablation, count
  the atoms where an intervention and the reference variant disagree,
  in either direction. Legal-move atoms are reported apart from
  termination/goal atoms and successor atoms. A count of 0 means the
  ablation is **functionally exact** on *S*, assuming the reference is
  right.
- **Collateral atoms.** Count the atoms the intervention changes that
  the reference leaves as they were. These measure damage to behaviour
  that belongs to other rules.
- **Which intervention is scored.** For each method and change, the
  scored one is the closest: the valid intervention with the highest F1,
  with ties broken by fewer differing atoms. The question is whether the
  grouping contains an exact ablation at all, so the reference is
  allowed to pick it.
- **Modify, don't delete.** Where an ablation must modify another rule
  rather than delete it, the ownership split relaxes a guard at its call
  site (#313). How often that happens, and whether those interventions
  stay valid and exact, is reported per method.
- **A grouping metric too.** A better grouping should make clean
  ablations easier. So the number of changes with an exact ablation,
  and the collateral at the closest ablation, are also reported per
  grouping method, under both procedures.

**Setup statements.** Not every statement is an ablation candidate. The
reports count three kinds per game:

- (a) language: geometry, coordinate and counting arithmetic;
- (b) init: the initial position;
- (c) role/outcome: role declarations, terminal and goal statements.

(b) and (c) are read from the syntax. For (a), LGREF's language verdict
is scored against a provisional reference (`lgref/bench/references/
kinds.yaml`, written by Claude). It reports precision and recall for
"not an ablation candidate", and names every real rule statement that
gets marked language, because the user asked that this error never
happen. Two verdicts are scored:

- the definitive indicator, applied statement by statement: no state
  dependence at any depth;
- the #202 cluster verdict on LGREF's groups.

Everything else is attempted as an ablation. A failed ablation is
reported as a failed candidate and is never relabelled as setup.
Ablation by substitution (for example, removing a piece type from the
initial position) is not built: the user is still deciding.

**The state set *S*** is fixed per game before any candidate is scored,
and is the union of:

- the probe states;
- every reachable state, where exhaustive enumeration is under 10,000
  states (tic-tac-toe, Nim, Corridor);
- otherwise (Breakthrough, Othello, and larger test games), the states of
  200 seeded random games of the unmodified game, plus 50 seeded random
  games of each reference variant, so that the states only a variant
  reaches are included. These are the affected states and boundary
  cases. The bound is cost: one candidate is evaluated in every state of
  *S*, there are up to ~180 candidates per game, and Othello's 62,789
  reachable states take about two minutes per candidate.

Negative controls are the `no_effect` change and the `unchanged` probes.

**Valid intervention rate** = valid / attempted. It is reported
separately from the share of interventions that change behaviour and
the share that reproduce a targeted reference.

**Grouping consistency across equivalent encodings** is extended BCubed
F1 between a method's grouping of the original and its grouping of the
rewrite. Statements are compared through the rewrite's provenance map,
because a rewrite that splits or merges statements changes the count.

### The blind Claude review (subjective, secondary)

Every method's actual grouping of a game is shown to a reviewer. The
reviewer never sees the reference grouping. For every group it gives a
1–5 score for how sensible and readable the group is, with a reason of
at most 20 words. It then scores each grouping as a whole, from 1 to 5.
The review is built to compare methods, and it is still only an
opinion:

- **The same prompt** (`lgref.bench.review.PROMPT`) is used for every
  game and every method.
- **Blind.** One packet per game holds all the groupings, each under a
  neutral label (`G1`, `G2`, ...) in a seeded random order. The packet
  never names a method. Methods whose groupings are identical share one
  label and so get one review. The key from labels to methods is kept
  out of the reviewer's reach until the review is in.
- **The reviewer** is a fresh Claude agent, told to read only the packet
  and nothing else in the repository. It is not the agent that wrote the
  method, but it is the same model family. Of every limitation here,
  this is the one a human review would remove.
- Packets, raw replies and keys are kept in `docs/paper-a/review/`.

## Uncertainty and replication

- **The unit is the game.** Each method is paired with LGREF game by
  game, and the paired difference is reported per game.
- **Intervals.** Means over games carry 95% bootstrap intervals, made by
  resampling games: 10,000 resamples, seeded. With five dev games these
  intervals are wide, and the reports say so rather than narrowing them
  with statements.
- **Seeds.** Louvain, Leiden and the random baselines run on 30 seeds
  (0 to 29). The per-game spread over seeds is reported. Seeds are not
  pooled with games, because more seeds do not mean more games.
- **Dev and test are never pooled.** Every table states which of the
  two sets each row belongs to.

## The experiments

| exp | question | games | stage |
|---|---|---|---|
| 1 | reproduce the prespecified changes; probes for every grouping method | dev, then test | 4, 5 |
| 2 | LGREF against name-token grouping, plain dependency clustering, Louvain with and without the overlap step, Leiden (same graph, objective and overlap step), link communities (same edges), one group per statement, matched-size random groups | dev, then test | 2 builds them, 4 runs them |
| 3 | sensitivity: edge weights, hub filtering, resolution, overlap threshold, each edge type removed; spread over seeds | dev only | 4 |
| 4 | representation invariance: scrambled names, reordered statements, helper extraction and inlining, split or combined definitions, restructured predicates; behaviour preserved, checked exhaustively on small games and by testing on larger ones | dev, then test | 5 |
| 5 | functional interventions against the reference variants over *S*: validity, targeted agreement, failures caused by shared infrastructure | dev, then test | 5 |

Experiments 1–3 on the dev games set the protocol. Then the method is
**frozen**.

## The freeze

Before any test game is written or scored, `docs/paper-a/freeze.md`
records:

- the commit SHA of the frozen method;
- the configuration it runs with: weights, resolution rule, overlap
  threshold, and intervention procedure;
- the date.

After the freeze, nothing in `lgref/identify/` that affects grouping or
intervention changes for Paper A. If a bug is found after the freeze, it
is fixed as a new version. Test games are re-run under both versions,
and both results are reported. A test-game result is never used to
choose anything.

## Results that contradict the plan

A surprising result is first treated as a possible bug: check it
against the bound the rules put on it. If it survives that check, it is
recorded in the results with its explanation. It is not tuned away.

## Reproducing stage 1

```bash
python -m lgref.bench.wellformed othello4 --exhaustive --limit 200000
python -m lgref.bench.wellformed breakthrough5 --games 3000
python -m lgref.bench.annotation          # rewrites the annotation packet
python -m pytest -q lgref/tests/test_paper_a_benchmark.py
```

## Departures

- **2026-11-27 (#358), at the user's instruction.**
  - *Two sets only.* The stage 1 split had four categories: dev,
    dev_family, test_seen and test_fresh. There are now two sets,
    development and test, plus an excluded list. Drop-three and Monty
    Hall move to development, because a choice was made on each before
    Paper A. The other previously seen games move to test. The fresh
    test games are unchanged.
  - *Objective vs subjective metrics, and the blind Claude review.* Both
    sections were added under "Metrics".
  - *Exactness, collateral damage and setup statements.* The two
    counts beside the F1 were added under "Metrics", together with the
    three-kind setup report and LGREF's language verdict scored against
    a provisional reference. These are additions. No existing
    definition changed.
  - No test-game result existed when these changes were made. Drop-three
    and Monty Hall have no reference variants, so they enter the
    grouping experiments (2, 3, 4) and the review, not the intervention
    experiments (1, 5).
