# Session handoff — 2026-10-18

Supersedes `docs/session_handoff_2026-09-27b.md` for the agent-strength
arc. Issue #278; branch `claude/objective-extraction-268`.

## State in one line

The shipped agent is the **legacy 18-feature blend of seeds 71 and
601**. Its piece values are much better than they were reported to be —
**a weight name was never a price** — and the real remaining defect is
that a dense coverage count outvotes material on quiet moves.

```bash
python3 src/main.py --ai black --ai-agent td
python3 lgref/play_mnk.py --m 9 --n 9 --k 5 --style go
```

## READ THIS FIRST: a weight name is not a price

`lgref/weights/td_royal_chess.json` lists `Bishop` at +0.0669 and
`Pawn` at +0.0616, which reads as "a bishop is worth 1.1 pawns". A
reviewer said that could not be right. **It is not right, and it is not
what the evaluation charges.**

The columns are COLLINEAR. In this game a queen may take the form of a
piece type only once a friendly piece of that type has been captured,
so *bishops I hold* and *bishop form available to me* are
near-complements. Measured by `replicate.shared_variance` over 1618
positions:

    column                 R^2 explained by the others
    Royal / DownToOneRoyal        0.990 / 0.990
    Bishop / FormAvailable:bishop 0.983 / 0.982
    Rook   / FormAvailable:rook   0.954 / 0.949
    Knight / FormAvailable:knight 0.894 / 0.889
    Covers                        0.532
    Pawn                          0.159

The learner only ever sees each pair's SUM; the split between the two
weights is the optimiser's path, not a finding. So every probe and
guard that compared two weight names was comparing one arbitrary half
against a whole.

**Price a piece by taking it off the board** —
`validate.removal_price`, which includes every column that moves:

    piece     price   in pawns    piece-for-a-pawn
    Pawn     0.0620       1.00    --
    Bishop   0.1012       1.63    -0.0392  declines
    Knight   0.1987       3.21    -0.1367  declines
    Rook     0.4539       7.32    -0.3919  declines
    Queen    0.8553      13.80    -0.7933  declines
    King     0.8556      13.80    -0.7936  declines

`scratchpad/blunder_probe.py` computes `-piece + pawn` from two names
and is therefore WRONG. Do not use it. `scratchpad/prices.py` uses the
removal instrument.

## What is actually wrong: coverage outvotes material

Two reviewers' games show the same move. `scratchpad/replay.py` parses
a v3 royal-notation save, so the position can be reconstructed:
replaying to Black's 9th move and dumping the column deltas across the
line actually played gives

    Covers                 7.00 -> 21.00    +0.0801
    Bishop                 0.00 -> -1.00    -0.0669
    Pawn                   0.00 -> +1.00    +0.0616
    FormAvailable:bishop   0.00 -> +1.00    -0.0379
    TOTAL                                   +0.0395

Material nets **−0.0432, correctly a loss**. A coverage count rises
fourteen squares at 0.0057 each and pays **+0.0801** for the bishop, so
the whole line scores as a GAIN. The bishop is sold to buy board
coverage.

`validate.turn_leverage` is the general instrument for this: how far
each column's CONTRIBUTION moves when one turn is played, which is what
decides a move.

    column      median swing   largest   turns it moved
    Rook              0.3925    0.3925               11
    Knight            0.1231    0.1231               13
    Bishop            0.0669    0.0669                5
    Pawn              0.0616    0.0616               59
    Covers            0.0114    0.0973              434

Material moves rarely and by a lot. Coverage moves on nearly every turn
and its tail swing exceeds the bishop's entire price. **Coverage is not
redundant** (R² 0.53), so this is a pricing question, not a column to
delete.

### One of the two reported games was not a blunder

Worth recording because I nearly "fixed" it. In the first game
`9... Ne6-f4` looks like ignoring a threat, and `10. Nd3xe5` wins the
bishop — but `10... Nf4-d6j` is a **jump-capture of the knight on e5**
(f4→d6 is a 2-diagonal whose jumped square is e5). Black traded a
bishop for a knight, which this evaluation rates as a gain and which is
defensible. The second game is the real error: the recapture there was
a pawn, so it was bishop-for-pawn.

Replay a reported game before calling a move a blunder.

## The blunder metric had no floor

`rescuable_losses` counts at-risk PIECES while a turn moves ONE, so
when three are rescuable at once two are counted lost whatever is
played. Measured with `validate.rescue_oracle`, a policy that does
nothing but minimise the metric by enumeration:

    floor (enumerating)   32.8%   20 of 61
    the shipped agent     45.9%   28 of 61
    random play           83.6%   51 of 61

So the agent is **74% of the way from random to the best achievable**,
and the headroom is 8 pieces of 61 — under one standard error at this
sample. That is why every candidate in this issue scored 45.9% ± 1:
the instrument could not tell them apart. **Ranking candidates on it
needs roughly ten times the trials.**

The historical "2.5%" figure is a DIFFERENT instrument (the
`strong.material` hang rate, which is counts-only and blind to piece
trades). It is not comparable to this number.

## Measurement instruments

| instrument | general? | what it is for |
|---|---|---|
| `validate.removal_price` | yes — injected remover | what the evaluation charges for a piece. **Use this, never a weight name** |
| `validate.turn_leverage` | yes | which column decides a move |
| `validate.exchange_opinions` | yes | whether the evaluation calls a played-out exchange a gain |
| `validate.rescue_oracle` | yes | the blunder metric's floor |
| `replicate.shared_variance` | yes | how much of a column the others explain |
| `record.audit` | yes | a payload that cannot be replayed, or a feature that never varied |
| head-to-head race (`scratchpad/race.py`) | yes | the ship gate |
| `scratchpad/sweep.py` hang/miss/regret | **NO** — uses `strong.material` | diagnostic only; cannot see a piece trade |
| `scratchpad/blunder_probe.py` | **BROKEN** | prices a trade from two weight names |

## The three silent failures are now checked by code

`lgref/experiments/record.py`, called by the loader on every load:

- **a boolean training flag** (`lean: True`) is a claim no loader
  reads. FATAL when nothing in `extractor`/`drop_prefixes`/`dropped`
  records the transformation; reported otherwise. `record()` refuses to
  write one, so a trainer cannot describe an ablation it did not do.
- **a normaliser scale of zero** means the feature never varied, so its
  weight is the absence of data rather than a price. This is the
  signature of the aggregate that was never computed.
- **`observed` / `silent`** check an extractor against real positions,
  so "does this feature fire" costs one call instead of three seeds.

**Verify an experiment changed what you think it changed before reading
its result.**

## In flight

- `scratchpad/exchange.py` — the **measured exchange rate**. One side
  starts a piece of type T short, the other a pawn short, both play the
  same evaluation, and the win rate gives `value(T) − value(pawn)` in
  log-odds with no free parameter. `T = Pawn` is the control and must
  land on 0.5; a fifth run strips one side only, which supplies the
  denominator a difference cannot. 60 games each.
- `scratchpad/tdq.py` — **quiescent TD-leaf**, three seeds, 800 games.
  Depth 1 with quiescence 4: depth buys lookahead, which is not the
  defect; quiescence buys the recapture, which is. Plain TD fits the
  position the agent is standing in, so "bishop takes pawn" is fitted
  with the pawn won and the bishop not yet lost. 6.5 s/game against 68
  for depth-2 TD-leaf, which is what makes 800 games affordable.

## Rules adopted (keep these)

- **Race every change** against the current champion before shipping.
  Two ideas predicted as free wins were rejected by this
  (PVS/aspiration; move deduplication, which lost 1–4 on m,n,k).
- **Validate that the metric can detect the failure you care about, and
  measure its floor**, before reading a rate as a verdict.
- **Change one thing at a time.**
- **Replay the game** before accepting that a reported move was a
  blunder.

## Next steps, in order

1. Finish the exchange runs; convert the win rates to outcome-calibrated
   material ratios. Build a candidate that keeps the pawn where TD put
   it and sets the other material prices to pawn × measured ratio —
   only the RATIOS change, which is exactly the claim under test — and
   race it.
2. Price the three `tdq` seeds by removal, blend by measurement, race
   the best against the shipped blend.
3. If material ratios alone do not stop the coverage trade, calibrate
   the coverage price the same way: by measured match outcomes, never by
   choosing a number.
4. `Hanging` is done and had no effect: live feature, non-zero scale,
   consistent negative weight across three seeds, 45.9%/47.5%.

## Generality

`lgref/tests/test_generality_audit.py` — 28 tests, runs every time. No
general module may name a game in live code, import an engine, hide a
value in evaluation units, or depend on the adapter layer. `record.py`
is in that list.

Adapters (`features`, `legacy`, `mnk`, `strong`, `undo`) may know a
game but must never be *assumed* — capability is detected.

Every instrument added in this session takes its game knowledge as an
injected callable: `removal_price` takes a remover, `exchange_opinions`
a classifier, `turn_leverage` a column function.

## m,n,k

- Boards to 20×20×20, Go-style intersections with black first,
  seconds-per-move stepper (1–120s).
- Weights train on a board sized to k and transfer (names depend on k
  alone): 300 games in 20s on 7×7 beats 60 in 41s on 19×19.
- Depth at 5s: 7×7 → 6, 9×9 → 4, 13×13 → 3, 19×19 → 2. **Depth cannot
  be constant across board SIZES**; it is constant across the phases of
  one game, and that is tested.

## Tests

~730 in `lgref/tests/`, 1563 + 3 skipped in `tests/`. Key files:
`test_generality_audit.py`, `test_record.py` (one test per silent
failure), `test_shipped_weights.py` (one guard per blunder a human
found, now priced by removal).
