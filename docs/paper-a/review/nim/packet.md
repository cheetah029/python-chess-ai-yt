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

One pile of five objects. Two players take turns removing one or two objects. When the pile is empty the game ends, and the player who would move next wins (so taking the last object loses).

## The statements

```
  0  role(first)
  1  role(second)
  2  legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)
  3  legal(P,take(2)) :- true(control(P)) & true(pile(N)) & atleast2(N)
  4  legal(first,noop) :- true(control(second))
  5  legal(second,noop) :- true(control(first))
  6  next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)
  7  next(pile(M)) :- does(P,take(2)) & true(pile(N)) & succ(K,N) & succ(M,K)
  8  succ(0,1)
  9  succ(1,2)
 10  succ(2,3)
 11  succ(3,4)
 12  succ(4,5)
 13  positive(N) :- succ(M,N)
 14  atleast2(N) :- succ(K,N) & positive(K)
 15  next(control(first)) :- true(control(second))
 16  next(control(second)) :- true(control(first))
 17  empty_pile :- true(pile(0))
 18  terminal :- empty_pile
 19  goal(P,100) :- empty_pile & true(control(P))
 20  init(pile(5))
 21  init(control(first))
```

## Grouping G1 (22 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21

## Grouping G3 (8 groups)

- group 1: statements 15, 16, 17, 18, 19, 21
- group 2: statements 2, 4, 5
- group 3: statements 8, 11, 12
- group 4: statements 0, 1
- group 5: statements 3, 7
- group 6: statements 6, 20
- group 7: statements 9, 10
- group 8: statements 13, 14

## Grouping G4 (3 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 20
- group 2: statements 15, 16, 17, 18, 19, 21
- group 3: statements 0, 1

## Grouping G5 (6 groups)

- group 1: statements 6, 7, 8, 9, 10, 11, 12, 13, 14
- group 2: statements 2, 3, 4, 5, 6, 7, 20
- group 3: statements 15, 16, 17, 18, 19, 21
- group 4: statements 0, 1
- group 5: statements 2, 13
- group 6: statements 3, 14

## Grouping G6 (3 groups)

- group 1: statements 2, 3, 9, 11, 13, 14
- group 2: statements 6, 7, 8, 10, 12
- group 3: statements 17, 18, 19
- ungrouped: statements 0, 1, 4, 5, 15, 16, 20, 21

## Grouping G7 (8 groups)

- group 1: statements 15, 16, 17, 18, 19, 21
- group 2: statements 3, 4, 5
- group 3: statements 8, 9, 11
- group 4: statements 0, 1
- group 5: statements 2, 7
- group 6: statements 6, 20
- group 7: statements 10, 12
- group 8: statements 13, 14

## Grouping G8 (8 groups)

- group 1: statements 15, 16, 17, 18, 19, 21
- group 2: statements 2, 3, 4, 5
- group 3: statements 8, 9, 10, 11, 12, 13, 14
- group 4: statements 0, 1
- group 5: statements 2, 3, 4, 5, 7, 20
- group 6: statements 2, 3, 6, 20
- group 7: statements 9, 10, 11, 12, 13, 14
- group 8: statements 13, 14

## Grouping G9 (8 groups)

- group 1: statements 1, 8, 12, 15, 16, 21
- group 2: statements 0, 6, 18, 19
- group 3: statements 3, 4, 5, 7, 9, 14, 17
- group 4: statements 10, 20
- group 5: statements 0, 2, 6, 13, 18, 19
- group 6: statements 6, 11, 13, 18
- group 7: statements 4, 5, 7, 9, 14, 17
- group 8: statements 14, 17

## Grouping G10 (10 groups)

- group 1: statements 8, 9, 10, 11, 12
- group 2: statements 2, 3, 4, 5
- group 3: statements 6, 7, 17, 20
- group 4: statements 15, 16, 21
- group 5: statements 0, 1
- group 6: statements 13
- group 7: statements 14
- group 8: statements 17
- group 9: statements 18
- group 10: statements 19

