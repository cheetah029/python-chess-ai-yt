# synth_redundant -- statements to label

## The rules of play

Red and blue share a tally that starts at 0; red moves first. On a turn a player either adds 1 to the tally, or adds 2 (at most once per game), or lights their own lamp (once per game; the tally stays). The tally may not pass 6. The player who brings it to exactly 6 wins. A player whose lamp is lit may add 1.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(red)
  1  role(blue)
  2  plus(0,1,1)
  3  plus(1,1,2)
  4  plus(2,1,3)
  5  plus(3,1,4)
  6  plus(4,1,5)
  7  plus(5,1,6)
  8  plus(0,2,2)
  9  plus(1,2,3)
 10  plus(2,2,4)
 11  plus(3,2,5)
 12  plus(4,2,6)
 13  opponent(red,blue)
 14  opponent(blue,red)
 15  legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)
 16  next(tally(M)) :- does(P,add(1)) & true(tally(N)) & plus(N,1,M)
 17  legal(P,add(2)) :- true(control(P)) & true(tally(N)) & plus(N,2,M) & true(token(P))
 18  next(tally(M)) :- does(P,add(2)) & true(tally(N)) & plus(N,2,M)
 19  next(token(P)) :- true(token(P)) & ~does(P,add(2))
 20  legal(P,light) :- true(control(P)) & ~true(lit(P))
 21  next(lit(P)) :- does(P,light)
 22  next(lit(P)) :- true(lit(P))
 23  next(tally(N)) :- true(tally(N)) & does(P,light)
 24  legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M) & true(lit(P))
 25  legal(Q,noop) :- true(control(P)) & opponent(P,Q)
 26  next(control(Q)) :- true(control(P)) & opponent(P,Q)
 27  terminal :- true(tally(6))
 28  goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))
 29  goal(P,0) :- true(tally(6)) & true(control(P))
 30  init(tally(0))
 31  init(token(red))
 32  init(token(blue))
 33  init(control(red))
```
