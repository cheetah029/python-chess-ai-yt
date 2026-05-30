"""Tests for the clipboard fallback chain — fixing the reported
"Copy failed (clipboard unavailable)" UI on macOS.

Root cause: the previous helper tried (a) pyperclip — not installed
in this environment — then (b) pygame.scrap — flaky on macOS. Both
failed and the user saw the failure status.

Fix: insert a platform-native CLI fallback (pbcopy on macOS,
xclip/xsel on Linux, clip.exe on Windows) BEFORE pygame.scrap.
pbcopy is shipped with macOS at /usr/bin/pbcopy and always works for
text. The chain becomes:

    pyperclip (if installed) -> platform CLI -> pygame.scrap

If all three fail, the action returns False and the dialog shows
"Copy failed".

The helpers are factored so each can be tested in isolation:

    Game._copy_via_pyperclip(text)
    Game._copy_via_cli_tool(text, platform=...)
    Game._copy_via_pygame_scrap(text)
    Game._default_copy_to_clipboard(text)     # orchestrator

Mirror trio for read:

    Game._read_via_pyperclip()
    Game._read_via_cli_tool(platform=...)
    Game._read_via_pygame_scrap()
    Game._default_read_clipboard()
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import subprocess
import pytest

import pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

import game as game_module
from game import Game


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


# ---- helper presence ------------------------------------------------------

def test_copy_helpers_exist():
    """The three layered helpers must be importable from game."""
    for name in ('_copy_via_pyperclip', '_copy_via_cli_tool',
                 '_copy_via_pygame_scrap', '_default_copy_to_clipboard'):
        assert hasattr(game_module, name), (
            f"game module missing helper {name}")


def test_read_helpers_exist():
    for name in ('_read_via_pyperclip', '_read_via_cli_tool',
                 '_read_via_pygame_scrap', '_default_read_clipboard'):
        assert hasattr(game_module, name), (
            f"game module missing helper {name}")


# ---- CLI-tool fallback (the new piece) ------------------------------------

def test_cli_copy_uses_pbcopy_on_darwin(monkeypatch):
    captured = {}
    class FakeCompleted:
        def __init__(self):
            self.returncode = 0
    def fake_run(cmd, input=None, text=None, timeout=None, check=None):
        captured['cmd'] = cmd
        captured['input'] = input
        return FakeCompleted()
    monkeypatch.setattr(game_module.subprocess, 'run', fake_run)
    monkeypatch.setattr(game_module.shutil, 'which', lambda _: '/usr/bin/pbcopy')
    ok = game_module._copy_via_cli_tool('hello world', platform='darwin')
    assert ok is True
    assert captured['cmd'][0] == 'pbcopy'
    assert captured['input'] == 'hello world'


def test_cli_copy_uses_xclip_on_linux(monkeypatch):
    captured = {}
    class FakeCompleted:
        def __init__(self):
            self.returncode = 0
    def fake_run(cmd, input=None, text=None, timeout=None, check=None):
        captured['cmd'] = cmd
        captured['input'] = input
        return FakeCompleted()
    monkeypatch.setattr(game_module.subprocess, 'run', fake_run)
    # Simulate xclip available, xsel not.
    def fake_which(cmd):
        return '/usr/bin/xclip' if cmd == 'xclip' else None
    monkeypatch.setattr(game_module.shutil, 'which', fake_which)
    ok = game_module._copy_via_cli_tool('data', platform='linux')
    assert ok is True
    assert captured['cmd'][0] == 'xclip'


def test_cli_copy_falls_back_to_xsel_when_xclip_missing(monkeypatch):
    captured = {}
    class FakeCompleted:
        def __init__(self):
            self.returncode = 0
    def fake_run(cmd, input=None, text=None, timeout=None, check=None):
        captured['cmd'] = cmd
        return FakeCompleted()
    monkeypatch.setattr(game_module.subprocess, 'run', fake_run)
    def fake_which(cmd):
        return '/usr/bin/xsel' if cmd == 'xsel' else None
    monkeypatch.setattr(game_module.shutil, 'which', fake_which)
    ok = game_module._copy_via_cli_tool('data', platform='linux')
    assert ok is True
    assert captured['cmd'][0] == 'xsel'


def test_cli_copy_uses_clip_on_windows(monkeypatch):
    captured = {}
    class FakeCompleted:
        def __init__(self):
            self.returncode = 0
    def fake_run(cmd, input=None, text=None, timeout=None, check=None):
        captured['cmd'] = cmd
        return FakeCompleted()
    monkeypatch.setattr(game_module.subprocess, 'run', fake_run)
    monkeypatch.setattr(
        game_module.shutil, 'which',
        lambda cmd: r'C:\Windows\System32\clip.exe' if cmd == 'clip' else None)
    ok = game_module._copy_via_cli_tool('data', platform='win32')
    assert ok is True
    assert captured['cmd'][0] == 'clip'


def test_cli_copy_returns_false_when_no_tool_available(monkeypatch):
    monkeypatch.setattr(game_module.shutil, 'which', lambda cmd: None)
    assert game_module._copy_via_cli_tool('x', platform='linux') is False


def test_cli_copy_returns_false_when_subprocess_raises(monkeypatch):
    def fake_run(*a, **kw):
        raise OSError('boom')
    monkeypatch.setattr(game_module.subprocess, 'run', fake_run)
    monkeypatch.setattr(
        game_module.shutil, 'which', lambda _: '/usr/bin/pbcopy')
    assert game_module._copy_via_cli_tool('x', platform='darwin') is False


def test_cli_copy_returns_false_on_nonzero_returncode(monkeypatch):
    class FakeCompleted:
        def __init__(self):
            self.returncode = 1  # failure
    monkeypatch.setattr(
        game_module.subprocess, 'run', lambda *a, **k: FakeCompleted())
    monkeypatch.setattr(
        game_module.shutil, 'which', lambda _: '/usr/bin/pbcopy')
    assert game_module._copy_via_cli_tool('x', platform='darwin') is False


def test_cli_copy_returns_false_on_unknown_platform(monkeypatch):
    # 'aix3' isn't supported — no CLI tool registered.
    assert game_module._copy_via_cli_tool('x', platform='aix3') is False


# ---- CLI-tool READ --------------------------------------------------------

def test_cli_read_uses_pbpaste_on_darwin(monkeypatch):
    captured = {}
    class FakeCompleted:
        def __init__(self):
            self.returncode = 0
            self.stdout = 'pasted!'
    def fake_run(cmd, capture_output=None, text=None, timeout=None,
                 check=None):
        captured['cmd'] = cmd
        return FakeCompleted()
    monkeypatch.setattr(game_module.subprocess, 'run', fake_run)
    monkeypatch.setattr(
        game_module.shutil, 'which', lambda _: '/usr/bin/pbpaste')
    result = game_module._read_via_cli_tool(platform='darwin')
    assert result == 'pasted!'
    assert captured['cmd'][0] == 'pbpaste'


def test_cli_read_returns_none_when_no_tool(monkeypatch):
    monkeypatch.setattr(game_module.shutil, 'which', lambda _: None)
    assert game_module._read_via_cli_tool(platform='linux') is None


def test_cli_read_returns_none_on_nonzero_returncode(monkeypatch):
    class FakeCompleted:
        def __init__(self):
            self.returncode = 1
            self.stdout = ''
    monkeypatch.setattr(
        game_module.subprocess, 'run', lambda *a, **k: FakeCompleted())
    monkeypatch.setattr(
        game_module.shutil, 'which', lambda _: '/usr/bin/pbpaste')
    assert game_module._read_via_cli_tool(platform='darwin') is None


# ---- orchestrator (fallback chain) ----------------------------------------

def test_orchestrator_uses_pyperclip_first(monkeypatch):
    """If pyperclip succeeds, the CLI / pygame.scrap helpers must
    NOT be called (avoids redundant work / shell processes)."""
    call_log = []
    monkeypatch.setattr(
        game_module, '_copy_via_pyperclip',
        lambda text: call_log.append('pyperclip') or True)
    monkeypatch.setattr(
        game_module, '_copy_via_cli_tool',
        lambda text, platform=None: call_log.append('cli') or True)
    monkeypatch.setattr(
        game_module, '_copy_via_pygame_scrap',
        lambda text: call_log.append('scrap') or True)
    ok = game_module._default_copy_to_clipboard('x')
    assert ok is True
    assert call_log == ['pyperclip']


def test_orchestrator_falls_back_to_cli_when_pyperclip_fails(monkeypatch):
    call_log = []
    monkeypatch.setattr(
        game_module, '_copy_via_pyperclip',
        lambda text: call_log.append('pyperclip') or False)
    monkeypatch.setattr(
        game_module, '_copy_via_cli_tool',
        lambda text, platform=None: call_log.append('cli') or True)
    monkeypatch.setattr(
        game_module, '_copy_via_pygame_scrap',
        lambda text: call_log.append('scrap') or True)
    ok = game_module._default_copy_to_clipboard('x')
    assert ok is True
    assert call_log == ['pyperclip', 'cli']


def test_orchestrator_falls_back_to_pygame_scrap_when_first_two_fail(
        monkeypatch):
    call_log = []
    monkeypatch.setattr(
        game_module, '_copy_via_pyperclip',
        lambda text: call_log.append('pyperclip') or False)
    monkeypatch.setattr(
        game_module, '_copy_via_cli_tool',
        lambda text, platform=None: call_log.append('cli') or False)
    monkeypatch.setattr(
        game_module, '_copy_via_pygame_scrap',
        lambda text: call_log.append('scrap') or True)
    ok = game_module._default_copy_to_clipboard('x')
    assert ok is True
    assert call_log == ['pyperclip', 'cli', 'scrap']


def test_orchestrator_returns_false_when_all_fail(monkeypatch):
    monkeypatch.setattr(
        game_module, '_copy_via_pyperclip', lambda text: False)
    monkeypatch.setattr(
        game_module, '_copy_via_cli_tool',
        lambda text, platform=None: False)
    monkeypatch.setattr(
        game_module, '_copy_via_pygame_scrap', lambda text: False)
    assert game_module._default_copy_to_clipboard('x') is False


def test_read_orchestrator_uses_pyperclip_first(monkeypatch):
    monkeypatch.setattr(
        game_module, '_read_via_pyperclip', lambda: 'from-pyperclip')
    monkeypatch.setattr(
        game_module, '_read_via_cli_tool', lambda platform=None: 'from-cli')
    assert game_module._default_read_clipboard() == 'from-pyperclip'


def test_read_orchestrator_falls_through_when_pyperclip_returns_none(
        monkeypatch):
    monkeypatch.setattr(
        game_module, '_read_via_pyperclip', lambda: None)
    monkeypatch.setattr(
        game_module, '_read_via_cli_tool', lambda platform=None: 'from-cli')
    monkeypatch.setattr(
        game_module, '_read_via_pygame_scrap', lambda: 'from-scrap')
    assert game_module._default_read_clipboard() == 'from-cli'


def test_read_orchestrator_returns_none_when_all_return_none(monkeypatch):
    monkeypatch.setattr(
        game_module, '_read_via_pyperclip', lambda: None)
    monkeypatch.setattr(
        game_module, '_read_via_cli_tool', lambda platform=None: None)
    monkeypatch.setattr(
        game_module, '_read_via_pygame_scrap', lambda: None)
    assert game_module._default_read_clipboard() is None


# ---- end-to-end regression: the user's specific bug -----------------------

def test_copy_action_succeeds_via_cli_when_pyperclip_missing(monkeypatch):
    """Regression for the screenshot: pyperclip is not installed and
    pygame.scrap is unreliable on macOS, so the OLD chain failed.
    The NEW chain must reach the CLI layer and succeed.

    We monkeypatch the three layer helpers directly (rather than the
    raw subprocess.run) so this test stays insulated from pygame's
    own subprocess use during font enumeration."""
    # Simulate pyperclip + pygame.scrap both unavailable.
    monkeypatch.setattr(
        game_module, '_copy_via_pyperclip', lambda text: False)
    monkeypatch.setattr(
        game_module, '_copy_via_pygame_scrap', lambda text: False)
    # CLI layer succeeds — the middle of the chain now exists and is
    # reachable, which is the whole point of this PR.
    captured = {}
    def fake_cli(text, platform=None):
        captured['text'] = text
        return True
    monkeypatch.setattr(game_module, '_copy_via_cli_tool', fake_cli)

    g = Game()
    Game._copy_to_clipboard = staticmethod(
        game_module._default_copy_to_clipboard)
    ok = g.copy_to_clipboard_action()
    assert ok is True
    assert captured['text'] == g.serialize_to_text()


def test_real_pbcopy_path_exists_on_this_machine():
    """Sanity: on the developer's mac, pbcopy is available — so the
    fixed chain will work in the real UI (not a mock).

    Skipped on non-darwin platforms."""
    if sys.platform != 'darwin':
        pytest.skip('darwin-only sanity check')
    import shutil
    assert shutil.which('pbcopy') is not None, (
        "pbcopy is missing — macOS clipboard fallback won't work")
    assert shutil.which('pbpaste') is not None
