# kriegtictactoe -- groupings

File: `lgref/identify/testgames/kriegtictactoe.gdl`. Line numbers are lines of that file.

- **lgref**: 8 groups, 0 statements in no group
- **random_matched**: 8 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 21 | `role(xplayer)` | G07 | G01 |
| 22 | `role(oplayer)` | G07 | G05 |
| 23 | `symbol(xplayer,x)` | G01 | G02 |
| 24 | `symbol(oplayer,o)` | G01 | G03 |
| 25 | `init(cell(1,1,b))` | G00 | G06 |
| 26 | `init(cell(1,2,b))` | G00 | G00 |
| 27 | `init(cell(1,3,b))` | G00 | G00 |
| 28 | `init(cell(2,1,b))` | G00 | G00 |
| 29 | `init(cell(2,2,b))` | G00 | G02, G03 |
| 30 | `init(cell(2,3,b))` | G00 | G06 |
| 31 | `init(cell(3,1,b))` | G00 | G01 |
| 32 | `init(cell(3,2,b))` | G00 | G07 |
| 33 | `init(cell(3,3,b))` | G00 | G00 |
| 34 | `init(control(xplayer))` | G05 | G02, G03, G06 |
| 35 | `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,W)) & symbol(P,S) & distinct(W,S) & ~true(tried(P,M,N))` | G01 | G00 |
| 36 | `legal(xplayer,noop) :- true(control(oplayer))` | G01 | G01 |
| 37 | `legal(oplayer,noop) :- true(control(xplayer))` | G01 | G02 |
| 38 | `sees(P,ok) :- does(P,mark(M,N)) & true(cell(M,N,b))` | G01 | G01 |
| 39 | `sees(P,taken) :- does(P,mark(M,N)) & ~true(cell(M,N,b))` | G01 | G00 |
| 40 | `attempted(M,N) :- does(P,mark(M,N))` | G00, G01 | G04 |
| 41 | `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)` | G00, G01 | G00 |
| 42 | `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)` | G00 | G00 |
| 43 | `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)` | G00 | G02, G04 |
| 44 | `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))` | G01 | G00 |
| 45 | `next(tried(P,M,N)) :- true(tried(P,M,N))` | G01 | G02 |
| 46 | `next(control(xplayer)) :- true(control(oplayer))` | G05 | G02, G04 |
| 47 | `next(control(oplayer)) :- true(control(xplayer))` | G05 | G02 |
| 48 | `row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))` | G03 | G01 |
| 49 | `column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))` | G03 | G01 |
| 50 | `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` | G06 | G00, G01 |
| 51 | `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))` | G06 | G04 |
| 52 | `line(W) :- row(M,W)` | G02, G03 | G02 |
| 53 | `line(W) :- column(N,W)` | G02, G03 | G02 |
| 54 | `line(W) :- diagonal(W)` | G02, G03, G06 | G07 |
| 55 | `open :- true(cell(M,N,b))` | G02, G04 | G00 |
| 56 | `terminal :- line(x)` | G04 | G00, G01 |
| 57 | `terminal :- line(o)` | G04 | G05 |
| 58 | `terminal :- ~open` | G02, G04 | G05 |
| 59 | `goal(xplayer,100) :- line(x)` | G02 | G01 |
| 60 | `goal(xplayer,0) :- line(o)` | G02 | G02, G03 |
| 61 | `goal(xplayer,50) :- ~line(x) & ~line(o)` | G02 | G01 |
| 62 | `goal(oplayer,100) :- line(o)` | G02 | G01 |
| 63 | `goal(oplayer,0) :- line(x)` | G02 | G00 |
| 64 | `goal(oplayer,50) :- ~line(x) & ~line(o)` | G02 | G03 |

## lgref by group

### lgref G00 (13 statements)

- line 25: `init(cell(1,1,b))`
- line 26: `init(cell(1,2,b))`
- line 27: `init(cell(1,3,b))`
- line 28: `init(cell(2,1,b))`
- line 29: `init(cell(2,2,b))`
- line 30: `init(cell(2,3,b))`
- line 31: `init(cell(3,1,b))`
- line 32: `init(cell(3,2,b))`
- line 33: `init(cell(3,3,b))`
- line 40: `attempted(M,N) :- does(P,mark(M,N))` (also in G01)
- line 41: `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)` (also in G01)
- line 42: `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)`
- line 43: `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)`

### lgref G01 (11 statements)

- line 23: `symbol(xplayer,x)`
- line 24: `symbol(oplayer,o)`
- line 35: `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,W)) & symbol(P,S) & distinct(W,S) & ~true(tried(P,M,N))`
- line 36: `legal(xplayer,noop) :- true(control(oplayer))`
- line 37: `legal(oplayer,noop) :- true(control(xplayer))`
- line 38: `sees(P,ok) :- does(P,mark(M,N)) & true(cell(M,N,b))`
- line 39: `sees(P,taken) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 40: `attempted(M,N) :- does(P,mark(M,N))` (also in G00)
- line 41: `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)` (also in G00)
- line 44: `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 45: `next(tried(P,M,N)) :- true(tried(P,M,N))`

### lgref G02 (11 statements)

- line 52: `line(W) :- row(M,W)` (also in G03)
- line 53: `line(W) :- column(N,W)` (also in G03)
- line 54: `line(W) :- diagonal(W)` (also in G03, G06)
- line 55: `open :- true(cell(M,N,b))` (also in G04)
- line 58: `terminal :- ~open` (also in G04)
- line 59: `goal(xplayer,100) :- line(x)`
- line 60: `goal(xplayer,0) :- line(o)`
- line 61: `goal(xplayer,50) :- ~line(x) & ~line(o)`
- line 62: `goal(oplayer,100) :- line(o)`
- line 63: `goal(oplayer,0) :- line(x)`
- line 64: `goal(oplayer,50) :- ~line(x) & ~line(o)`

### lgref G03 (5 statements)

- line 48: `row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))`
- line 49: `column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))`
- line 52: `line(W) :- row(M,W)` (also in G02)
- line 53: `line(W) :- column(N,W)` (also in G02)
- line 54: `line(W) :- diagonal(W)` (also in G02, G06)

### lgref G04 (4 statements)

- line 55: `open :- true(cell(M,N,b))` (also in G02)
- line 56: `terminal :- line(x)`
- line 57: `terminal :- line(o)`
- line 58: `terminal :- ~open` (also in G02)

### lgref G05 (3 statements)

- line 34: `init(control(xplayer))`
- line 46: `next(control(xplayer)) :- true(control(oplayer))`
- line 47: `next(control(oplayer)) :- true(control(xplayer))`

### lgref G06 (3 statements)

- line 50: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))`
- line 51: `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))`
- line 54: `line(W) :- diagonal(W)` (also in G02, G03)

### lgref G07 (2 statements)

- line 21: `role(xplayer)`
- line 22: `role(oplayer)`


## random_matched by group

### random_matched G00 (13 statements)

- line 26: `init(cell(1,2,b))`
- line 27: `init(cell(1,3,b))`
- line 28: `init(cell(2,1,b))`
- line 33: `init(cell(3,3,b))`
- line 35: `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,W)) & symbol(P,S) & distinct(W,S) & ~true(tried(P,M,N))`
- line 39: `sees(P,taken) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 41: `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)`
- line 42: `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)`
- line 44: `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 50: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` (also in G01)
- line 55: `open :- true(cell(M,N,b))`
- line 56: `terminal :- line(x)` (also in G01)
- line 63: `goal(oplayer,0) :- line(x)`

### random_matched G01 (11 statements)

- line 21: `role(xplayer)`
- line 31: `init(cell(3,1,b))`
- line 36: `legal(xplayer,noop) :- true(control(oplayer))`
- line 38: `sees(P,ok) :- does(P,mark(M,N)) & true(cell(M,N,b))`
- line 48: `row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))`
- line 49: `column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))`
- line 50: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` (also in G00)
- line 56: `terminal :- line(x)` (also in G00)
- line 59: `goal(xplayer,100) :- line(x)`
- line 61: `goal(xplayer,50) :- ~line(x) & ~line(o)`
- line 62: `goal(oplayer,100) :- line(o)`

### random_matched G02 (11 statements)

- line 23: `symbol(xplayer,x)`
- line 29: `init(cell(2,2,b))` (also in G03)
- line 34: `init(control(xplayer))` (also in G03, G06)
- line 37: `legal(oplayer,noop) :- true(control(xplayer))`
- line 43: `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)` (also in G04)
- line 45: `next(tried(P,M,N)) :- true(tried(P,M,N))`
- line 46: `next(control(xplayer)) :- true(control(oplayer))` (also in G04)
- line 47: `next(control(oplayer)) :- true(control(xplayer))`
- line 52: `line(W) :- row(M,W)`
- line 53: `line(W) :- column(N,W)`
- line 60: `goal(xplayer,0) :- line(o)` (also in G03)

### random_matched G03 (5 statements)

- line 24: `symbol(oplayer,o)`
- line 29: `init(cell(2,2,b))` (also in G02)
- line 34: `init(control(xplayer))` (also in G02, G06)
- line 60: `goal(xplayer,0) :- line(o)` (also in G02)
- line 64: `goal(oplayer,50) :- ~line(x) & ~line(o)`

### random_matched G04 (4 statements)

- line 40: `attempted(M,N) :- does(P,mark(M,N))`
- line 43: `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)` (also in G02)
- line 46: `next(control(xplayer)) :- true(control(oplayer))` (also in G02)
- line 51: `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))`

### random_matched G05 (3 statements)

- line 22: `role(oplayer)`
- line 57: `terminal :- line(o)`
- line 58: `terminal :- ~open`

### random_matched G06 (3 statements)

- line 25: `init(cell(1,1,b))`
- line 30: `init(cell(2,3,b))`
- line 34: `init(control(xplayer))` (also in G02, G03)

### random_matched G07 (2 statements)

- line 32: `init(cell(3,2,b))`
- line 54: `line(W) :- diagonal(W)`

