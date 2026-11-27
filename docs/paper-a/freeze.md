# Paper A: the frozen method

Frozen on 2026-11-27 for issue #358. This was done after Experiments 1–4
ran on the development games (`results-dev.md`) and before any fresh test
game was written. After this point nothing in the list below changes for
Paper A. If a bug is found later, it gets a new version, and the test
games are re-run under both versions (`protocol.md`, "The freeze").

## What is frozen

The frozen commit is **`ab7b33b2adcddd64ba2a03cd30ed7929b76dc306`**
(merge of PR #357). The frozen code is:

- `lgref/identify/`: clauses, graph, clustering, ownership, intervention.
  Paper A has not changed any of it.
- `lgref/bench/methods.py`: every grouping method compared.
- `lgref/bench/interventions.py`: how a grouping becomes interventions.
- `lgref/bench/metrics.py` and `lgref/bench/behaviour.py`: the scores,
  together with the state set and the validity rule.

The configuration is production LGREF, unchanged:

| setting | value |
|---|---|
| edge weights | legality 3.0, shared_state 2.5, same_head 2.0, temporal 1.5, predicate 1.0, terminal 0.5, co_activation 0, co_use 0 |
| hub filter | fluents read by ≥ 8% of statements (games of ≥ 20 statements) give no shared_state edges |
| resolution | the coverage rule, tolerance 0.03 |
| overlap step | a statement joins any community holding ≥ 25% of its edge weight; generic board updates are held out and reattached to every rule they serve |
| minimum group size | 2 |
| intervention | primary: the ownership split (`ownership`). Also reported: deleting the whole group (`delete_group`) |
| seeds | 0–29 for groupings; 0 for interventions |

## Nothing was tuned, and why

Experiment 3, run on the seven development games, found no setting
that beats production by more than its interval: turning off the
terminal edge gives +0.031 [−0.000, 0.066], and a raw resolution of 0.5
gives +0.015 [−0.031, 0.054]. (On the first five development games,
before drop-three and Monty Hall joined the set, the resolution-0.5
gain was +0.044 [0.020, 0.067].) None of
them was adopted, for three reasons:

1. **The references are provisional and were written by the method's
   author.** Tuning toward them would fit the method to one person's
   reading of seven games, and that person is the same one whose method
   is being tested.
2. **The metric favours coarse groupings on these references.** The
   references share many statements: Othello's successor table is in
   three rules, for example. Because of that, extended BCubed rewards
   recall. `one_group` scores 0.494 and connected components score
   0.659, against LGREF's 0.664. On Othello, `one_group` beats LGREF
   outright (0.667 vs 0.432). The settings that raise F1 here coarsen
   the groups (a lower resolution, no terminal edge). Adopting one would
   move the method toward the artefact, not toward rules. Besides,
   reference F1 is now a SUBJECTIVE, secondary metric (`protocol.md`).
3. **Seven games.** The intervals in Experiment 3 are over seven
   games. On the original sheets, every gain sits inside its interval.

**After the freeze (#363).** The reference sheets were revised under the
user's convention that geometry and arithmetic are language. On the
revised sheets, one setting beats production beyond its interval:
turning off the terminal edge, +0.045 [0.003, 0.090] BCubed F1. The
freeze stands. The protocol forbids tuning after it, and the metric is
subjective. This is recorded so that the user can decide whether a
separately labelled post-freeze variant should also be reported.

If the user wants a tuned variant, the protocol allows it, but only
before any test game is written: a dev-only choice, recorded here as a
departure. The test-game list in `lgref/bench/catalog.py` is unaffected
either way.

## How the dev results relate to this commit

See "Commits" at the end of `results-dev.md`. In short:

- Experiment 1 ran on code byte-identical to `ab7b33b` in
  `lgref/bench/` and `lgref/identify/`.
- Experiments 2–4 ran on the stage 4 tree (#358). That tree changes only
  the runner and the tables, not how a grouping is made or scored.

Groupings are deterministic across processes and the intervention runs
are seeded, so a re-run reproduces the rows.
