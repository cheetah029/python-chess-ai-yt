# montyhall -- groupings

File: `lgref/identify/testgames/montyhall.gdl`. Line numbers are lines of that file.

- **lgref**: 7 groups, 0 statements in no group
- **random_matched**: 7 groups, 0 statements in no group

## Side by side

| line | statement | lgref | random_matched |
|---|---|---|---|
| 8 | `role(candidate)` | G06 | G04 |
| 9 | `role(random)` | G06 | G03 |
| 10 | `door(1)` | G02 | G00 |
| 11 | `door(2)` | G02 | G06 |
| 12 | `door(3)` | G02 | G00, G05 |
| 13 | `init(closed(1))` | G04 | G02 |
| 14 | `init(closed(2))` | G04 | G00, G01, G03, G05 |
| 15 | `init(closed(3))` | G04 | G04 |
| 16 | `init(step(1))` | G03 | G03 |
| 17 | `legal(random,hide_car(D)) :- true(step(1)) & door(D)` | G00, G02 | G01, G02, G03, G05 |
| 18 | `legal(random,open_door(D)) :- true(step(2)) & true(closed(D)) & ~true(car(D)) & ~true(chosen(D))` | G00 | G06 |
| 19 | `legal(random,noop) :- true(step(3))` | G00 | G01, G03 |
| 20 | `legal(candidate,choose(D)) :- true(step(1)) & door(D)` | G00, G02 | G01 |
| 21 | `legal(candidate,noop) :- true(step(2))` | G00 | G01, G03 |
| 22 | `legal(candidate,noop) :- true(step(3))` | G00 | G00, G02 |
| 23 | `legal(candidate,switch) :- true(step(3))` | G00, G05 | G01, G05 |
| 24 | `sees(candidate,opened(D)) :- does(random,open_door(D))` | G00 | G03 |
| 25 | `next(car(D)) :- does(random,hide_car(D))` | G00, G01, G03, G05 | G02 |
| 26 | `next(car(D)) :- true(car(D))` | G01, G03 | G02 |
| 27 | `next(closed(D)) :- true(closed(D)) & ~does(random,open_door(D))` | G00, G04 | G00 |
| 28 | `next(chosen(D)) :- does(candidate,choose(D))` | G01, G02, G03, G05 | G00 |
| 29 | `next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)` | G01, G05 | G00, G02 |
| 30 | `next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))` | G01, G05 | G00, G04 |
| 31 | `next(step(2)) :- true(step(1))` | G03 | G00 |
| 32 | `next(step(3)) :- true(step(2))` | G03 | G01 |
| 33 | `next(step(4)) :- true(step(3))` | G03 | G00 |
| 34 | `terminal :- true(step(4))` | G01, G03 | G04 |
| 35 | `goal(candidate,100) :- true(chosen(D)) & true(car(D))` | G01 | G01 |
| 36 | `goal(candidate,0) :- true(chosen(D)) & ~true(car(D))` | G01 | G01, G05 |
| 37 | `goal(random,0)` | G01 | G03 |

## lgref by group

### lgref G00 (10 statements)

- line 17: `legal(random,hide_car(D)) :- true(step(1)) & door(D)` (also in G02)
- line 18: `legal(random,open_door(D)) :- true(step(2)) & true(closed(D)) & ~true(car(D)) & ~true(chosen(D))`
- line 19: `legal(random,noop) :- true(step(3))`
- line 20: `legal(candidate,choose(D)) :- true(step(1)) & door(D)` (also in G02)
- line 21: `legal(candidate,noop) :- true(step(2))`
- line 22: `legal(candidate,noop) :- true(step(3))`
- line 23: `legal(candidate,switch) :- true(step(3))` (also in G05)
- line 24: `sees(candidate,opened(D)) :- does(random,open_door(D))`
- line 25: `next(car(D)) :- does(random,hide_car(D))` (also in G01, G03, G05)
- line 27: `next(closed(D)) :- true(closed(D)) & ~does(random,open_door(D))` (also in G04)

### lgref G01 (9 statements)

- line 25: `next(car(D)) :- does(random,hide_car(D))` (also in G00, G03, G05)
- line 26: `next(car(D)) :- true(car(D))` (also in G03)
- line 28: `next(chosen(D)) :- does(candidate,choose(D))` (also in G02, G03, G05)
- line 29: `next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)` (also in G05)
- line 30: `next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))` (also in G05)
- line 34: `terminal :- true(step(4))` (also in G03)
- line 35: `goal(candidate,100) :- true(chosen(D)) & true(car(D))`
- line 36: `goal(candidate,0) :- true(chosen(D)) & ~true(car(D))`
- line 37: `goal(random,0)`

### lgref G02 (6 statements)

- line 10: `door(1)`
- line 11: `door(2)`
- line 12: `door(3)`
- line 17: `legal(random,hide_car(D)) :- true(step(1)) & door(D)` (also in G00)
- line 20: `legal(candidate,choose(D)) :- true(step(1)) & door(D)` (also in G00)
- line 28: `next(chosen(D)) :- does(candidate,choose(D))` (also in G01, G03, G05)

### lgref G03 (8 statements)

- line 16: `init(step(1))`
- line 25: `next(car(D)) :- does(random,hide_car(D))` (also in G00, G01, G05)
- line 26: `next(car(D)) :- true(car(D))` (also in G01)
- line 28: `next(chosen(D)) :- does(candidate,choose(D))` (also in G01, G02, G05)
- line 31: `next(step(2)) :- true(step(1))`
- line 32: `next(step(3)) :- true(step(2))`
- line 33: `next(step(4)) :- true(step(3))`
- line 34: `terminal :- true(step(4))` (also in G01)

### lgref G04 (4 statements)

- line 13: `init(closed(1))`
- line 14: `init(closed(2))`
- line 15: `init(closed(3))`
- line 27: `next(closed(D)) :- true(closed(D)) & ~does(random,open_door(D))` (also in G00)

### lgref G05 (5 statements)

- line 23: `legal(candidate,switch) :- true(step(3))` (also in G00)
- line 25: `next(car(D)) :- does(random,hide_car(D))` (also in G00, G01, G03)
- line 28: `next(chosen(D)) :- does(candidate,choose(D))` (also in G01, G02, G03)
- line 29: `next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)` (also in G01)
- line 30: `next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))` (also in G01)

### lgref G06 (2 statements)

- line 8: `role(candidate)`
- line 9: `role(random)`


## random_matched by group

### random_matched G00 (10 statements)

- line 10: `door(1)`
- line 12: `door(3)` (also in G05)
- line 14: `init(closed(2))` (also in G01, G03, G05)
- line 22: `legal(candidate,noop) :- true(step(3))` (also in G02)
- line 27: `next(closed(D)) :- true(closed(D)) & ~does(random,open_door(D))`
- line 28: `next(chosen(D)) :- does(candidate,choose(D))`
- line 29: `next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)` (also in G02)
- line 30: `next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))` (also in G04)
- line 31: `next(step(2)) :- true(step(1))`
- line 33: `next(step(4)) :- true(step(3))`

### random_matched G01 (9 statements)

- line 14: `init(closed(2))` (also in G00, G03, G05)
- line 17: `legal(random,hide_car(D)) :- true(step(1)) & door(D)` (also in G02, G03, G05)
- line 19: `legal(random,noop) :- true(step(3))` (also in G03)
- line 20: `legal(candidate,choose(D)) :- true(step(1)) & door(D)`
- line 21: `legal(candidate,noop) :- true(step(2))` (also in G03)
- line 23: `legal(candidate,switch) :- true(step(3))` (also in G05)
- line 32: `next(step(3)) :- true(step(2))`
- line 35: `goal(candidate,100) :- true(chosen(D)) & true(car(D))`
- line 36: `goal(candidate,0) :- true(chosen(D)) & ~true(car(D))` (also in G05)

### random_matched G02 (6 statements)

- line 13: `init(closed(1))`
- line 17: `legal(random,hide_car(D)) :- true(step(1)) & door(D)` (also in G01, G03, G05)
- line 22: `legal(candidate,noop) :- true(step(3))` (also in G00)
- line 25: `next(car(D)) :- does(random,hide_car(D))`
- line 26: `next(car(D)) :- true(car(D))`
- line 29: `next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)` (also in G00)

### random_matched G03 (8 statements)

- line 9: `role(random)`
- line 14: `init(closed(2))` (also in G00, G01, G05)
- line 16: `init(step(1))`
- line 17: `legal(random,hide_car(D)) :- true(step(1)) & door(D)` (also in G01, G02, G05)
- line 19: `legal(random,noop) :- true(step(3))` (also in G01)
- line 21: `legal(candidate,noop) :- true(step(2))` (also in G01)
- line 24: `sees(candidate,opened(D)) :- does(random,open_door(D))`
- line 37: `goal(random,0)`

### random_matched G04 (4 statements)

- line 8: `role(candidate)`
- line 15: `init(closed(3))`
- line 30: `next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))` (also in G00)
- line 34: `terminal :- true(step(4))`

### random_matched G05 (5 statements)

- line 12: `door(3)` (also in G00)
- line 14: `init(closed(2))` (also in G00, G01, G03)
- line 17: `legal(random,hide_car(D)) :- true(step(1)) & door(D)` (also in G01, G02, G03)
- line 23: `legal(candidate,switch) :- true(step(3))` (also in G01)
- line 36: `goal(candidate,0) :- true(chosen(D)) & ~true(car(D))` (also in G01)

### random_matched G06 (2 statements)

- line 11: `door(2)`
- line 18: `legal(random,open_door(D)) :- true(step(2)) & true(closed(D)) & ~true(car(D)) & ~true(chosen(D))`

