"""GDL parity tests for the first-class last-move flags redesign
(issue #154, mirroring engine PR #151):

  1. BEGIN-time reactive arming: `reactive_armed` is now a fluent
     RECORDED by `next` rules at move time (`next` bodies evaluate
     against the pre-move position), so a mover landing between the
     bishop and its own origin square — the "self-blocking trail" —
     no longer disarms the bishop. The old derived-predicate design
     evaluated LoS post-move and wrongly lost exactly those captures.
  2. jump_capture and reactive_capture now record
     spatial_move_last_turn (they are spatial moves — the moved
     knight/bishop must be Restriction-2 blocked, jump-capturable,
     and reactive-armable afterward).
  3. Boulder moves record nothing (the neutral boulder arms no rule).
  4. cross_validation.board_to_gdl_facts emits the engine's
     first-class flags as fluents, and engine bishop captures map to
     the GDL's reactive_capture action — so injected mid-game states
     carry the last-move context and the trail case cross-validates.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()

import pytest

from ggp.game import GGPGame
from ggp.cross_validation import board_to_gdl_facts, compare_legal_moves

INTEGRATED = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl',
                          'integrated.gdl')


@pytest.fixture(scope='module')
def ggp_template():
    return GGPGame.from_file(INTEGRATED)


def _fresh(ggp_template, facts):
    """Clone the loaded game with an injected state."""
    ggp_template.state = set(facts)
    return ggp_template


def _base_cells():
    """Kings only (h8 white, a8 black is row0col0... use distinct
    corners): white king h1-area is irrelevant — keep them far away."""
    return [
        ('cell', 'a', '8', 'black', 'king'),
        ('cell', 'h', '8', 'white', 'king'),
    ]


# ---- 1. begin-time arming: the self-blocking trail ----------------------

def test_trail_jump_keeps_bishop_armed_and_capture_legal(ggp_template):
    """Black knight on d5 (the white h1-bishop's diagonal) makes the
    2-diagonal jump d5->f3, landing BETWEEN the bishop and its own
    origin. Begin-time semantics: the bishop was armed when the move
    began, so its reactive capture at f3 must be legal — the old
    post-move LoS derivation wrongly said no."""
    facts = _base_cells() + [
        ('cell', 'h', '1', 'white', 'bishop'),
        ('cell', 'd', '5', 'black', 'knight'),
        ('control', 'black'),
        ('turn_number', '6'),
    ]
    g = _fresh(ggp_template, facts)
    moves = g.legal_moves('black')
    jump = ('move', 'knight', 'd', '5', 'f', '3')
    assert jump in moves, f'setup: the 2-diagonal jump must be legal; got {moves[:8]}'
    g.step({'black': jump, 'white': 'noop'})

    # The armed pair was recorded at move time (begin-time LoS).
    assert ('reactive_armed', 'h', '1', 'f', '3') in g.state, (
        'bishop must be armed against the trail-jumping knight '
        f'(state last-move facts: '
        f'{[f for f in g.state if "armed" in str(f) or "spatial" in str(f)]})')
    # And the capture is legal on white's immediate next turn.
    capture = ('reactive_capture', 'h', '1', 'f', '3')
    assert capture in g.legal_moves('white'), (
        'the reactive capture must be legal despite the mover '
        'blocking the post-move line (begin-time semantics)')


def test_reactive_capture_records_last_move(ggp_template):
    """Executing the reactive capture is itself a spatial bishop
    move: its destination must be recorded so the bishop is
    Restriction-2 blocked / jump-capturable / armable afterward."""
    facts = _base_cells() + [
        ('cell', 'h', '1', 'white', 'bishop'),
        ('cell', 'f', '3', 'black', 'knight'),
        ('reactive_armed', 'h', '1', 'f', '3'),
        ('spatial_move_last_turn', 'f', '3'),
        ('control', 'white'),
        ('turn_number', '7'),
    ]
    g = _fresh(ggp_template, facts)
    capture = ('reactive_capture', 'h', '1', 'f', '3')
    assert capture in g.legal_moves('white')
    g.step({'white': capture, 'black': 'noop'})
    assert ('cell', 'f', '3', 'white', 'bishop') in g.state
    assert ('spatial_move_last_turn', 'f', '3') in g.state, (
        'reactive_capture must record its destination as the last '
        'spatial move (previously missing)')


# ---- 2. jump_capture records last-move ----------------------------------

def test_jump_capture_records_last_move(ggp_template):
    """An accepted jump-capture is a spatial knight move: its landing
    must be recorded (previously missing)."""
    facts = _base_cells() + [
        ('cell', 'd', '5', 'black', 'knight'),
        ('cell', 'd', '4', 'white', 'pawn'),
        # The pawn moved last turn -> jump-capture eligible.
        ('spatial_move_last_turn', 'd', '4'),
        ('control', 'black'),
        ('turn_number', '6'),
    ]
    g = _fresh(ggp_template, facts)
    jumps = [m for m in g.legal_moves('black')
             if isinstance(m, tuple) and m[0] == 'jump_capture'
             and m[5] == 'd' and m[6] == '4']
    assert jumps, 'setup: a jump_capture over the just-moved pawn must be legal'
    jump = jumps[0]
    g.step({'black': jump, 'white': 'noop'})
    landing = (jump[3], jump[4])
    assert ('cell', 'd', '4', 'white', 'pawn') not in g.state  # captured
    assert ('spatial_move_last_turn', landing[0], landing[1]) in g.state, (
        'jump_capture must record its landing as the last spatial '
        'move (previously missing)')


# ---- 3. boulder records nothing -----------------------------------------

def test_boulder_move_records_nothing(ggp_template):
    """The neutral boulder arms no rule: no spatial_move_last_turn,
    no reactive_armed — even with a bishop watching its origin."""
    facts = _base_cells() + [
        ('cell', 'd', '4', 'none', 'boulder'),
        ('boulder_cooldown', '0'),
        ('cell', 'h', '8', 'white', 'king'),
        ('cell', 'a', '1', 'white', 'bishop'),   # diagonal LoS to d4
        ('control', 'black'),
        ('turn_number', '6'),
    ]
    g = _fresh(ggp_template, facts)
    moves = [m for m in g.legal_moves('black')
             if isinstance(m, tuple) and m[0] == 'move' and m[1] == 'boulder']
    assert moves, 'setup: the boulder must have a legal move'
    g.step({'black': moves[0], 'white': 'noop'})
    assert not any(isinstance(f, tuple) and f[0] == 'spatial_move_last_turn'
                   for f in g.state), 'boulder move must record no last move'
    assert not any(isinstance(f, tuple) and f[0] == 'reactive_armed'
                   for f in g.state), 'boulder move must arm no bishop'


# ---- 4. engine <-> GDL cross-validation of the trail case ---------------

def test_trail_case_cross_validates_against_engine(ggp_template):
    """Drive the trail jump in the ENGINE (first-class flags), inject
    the resulting board via board_to_gdl_facts (which now emits the
    flags as fluents), and require both sides to agree the reactive
    capture is legal."""
    from game import Game
    from ai_controller import AIController
    from piece import King, Bishop, Knight

    game = Game()
    b = game.board
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    b.squares[0][0].piece = King('black')
    b.squares[0][7].piece = King('white')
    wb = Bishop('white')
    b.squares[7][7].piece = wb                  # h1
    b.squares[3][3].piece = Knight('black')     # d5
    b.turn_number = 10
    b.clear_turn_flags()
    game.next_player = 'black'

    ai = AIController('white')
    jump = [t for t in ai.legal_turns(game)
            if t.turn_type == 'move' and t.from_sq == (3, 3)
            and t.to_sq == (5, 5)]
    assert jump, 'setup: engine must offer the 2-diagonal jump'
    ai._apply_turn(game, jump[0])
    assert wb.reactive_armed is True            # engine begin-time flag

    ggp = ggp_template
    ggp.state = set(board_to_gdl_facts(b, game.next_player))
    assert ('reactive_armed', 'h', '1', 'f', '3') in ggp.state, (
        'board_to_gdl_facts must emit the recorded arming')

    diff = compare_legal_moves(game, ggp, 'white')
    capture = ('reactive_capture', 'h', '1', 'f', '3')
    assert capture in diff['common'], (
        f'the trail-case reactive capture must be legal on BOTH '
        f"sides; engine_only={diff['engine_only'][:4]}, "
        f"ggp_only={diff['ggp_only'][:4]}")
