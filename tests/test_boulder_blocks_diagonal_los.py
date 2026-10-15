"""The boulder on the central intersection must block DIAGONAL lines of
sight -- and for a long time it did not.

RULEBOOK.md, Boulder: "when on the central intersection, the boulder
blocks diagonal lines only -- not files or ranks."
RULEBOOK.md, Reactive-armed: a bishop is armed only with "unblocked
diagonal line-of-sight to that move's INITIAL square at the moment the
move began".

THE DEFECT. A boulder on the intersection sits on NO square -- it is
held in `board.boulder` with `on_intersection` set -- so any scan that
asks only `squares[r][c].has_piece()` walks straight through it.
`straightline_squares` and `straightline_of_sight_squares` had always
guarded the crossing with `_diagonal_crosses_center`; the two LoS
helpers never did. The result was that bishop MOVEMENT was blocked
correctly while bishop ARMING was not, which is exactly the shape of
the bug as reported.

REPORTED GAME. With the boulder on the intersection, a pawn moved
f3-f4 and a black bishop on a8 was allowed to capture it: `Ba8xf4`. The
a8-f3 diagonal runs a8, b7, c6, d5, e4, f3, and the d5 -> e4 step
crosses the centre point, so that bishop was never on an unblocked
diagonal to f3 and should never have been armed.

Three call sites shared the one root cause: `_compute_armed_bishops`
(the live arming), `_enemy_base_queen_has_los_to` (queen manipulation
Restriction 2, which had the same hole on its diagonal case), and the
save/reload path in `game.py` that reconstructs `reactive_armed`.

The GDL was CORRECT throughout: `bishop_diag_los` resolves through
`los_diag_ray`, which carries `~center_crossing_blocked` on both its
base case and its recursive step. That is checked here too, so a future
edit cannot quietly drop it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

from experiments.variants import make_engine
from move import Move
from piece import Bishop, King, Pawn, Queen
from square import Square


def _bare_board(boulder_centred=True):
    """An empty board with both kings, so positions stay legal."""
    engine = make_engine('full', max_turns=60)
    board = engine.board
    for row in range(8):
        for col in range(8):
            board.squares[row][col].piece = None
    board.squares[0][6].piece = King('black')
    board.squares[7][6].piece = King('white')
    board.turn_number = 10
    engine.turn_number = 10
    if not boulder_centred:
        board.boulder.on_intersection = False
        board.squares[7][0].piece = board.boulder   # parked off the lines
    return engine, board


def test_the_reported_capture_is_illegal():
    """`Ba8xf4` after `Pf3-f4`, boulder on the intersection."""
    engine, board = _bare_board()
    board.squares[0][0].piece = Bishop('black')      # a8
    board.squares[5][5].piece = Pawn('white')        # f3
    pawn = board.squares[5][5].piece

    assert board._compute_armed_bishops(pawn, Square(5, 5)) == [], (
        'the bishop was armed across the central intersection')
    board.move(pawn, Move(Square(5, 5), Square(4, 5)))   # f3 -> f4
    engine.current_player = 'black'
    assert board.squares[0][0].piece.reactive_armed is False
    captures = [turn for turn in engine.get_all_legal_turns()
                if turn.to_sq == (4, 5) and getattr(turn, 'is_capture',
                                                    False)]
    assert captures == [], 'Ba8xf4 is still offered'


def test_the_same_capture_is_legal_with_the_boulder_elsewhere():
    """The control. Without it this test file would pass just as well
    against a bishop that can never reactive-capture at all."""
    engine, board = _bare_board(boulder_centred=False)
    board.squares[0][0].piece = Bishop('black')
    board.squares[5][5].piece = Pawn('white')
    pawn = board.squares[5][5].piece

    assert len(board._compute_armed_bishops(pawn, Square(5, 5))) == 1
    board.move(pawn, Move(Square(5, 5), Square(4, 5)))
    engine.current_player = 'black'
    assert board.squares[0][0].piece.reactive_armed is True
    captures = [turn for turn in engine.get_all_legal_turns()
                if turn.to_sq == (4, 5) and getattr(turn, 'is_capture',
                                                    False)]
    assert captures, 'the reactive capture was broken by the fix'


def test_both_centre_diagonals_are_blocked():
    """d5-e4 and e5-d4 are the two steps that span the centre point."""
    _engine, board = _bare_board()
    # a8-h1 runs through d5 -> e4.
    assert board._has_unblocked_diagonal_los(0, 0, 7, 7) is False
    # h8-a1 runs through e5 -> d4.
    assert board._has_unblocked_diagonal_los(0, 7, 7, 0) is False


def test_ranks_and_files_through_the_centre_stay_open():
    """"diagonal lines only -- not files or ranks". A rank or file step
    across the middle must be unaffected, or the boulder would be
    blocking lines the rules say it does not."""
    _engine, board = _bare_board()
    assert board._has_unblocked_queen_los(3, 0, 3, 7) is True   # rank 5
    assert board._has_unblocked_queen_los(4, 0, 4, 7) is True   # rank 4
    assert board._has_unblocked_queen_los(0, 3, 7, 3) is True   # file d
    assert board._has_unblocked_queen_los(0, 4, 7, 4) is True   # file e
    # And the single steps across the middle, which is where a
    # too-eager guard would bite.
    assert board._has_unblocked_queen_los(3, 3, 3, 4) is True
    assert board._has_unblocked_queen_los(3, 3, 4, 3) is True


def test_a_diagonal_that_misses_the_centre_is_unaffected():
    _engine, board = _bare_board()
    assert board._has_unblocked_diagonal_los(1, 0, 6, 5) is True
    assert board._has_unblocked_diagonal_los(0, 1, 6, 7) is True


def test_the_crossing_is_checked_on_the_final_step_too():
    """A path can cross the centre on its LAST step: d5 to e4 with the
    target standing on e4 is still a crossing, and a loop that only
    inspects squares strictly between would miss it."""
    _engine, board = _bare_board()
    assert board._has_unblocked_diagonal_los(3, 3, 4, 4) is False
    assert board._has_unblocked_diagonal_los(3, 4, 4, 3) is False
    assert board._has_unblocked_queen_los(3, 3, 4, 4) is False


def test_queen_manipulation_los_is_blocked_on_the_diagonal():
    """The second instance of the same defect, which nobody reported.
    Restriction 2 consults an enemy base-form queen's line of sight, and
    its diagonal case walked through the intersection as well."""
    _engine, board = _bare_board()
    board.squares[0][0].piece = Queen('black')       # a8, base form
    board.squares[5][5].piece = Pawn('white')        # f3
    assert board._enemy_base_queen_has_los_to('black', 5, 5) is False
    # Along a rank the same queen must still see, since ranks are open.
    board.squares[0][0].piece = None
    board.squares[5][0].piece = Queen('black')       # a3, same rank as f3
    assert board._enemy_base_queen_has_los_to('black', 5, 5) is True


def test_a_boulder_standing_on_a_real_square_blocks_as_a_piece():
    """Off the intersection the boulder is an ordinary blocker, so the
    centre-crossing rule must not be the only thing stopping a line."""
    _engine, board = _bare_board(boulder_centred=False)
    board.squares[7][0].piece = None
    board.squares[3][3].piece = board.boulder        # d5
    assert board._has_unblocked_diagonal_los(0, 0, 5, 5) is False
    # The endpoint itself is never treated as a blocker.
    assert board._has_unblocked_diagonal_los(0, 0, 3, 3) is True


def test_the_official_gdl_blocks_the_crossing_in_both_clauses():
    """The GDL was right all along, and must stay right.

    `bishop_diag_los` resolves through `queen_los_diag` ->
    `los_diag_ray`, and BOTH clauses of that ray -- the single step and
    the recursive extension -- have to carry the guard. Dropping it from
    either one would reopen this hole in the specification.
    """
    path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl',
                        'integrated.gdl')
    with open(path) as handle:
        lines = [line.strip() for line in handle]
    rays = [line for line in lines if line.startswith('los_diag_ray(')]
    assert len(rays) >= 2, 'los_diag_ray is no longer two clauses'
    for clause in rays:
        assert '~center_crossing_blocked' in clause, clause
    assert any(line.startswith('bishop_diag_los(')
               and 'queen_los_diag' in line for line in lines), (
        'bishop arming no longer resolves through the guarded ray')
    assert any(line.startswith('center_crossing_blocked(')
               and 'boulder_at(intersection)' in line for line in lines)
