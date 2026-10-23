# Which build the reviewer has approved

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

## CURRENT — approved 2026-10-20

- **file**: `lgref/weights/td_royal_chess.json`
- **sha**: `986895d4b4220c85`
- **archived as**: `archive/2026-10-18_09cb8872.json`
- **what it is**: the legacy 18-feature set, seeds 71 and 601
  averaged, 19 weights
- **why approved**: a reviewer played it and confirmed the midgame
  recovered — on move 9 of a reported game it recaptures a knight,
  where the superseded build moved the boulder onto its own pawn,
  hanging its king and dropping a knight in the same turn
- **known weaknesses**: blind to the boulder (no feature survives
  `differentials` for it); no representation of a bishop pin; builds
  no threats of its own in m,n,k

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
