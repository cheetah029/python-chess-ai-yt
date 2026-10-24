"""What the playable programs must always do.

Two things a reviewer has had to report more than once:

  (a) the program must RUN -- `play_mnk.py` once crashed on startup
      because an option was declared twice;
  (b) user-facing behaviour must not change unless it was asked for --
      the board became draggable during the computer's turn because a
      change to WHERE the search runs removed an invariant nobody had
      written down.

These tests are the contract. They are deliberately coarse and about
behaviour a person would notice, not about internals.
"""

import os
import subprocess
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def _pygame_up():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


# ---- (b) the human can still play on their own turn -----------------

def test_the_human_can_touch_the_board_on_their_own_turn():
    """THE POSITIVE CONTROL for the input lock. A guard that blocks the
    computer's turn is worthless if it also blocks the human's -- and
    that failure would look exactly like 'the game stopped responding'.
    """
    from ai_controller import AIController
    from game import Game

    game = Game()
    player = game._make_ai_player('td')
    if player is None:
        pytest.skip('no TD agent in this build')
    # The AI has BLACK; white (the human) is to move at the start.
    game.ai_controllers['black'] = AIController('black', player)
    assert game.is_board_input_locked() is False, (
        'the board is locked on the human turn, so the game looks frozen')


def test_the_lock_follows_whose_turn_it_is():
    from ai_controller import AIController
    from game import Game

    game = Game()
    player = game._make_ai_player('td')
    if player is None:
        pytest.skip('no TD agent in this build')
    game.ai_controllers['white'] = AIController('white', player)
    assert game.is_board_input_locked() is True
    game.next_turn()                      # now black, a human
    assert game.is_board_input_locked() is False


def test_computer_versus_computer_locks_the_board_for_both_sides():
    from ai_controller import AIController
    from game import Game

    game = Game()
    player = game._make_ai_player('td')
    if player is None:
        pytest.skip('no TD agent in this build')
    game.ai_controllers['white'] = AIController('white', player)
    game.ai_controllers['black'] = AIController('black', player)
    assert game.is_board_input_locked() is True
    game.next_turn()
    assert game.is_board_input_locked() is True


# ---- (a) and start-up cost ------------------------------------------

def test_starting_an_mnk_game_is_fast_once_the_weights_exist():
    """Only THINKING should cost visible time. Training ran on every
    Start -- twenty seconds before a board appeared -- for weights that
    are identical every run."""
    from lgref.play_mnk import Brain

    brain = Brain(rounds=2, games=4, seed=17, use_td_leaf=False,
                  depth=2, budget=2.0)
    brain.evaluation(5, 5, 4)             # pays for it once
    again = Brain(rounds=2, games=4, seed=17, use_td_leaf=False,
                  depth=2, budget=2.0)
    began = time.time()
    again.evaluation(5, 5, 4)
    elapsed = time.time() - began
    assert elapsed < 2.0, (
        'a second Start on the same board took {0:.1f}s; it should be '
        'reading cached weights'.format(elapsed))


def test_a_corrupt_cache_costs_time_and_never_correctness():
    """A half-read cache must mean training again, not playing on
    whatever parsed."""
    from lgref.play_mnk import Brain

    brain = Brain(rounds=1, games=2, seed=99, use_td_leaf=False,
                  depth=2, budget=1.0)
    path = brain._cache_path((6, 6, 3))
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'w') as handle:
        handle.write('{ this is not json')
    try:
        assert brain._load_cached((6, 6, 3)) is None
        evaluate = brain.evaluation(6, 6, 3)
        assert callable(evaluate)
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.parametrize('relative', [
    os.path.join('lgref', 'play_mnk.py'),
    os.path.join('src', 'main.py'),
])
def test_a_playable_program_still_starts(relative):
    """(a), the coarsest possible check and the one that has failed."""
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, relative), '--help'],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=180)
    assert result.returncode == 0, result.stdout.decode('utf-8', 'replace')


def test_the_mnk_window_opens_and_closes_without_touching_pygame_state():
    """Opening the window must not leave the process unable to build
    another one -- `pygame.quit()` from a test seam did exactly that,
    and broke unrelated files four directories away."""
    import lgref.play_mnk as play

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    play.play_window(4, 4, 3, brain, 2,
                     {play.FIRST: 'human', play.SECOND: 'td'},
                     probe=lambda _api: True)
    assert pygame.get_init(), 'the window shut pygame down behind us'
    assert pygame.font.get_init()
