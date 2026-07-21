"""End-to-end: load step-2 GDL (kings + queens + pawns) into the
GGP, enumerate legal moves from the initial state, sanity-check.

Step 2 board: kings + queens + 16 pawns (rank 2 white, rank 7
black). 32-piece game minus rooks/knights/bishops/boulder.

Expected legal moves from initial state for white:
- 8 white pawns, each at rank 2. Each pawn can:
    * Forward 1 (rank 2 -> rank 3) if empty — always empty initially.
    * Sideways left/right if empty — both ALWAYS blocked by friendly
      pawns at init (every pawn has friends at both sides on rank 2,
      except the a-file and h-file pawns which only have one neighbour
      — but that neighbour is friendly too, blocking sideways).
  So each pawn = 1 forward move = 8 moves total.
- White king at g1. Neighbours: f1, h1, f2, g2, h2 — f1 = empty,
  h1 = empty, f2/g2/h2 = own pawns. King can capture friendlies, so
  all 5 neighbours are reachable. **But step-2 GDL's legal rule
  excludes friend_at**, so only f1 and h1. = 2 king moves.
- White queen at b1. Neighbours: a1, c1, a2, b2, c2 — a1/c1 empty,
  a2/b2/c2 = own pawns. Excluding friendlies = 2 queen moves.

Total: 8 + 2 + 2 = 12 legal moves for white at init.

(The GDL doesn't yet encode the v2 king's friendly-capture
ability — that's a later refinement. Step-2 king rule is the
standard king-step minus friendly-occupied. Verified by
inspection of docs/gdl/step2_kings_queens_pawns.gdl.)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


GDL_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl')
STEP2 = os.path.join(GDL_DIR, 'step2_kings_queens_pawns.gdl')


def test_step2_loads_into_ggp():
    g = GGPGame.from_file(STEP2)
    assert g is not None


def test_step2_has_two_roles():
    g = GGPGame.from_file(STEP2)
    assert sorted(g.roles) == ['black', 'white']


def test_step2_initial_state_has_20_cells():
    """2 kings + 2 queens + 16 pawns = 20 cells."""
    g = GGPGame.from_file(STEP2)
    cells = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell']
    assert len(cells) == 20


def test_step2_initial_state_has_all_pawns():
    g = GGPGame.from_file(STEP2)
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    for f in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'):
        assert cells.get((f, '2')) == ('white', 'pawn')
        assert cells.get((f, '7')) == ('black', 'pawn')


def test_step2_legal_white_moves_at_init():
    """8 pawn forward moves + 5 king moves + 2 queen moves = 15.

    2026-07-20 in-place cleanup: the king's rule now matches the
    rulebook — the king may capture FRIENDLY pieces (the old early-
    step rule wrongly carried a friend-at guard), so g1 gains f2/g2/
    h2 captures on top of the empty f1/h1."""
    g = GGPGame.from_file(STEP2)
    moves = g.legal_moves('white')
    assert len(moves) == 15, (
        f'expected 12 white legal moves at init; got {len(moves)}: '
        f'{moves}')


def test_step2_black_plays_noop_at_init():
    g = GGPGame.from_file(STEP2)
    moves = g.legal_moves('black')
    assert moves == ['noop']


def test_step2_a2_pawn_can_only_move_forward():
    """The a-file pawn at a2: no leftward sideways (off-board),
    rightward sideways blocked by b-pawn. Only a2->a3 legal."""
    g = GGPGame.from_file(STEP2)
    moves = g.legal_moves('white')
    a2_moves = [m for m in moves
                if isinstance(m, tuple) and len(m) >= 4
                and m[2] == 'a' and m[3] == '2']
    # Should be just the forward move.
    assert len(a2_moves) == 1
    assert a2_moves[0] == ('move', 'pawn', 'a', '2', 'a', '3')


def test_step2_step_advances_state():
    """Move a2 -> a3, verify state updated."""
    g = GGPGame.from_file(STEP2)
    move = ('move', 'pawn', 'a', '2', 'a', '3')
    g.step({'white': move, 'black': 'noop'})
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    assert cells.get(('a', '3')) == ('white', 'pawn')
    assert ('a', '2') not in cells
    assert ('control', 'black') in g.state


def test_step2_after_step_black_pawn_can_move_forward():
    """After white's a2->a3, black's a7->a6 should be legal."""
    g = GGPGame.from_file(STEP2)
    g.step({
        'white': ('move', 'pawn', 'a', '2', 'a', '3'),
        'black': 'noop',
    })
    moves = g.legal_moves('black')
    a7_moves = [m for m in moves
                if isinstance(m, tuple) and len(m) >= 4
                and m[2] == 'a' and m[3] == '7']
    assert ('move', 'pawn', 'a', '7', 'a', '6') in a7_moves


def test_step2_pawn_promotes_to_queen():
    """Force a pawn close to the last rank, push it, verify it
    becomes a queen in the next state."""
    g = GGPGame.from_file(STEP2)
    # Reset to a position where white has a pawn at a7 and black
    # has nothing on a8.
    g.state = {
        ('cell', 'g', '1', 'white', 'king'),
        ('cell', 'b', '1', 'white', 'queen'),
        ('cell', 'b', '8', 'black', 'king'),
        ('cell', 'g', '8', 'black', 'queen'),
        ('cell', 'a', '7', 'white', 'pawn'),  # ready to promote
        ('control', 'white'),
    }
    # 2026-07-20: promotion is an explicit action with a form choice
    # (a plain pawn move onto the last rank is no longer legal).
    move = ('promote', 'a', '7', 'a', '8', 'queen')
    assert move in g.legal_moves('white')
    g.step({'white': move, 'black': 'noop'})
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    # Pawn promoted to queen at a8.
    assert cells.get(('a', '8')) == ('white', 'queen'), (
        f'pawn at a8 should have promoted to queen; cells now {cells}')


def test_step2_random_self_play_runs_without_error():
    """Play a few turns of random self-play. Shouldn't crash or
    hang; should reach terminal or step cap."""
    import random
    random.seed(31)
    g = GGPGame.from_file(STEP2)
    players = {
        'white': RandomGGPPlayer('white', seed=1),
        'black': RandomGGPPlayer('black', seed=2),
    }
    result = play_game(g, players, max_steps=20)
    # Just verify we got back a dict.
    assert 'white' in result
    assert 'black' in result
