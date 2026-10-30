"""The fast reasoner answers exactly what the resolver answers (#290).

`ggp.fast` replaces top-down resolution with compiled bottom-up
evaluation, so it reaches its answers a completely different way. The
resolver stays as the reference: on seeded random play of every test
game and of Royal Chess, both are asked for every role's legal moves,
terminal, goals, the next state and every role's percepts, and must
agree on each.
"""

import os
import random
import sys
import time

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(ROOT, 'src'))

from ggp.game import GGPGame  # noqa: E402
from ggp import fast  # noqa: E402

TESTGAMES = os.path.join(ROOT, 'lgref', 'identify', 'testgames')
ROYAL = os.path.join(ROOT, 'docs', 'gdl', 'integrated.gdl')
SMALL = ['nim', 'corridor', 'tictactoe', 'montyhall', 'kriegtictactoe',
         'kuhnpoker']


def _same_play(path, games, plies, seed):
    """Play both reasoners in lockstep; return the plies compared."""
    rng = random.Random(seed)
    compared = 0
    for _ in range(games):
        new = GGPGame.from_file(path)
        old = GGPGame.from_file(path, reasoner='resolver')
        assert new.reasoner == 'fast' and old.reasoner == 'resolver'
        for _ in range(plies):
            legal = {}
            for role in old.roles:
                want = old.legal_moves(role)
                got = new.legal_moves(role)
                assert sorted(map(repr, got)) == sorted(map(repr, want)), role
                legal[role] = want
            assert new.is_terminal() == old.is_terminal()
            for role in old.roles:
                assert new.goal(role) == old.goal(role), role
            if old.is_terminal() or not all(legal.values()):
                break
            moves = {role: rng.choice(legal[role]) for role in old.roles}
            for role in old.roles:
                assert new.percepts(role, moves) == old.percepts(role, moves)
            new.step(moves)
            old.step(moves)
            assert new.state == old.state
            compared += 1
    return compared


@pytest.mark.parametrize('name', SMALL)
def test_fast_equals_resolver_on_every_test_game(name):
    path = os.path.join(TESTGAMES, name + '.gdl')
    assert _same_play(path, games=6, plies=40, seed=290) > 6


def test_fast_equals_resolver_on_royal_chess():
    """Royal Chess's GDL is written top-down: 37 relations, `legal`
    among them, have head variables only a caller binds, so it is the
    hard case for a bottom-up engine. (Both reasoners end one of these
    games at ply 2, after Black's boulder move, scoring it 0-0: that is
    the description's own reading, which they agree on.)"""
    assert _same_play(ROYAL, games=3, plies=6, seed=290) >= 10


#: Two things no test game needs, written so they are exercised: a
#: recursive relation computed bottom-up (`reach`, iterated to a fixed
#: point), and an on-demand relation that calls itself (`tie`, whose
#: second rule re-enters with its arguments swapped, which the cycle
#: guard must stop). The recursion is RIGHT recursion over an acyclic
#: graph, which is where the resolver is complete; see the next test.
RECURSIVE = """
role(a)
role(b)
init(at(n1))
init(control(a))
edge(n1,n2)
edge(n2,n3)
edge(n3,n4)
edge(n2,n4)
edge(n4,n5)
reach(X,Y) :- edge(X,Y)
reach(X,Z) :- edge(X,Y) & reach(Y,Z)
tie(X,Y) :- edge(X,Z)
tie(X,Y) :- tie(Y,X)
legal(P,go(Y)) :- true(control(P)) & true(at(X)) & reach(X,Y) & tie(Y,X)
legal(a,noop) :- true(control(b))
legal(b,noop) :- true(control(a))
next(at(Y)) :- does(P,go(Y))
next(control(a)) :- true(control(b))
next(control(b)) :- true(control(a))
terminal :- true(at(n5))
goal(a,100) :- true(at(n5)) & true(control(b))
goal(a,0) :- true(at(n5)) & true(control(a))
goal(b,100) :- true(at(n5)) & true(control(a))
goal(b,0) :- true(at(n5)) & true(control(b))
"""


def test_recursion_and_self_calls_match_the_resolver(tmp_path):
    path = tmp_path / 'recursive.gdl'
    path.write_text(RECURSIVE)
    program = fast.compile_kb(GGPGame(RECURSIVE)._rules_kb)
    assert 'tie' in program.demand and 'reach' not in program.demand
    game = GGPGame(RECURSIVE)
    assert sorted(game.legal_moves('a')) == [
        ('go', 'n2'), ('go', 'n3'), ('go', 'n4'), ('go', 'n5')]
    assert _same_play(str(path), games=8, plies=12, seed=1) >= 8


def test_left_recursion_through_a_cycle_gets_the_whole_closure():
    """Where the two reasoners DIFFER, and the fast one is right.

    The resolver's cycle guard treats `reach(n1, ?y)` and its recursive
    call `reach(n1, ?y2)` as the same goal and cuts the second, so under
    left recursion it finds only one-step answers. GDL's semantics is the
    least model, which here is everything reachable from n1."""
    text = RECURSIVE.replace(
        'reach(X,Z) :- edge(X,Y) & reach(Y,Z)',
        'reach(X,Z) :- reach(X,Y) & edge(Y,Z)').replace(
        'edge(n2,n4)', 'edge(n4,n2)')
    fast_moves = GGPGame(text).legal_moves('a')
    assert fast_moves == [('go', 'n2'), ('go', 'n3'), ('go', 'n4'),
                          ('go', 'n5')]
    old_moves = GGPGame(text, reasoner='resolver').legal_moves('a')
    assert old_moves == [('go', 'n2')]


def test_royal_chess_rules_that_cannot_run_forward_are_found():
    program = fast.compile_kb(GGPGame.from_file(ROYAL)._rules_kb)
    assert {'legal', 'same_rank', 'rook_step', 'empty'} <= program.demand
    assert 'true' not in program.demand


def test_legal_moves_are_sorted_so_every_process_agrees():
    game = GGPGame.from_file(os.path.join(TESTGAMES, 'tictactoe.gdl'))
    moves = game.legal_moves('xplayer')
    assert moves == sorted(moves, key=repr) and len(moves) == 9


def test_gdl_iii_keeps_the_resolver():
    """`knows` is defined over play histories, which only the epistemic
    model answers."""
    game = GGPGame.from_file(os.path.join(TESTGAMES, 'muddychildren.gdl'))
    assert game.reasoner == 'resolver'


def test_a_description_the_compiler_refuses_keeps_the_resolver():
    text = """
    role(a)
    init(on)
    p :- ~q
    q :- ~p
    legal(a, go) :- true(on)
    next(on) :- p
    terminal :- ~true(on)
    goal(a, 100) :- p
    """
    with pytest.raises(fast.Unsupported):
        fast.compile_kb(GGPGame(text, reasoner='resolver')._rules_kb)
    game = GGPGame(text)
    assert game.reasoner == 'resolver'
    assert game.legal_moves('a') == ['go']


def test_the_environment_can_ask_for_the_resolver(monkeypatch):
    """So a seeded result recorded before #290 re-runs exactly."""
    monkeypatch.setenv('GGP_REASONER', 'resolver')
    assert GGPGame.from_file(
        os.path.join(TESTGAMES, 'nim.gdl')).reasoner == 'resolver'
    monkeypatch.delenv('GGP_REASONER')
    assert GGPGame.from_file(
        os.path.join(TESTGAMES, 'nim.gdl')).reasoner == 'fast'


def test_a_game_pickles_and_its_copy_shares_the_program():
    """Searches copy games by pickling them (`fastcopy`), and a compiled
    rule is a closure, which does not pickle."""
    import copy
    import pickle
    game = GGPGame.from_file(os.path.join(TESTGAMES, 'tictactoe.gdl'))
    game.step({'xplayer': ('mark', '1', '1'), 'oplayer': 'noop'})
    for clone in (pickle.loads(pickle.dumps(game)), copy.deepcopy(game)):
        assert clone._program is game._program
        assert clone.state == game.state and clone.state is not game.state
        assert clone.legal_moves('oplayer') == game.legal_moves('oplayer')


def test_unknown_reasoner_is_refused():
    with pytest.raises(ValueError):
        GGPGame.from_file(os.path.join(TESTGAMES, 'nim.gdl'),
                          reasoner='propnet')


def test_fast_is_much_faster_on_royal_chess():
    """Relative, so it does not depend on the machine: on the same
    states the fast reasoner must be at least 10x quicker. Measured at
    ~100x (13 ms against ~1,400 ms a state; the hand-written engine
    takes ~1 ms)."""
    new = GGPGame.from_file(ROYAL)
    old = GGPGame.from_file(ROYAL, reasoner='resolver')
    rng = random.Random(7)
    states = []
    for _ in range(3):
        states.append(set(old.state))
        moves = {r: rng.choice(old.legal_moves(r)) for r in old.roles}
        old.step(moves)
    new.legal_moves('white')            # compile and warm the static model

    def timed(game):
        start = time.perf_counter()
        for state in states:
            game.state = set(state)
            if game._program is not None:
                game._program.models.clear()
            for role in game.roles:
                game.legal_moves(role)
            game.is_terminal()
        return time.perf_counter() - start

    old_seconds = timed(old)
    new_seconds = timed(new)
    assert new_seconds * 10 < old_seconds, (new_seconds, old_seconds)
