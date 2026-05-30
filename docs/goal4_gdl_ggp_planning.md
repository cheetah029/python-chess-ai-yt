# Goal 4 — GDL + GGP Planning (kickoff)

**Status:** kickoff, 2026-05-30.  
**Owner:** ag.  
**Prereqs:** Goals 1–3 (rules finalized; HvH/HvAI/CvC playable; AI training in
progress, currently at iter 64/75).

This document scopes Goal 4 of the project roadmap: formalizing the variant's
rules in a **Game Description Language (GDL)** and using/building a **General
Game Player (GGP)** to play them, aimed at an **ISEF submission in the ROBO
(Robotics and Intelligent Machines) category**.

The document is intentionally a *kickoff*, not a plan-of-record. It lays out
the landscape, names the hard parts, and proposes a small concrete first step
that can be executed without committing to a full GDL dialect or a specific
player implementation yet.

---

## 1. What we want

Two outcomes, in priority order:

1. **A correct, complete formal specification of the variant's rules in
   GDL** (or a GDL-adjacent formalism). The current rulebook
   (`RULEBOOK_v2.md`) is precise English prose. A GDL spec turns it into
   declarative logic that a general game player can ingest as input.

2. **A working General Game Player playing the variant from that spec.**
   "Working" here is graded:
   - **Baseline:** any existing GGP framework reads our GDL and produces
     legal play (no strength target yet).
   - **Comparison:** the GGP plays head-to-head against the Goal 3 trained
     network to give relative-strength data.
   - **Stretch:** the GGP's algorithmic approach scales, *unchanged*, to a
     proposed rule modification — demonstrating the "no retraining required"
     advantage that motivates Goal 4 in the first place.

The deeper research point — the one worth showing at ISEF — is that
**under rule churn, a GGP-style approach has a fundamentally different cost
curve from a trained NN**: rule changes are O(spec edit) for the GGP and
O(re-train) for the NN. This variant has churned rules many times during
design and is a faithful stress-test of that claim.

---

## 2. GDL landscape (background)

Two main dialects in the literature:

- **GDL-I (Stanford GDL, ~2005):** first-order Datalog/Prolog-flavored.
  Perfect-information, deterministic, synchronous turns. Used at the
  Stanford GGP competitions (2005 onward). Best-known engines: Cadia
  Player, FluxPlayer, TurboTurtle, Sancho. Reasoner toolkits: GGP-Base
  (Java), [Stanford GGP server](http://ggp.stanford.edu/), Palamedes.
- **GDL-II (~2010):** adds imperfect information (random events, hidden
  state). Strictly more expressive; tooling thinner.

Our variant is **perfect-information + deterministic** (boulder cooldown
and no-return are public state; no dice; no fog). Therefore **GDL-I is
sufficient** — start there.

Adjacent formalisms worth knowing about:
- **Toss / RBG (Regular Boardgames):** more concise than GDL for board
  games. Less mature ecosystem but more readable specs.
- **Zillions of Games (ZRF):** commercial, retired engine. Mentioned only
  because some prior chess-variant work used it; not a serious option for
  research.
- **Ludii:** the modern academic successor — a board-game–specific DSL
  with a strong solver and AI baseline. **Worth serious consideration** as
  an alternative target.

---

## 3. Why this variant is a good GGP benchmark

Most published GDL chess specs cover standard chess (with various holes
around castling/en-passant). This variant offers genuinely novel
mechanics that exercise corners of GDL most descriptions don't reach:

- **Per-piece state across turns:** manipulation freeze, knight
  invulnerability, bishop reactive-armed flag. GDL handles this naturally
  via per-piece facts in the next state, but few existing specs do it at
  this density. Good test of expressiveness.
- **Source-vs-destination reactive captures:** the knight's jump-capture
  (destination-based, triggered by an enemy landing at chebyshev-1)
  and the bishop's reactive capture (source-based, triggered by an enemy
  *leaving* the bishop's diagonal LoS). Both depend on
  *immediately-preceding-turn* facts — exactly the kind of cross-turn
  predicate that distinguishes a serious GDL from a state-only one.
- **Multi-step composite moves:** the rook moves two segments in one turn
  (1-step + 90° sweep); the knight may take a jump-capture sub-decision
  after the spatial leap. In GDL these are typically modeled as a single
  composite legal move enumerated up-front (the design we took in our
  Python `Turn` object), but the per-side enumeration is non-trivial.
- **Neutral piece with memory:** the boulder is owned by neither side,
  carries cooldown + no-return state, and has asymmetric capture rules
  (captures pawns only; only king captures it). Most GDL chess specs have
  no neutral piece at all.
- **Three loss conditions:** royal capture (both), no-legal-moves, and
  repetition-3, plus the tiny endgame's distance-3 limit. The repetition
  rule requires tracking *position counts* across the entire game —
  expressible in GDL but verbose, and our state-hash design (positional +
  flag-derived, see `project_state_hash_design.md`) is a non-trivial
  predicate to specify.
- **Conditional state inclusion:** the no-return-memory square and the
  moved-last-turn / reactive-armed flags only enter the state when they'd
  actually affect legality (see RULEBOOK_v2.md "Repetition Rule"). This
  is a subtle but real source of correctness work — the GDL must match
  the Python engine's hashing decisions exactly, or repetition counts
  diverge.

If we can get a complete, *correct* GDL spec for this variant, it's a
genuinely novel benchmark contribution.

---

## 4. The hard parts (formalization-grade)

Ranked by expected difficulty in GDL-I:

1. **Bishop reactive capture (source-based).** The "legal move" predicate
   must consult the *previous* turn's *source square* of the moving
   enemy. GDL handles this via a `did(?player, ?move)` literal in the
   prior state, but the predicate becomes textually heavy.
2. **Repetition rule state hashing.** The state-hash specification
   (positional + conditional per-piece flags + conditional boulder
   no-return) is precise in our Python code. Translating exactly is
   labor-intensive.
3. **Tiny endgame rule (cancel-queens + 1-to-2 valuation).** Modular
   arithmetic, min, balance condition. GDL-I can do this but it's verbose.
4. **Knight invulnerability with the "adjacent-enemy-other-than-jumped"
   condition.** Multi-condition predicate; easy to get wrong.
5. **Rook 2-segment move enumeration.** Direct in GDL — enumerate all
   (segment-1, segment-2) tuples; just lots of legal-move clauses.
6. **Manipulation Restriction 1 & 2.** Restriction 2 is the trickier one
   (must look back to the target's last *spatial* move, not just last
   turn).
7. **Multi-form queen (base / rook / bishop / knight).** State that
   carries the current form; transformation as a state-only action.

None of these are *impossible* in GDL-I — they're textually substantial
but mechanically straightforward.

---

## 5. Proposed first concrete step

Don't try to write the whole GDL spec on day one. Instead, **build a
small, isolated GDL fragment for a stripped-down variant**, verify it
end-to-end against an existing GGP reasoner, and iterate.

Proposed first-fragment scope:

- **8×8 board, kings + base-form queens only.** No pawns, no
  rook/bishop/knight/boulder, no manipulation, no transformation.
- **Only the win condition:** capture both royals.
- **No tiny endgame rule, no repetition rule** (yet).
- One side to move at a time, standard alternation.

This fragment lets us:
- Pick a GDL toolchain (GGP-Base / Palamedes / Ludii) and verify our
  install with a *known-trivial* spec.
- Get fluent with the syntax + reasoner before adding any of the hard
  parts (§4).
- Set up the comparison harness (GGP-side play, parsing legal moves,
  driving full games) that will be reused for every later fragment.

Then layer one mechanic at a time, in increasing-difficulty order:

| step | adds                                          | notes                              |
|------|-----------------------------------------------|------------------------------------|
| 1    | kings + base queens only                      | toolchain bootstrap                |
| 2    | + pawns (incl. capture asymmetry)             | first cross-piece interaction      |
| 3    | + rook (2-segment)                            | first multi-step move              |
| 4    | + knight (radius-2, no jump-capture yet)      | move enumeration                   |
| 5    | + bishop (teleport, no reactive yet)          | teleport-safety predicate          |
| 6    | + boulder (with cooldown + no-return)         | first neutral-piece state          |
| 7    | + queen actions (manipulation, transformation)| introduces cross-turn restrictions |
| 8    | + knight jump-capture & invuln                | first reactive capture             |
| 9    | + bishop reactive capture                     | source-based predicate (hardest)   |
| 10   | + repetition rule                             | game-level position counting       |
| 11   | + tiny endgame rule                           | distance counting + balance check  |

Each step ends with the same checkpoint: parse the spec in a GGP
reasoner, generate legal moves for a small handcrafted position, **compare
the set against the Python engine's `get_all_legal_turns()` output for
the same position.** Equality on a curated set of test positions is the
quality gate for moving to the next step.

---

## 6. Open questions for the user

These should be decided before any GDL writing begins:

1. **Dialect / toolchain.** GDL-I (Stanford, classic) vs Ludii (modern
   academic, board-game–specific DSL with a stronger solver baseline).
   GDL-I is the more recognizable ISEF "GGP" framing; Ludii is the more
   productive engineering choice. **Lean: GDL-I for the ISEF positioning,
   but evaluate Ludii in parallel as a fallback / cross-check.**
2. **Strength target for the GGP.** Baseline-legal-play (the easiest
   goal) vs head-to-head competitive vs the trained Goal-3 network.
3. **Scope of the ISEF submission.** Is the contribution (a) the GDL spec
   itself, (b) the GGP-vs-NN comparison, or (c) the rule-churn cost-curve
   experiment? Probably (a) + (c); (b) is supporting evidence.
4. **Timeline.** When is the ISEF deadline? Drives whether we go for the
   full 11-step rollout or stop at step 6 (a respectable subset).
5. **Reuse of the existing Python engine as ground truth.** Do we treat
   `src/engine.py` + `src/board.py` as the spec of last resort, or do we
   discover places where the rulebook and the engine disagree (a
   plausible side-effect)? The latter is real research value: a complete
   GDL spec will be a *formal verification* of the engine.

---

## 7. What's NOT in scope for Goal 4 (yet)

- **GDL-II** (imperfect information). Not needed.
- **Real-time / continuous-time rules.** This is a discrete turn-based
  game.
- **Learning inside the GGP.** Starting with classical reasoners
  (Monte-Carlo Tree Search, propositional networks). NN-augmented GGP is
  a stretch follow-on.
- **Rebuilding the existing engine.** GDL is *additive* — the Python
  engine remains the canonical game runtime for the human-vs-AI UI and
  for training.

---

## 8. Where this fits in the broader project

- **Goal 1 (rules finalized):** prerequisite met. We can formalize
  without fearing mid-stream rule changes.
- **Goal 2 (HvH / HvAI / CvC modes):** independent. The GGP will
  eventually plug into the CvC mode as another "player type" alongside
  random / easy / medium / hard.
- **Goal 3 (trained NN, in progress):** the GGP-vs-NN comparison is the
  capstone experiment. We can't start it until both the GDL is correct
  enough to play AND the network is trained enough to be a meaningful
  opponent (iter ~100 is the working target).
- **Goal 4 (this doc):** the long-horizon research direction. The
  rule-churn cost-curve story is the part that's hardest to find anywhere
  else and the part most likely to land at ISEF.

---

## 9. Immediate next action

When the user picks a dialect (§6 Q1), step 1 of §5 ("kings + base
queens only") can be drafted in a few hundred lines of GDL. Until then,
this doc is the kickoff record and the rulebook stays the source of truth.

---

## UPDATE — 2026-05-30: Step 1 landed (default dialect: GDL-I)

The user opted to "get started" on Goal 4 without explicitly answering
the open questions in §6, so the following defaults were taken; they
remain reversible:

- **Dialect: GDL-I (Stanford).** Lean from §6 Q1 carried over —
  matches the recognised "GGP" framing in ISEF / academic context.
  Ludii remains the fallback if GDL-I tooling becomes a blocker.
- **Step 1 written:** `docs/gdl/step1_kings_queens.gdl` — kings +
  base-form royal queens only, both starting at rulebook-correct
  squares (W K g1, W Q b1; B K b8, B Q g8 — rotational-symmetric
  setup), king-like 1-square move for both pieces, plain captures,
  win = capture both opponent royals.
- **Tests:** `tests/test_gdl_step1.py` — small S-expression parser
  + 8 structural invariants (parens balanced; both roles declared;
  white moves first; correct starting squares for K and Q; no extra
  piece types; at least one `legal` rule per side; `terminal` + `goal`
  rules exist; only known GDL-I top-level keywords used). These
  catch the kinds of bugs that come from hand-editing a GDL file
  (typos, missing role, wrong square). They do NOT verify legal-move
  equivalence with the Python engine — that's the gating criterion
  for step 2 and is implemented once a GDL reasoner is wired in.

**Reasoner integration (still NOT done):** the structural test is a
cheap sanity check; the real correctness gate is "parse this file in
a GGP reasoner (e.g. GGP-Base, Palamedes), enumerate legal moves
from a curated set of test positions, assert equality with
`engine.get_all_legal_turns()`." This requires installing a
reasoner — out of scope for the kickoff commit.

Choice of `(distinct ?x ?y)` semantics in next clauses: GDL-I's
standard convention is `(distinct ?x ?y)` as a built-in for
inequality. Used inline in the frame-axiom clause. If the chosen
reasoner uses `(not (= ?x ?y))` instead, that's a 5-minute
substitution.

### What step 2 will need

1. Add pawns to `init`. Setup: white pawns rank 2, black pawns rank 7.
2. Pawn move rules: forward/left/right 1 square (NOT backward) —
   the v2 sideways-move-but-not-capture asymmetry is the first
   non-trivial difference from standard chess. Adds `pawn_forward`
   and `pawn_capture_dir` helpers per colour.
3. Promotion on reaching the last rank: choose a queen form. For step
   2 we likely just promote to base queen (matching step 1's only
   non-king piece) — the multi-form queen + transformation comes in
   step 7.
4. Extend `lost` if needed: pawns don't count toward royal-capture
   victory, so `(lost ?player)` is unchanged. But pawn captures DO
   need a `next` clause that removes the captured pawn — the frame
   axiom handles this implicitly (the to-cell is replaced by the
   moving piece), so no change needed.

Estimated size: 60–100 lines additional GDL; ~10 additional
structural-test cases.

---

## UPDATE — 2026-05-30 (later): Step 2 landed; GDL versions clarified

### Step 2 GDL fragment shipped
`docs/gdl/step2_kings_queens_pawns.gdl` — ~150 lines including
comments. Adds:
- 16 pawns (rank 2 white, rank 7 black) to the `init` block.
- `pawn_forward` helper per colour: white = rank-increasing
  (1→2 ... 7→8), black = rank-decreasing (8→7 ... 2→1).
- Pawn forward MOVE (destination empty), pawn SIDEWAYS move
  (destination empty, adjacent file, same rank — the v2-unique
  "move-but-not-capture" sideways), pawn forward CAPTURE
  (destination enemy), pawn diagonal CAPTURES (forward-left,
  forward-right).
- `last_rank` helper + a `next` rule that turns a pawn arriving on
  the last rank into a base-form queen (multi-form / transformation
  deferred to step 7).
- Generic "moving piece arrives" rule branches on `(or (distinct
  ?piece pawn) (not (last_rank ?mover ?tr)))` to suppress itself in
  the promotion case so a pawn doesn't both promote AND remain a
  pawn at the destination.

Estimate was 60-100 lines; actual was closer to 100 lines of new
content plus duplicated step-1 helpers for self-containedness.

Tests: `tests/test_gdl_step2.py`, 13 structural assertions including
re-checks of step-1 invariants. All pass.

### GDL dialect choice — clarified (in response to user question)

There are three published GDL dialects:

- **GDL-I (Stanford, ~2005)** — perfect information, deterministic,
  finite, synchronous turns. The original Stanford GGP language;
  what most academic GGP work means by "GDL." Mature tooling
  (GGP-Base in Java, Palamedes, etc.). **What our fragments use.**
- **GDL-II (~2010, Thielscher)** — adds imperfect information: a
  built-in `random` role for chance events and a `sees` predicate
  for hidden information (each player sees only what they're told).
  Strictly more expressive. Tooling significantly thinner.
- **GDL-III (~2016, Thielscher)** — adds *epistemic* reasoning: a
  `knows` predicate so players can reason about what *other*
  players know about each others' knowledge. Strictly more
  expressive than GDL-II. Very thin tooling, mostly research
  prototypes.

**For this variant: GDL-I is correct.** Our game is fully observable
(every player sees the entire board, the boulder's cooldown, and
every per-piece flag), fully deterministic (no dice / shuffled deck),
and turn-based. GDL-II's hidden-info machinery and GDL-III's
epistemic predicates would add expressive power we genuinely don't
need, at the cost of significantly worse tooling. We'd only revisit
if a future variant adds fog-of-war or simultaneous moves.

### Still pending (next Goal 4 session)
- Install a GDL-I reasoner (lean: GGP-Base Java toolkit, or
  Palamedes if a Python-friendly path is available).
- Wire the legal-move-equivalence harness: parse step1/step2/step3
  in the reasoner, enumerate legal moves from curated positions,
  assert equality vs `engine.get_all_legal_turns()`. This is the
  gating criterion to advance further.
- Step 4 (knight radius-2 movement — without jump-capture or
  invuln yet).

---

## UPDATE — 2026-05-30 (later): Step 3 landed (rook 2-segment)

`docs/gdl/step3_add_rook.gdl` — ~280 lines. The first multi-segment
move in the fragment series. Key elements:

- **Rooks added to init**: White rooks at c1, f1; black rooks at
  c8, f8 — rotational-symmetric per RULEBOOK_v2.md back rank
  (Bishop-Queen-Rook-Knight-Knight-Rook-King-Bishop).
- **`rook_step` predicate** with a direction tag (n/s/e/w). Defined
  by enumerating every legal 1-square orthogonal step on the 8×8
  board. The direction tag drives segment 2's perpendicularity
  requirement.
- **`perpendicular` predicate**: (n,e), (n,w), (s,e), (s,w), (e,n),
  (e,s), (w,n), (w,s).
- **`sweep_path` predicate** (recursive): walks the perpendicular
  cells from segment-1's endpoint to segment-2's destination,
  asserting each intermediate square is empty. This encodes the
  rook's no-jumping constraint.
- **Two `legal` rules for rook moves**:
  1. Segment-2 length zero — rook stops right after segment 1.
  2. Segment-2 length ≥ 1 — perpendicular sweep with `sweep_path`.
- **State transitions** unchanged from step 2: frame axiom +
  "moving piece arrives" + control-passes. The rook physically goes
  origin → final; the intermediate square is conceptual only and
  doesn't need its own next-state clause.

Tests: `tests/test_gdl_step3.py` — 13 structural assertions
(step-2 invariants still hold + rook starting squares correct +
all kings/queens/pawns still correct + no extra piece types beyond
king/queen/pawn/rook + at least one legal rule mentions 'rook' +
'segment'/'rook_step'/etc. reference + a no-jumping construct).
All pass.

This brings the fragment series to 3 of 11 steps. Reasoner
integration (the actual correctness gate) is still ahead.

---

## UPDATE — 2026-05-30 (later still): Step 4 landed (knight radius-2)

`docs/gdl/step4_add_knight.gdl` — ~330 lines (most of it carried-
over helpers from steps 1-3; the knight-specific content is the
last ~50 lines). Adds the v2 knight's RADIUS-2 MOVEMENT only; the
reactive jump-capture and post-non-capture-jump invulnerability are
deferred to step 8.

Key constructs:

- `file_delta_1`, `file_delta_2`, `rank_delta_1`, `rank_delta_2`
  helpers: enumerate every file/rank pair at distance 1 or 2 on
  the 8-file/8-rank board. Symmetric (both directions).
- `knight_step (?ff ?fr ?tf ?tr)`: the 16 chebyshev-≤2-but-not-1
  destinations, split into three families:
    * 4 squares: 2-orthogonal (file_delta_2 + same rank OR same
      file + rank_delta_2)
    * 4 squares: 2-diagonal (file_delta_2 + rank_delta_2)
    * 8 squares: L-shape (file_delta_2 + rank_delta_1 OR
      file_delta_1 + rank_delta_2)
- One `legal` rule for the knight: any `knight_step` destination
  that isn't friend-occupied. No blocking constraint (knight jumps).

4 knights placed at rulebook-correct squares (d1, e1 / d8, e8).

Tests: `tests/test_gdl_step4.py` (13 structural assertions). All
pass.

### What step 5 will need (bishop teleport — NO reactive capture yet)

Step 5 will add the bishop. From RULEBOOK_v2.md:

  Move: teleport to any empty square that is NOT currently moveable
  to or capturable by any enemy piece. Enemy bishops, queens-as-
  bishop, and the boulder are EXCLUDED from this safety check.

For step 5 (no reactive capture yet), we encode just the teleport-
safety predicate. The hardest part is the destination-vs-source
distinction (the "exclude enemy bishops" exception): the safety
check considers enemy reach via spatial move OR direct capture, but
NOT via the bishop's own reactive-capture mechanism (which depends
on where the moving piece *came from*, not on where it goes).

In step 5 (no bishops doing reactive capture yet), the destination-
vs-source distinction doesn't bite, so we can encode a clean
"can_enemy_reach_directly" predicate without subtle exceptions.
The exception lands in step 9 along with bishop reactive capture.

Estimate: ~80 additional lines (4 bishops + teleport-safety
predicate + diagonal-LoS helpers carrying over from the rook step
work, partially).

### Fragment series progress
- Step 1 (kings + queens) — done
- Step 2 (+ pawns + promotion) — done
- Step 3 (+ rooks 2-segment) — done
- Step 4 (+ knights radius-2) — done
- Step 5 (+ bishops teleport) — DONE (2026-05-30)
- Step 6 (+ boulder cooldown + no-return) — NEXT
- Step 7 (+ queen actions: manipulation + transformation) — pending
- Step 8 (+ knight jump-capture + invuln) — pending
- Step 9 (+ bishop reactive capture) — pending
- Step 10 (+ repetition rule) — pending
- Step 11 (+ tiny endgame rule) — pending

Plus the always-pending: REASONER INTEGRATION. The structural tests
catch hand-edit bugs; legal-move-set equivalence against
`engine.get_all_legal_turns()` requires installing a GDL-I reasoner
(GGP-Base / Palamedes). That gating step is overdue and should
land before step 7 (the queen actions are where subtle semantics
will be easy to get wrong without machine verification).

---

## UPDATE — 2026-05-30 (very late): Step 5 landed (bishop teleport)

`docs/gdl/step5_add_bishop.gdl` — ~420 lines. Adds bishop teleport
movement; reactive capture is deferred to step 9.

Key new constructs:

- **4 bishops at rulebook-correct corners** (a1, h1 / a8, h8).
- **`can_capture_to(?attacker ?piece ?ff ?fr ?tf ?tr)`** — per-piece
  predicate: can this piece capture at (?tf, ?tr) ignoring whose
  turn it is? Used by the bishop's enemy-reach check. Defined for
  pawn, king, queen (base form), rook (2-segment), knight (radius-2).
- **`jump_capturable_by_knight(?attacker ?tf ?tr)`** — true if an
  enemy knight is at chebyshev-1 of (?tf, ?tr). Per RULEBOOK_v2.md:
  "capturable squares include squares reachable by the knight's
  jump capture" — destination-based, so we include it.
- **`can_move_to_only(?attacker pawn ?ff ?fr ?tf ?fr)`** — the
  v2-unique pawn sideways move. The bishop's safety check is
  "moved-to OR captured-by", and pawn sideways is the only case
  where a piece can move to a square it cannot capture at. Encoded
  separately so the bishop refuses pawn-sideways squares.
- **`enemy_can_reach(?mover ?tf ?tr)`** — the bishop's safety
  predicate. True iff any non-bishop enemy piece can capture at OR
  move to (?tf, ?tr), OR an enemy knight at chebyshev-1. **ENEMY
  BISHOPS ARE EXCLUDED** — per the destination-vs-source rationale
  in RULEBOOK_v2_elaborated.md (bishop reactive capture depends on
  where the moving piece *came from*, not on the destination, so
  it isn't a destination-reach threat).
- **Bishop teleport rule**: enumerate every (?tf, ?tr) cell via
  `file` / `rank` predicates, ensure it's empty AND not
  `enemy_can_reach`, AND not the bishop's own square.

The exclusion of enemy bishops is correctly set up here in step 5
even though it has no mechanical effect yet (bishops don't have
reactive capture until step 9). When step 9 lands the exclusion is
already in place — no refactor needed.

Tests: `tests/test_gdl_step5.py` (13 structural assertions). All
pass.

This brings the fragment series to **5 of 11** steps. Next step:
boulder (cooldown + no-return memory + neutral-piece blocking
semantics). The boulder is the first NEUTRAL piece in GDL — a
non-trivial new wrinkle (most GDL-I games have only player-owned
pieces).

---

## UPDATE — 2026-05-30 (very-very late): Step 6 landed (boulder)

`docs/gdl/step6_add_boulder.gdl` (~330 lines including comments).
Adds the BOULDER — the first neutral piece in the fragment series.

Key new constructs:
- `(boulder_at intersection)` init fact — boulder begins on the
  central intersection (not on any single square).
- `(boulder_first_move)` flag — TRUE until the boulder's first move.
- `(boulder_cooldown N)` counter — 0 = movable, 2 set after a move,
  decrements each turn (own + opponent).
- `(boulder_last ?f ?r)` memory — the boulder's previous square;
  no-return restriction blocks non-capture re-entry.
- `(turn_number ?n)` counter — supports the "white may not move
  boulder on turn 1" guard.
- `boulder_first_dest` predicate — the 4 central squares (d4, d5,
  e4, e5) the boulder may first move to from the intersection.
- 4 legal-rule families for boulder moves:
  * FIRST move from intersection to a central square (subject to
    cooldown + first_move flag + turn-1 guard).
  * SUBSEQUENT non-capture king-step to an empty non-last square.
  * SUBSEQUENT capture-pawn move (last-square exception covered
    by the capture branch).
- State transitions: boulder arrives at destination cell, origin
  cleared, cooldown set to 2 then decremented, last_square set,
  first_move flag cleared.

Boulder captures pawns of EITHER colour — encoded with no colour
check on the pawn (matches the rulebook clarification).

Tests: `tests/test_gdl_step6.py` (13 structural assertions). All
pass.

This brings the fragment series to **6 of 11** steps. Next step:
queen actions (manipulation + transformation) — step 7 is the
hardest mechanical step in the variant because manipulation has
cross-turn constraints (R1: manipulated piece may not make a
spatial move on its next own turn; R2: queen may not manipulate a
piece that made a spatial move on the immediately preceding turn).
Plus the multi-form queen (base / rook / bishop / knight) with
transformation as a non-spatial action.
