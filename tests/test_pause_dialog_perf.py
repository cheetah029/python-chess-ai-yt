"""Performance regression tests for the pause dialog (issue #164):
the dialog preview must not run the V3 save's self-verifying replay
(it renders every frame), and must cache across unchanged frames.
The Copy button keeps the fully verified serialization.
"""

import os
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
from game import Game
from ai_controller import AIController


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()


def _play(g, n, seed):
    import random
    rng = random.Random(seed)
    ai = AIController('white')
    for _ in range(n):
        if g.winner is not None:
            break
        turns = ai.legal_turns(g)
        if not turns:
            break
        ai._apply_turn(g, rng.choice(turns))
    return g


def test_unverified_serialize_matches_verified():
    """The fast path must produce byte-identical output for a normal
    game — only the safety re-check is skipped."""
    g = _play(Game(), 24, seed=7)
    assert g.serialize_to_text(verify=False) == g.serialize_to_text()


def test_preview_does_not_replay(monkeypatch):
    """The preview path must never run the self-verify replay:
    apply_token exploding must not affect it (while the verified
    path DOES replay)."""
    g = _play(Game(), 12, seed=9)

    def boom(*a, **k):
        raise AssertionError('preview must not replay the game')
    monkeypatch.setattr(notation, 'apply_token', boom)
    lines = g._pgn_dialog_preview_lines()
    assert lines, 'preview still renders without the replay'
    # The verified path replays -> hits the explosive stub -> falls
    # back to the V2 container (self-verify failure handling).
    text = g.serialize_to_text()
    assert '___VARIANT_SAVE_V2_BEGIN___' in text


def test_preview_cached_across_unchanged_frames(monkeypatch):
    g = _play(Game(), 12, seed=11)
    calls = {'n': 0}
    real = Game.serialize_to_text

    def counting(self, verify=True):
        calls['n'] += 1
        return real(self, verify=verify)
    monkeypatch.setattr(Game, 'serialize_to_text', counting)
    first = g._pgn_dialog_preview_lines()
    second = g._pgn_dialog_preview_lines()
    assert first == second
    assert calls['n'] == 1, 'unchanged frames must render from cache'
    # State change (undo) invalidates the cache exactly once.
    assert g.undo() is True
    g._pgn_dialog_preview_lines()
    g._pgn_dialog_preview_lines()
    assert calls['n'] == 2


def test_copy_still_fully_verified(monkeypatch):
    """The Copy action keeps the verified serialization: when the
    replay is broken, Copy falls back to V2 (proving it verified)."""
    g = _play(Game(), 10, seed=13)
    captured = {}
    monkeypatch.setattr(Game, '_copy_to_clipboard',
                        staticmethod(lambda t: captured.update(t=t) or True))

    def boom(*a, **k):
        raise AssertionError('verify replay ran (expected)')
    monkeypatch.setattr(notation, 'apply_token', boom)
    assert g.copy_to_clipboard_action()
    assert '___VARIANT_SAVE_V2_BEGIN___' in captured['t'], (
        'Copy must use the VERIFIED path (broken replay => V2 fallback)')
