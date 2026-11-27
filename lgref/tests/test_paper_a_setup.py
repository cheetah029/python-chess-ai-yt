"""Setup statements and LGREF's language verdict (Paper A, #358).

Pins that every development game has a provisional reference, that the
syntactic kinds are read correctly, and that a REAL RULE the definitive
indicator marks as language is reported by name rather than dropped --
the error the user asked to rule out.
"""

import lgref  # noqa: F401
from lgref.bench import setup
from lgref.bench.catalog import game_path, in_split
from lgref.identify.clauses import load


def test_every_dev_game_has_reference_kinds():
    for game in in_split('dev'):
        kinds = setup.reference_kinds(game, load(game_path(game)))
        assert kinds


def test_syntactic_kinds():
    nodes = load(game_path('breakthrough5'))
    kinds = setup.reference_kinds('breakthrough5', nodes)
    assert kinds['role#0'] == 'role'
    assert kinds['cell#54'] == 'init'
    assert kinds['terminal#48'] == 'outcome'
    assert kinds['forward#7'] == 'language'
    assert kinds['legal#30'] == 'rule'


def test_a_rule_marked_language_is_named():
    """Corridor's `inside` is a fixed table that IS the boundary rule.
    The definitive indicator calls it language; the report must say so
    statement by statement."""
    nodes = load(game_path('corridor'))
    ref = setup.reference_kinds('corridor', nodes)
    got = setup.score(setup.statement_verdict(nodes), ref, nodes)
    assert any(i.startswith('inside#') for i in got['rules_marked_language'])
    assert got['precision'] < 1.0


def test_report_covers_every_dev_game():
    text = setup.format_report(setup.report(in_split('dev')))
    for game in in_split('dev'):
        assert '| {} |'.format(game) in text


def test_reference_sheets_leave_language_out_of_every_rule():
    """The user's convention (#363): geometry and arithmetic are
    language, not rules, so no reference sheet puts them in a rule."""
    from lgref.bench.annotation import reference
    for game in in_split('dev'):
        nodes = load(game_path(game))
        kinds = setup.reference_kinds(game, nodes)
        membership = reference(game).membership()
        for node in nodes:
            if kinds[node.node_id] == 'language':
                assert not membership[node.index], node.node_id
