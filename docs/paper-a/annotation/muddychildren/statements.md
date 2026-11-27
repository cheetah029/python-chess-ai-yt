# muddychildren -- statements to label

## The rules of play

Two children, ann and bob. First, nature makes at least one of them muddy. Each child sees the other's forehead but not their own. Then, for three rounds, both children say yes or no at the same time, and must say yes exactly when they know they are muddy; each hears what the other said. A child wins if, at the end, they know whether they are muddy.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(ann)
  1  role(bob)
  2  role(random)
  3  init(round(0))
  4  yesno(0)
  5  yesno(1)
  6  child(ann)
  7  child(bob)
  8  legal(random,muddy(A,B)) :- true(round(0)) & yesno(A) & yesno(B) & oneMuddy(A,B)
  9  oneMuddy(1,B) :- yesno(B)
 10  oneMuddy(0,1)
 11  legal(C,noop) :- child(C) & true(round(0))
 12  legal(random,noop) :- ~true(round(0))
 13  next(has(ann,mud)) :- does(random,muddy(1,B))
 14  next(has(bob,mud)) :- does(random,muddy(A,1))
 15  next(has(C,mud)) :- true(has(C,mud))
 16  sees(C,dirt(D)) :- child(C) & true(has(D,mud)) & distinct(C,D)
 17  isMuddy(C) :- true(has(C,mud))
 18  isClean(C) :- child(C) & ~true(has(C,mud))
 19  someMuddy :- true(has(C,mud))
 20  knowsOwn(C) :- knows(C,isMuddy(C))
 21  knowsOwn(C) :- knows(C,isClean(C))
 22  legal(C,say(yes)) :- child(C) & ~true(round(0)) & knows(C,isMuddy(C))
 23  legal(C,say(no)) :- child(C) & ~true(round(0)) & ~knows(C,isMuddy(C))
 24  sees(C,said(D,X)) :- child(C) & does(D,say(X))
 25  next(round(1)) :- true(round(0))
 26  next(round(2)) :- true(round(1))
 27  next(round(3)) :- true(round(2))
 28  terminal :- true(round(3))
 29  goal(C,100) :- child(C) & knowsOwn(C)
 30  goal(C,0) :- child(C) & ~knowsOwn(C)
 31  goal(random,0)
```
