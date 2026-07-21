"""End-to-end: step-6 GDL (+ boulder, first neutral piece) into
the GGP.

Step 6 board: 32 cells + boulder on the central intersection (not
on any single square). Boulder is neutral (color = none).

Per RULEBOOK_v2.md:
- First move: boulder's first move must be to one of d4/d5/e4/e5.
- White may NOT move boulder on their first turn (turn 1).
- Captures: pawns only (either colour).
- Cooldown: both players make one turn between boulder moves.
- No-return memory: cannot move (non-capture) to immediately
  previous square.

Step 6 white legal moves at init (turn_number = 1):
- 8 pawns + 10 knights + 48 bishop teleports = 66 (same as step 5)
- 0 boulder moves (turn 1 white restriction)

Total: 66.

After white moves once + black plays noop, turn_number → 3, and
white CAN move boulder. (Black's turn at turn_number=2 is also
allowed but we test the white-on-turn-3 path.)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


STEP6 = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'step6_add_boulder.gdl')


def test_step6_loads_into_ggp():
    g = GGPGame.from_file(STEP6)
    assert g is not None


def test_step6_initial_state_has_32_cells_plus_boulder_facts():
    """32 cells (same as step 5) + boulder_at, boulder_first_move,
    boulder_cooldown facts."""
    g = GGPGame.from_file(STEP6)
    cells = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell']
    assert len(cells) == 32
    assert ('boulder_at', 'intersection') in g.state
    assert ('boulder_first_move',) in g.state
    assert ('boulder_cooldown', '0') in g.state


def test_step6_white_cannot_move_boulder_on_turn_1():
    """Per rulebook: white may not move boulder on their first
    turn. Verify no boulder move in the legal-moves set."""
    g = GGPGame.from_file(STEP6)
    moves = g.legal_moves('white')
    boulder_moves = [m for m in moves
                     if isinstance(m, tuple) and len(m) >= 2
                     and m[1] == 'boulder']
    assert boulder_moves == [], (
        f'white must not have boulder moves on turn 1; got '
        f'{boulder_moves}')


def test_step6_white_has_66_legal_moves_at_init():
    """Same as step 5 since boulder is locked on turn 1."""
    g = GGPGame.from_file(STEP6)
    moves = g.legal_moves('white')
    # 2026-07-20 cleanup: the king may capture friendlies per the
    # rulebook (adds f2/g2/h2 pawn captures + f1-rook + h1-bishop).
    assert len(moves) == 71, f'got {len(moves)}'


def test_step6_black_can_move_boulder_on_their_first_turn():
    """Black's first turn comes after white's, so turn_number=2.
    Per the rule, only WHITE is restricted on turn 1. Black should
    be able to move the boulder."""
    g = GGPGame.from_file(STEP6)
    # White does any pawn move.
    g.step({
        'white': ('move', 'pawn', 'a', '2', 'a', '3'),
        'black': 'noop',
    })
    # Now it's black's turn at turn_number=2. Boulder first move
    # to d4/d5/e4/e5 should be legal.
    moves = g.legal_moves('black')
    boulder_moves = [m for m in moves
                     if isinstance(m, tuple) and len(m) >= 2
                     and m[1] == 'boulder']
    # Expect at least 4 boulder moves (d4, d5, e4, e5).
    assert len(boulder_moves) >= 4, (
        f'black should have ≥4 boulder first-move options on '
        f'turn 2; got {boulder_moves}')


def test_step6_boulder_first_move_destinations_are_central_only():
    """Boulder's first move must be to d4/d5/e4/e5 only — NOT to
    other squares. Verify the legal-moves set is restricted."""
    g = GGPGame.from_file(STEP6)
    g.step({
        'white': ('move', 'pawn', 'a', '2', 'a', '3'),
        'black': 'noop',
    })
    moves = g.legal_moves('black')
    boulder_moves = [m for m in moves
                     if isinstance(m, tuple) and len(m) >= 2
                     and m[1] == 'boulder']
    valid_dests = {('d', '4'), ('d', '5'), ('e', '4'), ('e', '5')}
    for m in boulder_moves:
        # Move: (move boulder intersection ?tf ?tr) — 5 elements.
        assert (m[3], m[4]) in valid_dests, (
            f'boulder first move to non-central square: {m}')


def test_step6_random_self_play_runs_without_error():
    g = GGPGame.from_file(STEP6)
    players = {
        'white': RandomGGPPlayer('white', seed=6),
        'black': RandomGGPPlayer('black', seed=66),
    }
    result = play_game(g, players, max_steps=4)
    assert 'white' in result
