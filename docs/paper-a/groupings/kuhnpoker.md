# kuhnpoker -- groupings

File: `lgref/identify/testgames/kuhnpoker.gdl`. Line numbers are lines of that file.

- **lgref**: 15 groups, 0 statements in no group
- **random_matched**: 15 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 31 | `role(player1)` | G04 | G08 |
| 32 | `role(player2)` | G04 | G07 |
| 33 | `role(random)` | G04 | G03 |
| 34 | `player(player1)` | G05 | G10 |
| 35 | `player(player2)` | G05 | G08 |
| 36 | `opponent(player1,player2)` | G06 | G06 |
| 37 | `opponent(player2,player1)` | G06 | G01, G10 |
| 38 | `card(j)` | G07 | G06 |
| 39 | `card(q)` | G07 | G06 |
| 40 | `card(k)` | G07 | G02 |
| 41 | `higher(q,j)` | G08 | G09 |
| 42 | `higher(k,j)` | G08 | G01, G02, G09 |
| 43 | `higher(k,q)` | G08 | G04 |
| 44 | `action(check)` | G00 | G12 |
| 45 | `action(bet)` | G00 | G00 |
| 46 | `action(call)` | G00 | G01, G02, G05 |
| 47 | `action(fold)` | G00 | G03, G14 |
| 48 | `init(dealing)` | G01 | G01, G02, G11 |
| 49 | `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)` | G01 | G01, G06 |
| 50 | `legal(random,noop) :- ~true(dealing)` | G01, G02 | G13, G14 |
| 51 | `legal(P,check) :- true(control(P)) & ~facing(P)` | G02 | G00 |
| 52 | `legal(P,bet) :- true(control(P)) & ~facing(P)` | G01, G02, G09 | G00, G01, G10 |
| 53 | `legal(P,call) :- true(control(P)) & facing(P)` | G02 | G11 |
| 54 | `legal(P,fold) :- true(control(P)) & facing(P)` | G01, G02, G11 | G00 |
| 55 | `legal(P,noop) :- player(P) & ~true(control(P))` | G01, G02, G05 | G03 |
| 56 | `facing(P) :- opponent(P,Q) & true(bet_by(Q))` | G09 | G10 |
| 57 | `sees(player1,mycard(C)) :- does(random,deal(C,D))` | G00, G01, G10 | G03, G14 |
| 58 | `sees(player2,mycard(D)) :- does(random,deal(C,D))` | G00, G01, G10 | G04 |
| 59 | `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)` | G00 | G01 |
| 60 | `sees(P,shown(C)) :- opponent(P,Q) & true(holds(Q,C)) & to_showdown` | G10 | G02 |
| 61 | `to_showdown :- does(player2,check)` | G02 | G13 |
| 62 | `to_showdown :- does(P,call)` | G02 | G03 |
| 63 | `next(holds(player1,C)) :- does(random,deal(C,D))` | G01, G10 | G03 |
| 64 | `next(holds(player2,D)) :- does(random,deal(C,D))` | G01, G10 | G01 |
| 65 | `next(holds(P,C)) :- true(holds(P,C))` | G10 | G00 |
| 66 | `next(control(player1)) :- true(dealing)` | G01, G06 | G07 |
| 67 | `next(control(Q)) :- true(control(P)) & opponent(P,Q)` | G06 | G10 |
| 68 | `next(bet_by(P)) :- does(P,bet)` | G09 | G12 |
| 69 | `next(showdown(1)) :- does(player2,check)` | G12 | G02 |
| 70 | `next(showdown(2)) :- does(P,call)` | G12 | G08 |
| 71 | `next(folded(P)) :- does(P,fold)` | G11 | G05 |
| 72 | `terminal :- true(showdown(S))` | G13 | G05 |
| 73 | `terminal :- true(folded(P))` | G13, G14 | G04 |
| 74 | `best(P) :- opponent(P,Q) & true(holds(P,C)) & true(holds(Q,D)) & higher(C,D)` | G10 | G01, G02 |
| 75 | `goal(P,100) :- best(P) & true(showdown(2))` | G03 | G02 |
| 76 | `goal(P,75) :- best(P) & true(showdown(1))` | G03 | G09 |
| 77 | `goal(P,75) :- opponent(P,Q) & true(folded(Q))` | G03, G14 | G01, G10 |
| 78 | `goal(P,25) :- opponent(P,Q) & best(Q) & true(showdown(1))` | G03 | G00, G01, G10 |
| 79 | `goal(P,25) :- true(folded(P))` | G03, G14 | G03 |
| 80 | `goal(P,0) :- opponent(P,Q) & best(Q) & true(showdown(2))` | G03 | G07 |
| 81 | `goal(random,0)` | G03 | G00 |

## lgref by group

### lgref G00 (7 statements)

- line 44: `action(check)`
- line 45: `action(bet)`
- line 46: `action(call)`
- line 47: `action(fold)`
- line 57: `sees(player1,mycard(C)) :- does(random,deal(C,D))` (also in G01, G10)
- line 58: `sees(player2,mycard(D)) :- does(random,deal(C,D))` (also in G01, G10)
- line 59: `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)`

### lgref G01 (11 statements)

- line 48: `init(dealing)`
- line 49: `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)`
- line 50: `legal(random,noop) :- ~true(dealing)` (also in G02)
- line 52: `legal(P,bet) :- true(control(P)) & ~facing(P)` (also in G02, G09)
- line 54: `legal(P,fold) :- true(control(P)) & facing(P)` (also in G02, G11)
- line 55: `legal(P,noop) :- player(P) & ~true(control(P))` (also in G02, G05)
- line 57: `sees(player1,mycard(C)) :- does(random,deal(C,D))` (also in G00, G10)
- line 58: `sees(player2,mycard(D)) :- does(random,deal(C,D))` (also in G00, G10)
- line 63: `next(holds(player1,C)) :- does(random,deal(C,D))` (also in G10)
- line 64: `next(holds(player2,D)) :- does(random,deal(C,D))` (also in G10)
- line 66: `next(control(player1)) :- true(dealing)` (also in G06)

### lgref G02 (8 statements)

- line 50: `legal(random,noop) :- ~true(dealing)` (also in G01)
- line 51: `legal(P,check) :- true(control(P)) & ~facing(P)`
- line 52: `legal(P,bet) :- true(control(P)) & ~facing(P)` (also in G01, G09)
- line 53: `legal(P,call) :- true(control(P)) & facing(P)`
- line 54: `legal(P,fold) :- true(control(P)) & facing(P)` (also in G01, G11)
- line 55: `legal(P,noop) :- player(P) & ~true(control(P))` (also in G01, G05)
- line 61: `to_showdown :- does(player2,check)`
- line 62: `to_showdown :- does(P,call)`

### lgref G03 (7 statements)

- line 75: `goal(P,100) :- best(P) & true(showdown(2))`
- line 76: `goal(P,75) :- best(P) & true(showdown(1))`
- line 77: `goal(P,75) :- opponent(P,Q) & true(folded(Q))` (also in G14)
- line 78: `goal(P,25) :- opponent(P,Q) & best(Q) & true(showdown(1))`
- line 79: `goal(P,25) :- true(folded(P))` (also in G14)
- line 80: `goal(P,0) :- opponent(P,Q) & best(Q) & true(showdown(2))`
- line 81: `goal(random,0)`

### lgref G04 (3 statements)

- line 31: `role(player1)`
- line 32: `role(player2)`
- line 33: `role(random)`

### lgref G05 (3 statements)

- line 34: `player(player1)`
- line 35: `player(player2)`
- line 55: `legal(P,noop) :- player(P) & ~true(control(P))` (also in G01, G02)

### lgref G06 (4 statements)

- line 36: `opponent(player1,player2)`
- line 37: `opponent(player2,player1)`
- line 66: `next(control(player1)) :- true(dealing)` (also in G01)
- line 67: `next(control(Q)) :- true(control(P)) & opponent(P,Q)`

### lgref G07 (3 statements)

- line 38: `card(j)`
- line 39: `card(q)`
- line 40: `card(k)`

### lgref G08 (3 statements)

- line 41: `higher(q,j)`
- line 42: `higher(k,j)`
- line 43: `higher(k,q)`

### lgref G09 (3 statements)

- line 52: `legal(P,bet) :- true(control(P)) & ~facing(P)` (also in G01, G02)
- line 56: `facing(P) :- opponent(P,Q) & true(bet_by(Q))`
- line 68: `next(bet_by(P)) :- does(P,bet)`

### lgref G10 (7 statements)

- line 57: `sees(player1,mycard(C)) :- does(random,deal(C,D))` (also in G00, G01)
- line 58: `sees(player2,mycard(D)) :- does(random,deal(C,D))` (also in G00, G01)
- line 60: `sees(P,shown(C)) :- opponent(P,Q) & true(holds(Q,C)) & to_showdown`
- line 63: `next(holds(player1,C)) :- does(random,deal(C,D))` (also in G01)
- line 64: `next(holds(player2,D)) :- does(random,deal(C,D))` (also in G01)
- line 65: `next(holds(P,C)) :- true(holds(P,C))`
- line 74: `best(P) :- opponent(P,Q) & true(holds(P,C)) & true(holds(Q,D)) & higher(C,D)`

### lgref G11 (2 statements)

- line 54: `legal(P,fold) :- true(control(P)) & facing(P)` (also in G01, G02)
- line 71: `next(folded(P)) :- does(P,fold)`

### lgref G12 (2 statements)

- line 69: `next(showdown(1)) :- does(player2,check)`
- line 70: `next(showdown(2)) :- does(P,call)`

### lgref G13 (2 statements)

- line 72: `terminal :- true(showdown(S))`
- line 73: `terminal :- true(folded(P))` (also in G14)

### lgref G14 (3 statements)

- line 73: `terminal :- true(folded(P))` (also in G13)
- line 77: `goal(P,75) :- opponent(P,Q) & true(folded(Q))` (also in G03)
- line 79: `goal(P,25) :- true(folded(P))` (also in G03)


## random_matched by group

### random_matched G00 (7 statements)

- line 45: `action(bet)`
- line 51: `legal(P,check) :- true(control(P)) & ~facing(P)`
- line 52: `legal(P,bet) :- true(control(P)) & ~facing(P)` (also in G01, G10)
- line 54: `legal(P,fold) :- true(control(P)) & facing(P)`
- line 65: `next(holds(P,C)) :- true(holds(P,C))`
- line 78: `goal(P,25) :- opponent(P,Q) & best(Q) & true(showdown(1))` (also in G01, G10)
- line 81: `goal(random,0)`

### random_matched G01 (11 statements)

- line 37: `opponent(player2,player1)` (also in G10)
- line 42: `higher(k,j)` (also in G02, G09)
- line 46: `action(call)` (also in G02, G05)
- line 48: `init(dealing)` (also in G02, G11)
- line 49: `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)` (also in G06)
- line 52: `legal(P,bet) :- true(control(P)) & ~facing(P)` (also in G00, G10)
- line 59: `sees(P,opponent_did(M)) :- opponent(P,Q) & does(Q,M) & action(M)`
- line 64: `next(holds(player2,D)) :- does(random,deal(C,D))`
- line 74: `best(P) :- opponent(P,Q) & true(holds(P,C)) & true(holds(Q,D)) & higher(C,D)` (also in G02)
- line 77: `goal(P,75) :- opponent(P,Q) & true(folded(Q))` (also in G10)
- line 78: `goal(P,25) :- opponent(P,Q) & best(Q) & true(showdown(1))` (also in G00, G10)

### random_matched G02 (8 statements)

- line 40: `card(k)`
- line 42: `higher(k,j)` (also in G01, G09)
- line 46: `action(call)` (also in G01, G05)
- line 48: `init(dealing)` (also in G01, G11)
- line 60: `sees(P,shown(C)) :- opponent(P,Q) & true(holds(Q,C)) & to_showdown`
- line 69: `next(showdown(1)) :- does(player2,check)`
- line 74: `best(P) :- opponent(P,Q) & true(holds(P,C)) & true(holds(Q,D)) & higher(C,D)` (also in G01)
- line 75: `goal(P,100) :- best(P) & true(showdown(2))`

### random_matched G03 (7 statements)

- line 33: `role(random)`
- line 47: `action(fold)` (also in G14)
- line 55: `legal(P,noop) :- player(P) & ~true(control(P))`
- line 57: `sees(player1,mycard(C)) :- does(random,deal(C,D))` (also in G14)
- line 62: `to_showdown :- does(P,call)`
- line 63: `next(holds(player1,C)) :- does(random,deal(C,D))`
- line 79: `goal(P,25) :- true(folded(P))`

### random_matched G04 (3 statements)

- line 43: `higher(k,q)`
- line 58: `sees(player2,mycard(D)) :- does(random,deal(C,D))`
- line 73: `terminal :- true(folded(P))`

### random_matched G05 (3 statements)

- line 46: `action(call)` (also in G01, G02)
- line 71: `next(folded(P)) :- does(P,fold)`
- line 72: `terminal :- true(showdown(S))`

### random_matched G06 (4 statements)

- line 36: `opponent(player1,player2)`
- line 38: `card(j)`
- line 39: `card(q)`
- line 49: `legal(random,deal(C,D)) :- true(dealing) & card(C) & card(D) & distinct(C,D)` (also in G01)

### random_matched G07 (3 statements)

- line 32: `role(player2)`
- line 66: `next(control(player1)) :- true(dealing)`
- line 80: `goal(P,0) :- opponent(P,Q) & best(Q) & true(showdown(2))`

### random_matched G08 (3 statements)

- line 31: `role(player1)`
- line 35: `player(player2)`
- line 70: `next(showdown(2)) :- does(P,call)`

### random_matched G09 (3 statements)

- line 41: `higher(q,j)`
- line 42: `higher(k,j)` (also in G01, G02)
- line 76: `goal(P,75) :- best(P) & true(showdown(1))`

### random_matched G10 (7 statements)

- line 34: `player(player1)`
- line 37: `opponent(player2,player1)` (also in G01)
- line 52: `legal(P,bet) :- true(control(P)) & ~facing(P)` (also in G00, G01)
- line 56: `facing(P) :- opponent(P,Q) & true(bet_by(Q))`
- line 67: `next(control(Q)) :- true(control(P)) & opponent(P,Q)`
- line 77: `goal(P,75) :- opponent(P,Q) & true(folded(Q))` (also in G01)
- line 78: `goal(P,25) :- opponent(P,Q) & best(Q) & true(showdown(1))` (also in G00, G01)

### random_matched G11 (2 statements)

- line 48: `init(dealing)` (also in G01, G02)
- line 53: `legal(P,call) :- true(control(P)) & facing(P)`

### random_matched G12 (2 statements)

- line 44: `action(check)`
- line 68: `next(bet_by(P)) :- does(P,bet)`

### random_matched G13 (2 statements)

- line 50: `legal(random,noop) :- ~true(dealing)` (also in G14)
- line 61: `to_showdown :- does(player2,check)`

### random_matched G14 (3 statements)

- line 47: `action(fold)` (also in G03)
- line 50: `legal(random,noop) :- ~true(dealing)` (also in G13)
- line 57: `sees(player1,mycard(C)) :- does(random,deal(C,D))` (also in G03)

