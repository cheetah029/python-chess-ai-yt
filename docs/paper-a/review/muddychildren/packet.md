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

Two children, ann and bob. First, nature makes at least one of them muddy. Each child sees the other's forehead but not their own. Then, for three rounds, both children say yes or no at the same time, and must say yes exactly when they know they are muddy; each hears what the other said. A child wins if, at the end, they know whether they are muddy.

## The statements

```
  0  role(ann)
  1  role(bob)
  2  role(random)
  3  init(round(0))
  4  yesno(0)
  5  yesno(1)
  6  child(ann)
  7  child(bob)
  8  legal(random,muddy(A,B)) :- true(round(0)) & yesno(A) & yesno(B) & oneMuddy(A,B)
  9  oneMuddy(1,B) :- yesno(B)
 10  oneMuddy(0,1)
 11  legal(C,noop) :- child(C) & true(round(0))
 12  legal(random,noop) :- ~true(round(0))
 13  next(has(ann,mud)) :- does(random,muddy(1,B))
 14  next(has(bob,mud)) :- does(random,muddy(A,1))
 15  next(has(C,mud)) :- true(has(C,mud))
 16  sees(C,dirt(D)) :- child(C) & true(has(D,mud)) & distinct(C,D)
 17  isMuddy(C) :- true(has(C,mud))
 18  isClean(C) :- child(C) & ~true(has(C,mud))
 19  someMuddy :- true(has(C,mud))
 20  knowsOwn(C) :- knows(C,isMuddy(C))
 21  knowsOwn(C) :- knows(C,isClean(C))
 22  legal(C,say(yes)) :- child(C) & ~true(round(0)) & knows(C,isMuddy(C))
 23  legal(C,say(no)) :- child(C) & ~true(round(0)) & ~knows(C,isMuddy(C))
 24  sees(C,said(D,X)) :- child(C) & does(D,say(X))
 25  next(round(1)) :- true(round(0))
 26  next(round(2)) :- true(round(1))
 27  next(round(3)) :- true(round(2))
 28  terminal :- true(round(3))
 29  goal(C,100) :- child(C) & knowsOwn(C)
 30  goal(C,0) :- child(C) & ~knowsOwn(C)
 31  goal(random,0)
```

## Grouping G1 (32 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31

## Grouping G3 (7 groups)

- group 1: statements 4, 5, 8, 9, 10, 13, 14, 15
- group 2: statements 17, 20, 21, 28, 29, 30, 31
- group 3: statements 3, 25, 26, 27
- group 4: statements 0, 1, 2
- group 5: statements 6, 7, 18
- group 6: statements 11, 12, 22
- group 7: statements 16, 23, 24
- ungrouped: statements 19

## Grouping G4 (2 groups)

- group 1: statements 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 2: statements 0, 1, 2
- ungrouped: statements 19

## Grouping G5 (8 groups)

- group 1: statements 3, 6, 7, 8, 11, 12, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
- group 2: statements 4, 5, 8, 9, 10
- group 3: statements 8, 13, 14, 15
- group 4: statements 0, 1, 2
- group 5: statements 4, 5, 9
- group 6: statements 17, 22, 23
- group 7: statements 9, 10
- group 8: statements 17, 20
- ungrouped: statements 19

## Grouping G6 (4 groups)

- group 1: statements 6, 7, 11, 16, 22, 24
- group 2: statements 4, 5, 8, 9, 10
- group 3: statements 17, 20, 23, 29
- group 4: statements 18, 21, 30
- ungrouped: statements 0, 1, 2, 3, 12, 13, 14, 15, 19, 25, 26, 27, 28, 31

## Grouping G7 (7 groups)

- group 1: statements 4, 5, 8, 9, 10, 13, 14, 15
- group 2: statements 17, 20, 21, 29, 30, 31
- group 3: statements 3, 25, 26, 27
- group 4: statements 0, 1, 2
- group 5: statements 6, 7, 18
- group 6: statements 11, 12, 22
- group 7: statements 16, 23, 24
- ungrouped: statements 19, 28

## Grouping G8 (6 groups)

- group 1: statements 4, 5, 8, 9, 10, 12, 13, 14, 15
- group 2: statements 6, 7, 16, 17, 18, 20, 21, 24, 28, 29, 30, 31
- group 3: statements 6, 7, 8, 11, 12, 17, 22, 23, 24
- group 4: statements 3, 24, 25, 26, 27, 28
- group 5: statements 6, 7, 16, 18, 24, 28, 29, 30
- group 6: statements 0, 1, 2
- ungrouped: statements 19

## Grouping G9 (6 groups)

- group 1: statements 2, 5, 14, 17, 19, 22, 23, 26, 27
- group 2: statements 0, 4, 6, 10, 11, 13, 15, 24, 25, 28, 30, 31
- group 3: statements 0, 9, 10, 12, 14, 15, 21, 25, 27
- group 4: statements 1, 8, 13, 15, 16, 20
- group 5: statements 0, 4, 6, 10, 13, 15, 28, 31
- group 6: statements 3, 7, 29
- ungrouped: statements 18

## Grouping G10 (14 groups)

- group 1: statements 8, 11, 12, 22, 23
- group 2: statements 3, 25, 26, 27
- group 3: statements 0, 1, 2
- group 4: statements 13, 14, 15
- group 5: statements 29, 30, 31
- group 6: statements 4, 5
- group 7: statements 6, 7
- group 8: statements 9, 10
- group 9: statements 16, 24
- group 10: statements 20, 21
- group 11: statements 17
- group 12: statements 18
- group 13: statements 19
- group 14: statements 28

