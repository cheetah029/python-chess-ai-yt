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

A 3x3 bar of chocolate; the bottom-left square is poisoned. Players take turns choosing a remaining square and eating it together with every square above it and to its right. The player who eats the poisoned square loses.

## The statements

```
  0  role(first)
  1  role(second)
  2  atmost(1,1)
  3  atmost(1,2)
  4  atmost(1,3)
  5  atmost(2,2)
  6  atmost(2,3)
  7  atmost(3,3)
  8  opponent(first,second)
  9  opponent(second,first)
 10  legal(P,bite(X,Y)) :- true(control(P)) & true(square(X,Y))
 11  eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)
 12  next(square(X,Y)) :- true(square(X,Y)) & ~eaten(X,Y)
 13  legal(first,noop) :- true(control(second))
 14  legal(second,noop) :- true(control(first))
 15  next(control(first)) :- true(control(second))
 16  next(control(second)) :- true(control(first))
 17  poisoned :- ~true(square(1,1))
 18  terminal :- poisoned
 19  goal(P,100) :- poisoned & true(control(P))
 20  goal(P,0) :- poisoned & true(control(Q)) & opponent(P,Q)
 21  init(square(1,1))
 22  init(square(1,2))
 23  init(square(1,3))
 24  init(square(2,1))
 25  init(square(2,2))
 26  init(square(2,3))
 27  init(square(3,1))
 28  init(square(3,2))
 29  init(square(3,3))
 30  init(control(first))
```

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30

## Grouping G2 (10 groups)

- group 1: statements 12, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 2, 3, 4, 5, 6, 7
- group 3: statements 10, 13, 14
- group 4: statements 15, 16, 30
- group 5: statements 0, 1
- group 6: statements 8, 9
- group 7: statements 19, 20
- group 8: statements 11
- group 9: statements 17
- group 10: statements 18

## Grouping G3 (5 groups)

- group 1: statements 12, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 8, 9, 15, 16, 17, 18, 19, 20, 30
- group 3: statements 2, 3, 4, 5, 6, 7, 11
- group 4: statements 10, 13, 14
- group 5: statements 0, 1

## Grouping G4 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 11, 12
- group 2: statements 8, 9, 20
- group 3: statements 17, 18, 19
- ungrouped: statements 0, 1, 10, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30

## Grouping G5 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 8, 9, 15, 16, 17, 18, 19, 20, 30
- group 3: statements 0, 1

## Grouping G6 (7 groups)

- group 1: statements 12, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 8, 9, 15, 16, 17, 18, 19, 20, 30
- group 3: statements 2, 3, 4, 5, 6, 7, 11
- group 4: statements 10, 13, 14
- group 5: statements 0, 1
- group 6: statements 10, 11
- group 7: statements 11, 12

## Grouping G7 (5 groups)

- group 1: statements 11, 12, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 8, 9, 15, 16, 17, 18, 19, 20, 30
- group 3: statements 2, 3, 4, 5, 6, 7, 11
- group 4: statements 10, 11, 13, 14
- group 5: statements 0, 1

## Grouping G8 (5 groups)

- group 1: statements 1, 8, 9, 12, 13, 15, 16, 22, 24, 26, 29
- group 2: statements 4, 6, 11, 14, 18, 23, 25, 27, 28
- group 3: statements 0, 5, 7, 17, 19, 26, 30
- group 4: statements 2, 20, 21, 26
- group 5: statements 3, 10

## Grouping G9 (31 groups)

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

