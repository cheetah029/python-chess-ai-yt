"""Test runs never touch the user's clipboard (#420)."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'src')]
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')


def test_the_test_session_uses_the_private_clipboard():
    assert os.environ.get('LGREF_PRIVATE_CLIPBOARD') == '1'


def test_neither_clipboard_chain_runs_a_system_tool(monkeypatch):
    """Copy and read round-trip through the private buffer, and no
    subprocess (pbcopy, xclip, clip) is ever started."""
    from lgref import clipboard
    import game

    started = []

    def refuse(*args, **kwargs):
        started.append(args)
        raise AssertionError('a test reached the system clipboard')

    monkeypatch.setattr(subprocess, 'run', refuse)
    monkeypatch.setattr(subprocess, 'Popen', refuse)
    assert clipboard.copy_text('m,n,k save') is True
    assert clipboard.read_text() == 'm,n,k save'
    assert game._default_copy_to_clipboard('royal save') is True
    assert game._default_read_clipboard() == 'royal save'
    assert started == []


def test_outside_tests_the_real_chain_is_used(monkeypatch):
    """Without the switch the chain is the one it always was: the first
    system layer is asked."""
    from lgref import clipboard

    monkeypatch.delenv('LGREF_PRIVATE_CLIPBOARD')
    asked = []
    monkeypatch.setattr(clipboard, '_via_pyperclip_copy',
                        lambda text: asked.append(text) or True)
    assert clipboard.copy_text('x') is True
    assert asked == ['x']
