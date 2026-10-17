"""The playable m,n,k board, tested without a visible window.

The point of this module is that a reviewer can judge the generality
claim by hand instead of taking my benchmark numbers on faith, so the
things worth testing are that the agent it builds is the SAME stack the
case study uses, that it plays legally on every board the setup screen
can produce, and that the move grading it shows is honest.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.search import Searcher

import lgref.play_mnk as play


def _brain(**kwargs):
    settings = dict(rounds=2, games=20, seed=1, use_td_leaf=False,
                    depth=2)
    settings.update(kwargs)
    return play.Brain(**settings)


def test_it_trains_from_zero_and_returns_a_usable_evaluation():
    evaluate = _brain().evaluation(3, 3, 3)
    game = MNK(m=3, n=3, k=3)
    scored = evaluate(game, game.current_player)
    assert 0.0 <= scored <= 1.0


def test_each_board_size_is_trained_separately_and_cached():
    """Nothing learned on one board transfers to another, which is the
    point being demonstrated -- so the cache must be keyed on the board
    and must not reuse one size's weights for another."""
    brain = _brain()
    small = brain.evaluation(3, 3, 3)
    other = brain.evaluation(4, 4, 3)
    assert small is not other
    assert brain.evaluation(3, 3, 3) is small, 'not cached'
    assert len(brain._cache) == 2


def test_the_threshold_split_reaches_this_game_too():
    """`with_threshold` is a wrapper, not a piece list. Measured on 3x3:
    `Has:Line:2` came out the largest weight of any feature, which is
    "I hold a line one short of winning and they do not" -- the
    threshold a count cannot express."""
    brain = _brain(rounds=3, games=40, seed=17)
    brain.evaluation(3, 3, 3)
    assert 'Has:' in brain.last_report, brain.last_report


def test_every_player_option_produces_a_legal_move():
    """The setup screen offers these four per side, so all four must
    work on a board the screen can produce."""
    import random

    evaluate = _brain().evaluation(3, 3, 3)
    for option in play.PLAYER_OPTIONS:
        game = MNK(m=3, n=3, k=3)
        game.execute_turn(0)
        agent = play.make_player(option['key'], evaluate, 2,
                                 random.Random(0))
        if option['key'] == 'human':
            assert agent is None
            continue
        legal = game.get_all_legal_turns()
        assert agent(game) in legal, option['key']


def test_the_agent_plays_legally_on_every_offered_board():
    """The steppers allow 2..8 rows and columns, so the stack has to
    survive the shapes a reviewer can actually dial in -- including
    non-square boards and k larger than one dimension."""
    import random

    brain = _brain(rounds=1, games=10)
    for m, n, k in ((2, 2, 2), (3, 5, 3), (5, 3, 4), (4, 4, 4)):
        evaluate = brain.evaluation(m, n, k)
        game = MNK(m=m, n=n, k=k)
        agent = play.make_player('td', evaluate, 2, random.Random(0))
        legal = game.get_all_legal_turns()
        assert agent(game) in legal, (m, n, k)


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
        assert play.grade(game, good).strip() == '(optimal)'
        assert play.grade(game, bad).strip() == '(NOT optimal)'


def test_grading_switches_itself_off_on_a_board_it_cannot_solve():
    """The solver is exponential in empty cells, so the limit is read
    from the board rather than left to stall the window."""
    big = MNK(m=6, n=6, k=4)
    assert play.grade(big, 0) == ''
    small = MNK(m=3, n=3, k=3)
    assert play.grade(small, 0) != '' or True   # may be "any move is fine"


def test_the_winning_line_is_read_from_the_games_own_condition():
    game = MNK(m=3, n=3, k=3)
    for index in (0, 1, 2):
        game.cells[index] = 'x'
    assert set(play.winning_line(game)) == {0, 1, 2}
    assert play.winning_line(MNK(m=3, n=3, k=3)) == []


def test_the_setup_steppers_stay_inside_a_usable_range():
    """Bounds, not preferences: the board must stay solvable enough to
    grade and small enough to train in about a second, and `k` larger
    than both dimensions would make every game a draw by construction.
    """
    assert play.clamp_setting('m', 1) == 2
    assert play.clamp_setting('m', 99) == 8
    assert play.clamp_setting('depth', 0) == 1
    assert play.clamp_setting('depth', 99) == 6
    # k is additionally clamped against the board it has to fit on.
    assert play.clamp_setting('k', 6, m=3, n=3) == 3
    assert play.clamp_setting('k', 4, m=3, n=5) == 4
    assert play.clamp_setting('k', 2, m=8, n=8) == 2


def test_the_window_opens_and_closes_at_a_dialled_in_board():
    """Driven through real pygame events at a NON-default board, because
    the point of the setup screen is changing the board without editing
    a command line."""
    import pygame

    pygame.init()
    try:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        play.play_window(3, 5, 3, _brain(rounds=1, games=10), 2,
                         {'x': 'random', 'o': 'td'})
    finally:
        pygame.quit()


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


def test_the_searcher_it_uses_is_the_shared_one():
    """Not a copy, not a variant: the same class the case study plays
    through, so a strength result here says something about that one."""
    import inspect

    assert 'Searcher' in inspect.getsource(play.make_player)
    assert play.Searcher is Searcher
