# nim -- groupings

File: `lgref/identify/testgames/nim.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 0 statements in no group
- **random_matched**: 8 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 6 | `role(first)` | G03 | G01, G04 |
| 7 | `role(second)` | G03 | G00 |
| 8 | `legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)` | G01, G04, G05 | G04 |
| 9 | `legal(P,take(2)) :- true(control(P)) & true(pile(N)) & atleast2(N)` | G01, G04, G05 | G02 |
| 10 | `legal(first,noop) :- true(control(second))` | G01, G04 | G02, G06 |
| 11 | `legal(second,noop) :- true(control(first))` | G01, G04 | G02, G06 |
| 12 | `next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)` | G05 | G01, G04, G05 |
| 13 | `next(pile(M)) :- does(P,take(2)) & true(pile(N)) & succ(K,N) & succ(M,K)` | G04 | G02, G06 |
| 14 | `succ(0,1)` | G02 | G00 |
| 15 | `succ(1,2)` | G02, G06 | G02, G06 |
| 16 | `succ(2,3)` | G02, G06 | G03 |
| 17 | `succ(3,4)` | G02, G06 | G05 |
| 18 | `succ(4,5)` | G02, G06 | G00 |
| 19 | `positive(N) :- succ(M,N)` | G02, G06, G07 | G04, G05 |
| 20 | `atleast2(N) :- succ(K,N) & positive(K)` | G02, G06, G07 | G02, G06, G07 |
| 21 | `next(control(first)) :- true(control(second))` | G00 | G00 |
| 22 | `next(control(second)) :- true(control(first))` | G00 | G00 |
| 23 | `empty_pile :- true(pile(0))` | G00 | G02, G06, G07 |
| 24 | `terminal :- empty_pile` | G00 | G01, G04, G05 |
| 25 | `goal(P,100) :- empty_pile & true(control(P))` | G00 | G01, G04 |
| 26 | `init(pile(5))` | G04, G05 | G03 |
| 27 | `init(control(first))` | G00 | G00 |

## lgref by group

### lgref G00 (6 statements)

- line 21: `next(control(first)) :- true(control(second))`
- line 22: `next(control(second)) :- true(control(first))`
- line 23: `empty_pile :- true(pile(0))`
- line 24: `terminal :- empty_pile`
- line 25: `goal(P,100) :- empty_pile & true(control(P))`
- line 27: `init(control(first))`

### lgref G01 (4 statements)

- line 8: `legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)` (also in G04, G05)
- line 9: `legal(P,take(2)) :- true(control(P)) & true(pile(N)) & atleast2(N)` (also in G04, G05)
- line 10: `legal(first,noop) :- true(control(second))` (also in G04)
- line 11: `legal(second,noop) :- true(control(first))` (also in G04)

### lgref G02 (7 statements)

- line 14: `succ(0,1)`
- line 15: `succ(1,2)` (also in G06)
- line 16: `succ(2,3)` (also in G06)
- line 17: `succ(3,4)` (also in G06)
- line 18: `succ(4,5)` (also in G06)
- line 19: `positive(N) :- succ(M,N)` (also in G06, G07)
- line 20: `atleast2(N) :- succ(K,N) & positive(K)` (also in G06, G07)

### lgref G03 (2 statements)

- line 6: `role(first)`
- line 7: `role(second)`

### lgref G04 (6 statements)

- line 8: `legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)` (also in G01, G05)
- line 9: `legal(P,take(2)) :- true(control(P)) & true(pile(N)) & atleast2(N)` (also in G01, G05)
- line 10: `legal(first,noop) :- true(control(second))` (also in G01)
- line 11: `legal(second,noop) :- true(control(first))` (also in G01)
- line 13: `next(pile(M)) :- does(P,take(2)) & true(pile(N)) & succ(K,N) & succ(M,K)`
- line 26: `init(pile(5))` (also in G05)

### lgref G05 (4 statements)

- line 8: `legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)` (also in G01, G04)
- line 9: `legal(P,take(2)) :- true(control(P)) & true(pile(N)) & atleast2(N)` (also in G01, G04)
- line 12: `next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)`
- line 26: `init(pile(5))` (also in G04)

### lgref G06 (6 statements)

- line 15: `succ(1,2)` (also in G02)
- line 16: `succ(2,3)` (also in G02)
- line 17: `succ(3,4)` (also in G02)
- line 18: `succ(4,5)` (also in G02)
- line 19: `positive(N) :- succ(M,N)` (also in G02, G07)
- line 20: `atleast2(N) :- succ(K,N) & positive(K)` (also in G02, G07)

### lgref G07 (2 statements)

- line 19: `positive(N) :- succ(M,N)` (also in G02, G06)
- line 20: `atleast2(N) :- succ(K,N) & positive(K)` (also in G02, G06)


## random_matched by group

### random_matched G00 (6 statements)

- line 7: `role(second)`
- line 14: `succ(0,1)`
- line 18: `succ(4,5)`
- line 21: `next(control(first)) :- true(control(second))`
- line 22: `next(control(second)) :- true(control(first))`
- line 27: `init(control(first))`

### random_matched G01 (4 statements)

- line 6: `role(first)` (also in G04)
- line 12: `next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)` (also in G04, G05)
- line 24: `terminal :- empty_pile` (also in G04, G05)
- line 25: `goal(P,100) :- empty_pile & true(control(P))` (also in G04)

### random_matched G02 (7 statements)

- line 9: `legal(P,take(2)) :- true(control(P)) & true(pile(N)) & atleast2(N)`
- line 10: `legal(first,noop) :- true(control(second))` (also in G06)
- line 11: `legal(second,noop) :- true(control(first))` (also in G06)
- line 13: `next(pile(M)) :- does(P,take(2)) & true(pile(N)) & succ(K,N) & succ(M,K)` (also in G06)
- line 15: `succ(1,2)` (also in G06)
- line 20: `atleast2(N) :- succ(K,N) & positive(K)` (also in G06, G07)
- line 23: `empty_pile :- true(pile(0))` (also in G06, G07)

### random_matched G03 (2 statements)

- line 16: `succ(2,3)`
- line 26: `init(pile(5))`

### random_matched G04 (6 statements)

- line 6: `role(first)` (also in G01)
- line 8: `legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)`
- line 12: `next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)` (also in G01, G05)
- line 19: `positive(N) :- succ(M,N)` (also in G05)
- line 24: `terminal :- empty_pile` (also in G01, G05)
- line 25: `goal(P,100) :- empty_pile & true(control(P))` (also in G01)

### random_matched G05 (4 statements)

- line 12: `next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)` (also in G01, G04)
- line 17: `succ(3,4)`
- line 19: `positive(N) :- succ(M,N)` (also in G04)
- line 24: `terminal :- empty_pile` (also in G01, G04)

### random_matched G06 (6 statements)

- line 10: `legal(first,noop) :- true(control(second))` (also in G02)
- line 11: `legal(second,noop) :- true(control(first))` (also in G02)
- line 13: `next(pile(M)) :- does(P,take(2)) & true(pile(N)) & succ(K,N) & succ(M,K)` (also in G02)
- line 15: `succ(1,2)` (also in G02)
- line 20: `atleast2(N) :- succ(K,N) & positive(K)` (also in G02, G07)
- line 23: `empty_pile :- true(pile(0))` (also in G02, G07)

### random_matched G07 (2 statements)

- line 20: `atleast2(N) :- succ(K,N) & positive(K)` (also in G02, G06)
- line 23: `empty_pile :- true(pile(0))` (also in G02, G06)

