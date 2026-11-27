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

Two tokens on a corridor of squares 0 to 7: white starts on 0, black on 2; white moves first. On a turn a player steps their token one or two squares forward, or holds. A token may not land on the other token, may not leave the corridor, and may not make a two-square step straight after its own two-square step. Reaching square 7 wins.

## The statements

```
  0  role(white)
  1  role(black)
  2  succ(0,1)
  3  succ(1,2)
  4  succ(2,3)
  5  succ(3,4)
  6  succ(4,5)
  7  succ(5,6)
  8  succ(6,7)
  9  plus2(A,C) :- succ(A,B) & succ(B,C)
 10  legal(P,step(1)) :- true(control(P)) & true(at(P,A)) & succ(A,B) & inside(B) & clear(P,B)
 11  legal(P,step(2)) :- true(control(P)) & true(at(P,A)) & plus2(A,C) & inside(C) & clear(P,C) & true(fresh(P))
 12  legal(P,hold) :- true(control(P))
 13  legal(white,wait) :- true(control(black))
 14  legal(black,wait) :- true(control(white))
 15  inside(0)
 16  inside(1)
 17  inside(2)
 18  inside(3)
 19  inside(4)
 20  inside(5)
 21  inside(6)
 22  inside(7)
 23  clear(P,S) :- true(at(Q,T)) & distinct(P,Q) & distinct(S,T)
 24  next(stale(P)) :- does(P,step(2))
 25  next(stale(P)) :- does(P,wait) & true(stale(P))
 26  next(fresh(P)) :- does(P,step(1))
 27  next(fresh(P)) :- does(P,hold)
 28  next(fresh(P)) :- does(P,wait) & true(fresh(P))
 29  next(at(P,B)) :- does(P,step(1)) & true(at(P,A)) & succ(A,B)
 30  next(at(P,C)) :- does(P,step(2)) & true(at(P,A)) & plus2(A,C)
 31  next(at(P,A)) :- does(P,hold) & true(at(P,A))
 32  next(at(P,A)) :- does(P,wait) & true(at(P,A))
 33  next(control(white)) :- true(control(black))
 34  next(control(black)) :- true(control(white))
 35  home(P) :- true(at(P,7))
 36  terminal :- home(white)
 37  terminal :- home(black)
 38  goal(P,100) :- home(P)
 39  init(at(white,0))
 40  init(at(black,2))
 41  init(fresh(white))
 42  init(fresh(black))
 43  init(control(white))
```

## Grouping G1 (44 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43

## Grouping G3 (10 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 3: statements 29, 30, 31, 32, 39, 40
- group 4: statements 26, 27, 28, 41, 42
- group 5: statements 12, 13, 14, 25
- group 6: statements 35, 36, 37, 38
- group 7: statements 33, 34, 43
- group 8: statements 0, 1
- group 9: statements 10, 24
- group 10: statements 11, 23

## Grouping G4 (9 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 29
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 3: statements 10, 12, 13, 14, 24, 25, 28, 32
- group 4: statements 11, 26, 27, 28, 41, 42
- group 5: statements 29, 30, 31, 32, 39, 40
- group 6: statements 35, 36, 37, 38
- group 7: statements 33, 34, 43
- group 8: statements 0, 1
- group 9: statements 11, 23, 24, 26

## Grouping G5 (3 groups)

- group 1: statements 10, 11, 15, 16, 17, 18, 19, 20, 21, 22, 23
- group 2: statements 2, 3, 4, 5, 6, 7, 8, 9, 29, 30
- group 3: statements 35, 36, 37, 38
- ungrouped: statements 0, 1, 12, 13, 14, 24, 25, 26, 27, 28, 31, 32, 33, 34, 39, 40, 41, 42, 43

## Grouping G6 (9 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 3: statements 12, 13, 14, 24, 25
- group 4: statements 26, 27, 28, 41, 42
- group 5: statements 30, 31, 32, 39, 40
- group 6: statements 35, 36, 37, 38
- group 7: statements 33, 34, 43
- group 8: statements 0, 1
- group 9: statements 11, 23
- ungrouped: statements 10, 29

## Grouping G7 (12 groups)

- group 1: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 2: statements 2, 3, 4, 5, 6, 7, 8
- group 3: statements 10, 11, 12, 13, 14
- group 4: statements 26, 27, 28, 41, 42
- group 5: statements 33, 34, 43
- group 6: statements 0, 1
- group 7: statements 24, 25
- group 8: statements 36, 37
- group 9: statements 9
- group 10: statements 23
- group 11: statements 35
- group 12: statements 38
- ungrouped: statements 29, 30, 31, 32, 39, 40

## Grouping G8 (20 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 10, 11, 29, 30
- group 2: statements 10, 11, 15, 16, 17, 18, 19, 20, 21, 22
- group 3: statements 2, 3, 4, 5, 6, 7, 8, 9, 29
- group 4: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 5: statements 10, 11, 26, 27, 28, 41, 42
- group 6: statements 29, 30, 31, 32, 39, 40
- group 7: statements 10, 11, 13, 14, 28
- group 8: statements 10, 11, 12, 27
- group 9: statements 35, 36, 37, 38
- group 10: statements 10, 11, 23
- group 11: statements 10, 11, 24
- group 12: statements 12, 13, 14
- group 13: statements 13, 14, 25
- group 14: statements 13, 14, 32
- group 15: statements 33, 34, 43
- group 16: statements 0, 1
- group 17: statements 9, 11
- group 18: statements 9, 30
- group 19: statements 12, 31
- group 20: statements 24, 25

## Grouping G9 (10 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 29
- group 2: statements 15, 16, 17, 18, 19, 20, 21, 22
- group 3: statements 29, 30, 31, 32, 39, 40
- group 4: statements 11, 26, 27, 28, 41, 42
- group 5: statements 12, 13, 14, 24, 25, 28, 32
- group 6: statements 35, 36, 37, 38
- group 7: statements 33, 34, 43
- group 8: statements 0, 1
- group 9: statements 10, 23, 24, 25
- group 10: statements 11, 23, 24, 26

## Grouping G10 (10 groups)

- group 1: statements 0, 4, 7, 14, 18, 20, 21, 23, 40
- group 2: statements 10, 15, 27, 29, 34, 35, 41, 42
- group 3: statements 4, 8, 9, 16, 32, 39
- group 4: statements 2, 3, 6, 26, 36, 43
- group 5: statements 1, 5, 28, 37, 38, 39, 43
- group 6: statements 19, 25, 30, 31
- group 7: statements 13, 22, 24
- group 8: statements 11, 33
- group 9: statements 12, 17, 37, 38
- group 10: statements 6, 17, 36, 38

## Grouping G11 (4 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 39, 40, 41, 42
- group 2: statements 35, 36, 37, 38
- group 3: statements 33, 34, 43
- group 4: statements 0, 1

