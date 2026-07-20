"""Tests for the enriched FEN (user spec 2026-07-20): the FEN encodes
EVERYTHING in the current state hash — the only exclusions are the
repetition rule's state-history counts and the tiny-endgame distance
counts. The literal last move is recorded only when some rule
consults it at this position (Restriction 2, knight jump-capture
eligibility, bishop reactive arming) — move generation consumes the
actual coordinates, so they are strictly necessary exactly then.

Per-piece suffixes (canonical order ' * ! ^):
    '   transformed queen (class letter shows the form)
    *   promoted (non-royal) queen — the RARER kind gets the marker;
        plain Q/q is now always the royal queen (replaces the old
        b1/g8 starting-square heuristic)
    !   manipulation freeze (moved_by_queen)
    ^   invulnerable
Extra fields: bmem:<sq> (boulder no-return memory), last:<fromto>
(e.g. last:e2e4, only when legality-relevant).
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
from board import Board
from piece import King, Queen, Rook, Bishop, Knight, Pawn
from move import Move
from square import Square


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _bare_game(turn_number=10, next_player='white'):
    """Game whose board is emptied in place (kings only)."""
    g = Game()
    b = g.board
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[7][7].piece = King('white')
    b.squares[0][0].piece = King('black')
    b.turn_number = turn_number
    b.last_move = None
    b.last_move_turn_number = None
    g.next_player = next_player
    return g, b


def _reload(g):
    """to_fen -> load_from_fen on a fresh game; returns the new game."""
    fen = g.to_fen()
    g2 = Game()
    assert g2.load_from_fen(fen) is True, f'FEN failed to load: {fen}'
    return g2, fen


def _hashes_equal(g, g2):
    return (g.board.get_state_hash(g.next_player)
            == g2.board.get_state_hash(g2.next_player)
            and g.next_player == g2.next_player
            and g.board.turn_number == g2.board.turn_number)


# ---- the common case stays identical -------------------------------------

def test_initial_position_fen_unchanged():
    g = Game()
    assert g.to_fen() == ('bkrnnrqb/pppppppp/8/8/8/8/PPPPPPPP/BQRNNRKB '
                          'w turn:0 boulder:int:0')


# ---- queen markers -------------------------------------------------------

def test_promoted_queen_marker_and_royal_default():
    g, b = _bare_game()
    b.squares[4][4].piece = Queen('white', is_royal=True)     # royal
    pq = Queen('white', is_royal=False)                       # promoted
    b.squares[5][5].piece = pq
    fen = g.to_fen()
    assert 'Q*' in fen           # promoted queen carries the marker
    g2, fen = _reload(g)
    assert g2.board.squares[4][4].piece.is_royal is True
    assert g2.board.squares[5][5].piece.is_royal is False
    assert _hashes_equal(g, g2)


def test_plain_queen_is_royal_anywhere():
    """The old b1/g8 heuristic is gone: an unmarked Q is the royal
    queen wherever it stands."""
    g2 = Game()
    assert g2.load_from_fen('k7/8/8/4Q3/8/8/8/7K w turn:6') is True
    q = g2.board.squares[3][4].piece
    assert isinstance(q, Queen) and q.is_royal is True


def test_transformed_queen_markers():
    g, b = _bare_game()
    rq = Rook('white')                  # royal queen in rook form
    rq.is_transformed = True
    rq.is_royal = True
    b.squares[4][4].piece = rq
    pn = Knight('black')                # promoted queen in knight form
    pn.is_transformed = True
    pn.is_royal = False
    b.squares[3][3].piece = pn
    plain = Rook('black')               # a REAL rook for contrast
    b.squares[2][2].piece = plain
    fen = g.to_fen()
    assert "R'" in fen and "n'*" in fen
    g2, fen = _reload(g)
    r2 = g2.board.squares[4][4].piece
    assert isinstance(r2, Rook) and r2.is_transformed and r2.is_royal
    n2 = g2.board.squares[3][3].piece
    assert isinstance(n2, Knight) and n2.is_transformed and not n2.is_royal
    p2 = g2.board.squares[2][2].piece
    assert isinstance(p2, Rook) and not p2.is_transformed
    assert _hashes_equal(g, g2)


# ---- freeze + invulnerability -------------------------------------------

def test_freeze_and_invulnerable_markers():
    g, b = _bare_game()
    frozen = Pawn('black')
    frozen.moved_by_queen = True
    b.squares[3][3].piece = frozen
    shielded = Knight('white')
    shielded.invulnerable = True
    b.squares[5][5].piece = shielded
    fen = g.to_fen()
    assert 'p!' in fen and 'N^' in fen
    g2, fen = _reload(g)
    assert g2.board.squares[3][3].piece.moved_by_queen is True
    assert g2.board.squares[5][5].piece.invulnerable is True
    assert _hashes_equal(g, g2)


# ---- boulder memory ------------------------------------------------------

def test_boulder_memory_field():
    g, b = _bare_game()
    from piece import Boulder
    o = Boulder()
    o.on_intersection = False
    o.first_move = False
    o.cooldown = 1
    o.last_square = (4, 3)      # d4
    b.squares[3][3].piece = o
    # INVARIANT: board.boulder is None once the boulder is on a
    # square (Board.move clears it when leaving the intersection);
    # only the squares array holds it.
    b.boulder = None
    fen = g.to_fen()
    assert 'bmem:d4' in fen
    g2, fen = _reload(g)
    assert g2.board.boulder is None          # invariant preserved
    o2 = g2.board.squares[3][3].piece
    assert o2.last_square == (4, 3)
    assert o2.cooldown == 1
    assert _hashes_equal(g, g2)


# ---- legality-relevant last move ----------------------------------------

def test_last_move_encoded_when_queen_consults():
    """Enemy base-form queen has LOS to the piece that just moved ->
    Restriction 2 is armed -> the FEN must carry last:<fromto>."""
    g, b = _bare_game(turn_number=10, next_player='white')
    b.squares[4][4].piece = Pawn('black')          # moved last turn
    b.squares[4][1].piece = Queen('white', is_royal=True)  # LOS along rank
    b.last_move = Move(Square(3, 4), Square(4, 4))
    b.last_move_turn_number = 9
    fen = g.to_fen()
    assert 'last:e5e4' in fen
    g2, fen = _reload(g)
    assert g2.board.last_move is not None
    assert (g2.board.last_move.initial.row,
            g2.board.last_move.initial.col) == (3, 4)
    assert g2.board.last_move_turn_number == g2.board.turn_number - 1
    assert _hashes_equal(g, g2)


def test_last_move_encoded_when_bishop_armed():
    """Enemy bishop with diagonal LOS to the move's INITIAL square ->
    reactive capture armed -> last: field present, and the loaded
    game's legal turns include the reactive capture."""
    from ai_controller import AIController
    g, b = _bare_game(turn_number=10, next_player='white')
    b.squares[3][6].piece = Rook('black')          # moved last turn
    # White bishop with unblocked diagonal LOS to the move's INITIAL
    # square (3,3): (5,5)-(4,4)-(3,3) is clear — the moved piece went
    # OFF the diagonal, so the bishop stays armed in the current
    # position (arming is evaluated post-move, matching both the
    # state hash and bishop_moves generation).
    b.squares[5][5].piece = Bishop('white')
    b.last_move = Move(Square(3, 3), Square(3, 6))
    b.last_move_turn_number = 9
    fen = g.to_fen()
    assert 'last:d5g5' in fen
    g2, fen = _reload(g)
    assert _hashes_equal(g, g2)
    # The reactive capture is actually generated after the reload.
    ai = AIController('white')
    caps = [t for t in ai.legal_turns(g2)
            if t.turn_type == 'move' and t.to_sq == (3, 6)
            and type(t.piece).__name__ == 'Bishop']
    assert caps, 'reactive capture must survive the FEN round trip'


def test_last_move_omitted_when_nothing_consults():
    """A preceding move that no rule consults must NOT appear (the
    hash treats it as irrelevant; the FEN stays minimal)."""
    g, b = _bare_game(turn_number=10, next_player='white')
    b.squares[4][4].piece = Pawn('black')
    b.last_move = Move(Square(3, 4), Square(4, 4))
    b.last_move_turn_number = 9
    fen = g.to_fen()
    assert 'last:' not in fen
    g2, fen = _reload(g)
    assert _hashes_equal(g, g2)


def test_stale_last_move_omitted():
    """A last move from an EARLIER turn (not the immediately
    preceding one) never appears."""
    g, b = _bare_game(turn_number=10, next_player='white')
    b.squares[4][4].piece = Pawn('black')
    b.squares[4][1].piece = Queen('white', is_royal=True)
    b.last_move = Move(Square(3, 4), Square(4, 4))
    b.last_move_turn_number = 5          # stale
    fen = g.to_fen()
    assert 'last:' not in fen
    assert _hashes_equal(g, _reload(g)[0])


# ---- legality reproduction (the point of it all) -------------------------

def test_legal_turn_set_survives_reload_with_markers():
    """Full legal-turn-set equality across a FEN reload of a state
    with a frozen piece, an invulnerable piece, and an armed queen
    consult — the strongest form of 'the FEN captures the hash'."""
    from ai_controller import AIController
    g, b = _bare_game(turn_number=10, next_player='black')
    b.squares[4][4].piece = Pawn('black')
    b.squares[4][4].piece.moved_by_queen = True    # frozen
    shielded = Knight('white')
    shielded.invulnerable = True
    b.squares[3][3].piece = shielded
    b.squares[4][1].piece = Queen('white', is_royal=True)
    b.last_move = Move(Square(3, 4), Square(4, 4))
    b.last_move_turn_number = 9
    g2, fen = _reload(g)
    ai = AIController('white')

    def turn_set(game):
        return {(t.turn_type, t.from_sq, t.to_sq, t.transform_target,
                 t.promo_choice, t.jump_choice)
                for t in ai.legal_turns(game)}

    assert turn_set(g) == turn_set(g2)


# ---- old suffix-less FENs still parse ------------------------------------

def test_plain_old_fen_still_loads():
    g = Game()
    assert g.load_from_fen('bkrnnrqb/pppppppp/8/8/8/8/PPPPPPPP/BQRNNRKB '
                           'w turn:0 boulder:int:0') is True
    assert g.board.turn_number == 0
