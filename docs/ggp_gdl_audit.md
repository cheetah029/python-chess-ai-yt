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

All figures below are on the SAME deep sample — 300 positions across 10
games, 30 plies each — because sample depth materially changes the answer.

| Stage | Exact agreement on the legal-move set |
|---|---|
| Before | **14%** |
| After the GGP converter + translator fixes (G1–G4) | **54.7%** |
| After the GDL boulder-capture + bishop-safety fixes (B1, B3) | **73.0%** |
| After the central-intersection diagonal fix (B2) | **64.0%** |

Untranslatable engine turns went from "every manipulation and every boulder
first-move" to **zero**.

### On that last row, and on sample depth

Two things need stating plainly rather than being buried.

**B2 did not improve the deep-sample rate; it moved it from 73.0% to 64.0%.**
On a shallow sample (100 positions, 20 plies × 5 games) the same build
measures 87%. Both numbers are real; they are different samples. Agreement
**degrades with depth**, because later positions carry the transformed
queens, invulnerability and manipulation freezes where the remaining
divergences live.

The honest reading is that B2 is correct against the rulebook — the engine
blocks those diagonals and the GDL did not — but it is not a net win on
this metric, so something it interacts with is still wrong. It should not
be reported as an improvement, and the residual it exposes is open work,
not noise.

The general lesson is recorded in the gate test: a shallow sample flatters
this metric, so the gate deliberately samples several games to depth.

## Known remaining gaps

- **The divergence B2 exposed.** 73.0% → 64.0% on the deep sample means the
  central-intersection fix interacts with something still broken. Residual
  classes before B2 were engine-only bishop teleports, GGP-only knight moves
  and GGP-only jump-captures; these need re-classifying against the current
  build and fixing. This is the next piece of work.
- **B4** above — the tiny-endgame fluent/derived inconsistency.
- `turn_number` is emitted as a bare integer, but the GDL's `succ` chain only
  reaches 10. Legality does not currently depend on `succ` beyond
  `and_white_and_turn_1`, so this is latent rather than active — but it is a
  landmine for any future turn-dependent rule.
- Repetition is enforced host-side in `GGPGame` (#160) rather than through
  the GDL's own state-history counting, so `state_repetition_count` and
  `next_state_hash` are deliberately never injected.
