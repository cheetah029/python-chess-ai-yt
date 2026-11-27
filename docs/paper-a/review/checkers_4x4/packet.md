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

A 4x4 board, played on the dark squares. White starts with two men on its first row and moves up; black with two men on the last row, moving down; white moves first. A man steps one square diagonally forward onto an empty square; a king steps diagonally in any direction. A piece jumps diagonally over an adjacent enemy piece onto the empty square beyond, capturing it; one jump per turn. If a player can jump, they must. A man ending on the far row becomes a king. A player with no legal move loses; after 16 turns in all the game is drawn.

## The statements

```
  0  role(white)
  1  role(black)
  2  index(1)
  3  index(2)
  4  index(3)
  5  index(4)
  6  forward(white,1,2)
  7  forward(white,2,3)
  8  forward(white,3,4)
  9  forward(black,4,3)
 10  forward(black,3,2)
 11  forward(black,2,1)
 12  near(1,2)
 13  near(2,1)
 14  near(2,3)
 15  near(3,2)
 16  near(3,4)
 17  near(4,3)
 18  straddle(1,2,3)
 19  straddle(2,3,4)
 20  straddle(3,2,1)
 21  straddle(4,3,2)
 22  opponent(white,black)
 23  opponent(black,white)
 24  occupied(X,Y) :- true(at(P,K,X,Y))
 25  empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)
 26  enemy(P,X,Y) :- true(at(Q,K,X,Y)) & opponent(P,Q)
 27  heading(P,man,Y,Y2) :- forward(P,Y,Y2)
 28  heading(P,king,Y,Y2) :- role(P) & near(Y,Y2)
 29  step(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y2) & near(X,X2) & empty(X2,Y2)
 30  legal(P,step(X,Y,X2,Y2)) :- true(control(P)) & step(P,X,Y,X2,Y2) & ~canjump(P)
 31  jump(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y1) & straddle(Y,Y1,Y2) & straddle(X,X1,X2) & enemy(P,X1,Y1) & empty(X2,Y2)
 32  canjump(P) :- jump(P,X,Y,X2,Y2)
 33  legal(P,jump(X,Y,X2,Y2)) :- true(control(P)) & jump(P,X,Y,X2,Y2)
 34  jumped(X1,Y1) :- does(P,jump(X,Y,X2,Y2)) & straddle(X,X1,X2) & straddle(Y,Y1,Y2)
 35  arrives(P,K,X2,Y2) :- does(P,step(X,Y,X2,Y2)) & true(at(P,K,X,Y))
 36  arrives(P,K,X2,Y2) :- does(P,jump(X,Y,X2,Y2)) & true(at(P,K,X,Y))
 37  left(X,Y) :- does(P,step(X,Y,X2,Y2))
 38  left(X,Y) :- does(P,jump(X,Y,X2,Y2))
 39  next(at(P,K,X,Y)) :- arrives(P,K,X,Y) & ~farrow(P,Y)
 40  next(at(Q,K,X,Y)) :- true(at(Q,K,X,Y)) & ~left(X,Y) & ~jumped(X,Y)
 41  farrow(white,4)
 42  farrow(black,1)
 43  next(at(P,king,X,Y)) :- arrives(P,K,X,Y) & farrow(P,Y)
 44  legal(white,noop) :- true(control(black))
 45  legal(black,noop) :- true(control(white))
 46  next(control(white)) :- true(control(black))
 47  next(control(black)) :- true(control(white))
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
 64  next(tick(N2)) :- true(tick(N)) & succ(N,N2)
 65  mobile(P) :- step(P,X,Y,X2,Y2)
 66  mobile(P) :- jump(P,X,Y,X2,Y2)
 67  stuck(P) :- true(control(P)) & ~mobile(P)
 68  blocked :- stuck(P)
 69  timeup :- true(tick(16)) & ~blocked
 70  terminal :- blocked
 71  terminal :- timeup
 72  goal(P,0) :- stuck(P)
 73  goal(P,100) :- opponent(P,Q) & stuck(Q)
 74  goal(P,50) :- role(P) & timeup
 75  init(at(white,man,2,1))
 76  init(at(white,man,4,1))
 77  init(at(black,man,1,4))
 78  init(at(black,man,3,4))
 79  init(control(white))
 80  init(tick(0))
```

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80

## Grouping G2 (27 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63
- group 2: statements 6, 7, 8, 9, 10, 11
- group 3: statements 12, 13, 14, 15, 16, 17
- group 4: statements 2, 3, 4, 5
- group 5: statements 18, 19, 20, 21
- group 6: statements 30, 33, 44, 45
- group 7: statements 46, 47, 79
- group 8: statements 72, 73, 74
- group 9: statements 0, 1
- group 10: statements 22, 23
- group 11: statements 27, 28
- group 12: statements 35, 36
- group 13: statements 37, 38
- group 14: statements 41, 42
- group 15: statements 64, 80
- group 16: statements 65, 66
- group 17: statements 70, 71
- group 18: statements 24
- group 19: statements 25
- group 20: statements 26
- group 21: statements 29
- group 22: statements 31
- group 23: statements 32
- group 24: statements 34
- group 25: statements 67
- group 26: statements 68
- group 27: statements 69
- ungrouped: statements 39, 40, 43, 75, 76, 77, 78

## Grouping G3 (10 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63
- group 2: statements 0, 1, 22, 23, 26, 67, 68, 69, 70, 71, 72, 73, 74
- group 3: statements 30, 32, 33, 35, 36, 37, 38, 44, 45
- group 4: statements 39, 40, 41, 42, 43, 75, 76, 77, 78
- group 5: statements 12, 13, 14, 15, 16, 17, 28, 29
- group 6: statements 18, 19, 20, 21, 31, 34, 65, 66
- group 7: statements 6, 7, 8, 9, 10, 11, 27
- group 8: statements 2, 3, 4, 5, 24, 25
- group 9: statements 46, 47, 79
- group 10: statements 64, 80

## Grouping G4 (8 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64
- group 2: statements 18, 19, 20, 21, 30, 31, 32, 33, 34, 37, 38, 40
- group 3: statements 22, 23, 26, 65, 66, 67, 68, 70, 72, 73
- group 4: statements 12, 13, 14, 15, 16, 17, 28, 29
- group 5: statements 6, 7, 8, 9, 10, 11, 27
- group 6: statements 2, 3, 4, 5, 24, 25
- group 7: statements 35, 36, 39, 41, 42, 43
- group 8: statements 0, 1, 69, 71, 74
- ungrouped: statements 44, 45, 46, 47, 75, 76, 77, 78, 79, 80

## Grouping G5 (2 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 80
- group 2: statements 46, 47, 79

## Grouping G6 (32 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64
- group 2: statements 0, 1, 22, 23, 26, 28, 67, 68, 69, 70, 71, 72, 73, 74
- group 3: statements 12, 13, 14, 15, 16, 17, 28, 29
- group 4: statements 6, 7, 8, 9, 10, 11, 27
- group 5: statements 39, 40, 43, 75, 76, 77, 78
- group 6: statements 18, 19, 20, 21, 31, 34
- group 7: statements 2, 3, 4, 5, 25
- group 8: statements 31, 33, 34, 36, 38
- group 9: statements 30, 33, 44, 45
- group 10: statements 34, 37, 38, 40
- group 11: statements 35, 36, 39, 43
- group 12: statements 39, 41, 42, 43
- group 13: statements 27, 28, 29
- group 14: statements 30, 35, 37
- group 15: statements 46, 47, 79
- group 16: statements 64, 69, 80
- group 17: statements 65, 66, 67
- group 18: statements 24, 25
- group 19: statements 25, 29
- group 20: statements 25, 31
- group 21: statements 26, 31
- group 22: statements 27, 31
- group 23: statements 28, 31
- group 24: statements 29, 30
- group 25: statements 29, 65
- group 26: statements 30, 32
- group 27: statements 31, 32
- group 28: statements 31, 66
- group 29: statements 35, 36
- group 30: statements 37, 38
- group 31: statements 41, 42
- group 32: statements 65, 66

## Grouping G7 (10 groups)

- group 1: statements 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64
- group 2: statements 0, 1, 22, 23, 26, 28, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 80
- group 3: statements 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 75, 76, 77, 78
- group 4: statements 12, 13, 14, 15, 16, 17, 27, 28, 29, 65
- group 5: statements 6, 7, 8, 9, 10, 11, 27
- group 6: statements 18, 19, 20, 21, 31, 32, 34, 65, 66
- group 7: statements 2, 3, 4, 5, 24, 25
- group 8: statements 30, 32, 33, 34, 35, 36, 37, 38, 44, 45
- group 9: statements 46, 47, 79
- group 10: statements 64, 69, 80

## Grouping G8 (10 groups)

- group 1: statements 4, 6, 18, 19, 20, 21, 22, 30, 32, 35, 39, 43, 46, 54, 57, 70, 72
- group 2: statements 2, 12, 17, 24, 27, 36, 38, 45, 48, 49, 51, 59, 61, 63, 64, 66, 68
- group 3: statements 0, 3, 5, 16, 25, 28, 31, 33, 62, 65, 71, 73, 77, 78
- group 4: statements 2, 8, 12, 23, 41, 42, 47, 50, 52, 69
- group 5: statements 1, 11, 29, 37, 44, 52, 60
- group 6: statements 10, 12, 14, 15, 31, 34, 56, 68, 80
- group 7: statements 7, 9, 26, 67, 75, 76
- group 8: statements 0, 15, 25, 31, 55, 58, 73, 74, 78, 79
- group 9: statements 13, 40, 53
- group 10: statements 32, 49, 64

## Grouping G9 (81 groups)

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

