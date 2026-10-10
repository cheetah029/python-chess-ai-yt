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


# ---- the Phase B benchmark answers must be hidden too ------------------
#
# "Recorded" and "hidden" are two properties of ONE artifact, and Phase B
# needs both: recorded so there is something to score against, hidden so
# the method cannot score by reading the answer. Recorded-but-visible is
# leakage; hidden-but-unrecorded is unscoreable.
#
# The Royal Chess seed labels were already guarded above. The benchmark
# mappings were not, and they live INSIDE identify/ -- one import away
# from the clustering they score.

#: QUALIFIED names only. A first version matched the bare words and
#: flagged `cluster.py`, which has a local variable called `reference`
#: holding a coverage value -- nothing to do with the answers. A guard
#: that cries wolf gets deleted, so it matches the module path.
BENCHMARK_ANSWERS = ('testgames.ground_truth', 'testgames.reference',
                     'ground_truth.py', 'reference.py',
                     'from lgref.identify.testgames import',
                     'expected_partition')

#: Modules that legitimately read the answers, because scoring is their
#: job. `report.py` prints the comparison; nothing it computes feeds back
#: into the partition.
SCORERS = ('report.py',)


def _identify_modules_excluding_scorers():
    folder = os.path.join(LGREF_ROOT, 'identify')
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.py') or name in SCORERS:
            continue
        yield name, os.path.join(folder, name)


def test_the_clustering_code_cannot_see_the_benchmark_answers():
    """The partition must be produced without reading the mapping.

    `cluster.py` scoring well because it imported `ground_truth` would be
    the same defect as Phase 2 reading the seed labels, and nothing
    stopped it: `ground_truth.py` sits in the same package.
    """
    offenders = []
    for name, path in _identify_modules_excluding_scorers():
        with open(path) as handle:
            source = handle.read()
        for answer in BENCHMARK_ANSWERS:
            if answer in source:
                offenders.append('{} mentions {!r}'.format(name, answer))
        # And the structural check, which a renamed module cannot evade.
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module and \
                    'testgames' in node.module:
                offenders.append('{} imports from {}'.format(
                    name, node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if 'testgames' in alias.name:
                        offenders.append('{} imports {}'.format(
                            name, alias.name))
    assert not offenders, (
        'the code under test can reach the benchmark answers: {}'.format(
            offenders))


def test_the_scorer_is_still_allowed_to_read_them():
    """Otherwise the guard above would be satisfied by scoring nothing."""
    path = os.path.join(LGREF_ROOT, 'identify', 'report.py')
    with open(path) as handle:
        source = handle.read()
    assert 'ground_truth' in source, (
        'report.py is the scorer and must read the recorded mapping')


def test_every_benchmark_game_is_in_exactly_one_split():
    """Related variants share statements almost entirely, so a game and
    its ablations must never straddle a split."""
    from lgref.identify.testgames.ground_truth import GAMES, SPLITS

    placed = [game for names in SPLITS.values() for game in names]
    assert sorted(placed) == sorted(GAMES)
    assert len(placed) == len(set(placed)), 'a game appears in two splits'


def test_the_held_out_game_is_the_one_with_the_hard_properties():
    """Developing on the interaction would make it a tuning target."""
    from lgref.identify.testgames.ground_truth import SPLITS, STRUCTURE

    for game in SPLITS['test']:
        structure = STRUCTURE[game]
        assert structure['redundant'], (
            '{} is held out but has no redundant rule'.format(game))
        assert structure['interacting'], (
            '{} is held out but has no interacting rules'.format(game))
    for split in ('dev', 'validation'):
        for game in SPLITS[split]:
            assert not STRUCTURE[game]['interacting'], (
                '{} carries an interaction and is in {}, which makes the '
                'interaction a development target'.format(game, split))


def test_declared_shared_predicates_really_are_shared():
    """The declaration must match the data, or it is decoration.

    A first version declared sharing in a docstring while giving
    arithmetic its own rule, so NO statement in any of the three games
    belonged to more than one rule. Phase B asks for shared statements;
    this checks they exist.
    """
    from lgref.identify.clauses import load
    from lgref.identify.testgames.ground_truth import (STRUCTURE,
                                                       expected_partition)

    root = os.path.join(LGREF_ROOT, 'identify', 'testgames')
    for game, structure in STRUCTURE.items():
        nodes = load(os.path.join(root, game + '.gdl'))
        partition = expected_partition(game, nodes)
        multi = sum(1 for rules in partition.values() if len(rules) > 1)
        if structure['shared']:
            assert multi > 0, (
                '{} declares shared predicates {} but no statement belongs '
                'to more than one rule'.format(game, structure['shared']))
        else:
            assert multi == 0, (
                '{} declares no sharing but {} statements belong to more '
                'than one rule'.format(game, multi))
