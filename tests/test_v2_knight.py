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
- `Square.has_enemy_piece` returns False for invulnerable pieces.
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


def test_has_enemy_piece_returns_false_for_invulnerable_knight():
    """A invulnerable knight cannot be captured by enemies."""
    b = _make_board_with_pieces(
        white_pieces=[(lambda: Knight('white'), 3, 3)],
        black_pieces=[],
    )
    knight = b.squares[3][3].piece
    knight.invulnerable = True
    # From black's perspective, the knight at (3,3) should not be a capture target
    assert b.squares[3][3].has_enemy_piece('black') is False


def test_has_enemy_piece_returns_true_for_non_invulnerable_knight():
    """A non-invulnerable knight is capturable as normal."""
    b = _make_board_with_pieces(
        white_pieces=[(lambda: Knight('white'), 3, 3)],
        black_pieces=[],
    )
    assert b.squares[3][3].has_enemy_piece('black') is True


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

def _setup_jump_capture_scenario(jumped_piece_factory, jumped_color_attr=None):
    """Set up a board where a white knight at (3,3) can jump over (3,4)
    to land at (3,5), with the jumped square holding the given piece.

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
    """Boulder cannot be captured by knight. invulnerability still triggers."""
    b = _make_board_with_pieces(
        white_pieces=[
            (lambda: King('white'), 7, 7),
            (lambda: Knight('white'), 3, 3),
        ],
        black_pieces=[(lambda: King('black'), 0, 0)],
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
    """Boulder can't be captured by knight → survives → invulnerability."""
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
    """If the player declines the jump-capture, the jumped piece survives
    and invulnerability triggers. The declining behavior is performed by the caller
    (UI/engine) — Board.set_invulnerable_after_jump_decline provides the hook."""
    b, knight, _ = _setup_jump_capture_scenario(lambda: Pawn('black'))
    b.turn_number = 2
    _set_last_move(b, (2, 4), (3, 4), turn_number_at_move=1)
    move = Move(Square(3, 3), Square(3, 5))

    targets = b.move(knight, move)
    assert targets == [(3, 4)]
    # Decline: caller invokes the helper to set invulnerability since the player
    # chose not to capture.
    b.set_invulnerable_after_jump_decline(knight)

    assert b.squares[3][4].piece is not None  # jumped piece survives
    assert knight.invulnerable is True


# -------------------------------------------------------------------------
# Section 8: Manipulation interaction
# -------------------------------------------------------------------------

def test_invulnerable_applies_when_knight_moved_via_manipulation():
    """If a queen manipulates an enemy knight into a jump, the knight
    still gets invulnerability (the rule reads 'knight made a move that jumps over
    a piece', not 'the knight's owner initiated the move')."""
    b = _make_board_with_pieces(
        white_pieces=[(lambda: King('white'), 7, 7)],
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
    # Knight (black) jumped over its own pawn → invulnerable
    assert knight.invulnerable is True


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


def test_compute_piece_overlays_all_image_render_kind():
    """Every overlay returned by compute_piece_overlays is currently
    image-rendered (PNG-backed) — queen marker, pawn marker, and shield
    are all loaded as images. Each must therefore include an 'asset'
    key pointing to a .png file."""
    q = Queen('white', is_royal=True)
    q.is_transformed = True
    q.invulnerable = True
    overlays = compute_piece_overlays(q)
    # Two overlays expected: queen_marker + shield.
    assert len(overlays) == 2
    for ov in overlays:
        assert ov.get('render_kind') == 'image', f"expected image render_kind, got {ov!r}"
        assert 'asset' in ov, f"overlay missing 'asset' key: {ov!r}"
        assert ov['asset'].endswith('.png'), f"asset is not a .png: {ov['asset']!r}"


def test_compute_piece_overlays_shield_asset_uses_piece_color():
    """The shield's asset path is colour-keyed by the piece's side, just
    like the queen and pawn markers. A white piece's shield loads from
    `white_shield.png`; a black piece's shield from `black_shield.png`."""
    for color, expected_filename in (('white', 'white_shield.png'),
                                     ('black', 'black_shield.png')):
        n = Knight(color)
        n.invulnerable = True
        overlays = compute_piece_overlays(n)
        shield_overlays = [o for o in overlays if o['kind'] == 'shield']
        assert len(shield_overlays) == 1
        assert shield_overlays[0]['asset'].endswith(expected_filename), (
            f"For {color} knight, expected asset ending with "
            f"{expected_filename}, got {shield_overlays[0]['asset']!r}"
        )


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
