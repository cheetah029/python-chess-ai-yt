# Session handoff, 2026-10-24

Supersedes `session_handoff_2026-10-20.md` for issue #278.

---

# READ THIS FIRST: a change ships on a proof, not on a quiet gate

**`docs/strictly-better-method.md` is the procedure. Follow it before
writing any code.** `docs/candidate-designs.md` applies it to every
planned change. `lgref/experiments/certificate.py` is the machinery and
`lgref/tests/test_method.py` enforces it.

The reviewer's correction, and it is right at the root:

> "I am asking for strict improvement, not overall improvement. If even
> a single thing is worse, the change cannot be shipped. So using gates
> to 'test' for strict improvement is wrong in and of itself. What
> needs to be done from the start is to design the methodology of
> building the change so that it is certainly strictly better."

**A gate is a detector.** It reports what it can see, at the power it
has, on the phases it reaches. An empty result means *nothing was
detected*, never *nothing is there*. Three times this week the gap was
real:

| the gate said | the truth |
|---|---|
| tempo loss inside the noise floor | down on all four training seeds |
| 13x13 clean | its endgame band has **no samples at all**; 5x5 found a 0.9-point loss |
| +7.0 opening placement | measured while the change had crippled the search to depth 1 |

**A gate may refuse a change. It may never licence one.**

What licenses one: a certificate, **declared before the code and proven
after**, in one of four classes — IDENTICAL (same values, less cost),
CONFINED (no effect outside a rule-defined region), MONOTONE (a
quantity can only move one way), UNSOUND (removes an operation whose
premise is false here). **A proven class that differs from the declared
one is a failure, not a relabelling**, and a test enforces that.

---

## What is shipped, and its certificate

| change | class | premise discharged against |
|---|---|---|
| `features.mnk` extraction | IDENTICAL | the pre-rewrite code recovered from git; 60 positions, six boards |
| `Game._deep_copy_board` | IDENTICAL | state hash over 12 snapshots |
| `Game.jump_to_start/end` | IDENTICAL | stepping all the way |
| futility via `has_tactics` | UNSOUND | premise false in m,n,k, true in the case study |

**Off, each with an entry rather than silence:** the m,n,k tie-break
(`TIE_BREAK_ENABLED = False`), `Reach`, the intersection boulder,
`EndgamePinned`, `BoulderPressure`.

---

## The three bugs fixed this session, and why they mattered

**1. Futility pruning in a game with no captures.** It assumes a quiet
move cannot change the score. m,n,k turns are plain integers with no
`is_capture`, so *every* move counted as quiet: the guard pruned 305
moves **including the block**, and a "complete" depth-2 search in 1131
nodes chose to lose a mate-in-one. This predates all of this week's
work. Now detected, the way undo support is.

**2. The extractor built a `Counter` per winning line** — 1,020 per
evaluation on 19x19, 70% of the cost. 1.32 ms → 0.23 ms, output
identical.

**3. My own tie-break was a 20× slowdown** — `threat_count` rescans
every legal move, so ranking one candidate cost 0.108 s and a root
sweep 9.74 s against 0.47 s. The search could not finish one ply, so
the agent played the best of an arbitrary partial set and stopped
opening in the centre. **The fix for the opening was breaking the
opening.**

| the reviewer's position | before | after |
|---|---|---|
| plays | 8,12 (loses) | **11,14 (blocks)** |
| depth reached | 1 | **2** |
| nodes in 5 s | 641 | **8032** |

**Depth is the lever.** Nothing in the evaluation changed.

---

## Open defects, measured

**m,n,k**
- **Opening placement 15.5% on 13x13** where random scores 50%. The
  only known fix (centrality tie-break) is **not certifiable** — see
  `candidate-designs.md` §1b.
- **`Line:1` ≈ `Line:2`** (+0.1199 vs +0.1249): the evaluation values
  touching many lines as much as building along one. Refitting `Line:2`
  alone against random playouts gives +0.0012 — *worse* — because
  random play neither builds nor punishes failing to build. The signal
  is absent from the distribution, not mis-weighted.
- **`Marks` = −0.1283 is a disguised turn indicator**, not a claim that
  stones are bad: the mark differential is fixed by whose turn it is,
  so the column is collinear with side-to-move.
- 19x19 runs on 7x7-trained weights.

**Royal Chess**
- **Boulder long-term pressure.** Pawns lost within 12 plies by
  distance: 44% / 35% / 29% / 28% / 25% / 11% / 0%. Everything from
  distance 2 is past the horizon (cooldown = one boulder move per three
  plies). `BoulderPressure` is **not certifiable** as an evaluation
  term.
- **The bishop pin.** Three attempts, three refusals: inert feature,
  worthless retrain, real-but-too-small term (−0.0187, raced 30–30).
  `Pinned` trains to ±0.00 on 9,706 observations because self-play
  never converts a pin.
- **Blunders at the reviewer's moves 14–15** (knight for pawn, bishop
  for pawn) — not yet diagnosed.

---

## The productive direction

Two classes discharge easily and both buy **depth**, which is what
measurably fixed the blunder:

- **IDENTICAL speedups.** Three shipped. More available.
- **UNSOUND removals.** One shipped. **Not yet checked: late-move
  reduction, `reduce_turns`, quiescence** — each rests on a
  quiet/forcing distinction m,n,k does not have. These are the next
  thing to examine.

---

## Runs in flight at handoff

- **Re-gate** of the tie-break on 5x5 and 13x13 against the repaired
  search. Every earlier m,n,k gate number was measured on the crippled
  search and is void. Note that even a clean result **cannot licence**
  the tie-break — see §1b.
- **Boulder race** at depth 3, `current 3 – 4 rival, 2 drawn` after 9
  of 24 games.

## Hygiene fixed

- Test runs no longer write weight caches into the repository
  (`MNK_CACHE_DIR` + a session fixture). A test-written file had been
  picked up by a tool and produced a **published wrong diagnosis**
  (`Line:2 = −0.0347` from an agent nobody plays).
- Tools ask the `Brain` for its cache key instead of globbing.
- Git has no configured identity on this machine; commits use
  `-c user.name/user.email` matching the existing history.

---

## Later the same day: the three heuristics, and the depth answer

**Late move reduction — UNSOUND, removed for m,n,k.** Declared before
the code, proven after. Its premise is a claim about the ordering, and
measured on 9x9 k=5 over 116 positions the ordering carries no
information: the best move sits at mean position **0.528** (0.5 = none),
reaches the first quarter **6.0%** of the time against a 25% baseline,
and falls in the reduced region **97.4%** of the time. The case study
still reduces — nothing removed there.

**`reduce_turns` and quiescence — INERT, not unsound.** `reduce_turns`
is injected and the window never injects it; quiescence is passed 0 and
returns immediately with no tactical turns. Neither needs removing
because neither runs.

**Depth: the puzzle is solved, and it was the clock.** At constant
depth, deeper is reliably better on 5x5 — depth 1 vs 2 is **0–24**,
depth 1 vs 3 is **1–36**. Depth 1 never beat depth 2 in forty games.

**But under a clock the depth varies by phase**: on 13x13 in five
seconds it is 3 at two marks, 6 at twenty, 10 at sixty. That makes the
player a different player in each phase **and confounds every
per-phase number in this handoff** — the endgame band was searched
seven plies deeper than the opening band. Both gate tools now fix the
depth; the earlier per-phase readings (including "placement declines
late in the game") partly measured the search.

**Constant depth costs**, worst observed move time with no clock:

| board | depth 2 | depth 3 |
|---|---|---|
| 9x9 | 0.1 s | 1.0 s |
| 13x13 | 0.3 s | 11.4 s |
| 19x19 | 2.0 s | 73 s |

So the standard going forward is a **fixed depth chosen per board
size**, not a fixed number of seconds. Making that the player's default
is a behaviour change and needs its own justification — it has not been
done, and is the next decision to take.

**A negative result kept on purpose:** the partial-iteration guard was
suspected and cleared — on 13x13 the hurried answer matched the
complete search at the depth it reached in 14 of 14 positions.

