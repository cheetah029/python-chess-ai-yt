"""Clustering must be reproducible from the config and seed alone.

The project's engineering rules require a run to be reproducible from
one config plus a seed. Clustering was not: `seed` reaches Louvain, but
the NODE AND EDGE ORDER handed to it came from iterating Python sets of
string ids, and string hashing varies per process. Measured on the
522-clause description across five values of PYTHONHASHSEED, the same
input produced 18, 19, 20, 19 and 19 clusters with different size
distributions. Every cluster count this project has reported was one
sample from that distribution.

Diagnosing it surfaced a second, independent defect: `extra` (shared
helpers, from `_shared_members`) was indexed against the raw Louvain
community order while `served` (held-out generic clauses) was indexed
against the size-sorted order. Whenever sorting moved a community --
almost always -- shared helpers were attached to the wrong rules.

Both are guarded here.
"""

import os
import subprocess
import sys
import textwrap

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# The CASE-STUDY description, not a validation game. Both defects were
# measured here and neither reproduces on tic-tac-toe: 35 clauses give a
# partition too small and too stable to expose either one. A regression
# test has to run where the bug lives.
GAME = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')

PROBE = textwrap.dedent("""
    import hashlib, sys
    from lgref.identify.clauses import load
    from lgref.identify.graph import ClauseGraph
    from lgref.identify.cluster import cluster
    graph = ClauseGraph(load(sys.argv[1]))
    rules, dropped = cluster(graph, resolution=1.0, seed=0)
    payload = repr([(r.rule_id, sorted(r.clause_ids),
                     sorted(r.shared_clause_ids)) for r in rules])
    print(hashlib.sha256(payload.encode()).hexdigest())
""")


def _partition_signature(hash_seed):
    """Cluster in a fresh process under a given PYTHONHASHSEED."""
    env = dict(os.environ)
    env['PYTHONHASHSEED'] = str(hash_seed)
    env['PYTHONPATH'] = REPO + os.pathsep + os.path.join(REPO, 'src')
    out = subprocess.run(
        [sys.executable, '-c', PROBE, GAME],
        capture_output=True, text=True, env=env, cwd=REPO, check=True)
    return out.stdout.strip()


@pytest.mark.parametrize('hash_seed', [0, 1, 2, 3])
def test_partition_is_independent_of_string_hashing(hash_seed):
    """Same config, same seed, different hash seed -> same partition.

    Run in SUBPROCESSES: PYTHONHASHSEED is fixed at interpreter start,
    so this cannot be exercised inside one test process.
    """
    assert _partition_signature(hash_seed) == _partition_signature(0), (
        'clustering depends on string hash order, so a reported cluster '
        'count is not reproducible from the config and seed')


def test_shared_helpers_attach_to_rules_they_touch():
    """A shared clause must have an edge into the rule it is shared with.

    `_shared_members` only adds a clause to a community when most of its
    edge weight lands there, so a shared member always has edges to its
    rule. If the two attachment steps disagree about which index means
    which community, shared clauses land on unrelated rules and this
    invariant breaks. That is exactly what the index mismatch did.
    """
    from lgref.identify.clauses import load
    from lgref.identify.graph import ClauseGraph
    from lgref.identify.cluster import cluster, weighted_graph

    graph = ClauseGraph(load(GAME))
    rules, _ = cluster(graph, resolution=1.0, seed=0)
    g = weighted_graph(graph)

    checked = 0
    for rule in rules:
        own = set(rule.clause_ids)
        for shared in rule.shared_clause_ids:
            if shared not in g:
                continue
            neighbours = set(g.neighbors(shared))
            assert neighbours & own, (
                '{}: shared clause {} has no edge to any of the rule\'s '
                'own clauses -- shared members are being attached to the '
                'wrong communities'.format(rule.rule_id, shared))
            checked += 1
    assert checked, 'no shared members found; the invariant tested nothing'
