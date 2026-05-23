"""Tests for the in-UI mode selector AND AI-aware undo/redo.

The Game owns:

  - `user_side` ('white' or 'black') — which side the human plays.
  - `opponent`  ('human' or an AI key like 'random') — who plays the OTHER side.

These two choices are INDEPENDENT in the in-UI menu (you don't have to pick
between "Human (W) vs Random (B)" and "Random (W) vs Human (B)" — you pick a
side AND an opponent). `mode`, `ai_color`, and `ai_controller` are derived
from those two and are kept in sync automatically.

Undo/redo respect the AI: in human-vs-AI mode the user expects the undo key
to take them back to their PREVIOUS turn (rolling back both the AI's last
move and the user's last move), not just the AI's last move. Redo
symmetrically advances to the next user turn.
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


# --- defaults / catalog -----------------------------------------------------

def test_default_state():
    g = Game()
    assert g.user_side == 'white'   # default = human plays white
    assert g.opponent == 'human'
    assert g.mode == 'human_vs_human'
    assert g.ai_color is None
    assert g.ai_controller is None
    assert g.mode_menu is None
    assert g.mode_menu_rects == []


def test_side_options_catalog():
    keys = [opt['key'] for opt in Game.SIDE_OPTIONS]
    assert keys == ['white', 'black']
    for opt in Game.SIDE_OPTIONS:
        assert 'label' in opt and isinstance(opt['label'], str) and opt['label']


def test_opponent_options_catalog_has_human_and_random():
    keys = [opt['key'] for opt in Game.OPPONENT_OPTIONS]
    assert 'human' in keys
    assert 'random' in keys
    for opt in Game.OPPONENT_OPTIONS:
        assert 'label' in opt and isinstance(opt['label'], str) and opt['label']


# --- open / close menu ------------------------------------------------------

def test_open_close_mode_menu():
    g = Game()
    g.open_mode_menu()
    assert g.mode_menu is not None
    assert 'sides' in g.mode_menu and 'opponents' in g.mode_menu
    g.close_mode_menu()
    assert g.mode_menu is None
    assert g.mode_menu_rects == []


def test_open_menu_does_not_advance_game():
    g = Game()
    turn_no = g.board.turn_number
    g.open_mode_menu()
    g.close_mode_menu()
    assert g.board.turn_number == turn_no


def test_is_any_menu_open_includes_mode_menu():
    g = Game()
    assert g.is_any_menu_open() is False
    g.open_mode_menu()
    assert g.is_any_menu_open() is True
    g.close_mode_menu()
    assert g.is_any_menu_open() is False


# --- apply_mode_selection: side / opponent independently --------------------

def test_apply_side_only_updates_user_side():
    g = Game()
    g.apply_mode_selection(side='black')
    assert g.user_side == 'black'
    assert g.opponent == 'human'         # unchanged
    assert g.ai_controller is None       # still no AI


def test_apply_opponent_human_keeps_human_vs_human():
    g = Game()
    g.apply_mode_selection(opponent='human')
    assert g.opponent == 'human'
    assert g.mode == 'human_vs_human'
    assert g.ai_color is None
    assert g.ai_controller is None


def test_apply_opponent_random_with_default_side_makes_ai_black():
    g = Game()  # user_side defaults to 'white'
    g.apply_mode_selection(opponent='random')
    assert g.opponent == 'random'
    assert g.mode == 'human_vs_random'
    assert g.ai_color == 'black'
    assert isinstance(g.ai_controller, AIController)
    assert g.ai_controller.color == 'black'


def test_apply_opponent_random_with_user_side_black_makes_ai_white():
    g = Game()
    g.apply_mode_selection(side='black')
    g.apply_mode_selection(opponent='random')
    assert g.ai_color == 'white'
    assert g.ai_controller.color == 'white'


def test_switching_user_side_with_active_ai_updates_ai_color():
    g = Game()
    g.apply_mode_selection(opponent='random')   # AI = black
    assert g.ai_color == 'black'
    g.apply_mode_selection(side='black')        # now user = black; AI must flip
    assert g.user_side == 'black'
    assert g.ai_color == 'white'
    assert g.ai_controller.color == 'white'


def test_switching_opponent_to_human_clears_ai_controller():
    g = Game()
    g.apply_mode_selection(opponent='random')
    assert g.ai_controller is not None
    g.apply_mode_selection(opponent='human')
    assert g.opponent == 'human'
    assert g.ai_color is None
    assert g.ai_controller is None


def test_apply_mode_with_both_side_and_opponent():
    g = Game()
    g.apply_mode_selection(side='black', opponent='random')
    assert g.user_side == 'black'
    assert g.opponent == 'random'
    assert g.ai_color == 'white'
    assert isinstance(g.ai_controller, AIController)


def test_apply_mode_with_no_args_is_a_noop():
    g = Game()
    g.apply_mode_selection()  # nothing changes
    assert g.user_side == 'white'
    assert g.opponent == 'human'
    assert g.ai_controller is None


def test_apply_invalid_side_raises():
    g = Game()
    with pytest.raises(ValueError):
        g.apply_mode_selection(side='green')


def test_apply_invalid_opponent_raises():
    g = Game()
    with pytest.raises(ValueError):
        g.apply_mode_selection(opponent='galaxy_brain_ai')


# --- menu rendering / click rects -------------------------------------------

def test_apply_mode_selection_does_not_auto_close_menu():
    """Live-settings model: clicking a button updates the mode but leaves the
    menu open so the user can also change the other dimension. Menu closes
    only on M / Esc / close_mode_menu()."""
    g = Game()
    g.open_mode_menu()
    g.apply_mode_selection(side='black')
    assert g.mode_menu is not None
    g.apply_mode_selection(opponent='random')
    assert g.mode_menu is not None


def test_show_mode_menu_noop_when_closed():
    g = Game()
    surface = pygame.Surface((800, 800))
    g.show_mode_menu(surface)
    assert g.mode_menu_rects == []


def test_show_mode_menu_populates_rects_for_both_groups_when_open():
    g = Game()
    g.open_mode_menu()
    surface = pygame.Surface((800, 800))
    g.show_mode_menu(surface)
    # Entries are (rect, group_key, option_key)
    groups = set(g for (_r, g, _k) in g.mode_menu_rects)
    assert 'side' in groups
    assert 'opponent' in groups
    n_sides = sum(1 for (_r, g, _k) in g.mode_menu_rects if g == 'side')
    n_opps = sum(1 for (_r, g, _k) in g.mode_menu_rects if g == 'opponent')
    assert n_sides == len(Game.SIDE_OPTIONS)
    assert n_opps == len(Game.OPPONENT_OPTIONS)
    for rect, group, key in g.mode_menu_rects:
        assert isinstance(rect, pygame.Rect)
        assert group in ('side', 'opponent')
        assert isinstance(key, str)


# --- integration with AIController -----------------------------------------

def test_take_ai_turn_after_apply():
    random.seed(7)
    g = Game()
    g.apply_mode_selection(side='black', opponent='random')   # AI is white, moves first
    assert g.ai_controller.is_ai_turn(g)
    turn_no = g.board.turn_number
    assert g.ai_controller.take_turn(g) is True
    assert g.board.turn_number == turn_no + 1
    assert g.next_player == 'black'  # now user's turn


def test_take_ai_turn_only_on_ai_color():
    g = Game()
    g.apply_mode_selection(opponent='random')  # user white, AI black
    assert g.ai_controller.is_ai_turn(g) is False  # white to move = user
    assert g.ai_controller.take_turn(g) is False
    assert g.board.turn_number == 0


# --- undo / redo: human-vs-human (existing single-step behavior preserved) --

def _advance(g, n):
    """Apply n random legal turns using a throwaway random pick, mirroring
    how the human path would advance turns. (We can't run the actual UI
    event loop here, so we drive Game.next_turn via a helper AIController
    on whichever color is to move.)"""
    helpers = {'white': AIController('white'), 'black': AIController('black')}
    for _ in range(n):
        if g.winner is not None:
            return
        helpers[g.next_player].take_turn(g)


def test_undo_redo_human_vs_human_single_step():
    random.seed(11)
    g = Game()  # human-vs-human
    _advance(g, 4)  # turns 1..4
    assert g.board.turn_number == 4

    assert g.undo() is True
    assert g.board.turn_number == 3   # single-step undo

    assert g.redo() is True
    assert g.board.turn_number == 4


# --- undo / redo: human-vs-AI (skip the AI's turn) -------------------------

def test_undo_in_ai_mode_skips_to_previous_user_turn_user_white():
    """User plays white; AI plays black. Each user move is followed by an AI
    move. Undo from the user's turn should roll back BOTH the AI's most recent
    move and the user's most recent move, landing on the user's PREVIOUS turn."""
    random.seed(13)
    g = Game()
    g.apply_mode_selection(opponent='random')   # AI = black, AI moves second
    _advance(g, 4)  # turn 1 user, turn 2 AI, turn 3 user, turn 4 AI → user to move
    assert g.next_player == 'white'             # user's turn
    assert g.board.turn_number == 4

    assert g.undo() is True
    assert g.next_player == 'white'             # still user's turn (skipped AI's)
    assert g.board.turn_number == 2             # rolled back BOTH last moves


def test_undo_in_ai_mode_skips_to_previous_user_turn_user_black():
    random.seed(17)
    g = Game()
    g.apply_mode_selection(side='black', opponent='random')   # AI = white, moves first
    _advance(g, 4)  # turn 1 AI, turn 2 user, turn 3 AI, turn 4 user → AI to move
    assert g.next_player == 'white'             # AI's turn
    assert g.board.turn_number == 4

    # Advance one more turn (AI) so the user is about to play.
    _advance(g, 1)
    assert g.next_player == 'black'             # user's turn
    assert g.board.turn_number == 5

    assert g.undo() is True
    assert g.next_player == 'black'             # still user's turn
    assert g.board.turn_number == 3             # rolled back BOTH last moves


def test_redo_in_ai_mode_advances_to_next_user_turn():
    random.seed(19)
    g = Game()
    g.apply_mode_selection(opponent='random')   # AI = black
    _advance(g, 4)
    assert g.board.turn_number == 4
    assert g.next_player == 'white'

    # Undo: turn 4 → turn 2.
    g.undo()
    assert g.board.turn_number == 2
    assert g.next_player == 'white'

    # Redo: turn 2 → turn 4 (skip back over the AI's turn).
    assert g.redo() is True
    assert g.board.turn_number == 4
    assert g.next_player == 'white'


def test_undo_at_game_start_when_user_is_black():
    """When the user is black and the AI plays white (moves first), undoing
    from the user's first turn should NOT crash and should stop at the earliest
    available state."""
    random.seed(23)
    g = Game()
    g.apply_mode_selection(side='black', opponent='random')
    _advance(g, 1)  # AI moves; now user's turn
    assert g.next_player == 'black'
    assert g.board.turn_number == 1

    # Undo from here: we want a user-turn state, but the only earlier state is
    # the initial state (AI's turn). The implementation should stop gracefully
    # and not raise.
    result = g.undo()
    # It either undid to the initial state (next_player='white') or refused —
    # but it must not raise, and it must not leave the game in a corrupt state.
    assert result is True
    assert g.board.turn_number == 0


def test_undo_blocked_in_intermediate_state():
    """Existing invariant preserved: undo refuses while a UI menu is open."""
    random.seed(29)
    g = Game()
    g.apply_mode_selection(opponent='random')
    _advance(g, 4)
    g.open_mode_menu()
    assert g.undo() is False   # mode menu is open
    g.close_mode_menu()
    assert g.undo() is True    # now allowed


def test_redo_stack_cleared_on_new_turn():
    """Existing invariant preserved: making a new turn invalidates the redo
    stack (the timeline diverges)."""
    random.seed(31)
    g = Game()
    g.apply_mode_selection(opponent='random')
    _advance(g, 4)
    g.undo()
    assert g.can_redo() is True
    # Make a new turn (user) — diverges from the undone timeline.
    _advance(g, 1)
    assert g.can_redo() is False
