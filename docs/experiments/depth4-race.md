# Depth 4 against depth 3 — the race that made V7

Issue #279. The decision rule below was written on 2026-11-26, before
any game was played. The race found depth 4 to be a large strength
gain, and the user then made depth 4 a new major version,
**V7** ([`docs/agent-versions.md`](../agent-versions.md)).

## The rule, as declared

- **Question:** with today's shipped player (weights
  `lgref/weights/td_royal_chess.json`, main 9037ad0), does searching at
  depth 4 instead of 3 make it stronger?
- **Race:** 40 games of the shipped weights against themselves, one
  side at depth 4 and the other at depth 3.
  - No clock. A cap of 150 plies, after which a game is a draw.
  - Colours alternate game by game.
  - Openings come from `random_play` with seed 1000 + game index, for
    4–14 random plies (seeded by the game index).
  - Both sides use the window's own loader:
    `tools/race_agents.window_searcher(weights, depth)`, quiescence 2.
- **Score:** (wins + draws/2) / games, with a 95% Wilson interval.
- **Decision:** depth 4 is a real strength gain if it scores at least
  60% AND the interval's lower bound is above 50%. Otherwise the
  depth-4 push stops and the evaluation (#278) comes first. The result
  is reported either way, with no stopping early on a running score.

## Corrected result: every game played to its end (2026-11-27)

The user then ruled that Royal Chess strength data takes **no turn cap**.
The game has no draw outcome, so a capped game is an artefact. Scoring
it as half is wrong because one side may have been winning, and
dropping it loses the long games. The 6 capped games were replayed from
the same openings with no cap. Both players are deterministic, so each
replay repeats the capped game exactly up to the cap and then continues.

| Game | Depth 4 played | Plies after the opening | Winner |
|---:|---|---:|---|
| 7 | black | 197 | depth 4 |
| 14 | white | 146 | depth 4 |
| 17 | black | 156 | depth 4 |
| 19 | black | 221 | **depth 3** |
| 32 | white | 172 | depth 4 |
| 36 | white | 265 | **depth 3** |

| | Games | Depth-4 wins | Draws | Depth-4 losses | Score | 95% Wilson |
|---|---:|---:|---:|---:|---:|---:|
| **All, no cap** | **40** | **38** | **0** | **2** | **95.0%** | **[83.5, 98.6]** |

Depth 4 still passes the rule declared beforehand, by a wider margin.
The table below is the original capped result, kept for the record.

## Result as first reported (capped at 150 plies)

| | Games | Depth-4 wins | Draws | Depth-4 losses | Score | 95% Wilson |
|---|---:|---:|---:|---:|---:|---:|
| Depth 4 as white | 20 | 17 | 3 | 0 | 92.5% | |
| Depth 4 as black | 20 | 17 | 3 | 0 | 92.5% | |
| **All** | **40** | **34** | **6** | **0** | **92.5%** | **[80.1, 97.4]** |

**Depth 4 passes the rule by a wide margin.**

- **Draws:** all 6 were stopped by the 150-ply turn cap (games 7, 14,
  17, 19, 32 and 36).
- **Length:** games averaged 88 plies.
- **CPU per game:** depth 4 averaged 633 s, about 14 s per move;
  depth 3 averaged 182 s, about 4 s per move. That is 3.5 times the
  CPU, measured on a loaded machine.

## Checks against a hidden or trivial error

1. **The draw flag was wrong, and the score is not affected.**
   - The race script marked a game "truncated" by comparing the plies
     played after the opening with the cap.
   - The engine counts the opening plies too. So every one of the 6
     draws was in fact the turn cap: its opening plies plus its game
     plies come to exactly 150.
   - The declared rule scores a capped game as a draw, so the capped
     score was computed correctly by that rule. The check now reads
     `engine.turn_number`.
   - The cap itself was the larger problem. With every game played to
     its end, 4 of the 6 became depth-4 wins and 2 became depth-3
     wins. See "Corrected result" above.
2. **The harness has no bias toward the depth-4 label.**
   - A null control ran 20 games through the same script with BOTH
     sides at depth 3 and the same openings.
   - The side labelled "d4" scored 8.5 of 20, 42.5% [23.8, 63.6],
     which is consistent with 50%. One game hit the cap and was
     flagged correctly by the fixed check.
3. **The race reproduces.**
   - Game 2 was replayed on main d98c09c, which is after the
     search-speed changes 17 and 18. It gave the same result at the same
     ply count: a depth-4 win at 59 plies.
   - That also checks that those two changes left this game's moves
     alone, as their certificates say.
4. **The code was read for the usual mistakes.**
   - The winner is credited by colour, through the same `sides` map
     that chose each mover.
   - Colours alternate by game index, and the depth-4 wins are split
     17 and 17 between the colours.
   - The two searchers are separate objects, and no table or cache is
     shared at module level.
   - Depth really differed: the depth-4 side used 3.5 times the CPU.

## Guarantee 1: no line is searched shallower than at depth 3 (#390)

The user asked that depth 4 be at least as competent as depth 3
everywhere. The first guarantee proposed was that depth 4 never searches
a move less deeply than depth 3 does. Late-move reduction is the only
thing in the search that could break that.

**It already holds, with no code change.** A move is reduced by one ply
only at a node with remaining depth 2 or more (`lmr_depth = 2`):

- at depth 3 the root's children have remaining depth 2, so a line is
  reduced at most once and reaches the horizon after 2 or 3 full-width
  plies;
- at depth 4 a reduction at remaining depth 3 leaves 1, below the gate,
  so a line is still reduced at most once and reaches the horizon after
  3 or 4 plies.

Measured over three midgame positions, last deepening pass only:

| Search | Plies at which lines reach the horizon |
|---|---|
| Depth 3 | 2 or 3 |
| Depth 4 | 3 or 4 |

So the shallowest line at depth 4 is as deep as the deepest line at
depth 3. Quiescence beyond the horizon is the same in both.

`test_depth_four_never_searches_a_line_shallower_than_depth_three`
(`lgref/tests/test_search_efficiency.py`) keeps it true. A mutant that
reduces by two plies fails it: it finds a depth-4 line 2 plies deep. A
mutant that also reduces at remaining depth 1 passes, correctly, because
a reduction there makes no line shallower.

This is why, in race game 36, depth 4 without reduction chose the same
moves as depth 4 with it: reduction was not what lost that game.
## Why depth 4 lost game 19, and the fix (#393)

Game 19 was one of the two games depth 3 won. From ply 183 the tiny
endgame was active, with a lone royal queen on each side. Both players
valued every position at exactly 0.500 until depth 4 lost on
no_legal_moves at ply 221.

**An exact solve of depth 4's decisions** (every move searched to the
end of the game, with a memo keyed on the full history):

| Ply | Depth 4's moves | Winning moves | Played |
|---:|---:|---:|---|
| 205 | 10 | **3** | a losing move |
| 207–219 | 3–6 | 0 | (already lost) |

So the game was still won at ply 205, 15 plies from the end.

**The cause was the transposition table, not the evaluation or the
depth.** A freshly built depth-4 searcher on the ply-205 position values
it at 0.552 and plays a winning move, `(4,2)→(6,3)`. The searcher in the
game had carried its table over from earlier moves. That table is keyed
on the state hash, and by the rulebook's own definition the hash leaves
out the repetition counts and the distance counts. Both change which
turns are legal, so the table returned values computed under a different
history.

**The fix is general.** The searcher's key is the state hash plus
whatever history the game says its rules consult (`board.history_key()`).
The searcher learns nothing about Royal Chess. Royal Chess returns both
counts while the tiny endgame is active, and nothing otherwise, so play
outside the tiny endgame is unchanged. That is the CONFINED certificate
`test_the_search_key_carrying_history_is_confined`.

**Replaying game 19 with the fix:** play is identical up to ply 193,
inside the tiny endgame, where depth 4 first moves differently. **Depth 4
then wins, in 218 plies, capturing both royals.** This held with the
distance counts alone in the key, and with both counts.

**What the repetition rule does in a search,** measured on depth-4
searches of real game positions:

| Where | Searches | Turns the repetition rule blocked |
|---|---:|---:|
| Before the tiny endgame (games 19 and 36, plies 60–240) | 7 | 0 |
| In the tiny endgame (game 19, ply 190) | 1 | 24 |

That is why the key carries the repetition counts in the tiny endgame,
and why leaving them out elsewhere is a measured, stated gap rather than
a silent one.

**What it does not fix.** Even the fresh search ties one losing move,
`(4,2)→(6,1)`, at 0.552 with two of the winners. At ply 205 the three
winning moves are exactly the three that leave the opponent the fewest
legal turns (4, 5 and 5, against 9 to 24 for the losers). A tie-break
built on that, which follows from the rule that a player with no legal
turn loses, is the next candidate. It will be measured on solvable
tiny-endgame positions before anything is proposed.

## Game log

```
game 0 d4=white result=d4 plies=85 truncated=False d4cpu=240s d3cpu=68s elapsed=309s
game 1 d4=black result=d4 plies=96 truncated=False d4cpu=351s d3cpu=110s elapsed=775s
game 2 d4=white result=d4 plies=59 truncated=False d4cpu=202s d3cpu=44s elapsed=1023s
game 3 d4=black result=d4 plies=71 truncated=False d4cpu=218s d3cpu=72s elapsed=1315s
game 4 d4=white result=d4 plies=62 truncated=False d4cpu=317s d3cpu=80s elapsed=1719s
game 5 d4=black result=d4 plies=71 truncated=False d4cpu=409s d3cpu=106s elapsed=2241s
game 6 d4=white result=d4 plies=106 truncated=False d4cpu=308s d3cpu=100s elapsed=2656s
game 7 d4=black result=draw plies=141 truncated=False d4cpu=1573s d3cpu=355s elapsed=4836s
game 8 d4=white result=d4 plies=86 truncated=False d4cpu=735s d3cpu=210s elapsed=6341s
game 9 d4=black result=d4 plies=99 truncated=False d4cpu=943s d3cpu=386s elapsed=7749s
game 10 d4=white result=d4 plies=62 truncated=False d4cpu=617s d3cpu=148s elapsed=8550s
game 11 d4=black result=d4 plies=97 truncated=False d4cpu=813s d3cpu=218s elapsed=10048s
game 12 d4=white result=d4 plies=34 truncated=False d4cpu=277s d3cpu=85s elapsed=10577s
game 13 d4=black result=d4 plies=64 truncated=False d4cpu=441s d3cpu=123s elapsed=11325s
game 14 d4=white result=draw plies=145 truncated=False d4cpu=647s d3cpu=261s elapsed=12372s
game 15 d4=black result=d4 plies=69 truncated=False d4cpu=635s d3cpu=161s elapsed=13268s
game 16 d4=white result=d4 plies=98 truncated=False d4cpu=850s d3cpu=243s elapsed=14512s
game 17 d4=black result=draw plies=138 truncated=False d4cpu=1136s d3cpu=194s elapsed=16015s
game 18 d4=white result=d4 plies=85 truncated=False d4cpu=667s d3cpu=192s elapsed=17055s
game 19 d4=black result=draw plies=136 truncated=False d4cpu=918s d3cpu=234s elapsed=18504s
game 20 d4=white result=d4 plies=91 truncated=False d4cpu=262s d3cpu=51s elapsed=313s
game 21 d4=black result=d4 plies=62 truncated=False d4cpu=306s d3cpu=97s elapsed=721s
game 22 d4=white result=d4 plies=73 truncated=False d4cpu=287s d3cpu=69s elapsed=1079s
game 23 d4=black result=d4 plies=70 truncated=False d4cpu=387s d3cpu=103s elapsed=1573s
game 24 d4=white result=d4 plies=91 truncated=False d4cpu=406s d3cpu=93s elapsed=2084s
game 25 d4=black result=d4 plies=72 truncated=False d4cpu=298s d3cpu=90s elapsed=2476s
game 26 d4=white result=d4 plies=82 truncated=False d4cpu=775s d3cpu=225s elapsed=3546s
game 27 d4=black result=d4 plies=90 truncated=False d4cpu=398s d3cpu=119s elapsed=4071s
game 28 d4=white result=d4 plies=94 truncated=False d4cpu=692s d3cpu=175s elapsed=5315s
game 29 d4=black result=d4 plies=50 truncated=False d4cpu=402s d3cpu=124s elapsed=6158s
game 30 d4=white result=d4 plies=63 truncated=False d4cpu=548s d3cpu=133s elapsed=6941s
game 31 d4=black result=d4 plies=138 truncated=False d4cpu=825s d3cpu=249s elapsed=8046s
game 32 d4=white result=draw plies=145 truncated=False d4cpu=2418s d3cpu=819s elapsed=12248s
game 33 d4=black result=d4 plies=79 truncated=False d4cpu=633s d3cpu=288s elapsed=13283s
game 34 d4=white result=d4 plies=43 truncated=False d4cpu=302s d3cpu=90s elapsed=13723s
game 35 d4=black result=d4 plies=96 truncated=False d4cpu=997s d3cpu=263s elapsed=15160s
game 36 d4=white result=draw plies=141 truncated=False d4cpu=1272s d3cpu=459s elapsed=17192s
game 37 d4=black result=d4 plies=94 truncated=False d4cpu=524s d3cpu=167s elapsed=18042s
game 38 d4=white result=d4 plies=57 truncated=False d4cpu=448s d3cpu=151s elapsed=18852s
game 39 d4=black result=d4 plies=87 truncated=False d4cpu=835s d3cpu=131s elapsed=21124s
```

(`truncated=False` on games 7, 14, 17, 19, 32 and 36 is the faulty flag
described in check 1. Those games were capped.)
