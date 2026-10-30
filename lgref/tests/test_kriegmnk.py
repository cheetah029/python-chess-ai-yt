"""Krieg-m,n,k is m,n,k with the opponent's marks hidden (issue #294).

1. AT 3,3,3 IT IS KRIEG-TICTACTOE: the generated description plays
   identically to the hand-written `kriegtictactoe.gdl`, view for view.
2. ITS LINES ARE THE M,N,K LINES: on random boards, terminal and goals
   agree with a direct Python check of k in a row.
3. THE CHECKED-IN 5,5,4 FILE IS WHAT THE GENERATOR WRITES.
4. IT IS WELL-FORMED for GDL-II, and V6 and V0 play it from their views.
"""

import collections
import os
import random
import sys

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp.epistemic import KnowledgeModel  # noqa: E402
from ggp.game import GGPGame  # noqa: E402

from lgref.experiments import hidden  # noqa: E402
from lgref.experiments.gdl import GdlGame, load  # noqa: E402
from lgref.identify.testgames import kriegmnk  # noqa: E402
from lgref.tests.test_hidden import _Watched, _seal  # noqa: E402

GAMES = os.path.join(HERE, '..', 'identify', 'testgames')
KRIEG = os.path.join(GAMES, 'kriegtictactoe.gdl')
K554 = os.path.join(GAMES, 'kriegmnk_5_5_4.gdl')


def test_at_3_3_3_it_plays_exactly_as_krieg_tictactoe():
    with open(KRIEG) as handle:
        written = handle.read()
    generated = kriegmnk.generate(3, 3, 3)
    plies = 0
    for seed in range(60):
        a = GdlGame(GGPGame(written), max_turns=40, seed=seed)
        b = GdlGame(GGPGame(generated), max_turns=40, seed=seed)
        rng = random.Random(seed)
        while not a.is_game_over():
            assert not b.is_game_over()
            for role in a.roles:
                assert a.view(role) == b.view(role)
            turn = rng.choice(a.get_all_legal_turns())
            a.execute_turn(turn)
            b.execute_turn(turn)
            plies += 1
        assert b.is_game_over() and a.winner == b.winner
    assert plies > 400


def test_the_checked_in_5_5_4_is_what_the_generator_writes():
    with open(K554) as handle:
        assert handle.read() == kriegmnk.generate(5, 5, 4)


def test_line_counts():
    assert len(kriegmnk.lines(3, 3, 3)) == 8
    assert len(kriegmnk.lines(5, 5, 4)) == 28           # 10 + 10 + 8
    assert len(kriegmnk.lines(13, 13, 5)) == 396        # 234 + 162


def _has_line(board, mark, m, n, k):
    for r in range(1, m + 1):
        for c in range(1, n + 1):
            for dr, dc in kriegmnk.DIRECTIONS:
                if all(board.get((r + i * dr, c + i * dc)) == mark
                       for i in range(k)):
                    return True
    return False


def test_terminal_and_goals_are_k_in_a_row_on_random_boards():
    for m, n, k in ((5, 5, 4), (4, 6, 3), (6, 4, 4)):
        game = GGPGame(kriegmnk.generate(m, n, k))
        rng = random.Random(m * 100 + n * 10 + k)
        for _ in range(150):
            board = dict(((r, c), rng.choice('xob'))
                         for r in range(1, m + 1) for c in range(1, n + 1))
            game.state = {('cell', str(r), str(c), w)
                          for (r, c), w in board.items()}
            game.state.add(('control', 'xplayer'))
            x = _has_line(board, 'x', m, n, k)
            o = _has_line(board, 'o', m, n, k)
            full = 'b' not in board.values()
            assert game.is_terminal() == (x or o or full)
            if x and not o:
                assert game.goal('xplayer') == 100
                assert game.goal('oplayer') == 0
            elif not x and not o:
                assert game.goal('xplayer') == game.goal('oplayer') == 50


def test_a_player_is_told_only_ok_or_taken():
    game = load(K554)
    game.execute_turn(('xplayer', ('mark', '3', '3')))
    assert game.view('xplayer').steps[-1] == (
        ('mark', '3', '3'), frozenset({'ok'}))
    assert game.view('oplayer').steps[-1] == ('noop', frozenset())
    game.execute_turn(('oplayer', ('mark', '3', '3')))
    assert game.view('oplayer').steps[-1] == (
        ('mark', '3', '3'), frozenset({'taken'}))
    assert game.current_player == 'xplayer'
    game.execute_turn(('xplayer', ('mark', '1', '1')))
    assert ('mark', '3', '3') not in game.view('oplayer').legal
    assert len(game.view('oplayer').legal) == 24


def test_5_5_4_is_gdl_ii_well_formed_and_not_an_identification_gate():
    from lgref.identify.testgames import ground_truth

    game = GGPGame.from_file(K554)
    assert game.dialect == 'GDL-II'
    assert all('krieg' not in str(key).lower()
               for key in ground_truth.GAMES)
    model = KnowledgeModel(game, game.state)
    for length in range(1, 4):
        for role in ('xplayer', 'oplayer'):
            groups = collections.defaultdict(set)
            for history in model.sequences(length):
                groups[model.view(history, role)].add(
                    tuple(model.legal(history, role)))
            assert all(len(legal) == 1 for legal in groups.values()), (
                role, length)


def test_v6_and_v0_play_5_5_4_from_their_views_only():
    with open(K554) as handle:
        rules = handle.read()
    for seed in range(3):
        game = _seal(load(K554, seed=seed))
        players = {}
        for index, role in enumerate(('xplayer', 'oplayer')):
            inner = (hidden.DeterminizedPlayer(rules, role, seed=seed)
                     if (index + seed) % 2
                     else hidden.UniformPlayer(role, seed=seed))
            players[role] = _Watched(inner)
        assert hidden.play(game, players) is not None
        assert any(w.calls for w in players.values())


def test_the_generator_refuses_an_impossible_k():
    import pytest

    with pytest.raises(ValueError):
        kriegmnk.generate(3, 3, 4)
