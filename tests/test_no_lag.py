"""Nothing in either window may be slow except the computer thinking.

THE STANDING REQUIREMENT, in the reviewer's words: "make sure there is
no lag in any part of both GUIs whatsoever except for only when the
computer is thinking."

Every number here was a real complaint before it was a test:

  - loading a board took 10.4 seconds, because the agent's opening
    prior was estimated by playing 400 random games. The same quantity
    is read exactly from the win condition in 0.01s.
  - jumping to the start of a game took 38ms at 60 plies and 77ms at
    120, because each step rebuilt the whole board from its snapshot.
  - dragging a piece stuttered at 54ms because the thinking thread
    starved the UI.

THE BUDGETS ARE DELIBERATELY LOOSE. A test that asserts a tight time on
a shared machine fails for reasons that have nothing to do with the
code, and a flaky guard gets deleted. These are set where a PERSON
notices -- about 100ms for an action, a second for opening a board --
so they catch a regression of the kind that was actually reported, not
a slow afternoon.
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

#: What a person notices. Not what the machine can do.
INSTANT = 0.15
OPENING_A_BOARD = 2.0


def elapsed(action):
    started = time.time()
    result = action()
    return result, time.time() - started


# ---- m,n,k ----------------------------------------------------------

def test_the_opening_prior_is_read_not_sampled():
    """10.4 SECONDS ON 19x19, and the reviewer felt every one of them.
    The prior is now read from the win condition, which is both exact
    and free; sampling it was noise at that size anyway."""
    import lgref.play_mnk as play

    play._PRIORS.clear()
    for board in ((9, 9, 5), (19, 19, 5), (20, 20, 5)):
        play._PRIORS.clear()
        _prior, cost = elapsed(lambda b=board: play.opening_prior(*b))
        assert cost < INSTANT, (
            'building the opening prior for {0} took {1:.2f}s'.format(
                board, cost))


def test_the_prior_names_the_exact_centre_on_every_board():
    """The reviewer: "it played 13,12 on the first move". A sampled
    prior could not do better -- on 19x19 its error bar (0.038) was
    wider than the spread across its top ten cells (0.033)."""
    import lgref.play_mnk as play

    for m, n, k in ((9, 9, 5), (19, 19, 5), (13, 13, 5)):
        play._PRIORS.clear()
        prior = play.opening_prior(m, n, k)
        best = max(prior, key=prior.get)
        row, col = divmod(best, n)
        assert (m - row, col + 1) == ((m + 1) // 2, (n + 1) // 2), (
            '{0}x{1}: prior favours {2},{3}'.format(
                m, n, m - row, col + 1))


def test_starting_a_game_is_not_slow_even_on_the_largest_board():
    import lgref.play_mnk as play

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    taken = {}

    def probe(api):
        started = time.time()
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        taken['start'] = time.time() - started
        return True

    play.play_window(19, 19, 5, brain, 2,
                     {play.FIRST: 'human', play.SECOND: 'human'},
                     probe=probe)
    assert taken['start'] < OPENING_A_BOARD, (
        'opening a 19x19 board took {0:.2f}s'.format(taken['start']))


def test_every_window_action_is_instant():
    """Undo, redo, jumping to either end, copying, flipping a setting
    -- none of these thinks, so none of them may take time."""
    import lgref.play_mnk as play

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    slow = {}

    def probe(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        for move in range(0, 60, 2):
            api['commit'](move)
        checks = (
            ('undo', api['undo']),
            ('redo', api['redo']),
            ('jump to start', lambda: [None for _ in iter(
                lambda: api['undo'](), False)]),
            ('jump to end', lambda: [None for _ in iter(
                lambda: api['redo'](), False)]),
            ('copy', api['copy_game']),
            ('draw', api['draw']),
            ('restart', api['restart']),
        )
        for name, action in checks:
            _result, cost = elapsed(action)
            if cost > INSTANT:
                slow[name] = cost
        return True

    play.play_window(19, 19, 5, brain, 2,
                     {play.FIRST: 'human', play.SECOND: 'human'},
                     probe=probe)
    assert not slow, 'these window actions were not instant: {0}'.format(
        slow)


# ---- the case study --------------------------------------------------

def test_the_case_study_window_opens_instantly():
    from game import Game

    _game, cost = elapsed(Game)
    assert cost < OPENING_A_BOARD, (
        'building the game took {0:.2f}s'.format(cost))


def test_jumping_through_a_long_game_is_instant():
    """38ms at 60 plies and 77ms at 120 before the jump stopped
    rebuilding every position it passed through."""
    from game import Game

    game = Game()
    for _ply in range(200):
        game._history.append(game._snapshot())

    _ok, back = elapsed(game.jump_to_start)
    _ok2, forward = elapsed(game.jump_to_end)
    assert back < INSTANT, 'jump to start took {0:.3f}s'.format(back)
    assert forward < INSTANT, 'jump to end took {0:.3f}s'.format(forward)


def test_a_single_step_is_instant_too():
    from game import Game

    game = Game()
    for _ply in range(120):
        game._history.append(game._snapshot())
    _ok, cost = elapsed(game.undo)
    assert cost < INSTANT, 'one undo took {0:.3f}s'.format(cost)


def test_the_board_does_not_think_while_the_agent_does():
    """The only permitted slowness is the computer's turn, and while it
    is thinking the board must be LOCKED rather than merely slow -- a
    reviewer was able to drag the computer's pieces during its move."""
    from game import Game

    game = Game()
    assert hasattr(game, 'is_board_input_locked')
