"""A standing audit: nothing general may learn about a particular game.

This file exists because generality was lost four separate times in
this project and every one was found by a human playing the agent or by
a check written AFTER the damage:

  - `discover.py` quietly became a Royal Chess module while its own
    docstring said otherwise -- it walked `range(8)`, imported a piece
    class, and listed three piece names by hand.
  - the futility margin was `0.02`, justified in its own comment by
    "one piece is worth 0.03-0.05 TO THIS EVALUATION" -- a constant in
    one game's value units, inside the module that claims to know none.
  - `_quiesce` crashed on any game with captures that had no board of
    squares, because it called an engine-shaped helper unconditionally.
  - a docstring claimed a relative gate, citing this game's piece
    values, that was never in the code.

So the rules are checked mechanically and on every run.

WHAT COUNTS AS A VIOLATION. Prose may discuss the case study -- a
docstring explaining why a measurement came out the way it did is not
encoding a domain. LIVE CODE may not: no piece name, no board size, no
value in one game's units. The checks below read the AST and ignore
docstrings for exactly that reason.
"""

import ast
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

#: Modules that must know NO game. The adapter layer (`features`), the
#: frozen copy of it (`legacy`), the second game itself (`mnk`) and the
#: hand-supplied opponent (`strong`) are deliberately excluded and are
#: covered by their own rules further down.
#:
#: `undo` is excluded too, and the distinction matters. It is a FAST
#: PATH for engines shaped like the case study -- a board of squares
#: with per-piece attributes -- and it says so in its own docstring. An
#: adapter is allowed to know a game; what it is NOT allowed to do is
#: be assumed. The rule for `undo` is therefore different and is
#: checked by `test_an_adapter_fast_path_is_detected_not_assumed`:
#: capability is detected, and everything still works when it is
#: absent.
GENERAL_MODULES = (
    'lgref.experiments.search',
    'lgref.experiments.bootstrap',
    'lgref.experiments.discover',
    'lgref.experiments.replicate',
    'lgref.experiments.validate',
    'lgref.experiments.fastcopy',
    'lgref.experiments.iterate',
)

#: Words that name a thing in one of the two games. A general module
#: may not contain any of them in live code.
DOMAIN_WORDS = (
    'rook', 'bishop', 'knight', 'pawn', 'queen', 'king', 'royal',
    'boulder', 'castling', 'promotion', 'tictactoe', 'gomoku',
    'Line:', 'Marks', 'win_lines',
)


def _live_strings_and_names(module):
    """Every string, attribute and name in the module's CODE.

    Docstrings are excluded: explaining a domain is not encoding one,
    and these modules legitimately record what a measurement on the
    case study showed.
    """
    tree = ast.parse(inspect.getsource(module))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            text = ast.get_docstring(node, clean=False)
            if text is not None:
                docstrings.add(text)
    live = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Str) and node.s not in docstrings:
            live.add(node.s)
        elif isinstance(node, ast.Attribute):
            live.add(node.attr)
        elif isinstance(node, ast.Name):
            live.add(node.id)
    return live


@pytest.mark.parametrize('name', GENERAL_MODULES)
def test_a_general_module_names_no_game(name):
    module = __import__(name, fromlist=['x'])
    live = ' '.join(x for x in _live_strings_and_names(module)
                    if len(x) < 48).lower()
    for word in DOMAIN_WORDS:
        assert word.lower() not in live, (
            '{0} contains {1!r} in live code'.format(name, word))


@pytest.mark.parametrize('name', GENERAL_MODULES)
def test_a_general_module_imports_no_game(name):
    """Importing an engine is how a module stops being general without
    anyone noticing. `discover.py` imported a piece class."""
    module = __import__(name, fromlist=['x'])
    tree = ast.parse(inspect.getsource(module))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
            imported += ['{0}.{1}'.format(node.module, a.name)
                         for a in node.names]
    banned = ('piece', 'board', 'engine', 'game', 'const',
              'experiments.variants', 'lgref.experiments.features',
              'lgref.experiments.legacy', 'lgref.experiments.strong')
    for name_ in imported:
        head = name_.split('.')[0]
        assert head not in banned and name_ not in banned, (
            '{0} imports {1}'.format(name, name_))


def test_an_adapter_fast_path_is_detected_not_assumed():
    """An adapter may know a game. It may not be REQUIRED.

    `undo` reads a board of squares and per-piece attributes, so it
    only applies to engines shaped that way -- and a game without one
    has to keep working, by copying instead. `_quiesce` once called an
    engine-shaped helper unconditionally and CRASHED every game with
    captures that had no such board.
    """
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher
    from lgref.experiments.undo import supports_undo

    from experiments.variants import make_engine

    assert supports_undo(make_engine('full', max_turns=20)) is True
    flat = MNK(m=4, n=4, k=3)
    assert supports_undo(flat) is False

    # And the search works on the one without it.
    searcher = Searcher(lambda g, p: 0.5, max_depth=3, budget=5.0)
    assert searcher.choose_turn(flat.get_all_legal_turns(), flat) in \
        flat.get_all_legal_turns()


def test_the_snapshot_saves_whatever_a_piece_carries():
    """It used a HAND-WRITTEN LIST of this engine's attribute names,
    which meant a flag added later would silently not be restored --
    and put `queen` into a module that claims to detect rather than
    assume. It copies the instance dictionary now, so a new attribute
    is covered without anyone remembering it."""
    from lgref.experiments.undo import restore, snapshot

    from experiments.variants import make_engine

    engine = make_engine('full', max_turns=40)
    piece = next(sq.piece for row in engine.board.squares for sq in row
                 if sq.piece is not None)
    token = snapshot(engine)
    piece.invented_flag_nobody_listed = 'set after the snapshot'
    restore(engine, token)
    assert not hasattr(piece, 'invented_flag_nobody_listed'), (
        'an attribute added during the move survived the undo')


def test_no_general_module_hides_a_value_in_evaluation_units():
    """The futility margin was 0.02 because "one piece is worth
    0.03-0.05 to this evaluation". A threshold compared against a SCORE
    has to be derived from scores the search has seen, not written down.
    """
    from lgref.experiments.search import Searcher

    searcher = Searcher(lambda g, p: 0.5)
    assert searcher.futility_margin is None, (
        'the margin is supplied again; it must be derived from the '
        'evaluation, see `_observe`')
    # The dimensionless parts are allowed: they shape the tree, not the
    # units. They must stay dimensionless.
    assert 0.0 < searcher.futility_fraction <= 1.0
    assert searcher.futility_min_samples >= 1


def test_the_hand_supplied_opponent_is_not_an_instrument():
    """`strong.py` carries a written-down material table. It may be
    PLAYED against and it may not be used to measure anything that is
    reported as a property of the framework."""
    import pkgutil

    import lgref.experiments as package

    offenders = []
    for info in pkgutil.iter_modules(package.__path__):
        if info.name in ('strong', 'legacy'):
            continue
        module = __import__('lgref.experiments.' + info.name,
                            fromlist=['x'])
        try:
            source = inspect.getsource(module)
        except (OSError, TypeError):
            continue
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and \
                    node.module.endswith('strong'):
                offenders.append(info.name)
    assert not offenders, (
        'these modules import the hand-supplied material table: '
        '{0}'.format(offenders))


def test_both_games_run_through_the_same_learner_and_search():
    """The claim in one line: the same two modules play both games.

    Not a style check -- it constructs an agent for each game from the
    SAME classes and makes it choose a legal move.
    """
    import random

    from experiments.variants import make_engine

    from lgref.experiments.bootstrap import normalise, run, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import (mnk as mnk_features,
                                            royal_chess, with_threshold)
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    cases = [
        ('royal chess', lambda *a, **k: make_engine('full', max_turns=60),
         with_threshold(royal_chess)),
        ('m,n,k', lambda *a, **k: MNK(m=4, n=4, k=3),
         with_threshold(mnk_features)),
    ]
    for label, make_game, extractor in cases:
        scales = {}
        history = run(make_game, extractor, rounds=1, games_per_round=2,
                      alpha=0.08, epsilon=0.3, seed=1, max_turns=40,
                      scales=scales, budget_seconds=20.0)
        weights = history[-1].weights

        def evaluate(engine, perspective, weights=weights, scales=scales,
                     extractor=extractor):
            raw = differentials(extractor(engine), perspective)
            return value(weights, normalise(raw, dict(scales),
                                            update=False))

        game = make_game()
        turns = game.get_all_legal_turns()
        searcher = Searcher(evaluate, max_depth=2, budget=10.0,
                            quiescence=1)
        assert searcher.choose_turn(turns, game) in turns, label


def test_the_threshold_wrapper_is_not_a_piece_list():
    """`with_threshold` must derive its names from whatever it wraps."""
    from lgref.experiments.features import with_threshold

    def invented(_engine):
        return {('red', 'Widgets'): 2, ('blue', 'Widgets'): 0}

    split = with_threshold(invented)(None)
    assert split[('red', 'Widgets')] == 2
    assert split[('red', 'Missing:Widgets')] == 0
    assert split[('blue', 'Missing:Widgets')] == 1


def test_the_protocol_extractor_runs_on_an_invented_game():
    """`features.generic` claims to need only the move protocol, so it
    has to work on a game neither of ours resembles."""
    from lgref.experiments.features import generic

    class Invented(object):
        current_player = 'red'
        winner = None

        def get_all_legal_turns(self):
            return [1, 2, 3]

        def is_game_over(self):
            return False

    counts = generic(Invented())
    assert counts, 'nothing was extracted from a game it has not seen'
    assert set(o for o, _n in counts) == {'red'}
    assert ('red', 'Mobility') in counts


def test_the_weights_payload_pins_its_own_feature_set():
    """The loader reconstructs the feature set rather than assuming it.
    Every field here exists because it drifted at least once."""
    import json

    path = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'td_royal_chess.json')
    payload = json.load(open(path))
    for field in ('extractor', 'dropped', 'drop_prefixes'):
        assert field in payload, (
            '{0} is missing; the loader would have to guess'.format(field))


def test_the_material_harness_is_labelled_domain_specific():
    """IT IS NOT A GENERAL METRIC and must not be mistaken for one.

    The hang/miss/regret harness scores material with `strong.material`,
    a written-down piece table. It is a useful diagnostic on the case
    study and it cannot be used to compare framework-level claims,
    because a different game has no such table. The general measure is
    match play: wins, losses and draws read from the engine.
    """
    from lgref.experiments import strong

    source = inspect.getsource(strong)
    assert 'OPPONENT' in source or 'opponent' in source, (
        'strong.py must say what it is for')
    assert hasattr(strong, 'material'), (
        'the hand-supplied table moved; this guard needs updating')
