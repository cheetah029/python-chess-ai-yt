"""Tests for the GDL gap-closure package (issue #158).

Covers, per rulebook (RULEBOOK_v2.md read in full for this work):
  1. Queen identity TRANSFER: queen_form + queen_royal follow the
     queen when it moves (previously keyed to the square — a moved
     queen lost its form fact, becoming inert, and the royal queen
     lost royalty on its first move).
  2. Bishop manipulation: teleport destinations + the
     double-manipulation reactive capture (rulebook Bishop section)
     — previously absent entirely.
  3. Rook manipulation: full 2-segment destinations (the old rule
     had unbound head variables and produced nothing sound).
  4. Promotion form choice: promote / manipulate_promote actions,
     base queen always available, transformed forms gated on
     captured_friendly; plain pawn moves onto the last rank are no
     longer legal; the promoted queen carries queen_form (was
     previously inert) and is NOT royal.
  5. Invulnerability guards on non-king captures (audit item: only
     the king was patched).
  6. Queen-as-bishop reactive arming + capture (rulebook: reactive
     applies to "bishops and queens-as-bishop"; the #155 arming
     rules only matched cell=bishop).
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

INTEGRATED = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl',
                          'integrated.gdl')


@pytest.fixture(scope='module')
def ggp():
    return GGPGame.from_file(INTEGRATED)


def _set(ggp, facts):
    ggp.state = set(facts)
    return ggp


KINGS = [('cell', 'a', '8', 'black', 'king'),
         ('cell', 'h', '8', 'white', 'king')]


# ---- 1. queen identity transfer ------------------------------------------

def test_queen_form_and_royal_transfer_on_move(ggp):
    g = _set(ggp, KINGS + [
        ('cell', 'd', '4', 'white', 'queen'),
        ('queen_form', 'd', '4', 'base'),
        ('queen_royal', 'd', '4'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    mv = ('move', 'queen', 'd', '4', 'd', '5')
    assert mv in g.legal_moves('white')
    g.step({'white': mv, 'black': 'noop'})
    assert ('queen_form', 'd', '5', 'base') in g.state, \
        'queen_form must follow the moved queen'
    assert ('queen_royal', 'd', '5') in g.state, \
        'royalty must follow the moved royal queen'
    assert ('queen_form', 'd', '4', 'base') not in g.state
    assert ('queen_royal', 'd', '4') not in g.state
    # And the moved queen can move AGAIN (it was inert before the
    # fix — no queen_form fact means no movement rule can fire).
    followup = set(g.state) - {('control', 'black')} | {('control', 'white')}
    g2 = _set(ggp, followup)
    assert ('move', 'queen', 'd', '5', 'd', '6') in g2.legal_moves('white')


def test_captured_queen_form_does_not_leak_to_capturer(ggp):
    """A rook capturing a transformed queen must not inherit its
    queen_form fact."""
    g = _set(ggp, KINGS + [
        ('cell', 'd', '4', 'white', 'rook'),
        ('cell', 'd', '5', 'black', 'queen'),
        ('queen_form', 'd', '5', 'knight'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    mv = ('move', 'rook', 'd', '4', 'd', '5')
    assert mv in g.legal_moves('white')
    g.step({'white': mv, 'black': 'noop'})
    assert ('cell', 'd', '5', 'white', 'rook') in g.state
    assert not any(f[0] == 'queen_form' for f in g.state
                   if isinstance(f, tuple)), \
        'the captured queen\'s form fact must die with it'


# ---- 2. bishop manipulation ----------------------------------------------

def test_bishop_manipulation_teleport_offered(ggp):
    g = _set(ggp, KINGS + [
        ('cell', 'g', '4', 'white', 'queen'),
        ('queen_form', 'g', '4', 'base'),
        ('queen_royal', 'g', '4'),
        ('cell', 'e', '4', 'black', 'bishop'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    manips = [m for m in g.legal_moves('white')
              if isinstance(m, tuple) and m[0] == 'manipulate'
              and (m[3], m[4]) == ('e', '4')]
    assert manips, 'manipulating the enemy bishop (teleport) must be offered'


def test_double_manipulation_reactive_capture_in_gdl(ggp):
    """Turn N: white manipulated black's rook off the white bishop's
    diagonal (state below is turn N+1: bishop armed, rook flagged +
    frozen). Black manipulates the ARMED white bishop to capture
    black's own rook — the rulebook's double-manipulation case."""
    g = _set(ggp, KINGS + [
        ('cell', 'h', '1', 'white', 'bishop'),
        ('cell', 'e', '5', 'black', 'rook'),
        ('spatial_move_last_turn', 'e', '5'),
        ('manipulation_freeze', 'e', '5'),
        ('reactive_armed', 'h', '1', 'e', '5'),
        ('cell', 'f', '1', 'black', 'queen'),
        ('queen_form', 'f', '1', 'base'),
        ('queen_royal', 'f', '1'),
        ('control', 'black'), ('turn_number', '7'),
    ])
    double = [m for m in g.legal_moves('black')
              if isinstance(m, tuple) and m[0] == 'manipulate'
              and (m[3], m[4]) == ('h', '1') and (m[5], m[6]) == ('e', '5')]
    assert double, ('the double-manipulation reactive capture must be '
                    'offered to the manipulator')
    g.step({'black': double[0], 'white': 'noop'})
    assert ('cell', 'e', '5', 'white', 'bishop') in g.state
    assert not any(isinstance(f, tuple) and f[:3] == ('cell', 'e', '5')
                   and f[3] == 'black' for f in g.state), 'rook captured'


# ---- 3. rook manipulation ------------------------------------------------

def test_rook_manipulation_full_two_segment(ggp):
    g = _set(ggp, KINGS + [
        ('cell', 'g', '4', 'white', 'queen'),
        ('queen_form', 'g', '4', 'base'),
        ('queen_royal', 'g', '4'),
        ('cell', 'e', '4', 'black', 'rook'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    manips = [m for m in g.legal_moves('white')
              if isinstance(m, tuple) and m[0] == 'manipulate'
              and (m[3], m[4]) == ('e', '4')]
    dests = {(m[5], m[6]) for m in manips}
    assert ('e', '5') in dests, 'step-1 destination must be offered'
    assert ('f', '5') in dests or ('d', '5') in dests, \
        f'2-segment sweep destinations must be offered; got {sorted(dests)[:10]}'


# ---- 4. promotion form choice --------------------------------------------

def test_promote_action_with_form_choice(ggp):
    g = _set(ggp, KINGS + [
        ('cell', 'b', '7', 'white', 'pawn'),
        ('captured_friendly', 'white', 'knight'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    moves = g.legal_moves('white')
    # Plain pawn move onto the last rank is no longer legal.
    assert ('move', 'pawn', 'b', '7', 'b', '8') not in moves
    promos = [m for m in moves
              if isinstance(m, tuple) and m[0] == 'promote'
              and (m[1], m[2]) == ('b', '7')]
    forms = {m[5] for m in promos}
    assert 'queen' in forms, 'base form always available'
    assert 'knight' in forms, 'captured-friendly-unlocked form available'
    assert 'rook' not in forms and 'bishop' not in forms, \
        'locked forms must not be offered'
    # Execute: promoted queen carries its form and is NOT royal.
    choice = [m for m in promos if m[5] == 'knight'][0]
    g.step({'white': choice, 'black': 'noop'})
    assert ('cell', 'b', '8', 'white', 'queen') in g.state
    assert ('queen_form', 'b', '8', 'knight') in g.state
    assert ('queen_royal', 'b', '8') not in g.state
    assert ('spatial_move_last_turn', 'b', '8') in g.state


def test_manipulate_promote_action(ggp):
    """White queen manipulates a BLACK pawn onto black's last rank
    (rank 1): the manipulated promotion must exist, use the PAWN
    OWNER's unlocked forms, and freeze the new piece."""
    g = _set(ggp, KINGS + [
        ('cell', 'd', '2', 'black', 'pawn'),
        ('cell', 'f', '2', 'white', 'queen'),
        ('queen_form', 'f', '2', 'base'),
        ('queen_royal', 'f', '2'),
        ('captured_friendly', 'black', 'rook'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    moves = g.legal_moves('white')
    promos = [m for m in moves
              if isinstance(m, tuple) and m[0] == 'manipulate_promote'
              and (m[3], m[4]) == ('d', '2')]
    forms = {m[7] for m in promos}
    assert 'queen' in forms and 'rook' in forms, \
        f'manipulated promotion forms must be offered; got {sorted(forms)}'
    assert 'knight' not in forms
    choice = [m for m in promos if m[5] == 'd' and m[6] == '1'
              and m[7] == 'rook'][0]
    g.step({'white': choice, 'black': 'noop'})
    assert ('cell', 'd', '1', 'black', 'queen') in g.state
    assert ('queen_form', 'd', '1', 'rook') in g.state
    assert ('manipulation_freeze', 'd', '1') in g.state


# ---- 5. invulnerability guards -------------------------------------------

def test_invulnerable_piece_uncapturable_by_rook_and_pawn(ggp):
    g = _set(ggp, KINGS + [
        ('cell', 'd', '4', 'white', 'rook'),
        ('cell', 'd', '5', 'black', 'knight'),
        ('invulnerable', 'd', '5'),
        ('cell', 'c', '4', 'white', 'pawn'),
        ('control', 'white'), ('turn_number', '6'),
    ])
    moves = g.legal_moves('white')
    assert ('move', 'rook', 'd', '4', 'd', '5') not in moves, \
        'rook must not capture an invulnerable piece'
    assert ('move', 'pawn', 'c', '4', 'd', '5') not in moves, \
        'pawn must not diagonal-capture an invulnerable piece'


# ---- 6. queen-as-bishop reactive -----------------------------------------

def test_queen_as_bishop_gets_armed_and_captures(ggp):
    """Rulebook: reactive capture applies to bishops AND
    queens-as-bishop. The white queen-as-bishop on h1 must be armed
    by the knight's trail jump and capture it — arriving as a QUEEN
    (form + royalty intact)."""
    g = _set(ggp, KINGS + [
        ('cell', 'h', '1', 'white', 'queen'),
        ('queen_form', 'h', '1', 'bishop'),
        ('queen_royal', 'h', '1'),
        ('cell', 'd', '5', 'black', 'knight'),
        ('control', 'black'), ('turn_number', '6'),
    ])
    jump = ('move', 'knight', 'd', '5', 'f', '3')
    assert jump in g.legal_moves('black')
    g.step({'black': jump, 'white': 'noop'})
    assert ('reactive_armed', 'h', '1', 'f', '3') in g.state, \
        'queen-as-bishop must be armed (begin-time)'
    capture = ('reactive_capture', 'h', '1', 'f', '3')
    assert capture in g.legal_moves('white')
    g.step({'white': capture, 'black': 'noop'})
    assert ('cell', 'f', '3', 'white', 'queen') in g.state, \
        'the capturer arrives as a QUEEN, not a bishop'
    assert ('queen_form', 'f', '3', 'bishop') in g.state
    assert ('queen_royal', 'f', '3') in g.state


# ---- 7. straight line-of-sight -------------------------------------------

def test_line_of_sight_cannot_bend(ggp):
    """The old queen_los recursion did not thread the ray direction,
    so 'LoS' could bend around corners (and exploded exponentially on
    sparse boards). A queen at d4 must NOT be able to manipulate a
    piece at f6 (not on any straight line from d4) even though a bent
    rook-walk d4->d6->f6 exists over empty squares."""
    g = _set(ggp, KINGS + [
        ('cell', 'd', '4', 'white', 'queen'),
        ('queen_form', 'd', '4', 'base'),
        ('queen_royal', 'd', '4'),
        ('cell', 'f', '5', 'black', 'rook'),   # not on a d4 ray
        ('control', 'white'), ('turn_number', '6'),
    ])
    manips = [m for m in g.legal_moves('white')
              if isinstance(m, tuple)
              and m[0] in ('manipulate', 'manipulate_promote')
              and (m[3], m[4]) == ('f', '5')]
    assert not manips, (
        'f5 is not on a straight line from d4 — manipulation must be '
        f'illegal (bent-LoS bug); got {manips[:4]}')
    # Straight-line manipulation still works: put the rook on the ray.
    g2 = _set(ggp, KINGS + [
        ('cell', 'd', '4', 'white', 'queen'),
        ('queen_form', 'd', '4', 'base'),
        ('queen_royal', 'd', '4'),
        ('cell', 'f', '6', 'black', 'rook'),   # on the d4 ne diagonal
        ('control', 'white'), ('turn_number', '6'),
    ])
    manips2 = [m for m in g2.legal_moves('white')
               if isinstance(m, tuple) and m[0] == 'manipulate'
               and (m[3], m[4]) == ('f', '6')]
    assert manips2, 'straight-diagonal manipulation must remain legal'


# ---- 8. manipulation freeze actually blocks moves ------------------------

def test_frozen_piece_cannot_move(ggp):
    """Restriction 1: a manipulated piece may not make a spatial move
    on its next turn. The freeze fluent was previously SET but never
    consulted by any legal rule — frozen pieces could still move."""
    g = _set(ggp, KINGS + [
        ('cell', 'd', '4', 'black', 'rook'),
        ('manipulation_freeze', 'd', '4'),
        ('spatial_move_last_turn', 'd', '4'),
        ('cell', 'b', '2', 'black', 'pawn'),
        ('control', 'black'), ('turn_number', '7'),
    ])
    moves = g.legal_moves('black')
    rook_moves = [m for m in moves if isinstance(m, tuple)
                  and m[0] == 'move' and m[1] == 'rook']
    assert not rook_moves, (
        f'a frozen rook must have NO spatial moves; got {rook_moves[:4]}')
    pawn_moves = [m for m in moves if isinstance(m, tuple)
                  and m[0] == 'move' and m[1] == 'pawn']
    assert pawn_moves, 'unfrozen pieces still move'
