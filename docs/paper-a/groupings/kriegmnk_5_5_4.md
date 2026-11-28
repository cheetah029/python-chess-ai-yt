# kriegmnk_5_5_4 -- groupings

File: `lgref/identify/testgames/kriegmnk_5_5_4.gdl`. Line numbers are lines of that file.

- **lgref**: 6 groups, 0 statements in no group
- **random_matched**: 6 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 16 | `role(xplayer)` | G05 | G01 |
| 17 | `role(oplayer)` | G05 | G01 |
| 18 | `symbol(xplayer,x)` | G02 | G01 |
| 19 | `symbol(oplayer,o)` | G02 | G02 |
| 20 | `init(cell(1,1,b))` | G01 | G00 |
| 21 | `init(cell(1,2,b))` | G01 | G00 |
| 22 | `init(cell(1,3,b))` | G01 | G00 |
| 23 | `init(cell(1,4,b))` | G01 | G01 |
| 24 | `init(cell(1,5,b))` | G01 | G01 |
| 25 | `init(cell(2,1,b))` | G01 | G01 |
| 26 | `init(cell(2,2,b))` | G01 | G01 |
| 27 | `init(cell(2,3,b))` | G01 | G01 |
| 28 | `init(cell(2,4,b))` | G01 | G00 |
| 29 | `init(cell(2,5,b))` | G01 | G00, G04 |
| 30 | `init(cell(3,1,b))` | G01 | G01 |
| 31 | `init(cell(3,2,b))` | G01 | G02 |
| 32 | `init(cell(3,3,b))` | G01 | G02 |
| 33 | `init(cell(3,4,b))` | G01 | G00 |
| 34 | `init(cell(3,5,b))` | G01 | G00 |
| 35 | `init(cell(4,1,b))` | G01 | G00 |
| 36 | `init(cell(4,2,b))` | G01 | G00, G03 |
| 37 | `init(cell(4,3,b))` | G01 | G00 |
| 38 | `init(cell(4,4,b))` | G01 | G00, G03 |
| 39 | `init(cell(4,5,b))` | G01 | G01 |
| 40 | `init(cell(5,1,b))` | G01 | G05 |
| 41 | `init(cell(5,2,b))` | G01 | G01, G02 |
| 42 | `init(cell(5,3,b))` | G01 | G02 |
| 43 | `init(cell(5,4,b))` | G01 | G00 |
| 44 | `init(cell(5,5,b))` | G01 | G00, G04 |
| 45 | `init(control(xplayer))` | G02 | G01 |
| 46 | `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,W)) & symbol(P,S) & distinct(W,S) & ~true(tried(P,M,N))` | G02 | G00 |
| 47 | `legal(xplayer,noop) :- true(control(oplayer))` | G02 | G02 |
| 48 | `legal(oplayer,noop) :- true(control(xplayer))` | G02 | G00 |
| 49 | `sees(P,ok) :- does(P,mark(M,N)) & true(cell(M,N,b))` | G02 | G00 |
| 50 | `sees(P,taken) :- does(P,mark(M,N)) & ~true(cell(M,N,b))` | G02 | G01 |
| 51 | `attempted(M,N) :- does(P,mark(M,N))` | G01, G02 | G00 |
| 52 | `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)` | G01, G02 | G00 |
| 53 | `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)` | G01 | G01 |
| 54 | `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)` | G01 | G00 |
| 55 | `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))` | G02 | G00, G03 |
| 56 | `next(tried(P,M,N)) :- true(tried(P,M,N))` | G02 | G00, G03 |
| 57 | `next(control(xplayer)) :- true(control(oplayer))` | G02 | G01 |
| 58 | `next(control(oplayer)) :- true(control(xplayer))` | G02 | G01 |
| 59 | `open :- true(cell(M,N,b))` | G00, G04 | G00 |
| 60 | `terminal :- line(x)` | G00, G04 | G01 |
| 61 | `terminal :- line(o)` | G00, G04 | G00 |
| 62 | `terminal :- ~open` | G00, G04 | G00 |
| 63 | `goal(xplayer,100) :- line(x)` | G00, G03 | G01 |
| 64 | `goal(xplayer,0) :- line(o)` | G00, G03 | G05 |
| 65 | `goal(xplayer,50) :- ~line(x) & ~line(o)` | G00, G03 | G00 |
| 66 | `goal(oplayer,100) :- line(o)` | G00, G03 | G02 |
| 67 | `goal(oplayer,0) :- line(x)` | G00, G03 | G00 |
| 68 | `goal(oplayer,50) :- ~line(x) & ~line(o)` | G00, G03 | G01 |
| 69 | `line(W) :- true(cell(1,1,W)) & true(cell(1,2,W)) & true(cell(1,3,W)) & true(cell(1,4,W)) & distinct(W,b)` | G00 | G00 |
| 70 | `line(W) :- true(cell(1,1,W)) & true(cell(2,1,W)) & true(cell(3,1,W)) & true(cell(4,1,W)) & distinct(W,b)` | G00 | G00 |
| 71 | `line(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W)) & true(cell(4,4,W)) & distinct(W,b)` | G00 | G02 |
| 72 | `line(W) :- true(cell(1,2,W)) & true(cell(1,3,W)) & true(cell(1,4,W)) & true(cell(1,5,W)) & distinct(W,b)` | G00 | G01 |
| 73 | `line(W) :- true(cell(1,2,W)) & true(cell(2,2,W)) & true(cell(3,2,W)) & true(cell(4,2,W)) & distinct(W,b)` | G00 | G00 |
| 74 | `line(W) :- true(cell(1,2,W)) & true(cell(2,3,W)) & true(cell(3,4,W)) & true(cell(4,5,W)) & distinct(W,b)` | G00 | G00, G04 |
| 75 | `line(W) :- true(cell(1,3,W)) & true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & distinct(W,b)` | G00 | G01 |
| 76 | `line(W) :- true(cell(1,4,W)) & true(cell(2,4,W)) & true(cell(3,4,W)) & true(cell(4,4,W)) & distinct(W,b)` | G00 | G01 |
| 77 | `line(W) :- true(cell(1,4,W)) & true(cell(2,3,W)) & true(cell(3,2,W)) & true(cell(4,1,W)) & distinct(W,b)` | G00 | G00 |
| 78 | `line(W) :- true(cell(1,5,W)) & true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & distinct(W,b)` | G00 | G00 |
| 79 | `line(W) :- true(cell(1,5,W)) & true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & distinct(W,b)` | G00 | G01 |
| 80 | `line(W) :- true(cell(2,1,W)) & true(cell(2,2,W)) & true(cell(2,3,W)) & true(cell(2,4,W)) & distinct(W,b)` | G00 | G00 |
| 81 | `line(W) :- true(cell(2,1,W)) & true(cell(3,1,W)) & true(cell(4,1,W)) & true(cell(5,1,W)) & distinct(W,b)` | G00 | G00 |
| 82 | `line(W) :- true(cell(2,1,W)) & true(cell(3,2,W)) & true(cell(4,3,W)) & true(cell(5,4,W)) & distinct(W,b)` | G00 | G01 |
| 83 | `line(W) :- true(cell(2,2,W)) & true(cell(2,3,W)) & true(cell(2,4,W)) & true(cell(2,5,W)) & distinct(W,b)` | G00 | G01 |
| 84 | `line(W) :- true(cell(2,2,W)) & true(cell(3,2,W)) & true(cell(4,2,W)) & true(cell(5,2,W)) & distinct(W,b)` | G00 | G00 |
| 85 | `line(W) :- true(cell(2,2,W)) & true(cell(3,3,W)) & true(cell(4,4,W)) & true(cell(5,5,W)) & distinct(W,b)` | G00 | G01 |
| 86 | `line(W) :- true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & true(cell(5,3,W)) & distinct(W,b)` | G00 | G00, G03 |
| 87 | `line(W) :- true(cell(2,4,W)) & true(cell(3,4,W)) & true(cell(4,4,W)) & true(cell(5,4,W)) & distinct(W,b)` | G00 | G02 |
| 88 | `line(W) :- true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & true(cell(5,1,W)) & distinct(W,b)` | G00 | G00, G03 |
| 89 | `line(W) :- true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & true(cell(5,5,W)) & distinct(W,b)` | G00 | G01, G02 |
| 90 | `line(W) :- true(cell(2,5,W)) & true(cell(3,4,W)) & true(cell(4,3,W)) & true(cell(5,2,W)) & distinct(W,b)` | G00 | G02 |
| 91 | `line(W) :- true(cell(3,1,W)) & true(cell(3,2,W)) & true(cell(3,3,W)) & true(cell(3,4,W)) & distinct(W,b)` | G00 | G02 |
| 92 | `line(W) :- true(cell(3,2,W)) & true(cell(3,3,W)) & true(cell(3,4,W)) & true(cell(3,5,W)) & distinct(W,b)` | G00 | G01 |
| 93 | `line(W) :- true(cell(4,1,W)) & true(cell(4,2,W)) & true(cell(4,3,W)) & true(cell(4,4,W)) & distinct(W,b)` | G00 | G02 |
| 94 | `line(W) :- true(cell(4,2,W)) & true(cell(4,3,W)) & true(cell(4,4,W)) & true(cell(4,5,W)) & distinct(W,b)` | G00 | G01 |
| 95 | `line(W) :- true(cell(5,1,W)) & true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & distinct(W,b)` | G00 | G00, G04 |
| 96 | `line(W) :- true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & true(cell(5,5,W)) & distinct(W,b)` | G00 | G02 |

## lgref by group

### lgref G00 (38 statements)

- line 59: `open :- true(cell(M,N,b))` (also in G04)
- line 60: `terminal :- line(x)` (also in G04)
- line 61: `terminal :- line(o)` (also in G04)
- line 62: `terminal :- ~open` (also in G04)
- line 63: `goal(xplayer,100) :- line(x)` (also in G03)
- line 64: `goal(xplayer,0) :- line(o)` (also in G03)
- line 65: `goal(xplayer,50) :- ~line(x) & ~line(o)` (also in G03)
- line 66: `goal(oplayer,100) :- line(o)` (also in G03)
- line 67: `goal(oplayer,0) :- line(x)` (also in G03)
- line 68: `goal(oplayer,50) :- ~line(x) & ~line(o)` (also in G03)
- line 69: `line(W) :- true(cell(1,1,W)) & true(cell(1,2,W)) & true(cell(1,3,W)) & true(cell(1,4,W)) & distinct(W,b)`
- line 70: `line(W) :- true(cell(1,1,W)) & true(cell(2,1,W)) & true(cell(3,1,W)) & true(cell(4,1,W)) & distinct(W,b)`
- line 71: `line(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W)) & true(cell(4,4,W)) & distinct(W,b)`
- line 72: `line(W) :- true(cell(1,2,W)) & true(cell(1,3,W)) & true(cell(1,4,W)) & true(cell(1,5,W)) & distinct(W,b)`
- line 73: `line(W) :- true(cell(1,2,W)) & true(cell(2,2,W)) & true(cell(3,2,W)) & true(cell(4,2,W)) & distinct(W,b)`
- line 74: `line(W) :- true(cell(1,2,W)) & true(cell(2,3,W)) & true(cell(3,4,W)) & true(cell(4,5,W)) & distinct(W,b)`
- line 75: `line(W) :- true(cell(1,3,W)) & true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & distinct(W,b)`
- line 76: `line(W) :- true(cell(1,4,W)) & true(cell(2,4,W)) & true(cell(3,4,W)) & true(cell(4,4,W)) & distinct(W,b)`
- line 77: `line(W) :- true(cell(1,4,W)) & true(cell(2,3,W)) & true(cell(3,2,W)) & true(cell(4,1,W)) & distinct(W,b)`
- line 78: `line(W) :- true(cell(1,5,W)) & true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & distinct(W,b)`
- line 79: `line(W) :- true(cell(1,5,W)) & true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & distinct(W,b)`
- line 80: `line(W) :- true(cell(2,1,W)) & true(cell(2,2,W)) & true(cell(2,3,W)) & true(cell(2,4,W)) & distinct(W,b)`
- line 81: `line(W) :- true(cell(2,1,W)) & true(cell(3,1,W)) & true(cell(4,1,W)) & true(cell(5,1,W)) & distinct(W,b)`
- line 82: `line(W) :- true(cell(2,1,W)) & true(cell(3,2,W)) & true(cell(4,3,W)) & true(cell(5,4,W)) & distinct(W,b)`
- line 83: `line(W) :- true(cell(2,2,W)) & true(cell(2,3,W)) & true(cell(2,4,W)) & true(cell(2,5,W)) & distinct(W,b)`
- line 84: `line(W) :- true(cell(2,2,W)) & true(cell(3,2,W)) & true(cell(4,2,W)) & true(cell(5,2,W)) & distinct(W,b)`
- line 85: `line(W) :- true(cell(2,2,W)) & true(cell(3,3,W)) & true(cell(4,4,W)) & true(cell(5,5,W)) & distinct(W,b)`
- line 86: `line(W) :- true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & true(cell(5,3,W)) & distinct(W,b)`
- line 87: `line(W) :- true(cell(2,4,W)) & true(cell(3,4,W)) & true(cell(4,4,W)) & true(cell(5,4,W)) & distinct(W,b)`
- line 88: `line(W) :- true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & true(cell(5,1,W)) & distinct(W,b)`
- line 89: `line(W) :- true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & true(cell(5,5,W)) & distinct(W,b)`
- line 90: `line(W) :- true(cell(2,5,W)) & true(cell(3,4,W)) & true(cell(4,3,W)) & true(cell(5,2,W)) & distinct(W,b)`
- line 91: `line(W) :- true(cell(3,1,W)) & true(cell(3,2,W)) & true(cell(3,3,W)) & true(cell(3,4,W)) & distinct(W,b)`
- line 92: `line(W) :- true(cell(3,2,W)) & true(cell(3,3,W)) & true(cell(3,4,W)) & true(cell(3,5,W)) & distinct(W,b)`
- line 93: `line(W) :- true(cell(4,1,W)) & true(cell(4,2,W)) & true(cell(4,3,W)) & true(cell(4,4,W)) & distinct(W,b)`
- line 94: `line(W) :- true(cell(4,2,W)) & true(cell(4,3,W)) & true(cell(4,4,W)) & true(cell(4,5,W)) & distinct(W,b)`
- line 95: `line(W) :- true(cell(5,1,W)) & true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & distinct(W,b)`
- line 96: `line(W) :- true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & true(cell(5,5,W)) & distinct(W,b)`

### lgref G01 (29 statements)

- line 20: `init(cell(1,1,b))`
- line 21: `init(cell(1,2,b))`
- line 22: `init(cell(1,3,b))`
- line 23: `init(cell(1,4,b))`
- line 24: `init(cell(1,5,b))`
- line 25: `init(cell(2,1,b))`
- line 26: `init(cell(2,2,b))`
- line 27: `init(cell(2,3,b))`
- line 28: `init(cell(2,4,b))`
- line 29: `init(cell(2,5,b))`
- line 30: `init(cell(3,1,b))`
- line 31: `init(cell(3,2,b))`
- line 32: `init(cell(3,3,b))`
- line 33: `init(cell(3,4,b))`
- line 34: `init(cell(3,5,b))`
- line 35: `init(cell(4,1,b))`
- line 36: `init(cell(4,2,b))`
- line 37: `init(cell(4,3,b))`
- line 38: `init(cell(4,4,b))`
- line 39: `init(cell(4,5,b))`
- line 40: `init(cell(5,1,b))`
- line 41: `init(cell(5,2,b))`
- line 42: `init(cell(5,3,b))`
- line 43: `init(cell(5,4,b))`
- line 44: `init(cell(5,5,b))`
- line 51: `attempted(M,N) :- does(P,mark(M,N))` (also in G02)
- line 52: `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)` (also in G02)
- line 53: `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)`
- line 54: `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)`

### lgref G02 (14 statements)

- line 18: `symbol(xplayer,x)`
- line 19: `symbol(oplayer,o)`
- line 45: `init(control(xplayer))`
- line 46: `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,W)) & symbol(P,S) & distinct(W,S) & ~true(tried(P,M,N))`
- line 47: `legal(xplayer,noop) :- true(control(oplayer))`
- line 48: `legal(oplayer,noop) :- true(control(xplayer))`
- line 49: `sees(P,ok) :- does(P,mark(M,N)) & true(cell(M,N,b))`
- line 50: `sees(P,taken) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 51: `attempted(M,N) :- does(P,mark(M,N))` (also in G01)
- line 52: `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)` (also in G01)
- line 55: `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 56: `next(tried(P,M,N)) :- true(tried(P,M,N))`
- line 57: `next(control(xplayer)) :- true(control(oplayer))`
- line 58: `next(control(oplayer)) :- true(control(xplayer))`

### lgref G03 (6 statements)

- line 63: `goal(xplayer,100) :- line(x)` (also in G00)
- line 64: `goal(xplayer,0) :- line(o)` (also in G00)
- line 65: `goal(xplayer,50) :- ~line(x) & ~line(o)` (also in G00)
- line 66: `goal(oplayer,100) :- line(o)` (also in G00)
- line 67: `goal(oplayer,0) :- line(x)` (also in G00)
- line 68: `goal(oplayer,50) :- ~line(x) & ~line(o)` (also in G00)

### lgref G04 (4 statements)

- line 59: `open :- true(cell(M,N,b))` (also in G00)
- line 60: `terminal :- line(x)` (also in G00)
- line 61: `terminal :- line(o)` (also in G00)
- line 62: `terminal :- ~open` (also in G00)

### lgref G05 (2 statements)

- line 16: `role(xplayer)`
- line 17: `role(oplayer)`


## random_matched by group

### random_matched G00 (38 statements)

- line 20: `init(cell(1,1,b))`
- line 21: `init(cell(1,2,b))`
- line 22: `init(cell(1,3,b))`
- line 28: `init(cell(2,4,b))`
- line 29: `init(cell(2,5,b))` (also in G04)
- line 33: `init(cell(3,4,b))`
- line 34: `init(cell(3,5,b))`
- line 35: `init(cell(4,1,b))`
- line 36: `init(cell(4,2,b))` (also in G03)
- line 37: `init(cell(4,3,b))`
- line 38: `init(cell(4,4,b))` (also in G03)
- line 43: `init(cell(5,4,b))`
- line 44: `init(cell(5,5,b))` (also in G04)
- line 46: `legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,W)) & symbol(P,S) & distinct(W,S) & ~true(tried(P,M,N))`
- line 48: `legal(oplayer,noop) :- true(control(xplayer))`
- line 49: `sees(P,ok) :- does(P,mark(M,N)) & true(cell(M,N,b))`
- line 51: `attempted(M,N) :- does(P,mark(M,N))`
- line 52: `next(cell(M,N,S)) :- does(P,mark(M,N)) & true(cell(M,N,b)) & symbol(P,S)`
- line 54: `next(cell(M,N,b)) :- true(cell(M,N,b)) & ~attempted(M,N)`
- line 55: `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))` (also in G03)
- line 56: `next(tried(P,M,N)) :- true(tried(P,M,N))` (also in G03)
- line 59: `open :- true(cell(M,N,b))`
- line 61: `terminal :- line(o)`
- line 62: `terminal :- ~open`
- line 65: `goal(xplayer,50) :- ~line(x) & ~line(o)`
- line 67: `goal(oplayer,0) :- line(x)`
- line 69: `line(W) :- true(cell(1,1,W)) & true(cell(1,2,W)) & true(cell(1,3,W)) & true(cell(1,4,W)) & distinct(W,b)`
- line 70: `line(W) :- true(cell(1,1,W)) & true(cell(2,1,W)) & true(cell(3,1,W)) & true(cell(4,1,W)) & distinct(W,b)`
- line 73: `line(W) :- true(cell(1,2,W)) & true(cell(2,2,W)) & true(cell(3,2,W)) & true(cell(4,2,W)) & distinct(W,b)`
- line 74: `line(W) :- true(cell(1,2,W)) & true(cell(2,3,W)) & true(cell(3,4,W)) & true(cell(4,5,W)) & distinct(W,b)` (also in G04)
- line 77: `line(W) :- true(cell(1,4,W)) & true(cell(2,3,W)) & true(cell(3,2,W)) & true(cell(4,1,W)) & distinct(W,b)`
- line 78: `line(W) :- true(cell(1,5,W)) & true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & distinct(W,b)`
- line 80: `line(W) :- true(cell(2,1,W)) & true(cell(2,2,W)) & true(cell(2,3,W)) & true(cell(2,4,W)) & distinct(W,b)`
- line 81: `line(W) :- true(cell(2,1,W)) & true(cell(3,1,W)) & true(cell(4,1,W)) & true(cell(5,1,W)) & distinct(W,b)`
- line 84: `line(W) :- true(cell(2,2,W)) & true(cell(3,2,W)) & true(cell(4,2,W)) & true(cell(5,2,W)) & distinct(W,b)`
- line 86: `line(W) :- true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & true(cell(5,3,W)) & distinct(W,b)` (also in G03)
- line 88: `line(W) :- true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & true(cell(5,1,W)) & distinct(W,b)` (also in G03)
- line 95: `line(W) :- true(cell(5,1,W)) & true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & distinct(W,b)` (also in G04)

### random_matched G01 (29 statements)

- line 16: `role(xplayer)`
- line 17: `role(oplayer)`
- line 18: `symbol(xplayer,x)`
- line 23: `init(cell(1,4,b))`
- line 24: `init(cell(1,5,b))`
- line 25: `init(cell(2,1,b))`
- line 26: `init(cell(2,2,b))`
- line 27: `init(cell(2,3,b))`
- line 30: `init(cell(3,1,b))`
- line 39: `init(cell(4,5,b))`
- line 41: `init(cell(5,2,b))` (also in G02)
- line 45: `init(control(xplayer))`
- line 50: `sees(P,taken) :- does(P,mark(M,N)) & ~true(cell(M,N,b))`
- line 53: `next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)`
- line 57: `next(control(xplayer)) :- true(control(oplayer))`
- line 58: `next(control(oplayer)) :- true(control(xplayer))`
- line 60: `terminal :- line(x)`
- line 63: `goal(xplayer,100) :- line(x)`
- line 68: `goal(oplayer,50) :- ~line(x) & ~line(o)`
- line 72: `line(W) :- true(cell(1,2,W)) & true(cell(1,3,W)) & true(cell(1,4,W)) & true(cell(1,5,W)) & distinct(W,b)`
- line 75: `line(W) :- true(cell(1,3,W)) & true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & distinct(W,b)`
- line 76: `line(W) :- true(cell(1,4,W)) & true(cell(2,4,W)) & true(cell(3,4,W)) & true(cell(4,4,W)) & distinct(W,b)`
- line 79: `line(W) :- true(cell(1,5,W)) & true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & distinct(W,b)`
- line 82: `line(W) :- true(cell(2,1,W)) & true(cell(3,2,W)) & true(cell(4,3,W)) & true(cell(5,4,W)) & distinct(W,b)`
- line 83: `line(W) :- true(cell(2,2,W)) & true(cell(2,3,W)) & true(cell(2,4,W)) & true(cell(2,5,W)) & distinct(W,b)`
- line 85: `line(W) :- true(cell(2,2,W)) & true(cell(3,3,W)) & true(cell(4,4,W)) & true(cell(5,5,W)) & distinct(W,b)`
- line 89: `line(W) :- true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & true(cell(5,5,W)) & distinct(W,b)` (also in G02)
- line 92: `line(W) :- true(cell(3,2,W)) & true(cell(3,3,W)) & true(cell(3,4,W)) & true(cell(3,5,W)) & distinct(W,b)`
- line 94: `line(W) :- true(cell(4,2,W)) & true(cell(4,3,W)) & true(cell(4,4,W)) & true(cell(4,5,W)) & distinct(W,b)`

### random_matched G02 (14 statements)

- line 19: `symbol(oplayer,o)`
- line 31: `init(cell(3,2,b))`
- line 32: `init(cell(3,3,b))`
- line 41: `init(cell(5,2,b))` (also in G01)
- line 42: `init(cell(5,3,b))`
- line 47: `legal(xplayer,noop) :- true(control(oplayer))`
- line 66: `goal(oplayer,100) :- line(o)`
- line 71: `line(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W)) & true(cell(4,4,W)) & distinct(W,b)`
- line 87: `line(W) :- true(cell(2,4,W)) & true(cell(3,4,W)) & true(cell(4,4,W)) & true(cell(5,4,W)) & distinct(W,b)`
- line 89: `line(W) :- true(cell(2,5,W)) & true(cell(3,5,W)) & true(cell(4,5,W)) & true(cell(5,5,W)) & distinct(W,b)` (also in G01)
- line 90: `line(W) :- true(cell(2,5,W)) & true(cell(3,4,W)) & true(cell(4,3,W)) & true(cell(5,2,W)) & distinct(W,b)`
- line 91: `line(W) :- true(cell(3,1,W)) & true(cell(3,2,W)) & true(cell(3,3,W)) & true(cell(3,4,W)) & distinct(W,b)`
- line 93: `line(W) :- true(cell(4,1,W)) & true(cell(4,2,W)) & true(cell(4,3,W)) & true(cell(4,4,W)) & distinct(W,b)`
- line 96: `line(W) :- true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & true(cell(5,5,W)) & distinct(W,b)`

### random_matched G03 (6 statements)

- line 36: `init(cell(4,2,b))` (also in G00)
- line 38: `init(cell(4,4,b))` (also in G00)
- line 55: `next(tried(P,M,N)) :- does(P,mark(M,N)) & ~true(cell(M,N,b))` (also in G00)
- line 56: `next(tried(P,M,N)) :- true(tried(P,M,N))` (also in G00)
- line 86: `line(W) :- true(cell(2,3,W)) & true(cell(3,3,W)) & true(cell(4,3,W)) & true(cell(5,3,W)) & distinct(W,b)` (also in G00)
- line 88: `line(W) :- true(cell(2,4,W)) & true(cell(3,3,W)) & true(cell(4,2,W)) & true(cell(5,1,W)) & distinct(W,b)` (also in G00)

### random_matched G04 (4 statements)

- line 29: `init(cell(2,5,b))` (also in G00)
- line 44: `init(cell(5,5,b))` (also in G00)
- line 74: `line(W) :- true(cell(1,2,W)) & true(cell(2,3,W)) & true(cell(3,4,W)) & true(cell(4,5,W)) & distinct(W,b)` (also in G00)
- line 95: `line(W) :- true(cell(5,1,W)) & true(cell(5,2,W)) & true(cell(5,3,W)) & true(cell(5,4,W)) & distinct(W,b)` (also in G00)

### random_matched G05 (2 statements)

- line 40: `init(cell(5,1,b))`
- line 64: `goal(xplayer,0) :- line(o)`

