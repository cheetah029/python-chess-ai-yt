# Depth 4 everywhere: what it actually takes

Scope for the move-generation work, measured rather than estimated. The
request was to aim for depth 4 in every phase, and to scope the
restructuring separately from the evaluator work.

## Where the time goes

`cProfile` over 300 move generations from a ply-60 midgame position,
with the occupancy cache deliberately invalidated each time so the
numbers reflect what a search pays:

| | cumtime share | calls per generation |
|---|---|---|
| `update_threat_squares` | **33%** | 2 |
| `bishop_moves` | 22% | 1 per bishop |
| `_generate_piece_turns` | (65% cum) | 27 |
| `queen_moves_enemy` | 14% | 13 |
| `Square.has_enemy_piece` | 6% | **896** |
| `Square.in_range` | 5% | **507** |
| `Square.__init__` | 3% | **426** |

Total: about 0.74 ms per generation. The cost is spread — there is no
single hot spot to delete — which is what made this look unattractive
before.

## The number that changes the plan

Instrumenting the searcher to count moves generated and ordered against
descents actually performed, depth 4:

| position | ordered nodes | moves generated | descents | **searched / generated** |
|---|---|---|---|---|
| opening (ply 4) | 14,036 | 195,937 | 45,845 | **23.4%** |
| midgame (ply 60) | 2,606 | 48,032 | 9,334 | **19.4%** |

**Four fifths of move generation is thrown away.** Alpha-beta with good
ordering cuts off after a few moves at most nodes, but the generator
produces all fifty-odd first, and `order_turns` then sorts all of them.

This reframes the work. The expensive item is not any one function; it
is that the search asks for a complete legal-move list at every node and
uses a fifth of it.

## The plan, cheapest and least invasive first

### 1. Staged move generation — the main item

Give the searcher an optional staged interface and leave
`get_all_legal_turns()` exactly as it is:

    stage 1   the transposition-table move alone
    stage 2   captures and other forcing turns
    stage 3   quiet turns, generated only if the node has not cut off

**Why this is the right first move:** it is additive. The UI, the
trainer, the GGP cross-validation and every existing test keep calling
`get_all_legal_turns()` and see no change. The invasive option —
restructuring threat squares — touches code all four depend on.

**Expected gain:** bounded above by 1/0.234 = 4.3x on generation, and
realistically less, because identifying the captures for stage 2 needs
part of the work stage 3 would have done. A plain estimate is 2-3x.

**Risk:** legality filtering must stay complete. Repetition and
tiny-endgame checks are consulted during generation, and a staged
generator that defers them would produce illegal turns. This needs
checking against `RULEBOOK.md` per stage, not assuming.

### 2. Incremental threat squares — 33%, but invasive

`update_threat_squares` recomputes every piece's threat set whenever the
occupancy tuple changes. After a single move only the moved piece, the
captured piece, and pieces whose lines the move blocked or opened can
have changed.

**Expected gain:** most of the 33%, so about 1.3-1.5x overall.

**Why it is listed second despite being the biggest single item:** the
cache is read by the UI, the trainer and the GGP path, and its soundness
argument is carefully written down in `board.py` ("reads exactly two
things: which piece object stands on each square, and `knight_mode`").
An incremental version has to preserve that argument under moves,
captures, promotions and transformations, and a subtly wrong threat set
does not crash — it makes the agent look weak, which is the hardest
class of bug to notice. This is the item that belongs on its own branch
with its own differential test against the full recomputation.

### 3. Stop allocating `Square` objects — 14%, easy

426 `Square` instances are constructed per generation, and
`has_enemy_piece` / `in_range` are called 896 and 507 times on them.
Taking `(row, col)` integers instead removes the allocation entirely.
Mechanical, local, and testable by equivalence.

## Honest assessment of whether depth 4 is reachable

Opening depth 4 currently costs 18.2 s with the previous 11-feature
evaluation. A playable time control is about 4 s, so the requirement is
roughly **4.5x**.

    staged generation      2 - 3x
    incremental threats    1.3 - 1.5x
    square allocation      1.1x

Multiplied, 2.9x - 5.0x. So depth 4 everywhere is **plausible but not
assured**, and the honest form of the commitment is: do items 1 and 3
first, re-measure, and only take on item 2 if the remainder is actually
needed. Items 1 and 3 together may well be enough, and they are the two
that do not touch shared code.

## What this does NOT buy

Depth is not currently the limit on playing strength, which is measured
separately: over 40 positions with exhaustive 2-ply material truth, mean
material regret was 0.20 at depth 2 and 0.17 at depth 4 — a 14x compute
increase for a difference inside the noise. The case for depth 4 is that
it should pay off *once the evaluation is good enough to exploit it*,
not that it pays off now. Both lines of work are needed; neither
substitutes for the other.
