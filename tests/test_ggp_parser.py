"""Tests for the GGP S-expression / GDL parser
(`src/ggp/parser.py`).

The parser turns a GDL text into a sequence of nested tuples
(atoms as strings, lists as Python tuples). Variables start with
'?'; everything else is an atom or a list.

This is the foundation of the GGP — every higher layer (KB,
resolver, engine) consumes the parser's output.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from ggp.parser import parse, is_variable, strip_comments, tokenize


def test_parse_single_fact():
    forms = parse('(role white)')
    assert forms == [('role', 'white')]


def test_parse_multiple_facts():
    forms = parse('(role white)\n(role black)\n(init (control white))')
    assert forms == [
        ('role', 'white'),
        ('role', 'black'),
        ('init', ('control', 'white')),
    ]


def test_parse_rule():
    forms = parse('(<= (opponent white black))')
    assert forms == [('<=', ('opponent', 'white', 'black'))]


def test_parse_rule_with_body():
    text = '''
    (<= (legal ?p noop)
        (true (control ?other))
        (opponent ?other ?p))
    '''
    forms = parse(text)
    assert forms == [
        ('<=',
         ('legal', '?p', 'noop'),
         ('true', ('control', '?other')),
         ('opponent', '?other', '?p')),
    ]


def test_parse_strips_line_comments():
    text = '''
    ; this is a comment
    (role white)  ; inline comment
    (role black)
    '''
    forms = parse(text)
    assert forms == [('role', 'white'), ('role', 'black')]


def test_is_variable():
    assert is_variable('?x')
    assert is_variable('?player')
    assert is_variable('?ff')
    assert not is_variable('white')
    assert not is_variable('legal')
    assert not is_variable('')


def test_tokenize_basic():
    toks = tokenize('(role white)')
    assert toks == ['(', 'role', 'white', ')']


def test_tokenize_handles_extra_whitespace():
    toks = tokenize('  (role   white  )  ')
    assert toks == ['(', 'role', 'white', ')']


def test_strip_comments_preserves_code():
    text = 'foo  ; comment\nbar'
    assert strip_comments(text) == 'foo  \nbar'


def test_parse_unbalanced_paren_raises():
    with pytest.raises(ValueError):
        parse('(role white')


def test_parse_unexpected_close_raises():
    with pytest.raises(ValueError):
        parse(')')


def test_parse_handles_empty_input():
    assert parse('') == []
    assert parse('   \n\n   ') == []
    assert parse('; just a comment\n') == []


def test_parse_integrated_gdl_file():
    """The full integrated GDL must parse without errors — proves
    we can ingest the canonical artifact for reasoner work."""
    path = os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'gdl',
        'integrated.gdl')
    assert os.path.exists(path), 'integrated.gdl missing'
    with open(path) as f:
        text = f.read()
    forms = parse(text)
    assert len(forms) > 100, (
        f'expected hundreds of clauses; got {len(forms)}')


def test_parse_step1_file():
    path = os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'gdl',
        'step1_kings_queens.gdl')
    with open(path) as f:
        text = f.read()
    forms = parse(text)
    # Should have role declarations + init facts + rules.
    role_forms = [f for f in forms
                  if isinstance(f, tuple) and f and f[0] == 'role']
    assert len(role_forms) == 2
