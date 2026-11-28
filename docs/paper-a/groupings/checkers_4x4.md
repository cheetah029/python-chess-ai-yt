# checkers_4x4 -- groupings

File: `lgref/bench/games/checkers_4x4.gdl`. Line numbers are lines of that file.

- **lgref**: 10 groups, 0 statements in no group
- **random_matched**: 10 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 25 | `role(white)` | G01 | G02, G07 |
| 26 | `role(black)` | G01 | G04 |
| 29 | `index(1)` | G06 | G01, G03 |
| 30 | `index(2)` | G06 | G02 |
| 31 | `index(3)` | G06 | G00 |
| 32 | `index(4)` | G06 | G02 |
| 33 | `forward(white,1,2)` | G04 | G00 |
| 34 | `forward(white,2,3)` | G04 | G06 |
| 35 | `forward(white,3,4)` | G04 | G03 |
| 36 | `forward(black,4,3)` | G04 | G06 |
| 37 | `forward(black,3,2)` | G04 | G05 |
| 38 | `forward(black,2,1)` | G04 | G04 |
| 39 | `near(1,2)` | G03 | G01, G03, G05 |
| 40 | `near(2,1)` | G03 | G08 |
| 41 | `near(2,3)` | G03 | G05 |
| 42 | `near(3,2)` | G03 | G05, G07 |
| 43 | `near(3,4)` | G03 | G02 |
| 44 | `near(4,3)` | G03 | G01 |
| 45 | `straddle(1,2,3)` | G05 | G00 |
| 46 | `straddle(2,3,4)` | G05 | G00 |
| 47 | `straddle(3,2,1)` | G05 | G00 |
| 48 | `straddle(4,3,2)` | G05 | G00 |
| 49 | `opponent(white,black)` | G01 | G00 |
| 50 | `opponent(black,white)` | G01 | G03 |
| 53 | `occupied(X,Y) :- true(at(P,K,X,Y))` | G06 | G01 |
| 54 | `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` | G06 | G02, G07 |
| 55 | `enemy(P,X,Y) :- true(at(Q,K,X,Y)) & opponent(P,Q)` | G01 | G06 |
| 58 | `heading(P,man,Y,Y2) :- forward(P,Y,Y2)` | G03, G04 | G01 |
| 59 | `heading(P,king,Y,Y2) :- role(P) & near(Y,Y2)` | G01, G03 | G02 |
| 62 | `step(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y2) & near(X,X2) & empty(X2,Y2)` | G03 | G04 |
| 63 | `legal(P,step(X,Y,X2,Y2)) :- true(control(P)) & step(P,X,Y,X2,Y2) & ~canjump(P)` | G07 | G00 |
| 66 | `jump(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y1) & straddle(Y,Y1,Y2) & straddle(X,X1,X2) & enemy(P,X1,Y1) & empty(X2,Y2)` | G05 | G02, G05, G07 |
| 67 | `canjump(P) :- jump(P,X,Y,X2,Y2)` | G05, G07 | G00, G09 |
| 68 | `legal(P,jump(X,Y,X2,Y2)) :- true(control(P)) & jump(P,X,Y,X2,Y2)` | G07 | G02 |
| 69 | `jumped(X1,Y1) :- does(P,jump(X,Y,X2,Y2)) & straddle(X,X1,X2) & straddle(Y,Y1,Y2)` | G02, G05, G07 | G05 |
| 72 | `arrives(P,K,X2,Y2) :- does(P,step(X,Y,X2,Y2)) & true(at(P,K,X,Y))` | G02, G07 | G00 |
| 73 | `arrives(P,K,X2,Y2) :- does(P,jump(X,Y,X2,Y2)) & true(at(P,K,X,Y))` | G02, G07 | G01 |
| 74 | `left(X,Y) :- does(P,step(X,Y,X2,Y2))` | G02, G07 | G04 |
| 75 | `left(X,Y) :- does(P,jump(X,Y,X2,Y2))` | G02, G07 | G01 |
| 76 | `next(at(P,K,X,Y)) :- arrives(P,K,X,Y) & ~farrow(P,Y)` | G02 | G00 |
| 77 | `next(at(Q,K,X,Y)) :- true(at(Q,K,X,Y)) & ~left(X,Y) & ~jumped(X,Y)` | G02 | G08 |
| 78 | `farrow(white,4)` | G02 | G03 |
| 79 | `farrow(black,1)` | G02 | G03 |
| 80 | `next(at(P,king,X,Y)) :- arrives(P,K,X,Y) & farrow(P,Y)` | G02 | G00 |
| 83 | `legal(white,noop) :- true(control(black))` | G07 | G04 |
| 84 | `legal(black,noop) :- true(control(white))` | G07 | G01 |
| 85 | `next(control(white)) :- true(control(black))` | G08 | G00 |
| 86 | `next(control(black)) :- true(control(white))` | G08 | G03 |
| 87 | `succ(0,1)` | G00 | G01 |
| 88 | `succ(1,2)` | G00 | G01, G09 |
| 89 | `succ(2,3)` | G00 | G03 |
| 90 | `succ(3,4)` | G00 | G01 |
| 91 | `succ(4,5)` | G00 | G03, G04 |
| 92 | `succ(5,6)` | G00 | G08 |
| 93 | `succ(6,7)` | G00 | G00 |
| 94 | `succ(7,8)` | G00 | G07 |
| 95 | `succ(8,9)` | G00 | G05 |
| 96 | `succ(9,10)` | G00 | G00 |
| 97 | `succ(10,11)` | G00 | G07 |
| 98 | `succ(11,12)` | G00 | G01 |
| 99 | `succ(12,13)` | G00 | G04 |
| 100 | `succ(13,14)` | G00 | G01 |
| 101 | `succ(14,15)` | G00 | G02 |
| 102 | `succ(15,16)` | G00 | G01 |
| 103 | `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` | G00, G09 | G01, G09 |
| 106 | `mobile(P) :- step(P,X,Y,X2,Y2)` | G01, G03, G05 | G02 |
| 107 | `mobile(P) :- jump(P,X,Y,X2,Y2)` | G01, G05 | G01 |
| 108 | `stuck(P) :- true(control(P)) & ~mobile(P)` | G01 | G06 |
| 109 | `blocked :- stuck(P)` | G01 | G01, G05 |
| 110 | `timeup :- true(tick(16)) & ~blocked` | G01, G09 | G03 |
| 111 | `terminal :- blocked` | G01 | G00 |
| 112 | `terminal :- timeup` | G01 | G02 |
| 113 | `goal(P,0) :- stuck(P)` | G01 | G00 |
| 114 | `goal(P,100) :- opponent(P,Q) & stuck(Q)` | G01 | G02, G07 |
| 115 | `goal(P,50) :- role(P) & timeup` | G01 | G07 |
| 117 | `init(at(white,man,2,1))` | G02 | G06 |
| 118 | `init(at(white,man,4,1))` | G02 | G06 |
| 119 | `init(at(black,man,1,4))` | G02 | G02 |
| 120 | `init(at(black,man,3,4))` | G02 | G02, G07 |
| 121 | `init(control(white))` | G08 | G07 |
| 122 | `init(tick(0))` | G01, G09 | G05 |

## lgref by group

### lgref G00 (17 statements)

- line 87: `succ(0,1)`
- line 88: `succ(1,2)`
- line 89: `succ(2,3)`
- line 90: `succ(3,4)`
- line 91: `succ(4,5)`
- line 92: `succ(5,6)`
- line 93: `succ(6,7)`
- line 94: `succ(7,8)`
- line 95: `succ(8,9)`
- line 96: `succ(9,10)`
- line 97: `succ(10,11)`
- line 98: `succ(11,12)`
- line 99: `succ(12,13)`
- line 100: `succ(13,14)`
- line 101: `succ(14,15)`
- line 102: `succ(15,16)`
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G09)

### lgref G01 (17 statements)

- line 25: `role(white)`
- line 26: `role(black)`
- line 49: `opponent(white,black)`
- line 50: `opponent(black,white)`
- line 55: `enemy(P,X,Y) :- true(at(Q,K,X,Y)) & opponent(P,Q)`
- line 59: `heading(P,king,Y,Y2) :- role(P) & near(Y,Y2)` (also in G03)
- line 106: `mobile(P) :- step(P,X,Y,X2,Y2)` (also in G03, G05)
- line 107: `mobile(P) :- jump(P,X,Y,X2,Y2)` (also in G05)
- line 108: `stuck(P) :- true(control(P)) & ~mobile(P)`
- line 109: `blocked :- stuck(P)`
- line 110: `timeup :- true(tick(16)) & ~blocked` (also in G09)
- line 111: `terminal :- blocked`
- line 112: `terminal :- timeup`
- line 113: `goal(P,0) :- stuck(P)`
- line 114: `goal(P,100) :- opponent(P,Q) & stuck(Q)`
- line 115: `goal(P,50) :- role(P) & timeup`
- line 122: `init(tick(0))` (also in G09)

### lgref G02 (14 statements)

- line 69: `jumped(X1,Y1) :- does(P,jump(X,Y,X2,Y2)) & straddle(X,X1,X2) & straddle(Y,Y1,Y2)` (also in G05, G07)
- line 72: `arrives(P,K,X2,Y2) :- does(P,step(X,Y,X2,Y2)) & true(at(P,K,X,Y))` (also in G07)
- line 73: `arrives(P,K,X2,Y2) :- does(P,jump(X,Y,X2,Y2)) & true(at(P,K,X,Y))` (also in G07)
- line 74: `left(X,Y) :- does(P,step(X,Y,X2,Y2))` (also in G07)
- line 75: `left(X,Y) :- does(P,jump(X,Y,X2,Y2))` (also in G07)
- line 76: `next(at(P,K,X,Y)) :- arrives(P,K,X,Y) & ~farrow(P,Y)`
- line 77: `next(at(Q,K,X,Y)) :- true(at(Q,K,X,Y)) & ~left(X,Y) & ~jumped(X,Y)`
- line 78: `farrow(white,4)`
- line 79: `farrow(black,1)`
- line 80: `next(at(P,king,X,Y)) :- arrives(P,K,X,Y) & farrow(P,Y)`
- line 117: `init(at(white,man,2,1))`
- line 118: `init(at(white,man,4,1))`
- line 119: `init(at(black,man,1,4))`
- line 120: `init(at(black,man,3,4))`

### lgref G03 (10 statements)

- line 39: `near(1,2)`
- line 40: `near(2,1)`
- line 41: `near(2,3)`
- line 42: `near(3,2)`
- line 43: `near(3,4)`
- line 44: `near(4,3)`
- line 58: `heading(P,man,Y,Y2) :- forward(P,Y,Y2)` (also in G04)
- line 59: `heading(P,king,Y,Y2) :- role(P) & near(Y,Y2)` (also in G01)
- line 62: `step(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y2) & near(X,X2) & empty(X2,Y2)`
- line 106: `mobile(P) :- step(P,X,Y,X2,Y2)` (also in G01, G05)

### lgref G04 (7 statements)

- line 33: `forward(white,1,2)`
- line 34: `forward(white,2,3)`
- line 35: `forward(white,3,4)`
- line 36: `forward(black,4,3)`
- line 37: `forward(black,3,2)`
- line 38: `forward(black,2,1)`
- line 58: `heading(P,man,Y,Y2) :- forward(P,Y,Y2)` (also in G03)

### lgref G05 (9 statements)

- line 45: `straddle(1,2,3)`
- line 46: `straddle(2,3,4)`
- line 47: `straddle(3,2,1)`
- line 48: `straddle(4,3,2)`
- line 66: `jump(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y1) & straddle(Y,Y1,Y2) & straddle(X,X1,X2) & enemy(P,X1,Y1) & empty(X2,Y2)`
- line 67: `canjump(P) :- jump(P,X,Y,X2,Y2)` (also in G07)
- line 69: `jumped(X1,Y1) :- does(P,jump(X,Y,X2,Y2)) & straddle(X,X1,X2) & straddle(Y,Y1,Y2)` (also in G02, G07)
- line 106: `mobile(P) :- step(P,X,Y,X2,Y2)` (also in G01, G03)
- line 107: `mobile(P) :- jump(P,X,Y,X2,Y2)` (also in G01)

### lgref G06 (6 statements)

- line 29: `index(1)`
- line 30: `index(2)`
- line 31: `index(3)`
- line 32: `index(4)`
- line 53: `occupied(X,Y) :- true(at(P,K,X,Y))`
- line 54: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)`

### lgref G07 (10 statements)

- line 63: `legal(P,step(X,Y,X2,Y2)) :- true(control(P)) & step(P,X,Y,X2,Y2) & ~canjump(P)`
- line 67: `canjump(P) :- jump(P,X,Y,X2,Y2)` (also in G05)
- line 68: `legal(P,jump(X,Y,X2,Y2)) :- true(control(P)) & jump(P,X,Y,X2,Y2)`
- line 69: `jumped(X1,Y1) :- does(P,jump(X,Y,X2,Y2)) & straddle(X,X1,X2) & straddle(Y,Y1,Y2)` (also in G02, G05)
- line 72: `arrives(P,K,X2,Y2) :- does(P,step(X,Y,X2,Y2)) & true(at(P,K,X,Y))` (also in G02)
- line 73: `arrives(P,K,X2,Y2) :- does(P,jump(X,Y,X2,Y2)) & true(at(P,K,X,Y))` (also in G02)
- line 74: `left(X,Y) :- does(P,step(X,Y,X2,Y2))` (also in G02)
- line 75: `left(X,Y) :- does(P,jump(X,Y,X2,Y2))` (also in G02)
- line 83: `legal(white,noop) :- true(control(black))`
- line 84: `legal(black,noop) :- true(control(white))`

### lgref G08 (3 statements)

- line 85: `next(control(white)) :- true(control(black))`
- line 86: `next(control(black)) :- true(control(white))`
- line 121: `init(control(white))`

### lgref G09 (3 statements)

- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G00)
- line 110: `timeup :- true(tick(16)) & ~blocked` (also in G01)
- line 122: `init(tick(0))` (also in G01)


## random_matched by group

### random_matched G00 (17 statements)

- line 31: `index(3)`
- line 33: `forward(white,1,2)`
- line 45: `straddle(1,2,3)`
- line 46: `straddle(2,3,4)`
- line 47: `straddle(3,2,1)`
- line 48: `straddle(4,3,2)`
- line 49: `opponent(white,black)`
- line 63: `legal(P,step(X,Y,X2,Y2)) :- true(control(P)) & step(P,X,Y,X2,Y2) & ~canjump(P)`
- line 67: `canjump(P) :- jump(P,X,Y,X2,Y2)` (also in G09)
- line 72: `arrives(P,K,X2,Y2) :- does(P,step(X,Y,X2,Y2)) & true(at(P,K,X,Y))`
- line 76: `next(at(P,K,X,Y)) :- arrives(P,K,X,Y) & ~farrow(P,Y)`
- line 80: `next(at(P,king,X,Y)) :- arrives(P,K,X,Y) & farrow(P,Y)`
- line 85: `next(control(white)) :- true(control(black))`
- line 93: `succ(6,7)`
- line 96: `succ(9,10)`
- line 111: `terminal :- blocked`
- line 113: `goal(P,0) :- stuck(P)`

### random_matched G01 (17 statements)

- line 29: `index(1)` (also in G03)
- line 39: `near(1,2)` (also in G03, G05)
- line 44: `near(4,3)`
- line 53: `occupied(X,Y) :- true(at(P,K,X,Y))`
- line 58: `heading(P,man,Y,Y2) :- forward(P,Y,Y2)`
- line 73: `arrives(P,K,X2,Y2) :- does(P,jump(X,Y,X2,Y2)) & true(at(P,K,X,Y))`
- line 75: `left(X,Y) :- does(P,jump(X,Y,X2,Y2))`
- line 84: `legal(black,noop) :- true(control(white))`
- line 87: `succ(0,1)`
- line 88: `succ(1,2)` (also in G09)
- line 90: `succ(3,4)`
- line 98: `succ(11,12)`
- line 100: `succ(13,14)`
- line 102: `succ(15,16)`
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G09)
- line 107: `mobile(P) :- jump(P,X,Y,X2,Y2)`
- line 109: `blocked :- stuck(P)` (also in G05)

### random_matched G02 (14 statements)

- line 25: `role(white)` (also in G07)
- line 30: `index(2)`
- line 32: `index(4)`
- line 43: `near(3,4)`
- line 54: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G07)
- line 59: `heading(P,king,Y,Y2) :- role(P) & near(Y,Y2)`
- line 66: `jump(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y1) & straddle(Y,Y1,Y2) & straddle(X,X1,X2) & enemy(P,X1,Y1) & empty(X2,Y2)` (also in G05, G07)
- line 68: `legal(P,jump(X,Y,X2,Y2)) :- true(control(P)) & jump(P,X,Y,X2,Y2)`
- line 101: `succ(14,15)`
- line 106: `mobile(P) :- step(P,X,Y,X2,Y2)`
- line 112: `terminal :- timeup`
- line 114: `goal(P,100) :- opponent(P,Q) & stuck(Q)` (also in G07)
- line 119: `init(at(black,man,1,4))`
- line 120: `init(at(black,man,3,4))` (also in G07)

### random_matched G03 (10 statements)

- line 29: `index(1)` (also in G01)
- line 35: `forward(white,3,4)`
- line 39: `near(1,2)` (also in G01, G05)
- line 50: `opponent(black,white)`
- line 78: `farrow(white,4)`
- line 79: `farrow(black,1)`
- line 86: `next(control(black)) :- true(control(white))`
- line 89: `succ(2,3)`
- line 91: `succ(4,5)` (also in G04)
- line 110: `timeup :- true(tick(16)) & ~blocked`

### random_matched G04 (7 statements)

- line 26: `role(black)`
- line 38: `forward(black,2,1)`
- line 62: `step(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y2) & near(X,X2) & empty(X2,Y2)`
- line 74: `left(X,Y) :- does(P,step(X,Y,X2,Y2))`
- line 83: `legal(white,noop) :- true(control(black))`
- line 91: `succ(4,5)` (also in G03)
- line 99: `succ(12,13)`

### random_matched G05 (9 statements)

- line 37: `forward(black,3,2)`
- line 39: `near(1,2)` (also in G01, G03)
- line 41: `near(2,3)`
- line 42: `near(3,2)` (also in G07)
- line 66: `jump(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y1) & straddle(Y,Y1,Y2) & straddle(X,X1,X2) & enemy(P,X1,Y1) & empty(X2,Y2)` (also in G02, G07)
- line 69: `jumped(X1,Y1) :- does(P,jump(X,Y,X2,Y2)) & straddle(X,X1,X2) & straddle(Y,Y1,Y2)`
- line 95: `succ(8,9)`
- line 109: `blocked :- stuck(P)` (also in G01)
- line 122: `init(tick(0))`

### random_matched G06 (6 statements)

- line 34: `forward(white,2,3)`
- line 36: `forward(black,4,3)`
- line 55: `enemy(P,X,Y) :- true(at(Q,K,X,Y)) & opponent(P,Q)`
- line 108: `stuck(P) :- true(control(P)) & ~mobile(P)`
- line 117: `init(at(white,man,2,1))`
- line 118: `init(at(white,man,4,1))`

### random_matched G07 (10 statements)

- line 25: `role(white)` (also in G02)
- line 42: `near(3,2)` (also in G05)
- line 54: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G02)
- line 66: `jump(P,X,Y,X2,Y2) :- true(at(P,K,X,Y)) & heading(P,K,Y,Y1) & straddle(Y,Y1,Y2) & straddle(X,X1,X2) & enemy(P,X1,Y1) & empty(X2,Y2)` (also in G02, G05)
- line 94: `succ(7,8)`
- line 97: `succ(10,11)`
- line 114: `goal(P,100) :- opponent(P,Q) & stuck(Q)` (also in G02)
- line 115: `goal(P,50) :- role(P) & timeup`
- line 120: `init(at(black,man,3,4))` (also in G02)
- line 121: `init(control(white))`

### random_matched G08 (3 statements)

- line 40: `near(2,1)`
- line 77: `next(at(Q,K,X,Y)) :- true(at(Q,K,X,Y)) & ~left(X,Y) & ~jumped(X,Y)`
- line 92: `succ(5,6)`

### random_matched G09 (3 statements)

- line 67: `canjump(P) :- jump(P,X,Y,X2,Y2)` (also in G00)
- line 88: `succ(1,2)` (also in G01)
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G01)

