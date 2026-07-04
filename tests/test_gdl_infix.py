"""Tests for src/ggp/infix.py — the prefix-KIF → infix-HRF GDL
converter and the infix reader.

Background (2026-06-14 user report): our GDL fragments were written
in the classic KIF prefix notation used by GGP-Base / games.ggp.org:

    (<= (legal ?p (mark ?m ?n)) (true (cell ?m ?n b)))

Stanford's CURRENT GGP infrastructure (ggp.stanford.edu, Epilog)
uses the infix HRF (human-readable format) syntax instead:

    legal(P,mark(M,N)) :- true(cell(M,N,b))

Syntax mapping (emit direction):
  - variables  `?ff`           -> `FF` (uppercase, Prolog convention)
  - compound   `(f a ?b)`      -> `f(a,B)`
  - 0-ary      `(flag)`        -> `flag`
  - rule       `(<= h b1 b2)`  -> `h :- b1 & b2`
  - negation   `(not X)`       -> `~X`
  - distinct   kept as builtin -> `distinct(X,Y)`
  - `(or A B)` in a body       -> EXPANDED into one rule per branch
                                  (cartesian product for multiple ors)
  - `(= ?x c)` in a body       -> resolved by SUBSTITUTION (bind ?x:=c
                                  in the whole rule, drop the conjunct)
  - comments                   -> `%` line comments

The or-expansion and =-substitution keep the emitted file within
plain HRF (no disjunction operator needed) and are semantics-
preserving in standard Datalog.

The reader (parse_infix) maps the infix text back to the SAME
internal tuple representation our KB/Resolver already consume
(variables as '?'-prefixed lowercase strings, rules as
('<=', head, *body), negation as ('not', X)) — so GGPGame can load
either dialect.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.parser import parse
from ggp.infix import (
    term_to_infix, forms_to_infix_lines, parse_infix, convert_text)


GDL_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl')
INTEGRATED_PREFIX = os.path.join(GDL_DIR, 'integrated.gdl')
INTEGRATED_INFIX = os.path.join(GDL_DIR, 'integrated_infix.gdl')


# ---- term rendering -------------------------------------------------------

def test_atom_renders_as_is():
    assert term_to_infix('white') == 'white'
    assert term_to_infix('8') == '8'


def test_variable_renders_uppercase():
    assert term_to_infix('?ff') == 'FF'
    assert term_to_infix('?new_form') == 'NEW_FORM'


def test_compound_renders_with_parens_and_commas():
    assert term_to_infix(('cell', 'a', '1', 'white', 'king')) == \
        'cell(a,1,white,king)'


def test_nested_compound():
    assert term_to_infix(('true', ('control', '?p'))) == \
        'true(control(P))'


def test_zero_ary_tuple_renders_bare():
    assert term_to_infix(('boulder_first_move',)) == 'boulder_first_move'


# ---- form (fact / rule) rendering -----------------------------------------

def test_fact_renders_one_line():
    lines = forms_to_infix_lines([('role', 'white')])
    assert lines == ['role(white)']


def test_init_fact_renders_nested():
    lines = forms_to_infix_lines([('init', ('control', 'white'))])
    assert lines == ['init(control(white))']


def test_simple_rule_renders_with_neck_and_ampersands():
    form = ('<=', ('opponent', 'white', 'black'))
    assert forms_to_infix_lines([form]) == ['opponent(white,black)']
    form2 = ('<=', ('legal', '?p', 'noop'),
             ('true', ('control', '?o')),
             ('opponent', '?o', '?p'))
    assert forms_to_infix_lines([form2]) == [
        'legal(P,noop) :- true(control(O)) & opponent(O,P)']


def test_negation_renders_tilde():
    form = ('<=', ('empty', '?f', '?r'),
            ('not', ('occupied', '?f', '?r')))
    assert forms_to_infix_lines([form]) == [
        'empty(F,R) :- ~occupied(F,R)']


def test_terminal_bare_atom_head():
    form = ('<=', 'terminal', ('lost', 'white'))
    assert forms_to_infix_lines([form]) == ['terminal :- lost(white)']


# ---- or-expansion ---------------------------------------------------------

def test_or_in_body_expands_to_two_rules():
    form = ('<=', ('king_step', '?a', '?b'),
            ('adj', '?a', '?b'),
            ('or', ('foo', '?a'), ('bar', '?b')))
    lines = forms_to_infix_lines([form])
    assert lines == [
        'king_step(A,B) :- adj(A,B) & foo(A)',
        'king_step(A,B) :- adj(A,B) & bar(B)',
    ]


def test_two_ors_expand_cartesian():
    form = ('<=', ('h',),
            ('or', ('a',), ('b',)),
            ('or', ('c',), ('d',)))
    lines = forms_to_infix_lines([form])
    assert len(lines) == 4


# ---- =-substitution -------------------------------------------------------

def test_equality_conjunct_substitutes_constant():
    form = ('<=', ('legal', '?p', ('move', '?piece')),
            ('own', '?p', '?piece'),
            ('=', '?piece', 'king'))
    lines = forms_to_infix_lines([form])
    assert lines == ['legal(P,move(king)) :- own(P,king)']


def test_or_of_equalities_expands_and_substitutes():
    """The real pattern from step 1's king/queen shared rule."""
    form = ('<=', ('legal', '?p', ('move', '?piece', '?f')),
            ('cell', '?f', '?p', '?piece'),
            ('or', ('=', '?piece', 'king'), ('=', '?piece', 'queen')))
    lines = forms_to_infix_lines([form])
    assert lines == [
        'legal(P,move(king,F)) :- cell(F,P,king)',
        'legal(P,move(queen,F)) :- cell(F,P,queen)',
    ]


# ---- infix reader ----------------------------------------------------------

def test_parse_infix_fact():
    assert parse_infix('role(white)') == [('role', 'white')]


def test_parse_infix_rule():
    forms = parse_infix('legal(P,noop) :- true(control(O)) & opponent(O,P)')
    assert forms == [
        ('<=', ('legal', '?p', 'noop'),
         ('true', ('control', '?o')),
         ('opponent', '?o', '?p'))]


def test_parse_infix_negation():
    forms = parse_infix('empty(F,R) :- ~occupied(F,R)')
    assert forms == [
        ('<=', ('empty', '?f', '?r'),
         ('not', ('occupied', '?f', '?r')))]


def test_parse_infix_bare_terminal_head():
    forms = parse_infix('terminal :- lost(white)')
    assert forms == [('<=', 'terminal', ('lost', 'white'))]


def test_parse_infix_skips_percent_comments_and_blanks():
    text = '% header comment\n\nrole(white)   % trailing\nrole(black)\n'
    assert parse_infix(text) == [('role', 'white'), ('role', 'black')]


def test_parse_infix_fact_with_variables():
    """Universally-quantified facts like same_file(X,X)."""
    forms = parse_infix('same_file(X,X)')
    assert forms == [('same_file', '?x', '?x')]


# ---- round trip -------------------------------------------------------------

def test_round_trip_small_program():
    prefix_text = '''
    (role white)
    (role black)
    (init (control white))
    (<= (legal ?p noop) (true (control ?o)) (opponent ?o ?p))
    (<= (empty ?f ?r) (not (occupied ?f ?r)))
    '''
    infix_text = convert_text(prefix_text)
    round_tripped = parse_infix(infix_text)
    assert round_tripped == parse(prefix_text)


# ---- integration: full integrated.gdl conversion + GGP parity --------------

def test_convert_full_integrated_gdl():
    """The whole prefix integrated.gdl must convert without error."""
    with open(INTEGRATED_PREFIX) as f:
        text = f.read()
    infix_text = convert_text(text)
    assert ':-' in infix_text
    # No prefix-rule marker should survive.
    assert '(<=' not in infix_text
    # Must re-parse cleanly.
    forms = parse_infix(infix_text)
    assert len(forms) > 300


def test_generated_infix_file_exists_and_parses():
    """The committed integrated_infix.gdl artifact parses."""
    assert os.path.exists(INTEGRATED_INFIX), (
        'run docs/gdl/build_integrated_infix.py to generate the '
        'infix artifact')
    with open(INTEGRATED_INFIX) as f:
        forms = parse_infix(f.read())
    assert len(forms) > 300


def test_ggp_legal_move_parity_between_dialects():
    """THE key correctness check: GGPGame loaded from the infix file
    must produce the exact same legal-move set at init as the prefix
    file (71 moves for white, noop for black)."""
    from ggp.game import GGPGame
    g_prefix = GGPGame.from_file(INTEGRATED_PREFIX)
    g_infix = GGPGame.from_file(INTEGRATED_INFIX)
    prefix_moves = set(map(str, g_prefix.legal_moves('white')))
    infix_moves = set(map(str, g_infix.legal_moves('white')))
    assert prefix_moves == infix_moves, (
        f'dialect mismatch: prefix-only='
        f'{sorted(prefix_moves - infix_moves)[:5]}, '
        f'infix-only={sorted(infix_moves - prefix_moves)[:5]}')
    assert len(infix_moves) == 71
    assert g_infix.legal_moves('black') == ['noop']
