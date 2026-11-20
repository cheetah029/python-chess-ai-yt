"""Signals from play, and the protocol that tests them (#321).

The tracer is checked against proofs worked out by hand: a proof records
the statements it used, a statement tried and abandoned leaves no mark,
and one consulted under negation is not "used". The protocol is checked
for the same discipline as `protocol.py`: dev only for tuning,
validation once, test never.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.identify import signals
from lgref.identify.clauses import load
from lgref.identify.coactivation import collect_proof_traces
from lgref.identify.graph import ClauseGraph
from lgref.identify.testgames.ground_truth import SPLITS

# A one-move game whose proofs can be written down by hand.
#   0 role(p)
#   1 init(on)
#   2 legal(p, go(X)) :- true(on) & spot(X) & ~blocked(X)
#   3 spot(a)   4 spot(b)
#   5 blocked(b) :- true(on)
#   6 decoy(X)  :- spot(X) & ~spot(X)          (never provable)
#   7 next(done) :- does(p, go(X))
#   8 terminal :- true(done)
#   9 goal(p, 100) :- true(done)
GAME = """
role(p)
init(on)
legal(p, go(X)) :- true(on) & spot(X) & ~blocked(X)
spot(a)
spot(b)
blocked(b) :- true(on)
decoy(X) :- spot(X) & ~spot(X)
next(done) :- does(p, go(X))
terminal :- true(done)
goal(p, 100) :- true(done)
"""


def _trace():
    with tempfile.NamedTemporaryFile('w', suffix='.gdl',
                                     delete=False) as handle:
        handle.write(GAME)
    try:
        nodes = load(handle.name)
        return nodes, collect_proof_traces(handle.name, nodes, n_games=1,
                                           max_plies=5)
    finally:
        os.unlink(handle.name)


def test_a_proof_records_exactly_the_statements_it_used():
    nodes, proofs = _trace()
    ids = [n.node_id for n in nodes]
    as_sets = {frozenset(p) for p in proofs}
    # The one legal move, go(a): the legal statement and spot(a). The
    # negated `blocked(a)` was consulted and failed, so `blocked` is not
    # in the proof.
    assert frozenset({ids[2], ids[3]}) in as_sets
    # go(b) is not legal: spot(b) was tried and the proof abandoned, so
    # no recorded proof contains spot(b) with the legal statement.
    assert not any(ids[4] in p and ids[2] in p for p in proofs)
    # The successor, the ending and the payoff.
    assert frozenset({ids[7]}) in as_sets
    assert frozenset({ids[8]}) in as_sets
    assert frozenset({ids[9]}) in as_sets


def test_a_statement_never_proved_never_appears():
    nodes, proofs = _trace()
    decoy = nodes[6].node_id
    assert not any(decoy in p for p in proofs)


def test_co_use_links_a_shared_helper_into_each_rule_that_uses_it():
    """The point of containment over Jaccard: a helper used by two rules
    is linked to both, though it is used with each only half the time."""
    nodes = load(os.path.join(os.path.dirname(__file__), '..', 'identify',
                              'testgames', 'tictactoe.gdl'))
    graph = ClauseGraph(nodes)
    a, b, helper = (nodes[2].node_id, nodes[3].node_id, nodes[4].node_id)
    proofs = [{a, helper}] * 5 + [{b, helper}] * 5
    graph.add_co_use(proofs)
    edges = graph.edges['co_use']
    assert (min(a, helper), max(a, helper)) in edges or \
        (a, helper) in edges or (helper, a) in edges
    assert any(set(e) == {b, helper} for e in edges)
    assert not any(set(e) == {a, b} for e in edges)

    # Jaccard on the same proofs would not link the helper at all:
    # each rule shares half its helper's uses.
    graph2 = ClauseGraph(nodes)
    graph2.add_co_activation(proofs)
    assert not any(helper in e for e in graph2.edges['co_activation'])


def test_co_use_ignores_rarely_seen_pairs():
    nodes = load(os.path.join(os.path.dirname(__file__), '..', 'identify',
                              'testgames', 'tictactoe.gdl'))
    graph = ClauseGraph(nodes)
    graph.add_co_use([{nodes[2].node_id, nodes[4].node_id}] * 2)
    assert graph.edge_count('co_use') == 0


def test_co_use_is_off_by_default():
    from lgref.identify.cluster import DEFAULT_WEIGHTS
    assert DEFAULT_WEIGHTS['co_use'] == 0.0


# ---- the protocol only looks where it is allowed to -----------------------

def _spy(monkeypatch):
    seen = []
    real = signals.score

    def score(game, signal, seed=0):
        seen.append(game)
        return real(game, signal, seed)

    monkeypatch.setattr(signals, 'score', score)
    return seen


def test_tuning_reads_the_dev_split_only(monkeypatch):
    seen = _spy(monkeypatch)
    signals.select()
    assert set(seen) == set(SPLITS['dev'])


def test_the_decision_reads_the_validation_split_only(monkeypatch):
    seen = _spy(monkeypatch)
    signals.decide(('co_use', 1.0))
    assert set(seen) == set(SPLITS['validation'])


def test_ties_keep_the_static_default(monkeypatch):
    monkeypatch.setattr(signals, 'mean_ari', lambda games, s, seed=0: 0.5)
    assert signals.select()[0] == signals.DEFAULT
    assert signals.decide(('co_use', 1.0))[0] == signals.DEFAULT


def test_the_default_signal_is_the_production_graph():
    """`static` must score exactly what the protocol's default scores,
    or the comparison is against something production never runs."""
    from lgref.identify import protocol
    for game in SPLITS['dev']:
        assert signals.score(game, signals.DEFAULT)['ari'] == \
            protocol.score(game, protocol.DEFAULT)['ari']
