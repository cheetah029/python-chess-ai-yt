"""Every distinct version of the player is kept and can be played again.

A reviewer met a version of the player that no commit contains -- most
likely the window was launched while its source was half-way through an
edit -- and there was nothing to go back to. These tests hold the three
things that make that impossible now: the id changes exactly when the
player's sources do, a save keeps the tree AS IT IS (uncommitted edits
included), and a kept version unpacks byte-for-byte.
"""

import os
import shutil
import subprocess  # nosec B404
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

import player_versions  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which('git') is None,
                                reason='needs the git binary')


def _git(root, *args):
    return subprocess.run(  # nosec B603 B607
        ['git', '-C', str(root)] + list(args), check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t',
                 GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t'),
    ).stdout.decode().strip()


def _write(root, path, text):
    full = os.path.join(str(root), path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w') as handle:
        handle.write(text)


@pytest.fixture
def repo(tmp_path):
    """A small repository shaped like this one: a player in `src/` and
    `lgref/`, weights, tests and docs that are not the player."""
    _write(tmp_path, 'src/engine.py', 'RULES = 1\n')
    _write(tmp_path, 'lgref/experiments/search.py', 'DEPTH = 3\n')
    _write(tmp_path, 'lgref/weights/td_royal_chess.json', '{"w": 1}\n')
    _write(tmp_path, 'lgref/tests/test_search.py', 'X = 1\n')
    _write(tmp_path, 'docs/notes.md', 'notes\n')
    _write(tmp_path, '.gitignore', 'data/\n')
    _write(tmp_path, 'data/huge.bin', 'not source\n')
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'add', '-A')
    _git(tmp_path, 'commit', '-q', '-m', 'start')
    return tmp_path


def test_the_id_changes_exactly_when_the_player_does(repo):
    first = player_versions.player_id(str(repo))
    assert player_versions.player_id(str(repo)) == first, 'not stable'

    # Not the player: tests, docs, ignored data.
    _write(repo, 'lgref/tests/test_search.py', 'X = 2\n')
    _write(repo, 'docs/notes.md', 'other notes\n')
    assert player_versions.player_id(str(repo)) == first

    # The player: its code and its weights, each on its own.
    for path, text in (('lgref/experiments/search.py', 'DEPTH = 4\n'),
                       ('src/engine.py', 'RULES = 2\n'),
                       ('lgref/weights/td_royal_chess.json', '{"w": 2}\n')):
        before = player_versions.player_id(str(repo))
        _write(repo, path, text)
        assert player_versions.player_id(str(repo)) != before, (
            'editing {0} did not change the id, so a version that '
            'differs there would never be kept'.format(path))


def test_a_half_finished_edit_is_kept_and_plays_back_exactly(repo, tmp_path):
    """The case that was lost: the tree as it is mid-edit, never
    committed. It must be kept, and come back byte-for-byte."""
    git_dir = os.path.join(str(repo), '.git')
    committed, created = player_versions.save(str(repo), 'committed')
    assert created
    assert player_versions.save(str(repo))[1] is False, (
        'an unchanged player was saved twice')

    _write(repo, 'lgref/experiments/search.py', 'DEPTH = 3  # editing\n')
    _write(repo, 'src/new_module.py', 'NEW = True\n')   # untracked
    editing, created = player_versions.save(str(repo), 'mid-edit')
    assert created and editing != committed

    # Nothing about the checkout moved: same branch, same index, the
    # edit still uncommitted.
    assert 'search.py' in _git(repo, 'status', '--porcelain')

    kept = [v[0] for v in player_versions.versions(git_dir)]
    assert kept == [committed, editing]
    out = player_versions.export(git_dir, editing,
                                 str(tmp_path / 'replay'))
    for path in ('lgref/experiments/search.py', 'src/new_module.py',
                 'lgref/weights/td_royal_chess.json'):
        with open(os.path.join(out, path)) as a, \
                open(os.path.join(str(repo), path)) as b:
            assert a.read() == b.read(), path
    assert not os.path.exists(os.path.join(out, 'data', 'huge.bin')), (
        'ignored data was swept into the version')
    assert player_versions.player_id(out) == editing


def test_a_scratch_export_with_no_repository_is_kept_too(repo, tmp_path,
                                                         monkeypatch):
    """Measurements run from plain exports with no `.git`; those
    versions go into the main repository's store."""
    scratch = tmp_path / 'scratch'
    shutil.copytree(str(repo), str(scratch),
                    ignore=shutil.ignore_patterns('.git'))
    _write(scratch, 'src/engine.py', 'RULES = 3\n')
    monkeypatch.setenv('PLAYER_VERSIONS_GIT_DIR',
                       os.path.join(str(repo), '.git'))
    pid, created = player_versions.save(str(scratch), 'scratch')
    assert created
    assert pid in [v[0] for v in player_versions.versions(
        os.path.join(str(repo), '.git'))]


def test_the_window_names_and_keeps_the_version_it_runs(monkeypatch):
    """The title bar carries the id, so the version a reviewer saw is
    the one that was kept."""
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    import main

    saved = []
    monkeypatch.setattr(player_versions, 'save_quietly',
                        lambda root, note='': saved.append(root))
    pid = main.Main._keep_player_version()
    root = os.path.abspath(os.path.join(HERE, '..'))
    assert pid == player_versions.player_id(root)
    for _ in range(100):
        if saved:
            break
        import time
        time.sleep(0.01)
    assert saved == [root]
