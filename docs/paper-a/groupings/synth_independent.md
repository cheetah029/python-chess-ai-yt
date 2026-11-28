# synth_independent -- groupings

File: `lgref/bench/games/synth_independent.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 0 statements in no group
- **random_matched**: 8 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 17 | `role(red)` | G06 | G01 |
| 18 | `role(blue)` | G06 | G03 |
| 21 | `plus(0,1,1)` | G01 | G01, G02 |
| 22 | `plus(1,1,2)` | G01, G02 | G01, G07 |
| 23 | `plus(2,1,3)` | G01, G02 | G04 |
| 24 | `plus(3,1,4)` | G01 | G01 |
| 25 | `plus(4,1,5)` | G01 | G05 |
| 26 | `plus(5,1,6)` | G01 | G06 |
| 27 | `plus(0,2,2)` | G01, G02 | G00, G04 |
| 28 | `plus(1,2,3)` | G01, G02 | G00 |
| 29 | `plus(2,2,4)` | G01, G02 | G01, G02 |
| 30 | `plus(3,2,5)` | G01, G02 | G05 |
| 31 | `plus(4,2,6)` | G01, G02 | G00, G04 |
| 32 | `opponent(red,blue)` | G00 | G01, G02 |
| 33 | `opponent(blue,red)` | G00 | G01, G02 |
| 36 | `legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)` | G01, G07 | G00 |
| 37 | `next(tally(M)) :- does(P,add(1)) & true(tally(N)) & plus(N,1,M)` | G07 | G00 |
| 40 | `legal(P,add(2)) :- true(control(P)) & true(tally(N)) & plus(N,2,M) & true(token(P))` | G03 | G00 |
| 41 | `next(tally(M)) :- does(P,add(2)) & true(tally(N)) & plus(N,2,M)` | G04 | G05 |
| 42 | `next(token(P)) :- true(token(P)) & ~does(P,add(2))` | G03 | G01, G02 |
| 45 | `legal(P,light) :- true(control(P)) & ~true(lit(P))` | G05 | G06 |
| 46 | `next(lit(P)) :- does(P,light)` | G05 | G07 |
| 47 | `next(lit(P)) :- true(lit(P))` | G05 | G01 |
| 48 | `next(tally(N)) :- true(tally(N)) & does(P,light)` | G00, G04 | G01, G02 |
| 51 | `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` | G00 | G00 |
| 52 | `next(control(Q)) :- true(control(P)) & opponent(P,Q)` | G00 | G00 |
| 55 | `terminal :- true(tally(6))` | G00, G04 | G03 |
| 56 | `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))` | G00 | G00, G04 |
| 57 | `goal(P,0) :- true(tally(6)) & true(control(P))` | G00 | G03 |
| 59 | `init(tally(0))` | G00, G04 | G01, G02 |
| 60 | `init(token(red))` | G03 | G01 |
| 61 | `init(token(blue))` | G03 | G00 |
| 62 | `init(control(red))` | G00 | G03 |

## lgref by group

### lgref G00 (10 statements)

- line 32: `opponent(red,blue)`
- line 33: `opponent(blue,red)`
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G04)
- line 51: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)`
- line 52: `next(control(Q)) :- true(control(P)) & opponent(P,Q)`
- line 55: `terminal :- true(tally(6))` (also in G04)
- line 56: `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))`
- line 57: `goal(P,0) :- true(tally(6)) & true(control(P))`
- line 59: `init(tally(0))` (also in G04)
- line 62: `init(control(red))`

### lgref G01 (12 statements)

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
- line 36: `legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)` (also in G07)

### lgref G02 (7 statements)

- line 22: `plus(1,1,2)` (also in G01)
- line 23: `plus(2,1,3)` (also in G01)
- line 27: `plus(0,2,2)` (also in G01)
- line 28: `plus(1,2,3)` (also in G01)
- line 29: `plus(2,2,4)` (also in G01)
- line 30: `plus(3,2,5)` (also in G01)
- line 31: `plus(4,2,6)` (also in G01)

### lgref G03 (4 statements)

- line 40: `legal(P,add(2)) :- true(control(P)) & true(tally(N)) & plus(N,2,M) & true(token(P))`
- line 42: `next(token(P)) :- true(token(P)) & ~does(P,add(2))`
- line 60: `init(token(red))`
- line 61: `init(token(blue))`

### lgref G04 (4 statements)

- line 41: `next(tally(M)) :- does(P,add(2)) & true(tally(N)) & plus(N,2,M)`
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G00)
- line 55: `terminal :- true(tally(6))` (also in G00)
- line 59: `init(tally(0))` (also in G00)

### lgref G05 (3 statements)

- line 45: `legal(P,light) :- true(control(P)) & ~true(lit(P))`
- line 46: `next(lit(P)) :- does(P,light)`
- line 47: `next(lit(P)) :- true(lit(P))`

### lgref G06 (2 statements)

- line 17: `role(red)`
- line 18: `role(blue)`

### lgref G07 (2 statements)

- line 36: `legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)` (also in G01)
- line 37: `next(tally(M)) :- does(P,add(1)) & true(tally(N)) & plus(N,1,M)`


## random_matched by group

### random_matched G00 (10 statements)

- line 27: `plus(0,2,2)` (also in G04)
- line 28: `plus(1,2,3)`
- line 31: `plus(4,2,6)` (also in G04)
- line 36: `legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)`
- line 37: `next(tally(M)) :- does(P,add(1)) & true(tally(N)) & plus(N,1,M)`
- line 40: `legal(P,add(2)) :- true(control(P)) & true(tally(N)) & plus(N,2,M) & true(token(P))`
- line 51: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)`
- line 52: `next(control(Q)) :- true(control(P)) & opponent(P,Q)`
- line 56: `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))` (also in G04)
- line 61: `init(token(blue))`

### random_matched G01 (12 statements)

- line 17: `role(red)`
- line 21: `plus(0,1,1)` (also in G02)
- line 22: `plus(1,1,2)` (also in G07)
- line 24: `plus(3,1,4)`
- line 29: `plus(2,2,4)` (also in G02)
- line 32: `opponent(red,blue)` (also in G02)
- line 33: `opponent(blue,red)` (also in G02)
- line 42: `next(token(P)) :- true(token(P)) & ~does(P,add(2))` (also in G02)
- line 47: `next(lit(P)) :- true(lit(P))`
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G02)
- line 59: `init(tally(0))` (also in G02)
- line 60: `init(token(red))`

### random_matched G02 (7 statements)

- line 21: `plus(0,1,1)` (also in G01)
- line 29: `plus(2,2,4)` (also in G01)
- line 32: `opponent(red,blue)` (also in G01)
- line 33: `opponent(blue,red)` (also in G01)
- line 42: `next(token(P)) :- true(token(P)) & ~does(P,add(2))` (also in G01)
- line 48: `next(tally(N)) :- true(tally(N)) & does(P,light)` (also in G01)
- line 59: `init(tally(0))` (also in G01)

### random_matched G03 (4 statements)

- line 18: `role(blue)`
- line 55: `terminal :- true(tally(6))`
- line 57: `goal(P,0) :- true(tally(6)) & true(control(P))`
- line 62: `init(control(red))`

### random_matched G04 (4 statements)

- line 23: `plus(2,1,3)`
- line 27: `plus(0,2,2)` (also in G00)
- line 31: `plus(4,2,6)` (also in G00)
- line 56: `goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))` (also in G00)

### random_matched G05 (3 statements)

- line 25: `plus(4,1,5)`
- line 30: `plus(3,2,5)`
- line 41: `next(tally(M)) :- does(P,add(2)) & true(tally(N)) & plus(N,2,M)`

### random_matched G06 (2 statements)

- line 26: `plus(5,1,6)`
- line 45: `legal(P,light) :- true(control(P)) & ~true(lit(P))`

### random_matched G07 (2 statements)

- line 22: `plus(1,1,2)` (also in G01)
- line 46: `next(lit(P)) :- does(P,light)`

