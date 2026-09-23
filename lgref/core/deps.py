"""Turn a missing third-party dependency into an actionable message.

A bare `ModuleNotFoundError: No module named 'yaml'` names the symptom
and nothing else. The usual cause here is not a missing install at all:
it is a bare `python3` resolving to the system interpreter while the
shell still shows an active-venv prompt, so the dependency IS installed,
just not for the interpreter that ran. Saying which interpreter is
running is what makes that diagnosable.
"""

import importlib
import sys


def require(module, purpose, package=None):
    """Import `module`, or explain what is missing and how to fix it."""
    try:
        return importlib.import_module(module)
    except ImportError:
        raise SystemExit(
            '\n'.join((
                'LGREF needs `{}` for {}, and this interpreter does not '
                'have it.'.format(module, purpose),
                '',
                '  interpreter: {}'.format(sys.executable),
                '  sys.prefix:  {}'.format(sys.prefix),
                '',
                'If that is not the project venv, the dependency is '
                'probably installed and simply not visible here -- a shell '
                'can show an active-venv prompt while `python3` still '
                'resolves to the system interpreter. Run through the venv '
                'explicitly:',
                '',
                '    .venv/bin/python -m lgref ...',
                '',
                'If the venv itself is missing the package:',
                '',
                '    .venv/bin/python -m pip install -r requirements.txt',
                '',
                '(installs {})'.format(package or module),
            )))
