"""The playable game and the LGREF harness must enumerate the same moves.

Why this matters more than it looks. The project's trust order puts
RULEBOOK_v2.md first and `main.py` — the visually playable, heavily
hand-tested implementation — second. But every LGREF measurement runs
through `GameEngine`, not through `main.py`. If those two ever disagreed,
the study would be measuring a game the owner has never played.

They are not the same code path: `main.py` generates moves for ONE piece
when the player clicks it, while `GameEngine.get_all_legal_turns()`
enumerates every piece. They are two call sites over one shared rule
implementation in `board.py` — the same generators (`king_moves`,
`boulder_moves`, ...) followed by the same two filters
(`filter_repetition_moves`, `filter_endgame_moves`).

Sharing an implementation is not the same as agreeing, because each call
site carries its own guards: `main.py` special-cases the boulder (either
player may move it, except white on turn 1) and skips pieces frozen by
`moved_by_queen`. This test replays main.py's exact per-piece sequence and
asserts the union equals the engine's turn list.

It is a REPLICA, so it can drift from main.py. If main.py's selection logic
changes (around main.py:575-612), update `_main_py_move_set` to match —
a mismatch here means either a real divergence or a stale replica, and
both are worth knowing about.
"""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()
pygame.font.init()

from game import Game
from ai_controller import AIController
from piece import Boulder, King, Queen, Rook, Bishop, Knight, Pawn


class _SeededRandomPlayer:
    """RandomPlayer with an explicit RNG (the stock one uses global random)."""

    def __init__(self, rng):
        self._rng = rng

    def choose_turn(self, turns, engine=None):
        return self._rng.choice(turns) if turns else None


def _main_py_move_set(board, color):
    """Replay main.py's per-piece move generation for every clickable piece.

    Mirrors main.py:575-612 (piece selection) and main.py:545-552 (the
    boulder while it sits on the central intersection).
    """
    moves = set()

    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            piece.clear_moves()

            if isinstance(piece, Boulder):
                # Either player may move the boulder, except white on turn 1.
                if color == 'white' and board.turn_number == 0:
                    continue
                board.boulder_moves(piece, row, col)
            elif piece.color != color:
                continue
            elif getattr(piece, 'moved_by_queen', False):
                # v2 manipulation freeze: no spatial move this turn.
                continue
            elif isinstance(piece, King):
                board.king_moves(piece, row, col)
            elif isinstance(piece, Queen):
                board.queen_moves(piece, row, col)
            elif isinstance(piece, Rook):
                board.rook_moves(piece, row, col)
            elif isinstance(piece, Bishop):
                board.bishop_moves(piece, row, col)
            elif isinstance(piece, Knight):
                board.knight_moves(piece, row, col)
            elif isinstance(piece, Pawn):
                board.pawn_moves(piece, row, col)

            board.filter_repetition_moves(piece, color)
            board.filter_endgame_moves(piece, color)
            for move in piece.moves:
                moves.add((row, col, move.final.row, move.final.col))
            piece.clear_moves()

    # The boulder while still on the central intersection has no square of
    # its own, so it is reached by a separate branch in main.py and keyed
    # here with the engine's (-1, -1) sentinel origin.
    if board.boulder and board.boulder.on_intersection:
        if not (color == 'white' and board.turn_number == 0):
            boulder = board.boulder
            boulder.clear_moves()
            board.boulder_moves(boulder)
            board.filter_repetition_moves(boulder, color)
            board.filter_endgame_moves(boulder, color)
            for move in boulder.moves:
                moves.add((-1, -1, move.final.row, move.final.col))
            boulder.clear_moves()

    return moves


def _engine_move_set(controller, game):
    """Spatial moves from the engine, keyed the same way.

    Only 'move' and 'boulder' turns are comparable: manipulations and
    transformations are actions the UI reaches by other means, and the
    engine enumerates jump/promotion sub-choices as separate Turns that
    collapse to the same (from, to) pair.
    """
    moves = set()
    for turn in controller.legal_turns(game):
        if turn.turn_type not in ('move', 'boulder'):
            continue
        origin = turn.from_sq if turn.from_sq else (-1, -1)
        moves.add((origin[0], origin[1], turn.to_sq[0], turn.to_sq[1]))
    return moves


@pytest.mark.parametrize('trial', range(4))
def test_mainpy_and_engine_agree_over_a_game(trial):
    """Across a seeded game, both paths yield identical spatial-move sets."""
    rng = random.Random(500 + trial)
    game = Game()

    compared = 0
    for _ply in range(25):
        if game.winner is not None:
            break
        controller = AIController(game.next_player,
                                  player=_SeededRandomPlayer(rng))
        engine_moves = _engine_move_set(controller, game)
        main_moves = _main_py_move_set(game.board, game.next_player)
        compared += 1

        assert main_moves == engine_moves, (
            f'trial {trial}, ply {_ply}, mover {game.next_player}: '
            f'the playable path and GameEngine disagree.\n'
            f'  main.py-only: {sorted(main_moves - engine_moves)[:8]}\n'
            f'  engine-only : {sorted(engine_moves - main_moves)[:8]}\n'
            f'Either a real divergence (the study would be measuring a '
            f'different game from the one that is played), or this '
            f'replica has drifted from main.py:575-612.')

        if not controller.take_turn(game):
            break

    assert compared >= 5, f'only {compared} positions compared'


def test_replica_is_not_vacuous():
    """A replica that produced nothing would make the parity test pass
    for the wrong reason."""
    game = Game()
    moves = _main_py_move_set(game.board, 'white')
    assert len(moves) > 20, (
        f'only {len(moves)} moves at the initial position — the replica '
        f'is not generating properly')
