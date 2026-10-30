# The fast GDL reasoner (issue #290)

## Why it exists

The framework's claim is that a designer can hand it a game written only in
GDL, and it will play and analyse that game. Before this change, every
GDL-only game ran about **1,000× slower** than Royal Chess. Royal Chess was
the exception because it has a hand-written Python engine (`src/engine.py`),
and that engine is what plays it. Its GDL (`docs/gdl/integrated.gdl`) is only
cross-validated against the engine.

The old reasoner, `ggp.resolver`, is slow for three reasons:

- It answers each query top-down from scratch.
- It rebuilds the knowledge base for every query.
- It shares nothing between the sub-goals of one query, so the same fact is
  proved many times over.

## What it does

`src/ggp/fast.py` compiles a description once. For each state, it computes
every derived relation a single time and works forward from the facts, in
order of dependency:

- It handles one strongly connected component at a time.
- Inside a recursive component, it iterates semi-naively.
- It uses hash indexes, built on demand, on the arguments a rule has already
  bound.

Each rule becomes a Python function of nested loops, so nothing is
interpreted. All the queries of one state read the same model: every role's
legal moves, terminal, and goals. A joint move recomputes only the relations
that read `does`, which are `next` and `sees`.

Some rules have a head variable that no body literal binds. Corridor's
`clear/2` is one, and so are 37 of Royal Chess's relations, including
`legal`. These are answered top-down instead. Each one is compiled once for
every pattern of bound arguments it is called with, and its answers are
memoised for each state. That is top-down evaluation with tabling, still
compiled.

`GGPGame` uses the fast reasoner by default. `GGPGame(text, reasoner='resolver')`
keeps the original reasoner. Three kinds of description fall back to the
resolver automatically:

- GDL-III, because `knows` is defined over play histories;
- anything using `=`;
- anything with unstratified negation.

`game.reasoner` says which reasoner is in use.

## Measured

Royal Chess, legal moves for both roles plus terminal, on one state, after
warm-up:

| reasoner | per state |
|---|---|
| hand-written engine (`GameEngine.get_all_legal_turns`) | ~1 ms |
| fast reasoner | ~13 ms |
| resolver | ~1,400 ms |

The small test games are 7–22× faster than with the resolver. Krieg-TicTacToe
is 22× faster.

## How it is checked

`tests/test_ggp_fast.py` plays the two reasoners in lockstep on seeded random
play. The games are nim, corridor, tic-tac-toe, Monty Hall, Krieg-TicTacToe,
Kuhn poker and Royal Chess, plus a small game written to exercise recursion
and a relation that calls itself. On every ply, the two reasoners must give
equal sets of legal moves for each role, and equal terminal, goals, percepts
and next state. The test is shown to catch four broken engines:

- strata reversed;
- no semi-naive loop;
- no cycle guard;
- no stratification check.

### Where the two differ

There are two differences, and both are tested:

- **Order.** The fast reasoner returns legal moves sorted; the resolver
  returns them in derivation order. The sets are the same, the order is
  not. A seeded player that picks "the k-th legal move" can therefore pick a
  different move under the two reasoners.
- **Left recursion.** The resolver treats `reach(X, ?y)` and its recursive
  call `reach(X, ?y2)` as the same goal and cuts the second one. Under left
  recursion it therefore finds only one-step answers. The fast reasoner
  computes the least model, which is what GDL defines. None of the existing
  games use left recursion.

Every seeded result recorded before #290 reproduces exactly at the commit its
record row names. To reproduce one at a later commit, set
`GGP_REASONER=resolver` before running its command; that makes the resolver
the default for every `GGPGame`.

## Not yet routed through it

`lgref/experiments/gdl.py` (`derived_relations`, `_derived_counts`) still
queries the resolver directly to count each state's derived relations as
features. Routing those through the fast reasoner would make the learned GDL
player's features much faster to compute. The features should be the same
except under left recursion, but that is a change to an agent, and the
agent rules require it to be proven separately. It is a follow-up.
