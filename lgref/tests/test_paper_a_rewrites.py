"""Behaviour-preserving rewrites for Experiment 4 (Paper A).

Each rewrite must (1) change the writing, (2) keep the game -- checked
on every reachable state of the small dev games -- and (3) carry a
provenance map that covers every original statement. `verify` itself
must catch a rewrite that does change the game.
"""

import pytest

import lgref  # noqa: F401
from lgref.bench import rewrites as R
from lgref.bench import wellformed
from lgref.bench.catalog import game_path

SMALL = ('tictactoe', 'nim', 'corridor')


def _text(game):
    with open(game_path(game)) as handle:
        return handle.read()


def _forms(game):
    from ggp.infix import parse_infix
    return parse_infix(_text(game))


@pytest.mark.parametrize('game', SMALL)
@pytest.mark.parametrize('name', R.REWRITES)
def test_rewrite_preserves_behaviour_on_every_reachable_state(game, name):
    text = _text(game)
    states, mode = wellformed.walk(text, exhaustive=True, limit=10000)
    assert mode == 'exhaustive'
    assert R.verify(name, text, states) == []


@pytest.mark.parametrize('game', ('breakthrough5', 'othello4'))
@pytest.mark.parametrize('name', R.REWRITES)
def test_rewrite_preserves_behaviour_on_the_pilots(game, name):
    text = _text(game)
    states, _mode = wellformed.walk(text, games=15, seed=9)
    assert R.verify(name, text, states) == []


@pytest.mark.parametrize('name', R.REWRITES)
def test_rewrite_changes_the_writing(name):
    forms = _forms('othello4')
    new, _prov = R.rewrite(name, forms)
    assert new != forms


@pytest.mark.parametrize('name', R.REWRITES)
def test_provenance_covers_every_original_statement(name):
    forms = _forms('breakthrough5')
    new, provenance = R.rewrite(name, forms)
    assert set(provenance) == set(range(len(new)))
    covered = set()
    for sources in provenance.values():
        covered |= sources
    assert covered == set(range(len(forms)))


def test_count_changing_rewrites_change_the_count():
    forms = _forms('othello4')
    for name in ('extract', 'inline', 'duplicate'):
        new, _prov = R.rewrite(name, forms)
        assert len(new) != len(forms), name


def test_verify_catches_a_rewrite_that_changes_the_game(monkeypatch):
    """Drop one statement while claiming to rewrite: verify must say so."""
    text = _text('tictactoe')
    original = R.FUNCTIONS['permute']

    def broken(forms, seed=0):
        new, prov = original(forms, seed)
        return new[:-2] + new[-1:], prov

    monkeypatch.setitem(R.FUNCTIONS, 'permute', broken)
    states, _ = wellformed.walk(text, games=10, seed=0)
    assert R.verify('permute', text, states)


def test_helpers_exclude_state_and_keywords():
    names = R.helpers(_forms('breakthrough5'))
    assert 'cell' not in names and 'legal' not in names
    assert 'capture' in names and 'forward' in names


def test_verify_sees_percepts():
    """A rewrite that drops Monty Hall's `sees` rule changes what the
    candidate is told and nothing else; verify must notice."""
    text = _text('montyhall')
    original = R.FUNCTIONS['permute']

    def drop_sees(forms, seed=0):
        new, prov = original(forms, seed)
        keep = [i for i, f in enumerate(new)
                if not (isinstance(f, tuple) and f[0] == '<='
                        and f[1][0] == 'sees')]
        return [new[i] for i in keep], {j: prov[i]
                                        for j, i in enumerate(keep)}

    states, _ = wellformed.walk(text, games=20, seed=0)
    import pytest
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(R.FUNCTIONS, 'permute', drop_sees)
        found = R.verify('permute', text, states)
        assert any('percepts' in p for p in found)
    assert R.verify('permute', text, states) == []


def test_permute_leaves_an_action_named_like_a_helper_alone():
    """#386: checkers' helper `jump/5` shares its name with the action
    `jump/4`. Rotating every term named `jump` rotated the action inside
    `legal` and `does`, so the rewritten game had different moves."""
    from ggp.infix import parse_infix
    text = '\n'.join([
        'role(a)', 'init(at(1))', 'init(control(a))',
        'jump(P,X,Y) :- true(at(X)) & succ(X,Y) & role(P)',
        'succ(1,2)', 'succ(2,3)',
        'legal(P,jump(X,Y)) :- true(control(P)) & jump(P,X,Y)',
        'next(at(Y)) :- does(P,jump(X,Y))',
        'next(control(a)) :- true(control(a))',
        'terminal :- true(at(3))', 'goal(a,100) :- true(at(3))'])
    new, _prov = R.rewrite('permute', parse_infix(text))
    does = [g for f in new if f[0] == '<=' for g in f[2:]
            if g[0] == 'does']
    legal = [f[1] for f in new if f[0] == '<=' and f[1][0] == 'legal']
    actions = does + legal
    assert all(t[2] == ('jump', '?x', '?y') for t in actions), actions
    states, _ = wellformed.walk(text, exhaustive=True)
    assert R.verify('permute', text, states) == []


@pytest.mark.parametrize('game', ['checkers_4x4', 'foxgeese_mini',
                                  'kalah_mini', 'dotsboxes_2x2', 'hex_3x3',
                                  'chomp_3x3', 'synth_independent',
                                  'synth_shared', 'synth_redundant',
                                  'skirmish'])
@pytest.mark.parametrize('name', R.REWRITES)
def test_rewrite_preserves_behaviour_on_the_test_games(game, name):
    """#386: verify had only ever run on the development games, where no
    helper shares an action's name."""
    text = _text(game)
    states, _mode = wellformed.walk(text, games=8, seed=9)
    assert R.verify(name, text, states) == []
