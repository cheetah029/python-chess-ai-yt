# othello4 -- groupings

File: `lgref/bench/games/othello4.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 0 statements in no group
- **random_matched**: 8 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 21 | `role(black)` | G04 | G01, G02 |
| 22 | `role(white)` | G04 | G01 |
| 25 | `index(1)` | G02 | G02 |
| 26 | `index(2)` | G02 | G01, G02 |
| 27 | `index(3)` | G02 | G00, G05 |
| 28 | `index(4)` | G02 | G05 |
| 29 | `succ(0,1)` | G01 | G01, G04 |
| 30 | `succ(1,2)` | G01 | G01 |
| 31 | `succ(2,3)` | G01 | G00, G04 |
| 32 | `succ(3,4)` | G01 | G00 |
| 33 | `succ(4,5)` | G01 | G01 |
| 34 | `succ(5,6)` | G01 | G02 |
| 35 | `succ(6,7)` | G01 | G03 |
| 36 | `succ(7,8)` | G01 | G00 |
| 37 | `succ(8,9)` | G01 | G01 |
| 38 | `succ(9,10)` | G01 | G01 |
| 39 | `succ(10,11)` | G01 | G01, G02 |
| 40 | `succ(11,12)` | G01 | G01, G07 |
| 41 | `succ(12,13)` | G01 | G01, G07 |
| 42 | `succ(13,14)` | G01 | G00 |
| 43 | `succ(14,15)` | G01 | G00 |
| 44 | `succ(15,16)` | G01 | G00 |
| 45 | `delta(n,0,1)` | G03 | G00, G02 |
| 46 | `delta(s,0,m)` | G03 | G03 |
| 47 | `delta(e,1,0)` | G03 | G01 |
| 48 | `delta(w,m,0)` | G03 | G03 |
| 49 | `delta(ne,1,1)` | G03 | G03 |
| 50 | `delta(nw,m,1)` | G03 | G00 |
| 51 | `delta(se,1,m)` | G03 | G00 |
| 52 | `delta(sw,m,m)` | G03 | G02 |
| 53 | `shift(A,0,A) :- index(A)` | G02 | G00 |
| 54 | `shift(A,1,B) :- succ(A,B) & index(B)` | G01, G02 | G03 |
| 55 | `shift(A,m,B) :- succ(B,A) & index(B)` | G01, G02 | G01 |
| 56 | `step(X,Y,D,X2,Y2) :- delta(D,DX,DY) & shift(X,DX,X2) & shift(Y,DY,Y2)` | G00, G03 | G05 |
| 57 | `opponent(black,white)` | G00 | G01, G02 |
| 58 | `opponent(white,black)` | G00 | G00, G05 |
| 61 | `occupied(X,Y) :- true(cell(X,Y,C))` | G02 | G01 |
| 62 | `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)` | G02 | G01 |
| 66 | `closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & true(cell(X2,Y2,P))` | G00 | G00 |
| 67 | `closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)` | G00 | G04 |
| 68 | `flanks(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)` | G00 | G01 |
| 69 | `placeable(P,X,Y) :- empty(X,Y) & flanks(P,X,Y,D)` | G00, G02 | G03 |
| 72 | `legal(P,place(X,Y)) :- true(control(P)) & placeable(P,X,Y)` | G00 | G01 |
| 73 | `next(cell(X,Y,P)) :- does(P,place(X,Y))` | G00, G05 | G00, G05 |
| 76 | `flipped(P,X,Y,D,X2,Y2) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)` | G00 | G02 |
| 77 | `flipped(P,X,Y,D,X3,Y3) :- flipped(P,X,Y,D,X2,Y2) & step(X2,Y2,D,X3,Y3) & opponent(P,Q) & true(cell(X3,Y3,Q)) & closes(P,X3,Y3,D)` | G00 | G00 |
| 78 | `flips(A,B) :- does(P,place(X,Y)) & flipped(P,X,Y,D,A,B)` | G00, G05 | G05 |
| 79 | `next(cell(A,B,P)) :- does(P,place(X,Y)) & flips(A,B)` | G00, G05 | G02 |
| 80 | `next(cell(A,B,C)) :- true(cell(A,B,C)) & ~flips(A,B)` | G05 | G04 |
| 83 | `canplace(P) :- placeable(P,X,Y)` | G00 | G06 |
| 84 | `legal(P,pass) :- true(control(P)) & ~canplace(P)` | G00 | G01 |
| 85 | `legal(black,noop) :- true(control(white))` | G00 | G00 |
| 86 | `legal(white,noop) :- true(control(black))` | G00 | G04 |
| 87 | `next(control(white)) :- true(control(black))` | G06 | G05 |
| 88 | `next(control(black)) :- true(control(white))` | G06 | G03 |
| 91 | `after(X,Y,X2,Y) :- succ(X,X2) & index(X2) & index(Y)` | G01, G02 | G01 |
| 92 | `after(4,Y,1,Y2) :- succ(Y,Y2) & index(Y2)` | G01, G02 | G00, G03 |
| 93 | `tally(P,1,1,1) :- true(cell(1,1,P))` | G04 | G06 |
| 94 | `tally(P,1,1,0) :- role(P) & ~true(cell(1,1,P))` | G04 | G03 |
| 95 | `tally(P,X2,Y2,M) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & true(cell(X2,Y2,P)) & succ(N,M)` | G01, G04 | G00 |
| 96 | `tally(P,X2,Y2,N) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & ~true(cell(X2,Y2,P))` | G04 | G02 |
| 97 | `discs(P,N) :- tally(P,4,4,N)` | G00, G04 | G00 |
| 98 | `fewer(N,M) :- succ(N,M)` | G01, G07 | G00 |
| 99 | `fewer(N,M) :- succ(N,K) & fewer(K,M)` | G01, G07 | G02 |
| 100 | `ahead(P) :- opponent(P,Q) & discs(P,M) & discs(Q,N) & fewer(N,M)` | G00 | G00 |
| 101 | `level :- discs(black,N) & discs(white,N)` | G00 | G05 |
| 102 | `terminal :- ~canplace(black) & ~canplace(white)` | G00 | G01 |
| 103 | `goal(P,100) :- ahead(P)` | G00 | G00 |
| 104 | `goal(P,50) :- level` | G00 | G04 |
| 105 | `goal(P,0) :- opponent(P,Q) & ahead(Q)` | G00 | G01 |
| 107 | `init(cell(2,2,white))` | G05 | G06 |
| 108 | `init(cell(3,3,white))` | G05 | G00 |
| 109 | `init(cell(2,3,black))` | G05 | G04 |
| 110 | `init(cell(3,2,black))` | G05 | G01 |
| 111 | `init(control(black))` | G06 | G00 |

## lgref by group

### lgref G00 (24 statements)

- line 56: `step(X,Y,D,X2,Y2) :- delta(D,DX,DY) & shift(X,DX,X2) & shift(Y,DY,Y2)` (also in G03)
- line 57: `opponent(black,white)`
- line 58: `opponent(white,black)`
- line 66: `closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & true(cell(X2,Y2,P))`
- line 67: `closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)`
- line 68: `flanks(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)`
- line 69: `placeable(P,X,Y) :- empty(X,Y) & flanks(P,X,Y,D)` (also in G02)
- line 72: `legal(P,place(X,Y)) :- true(control(P)) & placeable(P,X,Y)`
- line 73: `next(cell(X,Y,P)) :- does(P,place(X,Y))` (also in G05)
- line 76: `flipped(P,X,Y,D,X2,Y2) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)`
- line 77: `flipped(P,X,Y,D,X3,Y3) :- flipped(P,X,Y,D,X2,Y2) & step(X2,Y2,D,X3,Y3) & opponent(P,Q) & true(cell(X3,Y3,Q)) & closes(P,X3,Y3,D)`
- line 78: `flips(A,B) :- does(P,place(X,Y)) & flipped(P,X,Y,D,A,B)` (also in G05)
- line 79: `next(cell(A,B,P)) :- does(P,place(X,Y)) & flips(A,B)` (also in G05)
- line 83: `canplace(P) :- placeable(P,X,Y)`
- line 84: `legal(P,pass) :- true(control(P)) & ~canplace(P)`
- line 85: `legal(black,noop) :- true(control(white))`
- line 86: `legal(white,noop) :- true(control(black))`
- line 97: `discs(P,N) :- tally(P,4,4,N)` (also in G04)
- line 100: `ahead(P) :- opponent(P,Q) & discs(P,M) & discs(Q,N) & fewer(N,M)`
- line 101: `level :- discs(black,N) & discs(white,N)`
- line 102: `terminal :- ~canplace(black) & ~canplace(white)`
- line 103: `goal(P,100) :- ahead(P)`
- line 104: `goal(P,50) :- level`
- line 105: `goal(P,0) :- opponent(P,Q) & ahead(Q)`

### lgref G01 (23 statements)

- line 29: `succ(0,1)`
- line 30: `succ(1,2)`
- line 31: `succ(2,3)`
- line 32: `succ(3,4)`
- line 33: `succ(4,5)`
- line 34: `succ(5,6)`
- line 35: `succ(6,7)`
- line 36: `succ(7,8)`
- line 37: `succ(8,9)`
- line 38: `succ(9,10)`
- line 39: `succ(10,11)`
- line 40: `succ(11,12)`
- line 41: `succ(12,13)`
- line 42: `succ(13,14)`
- line 43: `succ(14,15)`
- line 44: `succ(15,16)`
- line 54: `shift(A,1,B) :- succ(A,B) & index(B)` (also in G02)
- line 55: `shift(A,m,B) :- succ(B,A) & index(B)` (also in G02)
- line 91: `after(X,Y,X2,Y) :- succ(X,X2) & index(X2) & index(Y)` (also in G02)
- line 92: `after(4,Y,1,Y2) :- succ(Y,Y2) & index(Y2)` (also in G02)
- line 95: `tally(P,X2,Y2,M) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & true(cell(X2,Y2,P)) & succ(N,M)` (also in G04)
- line 98: `fewer(N,M) :- succ(N,M)` (also in G07)
- line 99: `fewer(N,M) :- succ(N,K) & fewer(K,M)` (also in G07)

### lgref G02 (12 statements)

- line 25: `index(1)`
- line 26: `index(2)`
- line 27: `index(3)`
- line 28: `index(4)`
- line 53: `shift(A,0,A) :- index(A)`
- line 54: `shift(A,1,B) :- succ(A,B) & index(B)` (also in G01)
- line 55: `shift(A,m,B) :- succ(B,A) & index(B)` (also in G01)
- line 61: `occupied(X,Y) :- true(cell(X,Y,C))`
- line 62: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)`
- line 69: `placeable(P,X,Y) :- empty(X,Y) & flanks(P,X,Y,D)` (also in G00)
- line 91: `after(X,Y,X2,Y) :- succ(X,X2) & index(X2) & index(Y)` (also in G01)
- line 92: `after(4,Y,1,Y2) :- succ(Y,Y2) & index(Y2)` (also in G01)

### lgref G03 (9 statements)

- line 45: `delta(n,0,1)`
- line 46: `delta(s,0,m)`
- line 47: `delta(e,1,0)`
- line 48: `delta(w,m,0)`
- line 49: `delta(ne,1,1)`
- line 50: `delta(nw,m,1)`
- line 51: `delta(se,1,m)`
- line 52: `delta(sw,m,m)`
- line 56: `step(X,Y,D,X2,Y2) :- delta(D,DX,DY) & shift(X,DX,X2) & shift(Y,DY,Y2)` (also in G00)

### lgref G04 (7 statements)

- line 21: `role(black)`
- line 22: `role(white)`
- line 93: `tally(P,1,1,1) :- true(cell(1,1,P))`
- line 94: `tally(P,1,1,0) :- role(P) & ~true(cell(1,1,P))`
- line 95: `tally(P,X2,Y2,M) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & true(cell(X2,Y2,P)) & succ(N,M)` (also in G01)
- line 96: `tally(P,X2,Y2,N) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & ~true(cell(X2,Y2,P))`
- line 97: `discs(P,N) :- tally(P,4,4,N)` (also in G00)

### lgref G05 (8 statements)

- line 73: `next(cell(X,Y,P)) :- does(P,place(X,Y))` (also in G00)
- line 78: `flips(A,B) :- does(P,place(X,Y)) & flipped(P,X,Y,D,A,B)` (also in G00)
- line 79: `next(cell(A,B,P)) :- does(P,place(X,Y)) & flips(A,B)` (also in G00)
- line 80: `next(cell(A,B,C)) :- true(cell(A,B,C)) & ~flips(A,B)`
- line 107: `init(cell(2,2,white))`
- line 108: `init(cell(3,3,white))`
- line 109: `init(cell(2,3,black))`
- line 110: `init(cell(3,2,black))`

### lgref G06 (3 statements)

- line 87: `next(control(white)) :- true(control(black))`
- line 88: `next(control(black)) :- true(control(white))`
- line 111: `init(control(black))`

### lgref G07 (2 statements)

- line 98: `fewer(N,M) :- succ(N,M)` (also in G01)
- line 99: `fewer(N,M) :- succ(N,K) & fewer(K,M)` (also in G01)


## random_matched by group

### random_matched G00 (24 statements)

- line 27: `index(3)` (also in G05)
- line 31: `succ(2,3)` (also in G04)
- line 32: `succ(3,4)`
- line 36: `succ(7,8)`
- line 42: `succ(13,14)`
- line 43: `succ(14,15)`
- line 44: `succ(15,16)`
- line 45: `delta(n,0,1)` (also in G02)
- line 50: `delta(nw,m,1)`
- line 51: `delta(se,1,m)`
- line 53: `shift(A,0,A) :- index(A)`
- line 58: `opponent(white,black)` (also in G05)
- line 66: `closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & true(cell(X2,Y2,P))`
- line 73: `next(cell(X,Y,P)) :- does(P,place(X,Y))` (also in G05)
- line 77: `flipped(P,X,Y,D,X3,Y3) :- flipped(P,X,Y,D,X2,Y2) & step(X2,Y2,D,X3,Y3) & opponent(P,Q) & true(cell(X3,Y3,Q)) & closes(P,X3,Y3,D)`
- line 85: `legal(black,noop) :- true(control(white))`
- line 92: `after(4,Y,1,Y2) :- succ(Y,Y2) & index(Y2)` (also in G03)
- line 95: `tally(P,X2,Y2,M) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & true(cell(X2,Y2,P)) & succ(N,M)`
- line 97: `discs(P,N) :- tally(P,4,4,N)`
- line 98: `fewer(N,M) :- succ(N,M)`
- line 100: `ahead(P) :- opponent(P,Q) & discs(P,M) & discs(Q,N) & fewer(N,M)`
- line 103: `goal(P,100) :- ahead(P)`
- line 108: `init(cell(3,3,white))`
- line 111: `init(control(black))`

### random_matched G01 (23 statements)

- line 21: `role(black)` (also in G02)
- line 22: `role(white)`
- line 26: `index(2)` (also in G02)
- line 29: `succ(0,1)` (also in G04)
- line 30: `succ(1,2)`
- line 33: `succ(4,5)`
- line 37: `succ(8,9)`
- line 38: `succ(9,10)`
- line 39: `succ(10,11)` (also in G02)
- line 40: `succ(11,12)` (also in G07)
- line 41: `succ(12,13)` (also in G07)
- line 47: `delta(e,1,0)`
- line 55: `shift(A,m,B) :- succ(B,A) & index(B)`
- line 57: `opponent(black,white)` (also in G02)
- line 61: `occupied(X,Y) :- true(cell(X,Y,C))`
- line 62: `empty(X,Y) :- index(X) & index(Y) & ~occupied(X,Y)`
- line 68: `flanks(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)`
- line 72: `legal(P,place(X,Y)) :- true(control(P)) & placeable(P,X,Y)`
- line 84: `legal(P,pass) :- true(control(P)) & ~canplace(P)`
- line 91: `after(X,Y,X2,Y) :- succ(X,X2) & index(X2) & index(Y)`
- line 102: `terminal :- ~canplace(black) & ~canplace(white)`
- line 105: `goal(P,0) :- opponent(P,Q) & ahead(Q)`
- line 110: `init(cell(3,2,black))`

### random_matched G02 (12 statements)

- line 21: `role(black)` (also in G01)
- line 25: `index(1)`
- line 26: `index(2)` (also in G01)
- line 34: `succ(5,6)`
- line 39: `succ(10,11)` (also in G01)
- line 45: `delta(n,0,1)` (also in G00)
- line 52: `delta(sw,m,m)`
- line 57: `opponent(black,white)` (also in G01)
- line 76: `flipped(P,X,Y,D,X2,Y2) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)`
- line 79: `next(cell(A,B,P)) :- does(P,place(X,Y)) & flips(A,B)`
- line 96: `tally(P,X2,Y2,N) :- after(X,Y,X2,Y2) & tally(P,X,Y,N) & ~true(cell(X2,Y2,P))`
- line 99: `fewer(N,M) :- succ(N,K) & fewer(K,M)`

### random_matched G03 (9 statements)

- line 35: `succ(6,7)`
- line 46: `delta(s,0,m)`
- line 48: `delta(w,m,0)`
- line 49: `delta(ne,1,1)`
- line 54: `shift(A,1,B) :- succ(A,B) & index(B)`
- line 69: `placeable(P,X,Y) :- empty(X,Y) & flanks(P,X,Y,D)`
- line 88: `next(control(black)) :- true(control(white))`
- line 92: `after(4,Y,1,Y2) :- succ(Y,Y2) & index(Y2)` (also in G00)
- line 94: `tally(P,1,1,0) :- role(P) & ~true(cell(1,1,P))`

### random_matched G04 (7 statements)

- line 29: `succ(0,1)` (also in G01)
- line 31: `succ(2,3)` (also in G00)
- line 67: `closes(P,X,Y,D) :- step(X,Y,D,X2,Y2) & opponent(P,Q) & true(cell(X2,Y2,Q)) & closes(P,X2,Y2,D)`
- line 80: `next(cell(A,B,C)) :- true(cell(A,B,C)) & ~flips(A,B)`
- line 86: `legal(white,noop) :- true(control(black))`
- line 104: `goal(P,50) :- level`
- line 109: `init(cell(2,3,black))`

### random_matched G05 (8 statements)

- line 27: `index(3)` (also in G00)
- line 28: `index(4)`
- line 56: `step(X,Y,D,X2,Y2) :- delta(D,DX,DY) & shift(X,DX,X2) & shift(Y,DY,Y2)`
- line 58: `opponent(white,black)` (also in G00)
- line 73: `next(cell(X,Y,P)) :- does(P,place(X,Y))` (also in G00)
- line 78: `flips(A,B) :- does(P,place(X,Y)) & flipped(P,X,Y,D,A,B)`
- line 87: `next(control(white)) :- true(control(black))`
- line 101: `level :- discs(black,N) & discs(white,N)`

### random_matched G06 (3 statements)

- line 83: `canplace(P) :- placeable(P,X,Y)`
- line 93: `tally(P,1,1,1) :- true(cell(1,1,P))`
- line 107: `init(cell(2,2,white))`

### random_matched G07 (2 statements)

- line 40: `succ(11,12)` (also in G01)
- line 41: `succ(12,13)` (also in G01)

