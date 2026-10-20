# Session handoff — 2026-10-19

Supersedes `docs/session_handoff_2026-09-27b.md` for the agent-strength
arc. Issue #278; branch `claude/objective-extraction-268`.

## State in one line

The shipped agent is the **legacy 18-feature blend of seeds 71 and
601**. A reviewer listed nine blunders across two games; replaying both
games reproduced all nine and found **two causes**, one fixed and one
newly represented. A candidate with the first cause ablated is winning
its race.

```bash
python3 src/main.py --ai black --ai-agent td
python3 lgref/play_mnk.py --m 9 --n 9 --k 5 --style go
```

## READ THIS FIRST: three ways a number here has been wrong

1. **A WEIGHT NAME IS NOT A PRICE.** The columns are collinear: a queen
   may take a form only once a friendly piece of that type has been
   captured, so *bishops I hold* and *bishop form available* are
   near-complements (R² 0.983/0.982 by `replicate.shared_variance`).
   The learner sees only the SUM. Price a piece with
   `validate.removal_price`, which takes it off the board and asks the
   evaluation again. `scratchpad/blunder_probe.py` computes
   `-piece + pawn` from two names and is **WRONG**; use
   `scratchpad/prices.py`.

2. **A RATE WITHOUT ITS FLOOR IS NOT A MEASUREMENT.**
   `rescuable_losses` counts at-risk PIECES while a turn moves ONE.
   Always report it beside `validate.rescue_oracle`.

3. **A BIG WEIGHT MAY REST ON NOTHING.** Adagrad gives sparse features
   large steps on purpose. `bootstrap.run` now counts per-feature
   observations into `support`, and `record.unsupported` names weights
   that are large on almost no data. On a 75-game run it found
   `Flag:moved_by_queen` at **+0.1936 on 12 observations** — the
   second-largest weight in the table.

## The measured prices (shipped weights)

    piece     price   in pawns    piece-for-a-pawn
    Pawn     0.0620       1.00    --
    Bishop   0.1012       1.63    -0.0392  declines
    Knight   0.1987       3.21    -0.1367  declines
    Rook     0.4539       7.32    -0.3919  declines
    Queen    0.8553      13.80    -0.7933  declines
    King     0.8556      13.80    -0.7936  declines

## The blunder rate, properly measured

At the depth the window plays (**3**, not the 2 every earlier number
used), with the metric's jump-capture blindness fixed, 200 trials:

    floor (a policy that only minimises the metric)   23.8%   39/164
    the shipped agent                                 49.4%   81/164
    random play                                       84.8%  139/164

The agent is **58% of the way from random to the best achievable**, and
the gap is 42 pieces of 164 — about eight standard errors. **There is
real headroom.** An earlier "74%" came from the broken metric at depth 2
on a quarter of the sample.

The historical "2.5%" is a DIFFERENT instrument (`strong.material`,
counts-only, blind to piece trades) and is not comparable.

## Cause one: free levers (fixed, racing)

At game 2 move 29 the agent gives away a pawn. The two lines:

    pawn g6-g5 (gives it)            pawn d6-e6 (keeps it)
      Pawn            -0.0616          RoyalForm:Rook   -0.1467
      Covers          +0.0057          Covers           +0.0629
      TOTAL           -0.0563          TOTAL            -0.0877

Keeping the pawn lets the opponent TRANSFORM a royal queen into rook
form, cancelling a differential the agent holds. `RoyalForm:Rook`
carries +0.1467 — 2.4 pawns — so the phantom threat costs more than the
pawn. A transformation captures nothing and risks nothing.

`validate.free_leverage` measures that asymmetry (how far a column moves
on turns that take NOTHING) and `lever_columns` flags the ones that
swing further, for free, than the cheapest MEASURED piece price. A piece
count cannot be moved that way; taking something off the board needs a
capture.

Three independent lines of evidence: the free-lever measurement; no
cross-seed replication (|mean|/SE 1.2–2.1, two with MIXED signs, against
13.98 for `Royal` and 6.88 for `Pawn`); and ablating them fixes **four**
of the nine reported blunders, including the one the reviewer named
specifically — game 2 move 40 now plays `king b7xc7` and recaptures.

**Candidate: `scratchpad/noforms.json`** — the shipped blend with
`drop_prefixes: ['RoyalForm:', 'PromotedQueenForm:']`. Expressed as a
REPLAYED ABLATION rather than zeroed weights: the two are the same
evaluation (w·x with w=0 contributes nothing) but only the ablation
travels with the payload. Racing the shipped blend: **5–11 behind after
19 games**, 3 drawn.

## Cause two: it could not see a pin (now represented)

A bishop captures only reactively, so a piece on its clear diagonal is
NOT attacked — which is why it looked safe — and every square it could
move to is lethal.

**Two of the nine "blunders" are forced consequences, not errors.** Game
1 move 21: the rook is attacked by a pawn AND on Bf3's diagonal, so it
is lost whatever happens and taking a pawn is best — the error was move
19, moving it there. Game 2 move 26: all eight king escape squares are
reactive-captured by Bg2 — the error was move 22.

`features.royal_chess` now counts **`Pinned`**: the mover's pieces on an
enemy reactive captor's clear diagonal. Four ray walks per captor, no
simulation, so it runs at a leaf. A reactive captor is DETECTED, not
listed — the extractor asks whether the engine gave the piece an
`assassin_squares` slot, so a queen in bishop form is covered.

It separates the blunder it was built for:

    rook f8-g4   ->  Pinned(black) 1 -> 2   (played; rook lost)
    rook f8-g6   ->  Pinned(black) 1 -> 1

Training: `scratchpad/pin_97{1,2,3}.json`, 800 games each, ablation
`('Attacked:', 'Hanging:', 'Threatens:', 'Flag:', 'RoyalForm:',
'PromotedQueenForm:', 'Pinned:')`. **Price by removal and race. Never
ship on a weight table.**

## Still open

- **g2 move 9** (bishop on e5 attacked, not moved) and **g2 move 23**
  (bishop reactive-captures onto a guarded square — reactive capture
  SKIPS the teleport-safety check). The `Pinned` weight may or may not
  reach these; they are about the bishop's own safety, not its victims'.
- **g2 move 30**, one pawn still walks into a capture.
- Self-captures: at depth 3 the agent chose zero of 156 available over
  49 positions, but a depth-2 race still logs a few.
- **How much the hand-written vocabulary buys** has never been measured.
  `features.generic` yields 8 features from the move generator alone
  (`Mobility`, `Reach`, `Moves:bishop`, `Captures:king`, `Type:move` —
  names discovered, not supplied). Train it and race it.

## THE NAMING DECISION: derive from the GDL

A reviewer asked whether the feature names are hand-picked, and whether
to keep hand-naming on Royal Chess for convenience or move to names
derived from the GDL alone. **Derive from the GDL.** Three reasons:

1. The project's claim is a framework for games it has not seen. A
   hand-written extractor per game makes that claim true only with
   human labour per game, which is the claim's negation.
2. The acceptance test is competence on an unseen ruleset. A
   hand-written adapter cannot pass it by construction.
3. The naming problem has an answer already in the file: the GDL names
   its own relations. `pile`, `control`, `at`, `fresh` are not
   inventions, they are that game's vocabulary.

**The hand-written Royal Chess extractor stays, as a measured
BASELINE** -- the number that says what human labour buys -- not as the
framework's answer. That gap has never been measured and should be
raced.

`lgref/experiments/gdl.py` is the general player: `GdlGame` puts any
`GGPGame` behind the learner's protocol, `features()` reads the state's
ground fluents. Measured, trained from zero, against a uniform mover:

    corridor.gdl    81 - 19    81.0%
    nim.gdl        110 - 10    91.7%

with weights that read as the games themselves (corridor:
`at@0is5 +0.62`, `at@0is1 -0.59`; nim: `pile@0is1 -0.996`,
`pile@0is2 +0.808`).

**It found two real bugs that neither Royal Chess nor m,n,k could**,
because both of those supply a written extractor and a real
`current_player`:

- `differentials` drops neutral owners, correctly -- but nim's whole
  state is `pile(5)`, owned by nobody, so the learner got ONE feature
  and lost 28-92. Shared quantities now belong to the side to move.
- at a terminal state every role holds only an idle move, so the mover
  fell through to `roles[0]` -- and `search._leaf` scores a finished
  position as `winner == current_player`. **Half of all terminal
  positions were read with the sign inverted**: 35% -> 91.7% on nim
  with the same weights.

Open: a game whose board constants are unrelated to its role names
(standard tic-tac-toe: roles `xplayer`/`oplayer`, marks `x`/`o`) gets
no ownership and reads as neutral. Binding constants to roles through
the GOAL rules is the next step.

## Are the feature names hand-picked?

Honest split, because a reviewer asked:

- **Discovered.** `Bishop`, `Rook`, `Knight`, `Pawn`, `King` come from
  `type(piece).__name__`, read off whatever is on the board. So does the
  `Form:` suffix. A new game's classes produce that game's names with no
  edit.
- **Hand-written.** `Royal`, `RoyalQueen`, `PromotedQueen`,
  `DownToOneRoyal` and the `Form:`/`FormAvailable:` prefixes are literal
  strings, keyed on this game's attributes (`is_royal`,
  `is_transformed`, `captured_pieces`).
- **One real leak.** `legacy.py` says the form list is "read from the
  engine's own mapping where it exposes one" — **the engine does not
  expose one**, so the hard-coded `('rook','bishop','knight')` fallback
  is always live. It is in the FROZEN extractor, which the shipped
  weights were fitted on, so it cannot be changed without retraining.
  The live extractor dropped `FormAvailable:` entirely.

Architecturally the adapter layer may know a game; the general modules
may not, and 28 audit tests enforce that. But "all of it derivable from
the GDL with no human intervention" is **not true today**.

## Entry points are now guarded

`lgref/play_mnk.py` declared `--budget` twice and **could not start** —
argparse raises while building the parser. It had 22 tests, every one of
which reached inside and called a function.

`tests/test_entry_points.py`: a static check over all 25 runnable
modules (no duplicate option strings; a `choices=` list must contain its
`default`); every module must compile; the playable ones run as
SUBPROCESSES; and a full m,n,k game through `--text`. Frozen snapshots
(`main_v0`, `main_v1`) have no parser at all, so `--help` hangs — they
get a "starts headless without exiting non-zero" check instead.

`tests/test_playable_agents.py` plays every selectable opponent at the
window's own `TD_DEPTH`/`TD_BUDGET_SECONDS` through
`Game._make_ai_player`. Five breakages in this issue reached a human
before a test, and each is reachable by starting the program and making
four moves.

## Instruments

| instrument | general? | for |
|---|---|---|
| `validate.removal_price` | yes — injected remover | what the evaluation charges for a piece |
| `validate.removal_columns` / `exclusive_columns` | yes | which columns belong to one piece alone |
| `validate.turn_leverage` | yes | which column decides a move |
| `validate.free_leverage` / `lever_columns` | yes | which columns the opponent can swing for free |
| `validate.rescue_oracle` | yes | the blunder metric's floor |
| `validate.exchange_opinions` | yes | whether a played-out exchange reads as a gain |
| `replicate.shared_variance` | yes | how much of a column the others explain |
| `record.audit` / `unsupported` | yes | unreplayable payloads; big weights on no data |
| head-to-head race (`scratchpad/race.py`) | yes | **the ship gate** |
| `scratchpad/sweep.py` hang/miss/regret | **NO** | `strong.material` is counts-only |
| `scratchpad/blunder_probe.py` | **BROKEN** | prices a trade from two weight names |

`scratchpad/replay.py` parses a v3 royal-notation save, so a reported
game can be reconstructed. **Replay a game before calling a move a
blunder** — it is the only thing in this issue that has reliably
contradicted an aggregate, in both directions.

## Rules adopted (keep these)

- **Race every change** against the current champion before shipping.
- **Measure the metric's floor and range** before reading a rate.
- **Verify an experiment changed what you think it changed** before
  reading its result: `record.audit` runs on every load.
- **Change one thing at a time.**
- **Test the front door**, not only the functions behind it.

## A failed design, recorded

Measuring piece values by **handicap races** (one side starts a bishop
short, the other a pawn short; the win rate gives the gap in log-odds
with no free parameter) **saturates**. At depth 1 losing a pawn and
losing a royal queen both land near p = 0.2: the agent cannot convert
graded material edges inside the ply cap. At depth 2 it is directionally
sensible but costs ~150 s/game, so 60 games gives a standard error wider
than the effect. Not usable at this strength.

## m,n,k

- Boards to 20×20×20, Go-style intersections with black first,
  seconds-per-move stepper (1–120 s).
- `--train-budget` is seconds of training per board size; `--budget` is
  seconds per move. **They were both `--budget`.**
- Weights train on a board sized to k and transfer: 300 games in 20 s on
  7×7 beats 60 in 41 s on 19×19.
- Depth at 5 s: 7×7 → 6, 9×9 → 4, 13×13 → 3, 19×19 → 2. **Depth cannot
  be constant across board SIZES**; it is constant across the phases of
  one game, and that is tested.

## Tests

~760 in `lgref/tests/`, plus `tests/test_entry_points.py` (72) and
`tests/test_playable_agents.py` (6). Key files:
`test_generality_audit.py` (28, no general module may name a game),
`test_record.py` (one per silent failure plus the support mechanism),
`test_pricing.py` (removal pricing, free leverage, every instrument run
on m,n,k), `test_shipped_weights.py` (one guard per blunder a human
found, priced by removal).
