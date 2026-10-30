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

    plain = Brain(rounds=1, games=2, seed=1, use_td_leaf=False, depth=2, train_budget=1.0)
    richer = Brain(rounds=1, games=2, seed=1, use_td_leaf=False, depth=2, train_budget=1.0)
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
    weight files, both payload hashes, the depth, the budget, the
    game count and the first game's number -- games are a function of
    their index, so `games=20` from game 1 and from game 21 are
    different races.
    """
    import subprocess

    done = subprocess.run(
        [sys.executable, 'tools/race_agents.py', '0'],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=600)
    head = done.stdout.decode().splitlines()[0]
    assert head.startswith('RACE'), (
        'the race does not record what it raced: {0!r}'.format(head))
    for term in ('current=', 'rival=', 'depth=', 'games=', 'first='):
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


def test_the_approved_mnk_vocabulary_is_pinned():
    """THE REVIEWER ASKED FOR THIS VERSION TO BE KEPT:

        "the rest of its moves are getting increasingly more dangerous
        and aggressive, making it a great player. I'm proud of this
        version - save it as one I like and any future versions must be
        strictly better than this one."

    m,n,k trains from zero when a board is chosen, so the version IS
    the feature set. Pinning its fingerprint means adding or removing a
    feature fails a test rather than changing the player quietly --
    which is exactly how `Reach:j` got in.
    """
    import hashlib
    import re

    sys.path.insert(0, ROOT)
    from lgref.experiments.features import mnk as mnk_features
    from lgref.experiments.features import with_threshold
    from lgref.experiments.mnk import MNK

    game = MNK(m=13, n=13, k=5)
    for turn in game.get_all_legal_turns()[:2]:
        game.execute_turn(turn)
    names = sorted(set(name for _owner, name
                       in with_threshold(mnk_features)(game)))
    tag = hashlib.sha1('|'.join(names).encode('utf-8')).hexdigest()[:8]

    text = open(APPROVED).read()
    found = re.search(r'fingerprint `([0-9a-f]{8})`', text)
    assert found, 'the record does not pin the m,n,k vocabulary'
    assert tag == found.group(1), (
        'the m,n,k feature set has changed and the approval record has '
        'not.\n  approved: {0}\n  current:  {1}\n  features: {2}\n'
        'A later version ships only by being STRICTLY BETTER than the '
        'approved one -- see the m,n,k section of APPROVED.md.'.format(
            found.group(1), tag, names))


def test_the_record_carries_the_floor_a_later_mnk_version_must_clear():
    """A baseline nobody wrote down is a baseline nobody can be held
    to."""
    text = open(APPROVED).read()
    section = text.split('## m,n,k')[1]
    for phrase in ('tempo', 'strictly better'):
        assert phrase in section.lower(), phrase
    assert '72.9' in section or '73.6' in section, (
        'the measured tempo floor is not recorded')


def test_both_games_are_under_the_strictly_better_rule():
    """THE REVIEWER PUT BOTH OF THEM THERE (2026-10-22):

        "The player is doing very well on both games and is steadily
        improving. Make sure all versions are strictly better than
        this one, otherwise don't ship them until you can make them
        strictly better."

    The second half is the part that is easy to lose: a change that
    cannot be SHOWN strictly better does not ship. "Not yet
    measurable" is a reason to keep measuring.
    """
    text = open(APPROVED).read()
    assert 'BOTH GAMES' in text
    assert 'does not ship' in text.lower()
    # Each game names a floor a later version has to clear.
    for game in ('m,n,k', 'Royal Chess'):
        assert 'floor a later' in text and game in text, game


def test_the_instruments_that_do_not_reach_the_case_study_are_listed():
    """A gate with a hole in it is worse than a gate with a hole
    somebody wrote down. Three instruments do not reach Royal Chess and
    the record says which and why, so nobody reports their absence as a
    pass."""
    text = open(APPROVED).read()
    for name in ('optimal_rate', 'forced_move_rate', 'initiative_rate'):
        assert name in text, (
            '{0} is not accounted for in the case study gate'.format(
                name))


def test_training_never_writes_into_the_repository():
    """A test run once wrote its own tiny builds -- rounds=1, games=2 --
    into `lgref/weights/mnk_cache/` beside the player's real ones. A
    tool globbed the directory, picked one up, and a diagnosis was
    PUBLISHED from an agent nobody plays.

    A session fixture was added to point the TESTS elsewhere. That
    fixed the tests and left every script and every interactive run
    free to do it again -- and one did on 2026-10-25, committing three
    more files. So the repository copy is now read-only on the write
    side, which is the half that caused the damage.

    Checked with `MNK_CACHE_DIR` unset, because that is the case the
    fixture was hiding.
    """
    import os
    import shutil
    import tempfile

    import lgref.play_mnk as play

    repo = os.path.join(os.path.dirname(os.path.abspath(play.__file__)),
                        'weights', 'mnk_cache')
    before = set(os.listdir(repo)) if os.path.isdir(repo) else set()

    previous = os.environ.pop('MNK_CACHE_DIR', None)
    scratch = tempfile.mkdtemp(prefix='mnk-writedir-')
    was_write_dir = play.Brain.WRITE_DIR
    play.Brain.WRITE_DIR = scratch
    try:
        # A board nothing has trained, with parameters nothing ships, so
        # a write is certain if one is going to happen at all.
        brain = play.Brain(rounds=1, games=2, seed=4242,
                           use_td_leaf=False, depth=2, train_budget=1.0)
        brain.evaluation(4, 4, 3)
        after = set(os.listdir(repo)) if os.path.isdir(repo) else set()
        assert after == before, (
            'training wrote into the repository: {0}'.format(
                sorted(after - before)))
        assert os.listdir(scratch), (
            'nothing was written anywhere, so this test proves nothing '
            'about where writes go')
    finally:
        play.Brain.WRITE_DIR = was_write_dir
        if previous is not None:
            os.environ['MNK_CACHE_DIR'] = previous
        shutil.rmtree(scratch, ignore_errors=True)


def test_a_shipped_weight_cache_is_still_read_from_the_repository():
    """Redirecting WRITES must not redirect reads -- the shipped builds
    live in the repository and the player has to find them."""
    import inspect

    import lgref.play_mnk as play

    source = inspect.getsource(play.Brain._load_cached)
    assert '_cache_path' in source, (
        'the loader no longer looks in the repository, so a shipped '
        'build would be retrained from scratch every run')
