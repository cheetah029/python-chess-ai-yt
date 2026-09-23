"""A manifest must stay resolvable after the branch it ran from is gone.

Issue #195. `git_sha` is recorded, but this repository squash-merges
feature branches: the recorded commit then becomes reachable from no
ref, and resolving it in a fresh clone fails. That happened to the first
reproducible Phase 1 gate run, and it happens to every run launched from
a branch -- so the reproducibility guarantee the field exists to provide
was not being provided for any experiment here.

A content hash does not depend on history, so no rewriting can
invalidate it.
"""

import json
import os
import subprocess
import tempfile

from lgref.core.manifest import (DEFAULT_CODE_INPUTS, RunManifest, code_hash,
                                 working_tree_diff)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def test_code_hash_is_stable_across_calls():
    assert code_hash(DEFAULT_CODE_INPUTS)['code_sha256'] == \
        code_hash(DEFAULT_CODE_INPUTS)['code_sha256']


def test_code_hash_covers_the_pipeline():
    hashed = {entry['path'] for entry in
              code_hash(DEFAULT_CODE_INPUTS)['inputs']}
    assert any(p.startswith('lgref/identify/') for p in hashed)
    assert any(p.startswith('lgref/ablate/') for p in hashed)
    assert any(p.endswith('.yaml') for p in hashed)


def test_code_hash_changes_when_a_hashed_file_changes(tmp_path):
    """Otherwise it is decoration rather than a fingerprint."""
    original = code_hash(DEFAULT_CODE_INPUTS)['code_sha256']
    target = os.path.join(REPO, 'lgref', 'ablate', 'operations.py')
    with open(target) as handle:
        before = handle.read()
    try:
        with open(target, 'w') as handle:
            handle.write(before + '\n# provenance test\n')
        assert code_hash(DEFAULT_CODE_INPUTS)['code_sha256'] != original
    finally:
        with open(target, 'w') as handle:
            handle.write(before)
    assert code_hash(DEFAULT_CODE_INPUTS)['code_sha256'] == original


def test_code_hash_does_not_depend_on_git_history():
    """The whole point: it survives a squash, a rebase, a fresh clone."""
    hashed = code_hash(DEFAULT_CODE_INPUTS)
    payload = json.dumps(hashed)
    assert 'git' not in payload.lower() or 'sha256' in payload


def test_a_missing_input_is_recorded_not_skipped():
    hashed = code_hash(['lgref/identify', 'lgref/does_not_exist'])
    missing = [e for e in hashed['inputs'] if e.get('missing')]
    assert missing, 'a missing input vanished silently'


def test_manifest_records_the_code_hash():
    with tempfile.TemporaryDirectory() as out:
        manifest = RunManifest.start('t', {'a': 1}, 0, out, repo_root=REPO)
        manifest.finish(status='ok')
        with open(os.path.join(out, 'manifest.json')) as handle:
            data = json.load(handle)
    assert data['code']['code_sha256']
    assert data['code']['inputs']


def test_a_dirty_tree_saves_its_diff():
    """`git_dirty` alone announced unreproducibility and then discarded
    the one thing that would have fixed it."""
    dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                           capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as out:
        manifest = RunManifest.start('t', {}, 0, out, repo_root=REPO)
        manifest.finish(status='ok')
        with open(os.path.join(out, 'manifest.json')) as handle:
            data = json.load(handle)
        if dirty:
            assert data.get('git_dirty') is True
            assert data.get('uncommitted_diff') == 'uncommitted.diff'
            assert os.path.exists(os.path.join(out, 'uncommitted.diff'))
        else:
            assert not data.get('uncommitted_diff')


def test_working_tree_diff_never_raises():
    """Provenance capture must not be able to fail a run."""
    assert working_tree_diff('/definitely/not/a/repo') in (None, '')
