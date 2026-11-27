# dropthree -- statements to label

## The rules of play

A grid four columns wide and three rows high, standing upright. Two players, red and yellow, take turns dropping a counter into a column that is not full; red moves first. A counter falls to the lowest empty cell of its column. Three of one colour in a row, in a column or on a diagonal wins. If the grid fills with no such line, the game ends with no winner.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(red)
  1  role(yellow)
  2  legal(P,drop(C)) :- true(control(P)) & landing(C,R)
  3  next(cell(C,R,r)) :- does(red,drop(C)) & landing(C,R)
  4  next(cell(C,R,y)) :- does(yellow,drop(C)) & landing(C,R)
  5  next(cell(C,R,W)) :- true(cell(C,R,W)) & distinct(W,b)
  6  next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(D)) & distinct(C,D)
  7  next(cell(C,R,b)) :- true(cell(C,R,b)) & does(P,drop(C)) & ~landing(C,R)
  8  below(1,2)
  9  below(2,3)
 10  landing(C,1) :- true(cell(C,1,b))
 11  landing(C,R) :- true(cell(C,R,b)) & below(Q,R) & ~true(cell(C,Q,b))
 12  legal(red,noop) :- true(control(yellow))
 13  legal(yellow,noop) :- true(control(red))
 14  next(control(red)) :- true(control(yellow))
 15  next(control(yellow)) :- true(control(red))
 16  right(1,2)
 17  right(2,3)
 18  right(3,4)
 19  hline(W) :- right(A,B) & right(B,C) & true(cell(A,R,W)) & true(cell(B,R,W)) & true(cell(C,R,W)) & distinct(W,b)
 20  vline(W) :- true(cell(C,1,W)) & true(cell(C,2,W)) & true(cell(C,3,W)) & distinct(W,b)
 21  dline(W) :- right(A,B) & right(B,C) & true(cell(A,1,W)) & true(cell(B,2,W)) & true(cell(C,3,W)) & distinct(W,b)
 22  dline(W) :- right(A,B) & right(B,C) & true(cell(A,3,W)) & true(cell(B,2,W)) & true(cell(C,1,W)) & distinct(W,b)
 23  line(W) :- hline(W)
 24  line(W) :- vline(W)
 25  line(W) :- dline(W)
 26  open :- true(cell(C,R,b))
 27  terminal :- line(r)
 28  terminal :- line(y)
 29  terminal :- ~open
 30  goal(red,100) :- line(r)
 31  goal(yellow,100) :- line(y)
 32  init(cell(1,1,b))
 33  init(cell(1,2,b))
 34  init(cell(1,3,b))
 35  init(cell(2,1,b))
 36  init(cell(2,2,b))
 37  init(cell(2,3,b))
 38  init(cell(3,1,b))
 39  init(cell(3,2,b))
 40  init(cell(3,3,b))
 41  init(cell(4,1,b))
 42  init(cell(4,2,b))
 43  init(cell(4,3,b))
 44  init(control(red))
```
