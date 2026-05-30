"""Tests for Computer-vs-Computer (CvC) mode and the generalised
per-side player-selection menu.

The earlier menu used two slots: a 'side' (which colour the human plays)
and an 'opponent' (who plays the other colour). That made human-vs-human
and human-vs-AI possible but couldn't express AI-vs-AI.

The new menu lets EACH SIDE be independently set to any of:
    'human' | 'random' | 'easy' | 'medium' | 'hard'

Modes (derived from the two per-side choices):
    HvH ->  both 'human'
    HvAI -> exactly one 'human'
    CvC ->  neither 'human' (the two AIs may be the same or different)

Backwards compat: `user_side`, `opponent`, `ai_color`, `ai_controller`
remain as derived properties so existing callers keep working in
HvH/HvAI. In CvC they read None (no single canonical human side / AI
controller).

These tests are headless: pygame uses SDL dummy drivers.
"""

import sys
import os
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

import random
import pytest

from game import Game
from ai_controller import AIController


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except pygame.error:
        pass


# ---- catalog --------------------------------------------------------------

def test_player_options_catalog_lists_all_player_types():
    """PLAYER_OPTIONS lists EVERY available player type. The same catalog
    is shown for both sides of the menu — there's no longer a separate
    'side' vs 'opponent' distinction."""
    keys = [opt['key'] for opt in Game.PLAYER_OPTIONS]
    for required in ('human', 'random', 'easy', 'medium', 'hard'):
        assert required in keys, f"PLAYER_OPTIONS missing {required!r}"
    for opt in Game.PLAYER_OPTIONS:
        assert 'label' in opt
        assert isinstance(opt['label'], str) and opt['label']


def test_default_white_and_black_player_are_human():
    """Default state is HvH: both sides start as 'human'."""
    g = Game()
    assert g.white_player == 'human'
    assert g.black_player == 'human'
    assert g.mode == 'human_vs_human'


# ---- apply_mode_selection: new per-side API --------------------------------

def test_apply_white_player_only_updates_white():
    g = Game()
    g.apply_mode_selection(white_player='random')
    assert g.white_player == 'random'
    assert g.black_player == 'human'  # unchanged


def test_apply_black_player_only_updates_black():
    g = Game()
    g.apply_mode_selection(black_player='random')
    assert g.black_player == 'random'
    assert g.white_player == 'human'


def test_apply_both_sides_simultaneously():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.white_player == 'random'
    assert g.black_player == 'random'


def test_apply_invalid_white_player_raises():
    g = Game()
    with pytest.raises(ValueError):
        g.apply_mode_selection(white_player='cheese')


def test_apply_invalid_black_player_raises():
    g = Game()
    with pytest.raises(ValueError):
        g.apply_mode_selection(black_player='cheese')


# ---- mode derivation -------------------------------------------------------

def test_mode_human_vs_human_when_both_human():
    g = Game()
    assert g.mode == 'human_vs_human'
    g.apply_mode_selection(white_player='human', black_player='human')
    assert g.mode == 'human_vs_human'


def test_mode_human_vs_ai_when_one_side_human():
    """Mode string carries the AI key for legacy callers
    (e.g. 'human_vs_random'). The new CvC tests don't pin a single
    'human_vs_ai' literal; they accept the prefix instead."""
    g = Game()
    g.apply_mode_selection(black_player='random')
    assert g.mode == 'human_vs_random'
    assert g.mode.startswith('human_vs_')
    assert g.mode != 'human_vs_human'

    g2 = Game()
    g2.apply_mode_selection(white_player='random')
    assert g2.mode == 'human_vs_random'


def test_mode_computer_vs_computer_when_neither_human():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.mode == 'computer_vs_computer'

    g2 = Game()
    g2.apply_mode_selection(white_player='random', black_player='easy')
    # Even when the two AIs differ, mode is CvC.
    # ('easy' may be unavailable on disk depending on checkpoints; the mode
    # is computed from the player keys regardless — availability gates the
    # MENU, not the mode model.)
    assert g2.mode == 'computer_vs_computer'


# ---- ai_controllers per side ----------------------------------------------

def test_ai_controllers_dict_has_both_keys_with_none_in_hvh():
    g = Game()
    assert g.ai_controllers == {'white': None, 'black': None}


def test_ai_controllers_white_set_when_white_is_ai():
    g = Game()
    g.apply_mode_selection(white_player='random')
    assert isinstance(g.ai_controllers['white'], AIController)
    assert g.ai_controllers['white'].color == 'white'
    assert g.ai_controllers['black'] is None


def test_ai_controllers_black_set_when_black_is_ai():
    g = Game()
    g.apply_mode_selection(black_player='random')
    assert isinstance(g.ai_controllers['black'], AIController)
    assert g.ai_controllers['black'].color == 'black'
    assert g.ai_controllers['white'] is None


def test_ai_controllers_both_set_in_cvc():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert isinstance(g.ai_controllers['white'], AIController)
    assert isinstance(g.ai_controllers['black'], AIController)
    assert g.ai_controllers['white'].color == 'white'
    assert g.ai_controllers['black'].color == 'black'


def test_switching_player_to_human_clears_that_sides_controller():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    g.apply_mode_selection(white_player='human')
    assert g.ai_controllers['white'] is None
    assert g.ai_controllers['black'] is not None  # untouched


# ---- backward-compat derived properties (HvH/HvAI keep working) ----------

def test_legacy_user_side_in_hvh_defaults_to_white():
    """HvH has no 'AI side' to subtract — keep the long-standing default
    that the human's perspective is white."""
    g = Game()
    assert g.user_side == 'white'


def test_legacy_user_side_in_hvai_is_the_human_color():
    g = Game()
    g.apply_mode_selection(white_player='random')
    assert g.user_side == 'black'

    g2 = Game()
    g2.apply_mode_selection(black_player='random')
    assert g2.user_side == 'white'


def test_legacy_user_side_in_cvc_is_none():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.user_side is None


def test_legacy_opponent_in_hvh_is_human():
    g = Game()
    assert g.opponent == 'human'


def test_legacy_opponent_in_hvai_is_the_ai_key():
    g = Game()
    g.apply_mode_selection(black_player='random')
    assert g.opponent == 'random'


def test_legacy_opponent_in_cvc_is_none():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.opponent is None


def test_legacy_ai_controller_in_hvai_returns_the_single_one():
    g = Game()
    g.apply_mode_selection(black_player='random')
    assert g.ai_controller is g.ai_controllers['black']


def test_legacy_ai_controller_in_cvc_is_none():
    """In CvC there are TWO ai_controllers — the singular property is
    None because there isn't ONE canonical AI."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.ai_controller is None


def test_legacy_ai_color_in_hvai_is_the_ai_color():
    g = Game()
    g.apply_mode_selection(black_player='random')
    assert g.ai_color == 'black'


def test_legacy_ai_color_in_cvc_is_none():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.ai_color is None


# ---- back-compat: old side= / opponent= apply_mode_selection kwargs -------

def test_legacy_apply_mode_side_only():
    """Old API: side='black' means the human plays black -> white side
    becomes whatever the opponent was (default 'human' -> still HvH but
    with the human's perspective flipped to black)."""
    g = Game()
    g.apply_mode_selection(side='black')
    assert g.user_side == 'black'
    assert g.white_player == 'human'  # opponent default
    assert g.black_player == 'human'  # human's side
    assert g.mode == 'human_vs_human'


def test_legacy_apply_mode_opponent_only_with_default_side():
    """Old API: opponent='random' with default user_side='white' ->
    AI plays black."""
    g = Game()
    g.apply_mode_selection(opponent='random')
    assert g.white_player == 'human'
    assert g.black_player == 'random'
    assert g.mode == 'human_vs_random'
    assert g.ai_color == 'black'


def test_legacy_apply_mode_side_and_opponent_together():
    g = Game()
    g.apply_mode_selection(side='black', opponent='random')
    assert g.user_side == 'black'
    assert g.white_player == 'random'
    assert g.black_player == 'human'
    assert g.ai_color == 'white'


# ---- menu open/close + rendering -----------------------------------------

def test_open_mode_menu_shape_carries_player_options_for_both_sides():
    """The opened menu carries the per-side player options that
    show_mode_menu will render."""
    g = Game()
    g.open_mode_menu()
    assert g.mode_menu is not None
    # New shape: per-side option lists.
    assert 'white' in g.mode_menu
    assert 'black' in g.mode_menu
    # Each side's options are the PLAYER_OPTIONS catalog.
    for side in ('white', 'black'):
        keys = [opt['key'] for opt in g.mode_menu[side]]
        assert set(keys) == {opt['key'] for opt in Game.PLAYER_OPTIONS}


def test_show_mode_menu_rects_group_by_white_and_black():
    """Each click rect is tagged with its side ('white' or 'black') and
    its player key — main.py uses these to dispatch back into
    apply_mode_selection(white_player=...) or (black_player=...)."""
    g = Game()
    g.open_mode_menu()
    surface = pygame.Surface((800, 800))
    g.show_mode_menu(surface)
    groups = set(group for (_r, group, _k) in g.mode_menu_rects)
    assert 'white' in groups
    assert 'black' in groups
    # No leftover 'side' / 'opponent' tags from the old design.
    assert 'side' not in groups
    assert 'opponent' not in groups
    # Per side, every AVAILABLE player option appears exactly once.
    available_keys = [
        opt['key'] for opt in Game.PLAYER_OPTIONS
        if g._ai_checkpoint_available(opt['key'])]
    for side in ('white', 'black'):
        side_keys = [k for (_r, group, k) in g.mode_menu_rects if group == side]
        assert sorted(side_keys) == sorted(available_keys)


# ---- AI turn dispatch in CvC ----------------------------------------------

def test_current_ai_controller_returns_white_when_white_to_move_in_cvc():
    """main.py needs to know which AI controller (if any) drives the
    CURRENT side to move. Expose a small helper so it doesn't have to
    reach into ai_controllers itself."""
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    assert g.next_player == 'white'
    assert g.current_ai_controller() is g.ai_controllers['white']


def test_current_ai_controller_returns_black_after_first_move_in_cvc():
    random.seed(101)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    g.current_ai_controller().take_turn(g)
    assert g.next_player == 'black'
    assert g.current_ai_controller() is g.ai_controllers['black']


def test_current_ai_controller_is_none_in_hvh():
    g = Game()
    assert g.current_ai_controller() is None


def test_current_ai_controller_is_none_on_user_turn_in_hvai():
    g = Game()
    g.apply_mode_selection(black_player='random')  # AI=black, user=white
    assert g.next_player == 'white'
    assert g.current_ai_controller() is None


def test_cvc_can_play_multiple_full_turns_via_take_turn():
    """Sanity: a CvC game can be driven forward by calling
    current_ai_controller().take_turn repeatedly until it ends (or hits
    a turn cap)."""
    random.seed(103)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    turns_played = 0
    for _ in range(50):
        ctrl = g.current_ai_controller()
        if ctrl is None or g.winner is not None:
            break
        before = g.board.turn_number
        ok = ctrl.take_turn(g)
        assert ok is True
        assert g.board.turn_number == before + 1
        turns_played += 1
    assert turns_played > 0


# ---- undo / redo in CvC ---------------------------------------------------

def _advance_cvc(g, n):
    for _ in range(n):
        if g.winner is not None:
            return
        ctrl = g.current_ai_controller()
        if ctrl is None:
            return
        ctrl.take_turn(g)


def test_undo_in_cvc_is_single_step():
    """CvC has no 'user side' to anchor on — undo steps back ONE ply,
    same as HvH. (Skip-AI-turn undo is only HvAI behaviour.)"""
    random.seed(107)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 4)
    assert g.board.turn_number == 4
    assert g.undo() is True
    assert g.board.turn_number == 3  # single step
    assert g.undo() is True
    assert g.board.turn_number == 2


def test_redo_in_cvc_is_single_step():
    random.seed(109)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    _advance_cvc(g, 4)
    g.undo()
    g.undo()
    assert g.board.turn_number == 2
    assert g.redo() is True
    assert g.board.turn_number == 3
    assert g.redo() is True
    assert g.board.turn_number == 4
