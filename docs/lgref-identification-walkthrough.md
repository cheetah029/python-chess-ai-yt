# How LGREF finds rules — a walkthrough in infix GDL

A plain-language companion to `docs/lgref-phase1.md`, which states the
method formally. This file answers four questions with worked examples
from the actual description:

1. How does the clustering decide which clauses belong together?
2. How big is a "rule" — the whole boulder, or just its no-return memory?
3. What does an ablation actually delete?
4. Can we ablate combinations, and should we?

**Dialect.** Every example is infix HRF from `docs/gdl/integrated.gdl`,
the project's official description (issue #190). The prefix-KIF file
`integrated_prefix.gdl` says the same thing in an outdated dialect that
is hard to read; it is never quoted here.

---

## The running example

Five real statements from `docs/gdl/integrated.gdl`, all concerning the
boulder:

```prolog
101  legal(PLAYER, move(boulder,intersection,TF,TR)) :-
         true(control(PLAYER)) & true(boulder_at(intersection)) &
         true(boulder_first_move) & true(boulder_cooldown(0)) &
         boulder_first_dest(TF,TR) & empty(TF,TR) &
         ~and_white_and_turn_1(PLAYER)

102  legal(PLAYER, move(boulder,FF,FR,TF,TR)) :-
         true(control(PLAYER)) & true(cell(FF,FR,none,boulder)) &
         true(boulder_cooldown(0)) & king_step(FF,FR,TF,TR) &
         empty(TF,TR) & ~true(boulder_last(TF,TR))

343  boulder_first_dest(d,4)

352  next(boulder_last(FF,FR)) :-
         does(MOVER, move(boulder,FF,FR,TF,TR)) & distinct(FF,intersection)

353  next(boulder_last(F,R)) :-
         true(boulder_last(F,R)) & ~boulder_moved_this_turn
```

A human reading `RULEBOOK_v2.md` knows that 102, 352 and 353 together
*are* the no-return memory. The program starts with 522 statements in a
flat list and no idea which go together.

---

## 1. How the clustering works

### Step 1 — parse each statement into a record

Head, body predicates, state read, state written, action, subject. One
distinction carries a lot of weight:

- `boulder_first_dest(d,4)` is a **derived predicate**. Recomputed
  whenever asked; nothing is stored.
- `true(boulder_cooldown(0))` reads a **fluent**: stored game state,
  written by a `next` rule on the previous turn.

Conflating the two was a real defect in this project's GDL. It matters
here because a fluent links clauses *across a turn boundary* and a
derived predicate links them *within* one turn.

### Step 2 — draw typed edges

Six kinds, each for a different reason. All six occur in the boulder:

| edge | meaning | example |
|---|---|---|
| `predicate` | B's body calls what A defines | 101 calls `boulder_first_dest`, 343 defines it |
| `same_head` | the alternative cases of one definition | the four `boulder_first_dest` facts |
| `legality` | a `legal` clause and the `next` clause that carries out that action | 102 permits `move(boulder,...)`; 352 fires on `does(_, move(boulder,...))` |
| `temporal` | A writes a fluent B reads, one turn later | 352 writes `boulder_last`, 102 reads it |
| `shared_state` | two clauses both *require* the same fluent | 101, 102, 103 all require `true(boulder_cooldown(0))` |
| `terminal` | both feed the ending condition | `lost`, `goal`, `terminal` |

Two of these are load-bearing and easy to miss.

**`legality`.** Clause 102 says the move is permitted; 352 says what
happens when it is played. Obviously one provision to a human — yet they
never mention each other. GDL routes the connection through the game
manager via `does`. Without a dedicated edge, permission and consequence
land in different clusters every time.

**`temporal`.** Clause 102 sits in the legal-move region of the file and
352 hundreds of lines away in the state-update region. They share no
predicate call. The only link is that one writes `boulder_last` and the
other reads it, a turn apart.

**The negation criterion.** Only *positive* reads make a `shared_state`
edge. `invulnerable` is read by 29 clauses, nearly always as
`~true(invulnerable(...))` — a guard. "Both clauses check the target is
not invulnerable" does not mean they are the same rule; it means
invulnerability *constrains* both. Counting negated reads merged every
capturing rule into one lump. Excluding them took shared-state edges from
580 to 82, and what survived was rule structure. Temporal edges still
count negated reads, which is why 102 ↔ 352 survives — correctly, since
the `boulder_last` fluent exists solely to serve that restriction.

### Step 3 — community detection

Louvain on the weighted graph: groups with many internal edges and few
leaving. Clauses implementing one rule reference each other heavily and
other rules lightly.

### Step 4 — soft membership

`empty` is called by nearly every movement rule. A clause connected into
several communities is marked a **shared member** of all of them rather
than being arbitrarily awarded to one.

### Step 5 — test each candidate by breaking it

Not graph analysis, an experiment. Delete the cluster's clauses; does it
load, is it playable, did anything observable change? Four verdicts:
`rule`, `load_bearing`, `inert`, `broken`.

### What this does not do

**It never learns the word "boulder."** It finds a group of clauses that
happen to be boulder clauses. Naming is Phase 2's job.

**Step 5 cannot tell a rule from the arithmetic it is written in.**
Delete `boulder_cooldown` and moves change. Delete `rank_delta_1`
("these squares are one rank apart") and the knight stops moving, so
moves also change. Same symptom, different cause. Open problem; see
`docs/lgref-phase1.md`.

---

## 2. How big is a rule? — it is a tree, not a level

Louvain's `resolution` decides how finely to cut. It is a *scale*
parameter measured against total graph weight, so a value calibrated on
34-clause tic-tac-toe is systematically too coarse on 522-clause Royal
Chess. Issue #189.

Turning the knob up, with no hand-tuning, separates the boulder into the
rulebook's own provisions:

| clause group | rulebook provision |
|---|---|
| `boulder_first_dest`, `boulder_at`, `center_crossing_blocked` | first move must be to d4/d5/e4/e5 |
| `boulder_cooldown`, `pawn_at` | the cooldown |
| `boulder_first_move`, `boulder_moved_this_turn` | White may not move it on turn 1 |
| `boulder_last` ×2 | **the no-return memory, alone** |
| `center_diag_pair` ×4 | blocks diagonals on the central intersection |

So the fine granularity is already in the graph. Reporting one flat list
at one resolution discarded it. The output should be a **hierarchy**:
the boulder subsystem contains boulder-movement rules, which contain the
no-return memory.

---

## 3. What an ablation deletes — and the granularity floor

Today: every clause of one cluster, deleted whole. Since the clusters
are currently too big, the ablations are too big — fixed by fixing the
resolution.

But there is a second limit that resolution does not fix. Look again:

```prolog
legal(PLAYER, move(boulder,FF,FR,TF,TR)) :-
    true(control(PLAYER)) & true(cell(FF,FR,none,boulder)) &
    true(boulder_cooldown(0)) & king_step(FF,FR,TF,TR) &
    empty(TF,TR) & ~true(boulder_last(TF,TR))
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
                   this, and only this, is the no-return restriction
```

The no-return memory is not three whole clauses. It is two whole clauses
(352, 353, which maintain the fluent) **plus one conjunct inside clause
102** — a clause that also does the separate job of defining how the
boulder moves at all.

Deleting whole clauses only, "ablate the no-return memory" deletes 102
and removes **all non-capturing boulder movement**. A much larger and
different experiment. Two operations are therefore needed:

- **delete a clause** — coarse; removes a whole case.
- **delete one conjunct from a body** (*relax*) — fine; isolates
  `boulder_last` from boulder movement.

Relaxing has two useful properties. Dropping a conjunct from an `&`-list
can only make a rule easier to satisfy, so the game gets *more*
permissive and relax ablations essentially never come back `broken` or
`load_bearing` — the two verdicts that make a rule unmeasurable. And it
is mechanically checkable: standard datalog safety (every head variable
still bound by a remaining positive conjunct) catches the cases where
dropping a conjunct leaves the clause unsafe. Dropping
`king_step(FF,FR,TF,TR)` from 102 would unbind `TF`/`TR`; dropping
`~true(boulder_last(TF,TR))` binds nothing and is safe.

---

## 4. Combination ablations

Cooldown and no-return are both throttles on the same piece — one limits
*how often* it moves, the other *where*. Remove the cooldown and the
boulder moves every turn, which gives the no-return rule far more work to
do. The two partly cover for each other, so:

> effect of removing both ≠ effect of removing one + effect of removing
> the other

The gap is the **interaction**, and it costs one extra run per pair:

```
interaction(A,B) = effect(remove A and B) − effect(remove A) − effect(remove B)
```

Near zero → independent provisions. Large and negative → redundant with
each other. Large and positive → they only function as a pair, and
splitting them was a mistake — which makes this an empirical check on
whether the clustering was right. Identification proposes; ablation
disposes.

### Relaxing everything is not removing the thing

Relaxing all the boulder restrictions gives an **unrestricted** boulder —
moves every turn, anywhere adjacent, returns freely. Probably a stronger
piece than the real one. That is not "no boulder." Three distinct
operations:

| operation | effect | case-study example |
|---|---|---|
| **relax** | drop a conjunct; game more permissive | the fine-grained boulder ablations |
| **remove** | delete a provision and the entity it governs | Boulder, Tiny Endgame, Queen Manipulation |
| **replace** | substitute an alternative definition | Knight Redesign (v2 → legacy knight) |

Relax and remove are generated automatically from the graph. **Replace
cannot be** — it needs a designer-written alternative. LGREF *discovers*
relax and remove candidates and *evaluates* replace variants proposed by
a designer.

### Budget

Full grids are combinatorial: five boulder atoms is 32 subsets, eight is
256, and across four subsystems roughly 300 variants against a Tier 1
budget of about 40. Staged instead:

- **Stage A** — baseline, each atom alone, each subsystem whole
  (≈25 variants). Fits Tier 1.
- **Stage B** — compute `residual = effect(whole) − Σ effect(atoms)` per
  subsystem; spend on pairs only where the residual is large. Adaptive,
  so nothing is paid for absent interactions.
- **Stage C** — Tier 2 (MCTS, win/loss/draw) affords 4–6 variants at
  three seeds: whole subsystems only.

Where a full grid is affordable it yields **Shapley values** — each
atom's share of the whole rule's effect, guaranteed to sum to the whole.
That is the exact reconciliation of atomic and composite ablation, and
worth doing on at least one subsystem as a demonstration.

---

## Implemented: the three modes

`lgref/ablate/operations.py` (issue #193). Both automatic modes are
derived from the logic — no predicate-name matching, nothing specific to
Royal Chess.

### relax — drop a body conjunct

```
relax boulder_last        drops 1 conjunct   [1 clause refused: would unbind a head variable]
relax boulder_cooldown    drops 6 conjuncts
```

**Safety is the discriminator, and it does real work.** Relaxing
`boulder_last` must drop the guard `~true(boulder_last(TF,TR))` out of
the movement rule — that guard *is* the no-return restriction — while
leaving `next(boulder_last(F,R)) :- true(boulder_last(F,R)) & ...`
alone, whose positive goal is the only thing binding the head's `F` and
`R`. Dropping it there yields a clause with no defined meaning, not a
freer game.

Polarity does **not** separate those two cases: the cooldown restriction
is the *positive* goal `true(boulder_cooldown(0))`, and dropping it is
exactly right because it binds nothing the head needs. What separates
them is whether the head stays bound. Refusals are reported, never
silent, so a partial relaxation cannot be read as a complete one.

Verified monotone: relaxing never shrinks the legal-move set.

### remove — delete an entity and everything that dies with it

```
remove bishop    522 -> 453 forms      remove knight    522 -> 391 forms
remove boulder   522 -> 474 forms      remove pawn      522 -> 453 forms
remove king      522 -> 490 forms      remove queen     522 -> 425 forms
remove rook      522 -> 483 forms
```

Entities come from the discriminator slot of the game's own action
terms, so the list is whatever the game is about — on nim it is `1` and
`2`, from `take(1)` and `take(2)`.

The closure has four stages, each one added because the previous version
produced a variant that loaded, played, and was wrong:

1. **Syntactic.** Facts and clauses mentioning the constant go — except
   that a *negative* mention is only a guard and is dropped on its own.
2. **Structural guards.** `distinct(PIECE, boulder)` is positive but is
   an *exclusion*, not a requirement that the boulder exist. Reading it
   as a requirement deleted the core `next(cell(...))` board update for
   every piece in the game.
3. **Dead code, to a fixpoint.** Undefined predicates, unread fluents,
   unused derived predicates. This is what reaches `boulder_cooldown`
   and `boulder_last` — they die because their writers and readers died,
   not because of their names. **Pre-existing gaps are excluded**: Royal
   Chess consults four predicates it never defines, and cascading from
   those deleted the entire tiny-endgame and repetition machinery when
   removing the *boulder*.
4. **Frozen entity state.** The hard one. `boulder_at` never contains
   the constant `boulder` anywhere; it is held true by
   `next(boulder_at(intersection)) :- true(boulder_at(intersection)) &
   ~boulder_moved_this_turn`. Remove the boulder, that guard becomes
   vacuously true, and the fluent is asserted forever — so the departed
   boulder goes on blocking the central diagonals. The signature is that
   the removal changed how a fluent can change and what remains can
   never change at all. A frozen fluent is not state; it is a constant
   the ablation accidentally left behind, belonging to the entity that
   used to move it.

### Confirmed distinct from relaxing everything

Relaxing all four boulder restrictions leaves all 522 forms and an
*unrestricted* boulder. Removing it leaves 474 forms and no boulder.
Different experiments, as intended.

## Running it

```bash
python3 -m lgref status
python3 -m lgref identify  --gdl docs/gdl/integrated.gdl
python3 -m lgref ablations --gdl docs/gdl/integrated.gdl
python3 -m lgref run       --gdl docs/gdl/integrated.gdl
```

`python3 lgref/main.py status` works too, and no `PYTHONPATH` is needed
for any of it — LGREF puts the repository root and `src/` on the path
itself. For the Phase 1 verdicts, which need the multi-minute
intervention probe:

```bash
python3 -m lgref.identify.gate --config lgref/config/phase1_gate.yaml
```

Work in progress: `status` lists which phases are built and what the
missing ones are waiting on, so the tool does not imply it is finished.
