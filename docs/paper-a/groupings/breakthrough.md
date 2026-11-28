# breakthrough -- groupings

File: `lgref/identify/testgames/breakthrough.gdl`. Line numbers are lines of that file.

- **lgref**: 7 groups, 0 statements in no group
- **random_matched**: 7 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 18 | `role(white)` | G06 | G00, G03 |
| 19 | `role(black)` | G06 | G01 |
| 22 | `forward(white,1,2)` | G02 | G00 |
| 23 | `forward(white,2,3)` | G02 | G01 |
| 24 | `forward(white,3,4)` | G02 | G00, G03 |
| 25 | `forward(black,4,3)` | G02 | G02 |
| 26 | `forward(black,3,2)` | G02 | G01 |
| 27 | `forward(black,2,1)` | G02 | G02 |
| 28 | `opponent(white,black)` | G01 | G01 |
| 29 | `opponent(black,white)` | G01 | G01, G02 |
| 32 | `legal(P,advance(C,R,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))` | G02, G03 | G03 |
| 33 | `next(cell(C,S,P)) :- does(P,advance(C,R,S))` | G00, G03 | G00, G03 |
| 34 | `next(cell(C,R,e)) :- does(P,advance(C,R,S))` | G00, G03 | G06 |
| 35 | `changed(C,R) :- does(P,advance(C,R,S))` | G00, G03 | G00 |
| 36 | `changed(C,S) :- does(P,advance(C,R,S))` | G00, G03 | G04 |
| 39 | `beside(1,2)` | G04 | G00 |
| 40 | `beside(2,1)` | G04 | G00 |
| 41 | `beside(2,3)` | G04 | G00, G03 |
| 42 | `beside(3,2)` | G04 | G01 |
| 43 | `legal(P,capture(C,R,D,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` | G01, G02, G03 | G00 |
| 44 | `next(cell(D,S,P)) :- does(P,capture(C,R,D,S))` | G00, G03 | G00, G03 |
| 45 | `next(cell(C,R,e)) :- does(P,capture(C,R,D,S))` | G00, G03 | G03 |
| 46 | `changed(C,R) :- does(P,capture(C,R,D,S))` | G00, G03 | G00 |
| 47 | `changed(D,S) :- does(P,capture(C,R,D,S))` | G00, G03 | G01 |
| 50 | `next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~changed(X,Y)` | G00 | G05 |
| 53 | `legal(white,noop) :- true(control(black))` | G03 | G00 |
| 54 | `legal(black,noop) :- true(control(white))` | G03 | G00 |
| 55 | `next(control(white)) :- true(control(black))` | G05 | G05 |
| 56 | `next(control(black)) :- true(control(white))` | G05 | G06 |
| 59 | `goalrow(white,4)` | G01 | G04 |
| 60 | `goalrow(black,1)` | G01 | G00 |
| 61 | `arrived(P) :- goalrow(P,R) & true(cell(C,R,P))` | G01 | G00 |
| 62 | `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))` | G01, G02 | G00 |
| 63 | `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` | G01, G02 | G02, G03 |
| 64 | `blocked(P) :- true(control(P)) & ~mobile(P)` | G01 | G04 |
| 65 | `terminal :- arrived(P)` | G01 | G00, G03 |
| 66 | `terminal :- blocked(P)` | G01 | G02 |
| 67 | `goal(P,100) :- arrived(P)` | G01 | G00 |
| 68 | `goal(P,100) :- blocked(Q) & opponent(Q,P)` | G01 | G02 |
| 70 | `init(cell(1,1,white))` | G00 | G00, G03 |
| 71 | `init(cell(2,1,white))` | G00 | G01 |
| 72 | `init(cell(3,1,white))` | G00 | G02 |
| 73 | `init(cell(1,2,e))` | G00 | G00, G03 |
| 74 | `init(cell(2,2,e))` | G00 | G01 |
| 75 | `init(cell(3,2,e))` | G00 | G01, G02, G03 |
| 76 | `init(cell(1,3,e))` | G00 | G02 |
| 77 | `init(cell(2,3,e))` | G00 | G01 |
| 78 | `init(cell(3,3,e))` | G00 | G01, G02 |
| 79 | `init(cell(1,4,black))` | G00 | G00 |
| 80 | `init(cell(2,4,black))` | G00 | G01 |
| 81 | `init(cell(3,4,black))` | G00 | G05 |
| 82 | `init(control(white))` | G05 | G04 |

## lgref by group

### lgref G00 (21 statements)

- line 33: `next(cell(C,S,P)) :- does(P,advance(C,R,S))` (also in G03)
- line 34: `next(cell(C,R,e)) :- does(P,advance(C,R,S))` (also in G03)
- line 35: `changed(C,R) :- does(P,advance(C,R,S))` (also in G03)
- line 36: `changed(C,S) :- does(P,advance(C,R,S))` (also in G03)
- line 44: `next(cell(D,S,P)) :- does(P,capture(C,R,D,S))` (also in G03)
- line 45: `next(cell(C,R,e)) :- does(P,capture(C,R,D,S))` (also in G03)
- line 46: `changed(C,R) :- does(P,capture(C,R,D,S))` (also in G03)
- line 47: `changed(D,S) :- does(P,capture(C,R,D,S))` (also in G03)
- line 50: `next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~changed(X,Y)`
- line 70: `init(cell(1,1,white))`
- line 71: `init(cell(2,1,white))`
- line 72: `init(cell(3,1,white))`
- line 73: `init(cell(1,2,e))`
- line 74: `init(cell(2,2,e))`
- line 75: `init(cell(3,2,e))`
- line 76: `init(cell(1,3,e))`
- line 77: `init(cell(2,3,e))`
- line 78: `init(cell(3,3,e))`
- line 79: `init(cell(1,4,black))`
- line 80: `init(cell(2,4,black))`
- line 81: `init(cell(3,4,black))`

### lgref G01 (13 statements)

- line 28: `opponent(white,black)`
- line 29: `opponent(black,white)`
- line 43: `legal(P,capture(C,R,D,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G02, G03)
- line 59: `goalrow(white,4)`
- line 60: `goalrow(black,1)`
- line 61: `arrived(P) :- goalrow(P,R) & true(cell(C,R,P))`
- line 62: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))` (also in G02)
- line 63: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G02)
- line 64: `blocked(P) :- true(control(P)) & ~mobile(P)`
- line 65: `terminal :- arrived(P)`
- line 66: `terminal :- blocked(P)`
- line 67: `goal(P,100) :- arrived(P)`
- line 68: `goal(P,100) :- blocked(Q) & opponent(Q,P)`

### lgref G02 (10 statements)

- line 22: `forward(white,1,2)`
- line 23: `forward(white,2,3)`
- line 24: `forward(white,3,4)`
- line 25: `forward(black,4,3)`
- line 26: `forward(black,3,2)`
- line 27: `forward(black,2,1)`
- line 32: `legal(P,advance(C,R,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))` (also in G03)
- line 43: `legal(P,capture(C,R,D,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G01, G03)
- line 62: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))` (also in G01)
- line 63: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G01)

### lgref G03 (12 statements)

- line 32: `legal(P,advance(C,R,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))` (also in G02)
- line 33: `next(cell(C,S,P)) :- does(P,advance(C,R,S))` (also in G00)
- line 34: `next(cell(C,R,e)) :- does(P,advance(C,R,S))` (also in G00)
- line 35: `changed(C,R) :- does(P,advance(C,R,S))` (also in G00)
- line 36: `changed(C,S) :- does(P,advance(C,R,S))` (also in G00)
- line 43: `legal(P,capture(C,R,D,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G01, G02)
- line 44: `next(cell(D,S,P)) :- does(P,capture(C,R,D,S))` (also in G00)
- line 45: `next(cell(C,R,e)) :- does(P,capture(C,R,D,S))` (also in G00)
- line 46: `changed(C,R) :- does(P,capture(C,R,D,S))` (also in G00)
- line 47: `changed(D,S) :- does(P,capture(C,R,D,S))` (also in G00)
- line 53: `legal(white,noop) :- true(control(black))`
- line 54: `legal(black,noop) :- true(control(white))`

### lgref G04 (4 statements)

- line 39: `beside(1,2)`
- line 40: `beside(2,1)`
- line 41: `beside(2,3)`
- line 42: `beside(3,2)`

### lgref G05 (3 statements)

- line 55: `next(control(white)) :- true(control(black))`
- line 56: `next(control(black)) :- true(control(white))`
- line 82: `init(control(white))`

### lgref G06 (2 statements)

- line 18: `role(white)`
- line 19: `role(black)`


## random_matched by group

### random_matched G00 (21 statements)

- line 18: `role(white)` (also in G03)
- line 22: `forward(white,1,2)`
- line 24: `forward(white,3,4)` (also in G03)
- line 33: `next(cell(C,S,P)) :- does(P,advance(C,R,S))` (also in G03)
- line 35: `changed(C,R) :- does(P,advance(C,R,S))`
- line 39: `beside(1,2)`
- line 40: `beside(2,1)`
- line 41: `beside(2,3)` (also in G03)
- line 43: `legal(P,capture(C,R,D,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))`
- line 44: `next(cell(D,S,P)) :- does(P,capture(C,R,D,S))` (also in G03)
- line 46: `changed(C,R) :- does(P,capture(C,R,D,S))`
- line 53: `legal(white,noop) :- true(control(black))`
- line 54: `legal(black,noop) :- true(control(white))`
- line 60: `goalrow(black,1)`
- line 61: `arrived(P) :- goalrow(P,R) & true(cell(C,R,P))`
- line 62: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))`
- line 65: `terminal :- arrived(P)` (also in G03)
- line 67: `goal(P,100) :- arrived(P)`
- line 70: `init(cell(1,1,white))` (also in G03)
- line 73: `init(cell(1,2,e))` (also in G03)
- line 79: `init(cell(1,4,black))`

### random_matched G01 (13 statements)

- line 19: `role(black)`
- line 23: `forward(white,2,3)`
- line 26: `forward(black,3,2)`
- line 28: `opponent(white,black)`
- line 29: `opponent(black,white)` (also in G02)
- line 42: `beside(3,2)`
- line 47: `changed(D,S) :- does(P,capture(C,R,D,S))`
- line 71: `init(cell(2,1,white))`
- line 74: `init(cell(2,2,e))`
- line 75: `init(cell(3,2,e))` (also in G02, G03)
- line 77: `init(cell(2,3,e))`
- line 78: `init(cell(3,3,e))` (also in G02)
- line 80: `init(cell(2,4,black))`

### random_matched G02 (10 statements)

- line 25: `forward(black,4,3)`
- line 27: `forward(black,2,1)`
- line 29: `opponent(black,white)` (also in G01)
- line 63: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G03)
- line 66: `terminal :- blocked(P)`
- line 68: `goal(P,100) :- blocked(Q) & opponent(Q,P)`
- line 72: `init(cell(3,1,white))`
- line 75: `init(cell(3,2,e))` (also in G01, G03)
- line 76: `init(cell(1,3,e))`
- line 78: `init(cell(3,3,e))` (also in G01)

### random_matched G03 (12 statements)

- line 18: `role(white)` (also in G00)
- line 24: `forward(white,3,4)` (also in G00)
- line 32: `legal(P,advance(C,R,S)) :- true(control(P)) & true(cell(C,R,P)) & forward(P,R,S) & true(cell(C,S,e))`
- line 33: `next(cell(C,S,P)) :- does(P,advance(C,R,S))` (also in G00)
- line 41: `beside(2,3)` (also in G00)
- line 44: `next(cell(D,S,P)) :- does(P,capture(C,R,D,S))` (also in G00)
- line 45: `next(cell(C,R,e)) :- does(P,capture(C,R,D,S))`
- line 63: `mobile(P) :- true(cell(C,R,P)) & forward(P,R,S) & beside(C,D) & opponent(P,Q) & true(cell(D,S,Q))` (also in G02)
- line 65: `terminal :- arrived(P)` (also in G00)
- line 70: `init(cell(1,1,white))` (also in G00)
- line 73: `init(cell(1,2,e))` (also in G00)
- line 75: `init(cell(3,2,e))` (also in G01, G02)

### random_matched G04 (4 statements)

- line 36: `changed(C,S) :- does(P,advance(C,R,S))`
- line 59: `goalrow(white,4)`
- line 64: `blocked(P) :- true(control(P)) & ~mobile(P)`
- line 82: `init(control(white))`

### random_matched G05 (3 statements)

- line 50: `next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~changed(X,Y)`
- line 55: `next(control(white)) :- true(control(black))`
- line 81: `init(cell(3,4,black))`

### random_matched G06 (2 statements)

- line 34: `next(cell(C,R,e)) :- does(P,advance(C,R,S))`
- line 56: `next(control(black)) :- true(control(white))`

