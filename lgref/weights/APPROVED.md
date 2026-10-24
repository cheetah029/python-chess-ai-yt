# Which build the reviewer has approved

> **BOTH GAMES ARE NOW UNDER THIS RULE** (reviewer, 2026-10-22):
>
> > "The player is doing very well on both games and is steadily
> > improving. Make sure all versions are strictly better than this
> > one, otherwise don't ship them until you can make them strictly
> > better."
>
> So the bar is the same for the case study and for m,n,k: a later
> version ships by **losing nothing**, and a change that cannot be
> shown to be strictly better **does not ship** — it waits until it
> can be. "Not yet measurable" is a reason to keep measuring, not a
> reason to ship.

A version nobody wrote down is a version nobody can go back to. This
file names the build that is approved for play, and everything it
supersedes. `test_ship_discipline.py` checks that the shipped weights
ARE the approved ones.

**A race win is not grounds for changing this entry.** A race reports
an aggregate over positions; a change can win overall and still be much
worse at a particular kind of position. `Reach:j` is the worked
example: it fixed the m,n,k opening and made the midgame worse, and one
number would have reported only the first. Promotion needs the race
AND evidence on the specific positions a reviewer reported AND no known
regression.

## CURRENT — approved 2026-10-20, **re-confirmed 2026-10-22**

- **file**: `lgref/weights/td_royal_chess.json`
- **sha**: `986895d4b4220c85`
- **archived as**: `archive/2026-10-18_09cb8872.json`
- **what it is**: the legacy 18-feature set, seeds 71 and 601
  averaged, 19 weights
- **why approved**: a reviewer played it and confirmed the midgame
  recovered — on move 9 of a reported game it recaptures a knight,
  where the superseded build moved the boulder onto its own pawn,
  hanging its king and dropping a knight in the same turn
- **re-confirmed**: "The player is doing very well on both games and
  is steadily improving" (2026-10-22). This build is the Royal Chess
  baseline a later one must beat without losing anything.
- **known weaknesses**: blind to the boulder — and now understood
  rather than merely observed: a neutral piece cancels out of a
  DIFFERENTIAL vocabulary, so no count of it can survive, and it can
  only reach the evaluation through its asymmetric effects. It is also
  blind for the whole OPENING even through those, because the boulder
  starts off-square on the central intersection (fixed behind a
  default-off flag, awaiting this gate). No representation of a bishop
  pin; `Pinned` prices at ≈0.09 pawns, which is far too small for a
  tactic the reviewer describes as decisive.

### The floor a later Royal Chess version must clear

The per-phase instruments that reach this game are `tie_rate` (does the
evaluation tell its moves apart) and `choice_rank` (where it plays,
against a prior learned from random play under the rules). Three others
do not, and the reasons are worth knowing rather than quietly working
around:

| instrument | why not |
|---|---|
| `optimal_rate` | no solver reaches a 64-square game |
| `forced_move_rate` | ports, but 237 seconds found ONE qualifying position — this game ends only when both royals are captured, so "the win in front of it" is almost never the question |
| `initiative_rate` | needs a game whose side to move can be set on a copy; this engine's does not |

So the Royal Chess gate is the race **at the played depth** plus those
two per-phase numbers plus the existing domain instruments
(`avoidable_losses`, `rescuable_losses`, `exchange_opinions`).

The measured floor, approved build at depth 3, `tools/rc_phase_rates.py`:

| phase | sharpness | placement | n |
|---|---|---|---|
| opening | 96.2% | 67.6% | 30 |
| midgame | 98.2% | 55.8% | 30 |
| endgame | 98.4% | 50.6% | 29 |

**Read the placement column carefully.** The prior is learned from
RANDOM games, so it is most informative in the opening — where which
squares are structurally strong still shows through the noise — and
least informative in the endgame, where concrete tactics decide and
random statistics say little. A score that falls toward 50% late may
be the PRIOR weakening rather than the agent. At n≈30 the noise floor
is about 10 points, so this is a floor to beat, not a result.

### Correction: the "+0.22 endgame pin signal" was over-claimed

Recorded here because it was committed as a finding and is not one.

`differentials(raw, me)['Pinned']` is POSITIVE when **my own** pieces
are pinned — the column is indexed by the owner of the pinned piece,
which is the side it is bad for. The measurement "pin correlates +0.230
with winning in thin positions, replicated at three seeds" therefore
says that having more of *my own* pieces pinned goes with winning,
which is not what I reported it as, and is not a pin effect.

Material does not explain it — the layout sampler builds symmetric
material, so that differential is identically zero across the sample.
The likely explanation is **placement**: a piece standing on an enemy
bishop's long diagonal is a piece in the open, and open pieces win
random playouts. The number is real; the reading was wrong.

What survives: fitting a weight on the regime-gated column with every
other weight frozen gives **−0.0187**, about 30% of a pawn, and the
sign is the one the rules imply — a pinned regular piece has no action
to stall with, so it must move, and moving is what gets it captured.
That estimate controls for the approved evaluation; the raw
correlation controls for nothing.

### Candidate: seeing the boulder on the intersection

**Not shipped.** It is correct — the engine generates a legal
`boulder capture` that the extractor scores as `Attacked=0` — but it
**fires in 1.8% of live positions** (7 of 400), because it needs the
boulder still on the intersection AND a pawn on one of the four
central squares at the same time. Uniform sampling cannot resolve
1.8% of anything against a four-point floor.

What makes the question tractable is that the change is **provably
inert everywhere else**: the extractor's output is identical unless
both conditions hold, so the agent cannot behave differently in the
other 98.2%. "Strictly better" therefore reduces to the conditioned
question — when the situation arises, does seeing the threat save the
pawn?

**It does not, and the reason is worth more than the fix.** Measured on
20 positions where the fix fires and the threatened side is to move:

| setting | pawn kept | n |
|---|---|---|
| boulder unseen | 95.0% | 20 |
| boulder seen | 95.0% | 20 |

The two arms choose **identical moves in 20 of 20 positions**, at
depth 1 and at depth 2. The feature changes the evaluation and never
the decision — because in the approved build `Attacked` weighs
**−0.0004** against a pawn at +0.0616, and **`Hanging` is not in the
shipped vocabulary at all** (nor is `Pinned`; the build is the legacy
18-feature set). Marking one more pawn attacked moves the evaluation by
**0.7% of a pawn**, which never changes an argmax.

**So the approved agent has no notion of a hanging piece at all — the
column is absent, not merely small — and plays well anyway** — because a one-ply threat is resolved by
the SEARCH, not by the evaluation. That is the lesson to carry: the
evaluation's job is what the search cannot reach. Adding features for
immediate tactics has not helped before and this says why. The bishop
pin is the opposite kind of thing — structural, persistent, outside a
depth-3 horizon — which is where the effort belongs.

## SUPERSEDED

| build | sha | why it is not approved |
|---|---|---|
| `archive/2026-10-19_ccdb27cb.json` | `form-ablated` | won its race 25–7 **at depth 2** while the window plays at depth 3; a reviewer found it much worse in play |

## Candidates under test

| candidate | status |
|---|---|
| boulder-aware retrain (live vocabulary) | training; must be BISECTED against the same vocabulary without the boulder fix before any claim about the boulder |
| jump-capture-aware search | racing against the search it replaced, same weights |
| `Reach:j` for m,n,k | reverted to off; fixes the opening, reported worse in the midgame |

## m,n,k — APPROVED 2026-10-22

**The reviewer played this version and asked for it to be kept:**

> "Other than its first few moves being weird and off the center, the
> rest of its moves are getting increasingly more dangerous and
> aggressive, making it a great player. I'm proud of this version."

So it is the baseline, and **a later version ships only by being
strictly better than it** — not better on average, not better in the
opening, better *and nowhere worse*.

### What the approved version is

m,n,k trains from zero when a board is chosen, so the "version" is the
FEATURE SET plus the search, not a weight file.

| | |
|---|---|
| vocabulary | `Line:1..k-1`, `Marks`, and the `Missing:` half of each — **10 features on 13x13 k=5**, fingerprint `4701b7c3` |
| `Reach:j` | **off.** Measured across FOUR training seeds, pooled (13x13 k=5, 1500 trials each): it costs **2.4 points of tempo** (72.9% → 70.5%, n=3436 a side, z = 2.21) and is **down on every one of the four seeds** (−4.3, −2.7, −0.5, −2.4). Forced-move answering is unchanged (+0.1, inside the floor). Its opening gain is real but narrower than it looks: +3.3 points of sharpness pooled, and **three of the four seeds are identical** (97.7 → 97.7/97.8) with the whole difference coming from seed 23, where the plain vocabulary trained badly (86.1%) and Reach did not (99.3%). So Reach buys ROBUSTNESS TO A BAD TRAINING RUN in the opening, not better openings — and pays for it with tempo in every run. That is the reviewer's own report: *"performs much better on starting moves near the center, but fails to attack effectively and wastes tempo on later moves."* |
| search | `Searcher`, iterative deepening under the per-move clock; sec/move `0` makes the depth exact |
| weights | trained at startup, cached in `lgref/weights/mnk_cache/` keyed on board **and** vocabulary fingerprint |

`lgref/tests/test_ship_discipline.py` pins the fingerprint, so adding
or removing a feature fails a test rather than changing the player
quietly.

### The floor a later version must clear

Measured on 13x13 k=5, 1500 trials, **pooled over four training seeds**
(11, 23, 37, 53) — pooled because one seed measures the training run,
not the feature set: the same vocabulary scores 97.7% opening sharpness
at three seeds and 86.1% at the fourth.


| phase | approved version | n |
|---|---|---|
| opening sharpness | 94.8% (97.7% at three seeds of four) | 6000 |
| midgame forced | 91.2% | 1508 |
| tempo | **72.9%** | 3436 |
| opening placement | not yet measured — the instrument is new | — |

**Tempo is IN the gate for m,n,k**, not merely reported. It was
descriptive on the grounds that a quiet move is not automatically a bad
one. The reviewer has since made that call explicitly:

> "Do not make any later versions fix the opening moves while
> simultaneously compromising everything else and all the good moves it
> makes afterwards. Reach did exactly that and so it was overall more
> ineffective than the original."

That is a value judgement about this game, and it is theirs. `Reach:j`
is the worked example: it cost 4.6 points of tempo (pooled, z = 2.94)
and bought nothing measurable anywhere else.

### The open problem, and the trap in it

The opening IS weak — the first few moves are off-centre. Fixing it is
wanted. Fixing it **at the cost of the midgame is not**, and that is
not a hypothetical constraint: it is exactly what the last attempt did.

Note also that `opening sharpness` is **not** the instrument for this.
It measures whether the evaluation DISTINGUISHES its moves, not whether
it plays near the centre, and it reads 97.7% for both feature sets. A
distance-from-centre instrument does not exist yet and is the next
thing to build.

## m,n,k, historically

There is no shipped build to approve. The m,n,k agent trains from zero
when a board is chosen, and `lgref/weights/mnk_cache/` only keeps what
that produced so the same board does not pay for it twice. Every file
there is regenerable, and the key includes a hash of the FEATURE NAMES
as well as the board — so a cached file can never be served to a
different feature set, which it silently was once.

What is under review there is the feature set itself:

| feature | status |
|---|---|
| `Line:j` | approved; the whole vocabulary before Reach |
| `Reach:j` | **off — on the reviewer's own play, not on the number below.** The measurement is WITHDRAWN: on 13x13 k=5 at training seed 11 it cost **4.6 points of tempo** — moves that neither make a threat nor remove one — pooled over two independent position samples (n=1680 a side, z = 2.94, p ≈ 0.003), while changing opening sharpness and forced-move answering by nothing measurable (97.7% vs 97.7% at n=1500; 90.7% vs 90.7% at n=377). That is the reviewer's report confirmed: "fails to attack effectively and wastes tempo on later moves". It is kept switchable because the problem it was written for is real — on 19x19 k=5 the plain line count saturates and ties across 121 cells — but the instrument for THAT claim (where the move lands, not whether moves are distinguished) does not exist yet. **At training seed 23 the verdict reverses**: Reach is 13.1 points of opening sharpness and 4.5 points of forced-move answering BETTER, with tempo inside the floor. The difference between TRAINING RUNS swamps the difference between feature sets, so a one-seed comparison measures the run. A four-seed pooled run is in flight; until it lands, the reason Reach is off is the reviewer's own games, which is evidence about the player in a way one training seed is not. |
