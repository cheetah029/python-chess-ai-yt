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

Nature picks Cheryl's birthday from ten given dates. Albert is told the month and Bernard the day. Then, in turn and in public, each says yes or no to a statement, and must say yes exactly when it is true: Albert, "I do not know the date, and I know Bernard does not know it"; Bernard, "now I know the date"; Albert, "now I know it too". A listener wins if at the end they know the date.

## The statements

```
  0  role(albert)
  1  role(bernard)
  2  role(random)
  3  init(round(0))
  4  date(may,15)
  5  date(may,16)
  6  date(may,19)
  7  date(june,17)
  8  date(june,18)
  9  date(july,14)
 10  date(july,16)
 11  date(august,14)
 12  date(august,15)
 13  date(august,17)
 14  listener(albert)
 15  listener(bernard)
 16  legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)
 17  legal(random,noop) :- ~true(round(0))
 18  next(birthday(M,D)) :- does(random,birthday(M,D))
 19  next(birthday(M,D)) :- true(birthday(M,D))
 20  sees(albert,month(M)) :- does(random,birthday(M,D))
 21  sees(bernard,day(D)) :- does(random,birthday(M,D))
 22  isDate(M,D) :- true(birthday(M,D))
 23  knowsDate(R) :- listener(R) & knows(R,isDate(M,D))
 24  bernardIgnorant :- ~knowsDate(bernard)
 25  firstClaim :- ~knowsDate(albert) & knows(albert,bernardIgnorant)
 26  legal(albert,noop) :- true(round(0))
 27  legal(bernard,noop) :- true(round(0))
 28  legal(albert,say(yes)) :- true(round(1)) & firstClaim
 29  legal(albert,say(no)) :- true(round(1)) & ~firstClaim
 30  legal(bernard,noop) :- true(round(1))
 31  legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)
 32  legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)
 33  legal(albert,noop) :- true(round(2))
 34  legal(albert,say(yes)) :- true(round(3)) & knowsDate(albert)
 35  legal(albert,say(no)) :- true(round(3)) & ~knowsDate(albert)
 36  legal(bernard,noop) :- true(round(3))
 37  sees(L,said(S,X)) :- listener(L) & does(S,say(X))
 38  next(round(1)) :- true(round(0))
 39  next(round(2)) :- true(round(1))
 40  next(round(3)) :- true(round(2))
 41  next(round(4)) :- true(round(3))
 42  terminal :- true(round(4))
 43  goal(R,100) :- listener(R) & knowsDate(R)
 44  goal(R,0) :- listener(R) & ~knowsDate(R)
 45  goal(random,0)
```

## Grouping G1 (46 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45

## Grouping G3 (7 groups)

- group 1: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
- group 2: statements 14, 15, 23, 24, 25, 42, 43, 44, 45
- group 3: statements 17, 26, 27, 28, 29, 30, 33, 36
- group 4: statements 3, 38, 39, 40, 41
- group 5: statements 16, 18, 19, 22
- group 6: statements 0, 1, 2
- group 7: statements 20, 21, 37
- ungrouped: statements 31, 32, 34, 35

## Grouping G4 (2 groups)

- group 1: statements 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45
- group 2: statements 0, 1, 2

## Grouping G5 (7 groups)

- group 1: statements 3, 14, 15, 16, 17, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45
- group 2: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16
- group 3: statements 16, 18, 20, 21, 37
- group 4: statements 0, 1, 2
- group 5: statements 18, 19, 22
- group 6: statements 20, 21
- group 7: statements 22, 23

## Grouping G6 (4 groups)

- group 1: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16
- group 2: statements 22, 23, 31, 32, 34, 35
- group 3: statements 14, 15, 37, 43, 44
- group 4: statements 24, 25, 28, 29
- ungrouped: statements 0, 1, 2, 3, 17, 18, 19, 20, 21, 26, 27, 30, 33, 36, 38, 39, 40, 41, 42, 45

## Grouping G7 (8 groups)

- group 1: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
- group 2: statements 14, 15, 23, 24, 25, 42, 43, 44, 45
- group 3: statements 17, 26, 27, 28, 29, 30, 33, 36
- group 4: statements 3, 38, 39, 40, 41
- group 5: statements 0, 1, 2
- group 6: statements 16, 20, 21
- group 7: statements 18, 19, 22
- group 8: statements 31, 34, 37
- ungrouped: statements 32, 35

## Grouping G8 (8 groups)

- group 1: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16
- group 2: statements 3, 14, 15, 23, 24, 25, 37, 38, 39, 40, 41, 42, 43, 44, 45
- group 3: statements 16, 17, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37
- group 4: statements 3, 37, 38, 39, 40, 41, 42
- group 5: statements 0, 1, 2
- group 6: statements 18, 19, 22
- group 7: statements 31, 34, 37
- group 8: statements 32, 35, 37
- ungrouped: statements 20, 21

## Grouping G9 (8 groups)

- group 1: statements 5, 7, 12, 14, 20, 21, 23, 34, 37, 42, 44
- group 2: statements 0, 2, 6, 11, 16, 17, 19, 24, 25, 26, 28, 30, 31, 32, 36
- group 3: statements 3, 8, 13, 15, 18, 20, 22, 30, 33, 38, 39, 40, 41, 45
- group 4: statements 0, 16, 19, 25, 30, 31, 32
- group 5: statements 1, 27, 35
- group 6: statements 4, 10, 43
- group 7: statements 30, 33, 41
- group 8: statements 13, 18, 30
- ungrouped: statements 9, 29

## Grouping G10 (13 groups)

- group 1: statements 16, 17, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36
- group 2: statements 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
- group 3: statements 3, 38, 39, 40, 41
- group 4: statements 0, 1, 2
- group 5: statements 20, 21, 37
- group 6: statements 43, 44, 45
- group 7: statements 14, 15
- group 8: statements 18, 19
- group 9: statements 22
- group 10: statements 23
- group 11: statements 24
- group 12: statements 25
- group 13: statements 42

