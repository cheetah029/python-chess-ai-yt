# breakthrough5 -- groupings

File: `lgref/bench/games/breakthrough5.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 0 statements in no group
- **random_matched**: 8 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 19 | `role(white)` | G07 | G05 |
| 20 | `role(black)` | G07 | G02 |
| 23 | `index(1)` | G04 | G05 |
| 24 | `index(2)` | G04 | G05 |
| 25 | `index(3)` | G04 | G01 |
| 26 | `index(4)` | G04 | G00 |
| 27 | `index(5)` | G04 | G00 |
| 28 | `forward(white,1,2)` | G02 | G03 |
| 29 | `forward(white,2,3)` | G02 | G00 |
| 30 | `forward(white,3,4)` | G02 | G01 |
| 31 | `forward(white,4,5)` | G02 | G03 |
| 32 | `forward(black,5,4)` | G02 | G04 |
| 33 | `forward(black,4,3)` | G02 | G02 |
| 34 | `forward(black,3,2)` | G02 | G05 |
| 35 | `forward(black,2,1)` | G02 | G02 |
| 36 | `beside(1,2)` | G03 | G03 |
| 37 | `beside(2,1)` | G03 | G00 |
| 38 | `beside(2,3)` | G03 | G00 |
| 39 | `beside(3,2)` | G03 | G00 |
| 40 | `beside(3,4)` | G03 | G01 |
| 41 | `beside(4,3)` | G03 | G06 |
| 42 | `beside(4,5)` | G03 | G01 |
| 43 | `beside(5,4)` | G03 | G01 |
| 44 | `opponent(white,black)` | G01 | G01, G02, G03 |
| 45 | `opponent(black,white)` | G01 | G03 |
| 48 | `occupied(X,Y) :- true(cell(X,Y,P))` | G04 | G04 |
| 49 | `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` | G02, G04 | G02, G03 |
| 52 | `straight(P,X,Y,X,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & empty(X,Y2)` | G02 | G00 |
| 53 | `diagonal(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & empty(X2,Y2)` | G02, G03 | G00, G05 |
| 54 | `capture(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & opponent(P,Q) & true(cell(X2,Y2,Q))` | G01, G02, G03 | G04 |
| 57 | `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & straight(P,X,Y,X2,Y2)` | G05 | G01 |
| 58 | `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & diagonal(P,X,Y,X2,Y2)` | G05 | G03 |
| 59 | `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & capture(P,X,Y,X2,Y2)` | G05 | G02 |
| 62 | `next(cell(X2,Y2,P)) :- does(P,move(X,Y,X2,Y2))` | G00, G05 | G00 |
| 63 | `touched(X,Y) :- does(P,move(X,Y,X2,Y2))` | G00, G05 | G00 |
| 64 | `touched(X2,Y2) :- does(P,move(X,Y,X2,Y2))` | G00, G05 | G01 |
| 65 | `next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~touched(X,Y)` | G00 | G03 |
| 68 | `legal(white,noop) :- true(control(black))` | G05 | G04 |
| 69 | `legal(black,noop) :- true(control(white))` | G05 | G00 |
| 70 | `next(control(white)) :- true(control(black))` | G06 | G00 |
| 71 | `next(control(black)) :- true(control(white))` | G06 | G02 |
| 74 | `goalrow(white,5)` | G01 | G02, G04 |
| 75 | `goalrow(black,1)` | G01 | G03 |
| 76 | `arrived(P) :- goalrow(P,Y) & true(cell(X,Y,P))` | G01 | G01 |
| 77 | `mobile(P) :- straight(P,X,Y,X2,Y2)` | G01 | G00 |
| 78 | `mobile(P) :- diagonal(P,X,Y,X2,Y2)` | G01 | G00 |
| 79 | `mobile(P) :- capture(P,X,Y,X2,Y2)` | G01 | G01 |
| 80 | `stuck(P) :- true(control(P)) & ~mobile(P)` | G01 | G04 |
| 81 | `terminal :- arrived(P)` | G01 | G00 |
| 82 | `terminal :- stuck(P)` | G01 | G06 |
| 83 | `goal(P,100) :- arrived(P)` | G01 | G03 |
| 84 | `goal(P,100) :- opponent(P,Q) & stuck(Q)` | G01 | G00 |
| 85 | `goal(P,0) :- opponent(P,Q) & arrived(Q)` | G01 | G07 |
| 86 | `goal(P,0) :- stuck(P)` | G01 | G00 |
| 88 | `init(cell(1,1,white))` | G00 | G01 |
| 89 | `init(cell(2,1,white))` | G00 | G02 |
| 90 | `init(cell(3,1,white))` | G00 | G00, G05 |
| 91 | `init(cell(4,1,white))` | G00 | G01 |
| 92 | `init(cell(5,1,white))` | G00 | G01 |
| 93 | `init(cell(1,2,white))` | G00 | G01 |
| 94 | `init(cell(2,2,white))` | G00 | G05 |
| 95 | `init(cell(3,2,white))` | G00 | G00 |
| 96 | `init(cell(4,2,white))` | G00 | G00 |
| 97 | `init(cell(5,2,white))` | G00 | G04 |
| 98 | `init(cell(1,4,black))` | G00 | G06 |
| 99 | `init(cell(2,4,black))` | G00 | G00 |
| 100 | `init(cell(3,4,black))` | G00 | G02 |
| 101 | `init(cell(4,4,black))` | G00 | G01 |
| 102 | `init(cell(5,4,black))` | G00 | G00 |
| 103 | `init(cell(1,5,black))` | G00 | G02 |
| 104 | `init(cell(2,5,black))` | G00 | G00 |
| 105 | `init(cell(3,5,black))` | G00 | G00, G05 |
| 106 | `init(cell(4,5,black))` | G00 | G07 |
| 107 | `init(cell(5,5,black))` | G00 | G02 |
| 108 | `init(control(white))` | G06 | G01 |

## lgref by group

### lgref G00 (24 statements)

- line 62: `next(cell(X2,Y2,P)) :- does(P,move(X,Y,X2,Y2))` (also in G05)
- line 63: `touched(X,Y) :- does(P,move(X,Y,X2,Y2))` (also in G05)
- line 64: `touched(X2,Y2) :- does(P,move(X,Y,X2,Y2))` (also in G05)
- line 65: `next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~touched(X,Y)`
- line 88: `init(cell(1,1,white))`
- line 89: `init(cell(2,1,white))`
- line 90: `init(cell(3,1,white))`
- line 91: `init(cell(4,1,white))`
- line 92: `init(cell(5,1,white))`
- line 93: `init(cell(1,2,white))`
- line 94: `init(cell(2,2,white))`
- line 95: `init(cell(3,2,white))`
- line 96: `init(cell(4,2,white))`
- line 97: `init(cell(5,2,white))`
- line 98: `init(cell(1,4,black))`
- line 99: `init(cell(2,4,black))`
- line 100: `init(cell(3,4,black))`
- line 101: `init(cell(4,4,black))`
- line 102: `init(cell(5,4,black))`
- line 103: `init(cell(1,5,black))`
- line 104: `init(cell(2,5,black))`
- line 105: `init(cell(3,5,black))`
- line 106: `init(cell(4,5,black))`
- line 107: `init(cell(5,5,black))`

### lgref G01 (16 statements)

- line 44: `opponent(white,black)`
- line 45: `opponent(black,white)`
- line 54: `capture(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & opponent(P,Q) & true(cell(X2,Y2,Q))` (also in G02, G03)
- line 74: `goalrow(white,5)`
- line 75: `goalrow(black,1)`
- line 76: `arrived(P) :- goalrow(P,Y) & true(cell(X,Y,P))`
- line 77: `mobile(P) :- straight(P,X,Y,X2,Y2)`
- line 78: `mobile(P) :- diagonal(P,X,Y,X2,Y2)`
- line 79: `mobile(P) :- capture(P,X,Y,X2,Y2)`
- line 80: `stuck(P) :- true(control(P)) & ~mobile(P)`
- line 81: `terminal :- arrived(P)`
- line 82: `terminal :- stuck(P)`
- line 83: `goal(P,100) :- arrived(P)`
- line 84: `goal(P,100) :- opponent(P,Q) & stuck(Q)`
- line 85: `goal(P,0) :- opponent(P,Q) & arrived(Q)`
- line 86: `goal(P,0) :- stuck(P)`

### lgref G02 (12 statements)

- line 28: `forward(white,1,2)`
- line 29: `forward(white,2,3)`
- line 30: `forward(white,3,4)`
- line 31: `forward(white,4,5)`
- line 32: `forward(black,5,4)`
- line 33: `forward(black,4,3)`
- line 34: `forward(black,3,2)`
- line 35: `forward(black,2,1)`
- line 49: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G04)
- line 52: `straight(P,X,Y,X,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & empty(X,Y2)`
- line 53: `diagonal(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & empty(X2,Y2)` (also in G03)
- line 54: `capture(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & opponent(P,Q) & true(cell(X2,Y2,Q))` (also in G01, G03)

### lgref G03 (10 statements)

- line 36: `beside(1,2)`
- line 37: `beside(2,1)`
- line 38: `beside(2,3)`
- line 39: `beside(3,2)`
- line 40: `beside(3,4)`
- line 41: `beside(4,3)`
- line 42: `beside(4,5)`
- line 43: `beside(5,4)`
- line 53: `diagonal(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & empty(X2,Y2)` (also in G02)
- line 54: `capture(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & opponent(P,Q) & true(cell(X2,Y2,Q))` (also in G01, G02)

### lgref G04 (7 statements)

- line 23: `index(1)`
- line 24: `index(2)`
- line 25: `index(3)`
- line 26: `index(4)`
- line 27: `index(5)`
- line 48: `occupied(X,Y) :- true(cell(X,Y,P))`
- line 49: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G02)

### lgref G05 (8 statements)

- line 57: `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & straight(P,X,Y,X2,Y2)`
- line 58: `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & diagonal(P,X,Y,X2,Y2)`
- line 59: `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & capture(P,X,Y,X2,Y2)`
- line 62: `next(cell(X2,Y2,P)) :- does(P,move(X,Y,X2,Y2))` (also in G00)
- line 63: `touched(X,Y) :- does(P,move(X,Y,X2,Y2))` (also in G00)
- line 64: `touched(X2,Y2) :- does(P,move(X,Y,X2,Y2))` (also in G00)
- line 68: `legal(white,noop) :- true(control(black))`
- line 69: `legal(black,noop) :- true(control(white))`

### lgref G06 (3 statements)

- line 70: `next(control(white)) :- true(control(black))`
- line 71: `next(control(black)) :- true(control(white))`
- line 108: `init(control(white))`

### lgref G07 (2 statements)

- line 19: `role(white)`
- line 20: `role(black)`


## random_matched by group

### random_matched G00 (24 statements)

- line 26: `index(4)`
- line 27: `index(5)`
- line 29: `forward(white,2,3)`
- line 37: `beside(2,1)`
- line 38: `beside(2,3)`
- line 39: `beside(3,2)`
- line 52: `straight(P,X,Y,X,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & empty(X,Y2)`
- line 53: `diagonal(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & empty(X2,Y2)` (also in G05)
- line 62: `next(cell(X2,Y2,P)) :- does(P,move(X,Y,X2,Y2))`
- line 63: `touched(X,Y) :- does(P,move(X,Y,X2,Y2))`
- line 69: `legal(black,noop) :- true(control(white))`
- line 70: `next(control(white)) :- true(control(black))`
- line 77: `mobile(P) :- straight(P,X,Y,X2,Y2)`
- line 78: `mobile(P) :- diagonal(P,X,Y,X2,Y2)`
- line 81: `terminal :- arrived(P)`
- line 84: `goal(P,100) :- opponent(P,Q) & stuck(Q)`
- line 86: `goal(P,0) :- stuck(P)`
- line 90: `init(cell(3,1,white))` (also in G05)
- line 95: `init(cell(3,2,white))`
- line 96: `init(cell(4,2,white))`
- line 99: `init(cell(2,4,black))`
- line 102: `init(cell(5,4,black))`
- line 104: `init(cell(2,5,black))`
- line 105: `init(cell(3,5,black))` (also in G05)

### random_matched G01 (16 statements)

- line 25: `index(3)`
- line 30: `forward(white,3,4)`
- line 40: `beside(3,4)`
- line 42: `beside(4,5)`
- line 43: `beside(5,4)`
- line 44: `opponent(white,black)` (also in G02, G03)
- line 57: `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & straight(P,X,Y,X2,Y2)`
- line 64: `touched(X2,Y2) :- does(P,move(X,Y,X2,Y2))`
- line 76: `arrived(P) :- goalrow(P,Y) & true(cell(X,Y,P))`
- line 79: `mobile(P) :- capture(P,X,Y,X2,Y2)`
- line 88: `init(cell(1,1,white))`
- line 91: `init(cell(4,1,white))`
- line 92: `init(cell(5,1,white))`
- line 93: `init(cell(1,2,white))`
- line 101: `init(cell(4,4,black))`
- line 108: `init(control(white))`

### random_matched G02 (12 statements)

- line 20: `role(black)`
- line 33: `forward(black,4,3)`
- line 35: `forward(black,2,1)`
- line 44: `opponent(white,black)` (also in G01, G03)
- line 49: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G03)
- line 59: `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & capture(P,X,Y,X2,Y2)`
- line 71: `next(control(black)) :- true(control(white))`
- line 74: `goalrow(white,5)` (also in G04)
- line 89: `init(cell(2,1,white))`
- line 100: `init(cell(3,4,black))`
- line 103: `init(cell(1,5,black))`
- line 107: `init(cell(5,5,black))`

### random_matched G03 (10 statements)

- line 28: `forward(white,1,2)`
- line 31: `forward(white,4,5)`
- line 36: `beside(1,2)`
- line 44: `opponent(white,black)` (also in G01, G02)
- line 45: `opponent(black,white)`
- line 49: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G02)
- line 58: `legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & diagonal(P,X,Y,X2,Y2)`
- line 65: `next(cell(X,Y,Z)) :- true(cell(X,Y,Z)) & ~touched(X,Y)`
- line 75: `goalrow(black,1)`
- line 83: `goal(P,100) :- arrived(P)`

### random_matched G04 (7 statements)

- line 32: `forward(black,5,4)`
- line 48: `occupied(X,Y) :- true(cell(X,Y,P))`
- line 54: `capture(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & opponent(P,Q) & true(cell(X2,Y2,Q))`
- line 68: `legal(white,noop) :- true(control(black))`
- line 74: `goalrow(white,5)` (also in G02)
- line 80: `stuck(P) :- true(control(P)) & ~mobile(P)`
- line 97: `init(cell(5,2,white))`

### random_matched G05 (8 statements)

- line 19: `role(white)`
- line 23: `index(1)`
- line 24: `index(2)`
- line 34: `forward(black,3,2)`
- line 53: `diagonal(P,X,Y,X2,Y2) :- true(cell(X,Y,P)) & forward(P,Y,Y2) & beside(X,X2) & empty(X2,Y2)` (also in G00)
- line 90: `init(cell(3,1,white))` (also in G00)
- line 94: `init(cell(2,2,white))`
- line 105: `init(cell(3,5,black))` (also in G00)

### random_matched G06 (3 statements)

- line 41: `beside(4,3)`
- line 82: `terminal :- stuck(P)`
- line 98: `init(cell(1,4,black))`

### random_matched G07 (2 statements)

- line 85: `goal(P,0) :- opponent(P,Q) & arrived(Q)`
- line 106: `init(cell(4,5,black))`

