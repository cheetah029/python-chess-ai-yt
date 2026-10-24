"""Every runnable module must still be runnable.

WHY THIS FILE EXISTS. `lgref/play_mnk.py` declared `--budget` twice, so
argparse refused the duplicate and the module died before it drew
anything:

    argparse.ArgumentError: argument --budget: conflicting option
    string: --budget

There were already 22 tests on that file. Every one of them reached
inside and called a function; NOT ONE went through the front door the
user actually uses. So the agent was tested, the training was tested,
the drawing was tested, the steppers were tested -- and the program
could not start.

The two flags were also not the same quantity. One is seconds of
TRAINING, spent once when Start is pressed; the other is seconds per
MOVE, spent on every move. Merging them would have been a real bug
even if argparse had accepted it, which is why the fix renames one
rather than deleting it.

THE SHAPE OF THE GUARD, since "add a test for this bug" would not have
been enough:

  - a STATIC check over every runnable module in the repository, so a
    duplicate option is caught wherever it appears and without running
    anything;
  - a SUBPROCESS check on the playable entry points, which exercises
    the import graph and the parser exactly as a shell invocation does;
  - a HEADLESS GAME for each playable game, so "it starts" is not
    confused with "it plays".
"""

import ast
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Directories that are not this repository's source: the virtualenv,
#: the agent's own scratch space, and the leftover git worktrees (a
#: standing instruction says to ignore those, and they hold stale copies
#: of these very files).
SKIP_PARTS = ('.venv', '.git', '.claude', 'scratchpad', 'node_modules',
              'snapshots', '__pycache__')

#: The entry points a person actually types. These get the expensive
#: checks. `--help` is safe on all of them: argparse exits before any
#: window opens or any training starts.
PLAYABLE = (
    os.path.join('lgref', 'play_mnk.py'),
    os.path.join('src', 'main.py'),
    os.path.join('src', 'main_v0.py'),
    os.path.join('src', 'main_v1.py'),
)


def _runnable_modules():
    """Every module in the repository with a `__main__` guard."""
    found = []
    for folder, children, files in os.walk(ROOT):
        children[:] = [child for child in children
                       if child not in SKIP_PARTS
                       and not child.startswith('.')]
        for name in sorted(files):
            if not name.endswith('.py'):
                continue
            path = os.path.join(folder, name)
            relative = os.path.relpath(path, ROOT)
            if any(part in SKIP_PARTS for part in relative.split(os.sep)):
                continue
            with open(path) as handle:
                text = handle.read()
            if '__main__' in text and 'if __name__' in text:
                found.append(relative)
    return found


RUNNABLE = _runnable_modules()


def test_the_repository_has_runnable_modules_to_check():
    """A discovery bug would make every test below vacuously pass."""
    assert len(RUNNABLE) > 10, RUNNABLE
    for expected in PLAYABLE:
        assert expected in RUNNABLE, (
            '{0} is not being discovered, so nothing below checks '
            'it'.format(expected))


def _option_strings(tree):
    """Every `add_argument('--flag', ...)` option string, by function.

    Grouped by the enclosing function so two parsers in two functions do
    not look like a conflict, which is the only false positive this
    check can produce.
    """
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.Module)):
            continue
        where = getattr(node, 'name', '<module>')
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            func = inner.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in ('add_argument', 'add_option'):
                continue
            for argument in inner.args:
                value = getattr(argument, 'value',
                                getattr(argument, 's', None))
                if isinstance(value, str) and value.startswith('-'):
                    out.setdefault(where, []).append(value)
    return out


@pytest.mark.parametrize('relative', RUNNABLE)
def test_no_module_declares_the_same_command_line_option_twice(relative):
    """THE BUG, asked statically of the whole repository.

    argparse raises at parser-construction time, which is the first
    thing `main` does -- so a duplicate makes the program unrunnable
    rather than merely wrong, and it cannot be caught by any test that
    calls a function inside the module.
    """
    with open(os.path.join(ROOT, relative)) as handle:
        tree = ast.parse(handle.read(), filename=relative)
    for where, options in _option_strings(tree).items():
        seen = {}
        for option in options:
            assert option not in seen, (
                '{0}: {1}() declares {2} twice. argparse raises '
                'ArgumentError on the duplicate, so the module cannot '
                'start. If the two uses are different quantities, give '
                'them different names.'.format(relative, where, option))
            seen[option] = True


@pytest.mark.parametrize('relative', RUNNABLE)
def test_every_runnable_module_parses_as_python(relative):
    """A syntax error in a module nothing imports is invisible until
    someone runs it."""
    with open(os.path.join(ROOT, relative)) as handle:
        source = handle.read()
    compile(source, relative, 'exec')


def _uses_argparse(relative):
    with open(os.path.join(ROOT, relative)) as handle:
        return 'argparse' in handle.read()


WITH_A_CLI = [name for name in PLAYABLE if _uses_argparse(name)]
WITHOUT_A_CLI = [name for name in PLAYABLE if not _uses_argparse(name)]


def test_the_two_kinds_of_entry_point_are_both_represented():
    """A split that stops being a split would silently skip one group.

    `main_v0.py` and `main_v1.py` are FROZEN snapshots with no argument
    parser at all -- they build `Main()` and run the loop -- so asking
    them for `--help` starts a game and hangs, which is what the first
    version of this file did for 180 seconds apiece. Each kind needs
    its own check, not a shared assumption.
    """
    assert WITH_A_CLI and WITHOUT_A_CLI, (WITH_A_CLI, WITHOUT_A_CLI)


@pytest.mark.parametrize('relative', WITH_A_CLI)
def test_every_playable_entry_point_answers_help(relative):
    """THE FRONT DOOR, exercised the way a shell does.

    This is the check that was missing when `play_mnk.py` declared
    `--budget` twice. It runs the real interpreter on the real file, so
    it catches an import error, a missing module, a duplicate option and
    a parser built at import time -- none of which a test that imports a
    function and calls it will see.

    `--help` makes argparse print and exit 0 before any window opens or
    any training starts, so this is fast and has no side effects.
    """
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, relative), '--help'],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=180)
    assert result.returncode == 0, (
        '{0} --help exited {1}:\n{2}'.format(
            relative, result.returncode,
            result.stdout.decode('utf-8', 'replace')[-3000:]))
    assert b'usage' in result.stdout.lower()


@pytest.mark.parametrize('relative', WITHOUT_A_CLI)
def test_an_entry_point_with_no_cli_still_starts(relative):
    """A frozen snapshot has no `--help`, so "does it start" is the
    question -- and it is the one that matters.

    Started headless and given a few seconds. A startup failure (an
    import error, a missing asset, a renamed constant) exits non-zero
    almost immediately; a working mainloop is still running when the
    time is up, and that is the pass. Nothing is clicked and no state is
    saved.
    """
    environment = dict(os.environ)
    environment.setdefault('SDL_VIDEODRIVER', 'dummy')
    environment.setdefault('SDL_AUDIODRIVER', 'dummy')
    process = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, relative)], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=environment)
    try:
        output = process.communicate(timeout=20)[0]
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return              # still running after 20s: it started
    assert process.returncode == 0, (
        '{0} exited {1} on startup:\n{2}'.format(
            relative, process.returncode,
            output.decode('utf-8', 'replace')[-3000:]))


@pytest.mark.parametrize('relative', PLAYABLE)
def test_no_playable_entry_point_rejects_its_own_defaults(relative):
    """Defaults that the parser itself refuses.

    A `choices=` list that does not contain the default, or a `type=`
    that cannot parse it, fails only when someone runs the program with
    no arguments -- which is exactly how a person starts it.
    """
    with open(os.path.join(ROOT, relative)) as handle:
        tree = ast.parse(handle.read(), filename=relative)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or \
                func.attr != 'add_argument':
            continue
        keywords = dict((kw.arg, kw.value) for kw in node.keywords
                        if kw.arg)
        if 'choices' not in keywords or 'default' not in keywords:
            continue
        try:
            choices = ast.literal_eval(keywords['choices'])
            default = ast.literal_eval(keywords['default'])
        except (ValueError, TypeError, SyntaxError):
            continue            # a name or a call; not checkable here
        if default is None:
            continue
        assert default in choices, (
            '{0}: default {1!r} is not among {2!r}, so running with no '
            'arguments fails'.format(relative, default, choices))


def test_the_mnk_player_runs_a_whole_game_through_its_own_front_door():
    """A FULL GAME through the real entry point, not through a function.

    `--text` with both sides played by the agent trains from zero, plays
    a game to a result and then asks "again?"; with stdin closed that
    read raises EOFError and the program exits 0. So this covers the
    parser, the import graph, the training, the search and the result
    report in one invocation -- which is what "it works" has to mean for
    something a person runs.

    Deliberately the smallest board and the smallest budgets, so it is
    seconds rather than minutes.
    """
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'lgref', 'play_mnk.py'),
         '--text', '--x', 'td', '--o', 'td', '--m', '3', '--n', '3',
         '--k', '3', '--train-budget', '3', '--budget', '1',
         '--rounds', '2', '--games', '4', '--depth', '2'],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=300)
    output = result.stdout.decode('utf-8', 'replace')
    assert result.returncode == 0, output[-3000:]
    assert ('wins' in output or 'draw' in output), (
        'no result was reported, so the game did not finish:\n'
        + output[-2000:])


def test_the_two_budgets_are_different_quantities():
    """The regression, named.

    `--train-budget` is spent once before play; `--budget` is spent on
    every move. They were both called `--budget`, which argparse refuses
    -- and if it had not, the window would have trained for the
    per-move time or spent the training time on one move.
    """
    import ast as _ast

    with open(os.path.join(ROOT, 'lgref', 'play_mnk.py')) as handle:
        tree = _ast.parse(handle.read())
    options = []
    for where, found in _option_strings(tree).items():
        if where == 'main':
            options = found
    assert '--budget' in options and '--train-budget' in options, options
