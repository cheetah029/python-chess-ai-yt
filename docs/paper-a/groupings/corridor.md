# corridor -- groupings

File: `lgref/identify/testgames/corridor.gdl`. Line numbers are lines of that file.

- **lgref**: 10 groups, 0 statements in no group
- **random_matched**: 10 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 48 | `role(white)` | G07 | G00 |
| 49 | `role(black)` | G07 | G04 |
| 52 | `succ(0,1)` | G00 | G03 |
| 53 | `succ(1,2)` | G00 | G03 |
| 54 | `succ(2,3)` | G00 | G00, G02 |
| 55 | `succ(3,4)` | G00 | G04 |
| 56 | `succ(4,5)` | G00 | G03, G09 |
| 57 | `succ(5,6)` | G00 | G00 |
| 58 | `succ(6,7)` | G00 | G02 |
| 59 | `plus2(A,C) :- succ(A,B) & succ(B,C)` | G00 | G02 |
| 62 | `legal(P,step(1)) :- true(control(P)) & true(at(P,A)) & succ(A,B) & inside(B) & clear(P,B)` | G08 | G01 |
| 63 | `legal(P,step(2)) :- true(control(P)) & true(at(P,A)) & plus2(A,C) & inside(C) & clear(P,C) & true(fresh(P))` | G03, G09 | G07 |
| 64 | `legal(P,hold) :- true(control(P))` | G04 | G08 |
| 65 | `legal(white,wait) :- true(control(black))` | G04 | G06 |
| 66 | `legal(black,wait) :- true(control(white))` | G04 | G00 |
| 69 | `inside(0)` | G01 | G01 |
| 70 | `inside(1)` | G01 | G02 |
| 71 | `inside(2)` | G01 | G08, G09 |
| 72 | `inside(3)` | G01 | G00 |
| 73 | `inside(4)` | G01 | G05 |
| 74 | `inside(5)` | G01 | G00 |
| 75 | `inside(6)` | G01 | G00 |
| 76 | `inside(7)` | G01 | G06 |
| 79 | `clear(P,S) :- true(at(Q,T)) & distinct(P,Q) & distinct(S,T)` | G08, G09 | G00 |
| 83 | `next(stale(P)) :- does(P,step(2))` | G04, G08, G09 | G06 |
| 84 | `next(stale(P)) :- does(P,wait) & true(stale(P))` | G04, G08 | G05 |
| 85 | `next(fresh(P)) :- does(P,step(1))` | G03, G09 | G03 |
| 86 | `next(fresh(P)) :- does(P,hold)` | G03 | G01 |
| 87 | `next(fresh(P)) :- does(P,wait) & true(fresh(P))` | G03, G04 | G04 |
| 93 | `next(at(P,B)) :- does(P,step(1)) & true(at(P,A)) & succ(A,B)` | G00, G02 | G01 |
| 94 | `next(at(P,C)) :- does(P,step(2)) & true(at(P,A)) & plus2(A,C)` | G02 | G05 |
| 95 | `next(at(P,A)) :- does(P,hold) & true(at(P,A))` | G02 | G05 |
| 96 | `next(at(P,A)) :- does(P,wait) & true(at(P,A))` | G02, G04 | G02 |
| 99 | `next(control(white)) :- true(control(black))` | G06 | G07 |
| 100 | `next(control(black)) :- true(control(white))` | G06 | G01 |
| 103 | `home(P) :- true(at(P,7))` | G05 | G01 |
| 104 | `terminal :- home(white)` | G05 | G03, G09 |
| 105 | `terminal :- home(black)` | G05 | G04, G08 |
| 106 | `goal(P,100) :- home(P)` | G05 | G04, G08, G09 |
| 108 | `init(at(white,0))` | G02 | G02, G04 |
| 109 | `init(at(black,2))` | G02 | G00 |
| 110 | `init(fresh(white))` | G03 | G01 |
| 111 | `init(fresh(black))` | G03 | G01 |
| 112 | `init(control(white))` | G06 | G03, G04 |

## lgref by group

### lgref G00 (9 statements)

- line 52: `succ(0,1)`
- line 53: `succ(1,2)`
- line 54: `succ(2,3)`
- line 55: `succ(3,4)`
- line 56: `succ(4,5)`
- line 57: `succ(5,6)`
- line 58: `succ(6,7)`
- line 59: `plus2(A,C) :- succ(A,B) & succ(B,C)`
- line 93: `next(at(P,B)) :- does(P,step(1)) & true(at(P,A)) & succ(A,B)` (also in G02)

### lgref G01 (8 statements)

- line 69: `inside(0)`
- line 70: `inside(1)`
- line 71: `inside(2)`
- line 72: `inside(3)`
- line 73: `inside(4)`
- line 74: `inside(5)`
- line 75: `inside(6)`
- line 76: `inside(7)`

### lgref G02 (6 statements)

- line 93: `next(at(P,B)) :- does(P,step(1)) & true(at(P,A)) & succ(A,B)` (also in G00)
- line 94: `next(at(P,C)) :- does(P,step(2)) & true(at(P,A)) & plus2(A,C)`
- line 95: `next(at(P,A)) :- does(P,hold) & true(at(P,A))`
- line 96: `next(at(P,A)) :- does(P,wait) & true(at(P,A))` (also in G04)
- line 108: `init(at(white,0))`
- line 109: `init(at(black,2))`

### lgref G03 (6 statements)

- line 63: `legal(P,step(2)) :- true(control(P)) & true(at(P,A)) & plus2(A,C) & inside(C) & clear(P,C) & true(fresh(P))` (also in G09)
- line 85: `next(fresh(P)) :- does(P,step(1))` (also in G09)
- line 86: `next(fresh(P)) :- does(P,hold)`
- line 87: `next(fresh(P)) :- does(P,wait) & true(fresh(P))` (also in G04)
- line 110: `init(fresh(white))`
- line 111: `init(fresh(black))`

### lgref G04 (7 statements)

- line 64: `legal(P,hold) :- true(control(P))`
- line 65: `legal(white,wait) :- true(control(black))`
- line 66: `legal(black,wait) :- true(control(white))`
- line 83: `next(stale(P)) :- does(P,step(2))` (also in G08, G09)
- line 84: `next(stale(P)) :- does(P,wait) & true(stale(P))` (also in G08)
- line 87: `next(fresh(P)) :- does(P,wait) & true(fresh(P))` (also in G03)
- line 96: `next(at(P,A)) :- does(P,wait) & true(at(P,A))` (also in G02)

### lgref G05 (4 statements)

- line 103: `home(P) :- true(at(P,7))`
- line 104: `terminal :- home(white)`
- line 105: `terminal :- home(black)`
- line 106: `goal(P,100) :- home(P)`

### lgref G06 (3 statements)

- line 99: `next(control(white)) :- true(control(black))`
- line 100: `next(control(black)) :- true(control(white))`
- line 112: `init(control(white))`

### lgref G07 (2 statements)

- line 48: `role(white)`
- line 49: `role(black)`

### lgref G08 (4 statements)

- line 62: `legal(P,step(1)) :- true(control(P)) & true(at(P,A)) & succ(A,B) & inside(B) & clear(P,B)`
- line 79: `clear(P,S) :- true(at(Q,T)) & distinct(P,Q) & distinct(S,T)` (also in G09)
- line 83: `next(stale(P)) :- does(P,step(2))` (also in G04, G09)
- line 84: `next(stale(P)) :- does(P,wait) & true(stale(P))` (also in G04)

### lgref G09 (4 statements)

- line 63: `legal(P,step(2)) :- true(control(P)) & true(at(P,A)) & plus2(A,C) & inside(C) & clear(P,C) & true(fresh(P))` (also in G03)
- line 79: `clear(P,S) :- true(at(Q,T)) & distinct(P,Q) & distinct(S,T)` (also in G08)
- line 83: `next(stale(P)) :- does(P,step(2))` (also in G04, G08)
- line 85: `next(fresh(P)) :- does(P,step(1))` (also in G03)


## random_matched by group

### random_matched G00 (9 statements)

- line 48: `role(white)`
- line 54: `succ(2,3)` (also in G02)
- line 57: `succ(5,6)`
- line 66: `legal(black,wait) :- true(control(white))`
- line 72: `inside(3)`
- line 74: `inside(5)`
- line 75: `inside(6)`
- line 79: `clear(P,S) :- true(at(Q,T)) & distinct(P,Q) & distinct(S,T)`
- line 109: `init(at(black,2))`

### random_matched G01 (8 statements)

- line 62: `legal(P,step(1)) :- true(control(P)) & true(at(P,A)) & succ(A,B) & inside(B) & clear(P,B)`
- line 69: `inside(0)`
- line 86: `next(fresh(P)) :- does(P,hold)`
- line 93: `next(at(P,B)) :- does(P,step(1)) & true(at(P,A)) & succ(A,B)`
- line 100: `next(control(black)) :- true(control(white))`
- line 103: `home(P) :- true(at(P,7))`
- line 110: `init(fresh(white))`
- line 111: `init(fresh(black))`

### random_matched G02 (6 statements)

- line 54: `succ(2,3)` (also in G00)
- line 58: `succ(6,7)`
- line 59: `plus2(A,C) :- succ(A,B) & succ(B,C)`
- line 70: `inside(1)`
- line 96: `next(at(P,A)) :- does(P,wait) & true(at(P,A))`
- line 108: `init(at(white,0))` (also in G04)

### random_matched G03 (6 statements)

- line 52: `succ(0,1)`
- line 53: `succ(1,2)`
- line 56: `succ(4,5)` (also in G09)
- line 85: `next(fresh(P)) :- does(P,step(1))`
- line 104: `terminal :- home(white)` (also in G09)
- line 112: `init(control(white))` (also in G04)

### random_matched G04 (7 statements)

- line 49: `role(black)`
- line 55: `succ(3,4)`
- line 87: `next(fresh(P)) :- does(P,wait) & true(fresh(P))`
- line 105: `terminal :- home(black)` (also in G08)
- line 106: `goal(P,100) :- home(P)` (also in G08, G09)
- line 108: `init(at(white,0))` (also in G02)
- line 112: `init(control(white))` (also in G03)

### random_matched G05 (4 statements)

- line 73: `inside(4)`
- line 84: `next(stale(P)) :- does(P,wait) & true(stale(P))`
- line 94: `next(at(P,C)) :- does(P,step(2)) & true(at(P,A)) & plus2(A,C)`
- line 95: `next(at(P,A)) :- does(P,hold) & true(at(P,A))`

### random_matched G06 (3 statements)

- line 65: `legal(white,wait) :- true(control(black))`
- line 76: `inside(7)`
- line 83: `next(stale(P)) :- does(P,step(2))`

### random_matched G07 (2 statements)

- line 63: `legal(P,step(2)) :- true(control(P)) & true(at(P,A)) & plus2(A,C) & inside(C) & clear(P,C) & true(fresh(P))`
- line 99: `next(control(white)) :- true(control(black))`

### random_matched G08 (4 statements)

- line 64: `legal(P,hold) :- true(control(P))`
- line 71: `inside(2)` (also in G09)
- line 105: `terminal :- home(black)` (also in G04)
- line 106: `goal(P,100) :- home(P)` (also in G04, G09)

### random_matched G09 (4 statements)

- line 56: `succ(4,5)` (also in G03)
- line 71: `inside(2)` (also in G08)
- line 104: `terminal :- home(white)` (also in G03)
- line 106: `goal(P,100) :- home(P)` (also in G04, G08)

