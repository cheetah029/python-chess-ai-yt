# Session handoff — 2026-10-20

Supersedes `docs/session_handoff_2026-10-19.md`. Issue #278; branch
`claude/objective-extraction-268`.

## THE STANDING METHODOLOGICAL RULE (reviewer directive, 2026-10-20)

**Do not use the agent's own play as evidence for a conclusion.** The
agent is not yet competent enough for its choices to be data. Using
them to argue about strategy is circular — especially when the question
is whether a thing the agent does is wrong.

Reason it out yourself. Use data only when it is a *validated*
measurement: a pure computation (`win_lines` structure), a head-to-head
race, an exact solver, or a deterministic property of the code. Never
"the agent played X, therefore X".

The older rules still hold, and all three are ways a number here has
been wrong before:

1. **A weight NAME is not a price.** Columns are collinear; price a
   piece with `validate.removal_price` by taking it off the board.
2. **A rate without its FLOOR is not a measurement.** Report
   `rescuable_losses` beside `validate.rescue_oracle`.
3. **A big weight may rest on almost nothing.** `record.unsupported`
   names weights that are large on few observations.

A fourth, learned this session:

4. **A "flat evaluation" control measures TIE-BREAKING, not nothing.**
   With all weights zero every move ties and the winner is whatever
   move ordering puts first — on corridor that control scored 81.2%
   before the move list was sorted and 0.0% after. Use the `chance`
   column (share of legal turns that are optimal) as the baseline.

## What is shipped

`lgref/weights/td_royal_chess.json` — the legacy 18-feature blend of
seeds 71 and 601, with `drop_prefixes: ['RoyalForm:',
'PromotedQueenForm:']` (13 weights). Raced 25–7 with 8 drawn.

Measured prices (by removal, every column that moves included):
Pawn 1.00, Bishop 1.63, Knight 3.21, Rook 7.32, royals 13.80.

**`lgref/weights/archive/` keeps every shipped version**, recovered
from git history, with `INDEX.md` saying what changed and whether each
still loads. Restore with a copy. Five of twelve predate the
`extractor` field and cannot load; their extractor was never frozen and
was *identified* (best name-overlap 0.30–0.67) rather than guessed.

## Decided this session

- **Depth 4 beats depth 3, 16–6 with 2 drawn** (22 decided). NOT yet
  raised in `Game.TD_DEPTH` — see "open" below.
- Costs: depth 3 median 2.57 s/move (p90 7.32); depth 4 median
  11.08 s (p90 17.50). The 30 s budget never binds at either.
- Coverage ablation **lost** (7–14, 19 drawn). Pin blend **lost**
  (8–16). Neither shipped.

## Fixed this session

- **The window froze for the whole search.** `take_turn` chooses *and*
  applies; the loop called it directly, so no event was read for
  seconds. Now `start_thinking`/`poll`/`finish_turn`/`abort` on a
  thread, with the search on a deep copy returning a *description*
  resolved against freshly enumerated turns. Pausing aborts.
- **Keys**: ← → step, Home/End (Up/Down alias) jump to the ends, both
  games.
- **m,n,k window** is resizable with full screen on F11.
- **The m,n,k opening** landed in a quadrant because 121 cells tie at
  the maximum line count on 19×19 k=5. `features._line_reach` adds the
  second-order measure; the best first move is now the true centre and
  the evaluation has 45 distinct values instead of 14. **Not an
  improvement on small boards** (4×4: 85.4% without, 81.2% with, n=48,
  SE≈5 — noise), and no board with the plateau is exactly solvable, so
  the case rests on the structural argument.
- **`play_window` called `pygame.quit()` under test**, tearing fonts
  down process-wide and breaking unrelated files.

## The GDL path — now the general answer to several things

`lgref/experiments/gdl.py` plays any GDL with features named from the
file's own relations. Optimal-action rate at one ply against exact
play on 3×3 tic-tac-toe (chance 34.1%, hand-written m,n,k 93.9%):

    60.9%  start — contributed NOTHING over flat
    69.4%  + ownership inferred by watching play (partition rule)
    71.4%  + conjuncts of each rule counted
    73.5%  + a conjunct blocked by a RIVAL told from an empty one
    77.6%  + absent levels read as zero
    87.8%  + a disjunction inheriting its disjuncts' counts

**Partial satisfaction is counted, never ranked.** Each level is its
own feature (`line~1`, `line~2`, …) with no ordering, no sign and no
single "progress" number — a single number *would be* the assumption
the reviewer warned against. The win condition separates none from
some and says nothing about two-of-three beating one-of-three.

Royal Chess's own GDL loads: 59 features, 71 legal turns matching the
engine's 71. Its derived vocabulary already contains `cell@2=bishop`,
`cell@2=knight`, `cell@2=rook`, `cell@2=pawn`.

**Blocked on interpreter speed** (~6 s per position), which is
engineering, not research. That speed is what stands between here and
applying partial satisfaction to Royal Chess's *capture* rules — which
is the general fix for the king-walk gap ("one conjunct short of
capturing" = "my king is one step from that pawn").

## THE BOULDER IS INVISIBLE TO THE EVALUATION (found, partly fixed)

Derived from the code, not from watching the agent:

1. The boulder reaches the extractor with owner `'none'`, which is in
   `NEUTRAL_OWNERS`, and `discover.differentials` **drops every
   neutral-owner feature**. So `Boulder` never survives differencing:
   the evaluation has no term for the boulder's existence, position or
   proximity to pawns.
2. The threat pass in `features.royal_chess` and in `legacy.py`
   **skipped neutral owners too**, so a pawn the boulder could capture
   did not even read as `Attacked`.
3. And underneath both: `Board.update_threat_squares` never populated
   `threat_squares` for the boulder at all, so there was nothing to
   include. Verified empty on a real mid-game board.

Fixed (3) in the engine — the boulder's eight adjacent squares, an
over-approximation that ignores cooldown and no-return **on purpose**,
because that cache is keyed on occupancy alone and its soundness
depends on reading no turn state. Safe for legal-move generation: the
only consumer is the bishop's teleport-safety check, which selects with
`has_enemy_piece`, which excludes the boulder by definition — and the
rulebook requires the boulder to be excluded from that check anyway.
Verified: 34 pawn-under-boulder-threat instances across 40 games where
there were previously none.

Fixed (2) in `features.royal_chess`. **NOT fixed for the shipped
agent**, which uses the frozen `legacy.py` and is therefore still
blind. Closing it needs a retrain on the live extractor plus a race.

**On whether Black should move the boulder first**: the mechanism the
reviewer describes is real and comes straight from the rules — the
no-return rule means the second mover cannot simply reverse the first
move, only deflect it, so the first mover sets a direction that drifts.
But the boulder is a SHARED resource with symmetric access once the
cooldown expires, and moving it develops nothing. I cannot establish
from the rules alone that the first boulder move beats a developing
move, and I am not going to assert it. Settling it would need exact
search on a reduced position, which would be real evidence.

## Open, in priority order

1. **Depth 4 + the early exit.** Depth 4 beat depth 3 **16–6, 2
   drawn**. The early exit (`Searcher.settle`) cuts a depth-4 move from
   15.22 s to **2.26 s** — cheaper than depth 3's 2.57 s — but changes
   the move in 6 of 20 positions, so it is racing: depth4+settle vs
   depth3, and depth4 vs depth4+settle. Ship only if both hold.
2. **A partial deepening pass no longer overwrites a trusted answer.**
   `_root` now reports whether it searched every root move; a pass that
   ran out of time partway is accepted only if it is at least as good
   as the completed answer it would replace. This is a strong candidate
   for the "sudden blunder in a position it was playing well" the
   reviewer reports — the old comment claimed a partial result was
   sound "because the best-ordered moves go first", which is only true
   when the ordering is good, and in a game with no captures the
   ordering is killers and history alone.
2. **The bishop is used to stall, not to pin.** The reviewer's analysis
   is the right one and is not yet implemented: in a king+bishop+pawn
   endgame the winning idea is to pin the enemy BISHOP with your own —
   which simultaneously frees your king from its pin — and then race
   the kings to the pawns. The agent has no representation of this. The
   `Pinned` feature exists in the live extractor, is correctly signed
   across two seeds, and is priced at ≈0.09 pawns, which is far too
   small.
3. **The boulder is under-used.** See the reasoning note below.
4. **Random mid-game blunders** in both games.
5. **GDL interpreter speed.**
6. **Phase 3** needs a competent instrument; Phase C (the evaluator's
   reliable envelope) was skipped.

## Rules questions settled with the reviewer

- **Repetition state stays legal-move-determining.** Measured on the
  stalling stretch of a reported game: 27 distinct states under *both*
  the current definition and a positions-only one, max repeat 2 — the
  coarser definition would not have shortened it by a ply, because the
  bishop's teleport generates genuinely different placements. Keep the
  conditional inclusion (`moved_last_turn` hashed only when a rule
  consults it; boulder memory only when it restricts) — that is already
  the right principle.
- **No "no-progress" rule.** The game is designed anti-draw; the tiny
  endgame rule handles genuinely stall-prone positions. Adding a
  no-progress bound would convert *winnable* positions into draws and
  record inaccurate results. Fix the agent instead.

## Tests

`lgref/tests/`: `test_generality_audit.py` (30), `test_unseen_gdl.py`
(24), `test_pricing.py`, `test_record.py`, `test_play_mnk_ui.py` (26),
`test_shipped_weights.py` (9, incl. the archive). `tests/`:
`test_entry_points.py` (72), `test_playable_agents.py`,
`test_async_thinking.py` (8).
