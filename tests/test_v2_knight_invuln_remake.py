"""Tests for the knight-invulnerability REMAKE (2026-06-14):
the "leap between friend and foe" rule.

NEW RULE (replaces the friendly/boulder-only jump rule):

    A knight gains invulnerability (for the opponent's next turn
    only) when it makes a NON-CAPTURING leap over a piece and lands
    adjacent (chebyshev-1) to a piece of the OPPOSITE ALLEGIANCE to
    the one it jumped:

      - jump a friendly piece or the boulder -> land beside an enemy
        (identical to the old rule), OR
      - jump an ENEMY -> land beside a FRIENDLY piece or the boulder
        (the NEW case).

    The boulder counts as friendly-side in both roles (jumpable
    obstacle, landing-adjacent support) and never as an enemy.
    Because the jumped piece and the landing-adjacent piece must be
    of opposite allegiances, they can never be the same piece — no
    exclusion clause is needed, though the jumped square is still
    skipped in the adjacency scan for robustness.

    Unchanged: capturing moves (standard or accepted jump-capture)
    never grant; queen-manipulated knight moves never functionally
    grant; duration is one opponent turn.

    NEW consequence: a DECLINED jump-capture (non-capturing leap
    over an eligible enemy) CAN now grant invulnerability if a
    friendly/boulder is adjacent to the landing.

This file covers the four worked positions from the design
discussion (catapult-over-attacker, supported enemy-vault, deep
infiltration, bishop-pin geometry) plus unit cases.
"""

import os
import sys

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

import pytest

from board import Board
from piece import King, Knight, Pawn, Rook, Bishop, Boulder
from move import Move
from square import Square


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _empty_board():
    b = Board()
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    return b


def _board_with(white=(), black=(), boulder_at=None):
    """white/black: iterables of (factory, row, col)."""
    b = _empty_board()
    for factory, r, c in white:
        b.squares[r][c].piece = factory()
    for factory, r, c in black:
        b.squares[r][c].piece = factory()
    if boulder_at is not None:
        r, c = boulder_at
        b.squares[r][c].piece = Boulder()
        b.squares[r][c].piece.on_intersection = False
        b.squares[r][c].piece.first_move = False
    return b


def _stationary_last_move(b):
    """Set last_move to an unrelated old move so the jumped enemy is
    NOT jump-capture-eligible (the leap proceeds as a plain
    non-capture jump)."""
    b.last_move = Move(Square(7, 0), Square(7, 1))
    b.last_move_turn_number = 0
    b.turn_number = 5


# ===========================================================================
# NEW CASE: jump an enemy, land beside a friendly -> invulnerable
# ===========================================================================

def test_invuln_granted_jumping_enemy_landing_beside_friendly():
    """Core new case: knight (3,3) jumps enemy at (3,4), lands (3,5);
    white pawn at (4,5) adjacent to the landing -> invulnerable."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3),
               (lambda: Pawn('white'), 4, 5)],   # friendly beside landing
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4)],   # jumped enemy
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is True


def test_invuln_NOT_granted_jumping_enemy_with_no_friendly_at_landing():
    """Same leap but no white piece near the landing -> no invuln.
    (This is the deep-infiltration gate.)"""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3)],
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4)],
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is False


def test_invuln_NOT_granted_jumping_enemy_landing_beside_only_enemies():
    """Jumped an enemy; landing has ANOTHER enemy adjacent but no
    friendly -> no invuln (opposite-allegiance requirement)."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3)],
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4),    # jumped enemy
               (lambda: Pawn('black'), 4, 5)],   # second enemy at landing
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is False


def test_boulder_counts_as_landing_friendly_when_jumping_enemy():
    """Jump an enemy, land beside the BOULDER -> boulder counts as
    friendly-side support -> invulnerable."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3)],
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4)],
        boulder_at=(4, 5),                        # beside landing (3,5)
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is True


# ===========================================================================
# OLD CASE preserved: jump friendly/boulder, land beside enemy
# ===========================================================================

def test_invuln_still_granted_jumping_friendly_landing_beside_enemy():
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3),
               (lambda: Pawn('white'), 3, 4)],   # jumped friendly
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 4, 5)],   # enemy beside landing
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is True


def test_invuln_still_NOT_granted_jumping_friendly_no_enemy_at_landing():
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3),
               (lambda: Pawn('white'), 3, 4),
               (lambda: Pawn('white'), 4, 5)],   # friendly at landing: not enough
        black=[(lambda: King('black'), 0, 0)],
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert knight.invulnerable is False


# ===========================================================================
# Worked position 1 — catapult-over-attacker is BLOCKED
# ===========================================================================

def test_catapult_over_attacker_blocked():
    """Side-chat Position 1: knight e4=(4,4) with friendly pawn at
    d4=(4,3); black rook steps to e5=(3,4) attacking. Knight vaults
    the rook to e6=(2,4). The home pawn at d4 is NOT adjacent to the
    landing -> jumped enemy + no friendly at landing -> NO invuln."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 4, 4),   # e4
               (lambda: Pawn('white'), 4, 3)],    # d4 (home support)
        black=[(lambda: King('black'), 0, 0),
               (lambda: Rook('black'), 3, 4)],    # e5 attacker (jumped)
    )
    knight = b.squares[4][4].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(4, 4), Square(2, 4)))   # e4 -> e6
    assert knight.invulnerable is False, (
        'catapult-over-attacker must NOT grant invuln — the home '
        'friendly does not follow the knight in')


# ===========================================================================
# Worked position 1b — supported enemy-vault is GRANTED
# ===========================================================================

def test_supported_enemy_vault_granted():
    """Side-chat Position 1b: same leap but a white pawn at d6=(2,3)
    is adjacent to the landing e6=(2,4) -> invuln granted."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 4, 4),   # e4
               (lambda: Pawn('white'), 2, 3)],    # d6 (forward support)
        black=[(lambda: King('black'), 0, 0),
               (lambda: Rook('black'), 3, 4)],    # e5 (jumped)
    )
    knight = b.squares[4][4].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(4, 4), Square(2, 4)))   # e4 -> e6
    assert knight.invulnerable is True, (
        'supported enemy-vault (friendly adjacent to landing) must '
        'grant invuln — this is the new attacking case')


# ===========================================================================
# Worked position 2 — deep infiltration is BLOCKED
# ===========================================================================

def test_deep_infiltration_blocked():
    """Infiltrated knight at e6=(2,4) vaults black pawn f6=(2,5) to
    g6=(2,6), no white piece anywhere near -> no invuln."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 2, 4)],   # e6, already deep
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 2, 5),      # f6 (jumped)
               (lambda: Pawn('black'), 1, 3),      # d7
               (lambda: Pawn('black'), 1, 5)],     # f7
    )
    knight = b.squares[2][4].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(2, 4), Square(2, 6)))   # e6 -> g6
    assert knight.invulnerable is False


# ===========================================================================
# Worked position 3 — bishop radius-3 pin geometry
# ===========================================================================

def test_bishop_pin_geometry_no_landing_adjacent_to_bishop():
    """Knight e4=(4,4), bishop h7=(1,7) pinning on the clear e4-h7
    diagonal at chebyshev distance 3. Verify by enumeration: no legal
    knight destination is adjacent to the bishop, and the only
    candidate landing (g6) requires jumping f5=(3,5) which must be
    occupied — i.e. the diagonal blocked — contradicting the pin.
    This is the geometric fact behind 'the bishop endgame is safe'."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 0),
               (lambda: Knight('white'), 4, 4)],   # e4
        black=[(lambda: King('black'), 0, 0),
               (lambda: Bishop('black'), 1, 7)],   # h7
    )
    # All 16 radius-2 destinations from e4=(4,4):
    deltas = [(-2, 0), (2, 0), (0, -2), (0, 2),
              (-2, -2), (-2, 2), (2, -2), (2, 2),
              (-2, -1), (-2, 1), (2, -1), (2, 1),
              (-1, -2), (-1, 2), (1, -2), (1, 2)]
    bishop_pos = (1, 7)
    adjacent_landings = []
    for dr, dc in deltas:
        r, c = 4 + dr, 4 + dc
        if not (0 <= r < 8 and 0 <= c < 8):
            continue
        if max(abs(r - bishop_pos[0]), abs(c - bishop_pos[1])) <= 1:
            adjacent_landings.append((r, c))
    # Only g6=(2,6) is adjacent to h7=(1,7).
    assert adjacent_landings == [(2, 6)]
    # The leap e4->g6 is the 2-diagonal move whose jumped square is
    # f5=(3,5) — ON the e4-h7 pin diagonal. With the diagonal clear
    # (the pin premise) the jumped square is EMPTY, so the leap grants
    # nothing (no piece jumped) and the knight cannot involve the
    # bishop. Verify f5 is on the diagonal between e4 and h7:
    assert (3, 5) == (4 - 1, 4 + 1)          # one diagonal step from e4
    assert abs(3 - 1) == abs(5 - 7)          # colinear with h7
    # And with f5 empty, moving e4->g6 must not grant invuln:
    knight = b.squares[4][4].piece
    _stationary_last_move(b)
    b.move(knight, Move(Square(4, 4), Square(2, 6)))
    assert knight.invulnerable is False


# ===========================================================================
# Jump-capture interaction
# ===========================================================================

def test_declined_jump_capture_over_enemy_CAN_now_grant_invuln():
    """NEW consequence: knight declines an offered jump-capture (the
    enemy moved last turn, so it's eligible) — the leap is
    non-capturing, the jumped piece is an enemy, and a friendly sits
    beside the landing -> invulnerability IS granted via the decline
    hook (set_invulnerable_after_jump_decline)."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3),
               (lambda: Pawn('white'), 4, 5)],   # friendly beside landing
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4)],   # eligible enemy (jumped)
    )
    knight = b.squares[3][3].piece
    # Make the jumped enemy eligible: it moved last turn
    # (first-class flag, 2026-07-20).
    b.last_move = Move(Square(2, 4), Square(3, 4))
    b.last_move_turn_number = 4
    b.turn_number = 5
    b.squares[3][4].piece.moved_last_turn = True
    targets = b.move(knight, Move(Square(3, 3), Square(3, 5)))
    # A jump-capture offer comes back; the player DECLINES:
    assert targets, 'expected a jump-capture offer'
    granted = b.set_invulnerable_after_jump_decline(
        knight, 3, 5, 3, 4)
    assert granted is True
    assert knight.invulnerable is True


def test_declined_jump_capture_without_friendly_grants_nothing():
    """Decline over an eligible enemy with NO friendly at the
    landing -> no invuln."""
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3)],
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4)],
    )
    knight = b.squares[3][3].piece
    b.last_move = Move(Square(2, 4), Square(3, 4))
    b.last_move_turn_number = 4
    b.turn_number = 5
    b.squares[3][4].piece.moved_last_turn = True   # first-class flag
    targets = b.move(knight, Move(Square(3, 3), Square(3, 5)))
    assert targets, 'expected a jump-capture offer'
    granted = b.set_invulnerable_after_jump_decline(
        knight, 3, 5, 3, 4)
    assert granted is False
    assert knight.invulnerable is False


# ===========================================================================
# Repetition-simulation consistency
# ===========================================================================

def test_would_cause_repetition_simulates_new_invuln_rule():
    """The would_cause_repetition simulation must mirror the NEW grant
    condition — a supported enemy-vault's simulated state hash must
    match the actually-recorded post-move hash (invulnerable flag
    included in both)."""
    import copy
    b = _board_with(
        white=[(lambda: King('white'), 7, 7),
               (lambda: Knight('white'), 3, 3),
               (lambda: Pawn('white'), 4, 5)],
        black=[(lambda: King('black'), 0, 0),
               (lambda: Pawn('black'), 3, 4)],
    )
    knight = b.squares[3][3].piece
    _stationary_last_move(b)
    move = Move(Square(3, 3), Square(3, 5))

    # Actual: apply via board.move + next_turn-equivalent clears.
    b_act = copy.deepcopy(b)
    act_knight = b_act.squares[3][3].piece
    b_act.move(act_knight, Move(Square(3, 3), Square(3, 5)))
    assert act_knight.invulnerable is True
    b_act.turn_number += 1
    b_act.clear_moved_by_queen_for_opponent('black')
    b_act.clear_invulnerable_for_color('black')
    actual_hash = b_act.get_state_hash('black')

    # Seed history so this exact resulting state has count 2 -> the
    # third occurrence must be blocked.
    b.state_history[actual_hash] = 2
    assert b.would_cause_repetition(knight, move, 'white') is True, (
        'simulation must produce the same hash as the actual move '
        '(including the NEW invuln grant) for the repetition rule '
        'to fire')
