"""The held-out seed labels must be unreachable from the pipeline.

The project's central claim is that Phase 2 predicts strategic functions
from rule structure alone, and Phase 4 scores those frozen predictions
against the designer's intended labels. That claim is void if the
inference code can see the labels it is being scored against.

The brief required this be enforced "with code structure, not
discipline". Three checks, in increasing strictness:

  1. lgref/reference/ is not an importable package (no __init__.py).
  2. No module under identify/ or functions/ imports it.
  3. No module under identify/ or functions/ mentions it AT ALL — not in
     a string literal, not in a path join, not in an open() call. This
     is the check that catches the realistic failure, which is not
     `import reference` but
     `open('lgref/reference/seed_labels.yaml')`.

Scope is identify/ and functions/ because those produce the prediction.
analysis/ is deliberately NOT covered: Phase 4 evaluation is exactly
where the labels are supposed to be read.
"""

import ast
import os

import pytest


LGREF_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DIR = os.path.join(LGREF_ROOT, 'reference')

# Packages that must never reach the held-out labels.
QUARANTINED = ('identify', 'functions')

FORBIDDEN_TOKEN = 'reference'


def _python_files(package):
    root = os.path.join(LGREF_ROOT, package)
    if not os.path.isdir(root):
        return []
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith('.py'):
                found.append(os.path.join(dirpath, name))
    return found


def test_reference_is_not_an_importable_package():
    """No __init__.py — so `import lgref.reference` cannot succeed."""
    assert os.path.isdir(REFERENCE_DIR), 'lgref/reference/ is missing'
    init = os.path.join(REFERENCE_DIR, '__init__.py')
    assert not os.path.exists(init), (
        'lgref/reference/__init__.py exists — that makes the held-out '
        'labels importable and breaks the isolation guarantee. Delete it.')


def test_seed_labels_file_exists():
    assert os.path.exists(os.path.join(REFERENCE_DIR, 'seed_labels.yaml'))


@pytest.mark.parametrize('package', QUARANTINED)
def test_no_import_of_reference(package):
    """AST check: no import statement naming the reference package."""
    offenders = []
    for path in _python_files(package):
        with open(path) as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if FORBIDDEN_TOKEN in alias.name.split('.'):
                        offenders.append(f'{path}:{node.lineno} import '
                                         f'{alias.name}')
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if FORBIDDEN_TOKEN in module.split('.'):
                    offenders.append(f'{path}:{node.lineno} from {module}')
                else:
                    # `from lgref import reference` names the package as
                    # an ALIAS, not as node.module. Checking only
                    # node.module misses it -- found by mutation-testing
                    # this guard, which is why the alias names are
                    # checked too.
                    for alias in node.names:
                        if FORBIDDEN_TOKEN in alias.name.split('.'):
                            offenders.append(
                                f'{path}:{node.lineno} from {module} '
                                f'import {alias.name}')
    assert not offenders, (
        'held-out reference labels imported by the prediction pipeline:\n  '
        + '\n  '.join(offenders))


@pytest.mark.parametrize('package', QUARANTINED)
def test_no_textual_mention_of_reference(package):
    """AST check: the token never appears in any string literal either.

    Catches the realistic leak — reading the YAML by path rather than
    importing it. Scanning string CONSTANTS via the AST (not raw text)
    keeps docstrings and comments free to discuss the isolation, which
    is what the modules under quarantine will legitimately need to do.
    """
    offenders = []
    for path in _python_files(package):
        with open(path) as f:
            tree = ast.parse(f.read(), filename=path)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None:
                    docstrings.add(doc)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in docstrings:
                    continue
                if FORBIDDEN_TOKEN in node.value:
                    snippet = node.value[:60].replace('\n', ' ')
                    offenders.append(f'{path}:{node.lineno} {snippet!r}')
    assert not offenders, (
        'held-out reference labels named in a string literal inside the '
        'prediction pipeline (a path-based read still leaks them):\n  '
        + '\n  '.join(offenders))
