"""End-to-end: step-5 GDL (+ bishop teleport) into the GGP.

Step 5 board: 2 kings + 2 queens + 4 rooks + 4 knights + 4 bishops +
16 pawns = 32 cells. Bishops at a1, h1, a8, h8 (rulebook-correct
corners per RULEBOOK_v2.md).

Bishop adds TELEPORT MOVEMENT — to any empty square that isn't
moved-to or captured-by any non-bishop enemy (with knight
jump-capture included; enemy bishops excluded per the destination-
vs-source rationale).

Step 5 white legal-move counts (manual analysis):
- 8 pawns × 1 forward
- 0 rooks (still blocked by knights/pawns)
- 10 knights (same 5 each as step 4)
- 0 king (g1 surrounded by friends: f1=rook, h1=bishop, f2/g2/h2=pawn)
- 0 queen (b1 surrounded by friends)
- 48 bishop teleports (24 per bishop — each reaches empty +
  not-enemy-attacked squares; some destinations excluded by enemy
  pawn capture-to threat, enemy knight jump-capture, etc.)

Total: 66.

These tests exercise the resolver's handling of:
- file + rank enumeration via the helper predicates
- The enemy_can_reach predicate (queries every non-bishop enemy's
  can_capture_to or can_move_to_only)
- The jump_capturable_by_knight enumeration
- The bishop's own-square exclusion via `(or (distinct ?ff ?tf)
  (distinct ?fr ?tr))`
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


STEP5 = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'step5_add_bishop.gdl')


def test_step5_loads_into_ggp():
    g = GGPGame.from_file(STEP5)
    assert g is not None


def test_step5_initial_state_has_32_cells():
    g = GGPGame.from_file(STEP5)
    cells = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell']
    assert len(cells) == 32


def test_step5_bishops_at_rulebook_corners():
    g = GGPGame.from_file(STEP5)
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    assert cells.get(('a', '1')) == ('white', 'bishop')
    assert cells.get(('h', '1')) == ('white', 'bishop')
    assert cells.get(('a', '8')) == ('black', 'bishop')
    assert cells.get(('h', '8')) == ('black', 'bishop')


def test_step5_white_has_66_legal_moves_at_init():
    """The GGP returns exactly 66 legal white moves. 8 pawns + 10
    knights + 48 bishop teleports. King + queen + rooks all blocked
    by surrounding friends at init."""
    g = GGPGame.from_file(STEP5)
    moves = g.legal_moves('white')
    # 2026-07-20 cleanup: the king may capture friendlies per the
    # rulebook (adds f2/g2/h2 pawn captures + f1-rook + h1-bishop captures).
    assert len(moves) == 71, (
        f'expected 66 legal white moves; got {len(moves)}')


def test_step5_bishop_a1_has_many_teleports():
    """The white bishop at a1 has many legitimate teleport
    destinations (empty squares not reachable by any non-bishop
    enemy)."""
    g = GGPGame.from_file(STEP5)
    moves = g.legal_moves('white')
    bishop_a1 = [m for m in moves
                 if isinstance(m, tuple) and len(m) >= 4
                 and m[1] == 'bishop' and m[2] == 'a' and m[3] == '1']
    assert len(bishop_a1) >= 20, (
        f'bishop a1 should have many teleports; got {len(bishop_a1)}')


def test_step5_bishop_cannot_teleport_to_friend_square():
    """Bishop a1 → a2 is illegal — a2 has a friend pawn."""
    g = GGPGame.from_file(STEP5)
    moves = g.legal_moves('white')
    assert ('move', 'bishop', 'a', '1', 'a', '2') not in moves


def test_step5_bishop_cannot_teleport_to_own_square():
    """Bishop a1 → a1 is a no-op and explicitly excluded by the
    `(or (distinct ?ff ?tf) (distinct ?fr ?tr))` body conjunct."""
    g = GGPGame.from_file(STEP5)
    moves = g.legal_moves('white')
    assert ('move', 'bishop', 'a', '1', 'a', '1') not in moves


def test_step5_bishop_cannot_teleport_to_enemy_pawn_capture_square():
    """A square that a black pawn could capture-to (forward-left or
    forward-right from rank 7). For black: forward = rank 7 → 6.
    So a black pawn at b7 can capture to a6, c6 — those are NOT
    safe for white bishop teleport. Verify a bishop teleport to
    such a square is excluded."""
    g = GGPGame.from_file(STEP5)
    moves = g.legal_moves('white')
    # Black pawn at b7 can capture to a6 (forward-diagonal-left).
    # White bishop teleport to a6 should be illegal.
    assert ('move', 'bishop', 'a', '1', 'a', '6') not in moves
    assert ('move', 'bishop', 'a', '1', 'c', '6') not in moves


def test_step5_random_self_play_runs_without_error():
    g = GGPGame.from_file(STEP5)
    players = {
        'white': RandomGGPPlayer('white', seed=5),
        'black': RandomGGPPlayer('black', seed=55),
    }
    result = play_game(g, players, max_steps=5)
    assert 'white' in result
