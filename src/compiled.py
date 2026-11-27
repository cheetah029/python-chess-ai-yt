"""Compiled hot paths: build them with Cython, load them only while fresh.

Issue #279. Depth 4 (V7) costs about 14 s of CPU per Royal Chess move in
pure Python. Compiling the unchanged source of the modules the search
spends its time in, with Cython, gives the same moves and node counts
at about 1.8x less CPU. No source is edited for it: Cython compiles the
Python as it is, with Python semantics.

TWO RULES MAKE IT SAFE.

1. A compiled module is used only while its source is UNCHANGED. The
   build records the SHA-256 of every source it compiled, and
   `activate` compares that with the source on disk at import time. An
   edited `board.py` therefore runs as Python, never as a stale
   compiled copy of its old self. Each module is checked on its own, so
   a mix of compiled and Python modules is allowed; they call each
   other through ordinary Python objects either way.
2. Nothing is compiled unless someone builds it. Without a build, or
   with `LGREF_COMPILED=0`, every import is the Python source, exactly
   as before this module existed.

Build (needs Cython 3.0.11 and a C compiler):

    python3 src/compiled.py build

The build goes to `build/compiled/` (ignored by git) and takes about a
minute. `python3 src/compiled.py status` says which modules would load
compiled. The proof that a compiled build plays identically is
`test_the_hot_modules_compiled_by_cython_play_identically` in
`lgref/tests/test_method.py`.
"""

import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
import subprocess  # nosec B404 - runs this interpreter on a fixed script
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(ROOT, 'build', 'compiled')
MANIFEST = 'manifest.json'

#: The modules compiled, by the name they are imported under, with
#: their source relative to the repository root. These are the ones the
#: depth-4 search spends its time in (move generation, turn execution,
#: the state hash, the evaluation, the search itself and its copying).
MODULES = {
    'board': 'src/board.py',
    'engine': 'src/engine.py',
    'piece': 'src/piece.py',
    'square': 'src/square.py',
    'move': 'src/move.py',
    'lgref.experiments.search': 'lgref/experiments/search.py',
    'lgref.experiments.legacy': 'lgref/experiments/legacy.py',
    'lgref.experiments.features': 'lgref/experiments/features.py',
    'lgref.experiments.fastcopy': 'lgref/experiments/fastcopy.py',
    'lgref.experiments.undo': 'lgref/experiments/undo.py',
}

_SETUP = '''
import json, sys
from setuptools import setup, Extension
from Cython.Build import cythonize
modules = json.loads(sys.argv.pop(1))
setup(script_args=sys.argv[1:], ext_modules=cythonize(
    [Extension(name, [path]) for name, path in modules.items()],
    language_level=3, quiet=True,
    compiler_directives={'binding': True}))
'''


def source_hash(path):
    """SHA-256 of a source file's bytes."""
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _interpreter():
    """What a compiled module is only valid for."""
    return '{0} {1}'.format(sys.implementation.cache_tag,
                            importlib.machinery.EXTENSION_SUFFIXES[0])


def build(out_dir=BUILD_DIR, root=ROOT, modules=None):
    """Compile `modules` (default `MODULES`) from `root` into `out_dir`.

    Each source is COPIED into a temporary directory and the copy is
    compiled, so Cython's generated C never lands in the source tree,
    and the hash recorded is the hash of exactly the bytes compiled. A
    file edited during the build is recorded as the version that was
    compiled, and then fails the freshness check at load time. Returns
    the manifest written.
    """
    modules = dict(MODULES if modules is None else modules)
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        script = os.path.join(work, 'setup_compiled.py')
        with open(script, 'w') as handle:
            handle.write(_SETUP)
        absolute, hashes = {}, {}
        for name, path in modules.items():
            with open(os.path.join(root, path), 'rb') as handle:
                data = handle.read()
            copy = os.path.join(work, 'source', path)
            os.makedirs(os.path.dirname(copy), exist_ok=True)
            with open(copy, 'wb') as handle:
                handle.write(data)
            absolute[name] = copy
            hashes[name] = hashlib.sha256(data).hexdigest()
        subprocess.run(  # nosec B603 - fixed argv, no shell
            [sys.executable, script, json.dumps(absolute), 'build_ext',
             '--build-lib', out_dir, '--build-temp',
             os.path.join(work, 'tmp')],
            check=True, cwd=work, stdout=subprocess.DEVNULL)
    manifest = {'interpreter': _interpreter(), 'modules': {}}
    for name, path in modules.items():
        found = _compiled_file(out_dir, name)
        if found is None:
            raise RuntimeError('the build produced no file for ' + name)
        manifest['modules'][name] = {
            'source': path, 'sha256': hashes[name],
            'file': os.path.relpath(found, out_dir)}
    with open(os.path.join(out_dir, MANIFEST), 'w') as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
    return manifest


def _compiled_file(out_dir, name):
    stem = os.path.join(out_dir, *name.split('.'))
    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
        if os.path.exists(stem + suffix):
            return stem + suffix
    return None


def fresh_modules(out_dir=BUILD_DIR, root=ROOT):
    """`{name: compiled file}` for every built module whose source is
    unchanged since the build. Empty when there is no build, when it
    was made for another interpreter, or when `LGREF_COMPILED=0`."""
    if os.environ.get('LGREF_COMPILED') == '0':
        return {}
    try:
        with open(os.path.join(out_dir, MANIFEST)) as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        return {}
    if manifest.get('interpreter') != _interpreter():
        return {}
    fresh = {}
    for name, entry in manifest.get('modules', {}).items():
        source = os.path.join(root, entry['source'])
        compiled = os.path.join(out_dir, entry['file'])
        try:
            if (source_hash(source) == entry['sha256']
                    and os.path.exists(compiled)):
                fresh[name] = compiled
        except OSError:
            continue
    return fresh


class _Finder(importlib.abc.MetaPathFinder):
    """Answers only for the fresh compiled modules; every other import,
    and every stale one, falls through to the normal finders."""

    def __init__(self, files):
        self.files = dict(files)

    def find_spec(self, name, path=None, target=None):
        compiled = self.files.get(name)
        if compiled is None:
            return None
        loader = importlib.machinery.ExtensionFileLoader(name, compiled)
        return importlib.util.spec_from_file_location(name, compiled,
                                                      loader=loader)


def activate(out_dir=BUILD_DIR, root=ROOT):
    """Load the fresh compiled modules from now on. Returns their names.

    Call it before the modules are first imported: one already imported
    stays what it is. Calling it twice replaces the earlier finder.
    """
    sys.meta_path[:] = [f for f in sys.meta_path
                        if not isinstance(f, _Finder)]
    files = fresh_modules(out_dir, root)
    if files:
        sys.meta_path.insert(0, _Finder(files))
    return sorted(files)


def loaded_from(names=None):
    """`{name: file}` for the given modules (default `MODULES`) as
    imported now, so a caller can check what actually runs."""
    return {name: getattr(sys.modules.get(name), '__file__', None)
            for name in (MODULES if names is None else names)}


def main(argv):
    if argv[1:2] == ['build']:
        manifest = build()
        print('built {0} modules into {1}'.format(
            len(manifest['modules']), BUILD_DIR))
    fresh = fresh_modules()
    for name in MODULES:
        print('{0:30s} {1}'.format(
            name, 'compiled' if name in fresh else 'python'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
