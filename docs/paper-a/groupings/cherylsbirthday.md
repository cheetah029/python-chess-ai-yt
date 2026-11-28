# cherylsbirthday -- groupings

File: `lgref/identify/testgames/cherylsbirthday.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 2 statements in no group
- **random_matched**: 8 groups, 2 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 19 | `role(albert)` | G04 | G01, G03 |
| 20 | `role(bernard)` | G04 | G04 |
| 21 | `role(random)` | G04 | G01 |
| 22 | `init(round(0))` | G01, G03 | G02 |
| 23 | `date(may,15)` | G00 | G05 |
| 24 | `date(may,16)` | G00 | G00 |
| 25 | `date(may,19)` | G00 | G01 |
| 26 | `date(june,17)` | G00 | G00 |
| 27 | `date(june,18)` | G00 | G02 |
| 28 | `date(july,14)` | G00 | - |
| 29 | `date(july,16)` | G00 | G05 |
| 30 | `date(august,14)` | G00 | G01 |
| 31 | `date(august,15)` | G00 | G00 |
| 32 | `date(august,17)` | G00 | G02, G07 |
| 33 | `listener(albert)` | G01 | G00 |
| 34 | `listener(bernard)` | G01 | G02 |
| 35 | `legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)` | G00, G02 | G01, G03 |
| 36 | `legal(random,noop) :- ~true(round(0))` | G02 | G01 |
| 37 | `next(birthday(M,D)) :- does(random,birthday(M,D))` | G05 | G02, G07 |
| 38 | `next(birthday(M,D)) :- true(birthday(M,D))` | G05 | G01, G03 |
| 39 | `sees(albert,month(M)) :- does(random,birthday(M,D))` | - | G00, G02 |
| 40 | `sees(bernard,day(D)) :- does(random,birthday(M,D))` | - | G00 |
| 41 | `isDate(M,D) :- true(birthday(M,D))` | G05 | G02 |
| 44 | `knowsDate(R) :- listener(R) & knows(R,isDate(M,D))` | G01 | G00 |
| 45 | `bernardIgnorant :- ~knowsDate(bernard)` | G01 | G01 |
| 47 | `firstClaim :- ~knowsDate(albert) & knows(albert,bernardIgnorant)` | G01 | G01, G03 |
| 49 | `legal(albert,noop) :- true(round(0))` | G02 | G01 |
| 50 | `legal(bernard,noop) :- true(round(0))` | G02 | G04 |
| 51 | `legal(albert,say(yes)) :- true(round(1)) & firstClaim` | G02 | G01 |
| 52 | `legal(albert,say(no)) :- true(round(1)) & ~firstClaim` | G02 | - |
| 53 | `legal(bernard,noop) :- true(round(1))` | G02 | G01, G02, G03, G06, G07 |
| 54 | `legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)` | G02, G06 | G01, G03 |
| 55 | `legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)` | G02, G07 | G01, G03 |
| 56 | `legal(albert,noop) :- true(round(2))` | G02 | G02, G06 |
| 57 | `legal(albert,say(yes)) :- true(round(3)) & knowsDate(albert)` | G02, G06 | G00 |
| 58 | `legal(albert,say(no)) :- true(round(3)) & ~knowsDate(albert)` | G02, G07 | G04 |
| 59 | `legal(bernard,noop) :- true(round(3))` | G02 | G01 |
| 60 | `sees(L,said(S,X)) :- listener(L) & does(S,say(X))` | G01, G02, G03, G06, G07 | G00 |
| 61 | `next(round(1)) :- true(round(0))` | G01, G03 | G02 |
| 62 | `next(round(2)) :- true(round(1))` | G01, G03 | G02 |
| 63 | `next(round(3)) :- true(round(2))` | G01, G03 | G02 |
| 64 | `next(round(4)) :- true(round(3))` | G01, G03 | G02, G06 |
| 65 | `terminal :- true(round(4))` | G01, G03 | G00 |
| 66 | `goal(R,100) :- listener(R) & knowsDate(R)` | G01 | G05 |
| 67 | `goal(R,0) :- listener(R) & ~knowsDate(R)` | G01 | G00 |
| 68 | `goal(random,0)` | G01 | G02 |

## lgref by group

### lgref G00 (11 statements)

- line 23: `date(may,15)`
- line 24: `date(may,16)`
- line 25: `date(may,19)`
- line 26: `date(june,17)`
- line 27: `date(june,18)`
- line 28: `date(july,14)`
- line 29: `date(july,16)`
- line 30: `date(august,14)`
- line 31: `date(august,15)`
- line 32: `date(august,17)`
- line 35: `legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)` (also in G02)

### lgref G01 (15 statements)

- line 22: `init(round(0))` (also in G03)
- line 33: `listener(albert)`
- line 34: `listener(bernard)`
- line 44: `knowsDate(R) :- listener(R) & knows(R,isDate(M,D))`
- line 45: `bernardIgnorant :- ~knowsDate(bernard)`
- line 47: `firstClaim :- ~knowsDate(albert) & knows(albert,bernardIgnorant)`
- line 60: `sees(L,said(S,X)) :- listener(L) & does(S,say(X))` (also in G02, G03, G06, G07)
- line 61: `next(round(1)) :- true(round(0))` (also in G03)
- line 62: `next(round(2)) :- true(round(1))` (also in G03)
- line 63: `next(round(3)) :- true(round(2))` (also in G03)
- line 64: `next(round(4)) :- true(round(3))` (also in G03)
- line 65: `terminal :- true(round(4))` (also in G03)
- line 66: `goal(R,100) :- listener(R) & knowsDate(R)`
- line 67: `goal(R,0) :- listener(R) & ~knowsDate(R)`
- line 68: `goal(random,0)`

### lgref G02 (14 statements)

- line 35: `legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)` (also in G00)
- line 36: `legal(random,noop) :- ~true(round(0))`
- line 49: `legal(albert,noop) :- true(round(0))`
- line 50: `legal(bernard,noop) :- true(round(0))`
- line 51: `legal(albert,say(yes)) :- true(round(1)) & firstClaim`
- line 52: `legal(albert,say(no)) :- true(round(1)) & ~firstClaim`
- line 53: `legal(bernard,noop) :- true(round(1))`
- line 54: `legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)` (also in G06)
- line 55: `legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)` (also in G07)
- line 56: `legal(albert,noop) :- true(round(2))`
- line 57: `legal(albert,say(yes)) :- true(round(3)) & knowsDate(albert)` (also in G06)
- line 58: `legal(albert,say(no)) :- true(round(3)) & ~knowsDate(albert)` (also in G07)
- line 59: `legal(bernard,noop) :- true(round(3))`
- line 60: `sees(L,said(S,X)) :- listener(L) & does(S,say(X))` (also in G01, G03, G06, G07)

### lgref G03 (7 statements)

- line 22: `init(round(0))` (also in G01)
- line 60: `sees(L,said(S,X)) :- listener(L) & does(S,say(X))` (also in G01, G02, G06, G07)
- line 61: `next(round(1)) :- true(round(0))` (also in G01)
- line 62: `next(round(2)) :- true(round(1))` (also in G01)
- line 63: `next(round(3)) :- true(round(2))` (also in G01)
- line 64: `next(round(4)) :- true(round(3))` (also in G01)
- line 65: `terminal :- true(round(4))` (also in G01)

### lgref G04 (3 statements)

- line 19: `role(albert)`
- line 20: `role(bernard)`
- line 21: `role(random)`

### lgref G05 (3 statements)

- line 37: `next(birthday(M,D)) :- does(random,birthday(M,D))`
- line 38: `next(birthday(M,D)) :- true(birthday(M,D))`
- line 41: `isDate(M,D) :- true(birthday(M,D))`

### lgref G06 (3 statements)

- line 54: `legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)` (also in G02)
- line 57: `legal(albert,say(yes)) :- true(round(3)) & knowsDate(albert)` (also in G02)
- line 60: `sees(L,said(S,X)) :- listener(L) & does(S,say(X))` (also in G01, G02, G03, G07)

### lgref G07 (3 statements)

- line 55: `legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)` (also in G02)
- line 58: `legal(albert,say(no)) :- true(round(3)) & ~knowsDate(albert)` (also in G02)
- line 60: `sees(L,said(S,X)) :- listener(L) & does(S,say(X))` (also in G01, G02, G03, G06)

### lgref: statements in no group

- line 39: `sees(albert,month(M)) :- does(random,birthday(M,D))`
- line 40: `sees(bernard,day(D)) :- does(random,birthday(M,D))`


## random_matched by group

### random_matched G00 (11 statements)

- line 24: `date(may,16)`
- line 26: `date(june,17)`
- line 31: `date(august,15)`
- line 33: `listener(albert)`
- line 39: `sees(albert,month(M)) :- does(random,birthday(M,D))` (also in G02)
- line 40: `sees(bernard,day(D)) :- does(random,birthday(M,D))`
- line 44: `knowsDate(R) :- listener(R) & knows(R,isDate(M,D))`
- line 57: `legal(albert,say(yes)) :- true(round(3)) & knowsDate(albert)`
- line 60: `sees(L,said(S,X)) :- listener(L) & does(S,say(X))`
- line 65: `terminal :- true(round(4))`
- line 67: `goal(R,0) :- listener(R) & ~knowsDate(R)`

### random_matched G01 (15 statements)

- line 19: `role(albert)` (also in G03)
- line 21: `role(random)`
- line 25: `date(may,19)`
- line 30: `date(august,14)`
- line 35: `legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)` (also in G03)
- line 36: `legal(random,noop) :- ~true(round(0))`
- line 38: `next(birthday(M,D)) :- true(birthday(M,D))` (also in G03)
- line 45: `bernardIgnorant :- ~knowsDate(bernard)`
- line 47: `firstClaim :- ~knowsDate(albert) & knows(albert,bernardIgnorant)` (also in G03)
- line 49: `legal(albert,noop) :- true(round(0))`
- line 51: `legal(albert,say(yes)) :- true(round(1)) & firstClaim`
- line 53: `legal(bernard,noop) :- true(round(1))` (also in G02, G03, G06, G07)
- line 54: `legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)` (also in G03)
- line 55: `legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)` (also in G03)
- line 59: `legal(bernard,noop) :- true(round(3))`

### random_matched G02 (14 statements)

- line 22: `init(round(0))`
- line 27: `date(june,18)`
- line 32: `date(august,17)` (also in G07)
- line 34: `listener(bernard)`
- line 37: `next(birthday(M,D)) :- does(random,birthday(M,D))` (also in G07)
- line 39: `sees(albert,month(M)) :- does(random,birthday(M,D))` (also in G00)
- line 41: `isDate(M,D) :- true(birthday(M,D))`
- line 53: `legal(bernard,noop) :- true(round(1))` (also in G01, G03, G06, G07)
- line 56: `legal(albert,noop) :- true(round(2))` (also in G06)
- line 61: `next(round(1)) :- true(round(0))`
- line 62: `next(round(2)) :- true(round(1))`
- line 63: `next(round(3)) :- true(round(2))`
- line 64: `next(round(4)) :- true(round(3))` (also in G06)
- line 68: `goal(random,0)`

### random_matched G03 (7 statements)

- line 19: `role(albert)` (also in G01)
- line 35: `legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)` (also in G01)
- line 38: `next(birthday(M,D)) :- true(birthday(M,D))` (also in G01)
- line 47: `firstClaim :- ~knowsDate(albert) & knows(albert,bernardIgnorant)` (also in G01)
- line 53: `legal(bernard,noop) :- true(round(1))` (also in G01, G02, G06, G07)
- line 54: `legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)` (also in G01)
- line 55: `legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)` (also in G01)

### random_matched G04 (3 statements)

- line 20: `role(bernard)`
- line 50: `legal(bernard,noop) :- true(round(0))`
- line 58: `legal(albert,say(no)) :- true(round(3)) & ~knowsDate(albert)`

### random_matched G05 (3 statements)

- line 23: `date(may,15)`
- line 29: `date(july,16)`
- line 66: `goal(R,100) :- listener(R) & knowsDate(R)`

### random_matched G06 (3 statements)

- line 53: `legal(bernard,noop) :- true(round(1))` (also in G01, G02, G03, G07)
- line 56: `legal(albert,noop) :- true(round(2))` (also in G02)
- line 64: `next(round(4)) :- true(round(3))` (also in G02)

### random_matched G07 (3 statements)

- line 32: `date(august,17)` (also in G02)
- line 37: `next(birthday(M,D)) :- does(random,birthday(M,D))` (also in G02)
- line 53: `legal(bernard,noop) :- true(round(1))` (also in G01, G02, G03, G06)

### random_matched: statements in no group

- line 28: `date(july,14)`
- line 52: `legal(albert,say(no)) :- true(round(1)) & ~firstClaim`

