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
              cost_model=None):
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
            'machine': machine_info(),
            'engine': engine_info(),
            'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'started_monotonic': time.monotonic(),
            'cost_model': cost_model,
        }
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
