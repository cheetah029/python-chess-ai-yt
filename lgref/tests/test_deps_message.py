"""A missing dependency must say which interpreter is missing it.

Reported from a shell showing an active-venv prompt: `python3 -m
lgref.identify.gate ...` raised a bare `ModuleNotFoundError: No module
named 'yaml'`. PyYAML *was* installed -- in the venv -- but `python3`
resolved to the system interpreter, so the message named a symptom that
pointed away from the cause.
"""

import os
import subprocess
import sys

import pytest

from lgref.core.deps import require

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SYSTEM_PYTHON = '/usr/bin/python3'


def test_require_returns_the_module_when_present():
    assert require('json', 'nothing in particular') is not None


def test_require_names_the_interpreter_not_just_the_module():
    with pytest.raises(SystemExit) as excinfo:
        require('definitely_not_installed_xyz', 'a test', 'some-package')
    message = str(excinfo.value)
    assert sys.executable in message, (
        'the message must say WHICH interpreter is missing the package; '
        'that is the whole diagnosis when a venv is not actually active')
    assert 'requirements.txt' in message
    assert 'some-package' in message
    assert '.venv/bin/python' in message


def test_requirements_file_lists_what_the_framework_imports():
    with open(os.path.join(REPO, 'requirements.txt')) as handle:
        text = handle.read().lower()
    for package in ('pyyaml', 'networkx', 'pyarrow'):
        assert package in text, '{} is imported but unpinned'.format(package)


@pytest.mark.skipif(not os.path.exists(SYSTEM_PYTHON),
                    reason='no system python to contrast against')
def test_an_interpreter_without_the_deps_gets_the_explanation():
    """End to end, through the entry point the user actually ran."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    done = subprocess.run(
        [SYSTEM_PYTHON, '-m', 'lgref.identify.gate',
         '--config', 'lgref/config/phase1_gate.yaml'],
        capture_output=True, text=True, env=env, cwd=REPO)
    combined = done.stdout + done.stderr
    if 'No module named' in combined and 'LGREF needs' not in combined:
        pytest.fail('bare ModuleNotFoundError escaped to the user:\n'
                    + combined[-400:])
    if 'LGREF needs' in combined:
        assert SYSTEM_PYTHON in combined or 'interpreter:' in combined
