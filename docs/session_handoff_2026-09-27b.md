# LGREF handoff — 2026-09-27 (later)

Supersedes `session_handoff_2026-09-27.md`, which supersedes the
2026-09-23 one. Read only this.

## Read this paragraph first

**Every measured statistic in this project is withdrawn** (#231). All
three sweeps were played by an agent that minimises the opponent's
legal-turn count, while `mean_branching` *counts legal turns* — the
instrument's objective was one of the metrics. Not a bias: a
circularity. Proof: removing the boulder raises branching 6.6 turns
under that agent and **lowers** it 3.4 under a player with no
objective.

**Structural results (Phases 1–2) do not depend on an agent and stand.**

## State

| phase | state |
|---|---|
| 0.5–2 | done. 46 functions, all operationally defined |
| 3 measurement | machinery done, **no valid data yet** |
| 4 analysis | done — 13 dimensions, two-arm agreement, reachability |
| 5 recommendation | done |
| 6–7 | not built |

## The next action, exactly

```bash
# 1. the gate must reach 19/19 before anything is run
.venv/bin/python -m lgref.verify.run --agent mcts --simulations 40 --plies 200

# 2. the strong arm: 132 games, ~4.3 wall-hours at 8 workers
.venv/bin/python -u -m lgref.experiments.pilot \
    --config lgref/config/phase4_twoarm.yaml --run-id twoarm-mcts

# 3. the control arm, nearly free — same config, agent: random
#    (copy the config, change `agent`, use --run-id twoarm-random)

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
| simulation cost | 0.024 s (was 0.22 — 9×) |
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
