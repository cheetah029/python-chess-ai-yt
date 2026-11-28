# synth_shared -- groupings

File: `lgref/bench/games/synth_shared.gdl`. Line numbers are lines of that file.

- **lgref**: 6 groups, 0 statements in no group
- **random_matched**: 6 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 17 | `role(red)` | G05 | G01 |
| 18 | `role(blue)` | G05 | G03 |
| 21 | `plus(0,1,1)` | G01 | G01, G02 |
| 22 | `plus(1,1,2)` | G01, G02 | G01, G02 |
| 23 | `plus(2,1,3)` | G01, G02 | G03 |
| 24 | `plus(3,1,4)` | G01 | G01 |
| 25 | `plus(4,1,5)` | G01 | G00, G03, G04 |
| 26 | `plus(5,1,6)` | G01 | G05 |
| 27 | `plus(0,2,2)` | G01, G02 | G00 |
| 28 | `plus(1,2,3)` | G01, G02 | G00, G03 |
| 29 | `plus(2,2,4)` | G01, G02 | G01, G02 |
| 30 | `plus(3,2,5)` | G01, G02 | G04 |
| 31 | `plus(4,2,6)` | G01, G02 | G00 |
| 32 | `opponent(red,blue)` | G00 | G01, G02 |
| 33 | `opponent(blue,red)` | G00 | G01, G02 |
| 36 | `room(P,K,M) :- true(control(P)) & true(tally(N)) & plus(N,K,M)` | G01, G02 | G00 |
| 37 | `next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)` | G00, G01, G02, G03 | G00 |
| 39 | `legal(P,add(1)) :- room(P,1,M)` | G00, G03, G04 | G00 |
| 41 | `legal(P,add(2)) :- room(P,2,M) & true(token(P))` | G03 | G04 |
| 42 | `next(token(P)) :- true(token(P)) & ~does(P,add(2))` | G03 | G01, G02 |
| 45 | `legal(P,light) :- true(control(P)) & ~true(lit(P))` | G00, G03, G04 | G05 |
| 46 | `next(lit(P)) :- does(P,light)` | G04 | G00, G01, G02, G03 |
| 47 | `next(lit(P)) :- true(lit(P))` | G04 | G01 |
| 48 | `next(tally(N)) :- true(tally(N)) & does(P,light)` | G00, G04 | G01, G02 |
| 51 | `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` | G00, G03 | G00 |
| 52 | `next(control(Q)) :- true(control(P)) & opponent(P,Q)` | G00 | G00 |
| 55 | `terminal :- true(tally(6))` | G00 | G03 |
| 56 | `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))` | G00 | G00, G04 |
| 57 | `goal(P,0) :- true(tally(6)) & true(control(P))` | G00 | G03 |
| 59 | `init(tally(0))` | G00 | G01, G02 |
| 60 | `init(token(red))` | G03 | G01 |
| 61 | `init(token(blue))` | G03 | G00 |
| 62 | `init(control(red))` | G00 | G00, G03, G04 |

## lgref by group

### lgref G00 (13 statements)

- line 32: `opponent(red,blue)`
- line 33: `opponent(blue,red)`
- line 37: `next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)` (also in G01, G02, G03)
- line 39: `legal(P,add(1)) :- room(P,1,M)` (also in G03, G04)
- line 45: `legal(P,light) :- true(control(P)) & ~true(lit(P))` (also in G03, G04)
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G04)
- line 51: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` (also in G03)
- line 52: `next(control(Q)) :- true(control(P)) & opponent(P,Q)`
- line 55: `terminal :- true(tally(6))`
- line 56: `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))`
- line 57: `goal(P,0) :- true(tally(6)) & true(control(P))`
- line 59: `init(tally(0))`
- line 62: `init(control(red))`

### lgref G01 (13 statements)

- line 21: `plus(0,1,1)`
- line 22: `plus(1,1,2)` (also in G02)
- line 23: `plus(2,1,3)` (also in G02)
- line 24: `plus(3,1,4)`
- line 25: `plus(4,1,5)`
- line 26: `plus(5,1,6)`
- line 27: `plus(0,2,2)` (also in G02)
- line 28: `plus(1,2,3)` (also in G02)
- line 29: `plus(2,2,4)` (also in G02)
- line 30: `plus(3,2,5)` (also in G02)
- line 31: `plus(4,2,6)` (also in G02)
- line 36: `room(P,K,M) :- true(control(P)) & true(tally(N)) & plus(N,K,M)` (also in G02)
- line 37: `next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)` (also in G00, G02, G03)

### lgref G02 (9 statements)

- line 22: `plus(1,1,2)` (also in G01)
- line 23: `plus(2,1,3)` (also in G01)
- line 27: `plus(0,2,2)` (also in G01)
- line 28: `plus(1,2,3)` (also in G01)
- line 29: `plus(2,2,4)` (also in G01)
- line 30: `plus(3,2,5)` (also in G01)
- line 31: `plus(4,2,6)` (also in G01)
- line 36: `room(P,K,M) :- true(control(P)) & true(tally(N)) & plus(N,K,M)` (also in G01)
- line 37: `next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)` (also in G00, G01, G03)

### lgref G03 (8 statements)

- line 37: `next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)` (also in G00, G01, G02)
- line 39: `legal(P,add(1)) :- room(P,1,M)` (also in G00, G04)
- line 41: `legal(P,add(2)) :- room(P,2,M) & true(token(P))`
- line 42: `next(token(P)) :- true(token(P)) & ~does(P,add(2))`
- line 45: `legal(P,light) :- true(control(P)) & ~true(lit(P))` (also in G00, G04)
- line 51: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` (also in G00)
- line 60: `init(token(red))`
- line 61: `init(token(blue))`

### lgref G04 (5 statements)

- line 39: `legal(P,add(1)) :- room(P,1,M)` (also in G00, G03)
- line 45: `legal(P,light) :- true(control(P)) & ~true(lit(P))` (also in G00, G03)
- line 46: `next(lit(P)) :- does(P,light)`
- line 47: `next(lit(P)) :- true(lit(P))`
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G00)

### lgref G05 (2 statements)

- line 17: `role(red)`
- line 18: `role(blue)`


## random_matched by group

### random_matched G00 (13 statements)

- line 25: `plus(4,1,5)` (also in G03, G04)
- line 27: `plus(0,2,2)`
- line 28: `plus(1,2,3)` (also in G03)
- line 31: `plus(4,2,6)`
- line 36: `room(P,K,M) :- true(control(P)) & true(tally(N)) & plus(N,K,M)`
- line 37: `next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)`
- line 39: `legal(P,add(1)) :- room(P,1,M)`
- line 46: `next(lit(P)) :- does(P,light)` (also in G01, G02, G03)
- line 51: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)`
- line 52: `next(control(Q)) :- true(control(P)) & opponent(P,Q)`
- line 56: `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))` (also in G04)
- line 61: `init(token(blue))`
- line 62: `init(control(red))` (also in G03, G04)

### random_matched G01 (13 statements)

- line 17: `role(red)`
- line 21: `plus(0,1,1)` (also in G02)
- line 22: `plus(1,1,2)` (also in G02)
- line 24: `plus(3,1,4)`
- line 29: `plus(2,2,4)` (also in G02)
- line 32: `opponent(red,blue)` (also in G02)
- line 33: `opponent(blue,red)` (also in G02)
- line 42: `next(token(P)) :- true(token(P)) & ~does(P,add(2))` (also in G02)
- line 46: `next(lit(P)) :- does(P,light)` (also in G00, G02, G03)
- line 47: `next(lit(P)) :- true(lit(P))`
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G02)
- line 59: `init(tally(0))` (also in G02)
- line 60: `init(token(red))`

### random_matched G02 (9 statements)

- line 21: `plus(0,1,1)` (also in G01)
- line 22: `plus(1,1,2)` (also in G01)
- line 29: `plus(2,2,4)` (also in G01)
- line 32: `opponent(red,blue)` (also in G01)
- line 33: `opponent(blue,red)` (also in G01)
- line 42: `next(token(P)) :- true(token(P)) & ~does(P,add(2))` (also in G01)
- line 46: `next(lit(P)) :- does(P,light)` (also in G00, G01, G03)
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G01)
- line 59: `init(tally(0))` (also in G01)

### random_matched G03 (8 statements)

- line 18: `role(blue)`
- line 23: `plus(2,1,3)`
- line 25: `plus(4,1,5)` (also in G00, G04)
- line 28: `plus(1,2,3)` (also in G00)
- line 46: `next(lit(P)) :- does(P,light)` (also in G00, G01, G02)
- line 55: `terminal :- true(tally(6))`
- line 57: `goal(P,0) :- true(tally(6)) & true(control(P))`
- line 62: `init(control(red))` (also in G00, G04)

### random_matched G04 (5 statements)

- line 25: `plus(4,1,5)` (also in G00, G03)
- line 30: `plus(3,2,5)`
- line 41: `legal(P,add(2)) :- room(P,2,M) & true(token(P))`
- line 56: `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))` (also in G00)
- line 62: `init(control(red))` (also in G00, G03)

### random_matched G05 (2 statements)

- line 26: `plus(5,1,6)`
- line 45: `legal(P,light) :- true(control(P)) & ~true(lit(P))`

