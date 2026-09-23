# LGREF Phase 1 — Rule Identification

**Formal clauses → rules.** Given a GDL description, identify which
clauses jointly implement each gameplay rule, and which of those rules
can have their contribution measured by ablation.

Issue [#187]. Vocabulary per [#175]: a *formal clause* is one statement
in the description; a *rule* is a gameplay provision implemented by one
or more clauses.

## Input dialect, and what is stale because of it

LGREF reads **infix HRF** GDL — `docs/gdl/integrated.gdl`, the project's
official dialect (issue #190). Prefix KIF is refused with an error
naming the converter, because the two dialects do not have the same
statement count and a silent fallback would change every number in this
document without saying so.

**The counts below are from the prefix reading and are stale.** Prefix
`(or A B)` bodies expand to one rule per branch in infix, so the
description LGREF now sees has **522 clauses, not 488**. Every figure in
"Gate result on Royal Chess" needs re-running at the new count. The
validation scores on tic-tac-toe and nim are stated by head predicate,
so those survive the change, but they are re-run too. Finer clause
granularity is the direction issue #189 wants, so the expansion is an
improvement rather than a problem — it still has to be measured rather
than assumed.

## Why this phase can be trusted

The GDL reproduces `main.py`'s legal-move set **exactly** — 1200/1200
sampled positions (Phase 0.5). Rules identified from these clauses
therefore describe the same game whose contributions Phase 3 measures.
Before that work, identification would have been built on a description
that disagreed with the engine from ply 1.

## Game-independence

LGREF evaluates rules in **any** GDL game; Royal Chess is the case study,
not the subject. Nothing in `lgref/identify/` names a Royal Chess
concept. Everything game-specific is derived from the description under
analysis:

| Derived | From |
|---|---|
| action names | the action terms of `legal(P, X(...))` |
| action subjects | constants in an action term's discriminator slot |
| predicate aliases | structural detection of mechanically derived variants |
| terminal predicates | direct feeders of `terminal` and `goal` |
| ubiquitous fluents | a fraction of clauses, calibrated per game |

Only GDL's own reserved words are fixed, and those are fixed by the
specification rather than by this game. The derived pipeline reproduces
the previously hardcoded one **exactly** on Royal Chess — same 488 nodes,
same edge counts — while also handling a card game whose actions are
`play` and `discard` over subjects `spade` and `heart`.

## Pipeline

### 1. Clause normalisation

Each clause becomes a typed node: head predicate, body predicates,
fluents read and written, action reads, action type, subjects, negated
goals, terminal dependency.

Two typings matter:

**Derived predicates and fluents are different node types.** `foo() :-
...` defines a predicate recomputed on demand; `true(foo)` reads
state written by `next(foo)`. A fluent creates a *temporal* edge
across a turn boundary, a derived predicate an immediate one. Conflating
them was a real defect in this project's GDL (#177 B4).

**Mechanically derived variants collapse onto their base.** Detected
structurally — a predicate whose name extends another's, takes more
arguments, and draws on the same predicates — never by a hardcoded
suffix. Found all five `_except` variants without knowing that
convention, and correctly declined to fold `rank_adj` into `rank`.

### 2. Typed dependency graph

Six edge types, separate because collapsing them makes whole classes of
rule unfindable:

| Edge | Meaning |
|---|---|
| `predicate` | B's body calls the predicate A defines |
| `same_head` | clauses defining one predicate — the disjunctive cases of a single definition |
| `legality` | a `legal` clause and the `next` clause performing that action |
| `temporal` | A writes a fluent B reads, **across a turn boundary** |
| `shared_state` | two clauses positively consulting the same fluent |
| `terminal` | both feed the ending condition |

`legality` edges are load-bearing because those two clauses communicate
only through `does`, which the game manager supplies — no predicate edge
ever links them, yet permitting an action and carrying it out are one
provision. `temporal` edges are how rules split across turns are found at
all: the boulder cooldown, the manipulation freeze and the bishop's
reactive arming all have halves separated in time.

**The negation criterion.** Only *positive* reads create a shared-state
edge. `invulnerable` is read by 29 clauses and `manipulation_freeze` by
21, nearly always as `~true(...)` — a guard, meaning one rule
*constraining* another rather than two clauses implementing one rule.
Linking all 29 capture rules because each checks invulnerability would
merge every capturing rule into one cluster. Edges fall 580 → 82, and the
survivors are rule signatures.

**Hub fluents are excluded from both shared-state and temporal edges.** A
hub has many writers *and* many readers, so it contributes their product
in temporal edges: on tic-tac-toe `cell` alone produced 104 of 115.

### 3. Clustering

Louvain over a weighted collapse of the typed edges, with **soft
membership** — a shared helper belongs to every rule it serves, rather
than being arbitrarily awarded to one.

Generic effect clauses are held out of the base partition and added back
as shared members. `does(M, move(PIECE, ...))` carries a *variable* in
the discriminator slot, so it serves every movement rule; leaving it in
merged every rule producing that action, and a single 88–91 clause
community survived every resolution from 0.5 to 16.0.

Weights are **parameters, not constants**, exposed so their influence can
be varied and reported.

### 4. Intervention coherence

For each candidate, build an ablated description and ask: does it
compile, is it still playable, and did behaviour change — either legal
moves lost, or *when games end*?

Four verdicts, deliberately not collapsed to pass/fail:

| Verdict | Meaning |
|---|---|
| `rule` | removable, playable, changes behaviour — **measurable by ablation** |
| `load_bearing` | removing it leaves no playable game. Likely a real provision, but its contribution **cannot be measured this way** |
| `inert` | nothing observable changed |
| `broken` | the ablated description does not load |

The `load_bearing` category is the honest one. Turn alternation *is* a
rule, but Phase 3 would otherwise compare a game against a non-game and
report the breakage as a contribution.

Termination is probed with **ten seeds** and compared on whether games
end plus mean length against a **relative** threshold. Each of those was
forced by a measured failure — see below.

## Validation: the gate

Scored against games whose boundaries a human can state with certainty,
**before** trusting the method on Royal Chess where nobody knows the
right answer and a plausible cluster list is indistinguishable from a
correct one.

Two games chosen to be structurally unlike Royal Chess: tic-tac-toe (no
pieces, no movement, no captures) and single-pile nim (no cells, no
spatial structure at all).

Pairwise scoring, because cluster labels are arbitrary. **ARI is the
headline** — recall alone is maximised by one giant cluster and precision
by all singletons, so only chance-corrected agreement penalises both.

| game | LGREF ARI | name-similarity | LGREF F1 | baseline F1 |
|---|---|---|---|---|
| tic-tac-toe | **0.687** | 0.659 | **0.779** | 0.730 |
| nim | **0.753** | 0.525 | **0.814** | 0.595 |

Resolution is **calibrated, not transferred** (#189). Louvain's
`resolution` is a scale parameter measured against total graph weight,
so a constant tuned on a 22–34 clause game is systematically too coarse
on a 522-clause one. It is chosen instead to hold *mean clauses per
rule* at the value validated against hand-verified boundaries —
tic-tac-toe 6.0, nim 5.2 — because a rule is a handful of clauses
whatever the size of the game: a bigger game has more rules, not bigger
ones.

The safety property is that the validation scores are **preserved** —
tic-tac-toe 0.711 and nim 0.734 under calibration, against 0.713 and
0.736 at the hand-picked resolution, and both still ahead of the
name-token baseline. The fix cannot have traded a known-good answer for
an unknown one. On Royal Chess it picks ~33,
and the largest cluster falls from **80 clauses to 14** — the
`load_bearing` blob holding the movement rules of every piece was an
artefact of the transferred constant, not a provision.

## Findings

### Co-activation does not help (null result)

The brief asks for dynamic co-activation as a third signal. Built,
measured, **disabled**:

| game | static only | + co-activation | raw co-occurrence |
|---|---|---|---|
| tic-tac-toe | 0.687 | 0.663 | 0.301 |
| nim | 0.753 | 0.613 | 0.251 |

Each state's firing clauses form a clique, and in a well-formed game most
clauses are satisfiable in most states — so co-firing largely reports
"the position is normal" rather than rule membership. On Royal Chess the
same filter still produced 3,737 edges from 16 states, and there is no
ground truth there to judge it against.

Weight set to 0.0; machinery kept and the `trace_only` baseline still
runs, so the finding is reported rather than hidden. Raising it requires
evidence from a game where it measurably helps.

### The baseline initially won, and that found two defects

Grouping by shared name tokens beat the typed graph (0.439 vs 0.659 on
tic-tac-toe). Diagnosing why found two real problems, neither visible on
Royal Chess:

1. the ubiquity cut was applied to shared-state but **not temporal**
   edges, so hub fluents merged rules through the back door;
2. **clauses defining the same predicate had no edge between them** —
   tic-tac-toe's 16 marking clauses had three edges among them, because
   its 13 `next cell` cases were mutually unconnected. That is exactly
   the signal the baseline exploits.

### Clustering was not reproducible, and that invalidated earlier counts

The engineering rules require a run to be reproducible from one config
plus a seed. Clustering was not. `seed` reached Louvain, but the node and
edge order handed to it came from iterating Python sets of string ids,
and string hashing varies per process. Measured on the case-study
description across five values of `PYTHONHASHSEED`, the same input gave
**18, 19, 20, 19 and 19 clusters** with different size distributions.

Every cluster count reported before this fix — including the gate result
of "17 candidates, 12 `rule`, 2 `load_bearing`, 3 `inert`" — was one
sample from that distribution rather than a result. The three clusters
that read as nameable rules may well be stable across samples, but that
was never checked, so it could not be claimed.

Diagnosing it surfaced a second and independent defect. `extra` (shared
helpers, from `_shared_members`) was indexed against the raw Louvain
community order, while `served` (held-out generic clauses, from
`_generic_service`) was indexed against the size-sorted order, and the
two were then combined as if the indices matched. Whenever sorting moved
a community — almost always — **shared helpers were attached to the
wrong rules.** That is a correctness defect, not a reproducibility one,
and it was present in every report.

Both are fixed: sorted node and edge insertion, communities returned in a
total order, and one index space for both attachment steps. Verified by
an identical partition signature across six hash seeds.

`lgref/tests/test_cluster_determinism.py` guards both. Written first
against tic-tac-toe, where **both mutations survived** — 35 clauses give
a partition too small and too stable to expose either defect. Repointed
at the case-study description, both mutations now fail the suite. A
regression test has to run where the bug lives.

### Measurement defects found in the intervention probe

- A standalone `check_cluster` never built a baseline *termination*
  probe, so every termination-governing rule read as inert.
- **One probe seed was not enough.** Removing tic-tac-toe's line
  detection still ends after nine marks (the board fills), so seed 0
  showed no difference. A test now asserts seed 0 hides this rule.
- **An absolute ply threshold was brittle**: at five seeds the line rule
  read as inert, at ten it passed. A criterion whose answer depends on
  sample size is not a criterion. Now relative to game length — one ply
  is decisive in nine-ply tic-tac-toe and invisible in a 300-ply variant.
- The baseline termination probe was recomputed **once per cluster**,
  turning a ~4 minute sweep into one still unfinished at 25. Hoisted.

## Held-out labels

The designer's seed ontology labels stay quarantined in
`lgref/reference/`, which is not an importable package.
`lgref/tests/test_label_isolation.py` walks the AST of every module under
`identify/` and `functions/` and fails the build on any import **or
string literal** naming it — because the realistic leak is a path-based
read, not an import. All three leak routes are mutation-tested.

Phase 1 never sees them.

## Gate result on Royal Chess — and an honest limitation

Full output: `lgref/report/phase1_royal_chess.txt`.

**488 clauses → 17 candidates → 12 `rule`, 2 `load_bearing`, 3 `inert`.**

Three clusters correspond to rules a human would name, which is real
evidence the method works on a description it was never tuned against:

| cluster | contents | reads as |
|---|---|---|
| R06 | `boulder_cooldown`, `boulder_first_dest`, `boulder_at`, `boulder_first_move`, `center_diag_pair` | the boulder rule |
| R04 | `reactive_armed`, `diag_step`, `bishop_diag_los`, `los_diag_ray` | bishop reactive capture |
| R02 | `tiny_endgame_active`, `distance_count`, `lost`, `terminal`, `goal`, `succ` | tiny endgame + termination |

### The limitation: coordinate geometry is not separated

Several clusters classified as `rule` are **board vocabulary, not
gameplay provisions**:

- **R01** — `file_delta_1`, `between_rank`, `rank_delta_2`, `knight_step`
- **R03** — `rook_step`, `sweep_path`, `los_orth_ray`
- **R05** — `rank_delta_1`, `between_file`, `file_delta_2`

These pass intervention coherence for a reason that exposes a real gap in
the test: **removing the vocabulary a rule is written in removes moves,
exactly as removing the rule would.** Delete `knight_step` and knights
stop moving; the probe sees 58 legal moves disappear and reports a
focused, playable, behaviour-changing ablation. It cannot tell "this rule
was removed" from "the language that rule is expressed in was removed".

This was predicted before the run and deliberately left unfixed, because
fixing it by hand would have meant tuning against Royal Chess with no way
to tell whether it helped.

**Why the obvious fix does not work.** "Clauses that touch no fluent are
static vocabulary" captures 275 of 488 clauses — more than half, and it
sweeps in `allowed_form`, `enemy_can_reach`, `dead` and
`at_least_7_non_king_non_boulder`, which are genuine rule content. The
criterion is too blunt.

**The principled fix**, which follows from what a rule *is* in this
framework: a clause that is **identical across every ablated variant of
the game** cannot be part of what distinguishes them. Board geometry is
common to all variants by construction; boulder cooldown is not. That
test is empirical rather than stipulated, needs no game knowledge, and
reuses the ablation machinery already built — but it requires a set of
variants to compare, which is exactly what Phase 3 supplies.

Until then, the candidate list should be read as **rules plus the
vocabulary they are written in**, not as a clean rule set. Phase 2 must
not treat R01/R03/R05 as provisions with strategic functions.
