# The evaluation must see every part of every game (#397)

Three times, a part of Royal Chess that the evaluation could not see
cost games before anyone noticed: the boulder, the Tiny Endgame Rule and
the repetition rule. A blind spot can't be seen in play. The player just
treats two different positions as the same. So it is caught by a test,
`lgref/tests/test_evaluation_blindness.py`, and the test covers games
nobody has written yet.

## What "sees" means

The parts of a game's state are its game description's own fluents.
The list comes from the GDL, not from anyone's memory of the game. For
every game the test:

1. **Coverage.** Every fluent relation the description declares (the
   head of a `next` rule, or an `init` fact) must turn up in states
   reached by seeded random play. A relation that is never reached
   can't be checked, so it must be listed in `NOT_REACHED` with a
   reason.
2. **Sensitivity, per relation.** Removing one of the relation's
   fluents from a state, or changing one of its non-role arguments to
   another value the relation takes, must change the features on at
   least one sampled state.
3. **Sensitivity, per fluent.** On the first sampled states, removing
   any single fluent must change the features. This catches an
   extractor that sees a relation but ignores some of its fluents.

A changed state is read with the mover of the state it came from, so a
change can't look "seen" only because the mover changed too. (The first
version of the test made exactly that mistake, and a mutant caught it.)

A relation that fails any check is a **blind spot**, and the test fails
and names it. `KNOWN_BLIND` lists blind spots that are known and not
yet fixed, each with its reason. The test also fails if a listed one is
no longer blind, so the list can only shrink. Today it is empty.

## The games

- Every development and test game in Paper A's catalog (22 games).
- **Royal Chess**, whose positions are read as the description's state
  through the engine-to-GDL converter
  (`lgref/experiments/gdl_engine.py`). That module adds the repetition
  counts (`state_repetition_count`), which the converter did not emit.
  `next_state_hash` is excluded: the description uses it to pass a
  successor's identity between two rules, and it is not a fluent of any
  position.

## Result (2026-11-27)

| Evaluation | Blind spots |
|---|---|
| GDL features (`lgref.experiments.gdl.features`), on all 22 GDL games | **none** |
| GDL features on Royal Chess, through `gdl_engine` | **none**: all 17 state fluents seen |
| The shipped hand-written Royal Chess evaluation (19 features) | **8 of 12** state parts |

The shipped evaluation's blind spots are recorded in the test
(`HAND_WRITTEN_BLIND`) as a measurement, not an endorsement:

- the boulder's cooldown and no-return memory;
- the manipulation freeze;
- knight invulnerability;
- which piece moved last turn;
- bishop reactive arming;
- the Tiny Endgame distance counts;
- the repetition counts.

It sees piece positions only through attack and cover terms whose
learned weights are close to zero. Replacing it with an evaluation
built on the GDL features is the next step of #397.

## What the audit does not claim

"Sees" means the features change. It does not mean the evaluation
weighs the change correctly: that is what training and measured play
decide. It is the minimum: a part the features never change on can't be
weighed at all.

## Mutation check

Each of these mutants of the extractor fails the test:

- skip `boulder_cooldown`;
- skip `invulnerable`;
- skip `distance_count`;
- skip the repetition counts;
- skip only the `cell` fluents in one column (caught only by check 3).
