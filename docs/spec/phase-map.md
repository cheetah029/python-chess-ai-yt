# Where the project actually is

Two documents number the work differently and both are current:
`project-execution-brief.md` has **Phases 0–7** (the build order) and
`project-overview.md` has **Phases A–G** (the research programme). They
are not alternatives — the brief's phases are how the overview's phases
get built. This maps them onto each other and states the status of each.

Status words mean exactly this:

- **done** — built, tested, and exercised on real data.
- **machinery done** — the code exists and is tested, but the result it
  is supposed to produce has not been produced.
- **partial** — some of it exists; what is missing is named.
- **not built** — nothing exists.

## The build order (brief Phases 0–7)

| phase | what it is | status |
|---|---|---|
| 0 | audit and plan | **done** |
| 1 | rule discovery from statements | **done** — typed statement graph, Louvain clustering with coverage-calibrated resolution |
| 2 | gameplay-role inference | **done** — 46 roles, every one operationally defined, with an expected direction per role recorded as data |
| 3 | ablation experiments and data collection | **partial** — machinery done and the CONTROL arm has valid data (132 games, 0 censored, 12/12 decisive per variant). The search arm has never been run with a valid agent |
| 4 | analysis | **done** — 13 dimensions, bootstrap intervals, variance decomposition, two-arm agreement, tie-aware ranking |
| 5 | recommendation engine | **done** — objective-indexed, refuses on wide intervals |
| 6 | evidence-constrained explanation | **not built** |
| 7 | results package | **not built** |

### Why Phase 3 is the one that is stuck

Three separate defects voided every measurement ever taken, and each had
to be fixed before any number could be trusted:

| issue | defect |
|---|---|
| #231 | the agent minimised the opponent's legal-turn count, and `mean_branching` COUNTS legal turns — the instrument's objective was one of the metrics |
| #247 | every simulation executed the caller's `Turn` on a deepcopy, and a `Turn` references a piece on the REAL board, so each simulated move wrote through to the live game |
| #255 | `list(set(...))` over piece-name strings ordered the legal-turn list by the interpreter's hash seed, so the same seed played a different game in every process |

All three are fixed and guarded by the 26-check pre-flight gate. What
remains is not a bug but a cost question, and the measurements say the
expensive option is the wrong one — see "the decision Phase 3 is waiting
on" below.

## The research programme (overview Phases A–G)

| phase | what it is | status |
|---|---|---|
| A | develop the framework using Royal Chess | **done** — this is what brief Phases 0–5 built |
| B | construct independent capability benchmarks | **partial** — one solvable game (tic-tac-toe) with an exact solver exists. The *set* of small games with recorded statement-to-rule mappings, shared statements, redundant and interacting rules, and dev/validation/held-out splits does NOT |
| C | develop and validate the MCTS evaluator | **partial** — exact-vs-search accuracy tests exist on the solvable game. Budget selection is not frozen, optimal-action rate and exact value loss are not reported, and the reliable envelope is not documented |
| D | freeze LGREF v1.0 | **not built** |
| E | test on held-out games | **not built** |
| F | analyse Royal Chess as a case study | **in progress** — the ablation work is this |
| G | measure resources and report impact | **partial** — `lgref/core/cost.py` tracks runtime and cost per run; no consolidated report |

## The thing this map exists to make visible

**Phase C is a prerequisite that has been skipped.** The overview is
explicit:

> Document which games and positions the evaluator can handle reliably
> **before using it as the measurement instrument for larger games.**

Royal Chess is the larger game. Its branching factor is ~68, and the
evaluator has been pointed at it without the envelope being established.
What is known about it is not reassuring:

- **#206** measured the search on Royal Chess as a *uniform sampler* —
  0% self-agreement, identical visit counts across all 65 root children.
- After the fixes, self-agreement is **2 of 4 at 2000 simulations**:
  better than uniform, nowhere near converged.
- The agent ladder then showed an effect **changing sign** between random
  play and a 40-simulation search, which is what an unconverged
  instrument does.

So the ordering problem is real, not theoretical. Phases B and C are the
gap between "we built a framework" and "we validated the instrument it
measures with", and they are also what Phase E (held-out games) depends
on — a held-out game needs benchmarks with hidden mappings, which is
Phase B.

## The decision Phase 3 is waiting on

The search arm costs **37–61 wall-hours** (measured: 43.8 s/ply at 800
simulations, 0.0548 s/simulation, games of 184–308 plies, 132 games at 8
workers). Two measurements say it would not buy what it looks like it
buys:

- at matched games a 40-simulation search resolved **0 of 22** cells
  where random play resolved **5**;
- quadrupling the random arm left resolvability flat at **2 of 10**
  variants.

More simulations do not buy resolvability and neither do more games. The
search arm's value is as the **second arm of the agreement test** — a
single arm can carry the wrong sign — not as a way to resolve more cells.

Meanwhile the agent-free route (#242) resolves effects at t = 11–162 in
seconds, and reaches a rule play never touches. So the order that the
evidence supports is: finish Phase C, then run the search arm as an
agreement arm on a budget chosen knowing what it resolves.
