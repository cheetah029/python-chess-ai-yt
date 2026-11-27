# hex_3x3 -- statements to label

## The rules of play

A 3x3 board of hexagonal cells. Red and blue take turns placing a stone of their colour on an empty cell; red moves first. Red wins by joining the bottom row to the top row with a chain of touching red stones, blue by joining the left column to the right column with blue stones.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(red)
  1  role(blue)
  2  index(1)
  3  index(2)
  4  index(3)
  5  succ(1,2)
  6  succ(2,3)
  7  touches(X,Y,X2,Y) :- succ(X,X2) & index(Y)
  8  touches(X,Y,X2,Y) :- succ(X2,X) & index(Y)
  9  touches(X,Y,X,Y2) :- index(X) & succ(Y,Y2)
 10  touches(X,Y,X,Y2) :- index(X) & succ(Y2,Y)
 11  touches(X,Y,X2,Y2) :- succ(X,X2) & succ(Y2,Y)
 12  touches(X,Y,X2,Y2) :- succ(X2,X) & succ(Y,Y2)
 13  opponent(red,blue)
 14  opponent(blue,red)
 15  legal(P,place(X,Y)) :- true(control(P)) & index(X) & index(Y) & ~taken(X,Y)
 16  taken(X,Y) :- true(cell(X,Y,P))
 17  next(cell(X,Y,P)) :- does(P,place(X,Y))
 18  next(cell(X,Y,P)) :- true(cell(X,Y,P))
 19  legal(red,noop) :- true(control(blue))
 20  legal(blue,noop) :- true(control(red))
 21  next(control(red)) :- true(control(blue))
 22  next(control(blue)) :- true(control(red))
 23  firstedge(red,X,1) :- index(X)
 24  firstedge(blue,1,Y) :- index(Y)
 25  lastedge(red,X,3) :- index(X)
 26  lastedge(blue,3,Y) :- index(Y)
 27  reach(P,X,Y) :- firstedge(P,X,Y) & true(cell(X,Y,P))
 28  reach(P,X2,Y2) :- reach(P,X,Y) & touches(X,Y,X2,Y2) & true(cell(X2,Y2,P))
 29  joined(P) :- reach(P,X,Y) & lastedge(P,X,Y)
 30  terminal :- joined(P)
 31  goal(P,100) :- joined(P)
 32  goal(P,0) :- opponent(P,Q) & joined(Q)
 33  init(control(red))
```
