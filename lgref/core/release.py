"""Publishing raw results to GitHub Releases, with committed checksums.

The storage decision (issue #172): raw Parquet is far too large for git
(~1-2 GB per sweep), but "results accumulate and are never deleted" is
worthless if the only copy is on one laptop. So:

  - raw Parquet bundles are uploaded as GitHub Release assets (free,
    2 GB per file), and
  - a SMALL index recording a SHA-256 per bundle IS committed to git.

The committed checksum is the point of the whole arrangement. It means
the reproduction script can download the bundles and PROVE they are the
same bytes the published figures were computed from. Without it,
"download the data from the release" is an appeal to trust; with it, a
reviewer can verify.

This module does the packaging, hashing and index bookkeeping. Actual
upload is left to `gh release upload`, which is printed as the command
to run: publishing is an outward-facing action, so it stays an explicit
human step rather than something a training script does on its own.
"""

import hashlib
import json
import os
import tarfile
import time


INDEX_FILENAME = 'release_index.json'
CHUNK = 1024 * 1024


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()


def bundle_run(run_dir, out_path=None):
    """Tar+gzip one run directory (manifest + parquet parts).

    Parquet is already compressed, so gzip here buys little on the data
    itself; the tar is for shipping ONE asset per run instead of dozens
    of part files, which keeps the release listing and the index legible.
    """
    run_dir = os.path.abspath(run_dir)
    if not os.path.isdir(run_dir):
        raise ValueError(f'not a run directory: {run_dir}')
    if out_path is None:
        parent = os.path.dirname(run_dir)
        name = f'{os.path.basename(os.path.dirname(run_dir))}-' \
               f'{os.path.basename(run_dir)}.tar.gz'
        out_path = os.path.join(parent, name)
    with tarfile.open(out_path, 'w:gz') as tar:
        tar.add(run_dir, arcname=os.path.basename(run_dir))
    return out_path


def describe_bundle(path, run_dir=None):
    """Checksum + size record for one bundle."""
    rec = {
        'asset': os.path.basename(path),
        'sha256': sha256_file(path),
        'bytes': os.path.getsize(path),
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    }
    if run_dir:
        manifest_path = os.path.join(run_dir, 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                m = json.load(f)
            # Carry the identifying provenance into the index so the
            # committed file alone answers "which code produced this?"
            rec.update({
                'run_id': m.get('run_id'),
                'seed': m.get('seed'),
                'git_sha': m.get('git_sha'),
                'config_hash': m.get('config_hash'),
                'status': m.get('status'),
            })
    return rec


def load_index(index_path):
    if not os.path.exists(index_path):
        return {'schema_version': 1, 'release_tag': None, 'bundles': {}}
    with open(index_path) as f:
        return json.load(f)


def update_index(index_path, record, release_tag=None):
    """Add or replace one bundle's record in the committed index.

    Keyed by asset name, so re-publishing a corrected bundle updates its
    checksum rather than appending a duplicate the verifier would then
    have to disambiguate.
    """
    index = load_index(index_path)
    if release_tag:
        index['release_tag'] = release_tag
    index['bundles'][record['asset']] = record
    index['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    os.makedirs(os.path.dirname(index_path) or '.', exist_ok=True)
    tmp = index_path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(index, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, index_path)
    return index


def verify_bundle(path, index_path):
    """Check a downloaded bundle against the committed checksum.

    Returns (ok, detail). Used by the reproduction script; a mismatch
    must be loud, because silently analysing the wrong bytes is exactly
    the failure this design exists to prevent.
    """
    index = load_index(index_path)
    asset = os.path.basename(path)
    rec = index.get('bundles', {}).get(asset)
    if rec is None:
        return False, f'{asset} is not in {INDEX_FILENAME}'
    if not os.path.exists(path):
        return False, f'{asset} not downloaded'
    actual = sha256_file(path)
    if actual != rec['sha256']:
        return False, (f'{asset} CHECKSUM MISMATCH\n'
                       f'  expected {rec["sha256"]}\n'
                       f'  actual   {actual}')
    return True, f'{asset} verified ({rec["bytes"]} bytes)'


def verify_all(download_dir, index_path):
    """Verify every bundle named in the index. Returns (ok, [details])."""
    index = load_index(index_path)
    details = []
    ok = True
    for asset in sorted(index.get('bundles', {})):
        good, detail = verify_bundle(os.path.join(download_dir, asset),
                                     index_path)
        ok = ok and good
        details.append(detail)
    return ok, details


def upload_command(path, release_tag):
    """The `gh` command to publish a bundle.

    Printed rather than executed: uploading publishes data outside the
    machine, which is a human decision, not a side effect of a run.
    """
    return f'gh release upload {release_tag} {path} --clobber'
