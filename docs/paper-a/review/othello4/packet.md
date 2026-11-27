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

A 4x4 board. The four centre squares start filled: white on (2,2) and (3,3), black on (2,3) and (3,2). Black moves first. A player places a disc on an empty square so that it outflanks at least one line of the opponent's discs: a straight or diagonal run of opponent discs closed at the far end by one of the player's own. Every outflanked disc, in every direction, flips to the player. A player who has no such placement passes. The game ends when neither player can place; the player with more discs wins, and equal counts are a draw.

## The statements

```
  0  role(black)
  1  role(white)
  2  index(1)
  3  index(2)
  4  index(3)
  5  index(4)
  6  succ(0,1)
  7  succ(1,2)
  8  succ(2,3)
  9  succ(3,4)
 10  succ(4,5)
 11  succ(5,6)
 12  succ(6,7)
 13  succ(7,8)
 14  succ(8,9)
 15  succ(9,10)
 16  succ(10,11)
 17  succ(11,12)
 18  succ(12,13)
 19  succ(13,14)
 20  succ(14,15)
 21  succ(15,16)
 22  delta(n,0,1)
 23  delta(s,0,m)
 24  delta(e,1,0)
 25  delta(w,m,0)
 26  delta(ne,1,1)
 27  delta(nw,m,1)
 28  delta(se,1,m)
 29  delta(sw,m,m)
 30  shift(A,0,A) :- index(A)
 31  shift(A,1,B) :- succ(A,B) & index(B)
 32  shift(A,m,B) :- succ(B,A) & index(B)
 33  step(X,Y,D,X2,Y2) :- delta(D,DX,DY) & shift(X,DX,X2) & shift(Y,DY,Y2)
 34  opponent(black,white)
 35  opponent(white,black)
 36  occupied(X,Y) :- true(cell(X,Y,C))
 37  empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)
 38  closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & true(cell(X2,Y2,P))
 39  closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)
 40  flanks(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)
 41  placeable(P,X,Y) :- empty(X,Y) & flanks(P,X,Y,D)
 42  legal(P,place(X,Y)) :- true(control(P)) & placeable(P,X,Y)
 43  next(cell(X,Y,P)) :- does(P,place(X,Y))
 44  flipped(P,X,Y,D,X2,Y2) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)
 45  flipped(P,X,Y,D,X3,Y3) :- flipped(P,X,Y,D,X2,Y2) & step(X2,Y2,D,X3,Y3) & opponent(P,Q) & true(cell(X3,Y3,Q)) & closes(P,X3,Y3,D)
 46  flips(A,B) :- does(P,place(X,Y)) & flipped(P,X,Y,D,A,B)
 47  next(cell(A,B,P)) :- does(P,place(X,Y)) & flips(A,B)
 48  next(cell(A,B,C)) :- true(cell(A,B,C)) & ~flips(A,B)
 49  canplace(P) :- placeable(P,X,Y)
 50  legal(P,pass) :- true(control(P)) & ~canplace(P)
 51  legal(black,noop) :- true(control(white))
 52  legal(white,noop) :- true(control(black))
 53  next(control(white)) :- true(control(black))
 54  next(control(black)) :- true(control(white))
 55  after(X,Y,X2,Y) :- succ(X,X2) & index(X2) & index(Y)
 56  after(4,Y,1,Y2) :- succ(Y,Y2) & index(Y2)
 57  tally(P,1,1,1) :- true(cell(1,1,P))
 58  tally(P,1,1,0) :- role(P) & ~true(cell(1,1,P))
 59  tally(P,X2,Y2,M) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & true(cell(X2,Y2,P)) & succ(N,M)
 60  tally(P,X2,Y2,N) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & ~true(cell(X2,Y2,P))
 61  discs(P,N) :- tally(P,4,4,N)
 62  fewer(N,M) :- succ(N,M)
 63  fewer(N,M) :- succ(N,K) & fewer(K,M)
 64  ahead(P) :- opponent(P,Q) & discs(P,M) & discs(Q,N) & fewer(N,M)
 65  level :- discs(black,N) & discs(white,N)
 66  terminal :- ~canplace(black) & ~canplace(white)
 67  goal(P,100) :- ahead(P)
 68  goal(P,50) :- level
 69  goal(P,0) :- opponent(P,Q) & ahead(Q)
 70  init(cell(2,2,white))
 71  init(cell(3,3,white))
 72  init(cell(2,3,black))
 73  init(cell(3,2,black))
 74  init(control(black))
```

## Grouping G1 (75 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74

## Grouping G3 (8 groups)

- group 1: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
- group 2: statements 34, 35, 38, 39, 40, 44, 45, 49, 64, 65, 66, 67, 68, 69
- group 3: statements 41, 42, 43, 46, 47, 48, 50, 51, 52, 70, 71, 72, 73
- group 4: statements 2, 3, 4, 5, 30, 31, 32, 36, 37, 55, 56
- group 5: statements 22, 23, 24, 25, 26, 27, 28, 29, 33
- group 6: statements 0, 1, 57, 58, 59, 60, 61
- group 7: statements 53, 54, 74
- group 8: statements 62, 63

## Grouping G4 (2 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- group 2: statements 53, 54, 74

## Grouping G5 (27 groups)

- group 1: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 31, 32, 55, 56, 62, 63
- group 2: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 55, 56, 59, 60
- group 3: statements 34, 35, 38, 39, 40, 44, 45, 49, 64, 65, 66, 67, 68, 69
- group 4: statements 34, 35, 39, 40, 44, 45, 49, 50, 64, 65, 66, 67, 68, 69
- group 5: statements 2, 3, 4, 5, 30, 31, 32, 55, 56
- group 6: statements 22, 23, 24, 25, 26, 27, 28, 29, 33
- group 7: statements 43, 47, 48, 70, 71, 72, 73
- group 8: statements 2, 3, 4, 5, 30, 37
- group 9: statements 33, 38, 39, 40, 44, 45
- group 10: statements 57, 58, 59, 60, 61
- group 11: statements 42, 50, 51, 52
- group 12: statements 0, 1, 58
- group 13: statements 31, 32, 33
- group 14: statements 40, 41, 49
- group 15: statements 42, 43, 47
- group 16: statements 44, 45, 46
- group 17: statements 46, 47, 48
- group 18: statements 50, 51, 52
- group 19: statements 53, 54, 74
- group 20: statements 61, 64, 65
- group 21: statements 62, 63, 64
- group 22: statements 0, 1
- group 23: statements 30, 33
- group 24: statements 36, 37
- group 25: statements 37, 41
- group 26: statements 41, 42
- group 27: statements 42, 46

## Grouping G6 (4 groups)

- group 1: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 31, 32, 55, 56, 59, 62, 63
- group 2: statements 22, 23, 24, 25, 26, 27, 28, 29, 33, 34, 35, 38, 39, 40, 44, 45, 46, 47, 48, 64, 67, 69
- group 3: statements 2, 3, 4, 5, 30, 36, 37, 41, 42, 49, 50, 66
- group 4: statements 0, 1, 57, 58, 60, 61, 65, 68
- ungrouped: statements 43, 51, 52, 53, 54, 70, 71, 72, 73, 74

## Grouping G7 (8 groups)

- group 1: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
- group 2: statements 34, 35, 38, 39, 40, 41, 44, 45, 49, 64, 65, 66, 67, 68, 69
- group 3: statements 42, 43, 46, 47, 48, 50, 51, 52, 70, 71, 72, 73
- group 4: statements 2, 3, 4, 5, 30, 31, 32, 36, 37, 55, 56
- group 5: statements 22, 23, 24, 25, 26, 27, 28, 29, 33
- group 6: statements 0, 1, 57, 58, 59, 60, 61
- group 7: statements 53, 54, 74
- group 8: statements 62, 63

## Grouping G8 (8 groups)

- group 1: statements 33, 34, 35, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 49, 50, 51, 52, 61, 64, 65, 66, 67, 68, 69
- group 2: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 31, 32, 55, 56, 59, 62, 63
- group 3: statements 2, 3, 4, 5, 30, 31, 32, 36, 37, 41, 55, 56
- group 4: statements 22, 23, 24, 25, 26, 27, 28, 29, 33
- group 5: statements 0, 1, 57, 58, 59, 60, 61
- group 6: statements 43, 46, 47, 48, 70, 71, 72, 73
- group 7: statements 53, 54, 74
- group 8: statements 62, 63

## Grouping G9 (8 groups)

- group 1: statements 4, 8, 9, 13, 19, 20, 21, 22, 27, 28, 30, 35, 38, 43, 45, 51, 56, 59, 61, 62, 64, 67, 71, 74
- group 2: statements 0, 1, 3, 6, 7, 10, 14, 15, 16, 17, 18, 24, 32, 34, 36, 37, 40, 42, 50, 55, 66, 69, 73
- group 3: statements 0, 2, 3, 11, 16, 22, 29, 34, 44, 47, 60, 63
- group 4: statements 12, 23, 25, 26, 31, 41, 54, 56, 58
- group 5: statements 6, 8, 39, 48, 52, 68, 72
- group 6: statements 4, 5, 33, 35, 43, 46, 53, 65
- group 7: statements 49, 57, 70
- group 8: statements 17, 18

## Grouping G10 (26 groups)

- group 1: statements 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
- group 2: statements 22, 23, 24, 25, 26, 27, 28, 29
- group 3: statements 43, 47, 48, 70, 71, 72, 73
- group 4: statements 2, 3, 4, 5
- group 5: statements 42, 50, 51, 52
- group 6: statements 57, 58, 59, 60
- group 7: statements 30, 31, 32
- group 8: statements 53, 54, 74
- group 9: statements 67, 68, 69
- group 10: statements 0, 1
- group 11: statements 34, 35
- group 12: statements 38, 39
- group 13: statements 44, 45
- group 14: statements 55, 56
- group 15: statements 62, 63
- group 16: statements 33
- group 17: statements 36
- group 18: statements 37
- group 19: statements 40
- group 20: statements 41
- group 21: statements 46
- group 22: statements 49
- group 23: statements 61
- group 24: statements 64
- group 25: statements 65
- group 26: statements 66

