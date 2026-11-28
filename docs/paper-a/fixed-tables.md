# Fixed tables: rule or language

Paper A, #400. This is the user's decision 3, option (c), a **post-freeze amendment** to the setup/language reference. The frozen reference (`kinds.yaml`) is kept, and its numbers are reported beside the amended ones.

- **Coded cut** (`lgref.bench.setup.fixed_table_candidates`): the predicate is a fixed table, meaning it is state-free at every depth. It is listed only if a legal, goal, terminal or next statement reads it, directly or through helpers.
- **Judged per entry**: whether the board geometry also uses it. No syntactic test separates a game's content from its vocabulary. Read as "no other table calls it", the test would make `opponent`, `forward` and `index` rules.
- **The principle applied**: a table is *language* when it encodes the board's coordinates, adjacency, directions or arithmetic, or generic vocabulary (players, cards, opponents) that would be the same in any game on that board. It is a *rule* when its content is specific to one rule of this game: which row wins, how a piece moves, the sowing order, the showdown ranking.
- Every verdict was written by Claude and is provisional. **The user may veto any entry**: edit `lgref/bench/references/fixed_tables.yaml` and re-run `python -m lgref.bench.setup --fixed-tables`.

## tictactoe

No fixed table shapes play.

## nim

| table | reaches | verdict | why |
|---|---|---|---|
| `atleast2` | legal | **language** | counting arithmetic: "at least two" over the pile sizes |
| `positive` | legal | **language** | counting arithmetic: "at least one" |
| `succ` | legal, next | **language** | successor table: arithmetic |

## corridor

| table | reaches | verdict | why |
|---|---|---|---|
| `inside` | legal | **rule** | the corridor limit IS the boundary rule (squares 0-7); not geometry any other rule needs |
| `plus2` | legal, next | **language** | arithmetic: two steps along the corridor |
| `succ` | legal, next | **language** | successor table: the corridor's geometry |

## breakthrough5

| table | reaches | verdict | why |
|---|---|---|---|
| `beside` | goal, legal, terminal | **language** | board geometry: adjacent columns |
| `forward` | goal, legal, terminal | **language** | board geometry: the row ahead for each side (moved to language in #363 under the user's convention) |
| `goalrow` | goal, terminal | **rule** | which row wins: the far-row win rule itself |
| `index` | goal, legal, terminal | **language** | board coordinates |
| `opponent` | goal, legal, terminal | **language** | vocabulary: who the other player is |

## othello4

| table | reaches | verdict | why |
|---|---|---|---|
| `after` | goal | **language** | counting order over the squares (scoring arithmetic) |
| `delta` | legal, next, terminal | **language** | board geometry: the eight directions |
| `fewer` | goal | **language** | counting comparison |
| `index` | goal, legal, next, terminal | **language** | board coordinates |
| `opponent` | goal, legal, next, terminal | **language** | vocabulary: who the other player is |
| `shift` | legal, next, terminal | **language** | board geometry: one step along a direction |
| `step` | legal, next, terminal | **language** | board geometry: the square one step away |
| `succ` | goal, legal, next, terminal | **language** | successor table: geometry and counting |

## dropthree

| table | reaches | verdict | why |
|---|---|---|---|
| `below` | legal, next | **language** | board geometry: the cell below |
| `right` | goal, terminal | **language** | board geometry: the column to the right |

## montyhall

| table | reaches | verdict | why |
|---|---|---|---|
| `door` | legal | **language** | vocabulary: the three doors |

## skirmish

| table | reaches | verdict | why |
|---|---|---|---|
| `close` | legal | **language** | board geometry: adjacent coordinates |
| `coord` | legal | **language** | board coordinates |
| `kingstep` | legal | **rule** | how the guard moves (one square in any direction): the guard's movement rule, not shared geometry |
| `opponent` | goal | **language** | vocabulary: who the other player is |
| `succ` | legal | **language** | successor table: geometry |
| `tsucc` | next | **language** | turn-counter arithmetic |

## muddychildren

| table | reaches | verdict | why |
|---|---|---|---|
| `child` | goal, legal | **language** | vocabulary: the children |
| `oneMuddy` | legal | **rule** | the dealing constraint (at least one child is muddy): rule content |
| `yesno` | legal | **language** | vocabulary: the two answers |

## kuhnpoker

| table | reaches | verdict | why |
|---|---|---|---|
| `card` | legal | **language** | vocabulary: the cards |
| `higher` | goal | **rule** | which card beats which: the showdown rule |
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `player` | legal | **language** | vocabulary: the players |

## leducholdem

| table | reaches | verdict | why |
|---|---|---|---|
| `amount` | next | **rule** | the bet amounts per round: betting rule content |
| `card` | legal | **language** | vocabulary: the cards |
| `higher` | goal | **rule** | which rank beats which: the showdown rule |
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `payoff` | goal | **rule** | the payoff table: the scoring rule |
| `player` | goal, legal | **language** | vocabulary: the players |
| `rank` | goal | **language** | vocabulary: the rank of each card |
| `succ` | next | **language** | successor table: arithmetic |

## russiancards

| table | reaches | verdict | why |
|---|---|---|---|
| `addmod` | legal | **language** | modular arithmetic |
| `card` | goal, legal | **language** | vocabulary: the cards |
| `lt` | legal | **language** | order over cards: arithmetic |
| `player` | goal, legal | **language** | vocabulary: the players |

## cherylsbirthday

| table | reaches | verdict | why |
|---|---|---|---|
| `date` | legal | **rule** | the ten candidate dates: the puzzle's content |
| `listener` | goal, legal | **language** | vocabulary: who is told what |

## kalah_mini

| table | reaches | verdict | why |
|---|---|---|---|
| `ahead` | next | **rule** | sowing distance along the ring: built from `ring`, so part of the sowing rule |
| `atmost` | next | **language** | counting comparison |
| `more` | goal, legal, next, terminal | **language** | counting comparison |
| `num` | goal, next | **language** | the numbers |
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `opposite` | next | **rule** | which pit faces which: used only by capture, so part of the capture rule |
| `ring` | next | **rule** | the sowing order, including which store each side skips: the sowing rule |
| `side` | goal, legal, next, terminal | **language** | board layout: which pits belong to which side |
| `storeof` | next | **language** | board layout: each side's store |
| `succ` | goal, legal, next, terminal | **language** | successor table: counting |
| `sum` | goal, next | **language** | counting arithmetic |
| `trio` | goal | **language** | board layout: each side's three pits |

## dotsboxes_2x2

| table | reaches | verdict | why |
|---|---|---|---|
| `bounds` | next | **language** | board geometry: the four lines around a box |
| `box` | next | **language** | board geometry: the boxes |
| `line` | goal, legal, terminal | **language** | board geometry: the lines |
| `more` | goal | **language** | counting comparison |
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `plus2` | next | **language** | counting arithmetic |
| `succ` | goal, next | **language** | successor table: counting |

## hex_3x3

| table | reaches | verdict | why |
|---|---|---|---|
| `firstedge` | goal, terminal | **rule** | which edge each player must connect from: the win rule |
| `index` | goal, legal, terminal | **language** | board coordinates |
| `lastedge` | goal, terminal | **rule** | which edge each player must connect to: the win rule |
| `opponent` | goal | **language** | vocabulary: who the other player is |
| `succ` | goal, terminal | **language** | successor table: geometry |
| `touches` | goal, terminal | **language** | board geometry: hex adjacency |

## checkers_4x4

| table | reaches | verdict | why |
|---|---|---|---|
| `farrow` | next | **rule** | the promotion row: the promotion rule |
| `forward` | goal, legal, terminal | **language** | board geometry: the row ahead for each side |
| `heading` | goal, legal, terminal | **rule** | which way men and kings may move: the movement rule, not shared geometry |
| `index` | goal, legal, terminal | **language** | board coordinates |
| `near` | goal, legal, terminal | **language** | board geometry: adjacent coordinates |
| `opponent` | goal, legal, terminal | **language** | vocabulary: who the other player is |
| `straddle` | goal, legal, next, terminal | **language** | board geometry: the square jumped over |
| `succ` | next | **language** | successor table: geometry |

## foxgeese_mini

| table | reaches | verdict | why |
|---|---|---|---|
| `beside` | goal, legal, terminal | **language** | board geometry: adjacent coordinates |
| `hop` | goal, legal, next, terminal | **language** | board geometry: a jump over one square |
| `index` | goal, legal, next, terminal | **language** | board coordinates |
| `orth` | goal, legal, terminal | **language** | board geometry: orthogonal neighbours |
| `straddle` | goal, legal, next, terminal | **language** | board geometry: the square jumped over |
| `succ` | next | **language** | successor table: geometry |
| `up` | goal, legal, terminal | **language** | board geometry: the row ahead |
| `waddle` | goal, legal, terminal | **rule** | how geese move (forward or sideways, never back): the geese movement rule |

## chomp_3x3

| table | reaches | verdict | why |
|---|---|---|---|
| `atmost` | next | **language** | board geometry: the order of rows and columns |
| `opponent` | goal | **language** | vocabulary: who the other player is |

## synth_independent

| table | reaches | verdict | why |
|---|---|---|---|
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `plus` | legal, next | **language** | addition table |

## synth_shared

| table | reaches | verdict | why |
|---|---|---|---|
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `plus` | legal, next | **language** | addition table |

## synth_redundant

| table | reaches | verdict | why |
|---|---|---|---|
| `opponent` | goal, legal, next | **language** | vocabulary: who the other player is |
| `plus` | legal, next | **language** | addition table |

## Effect on metric 11 (setup/language classification)

LGREF's two verdicts are scored for "language, not an ablation candidate": the frozen reference first, then the amended one. The last column lists the rule statements that the definitive indicator (no state dependence at any depth) still marks as language. Under the amendment those are errors.

| game | definitive indicator P / R: frozen -> amended | #202 cluster verdict P / R: frozen -> amended | rules the indicator marks language (amended) |
|---|---|---|---|
| tictactoe | n/a / n/a -> n/a / n/a | n/a / n/a -> n/a / n/a | none |
| nim | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 1.00 -> 1.00 / 1.00 | none |
| corridor | 0.50 / 1.00 -> 0.50 / 1.00 | 0.50 / 1.00 -> 0.50 / 1.00 | inside#15, inside#16, inside#17, inside#18, inside#19, inside#20, inside#21, inside#22 |
| breakthrough5 | 0.92 / 1.00 -> 0.92 / 1.00 | n/a / 0.00 -> n/a / 0.00 | goalrow#41, goalrow#42 |
| othello4 | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.71 -> 1.00 / 0.71 | none |
| dropthree | 1.00 / 1.00 -> 1.00 / 1.00 | n/a / 0.00 -> n/a / 0.00 | none |
| montyhall | 1.00 / 1.00 -> 1.00 / 1.00 | n/a / 0.00 -> n/a / 0.00 | none |
| skirmish | 0.86 / 1.00 -> 0.86 / 1.00 | 0.85 / 0.89 -> 0.85 / 0.89 | kingstep#15, kingstep#16, kingstep#17 |
| muddychildren | 0.67 / 1.00 -> 0.67 / 1.00 | n/a / 0.00 -> n/a / 0.00 | oneMuddy#9, oneMuddy#10 |
| kuhnpoker | 0.79 / 1.00 -> 0.79 / 1.00 | 0.50 / 0.27 -> 0.50 / 0.27 | higher#10, higher#11, higher#12 |
| leducholdem | 0.51 / 1.00 -> 0.51 / 1.00 | 0.42 / 0.70 -> 0.42 / 0.70 | higher#19, higher#20, higher#21, amount#27, amount#28, amount#29, amount#30, amount#31, amount#32, amount#33, amount#34, amount#35, amount#36, amount#37, amount#38, payoff#41, payoff#42, payoff#43, payoff#44, payoff#45, payoff#46, payoff#47 |
| russiancards | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.88 -> 1.00 / 0.88 | none |
| cherylsbirthday | 0.17 / 1.00 -> 0.17 / 1.00 | 0.00 / 0.00 -> 0.00 / 0.00 | date#4, date#5, date#6, date#7, date#8, date#9, date#10, date#11, date#12, date#13 |
| kalah_mini | 0.67 / 1.00 -> 0.55 / 1.00 | 0.36 / 0.24 -> 0.09 / 0.07 | opposite#12, opposite#13, opposite#14, opposite#15, opposite#16, opposite#17, ring#35, ring#36, ring#37, ring#38, ring#39, ring#40, ring#41, ring#42, ring#43, ring#44, ring#45, ring#46, ring#47, ring#48, ahead#50, ahead#51 |
| dotsboxes_2x2 | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.68 -> 1.00 / 0.68 | none |
| hex_3x3 | 0.76 / 1.00 -> 0.76 / 1.00 | 0.71 / 0.77 -> 0.71 / 0.77 | firstedge#23, firstedge#24, lastedge#25, lastedge#26 |
| checkers_4x4 | 0.90 / 1.00 -> 0.90 / 1.00 | 0.96 / 0.58 -> 0.96 / 0.58 | heading#27, heading#28, farrow#41, farrow#42 |
| foxgeese_mini | 0.95 / 1.00 -> 0.95 / 1.00 | 1.00 / 0.68 -> 1.00 / 0.68 | waddle#26, waddle#27 |
| chomp_3x3 | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.75 -> 1.00 / 0.75 | none |
| synth_independent | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.85 -> 1.00 / 0.85 | none |
| synth_shared | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.46 -> 1.00 / 0.46 | none |
| synth_redundant | 1.00 / 1.00 -> 1.00 / 1.00 | 1.00 / 0.85 -> 1.00 / 0.85 | none |
