# LGREF handoff — 2026-09-27

**Read this before `session_handoff_2026-09-23.md`.** That one describes
results that have since been withdrawn.

## The one thing to understand first

**Every measured statistic in this project is superseded** (#231). All
three sweeps were played by an agent that minimises the opponent's
legal-turn count, and `mean_branching` *counts legal turns* — the
instrument's objective was one of the metrics. That is circularity, not
bias. Demonstrated: removing the boulder raises branching by 6.6 turns
under that agent and **lowers** it by 3.4 under a player with no
objective. The sign belonged to the agent.

`lgref/experiments/mcts.py` had said in its own docstring from the start
that mobility is "the worst possible feature for this study". It was used
anyway, and a note declaring the substitution settled was added to the
designer's brief. Both corrected.

**Structural results (Phases 1–2) do not depend on an agent and stand.**

## Phase status

| phase | state |
|---|---|
| 0.5 cross-validation | done, ratcheted |
| 1 rule identification | done |
| 1b ablation operations | done |
| 2 function inference | done — 46 functions, all operationally defined |
| 3 measurement | machinery done; **no valid data** |
| 4 analysis | done — 13 dimensions, two-arm agreement, reachability |
| 5 recommendation | done — evidence matching, retain/revise/remove |
| 6–7 | not built |

## Run nothing without the gate

```bash
.venv/bin/python -m lgref.verify.run --agent random --plies 200
```

Nineteen checks; exits non-zero on any failure. **18 pass; the one
failure is the agent** and clears when the sweep switches to MCTS
(`MEASURING_AGENT` in `lgref/recommend/verdicts.py`).

It exists because ten defects were found in one session and **almost all
produced plausible numbers rather than errors**. It has already caught: a
config key (`agent:`) that nothing read, and two of my own mistakes — a
check that accused working code because it looked 24 plies deep at a rule
that appears at ply 82, and an ablation guard that landed in the *wrong
function* while the variant still behaved identically to the full game.

## The agent, with measured numbers

| | |
|---|---|
| simulation cost | **0.024 s** (was 0.22 — 9× after the playout fix and the engine work) |
| one full game @ 800 sims | **15.6 min** measured, not extrapolated |
| accuracy vs exact play | random 0.59, mobility 0.725, MCTS-800 **0.967**, chance 0.550 |
| self-agreement on Royal Chess | 200 sims 0/4, 800 sims 0/4, **2000 sims 2/4** |

**The search does not converge at any affordable budget** on a 53-wide
root. Another 10× means an array/bitboard board — a rewrite, not an
optimisation. So results will be agent-conditional whatever is spent, and
the two-arm design is how that is reported rather than hidden.

Why MCTS looked unaffordable: uniform rollouts ran 264 plies and **a
third returned no result**, scored as draws in a game with no draw
condition. A capture-preferring playout runs 40 plies with **zero**
censored. Objective unchanged — a rollout is still scored only by who won.

## Rules the games never reach

Zero tiny-endgame activations in 1440 games. The designer's diagnosis:
both that rule and the repetition rule need a niche position **plus**
near-optimal play from both sides, so imperfect agents never produce
them. `docs/spec/measuring-rare-rules.md` has the method:

    contribution = P(condition arises) × effect given it arises

"Never observed" is a **bound**, not a zero — 3/n at 95%, so 0.0021 for
1440 games, and ~14,400 games to expect 30 events. More games is not the
answer. Generalises because a rule's own clause guards *are* its
activation condition, and the parse already exists (#237).

## What to do next

1. Point the sweep at MCTS (config `agent:`, now actually consumed).
2. Run the gate. It must reach 19/19.
3. Pilot for cost, then a two-arm run: MCTS + random, **6 seed groups**
   rather than 3 — the between-seed term rests on the number of groups,
   not games per group.
4. Report only sign-agreeing effects (`lgref/analysis/arms.py`).
5. Then Phases 6–7.

## Things that are true and easy to get wrong

- **No draw condition.** An unfinished game is censored, not drawn.
- **`no_knight_redesign` ablates nothing it claims** (#228) — identical
  movement, a *broader* jump-capture, and *more* invulnerability. Use
  `no_knight_invulnerability`. Nothing measured through the old variant
  may be attributed to the redesign.
- **Board flags are class attributes on purpose.** Test helpers build
  boards with `Board.__new__(Board)`; instance attributes broke 17 tests.
- Seven columns have **no power** at pilot scale; the gate names them.
- `lgref/reference/` labels are read in Phases 4 **and 5**; the AST guard
  covers `identify/` and `functions/`, the packages that predict.
- Only 2 of 14 designer labels are `mapped_by: designer`; the rest are my
  translation awaiting review (`docs/spec/designer-intent.md`).

## Recurring mistakes

`memory/feedback_measurement_discipline.md`, plus from this session:
never place code by counting quote marks to find a docstring's end —
anchor on exact text; a differential check that cannot reach the rule it
judges must say **NOT EXERCISED**, not return a verdict; and state what a
denominator counts ("3 seed groups") in the same sentence as the verdict.
