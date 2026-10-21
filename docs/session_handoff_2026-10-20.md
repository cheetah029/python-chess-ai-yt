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

## THE REGRESSION, AND THE HOLE THAT LET IT SHIP

A reviewer reported the agent worse in both games and it has been
**reverted to `2026-10-18_09cb8872`** (the legacy 18-feature blend of
seeds 71 and 601, 19 weights).

**Why it shipped: the race ran at depth 2 and the window plays at
depth 3.** A change that helps at one depth can hurt at another, and
this project had already measured deeper search amplifying an
evaluation's flaw. So the ship gate was never gating the thing being
shipped.

Three structural fixes, not just a revert:

1. `tools/race_agents.py` defaults to the play depth (`RACE_DEPTH`
   overrides).
2. **The gate is in the repository.** It lived in a scratch directory
   — untracked, untested, free to drift from the window it gates.
3. A test asserts the harness default equals `Game.TD_DEPTH` and fails
   if the harness is missing. Its first version SKIPPED when it could
   not find the file, which would have hidden exactly this.

Ruled out with evidence: the engine's boulder threat squares cannot
change a legal move (`has_enemy_piece` is False for the boulder for
both colours, and that guard is on the only read of `threat_squares`;
full rules suite 1658 passed), and the async path's double call to
`get_all_legal_turns` is idempotent (0 of 30 positions differed).

## THE EARLY EXIT LOSES — do not ship it

    depth4 + early exit  vs  depth3        10 – 14
    depth4               vs  depth4+exit    7 – 0  (1 drawn)

It cuts a depth-4 move from 15.22 s to 2.26 s and costs real strength.
`Searcher.settle` stays `None`. The saving is not free, and that is
the answer to "can we think less on obvious moves": not this way.

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

## GDL interpreter: 3.5x faster, verified to change no answer

    6.00s -> 2.19s   caching the move derivation per state
    2.19s -> 2.12s   `is_variable` (16.6M calls in one query)
    2.12s -> 1.73s   second-level fact index on the inner head

Half the time was my own duplication: `current_player` derives the
mover by asking each role for its moves, and `get_all_legal_turns` then
asked again, so `legal_moves` ran three times per call.

The index is sound because a fact whose inner head differs from the
goal's cannot unify with it. It NARROWS, it does not decide — a goal
whose argument is a variable falls back to the flat list.

Verified: the case study's GDL and engine still agree on 71 legal turns
from two independent implementations; nim/corridor/tic-tac-toe give
identical legal-turn counts along fixed lines; the narrowed set is
checked against the flat one including the cases where narrowing must
not happen.

**This unblocks applying partial satisfaction to Royal Chess's own
capture rules** — "one conjunct short of capturing" is "my king is one
step from that pawn", which is the general form of the king-walk gap.

## m,n,k this session

- **The exact centre.** The second-order measure still tied at 9 cells;
  ITERATING it (eigenvector centrality on the line-incidence
  structure) isolates (9,9) uniquely. 55 distinct evaluation values
  over 361 first moves, against 14 before. The reply to a centre
  opening is now adjacent too.
- **Save format v2**: move numbers and coordinates (`1. j10 i11`) plus
  board, style, mode and sides. No drawn board. v1 still reads.
- **Loading rebuilds the history**, so undo/redo work on a loaded game;
  loading is available from the setup screen (button and V).
- **Reported move-216 blunder**: not random — h8 touches one of the
  opponent's live threes. The opponent had THREE live threes to the
  agent's NONE, so the error was earlier. The structural problem it
  points at is that the agent builds no threats of its own.

## GUI: two regressions I caused, and the contract that now guards them

**The board was touchable while the computer thought.** The piece
handlers gate on `piece.color == game.next_player`, which during the
computer's turn is the COMPUTER'S colour. The invariant that stopped a
human dragging those pieces was never written down — it was a
consequence of the mainloop calling the AI synchronously, so no event
was read at all. Moving the search off-thread removed the accident and
with it the invariant.

Now `Game.is_board_input_locked()`, consulted **before** any mouse
button. Keys and motion stay live; a PAUSED game deliberately unlocks.

**The lag was the interpreter lock**, measured:

    switch interval   worst frame gap   frames in 2.5 s
    0.0050 (default)        54.2 ms          298
    0.0010                  13.8 ms          903
    0.0002                  17.2 ms         1271

1 ms is the knee. Set while a search runs, restored when it lands.

**m,n,k trained on every Start** — 20 s before a board appeared, for
weights identical every run. Cached to disk: 0.00 s afterwards, and
k=3..8 are pre-warmed in `lgref/weights/mnk_cache/`.

`tests/test_gui_contract.py` is the standing contract, including a
POSITIVE CONTROL — the human must still be able to touch the board on
their own turn, because a lock that blocks both sides looks exactly
like a frozen game.

## Is the revert exact?

**The weights are byte-identical** to `2026-10-18_09cb8872`
(sha `986895d4b4220c85` both sides).

**The search is not.** The jump-capture predicate changed, and on the
reviewer's reported opening it alters 1 of 4 Black decisions
(`Ne8-e6` now against `Ne8-f6` before). That is a correctness fix — the
search previously treated a knight's jump-capture as a quiet move — but
it is a behaviour change and it is being raced against the old search
on the same weights before anything is concluded.

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

---

# After the revert: what a ship gate has to be

## The reviewer's warning, in one line

> *Winning a race does not mean the player is strictly better.*

This is now the load-bearing sentence of the whole arc, and there is
evidence for it on both games.

**m,n,k.** `Reach:j` — the line count weighted by the eigenvector
centrality of its cells — fixed a real defect. On a large board the
plain `Line:j` count saturates and ties across 121 cells, so no
line-counting feature can tell the centre from a quadrant, and the
agent opened in a corner. With Reach on, it opens in the centre. The
reviewer then played it and reported the MIDGAME worse: tempo spent on
moves that neither attacked nor defended. **Both of those are true at
once.** An aggregate race reports one number for them, and whichever
effect is larger decides the number. Reach is therefore OFF and kept
switchable (`features.mnk(game, use_reach=False)`), so the two phases
can be raced separately rather than traded blind.

**Royal Chess.** The form-ablated build won its race 25–7 and a
reviewer found it much worse in play. It was reverted.

## What is now gated, mechanically

`lgref/weights/APPROVED.md` — the record of what the reviewer has
approved. Current: `2026-10-18_09cb8872`, sha `986895d4`, the legacy
18-feature set, seeds 71 and 601 averaged. It names what it supersedes
and why, the known weaknesses (blind to the boulder, no representation
of a bishop pin), and the candidates under test.

`lgref/tests/test_ship_discipline.py` (7 tests):

- the shipped weights ARE the approved build — fails on
  `2026-10-19_ccdb27cb`, verified by swapping it in;
- every shipped payload is restorable from the archive — **rekeyed
  from the commit that shipped it to the PAYLOAD itself**, because a
  revert ships bytes already archived under another commit's name, and
  the old form reported the revert as unrestorable while the file sat
  in the archive;
- the race runs at the depth the window plays;
- a race STATES ITS OWN TERMS;
- the feature that helps one phase stays switchable;
- a weight cache is keyed on the vocabulary, not just the board;
- the archive and its index exist.

## A result that had to be thrown away

`race_depth3_revert.log` reads **`current 2 - 8 legacy, 2 drawn`** at
depth 3 over 12 games. There is no way left to tell which rival those
eight losses were against: the environment variable that chose it went
away with the shell that set it. Eight losses that cannot be attributed
are not a result. The run is discarded, and `tools/race_agents.py` now
prints both weight files, both payload hashes, the depth, the budget
and the game count before the first game.

`jumprace.log` (jump-capture-aware search vs the search it replaces,
same weights, depth 3) stopped at **aware 0 – 3 blind**. Three games is
not a result either, and this one is a flag rather than a verdict: the
more correct search lost all three. It needs a proper run before the
jump-aware search is treated as an improvement.

## m,n,k, the reviewer's second list

**Numeric coordinates, `10,10`.** Column first (the order `j10` already
used), both numbers 1-based, row counted from the bottom — so the
centre of 19x19 is `10,10`. **No parentheses**: the move list is parsed
by splitting on whitespace, so one move has to be one token, and
`(10, 10)` is two. The convention is written into every save, because
`10,10` is ambiguous on a non-square board unless the file says which
number is which. v1 and v2 saves still load, and the letter form still
names the same cells.

**The save carries the settings.** Depth, seconds per move, and the
training parameters. A save that names the board but not the depth
describes a position, not a game: the same moves at depth 2 and depth 6
are two different agents playing. Depth and the clock are restored on
load; the training parameters are reported, not applied — applying them
would let a paste start a three-minute retrain with nothing asking
first.

**Why the depth changed every move.** It is iterative deepening under a
per-move clock: the depth reached is whatever fits, and what fits grows
as the board fills and the branching factor falls. Depth 6 on an empty
8x8 is 8^6 positions; twenty moves later it is a fraction of that.
Setting sec/move to **0** removes the clock, and then the depth is
exactly the depth. The panel now says which regime it is in — "depth 6
exactly / no time limit" against "depth 4 max / 5s/move". **Depth 6 was
the stepper's ceiling**, raised to 10 now that the clock is removable.

**Also fixed:** the full-screen flicker (`set_mode` made the driver
report a resize; the resize recomputed the board and called `set_mode`
again — that cycle also ran on every window MOVE, which reports a
resize although nothing resized); confirmation on Restart and Setup,
armed on the button face, disarmed by a move or by arming the other;
the transient message moved to its own line BELOW the buttons, so
copying no longer overwrites "O played 10,10 (optimal)"; "White played
179" now reads "White played 10,10"; coordinates drawn on the board
itself; and the key legend's arrow characters, which rendered as empty
boxes in the fallback font, spelled out as Left/Right.

