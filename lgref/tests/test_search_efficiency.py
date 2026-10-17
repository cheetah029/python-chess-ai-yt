"""Iterative-deepening alpha-beta, and why the previous search was slow.

The playable learned agent searched ONE PLY. That was the right choice
inside the TD loop -- action selection there runs on every ply of every
training game -- and the wrong one for an opponent, which inherited it
by accident.

The first attempt at depth, `BeamPlayer`, ordered its moves by cloning
and evaluating every candidate at every node. Measured at branching 50:
a clone costs 0.896 ms and an evaluation 0.529 ms, so ordering cost
50 x 1.425 = 71 ms PER NODE. Alpha-beta at depth 3 needs about 700 nodes
when ordering is good, which is 50 seconds that way and 1 second with
free ordering. The depth was never the problem; the ordering cost was.

Measured gains, each isolated:

    killer moves + history      1.61x   (10181 -> 6317 nodes, depth 3)
    late move reductions        1.57x   ( 6317 -> 4015 nodes)
    transposition table         1.37x   (depth 2: 4.1s -> 3.0s)
    dropping mobility          34.8x    per evaluation

and the outcome on the blunder benchmark, same 40 positions throughout:

    random                        52.5%
    TD one-ply greedy             10.0%
    TD + this search, 2.5s         5.0%   mean depth 2.0
    AlphaBeta told material        0.0%
"""

import hashlib
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.mnk import MNK
from lgref.experiments.features import load_royal_chess_searcher
from lgref.experiments.search import Searcher, order_turns

WEIGHTS = os.path.join(os.path.dirname(__file__), '..', 'weights',
                       'td_royal_chess.json')


def _midgame(plies=60, seed=1):
    from lgref.experiments.random_play import build

    engine = make_engine('full', max_turns=400)
    mover = build('random', random.Random(seed), 0)
    for _ply in range(plies):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(mover.choose_turn(turns, engine))
    return engine


class _NameDerivedWeights(object):
    """A weight for every feature name, derived from the name itself.

    The tests here are about SEARCH -- node counts, depth reached,
    budgets, cutoff tables -- and they need an evaluation that is not
    flat. They do not need a GOOD one, and they must not depend on the
    shipped weights file, which is exactly what went wrong: merging the
    royal features renamed three features, the loader's staleness guard
    fired, and nine tests about alpha-beta mechanics failed over a
    retraining artifact they have no stake in.

    A name-derived weight is deterministic across runs, non-flat, and
    carries no knowledge of the game -- it is as happy to prefer losing
    a rook as keeping one. That is the point: if a search test only
    passes under weights that know chess, it is not testing the search.
    """

    def get(self, name, default=0.0):
        digest = hashlib.sha1(name.encode('utf-8')).hexdigest()
        return int(digest[:8], 16) / float(0xffffffff) - 0.5


def _searcher(**kwargs):
    """A searcher over the CURRENT feature set, whatever it is now."""
    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import royal_chess

    weights = _NameDerivedWeights()

    def evaluate(engine, perspective):
        raw = differentials(royal_chess(engine), perspective)
        return value(weights, normalise(raw, {}, update=False))

    return Searcher(evaluate, **kwargs)


def test_it_searches_deeper_than_one_ply():
    """The entire point. One ply cannot see a recapture, which is what
    'trades a rook for a pawn' looks like from the outside."""
    engine = _midgame()
    searcher = _searcher(budget=3.0)
    turns = engine.get_all_legal_turns()
    chosen = searcher.choose_turn(turns, engine)
    assert chosen in turns
    assert searcher.depth_reached >= 2, (
        'only reached depth {0}'.format(searcher.depth_reached))


def test_the_time_budget_is_honoured():
    """Iterative deepening means a budget is real: every completed depth
    leaves an answer, so an unfinished one can be abandoned.

    This regressed once -- the deadline was checked every 256 nodes and
    never in the root, and a 2s budget overran to 5s.
    """
    engine = _midgame()
    turns = engine.get_all_legal_turns()
    searcher = _searcher(budget=1.5)
    start = time.time()
    searcher.choose_turn(turns, engine)
    elapsed = time.time() - start
    assert elapsed < 1.5 * 2.0 + 1.0, (
        'took {0:.1f}s on a 1.5s budget'.format(elapsed))


def test_deeper_budgets_never_lose_depth():
    engine = _midgame()
    turns = engine.get_all_legal_turns()
    shallow = _searcher(budget=1.0)
    shallow.choose_turn(turns, engine)
    deep = _searcher(budget=4.0)
    deep.choose_turn(turns, engine)
    assert deep.depth_reached >= shallow.depth_reached


def test_late_move_reductions_fire_and_save_nodes():
    """They did NOT fire when first written: the gate was `depth >= 3`
    on the depth INSIDE `_search`, which is one less than the root
    depth, so a depth-3 search never triggered it and the node count
    was byte-identical with and without. Measured, not assumed.
    """
    engine = _midgame()
    turns = engine.get_all_legal_turns()

    # QUIESCENCE MUST BE ON for this to measure anything real, and that
    # is worth recording. With `quiescence=0` the reductions do not pay
    # at all -- measured 3006 nodes without against 3080 with, slightly
    # WORSE -- because the shallow scores a reduced search returns are
    # unresolved, so the re-search condition fires constantly and costs
    # more than the reduction saves. With quiescence resolving the
    # tactics it is a clear win:
    #
    #     depth 3   1739 -> 1034 nodes   1.68x
    #     depth 4  17683 -> 7804 nodes   2.27x
    #
    # An earlier version of this test used quiescence=0 and concluded
    # LMR was harmful. It was the configuration that was wrong.
    off = _searcher(budget=300.0, max_depth=4, quiescence=1)
    off.lmr_after = 10 ** 6
    off.choose_turn(turns, engine)

    on = _searcher(budget=300.0, max_depth=4, quiescence=1)
    on.choose_turn(turns, engine)

    assert on.reductions > 0, 'no reduction fired'
    assert on.nodes < off.nodes, (
        '{0} nodes with reductions against {1} without'.format(on.nodes,
                                                               off.nodes))


def test_cutoff_memory_is_learned_from_the_search_itself():
    """Killers and history encode no knowledge of the game -- they are
    counts of which moves produced cutoffs in this very search."""
    engine = _midgame()
    searcher = _searcher(budget=3.0, max_depth=3)
    searcher.choose_turn(engine.get_all_legal_turns(), engine)
    assert searcher.history or searcher.killers, (
        'neither table recorded a cutoff')


def test_captures_are_ordered_by_the_learned_weight():
    """Ordering reuses the weights TD derived from outcomes; it does not
    introduce a value table of its own."""
    engine = _midgame()
    turns = engine.get_all_legal_turns()
    payload = json.load(open(WEIGHTS))
    from lgref.experiments.features import capture_ranker
    ordered = order_turns(engine, turns, None,
                          capture_ranker(payload['weights'],
                                         payload.get('scales', {})))
    assert len(ordered) == len(turns)
    assert set(id(t) for t in ordered) == set(id(t) for t in turns)
    captures = [t for t in turns if getattr(t, 'is_capture', False)]
    if captures:
        # Every capture must precede every quiet move.
        first_quiet = next(
            (i for i, t in enumerate(ordered)
             if not getattr(t, 'is_capture', False)), len(ordered))
        last_capture = max(
            (i for i, t in enumerate(ordered)
             if getattr(t, 'is_capture', False)), default=-1)
        assert last_capture < first_quiet


def test_the_transposition_table_does_not_change_a_shallow_answer():
    """At depth 1 there is nothing to transpose, so the table must be
    invisible. (Deeper, it legitimately can differ: the state hash
    excludes the repetition counts by design, so a stored value may have
    been computed under a different history -- a trade every engine
    makes, recorded in the module docstring.)"""
    engine = _midgame()
    turns = engine.get_all_legal_turns()
    with_tt = _searcher(budget=60.0, max_depth=1)
    without = _searcher(budget=60.0, max_depth=1)
    without.use_tt = False
    assert (with_tt.choose_turn(turns, engine)
            is without.choose_turn(turns, engine))


def test_it_is_general_over_the_protocol():
    """No piece name, no board walk: it must run on m,n,k too."""
    import ast
    import inspect

    import lgref.experiments.search as module

    game = MNK(m=4, n=4, k=3)
    searcher = Searcher(lambda g, p: 0.5, max_depth=3, budget=2.0)
    assert searcher.choose_turn(game.get_all_legal_turns(), game) in \
        game.get_all_legal_turns()

    tree = ast.parse(inspect.getsource(module))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
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
    # Short literals only: `report`-style prose legitimately discusses
    # the case study, and a feature NAME is short where prose is not.
    short = ' '.join(x for x in live if len(x) < 40)
    for banned in ('Rook', 'Bishop', 'Knight', 'Pawn', 'royal',
                   'squares'):
        assert banned not in short, banned


def test_a_terminal_position_is_read_mover_relative():
    """A decided position scores 1.0 or 0.0, never the evaluation -- and
    FROM THE PERSPECTIVE OF THE PLAYER TO MOVE.

    `_leaf` used to take an explicit perspective while the recursion
    negated its result at every step, which made the two conventions
    agree at even plies and INVERT at odd ones. Measured on m,n,k: a
    depth-3 search over an evaluation worth 88.9% optimal scored 30.6%
    against a 32.6% chance baseline. The perspective argument is gone
    so the conventions cannot be mixed again, and this test pins the
    one that remains.
    """
    searcher = _searcher(budget=1.0)

    class Decided(object):
        def __init__(self, to_move):
            self.current_player = to_move
            self.winner = 'white'

        def is_game_over(self):
            return True

    # The winner is white throughout; only whose turn it is changes.
    assert searcher._leaf(Decided('white')) == 1.0
    assert searcher._leaf(Decided('black')) == 0.0


def test_a_stale_weights_file_is_refused_rather_than_half_applied():
    """The shipped loader must fail loudly on a feature rename.

    A weight whose name no longer exists never contributes, so the
    agent keeps playing with part of its evaluation missing. Caught in
    that state once: 17 saved names against 11 current, `Royal`,
    `Attacked` and `Covers` carrying no weight at all. An exception is
    the right outcome -- the only fix is to retrain.
    """
    import tempfile

    stale = {'weights': {'NoSuchFeature': 1.0}, 'scales': {}}
    handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump(stale, handle)
    handle.close()
    try:
        searcher = load_royal_chess_searcher(handle.name, budget=1.0,
                                             max_depth=1)
        engine = _midgame(plies=4)
        try:
            searcher.choose_turn(engine.get_all_legal_turns(), engine)
        except ValueError as error:
            assert 'do not match the current feature set' in str(error)
        else:
            raise AssertionError('a stale weights file was accepted')
    finally:
        os.unlink(handle.name)


GRAB, QUIET, RECAP = 'grab', 'quiet', 'recapture'


class _Turn(object):
    def __init__(self, kind):
        self.kind = kind
        self.is_capture = kind in (GRAB, RECAP)

    def __repr__(self):
        return self.kind


class _CopyPathCaptureGame(object):
    """A capture game with NO make/unmake support and no board.

    White may grab a pawn; black's only capture then wins a rook, so
    declining is correct and seeing that requires quiescence. The shape
    matters more than the game: `copy()` and no `board`, which is the
    path every engine other than the case study takes.
    """

    winner = None

    def __init__(self, stack=()):
        self.stack = list(stack)
        self.current_player = ('white' if len(self.stack) % 2 == 0
                               else 'black')

    def copy(self):
        return _CopyPathCaptureGame(self.stack)

    def execute_turn(self, turn):
        self.stack.append(turn.kind)
        self.current_player = ('white' if len(self.stack) % 2 == 0
                               else 'black')

    def is_game_over(self):
        return len(self.stack) >= 10

    def get_all_legal_turns(self):
        if self.is_game_over():
            return []
        if len(self.stack) == 1 and self.stack[0] == GRAB:
            return [_Turn(RECAP)]       # the recapture, and only here
        if not self.stack:
            return [_Turn(GRAB), _Turn(QUIET)]
        return [_Turn(QUIET)]


def _bait_evaluation(game, _perspective):
    white = 0.0
    if GRAB in game.stack:
        white += 1.0
    if RECAP in game.stack:
        white -= 5.0
    signed = white if game.current_player == 'white' else -white
    return 0.5 + signed / 20.0


def test_quiescence_resolves_captures_on_a_game_without_make_unmake():
    """Quiescence was BROKEN for every game but the case study, two ways.

    `_quiesce` descended into `child` and then recursed on `engine`.
    Those are the same object on the make/unmake path, which hid it
    completely on Royal Chess -- and on the copy path `child` is the
    clone that had the capture applied while `engine` is untouched, so
    quiescence re-searched the parent position and resolved nothing. It
    also called `restore` directly rather than `_ascend`, and `restore`
    with the copy path's `None` token raised AttributeError on the first
    capture tried. A game with captures and no board CRASHED.
    """
    from lgref.experiments.undo import supports_undo

    game = _CopyPathCaptureGame()
    assert not supports_undo(game), 'the stub must take the copy path'

    # Without quiescence the grab looks like a free pawn, which is the
    # control: it proves the position actually is bait.
    blind = Searcher(_bait_evaluation, max_depth=1, budget=5.0,
                     quiescence=0)
    assert blind.choose_turn(game.get_all_legal_turns(), game).kind == GRAB

    for depth in (1, 2, 4):
        searcher = Searcher(_bait_evaluation, max_depth=1, budget=5.0,
                            quiescence=depth)
        chosen = searcher.choose_turn(game.get_all_legal_turns(), game)
        assert chosen.kind == QUIET, (
            'quiescence {0} still took the bait'.format(depth))


def test_the_principal_variation_is_readable_and_non_destructive():
    """TD-leaf needs the leaf the search actually evaluated.

    The value a search reports for a position is the static evaluation
    of its PV LEAF, not of the position itself, so a learner that fits
    the evaluation at the root fits a quantity the search never reads.
    The line is recovered from the transposition table, which already
    stores a best move per node for ordering, so it costs one clone
    rather than a second search.
    """
    engine = _midgame()
    before_player = engine.current_player
    before_turns = len(engine.get_all_legal_turns())

    searcher = _searcher(budget=10.0, max_depth=3)
    searcher.choose_turn(engine.get_all_legal_turns(), engine)
    line, leaf = searcher.principal_variation(engine)

    assert line, 'no line was recovered'
    assert len(line) <= searcher.depth_reached
    # Odd-length lines hand the move to the other player.
    if len(line) % 2 == 1 and not leaf.is_game_over():
        assert leaf.current_player != before_player

    # The caller's engine must be untouched: the trainer keeps playing
    # on it after asking for the line.
    assert engine.current_player == before_player
    assert len(engine.get_all_legal_turns()) == before_turns


def test_a_search_that_never_ran_yields_an_empty_line():
    """No search, no belief. The walk must not invent one."""
    engine = _midgame()
    searcher = _searcher(budget=1.0, max_depth=2)
    line, leaf = searcher.principal_variation(engine)
    assert line == []
    assert leaf.current_player == engine.current_player


def test_pvs_is_sound_but_off_because_it_does_not_pay():
    """A measured NEGATIVE result, pinned so nobody retries it blind.

    I predicted PVS, aspiration windows and a leaf evaluation cache
    would all be free wins, and said so before measuring. Same midgame
    position, trainer paused so the clock is uncontended:

        depth 4, midgame      nodes    time
        baseline               6206   5.12s
        + PVS                  6363   5.19s
        + aspiration           6564   5.29s
        + eval cache           6206   5.00s
        all three              6726   5.35s

        depth 4, opening       nodes    time
        baseline              16503  15.50s
        all three             17549  15.86s

    PVS is SOUND -- it picks the baseline's move -- but does not pay,
    because the ordering is already good enough that there is little
    left to refute cheaply, so re-searches outnumber savings (54 became
    118). Aspiration was worse than slow: it was UNSOUND, writing
    narrow-window bounds into the shared transposition table that the
    full-window re-search then read as full-width, and it is gone
    rather than merely disabled.

    The real lesson is in the cache row: it serves 1576 hits of 6206
    nodes and saves 0.12s, because MOVE GENERATION dominates, not
    evaluation. No search-side trick reaches depth 4 from here.
    """
    from lgref.experiments.mcts import describe

    searcher = _searcher(budget=1.0)
    assert searcher.use_pvs is False, 'measured not to pay; stays off'
    assert searcher.use_eval_cache is True, 'non-harmful; left on'
    assert not hasattr(searcher, 'use_aspiration'), (
        'aspiration was unsound and was removed, not disabled')

    engine = _midgame()
    turns = engine.get_all_legal_turns()
    chosen = set()
    for pvs, cache in ((False, False), (True, False), (True, True)):
        one = _searcher(budget=600.0, max_depth=3, quiescence=2)
        one.use_pvs, one.use_eval_cache = pvs, cache
        chosen.add(describe(one.choose_turn(turns, engine)))
    assert len(chosen) == 1, (
        'PVS or the cache changed the chosen move, so it is unsound '
        'rather than merely slow: {0}'.format(chosen))


def test_the_evaluation_cache_never_changes_the_tree():
    """It is a memo, so the node count must be byte-identical."""
    engine = _midgame()
    turns = engine.get_all_legal_turns()
    off = _searcher(budget=600.0, max_depth=3, quiescence=2)
    off.use_eval_cache = False
    off.choose_turn(turns, engine)
    on = _searcher(budget=600.0, max_depth=3, quiescence=2)
    on.choose_turn(turns, engine)
    assert on.nodes == off.nodes, (
        '{0} nodes cached against {1} uncached'.format(on.nodes, off.nodes))
    assert on.eval_hits > 0, 'the cache served nothing, so it is untested'
