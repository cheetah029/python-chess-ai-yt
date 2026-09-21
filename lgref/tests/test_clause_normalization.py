"""Clause normalisation, tested on hand-written GDL.

Phase 1 identifies rules from clause structure, so a mis-typed clause
distorts every cluster downstream — and silently, because a cluster is
plausible-looking whatever it contains. These tests use small hand-written
GDL where the correct typing is obvious by inspection.

Two typings matter most, both established by the GDL audit:

  - a DERIVED predicate and a FLUENT are different node types, with
    different dependency semantics. Conflating them was a real defect
    (#177 B4);
  - the `_except` family is a mechanically derived encoding workaround and
    must collapse onto its base, or rules that use it appear twice their
    true size.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ggp.parser import parse
from lgref.identify import clauses as C


def _nodes(text):
    return C.normalize(parse(text))


def _one(text):
    got = _nodes(text)
    assert len(got) == 1, got
    return got[0]


# ---- head typing ---------------------------------------------------------

def test_derived_predicate_is_typed_derived():
    node = _one('(<= (pawnless) (not (any_pawn)))')
    assert node.head_predicate == 'pawnless'
    assert node.head_kind == 'derived'


def test_next_rule_is_typed_as_a_fluent_write():
    """`(next (X ...))` WRITES state. Its dependency on a clause that
    later READS X is temporal, not immediate — a different edge type."""
    node = _one('(<= (next (boulder_cooldown 0)) (true (boulder_at intersection)))')
    assert node.head_kind == 'fluent_write'
    assert node.head_predicate == 'boulder_cooldown'
    assert 'boulder_cooldown' in node.fluents_written
    assert 'boulder_at' in node.fluents_read


def test_init_is_typed_separately_from_next():
    """init seeds a fluent once; next carries it turn to turn. Both write,
    but only next participates in temporal cycles."""
    node = _one('(init (boulder_at intersection))')
    assert node.head_kind == 'fluent_init'
    assert 'boulder_at' in node.fluents_written


def test_legal_rule_records_its_action_type():
    node = _one('(<= (legal ?p (move knight ?a ?b ?c ?d)) (true (control ?p)))')
    assert node.head_kind == 'legal'
    assert node.action_type == 'move'
    assert 'control' in node.fluents_read


def test_jump_capture_is_recognised_as_its_own_action():
    node = _one('(<= (legal ?p (jump_capture ?a ?b ?c ?d ?e ?f)) (true (control ?p)))')
    assert node.action_type == 'jump_capture'


def test_facts_are_typed_as_facts():
    assert _one('(role white)').head_kind == 'role'
    assert _one('(<= (file_adj a b))').head_kind == 'derived'


# ---- fluent vs derived, the distinction that matters --------------------

def test_true_goal_is_a_fluent_read_not_a_body_predicate():
    """`(true (X))` reads state; a bare `(X)` calls a derived predicate.
    Recording both the same way would erase the temporal edge."""
    node = _one('(<= (foo) (true (bar)) (baz))')
    assert node.fluents_read == {'bar'}
    assert node.body_predicates == {'baz'}


def test_does_goal_is_recorded_as_an_action_read():
    node = _one('(<= (next (cell a 1 white king)) (does ?m (move king ?a ?b a 1)))')
    assert 'move' in node.actions_read


# ---- the _except family --------------------------------------------------

def test_except_predicates_collapse_onto_their_base():
    """`occupied_except` is `occupied` with a square threaded through —
    an encoding workaround for GDL's inability to evaluate in a
    hypothetical state, not a separate game concept."""
    assert C.canonical_predicate('occupied_except') == 'occupied'
    assert C.canonical_predicate('sweep_path_except') == 'sweep_path'
    assert C.canonical_predicate('occupied') == 'occupied'


def test_except_collapse_applies_to_heads_and_bodies():
    node = _one('(<= (empty_except ?f ?r ?x ?y) (not (occupied_except ?f ?r ?x ?y)))')
    assert node.head_predicate == 'empty'
    assert 'occupied' in node.body_predicates
    assert not any(p.endswith('_except') for p in node.body_predicates)


def test_a_predicate_merely_ending_in_except_like_text_is_untouched():
    """Guard against over-eager stripping: only the exact suffix."""
    assert C.canonical_predicate('_except') == '_except'
    assert C.canonical_predicate('excepted') == 'excepted'


# ---- negation and terminal dependency -----------------------------------

def test_negated_goals_are_recorded():
    """Negation matters for identification: a clause that BLOCKS on a
    fluent relates to it differently from one that requires it."""
    node = _one('(<= (foo) (not (true (invulnerable ?f ?r))) (bar))')
    assert 'invulnerable' in node.negated_goals
    assert 'invulnerable' in node.fluents_read


def test_terminal_dependency_is_flagged_through_lost():
    node = _one('(<= (lost ?p) (true (control ?p)) (no_legal_after_tiny_filter ?p))')
    assert node.terminal_dependency is True


def test_unrelated_clause_is_not_flagged_terminal():
    node = _one('(<= (file_adj a b))')
    assert node.terminal_dependency is False


# ---- piece tagging -------------------------------------------------------

def test_piece_types_are_collected_from_anywhere_in_the_clause():
    node = _one('(<= (legal ?p (move knight ?a ?b ?c ?d)) (true (cell ?a ?b ?p knight)))')
    assert node.piece_types == {'knight'}


def test_multiple_pieces_are_all_recorded():
    node = _one('(<= (foo) (true (cell ?a ?b ?p bishop)) (true (cell ?c ?d ?q rook)))')
    assert node.piece_types == {'bishop', 'rook'}


# ---- node identity -------------------------------------------------------

def test_node_ids_are_unique_across_clauses_of_one_predicate():
    """`legal` is defined by ~44 clauses that belong to DIFFERENT rules —
    one per piece. Ids must not collapse them."""
    nodes = _nodes('(<= (legal ?p (move knight ?a ?b ?c ?d)) (true (control ?p)))'
                   '(<= (legal ?p (move rook ?a ?b ?c ?d)) (true (control ?p)))')
    assert len({n.node_id for n in nodes}) == 2


# ---- the real ruleset ----------------------------------------------------

def test_the_integrated_ruleset_normalises():
    path = os.path.join(os.path.dirname(__file__), '..', '..',
                        'docs', 'gdl', 'integrated.gdl')
    nodes = C.load(path)
    assert len(nodes) > 400
    kinds = {n.head_kind for n in nodes}
    assert {'derived', 'fluent_write', 'legal', 'terminal', 'goal'} <= kinds
    assert not any((n.head_predicate or '').endswith('_except') for n in nodes)
    assert sum(1 for n in nodes if n.action_type) > 10
