# montyhall -- statements to label

## The rules of play

A game show with three doors. First, the host (a random player) hides a car behind one door while the candidate picks a door. Second, the host opens a door that is still closed, hides no car and was not picked; the candidate sees which. Third, the candidate may switch to the other closed door, or stay. The candidate wins if the door they end with hides the car.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(candidate)
  1  role(random)
  2  door(1)
  3  door(2)
  4  door(3)
  5  init(closed(1))
  6  init(closed(2))
  7  init(closed(3))
  8  init(step(1))
  9  legal(random,hide_car(D)) :- true(step(1)) & door(D)
 10  legal(random,open_door(D)) :- true(step(2)) & true(closed(D)) & ~true(car(D)) & ~true(chosen(D))
 11  legal(random,noop) :- true(step(3))
 12  legal(candidate,choose(D)) :- true(step(1)) & door(D)
 13  legal(candidate,noop) :- true(step(2))
 14  legal(candidate,noop) :- true(step(3))
 15  legal(candidate,switch) :- true(step(3))
 16  sees(candidate,opened(D)) :- does(random,open_door(D))
 17  next(car(D)) :- does(random,hide_car(D))
 18  next(car(D)) :- true(car(D))
 19  next(closed(D)) :- true(closed(D)) & ~does(random,open_door(D))
 20  next(chosen(D)) :- does(candidate,choose(D))
 21  next(chosen(D)) :- true(chosen(D)) & ~does(candidate,switch)
 22  next(chosen(D)) :- does(candidate,switch) & true(closed(D)) & ~true(chosen(D))
 23  next(step(2)) :- true(step(1))
 24  next(step(3)) :- true(step(2))
 25  next(step(4)) :- true(step(3))
 26  terminal :- true(step(4))
 27  goal(candidate,100) :- true(chosen(D)) & true(car(D))
 28  goal(candidate,0) :- true(chosen(D)) & ~true(car(D))
 29  goal(random,0)
```
