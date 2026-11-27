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

South owns pits s1, s2, s3 and a store; north owns n1, n2, n3 and a store. Each pit starts with one seed; south moves first. A player empties one of their non-empty pits and sows its seeds one by one into the following positions, around the board, into their own store but skipping the opponent's store. If the last seed lands in their own store, they move again. If it lands in one of their own empty pits and the opposite pit holds seeds, they capture that seed and the opposite seeds into their store. The game ends when the player to move has no seeds in their pits; each player scores their store plus the seeds left in their pits, and more wins, equal draws.

## The statements

```
  0  role(south)
  1  role(north)
  2  side(south,s1)
  3  side(south,s2)
  4  side(south,s3)
  5  side(north,n1)
  6  side(north,n2)
  7  side(north,n3)
  8  trio(south,s1,s2,s3)
  9  trio(north,n1,n2,n3)
 10  storeof(south,sstore)
 11  storeof(north,nstore)
 12  opposite(s1,n3)
 13  opposite(s2,n2)
 14  opposite(s3,n1)
 15  opposite(n1,s3)
 16  opposite(n2,s2)
 17  opposite(n3,s1)
 18  opponent(south,north)
 19  opponent(north,south)
 20  num(0)
 21  succ(0,1)
 22  succ(1,2)
 23  succ(2,3)
 24  succ(3,4)
 25  succ(4,5)
 26  succ(5,6)
 27  atmost(N,N) :- num(N)
 28  atmost(N,N) :- succ(M,N)
 29  atmost(A,C) :- succ(A,B) & atmost(B,C)
 30  more(A,B) :- succ(B,A)
 31  more(A,C) :- succ(B,A) & more(B,C)
 32  sum(A,0,A) :- num(A)
 33  sum(A,0,A) :- succ(B,A)
 34  sum(A,B2,C2) :- sum(A,B,C) & succ(B,B2) & succ(C,C2)
 35  ring(south,s1,s2)
 36  ring(south,s2,s3)
 37  ring(south,s3,sstore)
 38  ring(south,sstore,n1)
 39  ring(south,n1,n2)
 40  ring(south,n2,n3)
 41  ring(south,n3,s1)
 42  ring(north,n1,n2)
 43  ring(north,n2,n3)
 44  ring(north,n3,nstore)
 45  ring(north,nstore,s1)
 46  ring(north,s1,s2)
 47  ring(north,s2,s3)
 48  ring(north,s3,n1)
 49  legal(P,sow(S)) :- true(control(P)) & side(P,S) & true(seeds(S,N)) & more(N,0)
 50  ahead(P,S,1,B) :- side(P,S) & ring(P,S,B)
 51  ahead(P,S,K2,C) :- ahead(P,S,K,B) & ring(P,B,C) & succ(K,K2)
 52  sowing(P,S,N) :- does(P,sow(S)) & true(seeds(S,N))
 53  gets(B) :- sowing(P,S,N) & ahead(P,S,K,B) & atmost(K,N)
 54  last(B) :- sowing(P,S,N) & ahead(P,S,N,B)
 55  sown(S,0) :- does(P,sow(S))
 56  sown(B,N2) :- true(seeds(B,N)) & gets(B) & succ(N,N2)
 57  sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)
 58  emptied(S) :- does(P,sow(S))
 59  capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)
 60  seized(B) :- capture(P,B,O,M)
 61  seized(O) :- capture(P,B,O,M)
 62  haul(P,H) :- capture(P,B,O,M) & succ(M,H)
 63  hauls(P) :- capture(P,B,O,M)
 64  next(seeds(B,N)) :- sown(B,N) & ~seized(B)
 65  next(seeds(B,0)) :- seized(B)
 66  banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)
 67  gain(P,0) :- role(P) & ~banked(P) & ~hauls(P)
 68  gain(P,1) :- banked(P) & ~hauls(P)
 69  gain(P,H) :- hauls(P) & ~banked(P) & haul(P,H)
 70  gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)
 71  next(store(P,N2)) :- true(store(P,N)) & gain(P,G) & sum(N,G,N2)
 72  again(P) :- does(P,sow(S)) & storeof(P,T) & last(T)
 73  next(control(P)) :- again(P)
 74  legal(Q,noop) :- true(control(P)) & opponent(P,Q)
 75  next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)
 76  stocked(P) :- side(P,S) & true(seeds(S,N)) & more(N,0)
 77  over :- true(control(P)) & ~stocked(P)
 78  terminal :- over
 79  total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)
 80  goal(P,100) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(T,U)
 81  goal(P,50) :- over & opponent(P,Q) & total(P,T) & total(Q,T)
 82  goal(P,0) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(U,T)
 83  init(seeds(s1,1))
 84  init(seeds(s2,1))
 85  init(seeds(s3,1))
 86  init(seeds(n1,1))
 87  init(seeds(n2,1))
 88  init(seeds(n3,1))
 89  init(store(south,0))
 90  init(store(north,0))
 91  init(control(south))
```

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91

## Grouping G2 (11 groups)

- group 1: statements 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48
- group 2: statements 21, 22, 23, 24, 25, 26, 27, 28, 29, 53, 62
- group 3: statements 0, 1, 10, 11, 63, 66, 67, 68, 69, 70
- group 4: statements 8, 9, 20, 32, 33, 34, 71, 79, 89, 90
- group 5: statements 49, 52, 58, 72, 73, 74, 75, 77, 91
- group 6: statements 18, 19, 30, 31, 78, 80, 81, 82
- group 7: statements 64, 65, 83, 84, 85, 86, 87, 88
- group 8: statements 2, 3, 4, 5, 6, 7, 76
- group 9: statements 12, 13, 14, 15, 16, 17
- group 10: statements 55, 56, 57, 59, 60, 61
- group 11: statements 50, 51, 54

## Grouping G3 (34 groups)

- group 1: statements 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48
- group 2: statements 64, 65, 83, 84, 85, 86, 87, 88
- group 3: statements 2, 3, 4, 5, 6, 7
- group 4: statements 12, 13, 14, 15, 16, 17
- group 5: statements 21, 22, 23, 24, 25, 26
- group 6: statements 67, 68, 69, 70
- group 7: statements 27, 28, 29
- group 8: statements 32, 33, 34
- group 9: statements 55, 56, 57
- group 10: statements 71, 89, 90
- group 11: statements 73, 75, 91
- group 12: statements 80, 81, 82
- group 13: statements 0, 1
- group 14: statements 8, 9
- group 15: statements 10, 11
- group 16: statements 18, 19
- group 17: statements 30, 31
- group 18: statements 49, 74
- group 19: statements 50, 51
- group 20: statements 60, 61
- group 21: statements 20
- group 22: statements 52
- group 23: statements 53
- group 24: statements 54
- group 25: statements 58
- group 26: statements 59
- group 27: statements 62
- group 28: statements 63
- group 29: statements 66
- group 30: statements 72
- group 31: statements 76
- group 32: statements 77
- group 33: statements 78
- group 34: statements 79

## Grouping G4 (55 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 18, 19, 30, 31, 49, 73, 74, 75, 76, 77, 78, 80, 81, 82, 91
- group 2: statements 2, 3, 4, 5, 6, 7, 18, 19, 30, 31, 59, 74, 75, 76, 77, 78, 80, 81, 82
- group 3: statements 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51
- group 4: statements 18, 19, 30, 31, 73, 74, 75, 76, 77, 78, 80, 81, 82, 91
- group 5: statements 18, 19, 30, 31, 74, 75, 76, 77, 78, 79, 80, 81, 82
- group 6: statements 21, 22, 23, 24, 25, 26, 62, 69, 70
- group 7: statements 21, 22, 23, 24, 25, 26, 28, 29
- group 8: statements 21, 22, 23, 24, 25, 26, 30, 31
- group 9: statements 21, 22, 23, 24, 25, 26, 33, 34
- group 10: statements 64, 65, 83, 84, 85, 86, 87, 88
- group 11: statements 2, 3, 4, 5, 6, 7, 50
- group 12: statements 2, 3, 4, 5, 6, 7, 76
- group 13: statements 12, 13, 14, 15, 16, 17, 59
- group 14: statements 21, 22, 23, 24, 25, 26, 51
- group 15: statements 21, 22, 23, 24, 25, 26, 56
- group 16: statements 21, 22, 23, 24, 25, 26, 62
- group 17: statements 12, 13, 14, 15, 16, 17
- group 18: statements 49, 52, 58, 66, 72
- group 19: statements 63, 67, 68, 69, 70
- group 20: statements 66, 67, 68, 69, 70
- group 21: statements 67, 68, 69, 70, 71
- group 22: statements 10, 11, 66, 72
- group 23: statements 27, 28, 29, 53
- group 24: statements 32, 33, 34, 71
- group 25: statements 32, 33, 34, 79
- group 26: statements 55, 56, 57, 59
- group 27: statements 55, 56, 57, 64
- group 28: statements 60, 61, 64, 65
- group 29: statements 71, 79, 89, 90
- group 30: statements 0, 1, 67
- group 31: statements 8, 9, 79
- group 32: statements 27, 28, 29
- group 33: statements 32, 33, 34
- group 34: statements 50, 51, 53
- group 35: statements 50, 51, 54
- group 36: statements 52, 53, 66
- group 37: statements 52, 54, 72
- group 38: statements 53, 56, 57
- group 39: statements 55, 56, 57
- group 40: statements 59, 60, 61
- group 41: statements 72, 73, 75
- group 42: statements 0, 1
- group 43: statements 8, 9
- group 44: statements 10, 11
- group 45: statements 20, 27
- group 46: statements 20, 32
- group 47: statements 49, 55
- group 48: statements 49, 59
- group 49: statements 49, 79
- group 50: statements 54, 59
- group 51: statements 57, 58
- group 52: statements 59, 62
- group 53: statements 59, 63
- group 54: statements 59, 79
- group 55: statements 60, 61

## Grouping G5 (12 groups)

- group 1: statements 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51
- group 2: statements 8, 9, 20, 32, 33, 34, 59, 71, 75, 79, 89, 90
- group 3: statements 55, 57, 59, 60, 61, 64, 65, 83, 84, 85, 86, 87, 88
- group 4: statements 18, 19, 30, 31, 49, 59, 74, 75, 76, 77, 78, 79, 80, 81, 82
- group 5: statements 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 33, 34, 55, 56, 57, 59, 62, 70
- group 6: statements 0, 1, 59, 62, 63, 66, 67, 68, 69, 70
- group 7: statements 2, 3, 4, 5, 6, 7, 49, 59, 75, 76
- group 8: statements 12, 13, 14, 15, 16, 17, 59
- group 9: statements 20, 27, 28, 29, 52, 53, 55, 56, 57, 58, 59, 66
- group 10: statements 49, 52, 55, 58, 59, 66, 72, 73, 74, 75, 77, 78, 91
- group 11: statements 50, 51, 52, 53, 54, 59, 72
- group 12: statements 10, 11, 66, 72

## Grouping G6 (5 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 49, 55, 57, 58, 59, 60, 61, 64, 65, 76
- group 2: statements 20, 27, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54
- group 3: statements 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 33, 34, 56, 62, 70
- group 4: statements 8, 9, 18, 19, 32, 74, 75, 77, 78, 79, 80, 81, 82
- group 5: statements 0, 1, 10, 11, 63, 66, 67, 68, 69, 71, 72, 73
- ungrouped: statements 83, 84, 85, 86, 87, 88, 89, 90, 91

## Grouping G7 (12 groups)

- group 1: statements 4, 15, 20, 21, 25, 31, 46, 66, 67, 73, 83, 85, 86, 87, 89, 91
- group 2: statements 5, 12, 13, 14, 23, 39, 41, 53, 59, 64, 69, 84
- group 3: statements 13, 30, 33, 38, 51, 55, 58, 61, 62, 63, 65, 79, 82
- group 4: statements 0, 2, 12, 13, 17, 27, 32, 36, 37, 43, 45, 56, 64, 74, 78
- group 5: statements 2, 10, 13, 14, 24, 28, 30, 47, 52, 54, 56, 57, 71, 75, 76, 79, 81, 84
- group 6: statements 7, 8, 9, 13, 40, 42, 60, 70, 71, 75
- group 7: statements 0, 11, 12, 13, 19, 26, 29, 44, 77, 78
- group 8: statements 1, 6, 13, 22, 34, 50, 80
- group 9: statements 3, 10, 13, 16, 23, 28, 30, 35, 57, 70, 79, 90
- group 10: statements 0, 3, 12, 13, 17, 18, 32, 35, 36, 49, 68, 70, 79
- group 11: statements 3, 13, 16, 18, 67, 85, 88
- group 12: statements 18, 48, 70, 72

## Grouping G8 (92 groups)

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
- group 92: statements 91

