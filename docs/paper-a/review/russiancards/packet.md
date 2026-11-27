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

Seven cards, 0 to 6. Nature deals three to Alice, three to Bob and one to Cath; each sees only their own. Then two public announcements, which must be true: Alice announces the sum of her cards modulo 7, or her whole hand, or nothing; then Bob announces which card Cath holds, if he knows it, or nothing. Alice and Bob win if afterwards both know the whole deal and Cath does not learn who holds any card she does not hold; otherwise Cath wins.

## The statements

```
  0  role(alice)
  1  role(bob)
  2  role(cath)
  3  role(random)
  4  init(round(0))
  5  player(alice)
  6  player(bob)
  7  player(cath)
  8  card(0)
  9  card(1)
 10  card(2)
 11  card(3)
 12  card(4)
 13  card(5)
 14  card(6)
 15  lt(0,1)
 16  lt(0,2)
 17  lt(0,3)
 18  lt(0,4)
 19  lt(0,5)
 20  lt(0,6)
 21  lt(1,2)
 22  lt(1,3)
 23  lt(1,4)
 24  lt(1,5)
 25  lt(1,6)
 26  lt(2,3)
 27  lt(2,4)
 28  lt(2,5)
 29  lt(2,6)
 30  lt(3,4)
 31  lt(3,5)
 32  lt(3,6)
 33  lt(4,5)
 34  lt(4,6)
 35  lt(5,6)
 36  addmod(0,0,0)
 37  addmod(0,1,1)
 38  addmod(0,2,2)
 39  addmod(0,3,3)
 40  addmod(0,4,4)
 41  addmod(0,5,5)
 42  addmod(0,6,6)
 43  addmod(1,0,1)
 44  addmod(1,1,2)
 45  addmod(1,2,3)
 46  addmod(1,3,4)
 47  addmod(1,4,5)
 48  addmod(1,5,6)
 49  addmod(1,6,0)
 50  addmod(2,0,2)
 51  addmod(2,1,3)
 52  addmod(2,2,4)
 53  addmod(2,3,5)
 54  addmod(2,4,6)
 55  addmod(2,5,0)
 56  addmod(2,6,1)
 57  addmod(3,0,3)
 58  addmod(3,1,4)
 59  addmod(3,2,5)
 60  addmod(3,3,6)
 61  addmod(3,4,0)
 62  addmod(3,5,1)
 63  addmod(3,6,2)
 64  addmod(4,0,4)
 65  addmod(4,1,5)
 66  addmod(4,2,6)
 67  addmod(4,3,0)
 68  addmod(4,4,1)
 69  addmod(4,5,2)
 70  addmod(4,6,3)
 71  addmod(5,0,5)
 72  addmod(5,1,6)
 73  addmod(5,2,0)
 74  addmod(5,3,1)
 75  addmod(5,4,2)
 76  addmod(5,5,3)
 77  addmod(5,6,4)
 78  addmod(6,0,6)
 79  addmod(6,1,0)
 80  addmod(6,2,1)
 81  addmod(6,3,2)
 82  addmod(6,4,3)
 83  addmod(6,5,4)
 84  addmod(6,6,5)
 85  legal(random,deal(A1,A2,A3,B1,B2,B3,C)) :- true(round(0)) & lt(A1,A2) & lt(A2,A3) & lt(B1,B2) & lt(B2,B3) & distinct(B1,A1) & distinct(B1,A2) & distinct(B1,A3) & distinct(B2,A1) & distinct(B2,A2) & distinct(B2,A3) & distinct(B3,A1) & distinct(B3,A2) & distinct(B3,A3) & card(C) & distinct(C,A1) & distinct(C,A2) & distinct(C,A3) & distinct(C,B1) & distinct(C,B2) & distinct(C,B3)
 86  legal(random,noop) :- ~true(round(0))
 87  legal(P,noop) :- player(P) & true(round(0))
 88  next(hand(A1,A2,A3)) :- does(random,deal(A1,A2,A3,B1,B2,B3,C))
 89  next(hand(A1,A2,A3)) :- true(hand(A1,A2,A3))
 90  next(holds(alice,X)) :- does(random,deal(X,A2,A3,B1,B2,B3,C))
 91  next(holds(alice,X)) :- does(random,deal(A1,X,A3,B1,B2,B3,C))
 92  next(holds(alice,X)) :- does(random,deal(A1,A2,X,B1,B2,B3,C))
 93  next(holds(bob,X)) :- does(random,deal(A1,A2,A3,X,B2,B3,C))
 94  next(holds(bob,X)) :- does(random,deal(A1,A2,A3,B1,X,B3,C))
 95  next(holds(bob,X)) :- does(random,deal(A1,A2,A3,B1,B2,X,C))
 96  next(holds(cath,X)) :- does(random,deal(A1,A2,A3,B1,B2,B3,X))
 97  next(holds(P,X)) :- true(holds(P,X))
 98  sees(alice,mine(X)) :- does(random,deal(X,A2,A3,B1,B2,B3,C))
 99  sees(alice,mine(X)) :- does(random,deal(A1,X,A3,B1,B2,B3,C))
100  sees(alice,mine(X)) :- does(random,deal(A1,A2,X,B1,B2,B3,C))
101  sees(bob,mine(X)) :- does(random,deal(A1,A2,A3,X,B2,B3,C))
102  sees(bob,mine(X)) :- does(random,deal(A1,A2,A3,B1,X,B3,C))
103  sees(bob,mine(X)) :- does(random,deal(A1,A2,A3,B1,B2,X,C))
104  sees(cath,mine(X)) :- does(random,deal(A1,A2,A3,B1,B2,B3,X))
105  owns(P,X) :- true(holds(P,X))
106  aliceSum(S) :- true(hand(A1,A2,A3)) & addmod(A1,A2,T) & addmod(T,A3,S)
107  legal(alice,announce(sum(S))) :- true(round(1)) & aliceSum(S)
108  legal(alice,announce(hand(A1,A2,A3))) :- true(round(1)) & true(hand(A1,A2,A3))
109  legal(alice,announce(pass)) :- true(round(1))
110  legal(bob,noop) :- true(round(1))
111  legal(cath,noop) :- true(round(1))
112  legal(bob,announce(cath(C))) :- true(round(2)) & knows(bob,owns(cath,C))
113  legal(bob,announce(pass)) :- true(round(2))
114  legal(alice,noop) :- true(round(2))
115  legal(cath,noop) :- true(round(2))
116  sees(P,said(S,M)) :- player(P) & does(S,announce(M))
117  next(round(1)) :- true(round(0))
118  next(round(2)) :- true(round(1))
119  next(round(3)) :- true(round(2))
120  terminal :- true(round(3))
121  knowsOwner(R,X) :- player(R) & card(X) & knows(R,owns(P,X))
122  missesSome(R) :- player(R) & card(X) & ~knowsOwner(R,X)
123  knowsDeal(R) :- player(R) & ~missesSome(R)
124  cathLearns :- card(X) & ~true(holds(cath,X)) & knowsOwner(cath,X)
125  safe :- knowsDeal(alice) & knowsDeal(bob) & ~cathLearns
126  goal(alice,100) :- safe
127  goal(alice,0) :- ~safe
128  goal(bob,100) :- safe
129  goal(bob,0) :- ~safe
130  goal(cath,100) :- ~safe
131  goal(cath,0) :- safe
132  goal(random,0)
```

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132

## Grouping G2 (18 groups)

- group 1: statements 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84
- group 2: statements 85, 86, 87, 107, 108, 109, 110, 111, 112, 113, 114, 115
- group 3: statements 90, 91, 92, 93, 94, 95, 96, 97
- group 4: statements 98, 99, 100, 101, 102, 103, 104, 116
- group 5: statements 8, 9, 10, 11, 12, 13, 14
- group 6: statements 126, 127, 128, 129, 130, 131, 132
- group 7: statements 0, 1, 2, 3
- group 8: statements 4, 117, 118, 119
- group 9: statements 5, 6, 7
- group 10: statements 88, 89
- group 11: statements 105
- group 12: statements 106
- group 13: statements 120
- group 14: statements 121
- group 15: statements 122
- group 16: statements 123
- group 17: statements 124
- group 18: statements 125
- ungrouped: statements 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35

## Grouping G3 (6 groups)

- group 1: statements 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84
- group 2: statements 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 90, 91, 92, 93, 94, 95, 96, 97, 105, 121, 122, 123, 124
- group 3: statements 85, 86, 87, 88, 89, 98, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116
- group 4: statements 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35
- group 5: statements 4, 117, 118, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132
- group 6: statements 0, 1, 2, 3

## Grouping G4 (5 groups)

- group 1: statements 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 106, 107
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 85
- group 3: statements 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 87, 116, 121, 122, 123, 124
- group 4: statements 125, 126, 127, 128, 129, 130, 131
- group 5: statements 105, 112
- ungrouped: statements 0, 1, 2, 3, 4, 86, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 108, 109, 110, 111, 113, 114, 115, 117, 118, 119, 120, 132

## Grouping G5 (2 groups)

- group 1: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132
- group 2: statements 0, 1, 2, 3

## Grouping G6 (12 groups)

- group 1: statements 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 106
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 85
- group 3: statements 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 85, 105, 121, 122, 123, 124
- group 4: statements 85, 86, 87, 88, 89, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116
- group 5: statements 4, 117, 118, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132
- group 6: statements 85, 90, 91, 92, 93, 94, 95, 96, 97, 105, 124
- group 7: statements 85, 98, 99, 100, 101, 102, 103, 104, 116
- group 8: statements 5, 6, 7, 87, 116
- group 9: statements 0, 1, 2, 3
- group 10: statements 105, 112
- group 11: statements 123, 125
- group 12: statements 124, 125

## Grouping G7 (6 groups)

- group 1: statements 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 106
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 85
- group 3: statements 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 90, 91, 92, 93, 94, 95, 96, 97, 105, 116, 121, 122, 123, 124
- group 4: statements 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116
- group 5: statements 4, 117, 118, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132
- group 6: statements 0, 1, 2, 3

## Grouping G8 (6 groups)

- group 1: statements 0, 1, 5, 6, 7, 8, 11, 13, 15, 19, 20, 21, 24, 28, 30, 31, 33, 34, 35, 37, 41, 44, 47, 50, 51, 52, 57, 59, 62, 63, 82, 84, 85, 89, 90, 91, 94, 95, 97, 105, 110, 112, 119, 123, 125, 128, 129, 130, 131, 132
- group 2: statements 2, 4, 16, 22, 43, 46, 48, 49, 53, 54, 56, 58, 67, 69, 72, 75, 76, 80, 83, 92, 108, 113
- group 3: statements 14, 23, 29, 38, 40, 42, 45, 55, 60, 61, 64, 65, 71, 78, 88, 99, 101, 104, 106, 118, 120, 121, 126, 127
- group 4: statements 9, 12, 17, 18, 26, 32, 36, 39, 40, 55, 56, 60, 64, 68, 70, 71, 77, 78, 79, 81, 87, 90, 93, 96, 101, 102, 111, 115, 121, 122
- group 5: statements 3, 10, 27, 66, 74, 98, 100, 103, 107, 114, 116, 117, 124
- group 6: statements 25, 73, 86, 109

## Grouping G9 (133 groups)

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
- group 93: statements 92
- group 94: statements 93
- group 95: statements 94
- group 96: statements 95
- group 97: statements 96
- group 98: statements 97
- group 99: statements 98
- group 100: statements 99
- group 101: statements 100
- group 102: statements 101
- group 103: statements 102
- group 104: statements 103
- group 105: statements 104
- group 106: statements 105
- group 107: statements 106
- group 108: statements 107
- group 109: statements 108
- group 110: statements 109
- group 111: statements 110
- group 112: statements 111
- group 113: statements 112
- group 114: statements 113
- group 115: statements 114
- group 116: statements 115
- group 117: statements 116
- group 118: statements 117
- group 119: statements 118
- group 120: statements 119
- group 121: statements 120
- group 122: statements 121
- group 123: statements 122
- group 124: statements 123
- group 125: statements 124
- group 126: statements 125
- group 127: statements 126
- group 128: statements 127
- group 129: statements 128
- group 130: statements 129
- group 131: statements 130
- group 132: statements 131
- group 133: statements 132

