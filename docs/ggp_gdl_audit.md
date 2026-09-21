# GGP + GDL audit against the rulebook

Audit of the two least-trusted layers of the rule stack, done as part of
LGREF Phase 0.5 (issues #170, #177).

## Trust order

Established by the project owner, and used to decide which side is wrong
whenever two layers disagree:

1. **`RULEBOOK_v2.md`** — the English rulebook. Authoritative.
2. **The playable implementation** — `main.py` → `game.py` → `board.py`.
3. **The GDL** (`docs/gdl/`) — written afterwards; slightly untrustworthy.
4. **The GGP** (`src/ggp/`) — written last; underdeveloped and bug-prone.

`GameEngine` is **not** a separate fifth thing. `AIController.legal_turns`
points it at the live `Game` board, so the playable game and the LGREF
harness share one move-generation path through `board.py`. Whatever LGREF
measures is what `main.py` enforces. This matters for the paper: a reviewer
asking "did you measure the real game?" gets a structural answer, not a
promise.

## Why this audit exists

LGREF identifies rules from GDL clauses (Phase 1) and measures their
contributions by ablation in the engine (Phase 3). That is only valid if
the GDL and the engine describe the same game. Measured at the start of
Phase 0.5, they agreed on the legal-move set in **14% of midgame
positions**, with the first divergence at **ply 1 of every trial**.

The existing regression test hid this: it asserted
`perfect_match_count >= 1`, which the initial position satisfies
unconditionally, so it passed while reporting 5% agreement.

---

## Part 1 — GGP defects (the majority of the disagreement)

All in `src/ggp/cross_validation.py`. None of these are GDL rule errors:
the GDL asked for the right facts and the harness did not supply them.

### G1. Five fluents were never emitted by the state converter

`board_to_gdl_facts` translates a Python board into the GDL's state. Every
fluent it omits silently changes the meaning of the rules that read it: an
absent `boulder_cooldown` makes `(true (boulder_cooldown 0))` unsatisfiable,
and the boulder simply stops moving.

Enumerating every fluent read via `(true ...)` against what the converter
actually emitted:

| Fluent | Was emitted? | Consequence |
|---|---|---|
| `captured_friendly` | never | `allowed_form` could only derive `base` — **no transform was ever legal** |
| `manipulation_freeze` | never | Manipulation Restriction 1 ignored entirely |
| `boulder_last` | never | boulder no-return memory ignored |
| `distance_count` | never | Tiny Endgame distance limit inert |
| `tiny_endgame_active` | never | Tiny Endgame Rule never activated |

### G2. Boulder state was emitted only while on the central intersection

The whole boulder block sat under `if board.boulder is not None`. But
`board.boulder` is *only* the intersection reference — `Board` sets it to
`None` the moment the boulder moves onto a square (`board.py:140`), after
which the Boulder lives in `squares[r][c].piece`.

So once the boulder left the centre, **no cooldown, first-move flag or
no-return memory was emitted at all**. Verified directly: boulder on d5 with
`cooldown=2`, converter emitted exactly `('cell','d','5','none','boulder')`.

Largest single component of the disagreement: 285 engine-only and 506
GGP-only boulder moves across 200 sampled positions.

### G3. Boulder first-move from the intersection was untranslatable

The intersection is not a square, so the engine leaves `from_sq = None` and
the GDL names it with the atom `intersection`. `turn_to_gdl_move` bailed on
`from_sq is None`, dropping **every** engine boulder first-move from the
comparison and making all four of the GGP's look GGP-only.

### G4. Manipulations were dropped from the comparison entirely

`turn_to_gdl_move` returned `None` for every manipulation, on the grounds
that the engine's `Turn` does not record which queen acted.

It does not record it because it does not need to: **the manipulating queen
does not move and is otherwise unaffected**, so two queens with
line-of-sight to the same target produce the same successor state, and the
engine correctly enumerates that as one turn. The GDL's per-queen
granularity is a representational artifact, not a rule difference.

Resolved by normalising both sides to the engine's granularity
(`_normalize_manipulate` drops the queen's square). This is a deliberate
normalisation, recorded as such — not a fix to either side.

### G5. The regression test could not fail

See "Why this audit exists". Replaced by a real gate.

---

## Part 2 — GDL rule errors (engine correct, GDL wrong)

### B1. Any piece could capture the boulder

```
(<= (friend_at ?mover ?f ?r) (true (cell ?f ?r ?mover ?p)))
```

The boulder's colour is `none`, so it was nobody's friend, and every
non-king move rule guards only with `(not (friend_at ...))`. Knights, rooks
and queens could all take it.

> **Rulebook:** "the boulder may capture only pawns (of either colour);
> **only a king may capture the boulder**", and "the boulder is treated as a
> friendly piece by both sides for most purposes."

*Measured:* 18 GGP-only knight moves and 5 rook moves onto the boulder's
square.

**Fix:** a second `friend_at` clause making the boulder every side's friend.
`friend_at` is used **only** as a can't-land-here guard (17 uses, all
negated), and the king's move rule carries no such guard — so this blocks
non-king captures while leaving the king's boulder capture legal, which is
exactly the rulebook's wording.

### B2. The intersection boulder did not block diagonals

`boulder_at` appeared in exactly two rule bodies — the boulder's own move
and its persistence — and in **no** line-of-sight or path rule. Being off
the board, the intersection boulder is invisible to `occupied`, so every
diagonal ray passed straight through the centre.

> **Rulebook:** "when on the central intersection, the boulder blocks
> diagonal lines only — not files or ranks."

The engine implements this in five places via
`Board._diagonal_crosses_center` (`board.py:1548`). The GDL implemented it
nowhere.

**Fix:** a `center_crossing_blocked` predicate over the only two diagonal
steps that cross the intersection point (d5↔e4, e5↔d4), guarding the king
move, base-queen move, and both `los_diag_ray` clauses. Orthogonal rays
(`sweep_path`, `los_orth_ray`) are deliberately untouched — the rulebook
blocks diagonals only.

### B3. Bishop teleport safety ignored queen form

```
(distinct ?piece bishop)
(<= (can_capture_to ?atk queen ?ff ?fr ?tf ?tr) (king_step ?ff ?fr ?tf ?tr))
```

> **Rulebook:** "Enemy bishops, **queens-as-bishop**, and the boulder are
> excluded from this safety check."

Two defects, in opposite directions:

1. A transformed queen is `cell … queen` + `queen_form … bishop`, so
   `(distinct ?piece bishop)` did **not** exclude a queen-as-bishop. The GDL
   was *stricter* than the rulebook. *Measured:* 202 engine-only bishop
   teleports.
2. `can_capture_to` had one queen clause, `king_step`, so the check treated
   **every** queen as base form — blind to a queen-as-rook's sweep and a
   queen-as-knight's radius-2 reach. The GDL was *looser* than the rulebook,
   and a bishop could teleport onto a square either of them attacks.

**Fix:** a `bishop_like` predicate covering bishops and queens-as-bishop,
plus form-gated `can_capture_to` clauses for base, rook and knight forms.
The boulder needs no exclusion clause: its `none` colour never unifies with
the `?atk` bound by `(opponent ?mover ?atk)`, so it was already excluded.

A duplicate unguarded queen clause in `step6` had to be patched too — the
build unions clauses across step files, so one unguarded copy anywhere
defeats a guard added elsewhere.

### B5. The rook's threat range ignored its own pivot-blocking rule

The bishop teleport-safety check asks `can_capture_to` "could this enemy
piece capture at that square?". For the rook's two-segment move it asked:

```
(<= (can_capture_to ?atk rook ?ff ?fr ?tf ?tr)
    (rook_step ?ff ?fr ?mf ?mr ?dir1)
    (perpendicular ?dir1 ?dir2)
    (sweep_path ?mf ?mr ?tf ?tr ?dir2))
```

while the rook's own legal-move rule requires the pivot square to be empty:

```
    (rook_step ?ff ?fr ?mf ?mr ?dir1) (not (friend_at ...)) (not (occupied ?mf ?mr)) …
```

> **Rulebook (Rook):** "One square orthogonally. Then a 90° turn and any
> number of squares in the new direction… it may not jump over pieces."

A rook cannot turn the corner on an occupied square. Omitting
`(not (occupied ?mf ?mr))` credited every rook with threatening squares it
cannot actually reach, so the safety check marked too many squares unsafe
and the GGP refused bishop teleports the engine allows. This was the
dominant residual: **171 engine-only bishop teleports**.

Note `sweep_path` itself is correct — its recursive clause does require
empty intermediates. Only the pivot was unguarded.

**Fix:** add the pivot-empty condition to the two-segment clause.

**Self-inflicted variant.** The queen-as-rook clause added for B3 was
mirrored from this buggy rook clause and inherited the same omission. Both
are fixed together. Mirroring an existing rule is how a defect in it
propagates.

### B6. Knight jump-capture inclusion ignored the landing-square requirement

The bishop teleport-safety check must treat a square as unsafe if an enemy
knight could jump-capture a bishop standing there. It asked only whether
the square was adjacent to an enemy knight:

```
(<= (jump_capturable_by_knight ?atk ?tf ?tr)
    (true (cell ?nf ?nr ?atk knight))
    (king_step ?nf ?nr ?tf ?tr))
```

> **Rulebook (Knight, jump capture):** "the knight may capture that piece on
> its **immediate next turn** by making a normal radius-2 move **to an empty
> landing square**, with the moved enemy as the jumped square."

Adjacency is necessary but not sufficient: the knight also needs somewhere
legal to land. The rule ignored that, so every square beside an enemy
knight was flagged unsafe and the GGP refused bishop teleports the engine
correctly allows.

**Worked case** (seed 1000, ply 9). Black bishop b4, teleport to c4:

```
8 . k r n n r q .
7 p p p p p p p .
6 . . . . . . . p
5 . B . . . . . .     white bishop b5
4 . b . . . . . .     black bishop b4
3 . . . N . B . .     white KNIGHT d3
2 P P P P P P P P
1 . Q R N . R K .
  a b c d e f g h
```

c4 is chebyshev-1 from the white knight on d3, so the old rule called it
unsafe. But the only knight move that jumps **over** c4 is the 2-diagonal
d3→b5, and **b5 is occupied by a white bishop**. No jump capture was ever
available, and the engine was right to allow the teleport.

**Fix:** require a legal jump — `knight_step` to an `empty` landing square
with the target as the `knight_jumped_square` — mirroring the real
`legal jump_capture` rule. Queens-as-knight are included, since step 7 gives
them the same action.

**This vindicates the engine.** The dominant residual was a GDL defect, not
an engine one — consistent with the project's trust order.

### B7. Union-merge stale copies — a structural hazard, three instances

`build_integrated.py` merges the eleven step files by **de-duplicating
identical clauses**, i.e. by UNION. Each step file is self-contained and
redeclares the helpers it needs, which means a guard added to one file's
copy of a rule does **not** constrain another file's copy. Both survive the
merge, and since a predicate's clauses form a disjunction, **the looser copy
wins**.

Three instances surfaced during this audit, none of which failed a test at
the time:

1. **`can_capture_to ?atk queen`** — step6 kept an unguarded `king_step`
   copy after step5 gained `(true (queen_form ?ff ?fr base))`, so every
   queen was still treated as base form and the B3 fix was defeated.
2. **`enemy_can_reach`** — step6 kept the pre-`bishop_like` copies, so the
   queen-as-bishop exclusion never took effect.
3. **`legal (move bishop ...)`** — a stale call site at the old 4-argument
   arity survived after `enemy_can_reach` widened to 5. This one is worse
   than a wrong answer: a goal whose arity nothing defines is
   *unsatisfiable*, and under negation-as-failure `(not (unsatisfiable))` is
   vacuously **true**. The safety check did not fail — it silently
   evaporated, offering every empty square (71 -> 87 moves at the initial
   position).

Each was found by measuring engine/GGP agreement and working backwards, a
feedback loop far too slow for a merge-by-union build.

**`tests/test_gdl_step_file_consistency.py`** now enforces two invariants:

- *No clause is a strict weakening of another with the same head.* A stale
  copy has strictly fewer body goals than its guarded sibling, which is
  exactly this relation. A later step legitimately ADDS clauses, so mere
  difference is not flagged — only strict weakening.
- *No goal is called at an arity nothing defines.* This catches the silent
  evaporation directly.

An earlier attempt required shared predicates to be declared *identically*
across files. That was wrong: `legal`, `next` and `lost` differ by design,
because each step adds rules to them.

**The guard immediately found two further bugs.** Steps 1-5 predate the
boulder, so their `next (cell ...)` arrival and persistence rules carry no
`(distinct ?piece boulder)`. Correct in isolation — but after the union
merge a boulder move also fires the generic piece-arrival rule, writing
`(cell ?tf ?tr <player> boulder)` and giving the NEUTRAL boulder a colour
and an owner alongside its correct neutral cell.

This never appeared in cross-validation, which compares only `legal` and
re-injects state at every position, so the `next` rules are barely
exercised. It would corrupt state in actual GGP self-play (MCTS over the
GDL). The guard is now backported to all five files, where it is trivially
true but keeps the copies identical.

### B4. The Tiny Endgame Rule is unreachable (open)

`tiny_endgame_active` is **derived by a rule**:

```
(<= (tiny_endgame_active) (pawnless) (non_king_non_boulder_count_at_most 6) (tiny_balanced))
```

but **queried as a fluent**:

```
(<= (lost ?player) (true (control ?player)) (true (tiny_endgame_active)) …)
```

`(true X)` reads the state; nothing ever writes `tiny_endgame_active` via a
`next` rule. The fluent is therefore unsatisfiable and the tiny-endgame loss
condition is **dead in the GGP**.

The converter now emits the fact when the engine's rule is active, which
makes the rule reachable from an injected state. The GDL-side inconsistency
— derived predicate versus fluent — is **still open** and needs a decision:
either add `next` rules that carry it, or change the query sites to use the
derived form.

---

## Part 3 — Stale audit entry corrected

`docs/gdl_audit_against_rulebook.md` lists as open:

> "Invulnerability blocks captures by all attackers — still only step 8's
> KING rule is invuln-aware."

No longer true. `integrated.gdl` carries `(not (true (invulnerable ?tf ?tr)))`
on the pawn, rook, knight, queen and boulder rules. Step 12 closed it.

---

## Result

All figures on one reproducible sample: **300 positions, 10 games x 30 plies,
seeded** (`SeededRandomPlayer`, seeds 1000+trial). Two independent runs of the
same build reproduce the same number exactly.

| Stage | Exact agreement | Engine-only bishop teleports |
|---|---|---|
| Baseline | **14%** | 202 |
| GGP converter + translator fixes (G1-G5) | **54.7%** | - |
| GDL B1 + B3 (boulder capture, bishop safety) | **61.7%** | 274 |
| GDL B5 (rook pivot blocking) | **62.7%** | 240 |
| GDL B6 (knight jump landing square) | **89.0%** | **0** |

Untranslatable engine turns: every manipulation and boulder first-move -> **0**.

B6 is the single largest fix, worth +26.3 points here and +10 on the gate's
shallower sample. It also eliminated the engine-only bishop class entirely,
which is the strongest available evidence that the residual there was a GDL
defect and the engine was correct throughout.

### Two measurement errors worth recording

Both were mine, not defects in the code, and both would be far more damaging
during the Phase 3 sweep than in a diagnostic.

**The gate was not actually seeded.** `_play_random_ply` accepted an `rng` and
never used it, because `players.RandomPlayer` calls the module-level
`random.choice`. Every per-trial `random.Random(42 + trial)` was decorative, and
the same build measured 64.0% and 58.7%. Fixed by passing a seeded player into
`AIController`, which accepts one; runs now reproduce exactly.

**`integrated.gdl` was rebuilt underneath running measurements, twice.** That
produced two spurious "nondeterminism" results (82/86/86 and 86/86/96) whose
spread was entirely explained by which build each run happened to load. The GGP
resolver is in fact deterministic: its legal-move digest is identical across
`PYTHONHASHSEED` values. Do not edit inputs while a measurement is in flight.

### On sample depth

Agreement degrades with depth, because later positions carry the transformed
queens, invulnerability and manipulation freezes where the remaining
divergences live. The same post-B6 build reads 96% on 4 games x 25 plies and
89.0% on 10 games x 30 plies. A shallow sample flatters this metric, so the
gate deliberately samples several games to depth and the headline figure is
always the deep one.

## Known remaining gaps

- **31 GGP-only bishop teleports** — the mirror of the old problem: the GDL is
  now slightly too permissive where it was once too strict. One candidate is
  the landing-square check in B6 treating the teleporting bishop's own origin
  square as occupied, when it is vacated by the move being evaluated. Not yet
  investigated.
- **13 GGP-only jump-captures** and **7 engine-only manipulations** — unclassified.
- **B4** above — the tiny-endgame fluent/derived inconsistency.
- `turn_number` is emitted as a bare integer, but the GDL's `succ` chain only
  reaches 10. Legality does not currently depend on `succ` beyond
  `and_white_and_turn_1`, so this is latent rather than active — but it is a
  landmine for any future turn-dependent rule.
- Repetition is enforced host-side in `GGPGame` (#160) rather than through
  the GDL's own state-history counting, so `state_repetition_count` and
  `next_state_hash` are deliberately never injected.
