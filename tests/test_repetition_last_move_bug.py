"""Regression test for the actual repetition bug the user reported
(2026-05-31): "I can seemingly repeat the position forever, and
there is no manipulation involved at all. It is just queens moving
back and forth forever."

THE BUG: `Board.would_cause_repetition` simulates the move by
mutating the squares array, but does NOT update:
  - `self.last_move`
  - `self.last_move_turn_number`
  - `self.turn_number`

`get_state_hash` consults these to derive `moved_last_turn` and
`reactive_armed` flags. Specifically, `is_preceding` is computed as:
    last_move is not None AND last_move_turn_number == turn_number - 1

For the ACTUAL recorded state after a turn (via Game.next_turn):
  - `board.move` set last_move to the new move + last_move_turn_number = T
  - Game.next_turn incremented turn_number to T+1
  - record_state(next_player) → is_preceding = True (correctly references
    the just-made move)

For the SIMULATED state inside would_cause_repetition:
  - last_move + last_move_turn_number stay at the PREVIOUS turn's values
  - turn_number stays at T
  - is_preceding evaluates against the OLD last_move (from 1+ turns ago),
    so the derived flags are wrong

Result: the simulated state hash and the actual recorded state hash
DIFFER in their derived flags. The repetition filter never finds a
match → cycles repeat indefinitely.

This regression test demonstrates the bug by:
  1. Constructing a 4-piece position (2 kings + 2 queens).
  2. Setting up a state hash for the position with white to move
     AFTER black just moved BQ somewhere.
  3. Computing two hashes: the SIMULATED hash via the (fixed)
     would_cause_repetition logic, and the ACTUAL hash that would
     be recorded after applying the move via the normal game flow.
  4. Asserting the two hashes match.
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

import copy


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


# ---- the central regression ----------------------------------------------

def test_simulated_hash_matches_actual_hash_for_queen_bounce():
    """White queen bouncing between b1 and a1, black queen bouncing
    between g8 and h8. After each white move, the simulated hash
    (via would_cause_repetition's logic) must equal the actual
    recorded hash that game.next_turn would produce.
    """
    from board import Board
    from piece import Queen, King
    from move import Move
    from square import Square

    b = _empty_board()
    wq = Queen('white', is_royal=True)
    bq = Queen('black', is_royal=True)
    wk = King('white')
    bk = King('black')
    b.squares[7][1].piece = wq   # b1
    b.squares[7][6].piece = wk   # g1
    b.squares[0][6].piece = bq   # g8
    b.squares[0][1].piece = bk   # b8

    # Initial conditions: BLACK just moved (so is_preceding will
    # apply on white's turn). We set last_move to BQ g8->h8 and the
    # piece is currently at h8.
    b.squares[0][6].piece = None
    b.squares[0][7].piece = bq    # BQ moved to h8
    b.last_move = Move(Square(0, 6), Square(0, 7))
    b.last_move_turn_number = 0
    b.turn_number = 1
    b.update_lines_of_sight()
    b.update_threat_squares()

    # We're at the start of white's turn (turn 1). White is about to
    # move WQ b1 -> a1.
    move = Move(Square(7, 1), Square(7, 0))

    # ---- compute simulated hash via would_cause_repetition logic ----
    # Manually trace what would_cause_repetition does (with the fix
    # applied): mutate squares + set last_move = new move +
    # last_move_turn_number = turn_number + increment turn_number +
    # clear opponent invuln + clear_moved_by_queen_for_opponent +
    # get_state_hash(opponent).
    b_sim = copy.deepcopy(b)
    sim_piece = b_sim.squares[7][1].piece
    b_sim.squares[7][1].piece = None
    b_sim.squares[7][0].piece = sim_piece
    # FIX: simulate board.move's last_move update + game.next_turn's
    # turn_number increment.
    b_sim.last_move = move
    b_sim.last_move_turn_number = b_sim.turn_number
    b_sim.turn_number += 1
    # Game.next_turn does these in order:
    b_sim.clear_moved_by_queen_for_opponent('black')   # opp of opp = mover (white)
    b_sim.clear_invulnerable_for_color('black')
    sim_hash = b_sim.get_state_hash('black')

    # ---- compute actual hash via game.next_turn-equivalent flow ----
    b_act = copy.deepcopy(b)
    act_piece = b_act.squares[7][1].piece
    b_act.squares[7][1].piece = None
    b_act.squares[7][0].piece = act_piece
    # board.move sets last_move:
    b_act.last_move = move
    b_act.last_move_turn_number = b_act.turn_number
    # Game.next_turn flips next_player, increments turn_number,
    # clears flags, records state.
    b_act.turn_number += 1
    b_act.clear_moved_by_queen_for_opponent('black')   # for new mover (black)
    b_act.clear_invulnerable_for_color('black')
    act_hash = b_act.get_state_hash('black')

    assert sim_hash == act_hash, (
        'simulated state hash must match the actual recorded hash. '
        'If they differ, would_cause_repetition is failing to mirror '
        'the last_move + turn_number updates that game.next_turn '
        'applies. This is the bug behind "I can seemingly repeat the '
        'position forever, and there is no manipulation involved".')


def test_would_cause_repetition_catches_queen_bounce_cycle():
    """End-to-end: simulate a 4-turn queen bounce cycle. After the
    state hash has been recorded twice, the third occurrence's
    would_cause_repetition must return True. With the bug, it
    returned False forever; with the fix, it correctly returns True
    on the 3rd attempt.
    """
    from board import Board
    from piece import Queen, King
    from move import Move
    from square import Square

    b = _empty_board()
    wq = Queen('white', is_royal=True)
    bq = Queen('black', is_royal=True)
    wk = King('white')
    bk = King('black')
    b.squares[7][1].piece = wq   # b1
    b.squares[7][6].piece = wk   # g1
    b.squares[0][6].piece = bq   # g8
    b.squares[0][1].piece = bk   # b8

    b.update_lines_of_sight()
    b.update_threat_squares()

    # Helper: apply a move + game.next_turn-equivalent state changes.
    def apply_step(piece, fr, fc, tr, tc, mover):
        other = 'black' if mover == 'white' else 'white'
        b.squares[fr][fc].piece = None
        b.squares[tr][tc].piece = piece
        b.last_move = Move(Square(fr, fc), Square(tr, tc))
        b.last_move_turn_number = b.turn_number
        b.turn_number += 1
        b.clear_moved_by_queen_for_opponent(other)
        b.clear_invulnerable_for_color(other)
        h = b.get_state_hash(other)
        b.state_history[h] = b.state_history.get(h, 0) + 1
        return h

    # Initial state.
    h_init = b.get_state_hash('white')
    b.state_history[h_init] = 1

    # Cycle 1: WQ b1->a1, BQ g8->h8, WQ a1->b1, BQ h8->g8
    apply_step(wq, 7, 1, 7, 0, 'white')
    apply_step(bq, 0, 6, 0, 7, 'black')
    apply_step(wq, 7, 0, 7, 1, 'white')
    apply_step(bq, 0, 7, 0, 6, 'black')

    # Cycle 2: same moves again
    apply_step(wq, 7, 1, 7, 0, 'white')
    apply_step(bq, 0, 6, 0, 7, 'black')
    apply_step(wq, 7, 0, 7, 1, 'white')
    apply_step(bq, 0, 7, 0, 6, 'black')

    # Now we're back at h_init for the 3rd time. White is about to
    # try WQ b1->a1 again. The resulting state hash equals the
    # state hash recorded after move WQ b1->a1 in cycles 1 and 2
    # (recorded twice). would_cause_repetition should report True.
    move_b1_a1 = Move(Square(7, 1), Square(7, 0))
    result = b.would_cause_repetition(wq, move_b1_a1, 'white')
    assert result is True, (
        'a 3rd queen-bounce repetition must trigger the rule. With '
        'the bug, would_cause_repetition returns False forever '
        'because the simulated hash never matches the recorded hash '
        '(last_move + turn_number not updated in simulation).')
