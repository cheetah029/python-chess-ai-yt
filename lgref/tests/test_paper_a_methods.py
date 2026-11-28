"""The Paper A grouping methods (#350): each does what its name says.

  - `lgref` through the pluggable pipeline is EXACTLY production
    `cluster` at the calibrated resolution, on games where the overlap
    step actually fires (so the equality checks the overlap machinery);
  - Leiden and link communities give the textbook answer on graphs whose
    answer is known;
  - the random baseline keeps LGREF's shape and nothing else;
  - every method covers every statement and is deterministic, across
    processes with different hash seeds as well as within one.
"""

import json
import os
import random
import subprocess  # nosec B404: runs this interpreter on a fixed script
import sys

import pytest

import lgref  # noqa: F401
from lgref.bench import methods as M
from lgref.bench.catalog import game_path
from lgref.identify.clauses import load, normalize
from lgref.identify.cluster import calibrate_resolution, cluster
from lgref.identify.graph import ClauseGraph

DEV = ('tictactoe', 'nim', 'corridor', 'breakthrough5', 'othello4')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def _nodes(game):
    return load(game_path(game))


@pytest.mark.parametrize('game', DEV)
def test_lgref_method_is_production_cluster(game):
    nodes = _nodes(game)
    graph = ClauseGraph(nodes)
    rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
    want = sorted(sorted(r.all_clause_ids) for r in rules)
    got = M.lgref(nodes)
    assert sorted(sorted(g) for g in got.groups) == want
    assert sorted(sorted(c) for c in got.core) == sorted(
        sorted(r.clause_ids) for r in rules)


def test_the_equality_exercises_overlap():
    """If no dev game had a shared member, the test above could not see
    a broken overlap step."""
    shared = 0
    for game in DEV:
        grouping = M.lgref(_nodes(game))
        shared += sum(1 for n, g in grouping.membership().items()
                      if len(g) > 1)
    assert shared > 0


def test_hard_variants_have_no_overlap():
    for game in DEV:
        for method in ('louvain_hard', 'leiden_hard', 'dependency_louvain',
                       'components', 'singletons', 'one_group'):
            grouping = M.run(method, _nodes(game))
            assert all(len(g) <= 1
                       for g in grouping.membership().values()), method


@pytest.mark.parametrize('method', list(M.METHODS))
def test_every_method_covers_every_statement(method):
    nodes = _nodes('breakthrough5')
    grouping = M.run(method, nodes)
    ids = {n.node_id for n in nodes}
    assert set(grouping.membership()) == ids
    assert all(g and g <= ids for g in grouping.groups)


@pytest.mark.parametrize('method', list(M.METHODS))
def test_every_method_is_repeatable(method):
    nodes = _nodes('othello4')
    a = M.run(method, nodes, seed=3).groups
    b = M.run(method, nodes, seed=3).groups
    assert a == b


_SCRIPT = r'''
import json, sys
sys.path.insert(0, {repo!r})
import lgref
from lgref.bench import methods as M
from lgref.bench.catalog import game_path
from lgref.identify.clauses import load
nodes = load(game_path('othello4'))
out = {{m: [sorted(g) for g in M.run(m, nodes, seed=1).groups]
       for m in M.METHODS}}
print(json.dumps(out, sort_keys=True))
'''


def test_methods_are_deterministic_across_processes():
    """One interpreter has one hash seed, so repeating inside it proves
    nothing about set-ordering bugs; two seeds do."""
    script = _SCRIPT.format(repo=REPO)
    runs = []
    for hash_seed in ('0', '1'):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        done = subprocess.run(  # nosec B603: fixed argv, no shell
            [sys.executable, '-c', script], env=env, check=True,
            capture_output=True, text=True, timeout=600)
        runs.append(json.loads(done.stdout))
    assert runs[0] == runs[1]


# ---- known answers on toy graphs ----------------------------------------

def _toy(text):
    from ggp.infix import parse_infix
    return normalize(parse_infix(text))


def _two_cliques():
    """Two families of statements, each a clique of predicate calls,
    joined by one call: a(...) and b(...) predicates."""
    lines = []
    for family in ('a', 'b'):
        for i in range(5):
            body = ' & '.join('{}{}(X)'.format(family, j)
                              for j in range(5) if j != i)
            lines.append('{f}{i}(X) :- {b}'.format(f=family, i=i, b=body))
    lines.append('a0(X) :- b0(X)')
    return _toy('\n'.join(lines))


def test_leiden_splits_two_cliques():
    nodes = _two_cliques()
    grouping = M.leiden(nodes, resolution=1.0)
    names = [sorted(n.split('#')[0][0] for n in g) for g in grouping.groups]
    assert len(grouping.groups) == 2
    assert all(len(set(g)) == 1 for g in names)


def test_leiden_does_not_touch_global_random_state():
    random.seed(11)
    before = random.random()
    random.seed(11)
    M.leiden(_two_cliques(), resolution=1.0, seed=5)
    assert random.random() == before


def _graph(edges):
    import networkx as nx
    g = nx.Graph()
    for a, b in edges:
        g.add_edge(a, b, weight=1.0)
    return g, {n: i for i, n in enumerate(sorted(g.nodes))}


def test_link_communities_two_triangles_share_the_hinge():
    """Ahn et al.'s own example shape: two triangles meeting at node 3.
    Two link communities, node 3 in both, partition density 1."""
    g, order = _graph([(1, 2), (1, 3), (2, 3), (3, 4), (3, 5), (4, 5)])
    communities, density = M.link_communities_of(g, order)
    found = sorted(sorted(c) for c in communities)
    assert found == [[1, 2, 3], [3, 4, 5]]
    assert density == pytest.approx(1.0)


def test_link_communities_of_a_clique_is_one_community():
    g, order = _graph([(a, b) for a in range(5) for b in range(a + 1, 5)])
    communities, density = M.link_communities_of(g, order)
    assert communities == [set(range(5))]
    assert density == pytest.approx(1.0)


def test_link_communities_of_a_path_keeps_edges_apart():
    """A path has no community structure: D is 0 at every cut, so the
    single-edge partition (the first) is kept."""
    g, order = _graph([(1, 2), (2, 3), (3, 4)])
    communities, density = M.link_communities_of(g, order)
    assert len(communities) == 3 and density == 0.0


def test_random_matched_keeps_the_shape_only():
    nodes = _nodes('corridor')
    base = M.lgref(nodes)
    one = M.random_matched(nodes, seed=1)
    two = M.random_matched(nodes, seed=2)
    assert sorted(len(g) for g in one.groups) == sorted(
        len(g) for g in base.groups)
    assert sorted(len(g) for g in one.membership().values()) == sorted(
        len(g) for g in base.membership().values())
    assert one.groups != two.groups
    assert one.groups == M.random_matched(nodes, seed=1).groups


def test_trivial_baselines():
    nodes = _nodes('nim')
    assert len(M.singletons(nodes)) == len(nodes)
    assert len(M.one_group(nodes)) == 1


def test_link_communities_partition_density_is_in_range():
    grouping = M.link_communities(_nodes('othello4'))
    assert 0.0 <= grouping.info['partition_density'] <= 1.0


def test_igraph_is_pinned():
    with open(os.path.join(REPO, 'requirements.txt')) as handle:
        text = handle.read()
    assert 'igraph==' in text and 'texttable==' in text


def test_postfreeze_variant_is_kept_out_of_the_frozen_list():
    """#394: the post-freeze variant runs only when named, so no default
    run -- and no frozen result -- includes it."""
    assert 'lgref_postfreeze_noterminal' not in M.METHODS
    assert 'lgref_postfreeze_noterminal' in M.POSTFREEZE
    assert 'lgref_postfreeze_noterminal' in M.SEEDED


def test_postfreeze_variant_is_lgref_without_the_terminal_edge():
    from lgref.identify.cluster import DEFAULT_WEIGHTS
    nodes = _nodes('nim')
    got = M.run('lgref_postfreeze_noterminal', nodes, seed=0)
    weights = dict(DEFAULT_WEIGHTS)
    weights['terminal'] = 0.0
    assert got.groups == M.lgref(nodes, seed=0, weights=weights).groups
    assert got.method == 'lgref_postfreeze_noterminal'
    # ...and it is a different grouping from production on some game.
    assert any(M.run('lgref_postfreeze_noterminal', _nodes(g)).groups
               != M.lgref(_nodes(g)).groups for g in DEV)


def test_reports_list_the_postfreeze_variant():
    from lgref.bench import report
    record = {'rows': [{'method': 'lgref_postfreeze_noterminal'},
                       {'method': 'lgref'}]}
    assert report._methods_in(record) == ['lgref',
                                          'lgref_postfreeze_noterminal']
