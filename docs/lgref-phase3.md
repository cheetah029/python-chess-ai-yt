# LGREF Phase 3 — Contribution measurement

**Rules → measured contributions.** What difference does each ablation
actually make? Issue [#210].

## Run it

```bash
.venv/bin/python -m lgref.experiments.pilot --config lgref/config/phase3_pilot.yaml
```

Use `.venv/bin/python`, not a bare `python3`: on a machine where the
shell shows an active venv but `python3` still resolves to the system
interpreter, none of the project's packages are visible. LGREF names the
interpreter in its error rather than only the missing module.

## The decisive-game rate comes first, before any win rate

This variant has **no draw condition** — one win condition and four loss
conditions, none of them a draw. So a game stopped by the turn cap is
**censored**, not drawn, and a win rate over censored games measures the
cap rather than the rules ([#204]). Earlier runs at cap 100 reported
that agents "mostly drew" when **not one game in forty had finished**.

The pilot therefore reports decisive rate per variant first, and names
any variant whose games stop finishing as unusable for outcome metrics
rather than letting it contribute a plausible-looking number.

## Pilot result

Eight variants, six games each, mobility agent, turn cap 1000:

| variant | decisive | censored | mean turns | white | black |
|---|---|---|---|---|---|
| `baseline` | 100% | 0 | 47.8 | 1 | 5 |
| `control_double_move` | 100% | 0 | 48.3 | 3 | 3 |
| `control_inert` | 100% | 0 | 57.2 | 1 | 5 |
| `full` | 100% | 0 | 57.2 | 1 | 5 |
| `no_boulder` | 100% | 0 | 73.0 | 4 | 2 |
| `no_knight_redesign` | 100% | 0 | 48.5 | 1 | 5 |
| `no_queen_manipulation` | 100% | 0 | **98.8** | 1 | 5 |
| `no_tiny_endgame` | 100% | 0 | 57.2 | 1 | 5 |

**All variants finish**, so outcome metrics are usable — the gate this
phase was blocked on is passed.

### Cost

48 games in 160 s at 8 workers. The full sweep — 8 variants × 60 games ×
3 seeds = 1440 games — projects to **1.3 wall-hours**, against the 17
wall-hours originally budgeted for 480 MCTS games. That is ~13× cheaper
for 3× the games, and it follows from replacing an agent that was not
searching ([#206]).

## Two results worth reading carefully

### `control_inert` reproduces `full` exactly — as it must

Game for game, same seeds, same winners, same lengths. `control_inert`
is configured identically to `full`, so this validates the **harness**
rather than the game: had it differed, no variant difference could be
attributed to its ablation. A test pins it, alongside its complement —
that `no_boulder` *does* differ, so the harness demonstrably propagates
a real change.

### `no_tiny_endgame` also reproduces `full` exactly — and that is a finding

Byte-identical across all six games. The flag is honoured (the engine
consults it in three places), so this is not a silently ignored setting:
**the tiny endgame rule never fires in these games.** They end at 38–94
turns with most pieces still on the board, and the rule requires six or
fewer non-king pieces.

Under this agent, the tiny endgame rule has a **measured contribution of
zero** — not because it does nothing, but because play never reaches the
endgame it governs. That is a design-relevant null result, and it is
stated as conditional on this agent and these six games rather than as a
general claim about the rule.

## What this phase does not cover

Outcome metrics run on the **engine** variants. The fine-grained GDL
ablations from [#193] — relax, remove, replace — are measured
structurally instead, because playing one through the GGP resolver costs
over a minute per move: the mobility agent needs a legal-move generation
per root move, around 68 of them.

**The bridge between the two has not been verified yet.** Engine
`no_boulder` and GDL `remove boulder` are separate implementations of
one intent, and if they diverge the two tiers describe different games.
The cross-validation harness can compare them directly, and that check
should gate the full sweep rather than be discovered after it.
