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

## m,n,k

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
| `Reach:j` | **off.** Fixes the opening — on 19x19 k=5 the plain line count saturates and ties across 121 cells, so no line-counting feature can tell the centre from a quadrant. A reviewer played it and reported the midgame worse: tempo spent on moves that neither attacked nor defended. Kept switchable so the two phases can be raced apart. |
