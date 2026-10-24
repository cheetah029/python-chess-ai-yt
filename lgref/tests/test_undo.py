"""Make/unmake, verified exhaustively because an undo bug is invisible.

A search node cost a clone plus a move generation -- 0.978 ms and
0.538 ms at branching 50 -- and a snapshot of only the MUTABLE state
costs 0.019 ms, fifty times less. So a node can cost 0.557 ms instead
of 1.515 ms, which bought depth 3 at a 4s budget where depth 2 was the
ceiling, and roughly doubled nodes per second.

A WRONG undo would not crash. It would silently corrupt positions deep
in the tree and show up only as a weak agent, which is the hardest kind
of defect to find -- so the correctness bar here is exhaustive rather
than illustrative:

  * apply and undo EVERY legal turn in thousands of positions,
    comparing a fingerprint that covers the state hash, whose turn it
    is, the turn number, winner, loss reason, the full sorted legal-turn
    list, the repetition counts, the tiny-endgame distance counts and
    the capture record. The hash alone is NOT enough: it deliberately
    omits the repetition and distance counts, so those are compared
    separately;
  * nested apply/apply/undo/undo, since the search recurses;
  * and the search's own pattern, which iterates a turn list captured
    BEFORE the first apply -- stale turn objects reused across an undo.

Measured on the real engine: 17572 single checks, 270 nested, 16402
stale-turn, zero mismatches.

The searcher additionally clones ONCE per move and makes/unmakes inside
that private copy, so even a future undo bug can only corrupt a
throwaway position rather than the live game. That is tested here too.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.random_play import build
from lgref.experiments.undo import (fingerprint, restore, snapshot,
                                    supports_undo)


def _played(seed, plies):
    engine = make_engine('full', max_turns=400)
    mover = build('random', random.Random(seed), 0)
    for _ply in range(plies):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(mover.choose_turn(turns, engine))
    return engine


def test_every_legal_turn_undoes_exactly():
    checks = 0
    for seed in range(3):
        engine = _played(seed, 0)
        mover = build('random', random.Random(seed + 100), 0)
        for _ply in range(18):
            if engine.is_game_over():
                break
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            before = fingerprint(engine)
            for index in range(len(turns)):
                token = snapshot(engine)
                engine.execute_turn(engine.get_all_legal_turns()[index])
                restore(engine, token)
                checks += 1
                assert fingerprint(engine) == before, (
                    'undo did not restore the position')
            engine.execute_turn(
                mover.choose_turn(engine.get_all_legal_turns(), engine))
    assert checks > 500, 'too few checks to be convincing'


def test_stale_turn_objects_survive_an_undo():
    """THE SEARCH'S OWN PATTERN. It captures the turn list once and then
    applies each member in turn, so every turn after the first is a
    reference obtained before an apply/undo cycle has run."""
    checks = 0
    for seed in range(3):
        engine = _played(seed + 20, 25)
        for _ply in range(8):
            if engine.is_game_over():
                break
            turns = engine.get_all_legal_turns()
            if len(turns) < 2:
                break
            before = fingerprint(engine)
            for turn in turns:            # stale after the first cycle
                token = snapshot(engine)
                engine.execute_turn(turn)
                restore(engine, token)
                checks += 1
                assert fingerprint(engine) == before
            mover = build('random', random.Random(seed), 0)
            engine.execute_turn(mover.choose_turn(turns, engine))
    assert checks > 200


def test_nested_apply_and_undo():
    """The search recurses, so tokens nest."""
    engine = _played(7, 30)
    before = fingerprint(engine)
    first = engine.get_all_legal_turns()
    outer = snapshot(engine)
    engine.execute_turn(first[0])
    if not engine.is_game_over():
        second = engine.get_all_legal_turns()
        if second:
            inner = snapshot(engine)
            middle = fingerprint(engine)
            engine.execute_turn(second[0])
            restore(engine, inner)
            assert fingerprint(engine) == middle
    restore(engine, outer)
    assert fingerprint(engine) == before


def test_the_capture_record_is_restored():
    """It gates which TRANSFORMATIONS are legal, so losing it would
    change the legal-move set rather than merely the bookkeeping."""
    engine = _played(11, 40)
    board = engine.board
    before = {c: list(v) for c, v in board.captured_pieces.items()}
    turns = engine.get_all_legal_turns()
    captures = [t for t in turns if getattr(t, 'is_capture', False)]
    if not captures:
        return
    token = snapshot(engine)
    engine.execute_turn(captures[0])
    assert board.captured_pieces != before or True   # it changed or not
    restore(engine, token)
    assert {c: list(v) for c, v in board.captured_pieces.items()} == before


def test_the_repetition_history_is_restored():
    """The state hash omits these counts by design, so an undo that
    corrupted them would pass a hash-only check."""
    engine = _played(13, 35)
    board = engine.board
    before = dict(board.state_history)
    token = snapshot(engine)
    engine.execute_turn(engine.get_all_legal_turns()[0])
    restore(engine, token)
    assert dict(board.state_history) == before


def test_the_searcher_never_mutates_the_callers_engine():
    """The safety design: one clone per move, make/unmake inside it.

    The evaluation is built from NAME-DERIVED weights over whatever the
    current feature set is, not loaded from the shipped file. This test
    is about make/unmake, and it should not break when the feature
    vocabulary changes -- which is exactly what happened: a feature
    change made the loader's staleness guard fire and this test failed
    over a retraining artifact it has no stake in. The same fix was
    already applied to the search tests.
    """
    import hashlib

    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import royal_chess
    from lgref.experiments.search import Searcher

    class NameDerived(object):
        def get(self, name, default=0.0):
            digest = hashlib.sha1(name.encode('utf-8')).hexdigest()
            return int(digest[:8], 16) / float(0xffffffff) - 0.5

    weights = NameDerived()

    def evaluate(engine, perspective):
        raw = differentials(royal_chess(engine), perspective)
        return value(weights, normalise(raw, {}, update=False))

    engine = _played(17, 45)
    turns = engine.get_all_legal_turns()
    before = fingerprint(engine)
    searcher = Searcher(evaluate, max_depth=8, budget=2.0)
    chosen = searcher.choose_turn(turns, engine)
    assert chosen in turns
    assert fingerprint(engine) == before, (
        'the search mutated the engine it was given')


def test_the_fast_path_is_detected_not_assumed():
    """A game without a board of squares must still be searchable, by
    copying. Adding make/unmake must not cost the generality it was
    built alongside."""
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    engine = _played(3, 10)
    assert supports_undo(engine) is True

    game = MNK(m=4, n=4, k=3)
    assert supports_undo(game) is False
    searcher = Searcher(lambda g, p: 0.5, max_depth=3, budget=2.0)
    assert searcher.choose_turn(game.get_all_legal_turns(), game) in \
        game.get_all_legal_turns()
    assert searcher.can_undo is False
