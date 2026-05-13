"""Tests for v2 knight redesign: reactive jump-capture + post-jump invulnerability.

Version 2's knight rules replace the old "capture any adjacent enemy to the
landing square after a jump" behavior with two coordinated mechanics:

1. **Reactive jump-capture.** The knight may capture the jumped piece only
   if that piece (a) is an enemy and (b) made a spatial move on the
   immediately preceding turn. Adjacent-to-landing-square captures are
   removed entirely.
2. **Post-jump invulnerability.** When a knight jumps over any piece
   (color-agnostic) and the jumped piece survives the move, the knight
   becomes invulnerable to capture for the immediately following opponent
   turn. Invulnerability expires at the start of the knight-owner's next
   turn.

These tests verify:

- `Piece.invulnerable` attribute exists and defaults to False.
- `Square.has_capturable_enemy_piece` returns False for invulnerable pieces.
- `Board.clear_invulnerable_for_color` clears the flag for the named color only.
- `Board.last_move_turn_number` is initialized to None and updated alongside
  `last_move` whenever a spatial move is executed.
- `Game.next_turn` auto-clears invulnerability on the new current player's
  pieces so it persists for exactly one (the opponent's) turn.
- `Board.move()` for a knight:
  * sets `invulnerable` when the jumped piece survives (friendly, boulder,
    stationary enemy, or capture-declined enemy);
  * does NOT set `invulnerable` when the jumped piece is captured;
  * returns jump-capture targets only if the jumped piece is an enemy that
    moved on the immediately preceding turn;
  * never targets adjacent (non-jumped) enemies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Headless display so display.set_mode is not required
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

# pygame is required to construct Game (uses Config -> pygame.font.SysFont,
# pygame.mixer.Sound). Initialize all subsystems Game touches.
import pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

import pytest


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    """Re-initialize pygame subsystems before every Game-using test, since
    other tests in the suite may shut them down (pygame state is global)."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except pygame.error:
        pass


from piece import Piece, Pawn, Knight, Bishop, Rook, Queen, King, Boulder
from board import Board
from game import Game
from square import Square
from move import Move


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _make_board_with_pieces(white_pieces, black_pieces):
    """Build a board with only the listed pieces (clearing the default setup).

    `white_pieces` and `black_pieces` are lists of (piece_factory, row, col).
    """
    b = Board()
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    for factory, r, c in white_pieces:
        b.squares[r][c].piece = factory()
    for factory, r, c in black_pieces:
        b.squares[r][c].piece = factory()
    b.boulder = None
    return b


def _set_last_move(board, from_rc, to_rc, turn_number_at_move):
    """Manually establish a 'last move was at turn_number_at_move' state.

    The new knight rule needs `last_move` to point at the moved piece's
    final square AND `last_move_turn_number` to equal the turn that move
    happened on. Use this helper to simulate a prior turn's move.
    """
    from_sq = Square(*from_rc)
    to_sq = Square(*to_rc)
    board.last_move = Move(from_sq, to_sq)
    board.last_move_turn_number = turn_number_at_move


# -------------------------------------------------------------------------
# Section 1: invulnerable attribute basics
# -------------------------------------------------------------------------

def test_pieces_have_invulnerable_default_false():
    for piece_factory in (
        lambda: Pawn('white'),
        lambda: Knight('white'),
        lambda: Bishop('white'),
        lambda: Rook('white'),
        lambda: Queen('white'),
        lambda: King('white'),
        lambda: Boulder(),
    ):
        p = piece_factory()
        assert p.invulnerable is False, (
            f"{type(p).__name__} should default to invulnerable=False"
        )


def test_invulnerable_can_be_set_and_cleared():
    n = Knight('white')
    n.invulnerable = True
    assert n.invulnerable is True
    n.invulnerable = False
    assert n.invulnerable is False


def test_has_capturable_enemy_piece_returns_false_for_invulnerable_knight():
    """A invulnerable knight cannot be captured by enemies."""
    b = _make_board_with_pieces(
        white_pieces=[(lambda: Knight('white'), 3, 3)],
        black_pieces=[],
    )
    knight = b.squares[3][3].piece
    knight.invulnerable = True
    # From black's perspective, the knight at (3,3) should not be a capture target
    assert b.squares[3][3].has_capturable_enemy_piece('black') is False


def test_has_capturable_enemy_piece_returns_true_for_non_invulnerable_knight():
    """A non-invulnerable knight is capturable as normal."""
    b = _make_board_with_pieces(
        white_pieces=[(lambda: Knight('white'), 3, 3)],
        black_pieces=[],
    )
    assert b.squares[3][3].has_capturable_enemy_piece('black') is True


# -------------------------------------------------------------------------
# Section 2: Board.clear_invulnerable_for_color
# -------------------------------------------------------------------------

def test_clear_invulnerable_for_color_clears_target_color_only():
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 0, 0),
            (lambda: Knight('white'), 1, 1),
        ],
        black_pieces=[
            (lambda: King('black'), 7, 7),
            (lambda: Knight('black'), 6, 6),
        ],
    )
    b.squares[1][1].piece.invulnerable = True
    b.squares[6][6].piece.invulnerable = True

    b.clear_invulnerable_for_color('white')

    assert b.squares[1][1].piece.invulnerable is False  # white cleared
    assert b.squares[6][6].piece.invulnerable is True   # black untouched


def test_clear_invulnerable_for_color_handles_empty_board_for_color():
    b = _make_board_with_pieces(
        white_pieces=[(lambda: King('white'), 0, 0)],
        black_pieces=[],
    )
    # Should not raise even though no black pieces exist
    b.clear_invulnerable_for_color('black')


# -------------------------------------------------------------------------
# Section 3: Game.next_turn auto-clears invulnerability
# -------------------------------------------------------------------------

def test_next_turn_clears_invulnerable_on_new_current_player():
    """Trace: white's turn N (knight gains invulnerability) → black's turn N+1
    (knight invulnerable) → white's turn N+2 (invulnerability clears at start)."""
    g = Game()
    b = g.board
    # Find a white knight, give it invulnerability (simulate it was set during white's prior turn)
    white_knight = None
    for r in range(8):
        for c in range(8):
            piece = b.squares[r][c].piece
            if piece and piece.color == 'white' and isinstance(piece, Knight):
                white_knight = piece
                break
        if white_knight:
            break
    assert white_knight is not None
    white_knight.invulnerable = True

    # Currently next_player = white (start of game). Simulate having played:
    # advance to black's turn first.
    g.next_turn()
    assert g.next_player == 'black'
    # invulnerability still active (clearing white's pieces on black's turn start)
    assert white_knight.invulnerable is True

    # Now advance to white's next turn — invulnerability should clear.
    g.next_turn()
    assert g.next_player == 'white'
    assert white_knight.invulnerable is False


def test_next_turn_does_not_clear_other_color_invulnerable():
    """When white's turn starts (next_turn returns to white), only white's
    pieces' invulnerability is cleared. Any (hypothetical) black invulnerability stays."""
    g = Game()
    b = g.board
    # Find a black knight and pretend it is invulnerable
    black_knight = None
    for r in range(8):
        for c in range(8):
            piece = b.squares[r][c].piece
            if piece and piece.color == 'black' and isinstance(piece, Knight):
                black_knight = piece
                break
        if black_knight:
            break
    assert black_knight is not None
    black_knight.invulnerable = True

    # Advance to black's turn — clear_invulnerable_for_color('black') runs and clears it.
    g.next_turn()
    assert g.next_player == 'black'
    assert black_knight.invulnerable is False  # black's invulnerability cleared as black starts

    # Re-set and advance to white's turn — black's invulnerability should NOT be cleared
    black_knight.invulnerable = True
    g.next_turn()
    assert g.next_player == 'white'
    assert black_knight.invulnerable is True  # untouched


# -------------------------------------------------------------------------
# Section 4: last_move_turn_number tracking
# -------------------------------------------------------------------------

def test_board_init_last_move_turn_number_is_none():
    b = Board()
    assert b.last_move_turn_number is None


def test_board_move_updates_last_move_turn_number():
    """After a spatial move, last_move_turn_number should equal
    the turn_number at the time of the move."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Pawn('white'), 4, 4),
        ],
        black_pieces=[(lambda: King('black'), 0, 0)],
    )
    b.turn_number = 5
    pawn = b.squares[4][4].piece
    move = Move(Square(4, 4), Square(3, 4))
    b.move(pawn, move)
    assert b.last_move_turn_number == 5


# -------------------------------------------------------------------------
# Section 5: Reactive jump-capture eligibility
# -------------------------------------------------------------------------

def _setup_jump_capture_scenario(jumped_piece_factory, jumped_color_attr=None,
                                  with_adjacent_enemy=True):
    """Set up a board where a white knight at (3,3) can jump over (3,4)
    to land at (3,5), with the jumped square holding the given piece.

    By default (`with_adjacent_enemy=True`), a black pawn is placed at
    (4,5) — adjacent to the landing square and distinct from the jumped
    piece — so the v2 invulnerability condition is satisfied. Set this
    to False for tests that specifically need the no-adjacent-enemy
    case (where invulnerability should NOT trigger under the v2 rule).

    Returns (board, knight, move).
    """
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[(lambda: King('black'), 0, 0)],
    )
    # Place the jumped piece at (3,4)
    b.squares[3][4].piece = jumped_piece_factory()
    # Adjacent-enemy condition for v2 invulnerability: place an enemy at
    # a square adjacent to the landing (3,5) and not equal to the jumped
    # square. (4,5) is adjacent to (3,5) and not equal to (3,4). When
    # the jumped piece itself is an enemy (the most common test case),
    # this second enemy ensures invulnerability triggers regardless of
    # whether the jumped piece survives.
    if with_adjacent_enemy:
        b.squares[4][5].piece = Pawn('black')
    knight = b.squares[3][3].piece
    move = Move(Square(3, 3), Square(3, 5))
    return b, knight, move


def test_jump_capture_targets_jumped_piece_when_moved_last_turn():
    """If the jumped piece is an enemy that moved on the immediately
    preceding turn, jump-capture is eligible and targets list contains
    only the jumped piece."""
    b, knight, move = _setup_jump_capture_scenario(lambda: Pawn('black'))
    # Simulate: black's pawn just moved to (3,4) on the immediately preceding turn.
    # turn_number is currently 2 (knight is moving on turn 3, turn_number=2 during).
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)

    targets = b.move(knight, move)

    assert targets == [(3, 4)], (
        f"Expected only the jumped piece (3,4) as target, got {targets}"
    )


def test_jump_capture_denied_when_jumped_piece_did_not_move_last_turn():
    """Jumped piece is an enemy but did NOT move last turn — jump-capture
    is denied, knight just moves through, no targets returned."""
    b, knight, move = _setup_jump_capture_scenario(lambda: Pawn('black'))
    b.turn_number = 2
    # Last move was a different piece — not the jumped one
    _set_last_move(b, (5, 0), (5, 1), turn_number_at_move=1)

    targets = b.move(knight, move)

    # No targets means normal move continues
    assert not targets, f"Expected no jump-capture targets, got {targets}"
    # Jumped piece still on the board
    assert b.squares[3][4].piece is not None
    # Knight should be invulnerable since jumped piece survived
    assert knight.invulnerable is True


def test_jump_capture_denied_when_jumped_piece_is_friendly():
    """Friendly jumped piece can never be captured. invulnerability still triggers."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Pawn('white'))
    b.turn_number = 2
    # Even with last_move pointing at the friendly's square, no capture allowed.
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)

    assert not targets
    assert b.squares[3][4].piece is not None  # friendly survives
    assert knight.invulnerable is True


def test_jump_capture_denied_when_jumped_piece_is_boulder():
    """Boulder cannot be captured by knight. With an adjacent enemy at
    the landing square, the v2 invulnerability condition is met."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 4, 5),  # adjacent to landing (3,5)
        ],
    )
    boulder = Boulder()
    b.squares[3][4].piece = boulder
    b.turn_number = 2
    # Even if boulder moved last turn (boulder moves are spatial moves):
    _set_last_move(b, (3, 5), (3, 4), turn_number_at_move=1)

    knight = b.squares[3][3].piece
    move = Move(Square(3, 3), Square(3, 5))
    targets = b.move(knight, move)

    assert not targets, f"Boulder should never be jump-captured; got {targets}"
    assert b.squares[3][4].piece is boulder  # boulder survives
    assert knight.invulnerable is True


def test_jump_capture_denied_when_preceding_turn_was_an_action():
    """If the immediately preceding turn was a non-spatial action,
    last_move_turn_number is older than turn_number-1, so jump-capture
    is denied even if last_move points at the jumped piece's square."""
    b, knight, move = _setup_jump_capture_scenario(lambda: Pawn('black'))
    # turn_number = 3 means we're on turn 4 conceptually. last_move was
    # 2 turns ago (turn_number_at_move = 1 when turn_number was 1, meaning
    # the move happened during turn 2). Turn 3 was an action (didn't update).
    b.turn_number = 3
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)

    targets = b.move(knight, move)

    assert not targets, "After action turn, jump-capture should be denied"
    assert b.squares[3][4].piece is not None
    assert knight.invulnerable is True


def test_jump_capture_does_not_target_adjacent_non_jumped_pieces():
    """The new rule captures ONLY the jumped piece. Other adjacent enemies
    to the landing square must NOT be in the targets list."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 3, 4),  # jumped piece
            (lambda: Pawn('black'), 3, 6),  # adjacent to landing (3,5), NOT jumped
            (lambda: Pawn('black'), 4, 5),  # adjacent to landing, NOT jumped
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    # Mark the jumped pawn as the recently-moved piece
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)

    assert targets == [(3, 4)], (
        f"Should target ONLY the jumped piece, got {targets}"
    )
    # The other adjacent enemies must not appear
    assert (3, 6) not in (targets or [])
    assert (4, 5) not in (targets or [])


def test_jump_capture_denied_when_landing_square_not_empty():
    """If the knight makes a standard capture (landing square has enemy),
    jump-capture rule does not apply — even if jumped piece was eligible.
    Per the refined rule, the knight is NOT invulnerable when it captures
    anything (the capture-this-turn excludes invulnerability)."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 3, 4),  # jumped piece
            (lambda: Pawn('black'), 3, 5),  # landing target (standard capture)
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)

    # Standard capture happened — no jump-capture targets returned
    assert not targets
    # Knight is now at (3,5)
    assert b.squares[3][5].piece is knight
    # Jumped piece still alive at (3,4)
    assert b.squares[3][4].piece is not None
    # Knight is NOT invulnerable — it captured at the landing square
    assert knight.invulnerable is False


# -------------------------------------------------------------------------
# Section 6: invulnerability triggers
# -------------------------------------------------------------------------

def test_invulnerable_set_when_knight_jumps_friendly_pawn():
    """Knight jumps over a friendly: jumped piece can't be captured →
    survives → invulnerability."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Pawn('white'))
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_set_when_knight_jumps_stationary_enemy():
    """Knight jumps over an enemy that didn't move last turn → no
    jump-capture eligibility → enemy survives → invulnerability."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Pawn('black'))
    b.turn_number = 2
    # Last move was an unrelated piece
    _set_last_move(b, (5, 5), (5, 6), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_set_when_knight_jumps_boulder():
    """Boulder can't be captured by knight → survives. With an adjacent
    enemy (other than the boulder) at the landing square, the v2
    invulnerability condition is met."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 4, 5),  # adjacent to landing (3,5)
        ],
    )
    b.squares[3][4].piece = Boulder()
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_not_set_when_knight_does_not_jump():
    """Knight's leap goes over an empty square → no invulnerability."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[(lambda: King('black'), 0, 0)],
    )
    # No piece at (3,4) — empty jumped square
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is False


def test_invulnerable_not_set_on_standard_capture_with_jump_friendly():
    """Knight captures at landing AND jumped over a friendly piece in
    transit. Per the refined rule (no invulnerability on a capture
    turn), the knight is NOT invulnerable, even though the friendly
    jumped piece survives."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
            (lambda: Pawn('white'), 3, 4),  # jumped piece (friendly)
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Rook('black'), 3, 5),  # landing target — standard capture
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # Knight captured the rook — no invulnerability
    assert knight.invulnerable is False
    # Friendly jumped piece still alive
    assert b.squares[3][4].piece is not None


def test_invulnerable_not_set_on_standard_capture_with_jump_stationary_enemy():
    """Knight captures at landing AND jumped over a stationary enemy
    (one that did NOT move last turn). The jumped piece survives, but
    the knight made a capture this turn → no invulnerability."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 3, 4),  # jumped, did not move last turn
            (lambda: Rook('black'), 3, 5),  # landing — standard capture
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    # last_move pointing somewhere else (not the jumped pawn)
    _set_last_move(b, (5, 5), (5, 6), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is False
    assert b.squares[3][4].piece is not None  # jumped pawn survived


def test_invulnerable_not_set_on_standard_capture_with_jump_boulder():
    """Knight captures at landing AND jumped over the boulder.
    Boulder always survives, but the knight made a capture → no
    invulnerability."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Rook('black'), 3, 5),  # landing — standard capture
        ],
    )
    b.squares[3][4].piece = Boulder()  # jumped boulder
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is False
    assert isinstance(b.squares[3][4].piece, Boulder)


def test_invulnerable_not_set_when_knight_just_moves_normally():
    """Knight makes a standard capture without jumping over anyone (i.e.,
    jumped square is empty) — no invulnerability."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Rook('black'), 3, 5),  # landing target, jumped (3,4) is empty
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is False


def test_invulnerable_color_agnostic_trigger_with_friendly_jumped_piece():
    """invulnerability triggers regardless of jumped piece color — verify with friendly."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Bishop('white'))
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_color_agnostic_trigger_with_enemy_jumped_piece():
    """invulnerability triggers when a stationary enemy is jumped over."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Rook('black'))
    b.turn_number = 2
    _set_last_move(b, (5, 5), (5, 6), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


# -------------------------------------------------------------------------
# Section 6b: Adjacent-enemy condition for invulnerability
# -------------------------------------------------------------------------
#
# v2 refined invulnerability rule: the knight gains invulnerability after
# a non-capture spatial move only if all of the following hold:
#
#   (1) the move jumps over a piece (jumped square holds a piece),
#   (2) the landing square is adjacent (chebyshev distance 1) to at
#       least one enemy piece, and
#   (3) the adjacent enemy is not the same piece that was jumped over.
#
# These tests pin condition (2) and (3) specifically. Section 6 already
# covers condition (1) (knight must jump over a piece).

def test_invulnerable_not_set_when_no_adjacent_enemy_at_landing():
    """Knight jumps over a piece, lands at a square with no enemies in
    the 8 chebyshev-1 neighbors. The v2 invulnerability condition fails;
    no protection is granted.

    This is the key test that breaks perpetual invulnerability cycles —
    a knight bouncing in safe space (no enemies nearby) cannot maintain
    invulnerability."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=False
    )
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # Jumped piece is the friendly pawn at (3,4). Landing (3,5)'s
    # adjacent squares contain no enemies (kings are at (7,7) and (0,0),
    # both far from (3,5)).
    assert knight.invulnerable is False, (
        "No adjacent enemy at landing → no invulnerability under v2"
    )


def test_invulnerable_not_set_when_only_adjacent_enemy_is_jumped_piece():
    """The 'adjacent enemy must not be the jumped piece' clause.

    Setup: knight jumps over an ENEMY pawn at the jumped square. The
    jumped piece is adjacent to the landing square (necessarily, by
    geometry of the jump). If no OTHER enemy is adjacent to the landing,
    the condition fails — the jumped piece doesn't count as the
    triggering adjacency."""
    # Knight at (3,3) jumping to (3,5). Jumped square (3,4) has an enemy
    # pawn — this enemy is adjacent to (3,5) but is the jumped piece.
    # No other enemies near the landing.
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('black'), with_adjacent_enemy=False
    )
    b.turn_number = 2
    # Stationary enemy (didn't move last turn) so it's not jump-capture
    # eligible and the move proceeds as a non-capture jump.
    _set_last_move(b, (5, 5), (5, 6), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # The jumped enemy at (3,4) IS adjacent to landing (3,5), but it
    # doesn't count for invulnerability — it's the jumped piece. No
    # other enemy is adjacent. No invulnerability.
    assert knight.invulnerable is False


def test_invulnerable_set_with_adjacent_enemy_at_landing_diagonal():
    """Adjacent enemy in a diagonal neighbor of the landing → invulnerability.

    Tests that 'adjacent' means chebyshev 1 (including diagonals), not
    only orthogonal neighbors."""
    # Jumped piece is friendly so we can isolate the adjacency check.
    # Place an enemy diagonally adjacent to the landing (3,5) at (2,6).
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=False
    )
    b.squares[2][6].piece = Pawn('black')  # diagonal-adjacent to (3,5)
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_set_with_adjacent_enemy_at_landing_orthogonal():
    """Adjacent enemy orthogonally next to the landing → invulnerability."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=False
    )
    # Place an enemy orthogonally adjacent to (3,5) at (3,6).
    b.squares[3][6].piece = Pawn('black')
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_set_when_jumping_friendly_with_adjacent_enemy():
    """Jumping over a friendly piece AND landing adjacent to an enemy
    (other than the friendly) → invulnerability granted.

    This is the canonical "weaving path" scenario: the knight uses a
    friendly piece as a stepping stone to penetrate near enemy lines."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=True
    )
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # Jumped piece is friendly pawn at (3,4). Adjacent enemy pawn at
    # (4,5). The adjacent enemy is different from the jumped piece.
    assert knight.invulnerable is True


def test_invulnerable_set_when_jumping_enemy_with_different_adjacent_enemy():
    """Jumping over enemy A AND landing adjacent to enemy B (different
    from A) → invulnerability. Confirms multi-enemy engagement."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('black'), with_adjacent_enemy=True
    )
    b.turn_number = 2
    # Stationary jumped enemy (no jump-capture); knight just jumps over.
    _set_last_move(b, (5, 5), (5, 6), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # Jumped enemy at (3,4), additional enemy at (4,5). The additional
    # enemy is different from jumped piece → invulnerability granted.
    assert knight.invulnerable is True


def test_invulnerable_set_when_jumping_boulder_with_adjacent_enemy():
    """Jumping over the boulder + landing adjacent to an enemy →
    invulnerability granted. The boulder isn't an enemy, so the 'other
    than jumped piece' check is trivially satisfied for any adjacent
    enemy."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 4, 5),  # adjacent to landing (3,5)
        ],
    )
    b.squares[3][4].piece = Boulder()
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_invulnerable_not_set_when_jumping_boulder_no_adjacent_enemy():
    """Jumping over the boulder with no adjacent enemy at landing →
    no invulnerability. Boulder is neutral and doesn't count as the
    adjacent enemy itself."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[(lambda: King('black'), 0, 0)],
    )
    b.squares[3][4].piece = Boulder()
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is False


def test_friendly_adjacent_does_not_satisfy_condition():
    """A friendly piece adjacent to the landing does NOT count as the
    adjacent enemy. The condition specifically requires an ENEMY adjacent."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=False
    )
    # Add a friendly white pawn adjacent to landing (3,5) — but no enemy.
    b.squares[4][5].piece = Pawn('white')
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is False, (
        "Friendly adjacent piece does not satisfy the v2 invulnerability "
        "condition — an ENEMY must be adjacent."
    )


def test_invulnerable_works_across_all_8_adjacent_directions():
    """For each of the 8 adjacent squares to the landing (3,5), placing
    a lone enemy there should trigger invulnerability. This sweeps the
    full chebyshev-1 ring to ensure the condition is symmetric."""
    landing = (3, 5)
    jumped = (3, 4)  # constant across the sweep
    # All 8 chebyshev-1 neighbors of (3,5), excluding the jumped square (3,4):
    adjacencies = [
        (2, 4), (2, 5), (2, 6),
        (3, 6),
        (4, 4), (4, 5), (4, 6),
        # (3, 4) is the jumped square; excluded.
    ]
    for adj in adjacencies:
        b = _make_board_with_pieces(
            white_pieces=[
                (lambda: King('white'), 7, 7),
                (lambda: Knight('white'), 3, 3),
            ],
            black_pieces=[(lambda: King('black'), 0, 0)],
        )
        # Friendly jumped piece so the move is a clean non-capture jump.
        b.squares[jumped[0]][jumped[1]].piece = Pawn('white')
        # Single adjacent enemy at the sweep position.
        b.squares[adj[0]][adj[1]].piece = Pawn('black')
        knight = b.squares[3][3].piece
        b.turn_number = 2
        b.move(knight, Move(Square(3, 3), Square(*landing)))
        assert knight.invulnerable is True, (
            f"Adjacent enemy at {adj} should trigger invulnerability"
        )


def test_invulnerable_set_when_adjacent_enemy_is_itself_invulnerable():
    """Adjacent-enemy condition is about ENGAGEMENT, not capturability.
    An invulnerable enemy still occupies its square and is still an
    opposing piece — the knight charging past one obstacle to land
    next to it still counts as cavalry-charge engagement, so
    invulnerability should be granted.

    Regression test: previously the helper used
    `has_capturable_enemy_piece`, which filters out invulnerable
    pieces, causing the moving knight to incorrectly fail the
    adjacent-enemy check when the only adjacent enemy was an
    invulnerable knight."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=False
    )
    # Place an invulnerable enemy knight adjacent to the landing (3,5).
    adj_knight = Knight('black')
    adj_knight.invulnerable = True
    b.squares[4][5].piece = adj_knight
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True, (
        "An invulnerable adjacent enemy should still satisfy the "
        "engagement-based adjacent-enemy condition."
    )


def test_invulnerable_set_when_adjacent_enemy_is_invulnerable_other_piece():
    """Same check for non-knight invulnerable pieces. Any opposing
    piece that occupies an adjacent square satisfies the condition,
    regardless of whether it is currently capturable."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('white'), with_adjacent_enemy=False
    )
    # Manipulation freeze can leave any opposing piece invulnerable.
    adj_rook = Rook('black')
    adj_rook.invulnerable = True
    b.squares[2][5].piece = adj_rook
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    assert knight.invulnerable is True


def test_jump_decline_invulnerability_set_with_invulnerable_adjacent_enemy():
    """Decline path uses the same engagement check, so an invulnerable
    adjacent enemy is also valid here."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('black'), with_adjacent_enemy=False
    )
    # Adjacent invulnerable enemy (not the jumped piece).
    adj_knight = Knight('black')
    adj_knight.invulnerable = True
    b.squares[4][5].piece = adj_knight
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    targets = b.move(knight, move)
    assert targets == [(3, 4)]
    b.set_invulnerable_after_jump_decline(
        knight, landing_row=3, landing_col=5, jumped_row=3, jumped_col=4
    )
    assert knight.invulnerable is True


def test_invulnerable_not_set_when_only_jumped_square_holds_enemy():
    """Adversarial: the only enemy at chebyshev 1 of the landing is the
    one at the jumped square. The condition explicitly excludes the
    jumped piece, so no invulnerability."""
    # Knight at (3,3), jumps over enemy pawn at (3,4), lands at (3,5).
    # Place no other enemies anywhere near (3,5).
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('black'), with_adjacent_enemy=False
    )
    b.turn_number = 2
    _set_last_move(b, (5, 5), (5, 6), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # Black king at (0,0) is the only other enemy; not adjacent. The
    # jumped pawn at (3,4) is adjacent but excluded. No invulnerability.
    assert knight.invulnerable is False


# -------------------------------------------------------------------------
# Section 7: execute_jump_capture interaction
# -------------------------------------------------------------------------

def test_jump_capture_executed_does_not_set_invulnerable():
    """When the player goes through with a jump-capture, the jumped piece
    is removed and invulnerability does NOT trigger (jumped piece didn't survive)."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Pawn('black'))
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)
    assert targets == [(3, 4)]
    # Now execute the capture (this is what the UI/engine would do on click)
    b.execute_jump_capture(3, 4)

    assert b.squares[3][4].piece is None  # jumped piece removed
    assert knight.invulnerable is False  # no invulnerability when capture happens


def test_jump_capture_declined_sets_invulnerable():
    """If the player declines the jump-capture and the v2 adjacent-enemy
    condition is met, invulnerability triggers. The declining behavior
    is performed by the caller (UI/engine) —
    Board.set_invulnerable_after_jump_decline provides the hook.

    The scenario uses _setup_jump_capture_scenario which by default
    places an adjacent enemy at (4,5), satisfying the v2 condition."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Pawn('black'))
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)
    assert targets == [(3, 4)]
    # Decline: caller invokes the helper with landing + jumped coords so
    # the helper can evaluate the v2 adjacent-enemy condition.
    b.set_invulnerable_after_jump_decline(
        knight, landing_row=3, landing_col=5, jumped_row=3, jumped_col=4
    )

    assert b.squares[3][4].piece is not None  # jumped piece survives
    assert knight.invulnerable is True


def test_jump_capture_declined_does_not_set_invulnerable_without_adjacent_enemy():
    """Decline path also respects the v2 adjacent-enemy condition.
    Without an adjacent enemy at the landing (other than the jumped
    piece), declining a jump-capture does NOT grant invulnerability."""
    b, knight, _ = _setup_jump_capture_scenario(
        lambda: Pawn('black'), with_adjacent_enemy=False
    )
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)
    assert targets == [(3, 4)]
    b.set_invulnerable_after_jump_decline(
        knight, landing_row=3, landing_col=5, jumped_row=3, jumped_col=4
    )

    # Jumped piece is the only enemy adjacent to landing; condition fails.
    assert knight.invulnerable is False


# -------------------------------------------------------------------------
# Section 8: Manipulation interaction
# -------------------------------------------------------------------------

def test_invulnerable_applies_when_knight_moved_via_manipulation():
    """If a queen manipulates an enemy knight into a jump, the knight
    still gets invulnerability flag set by Board.move (separate from the
    manipulation-clears-invulnerability rule in rulebook line 327, which
    runs at the start of the knight player's next own turn).

    The v2 adjacent-enemy condition still applies: a white piece is
    placed adjacent to the landing square so the invulnerability
    condition is met."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            # White pawn adjacent to landing (3,5) so the v2 invulnerability
            # condition is satisfied (an enemy of the black knight is
            # adjacent to its landing square, and is not the jumped piece).
            (lambda: Pawn('white'), 4, 5),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Knight('black'), 3, 3),
            (lambda: Pawn('black'), 3, 4),  # friendly to the manipulated knight
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    move = Move(Square(3, 3), Square(3, 5))
    b.move(knight, move)
    # Knight (black) jumped over its own pawn AND landed adjacent to
    # a white piece (4,5) other than the jumped piece → invulnerable
    assert knight.invulnerable is True


# -------------------------------------------------------------------------
# Section: Board.knight_mode for snapshot mainloops
# -------------------------------------------------------------------------
#
# main_v0.py and main_v1.py are frozen reference snapshots of older
# rule sets. They must preserve their original knight behaviour
# (capture any adjacent enemy to the landing square after a jump; no
# invulnerability) even as the active main.py uses the v2 redesign.
# This is implemented via `Board(knight_mode=...)`:
#   - `KNIGHT_MODE_V2`     — default; the current rules.
#   - `KNIGHT_MODE_LEGACY` — pre-v2 rules used by the snapshots.

def test_board_default_knight_mode_is_v2():
    from board import Board
    b = Board()
    assert b.knight_mode == Board.KNIGHT_MODE_V2


def test_board_knight_mode_can_be_legacy():
    from board import Board
    b = Board(knight_mode=Board.KNIGHT_MODE_LEGACY)
    assert b.knight_mode == Board.KNIGHT_MODE_LEGACY


def test_legacy_knight_returns_multiple_adjacent_capture_targets():
    """In legacy mode, the knight's jump can return MULTIPLE adjacent
    enemy targets (not just the jumped piece). This is the pre-v2
    behaviour that `main_v0.py` and `main_v1.py` expect."""
    from board import Board
    b = Board(knight_mode=Board.KNIGHT_MODE_LEGACY)
    # Clear the default setup so only our test pieces are on the board.
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    # Place a white knight at e4 and surround the e6 landing with enemies.
    b.squares[4][4].piece = Knight('white')
    b.squares[3][4].piece = Pawn('black')   # e5 — jumped piece
    b.squares[2][3].piece = Pawn('black')   # d6 — adjacent to landing e6
    b.squares[2][5].piece = Pawn('black')   # f6 — adjacent to landing e6
    knight = b.squares[4][4].piece
    move = Move(Square(4, 4), Square(2, 4))  # e4 -> e6
    targets = b.move(knight, move)
    # Legacy returns adjacent enemies to landing, not just jumped piece.
    assert targets is not None and len(targets) >= 2, (
        f"Legacy knight should return multiple adjacent-enemy targets; got {targets}"
    )
    targets_set = set(targets)
    assert (3, 4) in targets_set, "e5 (jumped piece) should be a target"
    assert (2, 3) in targets_set, "d6 (adjacent to landing) should be a target"
    assert (2, 5) in targets_set, "f6 (adjacent to landing) should be a target"


def test_legacy_knight_does_not_gain_invulnerability_on_non_capture_jump():
    """Legacy knight has no invulnerability mechanic at all."""
    from board import Board
    b = Board(knight_mode=Board.KNIGHT_MODE_LEGACY)
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[4][4].piece = Knight('white')
    b.squares[3][4].piece = Pawn('white')  # friendly jumped piece — no targets returned
    knight = b.squares[4][4].piece
    move = Move(Square(4, 4), Square(2, 4))
    b.move(knight, move)
    # Legacy: no invulnerability flag set, period.
    assert knight.invulnerable is False


def test_v2_knight_still_uses_reactive_capture_after_legacy_added():
    """Sanity: adding the legacy mode didn't break v2 behaviour."""
    from board import Board
    b = Board(knight_mode=Board.KNIGHT_MODE_V2)
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[4][4].piece = Knight('white')
    b.squares[3][4].piece = Pawn('black')   # eligible jumped piece if it moved last turn
    b.squares[2][3].piece = Pawn('black')   # adjacent to landing — NOT captureable in v2
    b.squares[2][5].piece = Pawn('black')   # adjacent to landing — NOT captureable in v2
    knight = b.squares[4][4].piece
    b.turn_number = 2
    b.last_move = Move(Square(2, 4), Square(3, 4))
    b.last_move_turn_number = 1
    move = Move(Square(4, 4), Square(2, 4))
    targets = b.move(knight, move)
    assert targets == [(3, 4)], (
        f"v2 knight must only return the jumped piece as target; got {targets}"
    )


def test_enemy_king_cannot_capture_invulnerable_knight():
    """v2: invulnerability protects from ALL captures, including the
    enemy king. The king's special capture powers (friendlies, boulder)
    do not override invulnerability — this keeps the 'invulnerable
    means uncapturable' rule simple and consistent."""
    from board import Board
    b = _make_board_with_pieces(
        white_pieces=[(lambda: King('white'), 3, 3), (lambda: Knight('white'), 7, 7)],
        black_pieces=[(lambda: King('black'), 0, 0), (lambda: Knight('black'), 3, 4)],
    )
    enemy_knight = b.squares[3][4].piece
    enemy_knight.invulnerable = True
    king = b.squares[3][3].piece
    b.king_moves(king, 3, 3)
    dests = [(m.final.row, m.final.col) for m in king.moves]
    assert (3, 4) not in dests, (
        "Enemy king must not be able to capture an invulnerable knight"
    )


def test_friendly_king_cannot_capture_invulnerable_friendly_knight():
    """v2: invulnerability is universal protection during its single
    turn — even the friendly king (who normally CAN capture friendly
    pieces to free squares) cannot capture an invulnerable friendly
    knight."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 3, 3),
            (lambda: Knight('white'), 3, 4),  # friendly knight, invulnerable
        ],
        black_pieces=[(lambda: King('black'), 0, 0)],
    )
    friendly_knight = b.squares[3][4].piece
    friendly_knight.invulnerable = True
    king = b.squares[3][3].piece
    b.king_moves(king, 3, 3)
    dests = [(m.final.row, m.final.col) for m in king.moves]
    assert (3, 4) not in dests, (
        "Friendly king must not be able to capture an invulnerable "
        "friendly knight either — invulnerability is universal"
    )


def test_king_can_still_capture_non_invulnerable_pieces():
    """Sanity: the king's special capture power is unchanged for
    pieces that are NOT invulnerable. Friendly pieces, enemy pieces,
    boulder — all still capturable as before."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 3, 3),
            (lambda: Pawn('white'), 3, 4),    # friendly, not invulnerable
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Pawn('black'), 3, 2),    # enemy, not invulnerable
        ],
    )
    king = b.squares[3][3].piece
    b.king_moves(king, 3, 3)
    dests = [(m.final.row, m.final.col) for m in king.moves]
    # Adjacent squares with non-invulnerable pieces should be capturable.
    assert (3, 4) in dests, "King can still capture friendly non-invulnerable pawn"
    assert (3, 2) in dests, "King can still capture enemy non-invulnerable pawn"


def test_manipulated_knight_is_not_effectively_invulnerable():
    """Pin the 'View A' choice for the manipulation + invulnerability
    interaction: when a knight is moved via queen manipulation and
    jumps over a piece, the invulnerable flag IS briefly set by
    Board.move, but Game.next_turn (which clears invulnerable on the
    new current player's pieces) immediately clears it before the
    knight's own turn begins.

    Net effect: manipulated knights gain no functional invulnerability.
    Their owner's friendly king CAN capture them on the knight player's
    own turn (no protection to override), and the manipulator can
    attack them normally on their next turn.

    This pins the current behaviour so future refactors don't
    accidentally turn it into View B (where the rule would propagate
    invulnerability across the manipulator's player switch)."""
    g = Game()
    b = g.board
    # Manually set up a knight that just gained invulnerability mid-move.
    # We simulate the post-move state directly: knight has invulnerable
    # set, next_player switches to knight's owner.
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.squares[3][4].piece = Knight('black')
    knight = b.squares[3][4].piece
    knight.invulnerable = True
    # We're currently in white's turn (manipulator). Simulate end of
    # white's turn: next_turn switches to black and clears its
    # invulnerable flags.
    g.next_player = 'white'
    g.next_turn()
    # After next_turn: next_player is now 'black' (knight's owner).
    assert g.next_player == 'black'
    # Manipulated knight's invulnerable flag was cleared.
    assert knight.invulnerable is False, (
        "Manipulated knight should not be effectively invulnerable on "
        "its owner's own turn (View A)."
    )


def test_manipulated_knight_with_recent_move_is_jump_capture_eligible():
    """If the white queen manipulates the black knight into moving onto
    a square reachable by a jump from another white knight, the manipulated
    knight DID make a spatial move on the immediately preceding turn —
    so on white's next turn, white's other knight can jump-capture it."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[
            (lambda: King('black'), 0, 0),
            (lambda: Knight('black'), 3, 4),  # the manipulated piece
        ],
    )
    knight = b.squares[3][3].piece
    b.turn_number = 2
    # Simulate: black's knight was manipulated on the immediately preceding turn,
    # ending up at (3,4). last_move records that move.
    _set_last_move(b, (5, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    targets = b.move(knight, move)

    # The black knight at (3,4) IS jump-capture eligible (it moved last turn,
    # even via manipulation — any spatial move counts).
    assert targets == [(3, 4)]


# -------------------------------------------------------------------------
# Section 9: Visual overlay for invulnerable pieces
# -------------------------------------------------------------------------
#
# `compute_piece_overlays(piece)` returns a list of overlay specs to render
# on a piece's square. Each spec is a dict with at least 'kind' and
# 'position' keys; the renderer in game.show_pieces uses these to layer
# small icons (queen marker for royal-transformed, pawn marker for non-
# royal queen/transformed, and a shield icon for invulnerable pieces).
# The shield must NOT collide with the queen/pawn marker — positions
# must be unique across all overlays returned for a given piece.

from game import compute_piece_overlays


def test_compute_piece_overlays_empty_for_basic_pawn():
    p = Pawn('white')
    overlays = compute_piece_overlays(p)
    assert overlays == []


def test_compute_piece_overlays_empty_for_basic_knight():
    n = Knight('white')
    overlays = compute_piece_overlays(n)
    assert overlays == []


def test_compute_piece_overlays_shield_for_invulnerable_knight():
    n = Knight('white')
    n.invulnerable = True
    overlays = compute_piece_overlays(n)
    kinds = [o['kind'] for o in overlays]
    assert 'shield' in kinds


def test_compute_piece_overlays_no_shield_for_non_invulnerable_knight():
    n = Knight('white')
    n.invulnerable = False
    overlays = compute_piece_overlays(n)
    kinds = [o['kind'] for o in overlays]
    assert 'shield' not in kinds


def test_compute_piece_overlays_queen_marker_for_royal_transformed():
    """Royal queen transformed into a piece type: queen marker shown."""
    q = Queen('white', is_royal=True)
    q.is_transformed = True
    overlays = compute_piece_overlays(q)
    kinds = [o['kind'] for o in overlays]
    assert 'queen_marker' in kinds


def test_compute_piece_overlays_pawn_marker_for_non_royal_queen_or_transformed():
    """Promoted queen (non-royal) always shows the pawn marker so it can
    be distinguished from the royal queen."""
    q = Queen('white', is_royal=False)
    overlays = compute_piece_overlays(q)
    kinds = [o['kind'] for o in overlays]
    assert 'pawn_marker' in kinds


def test_compute_piece_overlays_shield_and_queen_marker_coexist():
    """A royal queen transformed into a knight that is currently
    invulnerable should show BOTH the queen marker (to indicate it's
    the royal queen in disguise) AND the shield (invulnerability)."""
    q = Queen('white', is_royal=True)
    q.is_transformed = True
    q.invulnerable = True
    overlays = compute_piece_overlays(q)
    kinds = {o['kind'] for o in overlays}
    assert 'queen_marker' in kinds
    assert 'shield' in kinds


def test_compute_piece_overlays_shield_and_pawn_marker_coexist():
    """A promoted queen transformed into a knight that is currently
    invulnerable should show BOTH the pawn marker (non-royal indicator)
    AND the shield (invulnerability)."""
    q = Queen('white', is_royal=False)
    q.is_transformed = True
    q.invulnerable = True
    overlays = compute_piece_overlays(q)
    kinds = {o['kind'] for o in overlays}
    assert 'pawn_marker' in kinds
    assert 'shield' in kinds


def test_compute_piece_overlays_shield_and_marker_in_different_corners():
    """When both a marker (queen or pawn) and the shield are shown,
    they must occupy different corners to avoid visual collision."""
    q = Queen('white', is_royal=True)
    q.is_transformed = True
    q.invulnerable = True
    overlays = compute_piece_overlays(q)
    positions = [o['position'] for o in overlays]
    assert len(positions) == len(set(positions)), (
        f"Overlay positions must be unique; got {positions}"
    )


def test_compute_piece_overlays_shield_for_any_invulnerable_piece_type():
    """The shield is shown for any invulnerable piece (knight being the
    typical case in v2, but other pieces can be invulnerable in engine
    manipulation variants — the indicator is generic)."""
    for piece in (Pawn('white'), Rook('white'), Bishop('white'), Knight('white')):
        piece.invulnerable = True
        overlays = compute_piece_overlays(piece)
        kinds = [o['kind'] for o in overlays]
        assert 'shield' in kinds, f"{type(piece).__name__} missing shield overlay"


def test_compute_piece_overlays_each_spec_has_required_keys():
    """Every overlay spec returned by compute_piece_overlays must have
    at least 'kind' and 'position' keys. This pins the contract for the
    renderer."""
    q = Queen('white', is_royal=True)
    q.is_transformed = True
    q.invulnerable = True
    overlays = compute_piece_overlays(q)
    for ov in overlays:
        assert 'kind' in ov
        assert 'position' in ov


def test_compute_piece_overlays_queen_pawn_markers_are_image_backed():
    """The queen and pawn markers are PNG-backed (loaded from disk and
    blitted). Each must therefore include an 'asset' key pointing to a
    .png file."""
    # Royal-transformed queen → queen marker.
    q = Queen('white', is_royal=True)
    q.is_transformed = True
    overlays = compute_piece_overlays(q)
    image_overlays = [o for o in overlays if o.get('render_kind') == 'image']
    assert len(image_overlays) == 1
    assert image_overlays[0]['kind'] == 'queen_marker'
    assert 'asset' in image_overlays[0]
    assert image_overlays[0]['asset'].endswith('.png')


def test_compute_piece_overlays_shield_is_vector_backed():
    """The shield overlay is rendered as a stack of antialiased vector
    polygons via pygame.gfxdraw — sharp at any scale, no raster source.
    The spec carries `render_kind: 'shield_vector'` and a `shield_id`
    key (not an `asset` path)."""
    n = Knight('white')
    n.invulnerable = True
    overlays = compute_piece_overlays(n)
    shield = [o for o in overlays if o['kind'] == 'shield']
    assert len(shield) == 1
    ov = shield[0]
    assert ov['render_kind'] == 'shield_vector'
    assert 'shield_id' in ov
    assert 'asset' not in ov, "shield is vector-rendered, no PNG asset"


def test_compute_piece_overlays_shield_id_uses_piece_color():
    """The shield's `shield_id` is colour-keyed by the piece's side, just
    like the image-backed queen/pawn markers. A white piece's shield
    looks up `white_shield`; a black piece's shield looks up
    `black_shield`."""
    for color, expected_id in (('white', 'white_shield'),
                               ('black', 'black_shield')):
        n = Knight(color)
        n.invulnerable = True
        overlays = compute_piece_overlays(n)
        shield_overlays = [o for o in overlays if o['kind'] == 'shield']
        assert len(shield_overlays) == 1
        assert shield_overlays[0]['shield_id'] == expected_id, (
            f"For {color} knight, expected shield_id={expected_id!r}, "
            f"got {shield_overlays[0]['shield_id']!r}"
        )


def test_shield_polygons_module_has_both_colors():
    """The auto-generated shield_polygons module must export polygon
    data for both `white_shield` and `black_shield` so the renderer
    can look them up by id."""
    from shield_polygons import SHIELD_POLYGONS
    assert 'white_shield' in SHIELD_POLYGONS
    assert 'black_shield' in SHIELD_POLYGONS


def test_shield_polygons_have_layered_structure():
    """Each shield's polygon list must have multiple layers (at minimum
    the outer silhouette plus an inner detail layer). Each layer is a
    dict with a hex color and a list of (x, y) normalized vertices."""
    from shield_polygons import SHIELD_POLYGONS
    for shield_id, layers in SHIELD_POLYGONS.items():
        assert len(layers) >= 2, f"{shield_id} should have >=2 layers"
        for layer in layers:
            assert 'color' in layer
            assert layer['color'].startswith('#') and len(layer['color']) == 7
            assert 'points' in layer
            assert len(layer['points']) >= 3
            for pt in layer['points']:
                assert isinstance(pt, tuple) and len(pt) == 2
                px, py = pt
                assert 0.0 <= px <= 1.0, f"{shield_id} x out of range: {px}"
                assert 0.0 <= py <= 1.0, f"{shield_id} y out of range: {py}"


def test_compute_piece_overlays_does_not_show_shield_for_boulder():
    """Boulders aren't capturable by enemies in the first place; they
    don't need an invulnerability indicator. Even if the flag is set
    (defensive), boulders shouldn't get the shield — it would be
    visually meaningless."""
    b = Boulder()
    b.invulnerable = True  # nonsensical but let's not crash
    overlays = compute_piece_overlays(b)
    kinds = [o['kind'] for o in overlays]
    assert 'shield' not in kinds


# -------------------------------------------------------------------------
# Section: Invulnerability interaction with every move generator
# -------------------------------------------------------------------------
#
# These tests pin the contract for every Board move generator and every
# rule-check that consults either Square.has_enemy_piece (broad — any
# opposing-colour presence) or Square.has_capturable_enemy_piece
# (narrow — opposing-colour, not boulder, not currently invulnerable).
#
# The intent is to lock in the correct semantic for each location so a
# future refactor can't silently break the rule by swapping one helper
# for the other.
#
# Capture-decision sites must use the NARROW helper (you can only
# capture pieces that are actually capturable). Engagement / presence /
# threat / blocker sites must use the BROAD helper (an invulnerable
# enemy still occupies its square, still threatens what it threatens,
# and still blocks line of sight).


def _bare_board(white_pieces=None, black_pieces=None):
    """Build a board with default kings + the given pieces. Returns the board."""
    extras_w = white_pieces or []
    extras_b = black_pieces or []
    return _make_board_with_pieces(
        white_pieces=[(lambda: King('white'), 7, 7)] + extras_w,
        black_pieces=[(lambda: King('black'), 0, 0)] + extras_b,
    )


# ---- 1. Knight standard capture (radius 2) ----

def test_knight_cannot_standard_capture_invulnerable_enemy():
    """A knight cannot land on a square holding an invulnerable enemy.

    The narrow helper (used internally by `isempty_or_enemy` which
    `knight_moves` consults) filters out invulnerable enemies, so the
    move is never generated."""
    b = _bare_board()
    knight = Knight('white')
    b.squares[3][3].piece = knight
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[3][5].piece = enemy  # radius-2 from knight (2-orthogonal)
    b.knight_moves(knight, 3, 3)
    dests = [(m.final.row, m.final.col) for m in knight.moves]
    assert (3, 5) not in dests, (
        "Knight must not be able to standard-capture an invulnerable enemy"
    )


def test_knight_can_standard_capture_non_invulnerable_enemy():
    """Sanity: capturable enemy is still a valid landing for the knight."""
    b = _bare_board()
    knight = Knight('white')
    b.squares[3][3].piece = knight
    b.squares[3][5].piece = Knight('black')  # capturable
    b.knight_moves(knight, 3, 3)
    dests = [(m.final.row, m.final.col) for m in knight.moves]
    assert (3, 5) in dests


# ---- 2. Knight jump-capture eligibility ----

def test_knight_cannot_jump_capture_invulnerable_jumped_enemy():
    """`_can_jump_capture` uses the narrow helper, so an invulnerable
    jumped enemy cannot be jump-captured even when the move-timing
    eligibility is met."""
    b = _bare_board()
    knight = Knight('white')
    b.squares[3][3].piece = knight
    enemy = Pawn('black')
    enemy.invulnerable = True  # jumped piece is invulnerable
    b.squares[3][4].piece = enemy
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))
    targets = b.move(knight, move)
    assert not targets, (
        "An invulnerable jumped piece must not be jump-capturable; "
        f"got targets {targets}"
    )


# ---- 3. Pawn diagonal capture ----

def test_pawn_cannot_capture_invulnerable_diagonal_enemy():
    """Pawn diagonal capture uses the narrow helper — invulnerable
    enemy on a pawn's diagonal capture square is not capturable."""
    b = _bare_board()
    pawn = Pawn('white')
    b.squares[5][4].piece = pawn  # white pawn on e3-equivalent
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[4][5].piece = enemy  # diagonal-forward from white pawn
    b.pawn_moves(pawn, 5, 4)
    dests = [(m.final.row, m.final.col) for m in pawn.moves]
    assert (4, 5) not in dests, (
        "Pawn must not be able to diagonally capture an invulnerable enemy"
    )


def test_pawn_can_capture_non_invulnerable_diagonal_enemy():
    b = _bare_board()
    pawn = Pawn('white')
    b.squares[5][4].piece = pawn
    b.squares[4][5].piece = Knight('black')  # capturable
    b.pawn_moves(pawn, 5, 4)
    dests = [(m.final.row, m.final.col) for m in pawn.moves]
    assert (4, 5) in dests


# ---- 4. Queen base-form adjacent capture ----

def test_queen_base_cannot_capture_invulnerable_adjacent_enemy():
    """Queen in base form captures adjacent (1 square) enemies. Uses
    the narrow helper via `isempty_or_enemy`."""
    b = _bare_board()
    queen = Queen('white', is_royal=True)
    b.squares[3][3].piece = queen
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[3][4].piece = enemy
    b.queen_moves(queen, 3, 3)
    dests = [(m.final.row, m.final.col) for m in queen.moves]
    assert (3, 4) not in dests


# ---- 5. Rook step-1 capture and step-2 blocker ----

def test_rook_cannot_capture_invulnerable_step1_enemy():
    """Already covered in test_piece_movement.py, but echoed here for
    a single self-contained suite that exercises every piece."""
    b = _bare_board()
    rook = Rook('white')
    b.squares[7][4].piece = rook
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[6][4].piece = enemy
    b.rook_moves(rook, 7, 4)
    dests = [(m.final.row, m.final.col) for m in rook.moves]
    assert (6, 4) not in dests


def test_rook_invulnerable_enemy_blocks_step2_sweep():
    b = _bare_board()
    rook = Rook('white')
    b.squares[7][4].piece = rook
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[6][6].piece = enemy  # in the perpendicular sweep path
    b.rook_moves(rook, 7, 4)
    dests = [(m.final.row, m.final.col) for m in rook.moves]
    assert (6, 6) not in dests, "must not capture invulnerable enemy in step-2"
    # And must not pass through:
    assert (6, 7) not in dests, "must not pass through invulnerable enemy"


# ---- 6. Bishop reactive capture ----

def test_bishop_reactive_capture_filters_invulnerable_target():
    """Bishop assassin capture requires `has_capturable_enemy_piece` at
    the destination — an invulnerable target at the moment of the
    bishop's turn cannot be captured."""
    b = _bare_board()
    bishop = Bishop('white')
    b.squares[7][7].piece = bishop  # at h1
    # Place an enemy on bishop's diagonal that just moved.
    enemy = Pawn('black')
    enemy.invulnerable = True
    b.squares[5][5].piece = enemy
    bishop.assassin_squares = [Square(6, 6)]  # the square the enemy left
    b.last_move = Move(Square(6, 6), Square(5, 5))
    b.bishop_moves(bishop, 7, 7)
    # The reactive-capture move should NOT exist because the target is
    # currently invulnerable.
    dests = [(m.final.row, m.final.col) for m in bishop.moves]
    assert (5, 5) not in dests


# ---- 7. Bishop teleport threat scan (broad) ----
#
# The bishop's teleport must avoid squares threatened by ENEMIES of
# any kind — including invulnerable ones, because their threats persist
# even though they can't be captured this turn. This uses the broad
# `has_enemy_piece` helper. Tested in test_piece_movement (the
# `test_bishop_avoids_threats_of_invulnerable_enemy_knight` test);
# we add an explicit cross-check below.

def test_bishop_threat_scan_includes_invulnerable_enemy():
    """Confirm bishop_moves uses the broad helper when collecting
    enemy threat squares: an invulnerable enemy's threats are still
    considered when filtering teleport destinations."""
    b = _bare_board()
    bishop = Bishop('white')
    b.squares[0][7].piece = bishop  # h8
    # Invulnerable enemy knight whose threats cover some squares.
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[4][4].piece = enemy
    # Compute the knight's threat squares so they're populated on
    # the piece object before bishop_moves runs.
    b.update_threat_squares()
    b.bishop_moves(bishop, 0, 7)
    # The knight at (4,4) threatens (e.g.) (2, 5) at radius-2. The
    # bishop must NOT teleport there.
    dests = [(m.final.row, m.final.col) for m in bishop.moves]
    # Spot-check one square the knight controls and that the bishop
    # could otherwise reach (an empty square not adjacent to other
    # pieces).
    assert (2, 5) not in dests, (
        "Bishop teleport must avoid squares threatened by an "
        "invulnerable enemy knight"
    )


# ---- 8. Bishop assassin-square registration (broad) ----

def test_bishop_assassin_registers_invulnerable_enemies():
    """`update_assassin_squares` uses the broad helper so an
    invulnerable enemy in the bishop's LOS is still registered. By
    the time the bishop's turn comes, the enemy's invulnerability
    will likely have expired, and the assassin capture will fire."""
    b = _bare_board()
    bishop = Bishop('white')
    b.squares[7][7].piece = bishop
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[4][4].piece = enemy  # on bishop's diagonal
    b.update_assassin_squares('white')
    assassin_squares_set = {(sq.row, sq.col) for sq in bishop.assassin_squares}
    assert (4, 4) in assassin_squares_set, (
        "Invulnerable enemy in the bishop's diagonal LOS must still "
        "be registered as an assassin target"
    )


# ---- 9. Knight invulnerability adjacent-enemy check (broad) ----
#
# This was the bug we fixed earlier: invulnerable adjacent enemies
# must count as engagement for the v2 invulnerability condition.
# Already covered by tests in Section 6b; we add a self-check here
# to keep this section comprehensive.

def test_knight_invulnerability_adjacent_check_counts_invulnerable_enemy():
    b = _bare_board()
    knight = Knight('white')
    b.squares[3][3].piece = knight
    # Friendly jumped piece so the move is a non-capture jump.
    b.squares[3][4].piece = Pawn('white')
    # Invulnerable enemy adjacent to the landing (3,5).
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[4][5].piece = enemy
    b.turn_number = 2
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is True


# ---- 10. Manipulation freeze-setting check (broad) ----
#
# When the manipulator finishes a manipulation move, the freeze flag
# must be applied to the manipulated enemy piece — even if that piece
# happens to be invulnerable (e.g., a v2 knight that gained
# invulnerability from the manipulated jump). This is the bug we
# fixed in main.py; the unit-level contract test lives in
# test_v2_freeze.py. We replicate one assertion here for parity.

def test_manipulation_freeze_inclusion_of_invulnerable_piece():
    """The contract: the freeze-setting orchestration should use the
    broad helper so an invulnerable enemy at the destination still
    receives moved_by_queen=True."""
    b = _bare_board()
    enemy = Knight('black')
    enemy.invulnerable = True
    b.squares[3][3].piece = enemy
    # Mirror the orchestration line in main.py: if it's an enemy of
    # 'white' (the manipulator), apply the freeze.
    if b.squares[3][3].has_enemy_piece('white'):
        b.squares[3][3].piece.moved_by_queen = True
    assert enemy.moved_by_queen is True
    # The wrong helper (narrow) would have skipped this:
    enemy.moved_by_queen = False
    if b.squares[3][3].has_capturable_enemy_piece('white'):
        b.squares[3][3].piece.moved_by_queen = True
    assert enemy.moved_by_queen is False, (
        "Documentation check: the narrow helper filters invulnerable "
        "enemies, which is why manipulation freeze must NOT use it."
    )


# ---- 11. queen_moves_enemy find-friendly-queen check (broad) ----
#
# Regression test for the brittle issue surfaced by the audit: if a
# manipulator's queen is ever invulnerable (rare today; possible in
# some manipulation variants), it must still be eligible to perform
# the manipulation action. The check looks for "is there a queen of
# the manipulator's colour here?" — a presence check, not a
# capturability check.

def test_queen_moves_enemy_finds_invulnerable_manipulator_queen():
    """An invulnerable manipulator-coloured queen can still
    manipulate an enemy piece in its line of sight."""
    b = _bare_board()
    # White (manipulator) queen, invulnerable.
    wq = Queen('white', is_royal=True)
    wq.invulnerable = True
    b.squares[3][3].piece = wq
    # Black enemy piece in the queen's file (LOS via the column).
    enemy = Rook('black')
    b.squares[0][3].piece = enemy
    b.turn_number = 5
    b.last_move_turn_number = 1  # no recent move blocks manipulation
    b.update_lines_of_sight()
    b.update_threat_squares()
    b.queen_moves_enemy(enemy, 0, 3)
    dests = [(m.final.row, m.final.col) for m in enemy.moves]
    assert len(dests) > 0, (
        "Manipulation must work even when the manipulator's queen is "
        "currently invulnerable; the find-queen check is engagement-"
        "based, not capturability-based."
    )
