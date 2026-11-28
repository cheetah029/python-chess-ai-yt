# kalah_mini -- groupings

File: `lgref/bench/games/kalah_mini.gdl`. Line numbers are lines of that file.

- **lgref**: 12 groups, 0 statements in no group
- **random_matched**: 12 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 29 | `role(south)` | G05 | G03, G06, G09 |
| 30 | `role(north)` | G05 | G07 |
| 33 | `side(south,s1)` | G06 | G03, G04 |
| 34 | `side(south,s2)` | G06 | G08, G09, G10 |
| 35 | `side(south,s3)` | G06 | G00 |
| 36 | `side(north,n1)` | G06 | G01 |
| 37 | `side(north,n2)` | G06 | G07 |
| 38 | `side(north,n3)` | G06 | G05 |
| 39 | `trio(south,s1,s2,s3)` | G01 | G05 |
| 40 | `trio(north,n1,n2,n3)` | G01 | G05 |
| 41 | `storeof(south,sstore)` | G11 | G04, G08 |
| 42 | `storeof(north,nstore)` | G11 | G06 |
| 43 | `opposite(s1,n3)` | G07 | G01, G03, G06, G09 |
| 44 | `opposite(s2,n2)` | G07 | G01, G02, G03, G04, G05, G06, G07, G08, G09, G10 |
| 45 | `opposite(s3,n1)` | G07 | G01, G04 |
| 46 | `opposite(n1,s3)` | G07 | G00 |
| 47 | `opposite(n2,s2)` | G07 | G08, G10 |
| 48 | `opposite(n3,s1)` | G07 | G03, G09 |
| 49 | `opponent(south,north)` | G03 | G09, G10, G11 |
| 50 | `opponent(north,south)` | G03 | G06 |
| 51 | `num(0)` | G01, G08 | G00 |
| 52 | `succ(0,1)` | G04 | G00 |
| 53 | `succ(1,2)` | G04 | G07 |
| 54 | `succ(2,3)` | G04 | G01, G08 |
| 55 | `succ(3,4)` | G04 | G04 |
| 56 | `succ(4,5)` | G04 | G00 |
| 57 | `succ(5,6)` | G04 | G06 |
| 58 | `atmost(N,N) :- num(N)` | G08 | G03 |
| 59 | `atmost(N,N) :- succ(M,N)` | G04, G08 | G04, G08 |
| 60 | `atmost(A,C) :- succ(A,B) & atmost(B,C)` | G04, G08 | G06 |
| 61 | `more(A,B) :- succ(B,A)` | G03, G04 | G02, G04, G08 |
| 62 | `more(A,C) :- succ(B,A) & more(B,C)` | G03, G04 | G00 |
| 63 | `sum(A,0,A) :- num(A)` | G01 | G03, G09 |
| 64 | `sum(A,0,A) :- succ(B,A)` | G01, G04 | G02 |
| 65 | `sum(A,B2,C2) :- sum(A,B,C) & succ(B,B2) & succ(C,C2)` | G01, G04 | G07 |
| 68 | `ring(south,s1,s2)` | G00 | G08, G09 |
| 69 | `ring(south,s2,s3)` | G00 | G03, G09 |
| 70 | `ring(south,s3,sstore)` | G00 | G03 |
| 71 | `ring(south,sstore,n1)` | G00 | G02 |
| 72 | `ring(south,n1,n2)` | G00 | G01 |
| 73 | `ring(south,n2,n3)` | G00 | G05 |
| 74 | `ring(south,n3,s1)` | G00 | G01 |
| 75 | `ring(north,n1,n2)` | G00 | G05 |
| 76 | `ring(north,n2,n3)` | G00 | G03 |
| 77 | `ring(north,n3,nstore)` | G00 | G06 |
| 78 | `ring(north,nstore,s1)` | G00 | G03 |
| 79 | `ring(north,s1,s2)` | G00 | G00 |
| 80 | `ring(north,s2,s3)` | G00 | G04 |
| 81 | `ring(north,s3,n1)` | G00 | G11 |
| 84 | `legal(P,sow(S)) :- true(control(P)) & side(P,S) & true(seeds(S,N)) & more(N,0)` | G03, G06, G09 | G09 |
| 85 | `ahead(P,S,1,B) :- side(P,S) & ring(P,S,B)` | G00, G10 | G07 |
| 86 | `ahead(P,S,K2,C) :- ahead(P,S,K,B) & ring(P,B,C) & succ(K,K2)` | G00, G10 | G02 |
| 87 | `sowing(P,S,N) :- does(P,sow(S)) & true(seeds(S,N))` | G08, G09, G10 | G04 |
| 88 | `gets(B) :- sowing(P,S,N) & ahead(P,S,K,B) & atmost(K,N)` | G08, G10 | G01 |
| 89 | `last(B) :- sowing(P,S,N) & ahead(P,S,N,B)` | G10 | G04 |
| 90 | `sown(S,0) :- does(P,sow(S))` | G02, G04, G08, G09 | G02 |
| 91 | `sown(B,N2) :- true(seeds(B,N)) & gets(B) & succ(N,N2)` | G04, G08 | G03, G04 |
| 92 | `sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)` | G02, G04, G08 | G04, G08 |
| 93 | `emptied(S) :- does(P,sow(S))` | G08, G09 | G02 |
| 96 | `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` | G01, G02, G03, G04, G05, G06, G07, G08, G09, G10 | G01 |
| 97 | `seized(B) :- capture(P,B,O,M)` | G02 | G05 |
| 98 | `seized(O) :- capture(P,B,O,M)` | G02 | G02 |
| 99 | `haul(P,H) :- capture(P,B,O,M) & succ(M,H)` | G04, G05 | G02 |
| 100 | `hauls(P) :- capture(P,B,O,M)` | G05 | G02 |
| 103 | `next(seeds(B,N)) :- sown(B,N) & ~seized(B)` | G02 | G01, G03 |
| 104 | `next(seeds(B,0)) :- seized(B)` | G02 | G02 |
| 105 | `banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)` | G05, G08, G09, G11 | G00 |
| 106 | `gain(P,0) :- role(P) & ~banked(P) & ~hauls(P)` | G05 | G00, G10 |
| 107 | `gain(P,1) :- banked(P) & ~hauls(P)` | G05 | G09 |
| 108 | `gain(P,H) :- hauls(P) & ~banked(P) & haul(P,H)` | G05 | G01 |
| 109 | `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` | G04, G05 | G05, G08, G09, G11 |
| 110 | `next(store(P,N2)) :- true(store(P,N)) & gain(P,G) & sum(N,G,N2)` | G01 | G04, G05 |
| 113 | `again(P) :- does(P,sow(S)) & storeof(P,T) & last(T)` | G09, G10, G11 | G11 |
| 114 | `next(control(P)) :- again(P)` | G09 | G00 |
| 117 | `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` | G03, G09 | G03 |
| 118 | `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` | G01, G03, G06, G09 | G04, G05 |
| 121 | `stocked(P) :- side(P,S) & true(seeds(S,N)) & more(N,0)` | G03, G06 | G04 |
| 122 | `over :- true(control(P)) & ~stocked(P)` | G03, G09 | G06 |
| 123 | `terminal :- over` | G03, G09 | G03, G06 |
| 124 | `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` | G01, G03 | G02, G04, G08, G09 |
| 125 | `goal(P,100) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(T,U)` | G03 | G07 |
| 126 | `goal(P,50) :- over & opponent(P,Q) & total(P,T) & total(Q,T)` | G03 | G04 |
| 127 | `goal(P,0) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(U,T)` | G03 | G02 |
| 129 | `init(seeds(s1,1))` | G02 | G00 |
| 130 | `init(seeds(s2,1))` | G02 | G01, G04 |
| 131 | `init(seeds(s3,1))` | G02 | G00, G10 |
| 132 | `init(seeds(n1,1))` | G02 | G00 |
| 133 | `init(seeds(n2,1))` | G02 | G00 |
| 134 | `init(seeds(n3,1))` | G02 | G10 |
| 135 | `init(store(south,0))` | G01 | G00 |
| 136 | `init(store(north,0))` | G01 | G08 |
| 137 | `init(control(south))` | G09 | G00 |

## lgref by group

### lgref G00 (16 statements)

- line 68: `ring(south,s1,s2)`
- line 69: `ring(south,s2,s3)`
- line 70: `ring(south,s3,sstore)`
- line 71: `ring(south,sstore,n1)`
- line 72: `ring(south,n1,n2)`
- line 73: `ring(south,n2,n3)`
- line 74: `ring(south,n3,s1)`
- line 75: `ring(north,n1,n2)`
- line 76: `ring(north,n2,n3)`
- line 77: `ring(north,n3,nstore)`
- line 78: `ring(north,nstore,s1)`
- line 79: `ring(north,s1,s2)`
- line 80: `ring(north,s2,s3)`
- line 81: `ring(north,s3,n1)`
- line 85: `ahead(P,S,1,B) :- side(P,S) & ring(P,S,B)` (also in G10)
- line 86: `ahead(P,S,K2,C) :- ahead(P,S,K,B) & ring(P,B,C) & succ(K,K2)` (also in G10)

### lgref G01 (12 statements)

- line 39: `trio(south,s1,s2,s3)`
- line 40: `trio(north,n1,n2,n3)`
- line 51: `num(0)` (also in G08)
- line 63: `sum(A,0,A) :- num(A)`
- line 64: `sum(A,0,A) :- succ(B,A)` (also in G04)
- line 65: `sum(A,B2,C2) :- sum(A,B,C) & succ(B,B2) & succ(C,C2)` (also in G04)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G02, G03, G04, G05, G06, G07, G08, G09, G10)
- line 110: `next(store(P,N2)) :- true(store(P,N)) & gain(P,G) & sum(N,G,N2)`
- line 118: `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` (also in G03, G06, G09)
- line 124: `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` (also in G03)
- line 135: `init(store(south,0))`
- line 136: `init(store(north,0))`

### lgref G02 (13 statements)

- line 90: `sown(S,0) :- does(P,sow(S))` (also in G04, G08, G09)
- line 92: `sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)` (also in G04, G08)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G03, G04, G05, G06, G07, G08, G09, G10)
- line 97: `seized(B) :- capture(P,B,O,M)`
- line 98: `seized(O) :- capture(P,B,O,M)`
- line 103: `next(seeds(B,N)) :- sown(B,N) & ~seized(B)`
- line 104: `next(seeds(B,0)) :- seized(B)`
- line 129: `init(seeds(s1,1))`
- line 130: `init(seeds(s2,1))`
- line 131: `init(seeds(s3,1))`
- line 132: `init(seeds(n1,1))`
- line 133: `init(seeds(n2,1))`
- line 134: `init(seeds(n3,1))`

### lgref G03 (15 statements)

- line 49: `opponent(south,north)`
- line 50: `opponent(north,south)`
- line 61: `more(A,B) :- succ(B,A)` (also in G04)
- line 62: `more(A,C) :- succ(B,A) & more(B,C)` (also in G04)
- line 84: `legal(P,sow(S)) :- true(control(P)) & side(P,S) & true(seeds(S,N)) & more(N,0)` (also in G06, G09)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G04, G05, G06, G07, G08, G09, G10)
- line 117: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` (also in G09)
- line 118: `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` (also in G01, G06, G09)
- line 121: `stocked(P) :- side(P,S) & true(seeds(S,N)) & more(N,0)` (also in G06)
- line 122: `over :- true(control(P)) & ~stocked(P)` (also in G09)
- line 123: `terminal :- over` (also in G09)
- line 124: `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` (also in G01)
- line 125: `goal(P,100) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(T,U)`
- line 126: `goal(P,50) :- over & opponent(P,Q) & total(P,T) & total(Q,T)`
- line 127: `goal(P,0) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(U,T)`

### lgref G04 (18 statements)

- line 52: `succ(0,1)`
- line 53: `succ(1,2)`
- line 54: `succ(2,3)`
- line 55: `succ(3,4)`
- line 56: `succ(4,5)`
- line 57: `succ(5,6)`
- line 59: `atmost(N,N) :- succ(M,N)` (also in G08)
- line 60: `atmost(A,C) :- succ(A,B) & atmost(B,C)` (also in G08)
- line 61: `more(A,B) :- succ(B,A)` (also in G03)
- line 62: `more(A,C) :- succ(B,A) & more(B,C)` (also in G03)
- line 64: `sum(A,0,A) :- succ(B,A)` (also in G01)
- line 65: `sum(A,B2,C2) :- sum(A,B,C) & succ(B,B2) & succ(C,C2)` (also in G01)
- line 90: `sown(S,0) :- does(P,sow(S))` (also in G02, G08, G09)
- line 91: `sown(B,N2) :- true(seeds(B,N)) & gets(B) & succ(N,N2)` (also in G08)
- line 92: `sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)` (also in G02, G08)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G05, G06, G07, G08, G09, G10)
- line 99: `haul(P,H) :- capture(P,B,O,M) & succ(M,H)` (also in G05)
- line 109: `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` (also in G05)

### lgref G05 (10 statements)

- line 29: `role(south)`
- line 30: `role(north)`
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G04, G06, G07, G08, G09, G10)
- line 99: `haul(P,H) :- capture(P,B,O,M) & succ(M,H)` (also in G04)
- line 100: `hauls(P) :- capture(P,B,O,M)`
- line 105: `banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)` (also in G08, G09, G11)
- line 106: `gain(P,0) :- role(P) & ~banked(P) & ~hauls(P)`
- line 107: `gain(P,1) :- banked(P) & ~hauls(P)`
- line 108: `gain(P,H) :- hauls(P) & ~banked(P) & haul(P,H)`
- line 109: `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` (also in G04)

### lgref G06 (10 statements)

- line 33: `side(south,s1)`
- line 34: `side(south,s2)`
- line 35: `side(south,s3)`
- line 36: `side(north,n1)`
- line 37: `side(north,n2)`
- line 38: `side(north,n3)`
- line 84: `legal(P,sow(S)) :- true(control(P)) & side(P,S) & true(seeds(S,N)) & more(N,0)` (also in G03, G09)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G04, G05, G07, G08, G09, G10)
- line 118: `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` (also in G01, G03, G09)
- line 121: `stocked(P) :- side(P,S) & true(seeds(S,N)) & more(N,0)` (also in G03)

### lgref G07 (7 statements)

- line 43: `opposite(s1,n3)`
- line 44: `opposite(s2,n2)`
- line 45: `opposite(s3,n1)`
- line 46: `opposite(n1,s3)`
- line 47: `opposite(n2,s2)`
- line 48: `opposite(n3,s1)`
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G04, G05, G06, G08, G09, G10)

### lgref G08 (12 statements)

- line 51: `num(0)` (also in G01)
- line 58: `atmost(N,N) :- num(N)`
- line 59: `atmost(N,N) :- succ(M,N)` (also in G04)
- line 60: `atmost(A,C) :- succ(A,B) & atmost(B,C)` (also in G04)
- line 87: `sowing(P,S,N) :- does(P,sow(S)) & true(seeds(S,N))` (also in G09, G10)
- line 88: `gets(B) :- sowing(P,S,N) & ahead(P,S,K,B) & atmost(K,N)` (also in G10)
- line 90: `sown(S,0) :- does(P,sow(S))` (also in G02, G04, G09)
- line 91: `sown(B,N2) :- true(seeds(B,N)) & gets(B) & succ(N,N2)` (also in G04)
- line 92: `sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)` (also in G02, G04)
- line 93: `emptied(S) :- does(P,sow(S))` (also in G09)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G04, G05, G06, G07, G09, G10)
- line 105: `banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)` (also in G05, G09, G11)

### lgref G09 (13 statements)

- line 84: `legal(P,sow(S)) :- true(control(P)) & side(P,S) & true(seeds(S,N)) & more(N,0)` (also in G03, G06)
- line 87: `sowing(P,S,N) :- does(P,sow(S)) & true(seeds(S,N))` (also in G08, G10)
- line 90: `sown(S,0) :- does(P,sow(S))` (also in G02, G04, G08)
- line 93: `emptied(S) :- does(P,sow(S))` (also in G08)
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G04, G05, G06, G07, G08, G10)
- line 105: `banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)` (also in G05, G08, G11)
- line 113: `again(P) :- does(P,sow(S)) & storeof(P,T) & last(T)` (also in G10, G11)
- line 114: `next(control(P)) :- again(P)`
- line 117: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)` (also in G03)
- line 118: `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` (also in G01, G03, G06)
- line 122: `over :- true(control(P)) & ~stocked(P)` (also in G03)
- line 123: `terminal :- over` (also in G03)
- line 137: `init(control(south))`

### lgref G10 (7 statements)

- line 85: `ahead(P,S,1,B) :- side(P,S) & ring(P,S,B)` (also in G00)
- line 86: `ahead(P,S,K2,C) :- ahead(P,S,K,B) & ring(P,B,C) & succ(K,K2)` (also in G00)
- line 87: `sowing(P,S,N) :- does(P,sow(S)) & true(seeds(S,N))` (also in G08, G09)
- line 88: `gets(B) :- sowing(P,S,N) & ahead(P,S,K,B) & atmost(K,N)` (also in G08)
- line 89: `last(B) :- sowing(P,S,N) & ahead(P,S,N,B)`
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)` (also in G01, G02, G03, G04, G05, G06, G07, G08, G09)
- line 113: `again(P) :- does(P,sow(S)) & storeof(P,T) & last(T)` (also in G09, G11)

### lgref G11 (4 statements)

- line 41: `storeof(south,sstore)`
- line 42: `storeof(north,nstore)`
- line 105: `banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)` (also in G05, G08, G09)
- line 113: `again(P) :- does(P,sow(S)) & storeof(P,T) & last(T)` (also in G09, G10)


## random_matched by group

### random_matched G00 (16 statements)

- line 35: `side(south,s3)`
- line 46: `opposite(n1,s3)`
- line 51: `num(0)`
- line 52: `succ(0,1)`
- line 56: `succ(4,5)`
- line 62: `more(A,C) :- succ(B,A) & more(B,C)`
- line 79: `ring(north,s1,s2)`
- line 105: `banked(P) :- does(P,sow(S)) & storeof(P,T) & gets(T)`
- line 106: `gain(P,0) :- role(P) & ~banked(P) & ~hauls(P)` (also in G10)
- line 114: `next(control(P)) :- again(P)`
- line 129: `init(seeds(s1,1))`
- line 131: `init(seeds(s3,1))` (also in G10)
- line 132: `init(seeds(n1,1))`
- line 133: `init(seeds(n2,1))`
- line 135: `init(store(south,0))`
- line 137: `init(control(south))`

### random_matched G01 (12 statements)

- line 36: `side(north,n1)`
- line 43: `opposite(s1,n3)` (also in G03, G06, G09)
- line 44: `opposite(s2,n2)` (also in G02, G03, G04, G05, G06, G07, G08, G09, G10)
- line 45: `opposite(s3,n1)` (also in G04)
- line 54: `succ(2,3)` (also in G08)
- line 72: `ring(south,n1,n2)`
- line 74: `ring(south,n3,s1)`
- line 88: `gets(B) :- sowing(P,S,N) & ahead(P,S,K,B) & atmost(K,N)`
- line 96: `capture(P,B,O,M) :- last(B) & does(P,sow(S)) & side(P,B) & true(seeds(B,0)) & opposite(B,O) & sown(O,M) & more(M,0)`
- line 103: `next(seeds(B,N)) :- sown(B,N) & ~seized(B)` (also in G03)
- line 108: `gain(P,H) :- hauls(P) & ~banked(P) & haul(P,H)`
- line 130: `init(seeds(s2,1))` (also in G04)

### random_matched G02 (13 statements)

- line 44: `opposite(s2,n2)` (also in G01, G03, G04, G05, G06, G07, G08, G09, G10)
- line 61: `more(A,B) :- succ(B,A)` (also in G04, G08)
- line 64: `sum(A,0,A) :- succ(B,A)`
- line 71: `ring(south,sstore,n1)`
- line 86: `ahead(P,S,K2,C) :- ahead(P,S,K,B) & ring(P,B,C) & succ(K,K2)`
- line 90: `sown(S,0) :- does(P,sow(S))`
- line 93: `emptied(S) :- does(P,sow(S))`
- line 98: `seized(O) :- capture(P,B,O,M)`
- line 99: `haul(P,H) :- capture(P,B,O,M) & succ(M,H)`
- line 100: `hauls(P) :- capture(P,B,O,M)`
- line 104: `next(seeds(B,0)) :- seized(B)`
- line 124: `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` (also in G04, G08, G09)
- line 127: `goal(P,0) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(U,T)`

### random_matched G03 (15 statements)

- line 29: `role(south)` (also in G06, G09)
- line 33: `side(south,s1)` (also in G04)
- line 43: `opposite(s1,n3)` (also in G01, G06, G09)
- line 44: `opposite(s2,n2)` (also in G01, G02, G04, G05, G06, G07, G08, G09, G10)
- line 48: `opposite(n3,s1)` (also in G09)
- line 58: `atmost(N,N) :- num(N)`
- line 63: `sum(A,0,A) :- num(A)` (also in G09)
- line 69: `ring(south,s2,s3)` (also in G09)
- line 70: `ring(south,s3,sstore)`
- line 76: `ring(north,n2,n3)`
- line 78: `ring(north,nstore,s1)`
- line 91: `sown(B,N2) :- true(seeds(B,N)) & gets(B) & succ(N,N2)` (also in G04)
- line 103: `next(seeds(B,N)) :- sown(B,N) & ~seized(B)` (also in G01)
- line 117: `legal(Q,noop) :- true(control(P)) & opponent(P,Q)`
- line 123: `terminal :- over` (also in G06)

### random_matched G04 (18 statements)

- line 33: `side(south,s1)` (also in G03)
- line 41: `storeof(south,sstore)` (also in G08)
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G05, G06, G07, G08, G09, G10)
- line 45: `opposite(s3,n1)` (also in G01)
- line 55: `succ(3,4)`
- line 59: `atmost(N,N) :- succ(M,N)` (also in G08)
- line 61: `more(A,B) :- succ(B,A)` (also in G02, G08)
- line 80: `ring(north,s2,s3)`
- line 87: `sowing(P,S,N) :- does(P,sow(S)) & true(seeds(S,N))`
- line 89: `last(B) :- sowing(P,S,N) & ahead(P,S,N,B)`
- line 91: `sown(B,N2) :- true(seeds(B,N)) & gets(B) & succ(N,N2)` (also in G03)
- line 92: `sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)` (also in G08)
- line 110: `next(store(P,N2)) :- true(store(P,N)) & gain(P,G) & sum(N,G,N2)` (also in G05)
- line 118: `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` (also in G05)
- line 121: `stocked(P) :- side(P,S) & true(seeds(S,N)) & more(N,0)`
- line 124: `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` (also in G02, G08, G09)
- line 126: `goal(P,50) :- over & opponent(P,Q) & total(P,T) & total(Q,T)`
- line 130: `init(seeds(s2,1))` (also in G01)

### random_matched G05 (10 statements)

- line 38: `side(north,n3)`
- line 39: `trio(south,s1,s2,s3)`
- line 40: `trio(north,n1,n2,n3)`
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G04, G06, G07, G08, G09, G10)
- line 73: `ring(south,n2,n3)`
- line 75: `ring(north,n1,n2)`
- line 97: `seized(B) :- capture(P,B,O,M)`
- line 109: `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` (also in G08, G09, G11)
- line 110: `next(store(P,N2)) :- true(store(P,N)) & gain(P,G) & sum(N,G,N2)` (also in G04)
- line 118: `next(control(Q)) :- does(P,sow(S)) & ~again(P) & opponent(P,Q)` (also in G04)

### random_matched G06 (10 statements)

- line 29: `role(south)` (also in G03, G09)
- line 42: `storeof(north,nstore)`
- line 43: `opposite(s1,n3)` (also in G01, G03, G09)
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G04, G05, G07, G08, G09, G10)
- line 50: `opponent(north,south)`
- line 57: `succ(5,6)`
- line 60: `atmost(A,C) :- succ(A,B) & atmost(B,C)`
- line 77: `ring(north,n3,nstore)`
- line 122: `over :- true(control(P)) & ~stocked(P)`
- line 123: `terminal :- over` (also in G03)

### random_matched G07 (7 statements)

- line 30: `role(north)`
- line 37: `side(north,n2)`
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G04, G05, G06, G08, G09, G10)
- line 53: `succ(1,2)`
- line 65: `sum(A,B2,C2) :- sum(A,B,C) & succ(B,B2) & succ(C,C2)`
- line 85: `ahead(P,S,1,B) :- side(P,S) & ring(P,S,B)`
- line 125: `goal(P,100) :- over & opponent(P,Q) & total(P,T) & total(Q,U) & more(T,U)`

### random_matched G08 (12 statements)

- line 34: `side(south,s2)` (also in G09, G10)
- line 41: `storeof(south,sstore)` (also in G04)
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G04, G05, G06, G07, G09, G10)
- line 47: `opposite(n2,s2)` (also in G10)
- line 54: `succ(2,3)` (also in G01)
- line 59: `atmost(N,N) :- succ(M,N)` (also in G04)
- line 61: `more(A,B) :- succ(B,A)` (also in G02, G04)
- line 68: `ring(south,s1,s2)` (also in G09)
- line 92: `sown(B,N) :- true(seeds(B,N)) & ~gets(B) & ~emptied(B)` (also in G04)
- line 109: `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` (also in G05, G09, G11)
- line 124: `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` (also in G02, G04, G09)
- line 136: `init(store(north,0))`

### random_matched G09 (13 statements)

- line 29: `role(south)` (also in G03, G06)
- line 34: `side(south,s2)` (also in G08, G10)
- line 43: `opposite(s1,n3)` (also in G01, G03, G06)
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G04, G05, G06, G07, G08, G10)
- line 48: `opposite(n3,s1)` (also in G03)
- line 49: `opponent(south,north)` (also in G10, G11)
- line 63: `sum(A,0,A) :- num(A)` (also in G03)
- line 68: `ring(south,s1,s2)` (also in G08)
- line 69: `ring(south,s2,s3)` (also in G03)
- line 84: `legal(P,sow(S)) :- true(control(P)) & side(P,S) & true(seeds(S,N)) & more(N,0)`
- line 107: `gain(P,1) :- banked(P) & ~hauls(P)`
- line 109: `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` (also in G05, G08, G11)
- line 124: `total(P,T) :- true(store(P,S0)) & trio(P,A,B,C) & true(seeds(A,X)) & true(seeds(B,Y)) & true(seeds(C,Z)) & sum(S0,X,T1) & sum(T1,Y,T2) & sum(T2,Z,T)` (also in G02, G04, G08)

### random_matched G10 (7 statements)

- line 34: `side(south,s2)` (also in G08, G09)
- line 44: `opposite(s2,n2)` (also in G01, G02, G03, G04, G05, G06, G07, G08, G09)
- line 47: `opposite(n2,s2)` (also in G08)
- line 49: `opponent(south,north)` (also in G09, G11)
- line 106: `gain(P,0) :- role(P) & ~banked(P) & ~hauls(P)` (also in G00)
- line 131: `init(seeds(s3,1))` (also in G00)
- line 134: `init(seeds(n3,1))`

### random_matched G11 (4 statements)

- line 49: `opponent(south,north)` (also in G09, G10)
- line 81: `ring(north,s3,n1)`
- line 109: `gain(P,G) :- hauls(P) & banked(P) & haul(P,H) & succ(H,G)` (also in G05, G08, G09)
- line 113: `again(P) :- does(P,sow(S)) & storeof(P,T) & last(T)`

