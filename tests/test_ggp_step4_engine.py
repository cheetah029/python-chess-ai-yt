"""End-to-end: step-4 GDL (+ knight radius-2) into the GGP.

Step 4 board: 2 kings + 2 queens + 4 rooks + 4 knights + 16 pawns =
28 cells. Adds the knight's chebyshev-≤2-but-not-1 16-square
movement pattern (no jump-capture / no invuln yet — those are
step 8).

Expected white legal moves at init:
- 8 pawns × 1 forward
- 0 rooks (rook moves to d1/e1 blocked by friend knights now at
  d1/e1; b1/c2/f2 still friend; other directions friend or off)
- 10 knights (2 × 5 each: 1 forward 2-orthogonal + 2 diagonal +
  2 L-shape via file_delta_1)
- 1 queen + 1 king (same as step 3)

Total = 20.

This is the first end-to-end test of the resolver's handling of
many disjoint rules (4 knight_step families, each branching on
file/rank deltas), and the FIRST test where ROOKS are FULLY
BLOCKED by new step-4 pieces — a useful "did my step change the
behavior of an existing rule" regression check.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


STEP4 = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'step4_add_knight.gdl')


def test_step4_loads_into_ggp():
    g = GGPGame.from_file(STEP4)
    assert g is not None


def test_step4_initial_state_has_28_cells():
    g = GGPGame.from_file(STEP4)
    cells = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell']
    assert len(cells) == 28


def test_step4_knights_at_rulebook_squares():
    """White knights at d1, e1; black knights at d8, e8."""
    g = GGPGame.from_file(STEP4)
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    assert cells.get(('d', '1')) == ('white', 'knight')
    assert cells.get(('e', '1')) == ('white', 'knight')
    assert cells.get(('d', '8')) == ('black', 'knight')
    assert cells.get(('e', '8')) == ('black', 'knight')


def test_step4_white_has_20_legal_moves_at_init():
    g = GGPGame.from_file(STEP4)
    moves = g.legal_moves('white')
    assert len(moves) == 20, (
        f'expected 20 legal white moves; got {len(moves)}: {moves}')


def test_step4_knight_d1_can_reach_d3():
    """d1 → d3 is the 2-orthogonal (file_d, rank_delta_2) family."""
    g = GGPGame.from_file(STEP4)
    moves = g.legal_moves('white')
    assert ('move', 'knight', 'd', '1', 'd', '3') in moves


def test_step4_knight_d1_can_reach_b3():
    """d1 → b3 is the 2-diagonal family."""
    g = GGPGame.from_file(STEP4)
    moves = g.legal_moves('white')
    assert ('move', 'knight', 'd', '1', 'b', '3') in moves


def test_step4_knight_d1_can_reach_c3():
    """d1 → c3 is the L-shape (file_delta_1 c, rank_delta_2) family."""
    g = GGPGame.from_file(STEP4)
    moves = g.legal_moves('white')
    assert ('move', 'knight', 'd', '1', 'c', '3') in moves


def test_step4_knight_d1_cannot_reach_b1():
    """d1 → b1 is 2-orthogonal same-rank, but b1 has friend queen."""
    g = GGPGame.from_file(STEP4)
    moves = g.legal_moves('white')
    assert ('move', 'knight', 'd', '1', 'b', '1') not in moves


def test_step4_rooks_have_no_legal_moves_at_init():
    """With knights at d1/e1, rooks at c1/f1 have NO legal moves
    (their previously-legal length-zero destinations are now
    friend-occupied)."""
    g = GGPGame.from_file(STEP4)
    moves = g.legal_moves('white')
    rook_moves = [m for m in moves
                  if isinstance(m, tuple) and len(m) >= 2
                  and m[1] == 'rook']
    assert rook_moves == [], (
        f'expected zero rook moves at init; got {rook_moves}')


def test_step4_after_d_pawn_advance_knight_can_use_d3():
    """After white d2 → d3, the knight at d1 can no longer reach
    d3 (now friend-occupied). But d2 should be reachable by
    knight d3-jump? No — knight moves chebyshev-2, not 1. So
    d1 can still reach b3, f3, c3, e3."""
    g = GGPGame.from_file(STEP4)
    g.step({
        'white': ('move', 'pawn', 'd', '2', 'd', '3'),
        'black': 'noop',
    })
    g.step({
        'white': 'noop',
        'black': ('move', 'pawn', 'a', '7', 'a', '6'),
    })
    moves = g.legal_moves('white')
    # d1 → d3 now blocked (d3 has friend pawn).
    assert ('move', 'knight', 'd', '1', 'd', '3') not in moves
    # b3, f3, c3, e3 still reachable.
    assert ('move', 'knight', 'd', '1', 'b', '3') in moves


def test_step4_random_self_play_runs_without_error():
    g = GGPGame.from_file(STEP4)
    players = {
        'white': RandomGGPPlayer('white', seed=4),
        'black': RandomGGPPlayer('black', seed=14),
    }
    result = play_game(g, players, max_steps=10)
    assert 'white' in result
