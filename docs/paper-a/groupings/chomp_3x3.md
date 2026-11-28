# chomp_3x3 -- groupings

File: `lgref/bench/games/chomp_3x3.gdl`. Line numbers are lines of that file.

- **lgref**: 5 groups, 0 statements in no group
- **random_matched**: 5 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 17 | `role(first)` | G04 | G02 |
| 18 | `role(second)` | G04 | G00 |
| 21 | `atmost(1,1)` | G02 | G03 |
| 22 | `atmost(1,2)` | G02 | G04 |
| 23 | `atmost(1,3)` | G02 | G01 |
| 24 | `atmost(2,2)` | G02 | G02 |
| 25 | `atmost(2,3)` | G02 | G01 |
| 26 | `atmost(3,3)` | G02 | G02 |
| 27 | `opponent(first,second)` | G01 | G00 |
| 28 | `opponent(second,first)` | G01 | G00 |
| 31 | `legal(P,bite(X,Y)) :- true(control(P)) & true(square(X,Y))` | G03 | G04 |
| 34 | `eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)` | G00, G02, G03 | G01 |
| 35 | `next(square(X,Y)) :- true(square(X,Y)) & ~eaten(X,Y)` | G00 | G00 |
| 38 | `legal(first,noop) :- true(control(second))` | G03 | G00 |
| 39 | `legal(second,noop) :- true(control(first))` | G03 | G01 |
| 40 | `next(control(first)) :- true(control(second))` | G01 | G00 |
| 41 | `next(control(second)) :- true(control(first))` | G01 | G00 |
| 44 | `poisoned :- ~true(square(1,1))` | G01 | G02 |
| 45 | `terminal :- poisoned` | G01 | G01 |
| 46 | `goal(P,100) :- poisoned & true(control(P))` | G01 | G02 |
| 47 | `goal(P,0) :- poisoned & true(control(Q)) & opponent(P,Q)` | G01 | G03 |
| 49 | `init(square(1,1))` | G00 | G03 |
| 50 | `init(square(1,2))` | G00 | G00 |
| 51 | `init(square(1,3))` | G00 | G01 |
| 52 | `init(square(2,1))` | G00 | G00 |
| 53 | `init(square(2,2))` | G00 | G01 |
| 54 | `init(square(2,3))` | G00 | G00, G02, G03 |
| 55 | `init(square(3,1))` | G00 | G01 |
| 56 | `init(square(3,2))` | G00 | G01 |
| 57 | `init(square(3,3))` | G00 | G00 |
| 58 | `init(control(first))` | G01 | G02 |

## lgref by group

### lgref G00 (11 statements)

- line 34: `eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)` (also in G02, G03)
- line 35: `next(square(X,Y)) :- true(square(X,Y)) & ~eaten(X,Y)`
- line 49: `init(square(1,1))`
- line 50: `init(square(1,2))`
- line 51: `init(square(1,3))`
- line 52: `init(square(2,1))`
- line 53: `init(square(2,2))`
- line 54: `init(square(2,3))`
- line 55: `init(square(3,1))`
- line 56: `init(square(3,2))`
- line 57: `init(square(3,3))`

### lgref G01 (9 statements)

- line 27: `opponent(first,second)`
- line 28: `opponent(second,first)`
- line 40: `next(control(first)) :- true(control(second))`
- line 41: `next(control(second)) :- true(control(first))`
- line 44: `poisoned :- ~true(square(1,1))`
- line 45: `terminal :- poisoned`
- line 46: `goal(P,100) :- poisoned & true(control(P))`
- line 47: `goal(P,0) :- poisoned & true(control(Q)) & opponent(P,Q)`
- line 58: `init(control(first))`

### lgref G02 (7 statements)

- line 21: `atmost(1,1)`
- line 22: `atmost(1,2)`
- line 23: `atmost(1,3)`
- line 24: `atmost(2,2)`
- line 25: `atmost(2,3)`
- line 26: `atmost(3,3)`
- line 34: `eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)` (also in G00, G03)

### lgref G03 (4 statements)

- line 31: `legal(P,bite(X,Y)) :- true(control(P)) & true(square(X,Y))`
- line 34: `eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)` (also in G00, G02)
- line 38: `legal(first,noop) :- true(control(second))`
- line 39: `legal(second,noop) :- true(control(first))`

### lgref G04 (2 statements)

- line 17: `role(first)`
- line 18: `role(second)`


## random_matched by group

### random_matched G00 (11 statements)

- line 18: `role(second)`
- line 27: `opponent(first,second)`
- line 28: `opponent(second,first)`
- line 35: `next(square(X,Y)) :- true(square(X,Y)) & ~eaten(X,Y)`
- line 38: `legal(first,noop) :- true(control(second))`
- line 40: `next(control(first)) :- true(control(second))`
- line 41: `next(control(second)) :- true(control(first))`
- line 50: `init(square(1,2))`
- line 52: `init(square(2,1))`
- line 54: `init(square(2,3))` (also in G02, G03)
- line 57: `init(square(3,3))`

### random_matched G01 (9 statements)

- line 23: `atmost(1,3)`
- line 25: `atmost(2,3)`
- line 34: `eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)`
- line 39: `legal(second,noop) :- true(control(first))`
- line 45: `terminal :- poisoned`
- line 51: `init(square(1,3))`
- line 53: `init(square(2,2))`
- line 55: `init(square(3,1))`
- line 56: `init(square(3,2))`

### random_matched G02 (7 statements)

- line 17: `role(first)`
- line 24: `atmost(2,2)`
- line 26: `atmost(3,3)`
- line 44: `poisoned :- ~true(square(1,1))`
- line 46: `goal(P,100) :- poisoned & true(control(P))`
- line 54: `init(square(2,3))` (also in G00, G03)
- line 58: `init(control(first))`

### random_matched G03 (4 statements)

- line 21: `atmost(1,1)`
- line 47: `goal(P,0) :- poisoned & true(control(Q)) & opponent(P,Q)`
- line 49: `init(square(1,1))`
- line 54: `init(square(2,3))` (also in G00, G02)

### random_matched G04 (2 statements)

- line 22: `atmost(1,2)`
- line 31: `legal(P,bite(X,Y)) :- true(control(P)) & true(square(X,Y))`

