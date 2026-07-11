"""Tests for the compressed (V2) game-save format.

User report (2026-06-15): the full-game save ("PGN") was extremely
long — ~1.1 MB for a 60-turn game — impractical to keep in a file.

Root cause: the payload pickles the ENTIRE undo history (one full
deep-copied Board per turn) and then base64-encodes the raw pickle
(+33%% on top). Pickled board snapshots are highly repetitive, so
zlib compression collapses them dramatically (~40x measured).

V2 format:

    === Chess Variant Save (v2 ruleset) ===
    ...human-readable header (unchanged)...

    ___VARIANT_SAVE_V2_BEGIN___
    <base64 of zlib-compressed pickle, wrapped at 76 chars/line>
    ___VARIANT_SAVE_V2_END___

Requirements pinned here:
  - serialize_to_text emits V2 (compressed).
  - V2 saves round-trip perfectly (same board, history, mode).
  - LEGACY V1 saves (uncompressed) still load — backward compat.
  - The compressed save is dramatically smaller than the V1
    encoding of the same payload.
  - The base64 body is line-wrapped (no single mega-line), which
    text editors and diff tools handle gracefully.
"""

import base64
import os
import pickle
import random
import sys
import zlib

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

from game import Game
from ai_controller import AIController


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


def _play(g, n):
    for _ in range(n):
        if g.winner is not None:
            return
        AIController(g.next_player).take_turn(g)


# ---- format ---------------------------------------------------------------

def test_serialize_emits_v2_markers():
    g = Game()
    text = g.serialize_to_text()
    assert '___VARIANT_SAVE_V2_BEGIN___' in text
    assert '___VARIANT_SAVE_V2_END___' in text
    # V1 markers must NOT appear in fresh saves.
    assert '___VARIANT_SAVE_V1_BEGIN___' not in text


def test_v2_payload_is_zlib_compressed():
    """The body between the V2 markers must decode as
    base64 -> zlib -> pickle dict."""
    g = Game()
    text = g.serialize_to_text()
    begin = text.find('___VARIANT_SAVE_V2_BEGIN___') + \
        len('___VARIANT_SAVE_V2_BEGIN___')
    end = text.find('___VARIANT_SAVE_V2_END___')
    body = text[begin:end].strip()
    payload = pickle.loads(zlib.decompress(base64.b64decode(body)))
    assert isinstance(payload, dict)
    assert 'board' in payload
    assert 'next_player' in payload


def test_v2_body_is_line_wrapped():
    """No single mega-line: after some played turns the base64 body
    must span multiple lines, each of bounded width."""
    random.seed(11)
    g = Game()
    _play(g, 8)
    text = g.serialize_to_text()
    begin = text.find('___VARIANT_SAVE_V2_BEGIN___')
    end = text.find('___VARIANT_SAVE_V2_END___')
    body_lines = [ln for ln in text[begin:end].splitlines()[1:]
                  if ln.strip()]
    assert len(body_lines) > 1, 'body should wrap across lines'
    assert all(len(ln) <= 80 for ln in body_lines), (
        f'body lines must stay within ~76-80 chars; got max '
        f'{max(len(ln) for ln in body_lines)}')


# ---- size -----------------------------------------------------------------

def test_v2_save_dramatically_smaller_than_v1_encoding():
    """The V2 save of a mid-length game must be at least 10x smaller
    than the V1 encoding (plain base64 of the uncompressed pickle)
    of the same payload. Measured real-world factor is ~40x; 10x is
    the conservative regression floor."""
    random.seed(13)
    g = Game()
    _play(g, 25)
    v2_text = g.serialize_to_text()
    # Reconstruct what V1 would have produced for the same payload.
    begin = v2_text.find('___VARIANT_SAVE_V2_BEGIN___') + \
        len('___VARIANT_SAVE_V2_BEGIN___')
    end = v2_text.find('___VARIANT_SAVE_V2_END___')
    pickled = zlib.decompress(
        base64.b64decode(v2_text[begin:end].strip()))
    v1_size = len(base64.b64encode(pickled))
    assert len(v2_text) * 10 < v1_size, (
        f'V2 save ({len(v2_text):,}) should be >=10x smaller than '
        f'the V1 encoding ({v1_size:,})')


# ---- round trip -----------------------------------------------------------

def test_v2_round_trip_preserves_board_and_history():
    random.seed(17)
    g = Game()
    _play(g, 12)
    text = g.serialize_to_text()
    g2 = Game.deserialize_from_text(text)
    assert g2.board.turn_number == g.board.turn_number
    assert g2.next_player == g.next_player
    assert g2.board.get_state_hash(g2.next_player) == \
        g.board.get_state_hash(g.next_player)
    assert g2.can_undo() == g.can_undo()
    # Undo works to the same depth.
    g.undo()
    g2.undo()
    assert g2.board.turn_number == g.board.turn_number


def test_v2_load_from_text_in_place():
    random.seed(19)
    src = Game()
    _play(src, 6)
    text = src.serialize_to_text()
    g = Game()
    board_id = id(g.board)
    assert g.load_from_text(text) is True
    assert id(g.board) == board_id     # in-place mutation contract
    assert g.board.turn_number == src.board.turn_number


# ---- backward compatibility -----------------------------------------------

def _make_v1_text(g):
    """Produce a LEGACY V1 save (uncompressed single-line base64) for
    backward-compat testing — replicating the old writer."""
    payload = {
        'version': 1,
        'board': g.board,
        'next_player': g.next_player,
        'winner': g.winner,
        'white_player': g.white_player,
        'black_player': g.black_player,
        '_perspective_side': g._perspective_side,
        '_history': g._history,
        '_redo_stack': g._redo_stack,
    }
    encoded = base64.b64encode(
        pickle.dumps(payload, protocol=4)).decode('ascii')
    return ('=== Chess Variant Save (v2 ruleset) ===\n'
            f'Mode: {g.mode}\n\n'
            '___VARIANT_SAVE_V1_BEGIN___\n'
            + encoded + '\n'
            '___VARIANT_SAVE_V1_END___\n')


def test_legacy_v1_save_still_loads():
    random.seed(23)
    src = Game()
    _play(src, 5)
    v1_text = _make_v1_text(src)
    g2 = Game.deserialize_from_text(v1_text)
    assert g2.board.turn_number == src.board.turn_number
    assert g2.next_player == src.next_player


def test_legacy_v1_load_from_text_in_place():
    src = Game()
    v1_text = _make_v1_text(src)
    g = Game()
    assert g.load_from_text(v1_text) is True


# ---- error handling stays intact -------------------------------------------

def test_garbage_still_rejected():
    g = Game()
    assert g.load_from_text('definitely not a save') is False
    assert g.load_from_text('') is False


def test_corrupt_v2_body_rejected_without_mutation():
    g_src = Game()
    text = g_src.serialize_to_text()
    corrupted = text.replace('___VARIANT_SAVE_V2_BEGIN___\n',
                             '___VARIANT_SAVE_V2_BEGIN___\n!!notb64!!')
    g = Game()
    assert g.load_from_text(corrupted) is False
    assert g.board.turn_number == 0
