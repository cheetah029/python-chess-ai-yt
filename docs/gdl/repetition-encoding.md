# Repetition Rule in the GDL: what is wrong now, and the options

Status: **options only, no decision.** Written for issue #389, which fixed
the Tiny Endgame limit and left the Repetition Rule alone on purpose. The
fix waits until the user picks an option.

## The rule

RULEBOOK.md: a player may not make a turn that would cause a board state
to appear **for the third time**. If every legal turn would do so, that
player loses. A "board state" is everything that determines the
legal-move set, with some fields counted only when a rule consults them:
`moved_last_turn` only when a queen, a knight or an armed bishop reads
it, and the boulder's no-return square only when it restricts a move.

So the rule needs, for each candidate turn, **the identity of the state
the turn would produce**, compared against every earlier state.

## What the current encoding does (step 10)

The rule is **enforced by the host**, not by the GDL. `GGPGame` counts
each resulting state in `step()`. With `enforce_repetition=True` it also
filters third-occurrence moves in `legal_moves()` and reports the loss
through `all_moves_repetition_blocked()`. The default is **off**.

The step-10 GDL is a sketch, and every part of it is wrong or inert:

| Statement | What it actually does |
|---|---|
| `would_repeat_third_time(NEXT_HASH) :- true(state_repetition_count(NEXT_HASH,2))` | Never true. No rule creates `state_repetition_count` facts. |
| `legal_after_repetition_filter(PLAYER,MOVE,NEXT_HASH) :- legal(PLAYER,MOVE) & ~would_repeat_third_time(NEXT_HASH)` | `NEXT_HASH` is not bound to the move. This is the same bug #389 fixed for the Tiny Endgame: if counts existed, one state at count 2 would ban every move. |
| `next(state_repetition_count(HASH,NEW_COUNT)) :- true(next_state_hash(HASH)) & ...` | Never fires. `next_state_hash` is never computed. |
| `all_legal_repetition_blocked(PLAYER) :- legal(PLAYER,MOVE) & would_repeat_third_time(DUMMY)` | Dead. Nothing reads it, and `DUMMY` is unbound. |
| `lost(PLAYER) :- no_legal_after_repetition_filter(PLAYER)` | Equivalent to the no-legal-turn loss today, because the filter never filters. It would be wrong the moment counts existed. |

What follows from this:

- **A pure-GDL reader plays a game with no repetition rule.** That covers
  an outside GGP player, `GGPGame` with the default setting, and any
  search that does not set the flag.
- **LGREF sees clauses that look like a rule but do nothing.** They take
  part in identification and in ablation as if they were real.
- The host key is the full fact set minus `turn_number`,
  `state_repetition_count` and `distance_count`. That is **finer** than
  the engine's conditional hash. The difference errs on the safe side: the
  host never blocks a turn the engine allows, but it can see a cycle one
  lap later.

The unbound `NEXT_HASH` was **not** fixed in #389. It has no single right
binding without a way to compute the successor state's identity, so any
binding would itself be a design choice.

## Options

Costs are rough estimates against the current 566-statement description.

### A. Host enforcement, honest GDL (smallest)

Delete the five inert step-10 statements, or rename them so they no longer
read as a rule. State plainly in the description that the host enforces
repetition. Turn `enforce_repetition` on wherever the GDL game must be the
rulebook's game.

- Cost: about 5 statements removed. LGREF fingerprints for Royal Chess
  re-recorded once.
- Wrong after it: the GDL alone still is not the rulebook's game. An
  outside GGP player still ignores the rule.

### B. A successor relation plus a full history (exact, expensive)

1. Rewrite every `next(F)` rule as a move-parameterised
   `after(MOVE, F)`, plus a single `next(F) :- turn_made(MOVE) &
   after(MOVE, F)`. The Tiny Endgame's `turn_squares` / `royal_after`
   are a small first instance of this.
2. Keep each past state as `seen(T, F)` fluents, tagged by turn.
3. A turn repeats a state if its `after` set equals some `seen(T, ·)`
   set: no fact in one is missing from the other.
4. Mirror the conditional fields with rules that decide whether a field
   counts.

- Cost: about 150 `next` rules rewritten, plus around 30 for comparison
  and the conditional fields. The turn counter needs an unbounded `succ`.
  The state grows by one copy of the position per turn, and each legal
  query compares every candidate turn against every past state: O(turns
  × facts).
- Wrong after it: nothing in principle, but it is slow late in a game.

### C. Option B with the window cut at irreversible turns

Only states since the last irreversible turn can recur. In this variant
those are a capture, a forward pawn move or a promotion. Sideways pawn
moves and boulder moves are reversible. B's history is cleared at each
irreversible turn.

- Cost: as B, plus about 5 statements. The history stays short in
  practice, but it is unbounded in principle (a long manoeuvring phase).

### D. A successor relation plus a canonical state term (exact, bounded)

Build, for each candidate turn, ONE term that names the resulting state:
a fold over the 64 squares in a fixed order plus the flag fields,
including the conditional ones. Keep `seen(TERM, COUNT)` fluents.
Repetition is then term identity, which a reasoner indexes as cheaply as a
hash.

- Cost: B's step 1 (about 150 rules), the fold over 64 squares and the
  flags (about 60 to 100), and about 10 for the counting. Each legal query
  builds one term of about 100 sub-terms per candidate turn. That should
  cost far less than B's comparison and does not grow with game length.
  It needs reasoners that handle deep terms (`ggp.fast` and the resolver
  both unify nested terms).
- Wrong after it: nothing in principle. This is the engine's state hash
  written in GDL.

## Recommendation

**A now, and D if a pure-GDL Royal Chess is ever required.** That would
be for an outside GGP player, or for an LGREF claim that rests on the GDL
alone.

A removes the misleading statements at almost no cost, and it keeps every
current consumer correct as long as the flag is set. D is the only exact
encoding whose per-move cost does not grow with the game. B and C are
simpler to write but slow late in the game.

Whichever is chosen, the change re-records the Royal Chess LGREF
fingerprints (`lgref/tests/test_gdl_dialects.py`, the statement count in
`lgref/tests/test_infix_input.py`), and the counts quoted in CLAUDE.md
and in the build header.
