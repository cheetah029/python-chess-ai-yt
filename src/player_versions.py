"""Every distinct version of the player, kept so any one can be played again.

A reviewer once met a player that answered `1. Bh1-h3` with `Ne8-f6`
where every committed version answers `Nd8-c6`. The most likely cause
is that the window was launched while the source it runs from was
half-way through an edit -- and that version was never committed, so
there was nothing to go back to. A version somebody liked has to be
recoverable even if it only existed for ten minutes.

So a version is identified by WHAT IT RUNS, not by a commit:

- `player_id(root)` hashes every Python source under `src/` and
  `lgref/` (tests excluded) and the shipped weights. Two trees with the
  same id play identically; a tree that differs in any of those files
  gets a new id. That is a superset of "plays differently" -- an edit
  to a comment also makes a new version -- and the superset is chosen
  on purpose, because the cheap alternatives (hash only the modules
  loaded so far, or probe a few positions) can miss a difference, and
  a missed version is exactly the loss this exists to prevent.

- `save(root)` stores the WHOLE tree as a git commit under
  `refs/players/<id>` if no version with that id exists yet. Committed
  or not, on a branch or in a scratch export, the files as they are
  right now. Git stores each file once, so a new version costs only
  the files that changed.

The window saves itself at launch (`Main.__init__`) and shows its id in
the title bar, so the version a reviewer saw is always the version kept.

    python src/player_versions.py list
    python src/player_versions.py save [--root DIR] [--note TEXT]
    python src/player_versions.py play <id-prefix>

`play` exports the version to a cache directory and runs its own
`src/main.py` there with this interpreter. It is a plain export, not a
git worktree, and it never touches the checkout.
"""

import hashlib
import os
import subprocess  # nosec B404
import sys
import tempfile
import time

REF_PREFIX = 'refs/players/'
WEIGHTS = os.path.join('lgref', 'weights', 'td_royal_chess.json')
#: Where `play` unpacks a version. Outside the repository on purpose:
#: an export inside it would be swept into the next snapshot.
CACHE = os.path.join(os.path.expanduser('~'), '.cache',
                     'royal-chess-players')


def _sources(root):
    """The files that decide how the player plays, as sorted paths
    relative to `root`."""
    found = []
    for top in ('src', 'lgref'):
        for directory, subdirs, files in os.walk(os.path.join(root, top)):
            subdirs[:] = sorted(d for d in subdirs
                                if d not in ('__pycache__', 'tests'))
            for name in files:
                if name.endswith('.py'):
                    found.append(os.path.relpath(
                        os.path.join(directory, name), root))
    if os.path.exists(os.path.join(root, WEIGHTS)):
        found.append(WEIGHTS)
    return sorted(found)


def player_id(root):
    """A 12-character id that changes whenever any source of the player
    does. Path separators are normalised so the id does not depend on
    the platform."""
    digest = hashlib.sha256()
    for path in _sources(root):
        digest.update(path.replace(os.sep, '/').encode())
        digest.update(b'\0')
        with open(os.path.join(root, path), 'rb') as handle:
            digest.update(hashlib.sha256(handle.read()).digest())
    return digest.hexdigest()[:12]


def _git(git_dir, *args, **kwargs):
    env = dict(os.environ)
    env.update(kwargs.pop('env', {}))
    done = subprocess.run(  # nosec B603
        ['git', '--git-dir', git_dir] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        check=True, **kwargs)
    return done.stdout.decode().strip()


def find_git_dir(root):
    """The repository versions are kept in: `PLAYER_VERSIONS_GIT_DIR`
    if set (a scratch export has no `.git` of its own), else the one
    `root` belongs to, else None."""
    explicit = os.environ.get('PLAYER_VERSIONS_GIT_DIR')
    if explicit:
        return explicit
    try:
        found = subprocess.run(  # nosec B603 B607
            ['git', '-C', root, 'rev-parse', '--absolute-git-dir'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return found.stdout.decode().strip() or None


def save(root, note='', git_dir=None):
    """Keep the tree at `root` as a version, unless one with the same id
    is already kept. Returns `(id, created)`."""
    root = os.path.abspath(root)
    git_dir = git_dir or find_git_dir(root)
    if git_dir is None:
        raise RuntimeError('no repository to keep versions in; set '
                           'PLAYER_VERSIONS_GIT_DIR')
    pid = player_id(root)
    ref = REF_PREFIX + pid
    try:
        _git(git_dir, 'rev-parse', '--verify', '--quiet', ref)
        return pid, False
    except subprocess.CalledProcessError:
        pass
    handle, index = tempfile.mkstemp(prefix='player-index-')
    os.close(handle)
    os.unlink(index)
    env = {'GIT_INDEX_FILE': index,
           'GIT_AUTHOR_NAME': 'player-versions',
           'GIT_AUTHOR_EMAIL': 'player-versions@localhost',
           'GIT_COMMITTER_NAME': 'player-versions',
           'GIT_COMMITTER_EMAIL': 'player-versions@localhost'}
    try:
        # The tree's own `.gitignore` decides what is source, exactly as
        # it does for a commit, so caches and data stay out.
        _git(git_dir, '--work-tree', root, 'add', '-A', '.', env=env,
             cwd=root)
        tree = _git(git_dir, 'write-tree', env=env)
    finally:
        if os.path.exists(index):
            os.unlink(index)
    try:
        head = subprocess.run(  # nosec B603 B607
            ['git', '-C', root, 'rev-parse', 'HEAD'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True).stdout.decode().strip()
    except (OSError, subprocess.CalledProcessError):
        head = ''
    # The SUBJECT is what `list` shows, so it carries the note.
    message = ('player {0}: {1}\n\nsaved {2}\nfrom {3}\nbased on {4}\n'
               .format(pid, note or os.path.basename(root),
                       time.strftime('%Y-%m-%d %H:%M:%S'), root,
                       head or 'an export with no commit of its own'))
    commit = _git(git_dir, 'commit-tree', tree, '-m', message, env=env)
    # The empty old value makes this a create-only update: two saves of
    # the same id racing each other cannot overwrite one another.
    _git(git_dir, 'update-ref', ref, commit, '')
    return pid, True


def versions(git_dir):
    """`(id, date, subject)` for every kept version, oldest first."""
    listed = _git(git_dir, 'for-each-ref', '--sort=committerdate',
                  '--format=%(refname)\t%(committerdate:iso)\t'
                  '%(contents:subject)', REF_PREFIX)
    found = []
    for line in listed.splitlines():
        parts = line.split('\t')
        if len(parts) < 2 or not parts[0].startswith(REF_PREFIX):
            continue
        found.append((parts[0][len(REF_PREFIX):], parts[1],
                      parts[2] if len(parts) > 2 else ''))
    return found


def resolve(git_dir, prefix):
    matches = [v[0] for v in versions(git_dir) if v[0].startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit('{0} versions match {1!r}'.format(len(matches),
                                                           prefix))
    return matches[0]


def export(git_dir, pid, destination=None):
    """Unpack a kept version into its own directory and return it."""
    destination = destination or os.path.join(CACHE, pid)
    if not os.path.isdir(os.path.join(destination, 'src')):
        os.makedirs(destination, exist_ok=True)
        archive = subprocess.run(  # nosec B603 B607
            ['git', '--git-dir', git_dir, 'archive', REF_PREFIX + pid],
            stdout=subprocess.PIPE, check=True).stdout
        subprocess.run(['tar', '-x', '-C', destination],  # nosec B603 B607
                       input=archive, check=True)
    return destination


def save_quietly(root, note=''):
    """For the window: never let keeping a version stop the game."""
    try:
        return save(root, note)
    except Exception:  # nosec B110
        return None


def main(argv):
    import argparse

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    commands = parser.add_subparsers(dest='command', required=True)
    saving = commands.add_parser('save')
    saving.add_argument('--root', default=here)
    saving.add_argument('--note', default='')
    commands.add_parser('list')
    commands.add_parser('id').add_argument('--root', default=here)
    playing = commands.add_parser('play')
    playing.add_argument('version')
    args, rest = parser.parse_known_args(argv)
    if args.command == 'id':
        print(player_id(args.root))
        return 0
    git_dir = find_git_dir(getattr(args, 'root', here))
    if git_dir is None:
        raise SystemExit('no repository; set PLAYER_VERSIONS_GIT_DIR')
    if args.command == 'save':
        pid, created = save(args.root, args.note, git_dir)
        print('{0} {1}'.format(pid, 'saved' if created else 'already kept'))
    elif args.command == 'list':
        for pid, date, note in versions(git_dir):
            print('{0}  {1}  {2}'.format(pid, date, note))
    elif args.command == 'play':
        pid = resolve(git_dir, args.version)
        where = export(git_dir, pid)
        print('playing version {0} from {1}'.format(pid, where), flush=True)
        return subprocess.call(  # nosec B603
            [sys.executable, os.path.join('src', 'main.py')] + rest,
            cwd=where)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
