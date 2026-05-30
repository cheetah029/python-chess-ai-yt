"""Tests for the pause-screen + PGN/FEN serialize/load dialog.

The dialog has TWO roles, intentionally unified per user spec:

  1. A *paused-game screen* that lets the user undo/redo without
     interfering with CvC autoplay. Opening the dialog halts the AI
     loop; closing the dialog resumes it.
  2. A *PGN/FEN-style save/load dialog* showing the serialized game
     state (with a Copy button) and a Paste/Load control to restore
     a previously-saved state.

Single key (P) opens it. Undo/redo are gated on the dialog being open
in CvC (otherwise they race the autoplay).

State-machine rules tested below:

  - The dialog open flag participates in `is_any_menu_open()` so it
    blocks AI dispatch and other interactions uniformly.
  - Opening the mode menu while the dialog is open CLOSES the dialog
    and OPENS the mode menu (and vice-versa). They are both
    paused-game states; only one is on screen at a time.
  - Reset-confirm can be activated FROM the dialog (R press), and
    the reset-confirm overlay takes precedence visually but the
    dialog state survives a cancelled reset.
  - Theme (T) and flip (F) work regardless of which paused state is
    on screen (viewing preferences never interfere).
  - All other keys (M / U / Y / R / P) have well-defined transitions.

Serialization round-trip rules:

  - serialize_to_text -> deserialize -> identical game (same board,
    same next_player, same winner, same undo/redo history, same per-
    side player choices, same _perspective_side).
  - Round-trip preserves boulder cooldown + no-return memory, knight
    invulnerability, manipulation freeze, repetition state-history
    counts, and tiny-endgame distance counts (all stored on the
    Board / its substructures).
  - Round-trip works in HvH, HvAI, and CvC modes.
  - Bad / truncated / wrong-version text raises a clean error
    (ValueError or similar) and leaves the existing game untouched.
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

import copy
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


# ===========================================================================
# Section 1 — pause-dialog state machine
# ===========================================================================

def test_pgn_dialog_default_closed():
    """Fresh game: no paused dialog open."""
    g = Game()
    assert g.pgn_dialog_open is False


def test_open_close_pgn_dialog():
    g = Game()
    g.open_pgn_dialog()
    assert g.pgn_dialog_open is True
    g.close_pgn_dialog()
    assert g.pgn_dialog_open is False


def test_open_pgn_dialog_is_idempotent():
    """Opening twice in a row is fine — second call is a no-op."""
    g = Game()
    g.open_pgn_dialog()
    g.open_pgn_dialog()
    assert g.pgn_dialog_open is True


def test_close_pgn_dialog_is_idempotent():
    """Closing when already closed is fine."""
    g = Game()
    g.close_pgn_dialog()
    assert g.pgn_dialog_open is False


def test_is_any_menu_open_includes_pgn_dialog():
    """The dialog blocks all input + AI dispatch via is_any_menu_open,
    same as mode_menu / transform_menu / promotion_menu / reset_confirm."""
    g = Game()
    assert g.is_any_menu_open() is False
    g.open_pgn_dialog()
    assert g.is_any_menu_open() is True
    g.close_pgn_dialog()
    assert g.is_any_menu_open() is False


def test_is_autoplay_paused_true_when_dialog_open():
    """is_autoplay_paused is the question main.py asks before dispatching
    a CvC AI turn. The pgn dialog must answer True."""
    g = Game()
    assert g.is_autoplay_paused() is False
    g.open_pgn_dialog()
    assert g.is_autoplay_paused() is True


def test_is_autoplay_paused_true_when_mode_menu_open():
    g = Game()
    g.open_mode_menu()
    assert g.is_autoplay_paused() is True


def test_is_autoplay_paused_true_when_reset_confirm_pending():
    g = Game()
    g.reset_confirm_pending = True
    assert g.is_autoplay_paused() is True


# ---- mutual exclusion between mode menu and pgn dialog ---------------------

def test_open_mode_menu_closes_pgn_dialog():
    """User spec: 'mode menu should be able to be opened during pause
    (which will close the pause screen and open the mode menu)'."""
    g = Game()
    g.open_pgn_dialog()
    g.open_mode_menu()
    assert g.mode_menu is not None
    assert g.pgn_dialog_open is False


def test_open_pgn_dialog_closes_mode_menu():
    """Symmetric: opening the pgn dialog while mode menu is up closes
    the mode menu."""
    g = Game()
    g.open_mode_menu()
    g.open_pgn_dialog()
    assert g.pgn_dialog_open is True
    assert g.mode_menu is None


def test_close_mode_menu_does_not_reopen_pgn_dialog():
    """When the user has switched mode menu -> pgn dialog -> mode menu,
    closing the mode menu must NOT auto-reopen the pgn dialog. The two
    are independent paused states."""
    g = Game()
    g.open_pgn_dialog()
    g.open_mode_menu()      # closes pgn
    g.close_mode_menu()
    assert g.pgn_dialog_open is False
    assert g.mode_menu is None


# ---- reset-confirm interaction --------------------------------------------

def test_reset_confirm_can_be_triggered_while_dialog_open():
    """The user spec allows 'R' to work during pause. We model this as:
    the dialog stays open and the reset-confirm flag also goes up.
    Both contribute to is_any_menu_open (still paused)."""
    g = Game()
    g.open_pgn_dialog()
    g.reset_confirm_pending = True
    assert g.is_any_menu_open() is True
    # The dialog flag is unchanged — the reset-confirm overlay renders
    # on top; main.py renders both, the confirm overlay covers the
    # dialog visually.
    assert g.pgn_dialog_open is True
    assert g.reset_confirm_pending is True


def test_reset_clears_pgn_dialog_flag():
    """A full reset() reinitializes the game; the pgn dialog flag
    starts False on the new state."""
    g = Game()
    g.open_pgn_dialog()
    g.reset()
    assert g.pgn_dialog_open is False


# ---- dialog rendering ------------------------------------------------------

def test_show_pgn_dialog_noop_when_closed():
    """Closed dialog leaves the surface untouched."""
    g = Game()
    surface = pygame.Surface((400, 400))
    surface.fill((10, 20, 30))
    g.show_pgn_dialog(surface)
    assert surface.get_at((200, 200))[:3] == (10, 20, 30)


def test_show_pgn_dialog_draws_when_open():
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((600, 600))
    surface.fill((10, 20, 30))
    g.show_pgn_dialog(surface)
    # The dialog now renders only inside a right-side panel. Sample a
    # pixel near the right edge — must differ from the untouched
    # background. (Centre pixel is intentionally left untouched so the
    # board is visible during pause; see
    # tests/test_pause_dialog_layout_and_fen.py for the
    # board-still-visible invariants.)
    assert surface.get_at((560, 100))[:3] != (10, 20, 30)


def test_show_pgn_dialog_populates_button_rects():
    """The dialog needs click rects for the Copy and Load buttons,
    populated each render for main.py's MOUSEBUTTONDOWN dispatch."""
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    g.show_pgn_dialog(surface)
    assert g.pgn_dialog_copy_rect is not None
    assert g.pgn_dialog_load_rect is not None
    assert isinstance(g.pgn_dialog_copy_rect, pygame.Rect)
    assert isinstance(g.pgn_dialog_load_rect, pygame.Rect)


def test_show_pgn_dialog_clears_rects_when_closed():
    g = Game()
    g.open_pgn_dialog()
    surface = pygame.Surface((800, 800))
    g.show_pgn_dialog(surface)
    g.close_pgn_dialog()
    g.show_pgn_dialog(surface)  # no-op
    assert g.pgn_dialog_copy_rect is None
    assert g.pgn_dialog_load_rect is None


# ===========================================================================
# Section 2 — serialize / deserialize (PGN/FEN-like text)
# ===========================================================================

def test_serialize_returns_a_non_empty_string():
    g = Game()
    text = g.serialize_to_text()
    assert isinstance(text, str)
    assert len(text) > 0


def test_serialized_text_carries_a_recognizable_header():
    """Human-readable header so the user can recognise it when pasted
    in another window. Format details internal — just check a marker."""
    g = Game()
    text = g.serialize_to_text()
    # Some sort of variant marker so loaders can detect wrong-format pastes.
    assert 'VARIANT_SAVE' in text or 'variant' in text.lower()


def test_serialized_text_includes_mode_and_turn_info():
    """The header is human-readable; mode + current turn should be visible."""
    g = Game()
    g.apply_mode_selection(opponent='random')
    text = g.serialize_to_text()
    assert 'human_vs_random' in text or 'random' in text.lower()


def test_round_trip_initial_game_preserves_board_and_turn():
    g = Game()
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.next_player == g.next_player
    assert g2.board.turn_number == g.board.turn_number
    assert g2.winner == g.winner


def test_round_trip_preserves_per_side_player_choices_hvh():
    g = Game()
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.white_player == 'human'
    assert g2.black_player == 'human'
    assert g2.mode == 'human_vs_human'


def test_round_trip_preserves_per_side_player_choices_hvai():
    g = Game()
    g.apply_mode_selection(opponent='random')   # AI = black
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.white_player == 'human'
    assert g2.black_player == 'random'
    assert g2.mode == 'human_vs_random'
    assert g2.ai_color == 'black'


def test_round_trip_preserves_cvc_mode():
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.white_player == 'random'
    assert g2.black_player == 'random'
    assert g2.mode == 'computer_vs_computer'
    assert g2.ai_controllers['white'] is not None
    assert g2.ai_controllers['black'] is not None


def test_round_trip_preserves_perspective_side_in_hvh():
    g = Game()
    g.apply_mode_selection(side='black')   # legacy: human plays black in HvH
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.user_side == 'black'
    assert g2._perspective_side == 'black'


def _take_random_turn(g):
    """Drive one turn via a helper AIController (the simplest way to
    apply a legal turn in tests)."""
    helper = AIController(g.next_player)
    helper.take_turn(g)


def test_round_trip_after_a_few_turns_preserves_board_state():
    random.seed(331)
    g = Game()
    for _ in range(4):
        _take_random_turn(g)
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    # Board state hash equality is the strongest check for "same position".
    assert g2.board.get_state_hash(g2.next_player) == \
        g.board.get_state_hash(g.next_player)
    assert g2.board.turn_number == g.board.turn_number


def test_round_trip_preserves_undo_redo_history():
    """A loaded game must support undo to the same depth as the original."""
    random.seed(337)
    g = Game()
    for _ in range(5):
        _take_random_turn(g)
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    # Both should report the same can_undo depth.
    assert g2.can_undo() == g.can_undo()
    # Undo on the loaded game should land on the same turn_number as
    # undo on the original.
    g.undo()
    g2.undo()
    assert g2.board.turn_number == g.board.turn_number
    assert g2.next_player == g.next_player


def test_round_trip_preserves_redo_stack_after_undo():
    random.seed(347)
    g = Game()
    for _ in range(4):
        _take_random_turn(g)
    g.undo()
    g.undo()
    assert g.can_redo() is True
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.can_redo() == g.can_redo()
    g.redo()
    g2.redo()
    assert g2.board.turn_number == g.board.turn_number


def test_load_from_text_replaces_current_game_state_in_place():
    """load_from_text mutates the existing game in place so callers
    holding references (main.py's `board`, `dragger`) stay valid.
    Returns True on success."""
    random.seed(353)
    g_source = Game()
    for _ in range(3):
        _take_random_turn(g_source)
    text = g_source.serialize_to_text()

    g = Game()
    original_board_id = id(g.board)
    ok = g.load_from_text(text)
    assert ok is True
    # board object identity preserved (in-place mutation).
    assert id(g.board) == original_board_id
    # state matches source
    assert g.board.turn_number == g_source.board.turn_number
    assert g.next_player == g_source.next_player


def test_load_from_text_returns_false_on_garbage_input():
    g = Game()
    ok = g.load_from_text('not a real save file')
    assert ok is False
    # Game state untouched.
    assert g.board.turn_number == 0


def test_load_from_text_returns_false_on_empty_input():
    g = Game()
    ok = g.load_from_text('')
    assert ok is False


def test_deserialize_from_text_raises_on_garbage():
    with pytest.raises(Exception):
        Game.deserialize_from_text('not a save')


def test_round_trip_preserves_winner_state():
    """Winner string is preserved across round-trip."""
    g = Game()
    g.winner = 'white'
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.winner == 'white'


# ===========================================================================
# Section 3 — clipboard interaction (via mockable provider)
# ===========================================================================

def test_clipboard_provider_can_be_monkeypatched(monkeypatch):
    """The dialog's Copy button calls Game._copy_to_clipboard; that
    helper must be overridable for tests."""
    captured = {}
    def fake_copy(text):
        captured['text'] = text
        return True
    monkeypatch.setattr(Game, '_copy_to_clipboard', staticmethod(fake_copy))
    g = Game()
    ok = Game._copy_to_clipboard(g.serialize_to_text())
    assert ok is True
    assert 'text' in captured
    assert len(captured['text']) > 0


def test_read_clipboard_can_be_monkeypatched(monkeypatch):
    """Symmetric for the Load button: Game._read_clipboard is the
    indirection."""
    monkeypatch.setattr(
        Game, '_read_clipboard', staticmethod(lambda: 'paste-result'))
    assert Game._read_clipboard() == 'paste-result'


def test_copy_action_emits_serialized_text(monkeypatch):
    """Wrapping behavior: Game.copy_to_clipboard_action serializes the
    current game and pushes it to the clipboard provider, returning
    True on success."""
    captured = {}
    def fake_copy(text):
        captured['text'] = text
        return True
    monkeypatch.setattr(Game, '_copy_to_clipboard', staticmethod(fake_copy))
    g = Game()
    ok = g.copy_to_clipboard_action()
    assert ok is True
    # The text pushed was a serialization that the same game can read back.
    g2 = Game.deserialize_from_text(captured['text'])
    assert g2.next_player == g.next_player


def test_load_action_reads_from_clipboard_and_loads(monkeypatch):
    """Game.load_from_clipboard_action calls _read_clipboard and feeds
    the text to load_from_text. Returns True on success."""
    random.seed(361)
    g_source = Game()
    for _ in range(3):
        _take_random_turn(g_source)
    serialized = g_source.serialize_to_text()
    monkeypatch.setattr(
        Game, '_read_clipboard', staticmethod(lambda: serialized))
    g = Game()
    ok = g.load_from_clipboard_action()
    assert ok is True
    assert g.board.turn_number == g_source.board.turn_number


def test_load_action_returns_false_on_empty_clipboard(monkeypatch):
    monkeypatch.setattr(Game, '_read_clipboard', staticmethod(lambda: None))
    g = Game()
    ok = g.load_from_clipboard_action()
    assert ok is False


def test_load_action_returns_false_on_bad_clipboard_content(monkeypatch):
    monkeypatch.setattr(
        Game, '_read_clipboard', staticmethod(lambda: 'not a save'))
    g = Game()
    ok = g.load_from_clipboard_action()
    assert ok is False
    # Game state untouched.
    assert g.board.turn_number == 0


# ===========================================================================
# Section 4 — undo/redo in CvC require the dialog to be open
# ===========================================================================

def test_cvc_undo_works_when_dialog_open():
    """In CvC, the user pauses (opens dialog), then undoes. The dialog-
    open state must NOT block undo — the user explicitly opened the
    dialog FOR the undo."""
    random.seed(367)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    # advance a few turns via the per-side controllers
    for _ in range(3):
        g.current_ai_controller().take_turn(g)
    assert g.board.turn_number == 3
    g.open_pgn_dialog()
    # can_undo's intermediate-state guard excludes the dialog
    # (otherwise undo would never work from the paused state).
    assert g.can_undo() is True
    assert g.undo() is True
    assert g.board.turn_number == 2


def test_cvc_redo_works_when_dialog_open():
    random.seed(373)
    g = Game()
    g.apply_mode_selection(white_player='random', black_player='random')
    for _ in range(4):
        g.current_ai_controller().take_turn(g)
    g.undo()
    assert g.board.turn_number == 3
    g.open_pgn_dialog()
    assert g.can_redo() is True
    assert g.redo() is True
    assert g.board.turn_number == 4


# ===========================================================================
# Section 5 — robustness sanity checks
# ===========================================================================

def test_serialized_text_format_is_stable_across_two_calls():
    """Same game serialized twice in a row should produce the same text
    (deterministic encoding — no random salting, no timestamps in the
    encoded payload)."""
    g = Game()
    a = g.serialize_to_text()
    b = g.serialize_to_text()
    assert a == b


def test_load_into_running_cvc_game_takes_effect_immediately():
    """A loaded game's mode is honoured by current_ai_controller right
    after load (no manual _refresh_ai call required)."""
    g_source = Game()
    g_source.apply_mode_selection(
        white_player='random', black_player='random')
    text = g_source.serialize_to_text()

    g = Game()
    g.load_from_text(text)
    assert g.current_ai_controller() is not None
    assert g.current_ai_controller().color == 'white'


def test_loading_a_finished_game_preserves_winner():
    g_source = Game()
    g_source.winner = 'black'
    text = g_source.serialize_to_text()
    g = Game()
    g.load_from_text(text)
    assert g.winner == 'black'


def test_dialog_open_flag_is_not_persisted_in_save():
    """Save the game with the dialog open; loaded game should NOT come
    back with the dialog open (UI state isn't part of the game state)."""
    g = Game()
    g.open_pgn_dialog()
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.pgn_dialog_open is False
