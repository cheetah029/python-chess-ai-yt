"""A tiny solvable game, for testing a search against exact answers.

Issue #206 measured MCTS on Royal Chess to be a uniform sampler: 0%
self-agreement and identical visit counts across all 65 root children.
That leaves a question the measurement could not settle -- is the
IMPLEMENTATION wrong, or is a branching factor of 68 simply too wide for
an affordable budget?

Tic-tac-toe answers it. It is small enough to solve exactly by minimax,
so every position has a known set of optimal moves and a search can be
scored against ground truth rather than against another search. Its
branching factor is at most 9, so an affordable budget covers the root
many times over. If MCTS plays it well, the implementation is sound and
Royal Chess was a budget problem; if it plays it badly, the
implementation is at fault.

The engine interface mirrors the Royal Chess one -- `get_all_legal_turns`,
`execute_turn`, `is_game_over`, `winner`, `current_player` -- so the
same agents play it unmodified.
"""

import copy
import functools

LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8),
         (0, 3, 6), (1, 4, 7), (2, 5, 8),
         (0, 4, 8), (2, 4, 6))


class TicTacToe:
    """Positions are a 9-tuple of 'x', 'o' or None."""

    def __init__(self, cells=None, to_move='x'):
        self.cells = list(cells) if cells else [None] * 9
        self.current_player = to_move
        self.turn_number = sum(1 for c in self.cells if c)
        self.max_turns = 9

    # ---- the engine interface the agents expect ----------------------

    def get_all_legal_turns(self):
        if self.winner is not None:
            return []
        return [i for i, c in enumerate(self.cells) if c is None]

    def execute_turn(self, turn):
        self.cells[turn] = self.current_player
        self.current_player = 'o' if self.current_player == 'x' else 'x'
        self.turn_number += 1

    def is_game_over(self):
        return self.winner is not None or not any(
            c is None for c in self.cells)

    @property
    def winner(self):
        for a, b, c in LINES:
            if self.cells[a] and self.cells[a] == self.cells[b] == \
                    self.cells[c]:
                return self.cells[a]
        return None

    def key(self):
        return (tuple(self.cells), self.current_player)


@functools.lru_cache(maxsize=None)
def _solve(cells, to_move):
    """Exact minimax value, from `to_move`'s perspective: +1/0/-1."""
    game = TicTacToe(cells, to_move)
    if game.winner is not None:
        return 1 if game.winner == to_move else -1
    moves = game.get_all_legal_turns()
    if not moves:
        return 0
    best = -2
    for move in moves:
        child = TicTacToe(cells, to_move)
        child.execute_turn(move)
        best = max(best, -_solve(tuple(child.cells), child.current_player))
    return best


def optimal_moves(game):
    """Every move preserving the position's exact value.

    A set, not a single move: scoring a search against one arbitrary
    optimum would penalise it for a different, equally perfect choice.
    """
    cells, to_move = tuple(game.cells), game.current_player
    value = _solve(cells, to_move)
    best = []
    for move in game.get_all_legal_turns():
        child = TicTacToe(cells, to_move)
        child.execute_turn(move)
        if -_solve(tuple(child.cells), child.current_player) == value:
            best.append(move)
    return set(best), value


def reachable_positions(limit=200, seed=0):
    """Non-terminal positions reachable in real play, de-duplicated."""
    import random

    rng = random.Random(seed)
    seen, out = set(), []
    while len(out) < limit:
        game = TicTacToe()
        while not game.is_game_over():
            key = game.key()
            if key not in seen:
                seen.add(key)
                out.append(TicTacToe(game.cells, game.current_player))
                if len(out) >= limit:
                    break
            moves = game.get_all_legal_turns()
            game.execute_turn(moves[rng.randrange(len(moves))])
    return out
