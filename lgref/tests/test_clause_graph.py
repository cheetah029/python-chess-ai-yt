"""Typed clause dependency graph, checked against rules verifiable by hand.

Clustering reads this graph, so a missing edge type makes a real rule
unfindable and a spurious one merges rules that should stay apart.
Neither failure announces itself: a wrong cluster is still a plausible
list of clauses. So these tests assert on structure the rulebook lets us
verify independently.
"""

import collections
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ggp.parser import parse
from lgref.identify.clauses import normalize
from lgref.identify.graph import ClauseGraph, build


def _graph(text):
    return ClauseGraph(normalize(parse(text)))


# ---- predicate edges -----------------------------------------------------

def test_predicate_edge_runs_from_definer_to_caller():
    g = _graph('(<= (pawnless) (not (any_pawn)))'
               '(<= (any_pawn) (true (cell ?f ?r ?c pawn)))')
    definer = [n for n in g.nodes if n.head_predicate == 'any_pawn'][0]
    caller = [n for n in g.nodes if n.head_predicate == 'pawnless'][0]
    assert (definer.node_id, caller.node_id) in g.edges['predicate']


# ---- temporal edges ------------------------------------------------------

def test_temporal_edge_links_a_fluent_writer_to_its_reader():
    """The boulder's cooldown is written on one turn and read on a later
    one. Nothing in the predicate graph connects those clauses — only a
    temporal edge can, and without it the boulder rule is not findable as
    one unit."""
    g = _graph('(<= (next (boulder_cooldown 2)) (does ?p (move boulder ?a ?b ?c ?d)))'
               '(<= (legal ?p (move boulder ?a ?b ?c ?d)) (true (boulder_cooldown 0)))')
    writer = [n for n in g.nodes if n.head_kind == 'fluent_write'][0]
    reader = [n for n in g.nodes if n.head_kind == 'legal'][0]
    assert (writer.node_id, reader.node_id) in g.edges['temporal']


def test_self_persistence_does_not_create_a_temporal_self_edge():
    """`(<= (next (X)) (true (X)) ...)` is a fluent carrying itself
    forward — self-continuity, not a dependency between two clauses."""
    g = _graph('(<= (next (boulder_at intersection)) (true (boulder_at intersection)))')
    assert g.edges['temporal'] == set()


# ---- legality edges ------------------------------------------------------

def test_legality_edge_links_permission_to_effect():
    """A `legal` clause and the `next` clause that carries out the same
    action communicate only through `does`, which the game manager
    supplies — so no predicate edge ever links them, though permitting an
    action and performing it are one provision."""
    g = _graph('(<= (legal ?p (jump_capture ?a ?b ?c ?d ?e ?f)) (true (control ?p)))'
               '(<= (next (invulnerable ?c ?d)) (does ?p (jump_capture ?a ?b ?c ?d ?e ?f)))')
    legal = [n for n in g.nodes if n.head_kind == 'legal'][0]
    effect = [n for n in g.nodes if n.head_kind == 'fluent_write'][0]
    pair = tuple(sorted((legal.node_id, effect.node_id)))
    assert pair in g.edges['legality']


def test_legality_edges_do_not_cross_action_types():
    """A move's permission must not be linked to a transform's effect."""
    g = _graph('(<= (legal ?p (move knight ?a ?b ?c ?d)) (true (control ?p)))'
               '(<= (next (queen_form ?a ?b rook)) (does ?p (transform ?a ?b rook)))')
    assert g.edges['legality'] == set()


# ---- shared-state edges: the negation criterion --------------------------

def test_positive_shared_reads_create_an_edge():
    g = _graph('(<= (a) (true (reactive_armed ?x ?y ?z ?w)))'
               '(<= (b) (true (reactive_armed ?x ?y ?z ?w)))')
    assert len(g.edges['shared_state']) == 1


def test_negated_guard_reads_do_not_create_an_edge():
    """`invulnerable` is read by 29 clauses and `manipulation_freeze` by
    21, nearly always as `(not (true (...)))`. A guard means one rule
    CONSTRAINING another, not two clauses implementing one rule. Linking
    every capture rule because each checks invulnerability would merge
    all of them into a single cluster."""
    g = _graph('(<= (a) (not (true (invulnerable ?f ?r))))'
               '(<= (b) (not (true (invulnerable ?f ?r))))')
    assert g.edges['shared_state'] == set()


def test_ubiquitous_fluents_are_excluded_on_a_real_description():
    """A fluent read by a large FRACTION of clauses is infrastructure.
    Measured on Royal Chess: cell 95 readers (19%), control 48 (10%),
    queen_form 45 (9%) — then a sharp drop to 7 and below.

    The property asserted is that NO edge exists solely because two
    clauses share a hub fluent. Checking the intersection of two linked
    clauses' reads would not show this: clauses joined by a legitimate
    boulder_cooldown edge usually read `cell` as well.

    The cut is a fraction rather than a name list, so it calibrates to
    whatever game is analysed.
    """
    g = build()
    readers = collections.Counter()
    for n in g.nodes:
        for f in n.fluents_read:
            readers[f] += 1
    hubs = {f for f, c in readers.items() if c > 40}
    assert {'cell', 'control', 'queen_form'} <= hubs

    for a, b in g.edges['shared_state']:
        shared = g.by_id[a].fluents_read & g.by_id[b].fluents_read
        assert shared - hubs, (
            f'{a} and {b} are linked but share only hub fluents '
            f'{sorted(shared)} — infrastructure leaked into shared_state')


def test_small_descriptions_keep_their_shared_state_edges():
    """The ubiquity cut must not fire below a usable sample — in a
    two-clause graph any shared fluent is '100% of clauses'."""
    g = _graph('(<= (a) (true (reactive_armed ?x ?y ?z ?w)))'
               '(<= (b) (true (reactive_armed ?x ?y ?z ?w)))')
    assert len(g.edges['shared_state']) == 1


# ---- terminal edges ------------------------------------------------------

def test_terminal_clauses_are_linked():
    g = _graph('(<= (lost ?p) (true (control ?p)) (no_moves ?p))'
               '(<= (terminal) (lost ?p))')
    assert len(g.edges['terminal']) >= 1


# ---- co-activation -------------------------------------------------------

def test_co_activation_edges_come_from_traces():
    """Static structure cannot tell a helper genuinely shared between two
    rules from one that merely could be. Only observed games can.

    An edge needs CONSISTENT association, not a single shared state:
    raw co-occurrence was measured to halve identification quality, so
    the trace here repeats enough times to clear both the association
    ratio and the minimum-observations floor.
    """
    g = _graph('(<= (a) (foo))(<= (b) (bar))')
    ids = [n.node_id for n in g.nodes]
    assert g.edge_count('co_activation') == 0
    g.add_co_activation([set(ids)] * 4)
    assert g.edge_count('co_activation') == 1


def test_co_activation_ignores_unknown_clause_ids():
    g = _graph('(<= (a) (foo))')
    g.add_co_activation([{'not-a-real-node#999', g.nodes[0].node_id}])
    assert g.edge_count('co_activation') == 0


# ---- no self-edges anywhere ---------------------------------------------

def test_no_edge_type_produces_a_self_loop():
    g = build()
    for kind, edges in g.edges.items():
        selfloops = [(a, b) for a, b in edges if a == b]
        assert not selfloops, f'{kind} has self-loops: {selfloops[:3]}'


# ---- the real ruleset ----------------------------------------------------

def test_real_graph_has_every_edge_type_populated():
    """A missing edge type means a whole class of rule is unfindable."""
    g = build()
    for kind in ('predicate', 'shared_state', 'legality', 'temporal',
                 'terminal'):
        assert g.edge_count(kind) > 0, f'{kind} edges absent'


def test_boulder_cooldown_is_connected_across_the_turn_boundary():
    """Hand-checkable: the boulder rule writes a cooldown and reads it
    back on a later turn. The temporal edges must exist, or the boulder
    rule cannot be identified as one unit."""
    g = build()
    writers = {n.node_id for n in g.nodes
               if 'boulder_cooldown' in n.fluents_written}
    readers = {n.node_id for n in g.nodes
               if 'boulder_cooldown' in n.fluents_read}
    assert writers and readers
    crossing = [(a, b) for (a, b) in g.edges['temporal']
                if a in writers and b in readers]
    assert crossing, 'no temporal edge carries the boulder cooldown'


def test_jump_capture_permission_is_linked_to_its_effects():
    g = build()
    legal = {n.node_id for n in g.nodes if n.action_type == 'jump_capture'}
    effects = {n.node_id for n in g.nodes if 'jump_capture' in n.actions_read}
    assert legal and effects
    linked = [e for e in g.edges['legality']
              if (e[0] in legal and e[1] in effects)
              or (e[1] in legal and e[0] in effects)]
    assert len(linked) == len(legal) * len(effects)


def test_shared_state_edges_are_rule_signatures_not_infrastructure():
    """The surviving shared-state fluents should be rule signatures —
    captured_friendly (transformation eligibility), boulder_cooldown,
    tiny_endgame_active, reactive_armed — not board infrastructure."""
    g = build()
    assert 0 < g.edge_count('shared_state') < 200, (
        'shared_state edge count suggests infrastructure fluents leaked in')
