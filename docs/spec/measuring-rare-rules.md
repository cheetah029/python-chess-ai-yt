# Measuring rules that play never reaches

## The problem, and why it is not a Royal Chess problem

Two of this game's rules almost never fire. The **tiny endgame rule**
needs a pawnless, balanced, few-piece position; the **repetition rule**
needs a player who wants to stall. As the designer put it, both require
"extremely optimal play from both sides to reach an equilibrium
position" *on top of* a niche condition — so with imperfect agents
neither arises. Measured: **zero tiny-endgame activations in 1440
games**.

Ablating such a rule measures nothing. The measurement is not wrong. It
is correct and empty.

Any rule set has rules like this — ones that fire only in late, rare, or
adversarially-produced states. A framework that measures rules by
playing games will systematically under-measure exactly those, and will
report them as contributing nothing, which is a different claim.

## The decomposition

    contribution  =  P(the condition arises)  ×  effect given it arises

The first factor is a property of the rule **and of the population of
play**. The second is a property of the rule alone. Reported separately
both are meaningful. Multiplied without being named, **a dormant rule
and a harmless rule are indistinguishable** — which is exactly the
failure the current results contain.

## "Never observed" is a bound, not a zero

Zero events in *n* games puts the rate below roughly 3/*n* at 95%
confidence (the rule of three). For 1440 games that is **0.0021**, and
expecting 30 activations at that rate would need about **14,400 games**
— roughly 3,600 core-hours with a search-based agent. Collecting more
games is not the answer, and saying "rate = 0" is a claim the data does
not support.

## A rule that never fires is a finding

"You wrote a rule that competent play never reaches" is among the most
actionable things a designer can be told. The framework should say it in
those words rather than reporting a contribution of zero. This costs
nothing and generalises to any game.

## Measuring the conditional factor without leaving the game

The tempting move is to **construct** activating positions. The risk is
measuring positions that cannot legally occur, and a contribution
computed over impossible positions is worse than none.

So **reach** them instead, by legal play under a recorded bias chosen to
shorten the path to the condition — capture-biased play reaches pawnless
endgames quickly, and that policy already exists as the MCTS playout.
Every position stays legal by construction, and the conditional effect
is reported **with** the activation rate under neutral play rather than
folded into one number.

## Why this generalises

The activation condition does not have to be hand-supplied. **LGREF
already parses the rules into clauses, so a rule's own clause body *is*
its activation condition** — whatever must hold for it to have any
effect. `tiny_endgame_active`, and a repetition count of two, are not
facts about Royal Chess typed in by hand: they are the guards those
rules' own clauses carry. Any GDL game gets the same treatment from the
same parse.

That gives a procedure with no game-specific step:

1. Take rule *R*'s clause guards as its activation predicate *A*.
2. Estimate **P(A)** under neutral play. If zero, report the bound and
   stop — *R* is dormant, and that is the result.
3. If *P(A)* is small but positive, reach *A* by biased legal play,
   recording the bias.
4. Measure the ablation effect from those states: the **conditional**
   contribution.
5. Report *P(A)* and the conditional effect **separately**, never their
   product alone.

## What is built and what is not

Built: the decomposition, the rule-of-three bound, the games-needed
figure, and the three-way verdict — dormant, underpowered, measurable
(`lgref/analysis/reachability.py`).

Not built: deriving the activation predicate from the clause guards
automatically, and the biased-reach sampler for step 3. The activation
columns are currently named per variant in `ACTIVATION`, which is the
hand-supplied version of what step 1 should compute (#237).
