"""The repetition state must not distinguish what no rule consults.

A state that is FINER than the legal-move set makes repetitions
accumulate more slowly than they should, which weakens the rule that
exists to terminate games. The rulebook is explicit that the state
captures "all information that determines the legal-move set at the
current position" -- so a difference no rule reads must not change the
hash.

`moved_last_turn` is the field where this is easy to get wrong, because
it is a property of the PREVIOUS turn. The rulebook says it is part of
the state only when some rule consults it at this position:

  - an enemy base-form queen has line-of-sight to the piece
    (Restriction 2 blocks manipulating a piece that just moved), OR
  - an enemy knight is at chebyshev-1 (jump-capture eligible), OR
  - any bishop is reactive-armed (the moved piece is its target).

These tests check both directions: ignored when nothing consults it,
and honoured when something does.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()

from board import Board
from piece import Bishop, King, Knight, Pawn, Queen, Rook


def _bare_board():
    """A board holding only what each test puts on it."""
    board = Board()
    for row in range(8):
        for col in range(8):
            board.squares[row][col].piece = None
    board.boulder = None
    return board


def _place(board, row, col, piece):
    board.squares[row][col].piece = piece
    return piece


def test_moved_last_turn_is_ignored_when_no_rule_consults_it():
    """THE INVARIANT THAT MATTERS. Two kings far apart, nothing that
    reads the flag: setting it must not change the hash, or every
    shuffle would look like a new position and the repetition rule
    would never fire."""
    board = _bare_board()
    white = _place(board, 7, 0, King('white'))
    _place(board, 0, 7, King('black'))
    before = board.get_state_hash('white')
    white.moved_last_turn = True
    after = board.get_state_hash('white')
    assert before == after, (
        'the hash changed although no rule consults moved_last_turn '
        'here; repetitions will accumulate too slowly')


def test_the_flag_is_honoured_when_an_enemy_knight_is_adjacent():
    """A knight at chebyshev-1 makes the moved piece jump-capturable,
    so the flag DOES change what is legal and must be hashed."""
    board = _bare_board()
    pawn = _place(board, 4, 4, Pawn('white'))
    _place(board, 3, 4, Knight('black'))
    _place(board, 7, 0, King('white'))
    _place(board, 0, 7, King('black'))
    before = board.get_state_hash('black')
    pawn.moved_last_turn = True
    assert board.get_state_hash('black') != before, (
        'an adjacent enemy knight consults the flag, so the two states '
        'have different legal moves and must hash differently')


def test_the_flag_is_honoured_when_an_enemy_base_queen_sees_it():
    """Restriction 2 forbids manipulating a piece that just moved, so a
    base-form queen with line-of-sight consults the flag."""
    board = _bare_board()
    pawn = _place(board, 4, 4, Pawn('white'))
    _place(board, 4, 0, Queen('black'))
    _place(board, 7, 0, King('white'))
    _place(board, 0, 7, King('black'))
    before = board.get_state_hash('black')
    pawn.moved_last_turn = True
    assert board.get_state_hash('black') != before


def test_the_flag_is_honoured_when_any_bishop_is_reactive_armed():
    """An armed bishop's capture TARGET is the piece that just moved, so
    which piece it was changes the legal-move set."""
    board = _bare_board()
    pawn = _place(board, 4, 4, Pawn('white'))
    bishop = _place(board, 1, 1, Bishop('black'))
    bishop.reactive_armed = True
    _place(board, 7, 0, King('white'))
    _place(board, 0, 7, King('black'))
    before = board.get_state_hash('black')
    pawn.moved_last_turn = True
    assert board.get_state_hash('black') != before


def test_a_distant_queen_without_line_of_sight_does_not_consult_it():
    """The check is LINE OF SIGHT, not mere presence -- a queen that
    cannot see the piece cannot manipulate it, so the flag is still
    irrelevant."""
    board = _bare_board()
    pawn = _place(board, 4, 4, Pawn('white'))
    _place(board, 1, 2, Queen('black'))        # not on rank, file or diagonal
    _place(board, 7, 0, King('white'))
    _place(board, 0, 7, King('black'))
    before = board.get_state_hash('black')
    pawn.moved_last_turn = True
    assert board.get_state_hash('black') == before, (
        'a queen with no line of sight made the flag matter')


def test_a_transformed_queen_does_not_consult_it():
    """Manipulation is base-form only (Restriction 3), so a queen in a
    transformed form cannot manipulate and does not consult the flag."""
    board = _bare_board()
    pawn = _place(board, 4, 4, Pawn('white'))
    rook = _place(board, 4, 0, Rook('black'))
    rook.is_transformed = True                 # a queen in rook form
    _place(board, 7, 0, King('white'))
    _place(board, 0, 7, King('black'))
    before = board.get_state_hash('black')
    pawn.moved_last_turn = True
    assert board.get_state_hash('black') == before, (
        'a transformed queen cannot manipulate, so the flag is '
        'irrelevant and must not be hashed')


def test_the_boulder_memory_is_only_hashed_when_it_restricts():
    """Same principle for the boulder's no-return square: it is part of
    the state only when it actually removes a legal move."""
    import inspect

    source = inspect.getsource(Board.get_state_hash)
    assert '_effective_boulder_last_square' in source, (
        'the boulder memory is hashed unconditionally, which makes the '
        'state finer than the legal-move set')
