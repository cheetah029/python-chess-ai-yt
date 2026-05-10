"""Tests for v2 game-level undo/redo and jump-capture cancel.

The Game class supports three coordinated reversal mechanics:

1. **Undo / Redo** — a per-turn history stack that lets the player roll
   back any number of completed turns (and re-apply them with redo).
   Triggered from `main.py` via the U key (undo) and the Y key (redo).

2. **Cancel during jump-capture second-click** — when the knight has
   landed and the player is being asked to capture the jumped piece or
   decline, an Esc / right-click / outside-target click should restore
   the state to before the knight's leap. This is distinct from undo
   because the turn hasn't fully completed yet (next_turn hasn't been
   called).

3. **In-between guards** — undo and redo are disallowed while any
   in-progress turn state is active (jump-capture pending, transform
   menu, promotion menu) to prevent capturing partial state.

These tests verify all three mechanics directly via the Game API,
without going through pygame events.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Headless display
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

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
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except pygame.error:
        pass


from piece import Pawn, Knight, Bishop, Rook, Queen, King, Boulder
from board import Board
from game import Game
from square import Square
from move import Move


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _find_piece(board, color, piece_type):
    """Return (row, col, piece) for the first piece of the given color/type."""
    for r in range(8):
        for c in range(8):
            piece = board.squares[r][c].piece
            if piece and piece.color == color and isinstance(piece, piece_type):
                return r, c, piece
    return None


def _make_simple_move_via_board(game, from_rc, to_rc):
    """Execute a spatial move directly on the board (bypasses UI), then call next_turn.

    Returns the moved piece (after the move; references stay valid since no deepcopy
    happens inside Board.move).
    """
    fr, fc = from_rc
    tr, tc = to_rc
    piece = game.board.squares[fr][fc].piece
    move = Move(Square(fr, fc), Square(tr, tc))
    game.board.move(piece, move)
    game.next_turn()
    return piece


# -------------------------------------------------------------------------
# Section 1: snapshot/restore primitive
# -------------------------------------------------------------------------

def test_snapshot_returns_dict_with_expected_keys():
    g = Game()
    snap = g._snapshot()
    assert 'board' in snap
    assert 'next_player' in snap
    assert 'winner' in snap


def test_snapshot_captures_next_player():
    g = Game()
    g.next_player = 'black'
    snap = g._snapshot()
    assert snap['next_player'] == 'black'


def test_snapshot_captures_winner():
    g = Game()
    g.winner = 'white'
    snap = g._snapshot()
    assert snap['winner'] == 'white'


def test_snapshot_board_is_independent_deepcopy():
    """Modifying the board after snapshot does NOT alter the snapshot."""
    g = Game()
    snap = g._snapshot()
    # Mutate board after snapshot
    g.board.squares[4][4].piece = None
    # Snapshot must still hold the original (centre square has no piece in default
    # setup, so let's mutate a known piece location: white pawn at (6,0))
    g2 = Game()
    snap2 = g2._snapshot()
    g2.board.squares[6][0].piece = None  # remove the pawn
    assert snap2['board'].squares[6][0].piece is not None, \
        "Snapshot's board should be independent of subsequent mutations"


def test_restore_replaces_state_fields():
    g = Game()
    snap = g._snapshot()
    # Mutate state
    g.next_player = 'black'
    g.winner = 'white'
    g.board.squares[6][0].piece = None
    # Restore
    g._restore(snap)
    assert g.next_player == 'white'
    assert g.winner is None
    assert g.board.squares[6][0].piece is not None


# -------------------------------------------------------------------------
# Section 2: initial history state
# -------------------------------------------------------------------------

def test_history_initialized_with_starting_snapshot():
    """At game start, history should contain exactly one snapshot
    representing the initial position."""
    g = Game()
    assert len(g._history) == 1


def test_redo_stack_initially_empty():
    g = Game()
    assert g._redo_stack == []


def test_pre_jump_capture_snapshot_initially_none():
    g = Game()
    assert g._pre_jump_capture_snapshot is None


# -------------------------------------------------------------------------
# Section 3: next_turn integration with history
# -------------------------------------------------------------------------

def test_next_turn_appends_snapshot_to_history():
    g = Game()
    initial_len = len(g._history)
    g.next_turn()
    assert len(g._history) == initial_len + 1


def test_next_turn_clears_redo_stack():
    g = Game()
    # Manually populate redo to verify it gets cleared on a real turn
    g._redo_stack.append(g._snapshot())
    g.next_turn()
    assert g._redo_stack == []


def test_history_grows_with_each_turn():
    g = Game()
    initial_len = len(g._history)
    for _ in range(5):
        g.next_turn()
    assert len(g._history) == initial_len + 5


# -------------------------------------------------------------------------
# Section 4: can_undo / can_redo guards
# -------------------------------------------------------------------------

def test_can_undo_false_at_game_start():
    """Initial state has only the starting snapshot — nothing to undo."""
    g = Game()
    assert g.can_undo() is False


def test_can_redo_false_at_game_start():
    g = Game()
    assert g.can_redo() is False


def test_can_undo_true_after_one_turn():
    g = Game()
    g.next_turn()
    assert g.can_undo() is True


def test_can_redo_true_after_undo():
    g = Game()
    g.next_turn()
    g.undo()
    assert g.can_redo() is True


def test_can_undo_false_during_jump_capture():
    g = Game()
    g.next_turn()
    # Simulate being in jump-capture pending state
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    assert g.can_undo() is False


def test_can_redo_false_during_jump_capture():
    g = Game()
    g.next_turn()
    g.undo()
    g.jump_capture_targets = [(3, 4)]
    assert g.can_redo() is False


def test_can_undo_false_during_transform_menu():
    g = Game()
    g.next_turn()
    g.transform_menu = {'piece': None, 'row': 0, 'col': 0, 'options': []}
    assert g.can_undo() is False


def test_can_undo_false_during_promotion_menu():
    g = Game()
    g.next_turn()
    g.promotion_menu = {'pawn': None, 'row': 0, 'col': 0}
    assert g.can_undo() is False


# -------------------------------------------------------------------------
# Section 5: undo restores state
# -------------------------------------------------------------------------

def test_undo_returns_false_when_nothing_to_undo():
    g = Game()
    assert g.undo() is False


def test_undo_returns_true_on_success():
    g = Game()
    g.next_turn()
    assert g.undo() is True


def test_undo_restores_next_player_after_one_turn():
    """After one next_turn, undo should restore next_player to its initial value."""
    g = Game()
    initial_player = g.next_player
    g.next_turn()
    assert g.next_player != initial_player  # turn switched
    g.undo()
    assert g.next_player == initial_player


def test_undo_restores_board_state_after_a_real_move():
    """Move a pawn forward, undo, verify pawn is back at its origin."""
    g = Game()
    # White's first pawn (e2 = row 6, col 4)
    pawn = g.board.squares[6][4].piece
    assert isinstance(pawn, Pawn) and pawn.color == 'white'
    move = Move(Square(6, 4), Square(5, 4))
    g.board.move(pawn, move)
    g.next_turn()
    # Verify the move happened
    assert g.board.squares[5][4].piece is not None
    assert g.board.squares[6][4].piece is None
    # Undo
    g.undo()
    # Pawn back at origin
    assert g.board.squares[6][4].piece is not None
    assert isinstance(g.board.squares[6][4].piece, Pawn)
    assert g.board.squares[5][4].piece is None


def test_undo_pops_history_pushes_redo():
    g = Game()
    g.next_turn()
    history_before = len(g._history)
    redo_before = len(g._redo_stack)
    g.undo()
    assert len(g._history) == history_before - 1
    assert len(g._redo_stack) == redo_before + 1


# -------------------------------------------------------------------------
# Section 6: redo restores state
# -------------------------------------------------------------------------

def test_redo_returns_false_when_nothing_to_redo():
    g = Game()
    assert g.redo() is False


def test_redo_returns_true_on_success():
    g = Game()
    g.next_turn()
    g.undo()
    assert g.redo() is True


def test_redo_restores_state_after_undo():
    """Undo a move then redo — state should be back at the post-move state."""
    g = Game()
    pawn = g.board.squares[6][4].piece
    move = Move(Square(6, 4), Square(5, 4))
    g.board.move(pawn, move)
    g.next_turn()
    # State A: pawn at (5,4)
    g.undo()
    # State 0: pawn at (6,4)
    assert g.board.squares[6][4].piece is not None
    g.redo()
    # State A again: pawn at (5,4)
    assert g.board.squares[5][4].piece is not None
    assert g.board.squares[6][4].piece is None


def test_redo_pops_redo_pushes_history():
    g = Game()
    g.next_turn()
    g.undo()
    history_before = len(g._history)
    redo_before = len(g._redo_stack)
    g.redo()
    assert len(g._history) == history_before + 1
    assert len(g._redo_stack) == redo_before - 1


# -------------------------------------------------------------------------
# Section 7: round-trip and multi-step undo/redo
# -------------------------------------------------------------------------

def test_undo_redo_round_trip_preserves_next_player():
    g = Game()
    g.next_turn()
    expected_player = g.next_player
    g.undo()
    g.redo()
    assert g.next_player == expected_player


def test_multiple_undo_walks_back_through_turns():
    g = Game()
    # 3 turns
    g.next_turn()
    g.next_turn()
    g.next_turn()
    # 3 undos should bring us back to start
    assert g.undo() is True
    assert g.undo() is True
    assert g.undo() is True
    # 4th undo: nothing to undo
    assert g.undo() is False


def test_multiple_redo_walks_forward_through_turns():
    g = Game()
    g.next_turn()
    g.next_turn()
    g.next_turn()
    # Undo all the way back
    g.undo(); g.undo(); g.undo()
    # Redo all the way forward
    assert g.redo() is True
    assert g.redo() is True
    assert g.redo() is True
    # 4th redo: nothing to redo
    assert g.redo() is False


def test_undo_to_initial_state_restores_starting_position():
    """Make several moves, undo all the way, board should match a fresh game's board."""
    g = Game()
    # Make 3 turns
    pawn1 = g.board.squares[6][4].piece
    g.board.move(pawn1, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    pawn2 = g.board.squares[1][4].piece
    g.board.move(pawn2, Move(Square(1, 4), Square(2, 4)))
    g.next_turn()
    pawn3 = g.board.squares[5][4].piece
    g.board.move(pawn3, Move(Square(5, 4), Square(4, 4)))
    g.next_turn()
    # Undo all three
    g.undo(); g.undo(); g.undo()
    # Verify the centre files are back to starting setup
    assert isinstance(g.board.squares[6][4].piece, Pawn)
    assert isinstance(g.board.squares[1][4].piece, Pawn)
    assert g.board.squares[5][4].piece is None
    assert g.board.squares[2][4].piece is None
    assert g.board.squares[4][4].piece is None


# -------------------------------------------------------------------------
# Section 8: redo invalidation when a new turn happens after undo
# -------------------------------------------------------------------------

def test_new_turn_after_undo_clears_redo_stack():
    g = Game()
    g.next_turn()
    g.next_turn()
    g.undo()  # populates redo
    assert len(g._redo_stack) > 0
    g.next_turn()  # new turn diverges history
    assert g._redo_stack == []


def test_can_redo_false_after_new_turn_post_undo():
    g = Game()
    g.next_turn()
    g.undo()
    assert g.can_redo() is True
    g.next_turn()
    assert g.can_redo() is False


# -------------------------------------------------------------------------
# Section 9: undo preserves board internals (captured pieces, distance counts)
# -------------------------------------------------------------------------

def test_undo_restores_captured_pieces_dict():
    """Capture a piece, undo, verify captured_pieces no longer records it."""
    g = Game()
    # Set up: white pawn at (6,4), black pawn at (5,5) (diagonal capture)
    g.board.squares[5][5].piece = Pawn('black')
    pawn = g.board.squares[6][4].piece
    g.board.move(pawn, Move(Square(6, 4), Square(5, 5)))
    g.next_turn()
    assert 'pawn' in g.board.captured_pieces['black']
    g.undo()
    assert 'pawn' not in g.board.captured_pieces['black']


def test_undo_restores_turn_number():
    g = Game()
    initial_turn_number = g.board.turn_number
    g.next_turn()
    g.next_turn()
    assert g.board.turn_number == initial_turn_number + 2
    g.undo()
    assert g.board.turn_number == initial_turn_number + 1
    g.undo()
    assert g.board.turn_number == initial_turn_number


# -------------------------------------------------------------------------
# Section 10: cancel jump-capture
# -------------------------------------------------------------------------

def test_cancel_jump_capture_returns_false_when_not_in_state():
    g = Game()
    assert g.cancel_jump_capture() is False


def test_cancel_jump_capture_restores_pre_move_board():
    """Simulate the pre-move snapshot being saved, then enter jump-capture state,
    then cancel. The board should be restored to the pre-move state."""
    g = Game()
    # Take a snapshot of the current pre-move state
    g._pre_jump_capture_snapshot = g._snapshot()
    # Simulate the knight having moved (mutate board)
    g.board.squares[6][4].piece = None  # pretend pawn vanished
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    g.jump_capture_piece = Knight('white')
    g.jump_capture_origin = (4, 5)
    # Cancel
    result = g.cancel_jump_capture()
    assert result is True
    # Board restored
    assert g.board.squares[6][4].piece is not None
    # State cleared
    assert g.jump_capture_targets is None
    assert g.jump_capture_landing is None
    assert g.jump_capture_piece is None
    assert g.jump_capture_origin is None
    assert g._pre_jump_capture_snapshot is None


def test_cancel_jump_capture_returns_false_with_no_snapshot():
    """If somehow we're in jump-capture state but no pre-move snapshot
    was saved, cancel should fail-safe (return False) rather than crash."""
    g = Game()
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    # No _pre_jump_capture_snapshot set
    assert g.cancel_jump_capture() is False


def test_cancel_jump_capture_does_not_consume_history():
    """Cancel should NOT push to history or pop from history — the turn
    isn't complete, history is for completed turns only."""
    g = Game()
    g.next_turn()
    history_len_before = len(g._history)
    redo_len_before = len(g._redo_stack)
    g._pre_jump_capture_snapshot = g._snapshot()
    g.jump_capture_targets = [(3, 4)]
    g.jump_capture_landing = (3, 5)
    g.jump_capture_piece = Knight('white')
    g.jump_capture_origin = (4, 5)
    g.cancel_jump_capture()
    assert len(g._history) == history_len_before
    assert len(g._redo_stack) == redo_len_before


# -------------------------------------------------------------------------
# Section 11: undo/redo do not affect dragger or hovered_sqr
# -------------------------------------------------------------------------

def test_undo_does_not_crash_with_active_hovered_sqr():
    """hovered_sqr is UI-only state; undo shouldn't blow up because of it."""
    g = Game()
    g.next_turn()
    g.hovered_sqr = g.board.squares[4][4]
    g.undo()  # should not raise
    # hovered_sqr is allowed to point at a stale square; the next render
    # cycle will refresh from current mouse position. We just don't crash.


# -------------------------------------------------------------------------
# Section 12: snapshot includes board sub-state (state_history, distance_counts)
# -------------------------------------------------------------------------

def test_snapshot_captures_state_history():
    """The board's state_history (for repetition rule) should be part of the snapshot."""
    g = Game()
    g.next_turn()
    g.next_turn()
    snap = g._snapshot()
    # The snapshot's board should have its own copy of state_history
    snap_history = snap['board'].state_history
    g.board.state_history.clear()
    # Snapshot's copy should be unaffected
    assert len(snap_history) > 0


def test_undo_restores_state_history():
    """state_history should be rolled back when undo is called."""
    g = Game()
    state_history_initial = dict(g.board.state_history)
    g.next_turn()
    g.next_turn()
    state_history_after_two = dict(g.board.state_history)
    assert state_history_after_two != state_history_initial
    g.undo()
    g.undo()
    assert dict(g.board.state_history) == state_history_initial
