# tictactoe -- groupings

File: `lgref/identify/testgames/tictactoe.gdl`. Line numbers are lines of that file.

- **lgref**: 6 groups, 0 statements in no group
- **random_matched**: 6 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 7 | `role(xplayer)` | G04 | G04 |
| 8 | `role(oplayer)` | G04 | G01, G02 |
| 9 | `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,b))` | G02 | G01 |
| 10 | `legal(xplayer,noop) :- true(control(oplayer))` | G02 | G00 |
| 11 | `legal(oplayer,noop) :- true(control(xplayer))` | G02 | G00 |
| 12 | `next(cell(M,N,x)) :- does(xplayer,mark(M,N))` | G01, G02 | G01, G02 |
| 13 | `next(cell(M,N,o)) :- does(oplayer,mark(M,N))` | G01, G02 | G00 |
| 14 | `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)` | G01 | G04 |
| 15 | `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)` | G01, G02 | G00, G05 |
| 16 | `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(N,K)` | G01, G02 | G01 |
| 17 | `next(control(xplayer)) :- true(control(oplayer))` | G03 | G02 |
| 18 | `next(control(oplayer)) :- true(control(xplayer))` | G03 | G00 |
| 19 | `row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))` | G00 | G01 |
| 20 | `column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))` | G00 | G01 |
| 21 | `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` | G00, G05 | G00, G05 |
| 22 | `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))` | G00, G05 | G01 |
| 23 | `line(W) :- row(M,W)` | G00 | G01 |
| 24 | `line(W) :- column(N,W)` | G00 | G01, G02 |
| 25 | `line(W) :- diagonal(W)` | G00 | G00 |
| 26 | `open :- true(cell(M,N,b))` | G00 | G00 |
| 27 | `terminal :- line(x)` | G00 | G02 |
| 28 | `terminal :- line(o)` | G00 | G01, G02 |
| 29 | `terminal :- ~open` | G00 | G03 |
| 30 | `goal(xplayer,100) :- line(x)` | G00 | G00 |
| 31 | `goal(oplayer,100) :- line(o)` | G00 | G03 |
| 32 | `init(cell(1,1,b))` | G01 | G01 |
| 33 | `init(cell(1,2,b))` | G01 | G01 |
| 34 | `init(cell(1,3,b))` | G01 | G02 |
| 35 | `init(cell(2,1,b))` | G01 | G00 |
| 36 | `init(cell(2,2,b))` | G01 | G00 |
| 37 | `init(cell(2,3,b))` | G01 | G01 |
| 38 | `init(cell(3,1,b))` | G01 | G01 |
| 39 | `init(cell(3,2,b))` | G01 | G03 |
| 40 | `init(cell(3,3,b))` | G01 | G00 |
| 41 | `init(control(xplayer))` | G03 | G00 |

## lgref by group

### lgref G00 (13 statements)

- line 19: `row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))`
- line 20: `column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))`
- line 21: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` (also in G05)
- line 22: `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))` (also in G05)
- line 23: `line(W) :- row(M,W)`
- line 24: `line(W) :- column(N,W)`
- line 25: `line(W) :- diagonal(W)`
- line 26: `open :- true(cell(M,N,b))`
- line 27: `terminal :- line(x)`
- line 28: `terminal :- line(o)`
- line 29: `terminal :- ~open`
- line 30: `goal(xplayer,100) :- line(x)`
- line 31: `goal(oplayer,100) :- line(o)`

### lgref G01 (14 statements)

- line 12: `next(cell(M,N,x)) :- does(xplayer,mark(M,N))` (also in G02)
- line 13: `next(cell(M,N,o)) :- does(oplayer,mark(M,N))` (also in G02)
- line 14: `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)`
- line 15: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)` (also in G02)
- line 16: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(N,K)` (also in G02)
- line 32: `init(cell(1,1,b))`
- line 33: `init(cell(1,2,b))`
- line 34: `init(cell(1,3,b))`
- line 35: `init(cell(2,1,b))`
- line 36: `init(cell(2,2,b))`
- line 37: `init(cell(2,3,b))`
- line 38: `init(cell(3,1,b))`
- line 39: `init(cell(3,2,b))`
- line 40: `init(cell(3,3,b))`

### lgref G02 (7 statements)

- line 9: `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,b))`
- line 10: `legal(xplayer,noop) :- true(control(oplayer))`
- line 11: `legal(oplayer,noop) :- true(control(xplayer))`
- line 12: `next(cell(M,N,x)) :- does(xplayer,mark(M,N))` (also in G01)
- line 13: `next(cell(M,N,o)) :- does(oplayer,mark(M,N))` (also in G01)
- line 15: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)` (also in G01)
- line 16: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(N,K)` (also in G01)

### lgref G03 (3 statements)

- line 17: `next(control(xplayer)) :- true(control(oplayer))`
- line 18: `next(control(oplayer)) :- true(control(xplayer))`
- line 41: `init(control(xplayer))`

### lgref G04 (2 statements)

- line 7: `role(xplayer)`
- line 8: `role(oplayer)`

### lgref G05 (2 statements)

- line 21: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` (also in G00)
- line 22: `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))` (also in G00)


## random_matched by group

### random_matched G00 (13 statements)

- line 10: `legal(xplayer,noop) :- true(control(oplayer))`
- line 11: `legal(oplayer,noop) :- true(control(xplayer))`
- line 13: `next(cell(M,N,o)) :- does(oplayer,mark(M,N))`
- line 15: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)` (also in G05)
- line 18: `next(control(oplayer)) :- true(control(xplayer))`
- line 21: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` (also in G05)
- line 25: `line(W) :- diagonal(W)`
- line 26: `open :- true(cell(M,N,b))`
- line 30: `goal(xplayer,100) :- line(x)`
- line 35: `init(cell(2,1,b))`
- line 36: `init(cell(2,2,b))`
- line 40: `init(cell(3,3,b))`
- line 41: `init(control(xplayer))`

### random_matched G01 (14 statements)

- line 8: `role(oplayer)` (also in G02)
- line 9: `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,b))`
- line 12: `next(cell(M,N,x)) :- does(xplayer,mark(M,N))` (also in G02)
- line 16: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(N,K)`
- line 19: `row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))`
- line 20: `column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))`
- line 22: `diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))`
- line 23: `line(W) :- row(M,W)`
- line 24: `line(W) :- column(N,W)` (also in G02)
- line 28: `terminal :- line(o)` (also in G02)
- line 32: `init(cell(1,1,b))`
- line 33: `init(cell(1,2,b))`
- line 37: `init(cell(2,3,b))`
- line 38: `init(cell(3,1,b))`

### random_matched G02 (7 statements)

- line 8: `role(oplayer)` (also in G01)
- line 12: `next(cell(M,N,x)) :- does(xplayer,mark(M,N))` (also in G01)
- line 17: `next(control(xplayer)) :- true(control(oplayer))`
- line 24: `line(W) :- column(N,W)` (also in G01)
- line 27: `terminal :- line(x)`
- line 28: `terminal :- line(o)` (also in G01)
- line 34: `init(cell(1,3,b))`

### random_matched G03 (3 statements)

- line 29: `terminal :- ~open`
- line 31: `goal(oplayer,100) :- line(o)`
- line 39: `init(cell(3,2,b))`

### random_matched G04 (2 statements)

- line 7: `role(xplayer)`
- line 14: `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)`

### random_matched G05 (2 statements)

- line 15: `next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)` (also in G00)
- line 21: `diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))` (also in G00)

