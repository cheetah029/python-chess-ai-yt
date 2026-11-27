"""Plain-Python implementations of the pilot games, for checking the GDL.

A GDL description can load, play and terminate and still encode the
wrong game: a flip that misses a direction, a capture allowed straight
ahead. So each pilot is written a SECOND time here, in ordinary Python
from the rules in the game file's header, and `lgref.bench.wellformed`
compares the two in every state it visits: same legal moves for each
role, same successor state for each joint move, same ending, same
payoff.

The two encodings were written by the same author (Claude), so an
agreement rules out encoding slips, not a misreading of the rules that
both share. The rules themselves are short enough to check by eye.

States use the GDL's own facts -- tuples such as ('cell', '2', '3',
'black') and ('control', 'white') -- so no translation sits between
the two implementations.
"""


class Breakthrough(object):
    """Breakthrough on an n x n board: two home rows each side."""

    roles = ('black', 'white')

    def __init__(self, size=5):
        self.size = size

    def initial(self):
        n = self.size
        facts = {('control', 'white')}
        for x in range(1, n + 1):
            for y in (1, 2):
                facts.add(('cell', str(x), str(y), 'white'))
            for y in (n - 1, n):
                facts.add(('cell', str(x), str(y), 'black'))
        return frozenset(facts)

    @staticmethod
    def _board(state):
        return {(int(f[1]), int(f[2])): f[3] for f in state
                if f[0] == 'cell'}

    @staticmethod
    def _mover(state):
        return next(f[1] for f in state if f[0] == 'control')

    def _moves_of(self, board, player):
        n = self.size
        dy = 1 if player == 'white' else -1
        enemy = 'black' if player == 'white' else 'white'
        out = []
        for (x, y), owner in board.items():
            if owner != player:
                continue
            y2 = y + dy
            if not 1 <= y2 <= n:
                continue
            if (x, y2) not in board:
                out.append((x, y, x, y2))
            for x2 in (x - 1, x + 1):
                if not 1 <= x2 <= n:
                    continue
                there = board.get((x2, y2))
                if there is None or there == enemy:
                    out.append((x, y, x2, y2))
        return out

    def _arrived(self, board):
        return {owner for (x, y), owner in board.items()
                if (owner == 'white' and y == self.size)
                or (owner == 'black' and y == 1)}

    def legal(self, state, role):
        board, mover = self._board(state), self._mover(state)
        if role != mover:
            return ['noop']
        return sorted(('move',) + tuple(str(v) for v in m)
                      for m in self._moves_of(board, role))

    def terminal(self, state):
        board, mover = self._board(state), self._mover(state)
        return bool(self._arrived(board)) or not self._moves_of(board,
                                                                mover)

    def goals(self, state):
        board, mover = self._board(state), self._mover(state)
        arrived = self._arrived(board)
        stuck = set() if self._moves_of(board, mover) else {mover}
        out = {}
        for role in self.roles:
            other = 'black' if role == 'white' else 'white'
            values = set()
            if role in arrived or other in stuck:
                values.add(100)
            if other in arrived or role in stuck:
                values.add(0)
            out[role] = values
        return out

    def next(self, state, moves):
        board, mover = self._board(state), self._mover(state)
        move = moves[mover]
        x, y, x2, y2 = (int(v) for v in move[1:])
        board = dict(board)
        del board[(x, y)]
        board[(x2, y2)] = mover
        other = 'black' if mover == 'white' else 'white'
        facts = {('control', other)}
        for (a, b), owner in board.items():
            facts.add(('cell', str(a), str(b), owner))
        return frozenset(facts)


DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0),
              (1, 1), (-1, 1), (1, -1), (-1, -1))


class Othello(object):
    """Othello on an n x n board, with passing."""

    roles = ('black', 'white')

    def __init__(self, size=4):
        self.size = size

    def initial(self):
        return frozenset({('cell', '2', '2', 'white'),
                          ('cell', '3', '3', 'white'),
                          ('cell', '2', '3', 'black'),
                          ('cell', '3', '2', 'black'),
                          ('control', 'black')})

    _board = staticmethod(Breakthrough._board)
    _mover = staticmethod(Breakthrough._mover)

    def _flips(self, board, player, x, y):
        """Every disc placing at (x, y) would flip, over all lines."""
        if (x, y) in board:
            return set()
        enemy = 'white' if player == 'black' else 'black'
        n = self.size
        out = set()
        for dx, dy in DIRECTIONS:
            run = []
            a, b = x + dx, y + dy
            while 1 <= a <= n and 1 <= b <= n and board.get((a, b)) == enemy:
                run.append((a, b))
                a, b = a + dx, b + dy
            if run and 1 <= a <= n and 1 <= b <= n \
                    and board.get((a, b)) == player:
                out.update(run)
        return out

    def _placements(self, board, player):
        n = self.size
        return [(x, y) for x in range(1, n + 1) for y in range(1, n + 1)
                if self._flips(board, player, x, y)]

    def legal(self, state, role):
        board, mover = self._board(state), self._mover(state)
        if role != mover:
            return ['noop']
        spots = self._placements(board, role)
        if not spots:
            return ['pass']
        return sorted(('place', str(x), str(y)) for x, y in spots)

    def terminal(self, state):
        board = self._board(state)
        return not any(self._placements(board, p) for p in self.roles)

    def goals(self, state):
        board = self._board(state)
        count = {p: sum(1 for o in board.values() if o == p)
                 for p in self.roles}
        out = {}
        for role in self.roles:
            other = 'white' if role == 'black' else 'black'
            if count[role] > count[other]:
                out[role] = {100}
            elif count[role] < count[other]:
                out[role] = {0}
            else:
                out[role] = {50}
        return out

    def next(self, state, moves):
        board, mover = self._board(state), self._mover(state)
        move = moves[mover]
        board = dict(board)
        if move != 'pass':
            x, y = int(move[1]), int(move[2])
            for spot in self._flips(board, mover, x, y):
                board[spot] = mover
            board[(x, y)] = mover
        other = 'white' if mover == 'black' else 'black'
        facts = {('control', other)}
        for (a, b), owner in board.items():
            facts.add(('cell', str(a), str(b), owner))
        return frozenset(facts)


def _facts(*items):
    return frozenset(items)


def _num(value):
    return str(value)


class Chomp(object):
    """Chomp on a 3x3 bar; (1,1) is poisoned and eating it loses."""

    roles = ('first', 'second')

    def initial(self):
        squares = {('square', _num(x), _num(y))
                   for x in (1, 2, 3) for y in (1, 2, 3)}
        return frozenset(squares | {('control', 'first')})

    @staticmethod
    def _squares(state):
        return {(int(f[1]), int(f[2])) for f in state if f[0] == 'square'}

    _mover = staticmethod(Breakthrough._mover)

    def legal(self, state, role):
        if role != self._mover(state):
            return ['noop']
        return sorted(('bite', _num(x), _num(y))
                      for x, y in self._squares(state))

    def terminal(self, state):
        return (1, 1) not in self._squares(state)

    def goals(self, state):
        mover = self._mover(state)
        return {r: ({100} if r == mover else {0}) for r in self.roles}

    def next(self, state, moves):
        mover = self._mover(state)
        _b, x, y = moves[mover]
        x, y = int(x), int(y)
        left = {(a, b) for a, b in self._squares(state)
                if not (a >= x and b >= y)}
        other = 'second' if mover == 'first' else 'first'
        return frozenset({('square', _num(a), _num(b)) for a, b in left}
                         | {('control', other)})


class Hex(object):
    """Hex on a 3x3 rhombus: red joins Y=1 to Y=3, blue X=1 to X=3."""

    roles = ('blue', 'red')
    NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))

    def initial(self):
        return frozenset({('control', 'red')})

    _board = staticmethod(Breakthrough._board)
    _mover = staticmethod(Breakthrough._mover)

    def _joined(self, board, player):
        if player == 'red':
            frontier = [(x, 1) for x in (1, 2, 3)
                        if board.get((x, 1)) == player]
        else:
            frontier = [(1, y) for y in (1, 2, 3)
                        if board.get((1, y)) == player]
        seen = set(frontier)
        while frontier:
            x, y = frontier.pop()
            far = y if player == 'red' else x
            if far == 3:
                return True
            for dx, dy in self.NEIGHBOURS:
                cell = (x + dx, y + dy)
                if cell not in seen and board.get(cell) == player:
                    seen.add(cell)
                    frontier.append(cell)
        return False

    def legal(self, state, role):
        if role != self._mover(state):
            return ['noop']
        board = self._board(state)
        return sorted(('place', _num(x), _num(y)) for x in (1, 2, 3)
                      for y in (1, 2, 3) if (x, y) not in board)

    def terminal(self, state):
        board = self._board(state)
        return any(self._joined(board, p) for p in self.roles)

    def goals(self, state):
        board = self._board(state)
        out = {}
        for role in self.roles:
            other = 'red' if role == 'blue' else 'blue'
            values = set()
            if self._joined(board, role):
                values.add(100)
            if self._joined(board, other):
                values.add(0)
            out[role] = values
        return out

    def next(self, state, moves):
        mover = self._mover(state)
        _p, x, y = moves[mover]
        other = 'red' if mover == 'blue' else 'blue'
        facts = {f for f in state if f[0] == 'cell'}
        facts.add(('cell', x, y, mover))
        facts.add(('control', other))
        return frozenset(facts)


class Kalah(object):
    """Kalah with three pits a side, one seed each, no wrap-around."""

    roles = ('north', 'south')
    PITS = {'south': ('s1', 's2', 's3'), 'north': ('n1', 'n2', 'n3')}
    STORE = {'south': 'sstore', 'north': 'nstore'}
    OPPOSITE = {'s1': 'n3', 's2': 'n2', 's3': 'n1',
                'n1': 's3', 'n2': 's2', 'n3': 's1'}

    def initial(self):
        facts = {('seeds', p, '1') for side in self.PITS.values()
                 for p in side}
        facts |= {('store', 'south', '0'), ('store', 'north', '0'),
                  ('control', 'south')}
        return frozenset(facts)

    @staticmethod
    def _read(state):
        pits = {f[1]: int(f[2]) for f in state if f[0] == 'seeds'}
        stores = {f[1]: int(f[2]) for f in state if f[0] == 'store'}
        mover = next(f[1] for f in state if f[0] == 'control')
        return pits, stores, mover

    def _order(self, player):
        other = 'north' if player == 'south' else 'south'
        return (list(self.PITS[player]) + [self.STORE[player]]
                + list(self.PITS[other]))

    def legal(self, state, role):
        pits, _stores, mover = self._read(state)
        if role != mover:
            return ['noop']
        return sorted(('sow', p) for p in self.PITS[role] if pits[p])

    def terminal(self, state):
        pits, _stores, mover = self._read(state)
        return not any(pits[p] for p in self.PITS[mover])

    def goals(self, state):
        pits, stores, _mover = self._read(state)
        total = {r: stores[r] + sum(pits[p] for p in self.PITS[r])
                 for r in self.roles}
        out = {}
        for role in self.roles:
            other = 'north' if role == 'south' else 'south'
            if total[role] > total[other]:
                out[role] = {100}
            elif total[role] < total[other]:
                out[role] = {0}
            else:
                out[role] = {50}
        return out

    def next(self, state, moves):
        pits, stores, mover = self._read(state)
        pits, stores = dict(pits), dict(stores)
        pit = moves[mover][1]
        ring = self._order(mover)
        count, pits[pit] = pits[pit], 0
        position = ring.index(pit)
        place = None
        for _seed in range(count):
            position = (position + 1) % len(ring)
            place = ring[position]
            if place == pit:
                raise ValueError('a sowing came round to its own pit')
            if place == self.STORE[mover]:
                stores[mover] += 1
            else:
                pits[place] += 1
        again = place == self.STORE[mover]
        if place in self.PITS[mover] and pits[place] == 1:
            facing = self.OPPOSITE[place]
            if pits[facing]:
                stores[mover] += 1 + pits[facing]
                pits[place] = pits[facing] = 0
        other = 'north' if mover == 'south' else 'south'
        facts = {('seeds', p, _num(n)) for p, n in pits.items()}
        facts |= {('store', r, _num(n)) for r, n in stores.items()}
        facts.add(('control', mover if again else other))
        return frozenset(facts)


class DotsBoxes(object):
    """Dots and boxes on a 3x3 grid of dots (four boxes)."""

    roles = ('a', 'b')

    def __init__(self):
        self.lines = ([('h', _num(i), _num(y)) for i in (1, 2)
                       for y in (1, 2, 3)]
                      + [('v', _num(x), _num(j)) for x in (1, 2, 3)
                         for j in (1, 2)])
        self.boxes = {}
        for i in (1, 2):
            for j in (1, 2):
                self.boxes[(i, j)] = {('h', _num(i), _num(j)),
                                      ('h', _num(i), _num(j + 1)),
                                      ('v', _num(i), _num(j)),
                                      ('v', _num(i + 1), _num(j))}

    def initial(self):
        return frozenset({('score', 'a', '0'), ('score', 'b', '0'),
                          ('control', 'a')})

    @staticmethod
    def _read(state):
        drawn = {f[1] for f in state if f[0] == 'drawn'}
        score = {f[1]: int(f[2]) for f in state if f[0] == 'score'}
        mover = next(f[1] for f in state if f[0] == 'control')
        return drawn, score, mover

    def legal(self, state, role):
        drawn, _score, mover = self._read(state)
        if role != mover:
            return ['noop']
        return sorted(('draw', line) for line in self.lines
                      if line not in drawn)

    def terminal(self, state):
        drawn, _score, _mover = self._read(state)
        return len(drawn) == len(self.lines)

    def goals(self, state):
        _drawn, score, _mover = self._read(state)
        out = {}
        for role in self.roles:
            other = 'b' if role == 'a' else 'a'
            if score[role] > score[other]:
                out[role] = {100}
            elif score[role] < score[other]:
                out[role] = {0}
            else:
                out[role] = {50}
        return out

    def next(self, state, moves):
        drawn, score, mover = self._read(state)
        line = moves[mover][1]
        after = drawn | {line}
        made = sum(1 for sides in self.boxes.values()
                   if line in sides and sides <= after)
        score = dict(score)
        score[mover] += made
        other = 'b' if mover == 'a' else 'a'
        facts = {('drawn', d) for d in after}
        facts |= {('score', r, _num(n)) for r, n in score.items()}
        facts.add(('control', mover if made else other))
        return frozenset(facts)


class Checkers(object):
    """Checkers on 4x4: forced single jumps, kings, a 16-turn draw."""

    roles = ('black', 'white')
    LIMIT = 16

    def initial(self):
        return frozenset({('at', 'white', 'man', '2', '1'),
                          ('at', 'white', 'man', '4', '1'),
                          ('at', 'black', 'man', '1', '4'),
                          ('at', 'black', 'man', '3', '4'),
                          ('control', 'white'), ('tick', '0')})

    @staticmethod
    def _read(state):
        pieces = {(int(f[3]), int(f[4])): (f[1], f[2]) for f in state
                  if f[0] == 'at'}
        mover = next(f[1] for f in state if f[0] == 'control')
        tick = next(int(f[1]) for f in state if f[0] == 'tick')
        return pieces, mover, tick

    @staticmethod
    def _rows(player, kind):
        if kind == 'king':
            return (1, -1)
        return (1,) if player == 'white' else (-1,)

    def _moves(self, pieces, player):
        steps, jumps = [], []
        for (x, y), (owner, kind) in pieces.items():
            if owner != player:
                continue
            for dy in self._rows(player, kind):
                for dx in (1, -1):
                    a, b = x + dx, y + dy
                    if not (1 <= a <= 4 and 1 <= b <= 4):
                        continue
                    if (a, b) not in pieces:
                        steps.append((x, y, a, b))
                        continue
                    c, d = a + dx, b + dy
                    if pieces[(a, b)][0] != player \
                            and 1 <= c <= 4 and 1 <= d <= 4 \
                            and (c, d) not in pieces:
                        jumps.append((x, y, c, d))
        return steps, jumps

    def legal(self, state, role):
        pieces, mover, _tick = self._read(state)
        if role != mover:
            return ['noop']
        steps, jumps = self._moves(pieces, role)
        out = [('jump',) + tuple(_num(v) for v in m) for m in jumps]
        if not jumps:
            out += [('step',) + tuple(_num(v) for v in m) for m in steps]
        return sorted(out)

    def _stuck(self, state):
        pieces, mover, _tick = self._read(state)
        steps, jumps = self._moves(pieces, mover)
        return not steps and not jumps

    def terminal(self, state):
        return self._stuck(state) or self._read(state)[2] == self.LIMIT

    def goals(self, state):
        _pieces, mover, _tick = self._read(state)
        if self._stuck(state):
            return {r: ({0} if r == mover else {100}) for r in self.roles}
        return {r: {50} for r in self.roles}

    def next(self, state, moves):
        pieces, mover, tick = self._read(state)
        kind, x, y, a, b = moves[mover]
        x, y, a, b = int(x), int(y), int(a), int(b)
        pieces = dict(pieces)
        owner, rank = pieces.pop((x, y))
        if kind == 'jump':
            del pieces[((x + a) // 2, (y + b) // 2)]
        if (owner == 'white' and b == 4) or (owner == 'black' and b == 1):
            rank = 'king'
        pieces[(a, b)] = (owner, rank)
        other = 'black' if mover == 'white' else 'white'
        facts = {('at', o, k, _num(p), _num(q))
                 for (p, q), (o, k) in pieces.items()}
        facts |= {('control', other), ('tick', _num(tick + 1))}
        return frozenset(facts)


class FoxGeese(object):
    """Fox and geese on 4x4: four geese, a jumping fox, 20 turns."""

    roles = ('fox', 'geese')
    LIMIT = 20

    def initial(self):
        facts = {('goose', _num(x), '1') for x in (1, 2, 3, 4)}
        facts |= {('fox', '3', '4'), ('lost', '0'), ('control', 'geese'),
                  ('tick', '0')}
        return frozenset(facts)

    @staticmethod
    def _read(state):
        geese = {(int(f[1]), int(f[2])) for f in state if f[0] == 'goose'}
        fox = [(int(f[1]), int(f[2])) for f in state if f[0] == 'fox']
        lost = next(int(f[1]) for f in state if f[0] == 'lost')
        mover = next(f[1] for f in state if f[0] == 'control')
        tick = next(int(f[1]) for f in state if f[0] == 'tick')
        return geese, fox, lost, mover, tick

    @staticmethod
    def _inside(x, y):
        return 1 <= x <= 4 and 1 <= y <= 4

    def _moves(self, state, role):
        geese, fox, _lost, _mover, _tick = self._read(state)
        full = geese | set(fox)
        out = []
        if role == 'geese':
            for x, y in geese:
                for dx, dy in ((0, 1), (1, 0), (-1, 0)):
                    a, b = x + dx, y + dy
                    if self._inside(a, b) and (a, b) not in full:
                        out.append(('glide', x, y, a, b))
            return out
        for x, y in fox:
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                a, b = x + dx, y + dy
                if not self._inside(a, b):
                    continue
                if (a, b) not in full:
                    out.append(('step', x, y, a, b))
                elif (a, b) in geese:
                    c, d = a + dx, b + dy
                    if self._inside(c, d) and (c, d) not in full:
                        out.append(('jump', x, y, c, d))
        return out

    def legal(self, state, role):
        mover = self._read(state)[3]
        if role != mover:
            return ['noop']
        return sorted((m[0],) + tuple(_num(v) for v in m[1:])
                      for m in self._moves(state, role))

    def _winner(self, state):
        _geese, _fox, lost, mover, tick = self._read(state)
        stuck = not self._moves(state, mover)
        if stuck and mover == 'fox':
            return 'geese'
        if lost == 2 or (stuck and mover == 'geese') or tick == self.LIMIT:
            return 'fox'
        return None

    def terminal(self, state):
        return self._winner(state) is not None

    def goals(self, state):
        winner = self._winner(state)
        return {r: ({100} if r == winner else {0}) for r in self.roles}

    def next(self, state, moves):
        geese, fox, lost, mover, tick = self._read(state)
        kind, x, y, a, b = moves[mover]
        x, y, a, b = int(x), int(y), int(a), int(b)
        geese = set(geese)
        if kind == 'glide':
            geese.discard((x, y))
            geese.add((a, b))
        else:
            fox = [(a, b)]
            if kind == 'jump':
                geese.discard(((x + a) // 2, (y + b) // 2))
                lost += 1
        other = 'fox' if mover == 'geese' else 'geese'
        facts = {('goose', _num(p), _num(q)) for p, q in geese}
        facts |= {('fox', _num(p), _num(q)) for p, q in fox}
        facts |= {('lost', _num(lost)), ('control', other),
                  ('tick', _num(tick + 1))}
        return frozenset(facts)


class TallyRace(object):
    """The synthetic race (lgref/bench/synth.py): step +1, jump +2 once,
    light a lamp once; whoever makes the tally exactly 6 wins. All
    three synthetic descriptions describe this one game."""

    roles = ('blue', 'red')

    def initial(self):
        return frozenset({('tally', '0'), ('token', 'red'),
                          ('token', 'blue'), ('control', 'red')})

    @staticmethod
    def _read(state):
        tally = next(int(f[1]) for f in state if f[0] == 'tally')
        tokens = {f[1] for f in state if f[0] == 'token'}
        lit = {f[1] for f in state if f[0] == 'lit'}
        mover = next(f[1] for f in state if f[0] == 'control')
        return tally, tokens, lit, mover

    def legal(self, state, role):
        tally, tokens, lit, mover = self._read(state)
        if role != mover:
            return ['noop']
        out = []
        if tally + 1 <= 6:
            out.append(('add', '1'))
        if tally + 2 <= 6 and role in tokens:
            out.append(('add', '2'))
        if role not in lit:
            out.append('light')
        return sorted(out, key=repr)

    def terminal(self, state):
        return self._read(state)[0] == 6

    def goals(self, state):
        mover = self._read(state)[3]
        return {r: ({0} if r == mover else {100}) for r in self.roles}

    def next(self, state, moves):
        tally, tokens, lit, mover = self._read(state)
        move = moves[mover]
        tokens, lit = set(tokens), set(lit)
        if move == 'light':
            lit.add(mover)
        else:
            tally += int(move[1])
            if move[1] == '2':
                tokens.discard(mover)
        other = 'blue' if mover == 'red' else 'red'
        facts = {('tally', _num(tally)), ('control', other)}
        facts |= {('token', t) for t in tokens}
        facts |= {('lit', p) for p in lit}
        return frozenset(facts)


SIMULATORS = {
    'breakthrough5': lambda: Breakthrough(5),
    'othello4': lambda: Othello(4),
    'chomp_3x3': Chomp,
    'hex_3x3': Hex,
    'kalah_mini': Kalah,
    'dotsboxes_2x2': DotsBoxes,
    'checkers_4x4': Checkers,
    'foxgeese_mini': FoxGeese,
    'synth_independent': TallyRace,
    'synth_shared': TallyRace,
    'synth_redundant': TallyRace,
}
