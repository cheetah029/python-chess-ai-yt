"""Scrolling must not click the board (#335).

pygame 2 reports each tick of a scroll wheel or a two-finger trackpad
scroll as a MOUSEWHEEL event AND as a MOUSEBUTTONDOWN/MOUSEBUTTONUP pair
with button 4 or 5 (6 or 7 for horizontal scrolling). The main loop
treated every button but the right one as a left click, so a scroll
gesture became a burst of rapid clicks on the square under the cursor.

These tests run the real main loop on a dummy display and feed it
scripted events, so they test what the window does, not its source.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()
pygame.font.init()

import pytest

import main as mainloop
from const import SQSIZE
from piece import Pawn


class _Stop(Exception):
    """Raised by the scripted event queue when it runs out."""


def _run(events, monkeypatch):
    """Run the main loop over `events` (one batch per frame), then stop.
    Returns the `Main` so the caller can inspect the game, and how many
    times a piece was picked up -- which is what a click on a piece does,
    even when the release puts it straight back."""
    monkeypatch.setattr(mainloop.Main, '_keep_player_version',
                        staticmethod(lambda: None))
    window = mainloop.Main()
    pickups = []
    drag_piece = window.game.dragger.drag_piece

    def counted(piece):
        pickups.append(piece)
        return drag_piece(piece)

    window.game.dragger.drag_piece = counted
    batches = [[event] for event in events]

    def scripted(*args, **kwargs):
        if not batches:
            raise _Stop
        return batches.pop(0)

    monkeypatch.setattr(pygame.event, 'get', scripted)
    with pytest.raises(_Stop):
        window.mainloop()
    return window, len(pickups)


def _e2():
    """Screen position of White's e-pawn, which can move at the start."""
    row, col = 6, 4
    return (col * SQSIZE + SQSIZE // 2, row * SQSIZE + SQSIZE // 2)


def _button(kind, button):
    return pygame.event.Event(kind, pos=_e2(), button=button)


def test_a_left_click_picks_up_the_piece(monkeypatch):
    """THE HARNESS CAN SEE A CLICK: pressing the left button on a White
    pawn picks it up. Without this, the scroll test below would pass
    for any loop that ignored every event."""
    window, pickups = _run([_button(pygame.MOUSEBUTTONDOWN, 1)],
                           monkeypatch)
    dragger = window.game.dragger
    assert pickups == 1
    assert dragger.dragging
    assert isinstance(dragger.piece, Pawn)


@pytest.mark.parametrize('button', [4, 5, 6, 7])
def test_scroll_ticks_do_not_click(monkeypatch, button):
    """Two-finger scrolling over a White pawn: several ticks, each a
    button press and release from a scroll button, with the MOUSEWHEEL
    event pygame sends alongside. Nothing may be picked up, even for a
    moment, and nothing may move. (Before the fix each tick picked the
    pawn up and the release put it back, so the board looked unchanged
    afterwards; only counting the pick-ups sees the clicks.)"""
    wheel = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False)
    events = []
    for _ in range(5):
        events += [wheel, _button(pygame.MOUSEBUTTONDOWN, button),
                   _button(pygame.MOUSEBUTTONUP, button)]
    window, pickups = _run(events, monkeypatch)
    assert pickups == 0
    assert not window.game.dragger.dragging
    assert window.game.board.turn_number == 0
    assert isinstance(window.game.board.squares[6][4].piece, Pawn)


def test_only_the_left_and_right_buttons_click():
    """The rule itself: buttons 1 and 3 click; every other mouse button
    event is ignored, and other events are left to their handlers."""
    for button in (1, 3):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            assert not mainloop.is_scroll_click(_button(kind, button))
    for button in (2, 4, 5, 6, 7, 8, 9):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            assert mainloop.is_scroll_click(_button(kind, button))
    motion = pygame.event.Event(pygame.MOUSEMOTION, pos=_e2(), rel=(0, 0),
                                buttons=(0, 0, 0))
    assert not mainloop.is_scroll_click(motion)
