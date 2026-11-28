"""Fingerprint LGREF's identification at the current commit on a fixed
set of game files (argv[1]): the groups (calibrated resolution, each
rule's statements and shared members) and, where the commit has it, the
ownership split (owned statements and relaxations). Seed 0.

Issue #409. Run it from a clean clone of the commit to fingerprint, with
the fixed game files in one directory, and PYTHONHASHSEED=0:

    PYTHONHASHSEED=0 .venv/bin/python tools/lgref_version_fingerprint.py \
        /path/to/games > fingerprints.json

It uses only APIs every V1 commit has (`clauses.load`, `ClauseGraph`,
`cluster.cluster`, and `calibrate_resolution` / `assign_ownership`
where they exist), so the same script runs on all of them. The results
are recorded in docs/lgref-version-fingerprints.json and
checked by lgref/tests/test_lgref_versions_doc.py.
"""
import glob
import hashlib
import json
import os
import sys

sys.path[:0] = ['.', 'src']

from lgref.identify.clauses import load  # noqa: E402
from lgref.identify.graph import ClauseGraph  # noqa: E402
from lgref.identify import cluster as C  # noqa: E402


def h(obj):
    blob = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


out = {}
for path in sorted(glob.glob(sys.argv[1] + '/*.gdl')):
    name = os.path.basename(path)
    try:
        nodes = load(path)
        g = ClauseGraph(nodes)
        calibrate = getattr(C, 'calibrate_resolution', None)
        res = calibrate(g, seed=0) if calibrate else 1.0
        rules, _dropped = C.cluster(g, resolution=res, seed=0)
        groups = [res, [[sorted(r.clause_ids), sorted(r.shared_clause_ids)]
                        for r in rules]]
        own = None
        if hasattr(C, 'assign_ownership'):
            if not any(getattr(r, 'owned_clause_ids', None) for r in rules):
                C.assign_ownership(rules, g)
            own = [[sorted(r.owned_clause_ids or ()),
                    sorted(map(str, r.relaxations or ()))] for r in rules]
        out[name] = {'groups': h(groups),
                     'ownership': h(own) if own is not None else None}
    except Exception as e:
        out[name] = {'error': type(e).__name__ + ': ' + str(e)[:60]}
json.dump(out, sys.stdout, indent=1, sort_keys=True)
