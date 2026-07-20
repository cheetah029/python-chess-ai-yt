"""Round-trip tests for royal chess notation and the V3 save format
(user request 2026-07-20): the save records only per-turn differences
in a readable movetext (like a standard chess PGN), preserves the full
undo/redo timeline plus the current position (CurrentTurn header near
the top), self-verifies on save, and falls back to the V2 container
when a game cannot be represented (e.g. FEN-loaded starting position).
V2 and legacy V1 saves must remain loadable.
"""

import os
import random
import sys

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

import pytest

import notation
from notation import (NotationError, parse_square, parse_token, square_name)
from game import Game, _SAVE_V2_BEGIN, _SAVE_V3_BEGIN
from ai_controller import AIController


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


# ---- helpers -------------------------------------------------------------

_APPLIER = None


def _applier():
    """A single AIController used purely as the turn enumerator +
    applier (its _apply_turn reads game.next_player, so one instance
    drives both colors)."""
    global _APPLIER
    if _APPLIER is None:
        _APPLIER = AIController('white')
    return _APPLIER


def _play_random(g, n_turns, seed):
    """Apply up to n_turns random legal turns to g (stops early on a
    winner). Deterministic under the seed."""
    rng = random.Random(seed)
    ai = _applier()
    for _ in range(n_turns):
        if g.winner is not None:
            break
        turns = ai.legal_turns(g)
        if not turns:
            break
        ai._apply_turn(g, rng.choice(turns))
    return g


def _play_greedy(g, prefer, max_turns):
    """Apply turns preferring the first matching predicate in
    `prefer` (list of functions Turn -> bool); falls back to the
    first legal turn. Deterministic. Returns the set of turn-type
    labels seen."""
    ai = _applier()
    seen = set()
    for _ in range(max_turns):
        if g.winner is not None:
            break
        turns = ai.legal_turns(g)
        if not turns:
            break
        chosen = None
        for pred in prefer:
            for t in turns:
                if pred(t):
                    chosen = t
                    break
            if chosen is not None:
                break
        if chosen is None:
            chosen = turns[0]
        seen.add(chosen.turn_type)
        if chosen.promo_choice is not None:
            seen.add('promotion')
        if chosen.jump_choice is not None:
            seen.add('jump_capture')
        ai._apply_turn(g, chosen)
    return seen


def _timeline(g):
    return g._history + list(reversed(g._redo_stack))


def _state_key(snap):
    return (snap['board'].get_state_hash(snap['next_player']),
            snap['next_player'], snap['winner'],
            snap['board'].turn_number)


def _assert_roundtrip(g):
    """Serialize g as V3, load into a fresh Game, and require the
    current position AND the entire undo/redo timeline to match.
    Returns the save text."""
    text = g.serialize_to_text()
    assert _SAVE_V3_BEGIN in text, 'expected a V3 royal-notation save'
    g2 = Game()
    assert g2.load_from_text(text) is True
    # Current position.
    assert g2.next_player == g.next_player
    assert g2.winner == g.winner
    assert g2.board.turn_number == g.board.turn_number
    assert (g2.board.get_state_hash(g2.next_player)
            == g.board.get_state_hash(g.next_player))
    # Full timeline, both stacks.
    assert len(g2._history) == len(g._history)
    assert len(g2._redo_stack) == len(g._redo_stack)
    for s1, s2 in zip(_timeline(g), _timeline(g2)):
        assert _state_key(s1) == _state_key(s2)
    return text


# ---- notation primitives -------------------------------------------------

def test_square_name_roundtrip():
    assert square_name(0, 0) == 'a8'
    assert square_name(7, 0) == 'a1'
    assert square_name(0, 7) == 'h8'
    assert square_name(7, 7) == 'h1'
    for r in range(8):
        for c in range(8):
            assert parse_square(square_name(r, c)) == (r, c)


def test_parse_token_shapes():
    t = parse_token('Pe2-e3')
    assert t['kind'] == 'spatial' and not t['manip'] and not t['capture']
    assert t['from_sq'] == parse_square('e2')
    assert t['to_sq'] == parse_square('e3')

    t = parse_token('>Pd7xd6')
    assert t['manip'] and t['capture']

    t = parse_token("R'a4xa7")
    assert t['letter'] == 'R' and t['transformed'] and t['capture']

    t = parse_token('Qd4=B')
    assert t['kind'] == 'transform' and t['target'] == 'bishop'
    assert t['sq'] == parse_square('d4')

    t = parse_token("B'f5=Q")
    assert t['kind'] == 'transform' and t['target'] == 'queen'

    t = parse_token('Nc3-e4j')
    assert t['jumpcap'] and not t['capture']

    t = parse_token('O**-d4')
    assert t['letter'] == 'O' and t['from_sq'] is None
    assert t['to_sq'] == parse_square('d4')

    t = parse_token('Pe7-e8=N')
    assert t['promo'] == 'knight'

    t = parse_token('>Pe2-e1=Q')
    assert t['manip'] and t['promo'] == 'queen'

    # '#' marks a game-ending turn; it can follow any token shape.
    t = parse_token('Qa2xa1#')
    assert t['terminal'] and t['capture']
    t = parse_token('Nc3-e3j#')
    assert t['terminal'] and t['jumpcap']
    t = parse_token('Qd4=R#')
    assert t['terminal'] and t['kind'] == 'transform'
    assert parse_token('Pe2-e3')['terminal'] is False

    for bad in ('Ze2-e3', 'Pe2e3', 'Pe2-e9', 'Qd4=X', 'Pe2-e3jx',
                '>Qd4=B', 'Pe2-e3#j', 'Pe2#-e3'):
        with pytest.raises(NotationError):
            parse_token(bad)


def test_movetext_numbering_roundtrip():
    tokens = ['Pe2-e3', 'Pd7-d6', 'Nb1-b3']
    text = notation.tokens_to_movetext(tokens)
    assert text.splitlines()[0] == '1. Pe2-e3 Pd7-d6'
    assert notation.movetext_to_tokens(text) == tokens


# ---- game round-trips ----------------------------------------------------

def test_random_game_roundtrip():
    g = _play_random(Game(), 40, seed=11)
    assert g.board.turn_number > 20    # setup sanity
    _assert_roundtrip(g)


def test_random_game_roundtrip_second_seed():
    g = _play_random(Game(), 60, seed=23)
    _assert_roundtrip(g)


def test_full_game_with_winner_roundtrip():
    g = _play_random(Game(), 2000, seed=5)
    assert g.winner is not None, 'seed expected to reach a decisive end'
    text = _assert_roundtrip(g)
    assert f'Winner: {g.winner}' in text
    # The game-ending turn carries the '#' marker — and only that one.
    movetext = text[text.find(_SAVE_V3_BEGIN) + len(_SAVE_V3_BEGIN):
                    text.find('___VARIANT_SAVE_V3_END___')]
    tokens = notation.movetext_to_tokens(movetext)
    assert tokens[-1].endswith('#')
    assert not any(t.endswith('#') for t in tokens[:-1])


def test_unfinished_game_has_no_terminal_marker():
    g = _play_random(Game(), 20, seed=13)
    assert g.winner is None
    text = _assert_roundtrip(g)
    assert '#' not in text[text.find(_SAVE_V3_BEGIN):]


def test_mid_timeline_current_turn_roundtrip():
    """Undo into the middle of the game, save, load: the loaded game
    shows the same mid-timeline position and the undone turns remain
    redoable — the CurrentTurn header near the top carries this."""
    g = _play_random(Game(), 30, seed=31)
    for _ in range(3):
        assert g.undo() is True
    current = len(g._history) - 1
    text = _assert_roundtrip(g)
    assert f'CurrentTurn: {current}' in text
    header = text[:text.find(_SAVE_V3_BEGIN)]
    assert 'CurrentTurn:' in header    # in the stats block, not movetext
    # Redo still works on the loaded game.
    g2 = Game()
    g2.load_from_text(text)
    assert g2.can_redo()
    depth = len(g2._history)
    assert g2.redo() is True
    assert len(g2._history) == depth + 1


def test_turn_type_coverage_roundtrip():
    """Greedy game exercising the action turn types (manipulation,
    transformation, boulder) — every token shape must survive the
    round trip."""
    g = Game()
    seen = _play_greedy(
        g,
        prefer=[
            lambda t: t.turn_type == 'transformation',
            lambda t: t.turn_type == 'manipulation',
            lambda t: t.turn_type == 'boulder',
        ],
        max_turns=60,
    )
    assert 'boulder' in seen
    assert 'manipulation' in seen
    assert 'transformation' in seen or 'move' in seen
    _assert_roundtrip(g)


def test_promotion_roundtrip():
    """Greedy pawn-pushing game reaching a promotion; the '=' token
    must survive the round trip."""
    g = Game()
    seen = _play_greedy(
        g,
        prefer=[
            lambda t: t.promo_choice is not None,
            lambda t: (t.turn_type == 'move'
                       and type(t.piece).__name__ == 'Pawn'),
        ],
        max_turns=120,
    )
    text = _assert_roundtrip(g)
    if 'promotion' in seen:
        assert '=' in text[text.find(_SAVE_V3_BEGIN):]


def test_jump_capture_roundtrip():
    """Greedy knight-heavy game; accepted jump-captures ('j' tokens)
    must survive the round trip when they occur."""
    g = Game()
    seen = _play_greedy(
        g,
        prefer=[
            lambda t: t.jump_choice is not None,
            lambda t: (t.turn_type == 'move'
                       and type(t.piece).__name__ == 'Knight'),
        ],
        max_turns=80,
    )
    text = _assert_roundtrip(g)
    if 'jump_capture' in seen:
        movetext = text[text.find(_SAVE_V3_BEGIN) + len(_SAVE_V3_BEGIN):
                        text.find('___VARIANT_SAVE_V3_END___')]
        assert any(tok.endswith('j')
                   for tok in notation.movetext_to_tokens(movetext))


# ---- back-compat + fallback ---------------------------------------------

def test_v2_container_still_loads():
    g = _play_random(Game(), 20, seed=41)
    text = g._serialize_v2()
    assert _SAVE_V2_BEGIN in text
    g2 = Game()
    assert g2.load_from_text(text) is True
    assert (g2.board.get_state_hash(g2.next_player)
            == g.board.get_state_hash(g.next_player))
    assert len(g2._history) == len(g._history)


def test_fen_started_game_serializes_v3_with_startfen():
    """A game begun from a loaded FEN now serializes as V3 with a
    StartFEN header (the counterpart of standard chess's
    [SetUp]/[FEN] PGN tags): the loader replays the movetext from
    that position instead of the standard setup."""
    src = _play_random(Game(), 12, seed=51)
    fen = src.to_fen()
    g = Game()
    assert g.load_from_fen(fen) is True
    _play_random(g, 6, seed=52)
    text = _assert_roundtrip(g)
    header = text[:text.find(_SAVE_V3_BEGIN)]
    assert 'StartFEN:' in header


def test_fen_started_game_mid_timeline_roundtrip():
    """Undo/redo positioning (CurrentTurn) works for FEN-started
    games too."""
    src = _play_random(Game(), 10, seed=53)
    g = Game()
    assert g.load_from_fen(src.to_fen()) is True
    _play_random(g, 8, seed=54)
    for _ in range(2):
        assert g.undo() is True
    text = _assert_roundtrip(g)
    g2 = Game()
    assert g2.load_from_text(text) is True
    assert g2.can_redo()
    assert g2.redo() is True


def test_non_fen_expressible_bottom_falls_back_to_v2():
    """A timeline whose bottom state carries flags the FEN summary
    cannot express (here: a manipulation freeze) must still fall
    back to the V2 container — the self-verify rejects the FEN
    reconstruction via the state hash."""
    g = Game()
    seen = _play_greedy(
        g, prefer=[lambda t: t.turn_type == 'manipulation'],
        max_turns=40)
    assert 'manipulation' in seen    # setup sanity
    frozen_at = None
    for i, snap in enumerate(g._history):
        board = snap['board']
        if any(getattr(board.squares[r][c].piece, 'moved_by_queen', False)
               for r in range(8) for c in range(8)
               if board.squares[r][c].piece is not None):
            frozen_at = i
            break
    assert frozen_at is not None and frozen_at > 0
    # Truncate the timeline so the frozen state becomes the bottom.
    g._history = g._history[frozen_at:]
    g._redo_stack = []
    text = g.serialize_to_text()
    assert _SAVE_V3_BEGIN not in text
    assert _SAVE_V2_BEGIN in text
    g2 = Game()
    assert g2.load_from_text(text) is True
    assert (g2.board.get_state_hash(g2.next_player)
            == g.board.get_state_hash(g.next_player))


def test_v3_much_smaller_than_v2():
    g = _play_random(Game(), 120, seed=61)
    v3 = g.serialize_to_text()
    v2 = g._serialize_v2()
    assert _SAVE_V3_BEGIN in v3
    assert len(v3) < len(v2) / 3, (
        f'V3 ({len(v3)}B) should be far smaller than V2 ({len(v2)}B)')


def test_perspective_and_live_winner_headers_roundtrip():
    """V3 must not lose the two payload fields that are not derivable
    from the movetext: the HvH perspective side and a live winner
    state (normally replay-derived, but authoritative in the header)."""
    g = _play_random(Game(), 8, seed=81)
    g.apply_mode_selection(side='black')
    g.winner = 'white'
    text = g.serialize_to_text()
    assert 'Perspective: black' in text
    assert 'Winner: white' in text
    g2 = Game.deserialize_from_text(text)
    assert g2.user_side == 'black'
    assert g2.winner == 'white'


def test_corrupt_movetext_fails_cleanly():
    g = _play_random(Game(), 10, seed=71)
    text = g.serialize_to_text()
    corrupted = text.replace('\n1. ', '\n1. Zz9-z9 ', 1)
    g2 = Game()
    pre = g2.board.get_state_hash(g2.next_player)
    assert g2.load_from_text(corrupted) is False
    assert g2.board.get_state_hash(g2.next_player) == pre  # untouched
