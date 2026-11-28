# skirmish -- groupings

File: `lgref/identify/testgames/skirmish.gdl`. Line numbers are lines of that file.

- **lgref**: 16 groups, 0 statements in no group
- **random_matched**: 16 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 18 | `role(white)` | G04 | G02, G05 |
| 19 | `role(black)` | G04 | G01, G02 |
| 22 | `coord(1)` | G05 | G03 |
| 23 | `coord(2)` | G05 | G05 |
| 24 | `coord(3)` | G05 | G01, G03 |
| 25 | `coord(4)` | G05 | G08 |
| 26 | `succ(1,2)` | G08 | G07, G10 |
| 27 | `succ(2,3)` | G08 | G08 |
| 28 | `succ(3,4)` | G08 | G00 |
| 33 | `occupied(X,Y) :- true(at(P,T,X,Y))` | G11 | G01 |
| 34 | `empty(X,Y) :- coord(X) & coord(Y) & ~occupied(X,Y)` | G05, G11 | G06 |
| 37 | `enemy_at(P,X,Y) :- true(at(Q,T,X,Y)) & distinct(P,Q)` | G01 | G06 |
| 38 | `struck(U,V) :- does(P,move(T,X,Y,U,V))` | G01, G03 | G01, G02 |
| 41 | `close(A,B) :- succ(A,B)` | G02, G08 | G00 |
| 42 | `close(A,B) :- succ(B,A)` | G02, G08 | G05, G08, G13 |
| 43 | `kingstep(X,Y,U,V) :- close(X,U) & close(Y,V)` | G01, G02 | G08, G13 |
| 44 | `kingstep(X,Y,U,Y) :- close(X,U) & coord(Y)` | G02, G05 | G07, G10 |
| 45 | `kingstep(X,Y,X,V) :- coord(X) & close(Y,V)` | G02, G05 | G05, G08, G14 |
| 46 | `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)` | G01, G02 | G04, G07, G10 |
| 47 | `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & enemy_at(P,U,V)` | G01, G02 | G00 |
| 50 | `north(X,Y,X,V) :- coord(X) & succ(Y,V)` | G05, G08, G12 | G05, G08, G15 |
| 51 | `north(X,Y,X,V) :- succ(Y,W) & empty(X,W) & north(X,W,X,V)` | G08, G12 | G01, G06 |
| 52 | `south(X,Y,X,V) :- coord(X) & succ(V,Y)` | G05, G08, G13 | G00 |
| 53 | `south(X,Y,X,V) :- succ(W,Y) & empty(X,W) & south(X,W,X,V)` | G08, G13 | G01, G03 |
| 54 | `east(X,Y,U,Y) :- coord(Y) & succ(X,U)` | G05, G08, G14 | G09 |
| 55 | `east(X,Y,U,Y) :- succ(X,W) & empty(W,Y) & east(W,Y,U,Y)` | G08, G14 | G00, G07 |
| 56 | `west(X,Y,U,Y) :- coord(Y) & succ(U,X)` | G05, G08, G15 | G03 |
| 57 | `west(X,Y,U,Y) :- succ(W,X) & empty(W,Y) & west(W,Y,U,Y)` | G08, G15 | G08 |
| 58 | `slide(X,Y,U,V) :- north(X,Y,U,V)` | G06 | G01 |
| 59 | `slide(X,Y,U,V) :- south(X,Y,U,V)` | G06 | G02, G08 |
| 60 | `slide(X,Y,U,V) :- east(X,Y,U,V)` | G06 | G00 |
| 61 | `slide(X,Y,U,V) :- west(X,Y,U,V)` | G06 | G07 |
| 62 | `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & empty(U,V)` | G01, G06 | G07 |
| 63 | `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & enemy_at(P,U,V)` | G01, G06 | G05 |
| 66 | `vacated(X,Y) :- does(P,move(T,X,Y,U,V))` | G01, G03 | G09 |
| 67 | `next(at(P,T,U,V)) :- does(P,move(T,X,Y,U,V))` | G01, G03 | G06 |
| 68 | `next(at(Q,S,A,B)) :- true(at(Q,S,A,B)) & ~vacated(A,B) & ~struck(A,B)` | G03 | G08, G15 |
| 71 | `legal(white,noop) :- true(control(black))` | G01 | G00 |
| 72 | `legal(black,noop) :- true(control(white))` | G01 | G01 |
| 73 | `next(control(white)) :- true(control(black))` | G09 | G07, G10 |
| 74 | `next(control(black)) :- true(control(white))` | G09 | G08, G12 |
| 77 | `opponent(white,black)` | G07, G10 | G04 |
| 78 | `opponent(black,white)` | G07, G10 | G01, G03 |
| 79 | `hasguard(P) :- true(at(P,guard,X,Y))` | G04 | G05, G08, G12 |
| 80 | `guardless(P) :- role(P) & ~hasguard(P)` | G04, G07, G10 | G11 |
| 81 | `tsucc(0,1)` | G00 | G04 |
| 82 | `tsucc(1,2)` | G00 | G02, G08 |
| 83 | `tsucc(2,3)` | G00 | G06 |
| 84 | `tsucc(3,4)` | G00 | G03 |
| 85 | `tsucc(4,5)` | G00 | G05, G11 |
| 86 | `tsucc(5,6)` | G00 | G00 |
| 87 | `tsucc(6,7)` | G00 | G03 |
| 88 | `tsucc(7,8)` | G00 | G01, G06 |
| 89 | `next(tick(N)) :- true(tick(M)) & tsucc(M,N)` | G00, G07 | G04 |
| 90 | `terminal :- guardless(P)` | G07 | G07 |
| 91 | `terminal :- true(tick(8))` | G07 | G00 |
| 92 | `goal(P,100) :- opponent(P,Q) & guardless(Q)` | G07, G10 | G03 |
| 94 | `init(at(white,guard,1,1))` | G03 | G02, G05 |
| 95 | `init(at(white,lancer,2,1))` | G03 | G05 |
| 96 | `init(at(black,guard,4,4))` | G03 | G09 |
| 97 | `init(at(black,lancer,3,4))` | G03 | G05 |
| 98 | `init(control(white))` | G09 | G01, G02 |
| 99 | `init(tick(0))` | G07 | G08, G14 |

## lgref by group

### lgref G00 (9 statements)

- line 81: `tsucc(0,1)`
- line 82: `tsucc(1,2)`
- line 83: `tsucc(2,3)`
- line 84: `tsucc(3,4)`
- line 85: `tsucc(4,5)`
- line 86: `tsucc(5,6)`
- line 87: `tsucc(6,7)`
- line 88: `tsucc(7,8)`
- line 89: `next(tick(N)) :- true(tick(M)) & tsucc(M,N)` (also in G07)

### lgref G01 (11 statements)

- line 37: `enemy_at(P,X,Y) :- true(at(Q,T,X,Y)) & distinct(P,Q)`
- line 38: `struck(U,V) :- does(P,move(T,X,Y,U,V))` (also in G03)
- line 43: `kingstep(X,Y,U,V) :- close(X,U) & close(Y,V)` (also in G02)
- line 46: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)` (also in G02)
- line 47: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & enemy_at(P,U,V)` (also in G02)
- line 62: `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & empty(U,V)` (also in G06)
- line 63: `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & enemy_at(P,U,V)` (also in G06)
- line 66: `vacated(X,Y) :- does(P,move(T,X,Y,U,V))` (also in G03)
- line 67: `next(at(P,T,U,V)) :- does(P,move(T,X,Y,U,V))` (also in G03)
- line 71: `legal(white,noop) :- true(control(black))`
- line 72: `legal(black,noop) :- true(control(white))`

### lgref G02 (7 statements)

- line 41: `close(A,B) :- succ(A,B)` (also in G08)
- line 42: `close(A,B) :- succ(B,A)` (also in G08)
- line 43: `kingstep(X,Y,U,V) :- close(X,U) & close(Y,V)` (also in G01)
- line 44: `kingstep(X,Y,U,Y) :- close(X,U) & coord(Y)` (also in G05)
- line 45: `kingstep(X,Y,X,V) :- coord(X) & close(Y,V)` (also in G05)
- line 46: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)` (also in G01)
- line 47: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & enemy_at(P,U,V)` (also in G01)

### lgref G03 (8 statements)

- line 38: `struck(U,V) :- does(P,move(T,X,Y,U,V))` (also in G01)
- line 66: `vacated(X,Y) :- does(P,move(T,X,Y,U,V))` (also in G01)
- line 67: `next(at(P,T,U,V)) :- does(P,move(T,X,Y,U,V))` (also in G01)
- line 68: `next(at(Q,S,A,B)) :- true(at(Q,S,A,B)) & ~vacated(A,B) & ~struck(A,B)`
- line 94: `init(at(white,guard,1,1))`
- line 95: `init(at(white,lancer,2,1))`
- line 96: `init(at(black,guard,4,4))`
- line 97: `init(at(black,lancer,3,4))`

### lgref G04 (4 statements)

- line 18: `role(white)`
- line 19: `role(black)`
- line 79: `hasguard(P) :- true(at(P,guard,X,Y))`
- line 80: `guardless(P) :- role(P) & ~hasguard(P)` (also in G07, G10)

### lgref G05 (11 statements)

- line 22: `coord(1)`
- line 23: `coord(2)`
- line 24: `coord(3)`
- line 25: `coord(4)`
- line 34: `empty(X,Y) :- coord(X) & coord(Y) & ~occupied(X,Y)` (also in G11)
- line 44: `kingstep(X,Y,U,Y) :- close(X,U) & coord(Y)` (also in G02)
- line 45: `kingstep(X,Y,X,V) :- coord(X) & close(Y,V)` (also in G02)
- line 50: `north(X,Y,X,V) :- coord(X) & succ(Y,V)` (also in G08, G12)
- line 52: `south(X,Y,X,V) :- coord(X) & succ(V,Y)` (also in G08, G13)
- line 54: `east(X,Y,U,Y) :- coord(Y) & succ(X,U)` (also in G08, G14)
- line 56: `west(X,Y,U,Y) :- coord(Y) & succ(U,X)` (also in G08, G15)

### lgref G06 (6 statements)

- line 58: `slide(X,Y,U,V) :- north(X,Y,U,V)`
- line 59: `slide(X,Y,U,V) :- south(X,Y,U,V)`
- line 60: `slide(X,Y,U,V) :- east(X,Y,U,V)`
- line 61: `slide(X,Y,U,V) :- west(X,Y,U,V)`
- line 62: `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & empty(U,V)` (also in G01)
- line 63: `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & enemy_at(P,U,V)` (also in G01)

### lgref G07 (8 statements)

- line 77: `opponent(white,black)` (also in G10)
- line 78: `opponent(black,white)` (also in G10)
- line 80: `guardless(P) :- role(P) & ~hasguard(P)` (also in G04, G10)
- line 89: `next(tick(N)) :- true(tick(M)) & tsucc(M,N)` (also in G00)
- line 90: `terminal :- guardless(P)`
- line 91: `terminal :- true(tick(8))`
- line 92: `goal(P,100) :- opponent(P,Q) & guardless(Q)` (also in G10)
- line 99: `init(tick(0))`

### lgref G08 (13 statements)

- line 26: `succ(1,2)`
- line 27: `succ(2,3)`
- line 28: `succ(3,4)`
- line 41: `close(A,B) :- succ(A,B)` (also in G02)
- line 42: `close(A,B) :- succ(B,A)` (also in G02)
- line 50: `north(X,Y,X,V) :- coord(X) & succ(Y,V)` (also in G05, G12)
- line 51: `north(X,Y,X,V) :- succ(Y,W) & empty(X,W) & north(X,W,X,V)` (also in G12)
- line 52: `south(X,Y,X,V) :- coord(X) & succ(V,Y)` (also in G05, G13)
- line 53: `south(X,Y,X,V) :- succ(W,Y) & empty(X,W) & south(X,W,X,V)` (also in G13)
- line 54: `east(X,Y,U,Y) :- coord(Y) & succ(X,U)` (also in G05, G14)
- line 55: `east(X,Y,U,Y) :- succ(X,W) & empty(W,Y) & east(W,Y,U,Y)` (also in G14)
- line 56: `west(X,Y,U,Y) :- coord(Y) & succ(U,X)` (also in G05, G15)
- line 57: `west(X,Y,U,Y) :- succ(W,X) & empty(W,Y) & west(W,Y,U,Y)` (also in G15)

### lgref G09 (3 statements)

- line 73: `next(control(white)) :- true(control(black))`
- line 74: `next(control(black)) :- true(control(white))`
- line 98: `init(control(white))`

### lgref G10 (4 statements)

- line 77: `opponent(white,black)` (also in G07)
- line 78: `opponent(black,white)` (also in G07)
- line 80: `guardless(P) :- role(P) & ~hasguard(P)` (also in G04, G07)
- line 92: `goal(P,100) :- opponent(P,Q) & guardless(Q)` (also in G07)

### lgref G11 (2 statements)

- line 33: `occupied(X,Y) :- true(at(P,T,X,Y))`
- line 34: `empty(X,Y) :- coord(X) & coord(Y) & ~occupied(X,Y)` (also in G05)

### lgref G12 (2 statements)

- line 50: `north(X,Y,X,V) :- coord(X) & succ(Y,V)` (also in G05, G08)
- line 51: `north(X,Y,X,V) :- succ(Y,W) & empty(X,W) & north(X,W,X,V)` (also in G08)

### lgref G13 (2 statements)

- line 52: `south(X,Y,X,V) :- coord(X) & succ(V,Y)` (also in G05, G08)
- line 53: `south(X,Y,X,V) :- succ(W,Y) & empty(X,W) & south(X,W,X,V)` (also in G08)

### lgref G14 (2 statements)

- line 54: `east(X,Y,U,Y) :- coord(Y) & succ(X,U)` (also in G05, G08)
- line 55: `east(X,Y,U,Y) :- succ(X,W) & empty(W,Y) & east(W,Y,U,Y)` (also in G08)

### lgref G15 (2 statements)

- line 56: `west(X,Y,U,Y) :- coord(Y) & succ(U,X)` (also in G05, G08)
- line 57: `west(X,Y,U,Y) :- succ(W,X) & empty(W,Y) & west(W,Y,U,Y)` (also in G08)


## random_matched by group

### random_matched G00 (9 statements)

- line 28: `succ(3,4)`
- line 41: `close(A,B) :- succ(A,B)`
- line 47: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & enemy_at(P,U,V)`
- line 52: `south(X,Y,X,V) :- coord(X) & succ(V,Y)`
- line 55: `east(X,Y,U,Y) :- succ(X,W) & empty(W,Y) & east(W,Y,U,Y)` (also in G07)
- line 60: `slide(X,Y,U,V) :- east(X,Y,U,V)`
- line 71: `legal(white,noop) :- true(control(black))`
- line 86: `tsucc(5,6)`
- line 91: `terminal :- true(tick(8))`

### random_matched G01 (11 statements)

- line 19: `role(black)` (also in G02)
- line 24: `coord(3)` (also in G03)
- line 33: `occupied(X,Y) :- true(at(P,T,X,Y))`
- line 38: `struck(U,V) :- does(P,move(T,X,Y,U,V))` (also in G02)
- line 51: `north(X,Y,X,V) :- succ(Y,W) & empty(X,W) & north(X,W,X,V)` (also in G06)
- line 53: `south(X,Y,X,V) :- succ(W,Y) & empty(X,W) & south(X,W,X,V)` (also in G03)
- line 58: `slide(X,Y,U,V) :- north(X,Y,U,V)`
- line 72: `legal(black,noop) :- true(control(white))`
- line 78: `opponent(black,white)` (also in G03)
- line 88: `tsucc(7,8)` (also in G06)
- line 98: `init(control(white))` (also in G02)

### random_matched G02 (7 statements)

- line 18: `role(white)` (also in G05)
- line 19: `role(black)` (also in G01)
- line 38: `struck(U,V) :- does(P,move(T,X,Y,U,V))` (also in G01)
- line 59: `slide(X,Y,U,V) :- south(X,Y,U,V)` (also in G08)
- line 82: `tsucc(1,2)` (also in G08)
- line 94: `init(at(white,guard,1,1))` (also in G05)
- line 98: `init(control(white))` (also in G01)

### random_matched G03 (8 statements)

- line 22: `coord(1)`
- line 24: `coord(3)` (also in G01)
- line 53: `south(X,Y,X,V) :- succ(W,Y) & empty(X,W) & south(X,W,X,V)` (also in G01)
- line 56: `west(X,Y,U,Y) :- coord(Y) & succ(U,X)`
- line 78: `opponent(black,white)` (also in G01)
- line 84: `tsucc(3,4)`
- line 87: `tsucc(6,7)`
- line 92: `goal(P,100) :- opponent(P,Q) & guardless(Q)`

### random_matched G04 (4 statements)

- line 46: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)` (also in G07, G10)
- line 77: `opponent(white,black)`
- line 81: `tsucc(0,1)`
- line 89: `next(tick(N)) :- true(tick(M)) & tsucc(M,N)`

### random_matched G05 (11 statements)

- line 18: `role(white)` (also in G02)
- line 23: `coord(2)`
- line 42: `close(A,B) :- succ(B,A)` (also in G08, G13)
- line 45: `kingstep(X,Y,X,V) :- coord(X) & close(Y,V)` (also in G08, G14)
- line 50: `north(X,Y,X,V) :- coord(X) & succ(Y,V)` (also in G08, G15)
- line 63: `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & enemy_at(P,U,V)`
- line 79: `hasguard(P) :- true(at(P,guard,X,Y))` (also in G08, G12)
- line 85: `tsucc(4,5)` (also in G11)
- line 94: `init(at(white,guard,1,1))` (also in G02)
- line 95: `init(at(white,lancer,2,1))`
- line 97: `init(at(black,lancer,3,4))`

### random_matched G06 (6 statements)

- line 34: `empty(X,Y) :- coord(X) & coord(Y) & ~occupied(X,Y)`
- line 37: `enemy_at(P,X,Y) :- true(at(Q,T,X,Y)) & distinct(P,Q)`
- line 51: `north(X,Y,X,V) :- succ(Y,W) & empty(X,W) & north(X,W,X,V)` (also in G01)
- line 67: `next(at(P,T,U,V)) :- does(P,move(T,X,Y,U,V))`
- line 83: `tsucc(2,3)`
- line 88: `tsucc(7,8)` (also in G01)

### random_matched G07 (8 statements)

- line 26: `succ(1,2)` (also in G10)
- line 44: `kingstep(X,Y,U,Y) :- close(X,U) & coord(Y)` (also in G10)
- line 46: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)` (also in G04, G10)
- line 55: `east(X,Y,U,Y) :- succ(X,W) & empty(W,Y) & east(W,Y,U,Y)` (also in G00)
- line 61: `slide(X,Y,U,V) :- west(X,Y,U,V)`
- line 62: `legal(P,move(lancer,X,Y,U,V)) :- true(control(P)) & true(at(P,lancer,X,Y)) & slide(X,Y,U,V) & empty(U,V)`
- line 73: `next(control(white)) :- true(control(black))` (also in G10)
- line 90: `terminal :- guardless(P)`

### random_matched G08 (13 statements)

- line 25: `coord(4)`
- line 27: `succ(2,3)`
- line 42: `close(A,B) :- succ(B,A)` (also in G05, G13)
- line 43: `kingstep(X,Y,U,V) :- close(X,U) & close(Y,V)` (also in G13)
- line 45: `kingstep(X,Y,X,V) :- coord(X) & close(Y,V)` (also in G05, G14)
- line 50: `north(X,Y,X,V) :- coord(X) & succ(Y,V)` (also in G05, G15)
- line 57: `west(X,Y,U,Y) :- succ(W,X) & empty(W,Y) & west(W,Y,U,Y)`
- line 59: `slide(X,Y,U,V) :- south(X,Y,U,V)` (also in G02)
- line 68: `next(at(Q,S,A,B)) :- true(at(Q,S,A,B)) & ~vacated(A,B) & ~struck(A,B)` (also in G15)
- line 74: `next(control(black)) :- true(control(white))` (also in G12)
- line 79: `hasguard(P) :- true(at(P,guard,X,Y))` (also in G05, G12)
- line 82: `tsucc(1,2)` (also in G02)
- line 99: `init(tick(0))` (also in G14)

### random_matched G09 (3 statements)

- line 54: `east(X,Y,U,Y) :- coord(Y) & succ(X,U)`
- line 66: `vacated(X,Y) :- does(P,move(T,X,Y,U,V))`
- line 96: `init(at(black,guard,4,4))`

### random_matched G10 (4 statements)

- line 26: `succ(1,2)` (also in G07)
- line 44: `kingstep(X,Y,U,Y) :- close(X,U) & coord(Y)` (also in G07)
- line 46: `legal(P,move(guard,X,Y,U,V)) :- true(control(P)) & true(at(P,guard,X,Y)) & kingstep(X,Y,U,V) & empty(U,V)` (also in G04, G07)
- line 73: `next(control(white)) :- true(control(black))` (also in G07)

### random_matched G11 (2 statements)

- line 80: `guardless(P) :- role(P) & ~hasguard(P)`
- line 85: `tsucc(4,5)` (also in G05)

### random_matched G12 (2 statements)

- line 74: `next(control(black)) :- true(control(white))` (also in G08)
- line 79: `hasguard(P) :- true(at(P,guard,X,Y))` (also in G05, G08)

### random_matched G13 (2 statements)

- line 42: `close(A,B) :- succ(B,A)` (also in G05, G08)
- line 43: `kingstep(X,Y,U,V) :- close(X,U) & close(Y,V)` (also in G08)

### random_matched G14 (2 statements)

- line 45: `kingstep(X,Y,X,V) :- coord(X) & close(Y,V)` (also in G05, G08)
- line 99: `init(tick(0))` (also in G08)

### random_matched G15 (2 statements)

- line 50: `north(X,Y,X,V) :- coord(X) & succ(Y,V)` (also in G05, G08)
- line 68: `next(at(Q,S,A,B)) :- true(at(Q,S,A,B)) & ~vacated(A,B) & ~struck(A,B)` (also in G08)

