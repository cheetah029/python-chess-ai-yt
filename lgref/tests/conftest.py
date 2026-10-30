"""Test runs must not write into the repository.

A test run wrote its own tiny weight builds -- rounds=1, games=2 --
into `lgref/weights/mnk_cache/` beside the player's real ones. A tool
that globbed the directory then picked one up, and a diagnosis was
published from an agent nobody plays. The repository is for shipped
artefacts; a scratch directory is for scratch.
"""

import os
import tempfile

import pytest


@pytest.fixture(autouse=True, scope='session')
def _cache_somewhere_else():
    scratch = tempfile.mkdtemp(prefix='mnk-cache-')
    previous = os.environ.get('MNK_CACHE_DIR')
    os.environ['MNK_CACHE_DIR'] = scratch
    try:
        import lgref.play_mnk as play
        play.Brain.CACHE_DIR = scratch
    except Exception:
        pass
    yield scratch
    if previous is None:
        os.environ.pop('MNK_CACHE_DIR', None)
    else:
        os.environ['MNK_CACHE_DIR'] = previous


@pytest.fixture(autouse=True)
def _no_test_leaks_the_switch_interval():
    """The interpreter-lock hand-off is process-wide state.

    Both windows shorten it to 1 ms while the computer thinks, so the
    drawing loop gets scheduled, and both restore it when the move
    lands or is aborted. A test that starts a think and then abandons
    the window leaks the shortened value into every test that follows
    -- which is how `test_the_switch_interval_is_restored_after_a_think`
    came to fail with `assert 0.001 < 0.001`: it was asserting against
    an ambient value another test had left behind.

    Restored per test, so one test's leak cannot become another's
    failure, and so nothing outside a search runs with a changed
    interpreter setting.
    """
    import sys as _sys

    previous = _sys.getswitchinterval()
    yield previous
    if _sys.getswitchinterval() != previous:
        _sys.setswitchinterval(previous)
