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
