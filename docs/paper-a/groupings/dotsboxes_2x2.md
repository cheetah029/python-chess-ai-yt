# dotsboxes_2x2 -- groupings

File: `lgref/bench/games/dotsboxes_2x2.gdl`. Line numbers are lines of that file.

- **lgref**: 7 groups, 3 statements in no group
- **random_matched**: 7 groups, 3 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 21 | `role(a)` | G06 | G00 |
| 22 | `role(b)` | G06 | G00 |
| 25 | `line(h(1,1))` | G00 | G01 |
| 26 | `line(h(2,1))` | G00 | G03 |
| 27 | `line(h(1,2))` | G00 | G00 |
| 28 | `line(h(2,2))` | G00 | G00 |
| 29 | `line(h(1,3))` | G00 | G02 |
| 30 | `line(h(2,3))` | G00 | G00 |
| 31 | `line(v(1,1))` | G00 | - |
| 32 | `line(v(2,1))` | G00 | G00, G05 |
| 33 | `line(v(3,1))` | G00 | G03 |
| 34 | `line(v(1,2))` | G00 | G02 |
| 35 | `line(v(2,2))` | G00 | G06 |
| 36 | `line(v(3,2))` | G00 | G01, G03, G04, G05 |
| 37 | `bounds(h(I,J),b(I,J)) :- box(I,J)` | G02 | G02, G03 |
| 38 | `bounds(h(I,J2),b(I,J)) :- box(I,J) & succ(J,J2)` | G02, G03 | G03 |
| 39 | `bounds(v(I,J),b(I,J)) :- box(I,J)` | G02 | G01 |
| 40 | `bounds(v(I2,J),b(I,J)) :- box(I,J) & succ(I,I2)` | G02, G03 | G03 |
| 41 | `box(1,1)` | G02 | - |
| 42 | `box(1,2)` | G02 | G01, G05 |
| 43 | `box(2,1)` | G02 | G02 |
| 44 | `box(2,2)` | G02 | G04 |
| 45 | `succ(0,1)` | G03 | G01, G05 |
| 46 | `succ(1,2)` | G03 | G01, G03 |
| 47 | `succ(2,3)` | G03 | G01 |
| 48 | `succ(3,4)` | G03 | G01, G03, G05 |
| 49 | `plus2(0,2)` | G04 | G01 |
| 50 | `plus2(1,3)` | G04 | G04 |
| 51 | `plus2(2,4)` | G04 | G04 |
| 52 | `more(A,B) :- succ(B,A)` | G01, G03 | G06 |
| 53 | `more(A,C) :- succ(B,A) & more(B,C)` | G01, G03 | G05 |
| 54 | `opponent(a,b)` | G01 | G00, G01 |
| 55 | `opponent(b,a)` | G01 | G01 |
| 58 | `legal(P,draw(L)) :- true(control(P)) & line(L) & ~true(drawn(L))` | G00, G05 | G00 |
| 59 | `next(drawn(L)) :- does(P,draw(L))` | G05 | G05 |
| 60 | `next(drawn(L)) :- true(drawn(L))` | - | G00 |
| 63 | `gap(L,B) :- bounds(L2,B) & distinct(L2,L) & ~true(drawn(L2))` | G02 | G01 |
| 64 | `closes(B) :- does(P,draw(L)) & bounds(L,B) & ~gap(L,B)` | G02, G05 | G01 |
| 65 | `completed :- closes(B)` | - | G00 |
| 66 | `double :- closes(B) & closes(B2) & distinct(B,B2)` | - | G02, G05 |
| 69 | `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & completed & ~double & succ(N,N2)` | G01, G03, G05 | G00 |
| 70 | `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)` | G01, G03, G04, G05 | G02 |
| 71 | `next(score(P,N)) :- true(score(P,N)) & ~scorer(P)` | G01 | G00 |
| 72 | `scorer(P) :- does(P,draw(L)) & completed` | G01, G05 | G00 |
| 75 | `next(control(P)) :- does(P,draw(L)) & completed` | G05 | G02, G03 |
| 78 | `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` | G01, G05 | G01 |
| 79 | `next(control(Q)) :- does(P,draw(L)) & ~completed & opponent(P,Q)` | G01, G03, G05 | G02 |
| 82 | `undrawn :- line(L) & ~true(drawn(L))` | G00, G01 | G02 |
| 83 | `terminal :- ~undrawn` | G01 | G01 |
| 84 | `goal(P,100) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(N,M)` | G01 | - |
| 85 | `goal(P,50) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,N))` | G01 | G01, G03 |
| 86 | `goal(P,0) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(M,N)` | G01 | G00 |
| 88 | `init(score(a,0))` | G01 | G01, G03, G05 |
| 89 | `init(score(b,0))` | G01 | G02 |
| 90 | `init(control(a))` | G05 | G05 |

## lgref by group

### lgref G00 (14 statements)

- line 25: `line(h(1,1))`
- line 26: `line(h(2,1))`
- line 27: `line(h(1,2))`
- line 28: `line(h(2,2))`
- line 29: `line(h(1,3))`
- line 30: `line(h(2,3))`
- line 31: `line(v(1,1))`
- line 32: `line(v(2,1))`
- line 33: `line(v(3,1))`
- line 34: `line(v(1,2))`
- line 35: `line(v(2,2))`
- line 36: `line(v(3,2))`
- line 58: `legal(P,draw(L)) :- true(control(P)) & line(L) & ~true(drawn(L))` (also in G05)
- line 82: `undrawn :- line(L) & ~true(drawn(L))` (also in G01)

### lgref G01 (17 statements)

- line 52: `more(A,B) :- succ(B,A)` (also in G03)
- line 53: `more(A,C) :- succ(B,A) & more(B,C)` (also in G03)
- line 54: `opponent(a,b)`
- line 55: `opponent(b,a)`
- line 69: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & completed & ~double & succ(N,N2)` (also in G03, G05)
- line 70: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)` (also in G03, G04, G05)
- line 71: `next(score(P,N)) :- true(score(P,N)) & ~scorer(P)`
- line 72: `scorer(P) :- does(P,draw(L)) & completed` (also in G05)
- line 78: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` (also in G05)
- line 79: `next(control(Q)) :- does(P,draw(L)) & ~completed & opponent(P,Q)` (also in G03, G05)
- line 82: `undrawn :- line(L) & ~true(drawn(L))` (also in G00)
- line 83: `terminal :- ~undrawn`
- line 84: `goal(P,100) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(N,M)`
- line 85: `goal(P,50) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,N))`
- line 86: `goal(P,0) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(M,N)`
- line 88: `init(score(a,0))`
- line 89: `init(score(b,0))`

### lgref G02 (10 statements)

- line 37: `bounds(h(I,J),b(I,J)) :- box(I,J)`
- line 38: `bounds(h(I,J2),b(I,J)) :- box(I,J) & succ(J,J2)` (also in G03)
- line 39: `bounds(v(I,J),b(I,J)) :- box(I,J)`
- line 40: `bounds(v(I2,J),b(I,J)) :- box(I,J) & succ(I,I2)` (also in G03)
- line 41: `box(1,1)`
- line 42: `box(1,2)`
- line 43: `box(2,1)`
- line 44: `box(2,2)`
- line 63: `gap(L,B) :- bounds(L2,B) & distinct(L2,L) & ~true(drawn(L2))`
- line 64: `closes(B) :- does(P,draw(L)) & bounds(L,B) & ~gap(L,B)` (also in G05)

### lgref G03 (11 statements)

- line 38: `bounds(h(I,J2),b(I,J)) :- box(I,J) & succ(J,J2)` (also in G02)
- line 40: `bounds(v(I2,J),b(I,J)) :- box(I,J) & succ(I,I2)` (also in G02)
- line 45: `succ(0,1)`
- line 46: `succ(1,2)`
- line 47: `succ(2,3)`
- line 48: `succ(3,4)`
- line 52: `more(A,B) :- succ(B,A)` (also in G01)
- line 53: `more(A,C) :- succ(B,A) & more(B,C)` (also in G01)
- line 69: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & completed & ~double & succ(N,N2)` (also in G01, G05)
- line 70: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)` (also in G01, G04, G05)
- line 79: `next(control(Q)) :- does(P,draw(L)) & ~completed & opponent(P,Q)` (also in G01, G05)

### lgref G04 (4 statements)

- line 49: `plus2(0,2)`
- line 50: `plus2(1,3)`
- line 51: `plus2(2,4)`
- line 70: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)` (also in G01, G03, G05)

### lgref G05 (10 statements)

- line 58: `legal(P,draw(L)) :- true(control(P)) & line(L) & ~true(drawn(L))` (also in G00)
- line 59: `next(drawn(L)) :- does(P,draw(L))`
- line 64: `closes(B) :- does(P,draw(L)) & bounds(L,B) & ~gap(L,B)` (also in G02)
- line 69: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & completed & ~double & succ(N,N2)` (also in G01, G03)
- line 70: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)` (also in G01, G03, G04)
- line 72: `scorer(P) :- does(P,draw(L)) & completed` (also in G01)
- line 75: `next(control(P)) :- does(P,draw(L)) & completed`
- line 78: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` (also in G01)
- line 79: `next(control(Q)) :- does(P,draw(L)) & ~completed & opponent(P,Q)` (also in G01, G03)
- line 90: `init(control(a))`

### lgref G06 (2 statements)

- line 21: `role(a)`
- line 22: `role(b)`

### lgref: statements in no group

- line 60: `next(drawn(L)) :- true(drawn(L))`
- line 65: `completed :- closes(B)`
- line 66: `double :- closes(B) & closes(B2) & distinct(B,B2)`


## random_matched by group

### random_matched G00 (14 statements)

- line 21: `role(a)`
- line 22: `role(b)`
- line 27: `line(h(1,2))`
- line 28: `line(h(2,2))`
- line 30: `line(h(2,3))`
- line 32: `line(v(2,1))` (also in G05)
- line 54: `opponent(a,b)` (also in G01)
- line 58: `legal(P,draw(L)) :- true(control(P)) & line(L) & ~true(drawn(L))`
- line 60: `next(drawn(L)) :- true(drawn(L))`
- line 65: `completed :- closes(B)`
- line 69: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & completed & ~double & succ(N,N2)`
- line 71: `next(score(P,N)) :- true(score(P,N)) & ~scorer(P)`
- line 72: `scorer(P) :- does(P,draw(L)) & completed`
- line 86: `goal(P,0) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(M,N)`

### random_matched G01 (17 statements)

- line 25: `line(h(1,1))`
- line 36: `line(v(3,2))` (also in G03, G04, G05)
- line 39: `bounds(v(I,J),b(I,J)) :- box(I,J)`
- line 42: `box(1,2)` (also in G05)
- line 45: `succ(0,1)` (also in G05)
- line 46: `succ(1,2)` (also in G03)
- line 47: `succ(2,3)`
- line 48: `succ(3,4)` (also in G03, G05)
- line 49: `plus2(0,2)`
- line 54: `opponent(a,b)` (also in G00)
- line 55: `opponent(b,a)`
- line 63: `gap(L,B) :- bounds(L2,B) & distinct(L2,L) & ~true(drawn(L2))`
- line 64: `closes(B) :- does(P,draw(L)) & bounds(L,B) & ~gap(L,B)`
- line 78: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)`
- line 83: `terminal :- ~undrawn`
- line 85: `goal(P,50) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,N))` (also in G03)
- line 88: `init(score(a,0))` (also in G03, G05)

### random_matched G02 (10 statements)

- line 29: `line(h(1,3))`
- line 34: `line(v(1,2))`
- line 37: `bounds(h(I,J),b(I,J)) :- box(I,J)` (also in G03)
- line 43: `box(2,1)`
- line 66: `double :- closes(B) & closes(B2) & distinct(B,B2)` (also in G05)
- line 70: `next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)`
- line 75: `next(control(P)) :- does(P,draw(L)) & completed` (also in G03)
- line 79: `next(control(Q)) :- does(P,draw(L)) & ~completed & opponent(P,Q)`
- line 82: `undrawn :- line(L) & ~true(drawn(L))`
- line 89: `init(score(b,0))`

### random_matched G03 (11 statements)

- line 26: `line(h(2,1))`
- line 33: `line(v(3,1))`
- line 36: `line(v(3,2))` (also in G01, G04, G05)
- line 37: `bounds(h(I,J),b(I,J)) :- box(I,J)` (also in G02)
- line 38: `bounds(h(I,J2),b(I,J)) :- box(I,J) & succ(J,J2)`
- line 40: `bounds(v(I2,J),b(I,J)) :- box(I,J) & succ(I,I2)`
- line 46: `succ(1,2)` (also in G01)
- line 48: `succ(3,4)` (also in G01, G05)
- line 75: `next(control(P)) :- does(P,draw(L)) & completed` (also in G02)
- line 85: `goal(P,50) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,N))` (also in G01)
- line 88: `init(score(a,0))` (also in G01, G05)

### random_matched G04 (4 statements)

- line 36: `line(v(3,2))` (also in G01, G03, G05)
- line 44: `box(2,2)`
- line 50: `plus2(1,3)`
- line 51: `plus2(2,4)`

### random_matched G05 (10 statements)

- line 32: `line(v(2,1))` (also in G00)
- line 36: `line(v(3,2))` (also in G01, G03, G04)
- line 42: `box(1,2)` (also in G01)
- line 45: `succ(0,1)` (also in G01)
- line 48: `succ(3,4)` (also in G01, G03)
- line 53: `more(A,C) :- succ(B,A) & more(B,C)`
- line 59: `next(drawn(L)) :- does(P,draw(L))`
- line 66: `double :- closes(B) & closes(B2) & distinct(B,B2)` (also in G02)
- line 88: `init(score(a,0))` (also in G01, G03)
- line 90: `init(control(a))`

### random_matched G06 (2 statements)

- line 35: `line(v(2,2))`
- line 52: `more(A,B) :- succ(B,A)`

### random_matched: statements in no group

- line 31: `line(v(1,1))`
- line 41: `box(1,1)`
- line 84: `goal(P,100) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(N,M)`

