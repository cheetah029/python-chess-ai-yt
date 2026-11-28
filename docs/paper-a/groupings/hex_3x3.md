# hex_3x3 -- groupings

File: `lgref/bench/games/hex_3x3.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 1 statements in no group
- **random_matched**: 8 groups, 1 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 19 | `role(red)` | G05 | G05 |
| 20 | `role(blue)` | G05 | G02 |
| 23 | `index(1)` | G00 | G01 |
| 24 | `index(2)` | G00 | G03 |
| 25 | `index(3)` | G00 | G03 |
| 26 | `succ(1,2)` | G02, G06 | G02, G06 |
| 27 | `succ(2,3)` | G02, G06 | G04 |
| 28 | `touches(X,Y,X2,Y) :- succ(X,X2) & index(Y)` | G02 | G05 |
| 29 | `touches(X,Y,X2,Y) :- succ(X2,X) & index(Y)` | G02 | G01 |
| 30 | `touches(X,Y,X,Y2) :- index(X) & succ(Y,Y2)` | G02 | G00 |
| 31 | `touches(X,Y,X,Y2) :- index(X) & succ(Y2,Y)` | G02 | G00 |
| 32 | `touches(X,Y,X2,Y2) :- succ(X,X2) & succ(Y2,Y)` | G02 | G00 |
| 33 | `touches(X,Y,X2,Y2) :- succ(X2,X) & succ(Y,Y2)` | G02 | G00, G07 |
| 34 | `opponent(red,blue)` | G01 | G02 |
| 35 | `opponent(blue,red)` | G01 | G01 |
| 38 | `legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)` | G00, G03 | G02, G07 |
| 39 | `taken(X,Y) :- true(cell(X,Y,P))` | G03 | G01 |
| 40 | `next(cell(X,Y,P)) :- does(P,place(X,Y))` | G03 | G02 |
| 41 | `next(cell(X,Y,P)) :- true(cell(X,Y,P))` | - | G04 |
| 44 | `legal(red,noop) :- true(control(blue))` | G03 | G03 |
| 45 | `legal(blue,noop) :- true(control(red))` | G03 | G00 |
| 46 | `next(control(red)) :- true(control(blue))` | G04 | G02, G06 |
| 47 | `next(control(blue)) :- true(control(red))` | G04 | G02 |
| 50 | `firstedge(red,X,1) :- index(X)` | G00 | G02 |
| 51 | `firstedge(blue,1,Y) :- index(Y)` | G00 | G04 |
| 52 | `lastedge(red,X,3) :- index(X)` | G00 | G00 |
| 53 | `lastedge(blue,3,Y) :- index(Y)` | G00 | G01 |
| 54 | `reach(P,X,Y) :- firstedge(P,X,Y) & true(cell(X,Y,P))` | G00, G07 | G00 |
| 55 | `reach(P,X2,Y2) :- reach(P,X,Y) & touches(X,Y,X2,Y2) & true(cell(X2,Y2,P))` | G02, G07 | G00 |
| 56 | `joined(P) :- reach(P,X,Y) & lastedge(P,X,Y)` | G01 | G03 |
| 59 | `terminal :- joined(P)` | G01 | G00, G03 |
| 60 | `goal(P,100) :- joined(P)` | G01 | G02 |
| 61 | `goal(P,0) :- opponent(P,Q) & joined(Q)` | G01 | - |
| 63 | `init(control(red))` | G04 | G01 |

## lgref by group

### lgref G00 (9 statements)

- line 23: `index(1)`
- line 24: `index(2)`
- line 25: `index(3)`
- line 38: `legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)` (also in G03)
- line 50: `firstedge(red,X,1) :- index(X)`
- line 51: `firstedge(blue,1,Y) :- index(Y)`
- line 52: `lastedge(red,X,3) :- index(X)`
- line 53: `lastedge(blue,3,Y) :- index(Y)`
- line 54: `reach(P,X,Y) :- firstedge(P,X,Y) & true(cell(X,Y,P))` (also in G07)

### lgref G01 (6 statements)

- line 34: `opponent(red,blue)`
- line 35: `opponent(blue,red)`
- line 56: `joined(P) :- reach(P,X,Y) & lastedge(P,X,Y)`
- line 59: `terminal :- joined(P)`
- line 60: `goal(P,100) :- joined(P)`
- line 61: `goal(P,0) :- opponent(P,Q) & joined(Q)`

### lgref G02 (9 statements)

- line 26: `succ(1,2)` (also in G06)
- line 27: `succ(2,3)` (also in G06)
- line 28: `touches(X,Y,X2,Y) :- succ(X,X2) & index(Y)`
- line 29: `touches(X,Y,X2,Y) :- succ(X2,X) & index(Y)`
- line 30: `touches(X,Y,X,Y2) :- index(X) & succ(Y,Y2)`
- line 31: `touches(X,Y,X,Y2) :- index(X) & succ(Y2,Y)`
- line 32: `touches(X,Y,X2,Y2) :- succ(X,X2) & succ(Y2,Y)`
- line 33: `touches(X,Y,X2,Y2) :- succ(X2,X) & succ(Y,Y2)`
- line 55: `reach(P,X2,Y2) :- reach(P,X,Y) & touches(X,Y,X2,Y2) & true(cell(X2,Y2,P))` (also in G07)

### lgref G03 (5 statements)

- line 38: `legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)` (also in G00)
- line 39: `taken(X,Y) :- true(cell(X,Y,P))`
- line 40: `next(cell(X,Y,P)) :- does(P,place(X,Y))`
- line 44: `legal(red,noop) :- true(control(blue))`
- line 45: `legal(blue,noop) :- true(control(red))`

### lgref G04 (3 statements)

- line 46: `next(control(red)) :- true(control(blue))`
- line 47: `next(control(blue)) :- true(control(red))`
- line 63: `init(control(red))`

### lgref G05 (2 statements)

- line 19: `role(red)`
- line 20: `role(blue)`

### lgref G06 (2 statements)

- line 26: `succ(1,2)` (also in G02)
- line 27: `succ(2,3)` (also in G02)

### lgref G07 (2 statements)

- line 54: `reach(P,X,Y) :- firstedge(P,X,Y) & true(cell(X,Y,P))` (also in G00)
- line 55: `reach(P,X2,Y2) :- reach(P,X,Y) & touches(X,Y,X2,Y2) & true(cell(X2,Y2,P))` (also in G02)

### lgref: statements in no group

- line 41: `next(cell(X,Y,P)) :- true(cell(X,Y,P))`


## random_matched by group

### random_matched G00 (9 statements)

- line 30: `touches(X,Y,X,Y2) :- index(X) & succ(Y,Y2)`
- line 31: `touches(X,Y,X,Y2) :- index(X) & succ(Y2,Y)`
- line 32: `touches(X,Y,X2,Y2) :- succ(X,X2) & succ(Y2,Y)`
- line 33: `touches(X,Y,X2,Y2) :- succ(X2,X) & succ(Y,Y2)` (also in G07)
- line 45: `legal(blue,noop) :- true(control(red))`
- line 52: `lastedge(red,X,3) :- index(X)`
- line 54: `reach(P,X,Y) :- firstedge(P,X,Y) & true(cell(X,Y,P))`
- line 55: `reach(P,X2,Y2) :- reach(P,X,Y) & touches(X,Y,X2,Y2) & true(cell(X2,Y2,P))`
- line 59: `terminal :- joined(P)` (also in G03)

### random_matched G01 (6 statements)

- line 23: `index(1)`
- line 29: `touches(X,Y,X2,Y) :- succ(X2,X) & index(Y)`
- line 35: `opponent(blue,red)`
- line 39: `taken(X,Y) :- true(cell(X,Y,P))`
- line 53: `lastedge(blue,3,Y) :- index(Y)`
- line 63: `init(control(red))`

### random_matched G02 (9 statements)

- line 20: `role(blue)`
- line 26: `succ(1,2)` (also in G06)
- line 34: `opponent(red,blue)`
- line 38: `legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)` (also in G07)
- line 40: `next(cell(X,Y,P)) :- does(P,place(X,Y))`
- line 46: `next(control(red)) :- true(control(blue))` (also in G06)
- line 47: `next(control(blue)) :- true(control(red))`
- line 50: `firstedge(red,X,1) :- index(X)`
- line 60: `goal(P,100) :- joined(P)`

### random_matched G03 (5 statements)

- line 24: `index(2)`
- line 25: `index(3)`
- line 44: `legal(red,noop) :- true(control(blue))`
- line 56: `joined(P) :- reach(P,X,Y) & lastedge(P,X,Y)`
- line 59: `terminal :- joined(P)` (also in G00)

### random_matched G04 (3 statements)

- line 27: `succ(2,3)`
- line 41: `next(cell(X,Y,P)) :- true(cell(X,Y,P))`
- line 51: `firstedge(blue,1,Y) :- index(Y)`

### random_matched G05 (2 statements)

- line 19: `role(red)`
- line 28: `touches(X,Y,X2,Y) :- succ(X,X2) & index(Y)`

### random_matched G06 (2 statements)

- line 26: `succ(1,2)` (also in G02)
- line 46: `next(control(red)) :- true(control(blue))` (also in G02)

### random_matched G07 (2 statements)

- line 33: `touches(X,Y,X2,Y2) :- succ(X2,X) & succ(Y,Y2)` (also in G00)
- line 38: `legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)` (also in G02)

### random_matched: statements in no group

- line 61: `goal(P,0) :- opponent(P,Q) & joined(Q)`

