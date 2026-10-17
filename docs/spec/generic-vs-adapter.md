# What full generality costs, measured

A reviewer put the challenge plainly: the threat features look
hand-picked, "square coverage" and "attacked" sound like someone's idea
of what matters in chess, and nothing should be specific to the case
study. This is the measurement that answers it, rather than an argument.

## The two layers

**`features.generic`** reads the MOVE PROTOCOL and nothing else:
`get_all_legal_turns()`, `current_player`, and whatever
`mcts.describe` can see on a turn. It walks no board and names no piece
type. It cannot be hand-picked, because there is nothing to pick from.

    Mobility      how many legal turns exist
    Reach         how many distinct destinations they lead to
    Moves:N       turns belonging to each piece identity N
    Captures:N    how many of those are captures
    Type:T        turns of each turn type the engine declares

Identities come from the turn, so they are the engine's own names. On a
game whose turns are plain data — m,n,k's are integers — the
per-identity families are simply absent and only `Mobility` and `Reach`
remain.

**The per-game adapters** (`features.royal_chess`, `features.mnk`) read
the board. They still take their vocabulary from the engine
(`type(piece).__name__`, `win_lines`, `threat_squares`) rather than from
a list, but they require the engine to HAVE a board.

## Why the adapter layer exists at all

Not as a shortcut. An engine generates legal turns only for the **player
to move**, so everything derivable from the protocol is mover-relative
and has no opponent-side counterpart to difference against — the
differential of a mover-only feature is always `+n` rather than a
comparison. A symmetric evaluation needs both sides' state at once, and
the only thing that exposes that is the board, which the protocol does
not require an engine to have.

That is a property of the protocol, and it is the honest reason the
adapters are not going away.

## The measurement

TD from zero, graded against exact minimax, 300 trials, same seed
throughout. `both` is the adapter's features plus the protocol's.

### 3×3 k=3 — chance 37.6%, uniform control 37.4%

| features | one-ply | depth 3 | count |
|---|---|---|---|
| protocol only | 50.5% | 68.9% | 4 |
| adapter | 91.9% | 96.4% | 6 |
| both | 91.9% | 96.4% | 10 |

### 4×4 k=3 — chance 31.9%, uniform control 25.8%

| features | one-ply | depth 3 | count |
|---|---|---|---|
| protocol only | 51.5% | 86.5% | 4 |
| adapter | 84.6% | 97.0% | 6 |
| **both** | **87.4%** | **99.2%** | 10 |

## What it says

1. **Full generality is not useless.** Protocol-only features beat
   chance by 20 points at one ply and reach 86.5% behind a depth-3
   search. An agent that knows nothing about any game except how to ask
   for its legal moves plays respectably.

2. **The board is worth a lot at one ply, and much less with search.**
   The adapter's advantage is 33 points at one ply (84.6% against
   51.5%) and 10 points at depth 3 (97.0% against 86.5%). Search
   substitutes for features, which is the expected trade and worth
   knowing when deciding where to spend effort.

3. **The two layers are complementary, not redundant.** On 4×4,
   combining them beats the adapter alone — 99.2% against 97.0% at
   depth 3, and 87.4% against 84.6% at one ply. The protocol features
   carry something the board-reading adapter does not, so the generic
   layer earns its place in the shipped extractor rather than merely
   existing to answer the objection.

4. On 3×3 the combination is identical to the adapter, to the digit.
   The board is small enough that the adapter already saturates, so
   there is nothing left for the protocol layer to add. The gain in (3)
   is a 4×4 result and should not be quoted as general.

## The limitation of this measurement

It is one game family, at two sizes, with exact grading available only
because the boards are tiny. It says the generic layer is useful on
m,n,k; it does not establish how much it adds on an 8×8 variant, where
there is no exact reference to grade against and the comparison has to
be made by relative play instead.
