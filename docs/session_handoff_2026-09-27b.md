# LGREF handoff — 2026-09-27 (later)

Supersedes `session_handoff_2026-09-27.md`, which supersedes the
2026-09-23 one. Read only this.

## Read this paragraph first

**Every measured statistic in this project is withdrawn**, for THREE
independent reasons. Any one of them alone would be enough.

| # | what was wrong | why it voids the numbers |
|---|---|---|
| #231 | the agent minimised the opponent's legal-turn count, and `mean_branching` COUNTS legal turns | the instrument's objective was one of the metrics — a circularity, not a bias |
| #247 | every simulation executed the caller's `Turn` on a deepcopy, and a `Turn` holds a reference to a piece on the REAL board | each simulated move wrote cooldown/moved/last-square through to the live game |
| #255 | `list(set(captured))` over piece-name strings ordered the legal-turn list by the interpreter's hash seed | the same seed played a different game in every process, so nothing reproduces |

**Structural results (Phases 1–2) do not depend on an agent and stand.**

### Reason one, in full (#231)

All three sweeps were played by an agent that minimises the opponent's
legal-turn count, while `mean_branching` *counts legal turns*. Proof:
removing the boulder raises branching 6.6 turns under that agent and
**lowers** it 3.4 under a player with no objective.

## State

| phase | state |
|---|---|
| 0.5–2 | done. 46 functions, all operationally defined |
| 3 measurement | machinery done, **no valid data yet** |
| 4 analysis | done — 13 dimensions, two-arm agreement, reachability |
| 5 recommendation | done |
| 6–7 | not built |

## Gate status

**CONFIRMED GREEN: 25 checks, 0 failed** (exit 0), under
`--agent mcts --simulations 40 --plies 200` at the run's own cap of
1600. The two lines that were defects before:

```
PASS  pilot games reach a result   all 4 finished; at 4 games that bounds
                                   the censored share at 75%, not at zero
PASS  both players are sampled     white=76 black=76
```

Nothing censored, where the previous run cut off one game in four. The
no-power list also shrank from 7 columns to 6 -- `response_turns` gained
power once games finish instead of being cut off, which is a second
measurement the old cap was quietly costing.

The run before this one reported **23 checks, 0 failed** — and that clean
verdict still hid a defect, which is the lesson of this section.

### What a PASS was hiding (#254)

The run's own line read:

```
PASS  pilot games reach a result    1 of 4 censored — outcome columns are thinner than they look
```

A quarter of the pilot's games were cut off and the gate called it a
pass. Three things were wrong at once:

1. **The gate ran below its own floor.** `OUTCOME_SAFE_TURN_CAP` is
   800 and `require_outcome_safe_cap` exists to refuse anything lower.
   `pilot.py` calls it; `lgref/verify/run.py` never did, and defaulted
   to **400**. The component whose job is to refuse an invalid
   configuration was running under one.
2. **The check only refused TOTAL censoring**, while its docstring, the
   argparse comment and this handoff all said it "refuses a cap that
   censors". It now refuses any.
3. **The cap itself was in the tail.** `max_turns` was 1000; the
   longest game in the #204 sample was 949. It is now
   `CENSOR_FREE_TURN_CAP = 1600`, the level where all forty finished —
   which costs almost nothing, since the bill is the sum of game
   LENGTHS and only the censored tail runs on.

### And a claim that was simply backwards

The code asserted, with a test pinning it, that *a weaker search needs a
longer cap because a cheap search plays on longer*. Measured at cap
1600:

| seed 0 | plies |
|---|---|
| random play | 689 |
| MCTS, 40 simulations | **184** |

Search SHORTENS games — it finds the win instead of shuffling toward
it. So the random-play table in #204 is an upper bound on what any
search needs, which is what lets the cap be set from it. The pilot was
never slow because of the cap; it is slow because a ply costs 2.1s of
thinking.

### The earlier run, for history

An earlier full run reported **21 checks, 1 failed** — `white_win`
constant across the pilot. Diagnosed: **every pilot game hit the turn
cap** (`winner=None`, `capped=True`, four of four). Not a result,
censoring — and the cause was mine, lowering the pilot cap to 120 to
make the gate cheap. There is no draw condition, so a capped game is
censored and every outcome column goes False for reasons unrelated to
the rules.

Fixed at the time by `check_pilot_games_finish` plus a pilot cap of
400 — both of which #254 then had to fix again, above: the check only
refused TOTAL censoring, and 400 is below the project's own floor. The
constant-column check defers to it when every game is capped, so the
cause is not buried under its consequences.

**The conclusion drawn here was wrong** and is recorded only so the
correction has something to point at. It read: *"a weaker pilot agent
needs a LONGER cap, not a shorter one — the cheap search plays on longer
than the run's agent."* Measured at cap 1600, seed 0: random play 689
plies, a 40-simulation search 184. Search shortens games. The pilot was
slow because a ply costs 2.14s of thinking, not because of the cap, and
lowering the cap bought censored games rather than speed.

The gate now runs **26 checks**: 1 control identity + 9 per-variant
replays + 10 pre-pilot + 6 pilot. It ran 23 before #254 and #255 added one
each. Earlier handoffs said 24, which was never right -- count the
`record(checks.` calls plus the variant loop rather than trusting the
prose. The ones that caught the worst defects:

- `choosing a move leaves the board unchanged` — fingerprints every
  piece's position, cooldown, moved, invulnerable, freeze,
  reactive-armed and last-square before and after an agent thinks
- `pilot games reach a result` — refuses a cap that censors AT ALL,
  because a censored game makes every outcome column False for reasons
  unrelated to the rules
- `the turn cap does not censor` — reads the cap instead of the pilot.
  Four games that all finish bound the censored share at 75% by the rule
  of three, so the pilot cannot establish this and never could
- `a seed reproduces its run in another process` — replays a seed under
  a different `PYTHONHASHSEED` and compares a checksum of every move

Pilot defaults: **one game per seed group** at the run's own cap of
1600. The cap is no longer the cheap knob it was treated as -- a gate
that verifies a cheaper configuration than the run verifies the wrong
thing -- so what stays small is the NUMBER of pilot games, not their
length.

## Manipulation is NOT broken — the agent just never picks it (#257)

Raised because a positive control asserting "the full variant uses
manipulation" failed. It is not an engine defect. Under uniform-random
play over 6 games and 1,667 plies:

```
plies OFFERING manipulation   240   (14.4% of plies)
manipulation turns offered   2800   of 125,843 legal turns (2.2%)
manipulation turns CHOSEN      36   expected if uniform: 37.1
manipulation turns RECORDED    36
```

Offered, chosen at almost exactly the uniform rate, executed, and
recorded. The engine is correct end to end.

What the control actually caught is that the **mobility agent** takes an
argmax over ~70 options, and an action that is 2.2% of the menu never
ranked first in 8 games. That is an agent property, not a rule one, and
the control now tests whether manipulation is OFFERED — which is what an
ablation removes — rather than whether some agent chose it.

## The search's descriptions are not injective, and that is fine (#257)

`describe()` reduces a Turn to plain data so the tree holds no reference
to a live board (the #247 fix), and `resolve()` maps it back by taking
the FIRST legal turn that matches. Measured over 62,033 descriptions:
**1.3% are shared by two or more distinct legal turns.**

The cause is the variant's rook — one square orthogonally, then a 90°
turn and a sweep — so (0,5) → (1,6) exists as up-then-right and
right-then-up, and only the endpoints are recorded.

It is nevertheless sound. Executing every member of each collision group
and fingerprinting the result (positions, royal/transformed markers,
invulnerability, manipulation freeze, moved-last-turn, reactive-armed,
cooldown, last-square, side to move):

```
collision groups with IDENTICAL result:  {'move': 381, 'manipulation': 1}
collision groups with DIFFERENT result:  none
```

`describe` is injective **up to resulting state**, which is the property
the search needs. Now checked by the gate rather than assumed: if a rule
ever makes the rook's path observable, the search would explore one turn
and play another with no error at all.

## The run watches itself now (`lgref/experiments/health.py`)

The gate checks what would invalidate a run BEFORE it starts. It cannot
see what breaks at game 80 of 132, and at 37–61 wall-hours that
distinction is most of the budget. `RunHealth` is wired into
`lgref.experiments.pilot` and **aborts on the first row that is not a
measurement**.

Three layers, cheapest first:

1. **Every row, as it arrives** — censored game, missing column, an
   `agent` field holding an object instead of a name (#230), the wrong
   agent or simulation budget, a variant the config does not list, a
   zero-length game.
2. **A canary, every `canary_every` games** — one fixed-seed random game
   whose move sequence is checksummed at startup and re-checksummed
   later, about 0.2s. It notices anything that changes what the engine
   does mid-run: a variant flag leaking between pool jobs, a mutated
   class attribute, an interpreter that stopped reproducing. The gate
   proves determinism BEFORE the run; this proves it stayed that way
   DURING it. It also re-reads every variant's ablation switches and
   compares them to startup.
3. **Running aggregates** — constant columns named at game 20 rather
   than at the end, with the rare ones exempted, and with
   `turn_cap_reached` / `draw_or_censored` / `decisive` exempted while
   nothing is censored, because those being constant is SUCCESS. (The
   gate's own version of this check reported success as a defect once,
   #253; the same mistake was made here and measured out.)

Verified end to end on `lgref/config/smoke_health.yaml` — 8 random-play
games, 4 canary checks, 0 censored, per-variant decisive counts — and
every failure mode has a test that proves it is caught.

Worker reuse was checked directly, since the pool runs `no_boulder` and
`full` in the same interpreter: the ablation switches are INSTANCE
attributes with `True` defaults, and a sequence of eight interleaved
variants restored every switch on every `full`.

## THE SEED DID NOT NAME THE GAME (#255)

Found while checking the cap, and worse than the thing being checked.
Identical call, three consecutive processes:

```
play_one('full', seed=0, max_turns=1600, agent='random')
  -> 689 plies, white     -> 304 plies, black     -> 236 plies, black
```

`Board.get_transformation_options` built its list with
`list(set(captured))` over piece-name STRINGS. CPython randomises string
hashing per process, so the option order differed in every run, reached
the legal-turn list, and an agent picking `turns[rng.randrange(...)]`
chose a different turn from the SAME RNG draw. Fixing
`PYTHONHASHSEED` made it reproduce 4 of 4.

Fixed with `sorted(set(captured))`. The rulebook offers a SET of forms
("rook, bishop, or knight — provided a friendly piece of that type has
been captured earlier"), so nothing ranks them and only the instability
was wrong.

**Why the gate said "a seed reproduces its run — PASS".** It replayed
the seed twice in ONE process, and one process has one hash seed, so
both replays scrambled identically. No number of in-process repeats
could have found this.

**And the sweep is multi-process.** `n_workers: 8`, and multiprocessing
uses spawn on macOS, so each worker had its own hash seed: the same seed
produced a different game depending on which worker took the job. The
rows would not have been reproducible from their own manifests.

This is the THIRD independent reason every measurement so far is void,
after #231 (agent objective) and #247 (simulation contamination). Unlike
those two it would have survived into the published artefact.

## The run costs an order of magnitude more than planned (#254)

**MEASURE THIS AGAIN BEFORE COMMITTING THE MACHINE.** The plan said
132 games at ~4.3 wall-hours on 8 workers. Measured directly, at the
run's own budget of 800 simulations, over 8 plies with branching 56-79:

```
43.8 s per ply        0.0548 s per simulation
```

The handoff's own table said 0.024 s per simulation; the measurement is
2.3x that. And a game is not short:

| agent | plies |
|---|---|
| random | median ~340, max 865 |
| MCTS, 40 sims | 184 and 308 |

At 43.8 s/ply and 184-308 plies, ONE game at 800 simulations costs
2.2-3.7 hours. For 132 games:

```
296 - 490 core-hours  ->  37 - 61 wall-hours at 8 workers
```

not 4.3. The 4.3 figure implies 0.0064 s/simulation, which is 8.5x
faster than anything measured here; it was almost certainly carried
over from the superseded mobility agent, whose per-move cost is not
comparable.

**Where the time goes**, measured from a mid-game position rather than
guessed:

```
one rollout            0.0628 s      87% of a simulation
deepcopy(engine)       0.0094 s      13%
get_all_legal_turns    0.0014 s
```

`MCTSPlayer.choose_turn` deepcopies the engine once per simulation --
800 whole-engine copies per ply -- but that is the CHEAP half. A rollout
costs 45x one legal-move generation, i.e. it runs roughly 45 plies deep
before something terminates it. Optimising the copy would buy 13%;
the rollout is the only lever that matters.

That lever is also the constrained one: `rollout_depth` is already 200
and `censored_share` is reported as a measurement FAILURE, so truncating
rollouts trades time for exactly the thing the gate refuses. A cheaper
playout policy would have to stay win-condition-only to avoid
reintroducing #231.

**The honest options**, none of them free:

- fewer simulations (weakens the agent, and agent strength is exactly
  what the two-arm design is trying to hold up)
- fewer games (widens every interval)
- make-unmake instead of deepcopy, or a cheaper rollout (a value
  heuristic would reintroduce the objective bias #231 was raised to
  remove)
- spend the 37-61 hours

This is a decision for the human, not a default to pick.

## What the first valid dataset showed (random arm, 132 games)

The control arm ran clean: 132 games, **0 censored**, 13 canary checks,
every variant 12 of 12 decisive, white/black balanced (6/6, 7/5, 5/7 —
which also disposes of the earlier "one side loses every time"). The
pipeline works end to end: pilot -> analysis -> recommend.

It also produced the two defects in `#259` and `#260`, both in the
PRIMARY output, which is the argument for running the cheap arm first.

### More games do not help (measured)

| seed groups | games | effect | inconclusive | seed-dominated | ranked |
|---|---|---|---|---|---|
| 6 | 132 | 11 | 66 | 33 | 2/10 |
| 12 | 264 | 9 | 68 | 33 | 2/10 |
| 24 | 528 | 13 | 74 | 23 | 2/10 |

**Quadrupling the sample leaves resolvability flat at 2 of 10 variants.**
Most cells are `inconclusive` -- the bootstrap interval spans zero -- so
the effects are genuinely small relative to noise under random play. That
is what one would expect if these rules matter only under purposeful
play, and it is an argument that the search arm is NECESSARY rather than
redundant. It is not proof of that: the alternative reading is that the
effects are small full stop.

### A ladder too small to read (a mistake worth not repeating)

The first agent-strength ladder used 4 games per variant:

```
sims     effects   max|d|
   0           5     1.35
  20           4     5.26
  40           0        -
```

This says nothing about whether strength helps. `cohens_d` standardises
by a pooled variance estimated from 4 points, so a near-constant metric
produces a huge finite d that passes every filter -- 5.26 at one rung and
nothing at the next is the signature of small-sample instability, not a
trend. Re-run at 12 games per variant, matching the real design.

DO NOT read a rung comparison whose per-variant game count is below the
real design's. It was tempting to report "effects do not grow with
strength" from the table above, and that would have been the same error
as the boulder 1% claim.

## The ladder at real power, and what it means for the budget

Re-run at 12 games per variant, matching the design (3 variants, 6 seed
groups x 2 games), 0 censored at both rungs:

| sims | games | cells | effect | inconclusive | seed-dom | max abs d |
|---|---|---|---|---|---|---|
| 0 (random) | 36 | 22 | **5** | 17 | 0 | 0.99 |
| 40 (MCTS) | 36 | 22 | **0** | 22 | 0 | - |

Search resolved FEWER effects, not more, and every cell was
`inconclusive` -- interval spans zero -- rather than seed-dominated. That
happens either because the spread grew or because the difference shrank,
and the two have opposite consequences. Measured:

| metric | diff @0 | diff @40 | sd ratio |
|---|---|---|---|
| `mean_branching` | **-5.22** | **+2.17** | 1.14 |
| `mean_attack_coverage` | +0.70 | +1.42 | 1.39 |
| `total_turns` | -36.4 | -56.5 | 1.16 |
| `mean_reachable_mover` | -2.42 | -0.80 | 0.94 |
| `mean_denied_squares` | +2.16 | +0.29 | 0.77 |

**The spread barely moved (0.77-1.39). The DIFFERENCES moved, and
`mean_branching` FLIPPED SIGN.** Removing the boulder lowers branching
under random play and raises it under a 40-simulation search -- the same
direction change #231 recorded for the mobility agent.

STATED CAREFULLY: this is 12 games per variant, one ablation, and the
interval spans zero, so it is not an established sign flip. It is
consistent with the boulder's branching effect being agent-dependent, and
it is the second independent agent for which the sign differs from random
play. It must not be written up as a finding on this evidence.

### What this says about the 37-61 hour run

Three things, none of them "just run it":

1. **More simulations do not buy resolvability.** At matched games, 40
   sims resolved 0 of 22 where random resolved 5. Nothing suggests 800
   sims reverses that; the differences are small and the spread is
   comparable, so 132 games at 800 sims would likely produce a mostly
   inconclusive table for 37-61 hours.
2. **More games do not buy it either.** Quadrupling the random arm left
   resolvability flat at 2 of 10 variants.
3. **But the agent still matters for VALIDITY.** The sign flip means a
   single-arm result can carry the wrong sign, so a cheap arm is not a
   substitute -- it is one arm of a test that needs two.

The escape is not a bigger play-based run. It is the two routes that do
not depend on an agent at all:

- **#242 policy-independent position sampling** -- the structural half of
  the profile (branching, coverage, reach, denial) measured over
  positions sampled without a policy. Agent-independent BY
  CONSTRUCTION, and cheap: no games to play.
- **#244 exact endgame solution** -- exact values on a defined subspace,
  which is agent-independent for the same reason.

RECOMMENDATION: do #242 before spending the machine on the search arm.
It addresses the objectivity requirement directly rather than hoping a
stronger agent converges, and it costs hours rather than days. The search
arm remains worth running afterwards as the second arm of the agreement
test, on a budget chosen knowing it will resolve few cells.

## Route 2 is built: structural metrics with no agent at all (#242)

`lgref/experiments/positions.py`. Positions are CONSTRUCTED by placement,
so no policy chose them, and each is measured under the baseline AND the
ablation, so only the RULE differs. Position variance cancels within the
pair instead of being averaged away with more games -- which is #241
arriving for free and is why this resolves what 12 games of play could
not.

```
.venv/bin/python -m lgref.experiments.positions --positions 200
```

### The controls first, because a method that invents differences is worse than none

| variant | verdict |
|---|---|
| `control_inert` (rule-identical) | **exactly zero on all 17 metrics, sd 0** |
| `no_boulder` | structural effect, branching **t = -12.4** |
| `no_queen_manipulation` | structural effect, branching **t = -14.2** |

The rule-identical control reading exact zero across 200 positions is the
noise floor, and it is what makes the rest credible.

### It settles the sign the agents disagreed on

| how measured | boulder's effect on branching |
|---|---|
| random play | **-5.22** |
| 40-simulation search | **+2.17** |
| **no policy at all** | **-3.41 (t = -12.4)** |

Removing the boulder LOWERS branching. The positive sign under search is
a property of which positions search visits, not of the rule.

### And it measures a rule play never reaches

The gate reports `no_tiny_endgame` as NOT EXERCISED across 200 plies of
four lines. Its precondition is no pawns, at most six non-king pieces and
a balanced position; its restriction then bites only once a royal distance
has occurred three times. Sampled in that regime -- `--endgame
--saturate`, which activates it in 150 of 150 positions:

```
legal_branching             +52.78     nonzero 150/150
reachable_squares_mover     +34.33
denied_squares              -34.14
```

**The rule removes about fifty-three legal turns per position** in its
binding regime. That is a measurement of a rule the play-based pipeline
cannot reach at all, and it bounds the rule's maximum influence rather
than averaging it over play.

### A zero here has THREE meanings, and the code says which

Reporting an absence as a measured zero is #259's mistake, so `classify`
distinguishes:

- `control_inert` -- rule-identical, zero is correct and meaningful;
- `no_knight_invulnerability`, `no_bishop_reactive`, `no_repetition_rule`
  -- the mechanism needs per-piece state only PLAY sets (a jump grants
  invulnerability; arming depends on where the last move began), so a
  constructed position has nothing to remove: **not exercised**;
- `no_tiny_endgame` -- the rule's precondition is not met by the default
  material: **not exercised by this sampling regime**, with the regime
  that does exercise it named.

### What it cannot do, stated rather than hidden

Outcome metrics -- win rate, decisiveness, game length -- are properties
of PLAY and cannot be freed this way; `docs/spec/objectivity.md` says so
and this module repeats it. A constructed position may also be
unreachable in real play, which is the price of dropping the policy.

## The next action, exactly

```bash
# 0. re-run the gate end to end; it must reach 26/26
.venv/bin/python -m lgref.verify.run --agent mcts --simulations 40 --plies 200

# 1. DECIDE THE BUDGET FIRST. 132 games is 37-61 wall-hours at these
#    settings, not the 4.3 this file used to claim -- see "The run
#    costs an order of magnitude more than planned" above. Do not start
#    this without choosing between fewer simulations, fewer games, a
#    cheaper rollout, or the time.

# 2. the strong arm
.venv/bin/python -u -m lgref.experiments.pilot \
    --config lgref/config/phase4_twoarm.yaml --run-id twoarm-mcts

# 3. the control arm, nearly free (a random game costs ~0.5s).
#    It is a FILE now, not a hand-edit: a copied config is where a seed
#    list drifts, and a drifted arm confounds the only comparison that
#    can tell a rule effect from an agent effect. A test asserts the two
#    differ in exactly `agent` and `agent_simulations`.
.venv/bin/python -u -m lgref.experiments.pilot \
    --config lgref/config/phase4_twoarm_random.yaml --run-id twoarm-random

# 4. then
.venv/bin/python -m lgref.analysis.run      --results results/lgref/twoarm-mcts
.venv/bin/python -m lgref.recommend.run     --results results/lgref/twoarm-mcts
# and the cross-check that decides what may be reported at all:
#   lgref/analysis/arms.py  compare(rows)  over BOTH runs' rows
```

The run is 11 variants × **6 seed groups** × 2 games. Six not three:
`variance_share` takes its between-seed term from the variance of the
*group means*, so it rests on the number of groups however many games
back them.

## Objectivity — the live question (`docs/spec/objectivity.md`)

The designer rejected "effects are agent-conditional" as abandoning the
project's purpose, and was right. **Converging a search was never the
only route**; two of the four routes remove the agent entirely:

| route | buys | agent-free? | issue |
|---|---|---|---|
| 4 paired designs (common random numbers) | more resolved cells at the same cost | no | #241 |
| 2 policy-free position sampling | the structural half of the profile | **yes** | #242 |
| 3 agent ladder + trend | a measured trend toward the limit | quantified | #243 |
| 1 exact endgame solution | exact values on a defined subspace | **yes** | #244 |

**Route 1 is the prize**, and it lands exactly where the current method
fails: the tiny endgame and repetition rules are unreachable by play
*and* live in the low-piece-count subspace where retrograde analysis is
tractable. The state encoding already exists — `RULEBOOK.md`'s
repetition section defines the state and `src/` computes the hash.

Route 3 is **built**: `arms.ladder()` and `arms.trend()`, which reports
`settling` / `unstable` / `too few` (two points always look like a
line). Order the arms weakest-first by measured accuracy against exact
play.

What stays conditional: outcome metrics on full-board midgame positions
at branching ~53. That is a quantified residue, not a shrug.

## The caveat that governs what may be claimed

The search **does not converge**. Self-agreement on a 53-wide root is
2 of 4 at 2000 simulations — the same position with two seeds gives
different moves half the time. Another 10× of engine speed would need
an array/bitboard board: a rewrite, not an optimisation.

So effects are **conditional on this agent**, always. The two-arm design
does not remove that; it makes it visible. An effect whose **sign
differs** between arms is a property of the agent and must not be
reported as a property of a rule (`lgref/analysis/arms.py`). An effect
agreeing across arms is *not proven* independent — two agents can share
a bias — but disagreement is disproof, and one arm cannot run the test.

The paper can claim: "under these two agents, these effects are stable
and these are agent-dependent." It cannot claim "this is the rule's
effect under optimal play".

## Agent facts, measured

| | |
|---|---|
| simulation cost | 0.0548 s measured at 800 sims (#254). The 0.024 s recorded here earlier does not reproduce |
| one game @ 800 sims | **15.6 min**, measured not extrapolated |
| accuracy vs exact play | random 0.59, mobility 0.725, MCTS-800 **0.967**, chance 0.550 |

Why MCTS looked unaffordable: uniform rollouts ran 264 plies and **a
third returned no result**, scored as draws in a game with no draw
condition. Capture-preferring playout: 40 plies, **zero** censored.
Objective unchanged — a rollout is still scored only by who won.

## Rules the games never reach

Zero tiny-endgame activations in 1440 games. Both that rule and the
repetition rule need a niche position **plus** near-optimal play from
both sides. `docs/spec/measuring-rare-rules.md`:

    contribution = P(condition arises) × effect given it arises

"Never observed" is a **bound** not a zero — 3/n at 95%, so 0.0021 for
1440 games and ~14,400 games to expect 30 events. More games is not the
answer. Generalises because a rule's own clause guards *are* its
activation condition and the parse already exists (#237).

## All four objectivity routes are the plan, not one

They cover different things and do not substitute for each other:

- **2 and 1 are the only agent-free ones**, and they cover *different
  halves*. Route 2 makes the position-space metrics objective (coverage,
  denial, branching, material). Route 1 makes the outcome metrics exact,
  but only in the low-piece subspace.
- **3 covers what neither reaches**: outcome metrics in full-board
  midgame positions, where exact solution is impossible. It turns that
  residue into a measured trend with a bound instead of a shrug.
- **4 buys nothing on its own** and multiplies all three, which is why
  it goes first: 31 of 49 cells came back seed-dominated, and common
  random numbers is the cheapest way to resolve more of them.

Do 4, then 2, then 3, then 1.

## The boulder is nearly immobile under search play (#247)

Measured over 300 turns each, same engine, `full`:

| agent | turns where a boulder move is LEGAL |
|---|---|
| random | 261 of 300 (**87%**) |
| MCTS (40 sims) | 3 of 300 (**1%**) |

`shared_object_influence` is the designer's stated **primary** function
for the boulder. If the piece is immobile under competent play, that
function is close to inoperative there — a finding, and exactly what
the two-arm design exists to surface. It also explains why
`turns_boulder` and `shared_entity_turns` come back constant-zero in an
MCTS pilot; those columns are not broken.

**The mechanism is NOT established.** In one traced game the boulder
leaves the intersection early and then has zero legal moves while all
four central squares are empty — which rules out the obvious blocking
explanation. It is not captured. A bug in the boulder's state after a
deepcopy in search has **not** been excluded, and must be before either
arm's boulder numbers are trusted.

## Traps

- **`identify` and `functions` reported different partitions** under the
  same rule IDs — 20 rules against 55, with `R00` naming a 223-clause
  cluster in one and a 44-clause one in the other. Every subcommand now
  goes through `main._cluster_for`, which calibrates when the caller
  left the resolution at its default.
- **Agent switches empty columns silently.** `MCTSPlayer` exposed
  `last_root_values` but the metrics read `last_scores`, so four
  columns went blank including a profile dimension. Nothing errored;
  the gate caught it. Any new agent must expose `last_scores` AND
  `score_tolerance` — "near-optimal" is in the agent's own units (win
  rate 0.05 for MCTS, one legal turn for mobility).

- **No draw condition.** An unfinished game is censored, not drawn.
- **`no_knight_redesign` ablates nothing it claims** (#228): identical
  movement, *broader* jump-capture, *more* invulnerability. Use
  `no_knight_invulnerability`.
- **Board ablation flags are class attributes** — test helpers build
  boards with `Board.__new__(Board)`; instance attributes broke 17 tests.
- **`mobility` is refused by the gate.** It exists only to reproduce
  withdrawn runs.
- Seven columns have **no power** at pilot scale; the gate names them.
- Only 2 of 14 designer labels are `mapped_by: designer`; the rest are
  my translation awaiting review (`docs/spec/designer-intent.md`).

## Recurring mistakes

`memory/feedback_measurement_discipline.md`, plus this session: never
place code by counting quote marks to find a docstring's end — anchor on
exact text (a guard landed in the wrong function and gated nothing while
the variant looked identical to the full game); a differential check that
cannot reach the rule it judges must say **NOT EXERCISED**, not return a
verdict; and name what a denominator counts ("3 seed groups") in the same
sentence as the verdict.
