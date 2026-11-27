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

A 3x3 board of hexagonal cells. Red and blue take turns placing a stone of their colour on an empty cell; red moves first. Red wins by joining the bottom row to the top row with a chain of touching red stones, blue by joining the left column to the right column with blue stones.

## The statements

```
  0  role(red)
  1  role(blue)
  2  index(1)
  3  index(2)
  4  index(3)
  5  succ(1,2)
  6  succ(2,3)
  7  touches(X,Y,X2,Y) :- succ(X,X2) & index(Y)
  8  touches(X,Y,X2,Y) :- succ(X2,X) & index(Y)
  9  touches(X,Y,X,Y2) :- index(X) & succ(Y,Y2)
 10  touches(X,Y,X,Y2) :- index(X) & succ(Y2,Y)
 11  touches(X,Y,X2,Y2) :- succ(X,X2) & succ(Y2,Y)
 12  touches(X,Y,X2,Y2) :- succ(X2,X) & succ(Y,Y2)
 13  opponent(red,blue)
 14  opponent(blue,red)
 15  legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)
 16  taken(X,Y) :- true(cell(X,Y,P))
 17  next(cell(X,Y,P)) :- does(P,place(X,Y))
 18  next(cell(X,Y,P)) :- true(cell(X,Y,P))
 19  legal(red,noop) :- true(control(blue))
 20  legal(blue,noop) :- true(control(red))
 21  next(control(red)) :- true(control(blue))
 22  next(control(blue)) :- true(control(red))
 23  firstedge(red,X,1) :- index(X)
 24  firstedge(blue,1,Y) :- index(Y)
 25  lastedge(red,X,3) :- index(X)
 26  lastedge(blue,3,Y) :- index(Y)
 27  reach(P,X,Y) :- firstedge(P,X,Y) & true(cell(X,Y,P))
 28  reach(P,X2,Y2) :- reach(P,X,Y) & touches(X,Y,X2,Y2) & true(cell(X2,Y2,P))
 29  joined(P) :- reach(P,X,Y) & lastedge(P,X,Y)
 30  terminal :- joined(P)
 31  goal(P,100) :- joined(P)
 32  goal(P,0) :- opponent(P,Q) & joined(Q)
 33  init(control(red))
```

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33

## Grouping G2 (15 groups)

- group 1: statements 7, 8, 9, 10, 11, 12
- group 2: statements 2, 3, 4
- group 3: statements 15, 19, 20
- group 4: statements 21, 22, 33
- group 5: statements 0, 1
- group 6: statements 5, 6
- group 7: statements 13, 14
- group 8: statements 17, 18
- group 9: statements 23, 24
- group 10: statements 25, 26
- group 11: statements 27, 28
- group 12: statements 31, 32
- group 13: statements 16
- group 14: statements 29
- group 15: statements 30

## Grouping G3 (7 groups)

- group 1: statements 5, 6, 7, 8, 9, 10, 11, 12
- group 2: statements 2, 3, 4, 23, 24, 25, 26
- group 3: statements 13, 14, 29, 30, 31, 32
- group 4: statements 15, 16, 17, 18, 19, 20
- group 5: statements 21, 22, 33
- group 6: statements 0, 1
- group 7: statements 27, 28

## Grouping G4 (3 groups)

- group 1: statements 2, 3, 4, 15, 16, 23, 24, 25, 26, 27, 29, 30, 31
- group 2: statements 5, 6, 7, 8, 9, 10, 11, 12, 28
- group 3: statements 13, 14, 32
- ungrouped: statements 0, 1, 17, 18, 19, 20, 21, 22, 33

## Grouping G5 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32
- group 2: statements 21, 22, 33
- group 3: statements 0, 1

## Grouping G6 (16 groups)

- group 1: statements 5, 6, 7, 8, 9, 10, 11, 12, 28
- group 2: statements 2, 3, 4, 7, 8, 9, 10
- group 3: statements 2, 3, 4, 23, 24, 25, 26
- group 4: statements 13, 14, 29, 30, 31, 32
- group 5: statements 2, 3, 4, 15
- group 6: statements 15, 19, 20
- group 7: statements 21, 22, 33
- group 8: statements 23, 24, 27
- group 9: statements 25, 26, 29
- group 10: statements 0, 1
- group 11: statements 15, 16
- group 12: statements 15, 17
- group 13: statements 17, 18
- group 14: statements 27, 28
- group 15: statements 27, 29
- group 16: statements 28, 29

## Grouping G7 (8 groups)

- group 1: statements 2, 3, 4, 15, 23, 24, 25, 26, 27
- group 2: statements 13, 14, 29, 30, 31, 32
- group 3: statements 5, 6, 7, 8, 9, 10, 11, 12, 28
- group 4: statements 15, 16, 17, 19, 20
- group 5: statements 21, 22, 33
- group 6: statements 0, 1
- group 7: statements 5, 6
- group 8: statements 27, 28
- ungrouped: statements 18

## Grouping G8 (8 groups)

- group 1: statements 9, 10, 11, 12, 20, 25, 27, 28, 30
- group 2: statements 2, 8, 14, 16, 26, 33
- group 3: statements 1, 5, 13, 15, 17, 21, 22, 23, 31
- group 4: statements 3, 4, 19, 29, 30
- group 5: statements 6, 18, 24
- group 6: statements 0, 7
- group 7: statements 5, 21
- group 8: statements 12, 15
- ungrouped: statements 32

## Grouping G9 (34 groups)

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

