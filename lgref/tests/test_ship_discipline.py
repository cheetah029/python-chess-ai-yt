"""What must be true before a change to the agent ships.

A REVIEWER'S WARNING, written down because it has already cost a
working agent: *winning a race does not mean the player is strictly
better*. A race reports an AGGREGATE over positions. A change can win
overall while being much worse at a particular kind of position, and
the aggregate hides it.

That is not hypothetical here. `Reach:j` fixed the m,n,k opening -- on
19x19 k=5 the plain line count saturates at 20 and ties across 121
cells, so no line-counting feature can tell the centre from a quadrant
-- and a reviewer who played with it found the MIDGAME worse, tempo
spent on moves that neither attacked nor defended. Both are true. An
aggregate would have reported one number.

So the gate is not one number. These tests pin the parts of that which
can be checked mechanically; the rest is judgement and belongs in the
handoff.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
APPROVED = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'APPROVED.md')


def test_there_is_a_record_of_what_the_reviewer_has_approved():
    """A version nobody wrote down is a version nobody can go back to.
    The file names the CURRENT approved build and everything it
    supersedes, so 'revert to what worked' is a lookup rather than an
    archaeology exercise."""
    assert os.path.exists(APPROVED), (
        'no record of which build the reviewer approved')
    text = open(APPROVED).read()
    assert 'CURRENT' in text, 'the record does not name a current build'
    assert 'sha' in text.lower(), (
        'the record does not pin the approved weights by hash, so it '
        'cannot be checked')


def test_the_shipped_weights_are_the_approved_ones():
    """THE CHECK THAT WOULD HAVE CAUGHT THE REGRESSION. A build ships
    only when the record says so; anything else is a candidate."""
    import hashlib
    import re

    text = open(APPROVED).read()
    # Tolerant of the markdown around it: the record is for a human to
    # read, so the matcher bends, not the document.
    found = re.search(r'CURRENT.*?sha\W{0,8}([0-9a-f]{8,})', text,
                      re.S | re.I)
    assert found, 'the record does not give the current build a hash'
    wanted = found.group(1)
    shipped = hashlib.sha256(
        open(os.path.join(os.path.dirname(__file__), '..', 'weights',
                          'td_royal_chess.json'), 'rb').read()).hexdigest()
    assert shipped.startswith(wanted), (
        'the shipped weights are not the approved build.\n'
        '  approved: {0}\n  shipped:  {1}\n'
        'Either ship the approved build or update the record -- but a '
        'race win alone is not grounds for updating it.'.format(
            wanted, shipped[:len(wanted)]))


def test_a_feature_that_helps_one_phase_can_be_switched_off():
    """`Reach:j` is kept and OFF rather than deleted, because the
    problem it solved is real and the problem it caused is also real.
    A feature that can only be all-or-nothing cannot be raced per
    position type."""
    import inspect

    from lgref.experiments.features import mnk

    signature = inspect.signature(mnk)
    assert 'use_reach' in signature.parameters, (
        'the feature is no longer switchable, so the opening fix and '
        'the midgame regression cannot be separated')
    assert signature.parameters['use_reach'].default is False


def test_weight_caches_are_keyed_on_the_vocabulary_not_just_the_board():
    """Weights mean nothing apart from the feature set they were fitted
    on. The m,n,k cache was keyed on the board alone, and the feature
    set changed under it twice in one session -- a cache hit would have
    handed the new extractor the old one's weights with nothing saying
    so."""
    from lgref.play_mnk import Brain

    plain = Brain(rounds=1, games=2, seed=1, use_td_leaf=False, depth=2,
                  budget=1.0)
    richer = Brain(rounds=1, games=2, seed=1, use_td_leaf=False, depth=2,
                   budget=1.0)
    richer.extractor = lambda game: dict(
        list(plain.extractor(game).items())
        + [(('x', 'Invented'), 1)])
    assert plain._cache_path((6, 6, 3)) != richer._cache_path((6, 6, 3)), (
        'two different feature sets share a cache file')


def test_every_shipped_build_remains_restorable():
    """The archive is the thing that makes a revert cheap, and a cheap
    revert is what makes it safe to say no to a change."""
    import glob

    archive = os.path.join(os.path.dirname(__file__), '..', 'weights',
                           'archive')
    assert glob.glob(os.path.join(archive, '*.json'))
    assert os.path.exists(os.path.join(archive, 'INDEX.md'))
    assert os.path.exists(os.path.join(archive, 'candidates',
                                       'README.md'))


def test_a_race_states_its_own_terms():
    """A 12-game log in this session read `current 2 - 8 legacy` at
    depth 3 and nothing in it said which rival those eight losses were
    against -- the environment variable that chose the rival went away
    with the shell. Eight losses that cannot be attributed are not a
    result, and the run had to be discarded.

    So the harness prints its terms before the first game: both
    weight files, both payload hashes, the depth, the budget and the
    game count.
    """
    import subprocess

    done = subprocess.run(
        [sys.executable, 'tools/race_agents.py', '0'],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=600)
    head = done.stdout.decode().splitlines()[0]
    assert head.startswith('RACE'), (
        'the race does not record what it raced: {0!r}'.format(head))
    for term in ('current=', 'rival=', 'depth=', 'games='):
        assert term in head, 'the header omits {0}'.format(term)
    import re
    assert re.search(r'\(([0-9a-f]{8})\)', head), (
        'the header names the weight files but does not pin their '
        'contents, so two different builds at one path log the same')


def test_the_race_runs_at_the_depth_the_window_plays():
    """THE EXACT HOLE THAT SHIPPED A WORSE AGENT: raced at depth 2,
    played at depth 3. Kept here as well as in the entry-point tests
    because this is the file someone reads before shipping."""
    import re

    sys.path.insert(0, os.path.join(ROOT, 'src'))
    from game import Game

    source = open(os.path.join(ROOT, 'tools', 'race_agents.py')).read()
    default = re.search(r"RACE_DEPTH',\s*'(\d+)'", source)
    assert default, 'the race no longer has a default depth'
    assert int(default.group(1)) == Game.TD_DEPTH, (
        'the race defaults to depth {0} but the window plays at depth '
        '{1}'.format(default.group(1), Game.TD_DEPTH))


def test_the_approval_record_and_the_archive_agree():
    """A record that drifts from the archive is worse than none: it
    names a build to go back to that is not the one on disk."""
    import hashlib
    import re

    text = open(APPROVED).read()
    found = re.search(r'archived as.*?`([^`]+)`', text, re.I)
    assert found, 'the record does not say where the approved build is kept'
    kept = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        found.group(1))
    assert os.path.exists(kept), (
        'the record points at {0}, which is not in the '
        'archive'.format(found.group(1)))
    wanted = re.search(r'CURRENT.*?sha\W{0,8}([0-9a-f]{8,})', text,
                       re.S | re.I).group(1)
    digest = hashlib.sha256(open(kept, 'rb').read()).hexdigest()
    assert digest.startswith(wanted), (
        'the archived copy of the approved build does not match the '
        'hash the record gives it')


def test_the_archive_index_says_which_build_is_approved():
    """Somebody reading the archive should not have to open a second
    file to find out which of twelve files is the live one."""
    index = open(os.path.join(os.path.dirname(__file__), '..', 'weights',
                              'archive', 'INDEX.md')).read()
    assert 'APPROVED.md' in index
    assert 'OUTDATED' in index.upper()
