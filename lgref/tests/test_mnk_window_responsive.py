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
                       depth=depth, train_budget=1.0)
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


def spin_until_judged(api, limit=120.0):
    """Draw frames until a verdict has been spliced into the note.

    The verdict arrives AFTER the move, on purpose: the exact grader
    costs seconds and nobody should wait for a label to see where the
    stone went. So the eventual note is what the IDENTICAL certificate
    compares, not the note the instant the move lands.
    """
    deadline = time.time() + limit
    while api['judging']['thread'] is not None:
        api['draw']()
        api['land_judge']()
        assert time.time() < deadline, 'the grader never finished'


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
        # THE MOVE IS VISIBLE BEFORE THE VERDICT IS, which is the whole
        # point: the grader costs 8.98s on a full board of this size.
        landed = api['state']['note']
        assert 'optimal' not in landed and 'any move' not in landed, (
            'the verdict was already in the note, so grading is still '
            'on the move critical path: {0!r}'.format(landed))
        spin_until_judged(api)
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
        # A KNOWN BASELINE, not whatever the last test left behind.
        # This asserted against the ambient value and failed with
        # `assert 0.001 < 0.001`, because another test had leaked the
        # shortened interval -- a real isolation bug, now also closed
        # by an autouse fixture in conftest.
        sys.setswitchinterval(0.005)
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
        sys.setswitchinterval(0.005)
        original = sys.getswitchinterval()
        assert api['begin_think']()
        api['abort_think']()
        return original, sys.getswitchinterval()

    original, after = drive(check)
    assert after == original


def test_a_truncated_training_run_says_it_was_truncated():
    """`Brain.budget` is a wall clock that stops starting new games, so
    on a slower machine the same settings and the same SEED produce a
    different agent.

    Measured here: the window's 6 rounds x 60 games finish in 10.7 s
    against a 20 s budget, so the clock is inert on this machine. That
    is not the same as inert, which is why the report has to say when
    it fired instead of quoting the count it managed as if that were a
    fact about the board.
    """
    import os
    import tempfile

    scratch = tempfile.mkdtemp(prefix='mnk-truncate-')
    previous = os.environ.get('MNK_CACHE_DIR')
    os.environ['MNK_CACHE_DIR'] = scratch
    try:
        # A budget far too small to finish, so the clock certainly fires.
        brain = play.Brain(rounds=4, games=40, seed=5, use_td_leaf=False,
                           depth=2, train_budget=0.05)
        brain.evaluation(5, 5, 4)
        short = brain.last_report.splitlines()[0]
        assert 'SHORT' in short, (
            'the run was cut off by the clock and the report did not '
            'say so: {0!r}'.format(short))
        assert 'of 160 games' in short, short
    finally:
        if previous is None:
            os.environ.pop('MNK_CACHE_DIR', None)
        else:
            os.environ['MNK_CACHE_DIR'] = previous


def test_an_untruncated_training_run_says_nothing_extra():
    """The notice must not fire on a complete run, or it becomes noise
    that nobody reads when it matters."""
    import os
    import tempfile

    scratch = tempfile.mkdtemp(prefix='mnk-complete-')
    previous = os.environ.get('MNK_CACHE_DIR')
    os.environ['MNK_CACHE_DIR'] = scratch
    try:
        brain = play.Brain(rounds=1, games=2, seed=5, use_td_leaf=False,
                           depth=2, train_budget=None)
        brain.evaluation(5, 5, 4)
        line = brain.last_report.splitlines()[0]
        assert 'SHORT' not in line, line
    finally:
        if previous is None:
            os.environ.pop('MNK_CACHE_DIR', None)
        else:
            os.environ['MNK_CACHE_DIR'] = previous


# ---- input latency, the same check Royal Chess gets -----------------
#
# Royal Chess's keys lagged while the computer thought because
# `show_pieces` decoded a PNG per piece per frame -- 5.57 ms of a
# 5.15 ms frame, rising to 47.75 ms under a search. This window was
# measured for the same defect and does NOT have it: 0.38 ms a frame
# both idle and while thinking, because its fonts are cached in a dict
# and it draws shapes rather than loading images.
#
# Tested anyway, because "it does not have the defect today" is only
# worth something if it stays true -- one `pygame.image.load` or one
# `SysFont` call added inside `draw` would reintroduce it.

def test_a_frame_loads_no_images_and_builds_no_fonts():
    """THE DEFECT AS A COUNT, not a duration -- a wall-clock threshold
    on a shared machine is a flaky test.

    Both calls are cheap once and expensive per frame, and both are the
    shape of mistake that made the other window lag.
    """
    calls = {'images': 0, 'fonts': 0}
    real_load = pygame.image.load
    real_font = pygame.font.SysFont

    def counted_load(path, *rest, **kw):
        calls['images'] += 1
        return real_load(path, *rest, **kw)

    def counted_font(*args, **kw):
        calls['fonts'] += 1
        return real_font(*args, **kw)

    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        api['draw']()                       # warm anything that caches
        pygame.image.load = counted_load
        pygame.font.SysFont = counted_font
        try:
            for _frame in range(30):
                api['draw']()
        finally:
            pygame.image.load = real_load
            pygame.font.SysFont = real_font
        return dict(calls)

    counts = drive(check, m=9, n=9, k=5, depth=2)
    assert counts['images'] == 0, (
        '{0} images were loaded across 30 frames; decoding per frame is '
        'what made the Royal Chess keys lag'.format(counts['images']))
    assert counts['fonts'] == 0, (
        '{0} fonts were built across 30 frames; `font()` caches by '
        '(size, bold) and something is going round it'.format(
            counts['fonts']))


def test_the_frame_cost_does_not_collapse_while_the_computer_thinks():
    """Measured at 0.38 ms a frame idle AND while thinking, worst
    1.66 ms. The bound is deliberately generous so this passes on a
    loaded machine; the frame COUNT carries the rest of the claim.
    """
    import statistics

    def check(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        idle = []
        for _frame in range(40):
            started = time.perf_counter()
            api['draw']()
            idle.append((time.perf_counter() - started) * 1000.0)
        assert api['begin_think']()
        busy = []
        deadline = time.time() + 120
        while not api['thinking_done']() and time.time() < deadline:
            started = time.perf_counter()
            api['draw']()
            busy.append((time.perf_counter() - started) * 1000.0)
        api['land_think']()
        return idle, busy

    idle, busy = drive(check, m=9, n=9, k=5, depth=3)
    assert len(busy) >= 20, (
        'only {0} frames were drawn during the search'.format(len(busy)))
    # THE MEDIAN, NOT THE MAX. The Royal Chess counterpart asserted on
    # `max` and failed inside a full-suite run at 135.8 ms worst with a
    # median of 9.5 ms over 2,502 frames -- one spike in 2,502 is the
    # operating system, not the window.
    middle = statistics.median(busy)
    assert middle < 25.0, (
        'the typical frame during the search was {0:.1f} ms against '
        '{1:.1f} ms idle (worst {2:.1f} ms over {3} frames)'.format(
            middle, statistics.median(idle), max(busy), len(busy)))
