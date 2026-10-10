"""Solvable games at a CHOSEN branching factor, for Phase B and C.

THE MISSING RUNG. Phase C validates the search against exact solutions
and then documents the envelope in which it can be trusted. There were
only two points on that curve, and they are 6x apart:

    tic-tac-toe   branching <= 9    95% optimal at 160 simulations
    Royal Chess   branching ~58     0% SELF-AGREEMENT at 400

A conclusion drawn from two points that far apart is a guess. The
question "is one search enough for small, medium and large games, or do
we need different searches" cannot be answered from the ends alone --
what is needed is the shape in between.

An m,n,k-game supplies it: m by n board, k in a row to win, so the
branching factor is the empty-cell count and is chosen rather than
inherited. It is the same rules family as `solvable.py`'s tic-tac-toe,
which is exactly `mnk(3, 3, 3)`.

IT IS SOLVED FROM A POSITION, NOT FROM EMPTY. Solving 4x4 k=4 from the
empty board means memoising millions of states; solving it from a
position with four stones placed takes 0.47s, and with two placed 5.2s.
Since the search is being scored on positions anyway, the solver only
ever needs the subtree below one, and the prefill count is what sets the
branching factor.

WHAT THIS IS NOT. These are capability benchmarks for the EVALUATOR, not
miniatures of Royal Chess. A game with a wide board and a short win
condition is not a chess variant, and nothing about rule roles transfers
from one to the other. Phase B's benchmarks -- small games with recorded
statement-to-rule mappings, shared statements and interacting rules --
are a separate build; this is the part Phase C needs.
"""

import functools
import random

#: Win-line directions: east, south, south-east, south-west. Four is
#: enough -- the reverse of each is the same line read backwards.
_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


@functools.lru_cache(maxsize=None)
def win_lines(m, n, k):
    """Every k-in-a-row index tuple on an m x n board."""
    out = []
    for row in range(m):
        for col in range(n):
            for d_row, d_col in _DIRECTIONS:
                cells = []
                for step in range(k):
                    r, c = row + d_row * step, col + d_col * step
                    if 0 <= r < m and 0 <= c < n:
                        cells.append(r * n + c)
                if len(cells) == k:
                    out.append(tuple(cells))
    return tuple(out)


class MNK:
    """An m,n,k-game behind the engine interface the agents expect.

    `get_all_legal_turns`, `execute_turn`, `is_game_over`, `winner`,
    `current_player` -- the same surface `solvable.TicTacToe` exposes, so
    the agents play it unmodified and nothing in the search needs to know
    which game it is in.
    """

    def __init__(self, m=4, n=4, k=4, cells=None, to_move='x'):
        self.m, self.n, self.k = m, n, k
        self.cells = list(cells) if cells else [None] * (m * n)
        self.current_player = to_move
        self.turn_number = sum(1 for c in self.cells if c)
        self.max_turns = m * n

    def copy(self):
        return MNK(self.m, self.n, self.k, tuple(self.cells),
                   self.current_player)

    def get_all_legal_turns(self):
        if self.winner is not None:
            return []
        return [i for i, c in enumerate(self.cells) if c is None]

    def execute_turn(self, turn):
        self.cells[turn] = self.current_player
        self.current_player = 'o' if self.current_player == 'x' else 'x'
        self.turn_number += 1

    def is_game_over(self):
        return self.winner is not None or all(c is not None
                                              for c in self.cells)

    @property
    def winner(self):
        for line in win_lines(self.m, self.n, self.k):
            first = self.cells[line[0]]
            if first and all(self.cells[i] == first for i in line):
                return first
        return None

    def key(self):
        return (tuple(self.cells), self.current_player)

    @property
    def branching(self):
        return len(self.get_all_legal_turns())


@functools.lru_cache(maxsize=None)
def _winner_of(cells, m, n, k):
    for line in win_lines(m, n, k):
        first = cells[line[0]]
        if first and all(cells[i] == first for i in line):
            return first
    return None


@functools.lru_cache(maxsize=None)
def solve(cells, to_move, m, n, k):
    """Exact minimax value from `to_move`'s perspective: +1, 0 or -1.

    The early exit on a found win is sound rather than a heuristic: +1 is
    the maximum, so nothing below can improve on it. It is also what
    makes branching 12-14 affordable.
    """
    won = _winner_of(cells, m, n, k)
    if won is not None:
        return 1 if won == to_move else -1
    empties = [i for i, c in enumerate(cells) if c is None]
    if not empties:
        return 0
    other = 'o' if to_move == 'x' else 'x'
    best = -2
    for index in empties:
        nxt = list(cells)
        nxt[index] = to_move
        value = -solve(tuple(nxt), other, m, n, k)
        if value > best:
            best = value
            if best == 1:
                break
    return best


def optimal_moves(game):
    """(set of every value-preserving move, the position's exact value).

    A SET, because Phase C says any equally optimal action counts as
    correct and scoring against one arbitrary member would mark a perfect
    choice wrong.
    """
    cells = tuple(game.cells)
    to_move = game.current_player
    other = 'o' if to_move == 'x' else 'x'
    value = solve(cells, to_move, game.m, game.n, game.k)
    best = set()
    for index in game.get_all_legal_turns():
        nxt = list(cells)
        nxt[index] = to_move
        if -solve(tuple(nxt), other, game.m, game.n, game.k) == value:
            best.add(index)
    return best, value


#: Boards worth benchmarking on, and why this one is the default.
#:
#: A benchmark where EVERY move is optimal measures nothing: the search
#: scores 100% by picking at random. Measured as the share of legal moves
#: that preserve the position's value, at branching 9 and 12:
#:
#:   4x4 k=4    78%, 100%   <- useless; the game is a dead draw
#:   4x4 k=3    40%,  53%
#:   5x5 k=4    46%,  60%
#:   5x4 k=4    29%,  46%   <- the real decision, and the default
#:
#: So `DISCRIMINATING` is not a style preference. On 4x4 k=4 at branching
#: 12 every one of the twelve moves held the draw, and an accuracy figure
#: from it would have been a measurement of nothing.
DISCRIMINATING = (5, 4, 4)


def positions_at_branching(branching, m=4, n=4, k=4, count=20, seed=0,
                           require_decision=True):
    """Legal, undecided positions whose empty-cell count is `branching`.

    Reached by random legal play rather than by filling cells arbitrarily,
    so every position is one the game can actually be in -- an arbitrary
    fill can place four in a row for a player who never had four turns.

    `require_decision` drops positions where EVERY legal move preserves
    the value. Those cannot distinguish a search from a coin, and on
    4x4 k=4 at branching 12 they were all of them.
    """
    rng = random.Random(seed)
    want = m * n - branching
    out = []
    attempts = 0
    while len(out) < count and attempts < count * 200:
        attempts += 1
        game = MNK(m, n, k)
        while game.turn_number < want and not game.is_game_over():
            turns = game.get_all_legal_turns()
            if not turns:
                break
            game.execute_turn(turns[rng.randrange(len(turns))])
        if game.turn_number != want or game.is_game_over():
            continue
        if len(game.get_all_legal_turns()) < 2:
            continue
        if require_decision:
            best, _value = optimal_moves(game)
            if len(best) >= len(game.get_all_legal_turns()):
                continue
        out.append(game)
    return out


def decision_density(positions):
    """Mean share of legal moves that are optimal, over `positions`.

    REPORTED BESIDE ANY ACCURACY FIGURE. If it is near 1, a search cannot
    be wrong and the accuracy is a property of the benchmark rather than
    of the search.
    """
    ratios = []
    for game in positions:
        legal = game.get_all_legal_turns()
        if not legal:
            continue
        best, _value = optimal_moves(game)
        ratios.append(len(best) / float(len(legal)))
    if not ratios:
        return float('nan')
    return sum(ratios) / len(ratios)
