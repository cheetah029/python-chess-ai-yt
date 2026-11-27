"""The nine fresh Paper A test games (#370), written after the freeze.

What is pinned here, and why:

  - each is infix HRF (the official dialect), loads, and is a
    well-formed game;
  - each agrees with an independent plain-Python implementation
    (`lgref.bench.simulators`) in every visited state -- every
    reachable state for the eight small games, seeded random games for
    fox and geese -- and that comparison FAILS on a mutated
    description, so it is a real check;
  - hand-built positions whose answers are known from the rules: a
    capture in Kalah, forced capture and promotion in checkers, a
    connection in Hex, a double box, a fox jump, the region a bite
    removes, the one-jump limit of the synthetic race;
  - the three synthetic files are exactly what `lgref.bench.synth`
    generates, and describe the same game.

Both implementations of each game were written by Claude, so agreement
rules out encoding slips, not a misreading of the rules both share.
"""

import pytest

import lgref  # noqa: F401  (puts src/ on the path)
from lgref.bench import catalog, probes, synth, wellformed
from lgref.bench.simulators import SIMULATORS

FRESH = ('kalah_mini', 'dotsboxes_2x2', 'hex_3x3', 'checkers_4x4',
         'foxgeese_mini', 'chomp_3x3', 'synth_independent',
         'synth_shared', 'synth_redundant')
#: Reachable-state counts, found exhaustively. A change to a game that
#: alters its state space fails here first.
REACHABLE = {'kalah_mini': 113, 'dotsboxes_2x2': 5349, 'hex_3x3': 5514,
             'checkers_4x4': 1556, 'chomp_3x3': 38,
             'synth_independent': 73, 'synth_shared': 73,
             'synth_redundant': 73}


def _text(game):
    with open(catalog.game_path(game)) as handle:
        return handle.read()


def _game_at(game, facts):
    g = wellformed.open_game(_text(game))
    g.state = probes._state(facts)
    return g


def _legal(game, facts, role):
    return sorted(_game_at(game, facts).legal_moves(role), key=repr)


def _after(game, facts, joint):
    g = _game_at(game, facts)
    g.step({r: probes._term(m) for r, m in joint.items()})
    return frozenset(g.state)


def _facts(text):
    return frozenset(probes._state(text))


def test_the_fresh_games_are_the_catalog_s():
    assert set(FRESH) == {g.name for g in catalog.GAMES
                          if g.split == 'test'
                          and g.path.startswith(catalog.NEW_GAMES)}
    assert set(catalog.existing('test')) >= set(FRESH)


@pytest.mark.parametrize('game', FRESH)
def test_infix_and_loads(game):
    text = _text(game)
    assert '(<=' not in text
    assert 'AFTER' in text and 'freeze (ab7b33b)' in text
    g = wellformed.open_game(text)
    assert not g.is_terminal()


@pytest.mark.parametrize('game', sorted(REACHABLE))
def test_agrees_with_simulator_on_every_reachable_state(game):
    text = _text(game)
    states, mode = wellformed.walk(text, exhaustive=True, limit=200000)
    assert mode == 'exhaustive' and len(states) == REACHABLE[game]
    assert wellformed.check(text, states, SIMULATORS[game]()) == []


def test_fox_and_geese_agrees_with_simulator():
    text = _text('foxgeese_mini')
    states, mode = wellformed.walk(text, exhaustive=True, limit=10000)
    assert mode != 'exhaustive'          # too big: sampled instead
    states, mode = wellformed.walk(text, games=150, seed=4)
    assert len(states) > 1500
    assert wellformed.check(text, states, SIMULATORS['foxgeese_mini']()) \
        == []


@pytest.mark.parametrize('game,old,new', [
    ('kalah_mini', 'opposite(s2,n2)\n', 'opposite(s2,n1)\n'),
    ('kalah_mini', 'ring(north,nstore,s1)\n', 'ring(north,nstore,n1)\n'),
    ('dotsboxes_2x2', ' & ~double & succ(N,N2)', ' & succ(N,N2)'),
    ('hex_3x3', 'touches(X,Y,X2,Y2) :- succ(X,X2) & succ(Y2,Y)\n', ''),
    ('checkers_4x4', ' & ~canjump(P)', ''),
    ('checkers_4x4', 'farrow(black,1)\n', ''),
    ('foxgeese_mini', 'waddle(X,Y,X2,Y) :- beside(X,X2) & index(Y)\n', ''),
    ('chomp_3x3', 'atmost(2,3)\n', ''),
    ('synth_shared', ' & true(token(P))', ''),
    ('synth_independent', 'next(lit(P)) :- true(lit(P))\n', ''),
])
def test_simulator_comparison_fails_on_a_mutant(game, old, new):
    text = _text(game)
    assert text.count(old) == 1
    mutant = text.replace(old, new)
    states, _mode = wellformed.walk(mutant, games=60, seed=0)
    assert wellformed.check(mutant, states, SIMULATORS[game]())


def test_synthetic_files_are_generated():
    for name in synth.NAMES:
        assert _text(name) == synth.text(name), name


def test_the_three_synthetic_games_have_one_behaviour():
    walks = [wellformed.walk(_text(n), exhaustive=True)[0]
             for n in synth.NAMES]
    assert set(walks[0]) == set(walks[1]) == set(walks[2])


# ---- hand-built positions with known answers ----------------------------

KALAH = ('control(south) seeds(s1,0) seeds(s2,2) seeds(s3,0) seeds(n1,1) '
         'seeds(n2,0) seeds(n3,3) store(south,0) store(north,0)')


def test_kalah_capture_takes_the_opposite_pit():
    # s2's two seeds go to s3 and the store: last seed in the store,
    # so south moves again, and nothing is captured.
    after = _after('kalah_mini', KALAH, {'south': 'sow(s2)',
                                         'north': 'noop'})
    assert ('store', 'south', '1') in after
    assert ('control', 'south') in after
    # One seed from s1 would land in empty s2 opposite n2 (empty):
    # no capture. Put a seed in s1 and one in n2 instead.
    state = KALAH.replace('seeds(s1,0)', 'seeds(s1,1)').replace(
        'seeds(s2,2)', 'seeds(s2,0)').replace('seeds(n2,0)', 'seeds(n2,2)')
    after = _after('kalah_mini', state, {'south': 'sow(s1)',
                                         'north': 'noop'})
    assert ('store', 'south', '3') in after          # 1 + 2 captured
    assert ('seeds', 's2', '0') in after and ('seeds', 'n2', '0') in after
    assert ('control', 'north') in after


def test_kalah_sowing_skips_the_opponent_store():
    state = ('control(north) seeds(s1,0) seeds(s2,0) seeds(s3,1) '
             'seeds(n1,0) seeds(n2,0) seeds(n3,5) store(south,0) '
             'store(north,0)')
    after = _after('kalah_mini', state, {'north': 'sow(n3)',
                                         'south': 'noop'})
    # n3's five seeds: north store, s1, s2, s3, n1. The last lands in
    # north's own empty pit n1, opposite s3 (now 2): a capture of 3.
    assert ('store', 'north', '4') in after
    assert ('store', 'south', '0') in after
    assert ('seeds', 's3', '0') in after and ('seeds', 'n1', '0') in after


def test_kalah_ends_when_the_mover_is_bare():
    state = ('control(south) seeds(s1,0) seeds(s2,0) seeds(s3,0) '
             'seeds(n1,2) seeds(n2,0) seeds(n3,0) store(south,3) '
             'store(north,1)')
    g = _game_at('kalah_mini', state)
    assert g.is_terminal()
    assert wellformed.goal_values(g, 'south') == {50}


def test_checkers_capture_is_forced():
    state = ('control(white) tick(3) at(white,man,2,1) at(white,man,4,1) '
             'at(black,man,3,2) at(black,man,1,4)')
    moves = _legal('checkers_4x4', state, 'white')
    assert moves == [('jump', '2', '1', '4', '3'),
                     ('jump', '4', '1', '2', '3')]


def test_checkers_promotion_and_king_moves():
    state = ('control(white) tick(5) at(white,man,2,3) at(black,man,1,2)')
    after = _after('checkers_4x4', state, {'white': 'step(2,3,1,4)',
                                           'black': 'noop'})
    assert ('at', 'white', 'king', '1', '4') in after
    king = ('control(white) tick(6) at(white,king,2,3) at(black,man,4,1)')
    assert ('step', '2', '3', '1', '2') in _legal('checkers_4x4', king,
                                                  'white')


def test_checkers_draw_at_the_turn_limit():
    g = _game_at('checkers_4x4', 'control(white) tick(16) '
                 'at(white,man,2,1) at(black,man,3,4)')
    assert g.is_terminal()
    assert wellformed.goal_values(g, 'white') == {50}


def test_hex_connection_wins():
    red = ('control(blue) cell(2,1,red) cell(1,2,red) cell(1,3,red) '
           'cell(3,1,blue) cell(3,2,blue)')
    g = _game_at('hex_3x3', red)
    assert g.is_terminal()
    assert wellformed.goal_values(g, 'red') == {100}
    # (2,1) and (2,2) do not touch along the other diagonal: (1,2)-(2,1)
    # touches, (1,1)-(2,2) does not.
    apart = 'control(blue) cell(1,1,red) cell(2,2,red) cell(2,3,red)'
    assert not _game_at('hex_3x3', apart).is_terminal()


def test_dots_double_box_scores_two_and_moves_again():
    lines = ' '.join('drawn({})'.format(x) for x in (
        'h(1,1)', 'h(2,1)', 'h(1,2)', 'h(2,2)', 'v(1,1)', 'v(3,1)'))
    state = 'control(a) score(a,0) score(b,0) ' + lines
    after = _after('dotsboxes_2x2', state, {'a': 'draw(v(2,1))',
                                            'b': 'noop'})
    assert ('score', 'a', '2') in after and ('control', 'a') in after


def test_fox_jump_captures_and_geese_never_move_down():
    state = ('control(fox) tick(4) lost(0) fox(3,4) goose(3,3) '
             'goose(1,1) goose(2,1) goose(4,1)')
    assert ('jump', '3', '4', '3', '2') in _legal('foxgeese_mini', state,
                                                  'fox')
    after = _after('foxgeese_mini', state, {'fox': 'jump(3,4,3,2)',
                                            'geese': 'noop'})
    assert ('lost', '1') in after and ('goose', '3', '3') not in after
    geese = ('control(geese) tick(5) lost(0) fox(1,1) goose(3,3) '
             'goose(2,2)')
    moves = _legal('foxgeese_mini', geese, 'geese')
    assert ('glide', '3', '3', '3', '2') not in moves
    assert ('glide', '3', '3', '3', '4') in moves


def test_fox_trapped_loses():
    state = ('control(fox) tick(4) lost(0) fox(1,4) goose(2,4) '
             'goose(1,3) goose(3,4) goose(1,2)')
    g = _game_at('foxgeese_mini', state)
    assert g.is_terminal()
    assert wellformed.goal_values(g, 'geese') == {100}


def test_chomp_bite_removes_the_region():
    full = 'control(first) ' + ' '.join(
        'square({},{})'.format(x, y) for x in (1, 2, 3) for y in (1, 2, 3))
    after = _after('chomp_3x3', full, {'first': 'bite(2,2)',
                                       'second': 'noop'})
    left = {(f[1], f[2]) for f in after if f[0] == 'square'}
    assert left == {('1', '1'), ('1', '2'), ('1', '3'), ('2', '1'),
                    ('3', '1')}


@pytest.mark.parametrize('game', synth.NAMES)
def test_synthetic_jump_only_once(game):
    state = 'control(red) tally(1) token(blue)'
    moves = _legal(game, state, 'red')
    assert ('add', '2') not in moves and ('add', '1') in moves
    assert 'light' in moves
