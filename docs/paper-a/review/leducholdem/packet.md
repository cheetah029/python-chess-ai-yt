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

Six cards, two each of jack < queen < king. Both players put in one chip. Nature deals each player one private card, of which the player learns the rank. A betting round follows, with bets of 2: check or bet, then fold, call or raise, with at most one bet and one raise per round; two checks or a call end the round, a fold ends the hand. Nature then turns one public card, and a second betting round follows with bets of 4. Player1 acts first in each round, and each player sees the other's actions. At the showdown a card pairing the public card wins, otherwise the higher card; equal ranks split the pot. Payoffs scale the chips won or lost.

## The statements

```
  0  role(player1)
  1  role(player2)
  2  role(random)
  3  player(player1)
  4  player(player2)
  5  opponent(player1,player2)
  6  opponent(player2,player1)
  7  card(j1)
  8  card(j2)
  9  card(q1)
 10  card(q2)
 11  card(k1)
 12  card(k2)
 13  rank(j1,j)
 14  rank(j2,j)
 15  rank(q1,q)
 16  rank(q2,q)
 17  rank(k1,k)
 18  rank(k2,k)
 19  higher(q,j)
 20  higher(k,j)
 21  higher(k,q)
 22  action(check)
 23  action(bet)
 24  action(call)
 25  action(raise)
 26  action(fold)
 27  amount(1,1,0,1)
 28  amount(1,1,1,3)
 29  amount(1,1,2,5)
 30  amount(2,1,0,1)
 31  amount(2,1,1,5)
 32  amount(2,1,2,9)
 33  amount(2,3,0,3)
 34  amount(2,3,1,7)
 35  amount(2,3,2,11)
 36  amount(2,5,0,5)
 37  amount(2,5,1,9)
 38  amount(2,5,2,13)
 39  succ(0,1)
 40  succ(1,2)
 41  payoff(1,53,47)
 42  payoff(3,59,41)
 43  payoff(5,65,35)
 44  payoff(7,71,29)
 45  payoff(9,77,23)
 46  payoff(11,83,17)
 47  payoff(13,89,11)
 48  init(dealing)
 49  init(stake(1))
 50  nature_turn :- true(dealing)
 51  nature_turn :- true(revealing)
 52  legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)
 53  legal(random,reveal(C)) :- true(revealing) & card(C) & ~dealt(C)
 54  legal(random,noop) :- ~nature_turn
 55  dealt(C) :- true(holds(P,C))
 56  facing(P) :- opponent(P,Q) & true(bet_by(Q))
 57  legal(P,check) :- true(control(P)) & ~facing(P)
 58  legal(P,bet) :- true(control(P)) & ~facing(P)
 59  legal(P,call) :- true(control(P)) & facing(P)
 60  legal(P,fold) :- true(control(P)) & facing(P)
 61  legal(P,raise) :- true(control(P)) & facing(P) & true(bets(1))
 62  legal(P,noop) :- player(P) & ~true(control(P))
 63  round_ends :- does(P,call)
 64  round_ends :- does(player2,check)
 65  folding :- does(P,fold)
 66  revealed_now :- does(random,reveal(C))
 67  sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)
 68  sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)
 69  sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)
 70  sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)
 71  sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown
 72  to_showdown :- true(round(2)) & round_ends
 73  next(holds(player1,C)) :- does(random,deal(C,D))
 74  next(holds(player2,D)) :- does(random,deal(C,D))
 75  next(holds(P,C)) :- true(holds(P,C))
 76  next(board(C)) :- does(random,reveal(C))
 77  next(board(C)) :- true(board(C))
 78  next(round(1)) :- does(random,deal(C,D))
 79  next(round(2)) :- does(random,reveal(C))
 80  next(round(R)) :- true(round(R)) & ~revealed_now
 81  next(revealing) :- true(round(1)) & round_ends
 82  next(control(player1)) :- does(random,deal(C,D))
 83  next(control(player1)) :- does(random,reveal(C))
 84  next(control(Q)) :- true(control(P)) & opponent(P,Q) & ~round_ends & ~folding
 85  next(bets(0)) :- does(random,deal(C,D))
 86  next(bets(0)) :- does(random,reveal(C))
 87  next(bets(0)) :- does(player1,check) & true(bets(0))
 88  next(bets(1)) :- does(P,bet)
 89  next(bets(2)) :- does(P,raise)
 90  next(bet_by(P)) :- does(P,bet)
 91  next(bet_by(P)) :- does(P,raise)
 92  next(stake(S)) :- true(stake(S)) & ~round_ends
 93  next(stake(S)) :- true(stake(S)) & does(player2,check)
 94  next(stake(X)) :- true(stake(S)) & does(P,call) & true(round(R)) & true(bets(K)) & amount(R,S,K,X)
 95  next(showdown(S)) :- true(round(2)) & does(player2,check) & true(stake(S))
 96  next(showdown(X)) :- true(round(2)) & does(P,call) & true(stake(S)) & true(bets(K)) & amount(2,S,K,X)
 97  next(folded(P,X)) :- does(P,fold) & true(round(R)) & true(stake(S)) & true(bets(K)) & succ(J,K) & amount(R,S,J,X)
 98  terminal :- true(showdown(X))
 99  terminal :- true(folded(P,X))
100  paired(P) :- true(holds(P,C)) & rank(C,R) & true(board(B)) & rank(B,R)
101  beats(P) :- opponent(P,Q) & paired(P) & ~paired(Q)
102  beats(P) :- opponent(P,Q) & ~paired(P) & ~paired(Q) & true(holds(P,C)) & rank(C,R) & true(holds(Q,D)) & rank(D,S) & higher(R,S)
103  split :- ~beats(player1) & ~beats(player2)
104  goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)
105  goal(P,L) :- opponent(P,Q) & beats(Q) & true(showdown(X)) & payoff(X,W,L)
106  goal(P,50) :- player(P) & true(showdown(X)) & split
107  goal(P,W) :- opponent(P,Q) & true(folded(Q,X)) & payoff(X,W,L)
108  goal(P,L) :- true(folded(P,X)) & payoff(X,W,L)
109  goal(random,0)
```

## Grouping G1 (110 groups)

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

## Grouping G2 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109

## Grouping G3 (25 groups)

- group 1: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38
- group 2: statements 41, 42, 43, 44, 45, 46, 47
- group 3: statements 55, 71, 73, 74, 75, 100, 102
- group 4: statements 7, 8, 9, 10, 11, 12
- group 5: statements 13, 14, 15, 16, 17, 18
- group 6: statements 22, 23, 24, 25, 26, 70
- group 7: statements 72, 78, 79, 80, 81
- group 8: statements 85, 86, 87, 88, 89
- group 9: statements 48, 50, 51, 54
- group 10: statements 49, 92, 93, 94
- group 11: statements 53, 66, 76, 77
- group 12: statements 57, 59, 63, 64
- group 13: statements 98, 104, 105, 106
- group 14: statements 99, 107, 108, 109
- group 15: statements 0, 1, 2
- group 16: statements 3, 4, 69
- group 17: statements 5, 6, 56
- group 18: statements 19, 20, 21
- group 19: statements 39, 40, 97
- group 20: statements 52, 67, 68
- group 21: statements 82, 83, 84
- group 22: statements 58, 90
- group 23: statements 60, 65
- group 24: statements 61, 91
- group 25: statements 101, 103
- ungrouped: statements 62, 95, 96

## Grouping G4 (22 groups)

- group 1: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38
- group 2: statements 41, 42, 43, 44, 45, 46, 47, 69, 107, 108
- group 3: statements 7, 8, 9, 10, 11, 12
- group 4: statements 13, 14, 15, 16, 17, 18, 67, 68, 69, 100
- group 5: statements 22, 23, 24, 25, 26, 67, 68, 69, 70
- group 6: statements 48, 50, 51, 52, 53, 54, 66, 67, 68, 69, 73, 74, 76, 78, 79, 82, 83, 85, 86
- group 7: statements 55, 67, 68, 69, 71, 73, 74, 75, 76, 77, 100, 102
- group 8: statements 49, 78, 79, 85, 86, 92, 93, 94, 95
- group 9: statements 57, 58, 59, 60, 61, 65, 69, 82, 83, 84, 90
- group 10: statements 61, 82, 83, 85, 86, 87, 88, 89, 91
- group 11: statements 66, 69, 72, 78, 79, 80, 81, 95
- group 12: statements 0, 1, 2
- group 13: statements 19, 20, 21
- group 14: statements 39, 40, 69, 78, 79, 85, 86, 97
- group 15: statements 56, 69, 90, 91
- group 16: statements 69, 98, 104, 105, 106
- group 17: statements 69, 99, 107, 108
- group 18: statements 3, 4, 69
- group 19: statements 5, 6, 69
- group 20: statements 57, 64, 82, 83
- group 21: statements 59, 63, 82, 83
- group 22: statements 69, 101, 103
- ungrouped: statements 62, 96, 109

## Grouping G5 (10 groups)

- group 1: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 94, 96, 97
- group 2: statements 13, 14, 15, 16, 17, 18, 19, 20, 21, 67, 68, 69, 71, 100, 102
- group 3: statements 5, 6, 41, 42, 43, 44, 45, 46, 47, 101, 104, 105, 107, 108
- group 4: statements 7, 8, 9, 10, 11, 12, 52, 53, 55
- group 5: statements 63, 64, 65, 72, 81, 84, 92
- group 6: statements 22, 23, 24, 25, 26, 70
- group 7: statements 56, 57, 58, 59, 60, 61
- group 8: statements 3, 4, 62, 103, 106
- group 9: statements 50, 51, 54
- group 10: statements 66, 80
- ungrouped: statements 0, 1, 2, 48, 49, 73, 74, 75, 76, 77, 78, 79, 82, 83, 85, 86, 87, 88, 89, 90, 91, 93, 95, 98, 99, 109

## Grouping G6 (23 groups)

- group 1: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38
- group 2: statements 13, 14, 15, 16, 17, 18, 67, 68, 69
- group 3: statements 41, 42, 43, 44, 45, 46, 47
- group 4: statements 55, 71, 73, 74, 75, 100, 102
- group 5: statements 7, 8, 9, 10, 11, 12
- group 6: statements 22, 23, 24, 25, 26, 70
- group 7: statements 48, 50, 51, 52, 54
- group 8: statements 72, 78, 79, 80, 81
- group 9: statements 85, 86, 87, 88, 89
- group 10: statements 49, 92, 93, 94
- group 11: statements 53, 66, 76, 77
- group 12: statements 56, 58, 90, 91
- group 13: statements 57, 59, 63, 64
- group 14: statements 98, 104, 105, 106
- group 15: statements 0, 1, 2
- group 16: statements 19, 20, 21
- group 17: statements 39, 40, 97
- group 18: statements 82, 83, 84
- group 19: statements 99, 107, 108
- group 20: statements 3, 4
- group 21: statements 5, 6
- group 22: statements 60, 65
- group 23: statements 101, 103
- ungrouped: statements 61, 62, 95, 96, 109

## Grouping G7 (36 groups)

- group 1: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38
- group 2: statements 52, 53, 54, 57, 58, 59, 60, 61, 62
- group 3: statements 41, 42, 43, 44, 45, 46, 47
- group 4: statements 7, 8, 9, 10, 11, 12
- group 5: statements 13, 14, 15, 16, 17, 18
- group 6: statements 104, 105, 106, 107, 108, 109
- group 7: statements 22, 23, 24, 25, 26
- group 8: statements 63, 64, 78, 79, 80
- group 9: statements 67, 68, 69, 70, 71
- group 10: statements 85, 86, 87, 88, 89
- group 11: statements 49, 92, 93, 94
- group 12: statements 0, 1, 2
- group 13: statements 19, 20, 21
- group 14: statements 72, 95, 96
- group 15: statements 73, 74, 75
- group 16: statements 82, 83, 84
- group 17: statements 3, 4
- group 18: statements 5, 6
- group 19: statements 39, 40
- group 20: statements 50, 51
- group 21: statements 50, 51
- group 22: statements 63, 64
- group 23: statements 76, 77
- group 24: statements 90, 91
- group 25: statements 98, 99
- group 26: statements 101, 102
- group 27: statements 48
- group 28: statements 55
- group 29: statements 56
- group 30: statements 65
- group 31: statements 66
- group 32: statements 66
- group 33: statements 81
- group 34: statements 97
- group 35: statements 100
- group 36: statements 103

## Grouping G8 (66 groups)

- group 1: statements 3, 4, 5, 6, 41, 42, 43, 44, 45, 46, 47, 56, 57, 58, 59, 60, 61, 62, 84, 98, 99, 101, 103, 104, 105, 106, 107, 108, 109
- group 2: statements 3, 4, 5, 6, 41, 42, 43, 44, 45, 46, 47, 56, 71, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109
- group 3: statements 3, 4, 5, 6, 41, 42, 43, 44, 45, 46, 47, 56, 95, 96, 97, 98, 99, 101, 103, 104, 105, 106, 107, 108, 109
- group 4: statements 3, 4, 5, 6, 41, 42, 43, 44, 45, 46, 47, 56, 69, 70, 98, 99, 101, 103, 104, 105, 106, 107, 108, 109
- group 5: statements 3, 4, 5, 6, 41, 42, 43, 44, 45, 46, 47, 56, 98, 99, 101, 103, 104, 105, 106, 107, 108, 109
- group 6: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 94, 96, 97
- group 7: statements 13, 14, 15, 16, 17, 18, 67, 68, 69, 70, 71, 100, 102
- group 8: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38
- group 9: statements 49, 72, 78, 79, 80, 81, 92, 93, 94, 95, 96, 97
- group 10: statements 57, 59, 60, 61, 62, 84, 93, 94, 95, 96, 97
- group 11: statements 13, 14, 15, 16, 17, 18, 67, 68, 69, 70
- group 12: statements 54, 57, 58, 59, 60, 61, 62, 82, 83, 84
- group 13: statements 52, 54, 57, 58, 59, 60, 61, 62, 82
- group 14: statements 53, 54, 57, 58, 59, 60, 61, 62, 83
- group 15: statements 57, 58, 61, 85, 86, 87, 88, 89
- group 16: statements 85, 86, 87, 88, 89, 94, 96, 97
- group 17: statements 7, 8, 9, 10, 11, 12, 52
- group 18: statements 7, 8, 9, 10, 11, 12, 53
- group 19: statements 55, 71, 73, 74, 75, 100, 102
- group 20: statements 7, 8, 9, 10, 11, 12
- group 21: statements 22, 23, 24, 25, 26, 70
- group 22: statements 71, 72, 95, 96, 97, 102
- group 23: statements 22, 23, 24, 25, 26
- group 24: statements 69, 70, 95, 96, 97
- group 25: statements 85, 86, 87, 88, 89
- group 26: statements 19, 20, 21, 102
- group 27: statements 62, 69, 70, 84
- group 28: statements 62, 71, 84, 102
- group 29: statements 0, 1, 2
- group 30: statements 19, 20, 21
- group 31: statements 39, 40, 97
- group 32: statements 48, 50, 52
- group 33: statements 52, 67, 68
- group 34: statements 52, 73, 74
- group 35: statements 53, 79, 81
- group 36: statements 57, 64, 84
- group 37: statements 59, 63, 84
- group 38: statements 60, 65, 84
- group 39: statements 63, 72, 81
- group 40: statements 64, 72, 81
- group 41: statements 76, 77, 100
- group 42: statements 39, 40
- group 43: statements 48, 50
- group 44: statements 50, 51
- group 45: statements 50, 54
- group 46: statements 51, 53
- group 47: statements 51, 54
- group 48: statements 51, 81
- group 49: statements 52, 53
- group 50: statements 52, 78
- group 51: statements 52, 85
- group 52: statements 53, 55
- group 53: statements 53, 66
- group 54: statements 53, 69
- group 55: statements 53, 76
- group 56: statements 53, 86
- group 57: statements 56, 90
- group 58: statements 56, 91
- group 59: statements 58, 90
- group 60: statements 61, 91
- group 61: statements 63, 64
- group 62: statements 63, 92
- group 63: statements 64, 92
- group 64: statements 66, 80
- group 65: statements 76, 77
- group 66: statements 90, 91

## Grouping G9 (22 groups)

- group 1: statements 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38
- group 2: statements 41, 42, 43, 44, 45, 46, 47, 69, 107, 108
- group 3: statements 7, 8, 9, 10, 11, 12
- group 4: statements 13, 14, 15, 16, 17, 18, 67, 68, 69, 100
- group 5: statements 22, 23, 24, 25, 26, 67, 68, 69, 70
- group 6: statements 48, 50, 51, 52, 53, 54, 66, 67, 68, 69, 73, 74, 76, 78, 79, 82, 83, 85, 86
- group 7: statements 55, 67, 68, 69, 71, 73, 74, 75, 76, 77, 100, 102
- group 8: statements 49, 78, 79, 85, 86, 92, 93, 94, 95
- group 9: statements 57, 58, 59, 60, 61, 65, 69, 82, 83, 84, 90
- group 10: statements 61, 82, 83, 85, 86, 87, 88, 89, 91
- group 11: statements 66, 69, 72, 78, 79, 80, 81, 95
- group 12: statements 69, 98, 104, 105, 106, 109
- group 13: statements 0, 1, 2
- group 14: statements 19, 20, 21
- group 15: statements 39, 40, 69, 78, 79, 85, 86, 97
- group 16: statements 56, 69, 90, 91
- group 17: statements 69, 99, 107, 108
- group 18: statements 3, 4, 69
- group 19: statements 5, 6, 69
- group 20: statements 57, 64, 82, 83
- group 21: statements 59, 63, 82, 83
- group 22: statements 69, 101, 103
- ungrouped: statements 62, 96

## Grouping G10 (22 groups)

- group 1: statements 2, 13, 25, 47, 48, 75, 80, 84, 85, 87, 99, 106
- group 2: statements 6, 28, 31, 49, 57, 58, 88, 97, 104, 105
- group 3: statements 29, 69, 81, 91, 94, 102
- group 4: statements 1, 7, 8, 16, 30, 50, 95, 96, 100, 104
- group 5: statements 1, 7, 10, 37, 43, 66, 89, 104, 109
- group 6: statements 1, 4, 7, 9, 11, 14, 18, 26, 34, 55, 59, 70, 71, 77, 78, 83, 90, 92, 104
- group 7: statements 1, 7, 26, 40, 55, 56, 62, 70, 72, 100, 104, 107
- group 8: statements 17, 18, 27, 36, 64, 71, 77, 82, 83
- group 9: statements 9, 12, 15, 20, 21, 39, 46, 76, 90, 101, 104
- group 10: statements 9, 18, 32, 68, 76, 77, 79, 90, 93
- group 11: statements 11, 27, 42, 60, 71, 83, 98, 104
- group 12: statements 5, 33, 53, 61, 104, 108
- group 13: statements 3, 23, 103
- group 14: statements 22, 41, 67
- group 15: statements 18, 19, 35, 45, 71, 77, 83, 104
- group 16: statements 12, 86, 93, 104
- group 17: statements 38, 49, 97, 104
- group 18: statements 54, 73, 104
- group 19: statements 24, 44, 104
- group 20: statements 0, 9, 20, 90
- group 21: statements 9, 15, 63, 90
- group 22: statements 51, 65, 104
- ungrouped: statements 52, 74

## Grouping G11 (2 groups)

- group 1: statements 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109
- group 2: statements 0, 1, 2

