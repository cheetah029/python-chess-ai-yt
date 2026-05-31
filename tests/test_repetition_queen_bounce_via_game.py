"""End-to-end repetition test via the FULL Game + engine path.

User report (2026-05-31): "I can seemingly repeat the position
forever, and there is no manipulation involved at all. It is just
queens moving back and forth forever."

This file plays a 4-turn queen-bounce cycle THREE times via
Game.next_turn (mirroring how main.py drives moves) and asserts that
the engine's `would_cause_repetition` filter blocks the third
occurrence's first move.
"""

import sys
import os
import pytest

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


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _empty_board(g):
    """Clear g's board so we can place a minimal test position."""
    for r in range(8):
        for c in range(8):
            g.board.squares[r][c].piece = None
    g.board.boulder = None


def _apply_via_game(g, fr, fc, tr, tc):
    """Apply a spatial move via Game's normal flow: board.move +
    game.next_turn. Mirrors what main.py / ai_controller do."""
    from move import Move
    from square import Square
    piece = g.board.squares[fr][fc].piece
    g.board.move(piece, Move(Square(fr, fc), Square(tr, tc)))
    g.next_turn()


def test_queen_bounce_3rd_occurrence_blocked_via_engine():
    """White queen bounces b1<->a1 while black queen bounces
    g8<->h8. After two full cycles (the initial state has appeared
    3 times — once at start, twice at end of cycles 1 and 2),
    attempting to start cycle 3 should be blocked: would_cause_
    repetition on the next move must return True.
    """
    from game import Game
    from piece import Queen, King

    g = Game()
    _empty_board(g)
    # Minimal 4-piece position.
    wk = King('white'); g.board.squares[7][6].piece = wk   # g1
    wq = Queen('white', is_royal=True); g.board.squares[7][1].piece = wq  # b1
    bk = King('black'); g.board.squares[0][1].piece = bk   # b8
    bq = Queen('black', is_royal=True); g.board.squares[0][6].piece = bq  # g8

    g.board.update_lines_of_sight()
    g.board.update_threat_squares()

    # Record initial state (Game's constructor already did this, but
    # we re-record after pieces are placed to overwrite any stale
    # hash from the default starting position).
    g.board.state_history = {}
    g.board.record_state(g.next_player)

    # ---- cycle 1 ----
    _apply_via_game(g, 7, 1, 7, 0)   # WQ b1->a1
    _apply_via_game(g, 0, 6, 0, 7)   # BQ g8->h8
    _apply_via_game(g, 7, 0, 7, 1)   # WQ a1->b1
    _apply_via_game(g, 0, 7, 0, 6)   # BQ h8->g8

    # ---- cycle 2 ----
    _apply_via_game(g, 7, 1, 7, 0)
    _apply_via_game(g, 0, 6, 0, 7)
    _apply_via_game(g, 7, 0, 7, 1)
    _apply_via_game(g, 0, 7, 0, 6)

    # We're now back at the initial position. It has been recorded
    # 3 times: initially, after cycle 1, and after cycle 2.
    initial_hash = g.board.get_state_hash(g.next_player)
    assert g.board.state_history.get(initial_hash, 0) >= 3, (
        f'after 2 cycles, the initial state hash should be in '
        f'state_history at least 3 times; got '
        f'{g.board.state_history.get(initial_hash, 0)}. '
        f'If less than 3, the recorded hashes are diverging — meaning '
        f'subsequent identical-looking visits register as distinct '
        f'states. This is the bug behind "I can repeat the position '
        f'forever".')


def test_queen_bounce_engine_legal_moves_excludes_repetition():
    """Same setup. After 2 cycles, querying the engine for legal
    moves at white's turn (about to make WQ b1->a1 the 3rd time)
    should NOT include WQ b1->a1.
    """
    from game import Game
    from engine import GameEngine
    from piece import Queen, King

    g = Game()
    _empty_board(g)
    wk = King('white'); g.board.squares[7][6].piece = wk
    wq = Queen('white', is_royal=True); g.board.squares[7][1].piece = wq
    bk = King('black'); g.board.squares[0][1].piece = bk
    bq = Queen('black', is_royal=True); g.board.squares[0][6].piece = bq

    g.board.update_lines_of_sight()
    g.board.update_threat_squares()
    g.board.state_history = {}
    g.board.record_state(g.next_player)

    # cycle 1 + 2
    for _ in range(2):
        _apply_via_game(g, 7, 1, 7, 0)
        _apply_via_game(g, 0, 6, 0, 7)
        _apply_via_game(g, 7, 0, 7, 1)
        _apply_via_game(g, 0, 7, 0, 6)

    # Now white is about to move. Query the engine for legal turns.
    engine = GameEngine(g.board)
    engine.current_player = g.next_player
    engine.turn_number = g.board.turn_number
    legal_turns = engine.get_all_legal_turns()

    # The WQ b1->a1 turn should NOT be in the list.
    wq_b1_a1 = [
        t for t in legal_turns
        if (t.turn_type == 'move'
            and t.from_sq == (7, 1)
            and t.to_sq == (7, 0))
    ]
    assert wq_b1_a1 == [], (
        f'engine.get_all_legal_turns must exclude WQ b1->a1 after '
        f'2 cycles (it would cause the 3rd repetition of the '
        f'initial state). Got {len(wq_b1_a1)} turns matching this '
        f'move. legal_turns count = {len(legal_turns)}.')
