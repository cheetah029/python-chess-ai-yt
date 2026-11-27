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

A game show with three doors. First, the host (a random player) hides a car behind one door while the candidate picks a door. Second, the host opens a door that is still closed, hides no car and was not picked; the candidate sees which. Third, the candidate may switch to the other closed door, or stay. The candidate wins if the door they end with hides the car.

## The statements

```
  0  role(candidate)
  1  role(random)
  2  door(1)
  3  door(2)
  4  door(3)
  5  init(closed(1))
  6  init(closed(2))
  7  init(closed(3))
  8  init(step(1))
  9  legal(random,hide_car(D)) :- true(step(1)) & door(D)
 10  legal(random,open_door(D)) :- true(step(2)) & true(closed(D)) & ~true(car(D)) & ~true(chosen(D))
 11  legal(random,noop) :- true(step(3))
 12  legal(candidate,choose(D)) :- true(step(1)) & door(D)
 13  legal(candidate,noop) :- true(step(2))
 14  legal(candidate,noop) :- true(step(3))
 15  legal(candidate,switch) :- true(step(3))
 16  sees(candidate,opened(D)) :- does(random,open_door(D))
 17  next(car(D)) :- does(random,hide_car(D))
 18  next(car(D)) :- true(car(D))
 19  next(closed(D)) :- true(closed(D)) & ~does(random,open_door(D))
 20  next(chosen(D)) :- does(candidate,choose(D))
 21  next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)
 22  next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))
 23  next(step(2)) :- true(step(1))
 24  next(step(3)) :- true(step(2))
 25  next(step(4)) :- true(step(3))
 26  terminal :- true(step(4))
 27  goal(candidate,100) :- true(chosen(D)) & true(car(D))
 28  goal(candidate,0) :- true(chosen(D)) & ~true(car(D))
 29  goal(random,0)
```

## Grouping G1 (30 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29

## Grouping G3 (9 groups)

- group 1: statements 2, 3, 4, 12
- group 2: statements 5, 6, 7, 19
- group 3: statements 8, 23, 24, 25
- group 4: statements 9, 11, 13, 14
- group 5: statements 15, 20, 21, 22
- group 6: statements 17, 18, 26
- group 7: statements 27, 28, 29
- group 8: statements 0, 1
- group 9: statements 10, 16

## Grouping G4 (7 groups)

- group 1: statements 9, 10, 11, 12, 13, 14, 15, 16, 19, 20
- group 2: statements 17, 18, 20, 21, 22, 26, 27, 28, 29
- group 3: statements 2, 3, 4, 9, 12, 17
- group 4: statements 8, 17, 18, 20, 23, 24, 25, 26
- group 5: statements 5, 6, 7, 19
- group 6: statements 15, 17, 20, 21, 22
- group 7: statements 0, 1

## Grouping G5 (1 groups)

- group 1: statements 2, 3, 4, 9, 12
- ungrouped: statements 0, 1, 5, 6, 7, 8, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29

## Grouping G6 (9 groups)

- group 1: statements 2, 3, 4, 9
- group 2: statements 5, 6, 7, 19
- group 3: statements 8, 23, 24, 25
- group 4: statements 11, 12, 13, 14
- group 5: statements 15, 20, 21, 22
- group 6: statements 17, 18, 26
- group 7: statements 27, 28, 29
- group 8: statements 0, 1
- group 9: statements 10, 16

## Grouping G7 (10 groups)

- group 1: statements 9, 10, 11, 12, 13, 14, 15
- group 2: statements 5, 6, 7, 19
- group 3: statements 8, 23, 24, 25
- group 4: statements 2, 3, 4
- group 5: statements 20, 21, 22
- group 6: statements 27, 28, 29
- group 7: statements 0, 1
- group 8: statements 17, 18
- group 9: statements 16
- group 10: statements 26

## Grouping G8 (11 groups)

- group 1: statements 8, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 8, 17, 18, 23, 24, 25, 26, 27, 28, 29
- group 3: statements 9, 10, 11, 12, 13, 14, 15, 20
- group 4: statements 2, 3, 4, 9, 12
- group 5: statements 5, 6, 7, 19
- group 6: statements 15, 20, 21, 22
- group 7: statements 2, 3, 4
- group 8: statements 0, 1
- group 9: statements 9, 17
- group 10: statements 10, 16
- group 11: statements 10, 19

## Grouping G9 (7 groups)

- group 1: statements 9, 10, 11, 12, 13, 14, 15, 16, 17, 19
- group 2: statements 17, 18, 20, 21, 22, 26, 27, 28, 29
- group 3: statements 2, 3, 4, 9, 12, 20
- group 4: statements 8, 17, 18, 20, 23, 24, 25, 26
- group 5: statements 5, 6, 7, 19
- group 6: statements 15, 17, 20, 21, 22
- group 7: statements 0, 1

## Grouping G10 (7 groups)

- group 1: statements 2, 4, 6, 14, 19, 20, 21, 22, 23, 25
- group 2: statements 6, 9, 11, 12, 13, 15, 24, 27, 28
- group 3: statements 5, 9, 14, 17, 18, 21
- group 4: statements 1, 6, 8, 9, 11, 13, 16, 29
- group 5: statements 0, 7, 22, 26
- group 6: statements 4, 6, 9, 15, 28
- group 7: statements 3, 10

## Grouping G11 (2 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29
- group 2: statements 0, 1

