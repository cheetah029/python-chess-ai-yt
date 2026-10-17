"""The playable m,n,k board, tested without opening a window.

The point of this module is that a reviewer can judge the generality
claim by hand instead of taking my benchmark numbers on faith, so the
things worth testing are that the agent it builds is the SAME stack the
case study uses, that it plays legally, and that the move grading it
shows is honest.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.search import Searcher

import lgref.play_mnk as play


def test_it_trains_from_zero_and_returns_a_usable_evaluation():
    evaluate, weights = play.train(3, 3, 3, rounds=2, per_round=20,
                                   seed=1, depth=2, use_td_leaf=False)
    assert weights, 'nothing was learned'
    game = MNK(m=3, n=3, k=3)
    scored = evaluate(game, game.current_player)
    assert 0.0 <= scored <= 1.0


def test_the_presence_indicators_reach_this_game_too():
    """`with_presence` is a wrapper, not a piece list, so it must apply
    here. Measured on 3x3: `Has:Line:2` came out the second largest
    weight of any feature, which is 'I have a line one short of winning
    and they do not' -- the threshold a count cannot express."""
    _evaluate, weights = play.train(3, 3, 3, rounds=3, per_round=40,
                                    seed=17, depth=2, use_td_leaf=False)
    assert any(name.startswith('Has:') for name in weights), sorted(weights)


def test_the_agent_plays_a_legal_move_through_the_shared_searcher():
    evaluate, _weights = play.train(3, 3, 3, rounds=2, per_round=20,
                                    seed=1, depth=2, use_td_leaf=False)
    game = MNK(m=3, n=3, k=3)
    game.execute_turn(0)
    searcher = Searcher(evaluate, max_depth=3, budget=5.0, quiescence=0)
    legal = game.get_all_legal_turns()
    assert searcher.choose_turn(legal, game) in legal


def test_the_grade_shown_to_the_player_matches_exact_minimax():
    """It is shown next to every agent move, so it must not flatter."""
    game = MNK(m=3, n=3, k=3)
    game.cells[0] = 'x'
    game.cells[1] = 'x'
    game.cells[4] = 'o'
    game.current_player = 'x'
    best, _value = optimal_moves(game)
    legal = game.get_all_legal_turns()
    if best and len(best) < len(legal):
        good = sorted(best)[0]
        bad = sorted(set(legal) - set(best))[0]
        assert play.grade(game, good) == ' (optimal)'
        assert play.grade(game, bad) == ' (NOT optimal)'


def test_nothing_about_the_case_study_leaks_into_the_player():
    """It must read as a second game, not as a port of the first."""
    import ast
    import inspect

    source = inspect.getsource(play)
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            text = ast.get_docstring(node, clean=False)
            if text is not None:
                docstrings.add(text)
    live = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Str) and node.s not in docstrings:
            live.add(node.s)
        elif isinstance(node, ast.Attribute):
            live.add(node.attr)
        elif isinstance(node, ast.Name):
            live.add(node.id)
    short = ' '.join(x for x in live if len(x) < 40)
    for banned in ('Rook', 'Bishop', 'Knight', 'Pawn', 'royal', 'boulder',
                   'royal_chess'):
        assert banned not in short, banned
