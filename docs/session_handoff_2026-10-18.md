# Session handoff — 2026-10-18

Supersedes `docs/session_handoff_2026-09-27b.md` for the agent-strength
arc. Issue #278; branch `claude/objective-extraction-268`.

## State in one line

**The playable agent has been RESTORED to the 18-feature seed-71
weights (commit `8dccbf0`)** — the version the reviewer measured as most
competent — after a long run of changes made it worse. It saves the
knight in the position where its successor blundered.

```bash
python3 src/main.py --ai black --ai-agent td
python3 lgref/play_mnk.py --m 9 --n 9 --k 5 --style go
```

## What is shipped

`lgref/weights/td_royal_chess.json` — `extractor: "legacy"`, 18
features, TD-root seed 71, 800 games. The loader builds the frozen
extractor in `lgref/experiments/legacy.py` from the `extractor` field.

| measure | shipped (71+601) | superseded 5-seed |
|---|---|---|
| reviewer's blunder position | **saves the knight** | blunders |
| rescuable pieces lost | **44.3%** | 47.5% |
| head-to-head race | 27–27 over 70 games | 27–27 |
| bishop value | **−0.0077 (bad)** | +0.069 |
| knight value | **4.3 pawns (good)** | 1.3 pawns |

**The open problem**: the restored weights give away BISHOPS; the
superseded ones gave away KNIGHTS. No version yet declines both. The
70-game race between them was an exact tie, which is why neither is
obviously right and why the reviewer's direct evidence decided it.

## The three things that caused the regression

Recorded because preventing a repeat matters more than the fix.

1. **Ten per-identity relational columns added at once**
   (`Attacked:I`, `Hanging:I`, `Threatens:I`, plus flag counts — 42
   columns). They diluted material and cost strength. Never raced
   before shipping.
2. **Ablated wholesale when that showed up**, throwing out the one good
   idea with them: *attacked AND undefended*. The lean set has
   `Attacked` (defended or not), which cannot tell a trade from a gift.
3. **The metric could not see the resulting blunders.**
   `strong.material` is COUNTS ONLY — a knight equals a pawn — so
   "0/40 hangs, 0.12 regret" was measured by an instrument blind to the
   exact failure being reported. Every candidate chosen over several
   rounds was selected by it.

## Rules adopted (keep these)

- **Race every change** against the current champion before shipping.
  Two ideas predicted as free wins were rejected by this
  (PVS/aspiration; move deduplication, which lost 1–4 on m,n,k).
- **Validate the metric can detect the failure you care about** before
  trusting it. This is the lesson of item 3.
- **Change one thing at a time.** Items 1 and 2 were both bulk changes.

## Measurement instruments

| instrument | general? | use |
|---|---|---|
| `validate.rescuable_losses` | **yes** — no piece values | the blunder metric; what a human reports |
| head-to-head race (`scratchpad/race.py`) | **yes** — wins/losses only | the ship gate |
| `scratchpad/sweep.py` hang/miss/regret | **NO** — uses `strong.material` | diagnostic only; cannot see piece trades |
| `scratchpad/blunder_probe.py` | domain | prices piece-for-pawn from the weights |

`strong.material` must never again be used to judge a claim about
material. A test pins its blindness.

## In flight when the session ended

Three seeds training with ONE aggregate `Hanging` feature
(`scratchpad/hang_80{1,2,3}.json`) — "attacked and undefended", the
idea thrown out in item 2, added back alone rather than as ten columns.
**Judge it on `rescuable_losses` and a race, not on the counting
harness.** If it beats 44.3% and wins its race, it ships; otherwise the
restored weights stay.

Note: adding `Hanging` changed the feature vocabulary, so pre-existing
lean weights no longer load — the staleness guard catches this.

## DONE: the bishop is fixed without losing the knight

The restored weights are sound except they trade bishops for pawns
(`4. Pe2-e3 Bh5xe3 5. Pd2xe3` in a reviewer's game -- reactive capture
skips the teleport-safety check, so the bishop lands on a guarded
square).

Three runs of the legacy feature set exist (seed 71 shipped, 601, 602
in the scratchpad). Searching every blend of them for one that declines
BOTH trades found exactly one:

    blend       knight/p  bishop/p   B-for-P   K-for-P
    71               4.3      -0.2   +0.0578   -0.1639   (shipped; loses bishops)
    601              0.4       1.9   -0.0682   +0.0411   (loses knights)
    601+71           2.0       1.1   -0.0052   -0.0614   DECLINES BOTH
    601+602+71       1.0       0.9   +0.0106   +0.0011   (loses both)

Verified on the reviewer's actual positions:

    weights     bishop position        knight position
    restored    SACRIFICES the bishop  saves the knight
    601+71      keeps the bishop       saves the knight

**SHIPPED.** It beat the seed-71 restore **13-6 with 6 drawn over 25
games**, leading from game 4, and `rescuable_losses` is 45.9% against
44.3% -- 28 pieces against 27, one piece, inside the noise. The race
and the two position tests both favour it; the blunder metric is flat
between them.

Shipped values: Royal 6.9 pawns, Rook 6.4, Knight 2.0, Bishop 1.1.
Both trades decline: bishop-for-pawn -0.0052, knight-for-pawn -0.0614.

The bishop guard in `test_shipped_weights.py` is STRICT again; it had
been recorded as a known failure while the seed-71 restore was
shipped.

Averaging all THREE seeds makes it worse (pawn rises to 0.074 while
knight falls to 0.073), so "more seeds" is not automatically better
here -- the blend has to be chosen by measurement.

## Next steps, in order

1. Finish the `Hanging` seeds; measure and race. 44.3% is the number.
2. **The bishop/knight trade-off is the real open problem.** No run has
   both. Candidates: average runs that err differently (worked once:
   5 seeds beat 2), or train longer (TD-leaf at 70 games was far too
   noisy; TD-root needed 800 to stabilise).
3. TD-leaf is untested fairly. The one run that was raced had been
   trained on the known-bad 67-feature set because a patch silently
   failed. Its knight signal was strong (+0.085 → +0.227).

## Generality

`lgref/tests/test_generality_audit.py` — 25 tests, runs every time. No
general module may name a game in live code, import an engine, hide a
value in evaluation units, or depend on the adapter layer. It found and
fixed two leaks (`undo.PIECE_FLAGS`; `discover` importing `features`).

Adapters (`features`, `legacy`, `mnk`, `strong`, `undo`) may know a
game but must never be *assumed* — capability is detected.

## m,n,k

- Boards to 20×20×20, Go-style intersections with black first,
  seconds-per-move stepper (1–120s).
- Weights train on a board sized to k and transfer (names depend on k
  alone): 300 games in 20s on 7×7 beats 60 in 41s on 19×19.
- Depth at 5s: 7×7 → 6, 9×9 → 4, 13×13 → 3, 19×19 → 2. **Depth cannot
  be constant across board SIZES**; it is constant across the phases of
  one game, and that is tested.

## Tests

~720 in `lgref/tests/`, 1563 + 3 skipped in `tests/`. Key additions:
`test_generality_audit.py`, `test_shipped_weights.py` (one guard per
blunder a human found), plus guards for depth consistency,
skip-equivalence, self-capture ordering and Go labels.
