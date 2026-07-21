"""Regression tests for the first-class last-move flags redesign
(user decision 2026-07-20, closing two state-hash gaps):

  GAP 1 (confirmed): the old hash's reactive_armed evaluated bishop
  LoS to the move's initial square in the POST-move position, while
  generation honored BEGIN-time LoS (rulebook: the piece "begins its
  move on a square within the bishop's diagonal line-of-sight"). A
  mover landing on its own trail (knight 2-diagonal jump along the
  bishop's diagonal) was capturable live, yet the armed and unarmed
  states hashed equal — and a FEN reload lost the capture.

  GAP 2: the old hash set moved_last_turn only under queen-LoS /
  knight-adjacency consultation, never for an armed bishop — so the
  armed bishop's capture TARGET was not pinned (two states with the
  same armed set but different movers hashed equal with different
  legal captures).

Design: `piece.moved_last_turn` (exactly one piece) and
`piece.reactive_armed` (bishops, from PRE-move LoS) are set by
Board.move, expired by the next turn (including action turns via
record_action_turn), consumed by generation, the hash, and the FEN.
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

from game import Game
from ai_controller import AIController
from piece import King, Queen, Rook, Bishop, Knight, Pawn


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _bare_game(next_player, turn_number=10):
    g = Game()
    b = g.board
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[0][0].piece = King('black')
    b.squares[0][7].piece = King('white')
    b.turn_number = turn_number
    b.last_move = None
    b.last_move_turn_number = None
    b.clear_turn_flags()
    g.next_player = next_player
    return g, b


def _ai():
    return AIController('white')


# ---- GAP 1: begin-time arming (the confirmed bug) ------------------------

def test_self_blocking_trail_stays_armed_and_roundtrips():
    """Knight jumps along the bishop's diagonal, landing between the
    bishop and its own start square: begin-time LoS was clear, so the
    reactive capture is live — and must survive hashing and the FEN
    round trip (the old post-move LoS check lost it)."""
    g, b = _bare_game(next_player='black')
    wb = Bishop('white')
    b.squares[7][7].piece = wb
    b.squares[3][3].piece = Knight('black')

    ai = _ai()
    jump = [t for t in ai.legal_turns(g)
            if t.turn_type == 'move' and t.from_sq == (3, 3)
            and t.to_sq == (5, 5)]
    assert jump, 'setup: the 2-diagonal jump must be legal'
    ai._apply_turn(g, jump[0])

    # Flags: begin-time armed, mover marked.
    assert wb.reactive_armed is True
    assert b.squares[5][5].piece.moved_last_turn is True
    # Live reactive capture offered.
    live = [t for t in ai.legal_turns(g)
            if t.from_sq == (7, 7) and t.to_sq == (5, 5)]
    assert live, 'reactive capture must be offered live'

    # FEN round trip preserves the capture and the hash.
    fen = g.to_fen()
    assert 'B+' in fen and 'n~' in fen
    g2 = Game()
    assert g2.load_from_fen(fen) is True
    re = [t for t in ai.legal_turns(g2)
          if t.from_sq == (7, 7) and t.to_sq == (5, 5)]
    assert re, 'reactive capture must survive the FEN round trip'
    assert (g.board.get_state_hash('white')
            == g2.board.get_state_hash('white'))

    # The armed state hashes DIFFERENTLY from the flagless twin —
    # this inequality is exactly what the old design got wrong.
    g3 = Game()
    assert g3.load_from_fen(fen.replace('B+', 'B')
                            .replace('n~', 'n')) is True
    assert (g.board.get_state_hash('white')
            != g3.board.get_state_hash('white'))


# ---- GAP 2: the armed bishop's target is pinned --------------------------

def test_armed_bishop_target_is_pinned_by_hash():
    """Two states with the identical placement and the same armed
    bishop but DIFFERENT moved pieces must hash differently — the
    armed bishop's legal capture differs."""
    def build(moved_sq):
        g, b = _bare_game(next_player='white')
        armed = Bishop('white')
        armed.reactive_armed = True
        b.squares[5][5].piece = armed
        b.squares[1][0].piece = Rook('black')
        b.squares[1][2].piece = Knight('black')
        b.squares[moved_sq[0]][moved_sq[1]].piece.moved_last_turn = True
        return g

    ga = build((1, 0))       # the rook moved
    gb = build((1, 2))       # the knight moved
    assert (ga.board.get_state_hash('white')
            != gb.board.get_state_hash('white')), (
        'the armed capture target must be pinned by the hash')


# ---- lifecycle -----------------------------------------------------------

def test_transformation_expires_flags():
    """A real transformation (action turn) expires both flags — the
    previous move is no longer the immediately preceding turn."""
    g, b = _bare_game(next_player='black')
    wb = Bishop('white')
    b.squares[7][7].piece = wb
    b.squares[3][3].piece = Knight('black')
    bq = Queen('black', is_royal=True)
    b.squares[0][2].piece = bq
    b.captured_pieces['black'].append('rook')

    ai = _ai()
    jump = [t for t in ai.legal_turns(g)
            if t.turn_type == 'move' and t.from_sq == (3, 3)
            and t.to_sq == (5, 5)]
    ai._apply_turn(g, jump[0])
    assert wb.reactive_armed is True

    # White transforms nothing — it's white's turn; give white a
    # transformable queen instead and transform it.
    wq = Queen('white', is_royal=True)
    b.squares[7][0].piece = wq
    b.captured_pieces['white'].append('rook')
    trans = [t for t in ai.legal_turns(g)
             if t.turn_type == 'transformation' and t.from_sq == (7, 0)]
    assert trans, 'setup: white queen must be able to transform'
    ai._apply_turn(g, trans[0])

    assert wb.reactive_armed is False
    assert b.squares[5][5].piece.moved_last_turn is False


def test_boulder_move_expires_without_setting():
    """A boulder turn expires the previous flags and sets none (the
    neutral boulder arms no rule)."""
    g, b = _bare_game(next_player='black')
    b.squares[3][3].piece = Knight('black')
    from piece import Boulder
    o = Boulder()
    o.on_intersection = False
    o.first_move = False
    b.squares[6][6].piece = o

    ai = _ai()
    jump = [t for t in ai.legal_turns(g)
            if t.turn_type == 'move' and t.from_sq == (3, 3)]
    ai._apply_turn(g, jump[0])
    moved = [p for r in range(8) for c in range(8)
             for p in [b.squares[r][c].piece]
             if p is not None and p.moved_last_turn]
    assert len(moved) == 1

    boulder_turns = [t for t in ai.legal_turns(g)
                     if t.turn_type == 'boulder']
    assert boulder_turns, 'setup: white must have a boulder move'
    ai._apply_turn(g, boulder_turns[0])
    flagged = [p for r in range(8) for c in range(8)
               for p in [b.squares[r][c].piece]
               if p is not None and (p.moved_last_turn or p.reactive_armed)]
    assert flagged == []


def test_promotion_transfers_moved_flag():
    """The promoted piece replaces the pawn that just moved — it
    inherits moved_last_turn so armed bishops / knight windows still
    target it."""
    g, b = _bare_game(next_player='white')
    wp = Pawn('white')
    wp.moved = True
    b.squares[1][3].piece = wp

    ai = _ai()
    promo = [t for t in ai.legal_turns(g)
             if t.promo_choice == 'queen' and t.from_sq == (1, 3)]
    assert promo, 'setup: promotion must be available'
    ai._apply_turn(g, promo[0])
    promoted = b.squares[0][3].piece
    assert isinstance(promoted, Queen)
    assert promoted.moved_last_turn is True


def test_double_manipulation_arms_bishop():
    """A manipulates B's piece off A's bishop's LoS: arming happens at
    the manipulation move itself (begin-time), replacing the old
    stale-cache workaround."""
    g, b = _bare_game(next_player='white')
    wb = Bishop('white')
    b.squares[7][7].piece = wb
    # Black rook on the white bishop's diagonal; white queen with LoS
    # to it for the manipulation.
    br = Rook('black')
    b.squares[4][4].piece = br
    wq = Queen('white', is_royal=True)
    b.squares[4][6].piece = wq          # rank LoS to the rook

    ai = _ai()
    manip = [t for t in ai.legal_turns(g)
             if t.turn_type == 'manipulation' and t.from_sq == (4, 4)]
    assert manip, 'setup: manipulation of the rook must be available'
    off_diag = [t for t in manip if t.to_sq[0] != t.to_sq[1]]
    target = off_diag[0] if off_diag else manip[0]
    ai._apply_turn(g, target)
    assert wb.reactive_armed is True
    moved_sq = target.to_sq
    assert b.squares[moved_sq[0]][moved_sq[1]].piece.moved_last_turn is True

def test_double_manipulation_reactive_capture_offered():
    """Rulebook (Bishop, "Manipulation and reactive capture"): a
    DOUBLE manipulation produces a valid reactive capture — on turn
    N, player A manipulates B's piece P off A's bishop's LoS; on turn
    N+1, B manipulates A's (armed) bishop to reactive-capture P at
    its new square. The capture choice belongs to the manipulator
    (B), removing B's own piece — a player's-turn self-capture, never
    a same-color capture (the capturing bishop is A's).

    Closed as a side effect of the first-class flags redesign
    (PR #151): arming is recorded at the manipulation move itself,
    and bishop generation consults the flag regardless of who drives
    the bishop. This test pins it (the docs previously called it a
    known engine gap)."""
    g, b = _bare_game(next_player='white')
    wb = Bishop('white')
    b.squares[7][7].piece = wb                          # h1
    br = Rook('black')
    b.squares[4][4].piece = br                          # e4, on h1's diagonal
    wq = Queen('white', is_royal=True)
    b.squares[4][6].piece = wq                          # g4: rank LoS to e4
    bq = Queen('black', is_royal=True)
    b.squares[7][5].piece = bq                          # f1: rank LoS to h1

    ai = _ai()
    # Turn N: white manipulates the black rook e4 -> e5 (off the diagonal).
    manip = [t for t in ai.legal_turns(g) if t.turn_type == 'manipulation'
             and t.from_sq == (4, 4) and t.to_sq == (3, 4)]
    assert manip, 'setup: white must be able to manipulate the rook'
    ai._apply_turn(g, manip[0])
    assert wb.reactive_armed is True
    assert br.moved_last_turn is True and br.moved_by_queen is True

    # Turn N+1: black manipulates white's ARMED bishop onto the rook.
    double = [t for t in ai.legal_turns(g) if t.turn_type == 'manipulation'
              and t.from_sq == (7, 7) and t.to_sq == (3, 4)]
    assert double, ('the double-manipulation reactive capture must be '
                    'offered to the manipulator')
    ai._apply_turn(g, double[0])
    landed = b.squares[3][4].piece
    assert isinstance(landed, Bishop) and landed.color == 'white'
    assert not any(b.squares[r][c].piece is br
                   for r in range(8) for c in range(8)), 'rook captured'
