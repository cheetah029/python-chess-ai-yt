# GDL → RULEBOOK_v2 Audit (2026-05-31)

This document cross-checks each rule from `RULEBOOK_v2.md` against
its encoding in the 11-step GDL fragment series + `integrated.gdl`.
**Status flags**:

- ✅ **Encoded correctly** — the GDL faithfully matches the rulebook
- ⚠️ **Encoded with a known limitation** — the GDL captures the
  spirit but a documented simplification or sketch is in place
- ❌ **Bug or gap** — the GDL deviates from the rulebook in a way
  that affects legal-move enumeration or win-condition determination

Audit performed end-to-end via the GGP (steps 1-7 fully executed,
8-11 smoke-checked + structural-only). Several bugs surfaced during
PRs #103-#106; this doc records all current known status.

---

## 1. Objective & win/loss conditions

| Rule | GDL location | Status |
|---|---|---|
| Win = capture both opponent royals (king + ROYAL queen) | step 7+ uses `queen_royal` flag, `lost(player) :- dead(player, king), royal_queen_dead(player)` | ✅ |
| Promoted queens DO NOT count toward victory | step 7's `queen_royal` is only set in `init` for b1/g8 + persists via `(next (queen_royal …))` only while the royal queen lives | ✅ |
| Loss: no legal turn available at start of turn | partially in step 10's `no_legal_after_repetition_filter` — but the rulebook's broader "No Legal Moves Loss" applies to ALL situations, not just repetition-filtered | ⚠️ Encoded only in the repetition-loss path; a unified `no-legal-turn-loss` for all reasons isn't present |
| Loss: repetition 3rd time | step 10 sketches `state_repetition_count` + `would_repeat_third_time` filter | ⚠️ Hash representation deferred to reasoner integration |
| Loss: tiny endgame non-capture distance > 3 | step 11 sketches `tiny_endgame_limit_exceeded` | ⚠️ Cancel-queens balance valuation sketched |

---

## 2. Board & setup

| Rule | GDL location | Status |
|---|---|---|
| 8×8 board, rotational-symmetric setup | All steps' `init` clauses use rulebook-correct squares per piece (B-Q-R-N-N-R-K-B back rank) | ✅ |
| White moves first | All steps: `(init (control white))` | ✅ |
| Boulder starts on central intersection | step 6+: `(init (boulder_at intersection))` | ✅ |

---

## 3. Pieces

### Pawn (step 2+)

| Rule | GDL location | Status |
|---|---|---|
| Move: forward + sideways (NOT backward) | step 2: `pawn_forward` (one direction per colour) + sideways via `file_adj` | ✅ |
| Capture: forward + diagonal forward | step 2: pawn capture rules | ✅ |
| Promotion to non-royal queen | step 2: `(<= (next (cell ?tf ?tr ?mover queen)) (does ?mover (move pawn ?ff ?fr ?tf ?tr)) (last_rank ?mover ?tr))` | ⚠️ Always to BASE queen; the rulebook says the player chooses the form (base/rook/bishop/knight if captured) |
| Promoted queens don't get `queen_royal` marker | step 7+: promotion next rule doesn't set queen_royal | ✅ Correct (royal flag is for the b1/g8 originals only) |

### King (all steps)

| Rule | GDL location | Status |
|---|---|---|
| Move: 1 square in any direction | All steps: `king_step ?ff ?fr ?tf ?tr` | ✅ |
| **Capture friendlies** | NOT encoded — the legal rule for king has `(not (friend_at ?player ?tf ?tr))` which BLOCKS friendly capture | ❌ **GAP — the v2 king's friendly-capture ability isn't encoded; legal-move enumeration is missing some moves** |
| **Capture the boulder** | NOT encoded — boulder is on a cell with `none` colour; `friend_at` check excludes it but no positive rule enables boulder capture by king | ❌ **GAP — king→boulder capture missing** |
| Invuln does NOT override king capture | NOT encoded — king rule doesn't consult `(true (invulnerable ?tf ?tr))` | ❌ **GAP — king can still capture invuln pieces in current GDL; should be blocked** |

### Queen (step 7+)

| Rule | GDL location | Status |
|---|---|---|
| Base form: king-step move | step 7: queen-base legal rule = king-step + friend-at filter | ✅ (modulo king's friendly-capture issue — queens correctly CAN'T capture friendlies) |
| Multi-form: rook / bishop / knight | step 7: queen_form facts + `queen_form ?ff ?fr rook → rook_step rule`, queen-as-knight rule | ⚠️ Queen-as-bishop teleport sketched in comment only — not encoded |
| Transformation action | step 7: `(<= (legal ?p (transform ?f ?r ?new_form)) … (allowed_form ?p ?new_form))` | ✅ |
| Transformation requires captured friendly piece | `(<= (allowed_form ?owner rook) (true (captured_friendly ?owner rook)))` etc. | ⚠️ The `captured_friendly` next-clause is NOT encoded — flag never gets set, so transformations to rook/bishop/knight never actually unlock |
| Return to base always allowed | `(<= (allowed_form ?owner base))` always succeeds | ✅ |
| Distinct from base form | `(distinct ?new_form base)` in transform rule | ✅ (after the 2026-05-31 resolver fix for `distinct` on unbound operands) |
| Manipulation: queen moves enemy piece within LoS | step 7: `queen_los` (orthogonal + diagonal) + manipulate rules per piece type | ⚠️ Encoded for pawn / king / rook / knight; bishop manipulation sketched in comment only |
| R1: manipulated piece can't make spatial move next own turn | step 7: `manipulation_freeze` flag set in `next`; legal-rule guards check it | ⚠️ Per-piece freeze-clear timing is approximate (the rulebook says "next OWN turn" but the GDL clears in the next state) |
| R2: queen can't manipulate piece that moved last turn | step 7: `(not (true (spatial_move_last_turn ?ef ?er)))` | ✅ |
| R3: queen can't manipulate king / boulder / enemy base-queen | step 7: `manipulable_target` rule excludes king, boulder, and `target_is_base_queen` | ✅ |

### Rook (step 3+)

| Rule | GDL location | Status |
|---|---|---|
| 2-segment move (1 orthogonal + 90° + N in new direction) | step 3: 2 legal rules (length-0 + length-≥1 via sweep_path) | ✅ End-to-end validated via GGP step 3 test |
| Can't jump over pieces | `(not (occupied ?mf ?mr))` inside sweep_path recursive case | ✅ |
| Stop on / capture first enemy | length-≥1 rule has `(not (friend_at ?player ?tf ?tr))` at destination | ✅ |

### Bishop (step 5+)

| Rule | GDL location | Status |
|---|---|---|
| Teleport to safe empty square | step 5: enumerate via `(file ?tf) (rank ?tr)` + `(empty ?tf ?tr) + (not (enemy_can_reach ?player ?tf ?tr))` | ✅ (after 2026-05-31 step-5 scaffold-rule fix — pre-fix, ANY occupied cell was a legal destination) |
| Enemy bishops EXCLUDED from safety check | step 5: `enemy_can_reach` uses `(distinct ?piece bishop)` to skip enemy bishops | ✅ |
| Knight jump-capture squares INCLUDED in capturable set | step 5: `jump_capturable_by_knight` predicate, queried inside enemy_can_reach | ✅ |
| Reactive capture: enemy left bishop's diagonal LoS → bishop may capture next turn | step 9: `reactive_armed ?bf ?br ?dest_f ?dest_r` + `reactive_capture` legal rule | ⚠️ Pairing of `spatial_move_origin` ↔ `spatial_move_last_turn` assumes single-move turns; may not handle multi-event turns correctly |
| Reactive capture bypasses teleport-safety | step 9: reactive_capture rule has NO `enemy_can_reach` guard | ✅ |
| Boulder excluded from safety check | step 5's `enemy_can_reach` doesn't check the boulder | ⚠️ Boulder isn't enumerated as a `(true (cell ?ef ?er ?atk ?piece))` enemy fact since color = 'none' ≠ atk, so it's implicitly excluded — but this is happenstance, not explicit |

### Knight (step 4+)

| Rule | GDL location | Status |
|---|---|---|
| Radius-2 (16-square) move pattern | step 4: file_delta_1/2 + rank_delta_1/2 + knight_step (3 families) | ✅ End-to-end validated via GGP step 4 test |
| Can jump over pieces | No path-clear check in knight_step | ✅ (legal rule only checks destination) |
| Standard capture | knight legal rule allows destination with non-friend | ✅ |
| Jumped square per move family | step 8: `knight_jumped_square` per family with between_file/rank | ✅ |
| Jump-capture: enemy moved onto jumped square last turn | step 8: `(legal ?p (jump_capture …)) … (true (spatial_move_last_turn ?jf ?jr))` | ⚠️ Smoke-tested only; specific position tests deferred |
| Invuln: non-capture jump over friend or boulder, with adjacent non-jumped enemy | step 8: `next (invulnerable ?tf ?tr)` set with the trigger conditions | ⚠️ Smoke-tested only |
| Invuln blocks all captures including king | step 8: example invuln-aware king move rule | ⚠️ Only the king is patched as an example; other capturers (queen, rook, knight, pawn, bishop) NOT yet invuln-aware in step 8 |

### Boulder (step 6+)

| Rule | GDL location | Status |
|---|---|---|
| Neutral piece | All cell facts for boulder use color `none` | ✅ |
| First move: to one of d4/d5/e4/e5 | step 6: `boulder_first_dest` + first-move legal rule | ✅ |
| White can't move boulder on turn 1 | step 6: `(not (and_white_and_turn_1 ?player))` guard | ✅ End-to-end validated via GGP step 6 test |
| Subsequent: king-step | step 6: subsequent legal rule uses `king_step` | ✅ |
| Captures pawns only (either colour) | step 6: capture rule uses `(pawn_at ?tf ?tr)` (no colour check) | ✅ |
| Only king can capture boulder | NOT encoded — see King section above. King rule doesn't have an explicit boulder-capture branch | ❌ **GAP** |
| Cooldown: both players make 1 turn between boulder moves | step 6: `(boulder_cooldown N)` set to 2 after move, decrements each turn | ✅ |
| No-return memory: can't return via non-capture | step 6: subsequent non-capture legal rule has `(not (true (boulder_last ?tf ?tr)))` | ✅ |
| Capture exception: can return to last_square if pawn there | step 6: capture-return rule doesn't check boulder_last | ✅ |
| Boulder persists on intersection while not moved | step 6: persistence rule added 2026-05-31 (was a bug) | ✅ |
| On intersection, blocks diagonals not files/ranks | NOT encoded — this affects bishop teleport LoS through the intersection | ❌ **GAP** |
| Treated as friendly by both sides for most purposes | Implicitly via various exclusions, not unified | ⚠️ |

---

## 4. Repetition rule (step 10+)

| Rule | GDL location | Status |
|---|---|---|
| Strict 3rd-occurrence blocking | step 10: `(would_repeat_third_time ?h) :- (state_repetition_count ?h 2)` | ⚠️ Sketched |
| State hash includes per-piece flags | step 10's hash representation is a placeholder | ⚠️ Full encoding deferred to reasoner integration |
| Loss when every legal turn would 3rd-repeat | step 10: `no_legal_after_repetition_filter` + extended `lost` | ⚠️ Sketched |

---

## 5. Tiny endgame rule (step 11)

| Rule | GDL location | Status |
|---|---|---|
| Activation: pawnless + ≤6 non-king-non-boulder + balanced | step 11: `tiny_endgame_active = pawnless + non_king_non_boulder_count_at_most_6 + tiny_balanced` | ⚠️ The 7-piece-existence count is a placeholder; cancel-queens balance valuation is sketched |
| Distance counts per royal-distance value | step 11: `distance_count ?d ?n` with activation + non-capture-increment + capture-reset rules | ⚠️ `closest_royal_pair_distance` min-aggregation sketched |
| Limit: non-capture move pushing count > 3 is illegal | step 11: `legal_after_tiny_filter` filter | ⚠️ Sketched |
| Loss when every legal turn is filtered | step 11: extended `lost` clause | ⚠️ Sketched |

---

## Summary of known gaps requiring follow-up

### Update 2026-05-31 (PR #109): partial fixes landed

Re-verification via the GGP after PRs #100-#108 shows:
- ✅ **King friendly-capture** — step 7's split king/queen rules ALREADY enable king-friendly-capture (the audit's original concern was wrong; the carry-over rule from step 1 doesn't allow friendlies, but the step-7 split rule does, and the integrated.gdl uses the step-7 rule).
- ✅ **Queen-as-bishop teleport** — added in PR #109 (same shape as bishop teleport gated on `queen_form bishop`).
- ✅ **`captured_friendly` next-clause** — added in PR #109. Set when a move OR manipulation captures a piece; persists forever. Transformation to rook/bishop/knight now actually unlocks once a friendly piece is captured.
- ✅ **Transform rule body order** — `allowed_form` reordered before `distinct` so the resolver-distinct guard (which fails on unbound operands) doesn't bail.

**Remaining high-priority:**

1. ~~King → boulder capture~~ — re-verified: king's step-7 rule has NO `friend_at` filter, so it CAN move onto a boulder cell. Step 6's boulder-cell persistence rule fixed in PR #110 to NOT persist boulder cell when it's the king's destination (was a bug that would put both `(cell X Y none boulder)` and `(cell X Y white king)` in next state). King→boulder capture now correctly resolves.
2. **Invulnerability blocks captures by all attackers** — still only step 8's KING rule is invuln-aware; queen/rook/knight/pawn/bishop capture rules in steps 1-7 need the same guard. Deferred — would require editing each step file's rules; each step's rules are pulled into `integrated.gdl` via dedup-merge.

**Medium-priority (affects specific edge cases):**

5. Pawn promotion always to BASE queen; rulebook says the player chooses the form (base/rook/bishop/knight subject to the captured-piece rule).
7. Bishop manipulation (queen manipulating an enemy bishop) sketched only.

**Low-priority (sketched-by-design, awaiting reasoner integration):**

8. State hash encoding for repetition rule (step 10).
9. Cancel-queens balance valuation, closest-royal-pair-distance min (step 11).
10. Per-piece manipulation-freeze "next OWN turn" clearing timing.

**Working as designed (rulebook says X; GDL faithfully encodes X):**

Most everything else, including: piece movement, manipulation R1/R2/R3, boulder first move + cooldown + no-return + persistence, bishop teleport safety (post-2026-05-31 fix), rook 2-segment, knight radius-2, transformation, win condition via royal queens.

---

## Audit methodology

End-to-end validation via the GGP (PRs #100, #102-#107) executed steps 1-7 against legal-move enumeration and surfaced the following bugs that pure structural tests had missed:

- step 5: leftover scaffold rule allowed ANY occupied cell as bishop destination
- step 6: missing `(boulder_at intersection)` persistence rule
- resolver: `distinct` builtin silently succeeded when operands were unbound

Steps 8-11 are smoke-tested (rule constructs present in `integrated.gdl`) but not yet exercised in cross-turn-state positions. Cross-validation against `engine.get_all_legal_turns()` for the same Python game state is the next major check.

This audit will be re-run after each substantive fix to keep the
status table accurate.
