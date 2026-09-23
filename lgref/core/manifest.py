"""Run manifests — the provenance record for every LGREF experiment.

Non-negotiable project rule: any run must be reproducible from a single
config file plus a seed, and every run records what produced it. A
manifest answers, months later and for a reviewer who was not there:
which code, which config, which seed, on what machine, for how long,
and at what cost.

A manifest is written TWICE: once at run start (so a crashed or killed
run still leaves evidence it was attempted, with status 'running'), and
once at completion with outcome, timings and cost filled in. Nothing is
ever deleted or rewritten in place by a later run — see storage.py for
the accumulate-only layout.

The config hash is over the fully-resolved config, not the file text, so
two runs whose YAML differs only in comments or key order hash equal.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
import time


SCHEMA_VERSION = 1


# The files whose contents determine an LGREF run: the identification
# pipeline, the ablation operations, the shared infrastructure, and the
# configs. Not src/ -- the engine is fingerprinted separately by
# engine_info(), and not the description, which the caller passes since
# it differs per run.
DEFAULT_CODE_INPUTS = (
    'lgref/identify', 'lgref/ablate', 'lgref/core', 'lgref/config',
)


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


def git_sha(repo_root=None, short=False):
    """Current commit SHA, or None outside a git work tree.

    Never raises: provenance capture must not be able to fail a run.
    """
    cmd = ['git', 'rev-parse', '--short' if short else 'HEAD']
    try:
        out = subprocess.run(
            cmd, cwd=repo_root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def git_is_dirty(repo_root=None):
    """True if the work tree has uncommitted changes, None if unknown.

    A dirty tree means `git_sha` does NOT fully describe the code that
    ran, so the manifest records it rather than quietly implying the
    commit is the whole story.
    """
    try:
        out = subprocess.run(['git', 'status', '--porcelain'],
                             cwd=repo_root, capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return bool(out.stdout.strip())


def config_hash(config):
    """Stable SHA-256 over a resolved config mapping.

    Canonicalised with sorted keys so formatting, comments and key order
    cannot change the hash. Non-JSON-serialisable values fall back to
    repr, which keeps the hash stable within a Python version without
    claiming cross-version stability for exotic types.
    """
    blob = json.dumps(config, sort_keys=True, default=repr,
                      separators=(',', ':'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def machine_info():
    """Identify the host well enough to explain timing differences."""
    return {
        'platform': platform.platform(),
        'processor': platform.processor() or platform.machine(),
        'python': sys.version.split()[0],
        'cpu_count': os.cpu_count(),
        'hostname': platform.node(),
    }


def engine_info():
    """Version-identify the game rules this run measured.

    The rules live in src/ and are shared with the playable game, so the
    manifest records the engine module's own fingerprint rather than a
    version string nobody remembers to bump.
    """
    info = {}
    try:
        import engine  # noqa: F401  (src/ must be on sys.path)
        path = getattr(engine, '__file__', None)
        info['engine_module'] = path
        if path and os.path.exists(path):
            with open(path, 'rb') as f:
                info['engine_sha256'] = hashlib.sha256(f.read()).hexdigest()
    except Exception as exc:                      # pragma: no cover
        info['engine_import_error'] = repr(exc)
    return info


def code_hash(paths, repo_root=None):
    """Fingerprint the files that actually determine a run.

    `git_sha` is recorded too, but it does not survive this repository's
    workflow: runs are launched from a feature branch, the branch is
    squash-merged, and the recorded commit becomes reachable from no ref
    -- so resolving it in a fresh clone fails. That happened to the first
    reproducible Phase 1 gate run, and it happens to EVERY run launched
    from a branch, which means the guarantee the field exists to provide
    was not being provided for any experiment in the project (#195).

    A content hash does not depend on history at all, so no rewriting can
    invalidate it, and it answers the question the SHA was standing in
    for -- "was this the same code?" -- directly.

    Returns {'code_sha256': ..., 'inputs': [{path, sha256, bytes}, ...]}
    with inputs sorted, so the digest is stable across filesystems.
    """
    root = repo_root or _repo_root()
    entries = []
    for item in sorted(paths):
        full = item if os.path.isabs(item) else os.path.join(root, item)
        if os.path.isdir(full):
            files = []
            for base, _, names in os.walk(full):
                if '__pycache__' in base:
                    continue
                files += [os.path.join(base, n) for n in names
                          if n.endswith(('.py', '.gdl', '.yaml', '.yml'))]
        elif os.path.exists(full):
            files = [full]
        else:
            entries.append({'path': item, 'sha256': None, 'missing': True})
            continue
        for name in sorted(files):
            with open(name, 'rb') as handle:
                blob = handle.read()
            entries.append({
                'path': os.path.relpath(name, root),
                'sha256': hashlib.sha256(blob).hexdigest(),
                'bytes': len(blob),
            })

    digest = hashlib.sha256()
    for entry in entries:
        digest.update(entry['path'].encode())
        digest.update((entry['sha256'] or 'missing').encode())
    return {'code_sha256': digest.hexdigest(), 'inputs': entries}


def working_tree_diff(repo_root=None, max_bytes=2_000_000):
    """The uncommitted state, INCLUDING untracked files.

    `git_dirty` was recorded without the diff, so a run from a dirty
    tree announced that it was unreproducible and then threw away the
    one thing that would have fixed it.

    Untracked files have to be in here. `git status` counts them as
    dirty but `git diff HEAD` does not show them, so a run whose new
    code is not yet added -- which is every run during development --
    produced `git_dirty: true` next to an EMPTY diff. A test caught
    exactly that on this module's own first version.
    """
    root = repo_root or _repo_root()

    def _run(args):
        try:
            done = subprocess.run(args, cwd=root, capture_output=True,
                                  text=True, timeout=60)
            return done.stdout or ''
        except Exception:                          # pragma: no cover
            return ''

    parts = [_run(['git', 'diff', 'HEAD'])]

    untracked = [name for name in
                 _run(['git', 'ls-files', '--others',
                       '--exclude-standard']).splitlines() if name]
    for name in untracked:
        # `--no-index` against /dev/null renders a new file as a diff,
        # so the capture is one applicable patch rather than a patch
        # plus a pile of loose files.
        parts.append(_run(['git', 'diff', '--no-index', '--binary',
                           '/dev/null', name]))

    diff = ''.join(parts)
    if len(diff) > max_bytes:
        diff = diff[:max_bytes] + (
            '\n... truncated at {} bytes; {} untracked file(s) were '
            'included\n'.format(max_bytes, len(untracked)))
    return diff or None


class RunManifest:
    """Provenance + cost record for one experiment run.

    Usage:

        m = RunManifest.start(run_id, config, seed, out_dir)
        ...                       # do the work
        m.finish(status='ok', metrics={...})

    `start` writes manifest.json immediately with status 'running'.
    `finish` rewrites it with the outcome. A run that dies in between
    leaves a 'running' manifest, which is the signal that a result
    directory is incomplete rather than merely empty.
    """

    FILENAME = 'manifest.json'

    def __init__(self, data, out_dir):
        self.data = data
        self.out_dir = out_dir

    # ---- construction ---------------------------------------------------

    @classmethod
    def start(cls, run_id, config, seed, out_dir, repo_root=None,
              cost_model=None, code_inputs=None):
        os.makedirs(out_dir, exist_ok=True)
        data = {
            'schema_version': SCHEMA_VERSION,
            'run_id': run_id,
            'status': 'running',
            'seed': seed,
            'config': config,
            'config_hash': config_hash(config),
            'git_sha': git_sha(repo_root),
            'git_dirty': git_is_dirty(repo_root),
            'code': code_hash(code_inputs or DEFAULT_CODE_INPUTS, repo_root),
            'machine': machine_info(),
            'engine': engine_info(),
            'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'started_monotonic': time.monotonic(),
            'cost_model': cost_model,
        }
        if data['git_dirty']:
            diff = working_tree_diff(repo_root)
            if diff:
                with open(os.path.join(out_dir, 'uncommitted.diff'),
                          'w') as handle:
                    handle.write(diff)
                data['uncommitted_diff'] = 'uncommitted.diff'
        m = cls(data, out_dir)
        m.write()
        return m

    # ---- completion -----------------------------------------------------

    def finish(self, status='ok', metrics=None, cost=None, error=None):
        """Seal the manifest with outcome, wall-clock and cost."""
        started = self.data.pop('started_monotonic', None)
        elapsed = (time.monotonic() - started) if started is not None else None
        self.data['status'] = status
        self.data['finished_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        self.data['wall_clock_s'] = elapsed
        if metrics is not None:
            self.data['metrics'] = metrics
        if cost is not None:
            self.data['cost'] = cost
        if error is not None:
            self.data['error'] = error
        self.write()
        return self

    # ---- io -------------------------------------------------------------

    @property
    def path(self):
        return os.path.join(self.out_dir, self.FILENAME)

    def write(self):
        # Write-then-rename so a crash mid-write cannot leave a
        # truncated manifest that looks like a valid one.
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.data, f, indent=2, sort_keys=True, default=repr)
            f.write('\n')
        os.replace(tmp, self.path)
        return self.path

    @classmethod
    def load(cls, out_dir):
        with open(os.path.join(out_dir, cls.FILENAME)) as f:
            return cls(json.load(f), out_dir)
