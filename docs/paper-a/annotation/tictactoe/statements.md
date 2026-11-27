# tictactoe -- statements to label

## The rules of play

Two players, x and o, take turns marking a blank cell of a 3x3 grid; x moves first. Three of one mark in a row, a column or a diagonal wins. If the grid fills with no such line, the game ends with no winner.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(xplayer)
  1  role(oplayer)
  2  legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,b))
  3  legal(xplayer,noop) :- true(control(oplayer))
  4  legal(oplayer,noop) :- true(control(xplayer))
  5  next(cell(M,N,x)) :- does(xplayer,mark(M,N))
  6  next(cell(M,N,o)) :- does(oplayer,mark(M,N))
  7  next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)
  8  next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(M,J)
  9  next(cell(M,N,b)) :- true(cell(M,N,b)) & does(P,mark(J,K)) & distinct(N,K)
 10  next(control(xplayer)) :- true(control(oplayer))
 11  next(control(oplayer)) :- true(control(xplayer))
 12  row(M,W) :- true(cell(M,1,W)) & true(cell(M,2,W)) & true(cell(M,3,W))
 13  column(N,W) :- true(cell(1,N,W)) & true(cell(2,N,W)) & true(cell(3,N,W))
 14  diagonal(W) :- true(cell(1,1,W)) & true(cell(2,2,W)) & true(cell(3,3,W))
 15  diagonal(W) :- true(cell(1,3,W)) & true(cell(2,2,W)) & true(cell(3,1,W))
 16  line(W) :- row(M,W)
 17  line(W) :- column(N,W)
 18  line(W) :- diagonal(W)
 19  open :- true(cell(M,N,b))
 20  terminal :- line(x)
 21  terminal :- line(o)
 22  terminal :- ~open
 23  goal(xplayer,100) :- line(x)
 24  goal(oplayer,100) :- line(o)
 25  init(cell(1,1,b))
 26  init(cell(1,2,b))
 27  init(cell(1,3,b))
 28  init(cell(2,1,b))
 29  init(cell(2,2,b))
 30  init(cell(2,3,b))
 31  init(cell(3,1,b))
 32  init(cell(3,2,b))
 33  init(cell(3,3,b))
 34  init(control(xplayer))
```
