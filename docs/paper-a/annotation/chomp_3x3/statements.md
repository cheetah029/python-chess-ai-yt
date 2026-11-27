# chomp_3x3 -- statements to label

## The rules of play

A 3x3 bar of chocolate; the bottom-left square is poisoned. Players take turns choosing a remaining square and eating it together with every square above it and to its right. The player who eats the poisoned square loses.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(first)
  1  role(second)
  2  atmost(1,1)
  3  atmost(1,2)
  4  atmost(1,3)
  5  atmost(2,2)
  6  atmost(2,3)
  7  atmost(3,3)
  8  opponent(first,second)
  9  opponent(second,first)
 10  legal(P,bite(X,Y)) :- true(control(P)) & true(square(X,Y))
 11  eaten(X2,Y2) :- does(P,bite(X,Y)) & atmost(X,X2) & atmost(Y,Y2)
 12  next(square(X,Y)) :- true(square(X,Y)) & ~eaten(X,Y)
 13  legal(first,noop) :- true(control(second))
 14  legal(second,noop) :- true(control(first))
 15  next(control(first)) :- true(control(second))
 16  next(control(second)) :- true(control(first))
 17  poisoned :- ~true(square(1,1))
 18  terminal :- poisoned
 19  goal(P,100) :- poisoned & true(control(P))
 20  goal(P,0) :- poisoned & true(control(Q)) & opponent(P,Q)
 21  init(square(1,1))
 22  init(square(1,2))
 23  init(square(1,3))
 24  init(square(2,1))
 25  init(square(2,2))
 26  init(square(2,3))
 27  init(square(3,1))
 28  init(square(3,2))
 29  init(square(3,3))
 30  init(control(first))
```
