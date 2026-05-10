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


# -------------------------------------------------------------------------
# Section 13: Object-identity preservation (REGRESSION)
# -------------------------------------------------------------------------
#
# The UI in main.py captures local references to the board and dragger
# at the start of the mainloop. If undo/redo replaced `game.board` with
# a new object, those locals would go stale and the UI would render the
# new board while the click handlers operated on the old board — producing
# the "piece appears in two places, drag picks up an invisible ghost,
# move not undone" bug. Regression-test that undo and redo mutate the
# board in place rather than replacing it.

def test_undo_preserves_board_object_identity():
    g = Game()
    board_id = id(g.board)
    g.next_turn()
    g.next_turn()
    g.undo()
    assert id(g.board) == board_id, (
        "Undo replaced game.board with a new object — external references "
        "(e.g. main.py's local board variable) will go stale and cause UI desync."
    )


def test_redo_preserves_board_object_identity():
    g = Game()
    board_id = id(g.board)
    g.next_turn()
    g.undo()
    g.redo()
    assert id(g.board) == board_id, (
        "Redo replaced game.board with a new object."
    )


def test_external_board_reference_remains_valid_through_undo_redo():
    """Simulate main.py's pattern: a local variable bound to game.board
    at the start, then undo/redo. The local must stay synchronized with
    game.board (i.e., remain the same object) so that subsequent reads
    see the post-undo state."""
    g = Game()
    external_board = g.board  # like `board = self.game.board` in mainloop
    # Make a real move
    pawn = g.board.squares[6][4].piece
    g.board.move(pawn, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    # Undo
    g.undo()
    # External reference must still be game.board AND show the restored state
    assert external_board is g.board
    assert external_board.squares[6][4].piece is not None
    assert external_board.squares[5][4].piece is None
    # Redo
    g.redo()
    assert external_board is g.board
    assert external_board.squares[5][4].piece is not None
    assert external_board.squares[6][4].piece is None


# -------------------------------------------------------------------------
# Section 14: Snapshot immutability (REGRESSION)
# -------------------------------------------------------------------------
#
# If restore shared array references with the snapshot in history, then
# any post-restore live mutation would silently contaminate the snapshot.
# The next undo to that snapshot would see the mutated state, breaking
# undo correctness across multiple cycles.

def test_history_snapshot_unaffected_by_post_restore_live_mutation():
    """After undo restores from a snapshot, mutating the live board must
    NOT modify the snapshot in history."""
    g = Game()
    g.next_turn()
    g.next_turn()
    snap = g._history[1]
    snap_pawn_before = snap['board'].squares[6][4].piece
    assert snap_pawn_before is not None

    g.undo()  # restores from history[1]
    # Live mutation
    g.board.squares[6][4].piece = None
    g.board.squares[3][3].piece = Knight('white')

    # Snapshot must be unchanged
    assert snap['board'].squares[6][4].piece is snap_pawn_before
    assert snap['board'].squares[3][3].piece is None


def test_redo_stack_snapshot_unaffected_by_live_mutation():
    """When undo pushes the current state to the redo stack, that
    snapshot must remain pristine even if the live board changes."""
    g = Game()
    g.next_turn()
    g.next_turn()
    g.undo()
    # The just-undone state is now in redo
    snap = g._redo_stack[-1]
    snap_pawn = snap['board'].squares[6][4].piece

    # Mutate live
    g.board.squares[6][4].piece = None

    # Snapshot in redo unchanged
    assert snap['board'].squares[6][4].piece is snap_pawn


def test_initial_history_snapshot_unaffected_by_live_mutation():
    """The initial-state snapshot in history[0] must stay pristine
    throughout the entire game, since any number of undos may eventually
    restore from it."""
    g = Game()
    initial_snap = g._history[0]
    pawn_in_snap = initial_snap['board'].squares[6][4].piece
    g.next_turn()
    g.board.squares[6][4].piece = None
    assert initial_snap['board'].squares[6][4].piece is pawn_in_snap


def test_repeated_undo_redo_cycles_remain_consistent():
    """Cycling undo/redo many times should produce identical results
    each time — verifies snapshots aren't being contaminated mid-cycle."""
    g = Game()
    pawn = g.board.squares[6][4].piece
    g.board.move(pawn, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    pawn2 = g.board.squares[1][4].piece
    g.board.move(pawn2, Move(Square(1, 4), Square(2, 4)))
    g.next_turn()
    # Now do 5 undo/redo cycles and verify the position oscillates correctly.
    for _ in range(5):
        g.undo()
        # After undo: black pawn back at (1,4), white pawn at (5,4)
        assert g.board.squares[1][4].piece is not None
        assert g.board.squares[2][4].piece is None
        assert g.board.squares[5][4].piece is not None
        g.redo()
        # After redo: black pawn at (2,4)
        assert g.board.squares[1][4].piece is None
        assert g.board.squares[2][4].piece is not None


# -------------------------------------------------------------------------
# Section 15: Dragger guard (REGRESSION)
# -------------------------------------------------------------------------
#
# Undo/redo must be blocked while the user is mid-drag. If we restored
# the board while a drag was in progress, dragger.piece would point at
# a piece object that no longer exists in the restored board (since the
# restored board's pieces are deep-copied from the snapshot), causing
# stale-reference bugs on the subsequent release.

def test_can_undo_false_while_dragging():
    g = Game()
    g.next_turn()
    assert g.can_undo() is True
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    assert g.can_undo() is False


def test_can_redo_false_while_dragging():
    g = Game()
    g.next_turn()
    g.undo()
    assert g.can_redo() is True
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    assert g.can_redo() is False


def test_undo_returns_false_while_dragging():
    g = Game()
    g.next_turn()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    assert g.undo() is False


def test_redo_returns_false_while_dragging():
    g = Game()
    g.next_turn()
    g.undo()
    g.dragger.dragging = True
    g.dragger.piece = Knight('white')
    assert g.redo() is False


# -------------------------------------------------------------------------
# Section 16: Board-internal field reachability (REGRESSION)
# -------------------------------------------------------------------------
#
# In-place restoration via __dict__ update must cover every field on
# Board so the live board fully reflects the snapshot. Verify the major
# board fields are individually restored.

def test_undo_restores_last_move_field():
    g = Game()
    pawn = g.board.squares[6][4].piece
    g.board.move(pawn, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    last_move_after = g.board.last_move
    assert last_move_after is not None
    g.undo()
    # last_move was None at game start
    assert g.board.last_move is None


def test_undo_restores_last_move_turn_number_field():
    g = Game()
    pawn = g.board.squares[6][4].piece
    g.board.move(pawn, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    assert g.board.last_move_turn_number is not None
    g.undo()
    assert g.board.last_move_turn_number is None


def test_snapshot_includes_distance_counts():
    """tiny_endgame's distance_counts must be part of the board snapshot
    so undo correctly rolls back distance-count state."""
    g = Game()
    g.board.distance_counts[5] = 42
    snap = g._snapshot()
    # Mutating live must not affect snapshot
    g.board.distance_counts[5] = 0
    assert snap['board'].distance_counts[5] == 42


def test_snapshot_includes_tiny_endgame_active_flag():
    """tiny_endgame_active must be part of the board snapshot."""
    g = Game()
    g.board.tiny_endgame_active = True
    snap = g._snapshot()
    g.board.tiny_endgame_active = False
    assert snap['board'].tiny_endgame_active is True


# -------------------------------------------------------------------------
# Section 17: Realistic UI-flow scenario (REGRESSION)
# -------------------------------------------------------------------------
#
# Reproduce the user-reported failure mode end-to-end via the Game API.

def test_drag_after_undo_uses_post_undo_pieces():
    """The user reported that after undo, dragging a piece picks up a
    'ghost' from the pre-undo state. Verify that after undo, the pieces
    accessible via game.board are the post-undo ones (not stale)."""
    g = Game()
    pawn_at_6_4_initially = g.board.squares[6][4].piece
    # Move pawn forward
    g.board.move(pawn_at_6_4_initially, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    assert g.board.squares[6][4].piece is None
    assert g.board.squares[5][4].piece is pawn_at_6_4_initially  # same obj after move
    # Undo
    g.undo()
    # After undo: pawn at (6,4) again, but it might be a NEW pawn object
    # (deepcopy from snapshot). What MUST be true: the pawn is at (6,4),
    # not at (5,4), and accessing it via game.board.squares returns it.
    new_pawn = g.board.squares[6][4].piece
    assert new_pawn is not None
    assert isinstance(new_pawn, Pawn)
    assert g.board.squares[5][4].piece is None
    # Simulate "drag" — pick up the piece via game.board.squares
    # (this is what main.py does on left-click).
    picked_up = g.board.squares[6][4].piece
    assert picked_up is new_pawn  # same as above; consistent reads


def test_undo_then_make_new_move_does_not_resurrect_old_pieces():
    """After undo, making a new move should produce a clean post-move state
    — no stale piece references from the pre-undo timeline."""
    g = Game()
    pawn_orig = g.board.squares[6][4].piece
    g.board.move(pawn_orig, Move(Square(6, 4), Square(5, 4)))
    g.next_turn()
    # Undo
    g.undo()
    # Make a different first move via the restored board
    new_pawn = g.board.squares[6][3].piece  # a different pawn (d-file)
    g.board.move(new_pawn, Move(Square(6, 3), Square(5, 3)))
    g.next_turn()
    # The d-pawn should be at (5,3); the e-pawn should still be at (6,4)
    assert g.board.squares[5][3].piece is not None
    assert g.board.squares[6][3].piece is None
    assert g.board.squares[6][4].piece is not None
    assert g.board.squares[5][4].piece is None  # NOT moved


def test_undo_after_in_place_restore_isolates_live_from_snapshot():
    """After undo, mutating the live board must NOT affect the snapshot
    we restored from. This is the core invariant for snapshot stability
    across multiple undo cycles."""
    g = Game()
    g.next_turn()
    snap_to_restore_from = g._history[0]
    snap_initial_squares_id = id(snap_to_restore_from['board'].squares)
    g.undo()
    # After undo, live board should be different array than snapshot
    assert id(g.board.squares) != snap_initial_squares_id, (
        "Live board.squares must be a different array than the snapshot's "
        "to prevent live mutations from contaminating the snapshot."
    )
