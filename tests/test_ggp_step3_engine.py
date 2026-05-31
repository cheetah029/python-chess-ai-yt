"""End-to-end: step-3 GDL (kings + queens + pawns + rooks) into
the GGP.

Step 3 board: 2 kings + 2 queens + 4 rooks + 16 pawns = 24 cells.
First multi-segment move in the series (rook 2-segment via
sweep_path + perpendicular).

Expected legal moves for white at init:
- 8 pawns × 1 forward each (sideways blocked by friendly pawns)
- 2 rooks at c1 and f1, each with 1 legal length-zero move:
  c1 → d1 (east, since b1 has friend queen, c2 has friend pawn)
  f1 → e1 (west, since g1 has friend king, f2 has friend pawn)
  Length-≥1 moves blocked because every perpendicular destination
  is a friend square (d2, e2, b2 are friend pawns).
- 1 king at g1: only g1 → h1 (other neighbours friend).
- 1 queen at b1: only b1 → a1 (other neighbours friend).

Total: 8 + 2 + 1 + 1 = 12 legal moves for white.

This is the FIRST end-to-end multi-segment validation. Exercises
the resolver's handling of:
- The `sweep_path` recursive rule (base case + recursive case)
- `(not (occupied ?))` inside a body
- `perpendicular ?dir1 ?dir2` enumeration
- Multiple matching rules with same predicate (`legal` rook
  length-zero + length-≥1)
- `(not (friend_at ?))` destination check that filters
  segment-≥1 moves where the sweep destination is friend-occupied
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


STEP3 = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'step3_add_rook.gdl')


def test_step3_loads_into_ggp():
    g = GGPGame.from_file(STEP3)
    assert g is not None


def test_step3_initial_state_has_24_cells():
    """2 kings + 2 queens + 4 rooks + 16 pawns = 24."""
    g = GGPGame.from_file(STEP3)
    cells = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell']
    assert len(cells) == 24


def test_step3_rooks_at_rulebook_squares():
    """White rooks at c1, f1; black rooks at c8, f8 (rotational
    symmetric back rank per RULEBOOK_v2.md)."""
    g = GGPGame.from_file(STEP3)
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    assert cells.get(('c', '1')) == ('white', 'rook')
    assert cells.get(('f', '1')) == ('white', 'rook')
    assert cells.get(('c', '8')) == ('black', 'rook')
    assert cells.get(('f', '8')) == ('black', 'rook')


def test_step3_white_has_12_legal_moves_at_init():
    g = GGPGame.from_file(STEP3)
    moves = g.legal_moves('white')
    assert len(moves) == 12, (
        f'expected 12 legal white moves; got {len(moves)}: {moves}')


def test_step3_white_rook_c1_to_d1_legal():
    """The one legal rook move from c1: east 1 square (length-
    zero segment 2)."""
    g = GGPGame.from_file(STEP3)
    moves = g.legal_moves('white')
    assert ('move', 'rook', 'c', '1', 'd', '1') in moves


def test_step3_white_rook_c1_to_d2_blocked():
    """Length-≥1 c1 → d1 → north to d2: blocked because d2 has
    friend pawn."""
    g = GGPGame.from_file(STEP3)
    moves = g.legal_moves('white')
    assert ('move', 'rook', 'c', '1', 'd', '2') not in moves


def test_step3_white_rook_f1_to_e1_legal():
    g = GGPGame.from_file(STEP3)
    moves = g.legal_moves('white')
    assert ('move', 'rook', 'f', '1', 'e', '1') in moves


def test_step3_black_plays_noop_at_init():
    g = GGPGame.from_file(STEP3)
    assert g.legal_moves('black') == ['noop']


def test_step3_step_applies_rook_move():
    """Apply WR c1 → d1, verify state."""
    g = GGPGame.from_file(STEP3)
    g.step({
        'white': ('move', 'rook', 'c', '1', 'd', '1'),
        'black': 'noop',
    })
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    assert cells.get(('d', '1')) == ('white', 'rook')
    assert ('c', '1') not in cells


def test_step3_after_pawn_advance_rook_can_use_segment_2():
    """After white advances d2 → d3, rook at c1 can now do
    c1 → d1 east + perpendicular north sweep_path to d2 (which
    is now empty)."""
    g = GGPGame.from_file(STEP3)
    # White d2 → d3 (clears d2).
    g.step({
        'white': ('move', 'pawn', 'd', '2', 'd', '3'),
        'black': 'noop',
    })
    # Now it's black's turn — they play noop equivalent.
    g.step({
        'white': 'noop',
        'black': ('move', 'pawn', 'a', '7', 'a', '6'),
    })
    # White's turn again. Rook c1 → d2 (via c1→d1 east + north
    # sweep to d2): d2 is empty now.
    moves = g.legal_moves('white')
    rook_moves = [m for m in moves
                  if isinstance(m, tuple) and len(m) >= 2
                  and m[1] == 'rook']
    assert ('move', 'rook', 'c', '1', 'd', '2') in moves, (
        f'after d2 cleared, rook c1 should reach d2 via '
        f'segment-≥1; got rook moves: {rook_moves}')


def test_step3_random_self_play_runs_without_error():
    import random
    random.seed(303)
    g = GGPGame.from_file(STEP3)
    players = {
        'white': RandomGGPPlayer('white', seed=1),
        'black': RandomGGPPlayer('black', seed=2),
    }
    result = play_game(g, players, max_steps=15)
    assert 'white' in result
    assert 'black' in result
