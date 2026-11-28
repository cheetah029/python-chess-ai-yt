"""The #400 post-freeze amendment: fixed tables as rules (decision 3c).

Pins the coded half of the cut on hand-built cases, that the verdict
file covers exactly the candidates of every benchmark game, that the
amendment changes only fixed-table statements, and that the frozen
reference is untouched.
"""

import pytest

import lgref  # noqa: F401
from lgref.bench import setup
from lgref.bench.catalog import game_path, in_split
from lgref.identify.clauses import load, normalize

GAMES = list(in_split('dev')) + list(in_split('test'))


def _toy(text):
    from ggp.infix import parse_infix
    return normalize(parse_infix(text))


def test_a_table_read_only_through_a_helper_is_a_candidate():
    nodes = _toy('\n'.join([
        'role(a)', 'win(5)', 'won(P) :- true(at(P,X)) & win(X)',
        'goal(a,100) :- won(a)', 'terminal :- won(a)',
        'init(at(a,1))', 'legal(a,noop)', 'next(at(a,X)) :- true(at(a,X))']))
    got = setup.fixed_table_candidates(nodes)
    assert got == {'win': ['goal', 'terminal']}


def test_a_table_that_shapes_only_next_is_a_candidate():
    nodes = _toy('\n'.join([
        'role(a)', 'ring(1,2)', 'ring(2,1)', 'init(at(1))', 'legal(a,go)',
        'next(at(Y)) :- true(at(X)) & ring(X,Y)', 'terminal :- true(at(2))',
        'goal(a,100) :- true(at(2))']))
    assert setup.fixed_table_candidates(nodes) == {'ring': ['next']}


def test_a_state_reading_helper_is_not_a_fixed_table():
    nodes = _toy('\n'.join([
        'role(a)', 'init(at(1))', 'here(X) :- true(at(X))',
        'legal(a,go) :- here(1)', 'next(at(2)) :- does(a,go)',
        'terminal :- here(2)', 'goal(a,100) :- here(2)']))
    assert setup.fixed_table_candidates(nodes) == {}


def test_an_unused_table_is_not_a_candidate():
    nodes = _toy('\n'.join([
        'role(a)', 'spare(1)', 'init(at(1))', 'legal(a,go)',
        'next(at(2)) :- does(a,go)', 'terminal :- true(at(2))',
        'goal(a,100) :- true(at(2))']))
    assert setup.fixed_table_candidates(nodes) == {}


@pytest.mark.parametrize('game', GAMES)
def test_verdicts_cover_exactly_the_candidates(game):
    assert setup.check_fixed_tables(game, load(game_path(game))) == []


def test_the_examples_the_user_named_are_rules():
    for game, table in (('corridor', 'inside'), ('breakthrough5',
                                                 'goalrow'),
                        ('kalah_mini', 'ahead')):
        assert setup.fixed_table_verdicts(game)[table]['verdict'] == 'rule'


@pytest.mark.parametrize('game', GAMES)
def test_the_amendment_changes_only_fixed_table_statements(game):
    nodes = load(game_path(game))
    frozen = setup.reference_kinds(game, nodes)
    amended = setup.amended_reference_kinds(game, nodes)
    tables = set(setup.fixed_table_candidates(nodes))
    for node in nodes:
        if frozen[node.node_id] != amended[node.node_id]:
            assert node.head_predicate in tables


def test_the_doc_lists_every_game(tmp_path):
    path = setup.write_fixed_tables_doc(GAMES, str(tmp_path / 'f.md'))
    text = open(path).read()
    for game in GAMES:
        assert '## {}'.format(game) in text
    assert 'MISSING' not in text
