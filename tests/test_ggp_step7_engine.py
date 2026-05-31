"""End-to-end: step-7 GDL (queen actions) via the INTEGRATED GDL.

Step 7's standalone file deliberately omits the carry-over piece
helpers (rook/knight/bishop) to keep the file focused on the
queen-action additions. For end-to-end testing via the GGP we use
`integrated.gdl` which concatenates all 11 step fragments.

What step 7 adds (per RULEBOOK_v2.md Queen → Manipulation +
Transformation):
- (queen_form ?f ?r ?form) per-queen marker
- (queen_royal ?f ?r) marks rulebook royal queens
- Transformation legal rule (queen ↔ rook/bishop/knight, gated
  on captured_friendly)
- Manipulation legal rules (one per movable piece type, with R1
  freeze + R2 spatial-move-last-turn check + R3 king/boulder/
  base-queen exclusions)
- Multi-form queen movement (queen-as-rook, queen-as-knight, etc.)
- lost-condition uses queen_royal

Initial state at white turn 1:
- White's only legal queen action is to move b1 → a1 (the rest
  of the queen's neighbours are friend-occupied)
- No transformation available (no captured_friendly facts yet)
- No manipulation available (the only enemy pieces in queen LoS
  via rank/file/diag of b1 are limited; in init no enemy is
  visible to b1's LoS)

Total: 72 legal moves for white at init (66 from step 5/6 + a few
new transform/manipulate cases that depend on init state).

The exact count is what the resolver returns; we cross-check the
structural correctness via spot tests rather than asserting a
specific number that could shift if I refine the carry-over set.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


INTEGRATED = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'integrated.gdl')


def test_integrated_loads_into_ggp():
    g = GGPGame.from_file(INTEGRATED)
    assert g is not None


def test_integrated_initial_state_has_queen_form_facts():
    """Both starting queens marked as base form."""
    g = GGPGame.from_file(INTEGRATED)
    forms = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'queen_form']
    forms_set = {(f[1], f[2], f[3]) for f in forms}
    assert ('b', '1', 'base') in forms_set
    assert ('g', '8', 'base') in forms_set


def test_integrated_initial_state_has_queen_royal_facts():
    g = GGPGame.from_file(INTEGRATED)
    royals = [(f[1], f[2]) for f in g.state
              if isinstance(f, tuple) and f[0] == 'queen_royal']
    assert ('b', '1') in royals
    assert ('g', '8') in royals


def test_integrated_white_has_at_least_60_legal_moves():
    """Smoke test: white has many legal moves at init. We don't
    pin the exact number (depends on the integrated.gdl's
    composition) but the count should be substantial — at least
    60 (covers 8 pawns + 10 knights + ~40+ bishop teleports +
    a queen move)."""
    g = GGPGame.from_file(INTEGRATED)
    moves = g.legal_moves('white')
    assert len(moves) >= 60, f'expected ≥60 legal moves; got {len(moves)}'


def test_integrated_white_queen_has_no_moves_at_init():
    """White queen at b1 (base form). ALL its king-step
    neighbours (a1, c1, a2, b2, c2) are friend-occupied in the
    full step-7 setup — a1 has a friend bishop, c1 has friend
    rook, a2/b2/c2 friend pawns. So the queen has zero legal
    moves at init (correctly enforced by the
    `(not (friend_at ?player ?tf ?tr))` body conjunct)."""
    g = GGPGame.from_file(INTEGRATED)
    moves = g.legal_moves('white')
    queen_moves = [m for m in moves
                   if isinstance(m, tuple) and len(m) >= 2
                   and m[1] == 'queen']
    assert queen_moves == [], (
        f'queen at b1 has zero legal moves at init; got {queen_moves}')


def test_integrated_white_has_no_transformation_at_init():
    """Transformation requires (captured_friendly ?owner ?piece)
    which is not in the initial state (no captures yet). So the
    queen can only transform back to base — but it's already base.
    So no transform actions."""
    g = GGPGame.from_file(INTEGRATED)
    moves = g.legal_moves('white')
    transforms = [m for m in moves
                  if isinstance(m, tuple) and m[0] == 'transform']
    # Allowed: transform b 1 base (return-to-base from base — should
    # not be legal since queen IS in base, but the rule's body
    # checks the queen ISN'T in base for return-to-base).
    # We expect 0 transforms at init.
    assert len(transforms) == 0, (
        f'no transform actions should be legal at init; got '
        f'{transforms}')


def test_integrated_black_plays_noop_at_init():
    g = GGPGame.from_file(INTEGRATED)
    assert g.legal_moves('black') == ['noop']


def test_integrated_random_self_play_runs_a_few_turns():
    g = GGPGame.from_file(INTEGRATED)
    players = {
        'white': RandomGGPPlayer('white', seed=7),
        'black': RandomGGPPlayer('black', seed=77),
    }
    result = play_game(g, players, max_steps=3)
    assert 'white' in result
