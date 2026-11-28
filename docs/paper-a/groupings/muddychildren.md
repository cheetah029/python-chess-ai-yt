# muddychildren -- groupings

File: `lgref/identify/testgames/muddychildren.gdl`. Line numbers are lines of that file.

- **lgref**: 6 groups, 1 statements in no group
- **random_matched**: 6 groups, 1 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 18 | `role(ann)` | G05 | G01, G02, G04 |
| 19 | `role(bob)` | G05 | G03 |
| 20 | `role(random)` | G05 | G00 |
| 21 | `init(round(0))` | G03 | G05 |
| 22 | `yesno(0)` | G00 | G01, G04 |
| 23 | `yesno(1)` | G00 | G00 |
| 24 | `child(ann)` | G01, G02, G04 | G01, G04 |
| 25 | `child(bob)` | G01, G02, G04 | G05 |
| 26 | `legal(random,muddy(A,B)) :- true(round(0)) & yesno(A) & yesno(B) & oneMuddy(A,B)` | G00, G02 | G03 |
| 27 | `oneMuddy(1,B) :- yesno(B)` | G00 | G02 |
| 28 | `oneMuddy(0,1)` | G00 | G01, G02, G04 |
| 29 | `legal(C,noop) :- child(C) & true(round(0))` | G02 | G01 |
| 30 | `legal(random,noop) :- ~true(round(0))` | G00, G02 | G02 |
| 31 | `next(has(ann,mud)) :- does(random,muddy(1,B))` | G00 | G01, G03, G04 |
| 32 | `next(has(bob,mud)) :- does(random,muddy(A,1))` | G00 | G00, G02 |
| 33 | `next(has(C,mud)) :- true(has(C,mud))` | G00 | G01, G02, G03, G04 |
| 34 | `sees(C,dirt(D)) :- child(C) & true(has(D,mud)) & distinct(C,D)` | G01, G04 | G03 |
| 35 | `isMuddy(C) :- true(has(C,mud))` | G01, G02 | G00 |
| 36 | `isClean(C) :- child(C) & ~true(has(C,mud))` | G01, G04 | - |
| 37 | `someMuddy :- true(has(C,mud))` | - | G00 |
| 40 | `knowsOwn(C) :- knows(C,isMuddy(C))` | G01 | G03 |
| 41 | `knowsOwn(C) :- knows(C,isClean(C))` | G01 | G02 |
| 42 | `legal(C,say(yes)) :- child(C) & ~true(round(0)) & knows(C,isMuddy(C))` | G02 | G00 |
| 43 | `legal(C,say(no)) :- child(C) & ~true(round(0)) & ~knows(C,isMuddy(C))` | G02 | G00 |
| 44 | `sees(C,said(D,X)) :- child(C) & does(D,say(X))` | G01, G02, G03, G04 | G01 |
| 45 | `next(round(1)) :- true(round(0))` | G03 | G01, G02 |
| 46 | `next(round(2)) :- true(round(1))` | G03 | G00 |
| 47 | `next(round(3)) :- true(round(2))` | G03 | G00, G02 |
| 48 | `terminal :- true(round(3))` | G01, G03, G04 | G01, G04 |
| 49 | `goal(C,100) :- child(C) & knowsOwn(C)` | G01, G04 | G05 |
| 50 | `goal(C,0) :- child(C) & ~knowsOwn(C)` | G01, G04 | G01 |
| 51 | `goal(random,0)` | G01 | G01, G04 |

## lgref by group

### lgref G00 (9 statements)

- line 22: `yesno(0)`
- line 23: `yesno(1)`
- line 26: `legal(random,muddy(A,B)) :- true(round(0)) & yesno(A) & yesno(B) & oneMuddy(A,B)` (also in G02)
- line 27: `oneMuddy(1,B) :- yesno(B)`
- line 28: `oneMuddy(0,1)`
- line 30: `legal(random,noop) :- ~true(round(0))` (also in G02)
- line 31: `next(has(ann,mud)) :- does(random,muddy(1,B))`
- line 32: `next(has(bob,mud)) :- does(random,muddy(A,1))`
- line 33: `next(has(C,mud)) :- true(has(C,mud))`

### lgref G01 (12 statements)

- line 24: `child(ann)` (also in G02, G04)
- line 25: `child(bob)` (also in G02, G04)
- line 34: `sees(C,dirt(D)) :- child(C) & true(has(D,mud)) & distinct(C,D)` (also in G04)
- line 35: `isMuddy(C) :- true(has(C,mud))` (also in G02)
- line 36: `isClean(C) :- child(C) & ~true(has(C,mud))` (also in G04)
- line 40: `knowsOwn(C) :- knows(C,isMuddy(C))`
- line 41: `knowsOwn(C) :- knows(C,isClean(C))`
- line 44: `sees(C,said(D,X)) :- child(C) & does(D,say(X))` (also in G02, G03, G04)
- line 48: `terminal :- true(round(3))` (also in G03, G04)
- line 49: `goal(C,100) :- child(C) & knowsOwn(C)` (also in G04)
- line 50: `goal(C,0) :- child(C) & ~knowsOwn(C)` (also in G04)
- line 51: `goal(random,0)`

### lgref G02 (9 statements)

- line 24: `child(ann)` (also in G01, G04)
- line 25: `child(bob)` (also in G01, G04)
- line 26: `legal(random,muddy(A,B)) :- true(round(0)) & yesno(A) & yesno(B) & oneMuddy(A,B)` (also in G00)
- line 29: `legal(C,noop) :- child(C) & true(round(0))`
- line 30: `legal(random,noop) :- ~true(round(0))` (also in G00)
- line 35: `isMuddy(C) :- true(has(C,mud))` (also in G01)
- line 42: `legal(C,say(yes)) :- child(C) & ~true(round(0)) & knows(C,isMuddy(C))`
- line 43: `legal(C,say(no)) :- child(C) & ~true(round(0)) & ~knows(C,isMuddy(C))`
- line 44: `sees(C,said(D,X)) :- child(C) & does(D,say(X))` (also in G01, G03, G04)

### lgref G03 (6 statements)

- line 21: `init(round(0))`
- line 44: `sees(C,said(D,X)) :- child(C) & does(D,say(X))` (also in G01, G02, G04)
- line 45: `next(round(1)) :- true(round(0))`
- line 46: `next(round(2)) :- true(round(1))`
- line 47: `next(round(3)) :- true(round(2))`
- line 48: `terminal :- true(round(3))` (also in G01, G04)

### lgref G04 (8 statements)

- line 24: `child(ann)` (also in G01, G02)
- line 25: `child(bob)` (also in G01, G02)
- line 34: `sees(C,dirt(D)) :- child(C) & true(has(D,mud)) & distinct(C,D)` (also in G01)
- line 36: `isClean(C) :- child(C) & ~true(has(C,mud))` (also in G01)
- line 44: `sees(C,said(D,X)) :- child(C) & does(D,say(X))` (also in G01, G02, G03)
- line 48: `terminal :- true(round(3))` (also in G01, G03)
- line 49: `goal(C,100) :- child(C) & knowsOwn(C)` (also in G01)
- line 50: `goal(C,0) :- child(C) & ~knowsOwn(C)` (also in G01)

### lgref G05 (3 statements)

- line 18: `role(ann)`
- line 19: `role(bob)`
- line 20: `role(random)`

### lgref: statements in no group

- line 37: `someMuddy :- true(has(C,mud))`


## random_matched by group

### random_matched G00 (9 statements)

- line 20: `role(random)`
- line 23: `yesno(1)`
- line 32: `next(has(bob,mud)) :- does(random,muddy(A,1))` (also in G02)
- line 35: `isMuddy(C) :- true(has(C,mud))`
- line 37: `someMuddy :- true(has(C,mud))`
- line 42: `legal(C,say(yes)) :- child(C) & ~true(round(0)) & knows(C,isMuddy(C))`
- line 43: `legal(C,say(no)) :- child(C) & ~true(round(0)) & ~knows(C,isMuddy(C))`
- line 46: `next(round(2)) :- true(round(1))`
- line 47: `next(round(3)) :- true(round(2))` (also in G02)

### random_matched G01 (12 statements)

- line 18: `role(ann)` (also in G02, G04)
- line 22: `yesno(0)` (also in G04)
- line 24: `child(ann)` (also in G04)
- line 28: `oneMuddy(0,1)` (also in G02, G04)
- line 29: `legal(C,noop) :- child(C) & true(round(0))`
- line 31: `next(has(ann,mud)) :- does(random,muddy(1,B))` (also in G03, G04)
- line 33: `next(has(C,mud)) :- true(has(C,mud))` (also in G02, G03, G04)
- line 44: `sees(C,said(D,X)) :- child(C) & does(D,say(X))`
- line 45: `next(round(1)) :- true(round(0))` (also in G02)
- line 48: `terminal :- true(round(3))` (also in G04)
- line 50: `goal(C,0) :- child(C) & ~knowsOwn(C)`
- line 51: `goal(random,0)` (also in G04)

### random_matched G02 (9 statements)

- line 18: `role(ann)` (also in G01, G04)
- line 27: `oneMuddy(1,B) :- yesno(B)`
- line 28: `oneMuddy(0,1)` (also in G01, G04)
- line 30: `legal(random,noop) :- ~true(round(0))`
- line 32: `next(has(bob,mud)) :- does(random,muddy(A,1))` (also in G00)
- line 33: `next(has(C,mud)) :- true(has(C,mud))` (also in G01, G03, G04)
- line 41: `knowsOwn(C) :- knows(C,isClean(C))`
- line 45: `next(round(1)) :- true(round(0))` (also in G01)
- line 47: `next(round(3)) :- true(round(2))` (also in G00)

### random_matched G03 (6 statements)

- line 19: `role(bob)`
- line 26: `legal(random,muddy(A,B)) :- true(round(0)) & yesno(A) & yesno(B) & oneMuddy(A,B)`
- line 31: `next(has(ann,mud)) :- does(random,muddy(1,B))` (also in G01, G04)
- line 33: `next(has(C,mud)) :- true(has(C,mud))` (also in G01, G02, G04)
- line 34: `sees(C,dirt(D)) :- child(C) & true(has(D,mud)) & distinct(C,D)`
- line 40: `knowsOwn(C) :- knows(C,isMuddy(C))`

### random_matched G04 (8 statements)

- line 18: `role(ann)` (also in G01, G02)
- line 22: `yesno(0)` (also in G01)
- line 24: `child(ann)` (also in G01)
- line 28: `oneMuddy(0,1)` (also in G01, G02)
- line 31: `next(has(ann,mud)) :- does(random,muddy(1,B))` (also in G01, G03)
- line 33: `next(has(C,mud)) :- true(has(C,mud))` (also in G01, G02, G03)
- line 48: `terminal :- true(round(3))` (also in G01)
- line 51: `goal(random,0)` (also in G01)

### random_matched G05 (3 statements)

- line 21: `init(round(0))`
- line 25: `child(bob)`
- line 49: `goal(C,100) :- child(C) & knowsOwn(C)`

### random_matched: statements in no group

- line 36: `isClean(C) :- child(C) & ~true(has(C,mud))`

