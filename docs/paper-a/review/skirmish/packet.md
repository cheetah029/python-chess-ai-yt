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

A 4x4 board. Each side has a guard and a lancer: white's on (1,1) and (2,1), black's on (4,4) and (3,4); white moves first. A guard steps one square in any direction. A lancer slides any distance along a row or a column through empty squares. A piece may move onto an empty square, or onto an enemy piece, which is captured. Taking the enemy guard wins; after eight turns the game ends with no winner.

## The statements

```
  0  role(white)
  1  role(black)
  2  coord(1)
  3  coord(2)
  4  coord(3)
  5  coord(4)
  6  succ(1,2)
  7  succ(2,3)
  8  succ(3,4)
  9  occupied(X,Y) :- true(at(P,T,X,Y))
 10  empty(X,Y) :- coord(X) & coord(Y) & ~occupied(X,Y)
 11  enemy_at(P,X,Y) :- true(at(Q,T,X,Y)) & distinct(P,Q)
 12  struck(U,V) :- does(P,move(T,X,Y,U,V))
 13  close(A,B) :- succ(A,B)
 14  close(A,B) :- succ(B,A)
 15  kingstep(X,Y,U,V) :- close(X,U) & close(Y,V)
 16  kingstep(X,Y,U,Y) :- close(X,U) & coord(Y)
 17  kingstep(X,Y,X,V) :- coord(X) & close(Y,V)
 18  legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)
 19  legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & enemy_at(P,U,V)
 20  north(X,Y,X,V) :- coord(X) & succ(Y,V)
 21  north(X,Y,X,V) :- succ(Y,W) & empty(X,W) & north(X,W,X,V)
 22  south(X,Y,X,V) :- coord(X) & succ(V,Y)
 23  south(X,Y,X,V) :- succ(W,Y) & empty(X,W) & south(X,W,X,V)
 24  east(X,Y,U,Y) :- coord(Y) & succ(X,U)
 25  east(X,Y,U,Y) :- succ(X,W) & empty(W,Y) & east(W,Y,U,Y)
 26  west(X,Y,U,Y) :- coord(Y) & succ(U,X)
 27  west(X,Y,U,Y) :- succ(W,X) & empty(W,Y) & west(W,Y,U,Y)
 28  slide(X,Y,U,V) :- north(X,Y,U,V)
 29  slide(X,Y,U,V) :- south(X,Y,U,V)
 30  slide(X,Y,U,V) :- east(X,Y,U,V)
 31  slide(X,Y,U,V) :- west(X,Y,U,V)
 32  legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & empty(U,V)
 33  legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & enemy_at(P,U,V)
 34  vacated(X,Y) :- does(P,move(T,X,Y,U,V))
 35  next(at(P,T,U,V)) :- does(P,move(T,X,Y,U,V))
 36  next(at(Q,S,A,B)) :- true(at(Q,S,A,B)) & ~vacated(A,B) & ~struck(A,B)
 37  legal(white,noop) :- true(control(black))
 38  legal(black,noop) :- true(control(white))
 39  next(control(white)) :- true(control(black))
 40  next(control(black)) :- true(control(white))
 41  opponent(white,black)
 42  opponent(black,white)
 43  hasguard(P) :- true(at(P,guard,X,Y))
 44  guardless(P) :- role(P) & ~hasguard(P)
 45  tsucc(0,1)
 46  tsucc(1,2)
 47  tsucc(2,3)
 48  tsucc(3,4)
 49  tsucc(4,5)
 50  tsucc(5,6)
 51  tsucc(6,7)
 52  tsucc(7,8)
 53  next(tick(N)) :- true(tick(M)) & tsucc(M,N)
 54  terminal :- guardless(P)
 55  terminal :- true(tick(8))
 56  goal(P,100) :- opponent(P,Q) & guardless(Q)
 57  init(at(white,guard,1,1))
 58  init(at(white,lancer,2,1))
 59  init(at(black,guard,4,4))
 60  init(at(black,lancer,3,4))
 61  init(control(white))
 62  init(tick(0))
```

## Grouping G1 (63 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62

## Grouping G3 (18 groups)

- group 1: statements 45, 46, 47, 48, 49, 50, 51, 52
- group 2: statements 0, 1, 41, 42, 43, 44, 56
- group 3: statements 35, 36, 57, 58, 59, 60
- group 4: statements 13, 14, 15, 16, 17
- group 5: statements 2, 3, 4, 5
- group 6: statements 28, 29, 30, 31
- group 7: statements 53, 54, 55, 62
- group 8: statements 6, 7, 8
- group 9: statements 19, 37, 38
- group 10: statements 39, 40, 61
- group 11: statements 9, 10
- group 12: statements 11, 33
- group 13: statements 12, 18
- group 14: statements 20, 21
- group 15: statements 22, 23
- group 16: statements 24, 25
- group 17: statements 26, 27
- group 18: statements 32, 34

## Grouping G4 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 57, 58, 59, 60
- group 2: statements 0, 1, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 62
- group 3: statements 39, 40, 61

## Grouping G5 (18 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27
- group 2: statements 12, 18, 19, 32, 33, 34, 35, 37, 38
- group 3: statements 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 4: statements 12, 34, 35, 36, 57, 58, 59, 60
- group 5: statements 41, 42, 44, 53, 54, 55, 56, 62
- group 6: statements 28, 29, 30, 31, 32, 33
- group 7: statements 15, 16, 17, 18, 19
- group 8: statements 28, 29, 30, 31
- group 9: statements 0, 1, 44
- group 10: statements 10, 18, 32
- group 11: statements 11, 19, 33
- group 12: statements 20, 21, 28
- group 13: statements 22, 23, 29
- group 14: statements 24, 25, 30
- group 15: statements 26, 27, 31
- group 16: statements 39, 40, 61
- group 17: statements 9, 10
- group 18: statements 43, 44

## Grouping G6 (6 groups)

- group 1: statements 2, 3, 4, 5, 9, 10, 13, 14, 15, 16, 17, 18, 19
- group 2: statements 6, 7, 8, 20, 21, 22, 23, 24, 25, 29, 30
- group 3: statements 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 4: statements 0, 1, 41, 42, 43, 44, 54, 56
- group 5: statements 11, 26, 27, 28, 31, 32, 33
- group 6: statements 12, 34, 36
- ungrouped: statements 35, 37, 38, 39, 40, 55, 57, 58, 59, 60, 61, 62

## Grouping G7 (18 groups)

- group 1: statements 45, 46, 47, 48, 49, 50, 51, 52
- group 2: statements 0, 1, 41, 42, 43, 44, 56
- group 3: statements 35, 36, 57, 58, 59, 60
- group 4: statements 13, 14, 15, 16, 17
- group 5: statements 2, 3, 4, 5
- group 6: statements 28, 29, 30, 31
- group 7: statements 53, 54, 55, 62
- group 8: statements 6, 7, 8
- group 9: statements 33, 37, 38
- group 10: statements 39, 40, 61
- group 11: statements 9, 10
- group 12: statements 11, 19
- group 13: statements 12, 18
- group 14: statements 20, 21
- group 15: statements 22, 23
- group 16: statements 24, 25
- group 17: statements 26, 27
- group 18: statements 32, 34

## Grouping G8 (16 groups)

- group 1: statements 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 2: statements 11, 12, 15, 18, 19, 32, 33, 34, 35, 37, 38
- group 3: statements 13, 14, 15, 16, 17, 18, 19
- group 4: statements 12, 34, 35, 36, 57, 58, 59, 60
- group 5: statements 0, 1, 43, 44
- group 6: statements 2, 3, 4, 5, 10, 16, 17, 20, 22, 24, 26
- group 7: statements 28, 29, 30, 31, 32, 33
- group 8: statements 41, 42, 44, 53, 54, 55, 56, 62
- group 9: statements 6, 7, 8, 13, 14, 20, 21, 22, 23, 24, 25, 26, 27
- group 10: statements 39, 40, 61
- group 11: statements 41, 42, 44, 56
- group 12: statements 9, 10
- group 13: statements 20, 21
- group 14: statements 22, 23
- group 15: statements 24, 25
- group 16: statements 26, 27

## Grouping G9 (16 groups)

- group 1: statements 8, 13, 19, 22, 25, 30, 37, 50, 55
- group 2: statements 1, 4, 9, 12, 21, 23, 28, 38, 42, 52, 61
- group 3: statements 0, 1, 12, 29, 46, 57, 61
- group 4: statements 2, 4, 23, 26, 42, 48, 51, 56
- group 5: statements 18, 41, 45, 53
- group 6: statements 0, 3, 14, 17, 20, 33, 43, 49, 57, 58, 60
- group 7: statements 10, 11, 21, 35, 47, 52
- group 8: statements 6, 16, 18, 25, 31, 32, 39, 54
- group 9: statements 5, 7, 14, 15, 17, 20, 27, 29, 36, 40, 43, 46, 62
- group 10: statements 24, 34, 59
- group 11: statements 6, 16, 18, 39
- group 12: statements 44, 49
- group 13: statements 40, 43
- group 14: statements 14, 15
- group 15: statements 17, 62
- group 16: statements 20, 36

## Grouping G10 (24 groups)

- group 1: statements 45, 46, 47, 48, 49, 50, 51, 52
- group 2: statements 18, 19, 32, 33, 37, 38
- group 3: statements 2, 3, 4, 5
- group 4: statements 28, 29, 30, 31
- group 5: statements 6, 7, 8
- group 6: statements 15, 16, 17
- group 7: statements 39, 40, 61
- group 8: statements 0, 1
- group 9: statements 13, 14
- group 10: statements 20, 21
- group 11: statements 22, 23
- group 12: statements 24, 25
- group 13: statements 26, 27
- group 14: statements 41, 42
- group 15: statements 53, 62
- group 16: statements 54, 55
- group 17: statements 9
- group 18: statements 10
- group 19: statements 11
- group 20: statements 12
- group 21: statements 34
- group 22: statements 43
- group 23: statements 44
- group 24: statements 56
- ungrouped: statements 35, 36, 57, 58, 59, 60

