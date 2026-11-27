# cherylsbirthday -- statements to label

## The rules of play

Nature picks Cheryl's birthday from ten given dates. Albert is told the month and Bernard the day. Then, in turn and in public, each says yes or no to a statement, and must say yes exactly when it is true: Albert, "I do not know the date, and I know Bernard does not know it"; Bernard, "now I know the date"; Albert, "now I know it too". A listener wins if at the end they know the date.

## The statements, numbered as on the sheet

`~` is "not", `&` is "and", and `true(...)` reads the current position, `does(...)` the move being played, and `next(...)` what holds after it. Capitalised words are variables.

```
  0  role(albert)
  1  role(bernard)
  2  role(random)
  3  init(round(0))
  4  date(may,15)
  5  date(may,16)
  6  date(may,19)
  7  date(june,17)
  8  date(june,18)
  9  date(july,14)
 10  date(july,16)
 11  date(august,14)
 12  date(august,15)
 13  date(august,17)
 14  listener(albert)
 15  listener(bernard)
 16  legal(random,birthday(M,D)) :- true(round(0)) & date(M,D)
 17  legal(random,noop) :- ~true(round(0))
 18  next(birthday(M,D)) :- does(random,birthday(M,D))
 19  next(birthday(M,D)) :- true(birthday(M,D))
 20  sees(albert,month(M)) :- does(random,birthday(M,D))
 21  sees(bernard,day(D)) :- does(random,birthday(M,D))
 22  isDate(M,D) :- true(birthday(M,D))
 23  knowsDate(R) :- listener(R) & knows(R,isDate(M,D))
 24  bernardIgnorant :- ~knowsDate(bernard)
 25  firstClaim :- ~knowsDate(albert) & knows(albert,bernardIgnorant)
 26  legal(albert,noop) :- true(round(0))
 27  legal(bernard,noop) :- true(round(0))
 28  legal(albert,say(yes)) :- true(round(1)) & firstClaim
 29  legal(albert,say(no)) :- true(round(1)) & ~firstClaim
 30  legal(bernard,noop) :- true(round(1))
 31  legal(bernard,say(yes)) :- true(round(2)) & knowsDate(bernard)
 32  legal(bernard,say(no)) :- true(round(2)) & ~knowsDate(bernard)
 33  legal(albert,noop) :- true(round(2))
 34  legal(albert,say(yes)) :- true(round(3)) & knowsDate(albert)
 35  legal(albert,say(no)) :- true(round(3)) & ~knowsDate(albert)
 36  legal(bernard,noop) :- true(round(3))
 37  sees(L,said(S,X)) :- listener(L) & does(S,say(X))
 38  next(round(1)) :- true(round(0))
 39  next(round(2)) :- true(round(1))
 40  next(round(3)) :- true(round(2))
 41  next(round(4)) :- true(round(3))
 42  terminal :- true(round(4))
 43  goal(R,100) :- listener(R) & knowsDate(R)
 44  goal(R,0) :- listener(R) & ~knowsDate(R)
 45  goal(random,0)
```
