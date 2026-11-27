You are reviewing ways of dividing the statements of a game description
into RULES -- the parts of a game a player would name when explaining
it (how a piece moves, how a capture works, when the game ends, who
wins). Several groupings of the same statements follow, each produced
automatically. Judge each one on its own; do not rank them against each
other, and do not guess how they were made.

For EVERY group of EVERY grouping give:
  - score: an integer 1-5
      5  clearly one recognisable rule, or a sensible shared piece
         several rules need
      4  mostly one rule, with a stray statement or a missing one
      3  a plausible but loose collection
      2  mostly unrelated statements, or a rule cut into a fragment
         that means little alone
      1  arbitrary
  - reason: at most 20 words.
Then, for each grouping as a whole, an overall score 1-5 (how well it
divides the game into its rules, and how readable the result is) and a
reason of at most 30 words. A statement may sit in several groups; that
is allowed. Statements in no group are listed as ungrouped.

Answer from this text alone: do not read files, search, or run tools.
Reply with ONE JSON object and nothing else, of this shape:

{"groupings": {"G1": {"groups": {"1": {"score": 4, "reason": "..."},
                                 "2": {...}},
                      "overall": {"score": 3, "reason": "..."}},
               "G2": {...}}}


## The game

Red and blue share a tally that starts at 0; red moves first. On a turn a player either adds 1 to the tally, or adds 2 (at most once per game), or lights their own lamp (once per game; the tally stays). The tally may not pass 6. The player who brings it to exactly 6 wins. A player whose lamp is lit may add 1.

## The statements

```
  0  role(red)
  1  role(blue)
  2  plus(0,1,1)
  3  plus(1,1,2)
  4  plus(2,1,3)
  5  plus(3,1,4)
  6  plus(4,1,5)
  7  plus(5,1,6)
  8  plus(0,2,2)
  9  plus(1,2,3)
 10  plus(2,2,4)
 11  plus(3,2,5)
 12  plus(4,2,6)
 13  opponent(red,blue)
 14  opponent(blue,red)
 15  legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)
 16  next(tally(M)) :- does(P,add(1)) & true(tally(N)) & plus(N,1,M)
 17  legal(P,add(2)) :- true(control(P)) & true(tally(N)) & plus(N,2,M) & true(token(P))
 18  next(tally(M)) :- does(P,add(2)) & true(tally(N)) & plus(N,2,M)
 19  next(token(P)) :- true(token(P)) & ~does(P,add(2))
 20  legal(P,light) :- true(control(P)) & ~true(lit(P))
 21  next(lit(P)) :- does(P,light)
 22  next(lit(P)) :- true(lit(P))
 23  next(tally(N)) :- true(tally(N)) & does(P,light)
 24  legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M) & true(lit(P))
 25  legal(Q,noop) :- true(control(P)) & opponent(P,Q)
 26  next(control(Q)) :- true(control(P)) & opponent(P,Q)
 27  terminal :- true(tally(6))
 28  goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))
 29  goal(P,0) :- true(tally(6)) & true(control(P))
 30  init(tally(0))
 31  init(token(red))
 32  init(token(blue))
 33  init(control(red))
```

## Grouping G1 (34 groups)

- group 1: statements 0
- group 2: statements 1
- group 3: statements 2
- group 4: statements 3
- group 5: statements 4
- group 6: statements 5
- group 7: statements 6
- group 8: statements 7
- group 9: statements 8
- group 10: statements 9
- group 11: statements 10
- group 12: statements 11
- group 13: statements 12
- group 14: statements 13
- group 15: statements 14
- group 16: statements 15
- group 17: statements 16
- group 18: statements 17
- group 19: statements 18
- group 20: statements 19
- group 21: statements 20
- group 22: statements 21
- group 23: statements 22
- group 24: statements 23
- group 25: statements 24
- group 26: statements 25
- group 27: statements 26
- group 28: statements 27
- group 29: statements 28
- group 30: statements 29
- group 31: statements 30
- group 32: statements 31
- group 33: statements 32
- group 34: statements 33

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33

## Grouping G3 (8 groups)

- group 1: statements 13, 14, 25, 26, 27, 28, 29, 33
- group 2: statements 2, 3, 5, 6, 7, 9
- group 3: statements 4, 8, 10, 11, 12
- group 4: statements 17, 19, 31, 32
- group 5: statements 18, 23, 30
- group 6: statements 20, 21, 22
- group 7: statements 0, 1
- group 8: statements 15, 16
- ungrouped: statements 24

## Grouping G4 (8 groups)

- group 1: statements 13, 14, 23, 25, 26, 27, 28, 29, 30, 33
- group 2: statements 2, 3, 4, 5, 6, 7, 9
- group 3: statements 3, 4, 8, 9, 10, 11, 12
- group 4: statements 17, 19, 31, 32
- group 5: statements 16, 23, 27, 30
- group 6: statements 20, 21, 22
- group 7: statements 0, 1
- group 8: statements 18, 24
- ungrouped: statements 15

## Grouping G5 (2 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 17, 18, 24
- group 2: statements 13, 14, 25, 26, 28
- ungrouped: statements 0, 1, 19, 20, 21, 22, 23, 27, 29, 30, 31, 32, 33

## Grouping G6 (8 groups)

- group 1: statements 13, 14, 25, 26, 27, 28, 29, 33
- group 2: statements 2, 3, 4, 5, 6, 7
- group 3: statements 8, 9, 10, 11, 12
- group 4: statements 17, 19, 31, 32
- group 5: statements 16, 23, 30
- group 6: statements 20, 21, 22
- group 7: statements 0, 1
- group 8: statements 18, 24
- ungrouped: statements 15

## Grouping G7 (10 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
- group 2: statements 15, 17, 20, 24, 25
- group 3: statements 16, 18, 23, 30
- group 4: statements 19, 31, 32
- group 5: statements 0, 1
- group 6: statements 13, 14
- group 7: statements 21, 22
- group 8: statements 26, 33
- group 9: statements 28, 29
- group 10: statements 27

## Grouping G8 (10 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 17, 18, 20, 24, 25
- group 2: statements 13, 14, 16, 18, 25, 26, 27, 28, 29, 33
- group 3: statements 13, 14, 23, 26, 27, 28, 29, 30, 33
- group 4: statements 13, 14, 26, 27, 28, 29, 33
- group 5: statements 15, 17, 19, 24, 31, 32
- group 6: statements 16, 18, 20, 23, 25, 30
- group 7: statements 0, 1
- group 8: statements 20, 21
- group 9: statements 21, 22
- group 10: statements 23, 30

## Grouping G9 (8 groups)

- group 1: statements 13, 14, 23, 25, 26, 27, 28, 29, 30, 33
- group 2: statements 2, 3, 4, 5, 6, 7, 9
- group 3: statements 3, 4, 8, 9, 10, 11, 12
- group 4: statements 17, 19, 31, 32
- group 5: statements 18, 23, 27, 30
- group 6: statements 20, 21, 22
- group 7: statements 0, 1
- group 8: statements 15, 16
- ungrouped: statements 24

## Grouping G10 (8 groups)

- group 1: statements 8, 9, 11, 12, 14, 15, 16, 24, 25, 33
- group 2: statements 5, 10, 13, 17, 20, 21, 27
- group 3: statements 1, 10, 17, 20, 22, 23, 31
- group 4: statements 2, 4, 19, 26
- group 5: statements 8, 11, 12, 32
- group 6: statements 6, 18, 29
- group 7: statements 0, 7
- group 8: statements 3, 30
- ungrouped: statements 28

## Grouping G11 (2 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33
- group 2: statements 0, 1

