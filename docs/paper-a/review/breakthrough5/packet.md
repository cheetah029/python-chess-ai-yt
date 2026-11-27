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

A 5x5 board. White starts with ten pawns on rows 1 and 2, black with ten on rows 4 and 5; white moves first and moves up the board, black down. On a turn a player moves one pawn one row forward: straight ahead onto an empty square, diagonally ahead onto an empty square, or diagonally ahead onto an enemy pawn, which is captured. A pawn never captures straight ahead. A pawn reaching the far row wins. A player with no legal move loses.

## The statements

```
  0  role(white)
  1  role(black)
  2  index(1)
  3  index(2)
  4  index(3)
  5  index(4)
  6  index(5)
  7  forward(white,1,2)
  8  forward(white,2,3)
  9  forward(white,3,4)
 10  forward(white,4,5)
 11  forward(black,5,4)
 12  forward(black,4,3)
 13  forward(black,3,2)
 14  forward(black,2,1)
 15  beside(1,2)
 16  beside(2,1)
 17  beside(2,3)
 18  beside(3,2)
 19  beside(3,4)
 20  beside(4,3)
 21  beside(4,5)
 22  beside(5,4)
 23  opponent(white,black)
 24  opponent(black,white)
 25  occupied(X,Y) :- true(cell(X,Y,P))
 26  empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)
 27  straight(P,X,Y,X,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & empty(X,Y2)
 28  diagonal(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & empty(X2,Y2)
 29  capture(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & opponent(P,Q) & true(cell(X2,Y2,Q))
 30  legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & straight(P,X,Y,X2,Y2)
 31  legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & diagonal(P,X,Y,X2,Y2)
 32  legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & capture(P,X,Y,X2,Y2)
 33  next(cell(X2,Y2,P)) :- does(P,move(X,Y,X2,Y2))
 34  touched(X,Y) :- does(P,move(X,Y,X2,Y2))
 35  touched(X2,Y2) :- does(P,move(X,Y,X2,Y2))
 36  next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~touched(X,Y)
 37  legal(white,noop) :- true(control(black))
 38  legal(black,noop) :- true(control(white))
 39  next(control(white)) :- true(control(black))
 40  next(control(black)) :- true(control(white))
 41  goalrow(white,5)
 42  goalrow(black,1)
 43  arrived(P) :- goalrow(P,Y) & true(cell(X,Y,P))
 44  mobile(P) :- straight(P,X,Y,X2,Y2)
 45  mobile(P) :- diagonal(P,X,Y,X2,Y2)
 46  mobile(P) :- capture(P,X,Y,X2,Y2)
 47  stuck(P) :- true(control(P)) & ~mobile(P)
 48  terminal :- arrived(P)
 49  terminal :- stuck(P)
 50  goal(P,100) :- arrived(P)
 51  goal(P,100) :- opponent(P,Q) & stuck(Q)
 52  goal(P,0) :- opponent(P,Q) & arrived(Q)
 53  goal(P,0) :- stuck(P)
 54  init(cell(1,1,white))
 55  init(cell(2,1,white))
 56  init(cell(3,1,white))
 57  init(cell(4,1,white))
 58  init(cell(5,1,white))
 59  init(cell(1,2,white))
 60  init(cell(2,2,white))
 61  init(cell(3,2,white))
 62  init(cell(4,2,white))
 63  init(cell(5,2,white))
 64  init(cell(1,4,black))
 65  init(cell(2,4,black))
 66  init(cell(3,4,black))
 67  init(cell(4,4,black))
 68  init(cell(5,4,black))
 69  init(cell(1,5,black))
 70  init(cell(2,5,black))
 71  init(cell(3,5,black))
 72  init(cell(4,5,black))
 73  init(cell(5,5,black))
 74  init(control(white))
```

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74

## Grouping G2 (20 groups)

- group 1: statements 33, 36, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- group 2: statements 7, 8, 9, 10, 11, 12, 13, 14
- group 3: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 4: statements 2, 3, 4, 5, 6
- group 5: statements 30, 31, 32, 37, 38
- group 6: statements 50, 51, 52, 53
- group 7: statements 39, 40, 74
- group 8: statements 44, 45, 46
- group 9: statements 0, 1
- group 10: statements 23, 24
- group 11: statements 34, 35
- group 12: statements 41, 42
- group 13: statements 48, 49
- group 14: statements 25
- group 15: statements 26
- group 16: statements 27
- group 17: statements 28
- group 18: statements 29
- group 19: statements 43
- group 20: statements 47

## Grouping G3 (8 groups)

- group 1: statements 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- group 2: statements 23, 24, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 3: statements 7, 8, 9, 10, 11, 12, 13, 14, 27, 28
- group 4: statements 15, 16, 17, 18, 19, 20, 21, 22, 29
- group 5: statements 30, 31, 32, 33, 34, 35, 37, 38
- group 6: statements 2, 3, 4, 5, 6, 25, 26
- group 7: statements 39, 40, 74
- group 8: statements 0, 1
- ungrouped: statements 36

## Grouping G4 (5 groups)

- group 1: statements 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 29, 30, 31, 32
- group 2: statements 23, 24, 41, 42, 43, 48, 50, 51, 52
- group 3: statements 2, 3, 4, 5, 6, 25, 26
- group 4: statements 44, 45, 46, 47, 49, 53
- group 5: statements 34, 35, 36
- ungrouped: statements 0, 1, 33, 37, 38, 39, 40, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74

## Grouping G5 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- group 2: statements 39, 40, 74
- group 3: statements 0, 1

## Grouping G6 (19 groups)

- group 1: statements 33, 36, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- group 2: statements 23, 24, 29, 43, 46, 47, 48, 49, 50, 51, 52, 53
- group 3: statements 7, 8, 9, 10, 11, 12, 13, 14, 27, 28, 29
- group 4: statements 15, 16, 17, 18, 19, 20, 21, 22, 28, 29
- group 5: statements 30, 31, 32, 34, 35, 37, 38
- group 6: statements 2, 3, 4, 5, 6, 26
- group 7: statements 30, 31, 32, 33
- group 8: statements 44, 45, 46, 47
- group 9: statements 26, 27, 28
- group 10: statements 34, 35, 36
- group 11: statements 39, 40, 74
- group 12: statements 41, 42, 43
- group 13: statements 0, 1
- group 14: statements 25, 26
- group 15: statements 27, 30
- group 16: statements 27, 44
- group 17: statements 28, 31
- group 18: statements 28, 45
- group 19: statements 29, 32

## Grouping G7 (8 groups)

- group 1: statements 33, 34, 35, 36, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- group 2: statements 23, 24, 29, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 3: statements 7, 8, 9, 10, 11, 12, 13, 14, 26, 27, 28, 29
- group 4: statements 15, 16, 17, 18, 19, 20, 21, 22, 28, 29
- group 5: statements 2, 3, 4, 5, 6, 25, 26
- group 6: statements 30, 31, 32, 33, 34, 35, 37, 38
- group 7: statements 39, 40, 74
- group 8: statements 0, 1

## Grouping G8 (8 groups)

- group 1: statements 5, 6, 8, 16, 17, 18, 27, 28, 33, 34, 38, 39, 44, 45, 48, 51, 53, 56, 61, 62, 65, 68, 70, 71
- group 2: statements 4, 9, 19, 21, 22, 23, 30, 35, 43, 46, 54, 57, 58, 59, 67, 74
- group 3: statements 1, 12, 14, 23, 26, 32, 40, 41, 55, 66, 69, 73
- group 4: statements 7, 10, 15, 23, 24, 26, 31, 36, 42, 50
- group 5: statements 11, 25, 29, 37, 41, 47, 63
- group 6: statements 0, 2, 3, 13, 28, 56, 60, 71
- group 7: statements 20, 49, 64
- group 8: statements 52, 72

## Grouping G9 (75 groups)

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
- group 46: statements 45
- group 47: statements 46
- group 48: statements 47
- group 49: statements 48
- group 50: statements 49
- group 51: statements 50
- group 52: statements 51
- group 53: statements 52
- group 54: statements 53
- group 55: statements 54
- group 56: statements 55
- group 57: statements 56
- group 58: statements 57
- group 59: statements 58
- group 60: statements 59
- group 61: statements 60
- group 62: statements 61
- group 63: statements 62
- group 64: statements 63
- group 65: statements 64
- group 66: statements 65
- group 67: statements 66
- group 68: statements 67
- group 69: statements 68
- group 70: statements 69
- group 71: statements 70
- group 72: statements 71
- group 73: statements 72
- group 74: statements 73
- group 75: statements 74

