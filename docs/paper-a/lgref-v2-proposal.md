# LGREF V2: a proposal for rule grouping (#411)

**This is a proposal only.** Nothing in it is implemented, run or
tuned. It says what V2 of LGREF's rule identification
(`docs/lgref-versions.md`) would be, which evidence each part rests on,
and how V2 would be evaluated.

V2 would be a new **major version**: it changes what decides which
statements go together, from one modularity partition (V1) to a
hierarchy of candidate groups from single statements up.

## The rule this proposal follows

The user's rule (2026-11-27): **a game is spent only when LGREF is tuned
on it**, that is, when a design or parameter choice is made because of
its results. Measuring on a game does not spend it.

So every component below is grounded in **development-set** results
only: tic-tac-toe, Nim, Corridor, 5x5 Breakthrough, 4x4 Othello (the five
with reference variants, 12 targeted rules), drop-three and Monty Hall.
No test-set result is used as a reason for anything. A component with no
development-set reason is dropped, or labelled as such. The test set
therefore stays unspent, and can evaluate V2 (see "How V2 would be
evaluated"). "Evidence deliberately not used" lists what was left out.

## Development-set evidence

All numbers are from `docs/paper-a/runs/exp1_dev.json`,
`draws_exp1_dev.json.gz` and `exp4_dev.json`.
`lgref/tests/test_paper_a_v2_proposal.py` recomputes every one of them.

**Definitions.** A rule's **closest ablation** is the method's valid,
non-empty intervention that changes something and has the fewest **rule
changes** (exactness: |atoms(A) Δ atoms(R)| over legal moves, endings,
payoffs and successors on the state set S, against the reference
ablation R). **Exact** means 0 rule changes. `ownership` deletes what a
group owns, relaxes its guards and keeps what other rules need;
`delete-group` deletes every statement of the group. V0 is the mean over
30 random draws, with a 95% bootstrap interval over draws.

**E1. Fine groups give exact ablations.** Exact rules of 12, under
`delete-group`:

| method | exact of 12 |
|---|---|
| singletons | 7 |
| name_tokens | 7 |
| link_communities | 7 |
| V1 (`lgref`) | 1 |
| V0 (30 draws) | 0.27 [0.13, 0.43] |

The three fine methods are exact on **the same 7 rules**: Breakthrough
`no_capture`, `no_diagonal_move` and `no_far_row_win`; tic-tac-toe
`no_column_line` and `no_diagonal_line`; Nim `take_one_only`; Othello
`no_flip`. V1's one exact rule (`no_diagonal_line`) is among them, so on
the development set **V1's communities find no exact rule that single
statements miss.**

**E2. The development rules are small.** Every targeted development
reference ablation touches 1 to 3 statements. So E1 shows that fine
groups suit small rules. It says nothing about rules that span many
statements, because the development set has none.

**E3. The ownership split helps groups, and hurts single statements.**

- For singletons, `ownership` gives 1 exact rule against 7 for
  `delete-group`.
- For name tokens, `ownership` gives Corridor `no_blocking` exactly,
  which no method reaches under `delete-group`. It is the only exact
  rule outside E1's seven.
- For V1, `ownership` gives a valid ablation for 10 of 12 rules, against
  7 of 12 under `delete-group`. But none of V1's 7 repaired ablations
  (a relaxed guard or a protected statement) is exact.

**E4. Overlap adds nothing measurable on the development set.** Link
communities (native overlap) are exact on exactly the same 7 rules as
singletons. On every development rule, under both procedures, their
closest ablation has at least as many rule changes as the singletons',
and they have no valid ablation where singletons lack one. So what link
communities did well is their **granularity**, which V2 keeps through
C1; their **overlap** contributed no exact rule and no lower count, and
is the only part dropped.

**E5. Stability.** Consistency is the extended BCubed F1 between a
method's grouping of a description and of each behaviour-preserving
rewrite, averaged over the six rewrites and 5 seeds, then over the 7
development games:

| method | consistency |
|---|---|
| singletons | 0.976 |
| name_tokens | 0.963 |
| V1 (`lgref`) | 0.956 |
| link_communities | 0.955 |
| leiden | 0.954 |
| louvain_hard | 0.941 |
| V0 | 0.622 |

- Leiden is no more stable than Louvain here (0.954 against V1's
  0.956), and has fewer exact rules (0 under `ownership`, 1 under
  `delete-group`, against V1's 1 and 1).
- Under the `reorder` rewrite, V1 loses its one exact `ownership`
  ablation (`results-dev.md`, Metric 10): Louvain's tie-breaks follow
  statement order.

**E6. Fine methods try more ablations.** On the 5 development games,
singletons attempt 251 interventions per procedure, name tokens 79,
link communities 83, V1 40. V0, matched to V1's 40, finds 0.27 exact
rules on average. More candidates means more chances for a closest
ablation, so part of E1 may be the number of tries and not the quality
of the groups.

**E7. Four rules no grouping reaches.** Nim `last_taker_wins`, Corridor
`no_tempo`, and Othello `place_anywhere` and `end_on_pass` are exact for
no method under either procedure. Their references change a statement
rather than remove one.

**E8. Accounting: every method's good development results.** For each
method, the development rules it gets exact under each procedure, its
consistency (E5's measure), and whether V2's components reach every one
of its exact rules. Then each exact rule, with every method and
procedure that got it, and the component of V2 that reaches it. Both
tables are generated by `python -m lgref.bench.v2_evidence` from the
development runs; the test checks they are reproduced here unchanged.

<!-- accounting:begin -->
| method | exact, ownership | exact, delete-group | consistency | its exact rules reached by V2 |
|---|---|---|---|---|
| V1 (`lgref`) | 1 | 1 | 0.956 | all 2 |
| louvain_hard | 1 | 2 | 0.941 | all 2 |
| leiden | 0 | 1 | 0.954 | all 1 |
| leiden_hard | 0 | 1 | 0.937 | all 1 |
| link_communities | 1 | 7 | 0.955 | all 7 |
| dependency_louvain | 0 | 0 | 0.948 | none to reach |
| components | 0 | 0 | 0.990 | none to reach |
| name_tokens | 1 | 7 | 0.963 | all 8 |
| singletons | 1 | 7 | 0.976 | all 7 |
| one_group | 0 | 0 | 1.000 | none to reach |
| V0 (30 draws) | 0.33 | 0.27 | 0.622 | none to reach (a mean over draws) |

| rule | exact for (method: procedure) | reached in V2 by |
|---|---|---|
| breakthrough5 `no_capture` | link_communities: del; name_tokens: del; singletons: del | C1 + C4 (single statement, deleted) |
| breakthrough5 `no_diagonal_move` | link_communities: del; name_tokens: del; singletons: del | C1 + C4 (single statement, deleted) |
| breakthrough5 `no_far_row_win` | link_communities: del; name_tokens: del; singletons: del | C1 + C4 (single statement, deleted) |
| corridor `no_blocking` | name_tokens: own | C3 + C4 (name-token group, ownership split) |
| nim `take_one_only` | V1 (`lgref`): own; louvain_hard: own; louvain_hard: del; link_communities: own; link_communities: del; name_tokens: del; singletons: own; singletons: del | C1 + C4 (single statement, deleted) |
| othello4 `no_flip` | link_communities: del; name_tokens: del; singletons: del | C1 + C4 (single statement, deleted) |
| tictactoe `no_column_line` | link_communities: del; name_tokens: del; singletons: del | C1 + C4 (single statement, deleted) |
| tictactoe `no_diagonal_line` | V1 (`lgref`): del; louvain_hard: del; leiden: del; leiden_hard: del; link_communities: del; name_tokens: del; singletons: del | C1 + C4 (single statement, deleted) |
<!-- accounting:end -->

- Every one of the 8 rules any method gets exact is reached by a kept
  component: 7 by C1 (a single statement, deleted, per C4) and Corridor
  `no_blocking` by C3 with the ownership split (C4).
- **louvain_hard's second exact rule** under `delete-group` (2 of 12,
  against V1's 1) is Nim `take_one_only`. Single statements are exact on
  it too, so C1 reaches it; no new component is needed.
- **Leiden and Leiden-hard against V1:** exact 0 under `ownership` and 1
  under `delete-group` each (V1: 1 and 1; the one is tic-tac-toe
  `no_diagonal_line`, also reached by C1); consistency 0.954 and 0.937
  (V1: 0.956).

## Subjective development evidence

The user (2026-11-27) separates two kinds of subjective evidence:

- **(a) agreement with a hand-written reference grouping** (BCubed F1).
  Weak: many groupings of a game are valid, and the reference is one of
  them.
- **(b) an after-the-fact rating**: a reviewer looks at actual groupings
  of the same game and judges which is better and why. Still subjective,
  but more direct, since there is no reference to choose. Preferred to
  (a).

Components resting only on (a) or (b) are kept in the design, **labelled
"supported by subjective evidence only"**. The paper need not report
them as results; they shape the design. Development games only. The
reviewers are Claude agents, the same model family as the method's
author.

**S1. The earlier blind review, read against LGREF** (kind b;
`results-dev.md`, "Blind Claude review"). One reviewer per game scored
every grouping 1-5 on its own. Per method, on how many of the 7
development games its overall score was higher than, equal to or lower
than LGREF's (`pairwise_review.absolute_table`):

<!-- absolute:begin -->
| method | higher than LGREF | equal | lower | same grouping as LGREF (one score) |
|---|---|---|---|---|
| louvain_hard | 1 | 3 | 3 | 0 |
| leiden | 0 | 1 | 1 | 5 |
| leiden_hard | 0 | 2 | 5 | 0 |
| link_communities | 0 | 4 | 3 | 0 |
| dependency_louvain | 0 | 0 | 7 | 0 |
| components | 0 | 3 | 4 | 0 |
| name_tokens | 2 | 4 | 1 | 0 |
| singletons | 0 | 0 | 7 | 0 |
| one_group | 0 | 0 | 7 | 0 |
| random_matched | 0 | 0 | 7 | 0 |
<!-- absolute:end -->

**S2. A side-by-side pairwise rating** (kind b, new for this proposal;
`lgref.bench.pairwise_review`). For each development game, LGREF's
grouping against each other method's, shown as A and B with the names
hidden and the order drawn per pair from a seeded generator. Groups the
two share are listed once; the reviewer rates what differs: A better, B
better or tie, with a one-line reason for each differing group. One
fresh reviewer agent per game, which saw only its packet
(`docs/paper-a/review-pairwise/<game>/packet.md`; answers in
`review.json`, the blinding key in `key.json`). Identical groupings are
not shown and are counted apart (`=`): 7 reviewers rated 69
comparisons, and 8 pairs were identical. V0 is its draw 0, the grouping
the runs scored. O = the other method better, L = LGREF better, T = tie:

<!-- pairwise:begin -->
| method | tictactoe | nim | corridor | breakthrough5 | othello4 | dropthree | montyhall | other better | tie | LGREF better | identical |
|---|---|---|---|---|---|---|---|---|---|---|---|
| louvain_hard | L | L | L | O | O | L | O | 3 | 0 | 4 | 0 |
| leiden | = | = | L | = | = | = | T | 0 | 1 | 1 | 5 |
| leiden_hard | L | L | L | O | O | L | O | 3 | 0 | 4 | 0 |
| link_communities | O | O | L | L | L | L | L | 2 | 0 | 5 | 0 |
| dependency_louvain | L | L | L | L | L | L | L | 0 | 0 | 7 | 0 |
| components | L | O | L | L | L | L | L | 1 | 0 | 6 | 0 |
| name_tokens | O | L | L | L | L | L | O | 2 | 0 | 5 | 0 |
| singletons | L | L | L | L | L | L | L | 0 | 0 | 7 | 0 |
| one_group | L | L | L | L | L | L | L | 0 | 0 | 7 | 0 |
| random_matched | L | L | L | L | L | L | L | 0 | 0 | 7 | 0 |
| lgref_postfreeze_noterminal | = | O | = | O | O | = | O | 4 | 0 | 0 | 3 |
<!-- pairwise:end -->

What the reviewers' reasons say, per method:

- **The terminal-edge-off variant (#394)** is rated better on all 4
  games where it differs, and worse on none. Reasons: it separates turn
  alternation from the ending and winning rule (Nim), keeps the capture
  definition out of the ending rule (Breakthrough), splits Othello's
  oversized core group, and gives Monty Hall clean, non-overlapping
  rules. On the objective development metrics it equals V1: the same
  exact rules (Nim `take_one_only` under `ownership`, tic-tac-toe
  `no_diagonal_line` under `delete-group`), valid ablations for the same
  10 and 7 rules, consistency 0.965.
- **louvain_hard and leiden_hard** each win 3 of 7 and lose 4. Their wins
  give two recurring reasons: a separate setup (initial position) group,
  and smaller groups without LGREF's heavy overlaps (Monty Hall,
  Othello). Their losses: statements left ungrouped, and fragments with
  effects cut off.
- **Link communities** win 2 of 7 (tic-tac-toe, Nim) and lose 5, for
  "many tiny overlapping groups that repeat statements". S1 agrees: never
  higher than LGREF.
- **Name tokens** win 2 of 7 pairwise and lose 5 ("scatters ending and
  winner into singletons"), but in S1 they score higher than LGREF on 2
  games, equal on 4 and lower on 1: mixed.
- **Singletons** lose all 7, in both S1 and S2: shown as the grouping
  of the game, single statements read as fragments.
- **Leiden** gives LGREF's grouping on 5 games; of the other 2, one tie
  and one loss. **Components, dependency Louvain, one_group and V0** lose
  every pairwise rating except components on Nim.

**S3. The same pairs, one fresh reviewer per pair.** In S2 one reviewer
rated every pair of a game, so it saw LGREF's grouping in every pair,
which can anchor it. Here every comparison was rated by its own fresh
reviewer, which saw only that packet, so each saw LGREF's grouping once.
The packets are S2's comparisons, with the same A/B side, one per file
(`docs/paper-a/review-pairwise-single/<game>/pair-<hash>/`; the folder
name is a hash so the path names no method). 76 reviewers: S2's 69 pairs
and S4's 7. Both protocols side by side (other better / tie / LGREF
better), with every verdict that changed:

<!-- protocols:begin -->
| method | per game: other / tie / LGREF | per pair: other / tie / LGREF | identical | verdicts that differ |
|---|---|---|---|---|
| louvain_hard | 3 / 0 / 4 | 4 / 0 / 3 | 0 | corridor (L -> O) |
| leiden | 0 / 1 / 1 | 0 / 1 / 1 | 5 | none |
| leiden_hard | 3 / 0 / 4 | 3 / 0 / 4 | 0 | none |
| link_communities | 2 / 0 / 5 | 4 / 0 / 3 | 0 | othello4 (L -> O), montyhall (L -> O) |
| dependency_louvain | 0 / 0 / 7 | 1 / 0 / 6 | 0 | breakthrough5 (L -> O) |
| components | 1 / 0 / 6 | 0 / 1 / 6 | 0 | nim (O -> L), dropthree (L -> T) |
| name_tokens | 2 / 0 / 5 | 5 / 0 / 2 | 0 | nim (L -> O), othello4 (L -> O), dropthree (L -> O) |
| singletons | 0 / 0 / 7 | 0 / 0 / 7 | 0 | none |
| one_group | 0 / 0 / 7 | 0 / 0 / 7 | 0 | none |
| random_matched | 0 / 0 / 7 | 0 / 0 / 7 | 0 | none |
| lgref_postfreeze_noterminal | 4 / 0 / 0 | 4 / 0 / 0 | 3 | none |
| lgref_plus_overlap | not rated | 0 / 0 / 7 | 0 | n/a |
<!-- protocols:end -->

- **The anchoring was real, and it favoured LGREF.** Of the 69 pairs, 9
  verdicts changed between protocols, 8 of them away from LGREF. Name
  tokens go from 2 / 5 to 5 / 2, link communities from 2 / 5 to 4 / 3,
  louvain_hard from 3 / 4 to 4 / 3, dependency Louvain from 0 / 7 to
  1 / 6. The terminal-edge-off variant (4 / 0), singletons, one_group
  and V0 (0 / 7) are unchanged.
- **The fresh reviewers' recurring reason is that V1's groups are too
  large**: "lumps all end-of-game logic into one large group", "one
  24-statement blob, hiding nearly every rule", "large, overlapping
  blends of many rules". Where name tokens, link communities or
  louvain_hard win, it is for separating legality, ending and winning
  into groups a player would name.

**S4. Overlap on its own** (rating only; `methods.lgref_plus_overlap`).
Link communities overlap AND split into many small groups, so their
ratings cannot say which of the two reviewers disliked. This variant is
V1's grouping unchanged, where each statement may also join one more
group: the group not already holding it that receives the largest share
of its weighted degree in V1's own graph, if that share is at least
0.15. The rule and the 0.15 (the value below V1's 0.25 in Experiment 3's
pre-existing overlap grid) were fixed before any rating or score of the
variant was seen, and were not tuned. It adds 9 to 26 memberships per
development game.

- **Rated per pair: LGREF better on all 7 games.** Reasons: "two groups
  nearly duplicate each other", "lists the identical group twice", "huge
  overlapping blobs covering half the game each".
- **Objective development metrics: identical to V1 on every rule**,
  under both procedures (the added statements are shared members, which
  an ablation keeps): the same exact rules, the same rules with a valid
  ablation (10 and 7), the same rule-change count on all 12 rules.
  Consistency is lower, 0.942 against V1's 0.956.
- So overlap as such adds nothing objectively and is rated worse. Link
  communities' per-pair wins come from their finer groups, not from
  their overlap.

## The proposed design

V2 keeps V1's information source (the typed, weighted statement graph,
`docs/lgref-versions.md`, V1.0) and changes what is built from it.

**C1. Single statements are the leaves (E1, E2).** Every statement is a
candidate group of its own. On the development set, this is the level
that gives exact ablations. The leaves are **ablation candidates, not the
grouping shown as the game's rules**: shown that way, singletons lose
every rating in S1 and S2. The grouping V2 presents is the rule level of
C2.

**C2. A hierarchy above the leaves, built from V1's graph (E2, E3).**
Statements are merged agglomeratively by V1's edge weights, and every
merge is a candidate group, up to V1's communities at the coverage-rule
resolution. The development set gives no reason for the upper levels
(E2: no rule there spans more than 3 statements). They are kept only so
that V2 can still propose multi-statement rules, which is the method's
claim, and they are **untested** until a game has such rules.

**C3. Name-token groups as an extra level (E3).** Statements whose head
predicates share a name token form candidate groups beside the
hierarchy. On the development set, this is the only way any method
reached Corridor `no_blocking`.

**C4. The ownership split for groups, deletion for single statements
(E3).** A candidate of one statement is ablated by deletion. A candidate
of two or more statements is ablated both ways, and both are reported.
The split is kept for groups because it reached `no_blocking` and raised
V1's coverage from 7 to 10 rules. It is dropped for single statements
because it cost 6 exact rules there.

**C5. Order- and seed-consensus wherever a step has tie-breaks (E5).**
Any step that depends on visiting order (for example, the community
level of C2) is run over several seeds and statement orders, and two
statements stay together only if most runs put them together. This
targets the `reorder` loss in E5. No consensus threshold is proposed;
choosing one would be tuning, and must be done on the development set.

**C6. A ranking, so that V2 can be compared at a fixed budget (E6).**
V2 ranks its candidates without looking at any reference. The proposed
ranking is by the share of a candidate's changed atoms that fall in one
action type (the focus measure in `report.scatter_table`), since it
needs no reference. V2 is then also scored on its top k candidates per
game, with k equal to V1's group count, so that it cannot win by trying
more.

**C7. No terminal edge in the graph that builds C2's upper levels
(S2). Supported by subjective evidence only.** The terminal-edge-off
variant is rated better than V1 on every development game where it
differs, and equals V1 on every objective development metric. It was
dropped in the first draft because its only support was kind (a); kind
(b) supports it.

**C8. A separate setup group (S1, S2). Supported by subjective evidence
only.** The initial-position statements form their own group at the
rule level, not merged with the board update. It is a reason given for
louvain_hard's and leiden_hard's pairwise wins on Breakthrough, and the
earlier review's recurring criticism of LGREF ("setup merged
with the board update"). It agrees with the reference-sheet convention
that, when no rule belongs to one piece type, `init` statements stay in
a setup group (`protocol.md`).

**C9. A finer rule level than V1's communities (S3). Supported by
subjective evidence only.** The grouping V2 presents as the game's rules
splits groups that mix legality, ending and winning. The candidate rule,
to be fixed on the development set before any test run: split each V1
community along the name-token groups of C3, so that, for example, the
ending statements and the payoff statements of a community become two
groups. Under the per-pair protocol, name tokens are rated above V1 on
5 of 7 games, link communities on 4 and louvain_hard on 4, each for
finer, nameable groups. It changes what is shown, not the ablation
candidates, which C1 to C4 already give.

**C10. No overlap beyond V1's (S4). Supported by subjective evidence,
with objective neutrality.** V2 adds no shared memberships of its own,
and the rule level shows each statement in its core group, with shared
members listed apart. Extra overlap was rated worse on all 7 games and
changed no objective number except consistency, which fell.

**What each other method contributes, and what is dropped** (E8):

- **Singletons:** all 7 exact rules kept, via C1. Their consistency
  (0.976, the highest of the non-trivial methods) is kept with them,
  since C1 is the same deterministic split.
- **Link communities:** all 7 exact rules kept, via C1, which is their
  granularity. Their subjective wins (4 of 7 under the per-pair
  protocol) are for finer, nameable groups, which C9 keeps. **Dropped:
  their overlap.** It gave no exact rule and no lower rule-change count
  than singletons on any development rule (E4). Isolated in S4, overlap
  added to V1's own groups is rated worse on all 7 games and changes no
  objective number but consistency, which falls.
- **louvain_hard:** both exact rules kept, via C1 (Nim `take_one_only`,
  tic-tac-toe `no_diagonal_line`). Its subjective wins (3 of 7 in S2, 4
  of 7 per pair) are for a separate setup group (C8), capture kept out of
  the ending (C7), smaller groups (C9) and fewer overlaps (C10).
  Dropping V1's overlap step altogether is not adopted: louvain_hard
  loses 3 of 7 per pair, for statements left ungrouped.
- **Name tokens:** all 8 exact rules kept (C1, C3 + C4), and the per-pair
  ratings (5 of 7 above V1) carry their finer, nameable groups into C9.
- **Leiden and Leiden-hard: dropped.** Their one exact rule each is
  reached by C1, and they do not beat V1 on any objective development
  number (exact 0 / 1 against V1's 1 / 1; consistency 0.954 and 0.937
  against 0.956). Subjectively, Leiden gives LGREF's grouping on 5 of 7
  games and wins none of the other 2. Leiden-hard wins on the same 3
  games as louvain_hard, for the same reasons.
- **Dependency Louvain, components, one_group:** no exact rule on the
  development set, so nothing to keep. Components' and one_group's high
  consistency (0.990, 1.000) comes from having two to four groups or
  one, and is not a property V2 can take without their coarseness. The
  ratings do not support that coarseness either: components win 1 of 7
  in S2, one_group and dependency Louvain none.
- **V1 itself:** both exact rules reached by C1. Its communities remain
  the top of C2's hierarchy, for the method's claim (untested, E2).
- **The post-freeze terminal-edge-off setting (#394): moved back in**,
  as C7, supported by subjective evidence only (S2).
- **Statement rewriting for E7's rules** (relaxing or replacing part of
  a statement): not reached by any grouping, so an intervention
  problem, not a grouping one. Out of scope for V2.

## Caveats on the subjective evidence

- **The reviewers are the same model family as the method's author.**
  Every rating in S1 to S4 was made by Claude agents, and the method,
  the reference sheets and this proposal were written by Claude. The
  ratings may share the author's view of what a rule is. Human ratings
  (the annotation packets in `lgref/bench/annotation.py` and
  `docs/paper-a/review/`) or reviewers from a different model would
  remove this bias. Neither has been done.
- **Anchoring.** S1 and S2 each showed one reviewer all of a game's
  groupings; S3 shows that this changed 9 of 69 verdicts, 8 of them
  away from LGREF once each reviewer saw LGREF's grouping only once. S3
  and S4 are the protocol to prefer.
- **Small samples.** 7 development games; one reviewer per comparison.

## Evidence deliberately not used

These were observed on the **test set**. None is a reason for any part
of V2. Using one would spend the test games it came from.

- Checkers' `canjump` case and its play-out results.
- The synthetic cases (`synth_independent`, `synth_shared`,
  `synth_redundant`).
- "Random beats LGREF on test", and every test-set exact count,
  including the 30-draw test results.
- The test-set results of the post-freeze variant (#394).
- The fixed-table verdicts on the test games (#400).
- Every test-set play-out, per-kind count and consistency value.

**Which evidence was development-only.** All of it:

| component | evidence | from |
|---|---|---|
| C1 single-statement leaves | E1, E2 | development only |
| C2 hierarchy from V1's graph | E2 (and the method's claim; untested) | development only |
| C3 name-token level | E3 | development only |
| C4 split for groups, deletion for statements | E3 | development only |
| C5 order and seed consensus | E5 | development only |
| C6 ranking and the budget | E6 | development only |
| C7 no terminal edge (subjective only) | S2, with E8's objective equality | development only |
| C8 separate setup group (subjective only) | S1, S2 | development only |
| C9 finer rule level (subjective only) | S3 | development only |
| C10 no extra overlap (subjective, objectively neutral) | S4 | development only |
| dropped: Leiden, overlap, rewriting | E4, E5, E7, E8, S1-S4 | development only |

## How V2 would be evaluated

1. **Design and tune on the development set only.** Any remaining
   choice (C5's threshold, C6's ranking, where C2 stops) is made on the
   development games, and recorded with its development result.
2. **Declare the proof before the code** (`docs/strictly-better-method.md`).
   The claim to test: V2 beats V1 on rule changes. Over the test set's
   rules, V2 has more wins than losses against V1 in the rule-changes
   table, and no per-kind table (legal moves, endings, payoffs) has more
   losses than wins.
3. **Freeze V2** at one commit, as V1 was frozen at `ab7b33b`
   (`freeze.md`), before it sees any test game.
4. **Run it once on the current test set** (10 games with references, 15
   in all), which this proposal has not spent. Report every table of
   `grouping-version-tables.md` with V2 as a column: against V0 (30
   draws, re-drawn to match V2's group sizes) and against V1. The
   baseline-V1 tables then gain their first column.
5. **Report the budget-matched result beside the full one** (C6): V2's
   top k candidates, k equal to V1's group count, against V1.
6. **A fix after the test run is V2.1**, run on both sets and reported
   beside V2.0, never in place of it.
7. **If the test set is ever used to tune V2**, it is spent, and a fresh
   set is needed. That set should hold at least as many targeted rules
   as the current one, and include rules whose reference ablation spans
   four or more statements, since the development set has none (E2).
