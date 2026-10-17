"""The objective, read from the game's own statements (#268).

A hand-written position score cannot serve a framework that must handle
unseen games. A game description DECLARES its objective, though, and the
predicates that declaration depends on are the quantities progress is
measured in. Reading them is reading the rules, not supplying an opinion,
and the same code reads any game -- which is the move strong general
players make.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from lgref.experiments import tactics
from lgref.experiments.objective import extract, royal_balance

ROOT = os.path.join(os.path.dirname(__file__), '..', 'identify',
                    'testgames')
REPO = os.path.join(os.path.dirname(__file__), '..', '..')


def test_it_reads_every_benchmark_game():
    """One extractor, four descriptions, no per-game code."""
    expected = {
        'nim': 'pile',
        'tictactoe': 'line',
        'corridor': 'home',
    }
    for game, predicate in expected.items():
        got = extract(os.path.join(ROOT, game + '.gdl'))
        assert got.roots, '{}: no terminal or goal found'.format(game)
        assert predicate in got.state_predicates, (
            '{}: expected the objective to depend on {!r}, got {}'.format(
                game, predicate, got.state_predicates))


def test_it_reads_royal_chess():
    got = extract(os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl'))
    assert 'dead' in got.state_predicates
    assert 'alive' in got.state_predicates


def test_it_finds_the_distance_measure_in_royal_chess():
    """Worth pinning, because it is the one DENSE quantity the objective
    depends on -- and the reason it cannot simply be used as an
    evaluation.

    It enters through the tiny-endgame loss condition. Using it to score
    leaves would make the agent play differently in `no_tiny_endgame`,
    where that rule is removed, so an evaluation extracted from a rule
    that is itself under ablation is circular for that rule -- the same
    class of error as #231.
    """
    got = extract(os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl'))
    assert 'closest_royal_pair_distance' in got.state_predicates


def test_gdl_keywords_are_not_reported_as_objective_features():
    for game in ('nim', 'tictactoe', 'corridor'):
        got = extract(os.path.join(ROOT, game + '.gdl'))
        for keyword in ('true', 'does', 'legal', 'next', 'role'):
            assert keyword not in got.state_predicates, game


# ---- why the extracted measure cannot guide the midgame ---------------

def test_the_royal_measure_is_flat_for_most_of_the_game():
    """Measured, because it is the crux of the strength problem.

    Royal Chess wins by capturing BOTH royals, so its objective is a
    conjunction of two rare events and the surviving-royal count is equal
    for both sides almost everywhere:

        after   0 plies: flat in 100% of positions
        after  20 plies: flat in  98%
        after  60 plies: flat in  82%
        after 120 plies: flat in  55%

    A measure that cannot order two positions cannot order two moves. The
    extraction is correct; the objective is simply sparse.
    """
    from experiments.variants import make_engine

    engine = make_engine('full', max_turns=100)
    counts = royal_balance(engine)
    assert counts == {'white': 2, 'black': 2}
    assert len(set(counts.values())) == 1, (
        'the opening position gives no gradient, by construction')


def test_no_move_can_win_outright_while_both_royals_live():
    """The structural fact that defeats exact shallow tactics here.

    Measured on a midgame position: 0 wins and 0 losses among 56 moves.
    There is no mate-in-one in this variant, so a one-ply solver -- which
    would remove the cheapest blunders in most games -- is silent in this
    one.
    """
    from experiments.variants import make_engine
    from piece import King, Queen

    engine = make_engine('full', max_turns=400)
    board = engine.board
    for row in range(8):
        for col in range(8):
            board.squares[row][col].piece = None
    board.boulder = None
    for colour, cls, row, col in (('white', King, 4, 4),
                                  ('white', Queen, 6, 6),
                                  ('black', King, 3, 4),
                                  ('black', Queen, 0, 0)):
        piece = cls(colour)
        piece.is_royal = True
        board.squares[row][col].piece = piece
    board.turn_number = 4
    engine.turn_number = 4
    engine.current_player = 'white'

    groups = tactics.classify(engine, engine.get_all_legal_turns())
    assert not groups[tactics.WIN], (
        'a win was found with both royals alive, which the rules forbid')


def test_the_tactical_layer_does_fire_when_a_win_is_one_ply_away():
    """Otherwise the test above would pass on a broken solver."""
    from experiments.variants import make_engine
    from piece import King, Queen

    engine = make_engine('full', max_turns=400)
    board = engine.board
    for row in range(8):
        for col in range(8):
            board.squares[row][col].piece = None
    board.boulder = None
    for colour, cls, row, col in (('white', King, 4, 4),
                                  ('white', Queen, 6, 6),
                                  ('black', King, 3, 4)):
        piece = cls(colour)
        piece.is_royal = True
        board.squares[row][col].piece = piece
    board.turn_number = 4
    engine.turn_number = 4
    engine.current_player = 'white'

    groups = tactics.classify(engine, engine.get_all_legal_turns())
    assert groups[tactics.WIN], (
        'black holds one royal, so capturing it ends the game')


def test_the_cost_of_the_tactical_layer_is_quadratic():
    """It is why it is not simply switched on: 56 moves cost 3192
    generations, about 34 seconds on a midgame position."""
    assert tactics.cost_estimate(56) == 56 * 57
    assert tactics.cost_estimate(56, lookahead=False) == 56
