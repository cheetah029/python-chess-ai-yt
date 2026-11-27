You are reviewing ways of dividing the statements of a game description
into RULES -- the parts of a game a player would name when explaining
it (how a piece moves, how a capture works, when the game ends, who
wins). Several groupings of the same statements follow, each produced
automatically. Judge each one on its own; do not rank them against each
other, and do not guess how they were made.

For EVERY group of EVERY grouping give:
  - score: an integer 1-5
      5  clearly one recognisable rule, or a sensible shared piece
         several rules need
      4  mostly one rule, with a stray statement or a missing one
      3  a plausible but loose collection
      2  mostly unrelated statements, or a rule cut into a fragment
         that means little alone
      1  arbitrary
  - reason: at most 20 words.
Then, for each grouping as a whole, an overall score 1-5 (how well it
divides the game into its rules, and how readable the result is) and a
reason of at most 30 words. A statement may sit in several groups; that
is allowed. Statements in no group are listed as ungrouped.

Answer from this text alone: do not read files, search, or run tools.
Reply with ONE JSON object and nothing else, of this shape:

{"groupings": {"G1": {"groups": {"1": {"score": 4, "reason": "..."},
                                 "2": {...}},
                      "overall": {"score": 3, "reason": "..."}},
               "G2": {...}}}


## The game

A 3x3 grid of dots enclosing four boxes, with twelve possible lines between neighbouring dots. Players a and b take turns drawing a line that is not yet drawn; a moves first. A line that completes one or two boxes scores a point per box, and the same player moves again. When every line is drawn, more points wins; equal points is a draw.

## The statements

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

## Grouping G1 (1 groups)

- group 1: statements 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54

## Grouping G2 (20 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
- group 2: statements 40, 41, 42, 52, 53
- group 3: statements 14, 15, 16, 17
- group 4: statements 18, 19, 20, 21
- group 5: statements 22, 23, 24, 25
- group 6: statements 26, 27, 28
- group 7: statements 44, 46, 54
- group 8: statements 49, 50, 51
- group 9: statements 0, 1
- group 10: statements 29, 30
- group 11: statements 31, 32
- group 12: statements 33, 45
- group 13: statements 34, 35
- group 14: statements 36
- group 15: statements 37
- group 16: statements 38
- group 17: statements 39
- group 18: statements 43
- group 19: statements 47
- group 20: statements 48

## Grouping G3 (8 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
- group 2: statements 14, 15, 16, 17, 18, 19, 20, 21, 36, 37
- group 3: statements 33, 34, 35, 38, 43, 44, 45, 46, 54
- group 4: statements 31, 32, 47, 48, 49, 50, 51
- group 5: statements 22, 23, 24, 25, 29, 30
- group 6: statements 39, 40, 41, 42, 52, 53
- group 7: statements 26, 27, 28
- group 8: statements 0, 1

## Grouping G4 (6 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 33, 47, 48
- group 2: statements 14, 15, 16, 17, 18, 19, 20, 21, 36, 37
- group 3: statements 22, 23, 24, 25, 29, 30, 40
- group 4: statements 31, 32, 45, 46, 49, 50, 51
- group 5: statements 26, 27, 28, 39, 41
- group 6: statements 38, 42, 43, 44
- ungrouped: statements 0, 1, 34, 35, 52, 53, 54

## Grouping G5 (2 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54
- group 2: statements 0, 1

## Grouping G6 (24 groups)

- group 1: statements 29, 30, 31, 32, 40, 41, 42, 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 2: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 33
- group 3: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 47
- group 4: statements 14, 15, 16, 17, 18, 19, 20, 21, 36
- group 5: statements 29, 30, 31, 32, 47, 48, 49, 50, 51
- group 6: statements 40, 41, 42, 44, 45, 46, 52, 53, 54
- group 7: statements 33, 40, 41, 44, 45, 46, 54
- group 8: statements 14, 15, 16, 17, 36, 37
- group 9: statements 15, 17, 22, 23, 24, 25
- group 10: statements 22, 23, 24, 25, 29, 30
- group 11: statements 22, 23, 24, 25, 40
- group 12: statements 22, 23, 24, 25
- group 13: statements 26, 27, 28, 41
- group 14: statements 26, 27, 28
- group 15: statements 33, 37, 43
- group 16: statements 37, 38, 43
- group 17: statements 38, 44, 46
- group 18: statements 39, 40, 41
- group 19: statements 0, 1
- group 20: statements 33, 34
- group 21: statements 34, 35
- group 22: statements 37, 39
- group 23: statements 38, 40
- group 24: statements 42, 43

## Grouping G7 (7 groups)

- group 1: statements 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 33, 47
- group 2: statements 29, 30, 31, 32, 40, 41, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 53
- group 3: statements 14, 15, 16, 17, 18, 19, 20, 21, 36, 37
- group 4: statements 15, 17, 22, 23, 24, 25, 29, 30, 40, 41, 46
- group 5: statements 26, 27, 28, 41
- group 6: statements 33, 34, 37, 40, 41, 43, 44, 45, 46, 54
- group 7: statements 0, 1
- ungrouped: statements 35, 38, 39

## Grouping G8 (7 groups)

- group 1: statements 0, 1, 4, 5, 7, 9, 31, 33, 35, 38, 40, 42, 43, 51
- group 2: statements 2, 13, 16, 19, 22, 23, 24, 25, 26, 31, 32, 36, 37, 45, 48, 50, 52
- group 3: statements 6, 11, 14, 20, 39, 41, 44, 46, 47, 53
- group 4: statements 3, 10, 13, 14, 15, 17, 23, 25, 44, 50, 52
- group 5: statements 13, 21, 27, 28
- group 6: statements 9, 13, 19, 22, 25, 30, 34, 39, 52, 54
- group 7: statements 12, 29
- ungrouped: statements 8, 18, 49

## Grouping G9 (55 groups)

- group 1: statements 0
- group 2: statements 1
- group 3: statements 2
- group 4: statements 3
- group 5: statements 4
- group 6: statements 5
- group 7: statements 6
- group 8: statements 7
- group 9: statements 8
- group 10: statements 9
- group 11: statements 10
- group 12: statements 11
- group 13: statements 12
- group 14: statements 13
- group 15: statements 14
- group 16: statements 15
- group 17: statements 16
- group 18: statements 17
- group 19: statements 18
- group 20: statements 19
- group 21: statements 20
- group 22: statements 21
- group 23: statements 22
- group 24: statements 23
- group 25: statements 24
- group 26: statements 25
- group 27: statements 26
- group 28: statements 27
- group 29: statements 28
- group 30: statements 29
- group 31: statements 30
- group 32: statements 31
- group 33: statements 32
- group 34: statements 33
- group 35: statements 34
- group 36: statements 35
- group 37: statements 36
- group 38: statements 37
- group 39: statements 38
- group 40: statements 39
- group 41: statements 40
- group 42: statements 41
- group 43: statements 42
- group 44: statements 43
- group 45: statements 44
- group 46: statements 45
- group 47: statements 46
- group 48: statements 47
- group 49: statements 48
- group 50: statements 49
- group 51: statements 50
- group 52: statements 51
- group 53: statements 52
- group 54: statements 53
- group 55: statements 54

