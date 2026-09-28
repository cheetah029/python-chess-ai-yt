# Getting to objective rule effects

## The objection

Reporting "under these two agents, these effects are stable" abandons
what the project is for. The goal is to **objectively quantify a rule's
contribution**, and a measurement that is conditional on whoever happened
to be playing does not do that.

That is correct. This document is the route back, and the first thing to
say is that **converging a search was never the only way there** — two of
the four routes below are *more* objective than a converged agent would
be, because they remove the agent entirely.

## What "objective" means here

The target is a property of **the game**, not of a player's experience of
it. The game-theoretic value of a position is that property: it does not
depend on who is playing. A rule's objective contribution is the
difference it makes to those values, and to the structure of the position
space.

Self-play with a strong agent *approximates* that. It is not the
definition of it, and treating it as the only route is what boxed this
project into agent-conditionality.

## Route 1 — Solve reduced instances exactly (no agent at all)

Positions with few pieces can be solved by retrograde analysis: the true
value of every position, computed rather than estimated. A rule's effect
is then the exact difference in those values with and without it. **No
agent appears anywhere**, so the result cannot be agent-conditional.

**The rules this project cannot currently measure are precisely the ones
this route measures best.** The tiny endgame rule requires ≤6 non-king
pieces and no pawns. The repetition rule matters when a player wants to
stall, which is an endgame behaviour. Both are unreachable by play and
both live in exactly the low-piece-count subspace where exact solution is
tractable.

Cost: the state space is positions × the per-piece flags that the state
hash already enumerates (queen form, manipulation freeze, invulnerability,
reactive-armed). `RULEBOOK.md`'s repetition section defines that state
exactly, and `src/` already computes the hash, so the encoding exists.

Scope limit, stated: this gives exact answers **on a subspace**, and the
subspace must be reported with the answer. It does not solve the opening.

## Route 2 — Sample positions independently of any policy

Many metrics are functions of a **position**: attack coverage, denied
squares, legal branching, material spread, force concentration. The agent
does not enter those formulas at all. It only decides **which positions
get looked at**.

So sample positions from a policy-independent distribution — uniformly
over legally reachable positions at a given depth, or from an ensemble
spanning many policies — and those metrics become agent-free. That is a
large fraction of the current profile made objective **without needing a
strong agent at all**.

What this does not cover: outcome metrics (win rate, decisiveness, game
length) are properties of play and cannot be separated from a policy this
way. Those need Route 1 or Route 3.

## Route 3 — An agent ladder, and the trend

Measure the same effect at several playing strengths: random, MCTS at 50,
200, 800, 2000. Then report the effect **as a function of agent strength**
rather than at one point.

If the magnitude is monotone and flattening as strength rises, the limit
can be bounded by extrapolation, and the claim becomes "the effect tends
to *x* as play improves" rather than "the effect was *x* under our agent".
If it is unstable across the ladder, that instability is the finding.

This converts a conditional result into a **measured trend toward the
objective quantity**. It is the standard move in empirical game theory and
it costs only more runs, not new machinery — the arms comparison already
generalises from two arms to N.

## Route 4 — Paired designs, to stop wasting the power we have

Run the variant and the baseline under **identical seeds and identical
agent internals**, so their trajectories stay matched as long as the rules
allow. The only difference is the rule.

This removes agent **noise** (not agent bias), and noise is what is
currently eating the results: 31 of 49 profile cells came back
seed-dominated. Common random numbers routinely cut variance by a large
factor, which means more effects resolve at the same compute.

## Order of work, and what each buys

| route | buys | agent-free? |
|---|---|---|
| 4 paired designs | more resolved cells at the same cost | no |
| 2 policy-free sampling | the structural half of the profile | **yes** |
| 3 agent ladder | a trend toward the limit, with a bound | no, but quantified |
| 1 exact endgames | exact values on a defined subspace | **yes** |

Route 4 first because it is cheapest and improves everything downstream.
Route 2 next because it makes a large part of the profile objective
immediately. Route 3 is a run-design change. Route 1 is the real prize and
the largest build, and it is the only one that answers the two rules that
play cannot reach.

## What will remain conditional, honestly

Full-board midgame positions at a branching factor near 53 cannot be
solved exactly and will not be. For outcome metrics in that regime, Route
3's extrapolation is the best available, and the claim must carry its
bound. That is a **quantified** limit rather than a shrug, and it is a
much smaller residue than "all our numbers are agent-conditional".
