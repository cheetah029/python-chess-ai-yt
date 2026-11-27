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


SIMULATORS = {
    'breakthrough5': lambda: Breakthrough(5),
    'othello4': lambda: Othello(4),
}
