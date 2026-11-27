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

A grid four columns wide and three rows high, standing upright. Two players, red and yellow, take turns dropping a counter into a column that is not full; red moves first. A counter falls to the lowest empty cell of its column. Three of one colour in a row, in a column or on a diagonal wins. If the grid fills with no such line, the game ends with no winner.

## The statements

```
  0  role(red)
  1  role(yellow)
  2  legal(P,drop(C)) :- true(control(P)) & landing(C,R)
  3  next(cell(C,R,r)) :- does(red,drop(C)) & landing(C,R)
  4  next(cell(C,R,y)) :- does(yellow,drop(C)) & landing(C,R)
  5  next(cell(C,R,W)) :- true(cell(C,R,W)) & distinct(W,b)
  6  next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(D)) & distinct(C,D)
  7  next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)
  8  below(1,2)
  9  below(2,3)
 10  landing(C,1) :- true(cell(C,1,b))
 11  landing(C,R) :- true(cell(C,R,b)) & below(Q,R) & ~true(cell(C,Q,b))
 12  legal(red,noop) :- true(control(yellow))
 13  legal(yellow,noop) :- true(control(red))
 14  next(control(red)) :- true(control(yellow))
 15  next(control(yellow)) :- true(control(red))
 16  right(1,2)
 17  right(2,3)
 18  right(3,4)
 19  hline(W) :- right(A,B) & right(B,C) & true(cell(A,R,W)) & true(cell(B,R,W)) & true(cell(C,R,W)) & distinct(W,b)
 20  vline(W) :- true(cell(C,1,W)) & true(cell(C,2,W)) & true(cell(C,3,W)) & distinct(W,b)
 21  dline(W) :- right(A,B) & right(B,C) & true(cell(A,1,W)) & true(cell(B,2,W)) & true(cell(C,3,W)) & distinct(W,b)
 22  dline(W) :- right(A,B) & right(B,C) & true(cell(A,3,W)) & true(cell(B,2,W)) & true(cell(C,1,W)) & distinct(W,b)
 23  line(W) :- hline(W)
 24  line(W) :- vline(W)
 25  line(W) :- dline(W)
 26  open :- true(cell(C,R,b))
 27  terminal :- line(r)
 28  terminal :- line(y)
 29  terminal :- ~open
 30  goal(red,100) :- line(r)
 31  goal(yellow,100) :- line(y)
 32  init(cell(1,1,b))
 33  init(cell(1,2,b))
 34  init(cell(1,3,b))
 35  init(cell(2,1,b))
 36  init(cell(2,2,b))
 37  init(cell(2,3,b))
 38  init(cell(3,1,b))
 39  init(cell(3,2,b))
 40  init(cell(3,3,b))
 41  init(cell(4,1,b))
 42  init(cell(4,2,b))
 43  init(cell(4,3,b))
 44  init(control(red))
```

## Grouping G1 (45 groups)

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
- group 36: statements 35
- group 37: statements 36
- group 38: statements 37
- group 39: statements 38
- group 40: statements 39
- group 41: statements 40
- group 42: statements 41
- group 43: statements 42
- group 44: statements 43
- group 45: statements 44

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44

## Grouping G3 (6 groups)

- group 1: statements 20, 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 2: statements 16, 17, 18, 19, 21, 22
- group 3: statements 2, 6, 7, 12, 13
- group 4: statements 3, 8, 9, 10, 11
- group 5: statements 14, 15, 44
- group 6: statements 0, 1
- ungrouped: statements 4, 5, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43

## Grouping G4 (4 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43
- group 2: statements 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 3: statements 14, 15, 44
- group 4: statements 0, 1

## Grouping G5 (16 groups)

- group 1: statements 3, 4, 5, 6, 7, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43
- group 2: statements 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 3: statements 16, 17, 18, 19, 21, 22
- group 4: statements 2, 3, 4, 6, 7
- group 5: statements 3, 4, 7, 10, 11
- group 6: statements 2, 10, 11
- group 7: statements 2, 12, 13
- group 8: statements 8, 9, 11
- group 9: statements 14, 15, 44
- group 10: statements 21, 22, 25
- group 11: statements 0, 1
- group 12: statements 8, 9
- group 13: statements 10, 11
- group 14: statements 12, 13
- group 15: statements 19, 23
- group 16: statements 20, 24

## Grouping G6 (4 groups)

- group 1: statements 2, 3, 4, 7, 8, 9, 10, 11
- group 2: statements 20, 23, 24, 25, 27, 28, 30, 31
- group 3: statements 16, 17, 18, 19, 21, 22
- group 4: statements 26, 29
- ungrouped: statements 0, 1, 5, 6, 12, 13, 14, 15, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44

## Grouping G7 (6 groups)

- group 1: statements 20, 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 2: statements 16, 17, 18, 19, 21, 22
- group 3: statements 7, 8, 9, 10, 11
- group 4: statements 2, 6, 12, 13
- group 5: statements 14, 15, 44
- group 6: statements 0, 1
- ungrouped: statements 3, 4, 5, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43

## Grouping G8 (6 groups)

- group 1: statements 3, 4, 5, 6, 7, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43
- group 2: statements 19, 20, 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 3: statements 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13
- group 4: statements 16, 17, 18, 19, 21, 22
- group 5: statements 14, 15, 44
- group 6: statements 0, 1

## Grouping G9 (6 groups)

- group 1: statements 0, 2, 7, 8, 11, 13, 16, 19, 21, 22, 25, 26, 30, 31, 32, 39, 40
- group 2: statements 3, 4, 9, 17, 18, 28, 33, 35, 37, 38, 44
- group 3: statements 0, 6, 7, 11, 12, 14, 20, 29, 39, 41, 43
- group 4: statements 10, 15, 27, 28, 36, 42
- group 5: statements 5, 23, 24
- group 6: statements 1, 34

## Grouping G10 (14 groups)

- group 1: statements 3, 4, 5, 6, 7, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43
- group 2: statements 2, 12, 13
- group 3: statements 14, 15, 44
- group 4: statements 16, 17, 18
- group 5: statements 23, 24, 25
- group 6: statements 27, 28, 29
- group 7: statements 0, 1
- group 8: statements 8, 9
- group 9: statements 10, 11
- group 10: statements 21, 22
- group 11: statements 30, 31
- group 12: statements 19
- group 13: statements 20
- group 14: statements 26

