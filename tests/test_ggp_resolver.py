"""Tests for the GGP knowledge base + resolver (`src/ggp/kb.py` +
`src/ggp/resolver.py`).

The resolver does backward-chaining with variable unification +
negation-as-failure + the GDL builtins (or / and / distinct / not).
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from ggp.parser import parse
from ggp.kb import KnowledgeBase
from ggp.resolver import Resolver


def _kb(text):
    kb = KnowledgeBase()
    for form in parse(text):
        kb.add_clause(form)
    return kb


def test_kb_distinguishes_facts_from_rules():
    kb = _kb('(role white)\n(<= (opponent white black))')
    assert kb.fact_count() == 1
    assert kb.rule_count() == 1


def test_ground_fact_query_succeeds():
    kb = _kb('(role white)\n(role black)')
    r = Resolver(kb)
    results = list(r.query(('role', 'white')))
    assert len(results) == 1     # one binding (the empty substitution)


def test_variable_query_returns_bindings():
    kb = _kb('(role white)\n(role black)')
    r = Resolver(kb)
    results = list(r.query(('role', '?x')))
    bindings = sorted(b['?x'] for b in results)
    assert bindings == ['black', 'white']


def test_rule_with_one_fact_body():
    kb = _kb('''
        (role white)
        (role black)
        (<= (opponent white black))
        (<= (opponent black white))
    ''')
    r = Resolver(kb)
    results = sorted(
        (b['?a'], b['?b'])
        for b in r.query(('opponent', '?a', '?b')))
    assert results == [('black', 'white'), ('white', 'black')]


def test_recursive_rule():
    """sweep_path or similar — recursion with a base case + a
    recursive case. We use a simple ancestor example."""
    kb = _kb('''
        (parent alice bob)
        (parent bob carol)
        (parent carol dave)
        (<= (ancestor ?x ?y) (parent ?x ?y))
        (<= (ancestor ?x ?y) (parent ?x ?z) (ancestor ?z ?y))
    ''')
    r = Resolver(kb)
    # alice's descendants
    results = sorted(b['?y'] for b in r.query(('ancestor', 'alice', '?y')))
    assert results == ['bob', 'carol', 'dave']


def test_negation_as_failure():
    kb = _kb('''
        (member a)
        (member b)
        (<= (not_member ?x) (not (member ?x)))
    ''')
    r = Resolver(kb)
    # 'c' is not a member, so not_member(c) holds
    assert any(True for _ in r.query(('not_member', 'c')))
    # 'a' IS a member, so not_member(a) does NOT hold
    assert not any(True for _ in r.query(('not_member', 'a')))


def test_distinct_builtin():
    kb = _kb('''
        (color red)
        (color blue)
        (<= (different ?x ?y) (color ?x) (color ?y) (distinct ?x ?y))
    ''')
    r = Resolver(kb)
    results = sorted(
        (b['?x'], b['?y'])
        for b in r.query(('different', '?x', '?y')))
    assert results == [('blue', 'red'), ('red', 'blue')]


def test_or_in_rule_body():
    kb = _kb('''
        (red apple)
        (blue sky)
        (<= (colored ?x) (or (red ?x) (blue ?x)))
    ''')
    r = Resolver(kb)
    results = sorted(b['?x'] for b in r.query(('colored', '?x')))
    assert results == ['apple', 'sky']


def test_query_with_no_results_returns_empty():
    kb = _kb('(role white)')
    r = Resolver(kb)
    assert list(r.query(('role', 'green'))) == []
    assert list(r.query(('nonexistent_predicate', '?x'))) == []


def test_compound_term_in_fact():
    kb = _kb('(init (control white))')
    r = Resolver(kb)
    # Query the compound (control X) inside init.
    results = list(r.query(('init', ('control', '?p'))))
    assert len(results) == 1
    assert results[0]['?p'] == 'white'


def test_step1_role_query():
    """Load step1_kings_queens.gdl and query roles."""
    path = os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'gdl',
        'step1_kings_queens.gdl')
    with open(path) as f:
        text = f.read()
    kb = KnowledgeBase()
    for form in parse(text):
        kb.add_clause(form)
    r = Resolver(kb)
    results = sorted(b['?r'] for b in r.query(('role', '?r')))
    assert results == ['black', 'white']


def test_step1_init_cell_query():
    """The 4 init cell facts for step 1 (W K g1, W Q b1, B K b8,
    B Q g8) should all be queriable."""
    path = os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'gdl',
        'step1_kings_queens.gdl')
    with open(path) as f:
        text = f.read()
    kb = KnowledgeBase()
    for form in parse(text):
        kb.add_clause(form)
    r = Resolver(kb)
    results = sorted(
        (b['?f'], b['?r'], b['?c'], b['?p'])
        for b in r.query(('init', ('cell', '?f', '?r', '?c', '?p'))))
    assert ('g', '1', 'white', 'king') in results
    assert ('b', '1', 'white', 'queen') in results
    assert ('b', '8', 'black', 'king') in results
    assert ('g', '8', 'black', 'queen') in results
    assert len(results) == 4
