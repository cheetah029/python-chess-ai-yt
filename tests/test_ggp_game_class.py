"""Tests for `src/ggp/game.py` — the GGP Game class that wraps
KB + resolver and exposes a clean state-machine API:

    g = GGPGame.from_file('step1_kings_queens.gdl')
    g.legal_moves('white')   -> list of move terms
    g.step({'white': move, 'black': 'noop'})   -> mutates state
    g.is_terminal()          -> bool
    g.goal('white')          -> int  (0-100 per GDL convention)
    g.roles                  -> ['white', 'black']

Plus a `RandomGGPPlayer` and a `play_game` helper for end-to-end
self-play validation.
"""

import os
import sys
import random
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame, RandomGGPPlayer, play_game


GDL_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl')
STEP1 = os.path.join(GDL_DIR, 'step1_kings_queens.gdl')


def _read(path):
    with open(path) as f:
        return f.read()


# ---- construction --------------------------------------------------------

def test_ggp_game_loads_from_file():
    g = GGPGame.from_file(STEP1)
    assert g is not None


def test_ggp_game_loads_from_text():
    text = _read(STEP1)
    g = GGPGame(text)
    assert g is not None


def test_ggp_game_exposes_roles():
    g = GGPGame.from_file(STEP1)
    assert sorted(g.roles) == ['black', 'white']


# ---- initial state -------------------------------------------------------

def test_ggp_game_initial_state_has_4_cells():
    g = GGPGame.from_file(STEP1)
    cells = [f for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell']
    assert len(cells) == 4


def test_ggp_game_initial_state_has_control_white():
    g = GGPGame.from_file(STEP1)
    assert ('control', 'white') in g.state


# ---- legal moves ---------------------------------------------------------

def test_ggp_game_legal_moves_white_at_init():
    g = GGPGame.from_file(STEP1)
    moves = g.legal_moves('white')
    assert len(moves) == 10, (
        f'expected 10 legal moves for white at init; got '
        f'{len(moves)}: {moves}')


def test_ggp_game_legal_moves_black_at_init_is_noop():
    g = GGPGame.from_file(STEP1)
    moves = g.legal_moves('black')
    assert moves == ['noop']


def test_ggp_game_legal_moves_for_unknown_role_is_empty():
    g = GGPGame.from_file(STEP1)
    assert g.legal_moves('green') == []


# ---- step (state progression) -------------------------------------------

def test_ggp_game_step_advances_state():
    g = GGPGame.from_file(STEP1)
    # White king g1 -> f1.
    move = ('move', 'king', 'g', '1', 'f', '1')
    g.step({'white': move, 'black': 'noop'})
    # After the move:
    #   - cell at g1 should be empty (no fact)
    #   - cell at f1 should hold white king
    #   - control should be black
    cells = {(f[1], f[2]): (f[3], f[4])
             for f in g.state
             if isinstance(f, tuple) and f[0] == 'cell'}
    assert cells.get(('f', '1')) == ('white', 'king'), (
        f'white king should be at f1 after move; got cells {cells}')
    assert ('g', '1') not in cells, (
        f'g1 should be empty after move; got cells {cells}')
    assert ('control', 'black') in g.state, (
        f'control should pass to black; state has {g.state}')


def test_ggp_game_step_does_not_create_does_facts():
    """After step, the (does ...) facts used for next-state derivation
    should NOT persist into the next state."""
    g = GGPGame.from_file(STEP1)
    move = ('move', 'king', 'g', '1', 'f', '1')
    g.step({'white': move, 'black': 'noop'})
    does_facts = [f for f in g.state
                  if isinstance(f, tuple) and f[0] == 'does']
    assert does_facts == []


def test_ggp_game_step_makes_other_side_legal_to_move():
    g = GGPGame.from_file(STEP1)
    move = ('move', 'king', 'g', '1', 'f', '1')
    g.step({'white': move, 'black': 'noop'})
    # Now it's black's turn.
    black_moves = g.legal_moves('black')
    # Black has its own king + queen now able to make 10 king-step
    # moves (or close — let's just verify > 1).
    assert len(black_moves) >= 5, (
        f'expected ≥5 black moves after white moved; got '
        f'{len(black_moves)}: {black_moves}')
    # And white now plays noop.
    white_moves = g.legal_moves('white')
    assert white_moves == ['noop']


# ---- terminal + goal ----------------------------------------------------

def test_ggp_game_not_terminal_at_init():
    g = GGPGame.from_file(STEP1)
    assert g.is_terminal() is False


def test_ggp_game_terminal_when_one_side_loses_all_royals():
    """Hand-construct a near-terminal state: only black has a piece."""
    g = GGPGame.from_file(STEP1)
    # Force white's king + queen off the board (state mutation).
    g.state = {
        ('cell', 'b', '8', 'black', 'king'),
        ('cell', 'g', '8', 'black', 'queen'),
        ('control', 'white'),
    }
    # No white royals → white has lost → game terminal.
    assert g.is_terminal() is True
    assert g.goal('black') == 100
    assert g.goal('white') == 0


def test_ggp_game_goal_zero_when_neither_side_has_won():
    g = GGPGame.from_file(STEP1)
    # Both alive — no goal yet (per GDL: goal only defined when
    # terminal; we return 0 by convention before then).
    assert g.goal('white') == 0
    assert g.goal('black') == 0


# ---- RandomGGPPlayer + play_game ----------------------------------------

def test_random_player_picks_a_legal_move():
    g = GGPGame.from_file(STEP1)
    p = RandomGGPPlayer('white', seed=42)
    move = p.choose(g)
    legal = g.legal_moves('white')
    assert move in legal


def test_random_player_deterministic_under_seed():
    g = GGPGame.from_file(STEP1)
    p1 = RandomGGPPlayer('white', seed=1234)
    p2 = RandomGGPPlayer('white', seed=1234)
    assert p1.choose(g) == p2.choose(g)


def test_play_game_runs_until_terminal_or_step_cap():
    """End-to-end: play step-1 with random players for both sides.
    Should either reach terminal (one side captured the other's
    royals) within the step cap, OR cleanly exit at the cap."""
    g = GGPGame.from_file(STEP1)
    players = {
        'white': RandomGGPPlayer('white', seed=1),
        'black': RandomGGPPlayer('black', seed=2),
    }
    result = play_game(g, players, max_steps=200)
    # result is {role: int_goal_or_zero}
    assert 'white' in result
    assert 'black' in result
    assert isinstance(result['white'], int)
    assert isinstance(result['black'], int)


def test_play_game_returns_zeros_if_not_terminal():
    """If the game doesn't terminate within max_steps, both goals
    should be 0 (no winner)."""
    g = GGPGame.from_file(STEP1)
    players = {
        'white': RandomGGPPlayer('white', seed=99),
        'black': RandomGGPPlayer('black', seed=100),
    }
    result = play_game(g, players, max_steps=2)   # tiny cap
    # 2 steps almost certainly won't terminate.
    assert result == {'white': 0, 'black': 0} or g.is_terminal()
