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

## Where the current work sits (2026-11-27)

Three tracks run in parallel. All three belong to this plan; none is a
side project. In short: the build order (0–7) is where it was, stuck at
Phase 3 with 6 and 7 not built. The current work is in programme Phases
B, C, D and E, which validate what Phases 1 and 3 built.

| Track | Issue(s) | Brief phase it serves | Programme phase it is | What it changes on this map |
|---|---|---|---|---|
| **Paper A**: does LGREF recover a game's rules? Groupings compared with 10 other methods on development games, then frozen and tested on held-out games. | #347, #350, #351, #358 | **1** (rule discovery) and **3** (its ablations), measured rather than assumed | **B** (benchmarks with recorded statement-to-rule mappings and dev/test splits, which is Paper A's stage 1), **D** (the freeze, stage 4), **E** (held-out games, stage 5) | B moves from *partial* toward *done*. D and E get built for the rule-identification half. Stages 1–3 are merged; stage 4 is running. |
| **Version tables**: every player version against fixed baselines on Royal Chess, three m,n,k boards, Nim and the GDL-II games. | #282, #349 | **3**: the search arm "has never been run with a valid agent", and these tables say which agent is valid where | **C** (document which games the player handles reliably, before using it as an instrument) and **G** (measured cost per game) | C gains a measured strength envelope per game. Filling every cell to n=100 first takes about 2 days, then 200, 300, 400. |
| **Depth 4 (V7)** and search speed | #278, #279 | **3**: a stronger and cheaper agent for the search arm | **C** (the player is the instrument) | V7 (depth 4) beat depth 3 at 92.5% [80.1, 97.4]. Search changes 13–19 are merged, the last one 1.81× faster by compiling. The game window switches to depth 4 after a per-phase check. |

**What this map does not yet reflect.** Its Phase C section above was
written about the MCTS evaluator. The players measured today are the
TD-learned alpha-beta versions, V4 and V7 (`docs/agent-versions.md`),
and their envelope is what the version tables are filling in. Phase 6
(evidence-constrained explanation) and Phase 7 (results package) are
still not built. Paper A's results package will be the first piece of
Phase 7.

## The research programme (overview Phases A–G)

| phase | what it is | status |
|---|---|---|
| A | develop the framework using Royal Chess | **done** — this is what brief Phases 0–5 built |
| B | construct independent capability benchmarks | **partial, in progress (Paper A)** — one solvable game (tic-tac-toe) with an exact solver exists. The *set* of small games with recorded statement-to-rule mappings, shared statements, redundant and interacting rules, and dev/validation/held-out splits does NOT |
| C | develop and validate the MCTS evaluator | **partial, in progress (version tables, V7)** — exact-vs-search accuracy tests exist on the solvable game. Budget selection is not frozen, optimal-action rate and exact value loss are not reported, and the reliable envelope is not documented |
| D | freeze LGREF v1.0 | **in progress for rule identification (Paper A stage 4)** |
| E | test on held-out games | **planned (Paper A stage 5)** |
| F | analyse Royal Chess as a case study | **in progress** — the ablation work is this |
| G | measure resources and report impact | **partial** — `lgref/core/cost.py` tracks runtime and cost per run; no consolidated report |

## The thing this map exists to make visible

**Phase C is a prerequisite that has been skipped.** The overview is
explicit:

> Document which games and positions the evaluator can handle reliably
> **before using it as the measurement instrument for larger games.**

Royal Chess is the larger game. Its branching factor is ~68, and the
evaluator has been pointed at it without the envelope being established.
It has now been measured, and the answer is that Royal Chess is
**outside** the envelope at any affordable budget.

**The implementation is sound.** On tic-tac-toe — solved, branching ≤ 9,
scored against the SET of optimal moves — it converges:

| sims | optimal-action | mean value loss |
|---|---|---|
| 10 | 72.5% | 0.375 |
| 40 | 80.0% | 0.237 |
| 160 | **95.0%** | 0.075 |

**The budget is the problem, and it scales badly.** On m,n,k games where
the branching factor is chosen:

| branching | 10 sims | 40 sims | 160 sims | chance |
|---|---|---|---|---|
| 6 | 68.8% | **100%** | 100% | 25% |
| 9 | 68.8% | 75.0% | **100%** | 40% |
| 12 | 25.0% | 43.8% | 62.5% | 22% |

40 simulations suffice at branching 6, 160 at 9, and at 12 even 160
reaches only 62.5%. The requirement grows far faster than linearly.

**On Royal Chess, branching ~58**, self-agreement — two searches of the
same position — against a chance baseline of 1/58 = 1.7%:

| sims | self-agreement | seconds for 12 searches |
|---|---|---|
| 10, 40, 160, 400, 800 | **0.0%** | — |
| 2000 | 16.7% (1 of 6) | 596 |

**At 800 simulations — the budget the planned run was configured for —
the search never reproduces its own choice.** The first non-zero point is
2000, and one hit in six positions is weak evidence of anything: the
interval on 16.7% from n = 6 spans roughly 0.4% to 64%.

The cost of going further is decisive. 2000 simulations took 596s for 12
searches — about 50s per move — so one game is ~3.5 hours and 132 games
is ~58 wall-hours, to obtain an agent that still disagrees with itself
five times in six.

This also retracts something. The agent ladder was read as showing an
effect **changing sign** between random play and a 40-simulation search,
and that was reported as evidence of agent-dependence. At 40 simulations
the search has 0% self-agreement, so it was not searching: the sign
change was noise. The structural route settled the same sign agent-free
at t = −12.4.

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
