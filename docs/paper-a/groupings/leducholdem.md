# leducholdem -- groupings

File: `lgref/identify/testgames/leducholdem.gdl`. Line numbers are lines of that file.

- **lgref**: 22 groups, 2 statements in no group
- **random_matched**: 22 groups, 2 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 40 | `role(player1)` | G12 | G19 |
| 41 | `role(player2)` | G12 | G03, G04, G05, G06 |
| 42 | `role(random)` | G12 | G00 |
| 43 | `player(player1)` | G17 | G12 |
| 44 | `player(player2)` | G17 | G05 |
| 45 | `opponent(player1,player2)` | G18 | G11 |
| 46 | `opponent(player2,player1)` | G18 | G01 |
| 48 | `card(j1)` | G02 | G03, G04, G05, G06 |
| 49 | `card(j2)` | G02 | G03 |
| 50 | `card(q1)` | G02 | G05, G08, G09, G19, G20 |
| 51 | `card(q2)` | G02 | G04 |
| 52 | `card(k1)` | G02 | G05, G10 |
| 53 | `card(k2)` | G02 | G08, G15 |
| 54 | `rank(j1,j)` | G03 | G00 |
| 55 | `rank(j2,j)` | G03 | G05 |
| 56 | `rank(q1,q)` | G03 | G08, G20 |
| 57 | `rank(q2,q)` | G03 | G03 |
| 58 | `rank(k1,k)` | G03 | G07 |
| 59 | `rank(k2,k)` | G03 | G05, G07, G09, G14 |
| 60 | `higher(q,j)` | G13 | G14 |
| 61 | `higher(k,j)` | G13 | G08, G19 |
| 62 | `higher(k,q)` | G13 | G08 |
| 64 | `action(check)` | G04 | G13 |
| 65 | `action(bet)` | G04 | G12 |
| 66 | `action(call)` | G04 | G18 |
| 67 | `action(raise)` | G04 | G00 |
| 68 | `action(fold)` | G04 | G05, G06 |
| 72 | `amount(1,1,0,1)` | G00 | G07, G10 |
| 73 | `amount(1,1,1,3)` | G00 | G01 |
| 74 | `amount(1,1,2,5)` | G00 | G02 |
| 75 | `amount(2,1,0,1)` | G00 | G03 |
| 76 | `amount(2,1,1,5)` | G00 | G01 |
| 77 | `amount(2,1,2,9)` | G00 | G09 |
| 78 | `amount(2,3,0,3)` | G00 | G11 |
| 79 | `amount(2,3,1,7)` | G00 | G05 |
| 80 | `amount(2,3,2,11)` | G00 | G14 |
| 81 | `amount(2,5,0,5)` | G00 | G07 |
| 82 | `amount(2,5,1,9)` | G00 | G04 |
| 83 | `amount(2,5,2,13)` | G00 | G16 |
| 84 | `succ(0,1)` | G14 | G08 |
| 85 | `succ(1,2)` | G14 | G06 |
| 88 | `payoff(1,53,47)` | G01 | G13 |
| 89 | `payoff(3,59,41)` | G01 | G10 |
| 90 | `payoff(5,65,35)` | G01 | G04 |
| 91 | `payoff(7,71,29)` | G01 | G18 |
| 92 | `payoff(9,77,23)` | G01 | G14 |
| 93 | `payoff(11,83,17)` | G01 | G08 |
| 94 | `payoff(13,89,11)` | G01 | G00 |
| 96 | `init(dealing)` | G05 | G00 |
| 97 | `init(stake(1))` | G07 | G01, G16 |
| 100 | `nature_turn :- true(dealing)` | G05 | G03 |
| 101 | `nature_turn :- true(revealing)` | G05 | G21 |
| 102 | `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)` | G05 | - |
| 103 | `legal(random,reveal(C)) :- true(revealing) & card(C) & ~dealt(C)` | G05 | G11 |
| 104 | `legal(random,noop) :- ~nature_turn` | G05 | G17 |
| 105 | `dealt(C) :- true(holds(P,C))` | G06 | G05, G06 |
| 108 | `facing(P) :- opponent(P,Q) & true(bet_by(Q))` | G15 | G06 |
| 109 | `legal(P,check) :- true(control(P)) & ~facing(P)` | G08, G19 | G01 |
| 110 | `legal(P,bet) :- true(control(P)) & ~facing(P)` | G08 | G01 |
| 111 | `legal(P,call) :- true(control(P)) & facing(P)` | G08, G20 | G05 |
| 112 | `legal(P,fold) :- true(control(P)) & facing(P)` | G08 | G10 |
| 113 | `legal(P,raise) :- true(control(P)) & facing(P) & true(bets(1))` | G08, G09 | G11 |
| 114 | `legal(P,noop) :- player(P) & ~true(control(P))` | - | G06 |
| 118 | `round_ends :- does(P,call)` | G20 | G20 |
| 119 | `round_ends :- does(player2,check)` | G19 | G07 |
| 120 | `folding :- does(P,fold)` | G08 | G21 |
| 121 | `revealed_now :- does(random,reveal(C))` | G05, G10 | G04 |
| 124 | `sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)` | G03, G04, G05, G06 | G13 |
| 125 | `sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)` | G03, G04, G05, G06 | G09 |
| 126 | `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` | G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21 | G02 |
| 127 | `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)` | G04 | G05, G06 |
| 128 | `sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown` | G06 | G05, G07, G10, G14 |
| 129 | `to_showdown :- true(round(2)) & round_ends` | G10 | G06 |
| 132 | `next(holds(player1,C)) :- does(random,deal(C,D))` | G05, G06 | G17 |
| 133 | `next(holds(player2,D)) :- does(random,deal(C,D))` | G05, G06 | - |
| 134 | `next(holds(P,C)) :- true(holds(P,C))` | G06 | G00 |
| 135 | `next(board(C)) :- does(random,reveal(C))` | G05, G06 | G08, G09 |
| 136 | `next(board(C)) :- true(board(C))` | G06 | G05, G07, G09, G14 |
| 138 | `next(round(1)) :- does(random,deal(C,D))` | G05, G07, G10, G14 | G05 |
| 139 | `next(round(2)) :- does(random,reveal(C))` | G05, G07, G10, G14 | G09 |
| 140 | `next(round(R)) :- true(round(R)) & ~revealed_now` | G10 | G00 |
| 142 | `next(revealing) :- true(round(1)) & round_ends` | G10 | G02 |
| 144 | `next(control(player1)) :- does(random,deal(C,D))` | G05, G08, G09, G19, G20 | G07 |
| 145 | `next(control(player1)) :- does(random,reveal(C))` | G05, G08, G09, G19, G20 | G05, G07, G10, G14 |
| 146 | `next(control(Q)) :- true(control(P)) & opponent(P,Q) & ~round_ends & ~folding` | G08 | G00 |
| 148 | `next(bets(0)) :- does(random,deal(C,D))` | G05, G07, G09, G14 | G00 |
| 149 | `next(bets(0)) :- does(random,reveal(C))` | G05, G07, G09, G14 | G15 |
| 150 | `next(bets(0)) :- does(player1,check) & true(bets(0))` | G09 | G00 |
| 151 | `next(bets(1)) :- does(P,bet)` | G09 | G01 |
| 152 | `next(bets(2)) :- does(P,raise)` | G09 | G04 |
| 154 | `next(bet_by(P)) :- does(P,bet)` | G08, G15 | G05, G08, G09, G19, G20 |
| 155 | `next(bet_by(P)) :- does(P,raise)` | G09, G15 | G02 |
| 157 | `next(stake(S)) :- true(stake(S)) & ~round_ends` | G07 | G05 |
| 158 | `next(stake(S)) :- true(stake(S)) & does(player2,check)` | G07 | G09, G15 |
| 159 | `next(stake(X)) :- true(stake(S)) & does(P,call) & true(round(R)) & true(bets(K)) & amount(R,S,K,X)` | G07 | G02 |
| 161 | `next(showdown(S)) :- true(round(2)) & does(player2,check) & true(stake(S))` | G07, G10 | G03 |
| 162 | `next(showdown(X)) :- true(round(2)) & does(P,call) & true(stake(S)) & true(bets(K)) & amount(2,S,K,X)` | - | G03 |
| 163 | `next(folded(P,X)) :- does(P,fold) & true(round(R)) & true(stake(S)) & true(bets(K)) & succ(J,K) & amount(R,S,J,X)` | G14 | G01, G16 |
| 166 | `terminal :- true(showdown(X))` | G11 | G10 |
| 167 | `terminal :- true(folded(P,X))` | G16 | G00 |
| 169 | `paired(P) :- true(holds(P,C)) & rank(C,R) & true(board(B)) & rank(B,R)` | G03, G06 | G03, G06 |
| 170 | `beats(P) :- opponent(P,Q) & paired(P) & ~paired(Q)` | G21 | G08 |
| 171 | `beats(P) :- opponent(P,Q) & ~paired(P) & ~paired(Q) & true(holds(P,C)) & rank(C,R) & true(holds(Q,D)) & rank(D,S) & higher(R,S)` | G06 | G02 |
| 172 | `split :- ~beats(player1) & ~beats(player2)` | G21 | G12 |
| 174 | `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` | G11 | G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21 |
| 175 | `goal(P,L) :- opponent(P,Q) & beats(Q) & true(showdown(X)) & payoff(X,W,L)` | G11 | G01 |
| 176 | `goal(P,50) :- player(P) & true(showdown(X)) & split` | G11 | G00 |
| 177 | `goal(P,W) :- opponent(P,Q) & true(folded(Q,X)) & payoff(X,W,L)` | G01, G16 | G06 |
| 178 | `goal(P,L) :- true(folded(P,X)) & payoff(X,W,L)` | G01, G16 | G11 |
| 179 | `goal(random,0)` | G11 | G04 |

## lgref by group

### lgref G00 (12 statements)

- line 72: `amount(1,1,0,1)`
- line 73: `amount(1,1,1,3)`
- line 74: `amount(1,1,2,5)`
- line 75: `amount(2,1,0,1)`
- line 76: `amount(2,1,1,5)`
- line 77: `amount(2,1,2,9)`
- line 78: `amount(2,3,0,3)`
- line 79: `amount(2,3,1,7)`
- line 80: `amount(2,3,2,11)`
- line 81: `amount(2,5,0,5)`
- line 82: `amount(2,5,1,9)`
- line 83: `amount(2,5,2,13)`

### lgref G01 (10 statements)

- line 88: `payoff(1,53,47)`
- line 89: `payoff(3,59,41)`
- line 90: `payoff(5,65,35)`
- line 91: `payoff(7,71,29)`
- line 92: `payoff(9,77,23)`
- line 93: `payoff(11,83,17)`
- line 94: `payoff(13,89,11)`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 177: `goal(P,W) :- opponent(P,Q) & true(folded(Q,X)) & payoff(X,W,L)` (also in G16)
- line 178: `goal(P,L) :- true(folded(P,X)) & payoff(X,W,L)` (also in G16)

### lgref G02 (6 statements)

- line 48: `card(j1)`
- line 49: `card(j2)`
- line 50: `card(q1)`
- line 51: `card(q2)`
- line 52: `card(k1)`
- line 53: `card(k2)`

### lgref G03 (10 statements)

- line 54: `rank(j1,j)`
- line 55: `rank(j2,j)`
- line 56: `rank(q1,q)`
- line 57: `rank(q2,q)`
- line 58: `rank(k1,k)`
- line 59: `rank(k2,k)`
- line 124: `sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)` (also in G04, G05, G06)
- line 125: `sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)` (also in G04, G05, G06)
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 169: `paired(P) :- true(holds(P,C)) & rank(C,R) & true(board(B)) & rank(B,R)` (also in G06)

### lgref G04 (9 statements)

- line 64: `action(check)`
- line 65: `action(bet)`
- line 66: `action(call)`
- line 67: `action(raise)`
- line 68: `action(fold)`
- line 124: `sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)` (also in G03, G05, G06)
- line 125: `sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)` (also in G03, G05, G06)
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 127: `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)`

### lgref G05 (19 statements)

- line 96: `init(dealing)`
- line 100: `nature_turn :- true(dealing)`
- line 101: `nature_turn :- true(revealing)`
- line 102: `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)`
- line 103: `legal(random,reveal(C)) :- true(revealing) & card(C) & ~dealt(C)`
- line 104: `legal(random,noop) :- ~nature_turn`
- line 121: `revealed_now :- does(random,reveal(C))` (also in G10)
- line 124: `sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)` (also in G03, G04, G06)
- line 125: `sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)` (also in G03, G04, G06)
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 132: `next(holds(player1,C)) :- does(random,deal(C,D))` (also in G06)
- line 133: `next(holds(player2,D)) :- does(random,deal(C,D))` (also in G06)
- line 135: `next(board(C)) :- does(random,reveal(C))` (also in G06)
- line 138: `next(round(1)) :- does(random,deal(C,D))` (also in G07, G10, G14)
- line 139: `next(round(2)) :- does(random,reveal(C))` (also in G07, G10, G14)
- line 144: `next(control(player1)) :- does(random,deal(C,D))` (also in G08, G09, G19, G20)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G08, G09, G19, G20)
- line 148: `next(bets(0)) :- does(random,deal(C,D))` (also in G07, G09, G14)
- line 149: `next(bets(0)) :- does(random,reveal(C))` (also in G07, G09, G14)

### lgref G06 (12 statements)

- line 105: `dealt(C) :- true(holds(P,C))`
- line 124: `sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)` (also in G03, G04, G05)
- line 125: `sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)` (also in G03, G04, G05)
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 128: `sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown`
- line 132: `next(holds(player1,C)) :- does(random,deal(C,D))` (also in G05)
- line 133: `next(holds(player2,D)) :- does(random,deal(C,D))` (also in G05)
- line 134: `next(holds(P,C)) :- true(holds(P,C))`
- line 135: `next(board(C)) :- does(random,reveal(C))` (also in G05)
- line 136: `next(board(C)) :- true(board(C))`
- line 169: `paired(P) :- true(holds(P,C)) & rank(C,R) & true(board(B)) & rank(B,R)` (also in G03)
- line 171: `beats(P) :- opponent(P,Q) & ~paired(P) & ~paired(Q) & true(holds(P,C)) & rank(C,R) & true(holds(Q,D)) & rank(D,S) & higher(R,S)`

### lgref G07 (9 statements)

- line 97: `init(stake(1))`
- line 138: `next(round(1)) :- does(random,deal(C,D))` (also in G05, G10, G14)
- line 139: `next(round(2)) :- does(random,reveal(C))` (also in G05, G10, G14)
- line 148: `next(bets(0)) :- does(random,deal(C,D))` (also in G05, G09, G14)
- line 149: `next(bets(0)) :- does(random,reveal(C))` (also in G05, G09, G14)
- line 157: `next(stake(S)) :- true(stake(S)) & ~round_ends`
- line 158: `next(stake(S)) :- true(stake(S)) & does(player2,check)`
- line 159: `next(stake(X)) :- true(stake(S)) & does(P,call) & true(round(R)) & true(bets(K)) & amount(R,S,K,X)`
- line 161: `next(showdown(S)) :- true(round(2)) & does(player2,check) & true(stake(S))` (also in G10)

### lgref G08 (11 statements)

- line 109: `legal(P,check) :- true(control(P)) & ~facing(P)` (also in G19)
- line 110: `legal(P,bet) :- true(control(P)) & ~facing(P)`
- line 111: `legal(P,call) :- true(control(P)) & facing(P)` (also in G20)
- line 112: `legal(P,fold) :- true(control(P)) & facing(P)`
- line 113: `legal(P,raise) :- true(control(P)) & facing(P) & true(bets(1))` (also in G09)
- line 120: `folding :- does(P,fold)`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G10, G11, G14, G15, G16, G17, G18, G21)
- line 144: `next(control(player1)) :- does(random,deal(C,D))` (also in G05, G09, G19, G20)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G09, G19, G20)
- line 146: `next(control(Q)) :- true(control(P)) & opponent(P,Q) & ~round_ends & ~folding`
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G15)

### lgref G09 (9 statements)

- line 113: `legal(P,raise) :- true(control(P)) & facing(P) & true(bets(1))` (also in G08)
- line 144: `next(control(player1)) :- does(random,deal(C,D))` (also in G05, G08, G19, G20)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G08, G19, G20)
- line 148: `next(bets(0)) :- does(random,deal(C,D))` (also in G05, G07, G14)
- line 149: `next(bets(0)) :- does(random,reveal(C))` (also in G05, G07, G14)
- line 150: `next(bets(0)) :- does(player1,check) & true(bets(0))`
- line 151: `next(bets(1)) :- does(P,bet)`
- line 152: `next(bets(2)) :- does(P,raise)`
- line 155: `next(bet_by(P)) :- does(P,raise)` (also in G15)

### lgref G10 (8 statements)

- line 121: `revealed_now :- does(random,reveal(C))` (also in G05)
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G11, G14, G15, G16, G17, G18, G21)
- line 129: `to_showdown :- true(round(2)) & round_ends`
- line 138: `next(round(1)) :- does(random,deal(C,D))` (also in G05, G07, G14)
- line 139: `next(round(2)) :- does(random,reveal(C))` (also in G05, G07, G14)
- line 140: `next(round(R)) :- true(round(R)) & ~revealed_now`
- line 142: `next(revealing) :- true(round(1)) & round_ends`
- line 161: `next(showdown(S)) :- true(round(2)) & does(player2,check) & true(stake(S))` (also in G07)

### lgref G11 (6 statements)

- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G14, G15, G16, G17, G18, G21)
- line 166: `terminal :- true(showdown(X))`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)`
- line 175: `goal(P,L) :- opponent(P,Q) & beats(Q) & true(showdown(X)) & payoff(X,W,L)`
- line 176: `goal(P,50) :- player(P) & true(showdown(X)) & split`
- line 179: `goal(random,0)`

### lgref G12 (3 statements)

- line 40: `role(player1)`
- line 41: `role(player2)`
- line 42: `role(random)`

### lgref G13 (3 statements)

- line 60: `higher(q,j)`
- line 61: `higher(k,j)`
- line 62: `higher(k,q)`

### lgref G14 (8 statements)

- line 84: `succ(0,1)`
- line 85: `succ(1,2)`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G15, G16, G17, G18, G21)
- line 138: `next(round(1)) :- does(random,deal(C,D))` (also in G05, G07, G10)
- line 139: `next(round(2)) :- does(random,reveal(C))` (also in G05, G07, G10)
- line 148: `next(bets(0)) :- does(random,deal(C,D))` (also in G05, G07, G09)
- line 149: `next(bets(0)) :- does(random,reveal(C))` (also in G05, G07, G09)
- line 163: `next(folded(P,X)) :- does(P,fold) & true(round(R)) & true(stake(S)) & true(bets(K)) & succ(J,K) & amount(R,S,J,X)`

### lgref G15 (4 statements)

- line 108: `facing(P) :- opponent(P,Q) & true(bet_by(Q))`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G16, G17, G18, G21)
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G08)
- line 155: `next(bet_by(P)) :- does(P,raise)` (also in G09)

### lgref G16 (4 statements)

- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G17, G18, G21)
- line 167: `terminal :- true(folded(P,X))`
- line 177: `goal(P,W) :- opponent(P,Q) & true(folded(Q,X)) & payoff(X,W,L)` (also in G01)
- line 178: `goal(P,L) :- true(folded(P,X)) & payoff(X,W,L)` (also in G01)

### lgref G17 (3 statements)

- line 43: `player(player1)`
- line 44: `player(player2)`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G18, G21)

### lgref G18 (3 statements)

- line 45: `opponent(player1,player2)`
- line 46: `opponent(player2,player1)`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G21)

### lgref G19 (4 statements)

- line 109: `legal(P,check) :- true(control(P)) & ~facing(P)` (also in G08)
- line 119: `round_ends :- does(player2,check)`
- line 144: `next(control(player1)) :- does(random,deal(C,D))` (also in G05, G08, G09, G20)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G08, G09, G20)

### lgref G20 (4 statements)

- line 111: `legal(P,call) :- true(control(P)) & facing(P)` (also in G08)
- line 118: `round_ends :- does(P,call)`
- line 144: `next(control(player1)) :- does(random,deal(C,D))` (also in G05, G08, G09, G19)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G08, G09, G19)

### lgref G21 (3 statements)

- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18)
- line 170: `beats(P) :- opponent(P,Q) & paired(P) & ~paired(Q)`
- line 172: `split :- ~beats(player1) & ~beats(player2)`

### lgref: statements in no group

- line 114: `legal(P,noop) :- player(P) & ~true(control(P))`
- line 162: `next(showdown(X)) :- true(round(2)) & does(P,call) & true(stake(S)) & true(bets(K)) & amount(2,S,K,X)`


## random_matched by group

### random_matched G00 (12 statements)

- line 42: `role(random)`
- line 54: `rank(j1,j)`
- line 67: `action(raise)`
- line 94: `payoff(13,89,11)`
- line 96: `init(dealing)`
- line 134: `next(holds(P,C)) :- true(holds(P,C))`
- line 140: `next(round(R)) :- true(round(R)) & ~revealed_now`
- line 146: `next(control(Q)) :- true(control(P)) & opponent(P,Q) & ~round_ends & ~folding`
- line 148: `next(bets(0)) :- does(random,deal(C,D))`
- line 150: `next(bets(0)) :- does(player1,check) & true(bets(0))`
- line 167: `terminal :- true(folded(P,X))`
- line 176: `goal(P,50) :- player(P) & true(showdown(X)) & split`

### random_matched G01 (10 statements)

- line 46: `opponent(player2,player1)`
- line 73: `amount(1,1,1,3)`
- line 76: `amount(2,1,1,5)`
- line 97: `init(stake(1))` (also in G16)
- line 109: `legal(P,check) :- true(control(P)) & ~facing(P)`
- line 110: `legal(P,bet) :- true(control(P)) & ~facing(P)`
- line 151: `next(bets(1)) :- does(P,bet)`
- line 163: `next(folded(P,X)) :- does(P,fold) & true(round(R)) & true(stake(S)) & true(bets(K)) & succ(J,K) & amount(R,S,J,X)` (also in G16)
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 175: `goal(P,L) :- opponent(P,Q) & beats(Q) & true(showdown(X)) & payoff(X,W,L)`

### random_matched G02 (6 statements)

- line 74: `amount(1,1,2,5)`
- line 126: `sees(P,board(R)) :- player(P) & does(random,reveal(C)) & rank(C,R)`
- line 142: `next(revealing) :- true(round(1)) & round_ends`
- line 155: `next(bet_by(P)) :- does(P,raise)`
- line 159: `next(stake(X)) :- true(stake(S)) & does(P,call) & true(round(R)) & true(bets(K)) & amount(R,S,K,X)`
- line 171: `beats(P) :- opponent(P,Q) & ~paired(P) & ~paired(Q) & true(holds(P,C)) & rank(C,R) & true(holds(Q,D)) & rank(D,S) & higher(R,S)`

### random_matched G03 (10 statements)

- line 41: `role(player2)` (also in G04, G05, G06)
- line 48: `card(j1)` (also in G04, G05, G06)
- line 49: `card(j2)`
- line 57: `rank(q2,q)`
- line 75: `amount(2,1,0,1)`
- line 100: `nature_turn :- true(dealing)`
- line 161: `next(showdown(S)) :- true(round(2)) & does(player2,check) & true(stake(S))`
- line 162: `next(showdown(X)) :- true(round(2)) & does(P,call) & true(stake(S)) & true(bets(K)) & amount(2,S,K,X)`
- line 169: `paired(P) :- true(holds(P,C)) & rank(C,R) & true(board(B)) & rank(B,R)` (also in G06)
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)

### random_matched G04 (9 statements)

- line 41: `role(player2)` (also in G03, G05, G06)
- line 48: `card(j1)` (also in G03, G05, G06)
- line 51: `card(q2)`
- line 82: `amount(2,5,1,9)`
- line 90: `payoff(5,65,35)`
- line 121: `revealed_now :- does(random,reveal(C))`
- line 152: `next(bets(2)) :- does(P,raise)`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 179: `goal(random,0)`

### random_matched G05 (19 statements)

- line 41: `role(player2)` (also in G03, G04, G06)
- line 44: `player(player2)`
- line 48: `card(j1)` (also in G03, G04, G06)
- line 50: `card(q1)` (also in G08, G09, G19, G20)
- line 52: `card(k1)` (also in G10)
- line 55: `rank(j2,j)`
- line 59: `rank(k2,k)` (also in G07, G09, G14)
- line 68: `action(fold)` (also in G06)
- line 79: `amount(2,3,1,7)`
- line 105: `dealt(C) :- true(holds(P,C))` (also in G06)
- line 111: `legal(P,call) :- true(control(P)) & facing(P)`
- line 127: `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)` (also in G06)
- line 128: `sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown` (also in G07, G10, G14)
- line 136: `next(board(C)) :- true(board(C))` (also in G07, G09, G14)
- line 138: `next(round(1)) :- does(random,deal(C,D))`
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G07, G10, G14)
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G08, G09, G19, G20)
- line 157: `next(stake(S)) :- true(stake(S)) & ~round_ends`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G06, G08, G10, G11, G14, G15, G16, G17, G18, G21)

### random_matched G06 (12 statements)

- line 41: `role(player2)` (also in G03, G04, G05)
- line 48: `card(j1)` (also in G03, G04, G05)
- line 68: `action(fold)` (also in G05)
- line 85: `succ(1,2)`
- line 105: `dealt(C) :- true(holds(P,C))` (also in G05)
- line 108: `facing(P) :- opponent(P,Q) & true(bet_by(Q))`
- line 114: `legal(P,noop) :- player(P) & ~true(control(P))`
- line 127: `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)` (also in G05)
- line 129: `to_showdown :- true(round(2)) & round_ends`
- line 169: `paired(P) :- true(holds(P,C)) & rank(C,R) & true(board(B)) & rank(B,R)` (also in G03)
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G08, G10, G11, G14, G15, G16, G17, G18, G21)
- line 177: `goal(P,W) :- opponent(P,Q) & true(folded(Q,X)) & payoff(X,W,L)`

### random_matched G07 (9 statements)

- line 58: `rank(k1,k)`
- line 59: `rank(k2,k)` (also in G05, G09, G14)
- line 72: `amount(1,1,0,1)` (also in G10)
- line 81: `amount(2,5,0,5)`
- line 119: `round_ends :- does(player2,check)`
- line 128: `sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown` (also in G05, G10, G14)
- line 136: `next(board(C)) :- true(board(C))` (also in G05, G09, G14)
- line 144: `next(control(player1)) :- does(random,deal(C,D))`
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G10, G14)

### random_matched G08 (11 statements)

- line 50: `card(q1)` (also in G05, G09, G19, G20)
- line 53: `card(k2)` (also in G15)
- line 56: `rank(q1,q)` (also in G20)
- line 61: `higher(k,j)` (also in G19)
- line 62: `higher(k,q)`
- line 84: `succ(0,1)`
- line 93: `payoff(11,83,17)`
- line 135: `next(board(C)) :- does(random,reveal(C))` (also in G09)
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G05, G09, G19, G20)
- line 170: `beats(P) :- opponent(P,Q) & paired(P) & ~paired(Q)`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G10, G11, G14, G15, G16, G17, G18, G21)

### random_matched G09 (9 statements)

- line 50: `card(q1)` (also in G05, G08, G19, G20)
- line 59: `rank(k2,k)` (also in G05, G07, G14)
- line 77: `amount(2,1,2,9)`
- line 125: `sees(player2,mycard(R)) :- does(random,deal(C,D)) & rank(D,R)`
- line 135: `next(board(C)) :- does(random,reveal(C))` (also in G08)
- line 136: `next(board(C)) :- true(board(C))` (also in G05, G07, G14)
- line 139: `next(round(2)) :- does(random,reveal(C))`
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G05, G08, G19, G20)
- line 158: `next(stake(S)) :- true(stake(S)) & does(player2,check)` (also in G15)

### random_matched G10 (8 statements)

- line 52: `card(k1)` (also in G05)
- line 72: `amount(1,1,0,1)` (also in G07)
- line 89: `payoff(3,59,41)`
- line 112: `legal(P,fold) :- true(control(P)) & facing(P)`
- line 128: `sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown` (also in G05, G07, G14)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G07, G14)
- line 166: `terminal :- true(showdown(X))`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G11, G14, G15, G16, G17, G18, G21)

### random_matched G11 (6 statements)

- line 45: `opponent(player1,player2)`
- line 78: `amount(2,3,0,3)`
- line 103: `legal(random,reveal(C)) :- true(revealing) & card(C) & ~dealt(C)`
- line 113: `legal(P,raise) :- true(control(P)) & facing(P) & true(bets(1))`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G14, G15, G16, G17, G18, G21)
- line 178: `goal(P,L) :- true(folded(P,X)) & payoff(X,W,L)`

### random_matched G12 (3 statements)

- line 43: `player(player1)`
- line 65: `action(bet)`
- line 172: `split :- ~beats(player1) & ~beats(player2)`

### random_matched G13 (3 statements)

- line 64: `action(check)`
- line 88: `payoff(1,53,47)`
- line 124: `sees(player1,mycard(R)) :- does(random,deal(C,D)) & rank(C,R)`

### random_matched G14 (8 statements)

- line 59: `rank(k2,k)` (also in G05, G07, G09)
- line 60: `higher(q,j)`
- line 80: `amount(2,3,2,11)`
- line 92: `payoff(9,77,23)`
- line 128: `sees(P,shown(R)) :- opponent(P,Q) & true(holds(Q,C)) & rank(C,R) & to_showdown` (also in G05, G07, G10)
- line 136: `next(board(C)) :- true(board(C))` (also in G05, G07, G09)
- line 145: `next(control(player1)) :- does(random,reveal(C))` (also in G05, G07, G10)
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G15, G16, G17, G18, G21)

### random_matched G15 (4 statements)

- line 53: `card(k2)` (also in G08)
- line 149: `next(bets(0)) :- does(random,reveal(C))`
- line 158: `next(stake(S)) :- true(stake(S)) & does(player2,check)` (also in G09)
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G16, G17, G18, G21)

### random_matched G16 (4 statements)

- line 83: `amount(2,5,2,13)`
- line 97: `init(stake(1))` (also in G01)
- line 163: `next(folded(P,X)) :- does(P,fold) & true(round(R)) & true(stake(S)) & true(bets(K)) & succ(J,K) & amount(R,S,J,X)` (also in G01)
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G17, G18, G21)

### random_matched G17 (3 statements)

- line 104: `legal(random,noop) :- ~nature_turn`
- line 132: `next(holds(player1,C)) :- does(random,deal(C,D))`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G18, G21)

### random_matched G18 (3 statements)

- line 66: `action(call)`
- line 91: `payoff(7,71,29)`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G21)

### random_matched G19 (4 statements)

- line 40: `role(player1)`
- line 50: `card(q1)` (also in G05, G08, G09, G20)
- line 61: `higher(k,j)` (also in G08)
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G05, G08, G09, G20)

### random_matched G20 (4 statements)

- line 50: `card(q1)` (also in G05, G08, G09, G19)
- line 56: `rank(q1,q)` (also in G08)
- line 118: `round_ends :- does(P,call)`
- line 154: `next(bet_by(P)) :- does(P,bet)` (also in G05, G08, G09, G19)

### random_matched G21 (3 statements)

- line 101: `nature_turn :- true(revealing)`
- line 120: `folding :- does(P,fold)`
- line 174: `goal(P,W) :- beats(P) & true(showdown(X)) & payoff(X,W,L)` (also in G01, G03, G04, G05, G06, G08, G10, G11, G14, G15, G16, G17, G18)

### random_matched: statements in no group

- line 102: `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)`
- line 133: `next(holds(player2,D)) :- does(random,deal(C,D))`

