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

## 5. The legality check visits cheap pieces first — IDENTICAL

`Board.has_legal_moves` runs after every executed turn to apply the
no-legal-moves loss. Over three depth-3 decisions (moves 2, 8 and 22)
it was called 31,131 times for 1.97 s, **and every call answered
True**. 1.31 s of that was `bishop_moves`: the scan visits pieces in
board order and stops at the first one with a legal move, so it often
builds a bishop's whole teleport list before it reaches a king or a
pawn that would already have answered.

The check is now a cheap first pass, then the full scan:

- `_cheap_piece_has_move` looks at the player's own pieces other than
  bishops, and the boulder on its square, each checked exactly as the
  full scan checks it: the same generator, the same repetition and
  tiny-endgame filters, frozen pieces skipped, and the boulder still
  barred on White's first turn.
- If none of them has a move, `_has_legal_moves_full` runs. This is the
  previous scan, unchanged, so it still decides every position the
  first pass does not.

Every check in the first pass is one the full scan makes, and each one
judges a single piece and leaves the board as it found it. So a True
from the first pass is a True the full scan would find, and the answer
cannot change.

**Certificate:** `test_cheap_first_legality_check_is_identical`. At
positions from six seeded games, for both players, the new check and
the full scan must give the same answer and leave the same state: the
state hash, every piece's flags and pending moves, the repetition
history and the distance counts. Real positions almost always answer at
the first pass, so each position is also checked in variants that
defeat it:

- the player's cheap pieces frozen, so the fallback answers;
- everything frozen, with and without the boulder;
- the queens removed, so the boulder acts alone, including on White's
  first turn, which play never reaches with the boulder on a square;
- only the king able to act, under a repetition rule that forbids every
  king move;
- in the tiny endgame, every royal distance at its limit.

All four outcomes must occur: the first pass answers, the fallback
answers, no legal move at all, and a position the full scan calls lost
where a first pass without the filters would have found a move. Then
three real searches with the previous check and the new one must give
the same move, node count and root values. Mutation-tested: a first
pass without either filter, one that moves frozen pieces, one that lets
the boulder move on White's first turn, or a check with no fallback
each fails it.

**Measured:** the same five decisions, the same moves and node counts,
process time 36.48 s → 34.08 s and 37.66 s → 32.25 s over two
interleaved runs against main after change 4. The machine was busy
(load average 2 to 3), so the spread is wide: **about 7% to 14%
faster, roughly 10%**. Decision 15 was flat in the first run and
every other decision was faster in both.

## Where the time goes after change 5 (profiled 2026-11-22)

The same two decisions as the first profile, 33.2 s under the profiler
(59.0 s then):

| where | with callees | share |
|---|---|---|
| move generation (`_generate_turns`) | 11.7 s | 35% |
| evaluation (`legacy.royal_chess`) | 6.2 s | 19% |
| `Board.get_state_hash`, 205,749 calls | 5.4 s | 16% |
| `Board.update_threat_squares` | 4.3 s | 13% |
| `Square.__init__`, 3,990,900 calls | 0.29 s | 0.9% |

The `Square` allocations the earlier "Next" list ended with are now
under 1%, so they are not worth a change.

## 6. The threat key survives an undo — IDENTICAL

Counting the threat recomputations by cause over those two decisions:

| update | updates | pieces recomputed |
|---|---|---|
| with no previous key | 37,889 | 1,036,497 |
| incremental | 44,007 | 57,198 |

**95% of the recomputation ran with no previous key**, and the key was
missing because `undo.restore` cleared it. The search undoes after
every move it tries, so the first update after each undo recomputed
every piece on the board.

`restore` already puts each piece's attributes back as they were at
the snapshot, `threat_squares` included. Now `snapshot` also saves the
board's threat key and `restore` puts it back, so the incremental
update recomputes only what differs from the key.

This is sound because every piece the key records holds the list
computed at that key. A list is written only by
`update_threat_squares`, which then sets the key, and a list is
always replaced, never edited in place. The restore puts back the
snapshot's lists together with its occupants, so the snapshot's key
describes them.

**Certificate:** `test_the_threat_key_survives_an_undo`. Every piece's
threat list at every update must be the same as with the clearing
restore, over two real depth-2 searches and four seeded games that, at
every ply, snapshot, play a random turn, list the turns, undo and list
the turns again. The searches must also give the same move, node count
and root values. More than 1,000 updates right after a restore must
recompute fewer pieces than stand on the board, so the kept key is
exercised. A restore that keeps the key but leaves the undone
position's lists must change the record. Mutation-tested: restoring the
key from before the undo fails the comparison, and saving no key fails
the coverage check.

**Measured:** the five decisions of change 1, the same moves and node
counts, process time 33.34 s → 31.09 s and 32.65 s → 30.59 s over two
interleaved runs against main after change 5, with every decision
faster in both: **about 6.5% faster**. The machine was busy (load
average 3 to 4), but the two runs agree to within half a point.

## 7. The state hash is built in one pass — IDENTICAL

Profiled after change 6 over all five decisions (47.1 s under the
profiler), `get_state_hash` was 8.4 s over 329,264 calls. It walked
all 64 squares three times: once to ask whether any bishop was
reactive-armed, once to build the entries, and once to list the
invulnerable pieces. The first walk alone was 20.6 million generator
steps.

Now one walk collects the pieces, whether any is reactive-armed, and
the invulnerable squares, and the entries are built from that list.
The walks only read the board, so merging them changes nothing. The
invulnerable squares are collected in row-major order, which is sorted
order for `(row, col)` pairs, so the sort is dropped.

**Certificate:** `test_the_state_hash_is_built_in_one_pass`. Every
hash returned must be the same tuple as the previous function's,
loaded from git (`c0a9a5a`) and bound to today's module. The cases are
twelve seeded games, two real depth-2 searches (same move, node count
and root values too), and four seeded games that mark a random handful
of pieces invulnerable before each hash. Those last games are needed:
play never leaves two pieces invulnerable at a recorded position,
because each knight's status is cleared before the opponent's position
is recorded, so only they test the sort premise. More than 100 hashes
must be taken with a bishop armed while another piece carries the
moved flag, and more than 100 with two or more pieces invulnerable.
Forgetting the arming, and listing the invulnerable squares column by
column, must each change the record. Mutation-tested: forgetting the
arming, sorting by column and dropping the invulnerable squares all
fail the comparison. Sorting by column is caught only by the crafted
games.

**Measured:** the five decisions, the same moves and node counts,
process time 30.99 s → 29.42 s and 31.77 s → 29.43 s over two
interleaved runs against main after change 6: **about 6% faster**.

## 8. The evaluation walks the threat squares once — IDENTICAL

The evaluation, `legacy.royal_chess`, was 6.4 s of the 47.1 s profile.
Most of its own time was two walks over every piece's threat squares:
one built the set of colours reaching each square, for `Attacked`, and
the other the set of squares each colour reaches, for `Covers`. That
was 12.9 million `setdefault` calls and 12.7 million `set.add` calls.

Now only the second is built, in one walk. The colours reaching a
square are exactly the colours whose set holds it, so a piece is
counted as attacked once for each other colour whose set holds its
square, as it was once for each attacking colour.

`legacy.py` is the frozen copy the approved player was fitted on, so
what stays frozen is its output. Its docstring now says so, and that
any further change needs the same proof.

**Certificate:** `test_the_evaluation_walks_the_threat_squares_once`.
Every feature dictionary must equal the frozen copy's, loaded from git
(`c0a9a5a`). The comparison is a list of items, so key order must match
too. The cases are six seeded games, two real depth-2 searches, and six
seeded games in which every threat list is replaced by a random one.
In some of those, a few pieces get a third colour for the evaluation
alone. Royal Chess has two sides, but the premises do not depend on
that, and with only two sides, two of the ways to get the rewrite
wrong change nothing.
Coverage: more than 1,000 evaluations with a piece reached by both its
own colour and the enemy, more than 100 with a piece reached by two
other colours, and more than 20 with a third colour reaching nothing.
Bite, and mutation-tested on the real code: counting the piece's own
colour, charging the attack to the attacker, giving a colour that
reaches nothing a `Covers` entry, and counting a piece once however
many colours reach it all fail. The last two fail only on the
third-colour games.

**Measured:** the evaluation alone, on positions from forty seeded
games, went from 0.068 ms to 0.038 ms a call, **44% faster**. In the
five decisions it is a small share: same moves and node counts,
29.44 s → 29.28 s and 30.25 s → 29.17 s, about 2%.

## 9. The recorded state hash is reused — IDENTICAL

Even in one walk, the state hash was computed about three times for
every position the search reached: `_next_turn` records it, then
`execute_turn` computed it again for the turn record's repetition
count, and the search computed it again as the node's key.

Now `record_state` keeps the hash it takes, with the player it was
taken for, as `board._recorded_state`. `execute_turn` clears it before
the turn and reuses it after. The searcher's `_descend` keeps it, and
`_node_key` uses it in place of `_key` while the board still holds that
very object. `_ascend` drops it.

**Move generation drops it too**, and that is the part the first
version missed. `_start_generation` expires one-turn flags the hash
reads: when it becomes a player's turn, the freeze on the pieces the
opponent's queen manipulated ends, which clears `moved_by_queen`. So
the hash a turn recorded stops describing the board as soon as the
next position generates its moves. The first version reused it
anyway. Its certificate passed, because its depth-2 searches never
reached a position where that changed a key. The full suite caught it:
`test_the_evaluation_cache_never_changes_the_tree` counted 4,416 nodes
with the evaluation cache against 4,375 without.

**Certificate:** `test_the_recorded_state_hash_is_reused`. Every turn
record and every node key, in order, must be the same as with both
reuses switched off. The cases are six seeded games and four real
searches: two at depth 2, one at depth 2 with the tie-breaking and
proved-loss guard on, and one at depth 3. Coverage: 10,364 turn
records and 8,064 node keys came from a kept hash; each must be more
than 2,000. Bite, and mutation-tested: a `_descend` that keeps the key
of the position it left fails the comparison.

Most of the guards change nothing in the comparison, so the test also
builds the path each guard is for, and checks it directly:
- a hash left from before a turn is never reused;
- a hash taken for the other player is never reused;
- after an undo, the node key is the parent's. This is also run under
  the engine's extra-move control, where the same player moves twice
  and only the drop in `_ascend` refuses the child's hash;
- after move generation, the kept hash is not used. Over twelve seeded
  games, generation changed the hash 60 times.

Mutation-tested on the real code: removing the drop in
`_start_generation`, the identity check in `_node_key`, the clear in
`execute_turn`, either player check, or the drop in `_ascend` each
fails one of these. The first two are caught only by the
generation check.

The declaration was written down after a first draft of the code, not
before it. The class, IDENTICAL, was settled when the change was
designed and before anything was measured. The entry in `DECLARED`
records that order, and that its premise (2) was first wrong.

**Measured:** the five decisions, same moves and node counts,
27.08 s → 25.27 s and 28.44 s → 25.67 s against change 8: **about 8%
faster**. The first version measured 11%, but part of that was the
reuse it should not have made.

## Where the time goes after change 9 (profiled 2026-11-22)

The five decisions under the profiler: 47.1 s after change 6, 39.4 s
now.

| where | with callees | share |
|---|---|---|
| move generation (`_generate_turns`) | 16.7 s | 42% |
| evaluation (`legacy.royal_chess`) | 4.0 s | 10% |
| `undo.snapshot` and `undo.restore` | 3.8 s | 10% |
| `Board.update_threat_squares` | 3.5 s | 9% |
| `Board.queen_moves_enemy`, 627,668 calls | 2.8 s | 7% |
| `Board.get_state_hash`, 147,193 calls | 2.6 s | 7% |

`get_state_hash` was 8.4 s over 329,264 calls before changes 7 and 9.

## 10. Manipulation targets are found once per generation — IDENTICAL

Move generation called `queen_moves_enemy` for every enemy piece, and
each call scanned all 64 squares for a queen of the mover's colour
whose line of sight holds that piece: 627,668 scans in the five
decisions, nearly all of them finding none.

Now `_generate_turns` finds those queens once, after the turn-start
housekeeping. `GameEngine._manipulation_reach` returns the squares
their lines of sight hold, as (row, col) pairs. An enemy piece on none
of them is skipped. Its move list is cleared, which is how the old path
left it, and nothing else is done. A piece on one of them goes through
`queen_moves_enemy` exactly as before.

The premises: with no such queen, `queen_moves_enemy` lists nothing,
and the old path then ran both filters on an empty list, which adds
zero to the block counters. Membership in a line of sight is decided
by row and column, through `Square.__eq__`. And nothing in the loop
moves a queen or changes a line of sight: listing a piece's moves only
lists them, and the repetition filter plays each move on trial and
takes it back.

**Certificate:** `test_manipulation_targets_are_found_once`. Every turn
list a generation returns, full or tactical, in order, and both block
counters, must be the same as with `_generate_turns` loaded from git
(9329471). The cases are eight seeded games, six seeded games that
play a manipulation whenever one is offered, and two real depth-2
searches, whose move, node count and root values are compared too.
Coverage: over 50,000 enemy pieces skipped, over 1,000 standing where
a queen sees them, and over 2,000 manipulations listed. Bite: an empty
set and the set of the wrong colour's queens each change the record.

Mutation-tested on the real code: testing for the wrong colour's
queens, transposing the squares, building the set for the mover's own
pieces, and leaving one square out of each line of sight all fail the
comparison. Dropping the clear on a skipped piece changes nothing in
today's games, because every enemy piece reaches the loop with an
empty move list. So the test builds the other case, a board whose
pieces all have moves left over, and checks the skipped pieces end
with none. Without the clear, that check fails.

**Measured:** the five decisions, same moves and node counts,
25.20 s → 22.90 s and 25.22 s → 23.05 s against change 9: **about 9%
faster**.

## 11. Tactical generation lists only captures — IDENTICAL

Tactical generation is four in five of all generations. It keeps only
moves onto an occupied square that is not the boulder, plus a knight's
jump-capture offers. Yet the pawn, rook, king, base-queen and boulder
generators listed every move first, building a `Move` and two
`Square`s for each one onto an empty square. The engine then threw
those away, and ran both filters on every piece, kept moves or not.

Now those five generators take `captures_only`, which the tactical
generation passes, and a move onto an empty square is not listed. Each
skip is on a branch whose destination is empty. The rook still sweeps
past empty squares, since a capture can lie beyond them. A piece left
with no tactical move returns before the filters. The knight lists all
its moves as before, because a move onto an empty square can be a
jump-capture offer. So do manipulated pieces, which are rare.

**Certificate:** `test_tactical_generation_lists_only_captures`. Every
turn list a generation returns, full or tactical, in order, and both
block counters, must be the same as with `_generate_turns`,
`_generate_piece_turns` and the five generators loaded from git
(9329471, so before change 10 as well). The cases are eight seeded
games, six that play a capture whenever one is offered, six that leave
the boulder on the central intersection for eighty plies, and two real
depth-2 searches. Coverage: each of the five pieces, in the tactical
generation, passes over more than 2,000 moves onto empty squares and
still lists more than 100 onto occupied ones; and the boulder can take
a pawn with its first move, off the intersection, more than 20 times.
Bite: a king that skips the friendly pieces it may capture changes the
record.

Mutation-tested on the real code: a king skipping occupied squares, a
rook sweep that stops at the first empty square, a boulder that cannot
take a pawn (from the intersection or after), an early return that
also drops a piece's single capture, and the king's skip applied to
the full generation all fail the comparison. The first boulder mutant
survived until the boulder-on-the-intersection games were added: no
other case has a pawn on a central square while the boulder can still
take it with its first move. Three mutants survive and are harmless.
Two make the pawn list some empty-square moves again, and one makes
the queen also skip friendly squares, which she cannot move onto. All
three only change what the engine's own tactical filter then discards.

The helper that loads an old function from git now keeps its default
arguments; it had been dropping them.

**Measured:** the five decisions, same moves and node counts,
23.89 s → 23.12 s and 23.93 s → 23.01 s against change 10: **about
3.5% faster**.

## 12. Undo copies each piece once — IDENTICAL

`undo.snapshot` and `undo.restore` run once for every move the search
tries, 103,075 times in the five decisions. Most of their time was
copying piece attributes: `snapshot` walked the board a second time to
collect the pieces, deduplicating them by id, and copied each with
`dict(vars(piece))`; `restore` emptied each piece's dictionary and
refilled it.

Now `snapshot` collects the pieces in the same walk that saves the
grid, copies each dictionary with `__dict__.copy()`, and saves the
boulder whenever there is one. `restore` gives each piece a fresh copy
of its saved dictionary, and puts the grid back with `zip`. Measured
on a midgame position: 9.9 µs → about 5.5 µs to snapshot, 7.0 µs →
about 4.5 µs to restore.

The premises: a piece saved twice is saved twice with equal contents,
taken at the same moment, so restoring it twice leaves what restoring
it once did, and the deduplication changed nothing. A fresh copy of the
saved dictionary holds what emptying and refilling the old one held,
in the same order. It must be a copy, so the token can be restored
again. And nothing keeps a reference to a piece's attribute dictionary
across a restore: only `features.py` reads `vars(piece)`, and only
while it walks.

**Certificate:** `test_undo_copies_each_piece_once`. Along seeded
games, at every ply, a snapshot is taken and up to four legal turns are
each applied and undone, some two deep, and sometimes the same token is
restored again after a further turn. After each restore, every square's
piece and every piece's attribute items, in order, are described, with
objects named by when they were first seen. The repetition history,
distance counts, captures and threat key are described too. All of it
must equal what `snapshot` and `restore` from git (9329471) produce.
Some games point `board.boulder` at the boulder after it has left the
intersection, so it is saved twice; play never does that. Some give a
piece a new attribute during each turn. Two real depth-2 searches
compare move, node count and root values. Coverage: the boulder saved
off the board, the boulder saved twice, a token restored twice and an
attribute added during a turn, each more than 20 times. Bite: a restore
that hands the piece the saved dictionary itself changes the record.

Mutation-tested on the real code: sharing the saved dictionary,
leaving the off-board boulder out, saving the live dictionary instead
of a copy, restoring the grid upside down, and refilling without
emptying all fail.

**Measured:** the five decisions, same moves and node counts, against
change 11. On a quiet machine, 22.05 s → 20.77 s and 21.80 s → 20.40 s:
**about 6% faster**. An earlier pair, run while three test suites
loaded the machine, gave 2.6% and 7.8%, and is not used.

## Where the time goes after change 12 (profiled 2026-11-22)

The five decisions under the profiler: 39.4 s after change 9, 31.7 s
now.

| where | with callees | share |
|---|---|---|
| move generation (`_generate_turns`) | 11.2 s | 35% |
| turn execution (`_execute_spatial_turn`), of which: | 9.6 s | 30% |
| — `_next_turn` (legality check, state record) | 3.9 s | 12% |
| — `Board.update_assassin_squares` | 1.9 s | 6% |
| — `Board.move` | 1.3 s | 4% |
| — `Board.clear_forbidden_squares` | 1.0 s | 3% |
| — `Board.decrement_boulder_cooldown` | 1.0 s | 3% |
| evaluation (`legacy.royal_chess`) | 3.9 s | 12% |
| `Board.update_threat_squares` | 3.4 s | 11% |
| `Board.get_state_hash`, 147,193 calls | 2.6 s | 8% |
| `undo.snapshot` and `undo.restore` | 2.0 s | 6% |

`snapshot` and `restore` were 3.8 s before change 12.

## 13. The engine no longer lists assassin squares — IDENTICAL

Turn execution called `Board.update_assassin_squares` at the end of
every turn, 103,075 times in the five decisions and 6% of the profiled
time. It walked the board and, for each of the mover's bishops, listed
the enemy pieces on its diagonals into `piece.assassin_squares`.

Nothing in play reads that list any more. Since the 2026-07-20
redesign the bishop's reactive capture is armed by `reactive_armed`,
which `Board.move` sets when a piece starts its move on the bishop's
diagonal, and it takes the piece carrying `moved_last_turn`. The list
is in no hash and no evaluation term. So `GameEngine` no longer calls
the method, on the spatial, promotion and transformation paths. The
method stays for its other callers (the game window, `notation.py`,
`ai_controller.py`) and their tests.

The premises: the method writes nothing but `assassin_squares` on the
mover's bishops; and no code reached from the engine or the search
looks inside the list. `features.py` reads the type of every attribute
value, and a list is a list either way.

**Certificate:** `test_the_engine_no_longer_lists_assassin_squares`. At
every ply of seeded games, games that take whenever they can, and games
that push their pawns to promotion, the legal turn list, the turn
record, the state hash and every piece's plain attributes other than
`assassin_squares` must equal what the turn execution from git
(1c769e4) produces; two real depth-2 searches compare every turn record
and the move, node count and root values. With the new code every
bishop, including the ones created by a promotion or a transformation,
holds a list that raises when anything looks inside it, so a reader
fails the test. The source must name the attribute only where it is
written, defined or documented, so a new reader is caught even on a
path the cases miss. Coverage: more than 1,000 turns end with one of
the mover's bishops seeing an enemy piece; more than 20
transformations, more than 20 promotions, and more than 5 promotions
while the boulder cools. Bite: a reactive capture that reads the list
raises, and a turn that skips the boulder's cooldown changes the record.

Mutation-tested on the real code: dropping the boulder's cooldown from
the transformation path or from the promotion path, dropping
`record_action_turn` from the transformation path, and cooling the
boulder on the turn it moved all fail. The promotion mutant survived at
first, because no case promoted while the boulder was cooling; the
pawn-pushing games now move the boulder often, which is what the last
coverage count is for.

**Measured:** the five decisions, same moves and node counts, against
change 12: 20.11 s → 19.42 s and 20.72 s → 19.69 s, **about 4%
faster**.

## 14. The turn-end walks read each square once — IDENTICAL

Four whole-board walks run on every turn the search tries:
`Board.clear_forbidden_squares`, `Board.decrement_boulder_cooldown`,
`Board.clear_invulnerable_for_color` and `GameEngine._count_pieces`.
Each reached a square as `self.squares[row][col]` up to four times,
over `range(ROWS)` and `range(COLS)`, and most called
`Square.has_piece()`.

Now each walks the rows and their squares directly, reads the square's
piece once into a local name, and tests `is not None` where it called
`has_piece()`, which is all `has_piece()` does. Every test, every write
and their order are as they were. Measured on a midgame board, the four
together: about 21 µs → 9 µs a turn.

The premise: `self.squares` is the eight rows of eight squares that the
ranges indexed, so each walk visits the same squares in the same order.

**Certificate:** `test_the_turn_end_walks_read_each_square_once`. At
every ply of seeded games, games that take whenever they can, and games
that push their pawns and move the boulder, the legal turn list, the
turn record (which holds the piece counts), the state hash and every
piece's plain attributes must equal what the four functions from git
(1c769e4) produce; two real depth-2 searches compare every turn record
and the move, node count and root values. Play never leaves a
forbidden square or zone behind, so each pair of functions is also
applied to two copies of twenty boards set up with forbidden squares
and zones, a boulder cooling, moved this turn or not, invulnerable
pieces of both colours and transformed queens; the copies must end
equal and the results match. Coverage: each branch changes more than
ten of those boards, and more than 50 transformed queens are counted.
Bite: a boulder cooled on the turn it moved, and a transformed queen
counted by its form, are each caught both on the boards and in the
games.

Mutation-tested on the real code: leaving the forbidden zone, skipping
the last row of forbidden squares, cooling the boulder on the turn it
moved, cooling it below zero, clearing the wrong colour's
invulnerability, counting a transformed queen by its form, and skipping
a row of the count all fail. The two forbidden-square mutants are
caught only by the boards, as expected: the default `freeze` mode never
sets a forbidden square.

**Measured:** the five decisions, same moves and node counts, against
change 13: 19.20 s → 18.17 s and 19.46 s → 18.15 s, **about 6%
faster**.

## 15. The state hash notes the queens in its walk — IDENTICAL

`get_state_hash` was 9.5% of the profiled search: 147,193 calls in the
five decisions, about 12 µs each. It walked the board to collect the
pieces, then walked the collected pieces again to build an entry for
each. For every piece carrying `moved_last_turn`, one after a spatial
turn, it called `_enemy_base_queen_has_los_to`, which scanned the whole
board again for an enemy base-form queen.

Now each entry is built in the first walk with the moved flag False.
The walk also notes the base-form queens of each colour and the pieces
carrying the flag. After it, when it is known whether any bishop is
armed, each noted piece is decided by the same three tests in the same
order. The queen test asks `_has_unblocked_queen_los` only from the
enemy queens the walk noted, and the entry's flag is set where the old
code set it. On positions sampled from seeded games: about 12.4 µs →
9.7 µs a hash.

The premises: the entries come in the same order; the queens asked are
the ones the old scan would find, in the same row-major order, picked
by the same test, and nothing in the hash changes the board; and an
entry with the flag set differs from one without only in that field.
`_enemy_base_queen_has_los_to` stays, with its own tests.

**Certificate:** `test_the_state_hash_notes_the_queens_in_its_walk`.
Every hash, in order, must equal what `get_state_hash` from git
(61c9e0a) returns, over seeded games, games that manipulate whenever
they can, games in which random pieces are given the moved flag, armed,
made invulnerable or given a forbidden square or zone before each turn,
and two real depth-2 searches, which compare move, node count and root
values too. Coverage: more than 1,000 flags pinned by an armed bishop
and more than 1,000 left unpinned; more than 500 pinned by an enemy
queen alone and more than 500 by an enemy knight alone; more than
1,000 hashes each with two flags at once, with white and with black
base queens, and with a transformed queen. Bite: asking the mover's
own queens, and setting the flag in the field before it, each change
the record.

Mutation-tested on the real code: deciding the flags before the arming
is known, pinning every flag, noting a flag against the wrong entry,
dropping the knight test, and asking only the last queen all fail.
Dropping the `is_transformed` test from the queen check survives, and
is equivalent: a transformed queen is an instance of its form's class,
and `transform_queen` builds a base-form queen with `is_transformed`
False, so no `Queen` is ever transformed.

**Measured:** the five decisions, same moves and node counts, against
change 14, five pairs: 18.07 s → 17.72 s on average, **about 2%
faster**, and faster in four pairs of five. Smaller than the hash's
share suggested, because most of a hash is building the entries, which
the change still does.

The legality check after each turn (`has_legal_moves`, 5% profiled)
was looked at in the same pass and left alone. Its first pass usually
answers with the first piece it tries, and the cost is that piece's
generator, mostly the boulder's. Trying pawns first saves about 2 µs a
call, about 1% of a search. But each piece tried ends with an empty
move list, so a different order changes which pieces keep the moves
they had, which the certificate for the first pass pins.

## 16. Turns without a sub-choice are built directly — IDENTICAL

`_generate_piece_turns` builds the Turns of one piece: 505,193 calls in
two of the five decisions. For every move it keeps, it built a
one-element list of jump choices and one of promotion choices, worked
out whether a jump was offered, and looped over both lists to build
each Turn with keyword arguments, though most moves offer no
jump-capture and are due no promotion. It also looked up the board and
tested the piece's class again for every move, and called
`has_piece()` on the destination.

Now the piece's class tests and the board are read once per piece. A
move that captures, or is not a knight's, and is not a pawn's move to
the last rank is appended as one Turn built directly, with positional
arguments. Every other move takes the general path, unchanged. On
positions sampled from seeded games: full generation 298 µs → 270 µs,
tactical generation 99 µs → 95 µs.

The premises: for such a move the general path finds no jump targets
and no promotion, so its lists are `[None]` and `[None]`,
`has_jump_offer` is False, and it builds exactly one Turn, or none when
a tactical move does not capture; the direct path builds that one, or
skips the same way. A piece's class does not change while its Turns are
built. And `target is not None` is all `has_piece()` tests.

A draft was timed before this was declared, to see whether it was worth
building, and put aside while the declaration was written; the entry in
`DECLARED` says so.

**Certificate:** `test_turns_without_a_sub_choice_are_built_directly`.
Every turn list a generation returns, full or tactical, in order, with
every Turn's attributes and both block counters, must equal what
`_generate_piece_turns` from git (61c9e0a) produces, over seeded games,
games that take whenever they can, games that push their pawns to
promotion, and two real depth-2 searches, which compare move, node
count and root values too. Coverage: more than 100,000 full and 10,000
tactical Turns built directly; more than 100 full and 100 tactical
Turns with a jump offer, and more than 100 full and 20 tactical
promotions, built by the general path. Bite: a direct Turn marked as
offering a jump, and a promotion sent down the direct path, each change
the record.

Mutation-tested on the real code: sending a knight's quiet move down
the direct path, sending black's promotions (to row 7) down it,
swapping `has_jump_offer` and `is_capture`, swapping the squares,
and counting a move onto the boulder as a capture all fail. Dropping
the boulder test from the tactical filter survives, and is harmless: a
move onto the boulder kept by it does not capture, so the emit loop's
tactical skip drops it. It would show only if the repetition or
endgame rule also blocked that move, so that a block counter moved.

**Measured:** the five decisions, same moves and node counts, against
change 15, three pairs: 17.78 s → 17.51 s on average, **about 1.5%
faster**, faster in each pair. Most generations in a search are
tactical, where the gain is smallest.

## 17. The evaluation walks the board once and remembers its keys — IDENTICAL

The search evaluates 48,776 positions in the five decisions. On sampled
positions with the threat squares already current, `legacy.royal_chess`
took 35 µs and the two wrappers the loader puts around it, `without`
and `drop_prefixes`, about 7 µs more. `royal_chess` walked the board
twice, once for the material and once for the threat squares, reading
every attribute through `getattr` with a default. Each wrapper decided
again, for every key on every call, whether to keep it.

Now `royal_chess` brings the threat squares up to date first, then
walks the board once: it counts the material as before and notes each
owned piece's square and threat list. After the walk it adds the royal
indicators, the zeroed threat features and the threat counts in the
order it added them before. It reads `color`, `is_royal`,
`is_transformed` and `threat_squares` directly. The wrappers remember,
for each key they have judged, whether it is kept. Full extractor:
41.9 µs → 35.0 µs.

The premises: bringing the threat squares up to date changes nothing
the material count reads, and an AttributeError from it, or from the
threat walk, still drops only the threat counts; the keys come in the
same order; every piece is a `Piece`, whose `__init__` sets the four
attributes; and whether a key is kept depends on the key and the
wrapper's fixed names alone.

**Certificate:** `test_evaluation_walks_once_and_remembers_keys`.
Every dictionary `royal_chess` returns, and every one each wrapper
returns, as lists of items in order, and every score, must equal what
the three functions from git (591414c) give, at each ply of seeded
random games, games that take whenever they can, games that transform
their queens whenever they can, and games that push their pawns, and
through two real depth-2 searches, which compare move, node count and
root values too. The shipped weights drop no key, so the games also
evaluate with an extractor that drops two prefix families and one
column. Coverage: more than 1,000 evaluations each with a piece
attacked, a transformed queen counted, a side down to one royal, and
keys dropped by each wrapper. Bite: a threat key given its place
before the material, and the first remembered decision applied to
every key, each change the record.

Mutation-tested on the real code: not bringing the threat squares up to
date, counting the boulder's square as owned, noting a piece only when
it has a threat list, counting a transformed queen by its form, a
prefix decision that sticks at True, and the column decision shared
between keys of one colour all fail.

**Measured:** the five decisions, same moves and node counts, against
change 16, five interleaved pairs: 28.34 s → 27.62 s on average, **about
2.5% faster**, faster in each pair. The machine was heavily loaded
(load average 10 to 15 on ten cores, from other work), which put every
time about 60% above a quiet run; the pairs were interleaved so that
both sides shared the load.

## 18. Three more turn walks read each square once — IDENTICAL

Three more whole-board walks run on every turn the search tries:
`Board.clear_turn_flags` (128,524 calls in the five decisions; it
expires the last-move flags at every spatial and action turn),
`Board._compute_armed_bishops` (102,622; the enemy bishops with a clear
diagonal to a moving piece's square) and `Board.get_royal_distance`
(103,075; for the turn record). As change 14 did for four others, each
now walks the rows and their squares directly and reads the square's
piece once; the two that need a square's row and column take them from
`enumerate`. `is_tiny_endgame` was left alone: it returns at the first
pawn, so it rarely walks far.

The premise: `self.squares` is the eight rows of eight squares the
ranges indexed, so each walk visits the same squares in the same order,
`enumerate` gives the indices the ranges gave, and the armed bishops
come back in the same order.

**Certificate:** `test_three_more_turn_walks_read_each_square_once`. At
every ply of seeded games, games that take whenever they can and games
that transform their queens whenever they can, the legal turn list, the
turn record (which holds the royal distance), the state hash and every
piece's plain attributes must equal what the three functions from git
(9037ad0) produce; two real depth-2 searches compare every turn record
and the move, node count and root values. Each pair is also applied to
two copies of thirty boards set up with last-move flags on many pieces,
movers of every colour including the neutral boulder, enemy bishops put
next to a mover so that several see it, and boards without a royal of
one colour; the copies must end equal and the results match, with the
armed bishops named by their squares in order. Coverage: flags cleared
on more than 20 boards, a distance found on more than 10 and none on
more than 3, a neutral mover more than 3 times, two or more armed
bishops more than 3 times, and enemy bishops none of which is armed
more than 20 times. Bite: a walk that skips the last row, and armed
bishops returned in reverse order, are each caught.

Mutation-tested on the real code: clearing only the moved flag, the
armed check with row and column swapped, arming the mover's own
bishops, and the royal distance skipping a row all fail. Counting the
royals' rows from 1 survives, and is equivalent: it shifts every royal
by the same amount, which no distance between two of them can see.

**Measured:** the three walks, same moves and node counts, five
interleaved pairs against change 17 on a heavily loaded machine (load
12-15 on ten cores): 50.21 s -> 48.79 s CPU on average, about 2.8%
faster, faster in each pair.

## Next, in order of expected gain per risk

1. Turn execution. The walks of change 14 still visit every square:
   skipping `clear_forbidden_squares` outright needs a proof that no
   piece can carry a forbidden square in the default `freeze` mode,
   which a board loaded from elsewhere can break, and finding the
   boulder without a walk needs a tracked reference that undo would
   have to restore. The legality check and the state hash are covered
   in section 15.
2. Move generation, 35%, now spread across the piece generators; the
   bishop's teleport list (1.5 s, full generation only) is the largest
   single one.
