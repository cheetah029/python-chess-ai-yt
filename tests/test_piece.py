import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from piece import Piece, Pawn, Knight, Bishop, Rook, Queen, King, Boulder


# --- Base Piece class ---

def test_piece_default_attributes():
    p = Piece('test', 'white', 1.0)
    assert p.name == 'test'
    assert p.color == 'white'
    assert p.value == 1.0
    assert p.is_royal is False
    assert p.is_transformed is False
    assert p.moved is False
    assert p.invulnerable is False
    assert p.moved_by_queen is False
    assert p.forbidden_square is None
    assert p.moves == []
    assert p.line_of_sight == []

def test_piece_black_value_sign():
    p = Piece('test', 'black', 5.0)
    assert p.value == -5.0


# --- Pawn ---

def test_pawn_attributes():
    pw = Pawn('white')
    assert pw.name == 'pawn'
    assert pw.color == 'white'
    assert pw.dir == -1
    assert pw.en_passant is False
    assert pw.is_royal is False
    assert pw.is_transformed is False

def test_pawn_black_direction():
    pb = Pawn('black')
    assert pb.dir == 1


# --- Knight ---

def test_knight_attributes():
    k = Knight('white')
    assert k.name == 'knight'
    assert k.value == 3.0
    assert k.is_royal is False
    assert k.is_transformed is False


# --- Bishop ---

def test_bishop_attributes():
    b = Bishop('black')
    assert b.name == 'bishop'
    assert b.assassin_squares == []
    assert b.is_royal is False
    assert b.is_transformed is False


# --- Rook ---

def test_rook_attributes():
    r = Rook('white')
    assert r.name == 'rook'
    assert r.value == 5.0
    assert r.is_royal is False
    assert r.is_transformed is False


# --- Queen ---

def test_queen_default_is_royal():
    q = Queen('white')
    assert q.name == 'queen'
    assert q.is_royal is True
    assert q.is_transformed is False

def test_queen_explicit_royal():
    q = Queen('black', is_royal=True)
    assert q.is_royal is True

def test_queen_non_royal_promoted():
    q = Queen('white', is_royal=False)
    assert q.is_royal is False
    assert q.is_transformed is False


# --- King ---

def test_king_is_royal():
    k = King('white')
    assert k.name == 'king'
    assert k.is_royal is True
    assert k.left_rook is None
    assert k.right_rook is None
    assert k.is_transformed is False


# --- Boulder ---

def test_boulder_attributes():
    b = Boulder()
    assert b.name == 'boulder'
    assert b.color == 'none'
    assert b.value == 0
    assert b.is_royal is False
    assert b.is_transformed is False
    assert b.cooldown == 0
    assert b.last_square is None
    assert b.first_move is True

def test_boulder_texture_path():
    b = Boulder()
    assert 'boulder.png' in b.texture
    assert b.color not in b.texture  # no color prefix


# --- is_transformed attribute ---

def test_is_transformed_can_be_set():
    r = Rook('white')
    assert r.is_transformed is False
    r.is_transformed = True
    assert r.is_transformed is True


# --- Piece methods ---

def test_add_and_clear_moves():
    p = Pawn('white')
    p.add_move('fake_move')
    assert len(p.moves) == 1
    p.clear_moves()
    assert p.moves == []
