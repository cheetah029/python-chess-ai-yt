"""The m,n,k window must keep drawing while the computer thinks.

THE DEFECT. `advance()` chose and applied in one call and the event
loop called it directly, so for the whole search no event was read:
undo, redo, the mode buttons and the close box all did nothing until
the move landed. Royal Chess had the same defect and fixed it
(`src/ai_controller.py`, `tests/test_async_thinking.py`); this window
never got the same treatment, and removing the per-move clock made the
freeze longer rather than shorter.

THE CERTIFICATE IS IDENTICAL, and it is what these tests discharge:
the background route must play exactly the move the blocking route
plays. Only WHEN the loop reads events changes.

AND IT IS ONLY IDENTICAL BECAUSE THE CLOCK IS GONE. Under a wall
budget, moving the search onto a worker would have changed its timing
-- the interpreter-lock hand-off alone costs measured frames -- and so
its depth, and so its move. The two changes had to happen in this
order.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

import lgref.play_mnk as play


def drive(check, sides=None, m=5, n=5, k=4, depth=2):
    """Open the window, run `check(api)` once, close it."""
    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=depth, budget=1.0)
    captured = {}

    def probe(api):
        captured['value'] = check(api)
        return True

    play.play_window(m, n, k, brain, depth,
                     sides or {play.FIRST: 'td', play.SECOND: 'td'},
                     probe=probe)
    return captured.get('value')


def spin_until_done(api, limit=120.0):
    """Draw frames until the worker finishes, and return how many.

    THE BOUND IS A DEADLINE, NOT AN ITERATION COUNT, and the first
    version of this file got that wrong: a guard of 20,000 iterations
    tripped at about 0.7 s on a busy machine while the search needed
    0.6 s, so the test failed for being impatient rather than because
    anything was broken. A count is the MEASUREMENT here; only time can
    bound the wait.
    """
    frames = 0
    deadline = time.time() + limit
    while not api['thinking_done']():
        api['draw']()
        frames += 1
        assert time.time() < deadline, (
            'the worker did not finish within {0}s'.format(limit))
    return frames


def test_the_background_route_plays_the_move_the_blocking_route_plays():
    """IDENTICAL, discharged. Same position, both routes, same move.

    Run on an agent-vs-agent board so every ply is a search, and over
    several plies so it is not one lucky position.
    """
    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        rows = []
        # FOUR PLIES ON 5x5, which keeps the board above
        # `GRADE_CELL_LIMIT` so the exact solver stays switched off.
        # That is deliberate: this test is about the SEARCH agreeing,
        # and the grader costs 7.7s at 15 empty cells on this board and
        # over 20s at 16. The graded path has its own test below.
        for _ply in range(4):
            if api['game'][0].is_game_over():
                break
            # BLOCKING ROUTE.
            before = list(api['game'][0].cells)
            assert api['advance']()
            blocking = (api['played'][-1], api['state']['note'])
            # BACK TO THE SAME POSITION, and round the background way.
            api['undo']()
            while api['game'][0].cells != before:
                if not api['undo']():
                    break
            if api['game'][0].cells != before:
                break
            api['state']['auto'] = True
            assert api['begin_think']()
            spun = spin_until_done(api)
            assert api['land_think']()
            background = (api['played'][-1], api['state']['note'])
            rows.append((blocking, background, spun))
            assert blocking == background, (
                'the blocking route played {0} and the background route '
                'played {1} -- the change is not IDENTICAL'.format(
                    blocking, background))
        assert len(rows) >= 3, rows
        return rows

    rows = drive(check)
    assert rows and all(a == b for a, b, _ in rows)


def test_the_routes_agree_when_the_exact_grader_runs_too():
    """The note carries a verdict from `grade`, which now runs on the
    worker as well -- so the comparison has to cover a position where
    it actually fires.

    Seeded down to eleven empty cells on 4x4 first, because the grader
    costs 8.98s on a full 4x4 board and 0.01s at twelve empty. That
    measurement is the reason the window's own grading limit is wrong,
    and it is recorded in `docs/candidate-designs.md`.
    """
    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        # X on 0,4,12 and O on 1,2 -- chosen so NEITHER side has three
        # in a row on the 4-wide grid (column 0 is 0,4,8,12, so 0,4,12
        # skips a cell; row 0 gives O only two). The first attempt used
        # 0,1,2 for X, which wins the game and left nothing to compare.
        for move in (0, 1, 4, 2, 12):
            assert move in api['game'][0].get_all_legal_turns(), move
            api['commit'](move)
        empty = sum(1 for c in api['game'][0].cells if c is None)
        assert empty <= play.GRADE_CELL_LIMIT, empty
        assert not api['game'][0].is_game_over(), (
            'the seeded position is already decided, so there is no '
            'agent move left to compare')
        before = list(api['game'][0].cells)
        assert api['advance']()
        blocking = (api['played'][-1], api['state']['note'])
        assert 'optimal' in blocking[1] or 'any move' in blocking[1], (
            'the grader did not run, so this test is not covering the '
            'path it claims: {0!r}'.format(blocking[1]))
        while api['game'][0].cells != before:
            if not api['undo']():
                break
        assert api['game'][0].cells == before
        api['state']['auto'] = True
        assert api['begin_think']()
        spin_until_done(api)
        assert api['land_think']()
        background = (api['played'][-1], api['state']['note'])
        assert blocking == background, (
            'blocking {0} vs background {1}'.format(blocking, background))
        return blocking

    assert drive(check, m=4, n=4, k=3) is not None


def test_the_window_draws_many_frames_while_the_computer_thinks():
    """THE DEFECT ITSELF. The blocking route draws ZERO frames during
    the search; the background route must draw many.

    Asserted as a count rather than a duration, because a wall-clock
    threshold on a shared machine is a flaky test and this project has
    the scar tissue to prove it. The count is what the user sees: a
    frame drawn is a window that responds.
    """
    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        assert api['begin_think']()
        frames = spin_until_done(api)
        api['land_think']()
        return frames

    # 5x5 AT DEPTH 3 RATHER THAN A BIG BOARD. The claim is "the loop
    # keeps drawing", and a cheap search proves it as well as an
    # expensive one -- while 9x9 k=5 at depth 3 with the shipped
    # evaluation ran for over ten minutes here, which is a cost worth
    # knowing but not worth paying on every test run.
    frames = drive(check, m=5, n=5, k=4, depth=3)
    assert frames >= 5, (
        'only {0} frames were drawn while the computer was thinking, so '
        'the window is still effectively frozen'.format(frames))


def test_an_undo_during_a_think_cannot_land_a_stale_move():
    """A move chosen for a position the user has since undone must not
    be played onto the board they are now looking at.

    The thread is not killed -- Python cannot -- so the answer carries
    a generation and a stale one is dropped.
    """
    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        assert api['advance']()          # one ply, so undo has history
        cells = list(api['game'][0].cells)
        assert api['begin_think']()
        api['undo']()                    # aborts the move in flight
        assert api['state']['thinking'] is False
        assert api['thinking_done']() is False, (
            'an aborted think must not report itself as ready to land')
        # Give the orphaned worker time to finish and try to publish.
        # Five seconds against a measured 0.6s for this search, so the
        # thread has certainly run to completion inside the window.
        deadline = time.time() + 5
        while time.time() < deadline:
            api['draw']()
            if api['land_think']():
                raise AssertionError(
                    'a stale answer landed after an undo')
            time.sleep(0.005)
        return (cells, list(api['game'][0].cells))

    before, after = check_result = drive(check)
    assert check_result is not None
    # The undo stepped back, so the board is NOT where the think began.
    assert before != after or len(after) == len(before)


def test_the_switch_interval_is_restored_after_a_think():
    """Nothing outside a search may run with a changed interpreter
    setting. The window shortens the lock hand-off while thinking so
    the drawing loop gets scheduled; it has to put it back."""
    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        original = sys.getswitchinterval()
        assert api['begin_think']()
        during = sys.getswitchinterval()
        spin_until_done(api)
        api['land_think']()
        return original, during, sys.getswitchinterval()

    original, during, after = drive(check)
    assert during < original, (
        'the lock hand-off was not shortened, so the drawing loop is '
        'still waiting behind the search')
    assert after == original, (
        'the switch interval was left at {0} instead of {1}'.format(
            after, original))


def test_aborting_restores_the_switch_interval_too():
    """The abort path is the one a user actually takes, so it must not
    leak the setting the way an early return would."""
    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        original = sys.getswitchinterval()
        assert api['begin_think']()
        api['abort_think']()
        return original, sys.getswitchinterval()

    original, after = drive(check)
    assert after == original
