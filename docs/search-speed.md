# Search speed (#279)

Making the same search cheaper is admissible on its own: an IDENTICAL
change has the same output and less cost, so strict improvement is
arithmetic (`docs/strictly-better-method.md`). Raising the depth is
not: a depth change alters the move in many positions and needs its
own certificate. So this file records speedups only, each with its
IDENTICAL test in `lgref/tests/test_method.py`.

## Where the time goes (profiled 2026-11-18)

Two depth-3 decisions of the reviewer's game (moves 4 and 15), the
Royal Chess player with tie resolution and the loss guard off, 59.0 s
under the profiler:

| function | calls | own time | with callees |
|---|---|---|---|
| `Board.update_threat_squares` | 131,460 | 10.5 s | 16.2 s |
| `Board.queen_moves_enemy` | 852,766 | 4.3 s | 7.7 s |
| `legacy.royal_chess` (evaluation features) | 37,120 | 3.7 s | 9.7 s |
| `Square.has_enemy_piece` | 59,237,274 | 3.1 s | 3.1 s |
| `Board.get_state_hash` | 214,599 | 2.9 s | 6.2 s |
| `Square.in_range` | 26,842,484 | 2.2 s | 2.2 s |
| `Square.__init__` | 22,998,265 | 1.4 s | 1.4 s |

`update_threat_squares` already caches on the position, and a
multi-entry cache was measured useless (5% hit rate: the calls are
genuinely different positions). What is left there is computing the
threat squares incrementally, which needs a differential test against
full recomputation.

## 1. The queen scan tests `isinstance` first — IDENTICAL

`queen_moves_enemy` scans all 64 squares, for every enemy piece in
every move generation, for a base-form queen of the mover's colour that
sees the target. It called the Python method `has_enemy_piece` on every
square before the built-in `isinstance(..., Queen)`: 54 of the 59
million `has_enemy_piece` calls above. Both tests are pure, so testing
`isinstance` first gives the same answer on every square.

**Certificate:** `test_queen_scan_order_is_identical` rebuilds the old
method from the new one's own source with that one condition put back,
and compares every legal turn, manipulations included, over positions
from twelve seeded random games; it requires that several of them offer
manipulations.

**Measured:** five decisions of the reviewer's game (moves 2, 4, 8, 15,
22), the same moves and the same node counts, process time 57.0 s →
52.6 s over two runs each: **about 8% faster**.

## 2. Threat squares are computed incrementally — IDENTICAL

`update_threat_squares` cached the whole map on the 64 occupants, but
almost every call is a different position (a 5% hit rate), so it
recomputed every piece every time, including each time `bishop_moves`
lifts a bishop off the board. It now recomputes only the pieces whose
threats READ a square whose occupant changed since its previous call,
and keeps every other piece's list:

| piece | squares its threats read (`_threat_reach`) |
|---|---|
| knight | the 5×5 box around it (landing squares within 2, jumped squares within 1) |
| rook | the rows just above and below it and the columns just left and right of it |
| pawn, queen, king, boulder | none besides its own square (plus the boulder's intersection flag, whose change recomputes everything) |
| bishop | none (bishops threaten nothing) |

A piece that is a different object, or stands on a different square, is
always recomputed. Sound because `threat_squares` is written only by
this method and no two boards share a piece object.

**Certificate:** `test_incremental_threat_squares_are_identical` replays
six seeded random games and two real depth-2 searches, records every
piece's threat list at **every call**, and requires the record to equal
the old method's (the new source with the incremental branch switched
off). It requires more than a thousand lists kept across a changed
position, so the incremental path is exercised, and it checks that
emptying the reach makes the records differ. Mutation-tested: dropping
the knight's reach, the rook's reach, or the rook's side columns each
fails it.

**Measured:** the same five decisions as change 1, the same moves and
the same node counts, process time 87.5 s → 71.9 s and 84.9 s → 72.0 s
over two interleaved runs on a loaded machine: **about 16–18% faster**.

## 3. Threat squares share frozen squares — IDENTICAL

Re-profiled after change 2 (moves 4 and 15, the shipped player at
depth 3): 14.6 million `Square` constructions, **8.7 million** of them
in `_compute_threat_squares`, one fresh square per threat recorded.
Every reader of `threat_squares` (`bishop_moves`, the evaluation
features, `metrics`) takes only `.row` and `.col` from an entry, so the
threat lists now hold `FIXED_SQUARES[row][col]`: one shared, piece-less
square per coordinate (`square.FixedSquare`).

Sharing is sound only if nobody writes to a shared square or tells two
apart by identity. So a `FixedSquare` is **frozen**: assigning or
deleting any attribute raises, and a writer cannot exist silently. A
copy, deepcopy or pickle hands back the shared square itself, so a
cloned board (the window copies by pickle) keeps the same property.

**Certificate:** `test_threat_squares_share_frozen_squares_identically`
rebuilds the old method from the new source with every shared square
put back to `Square(row, col)`, then compares, along six seeded random
games and two real depth-2 searches: every piece's threat list at
every call, every legal turn (manipulations included) along the games,
and the chosen move and node count of the searches. It checks that the
comparison can see a wrong threat list (with every list empty, both the
legal turns and the search change), that writing to a shared square
raises, and that copies resolve to the shared square. Mutation-tested:
an unfrozen `FixedSquare`, or one that copies like an ordinary square,
fails it.

**Measured, and it is small.** Full threat recomputation alone, 113
positions × 40, median of seven: 0.344 s → 0.275 s and 0.346 s →
0.280 s over two interleaved rounds, **about 19% faster**. That method
is about 14% of a search, so the five decisions of change 1 move only
**about 2%**: 42.73 s → 42.68 s and 44.69 s → 42.72 s, within the
run-to-run noise, with the same moves and the same node counts.

## 4. Tactical turns are generated on their own — IDENTICAL

This is the staged move generation from the plan, in the form this
searcher can use. The textbook version stages generation at interior
nodes: the transposition-table move, then captures, then quiet moves
only if no cutoff came first. Measured where generation actually
happens, over two depth-3 decisions (moves 4 and 15):

| call site | calls | generation | turns per call | tactical per call |
|---|---|---|---|---|
| `_search` at the horizon | 19,354 | 6.72 s | 65.3 | 3.8 |
| `_quiesce` | 9,850 | 3.09 s | 56.7 | 6.7 |
| `_search` interior | 704 | 0.25 s | 65.8 | 6.1 |

**97% of generation is at nodes that read only the tactical turns**, so
staging interior nodes would save almost nothing. The engine now has
`get_tactical_turns()`: exactly the turns of `get_all_legal_turns()`
that `royal_chess_tactical` accepts, in the same order, after the same
turn-start housekeeping (`_start_generation`). One loop serves both,
with a `tactical` switch:

- A bishop computes only its reactive capture (`bishop_reactive_moves`,
  the same code `bishop_moves` runs for it). The teleport list was
  4.8 s of 13.2 s of generation, and a teleport never captures.
- A queen's transformation options are skipped, since a transformation
  never captures.
- Every other piece keeps only the moves that capture or offer a
  jump-capture, before the repetition and tiny-endgame filters. Those
  filters judge each move on its own, so filtering the subset keeps
  exactly what the full generation keeps. A declined jump-capture takes
  nothing and is left out.

The searcher reads it at the horizon and in quiescence (the injected
`Searcher.tactical_turns`, set for Royal Chess in
`load_royal_chess_searcher`). An empty list means only "nothing
tactical", so there it still generates everything, to tell a quiet
position from one with no legal turn. That is about 22% of horizon
nodes. The turn-start housekeeping leaves the same state when it runs
twice, so the fallback is exact.

**It found a bug first.** The state comparison failed: full generation
cleared an armed queen-as-bishop's `reactive_armed` flag, and the
tactical generation, which skips transformations, did not. The
transformation repetition check saved the last-move flags after
swapping the queen out. Fixed separately, with its own certificate
(#330), before this change.

**Certificate:** `test_tactical_turns_are_generated_identically`. At
every sampled position of 14 seeded games, the tactical list must equal
the tactical filter of the full list, every field compared, and the
engine's state must agree after each generator and after the
fallback's tactical-then-full sequence. The games use three policies:
capture-happy random play (including seeds that reach the tiny
endgame), pawn pushes (so that captures promote), and kings stepping
back and forth (so that the repetition filter is live). Every kind of
capture must occur: landing, the king taking its own piece, the
boulder taking a pawn, manipulation, the bishop's reactive capture,
the knight's jump-capture, and a capture that promotes. Then three
real searches must give the same move, the same node count and the
same value for every root move as the searcher without the tactical
list. A tactical list missing its last turn must change the search.
Mutation-tested: dropping jump-captures, dropping the reactive
capture, or keeping declined jumps each fails it.

**Measured:** the five decisions of change 1, the same moves and the
same node counts, process time 40.56 s → 36.18 s and 40.81 s → 36.49 s
over two interleaved runs on a quiet machine: **about 11% faster**,
with every one of the five decisions faster.

## Next, in order of expected gain per risk

1. `Board.has_legal_moves`, called at the end of every executed turn
   to apply the no-legal-moves loss: 5.7 s of 46.5 in the profile. It
   returns at the first piece with a legal move, but it visits pieces
   in board order and so often runs a bishop's full teleport list
   first. The answer is a single boolean that does not depend on the
   order, so checking cheap pieces first would be IDENTICAL.
2. The remaining `Square` allocations (about 6 million in two
   decisions) are move squares in `bishop_moves`,
   `straightline_of_sight_squares`, `pawn_moves` and the other
   generators. They end up inside `Move` and `Turn` objects the UI and
   the trainer keep, so the sharing argument has to be made again for
   those readers. Expect a few percent at most.
