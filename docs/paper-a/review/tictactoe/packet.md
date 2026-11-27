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

Two players, x and o, take turns marking a blank cell of a 3x3 grid; x moves first. Three of one mark in a row, a column or a diagonal wins. If the grid fills with no such line, the game ends with no winner.

## The statements

```
  0  role(xplayer)
  1  role(oplayer)
  2  legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,b))
  3  legal(xplayer,noop) :- true(control(oplayer))
  4  legal(oplayer,noop) :- true(control(xplayer))
  5  next(cell(M,N,x)) :- does(xplayer,mark(M,N))
  6  next(cell(M,N,o)) :- does(oplayer,mark(M,N))
  7  next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)
  8  next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)
  9  next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(N,K)
 10  next(control(xplayer)) :- true(control(oplayer))
 11  next(control(oplayer)) :- true(control(xplayer))
 12  row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))
 13  column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))
 14  diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))
 15  diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))
 16  line(W) :- row(M,W)
 17  line(W) :- column(N,W)
 18  line(W) :- diagonal(W)
 19  open :- true(cell(M,N,b))
 20  terminal :- line(x)
 21  terminal :- line(o)
 22  terminal :- ~open
 23  goal(xplayer,100) :- line(x)
 24  goal(oplayer,100) :- line(o)
 25  init(cell(1,1,b))
 26  init(cell(1,2,b))
 27  init(cell(1,3,b))
 28  init(cell(2,1,b))
 29  init(cell(2,2,b))
 30  init(cell(2,3,b))
 31  init(cell(3,1,b))
 32  init(cell(3,2,b))
 33  init(cell(3,3,b))
 34  init(control(xplayer))
```

## Grouping G1 (35 groups)

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
- group 35: statements 34

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34

## Grouping G3 (5 groups)

- group 1: statements 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24
- group 2: statements 2, 3, 4, 5
- group 3: statements 10, 11, 34
- group 4: statements 0, 1
- group 5: statements 14, 15
- ungrouped: statements 6, 7, 8, 9, 25, 26, 27, 28, 29, 30, 31, 32, 33

## Grouping G4 (4 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 25, 26, 27, 28, 29, 30, 31, 32, 33
- group 2: statements 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24
- group 3: statements 10, 11, 34
- group 4: statements 0, 1

## Grouping G5 (11 groups)

- group 1: statements 5, 6, 7, 8, 9, 25, 26, 27, 28, 29, 30, 31, 32, 33
- group 2: statements 16, 17, 18, 19, 20, 21, 22, 23, 24
- group 3: statements 2, 5, 6, 8, 9
- group 4: statements 2, 3, 4
- group 5: statements 10, 11, 34
- group 6: statements 14, 15, 18
- group 7: statements 0, 1
- group 8: statements 3, 4
- group 9: statements 12, 16
- group 10: statements 13, 17
- group 11: statements 14, 15

## Grouping G6 (4 groups)

- group 1: statements 12, 16, 20, 24
- group 2: statements 14, 15, 18, 23
- group 3: statements 13, 17, 21
- group 4: statements 19, 22
- ungrouped: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34

## Grouping G7 (5 groups)

- group 1: statements 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24
- group 2: statements 2, 3, 4, 8
- group 3: statements 10, 11, 34
- group 4: statements 0, 1
- group 5: statements 14, 15
- ungrouped: statements 5, 6, 7, 9, 25, 26, 27, 28, 29, 30, 31, 32, 33

## Grouping G8 (6 groups)

- group 1: statements 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24
- group 2: statements 5, 6, 7, 8, 9, 25, 26, 27, 28, 29, 30, 31, 32, 33
- group 3: statements 2, 3, 4, 5, 6, 8, 9
- group 4: statements 10, 11, 34
- group 5: statements 0, 1
- group 6: statements 14, 15

## Grouping G9 (6 groups)

- group 1: statements 3, 4, 6, 8, 11, 14, 18, 19, 23, 28, 29, 33, 34
- group 2: statements 1, 2, 5, 9, 12, 13, 15, 16, 17, 21, 25, 26, 30, 31
- group 3: statements 1, 5, 10, 17, 20, 21, 27
- group 4: statements 22, 24, 32
- group 5: statements 0, 7
- group 6: statements 8, 14

## Grouping G10 (11 groups)

- group 1: statements 5, 6, 7, 8, 9, 25, 26, 27, 28, 29, 30, 31, 32, 33
- group 2: statements 2, 3, 4
- group 3: statements 10, 11, 34
- group 4: statements 16, 17, 18
- group 5: statements 20, 21, 22
- group 6: statements 0, 1
- group 7: statements 14, 15
- group 8: statements 23, 24
- group 9: statements 12
- group 10: statements 13
- group 11: statements 19

