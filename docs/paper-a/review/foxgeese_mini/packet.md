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

A 4x4 board. Four geese start on the bottom row and the fox near the top; the geese move first. The geese player moves one goose one square up or sideways onto an empty square. The fox steps one square up, down, left or right onto an empty square, or jumps over an adjacent goose onto the empty square beyond, capturing it. The fox wins by capturing two geese, or by lasting 20 turns. A side with no legal move on its turn loses.

## The statements

```
  0  role(geese)
  1  role(fox)
  2  index(1)
  3  index(2)
  4  index(3)
  5  index(4)
  6  up(1,2)
  7  up(2,3)
  8  up(3,4)
  9  beside(1,2)
 10  beside(2,1)
 11  beside(2,3)
 12  beside(3,2)
 13  beside(3,4)
 14  beside(4,3)
 15  straddle(1,2,3)
 16  straddle(2,3,4)
 17  straddle(3,2,1)
 18  straddle(4,3,2)
 19  orth(X,Y,X2,Y) :- beside(X,X2) & index(Y)
 20  orth(X,Y,X,Y2) :- index(X) & beside(Y,Y2)
 21  hop(X,Y,X1,Y,X2,Y) :- straddle(X,X1,X2) & index(Y)
 22  hop(X,Y,X,Y1,X,Y2) :- index(X) & straddle(Y,Y1,Y2)
 23  occupied(X,Y) :- true(goose(X,Y))
 24  occupied(X,Y) :- true(fox(X,Y))
 25  empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)
 26  waddle(X,Y,X,Y2) :- index(X) & up(Y,Y2)
 27  waddle(X,Y,X2,Y) :- beside(X,X2) & index(Y)
 28  glide(X,Y,X2,Y2) :- true(goose(X,Y)) & waddle(X,Y,X2,Y2) & empty(X2,Y2)
 29  legal(geese,glide(X,Y,X2,Y2)) :- true(control(geese)) & glide(X,Y,X2,Y2)
 30  glided(X,Y) :- does(geese,glide(X,Y,X2,Y2))
 31  next(goose(X2,Y2)) :- does(geese,glide(X,Y,X2,Y2))
 32  next(goose(X,Y)) :- true(goose(X,Y)) & ~glided(X,Y) & ~eaten(X,Y)
 33  stride(X,Y,X2,Y2) :- true(fox(X,Y)) & orth(X,Y,X2,Y2) & empty(X2,Y2)
 34  legal(fox,step(X,Y,X2,Y2)) :- true(control(fox)) & stride(X,Y,X2,Y2)
 35  next(fox(X2,Y2)) :- does(fox,step(X,Y,X2,Y2))
 36  next(fox(X,Y)) :- true(fox(X,Y)) & does(fox,noop)
 37  leap(X,Y,X2,Y2) :- true(fox(X,Y)) & hop(X,Y,X1,Y1,X2,Y2) & true(goose(X1,Y1)) & empty(X2,Y2)
 38  legal(fox,jump(X,Y,X2,Y2)) :- true(control(fox)) & leap(X,Y,X2,Y2)
 39  eaten(X1,Y1) :- does(fox,jump(X,Y,X2,Y2)) & hop(X,Y,X1,Y1,X2,Y2)
 40  next(fox(X2,Y2)) :- does(fox,jump(X,Y,X2,Y2))
 41  feast :- does(fox,jump(X,Y,X2,Y2))
 42  next(lost(N2)) :- true(lost(N)) & feast & succ(N,N2)
 43  next(lost(N)) :- true(lost(N)) & ~feast
 44  legal(geese,noop) :- true(control(fox))
 45  legal(fox,noop) :- true(control(geese))
 46  next(control(geese)) :- true(control(fox))
 47  next(control(fox)) :- true(control(geese))
 48  succ(0,1)
 49  succ(1,2)
 50  succ(2,3)
 51  succ(3,4)
 52  succ(4,5)
 53  succ(5,6)
 54  succ(6,7)
 55  succ(7,8)
 56  succ(8,9)
 57  succ(9,10)
 58  succ(10,11)
 59  succ(11,12)
 60  succ(12,13)
 61  succ(13,14)
 62  succ(14,15)
 63  succ(15,16)
 64  succ(16,17)
 65  succ(17,18)
 66  succ(18,19)
 67  succ(19,20)
 68  next(tick(N2)) :- true(tick(N)) & succ(N,N2)
 69  mobile(geese) :- glide(X,Y,X2,Y2)
 70  mobile(fox) :- stride(X,Y,X2,Y2)
 71  mobile(fox) :- leap(X,Y,X2,Y2)
 72  stuck(P) :- true(control(P)) & ~mobile(P)
 73  foxwins :- true(lost(2))
 74  foxwins :- stuck(geese)
 75  foxwins :- true(tick(20)) & ~stuck(fox)
 76  geesewin :- stuck(fox)
 77  terminal :- foxwins
 78  terminal :- geesewin
 79  goal(fox,100) :- foxwins
 80  goal(geese,0) :- foxwins
 81  goal(geese,100) :- geesewin
 82  goal(fox,0) :- geesewin
 83  init(goose(1,1))
 84  init(goose(2,1))
 85  init(goose(3,1))
 86  init(goose(4,1))
 87  init(fox(3,4))
 88  init(lost(0))
 89  init(control(geese))
 90  init(tick(0))
```

## Grouping G1 (91 groups)

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
- group 76: statements 75
- group 77: statements 76
- group 78: statements 77
- group 79: statements 78
- group 80: statements 79
- group 81: statements 80
- group 82: statements 81
- group 83: statements 82
- group 84: statements 83
- group 85: statements 84
- group 86: statements 85
- group 87: statements 86
- group 88: statements 87
- group 89: statements 88
- group 90: statements 89
- group 91: statements 90

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90

## Grouping G3 (10 groups)

- group 1: statements 2, 3, 4, 5, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 25, 26, 27
- group 2: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67
- group 3: statements 24, 29, 30, 33, 34, 35, 36, 38, 39, 40, 41, 44, 45, 87
- group 4: statements 68, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 90
- group 5: statements 23, 28, 31, 32, 37, 83, 84, 85, 86
- group 6: statements 69, 70, 71, 72
- group 7: statements 6, 7, 8
- group 8: statements 42, 43, 88
- group 9: statements 46, 47, 89
- group 10: statements 0, 1

## Grouping G4 (10 groups)

- group 1: statements 42, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68
- group 2: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 19, 20, 21, 22, 25, 26, 27
- group 3: statements 43, 68, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 90
- group 4: statements 24, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 44, 45, 87
- group 5: statements 23, 24, 25, 28, 30, 31, 32, 35, 37, 39, 40, 83, 84, 85, 86
- group 6: statements 15, 16, 17, 18, 21, 22, 39
- group 7: statements 69, 70, 71, 72
- group 8: statements 41, 42, 43, 73, 88
- group 9: statements 46, 47, 89
- group 10: statements 0, 1

## Grouping G5 (5 groups)

- group 1: statements 41, 42, 43, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68
- group 2: statements 2, 3, 4, 9, 10, 11, 12, 13, 14, 19, 20, 23, 24, 25, 27, 33, 34, 70
- group 3: statements 5, 15, 16, 17, 18, 21, 22, 30, 32, 37, 38, 39, 71
- group 4: statements 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82
- group 5: statements 6, 7, 8, 26, 28, 29, 69
- ungrouped: statements 0, 1, 31, 35, 36, 40, 44, 45, 46, 47, 83, 84, 85, 86, 87, 88, 89, 90

## Grouping G6 (11 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67
- group 2: statements 2, 3, 4, 5, 9, 10, 11, 12, 13, 14, 19, 20, 25, 26, 27
- group 3: statements 24, 29, 30, 33, 34, 35, 36, 38, 39, 40, 41, 44, 45, 87
- group 4: statements 68, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 90
- group 5: statements 23, 28, 31, 32, 37, 83, 84, 85, 86
- group 6: statements 15, 16, 17, 18, 21, 22
- group 7: statements 69, 70, 71, 72
- group 8: statements 6, 7, 8
- group 9: statements 42, 43, 88
- group 10: statements 46, 47, 89
- group 11: statements 0, 1

## Grouping G7 (28 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67
- group 2: statements 9, 10, 11, 12, 13, 14
- group 3: statements 31, 32, 83, 84, 85, 86
- group 4: statements 29, 34, 38, 44, 45
- group 5: statements 2, 3, 4, 5
- group 6: statements 15, 16, 17, 18
- group 7: statements 35, 36, 40, 87
- group 8: statements 79, 80, 81, 82
- group 9: statements 42, 43, 88
- group 10: statements 46, 47, 89
- group 11: statements 69, 70, 71
- group 12: statements 73, 74, 75
- group 13: statements 0, 1
- group 14: statements 19, 20
- group 15: statements 21, 22
- group 16: statements 23, 24
- group 17: statements 26, 27
- group 18: statements 68, 90
- group 19: statements 77, 78
- group 20: statements 25
- group 21: statements 28
- group 22: statements 30
- group 23: statements 33
- group 24: statements 37
- group 25: statements 39
- group 26: statements 41
- group 27: statements 72
- group 28: statements 76
- ungrouped: statements 6, 7, 8

## Grouping G8 (40 groups)

- group 1: statements 42, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67
- group 2: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68
- group 3: statements 23, 24, 28, 31, 32, 33, 35, 36, 37, 40, 83, 84, 85, 86, 87
- group 4: statements 73, 74, 75, 76, 77, 78, 79, 80, 81, 82
- group 5: statements 9, 10, 11, 12, 13, 14, 19, 20, 27
- group 6: statements 74, 75, 76, 77, 78, 79, 80, 81, 82
- group 7: statements 2, 3, 4, 5, 19, 20, 26, 27
- group 8: statements 2, 3, 4, 5, 21, 22
- group 9: statements 15, 16, 17, 18, 21, 22
- group 10: statements 23, 24, 25, 28, 33, 37
- group 11: statements 2, 3, 4, 5, 25
- group 12: statements 29, 34, 38, 44, 45
- group 13: statements 6, 7, 8, 26
- group 14: statements 29, 34, 44, 45
- group 15: statements 42, 43, 73, 88
- group 16: statements 69, 70, 71, 72
- group 17: statements 6, 7, 8
- group 18: statements 19, 20, 33
- group 19: statements 21, 22, 37
- group 20: statements 21, 22, 39
- group 21: statements 26, 27, 28
- group 22: statements 28, 29, 31
- group 23: statements 33, 34, 35
- group 24: statements 36, 44, 45
- group 25: statements 38, 39, 41
- group 26: statements 41, 42, 43
- group 27: statements 46, 47, 89
- group 28: statements 68, 75, 90
- group 29: statements 72, 74, 75
- group 30: statements 0, 1
- group 31: statements 28, 69
- group 32: statements 29, 30
- group 33: statements 30, 32
- group 34: statements 32, 39
- group 35: statements 33, 70
- group 36: statements 37, 38
- group 37: statements 37, 71
- group 38: statements 38, 40
- group 39: statements 72, 76
- group 40: statements 75, 90

## Grouping G9 (10 groups)

- group 1: statements 42, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68
- group 2: statements 2, 3, 4, 5, 6, 7, 8, 15, 16, 17, 18, 19, 20, 21, 22, 25, 26, 27, 39
- group 3: statements 43, 68, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 90
- group 4: statements 24, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 44, 45, 87
- group 5: statements 9, 10, 11, 12, 13, 14, 19, 20, 27
- group 6: statements 23, 24, 25, 28, 30, 31, 32, 35, 37, 39, 40, 83, 84, 85, 86
- group 7: statements 69, 70, 71, 72
- group 8: statements 41, 42, 43, 73, 88
- group 9: statements 46, 47, 89
- group 10: statements 0, 1

## Grouping G10 (10 groups)

- group 1: statements 0, 3, 9, 13, 16, 20, 28, 30, 35, 40, 42, 55, 57, 58, 60, 69, 70, 81, 84, 87, 88, 90
- group 2: statements 6, 11, 19, 21, 22, 23, 24, 26, 29, 34, 37, 41, 43, 44, 47, 52, 54, 76, 89
- group 3: statements 9, 12, 17, 27, 32, 36, 45, 49, 61, 64, 66, 68, 74, 77
- group 4: statements 2, 4, 14, 15, 21, 31, 33, 56, 63, 67, 73, 78, 82, 83, 85, 86
- group 5: statements 1, 23, 43, 48, 50, 59, 71, 79, 89
- group 6: statements 2, 10, 21, 31, 38, 51, 52, 62, 63, 65, 72, 73, 75, 85, 86
- group 7: statements 18, 39, 68, 80
- group 8: statements 5, 32, 66, 82, 90
- group 9: statements 25, 46, 53
- group 10: statements 7, 8

## Grouping G11 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 90
- group 2: statements 46, 47, 89
- group 3: statements 0, 1

