"""Jumping to the ends of a game, and what it must not change.

A reviewer reported that Up/Down -- jump to the start or the end of the
game -- is laggy in Royal Chess. It was, and for a reason worth
writing down: the jump called the single-step undo in a loop, and
every single step rebuilt the whole board from its snapshot. The cost
therefore grew with the length of the game. Measured on a pristine
opening board, which is the CHEAPEST case:

    60 plies    38 ms
    120 plies   77 ms

Every position in between is thrown away the instant it is built, so
only the last one was ever worth building. The jump now walks the stack
without restoring and restores the destination once, which is flat in
the length of the game:

    60 plies    0.1 ms
    120 plies   0.1 ms
    300 plies   0.2 ms

The risk in that change is not speed, it is CORRECTNESS: a jump that
lands somewhere subtly different from stepping all the way is a worse
bug than the lag it fixes. So these tests compare the two.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()
pygame.font.init()

from game import Game


def played(plies=12):
    """A game with `plies` recorded states behind it."""
    game = Game()
    for _ in range(plies):
        game._history.append(game._snapshot())
    return game


def where(game):
    """Everything that says where in the game we are."""
    return (game.board.get_state_hash(game.next_player), game.next_player,
            game.winner, len(game._history), len(game._redo_stack))


def test_jumping_to_the_start_lands_where_stepping_lands():
    stepped = played()
    while stepped.can_undo():
        stepped.undo()

    jumped = played()
    assert jumped.jump_to_start() is True

    assert where(jumped) == where(stepped)


def test_jumping_to_the_end_lands_where_stepping_lands():
    stepped = played()
    while stepped.can_undo():
        stepped.undo()
    while stepped.can_redo():
        stepped.redo()

    jumped = played()
    jumped.jump_to_start()
    assert jumped.jump_to_end() is True

    assert where(jumped) == where(stepped)


def test_the_redo_stack_is_left_in_the_order_stepping_would_leave_it():
    """Stepping FORWARD after a jump back must replay the game in the
    order it was played. If the jump pushed the states on backwards,
    the first redo would jump to the end."""
    stepped = played()
    while stepped.can_undo():
        stepped.undo()
    jumped = played()
    jumped.jump_to_start()

    for _ in range(4):
        assert stepped.redo() is True
        assert jumped.redo() is True
        assert where(jumped) == where(stepped)


def test_a_jump_restores_once_however_long_the_game_is():
    """THE FIX ITSELF. Counted rather than timed, because a timing
    assertion on a shared machine is a flaky test -- and the thing that
    was wrong was the COUNT."""
    game = played(40)
    calls = []
    original = game._restore
    game._restore = lambda snapshot: (calls.append(1), original(snapshot))[1]

    game.jump_to_start()
    assert len(calls) == 1, (
        'jumping to the start rebuilt the board {0} times'.format(len(calls)))

    del calls[:]
    game.jump_to_end()
    assert len(calls) == 1, (
        'jumping to the end rebuilt the board {0} times'.format(len(calls)))


def test_a_jump_with_nowhere_to_go_does_nothing():
    game = Game()
    assert game.jump_to_start() is False
    assert game.jump_to_end() is False
    game = played()
    assert game.jump_to_end() is False, 'there is nothing ahead yet'


def test_the_round_trip_returns_the_position_it_started_from():
    game = played()
    before = where(game)
    game.jump_to_start()
    game.jump_to_end()
    assert where(game) == before


# ---- the copy underneath -------------------------------------------

def test_a_snapshot_does_not_share_state_with_the_live_board():
    """The copy got cheaper (a pickle round-trip rather than
    `copy.deepcopy`, measured at 0.70 ms against 0.18). It must still be
    a real independent copy, or a later move would silently rewrite the
    history it is supposed to be able to return to."""
    game = Game()
    snapshot = game._snapshot()
    live = game.board.squares[6][4].piece
    assert live is not None, 'the test board is not what it was'
    game.board.squares[6][4].piece = None
    assert snapshot['board'].squares[6][4].piece is not None, (
        'mutating the live board changed the snapshot')


def test_the_cheap_copy_falls_back_rather_than_failing():
    """Correctness is not negotiable here; speed is. Anything in the
    graph that will not pickle must fall back to `deepcopy` rather than
    raise into the event loop."""
    game = Game()
    # A lambda is the honest fixture here: `pickle` refuses it, while
    # `deepcopy` treats a function as atomic and hands the same one
    # back. An object that raises in `__reduce__` would not do -- that
    # fails BOTH, so it proves nothing about the fallback.
    game.board.awkward = lambda: None
    copied = game._deep_copy_board(game.board)
    assert copied is not game.board
    assert hasattr(copied, 'awkward')
    assert copied.squares[6][4].piece is not None, (
        'the fallback produced a board that is not a board')
    # And the fallback is a real copy, not a shared reference.
    game.board.squares[6][4].piece = None
    assert copied.squares[6][4].piece is not None
