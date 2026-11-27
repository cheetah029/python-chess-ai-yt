# dotsboxes_2x2 -- statements to label

## The rules of play

A 3x3 grid of dots enclosing four boxes, with twelve possible lines between neighbouring dots. Players a and b take turns drawing a line that is not yet drawn; a moves first. A line that completes one or two boxes scores a point per box, and the same player moves again. When every line is drawn, more points wins; equal points is a draw.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(a)
  1  role(b)
  2  line(h(1,1))
  3  line(h(2,1))
  4  line(h(1,2))
  5  line(h(2,2))
  6  line(h(1,3))
  7  line(h(2,3))
  8  line(v(1,1))
  9  line(v(2,1))
 10  line(v(3,1))
 11  line(v(1,2))
 12  line(v(2,2))
 13  line(v(3,2))
 14  bounds(h(I,J),b(I,J)) :- box(I,J)
 15  bounds(h(I,J2),b(I,J)) :- box(I,J) & succ(J,J2)
 16  bounds(v(I,J),b(I,J)) :- box(I,J)
 17  bounds(v(I2,J),b(I,J)) :- box(I,J) & succ(I,I2)
 18  box(1,1)
 19  box(1,2)
 20  box(2,1)
 21  box(2,2)
 22  succ(0,1)
 23  succ(1,2)
 24  succ(2,3)
 25  succ(3,4)
 26  plus2(0,2)
 27  plus2(1,3)
 28  plus2(2,4)
 29  more(A,B) :- succ(B,A)
 30  more(A,C) :- succ(B,A) & more(B,C)
 31  opponent(a,b)
 32  opponent(b,a)
 33  legal(P,draw(L)) :- true(control(P)) & line(L) & ~true(drawn(L))
 34  next(drawn(L)) :- does(P,draw(L))
 35  next(drawn(L)) :- true(drawn(L))
 36  gap(L,B) :- bounds(L2,B) & distinct(L2,L) & ~true(drawn(L2))
 37  closes(B) :- does(P,draw(L)) & bounds(L,B) & ~gap(L,B)
 38  completed :- closes(B)
 39  double :- closes(B) & closes(B2) & distinct(B,B2)
 40  next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & completed & ~double & succ(N,N2)
 41  next(score(P,N2)) :- does(P,draw(L)) & true(score(P,N)) & double & plus2(N,N2)
 42  next(score(P,N)) :- true(score(P,N)) & ~scorer(P)
 43  scorer(P) :- does(P,draw(L)) & completed
 44  next(control(P)) :- does(P,draw(L)) & completed
 45  legal(Q,noop) :- true(control(P)) & opponent(P,Q)
 46  next(control(Q)) :- does(P,draw(L)) & ~completed & opponent(P,Q)
 47  undrawn :- line(L) & ~true(drawn(L))
 48  terminal :- ~undrawn
 49  goal(P,100) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(N,M)
 50  goal(P,50) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,N))
 51  goal(P,0) :- ~undrawn & opponent(P,Q) & true(score(P,N)) & true(score(Q,M)) & more(M,N)
 52  init(score(a,0))
 53  init(score(b,0))
 54  init(control(a))
```
