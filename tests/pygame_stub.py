"""Install a pygame stub ONLY when pygame is genuinely unavailable.

Three test modules used to install a stub into `sys.modules['pygame']`
unconditionally, at import time, and never remove it. Because that
happens during COLLECTION, every module pytest collected afterwards saw
the stub instead of the real library, and `pytest tests/` failed with 20
`AttributeError: module 'pygame' has no attribute ...` errors before a
single test ran. Each of those files passed on its own, so the breakage
was invisible to anyone running a subset -- which, with the whole suite
unrunnable, was everyone.

The stub turns out to be unnecessary when pygame is installed: the
mocked modules exercise board and piece logic, and all 350 of
test_piece_movement's tests pass against the real library. So the stub
becomes a fallback for an environment that lacks pygame, rather than the
default that silently poisons collection.

`sys.modules` is global and shared across the whole session. Anything
put there by one module is inherited by every module imported later, so
a stub installed for convenience is never local to the file that
installed it.
"""

import sys
import types


def _build():
    pygame = types.ModuleType('pygame')
    mixer = types.ModuleType('pygame.mixer')

    class Sound(object):
        def __init__(self, path):
            pass

        def play(self):
            pass

    mixer.Sound = Sound
    pygame.mixer = mixer
    return pygame, mixer


def install_if_missing():
    """Return True if a stub was installed, False if real pygame is used.

    Callers do not need the result; it exists so a test can assert which
    path was taken rather than guessing.
    """
    try:
        import pygame  # noqa: F401
        import pygame.mixer  # noqa: F401
    except ImportError:
        pygame_mock, mixer_mock = _build()
        sys.modules['pygame'] = pygame_mock
        sys.modules['pygame.mixer'] = mixer_mock
        return True
    return False
