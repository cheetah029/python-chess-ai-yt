"""Tests for the rulebook clarification: the boulder may capture
pawns of EITHER colour, including the moving player's own pawn.

User asked: should the boulder be able to capture pawns that are
the same colour as the player to move?

Engine inspection (src/board.py boulder_moves) shows the current
behaviour: the only filter on the boulder's capture is
`isinstance(target.piece, Pawn)` — NO colour check. So a same-
colour pawn IS capturable.

Rationale (to be documented in both rulebooks):
- The boulder is NEUTRAL (color = 'none'). It is owned by neither
  side. The standard "no same-colour capture" rule applies to
  OWNED pieces capturing pieces of their owner's colour; a neutral
  piece has no owner and so has no "same colour" to violate.
- The "boulder is treated as friendly by both sides for most
  purposes" clause governs how OTHER pieces treat the boulder
  (e.g. invuln support, manipulation eligibility); it does NOT
  restrict the boulder's own capture rules.
- The boulder's own capture rule says it "may capture pawns only"
  — that's the entire restriction. No colour qualifier.

Strategic note: capturing your own pawn via boulder is rarely
useful (it removes your own material) but is occasionally a
positional tool — clear a key square, dispose of a pawn the
opponent could otherwise manipulate, etc. The rule simply allows
it; it does not require the player to make use of it.

These tests verify the engine matches the documented rule.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Use mocked-pygame for the engine-level tests (the engine doesn't
# need a display). The conftest fixture loads the stub.
import pytest


@pytest.fixture(autouse=True)
def _stub_pygame_if_needed():
    if 'pygame' not in sys.modules:
        # Minimal stub so board.py / piece.py imports work headlessly.
        import types
        pg = types.ModuleType('pygame')
        sys.modules['pygame'] = pg


# ---- helper: clear board, place pieces by hand ----------------------------

def _make_clean_board():
    """Construct a Board, then empty every square so we can plant a
    minimal test position. Returns the Board."""
    from board import Board
    b = Board()
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    return b


def _place(b, r, c, piece):
    b.squares[r][c].piece = piece


def _legal_dests(b, piece, r, c):
    """Compute the legal destinations for `piece` at (r, c) using the
    boulder's mover. Returns a set of (row, col) tuples."""
    piece.clear_moves()
    b.boulder_moves(piece, r, c)
    return {(m.final.row, m.final.col) for m in piece.moves}


# ---- the central question --------------------------------------------------

def test_boulder_can_capture_white_pawn_when_white_to_move():
    """Rulebook clarification: boulder captures any pawn regardless
    of colour. White-to-move + white pawn adjacent to boulder —
    boulder may capture it."""
    from piece import Boulder, Pawn
    b = _make_clean_board()
    boulder = Boulder()
    boulder.first_move = False  # past the first-move constraint
    boulder.on_intersection = False
    boulder.cooldown = 0
    _place(b, 4, 4, boulder)  # boulder at d5
    # White pawn at d4 (one square south of boulder).
    white_pawn = Pawn('white')
    _place(b, 5, 4, white_pawn)
    dests = _legal_dests(b, boulder, 4, 4)
    assert (5, 4) in dests, (
        f"boulder at (4,4) should be able to capture WHITE pawn at "
        f"(5,4); legal dests were {dests}")


def test_boulder_can_capture_black_pawn_when_white_to_move():
    """Symmetric sanity: capturing an enemy pawn is also allowed
    (the rulebook never prohibited this)."""
    from piece import Boulder, Pawn
    b = _make_clean_board()
    boulder = Boulder()
    boulder.first_move = False
    boulder.on_intersection = False
    boulder.cooldown = 0
    _place(b, 4, 4, boulder)
    black_pawn = Pawn('black')
    _place(b, 5, 4, black_pawn)
    dests = _legal_dests(b, boulder, 4, 4)
    assert (5, 4) in dests, (
        f"boulder should be able to capture BLACK pawn; got dests "
        f"{dests}")


def test_boulder_cannot_capture_non_pawn_regardless_of_colour():
    """The rule restricts capture to pawns. A friendly knight in the
    boulder's adjacency must NOT be a legal capture destination —
    the boulder's "captures pawns only" rule blocks the move."""
    from piece import Boulder, Knight
    b = _make_clean_board()
    boulder = Boulder()
    boulder.first_move = False
    boulder.on_intersection = False
    boulder.cooldown = 0
    _place(b, 4, 4, boulder)
    knight = Knight('white')
    _place(b, 5, 4, knight)
    dests = _legal_dests(b, boulder, 4, 4)
    assert (5, 4) not in dests


def test_boulder_capture_of_friendly_pawn_uses_pawn_capture_branch():
    """The same-colour capture-pawn case should be treated identically
    to the enemy-pawn capture case — both go through the boulder's
    "is_pawn_capture" branch. This guards against future refactors
    that might add a colour gate."""
    from piece import Boulder, Pawn
    b = _make_clean_board()
    boulder = Boulder()
    boulder.first_move = False
    boulder.on_intersection = False
    boulder.cooldown = 0
    _place(b, 4, 4, boulder)
    # White pawn directly east of boulder.
    white_pawn = Pawn('white')
    _place(b, 4, 5, white_pawn)
    # Black pawn directly west of boulder.
    black_pawn = Pawn('black')
    _place(b, 4, 3, black_pawn)
    dests = _legal_dests(b, boulder, 4, 4)
    assert (4, 5) in dests, "boulder should capture white pawn east"
    assert (4, 3) in dests, "boulder should capture black pawn west"


def test_boulder_returning_to_capture_friendly_pawn_via_no_return_exception():
    """The no-return-memory rule has an exception for captures. Both
    enemy AND friendly pawn captures should trigger the exception
    (the rule keys on 'is this a pawn capture', not 'is this an
    enemy pawn capture')."""
    from piece import Boulder, Pawn
    b = _make_clean_board()
    boulder = Boulder()
    boulder.first_move = False
    boulder.on_intersection = False
    boulder.cooldown = 0
    boulder.last_square = (4, 5)  # boulder's most recent square
    _place(b, 4, 4, boulder)
    # White pawn at the no-return square — boulder should still be
    # able to RETURN there (since capture overrides the no-return rule
    # per the rulebook's "Exception — captures" clause).
    white_pawn = Pawn('white')
    _place(b, 4, 5, white_pawn)
    dests = _legal_dests(b, boulder, 4, 4)
    assert (4, 5) in dests, (
        f"boulder should be able to capture-return to (4,5) holding "
        f"a WHITE pawn — capture exception applies to either "
        f"colour. Got dests: {dests}")
