# foxgeese_mini -- groupings

File: `lgref/bench/games/foxgeese_mini.gdl`. Line numbers are lines of that file.

- **lgref**: 10 groups, 0 statements in no group
- **random_matched**: 10 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 23 | `role(geese)` | G09 | G00 |
| 24 | `role(fox)` | G09 | G04 |
| 27 | `index(1)` | G01 | G03, G05 |
| 28 | `index(2)` | G01 | G00 |
| 29 | `index(3)` | G01 | G03 |
| 30 | `index(4)` | G01 | G07 |
| 31 | `up(1,2)` | G01 | G01 |
| 32 | `up(2,3)` | G01 | G09 |
| 33 | `up(3,4)` | G01 | G09 |
| 34 | `beside(1,2)` | G04 | G00, G02 |
| 35 | `beside(2,1)` | G04 | G05 |
| 36 | `beside(2,3)` | G04 | G01 |
| 37 | `beside(3,2)` | G04 | G02 |
| 38 | `beside(3,4)` | G04 | G00 |
| 39 | `beside(4,3)` | G04 | G03 |
| 40 | `straddle(1,2,3)` | G01 | G03 |
| 41 | `straddle(2,3,4)` | G01 | G00 |
| 42 | `straddle(3,2,1)` | G01 | G02 |
| 43 | `straddle(4,3,2)` | G01 | G06 |
| 44 | `orth(X,Y,X2,Y) :- beside(X,X2) & index(Y)` | G01, G04 | G01 |
| 45 | `orth(X,Y,X,Y2) :- index(X) & beside(Y,Y2)` | G01, G04 | G00 |
| 46 | `hop(X,Y,X1,Y,X2,Y) :- straddle(X,X1,X2) & index(Y)` | G01 | G01, G03, G05 |
| 47 | `hop(X,Y,X,Y1,X,Y2) :- index(X) & straddle(Y,Y1,Y2)` | G01 | G01 |
| 50 | `occupied(X,Y) :- true(goose(X,Y))` | G05 | G01, G04 |
| 51 | `occupied(X,Y) :- true(fox(X,Y))` | G03, G05 | G01 |
| 52 | `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` | G01, G05 | G08 |
| 55 | `waddle(X,Y,X,Y2) :- index(X) & up(Y,Y2)` | G01 | G01 |
| 56 | `waddle(X,Y,X2,Y) :- beside(X,X2) & index(Y)` | G01, G04 | G02 |
| 57 | `glide(X,Y,X2,Y2) :- true(goose(X,Y)) & waddle(X,Y,X2,Y2) & empty(X2,Y2)` | G05 | G00 |
| 58 | `legal(geese,glide(X,Y,X2,Y2)) :- true(control(geese)) & glide(X,Y,X2,Y2)` | G03 | G01 |
| 59 | `glided(X,Y) :- does(geese,glide(X,Y,X2,Y2))` | G03, G05 | G00 |
| 60 | `next(goose(X2,Y2)) :- does(geese,glide(X,Y,X2,Y2))` | G03, G05 | G03, G05 |
| 61 | `next(goose(X,Y)) :- true(goose(X,Y)) & ~glided(X,Y) & ~eaten(X,Y)` | G05 | G02, G07 |
| 64 | `stride(X,Y,X2,Y2) :- true(fox(X,Y)) & orth(X,Y,X2,Y2) & empty(X2,Y2)` | G03 | G03 |
| 65 | `legal(fox,step(X,Y,X2,Y2)) :- true(control(fox)) & stride(X,Y,X2,Y2)` | G03 | G01 |
| 66 | `next(fox(X2,Y2)) :- does(fox,step(X,Y,X2,Y2))` | G03, G05 | G00 |
| 67 | `next(fox(X,Y)) :- true(fox(X,Y)) & does(fox,noop)` | G03 | G02 |
| 70 | `leap(X,Y,X2,Y2) :- true(fox(X,Y)) & hop(X,Y,X1,Y1,X2,Y2) & true(goose(X1,Y1)) & empty(X2,Y2)` | G03, G05 | G01 |
| 71 | `legal(fox,jump(X,Y,X2,Y2)) :- true(control(fox)) & leap(X,Y,X2,Y2)` | G03 | G05 |
| 72 | `eaten(X1,Y1) :- does(fox,jump(X,Y,X2,Y2)) & hop(X,Y,X1,Y1,X2,Y2)` | G01, G03, G05 | G06 |
| 73 | `next(fox(X2,Y2)) :- does(fox,jump(X,Y,X2,Y2))` | G03, G05 | G00 |
| 74 | `feast :- does(fox,jump(X,Y,X2,Y2))` | G03, G07 | G01 |
| 75 | `next(lost(N2)) :- true(lost(N)) & feast & succ(N,N2)` | G00, G07 | G00 |
| 76 | `next(lost(N)) :- true(lost(N)) & ~feast` | G02, G07 | G01, G04 |
| 79 | `legal(geese,noop) :- true(control(fox))` | G03 | G01 |
| 80 | `legal(fox,noop) :- true(control(geese))` | G03 | G02 |
| 81 | `next(control(geese)) :- true(control(fox))` | G08 | G08 |
| 82 | `next(control(fox)) :- true(control(geese))` | G08 | G01 |
| 83 | `succ(0,1)` | G00 | G04 |
| 84 | `succ(1,2)` | G00 | G02 |
| 85 | `succ(2,3)` | G00 | G04 |
| 86 | `succ(3,4)` | G00 | G05 |
| 87 | `succ(4,5)` | G00 | G01, G05 |
| 88 | `succ(5,6)` | G00 | G08 |
| 89 | `succ(6,7)` | G00 | G01 |
| 90 | `succ(7,8)` | G00 | G00 |
| 91 | `succ(8,9)` | G00 | G03 |
| 92 | `succ(9,10)` | G00 | G00 |
| 93 | `succ(10,11)` | G00 | G00 |
| 94 | `succ(11,12)` | G00 | G04 |
| 95 | `succ(12,13)` | G00 | G00 |
| 96 | `succ(13,14)` | G00 | G02 |
| 97 | `succ(14,15)` | G00 | G05 |
| 98 | `succ(15,16)` | G00 | G03, G05 |
| 99 | `succ(16,17)` | G00 | G02 |
| 100 | `succ(17,18)` | G00 | G05 |
| 101 | `succ(18,19)` | G00 | G02, G07 |
| 102 | `succ(19,20)` | G00 | G03 |
| 103 | `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` | G00, G02 | G02, G06 |
| 106 | `mobile(geese) :- glide(X,Y,X2,Y2)` | G06 | G00 |
| 107 | `mobile(fox) :- stride(X,Y,X2,Y2)` | G06 | G00 |
| 108 | `mobile(fox) :- leap(X,Y,X2,Y2)` | G06 | G04 |
| 109 | `stuck(P) :- true(control(P)) & ~mobile(P)` | G02, G06 | G05 |
| 110 | `foxwins :- true(lost(2))` | G02, G07 | G03, G05 |
| 111 | `foxwins :- stuck(geese)` | G02 | G02 |
| 112 | `foxwins :- true(tick(20)) & ~stuck(fox)` | G02 | G05 |
| 113 | `geesewin :- stuck(fox)` | G02 | G01 |
| 114 | `terminal :- foxwins` | G02 | G02 |
| 115 | `terminal :- geesewin` | G02 | G03 |
| 116 | `goal(fox,100) :- foxwins` | G02 | G04 |
| 117 | `goal(geese,0) :- foxwins` | G02 | G06 |
| 118 | `goal(geese,100) :- geesewin` | G02 | G00 |
| 119 | `goal(fox,0) :- geesewin` | G02 | G03, G07 |
| 121 | `init(goose(1,1))` | G05 | G03 |
| 122 | `init(goose(2,1))` | G05 | G00 |
| 123 | `init(goose(3,1))` | G05 | G03, G05 |
| 124 | `init(goose(4,1))` | G05 | G03, G05 |
| 125 | `init(fox(3,4))` | G03 | G00 |
| 126 | `init(lost(0))` | G07 | G00 |
| 127 | `init(control(geese))` | G08 | G01, G04 |
| 128 | `init(tick(0))` | G02 | G00, G07 |

## lgref by group

### lgref G00 (22 statements)

- line 75: `next(lost(N2)) :- true(lost(N)) & feast & succ(N,N2)` (also in G07)
- line 83: `succ(0,1)`
- line 84: `succ(1,2)`
- line 85: `succ(2,3)`
- line 86: `succ(3,4)`
- line 87: `succ(4,5)`
- line 88: `succ(5,6)`
- line 89: `succ(6,7)`
- line 90: `succ(7,8)`
- line 91: `succ(8,9)`
- line 92: `succ(9,10)`
- line 93: `succ(10,11)`
- line 94: `succ(11,12)`
- line 95: `succ(12,13)`
- line 96: `succ(13,14)`
- line 97: `succ(14,15)`
- line 98: `succ(15,16)`
- line 99: `succ(16,17)`
- line 100: `succ(17,18)`
- line 101: `succ(18,19)`
- line 102: `succ(19,20)`
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G02)

### lgref G01 (19 statements)

- line 27: `index(1)`
- line 28: `index(2)`
- line 29: `index(3)`
- line 30: `index(4)`
- line 31: `up(1,2)`
- line 32: `up(2,3)`
- line 33: `up(3,4)`
- line 40: `straddle(1,2,3)`
- line 41: `straddle(2,3,4)`
- line 42: `straddle(3,2,1)`
- line 43: `straddle(4,3,2)`
- line 44: `orth(X,Y,X2,Y) :- beside(X,X2) & index(Y)` (also in G04)
- line 45: `orth(X,Y,X,Y2) :- index(X) & beside(Y,Y2)` (also in G04)
- line 46: `hop(X,Y,X1,Y,X2,Y) :- straddle(X,X1,X2) & index(Y)`
- line 47: `hop(X,Y,X,Y1,X,Y2) :- index(X) & straddle(Y,Y1,Y2)`
- line 52: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G05)
- line 55: `waddle(X,Y,X,Y2) :- index(X) & up(Y,Y2)`
- line 56: `waddle(X,Y,X2,Y) :- beside(X,X2) & index(Y)` (also in G04)
- line 72: `eaten(X1,Y1) :- does(fox,jump(X,Y,X2,Y2)) & hop(X,Y,X1,Y1,X2,Y2)` (also in G03, G05)

### lgref G02 (14 statements)

- line 76: `next(lost(N)) :- true(lost(N)) & ~feast` (also in G07)
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G00)
- line 109: `stuck(P) :- true(control(P)) & ~mobile(P)` (also in G06)
- line 110: `foxwins :- true(lost(2))` (also in G07)
- line 111: `foxwins :- stuck(geese)`
- line 112: `foxwins :- true(tick(20)) & ~stuck(fox)`
- line 113: `geesewin :- stuck(fox)`
- line 114: `terminal :- foxwins`
- line 115: `terminal :- geesewin`
- line 116: `goal(fox,100) :- foxwins`
- line 117: `goal(geese,0) :- foxwins`
- line 118: `goal(geese,100) :- geesewin`
- line 119: `goal(fox,0) :- geesewin`
- line 128: `init(tick(0))`

### lgref G03 (16 statements)

- line 51: `occupied(X,Y) :- true(fox(X,Y))` (also in G05)
- line 58: `legal(geese,glide(X,Y,X2,Y2)) :- true(control(geese)) & glide(X,Y,X2,Y2)`
- line 59: `glided(X,Y) :- does(geese,glide(X,Y,X2,Y2))` (also in G05)
- line 60: `next(goose(X2,Y2)) :- does(geese,glide(X,Y,X2,Y2))` (also in G05)
- line 64: `stride(X,Y,X2,Y2) :- true(fox(X,Y)) & orth(X,Y,X2,Y2) & empty(X2,Y2)`
- line 65: `legal(fox,step(X,Y,X2,Y2)) :- true(control(fox)) & stride(X,Y,X2,Y2)`
- line 66: `next(fox(X2,Y2)) :- does(fox,step(X,Y,X2,Y2))` (also in G05)
- line 67: `next(fox(X,Y)) :- true(fox(X,Y)) & does(fox,noop)`
- line 70: `leap(X,Y,X2,Y2) :- true(fox(X,Y)) & hop(X,Y,X1,Y1,X2,Y2) & true(goose(X1,Y1)) & empty(X2,Y2)` (also in G05)
- line 71: `legal(fox,jump(X,Y,X2,Y2)) :- true(control(fox)) & leap(X,Y,X2,Y2)`
- line 72: `eaten(X1,Y1) :- does(fox,jump(X,Y,X2,Y2)) & hop(X,Y,X1,Y1,X2,Y2)` (also in G01, G05)
- line 73: `next(fox(X2,Y2)) :- does(fox,jump(X,Y,X2,Y2))` (also in G05)
- line 74: `feast :- does(fox,jump(X,Y,X2,Y2))` (also in G07)
- line 79: `legal(geese,noop) :- true(control(fox))`
- line 80: `legal(fox,noop) :- true(control(geese))`
- line 125: `init(fox(3,4))`

### lgref G04 (9 statements)

- line 34: `beside(1,2)`
- line 35: `beside(2,1)`
- line 36: `beside(2,3)`
- line 37: `beside(3,2)`
- line 38: `beside(3,4)`
- line 39: `beside(4,3)`
- line 44: `orth(X,Y,X2,Y) :- beside(X,X2) & index(Y)` (also in G01)
- line 45: `orth(X,Y,X,Y2) :- index(X) & beside(Y,Y2)` (also in G01)
- line 56: `waddle(X,Y,X2,Y) :- beside(X,X2) & index(Y)` (also in G01)

### lgref G05 (15 statements)

- line 50: `occupied(X,Y) :- true(goose(X,Y))`
- line 51: `occupied(X,Y) :- true(fox(X,Y))` (also in G03)
- line 52: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` (also in G01)
- line 57: `glide(X,Y,X2,Y2) :- true(goose(X,Y)) & waddle(X,Y,X2,Y2) & empty(X2,Y2)`
- line 59: `glided(X,Y) :- does(geese,glide(X,Y,X2,Y2))` (also in G03)
- line 60: `next(goose(X2,Y2)) :- does(geese,glide(X,Y,X2,Y2))` (also in G03)
- line 61: `next(goose(X,Y)) :- true(goose(X,Y)) & ~glided(X,Y) & ~eaten(X,Y)`
- line 66: `next(fox(X2,Y2)) :- does(fox,step(X,Y,X2,Y2))` (also in G03)
- line 70: `leap(X,Y,X2,Y2) :- true(fox(X,Y)) & hop(X,Y,X1,Y1,X2,Y2) & true(goose(X1,Y1)) & empty(X2,Y2)` (also in G03)
- line 72: `eaten(X1,Y1) :- does(fox,jump(X,Y,X2,Y2)) & hop(X,Y,X1,Y1,X2,Y2)` (also in G01, G03)
- line 73: `next(fox(X2,Y2)) :- does(fox,jump(X,Y,X2,Y2))` (also in G03)
- line 121: `init(goose(1,1))`
- line 122: `init(goose(2,1))`
- line 123: `init(goose(3,1))`
- line 124: `init(goose(4,1))`

### lgref G06 (4 statements)

- line 106: `mobile(geese) :- glide(X,Y,X2,Y2)`
- line 107: `mobile(fox) :- stride(X,Y,X2,Y2)`
- line 108: `mobile(fox) :- leap(X,Y,X2,Y2)`
- line 109: `stuck(P) :- true(control(P)) & ~mobile(P)` (also in G02)

### lgref G07 (5 statements)

- line 74: `feast :- does(fox,jump(X,Y,X2,Y2))` (also in G03)
- line 75: `next(lost(N2)) :- true(lost(N)) & feast & succ(N,N2)` (also in G00)
- line 76: `next(lost(N)) :- true(lost(N)) & ~feast` (also in G02)
- line 110: `foxwins :- true(lost(2))` (also in G02)
- line 126: `init(lost(0))`

### lgref G08 (3 statements)

- line 81: `next(control(geese)) :- true(control(fox))`
- line 82: `next(control(fox)) :- true(control(geese))`
- line 127: `init(control(geese))`

### lgref G09 (2 statements)

- line 23: `role(geese)`
- line 24: `role(fox)`


## random_matched by group

### random_matched G00 (22 statements)

- line 23: `role(geese)`
- line 28: `index(2)`
- line 34: `beside(1,2)` (also in G02)
- line 38: `beside(3,4)`
- line 41: `straddle(2,3,4)`
- line 45: `orth(X,Y,X,Y2) :- index(X) & beside(Y,Y2)`
- line 57: `glide(X,Y,X2,Y2) :- true(goose(X,Y)) & waddle(X,Y,X2,Y2) & empty(X2,Y2)`
- line 59: `glided(X,Y) :- does(geese,glide(X,Y,X2,Y2))`
- line 66: `next(fox(X2,Y2)) :- does(fox,step(X,Y,X2,Y2))`
- line 73: `next(fox(X2,Y2)) :- does(fox,jump(X,Y,X2,Y2))`
- line 75: `next(lost(N2)) :- true(lost(N)) & feast & succ(N,N2)`
- line 90: `succ(7,8)`
- line 92: `succ(9,10)`
- line 93: `succ(10,11)`
- line 95: `succ(12,13)`
- line 106: `mobile(geese) :- glide(X,Y,X2,Y2)`
- line 107: `mobile(fox) :- stride(X,Y,X2,Y2)`
- line 118: `goal(geese,100) :- geesewin`
- line 122: `init(goose(2,1))`
- line 125: `init(fox(3,4))`
- line 126: `init(lost(0))`
- line 128: `init(tick(0))` (also in G07)

### random_matched G01 (19 statements)

- line 31: `up(1,2)`
- line 36: `beside(2,3)`
- line 44: `orth(X,Y,X2,Y) :- beside(X,X2) & index(Y)`
- line 46: `hop(X,Y,X1,Y,X2,Y) :- straddle(X,X1,X2) & index(Y)` (also in G03, G05)
- line 47: `hop(X,Y,X,Y1,X,Y2) :- index(X) & straddle(Y,Y1,Y2)`
- line 50: `occupied(X,Y) :- true(goose(X,Y))` (also in G04)
- line 51: `occupied(X,Y) :- true(fox(X,Y))`
- line 55: `waddle(X,Y,X,Y2) :- index(X) & up(Y,Y2)`
- line 58: `legal(geese,glide(X,Y,X2,Y2)) :- true(control(geese)) & glide(X,Y,X2,Y2)`
- line 65: `legal(fox,step(X,Y,X2,Y2)) :- true(control(fox)) & stride(X,Y,X2,Y2)`
- line 70: `leap(X,Y,X2,Y2) :- true(fox(X,Y)) & hop(X,Y,X1,Y1,X2,Y2) & true(goose(X1,Y1)) & empty(X2,Y2)`
- line 74: `feast :- does(fox,jump(X,Y,X2,Y2))`
- line 76: `next(lost(N)) :- true(lost(N)) & ~feast` (also in G04)
- line 79: `legal(geese,noop) :- true(control(fox))`
- line 82: `next(control(fox)) :- true(control(geese))`
- line 87: `succ(4,5)` (also in G05)
- line 89: `succ(6,7)`
- line 113: `geesewin :- stuck(fox)`
- line 127: `init(control(geese))` (also in G04)

### random_matched G02 (14 statements)

- line 34: `beside(1,2)` (also in G00)
- line 37: `beside(3,2)`
- line 42: `straddle(3,2,1)`
- line 56: `waddle(X,Y,X2,Y) :- beside(X,X2) & index(Y)`
- line 61: `next(goose(X,Y)) :- true(goose(X,Y)) & ~glided(X,Y) & ~eaten(X,Y)` (also in G07)
- line 67: `next(fox(X,Y)) :- true(fox(X,Y)) & does(fox,noop)`
- line 80: `legal(fox,noop) :- true(control(geese))`
- line 84: `succ(1,2)`
- line 96: `succ(13,14)`
- line 99: `succ(16,17)`
- line 101: `succ(18,19)` (also in G07)
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G06)
- line 111: `foxwins :- stuck(geese)`
- line 114: `terminal :- foxwins`

### random_matched G03 (16 statements)

- line 27: `index(1)` (also in G05)
- line 29: `index(3)`
- line 39: `beside(4,3)`
- line 40: `straddle(1,2,3)`
- line 46: `hop(X,Y,X1,Y,X2,Y) :- straddle(X,X1,X2) & index(Y)` (also in G01, G05)
- line 60: `next(goose(X2,Y2)) :- does(geese,glide(X,Y,X2,Y2))` (also in G05)
- line 64: `stride(X,Y,X2,Y2) :- true(fox(X,Y)) & orth(X,Y,X2,Y2) & empty(X2,Y2)`
- line 91: `succ(8,9)`
- line 98: `succ(15,16)` (also in G05)
- line 102: `succ(19,20)`
- line 110: `foxwins :- true(lost(2))` (also in G05)
- line 115: `terminal :- geesewin`
- line 119: `goal(fox,0) :- geesewin` (also in G07)
- line 121: `init(goose(1,1))`
- line 123: `init(goose(3,1))` (also in G05)
- line 124: `init(goose(4,1))` (also in G05)

### random_matched G04 (9 statements)

- line 24: `role(fox)`
- line 50: `occupied(X,Y) :- true(goose(X,Y))` (also in G01)
- line 76: `next(lost(N)) :- true(lost(N)) & ~feast` (also in G01)
- line 83: `succ(0,1)`
- line 85: `succ(2,3)`
- line 94: `succ(11,12)`
- line 108: `mobile(fox) :- leap(X,Y,X2,Y2)`
- line 116: `goal(fox,100) :- foxwins`
- line 127: `init(control(geese))` (also in G01)

### random_matched G05 (15 statements)

- line 27: `index(1)` (also in G03)
- line 35: `beside(2,1)`
- line 46: `hop(X,Y,X1,Y,X2,Y) :- straddle(X,X1,X2) & index(Y)` (also in G01, G03)
- line 60: `next(goose(X2,Y2)) :- does(geese,glide(X,Y,X2,Y2))` (also in G03)
- line 71: `legal(fox,jump(X,Y,X2,Y2)) :- true(control(fox)) & leap(X,Y,X2,Y2)`
- line 86: `succ(3,4)`
- line 87: `succ(4,5)` (also in G01)
- line 97: `succ(14,15)`
- line 98: `succ(15,16)` (also in G03)
- line 100: `succ(17,18)`
- line 109: `stuck(P) :- true(control(P)) & ~mobile(P)`
- line 110: `foxwins :- true(lost(2))` (also in G03)
- line 112: `foxwins :- true(tick(20)) & ~stuck(fox)`
- line 123: `init(goose(3,1))` (also in G03)
- line 124: `init(goose(4,1))` (also in G03)

### random_matched G06 (4 statements)

- line 43: `straddle(4,3,2)`
- line 72: `eaten(X1,Y1) :- does(fox,jump(X,Y,X2,Y2)) & hop(X,Y,X1,Y1,X2,Y2)`
- line 103: `next(tick(N2)) :- true(tick(N)) & succ(N,N2)` (also in G02)
- line 117: `goal(geese,0) :- foxwins`

### random_matched G07 (5 statements)

- line 30: `index(4)`
- line 61: `next(goose(X,Y)) :- true(goose(X,Y)) & ~glided(X,Y) & ~eaten(X,Y)` (also in G02)
- line 101: `succ(18,19)` (also in G02)
- line 119: `goal(fox,0) :- geesewin` (also in G03)
- line 128: `init(tick(0))` (also in G00)

### random_matched G08 (3 statements)

- line 52: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)`
- line 81: `next(control(geese)) :- true(control(fox))`
- line 88: `succ(5,6)`

### random_matched G09 (2 statements)

- line 32: `up(2,3)`
- line 33: `up(3,4)`

