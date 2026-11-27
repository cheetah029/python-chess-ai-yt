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

Three cards, jack < queen < king. Both players put in one chip. Nature deals each player one card, which only that player sees. Player1 checks or bets one chip. After a check, player2 checks (showdown) or bets; after a bet, the other player folds (losing what they put in) or calls (showdown). Each player sees the other's actions. At a showdown both cards are shown and the higher card takes the pot.

## The statements

```
  0  role(player1)
  1  role(player2)
  2  role(random)
  3  player(player1)
  4  player(player2)
  5  opponent(player1,player2)
  6  opponent(player2,player1)
  7  card(j)
  8  card(q)
  9  card(k)
 10  higher(q,j)
 11  higher(k,j)
 12  higher(k,q)
 13  action(check)
 14  action(bet)
 15  action(call)
 16  action(fold)
 17  init(dealing)
 18  legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)
 19  legal(random,noop) :- ~true(dealing)
 20  legal(P,check) :- true(control(P)) & ~facing(P)
 21  legal(P,bet) :- true(control(P)) & ~facing(P)
 22  legal(P,call) :- true(control(P)) & facing(P)
 23  legal(P,fold) :- true(control(P)) & facing(P)
 24  legal(P,noop) :- player(P) & ~true(control(P))
 25  facing(P) :- opponent(P,Q) & true(bet_by(Q))
 26  sees(player1,mycard(C)) :- does(random,deal(C,D))
 27  sees(player2,mycard(D)) :- does(random,deal(C,D))
 28  sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)
 29  sees(P,shown(C)) :- opponent(P,Q) & true(holds(Q,C)) & to_showdown
 30  to_showdown :- does(player2,check)
 31  to_showdown :- does(P,call)
 32  next(holds(player1,C)) :- does(random,deal(C,D))
 33  next(holds(player2,D)) :- does(random,deal(C,D))
 34  next(holds(P,C)) :- true(holds(P,C))
 35  next(control(player1)) :- true(dealing)
 36  next(control(Q)) :- true(control(P)) & opponent(P,Q)
 37  next(bet_by(P)) :- does(P,bet)
 38  next(showdown(1)) :- does(player2,check)
 39  next(showdown(2)) :- does(P,call)
 40  next(folded(P)) :- does(P,fold)
 41  terminal :- true(showdown(S))
 42  terminal :- true(folded(P))
 43  best(P) :- opponent(P,Q) & true(holds(P,C)) & true(holds(Q,D)) & higher(C,D)
 44  goal(P,100) :- best(P) & true(showdown(2))
 45  goal(P,75) :- best(P) & true(showdown(1))
 46  goal(P,75) :- opponent(P,Q) & true(folded(Q))
 47  goal(P,25) :- opponent(P,Q) & best(Q) & true(showdown(1))
 48  goal(P,25) :- true(folded(P))
 49  goal(P,0) :- opponent(P,Q) & best(Q) & true(showdown(2))
 50  goal(random,0)
```

## Grouping G1 (51 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50

## Grouping G3 (15 groups)

- group 1: statements 3, 4, 17, 19, 24
- group 2: statements 13, 14, 15, 16, 28
- group 3: statements 29, 32, 33, 34, 43
- group 4: statements 44, 45, 47, 49, 50
- group 5: statements 0, 1, 2
- group 6: statements 7, 8, 9
- group 7: statements 10, 11, 12
- group 8: statements 18, 26, 27
- group 9: statements 20, 30, 38
- group 10: statements 21, 25, 37
- group 11: statements 22, 31, 39
- group 12: statements 42, 46, 48
- group 13: statements 5, 6
- group 14: statements 23, 40
- group 15: statements 35, 36
- ungrouped: statements 41

## Grouping G4 (2 groups)

- group 1: statements 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50
- group 2: statements 0, 1, 2

## Grouping G5 (24 groups)

- group 1: statements 5, 6, 25, 26, 27, 28, 29, 32, 33, 34, 36, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50
- group 2: statements 20, 21, 22, 23, 25, 38, 39, 40
- group 3: statements 18, 19, 20, 21, 22, 23, 24
- group 4: statements 13, 14, 15, 16, 28
- group 5: statements 7, 8, 9, 18
- group 6: statements 10, 11, 12, 43
- group 7: statements 13, 14, 15, 16
- group 8: statements 17, 18, 19, 35
- group 9: statements 0, 1, 2
- group 10: statements 3, 4, 24
- group 11: statements 7, 8, 9
- group 12: statements 10, 11, 12
- group 13: statements 18, 26, 27
- group 14: statements 18, 32, 33
- group 15: statements 3, 4
- group 16: statements 17, 35
- group 17: statements 20, 30
- group 18: statements 21, 37
- group 19: statements 22, 31
- group 20: statements 25, 37
- group 21: statements 29, 30
- group 22: statements 29, 31
- group 23: statements 30, 31
- group 24: statements 35, 36

## Grouping G6 (7 groups)

- group 1: statements 5, 6, 36, 46, 47, 49
- group 2: statements 10, 11, 12, 43, 44, 45
- group 3: statements 13, 14, 15, 16, 28
- group 4: statements 20, 21, 22, 23, 25
- group 5: statements 7, 8, 9, 18
- group 6: statements 3, 4, 24
- group 7: statements 29, 30, 31
- ungrouped: statements 0, 1, 2, 17, 19, 26, 27, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 48, 50

## Grouping G7 (15 groups)

- group 1: statements 13, 14, 15, 16, 26, 27, 28
- group 2: statements 17, 18, 19, 21, 23, 24, 26, 27, 32, 33, 35
- group 3: statements 0, 1, 2
- group 4: statements 3, 4, 24
- group 5: statements 5, 6, 35, 36
- group 6: statements 7, 8, 9
- group 7: statements 10, 11, 12
- group 8: statements 20, 30, 31, 38
- group 9: statements 21, 25, 37
- group 10: statements 22, 30, 31, 39
- group 11: statements 26, 27, 29, 32, 33, 34, 43
- group 12: statements 44, 45, 46, 47, 48, 49, 50
- group 13: statements 23, 40
- group 14: statements 41, 42
- group 15: statements 42, 46, 48

## Grouping G8 (15 groups)

- group 1: statements 13, 14, 15, 16, 26, 27, 28
- group 2: statements 17, 18, 19, 21, 23, 24, 26, 27, 32, 33, 35
- group 3: statements 19, 20, 21, 22, 23, 24, 30, 31
- group 4: statements 44, 45, 46, 47, 48, 49, 50
- group 5: statements 0, 1, 2
- group 6: statements 3, 4, 24
- group 7: statements 5, 6, 35, 36
- group 8: statements 7, 8, 9
- group 9: statements 10, 11, 12
- group 10: statements 21, 25, 37
- group 11: statements 26, 27, 29, 32, 33, 34, 43
- group 12: statements 23, 40
- group 13: statements 38, 39
- group 14: statements 41, 42
- group 15: statements 42, 46, 48

## Grouping G9 (15 groups)

- group 1: statements 14, 20, 21, 23, 34, 47, 50
- group 2: statements 6, 11, 15, 17, 18, 21, 28, 33, 43, 46, 47
- group 3: statements 9, 11, 15, 17, 29, 38, 43, 44
- group 4: statements 2, 16, 24, 26, 31, 32, 48
- group 5: statements 12, 27, 42
- group 6: statements 15, 40, 41
- group 7: statements 5, 7, 8, 18
- group 8: statements 1, 35, 49
- group 9: statements 0, 4, 39
- group 10: statements 10, 11, 45
- group 11: statements 3, 6, 21, 25, 36, 46, 47
- group 12: statements 17, 22
- group 13: statements 13, 37
- group 14: statements 19, 30
- group 15: statements 16, 19, 26

## Grouping G10 (18 groups)

- group 1: statements 18, 19, 20, 21, 22, 23, 24
- group 2: statements 44, 45, 46, 47, 48, 49, 50
- group 3: statements 13, 14, 15, 16
- group 4: statements 26, 27, 28, 29
- group 5: statements 30, 31, 38, 39
- group 6: statements 0, 1, 2
- group 7: statements 7, 8, 9
- group 8: statements 10, 11, 12
- group 9: statements 32, 33, 34
- group 10: statements 3, 4
- group 11: statements 5, 6
- group 12: statements 35, 36
- group 13: statements 41, 42
- group 14: statements 17
- group 15: statements 25
- group 16: statements 37
- group 17: statements 40
- group 18: statements 43

