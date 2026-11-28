# dropthree -- groupings

File: `lgref/identify/testgames/dropthree.gdl`. Line numbers are lines of that file.

- **lgref**: 6 groups, 0 statements in no group
- **random_matched**: 6 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 16 | `role(red)` | G05 | G00, G02 |
| 17 | `role(yellow)` | G05 | G05 |
| 21 | `legal(P,drop(C)) :- true(control(P)) & landing(C,R)` | G02 | G00 |
| 22 | `next(cell(C,R,r)) :- does(red,drop(C)) & landing(C,R)` | G00, G02 | G01 |
| 23 | `next(cell(C,R,y)) :- does(yellow,drop(C)) & landing(C,R)` | G00, G02 | G01 |
| 24 | `next(cell(C,R,W)) :- true(cell(C,R,W)) & distinct(W,b)` | G00 | G04 |
| 25 | `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(D)) & distinct(C,D)` | G00, G02 | G02 |
| 26 | `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)` | G00, G02 | G00, G02 |
| 29 | `below(1,2)` | G02 | G00 |
| 30 | `below(2,3)` | G02 | G01 |
| 31 | `landing(C,1) :- true(cell(C,1,b))` | G02 | G03 |
| 32 | `landing(C,R) :- true(cell(C,R,b)) & below(Q,R) & ~true(cell(C,Q,b))` | G02 | G00, G02 |
| 35 | `legal(red,noop) :- true(control(yellow))` | G02 | G02 |
| 36 | `legal(yellow,noop) :- true(control(red))` | G02 | G00 |
| 37 | `next(control(red)) :- true(control(yellow))` | G04 | G02 |
| 38 | `next(control(yellow)) :- true(control(red))` | G04 | G03 |
| 41 | `right(1,2)` | G03 | G00 |
| 42 | `right(2,3)` | G03 | G01 |
| 43 | `right(3,4)` | G03 | G01 |
| 44 | `hline(W) :- right(A,B) & right(B,C) & true(cell(A,R,W)) & true(cell(B,R,W)) & true(cell(C,R,W)) & distinct(W,b)` | G01, G03 | G00 |
| 45 | `vline(W) :- true(cell(C,1,W)) & true(cell(C,2,W)) & true(cell(C,3,W)) & distinct(W,b)` | G01 | G02 |
| 46 | `dline(W) :- right(A,B) & right(B,C) & true(cell(A,1,W)) & true(cell(B,2,W)) & true(cell(C,3,W)) & distinct(W,b)` | G03 | G00 |
| 47 | `dline(W) :- right(A,B) & right(B,C) & true(cell(A,3,W)) & true(cell(B,2,W)) & true(cell(C,1,W)) & distinct(W,b)` | G03 | G00 |
| 48 | `line(W) :- hline(W)` | G01 | G04 |
| 49 | `line(W) :- vline(W)` | G01 | G04 |
| 50 | `line(W) :- dline(W)` | G01 | G00 |
| 53 | `open :- true(cell(C,R,b))` | G01 | G00 |
| 54 | `terminal :- line(r)` | G01 | G03 |
| 55 | `terminal :- line(y)` | G01 | G01, G03 |
| 56 | `terminal :- ~open` | G01 | G02 |
| 57 | `goal(red,100) :- line(r)` | G01 | G00 |
| 58 | `goal(yellow,100) :- line(y)` | G01 | G00 |
| 60 | `init(cell(1,1,b))` | G00 | G00 |
| 61 | `init(cell(1,2,b))` | G00 | G01 |
| 62 | `init(cell(1,3,b))` | G00 | G05 |
| 63 | `init(cell(2,1,b))` | G00 | G01 |
| 64 | `init(cell(2,2,b))` | G00 | G03 |
| 65 | `init(cell(2,3,b))` | G00 | G01 |
| 66 | `init(cell(3,1,b))` | G00 | G01 |
| 67 | `init(cell(3,2,b))` | G00 | G00, G02 |
| 68 | `init(cell(3,3,b))` | G00 | G00 |
| 69 | `init(cell(4,1,b))` | G00 | G02 |
| 70 | `init(cell(4,2,b))` | G00 | G03 |
| 71 | `init(cell(4,3,b))` | G00 | G02 |
| 72 | `init(control(red))` | G04 | G01 |

## lgref by group

### lgref G00 (17 statements)

- line 22: `next(cell(C,R,r)) :- does(red,drop(C)) & landing(C,R)` (also in G02)
- line 23: `next(cell(C,R,y)) :- does(yellow,drop(C)) & landing(C,R)` (also in G02)
- line 24: `next(cell(C,R,W)) :- true(cell(C,R,W)) & distinct(W,b)`
- line 25: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(D)) & distinct(C,D)` (also in G02)
- line 26: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)` (also in G02)
- line 60: `init(cell(1,1,b))`
- line 61: `init(cell(1,2,b))`
- line 62: `init(cell(1,3,b))`
- line 63: `init(cell(2,1,b))`
- line 64: `init(cell(2,2,b))`
- line 65: `init(cell(2,3,b))`
- line 66: `init(cell(3,1,b))`
- line 67: `init(cell(3,2,b))`
- line 68: `init(cell(3,3,b))`
- line 69: `init(cell(4,1,b))`
- line 70: `init(cell(4,2,b))`
- line 71: `init(cell(4,3,b))`

### lgref G01 (11 statements)

- line 44: `hline(W) :- right(A,B) & right(B,C) & true(cell(A,R,W)) & true(cell(B,R,W)) & true(cell(C,R,W)) & distinct(W,b)` (also in G03)
- line 45: `vline(W) :- true(cell(C,1,W)) & true(cell(C,2,W)) & true(cell(C,3,W)) & distinct(W,b)`
- line 48: `line(W) :- hline(W)`
- line 49: `line(W) :- vline(W)`
- line 50: `line(W) :- dline(W)`
- line 53: `open :- true(cell(C,R,b))`
- line 54: `terminal :- line(r)`
- line 55: `terminal :- line(y)`
- line 56: `terminal :- ~open`
- line 57: `goal(red,100) :- line(r)`
- line 58: `goal(yellow,100) :- line(y)`

### lgref G02 (11 statements)

- line 21: `legal(P,drop(C)) :- true(control(P)) & landing(C,R)`
- line 22: `next(cell(C,R,r)) :- does(red,drop(C)) & landing(C,R)` (also in G00)
- line 23: `next(cell(C,R,y)) :- does(yellow,drop(C)) & landing(C,R)` (also in G00)
- line 25: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(D)) & distinct(C,D)` (also in G00)
- line 26: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)` (also in G00)
- line 29: `below(1,2)`
- line 30: `below(2,3)`
- line 31: `landing(C,1) :- true(cell(C,1,b))`
- line 32: `landing(C,R) :- true(cell(C,R,b)) & below(Q,R) & ~true(cell(C,Q,b))`
- line 35: `legal(red,noop) :- true(control(yellow))`
- line 36: `legal(yellow,noop) :- true(control(red))`

### lgref G03 (6 statements)

- line 41: `right(1,2)`
- line 42: `right(2,3)`
- line 43: `right(3,4)`
- line 44: `hline(W) :- right(A,B) & right(B,C) & true(cell(A,R,W)) & true(cell(B,R,W)) & true(cell(C,R,W)) & distinct(W,b)` (also in G01)
- line 46: `dline(W) :- right(A,B) & right(B,C) & true(cell(A,1,W)) & true(cell(B,2,W)) & true(cell(C,3,W)) & distinct(W,b)`
- line 47: `dline(W) :- right(A,B) & right(B,C) & true(cell(A,3,W)) & true(cell(B,2,W)) & true(cell(C,1,W)) & distinct(W,b)`

### lgref G04 (3 statements)

- line 37: `next(control(red)) :- true(control(yellow))`
- line 38: `next(control(yellow)) :- true(control(red))`
- line 72: `init(control(red))`

### lgref G05 (2 statements)

- line 16: `role(red)`
- line 17: `role(yellow)`


## random_matched by group

### random_matched G00 (17 statements)

- line 16: `role(red)` (also in G02)
- line 21: `legal(P,drop(C)) :- true(control(P)) & landing(C,R)`
- line 26: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)` (also in G02)
- line 29: `below(1,2)`
- line 32: `landing(C,R) :- true(cell(C,R,b)) & below(Q,R) & ~true(cell(C,Q,b))` (also in G02)
- line 36: `legal(yellow,noop) :- true(control(red))`
- line 41: `right(1,2)`
- line 44: `hline(W) :- right(A,B) & right(B,C) & true(cell(A,R,W)) & true(cell(B,R,W)) & true(cell(C,R,W)) & distinct(W,b)`
- line 46: `dline(W) :- right(A,B) & right(B,C) & true(cell(A,1,W)) & true(cell(B,2,W)) & true(cell(C,3,W)) & distinct(W,b)`
- line 47: `dline(W) :- right(A,B) & right(B,C) & true(cell(A,3,W)) & true(cell(B,2,W)) & true(cell(C,1,W)) & distinct(W,b)`
- line 50: `line(W) :- dline(W)`
- line 53: `open :- true(cell(C,R,b))`
- line 57: `goal(red,100) :- line(r)`
- line 58: `goal(yellow,100) :- line(y)`
- line 60: `init(cell(1,1,b))`
- line 67: `init(cell(3,2,b))` (also in G02)
- line 68: `init(cell(3,3,b))`

### random_matched G01 (11 statements)

- line 22: `next(cell(C,R,r)) :- does(red,drop(C)) & landing(C,R)`
- line 23: `next(cell(C,R,y)) :- does(yellow,drop(C)) & landing(C,R)`
- line 30: `below(2,3)`
- line 42: `right(2,3)`
- line 43: `right(3,4)`
- line 55: `terminal :- line(y)` (also in G03)
- line 61: `init(cell(1,2,b))`
- line 63: `init(cell(2,1,b))`
- line 65: `init(cell(2,3,b))`
- line 66: `init(cell(3,1,b))`
- line 72: `init(control(red))`

### random_matched G02 (11 statements)

- line 16: `role(red)` (also in G00)
- line 25: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(D)) & distinct(C,D)`
- line 26: `next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)` (also in G00)
- line 32: `landing(C,R) :- true(cell(C,R,b)) & below(Q,R) & ~true(cell(C,Q,b))` (also in G00)
- line 35: `legal(red,noop) :- true(control(yellow))`
- line 37: `next(control(red)) :- true(control(yellow))`
- line 45: `vline(W) :- true(cell(C,1,W)) & true(cell(C,2,W)) & true(cell(C,3,W)) & distinct(W,b)`
- line 56: `terminal :- ~open`
- line 67: `init(cell(3,2,b))` (also in G00)
- line 69: `init(cell(4,1,b))`
- line 71: `init(cell(4,3,b))`

### random_matched G03 (6 statements)

- line 31: `landing(C,1) :- true(cell(C,1,b))`
- line 38: `next(control(yellow)) :- true(control(red))`
- line 54: `terminal :- line(r)`
- line 55: `terminal :- line(y)` (also in G01)
- line 64: `init(cell(2,2,b))`
- line 70: `init(cell(4,2,b))`

### random_matched G04 (3 statements)

- line 24: `next(cell(C,R,W)) :- true(cell(C,R,W)) & distinct(W,b)`
- line 48: `line(W) :- hline(W)`
- line 49: `line(W) :- vline(W)`

### random_matched G05 (2 statements)

- line 17: `role(yellow)`
- line 62: `init(cell(1,3,b))`

