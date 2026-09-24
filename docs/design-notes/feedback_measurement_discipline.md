---
name: feedback-measurement-discipline
description: "Measurement and long-run discipline on this project: never extrapolate a stopping decision from one timing sample, never run a job whose output is buffered, and verify a regression test actually fails on the bug before trusting it. Read before starting any multi-minute run or writing a guard test."
metadata:
  node_type: memory
  type: feedback
---

# Measure with a spread, watch the run, and check the test fails first

Three failures I have repeated on this project. Each cost real time and
each has an easy preventative.

## 1. A stopping decision needs a spread, not a point

**Rule:** never extrapolate total cost from one timing sample, and never
kill a healthy run on such an extrapolation. Take at least three samples,
spanning the range of work items, before projecting.

**Why:** costs here are wildly non-uniform. The Phase 1 intervention
probe measured 0.0s, 0.0s, 178.1s, 21.2s, 126.7s, 86.1s, 133.3s, 250.9s
across consecutive clusters — the probe's cost tracks how many legal
moves the *ablated* game has per ply, which is exactly what each ablation
changes. A `load_bearing` verdict short-circuits and costs nothing.

Instances (2026-09-22): estimated a probe at 3.1s on an idle machine when
the real cost was 6.3s, a 3x error; and killed a healthy gate run at
cluster 4/21 after extrapolating from cluster 3's 178.3s, when cluster 4
then landed at 20.7s and the run would have finished comfortably.

**How to apply:** set generous timeouts so a timeout never forces the
decision. Report an estimate as a range with the sample count, not a
number. See `lgref/report/*/ABORTED.md` for the written-up instance.

## 2. A run you cannot see is a run you cannot manage

**Rule:** always run long jobs with unbuffered output (`python -u`) and a
per-item progress line. Never pipe a long run through `tail` — the pipe
buffers and you get nothing until the end.

**Why:** a silent multi-minute run is indistinguishable from a hung one.
Lost ~10 minutes to a cost-estimate script that buffered its stdout and
had to be killed blind, then lost more to a `pytest ... | tail -25` that
showed nothing while running.

Also: `until ! pgrep -f "<pattern>"` matches **its own command line**, so
it loops forever. Wait on a PID (`kill -0 $PID`) instead.

**How to apply:** `lgref.identify.gate` prints one line per cluster to
stderr with a rolling projection; keep that pattern for every sweep.

## 3. A guard test must fail on the bug before you trust it

**Rule:** after writing a regression test, mutate the fix back and
confirm the test fails. If it passes, the test is worthless.

**Why:** wrote `test_cluster_determinism.py` against tic-tac-toe and
**both mutations survived** — 35 clauses give a partition too small and
too stable to expose either defect. Repointed at the 522-clause
case-study description and both mutations then failed the suite.
A regression test has to run where the bug lives.

## 4. Read the experiment's design before interpreting its variance

**Rule:** before saying what a variance decomposition means, open the
config and count the REPLICATION UNITS — not the rows.

**Why:** reported the 1440-game Phase 4 sweep to the user as "8 variants
x 180 seeds, one game each". It is 8 variants x **3 seed groups** x 60
games; the 180 distinct `seed` values are `seed*1000 + game`, and
`load_rows` divides them back down to the group. `variance_share` takes
its between-seed term from the variance of the GROUP MEANS, so the
design detail decides the conclusion. Read one way, "ten times the games
moved two of 49 cells" says the effects are small. Read correctly, it
ALSO says the seed term rests on three numbers however many games back
them, and the remedy is more seed groups rather than more games. Same
number, different next action.

**How to apply:** for any decomposition, state the unit the denominator
counts ("3 seed groups", not "1440 games") in the same sentence as the
verdict. If more data is proposed as the remedy, say which axis grows.

Related: [[feedback-analysis-rigor]].
