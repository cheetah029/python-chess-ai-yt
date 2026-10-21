"""The boulder the evaluation could not see, and the half of that fix
that was missing.

A neutral piece that captures threatens BOTH sides, and the threat pass
skipped it because it had colour `none`. That was fixed. This file is
about the half the fix missed: for the whole opening of every game the
boulder is not on a square at all.

The rulebook puts it "on the intersection of the four central squares",
and `Board` holds it in `board.boulder` with `on_intersection` set,
outside `board.squares`. The threat pass walks squares. So until
somebody moves it, the fix saw nothing -- and its `threat_squares` is
empty there too, so there would have been nothing to read even if the
loop had reached it.

THE ENGINE IS THE AUTHORITY on whether that matters, not a reading of
the rulebook: a position with a pawn on a central square generates
`Turn(boulder capture ...)` with `is_capture` set. The threat is real
and legal.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine
from lgref.experiments.features import royal_chess
from piece import Pawn

#: Where the rulebook's four central squares are in board coordinates.
CENTRAL = ((3, 3), (3, 4), (4, 3), (4, 4))


def with_pawn_at(row, col, colour='white'):
    engine = make_engine('full', max_turns=40)
    pawn = Pawn(colour)
    pawn.row, pawn.col = row, col
    engine.board.squares[row][col].piece = pawn
    return engine


def test_the_engine_says_the_intersection_boulder_can_take_that_pawn():
    """The premise, checked against the engine rather than against my
    reading of the rulebook. Black is to move because White may not
    move the boulder on their first turn."""
    engine = with_pawn_at(4, 3)
    engine.current_player = 'black'
    captures = [turn for turn in engine.get_all_legal_turns()
                if getattr(turn, 'turn_type', None) == 'boulder'
                and getattr(turn, 'is_capture', False)]
    assert captures, (
        'the engine offers no boulder capture, so there is no threat '
        'here and this whole file is measuring nothing')


def test_the_shipped_extractor_does_not_see_it():
    """THE DEFECT, pinned so the fix cannot be quietly dropped. This
    asserts the CURRENT shipped behaviour, and it is expected to change
    only together with the flag below being turned on by default --
    through the per-phase gate, never silently."""
    for row, col in CENTRAL:
        raw = royal_chess(with_pawn_at(row, col))
        assert raw.get(('white', 'Attacked'), 0) == 0, (row, col)
        assert raw.get(('white', 'Hanging'), 0) == 0, (row, col)


def test_the_flag_makes_it_visible_on_every_central_square():
    for row, col in CENTRAL:
        raw = royal_chess(with_pawn_at(row, col),
                          see_intersection_boulder=True)
        assert raw.get(('white', 'Attacked'), 0) == 1, (row, col)
        assert raw.get(('white', 'Hanging'), 0) == 1, (row, col)


def test_it_sees_a_black_pawn_there_too():
    """A NEUTRAL PIECE THREATENS BOTH SIDES. The boulder takes pawns of
    either colour, so this is not a feature about White."""
    raw = royal_chess(with_pawn_at(4, 3, 'black'),
                      see_intersection_boulder=True)
    assert raw.get(('black', 'Attacked'), 0) == 1
    assert raw.get(('white', 'Attacked'), 0) == 0


def test_the_flag_is_off_by_default_and_changes_nothing_where_there_is_nothing():
    """It changes the VALUES of `Attacked` and `Hanging` under the same
    column names, so the shipped weights would be applied to a
    distribution they were not fitted on. That is a silent change to
    the playing agent, which is the thing this project has been burned
    by. Off by default, and identical on a position with no pawn in
    reach."""
    import inspect

    signature = inspect.signature(royal_chess)
    assert signature.parameters['see_intersection_boulder'].default is False
    plain = royal_chess(make_engine('full', max_turns=40))
    flagged = royal_chess(make_engine('full', max_turns=40),
                          see_intersection_boulder=True)
    assert plain == flagged


def test_a_boulder_on_cooldown_is_not_an_immediate_threat():
    """The rule is read off the board's own move generator rather than
    copied into the feature layer, so the cooldown comes along for
    free -- a boulder that may not move this turn is not threatening
    anything this turn."""
    engine = with_pawn_at(4, 3)
    engine.board.boulder.cooldown = 1
    raw = royal_chess(engine, see_intersection_boulder=True)
    assert raw.get(('white', 'Attacked'), 0) == 0


def test_the_rule_is_not_copied_into_the_feature_layer():
    """The central squares, the pawns-only capture and the cooldown all
    live in `Board.boulder_moves`. A second copy is a second copy to
    get wrong."""
    import inspect

    source = inspect.getsource(royal_chess)
    assert 'boulder_moves' in source
    assert '(3, 3)' not in source and '(4, 4)' not in source, (
        'the central squares are hard-coded in the feature layer')
