# LGREF rule identification: the validation protocol (#315)

Rule identification is validated against games small enough for a human
to state the rule boundaries with certainty. This document is the
protocol and its first full result. It replaces the Phase 1 gate's
three-game table (`docs/lgref-phase1.md`) as the authoritative account of
how well identification works.

## Why the protocol changed

A reviewer raised two problems:

1. **The resolution was tuned on coverage, not quality.** The production
   rule picks the finest Louvain resolution whose coverage stays within
   three points of the coarse end. Coverage is not rule quality: a method
   can keep every statement in some cluster while splitting coherent
   rules into fragments. The gate tests also scored every game at the
   raw default of 1.0, while Royal Chess was analysed at the calibrated
   resolution, so the procedure they validated was not the one that ran.
2. **Validation was too small.** Three games had labels, one of them the
   development game, and Corridor was the only held-out game.

## The protocol (`lgref/identify/protocol.py`)

The games, labels, splits and the rules below were **pre-registered on
issue #315** (with SHA-256 hashes of each file) before any of the new
games was scored. The files are committed unchanged, except that
`ground_truth.py` gained `STRUCTURE` records for the new games after
scoring (an existing test requires one per game). The labels and
splits are byte-identical, and the change is disclosed on the issue.

| split | games | used for |
|---|---|---|
| dev | tic-tac-toe, drop-three | **tuning**: the only split a setting is chosen on |
| validation | nim, Monty Hall | **one decision**, by a rule fixed in code |
| test | corridor, breakthrough-mini, skirmish, muddy children | **reporting only** |

- **Candidates are size-aware.** Louvain's resolution is measured
  against total graph weight, so a raw value tuned on 35-statement games
  does not transfer to the 522-statement Royal Chess description. The
  candidates are the coverage rule at tolerance *t* (*t* = 0.03 is the
  production default and the baseline) and *k* × the calibrated
  resolution. Raw resolutions are only reported, as sensitivity curves.
- **Tuning:** the highest mean dev ARI wins; a tie keeps the default.
- **Decision:** the dev winner replaces the default only if its mean
  validation ARI is *strictly* higher.

## The games

| game | statements | structure it adds | well-formedness |
|---|---|---|---|
| tic-tac-toe | 35 | separable rules | (existing) |
| drop-three | 45 | a GRAVITY rule both the permission and the update consult | exhaustive: 7,157 states, none stuck |
| nim | 22 | no spatial structure | (existing) |
| Monty Hall | 30 | a random player, private sight (GDL-II) | (existing) |
| corridor | 44 | shared, redundant and interacting rules | exhaustive (existing) |
| breakthrough-mini | 52 | two movement rules told apart only by their ACTION | exhaustive: 987 states, none stuck |
| skirmish | 63 | subject-specific movement — `move(guard, …)`, `move(lancer, …)` — as in Royal Chess | 6,000 states enumerated, none stuck; 200 random games all end within 8 plies |
| muddy children | 32 | knowledge as a game condition (GDL-III) | (existing) |

Labels are stated by head predicate, optionally narrowed by the action a
statement grants or reads (`legal/advance`, `cell/`, `legal/move.guard`).
Selectors are matched against the statement as written, never against
anything LGREF derives. Without them, breakthrough's two movement rules
could not be told apart: they share every head predicate.

## Result

Re-run after #318 and #319 were merged (#321). The only game that moved
is muddy children, 0.388 → 0.548: #319 stopped telling its two
mirror-image update statements apart by where a constant was written.

```
TUNING on dev -- mean ARI per candidate
  coverage t = 0.0 .. 0.2      0.709   (all six identical; 0.03 is the default)
  scaled   k = 0.5, 0.75       0.709
  scaled   k = 1.25 / 1.5 / 2  0.238 / 0.230 / 0.227
chosen on dev: coverage(0.03), the default -- by the tie rule
validation: chosen 0.561 vs default 0.561 -> default kept

split       game            ARI    name-token  groups
dev         tictactoe       0.711    0.675       6
dev         dropthree       0.707    0.747       6
validation  nim             0.838    0.525       8
validation  montyhall       0.285    0.314       7
test        corridor        0.387    0.316      10
test        breakthrough    0.380    0.218       7
test        skirmish        0.337    0.107      16
test        muddychildren   0.548    0.222       6
```

What this says, plainly:

- **The coverage tolerance does not matter on these games.** Every
  tolerance from 0 to 0.2 gives the same partition on both dev games, so
  the dev split cannot tell the tolerances apart, and the default stands
  by the tie rule. Scaling the resolution *up* from the calibrated value
  is clearly worse. Tuning on the dev split cannot resolve the
  reviewer's first concern on games this small; the sensitivity curves
  below are the evidence that does.
- **Held-out performance is well below development performance.**
  ARI is 0.71–0.84 on the games built like the original benchmark and
  0.34–0.55 on the test games. The one held-out result before #315
  (corridor, 0.387) was not an outlier.
- **The structural signal is real but weak.** Identification beats the
  name-token baseline on all four test games, by a wide margin on
  skirmish (0.337 vs 0.107), the game most like Royal Chess. It **loses**
  on drop-three (0.707 vs 0.747) and Monty Hall (0.285 vs 0.314), and
  Monty Hall is below the 0.60 floor. These three results are strict
  expected failures in `test_identification_validation.py`, not
  lowered floors: if a later change fixes one, the test fails until the
  entry is removed.

### Sensitivity: ARI at raw resolution (descriptive, not used for any choice)

```
game             0.5  0.75   1.0   1.5   2.0   3.0   4.0   6.0   8.0  12.0
tictactoe       0.71  0.71  0.71  0.71  0.27  0.26  0.24  0.24  0.25  0.20
dropthree       0.71  0.71  0.71  0.71  0.20  0.20  0.20  0.22  0.19  0.19
nim             0.73  0.73  0.73  0.73  0.73  0.52  0.36  0.36  0.24  0.09
montyhall       0.11  0.11  0.11  0.23  0.23  0.23  0.28  0.17  0.19  0.19
corridor        0.40  0.38  0.38  0.38  0.38  0.39  0.39  0.15  0.12  0.09
breakthrough    0.32  0.41  0.41  0.40  0.38  0.11  0.10  0.07 -0.00  0.01
skirmish        0.35  0.35  0.35  0.36  0.31  0.32  0.33  0.20  0.14  0.08
muddychildren   0.40  0.40  0.42  0.55  0.53  0.41  0.37  0.29  0.17  0.17
```

Every game has a plateau and then a cliff, and the cliff sits at
different resolutions for different games: about 2 for tic-tac-toe and
drop-three, 3 for nim, 6 for corridor. No single raw value is right for
all of them, which is the case for a size-aware rule. But the best
held-out value is not always the calibrated one: breakthrough reaches
0.41 at resolution 0.75 against 0.380 calibrated. **No setting turns
0.35 into 0.7**; the held-out gap is not a tuning problem.

### Failure modes (default procedure)

| game | rules fragmented (into n) | predicted rules merging reference rules | reference-shared statements kept shared |
|---|---|---|---|
| tic-tac-toe | lines 2, marking 2 | 1 | – |
| drop-three | alternation 2, dropping 2, lines 2 | 2 | – |
| nim | arithmetic 3, taking 3 | 1 | – |
| Monty Hall | choosing 5, hiding 5, opening 2, sequence 3, switching 3 | 3 | 0 / 3 |
| corridor | movement 6, tempo 4, blocking 2, boundary 2 | 4 | 0 / 8 |
| breakthrough | capturing 5, advancing 3, alternation 2, ending 2 | 4 | 0 / 21 |
| skirmish | lancer 9, guard 5, ending 4, alternation, blocking, capture 2 | 4 | 2 / 14 |
| muddy children | rounds 5, observing 4, announcing 3, knowledge 3, payoff 3, dealing 2 | 3 | 2 / 4 |

No game drops a labelled statement. Two failure modes dominate:

1. **Shared statements are not shared.** The reference puts 21 of
   breakthrough's statements in two rules (direction, opponent and the
   board machinery both movement rules need), and identification keeps
   none of them in two. The overlap mechanism (a statement joins a second
   rule when 25% of its edge weight goes there) almost never fires on
   these games. That matters beyond scoring: the ablation fix in #313
   decides what is shared from the call graph, not from this mechanism,
   for exactly this reason.
2. **Fragmentation, worst where one rule has many statements.**
   Skirmish's lancer rule (slides in four directions) lands in nine
   predicted rules, and corridor's movement in six. Statements defining
   different predicates for one behaviour (`north`, `south`, `east`,
   `west`) have only weak edges between them.

## What would and would not help

- **More graph-link heuristics, tuned on these numbers:** not
  admissible. The test split is now known; developing against it would
  turn it into a development set. A change to the method must be
  developed on dev, decided on validation, and then reported on test,
  as here.
- **Signals from play: tested, and not adopted** (next section).
- **Larger dev games** would make the tolerance tuning meaningful. On
  35–45 statement games every tolerance gives the same partition.

## Signals from play (#321)

With co-activation at weight zero, grouping is purely static, and the
earlier null result was one signal on two games. Two play signals were
run through this protocol, with every setting pre-registered on #321
before any score was seen (`lgref/identify/signals.py`):

- **co-activation**, the existing signal: statements whose bodies are
  satisfiable in the same sampled states (Jaccard ≥ 0.8);
- **co-use**, new and aimed at the shared-statement failure: for every
  outcome derived in play (each legal move, successor fact, ending and
  payoff), the statements its proof actually used. Edges use
  containment (the rarer statement of a pair appears with the other in
  ≥ 80% of its proofs), so a helper two rules share can link into both.
  The resolver is not modified: each statement carries a marker goal
  that records it in the substitution, so a statement tried and
  abandoned, or consulted under negation, leaves no mark.

Each signal was tried at weights 0.5, 1 and 2, with traces from 20
random games of up to 40 plies:

```
TUNING on dev -- mean ARI
  static         0.709   (default)
  co_activation  0.709 / 0.638 / 0.656    (weight 0.5 / 1 / 2)
  co_use         0.709 / 0.712 / 0.728
chosen on dev: co_use 2.0
validation: chosen 0.465 vs default 0.561 -> static kept

game           static  act0.5 act1.0 act2.0  use0.5 use1.0 use2.0
corridor        0.387   0.387  0.392  0.360   0.379  0.356  0.382
breakthrough    0.380   0.304  0.304  0.245   0.372  0.391  0.385
skirmish        0.337   0.212  0.197  0.188   0.278  0.310  0.288
muddychildren   0.548   0.490  0.483  0.419   0.532  0.503  0.514

labelled-shared statements kept in two or more rules (static -> best)
  breakthrough 0/21 -> 2/21 (use2.0), corridor 0/8 -> 1/8,
  skirmish 2/14 -> 3/14, muddy children 2/4 -> 3/4, Monty Hall 0/3 -> 3/3
  (act1.0, which lowers ARI elsewhere)
```

**Which reasoner.** These numbers were recorded under the resolver, before
#291 made the fast reasoner the default. The fast reasoner returns legal
moves sorted, so the random games behind the traces play out differently,
and the co-use scores move slightly (dev at weight 2: 0.716 instead of
0.728; breakthrough at weight 2: 0.403 instead of 0.385). Co-activation and
the static scores are unchanged. **The decision is the same**: dev picks
co-use at weight 2, and validation (0.465 vs 0.561) keeps static. To
reproduce the table exactly, run
`GGP_REASONER=resolver python3 -m lgref.identify.signals`.

What this says:

- **Neither signal is adopted.** Co-use wins on dev and loses clearly on
  validation (nim falls from 0.838 to 0.646). On the test games
  co-activation is worse everywhere it differs, and co-use is within
  noise of static, slightly below on average. Grouping stays static
  **because play-based grouping was tested on held-out games and did
  not help**, not by assumption.
- **The dev split cannot see sharing.** Neither dev game has a
  statement labelled as shared, so a signal aimed at sharing can only
  be judged on validation and test. A dev game with shared rules would
  make this tunable.
- **Why co-use does not recover sharing** (descriptive, from the traces,
  not used for any choice). 12 of breakthrough's 21 shared statements
  are `init` facts, consumed when the game is set up, which no proof in
  play ever uses. No play signal can see them. Of the other 9, 5 gain
  co-use edges, and none of those reaches both of the statement's
  rules. Corridor's 8 all gain edges, again none reaching both.
  Statements the reference shares are used mostly with ONE rule's
  statements in practice, so the signal reinforces a single home.

## Reproducing

```bash
python3 -m lgref.identify.protocol
```

The tests that pin the protocol's discipline (dev only for tuning,
validation once, test never) are in
`lgref/tests/test_validation_protocol.py`.
