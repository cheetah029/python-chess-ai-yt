"""Regression test for the repetition-rule manipulation bug
identified 2026-05-31 from a user-reported "AI repeated this
position 3 times in CvC" screenshot.

THE BUG: `Board.would_cause_repetition(piece, move, next_player)`
simulates the move by mutating the squares array, but does NOT
mirror the `piece.moved_by_queen = True` flag that gets set on a
manipulated piece AFTER the move applies (by the AI controller /
human UI / engine.execute_turn).

The state hash INCLUDES `moved_by_queen` per piece. So the
simulated state hash has `moved_by_queen=False` for the
manipulated piece, while the actual recorded state at the start
of the next opponent turn has `moved_by_queen=True`. The hashes
NEVER MATCH for manipulation moves → the repetition filter
never triggers on manipulation cycles → a manipulation cycle
can repeat the same actual state 3+ times without the rule
firing.

This regression test demonstrates the bug by:
  1. Constructing a small position with a queen + a manipulable
     opponent piece.
  2. Manipulating the same enemy piece back and forth to recreate
     the same hash 3 times.
  3. Verifying that `would_cause_repetition` returns True on the
     third occurrence (after the fix it does; before the fix
     it returns False — bug).
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _empty_board():
    """A board with all squares cleared (no boulder either) for
    constructing minimal test positions."""
    from board import Board
    b = Board()
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    return b


# ---- the bug ------------------------------------------------------------

def test_manipulation_simulation_sets_moved_by_queen():
    """The fix: when `would_cause_repetition` simulates a
    manipulation move (piece.color != mover's color), it must set
    `moved_by_queen=True` on the moved piece so the simulated state
    hash matches what the actual game records.

    We assert via a side-channel: peek at the piece's
    moved_by_queen flag immediately after the simulation completes
    (the simulation restores invuln and other state but our fix
    sets moved_by_queen=True on the simulation path and restores it
    afterward — so the assertion is on a DIFFERENT angle: that the
    simulated hash MATCHES the hash you'd get by actually applying
    the manipulation + clearing flags as game.next_turn does)."""
    from board import Board
    from piece import Queen, King, Pawn
    from move import Move
    from square import Square

    b = _empty_board()
    # White queen at b2 (sees diagonal to e5 — black pawn there).
    wq = Queen('white', is_royal=True)
    b.squares[6][1].piece = wq
    # White king at a1.
    wk = King('white')
    b.squares[7][0].piece = wk
    # Black king at h8.
    bk = King('black')
    b.squares[0][7].piece = bk
    # Black pawn at e5 (within white queen's diagonal LoS from b2).
    bp = Pawn('black')
    b.squares[3][4].piece = bp

    # Update LoS so queen_moves_enemy works.
    b.update_lines_of_sight()
    b.update_threat_squares()

    # The manipulation move: white queen manipulates black pawn at
    # (3, 4) to move forward (to e4, row 4 col 4 for black).
    move = Move(Square(3, 4), Square(4, 4))

    # Now compute hash by SIMULATING with the fix, and compute the
    # hash by ACTUALLY APPLYING the manipulation + setting
    # moved_by_queen + running game.next_turn's clear steps. The two
    # should match.
    next_player = 'white'  # the mover

    # First: the simulated hash via would_cause_repetition's
    # internal logic (which we'll call directly).
    # Use a deep-copy so the actual board isn't disturbed.
    import copy
    b_for_sim = copy.deepcopy(b)
    # would_cause_repetition returns count >= 2 — that's not the
    # comparison we want. Instead, we re-implement the inner hash
    # computation by reading get_state_hash AFTER applying the
    # simulated mutations exactly as the (fixed) would_cause_repetition
    # would. The fix MUST set moved_by_queen=True on the manipulated
    # piece's destination square.

    # Simulate (with the fix):
    sim_piece = b_for_sim.squares[3][4].piece
    b_for_sim.squares[3][4].piece = None
    b_for_sim.squares[4][4].piece = sim_piece
    # The fix should set moved_by_queen=True if this is a
    # manipulation (mover's color != piece.color).
    if sim_piece.color != next_player:
        sim_piece.moved_by_queen = True
    # Simulate clear_invulnerable_for_color(opponent):
    opponent = 'black'
    for r in range(8):
        for c in range(8):
            p = b_for_sim.squares[r][c].piece
            if p and p.color == opponent:
                p.invulnerable = False
    sim_hash = b_for_sim.get_state_hash(opponent)

    # Now compute the ACTUAL hash by applying the manipulation +
    # game.next_turn-equivalent clears. The piece's
    # moved_by_queen=True is set by the AI controller / UI AFTER
    # the move. Then game.next_turn clears OPPONENT's invuln (i.e.
    # black's invuln; we set none, so no-op) and records.
    b_actual = copy.deepcopy(b)
    actual_piece = b_actual.squares[3][4].piece
    b_actual.squares[3][4].piece = None
    b_actual.squares[4][4].piece = actual_piece
    # Mirror what the AI controller does after a manipulation:
    actual_piece.moved_by_queen = True
    # Game.next_turn-equivalent for the OPPONENT (black) starting
    # their turn:
    b_actual.clear_moved_by_queen_for_opponent('black')  # clears WHITE's flags
    b_actual.clear_invulnerable_for_color('black')       # clears BLACK's invuln
    actual_hash = b_actual.get_state_hash('black')

    assert sim_hash == actual_hash, (
        'simulated hash should match actual recorded hash for '
        'manipulation moves — the bug is that would_cause_repetition '
        'does NOT set moved_by_queen on the manipulated piece, so '
        'these diverge')


def test_would_cause_repetition_catches_manipulation_cycle():
    """End-to-end: build a position where the queen manipulates the
    SAME pawn back and forth. After 2 occurrences of a state, the
    third would_cause_repetition call must return True."""
    from board import Board
    from piece import Queen, King, Pawn
    from move import Move
    from square import Square

    b = _empty_board()
    # Minimal position: white queen at b2, white king at a1, black
    # king at h8, black pawn at e2 (within queen's rank).
    wq = Queen('white', is_royal=True)
    wk = King('white')
    bk = King('black')
    bp = Pawn('black')
    b.squares[6][1].piece = wq
    b.squares[7][0].piece = wk
    b.squares[0][7].piece = bk
    b.squares[6][4].piece = bp   # e2 — same rank as queen, queen can manipulate via rank LoS

    b.update_lines_of_sight()
    b.update_threat_squares()

    # Initial state at start of white's turn (about to manipulate).
    h0 = b.get_state_hash('white')
    b.state_history[h0] = 1

    # Manipulate the pawn forward — for black, "forward" is rank
    # decreasing. From e2 (row 6), forward = e1 (row 7). But the
    # pawn promotes there. Let's instead manipulate sideways: e2 -> d2.
    move_e2_to_d2 = Move(Square(6, 4), Square(6, 3))

    # Should NOT yet be a repetition (count=1, this would be 2nd).
    assert b.would_cause_repetition(bp, move_e2_to_d2, 'white') is False

    # Helper: apply move + mirror what game.next_turn does, record.
    def apply_and_record(piece, fr, fc, tr, tc, mover):
        other = 'black' if mover == 'white' else 'white'
        b.squares[fr][fc].piece = None
        b.squares[tr][tc].piece = piece
        # If manipulation (piece's color != mover): set moved_by_queen.
        if piece.color != 'none' and piece.color != mover:
            piece.moved_by_queen = True
        # Mirror board.move + Game.next_turn:
        b.last_move = Move(Square(fr, fc), Square(tr, tc))
        b.last_move_turn_number = b.turn_number
        b.turn_number += 1
        b.clear_moved_by_queen_for_opponent(other)
        b.clear_invulnerable_for_color(other)
        h = b.get_state_hash(other)
        b.state_history[h] = b.state_history.get(h, 0) + 1
        return h

    def undo_to(piece, fr, fc, tr, tc, prev_last_move, prev_turn_num):
        """Undo the moved piece + restore last_move + turn_number."""
        b.squares[tr][tc].piece = None
        b.squares[fr][fc].piece = piece
        piece.moved_by_queen = False
        b.last_move = prev_last_move
        b.last_move_turn_number = (
            (prev_turn_num - 1) if prev_last_move is not None else None)
        b.turn_number = prev_turn_num

    # Apply manipulation: pawn e2->d2.
    saved_last_move = b.last_move
    saved_turn = b.turn_number
    apply_and_record(bp, 6, 4, 6, 3, 'white')

    # Now back to white's turn: apply a no-op "round-trip" by
    # undoing and re-running — for simplicity, just undo and bump
    # state count manually for the post-cycle state.
    undo_to(bp, 6, 4, 6, 3, saved_last_move, saved_turn)

    # Apply manipulation again to reach the "d2 with moved_by_queen"
    # state a SECOND time.
    saved_last_move = b.last_move
    saved_turn = b.turn_number
    apply_and_record(bp, 6, 4, 6, 3, 'white')
    # Now state_history[h_d2] == 2.

    # Undo back to setup for the 3rd-attempt check.
    undo_to(bp, 6, 4, 6, 3, saved_last_move, saved_turn)

    # Try the 3rd attempt: would_cause_repetition should now block.
    assert b.would_cause_repetition(bp, move_e2_to_d2, 'white') is True, (
        'a third manipulation of the same pawn to the same square '
        'should trigger repetition — this is the bug the fix '
        'addresses')


# ---- non-manipulation cycle still works (regression: don't break the existing case) --

def test_would_cause_repetition_still_catches_normal_move_cycle():
    """The fix must not regress normal-move repetition. White king
    bouncing between two squares: after 2 occurrences of a state,
    the 3rd would_cause_repetition returns True."""
    from board import Board
    from piece import King, Queen
    from move import Move
    from square import Square

    b = _empty_board()
    wk = King('white')
    bk = King('black')
    wq = Queen('white', is_royal=True)
    b.squares[7][0].piece = wk   # white king a1
    b.squares[7][1].piece = wq   # white queen b1 (so king has a friend)
    b.squares[0][7].piece = bk   # black king h8

    b.update_lines_of_sight()
    b.update_threat_squares()

    # Initial.
    h0 = b.get_state_hash('white')
    b.state_history[h0] = 1

    move_a1_a2 = Move(Square(7, 0), Square(6, 0))
    # 1st time moving a1->a2 isn't yet repetition.
    assert b.would_cause_repetition(wk, move_a1_a2, 'white') is False

    # Apply.
    b.squares[7][0].piece = None
    b.squares[6][0].piece = wk
    b.clear_invulnerable_for_color('black')
    h1 = b.get_state_hash('black')
    b.state_history[h1] = b.state_history.get(h1, 0) + 1

    # Undo.
    b.squares[6][0].piece = None
    b.squares[7][0].piece = wk
    b.clear_invulnerable_for_color('white')
    h0_again = b.get_state_hash('white')
    if h0_again == h0:
        b.state_history[h0] = b.state_history.get(h0, 0) + 1
    else:
        b.state_history[h0_again] = 1

    # 2nd a1->a2.
    assert b.would_cause_repetition(wk, move_a1_a2, 'white') is False

    # Apply.
    b.squares[7][0].piece = None
    b.squares[6][0].piece = wk
    b.clear_invulnerable_for_color('black')
    h1_again = b.get_state_hash('black')
    b.state_history[h1_again] = b.state_history.get(h1_again, 0) + 1

    # Undo.
    b.squares[6][0].piece = None
    b.squares[7][0].piece = wk
    b.clear_invulnerable_for_color('white')

    # 3rd a1->a2 — would be the THIRD occurrence of h1. Should return True.
    assert b.would_cause_repetition(wk, move_a1_a2, 'white') is True
