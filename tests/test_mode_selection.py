"""Tests for the in-UI mode selector AND AI-aware undo/redo.

Historical note: the menu was originally a two-slot design — a 'side'
(which colour the human plays) and an 'opponent' (the other side). With
the addition of Computer-vs-Computer mode (2026-05-30), the menu is now
per-side: `white_player` and `black_player` each pick independently from
the same PLAYER_OPTIONS catalog ('human' | 'random' | 'easy' | 'medium' |
'hard'). The old `side` / `opponent` kwargs and the `user_side` /
`opponent` / `ai_controller` / `ai_color` attributes still work via
derived properties / a back-compat path in `apply_mode_selection` — this
test file exercises both APIs side-by-side.

CvC-specific behaviour is covered in tests/test_cvc_mode.py.

Undo/redo respect the AI: in human-vs-AI mode the user expects the undo
key to take them back to their PREVIOUS turn (rolling back both the AI's
last move and the user's last move), not just the AI's last move. Redo
symmetrically advances to the next user turn. In HvH and CvC undo is
single-step (no user side to anchor on in CvC).
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


def test_player_options_catalog_has_all_player_types():
    """The PLAYER_OPTIONS catalog (used per-side) carries every player
    type the menu offers. Catalog detail covered in test_cvc_mode.py;
    this assertion lives here to keep the legacy-API tests grouped."""
    keys = [opt['key'] for opt in Game.PLAYER_OPTIONS]
    for required in ('human', 'random', 'easy', 'medium', 'hard'):
        assert required in keys


def test_ai_difficulty_targets_configured():
    """The class-level _AI_DIFFICULTY dict maps each AI difficulty key to a
    target iteration and a resolution mode ('capped' or 'exact')."""
    assert 'easy' in Game._AI_DIFFICULTY
    assert 'medium' in Game._AI_DIFFICULTY
    assert 'hard' in Game._AI_DIFFICULTY
    for key in ('easy', 'medium', 'hard'):
        cfg = Game._AI_DIFFICULTY[key]
        assert isinstance(cfg['target'], int)
        assert cfg['mode'] in ('capped', 'exact')
    # Easy is 'capped' (auto-tracks latest up to its cap); Medium/Hard are
    # 'exact' (gated until their exact checkpoint exists).
    assert Game._AI_DIFFICULTY['easy']['mode'] == 'capped'
    assert Game._AI_DIFFICULTY['medium']['mode'] == 'exact'
    assert Game._AI_DIFFICULTY['hard']['mode'] == 'exact'


def test_ai_checkpoint_available_for_non_ai_keys():
    """`human` and `random` are always 'available' (not gated by a
    checkpoint)."""
    g = Game()
    assert g._ai_checkpoint_available('human') is True
    assert g._ai_checkpoint_available('random') is True


def test_make_ai_player_random_returns_none():
    """`random` opponent key returns None (AIController falls back to its
    built-in RandomPlayer)."""
    g = Game()
    assert g._make_ai_player('random') is None


def test_resolve_easy_capped_picks_highest_below_target(tmp_path):
    """Easy ('capped') resolves to the highest existing checkpoint at or
    below its target. With checkpoints 10, 20, 32 present and target 50,
    it picks 32. When 50 exists, it picks 50. Never exceeds 50."""
    saved_dir = Game._CHECKPOINT_DIR
    saved_easy = dict(Game._AI_DIFFICULTY['easy'])
    Game._CHECKPOINT_DIR = str(tmp_path)
    Game._AI_DIFFICULTY['easy'] = {'target': 50, 'mode': 'capped'}
    try:
        for it in (10, 20, 32):
            (tmp_path / f'model_iter_{it:04d}.pt').write_text('x')
        resolved = Game._resolve_ai_checkpoint('easy')
        assert resolved.endswith('model_iter_0032.pt')
        # Now iter 50 lands → easy should pick it exactly.
        (tmp_path / 'model_iter_0050.pt').write_text('x')
        assert Game._resolve_ai_checkpoint('easy').endswith('model_iter_0050.pt')
        # A later iter (60) must NOT be picked (cap is 50).
        (tmp_path / 'model_iter_0060.pt').write_text('x')
        assert Game._resolve_ai_checkpoint('easy').endswith('model_iter_0050.pt')
    finally:
        Game._CHECKPOINT_DIR = saved_dir
        Game._AI_DIFFICULTY['easy'] = saved_easy


def test_resolve_medium_exact_unavailable_until_checkpoint_exists(tmp_path):
    """Medium ('exact') resolves to None until its exact checkpoint exists,
    even when lower checkpoints are present."""
    saved_dir = Game._CHECKPOINT_DIR
    saved_med = dict(Game._AI_DIFFICULTY['medium'])
    Game._CHECKPOINT_DIR = str(tmp_path)
    Game._AI_DIFFICULTY['medium'] = {'target': 75, 'mode': 'exact'}
    try:
        for it in (10, 32, 50):
            (tmp_path / f'model_iter_{it:04d}.pt').write_text('x')
        assert Game._resolve_ai_checkpoint('medium') is None  # 75 not present
        (tmp_path / 'model_iter_0075.pt').write_text('x')
        assert Game._resolve_ai_checkpoint('medium').endswith('model_iter_0075.pt')
    finally:
        Game._CHECKPOINT_DIR = saved_dir
        Game._AI_DIFFICULTY['medium'] = saved_med


# --- open / close menu ------------------------------------------------------

def test_open_close_mode_menu():
    g = Game()
    g.open_mode_menu()
    assert g.mode_menu is not None
    # New per-side shape (post-CvC): 'white' and 'black' columns.
    assert 'white' in g.mode_menu and 'black' in g.mode_menu
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


def test_show_mode_menu_populates_rects_for_both_sides_when_open():
    """Post-CvC menu: rects tagged by side ('white' or 'black'). Each
    AI option whose checkpoint isn't on disk is dimmed and EXCLUDED from
    mode_menu_rects (not clickable). 'human' / 'random' always render."""
    g = Game()
    g.open_mode_menu()
    surface = pygame.Surface((800, 800))
    g.show_mode_menu(surface)
    sides_seen = set(side for (_r, side, _k) in g.mode_menu_rects)
    assert 'white' in sides_seen
    assert 'black' in sides_seen
    expected_per_side = sum(
        1 for opt in Game.PLAYER_OPTIONS
        if g._ai_checkpoint_available(opt['key']))
    assert expected_per_side >= 2  # 'human' + 'random' always available
    for side in ('white', 'black'):
        n = sum(1 for (_r, s, _k) in g.mode_menu_rects if s == side)
        assert n == expected_per_side
    for rect, side, key in g.mode_menu_rects:
        assert isinstance(rect, pygame.Rect)
        assert side in ('white', 'black')
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
