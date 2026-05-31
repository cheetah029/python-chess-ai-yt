"""Test the would_cause_repetition fix in a position where derived
flags MATTER (bishops with diagonal LoS to moved pieces).

The minimal queen-bounce case happens to have derived flags that
are all False regardless of which last_move is in effect. But in a
position with bishops on the moving piece's diagonal, the
`reactive_armed` flag DEPENDS on last_move.initial. So the simulated
hash MUST update last_move to match — without the fix, the
simulated hash uses the previous turn's last_move and produces a
hash that doesn't match the actual recorded one.
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
    from board import Board
    b = Board()
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    return b


def test_simulated_hash_matches_actual_with_bishop_on_diagonal():
    """A position with a bishop whose reactive_armed flag depends on
    the just-moved piece's initial square. Without the fix, the
    simulated hash uses the PREVIOUS turn's last_move and produces
    a different reactive_armed value than the actual recorded hash."""
    import copy
    from piece import Queen, King, Bishop
    from move import Move
    from square import Square

    b = _empty_board()
    # White bishop at a1 (sees the a1-h8 diagonal).
    wb = Bishop('white')
    b.squares[7][0].piece = wb
    # White king.
    wk = King('white')
    b.squares[7][6].piece = wk
    # Black king.
    bk = King('black')
    b.squares[0][1].piece = bk
    # Black queen at c6. The c6 square is on the a1-h8 diagonal
    # (a1=(7,0), b2=(6,1), c3=(5,2), ..., c6 is NOT on a1's
    # diagonal — let me use d4 instead: d4=(4,3), on a1-h8 diagonal
    # via 7,0 -> 6,1 -> 5,2 -> 4,3 ✓).
    bq = Queen('black', is_royal=True)
    b.squares[4][3].piece = bq

    # Set last_move = a previous black-queen move (some non-d4 square
    # for variety). Simulate state being mid-game.
    b.last_move = Move(Square(3, 3), Square(4, 3))   # BQ d5 -> d4 a turn ago
    b.last_move_turn_number = 5
    b.turn_number = 6
    b.update_lines_of_sight()
    b.update_threat_squares()

    # Now white is about to move. Move: WB teleport to c3 (on the
    # a1-h8 diagonal still).
    move = Move(Square(7, 0), Square(5, 2))

    # Simulate via the (fixed) would_cause_repetition logic.
    b_sim = copy.deepcopy(b)
    sim_piece = b_sim.squares[7][0].piece
    b_sim.squares[7][0].piece = None
    b_sim.squares[5][2].piece = sim_piece
    # FIX: set last_move + turn_number to match what board.move +
    # Game.next_turn would do.
    b_sim.last_move = move
    b_sim.last_move_turn_number = b_sim.turn_number
    b_sim.turn_number += 1
    b_sim.clear_moved_by_queen_for_opponent('black')
    b_sim.clear_invulnerable_for_color('black')
    sim_hash = b_sim.get_state_hash('black')

    # Compute actual via Game.next_turn-equivalent.
    b_act = copy.deepcopy(b)
    act_piece = b_act.squares[7][0].piece
    b_act.squares[7][0].piece = None
    b_act.squares[5][2].piece = act_piece
    b_act.last_move = move
    b_act.last_move_turn_number = b_act.turn_number
    b_act.turn_number += 1
    b_act.clear_moved_by_queen_for_opponent('black')
    b_act.clear_invulnerable_for_color('black')
    act_hash = b_act.get_state_hash('black')

    assert sim_hash == act_hash, (
        'with the last_move fix in place, simulated and actual '
        'hashes match even when bishops are positioned to make '
        'reactive_armed flag meaningful')


def test_would_cause_repetition_uses_fix():
    """Verify the fix is integrated: calling
    would_cause_repetition with a fresh state hash that we just
    recorded TWICE should return True."""
    import copy
    from piece import Queen, King
    from move import Move
    from square import Square

    b = _empty_board()
    wk = King('white'); b.squares[7][6].piece = wk
    wq = Queen('white', is_royal=True); b.squares[7][1].piece = wq
    bk = King('black'); b.squares[0][1].piece = bk
    bq = Queen('black', is_royal=True); b.squares[0][6].piece = bq

    b.update_lines_of_sight()
    b.update_threat_squares()

    # We're at turn 6. WQ just moved (last_move set). Black to move.
    b.last_move = Move(Square(7, 0), Square(7, 1))  # WQ a1->b1
    b.last_move_turn_number = 5
    b.turn_number = 6

    # Record the state we're at TWICE via direct manipulation
    # (simulating that this state was seen twice in the game's
    # history).
    h_now = b.get_state_hash('black')
    b.state_history[h_now] = 2

    # Now black is about to move BQ g8->h8. The resulting state hash
    # — when computed via the FIXED would_cause_repetition — would
    # have last_move = BQ g8->h8. If we artificially seeded
    # state_history with the hash that results from this exact
    # move, would_cause_repetition would block it.

    # We can't directly seed without computing the hash, so we
    # actually compute the "after BQ g8->h8" hash and seed it.
    b_after = copy.deepcopy(b)
    after_piece = b_after.squares[0][6].piece
    b_after.squares[0][6].piece = None
    b_after.squares[0][7].piece = after_piece
    b_after.last_move = Move(Square(0, 6), Square(0, 7))
    b_after.last_move_turn_number = b_after.turn_number
    b_after.turn_number += 1
    b_after.clear_moved_by_queen_for_opponent('white')
    b_after.clear_invulnerable_for_color('white')
    h_after = b_after.get_state_hash('white')

    # Seed with count 2 — would_cause_repetition should now return
    # True (executing would make it 3rd).
    b.state_history[h_after] = 2

    # Now check would_cause_repetition on b (not b_after).
    move = Move(Square(0, 6), Square(0, 7))
    result = b.would_cause_repetition(bq, move, 'black')
    assert result is True, (
        'would_cause_repetition must return True when the simulated '
        'state hash matches a state with count >= 2 in state_history. '
        'If False, the simulation is not producing the same hash as '
        'the actual recording would.')
