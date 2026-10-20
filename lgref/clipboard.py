"""Copy and paste text, without depending on either game.

WHY NOT IMPORT THE ONE IN `src/game.py`. There is a working clipboard
chain there, and reusing it would make the general m,n,k player import
the case study's engine module -- which is exactly the dependency the
generality audit exists to prevent. The chain is forty lines; the
dependency would be permanent.

THE CHAIN, in order, because each layer fails in a different
environment:

  1. `pyperclip`, when it happens to be installed;
  2. the PLATFORM'S OWN CLI TOOL -- `pbcopy`/`pbpaste` on macOS,
     `xclip` or `xsel` on X11, `clip` on Windows. This layer is the one
     that actually works most of the time and it was missing from the
     first version of the chain in `src/game.py`, which is why a
     reviewer saw "Copy failed (clipboard unavailable)" on a Mac that
     has `/usr/bin/pbcopy`;
  3. `pygame.scrap`, which is flaky on macOS and needs a real display.

Every layer is separately callable so a test can fail one and check
that the next is tried.
"""

import subprocess
import sys

#: platform -> ordered [(binary, argv)] for writing the clipboard.
COPY_COMMANDS = {
    'darwin': [('pbcopy', ['pbcopy'])],
    'linux': [('xclip', ['xclip', '-selection', 'clipboard']),
              ('xsel', ['xsel', '--clipboard', '--input'])],
    'linux2': [('xclip', ['xclip', '-selection', 'clipboard']),
               ('xsel', ['xsel', '--clipboard', '--input'])],
    'win32': [('clip', ['clip'])],
}

#: platform -> ordered [(binary, argv)] for reading it.
READ_COMMANDS = {
    'darwin': [('pbpaste', ['pbpaste'])],
    'linux': [('xclip', ['xclip', '-selection', 'clipboard', '-o']),
              ('xsel', ['xsel', '--clipboard', '--output'])],
    'linux2': [('xclip', ['xclip', '-selection', 'clipboard', '-o']),
               ('xsel', ['xsel', '--clipboard', '--output'])],
    'win32': [('powershell',
               ['powershell', '-NoProfile', '-Command', 'Get-Clipboard'])],
}


def _via_pyperclip_copy(text):
    import pyperclip

    pyperclip.copy(text)
    return True


def _via_pyperclip_read():
    import pyperclip

    return pyperclip.paste()


def _via_cli_copy(text, platform=None):
    for _name, argv in COPY_COMMANDS.get(platform or sys.platform, ()):
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            if process.returncode == 0:
                return True
        except (OSError, ValueError):
            continue
    return False


def _via_cli_read(platform=None):
    for _name, argv in READ_COMMANDS.get(platform or sys.platform, ()):
        try:
            process = subprocess.Popen(argv, stdout=subprocess.PIPE)
            out, _err = process.communicate()
            if process.returncode == 0:
                return out.decode('utf-8', 'replace')
        except (OSError, ValueError):
            continue
    return None


def copy_text(text):
    """True if the text reached the clipboard by any route."""
    for attempt in (lambda: _via_pyperclip_copy(text),
                    lambda: _via_cli_copy(text)):
        try:
            if attempt():
                return True
        except Exception:
            continue
    try:
        import pygame

        pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode('utf-8'))
        return True
    except Exception:
        return False


def read_text():
    """The clipboard's text, or None if no route worked."""
    for attempt in (_via_pyperclip_read, _via_cli_read):
        try:
            got = attempt()
            if got is not None:
                return got
        except Exception:
            continue
    try:
        import pygame

        pygame.scrap.init()
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
        if raw:
            return raw.decode('utf-8', 'replace').rstrip('\x00')
    except Exception:
        pass
    return None
