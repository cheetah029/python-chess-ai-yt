"""Tests for the in-UI mode selector (Goal 2).

The Game now owns mode state (which "computer opponent" the game is using)
and an in-UI menu for switching it. This is the testable layer; main.py just
opens the menu on a key press and dispatches clicks to it.

The mode selector is designed to be extensible: it ships with `off`,
`random_black`, and `random_white`, and future difficulty levels (Easy /
Medium / Hard AI) plug in by adding entries to `Game.MODE_OPTIONS` and a
factory for that player type.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Headless display/audio so Game (Config) and pygame work without a screen.
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


from game import Game
from ai_controller import AIController


# --- defaults / initial state -----------------------------------------------

def test_default_mode_is_human_vs_human():
    g = Game()
    assert g.mode == 'human_vs_human'
    assert g.ai_color is None
    assert g.ai_controller is None


def test_mode_menu_starts_closed():
    g = Game()
    assert g.mode_menu is None
    assert g.mode_menu_rects == []


def test_mode_options_class_attr_includes_required_keys():
    """Sanity: the catalog of selectable modes ships with the three baseline
    entries the UI needs. Future difficulty levels can append to it."""
    keys = [opt['key'] for opt in Game.MODE_OPTIONS]
    assert 'off' in keys
    assert 'random_black' in keys
    assert 'random_white' in keys
    # Each option carries a human-readable label for the menu.
    for opt in Game.MODE_OPTIONS:
        assert 'label' in opt and isinstance(opt['label'], str) and opt['label']


# --- open / close menu ------------------------------------------------------

def test_open_mode_menu_populates_state():
    g = Game()
    g.open_mode_menu()
    assert g.mode_menu is not None
    assert 'options' in g.mode_menu
    assert len(g.mode_menu['options']) >= 3


def test_close_mode_menu_clears_state():
    g = Game()
    g.open_mode_menu()
    g.close_mode_menu()
    assert g.mode_menu is None
    assert g.mode_menu_rects == []


def test_open_menu_does_not_advance_or_mutate_game():
    g = Game()
    turn_no = g.board.turn_number
    next_player = g.next_player
    g.open_mode_menu()
    g.close_mode_menu()
    assert g.board.turn_number == turn_no
    assert g.next_player == next_player


# --- applying a selection ---------------------------------------------------

def test_apply_mode_off_sets_human_vs_human():
    g = Game()
    g.apply_mode_selection('off')
    assert g.mode == 'human_vs_human'
    assert g.ai_color is None
    assert g.ai_controller is None


def test_apply_mode_random_black_creates_ai():
    g = Game()
    g.apply_mode_selection('random_black')
    assert g.mode == 'human_vs_random'
    assert g.ai_color == 'black'
    assert isinstance(g.ai_controller, AIController)
    assert g.ai_controller.color == 'black'


def test_apply_mode_random_white_creates_ai():
    g = Game()
    g.apply_mode_selection('random_white')
    assert g.mode == 'human_vs_random'
    assert g.ai_color == 'white'
    assert isinstance(g.ai_controller, AIController)
    assert g.ai_controller.color == 'white'


def test_apply_mode_invalid_option_raises():
    g = Game()
    with pytest.raises(ValueError):
        g.apply_mode_selection('definitely_not_a_real_mode')


def test_apply_mode_closes_menu():
    g = Game()
    g.open_mode_menu()
    g.apply_mode_selection('random_black')
    assert g.mode_menu is None
    assert g.mode_menu_rects == []


# --- switching modes --------------------------------------------------------

def test_switching_between_ai_colors_replaces_controller():
    g = Game()
    g.apply_mode_selection('random_black')
    first_controller = g.ai_controller
    assert first_controller.color == 'black'

    g.apply_mode_selection('random_white')
    assert g.ai_controller.color == 'white'
    # A fresh controller (or at least one configured for the new color).
    assert g.ai_color == 'white'


def test_switching_to_off_clears_controller():
    g = Game()
    g.apply_mode_selection('random_black')
    assert g.ai_controller is not None
    g.apply_mode_selection('off')
    assert g.mode == 'human_vs_human'
    assert g.ai_color is None
    assert g.ai_controller is None


# --- integration with AIController -----------------------------------------

def test_take_ai_turn_after_selecting_random_white():
    """White is AI under 'random_white'; white moves first, so the AI gets
    the very first turn and should be able to apply it."""
    random.seed(7)
    g = Game()
    g.apply_mode_selection('random_white')
    assert g.ai_controller.is_ai_turn(g)
    turn_no = g.board.turn_number
    took = g.ai_controller.take_turn(g)
    assert took is True
    assert g.board.turn_number == turn_no + 1
    assert g.next_player == 'black'
    assert g.ai_controller.is_ai_turn(g) is False


def test_take_ai_turn_only_on_ais_color():
    """Under 'random_black' the AI does not act on white's turn."""
    g = Game()
    g.apply_mode_selection('random_black')
    # White to move; AI plays black, so it's NOT the AI's turn.
    assert g.ai_controller.is_ai_turn(g) is False
    turn_no = g.board.turn_number
    took = g.ai_controller.take_turn(g)
    assert took is False
    assert g.board.turn_number == turn_no


def test_switching_to_ai_mode_mid_game_lets_ai_play():
    """Start human-vs-human, advance one turn, then switch to 'random_black'.
    Once it's black's turn, the AI takes over correctly."""
    random.seed(101)
    g = Game()
    # Advance one turn (white) using a throwaway controller, so it's now black's turn.
    AIController('white').take_turn(g)
    assert g.next_player == 'black'

    g.apply_mode_selection('random_black')
    assert g.ai_controller.is_ai_turn(g) is True
    turn_no = g.board.turn_number
    g.ai_controller.take_turn(g)
    assert g.board.turn_number == turn_no + 1


# --- rendering smoke tests --------------------------------------------------

def test_show_mode_menu_noop_when_closed():
    g = Game()
    surface = pygame.Surface((800, 800))
    g.show_mode_menu(surface)  # must not raise; menu is closed
    assert g.mode_menu_rects == []


def test_show_mode_menu_populates_rects_when_open():
    g = Game()
    g.open_mode_menu()
    surface = pygame.Surface((800, 800))
    g.show_mode_menu(surface)
    # One clickable rect per option in the catalog.
    assert len(g.mode_menu_rects) == len(g.mode_menu['options'])
    # Each entry is (rect, option_key).
    for rect, key in g.mode_menu_rects:
        assert isinstance(rect, pygame.Rect)
        assert isinstance(key, str)


# --- "any menu open" interaction -------------------------------------------

def test_any_menu_open_includes_mode_menu():
    """If main.py checks "is any menu open?" to gate other interactions,
    the mode menu must be included alongside transform/promotion menus."""
    g = Game()
    assert g.is_any_menu_open() is False
    g.open_mode_menu()
    assert g.is_any_menu_open() is True
    g.close_mode_menu()
    assert g.is_any_menu_open() is False
