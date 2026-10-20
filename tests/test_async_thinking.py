"""The computer must think without freezing the window.

A reviewer reported that flipping the board, changing the theme,
pausing, undo and redo all did nothing until the computer had finished
its move -- worst in computer-vs-computer, where there is nothing to do
but watch.

The cause was structural rather than a slow path: `take_turn` chooses
AND applies in one call, and the UI loop called it directly, so for the
whole search no event was read.

These tests drive the controller rather than the window, because that
is where the fix lives.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()
pygame.font.init()

import pytest

from ai_controller import AIController
from game import Game


@pytest.fixture(autouse=True)
def _pygame_up():
    """Defensive: another test file may have called `pygame.quit()`,
    which tears fonts down for the whole process. Building a `Game`
    needs them."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


class _SlowPlayer(object):
    """Takes a measurable time, like a real search does."""

    def __init__(self, seconds=0.6):
        self.seconds = seconds
        self.calls = 0

    def choose_turn(self, turns, _engine=None):
        self.calls += 1
        time.sleep(self.seconds)
        return turns[0]


def test_starting_a_search_returns_immediately():
    """THE WHOLE POINT. The call that begins thinking must not wait for
    thinking to finish, or the window is frozen for the same seconds it
    was before."""
    game = Game()
    control = AIController('white', _SlowPlayer(0.6))
    began = time.time()
    assert control.start_thinking(game) is True
    elapsed = time.time() - began
    assert elapsed < 0.3, (
        'start_thinking blocked for {0:.2f}s, so the UI loop is still '
        'frozen while the computer thinks'.format(elapsed))
    assert control.is_thinking()
    deadline = time.time() + 10
    while control.poll() is None and time.time() < deadline:
        time.sleep(0.02)
    assert control.poll() is not None


def test_the_board_is_not_touched_while_the_search_runs():
    """The search gets a COPY. A Turn holds a reference to the piece
    that produced it and `Board.move` writes through it, so handing the
    live board to another thread is a data race with the renderer."""
    game = Game()
    control = AIController('white', _SlowPlayer(0.4))
    before = [[square.piece for square in row]
              for row in game.board.squares]
    control.start_thinking(game)
    deadline = time.time() + 10
    while control.poll() is None and time.time() < deadline:
        # The renderer would be reading the board right here.
        after = [[square.piece for square in row]
                 for row in game.board.squares]
        assert after == before, 'the live board changed mid-search'
        time.sleep(0.02)
    assert control.poll() is not None


def test_aborting_discards_a_move_chosen_for_a_stale_position():
    """Pausing must be INSTANT, and undo must not be overwritten by a
    move chosen for the position that was undone."""
    game = Game()
    control = AIController('white', _SlowPlayer(0.5))
    control.start_thinking(game)
    began = time.time()
    control.abort()
    assert time.time() - began < 0.2, 'abort waited for the search'
    assert control.poll() is None
    assert not control.is_thinking()
    # Even after the thread finishes, its answer is not resurrected.
    time.sleep(0.8)
    assert control.poll() is None


def test_a_finished_search_applies_exactly_one_legal_turn():
    game = Game()
    control = AIController('white', _SlowPlayer(0.05))
    turn_number = game.board.turn_number
    control.start_thinking(game)
    deadline = time.time() + 10
    while control.poll() is None and time.time() < deadline:
        time.sleep(0.02)
    assert control.finish_turn(game, control.poll()) is True
    assert game.board.turn_number != turn_number or \
        game.next_player != 'white'


def test_the_description_is_resolved_against_the_live_board():
    """The turn objects the thread saw belong to ITS copy. Applying one
    of those would move a piece that is not on the screen."""
    game = Game()
    control = AIController('white', _SlowPlayer(0.05))
    control.start_thinking(game)
    deadline = time.time() + 10
    while control.poll() is None and time.time() < deadline:
        time.sleep(0.02)
    description = control.poll()
    assert isinstance(description, tuple), description
    assert control.finish_turn(game, description) is True


def test_a_second_start_while_thinking_is_refused():
    """Two searches for one move would both come back, and the loser's
    answer would be applied to a position it never saw."""
    game = Game()
    control = AIController('white', _SlowPlayer(0.4))
    assert control.start_thinking(game) is True
    assert control.start_thinking(game) is False


def test_the_main_loop_no_longer_calls_the_blocking_path():
    """The regression, pinned at the call site: `main.py` must drive the
    computer through start/poll/finish, not through `take_turn`."""
    import inspect

    import main as mainloop

    source = inspect.getsource(mainloop.Main.mainloop)
    assert '_ctrl.take_turn(' not in source, (
        'the mainloop calls take_turn again, which blocks for the whole '
        'search and freezes every key')
    for expected in ('start_thinking', 'poll()', 'finish_turn', 'abort'):
        assert expected in source, expected


def test_pausing_aborts_rather_than_waiting():
    import inspect

    import main as mainloop

    source = inspect.getsource(mainloop.Main.mainloop)
    # The CODE, not the comment four paragraphs above it that mentions
    # the same predicate -- the first version of this test matched the
    # comment and passed for the wrong reason.
    marker = 'if game.is_autoplay_paused():'
    assert marker in source, 'the pause check is gone entirely'
    paused = source[source.index(marker):]
    assert 'abort' in paused[:400], (
        'a paused game does not abort the move in flight, so pausing '
        'still waits for the computer')
