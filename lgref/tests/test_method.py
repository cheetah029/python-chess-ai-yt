"""The methodology itself, enforced.

THE REVIEWER'S OBJECTION, which is correct and goes to the root:

    "I am asking for strict improvement, not overall improvement. If
    even a single thing is worse, the change cannot be shipped. So
    using gates to 'test' for strict improvement is wrong in and of
    itself. What needs to be done from the start is to design the
    methodology of building the change so that it is certainly
    strictly better."

A gate is a DETECTOR. It reports what it can see, at the power it has,
on the phases it reaches. An empty result means "nothing detected",
never "nothing there" -- and this project has three worked examples of
the gap being real: a tempo loss inside the noise floor and down on all
four seeds; an endgame loss invisible on the board being measured; a
gain measured while the change crippled the search.

So every behavioural change that is ON in the player carries a
CERTIFICATE -- an argument made before the measurement, of a shape
whose premise can be checked mechanically. These tests re-check every
premise on every run. A change whose premise stops holding fails here,
not in a reviewer's game.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()
pygame.font.init()

import pytest

from lgref.experiments import certificate

#: Filled in by each certificate test: subject -> the kind actually
#: proven. Compared against `DECLARED` below.
PROVEN = {}


def record(proof):
    PROVEN[proof.subject] = proof.kind
    return proof


def mnk_positions(count=40, seed=5):
    from lgref.experiments.mnk import MNK

    rng = random.Random(seed)
    out = []
    while len(out) < count:
        m, n, k = rng.choice([(5, 5, 4), (9, 9, 5), (13, 13, 5),
                              (4, 4, 3), (7, 7, 5)])
        game = MNK(m=m, n=n, k=k)
        for _ply in range(rng.randint(0, m * n - 1)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        out.append(game)
    return out


# ---- the certificates, re-checked ----------------------------------

def test_the_extraction_rewrite_is_identical():
    """IDENTICAL. The per-line `Counter` was removed for speed, so the
    licence is that nothing else changed -- compared against the
    previous implementation loaded from git, not against a reading of
    the diff."""
    import importlib.util
    import subprocess
    import tempfile

    root = os.path.join(os.path.dirname(__file__), '..', '..')
    previous = subprocess.run(
        ['git', 'log', '--format=%H', '-n', '40', '--',
         'lgref/experiments/features.py'],
        cwd=root, stdout=subprocess.PIPE, timeout=120)
    commits = previous.stdout.decode().split()
    source = None
    for commit in commits:
        blob = subprocess.run(
            ['git', 'show', '{0}:lgref/experiments/features.py'.format(
                commit)], cwd=root, stdout=subprocess.PIPE, timeout=120)
        text = blob.stdout.decode()
        if 'held = collections.Counter(' in text:
            source = text
            break
    if source is None:
        pytest.skip('no pre-rewrite implementation in recent history')

    handle = tempfile.NamedTemporaryFile('w', suffix='.py', delete=False)
    handle.write(source)
    handle.close()
    spec = importlib.util.spec_from_file_location('features_before',
                                                  handle.name)
    before = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(before)

    from lgref.experiments.features import mnk as after

    proof = record(certificate.identical('features.mnk', before.mnk,
                                         after,
                                         mnk_positions(60)))
    assert proof.kind == 'IDENTICAL' and proof.checked == 60


def test_futility_removal_is_an_unsound_premise():
    """UNSOUND. Futility pruning assumes a quiet move cannot change the
    score. In a game whose only act is placing a stone, every move
    changes it -- so the premise is false and removing the guard costs
    nothing that was correctly gained."""
    from lgref.experiments.search import has_tactical_turns

    def premise_holds(game):
        """Does this game have the quiet/forcing distinction?"""
        return has_tactical_turns(game.get_all_legal_turns())

    proof = record(certificate.unsound('futility pruning in m,n,k',
                                       premise_holds,
                                       mnk_positions(30)))
    assert proof.kind == 'UNSOUND'

    # And it DOES hold for the case study, so nothing is removed there.
    from experiments.variants import make_engine
    engine = make_engine('full', max_turns=40)
    assert has_tactical_turns(engine.get_all_legal_turns()) is True


def test_late_move_reduction_removal_is_an_unsound_premise():
    """UNSOUND. LMR searches late-ordered moves shallower, on the
    premise that a late move is probably bad. That is a claim about the
    ORDERING, and in a game with no captures the ordering is killers
    and history alone.

    Measured on 9x9 k=5 over 116 positions: the best move sits at mean
    position 0.528 where 0.5 is no information, reaches the first
    quarter 6.0% of the time against a 25% chance baseline, and falls
    in the reduced region 97.4% of the time. The premise is not weak
    here, it is false.

    The premise checked below is the same capability futility rests on,
    because it is the same missing distinction -- and it HOLDS for the
    case study, where captures order the list, so nothing is removed
    there.
    """
    from lgref.experiments.search import has_tactical_turns

    def premise_holds(game):
        return has_tactical_turns(game.get_all_legal_turns())

    proof = record(certificate.unsound('late move reduction in m,n,k',
                                       premise_holds,
                                       mnk_positions(30)))
    assert proof.kind == 'UNSOUND'


def test_the_case_study_still_reduces_and_prunes():
    """Both removals are m,n,k-only. A change that quietly turned off
    an optimisation in the other game would be a regression nobody
    asked for."""
    from experiments.variants import make_engine
    from lgref.experiments.search import Searcher

    engine = make_engine('full', max_turns=40)
    searcher = Searcher(lambda state, who: 0.5, max_depth=3, quiescence=0, use_tt=False)
    searcher.choose_turn(engine.get_all_legal_turns(), engine)
    assert searcher.reductions > 0, (
        'late move reduction stopped firing in the case study')


def test_reduce_turns_and_quiescence_are_not_live_in_mnk():
    """THE OTHER TWO HEURISTICS, checked and found inert rather than
    unsound -- which is a different finding and worth recording as one.

    `reduce_turns` is injected and the m,n,k window never injects it.
    Quiescence is passed 0 there, and even if it were not, a position
    with no tactical turns returns its standing value immediately. So
    neither needs removing: neither runs.
    """
    import inspect

    import lgref.play_mnk as play
    from lgref.experiments.search import Searcher

    window = inspect.getsource(play.play_window)
    maker = inspect.getsource(play.make_player)
    assert 'reduce_turns' not in window and 'reduce_turns' not in maker
    assert 'quiescence=0' in maker

    signature = inspect.signature(Searcher.__init__)
    assert signature.parameters['reduce_turns'].default is None


def test_the_move_clock_is_an_unsound_premise():
    """UNSOUND. A per-move wall clock is the operation "stop deepening
    and answer with what you have", and its premise is that the GAME
    imposes a real-time constraint.

    Neither game here does. Both are bounded in PLIES: m,n,k ends when
    the board fills, Royal Chess when both royals fall or the turn cap
    is reached. The game description carries no time term at all, and
    the engines never read a clock to decide anything. So the premise
    fails on every case, and a number of seconds is a hand-supplied
    intervention that changes what the agent plays -- bias, by this
    project's own definition.

    DISCHARGED THREE WAYS, because "the rules say nothing about time"
    is the kind of claim that is easy to assert and worth checking:
    against the official game description, against the engines'
    termination predicates, and against the shipped defaults.
    """
    import inspect
    import io as _io
    import os
    import re

    import lgref.play_mnk as play
    from game import Game
    from lgref.experiments import features
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    here = os.path.dirname(__file__)
    gdl = os.path.join(here, '..', '..', 'docs', 'gdl', 'integrated.gdl')

    def reads_a_clock(source):
        """Does this code consult real time to decide anything?

        A CALL, not a substring. Looking for `time.` matched the
        comment "no implicit branching at execution time", which is
        prose about the engine and not a clock read -- the second false
        positive this check produced, and the certifier refused both
        rather than waving them through.
        """
        return bool(re.search(
            r'\b(time\.(time|monotonic|perf_counter)|perf_counter\s*\('
            r'|datetime\.|timeit)', source))

    def premise_the_game_constrains_move_time(case):
        """True if this case supplies a time constraint from the rules."""
        if case == 'game description':
            # The OFFICIAL dialect is infix HRF; the prefix file is
            # outdated and is not read here.
            #
            # WORD BOUNDARIES MATTER, and the first version of this
            # check got it wrong: a bare `time(` matched
            # `would_repeat_third_time(`, which is the repetition
            # rule's COUNT and has nothing to do with wall time. A
            # premise check that fires on a substring would have
            # refused this change for the wrong reason.
            text = _io.open(gdl, encoding='utf-8').read().lower()
            return bool(re.search(
                r'(?<![a-z_])(clock|wall_?time|elapsed|deadline|timeout'
                r'|seconds?|millisecond|time)\s*\(', text))
        if case == 'mnk termination':
            return reads_a_clock(inspect.getsource(MNK.is_game_over)
                                 + inspect.getsource(MNK))
        if case == 'royal chess termination':
            from engine import GameEngine
            return reads_a_clock(
                inspect.getsource(GameEngine.is_game_over))
        raise AssertionError(case)

    proof = record(certificate.unsound(
        'the move clock in a game whose rules have none',
        premise_the_game_constrains_move_time,
        ('game description', 'mnk termination',
         'royal chess termination')))
    assert proof.kind == 'UNSOUND'

    # AND THE OPERATION IS GONE ENTIRELY, not merely defaulted off. A
    # premise that fails while the operation still runs is an essay,
    # and a switch somebody can turn back on is still the operation.
    assert not hasattr(Searcher(lambda _g, _p: 0.5), 'budget')
    for subject in (Searcher.__init__, features.load_royal_chess_searcher,
                    play.make_player):
        assert 'budget' not in inspect.signature(subject).parameters, (
            '{0} still takes a budget'.format(subject))
    assert not hasattr(Game, 'TD_BUDGET_SECONDS')
    # The plumbing with it: no deadline, no out-of-time exception, no
    # clock test in the node loop, and no partial iteration to guard.
    #
    # CHECKED AGAINST THE CODE, NOT THE PROSE. The first version of
    # this grepped the source text and matched its own explanatory
    # comments, which name every one of these on purpose. The names
    # that matter are the ones the interpreter sees.
    import ast as _ast

    tree = _ast.parse(_io.open(
        os.path.join(os.path.dirname(__file__), '..', 'experiments',
                     'search.py'), encoding='utf-8').read())
    forbidden = {'deadline', '_OutOfTime', 'abandoned', 'budget'}
    seen = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Name):
            seen.add(node.id)
        elif isinstance(node, _ast.Attribute):
            seen.add(node.attr)
        elif isinstance(node, _ast.arg):
            seen.add(node.arg)
        elif isinstance(node, _ast.keyword) and node.arg:
            seen.add(node.arg)
        elif isinstance(node, (_ast.ClassDef, _ast.FunctionDef)):
            seen.add(node.name)
    leftover = sorted(forbidden & seen)
    assert not leftover, (
        'the searcher still refers to {0} in code -- the clock plumbing '
        'is not fully removed'.format(leftover))
    assert 'time' not in {alias.name
                          for node in _ast.walk(tree)
                          if isinstance(node, _ast.Import)
                          for alias in node.names}, (
        'the searcher still imports `time`')

    # AND THE POSITIVE HALF OF THE SAME CLAIM: what the rules DO bound
    # the game by. Showing no clock is read is weaker than showing
    # what is read instead.
    from engine import GameEngine
    over = inspect.getsource(GameEngine.is_game_over)
    assert 'turn_number' in over and 'max_turns' in over, over
    board = MNK(m=4, n=4, k=3)
    assert len(board.get_all_legal_turns()) == 16, (
        'm,n,k is bounded by the cells on the board, which is a count '
        'of plies and not a span of seconds')


def _royal_chess_clock_cases():
    """Royal Chess positions, with everything the case study's searcher
    needs to be rebuilt on either implementation."""
    import json
    import random

    from experiments.variants import make_engine
    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import (capture_ranker, royal_chess,
                                            royal_chess_tactical)

    path = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'td_royal_chess.json')
    if not os.path.exists(path):
        return []
    payload = json.load(open(path))
    weights, scales = payload['weights'], payload.get('scales', {})

    def evaluate(engine, perspective):
        raw = differentials(royal_chess(engine), perspective)
        return value(weights, normalise(raw, dict(scales), update=False))

    spec = {'evaluate': evaluate,
            'ranker': capture_ranker(weights, scales),
            'is_tactical': royal_chess_tactical}
    rng = random.Random(11)
    out = []
    for plies in (0, 6, 12, 18, 26, 34, 44):
        engine = make_engine('full', max_turns=400)
        ok = True
        for _ply in range(plies):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                ok = False
                break
            engine.execute_turn(rng.choice(turns))
        if not ok or engine.is_game_over():
            continue
        out.append((engine, engine.get_all_legal_turns(),
                    ('royal', spec)))
    return out


def test_removing_the_clock_plumbing_is_identical():
    """IDENTICAL. The clock was removed outright at the reviewer's
    instruction, so the licence is that the searcher without it decides
    exactly what the searcher with it decided when no budget was set.

    Compared against the PRE-REMOVAL implementation loaded from git,
    not against a reading of the diff -- the same discipline the
    extraction rewrite got.

    The premise is unusually clean: with no finite budget, every
    deadline test in the old code was `time.time() >= float('inf')`,
    which is never true, so those branches were dead. This proves it
    rather than asserting it, and it also re-establishes the property
    the removal rested on -- that a clock could only ever take depth
    AWAY, never add it.
    """
    import importlib.util
    import random
    import subprocess
    import tempfile

    root = os.path.join(os.path.dirname(__file__), '..', '..')
    log = subprocess.run(
        ['git', 'log', '--format=%H', '-n', '40', '--',
         'lgref/experiments/search.py'],
        cwd=root, stdout=subprocess.PIPE, timeout=120)
    source = None
    for commit in log.stdout.decode().split():
        blob = subprocess.run(
            ['git', 'show', '{0}:lgref/experiments/search.py'.format(
                commit)], cwd=root, stdout=subprocess.PIPE, timeout=120)
        text = blob.stdout.decode()
        if 'class _OutOfTime' in text and 'budget=None' in text:
            source = text
            break
    if source is None:
        pytest.skip('no pre-removal searcher in recent history')

    handle = tempfile.NamedTemporaryFile('w', suffix='.py', delete=False)
    handle.write(source)
    handle.close()
    spec = importlib.util.spec_from_file_location('search_before',
                                                  handle.name)
    before = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(before)

    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    def flat(_engine, _perspective):
        return 0.5

    rng = random.Random(5)
    cases = []
    for (m, n, k) in ((5, 5, 4), (9, 9, 5), (13, 13, 5)):
        for marks in (0, 4, 20):
            game = MNK(m=m, n=n, k=k)
            for _ply in range(marks):
                turns = game.get_all_legal_turns()
                if not turns or game.is_game_over():
                    break
                game.execute_turn(rng.choice(turns))
            turns = game.get_all_legal_turns()
            if len(turns) < 2:
                continue
            cases.append((game, turns, (m, n, marks)))
    assert len(cases) >= 8, len(cases)

    def run(module, case):
        game, turns, where = case
        cls = module.Searcher if module is not None else Searcher
        if isinstance(where, tuple) and where and where[0] == 'royal':
            kwargs = where[1]
            searcher = cls(kwargs['evaluate'], kwargs['ranker'],
                           max_depth=3, quiescence=2,
                           is_tactical=kwargs['is_tactical'])
        else:
            searcher = cls(flat, max_depth=3, quiescence=0)
        chosen = searcher.choose_turn(turns, game)
        return (repr(chosen), searcher.depth_reached, searcher.nodes)

    def old_choice(case):
        return run(before, case)

    def new_choice(case):
        return run(None, case)

    # THE CASE STUDY TOO, not only m,n,k. The reviewer asked for the
    # Royal Chess player to stay competent, and "the same player" is
    # the strongest form of that: same move, same depth, same node
    # count, on positions from the opening to 44 plies in.
    cases += _royal_chess_clock_cases()

    proof = record(certificate.identical('the move clock plumbing',
                                         old_choice, new_choice, cases))
    assert proof.kind == 'IDENTICAL'
    assert len(cases) >= 14, (
        'both games must be covered, got {0} cases'.format(len(cases)))

    # AND THE PROPERTY THE REMOVAL RESTED ON, re-established against
    # the implementation that still had a clock: it could only ever
    # take depth away.
    for game, turns, where in cases:
        if isinstance(where, tuple) and where and where[0] == 'royal':
            continue          # the reducer property is shown on m,n,k
        free = before.Searcher(flat, max_depth=3, quiescence=0)
        free.choose_turn(turns, game)
        assert free.depth_reached == 3, free.depth_reached
        for budget in (0.05, 0.5):
            clocked = before.Searcher(flat, max_depth=3, budget=budget,
                                      quiescence=0)
            clocked.choose_turn(turns, game)
            assert clocked.depth_reached <= free.depth_reached, (
                'a {0}s clock reached depth {1} where no clock reached '
                '{2} at {3} -- the clock was not only a reducer and the '
                'removal needed a different argument'.format(
                    budget, clocked.depth_reached, free.depth_reached,
                    where))


def test_thinking_off_the_ui_thread_is_identical():
    """IDENTICAL. The m,n,k window's search moved onto a worker so the
    event loop keeps running; the licence is that it plays the same
    move, with the same reported depth and the same grade.

    `advance()` is kept as the composition of begin/poll/land rather
    than as a second implementation, so there is one search path and
    the two routes cannot drift. This compares them anyway, because
    "they share code" is not the same claim as "they agree".

    AND THE ORDER OF THESE TWO CHANGES IS NOT ARBITRARY. Under a wall
    clock the routes DID disagree -- same move, "depth 2" blocking and
    "depth 1" in the background, because the drawing loop competes for
    the interpreter lock and the clock fired a ply earlier. So this
    certificate only exists because the clock went first.
    """
    import lgref.play_mnk as play

    captured = {}

    def probe(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        rows = []
        # Above `GRADE_CELL_LIMIT`, so the exponential solver stays
        # switched off -- it costs 7.7 s at 15 empty cells on 5x5.
        for _ply in range(3):
            if api['game'][0].is_game_over():
                break
            before = list(api['game'][0].cells)
            if not api['advance']():
                break
            blocking = (api['played'][-1], api['state']['note'])
            while api['game'][0].cells != before:
                if not api['undo']():
                    break
            if api['game'][0].cells != before:
                break
            api['state']['auto'] = True
            if not api['begin_think']():
                break
            spun = 0
            deadline = time.time() + 120
            while not api['thinking_done']():
                api['draw']()
                spun += 1
                assert time.time() < deadline, 'the worker never finished'
            assert api['land_think']()
            rows.append((blocking,
                         (api['played'][-1], api['state']['note'])))
        captured['rows'] = rows
        return True

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, train_budget=1.0)
    play.play_window(5, 5, 4, brain, 2,
                     {play.FIRST: 'td', play.SECOND: 'td'}, probe=probe)
    rows = captured.get('rows') or []
    assert len(rows) >= 3, rows

    proof = record(certificate.identical(
        'm,n,k window thinking off the UI thread',
        lambda row: row[0], lambda row: row[1], rows))
    assert proof.kind == 'IDENTICAL'

    # AND THE DEFAULT REALLY IS THE BACKGROUND ROUTE, not just an
    # available one. A seam that proves a path nobody takes proves
    # nothing.
    import inspect

    loop = inspect.getsource(play.play_window)
    assert '_begin_think()' in loop and '_land_think()' in loop
    # AND THERE IS NO CLOCK LEFT TO REINTRODUCE THE DISAGREEMENT. With
    # one, the two routes reached different depths from the same
    # position and this certificate did not exist.
    assert 'move_budget' not in inspect.signature(
        play.play_window).parameters


def test_the_exact_grade_is_off_the_move_critical_path():
    """IDENTICAL. `grade` runs an exact solver and used to run after
    the move was already chosen, so the move could not APPEAR until the
    label did -- 8.98 s on a full 4x4 board, which is the board this
    window opens at.

    The licence is that the move played and the note ONCE THE VERDICT
    HAS LANDED are the same strings as before. Only the moment the
    label appears changes, and a test asserts it appears later rather
    than taking that on trust.
    """
    import lgref.play_mnk as play

    captured = {}

    def probe(api):
        api['rebuild']()
        api['state']['screen'] = 'play'
        # DOWN TO ELEVEN EMPTY CELLS FIRST, so the grader actually
        # fires (0.01 s at twelve empty against 8.98 s on a full
        # board). X on 0,4,12 and O on 1,2 is three apiece with no
        # three in a row on a 4-wide grid.
        for move in (0, 1, 4, 2, 12):
            if move in api['game'][0].get_all_legal_turns():
                api['commit'](move)
        if api['game'][0].is_game_over():
            return True
        before = list(api['game'][0].cells)
        if not api['advance']():
            return True
        blocking = (api['played'][-1], api['state']['note'])
        while api['game'][0].cells != before:
            if not api['undo']():
                break
        if api['game'][0].cells != before:
            return True
        api['state']['auto'] = True
        if not api['begin_think']():
            return True
        deadline = time.time() + 120
        while not api['thinking_done']():
            api['draw']()
            assert time.time() < deadline
        assert api['land_think']()
        captured['before_verdict'] = api['state']['note']
        while api['judging']['thread'] is not None:
            api['draw']()
            api['land_judge']()
            assert time.time() < deadline
        captured['rows'] = [(blocking,
                             (api['played'][-1], api['state']['note']))]
        return True

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, train_budget=1.0)
    play.play_window(4, 4, 3, brain, 2,
                     {play.FIRST: 'td', play.SECOND: 'td'}, probe=probe)
    rows = captured.get('rows') or []
    assert rows, 'the graded path was never reached'

    # The grader did run, so this is not a vacuous comparison.
    assert 'optimal' in rows[0][0][1] or 'any move' in rows[0][0][1], rows
    # And it ran AFTER the move was shown.
    early = captured.get('before_verdict', '')
    assert 'optimal' not in early and 'any move' not in early, (
        'the verdict was in the note the moment the move landed, so it '
        'is still on the critical path: {0!r}'.format(early))

    proof = record(certificate.identical(
        'the exact grade on the move critical path',
        lambda row: row[0], lambda row: row[1], rows))
    assert proof.kind == 'IDENTICAL'


def test_the_default_depth_read_from_the_board_is_monotone():
    """MONOTONE, on two quantities at once, both measured against the
    player as it shipped BEFORE this session: `--depth 3` with a
    5-second clock.

      depth completed   D(board) >= the depth the clocked player
                        delivered, at every position on that board
      worst move time   <= the clock's own budget

    The first discharges from one control-flow fact plus the cap: the
    clocked player could not exceed min(3, whatever fits in 5 s),
    because every deadline test in the search is a `break` and
    `max_depth` capped it at 3. So choosing D as exactly that maximum
    makes the invariant an equality, and the cap is what keeps "deeper
    is obviously better" out of the argument -- depth 4 fits to 9x9 and
    is deliberately NOT taken.

    The second discharges from the measured table.
    """
    import lgref.play_mnk as play

    #: Worst-case seconds a move, no clock, shipped evaluation and
    #: shipped search settings. Measured 2026-10-25 on a quiet machine;
    #: an earlier table taken under four concurrent jobs was 2-3x
    #: higher and is superseded.
    COST = {
        (5, 5): {2: 0.00, 3: 0.03, 4: 0.07},
        (7, 7): {2: 0.01, 3: 0.17, 4: 0.88},
        (9, 9): {2: 0.04, 3: 0.48, 4: 2.76},
        (13, 13): {2: 0.15, 3: 4.02, 4: 17.03},
        (19, 19): {2: 1.35, 3: 46.70, 4: 218.83},
    }
    OLD_BUDGET, OLD_MAX_DEPTH = 5.0, 3

    rows = []
    for (m, n), costs in sorted(COST.items()):
        # What the clocked player actually delivered: the deepest
        # iteration that fitted, never more than its `max_depth`.
        fitted = [d for d in sorted(costs) if costs[d] <= OLD_BUDGET]
        delivered = min(OLD_MAX_DEPTH, max(fitted) if fitted else 1)
        chosen = play.affordable_depth(m, n)
        rows.append(((m, n), delivered, chosen, costs.get(chosen)))

    for board, delivered, chosen, seconds in rows:
        assert chosen >= delivered, (
            'on {0} the default is depth {1} where the clocked player '
            'delivered {2} -- that is a REDUCTION and the invariant '
            'does not hold'.format(board, chosen, delivered))
        assert chosen <= OLD_MAX_DEPTH, (
            'on {0} the default rose to {1}, which is the "deeper is '
            'better" argument this is not allowed to use'.format(
                board, chosen))
        assert seconds is not None and seconds <= OLD_BUDGET, (
            'on {0} depth {1} costs {2}s against the clock budget of '
            '{3}s'.format(board, chosen, seconds, OLD_BUDGET))

    proof = record(certificate.monotone(
        'the default depth is read from the board',
        lambda _case, depth: depth,
        lambda case: case[1],          # before: the depth DELIVERED
        lambda case: case[2],          # after:  the depth now chosen
        rows))
    assert proof.kind == 'MONOTONE'

    # NOT A VACUOUS PROOF, and this is the part that shows the baseline
    # is doing work. Against the depth that was CONFIGURED (3 on every
    # board) rather than the depth the clock DELIVERED, the same
    # certificate must FAIL -- 19x19 goes 3 -> 2. The whole argument
    # turns on which of those two is the honest baseline, so a test
    # that cannot tell them apart proves nothing.
    with pytest.raises(certificate.NotCertified):
        certificate.monotone(
            'the default depth against the CONFIGURED one',
            lambda _case, depth: depth,
            lambda _case: OLD_MAX_DEPTH,
            lambda case: case[2],
            rows)

    # AND IT IS GENERAL OVER THE BOARD, not a lookup of the sizes that
    # happen to have been measured -- the cell count is the branching
    # factor in this game, so an unmeasured board still lands in a band.
    assert play.affordable_depth(15, 15) in (2, 3)
    assert play.affordable_depth(4, 4) == 3
    assert play.affordable_depth(20, 20) == 2
    # The cap is a parameter, so a caller who has earned a deeper
    # default can ask for one rather than editing the table.
    assert play.affordable_depth(5, 5, cap=4) == 3


def test_the_texture_cache_renders_identical_pixels():
    """IDENTICAL, in the strongest form available: the rendered frame
    is compared PIXEL FOR PIXEL against the uncached renderer.

    `show_pieces` used to call `pygame.image.load(piece.texture)` for
    every piece on every frame -- a PNG decode from disk, thirty-two
    times a frame -- plus a load and a `smoothscale` for every overlay.
    That was 5.57 ms of a 5.15 ms frame, and the frame rose to 47.75 ms
    while a search was running, because the search thread and the
    drawing loop then both want a whole core. A key press waits behind
    the current frame, so the frame cost IS the input latency.

    RENDERED TWICE WITH THE CACHE AS WELL, which catches the failure a
    cache of mutable objects actually has: if anything drew on a cached
    surface, the second frame would differ from the first.
    """
    import game as game_module
    from game import Game

    pygame.display.set_mode((880, 880))
    screen = pygame.display.get_surface()

    def render(subject):
        subject.show_bg(screen)
        subject.show_last_move(screen)
        subject.show_moves(screen)
        subject.show_jump_capture_targets(screen)
        subject.show_coordinates(screen)
        subject.show_pieces(screen)
        subject.show_hover(screen)
        return pygame.image.tostring(screen, 'RGBA')

    def rearrange(subject, step):
        """A different position to render, without needing legal moves.

        The pixels are what is under test, so the board only has to
        CHANGE -- it does not have to change legally. Overlay-producing
        flags are toggled too, because the overlay path is the one that
        also caches a `smoothscale`.
        """
        squares = subject.board.squares
        source = squares[1][step % 8]
        target = squares[4][(step * 3) % 8]
        target.piece, source.piece = source.piece, target.piece
        for row in (0, 7):
            for col in range(8):
                piece = squares[row][col].piece
                if piece is None:
                    continue
                for flag in ('invulnerable', 'is_royal', 'transformed'):
                    if hasattr(piece, flag):
                        setattr(piece, flag, bool(step % 2))

    subject = Game()
    frames = []
    for _ply in range(4):
        # Cached, twice -- a mutated cache shows up as a difference
        # between two renders of the same position.
        first = render(subject)
        second = render(subject)
        assert first == second, (
            'two renders of one position differ, so something is '
            'drawing on a cached surface')
        # And against a renderer that decodes every texture afresh.
        game_module.clear_texture_cache()
        fresh = render(subject)
        assert fresh == first, (
            'the cached frame differs from a freshly decoded one')
        frames.append((first, fresh))
        rearrange(subject, _ply)

    assert len(frames) == 4, len(frames)
    # AND THE POSITIONS WERE ACTUALLY DIFFERENT, or four identical
    # frames would "pass" while testing one.
    assert len(set(first for first, _ in frames)) > 1, (
        'every frame rendered the same pixels, so the comparison only '
        'covered one position')

    proof = record(certificate.identical(
        'the per-frame texture decode',
        lambda pair: pair[1], lambda pair: pair[0], frames))
    assert proof.kind == 'IDENTICAL'

    # The cache is actually being used, or this test proves nothing
    # about the thing that was slow.
    game_module.clear_texture_cache()
    render(subject)
    assert game_module._TEXTURES, 'nothing was cached'
    import inspect
    body = inspect.getsource(Game.show_pieces)
    assert 'pygame.image.load' not in body, (
        'show_pieces still decodes a texture per frame')
    assert 'load_texture' in body


def test_the_threat_tie_break_is_structurally_inert():
    """NOT A CLASS, A FACT -- and the fact that stopped a change.

    §1a of `docs/candidate-designs.md` says the tie-break's THREAT
    level is admissible: CONFINED to ties, and MONOTONE on the
    active-move rate. Both premises do hold. It still does not ship,
    because it can never act.

    THE TWO CONDITIONS ARE DISJOINT, AND THE RULES MAKE THEM SO. A move
    is "active" only if it takes some winning configuration to k-1
    marks or removes one that is already there, which needs k-2 marks
    already standing in a single line. A tie at the root happens only
    while the line counts have not yet separated the candidates --
    which is the first few plies, before any line can hold k-2. So:

        board      marks   tied at the max   active among them
        19x19 k5       0               121                   0
        19x19 k5       2               103                   0
        19x19 k5       4               117                   0
        19x19 k5       8+              1-2                   0
        13x13 k5     0-2             24-25                   0
        13x13 k5      24+              1-2                 1-2

    Measured with the REAL root values at the played depth, full window
    -- a first attempt used a one-ply proxy, and backed-up minimax
    values are coarser, so the proxy could have understated ties.
    Zero positions of 66 across four boards had a tie containing both
    an active move and an inactive one.

    WHICH MEANS THE RECORD WAS WRONG. `tie_breaker`'s docstring credited
    the threat level with recovering a 0.8-point midgame tempo loss
    that the centrality level had caused. It cannot have: it never
    fires. That tempo movement was seed noise, and the docstring now
    says so.

    A certified change that does nothing is not an improvement -- the
    same conclusion §3 reached about the intersection boulder.
    """
    import random

    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher
    from lgref.experiments.undo import supports_undo

    brain = play.Brain(2, 8, 17, False, 2, train_budget=1.0)
    rng = random.Random(5)
    examined = can_act = big_ties = 0
    for (m, n, k) in ((9, 9, 5), (13, 13, 5)):
        evaluate = brain.evaluation(m, n, k)
        for marks in (0, 2, 4, 14, 24):
            game = MNK(m=m, n=n, k=k)
            for _ply in range(marks):
                turns = game.get_all_legal_turns()
                if not turns or game.is_game_over():
                    break
                game.execute_turn(rng.choice(turns))
            turns = game.get_all_legal_turns()
            if len(turns) < 2 or game.is_game_over():
                continue
            examined += 1
            searcher = Searcher(evaluate, max_depth=2, quiescence=0)
            searcher.can_undo = supports_undo(game)
            searcher.has_tactics = False
            me = game.current_player
            values = {}
            for turn in turns:
                child = game.copy()
                child.execute_turn(turn)
                if child.is_game_over():
                    values[turn] = (1.0 if child.winner == me
                                    else 0.5 if child.winner is None
                                    else 0.0)
                else:
                    values[turn] = 1.0 - searcher._search(
                        child, 1, 0.0, 1.0, me)
            top = max(values.values())
            tied = [turn for turn in turns if values[turn] == top]
            rank = play.tie_breaker(game)
            actives = sum(1 for turn in tied if rank(turn)[0])
            if len(tied) > 2:
                big_ties += 1
                assert actives == 0, (
                    'a {0}-way tie at {1} marks on {2}x{3} contained {4} '
                    'active moves -- the disjointness argument is wrong '
                    'and §1a may be worth shipping after all'.format(
                        len(tied), marks, m, n, actives))
            if 0 < actives < len(tied):
                can_act += 1

    assert examined >= 8, examined
    assert big_ties >= 1, (
        'no multi-way tie was sampled, so the claim that big ties hold '
        'no active moves was not actually tested')
    assert can_act == 0, (
        'the threat tie-break could act in {0} of {1} positions, so it '
        'is NOT inert and §1a should be reconsidered'.format(
            can_act, examined))


def test_the_board_copy_is_identical():
    """IDENTICAL. `copy.deepcopy` became a pickle round-trip for speed;
    the licence is that the copy is the same copy."""
    from game import Game

    game = Game()
    states = []
    for _ in range(12):
        states.append(game._snapshot())

    def by_pickle(snapshot):
        board = game._deep_copy_board(snapshot['board'])
        return board.get_state_hash('white')

    def by_deepcopy(snapshot):
        import copy
        return copy.deepcopy(snapshot['board']).get_state_hash('white')

    proof = record(certificate.identical('Game._deep_copy_board',
                                         by_deepcopy,
                                         by_pickle, states))
    assert proof.checked == 12


def test_jumping_is_identical_to_stepping():
    """IDENTICAL. The jump stopped rebuilding every position it passes
    through; the licence is that it lands in the same place."""
    from game import Game

    def stepping(plies):
        game = Game()
        for _ in range(plies):
            game._history.append(game._snapshot())
        while game.can_undo():
            game.undo()
        return (game.board.get_state_hash(game.next_player),
                game.next_player, len(game._history),
                len(game._redo_stack))

    def jumping(plies):
        game = Game()
        for _ in range(plies):
            game._history.append(game._snapshot())
        game.jump_to_start()
        return (game.board.get_state_hash(game.next_player),
                game.next_player, len(game._history),
                len(game._redo_stack))

    proof = record(certificate.identical('Game.jump_to_start', stepping,
                                         jumping, [3, 7, 12, 20]))
    assert proof.checked == 4


def test_the_cheap_threat_check_is_identical_to_the_general_one():
    """IDENTICAL. The tie-break reads the lines through one position
    instead of rescanning every legal move. It is OFF in the player,
    but the licence is checked anyway, because a switch that is off
    today is a switch somebody turns on."""
    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.validate import threat_count

    game = MNK(m=5, n=5, k=4)
    for cell in (0, 20, 1, 21):
        game.execute_turn(cell)
    prior = play.opening_prior(5, 5, 4)
    rank = play.tie_breaker(game, prior)

    me = game.current_player
    probe = game.copy()
    probe.execute_turn(game.get_all_legal_turns()[0])
    opponent = probe.current_player
    was_mine = threat_count(game, me)
    was_theirs = threat_count(game, opponent)

    def general(turn):
        after = game.copy()
        after.execute_turn(turn)
        return (threat_count(after, me) > was_mine
                or threat_count(after, opponent) < was_theirs
                or (after.is_game_over()
                    and getattr(after, 'winner', None) == me))

    def cheap(turn):
        return bool(rank(turn)[0])

    proof = record(certificate.identical('tie_breaker threat level',
                                         general,
                                         cheap,
                                         game.get_all_legal_turns()))
    assert proof.checked > 10


# ---- the rule itself ------------------------------------------------

#: THE CLASS EACH CHANGE WAS DESIGNED TO SATISFY, written down BEFORE
#: the change was built.
#:
#: WHY DECLARED SEPARATELY FROM PROVEN. Checking a certificate after
#: the code exists still lets the argument be chosen to fit whatever
#: the code turned out to do -- "I meant CONFINED, I could only prove
#: MONOTONE, so it is MONOTONE now". That is the same error as reading
#: a quiet gate as a licence, one level up: the conclusion is being
#: fitted to the result instead of the work being fitted to the
#: conclusion.
#:
#: So the class is declared here and PROVEN below, and a mismatch is a
#: failure rather than a relabelling. A change that cannot be proven in
#: the class it was designed for goes back to the design, not to this
#: table.
DECLARED = {
    'features.mnk': 'IDENTICAL',
    'Game._deep_copy_board': 'IDENTICAL',
    'Game.jump_to_start': 'IDENTICAL',
    'tie_breaker threat level': 'IDENTICAL',
    'futility pruning in m,n,k': 'UNSOUND',
    # DECLARED BEFORE THE CODE, 2026-10-24. Late-move reduction
    # searches late-ordered moves shallower, on the premise that a late
    # move is probably bad -- a claim about the ORDERING. Measured on
    # 9x9 k=5 over 116 positions: the best move sits at mean position
    # 0.528 where 0.5 is no information, lands in the first quarter
    # 6.0% of the time where chance is 25%, and sits in the reduced
    # region 97.4% of the time. The premise is not merely weak here, it
    # is false.
    'late move reduction in m,n,k': 'UNSOUND',
    # DECLARED BEFORE THE CODE, 2026-10-25. A per-move WALL CLOCK is an
    # operation -- "stop deepening and answer with what you have" --
    # and it rests on a premise: that the game imposes a real-time
    # constraint, so a shallower completed answer is the right trade.
    #
    # NEITHER GAME HERE IMPOSES ONE. m,n,k's rules bound the game in
    # PLIES, not seconds; Royal Chess's do the same; and the game
    # description contains no time term at all -- there is no `clock`,
    # `time` or `budget` predicate in `docs/gdl/integrated.gdl`, and
    # `is_game_over`/`winner` never read a clock. A 5-second budget is
    # a HAND-SUPPLIED number that changes what the agent plays, which
    # is the project's own definition of bias.
    #
    # So this is the same shape as futility pruning: an operation whose
    # premise the game does not supply. And it is removed the same way
    # -- by DETECTING the capability rather than deleting the code,
    # because a timed match is a real context and the clock is sound
    # there.
    #
    # WHAT IT IS NOT. This is NOT the inadmissible "deeper is better"
    # argument that `docs/strictly-better-method.md` refuses. The
    # configured depth does not change. The clock could only ever
    # REDUCE the completed depth below the configured one -- every
    # deadline test in the search is a `break`, a `raise` or a
    # `complete = False`, never an extension of the loop bound -- so
    # removing it makes the player deliver the depth it was asked for
    # instead of a load-dependent fraction of it.
    'the move clock in a game whose rules have none': 'UNSOUND',
    # DECLARED BEFORE THE CODE, 2026-10-25. The m,n,k window chooses
    # and applies in one call and the UI loop calls it directly, so for
    # the whole search no event is read -- undo, redo, the mode buttons
    # and the close box all do nothing. Royal Chess had exactly this
    # defect and fixed it (`src/ai_controller.py`,
    # `tests/test_async_thinking.py`); m,n,k never got the same
    # treatment, and removing the clock made its freeze longer.
    #
    # IDENTICAL, because the only thing that changes is WHEN the loop
    # reads events: the same searcher runs on the same position and
    # returns the same move, and the same grader grades it.
    #
    # AND IT IS ONLY IDENTICAL BECAUSE THE CLOCK IS GONE. With a wall
    # budget, moving the search onto a worker would have changed its
    # timing -- the GIL hand-off alone cost measured frames in the
    # Royal Chess version -- and therefore its depth, and therefore its
    # move. The certificate would have been unavailable. That is the
    # order these two changes have to happen in, and it is not a
    # coincidence worth leaving unrecorded.
    'm,n,k window thinking off the UI thread': 'IDENTICAL',
    # DECLARED BEFORE THE CODE, 2026-10-25. `grade` runs an exact
    # solver to label the move "(optimal)" or "(NOT optimal)", and it
    # ran after the move was ALREADY CHOSEN -- so the move could not
    # appear until the label did. Measured: 8.98 s on a full 4x4 board,
    # which is the window's own default, 7.72 s at 15 empty cells on
    # 5x5 and over 20 s at 16.
    #
    # The grade is an ANNOTATION, not part of choosing a move. So it
    # comes off the move's critical path: choose, land, show, and fill
    # the verdict in when it arrives.
    #
    # IDENTICAL on what is eventually shown -- the move played and the
    # note once the verdict has landed are the same strings the
    # blocking version produced. Only the moment the label appears
    # changes.
    #
    # NOT "lower GRADE_CELL_LIMIT", which was the obvious move and is
    # a trade: it removes a verdict the window used to show. With the
    # annotation off the critical path the threshold only has to stop a
    # runaway, so it is left alone and nothing is taken away.
    'the exact grade on the move critical path': 'IDENTICAL',
    # DECLARED BEFORE THE CODE, 2026-10-25. Removing the move clock
    # left a real residual: the configured depth was 3 for every board,
    # and on 19x19 k=5 a depth-3 move costs 46.70 s worst case, where
    # the 5-second clock had been quietly delivering depth 2. So the
    # default depth becomes a function of the board.
    #
    # MONOTONE, on TWO quantities at once, both against the player as
    # it shipped before this session (depth 3, 5 s clock):
    #
    #   depth completed   D(board) >= the depth the clocked player
    #                     delivered, at every position on that board
    #   worst move time   <= the clock's own budget
    #
    # Both discharge from the measured table plus one control-flow
    # fact: the clocked player could not exceed min(3, whatever fits in
    # 5 s), because every deadline test is a `break` and `max_depth`
    # capped it at 3. Choosing D(board) as exactly that maximum makes
    # the first invariant an equality and the second a strict decrease
    # on every board measured.
    #
    # WHAT IS NOT CLAIMED: that the move is identical. Where the old
    # clock's last iteration was partial, the answers can differ, and
    # "deeper is better" is not available as an argument here -- which
    # is why D is capped at the old `max_depth` rather than raised to
    # whatever now fits.
    'the default depth is read from the board': 'MONOTONE',
    # DECLARED BEFORE THE CODE, 2026-10-25. Royal Chess key presses are
    # laggy while the computer thinks, and the cause is not the
    # threading -- it is the frame. `show_pieces` calls
    # `pygame.image.load` for EVERY PIECE on EVERY FRAME, a PNG decode
    # from disk, plus a load-and-smoothscale for every overlay.
    #
    # Measured: 5.57 ms of a 5.15 ms frame is `show_pieces`, and the
    # frame goes to 47.75 ms while a search runs, because both threads
    # then want a whole core. A key press waits behind that frame, so
    # the frame cost IS the input latency.
    #
    # MEASURED FIRST, and the obvious knobs were measured and REFUSED:
    # a 16 ms frame limiter makes it WORSE (69.0 ms against 47.7 ms),
    # and a 0.2 ms switch interval buys the median (14.7 ms) but costs
    # the search 41% of its wall time and worsens the tail. Neither is
    # the fix. Making the frame cheap is.
    #
    # IDENTICAL, and in the strongest available form: the rendered
    # frame is compared PIXEL FOR PIXEL against the uncached renderer.
    # A texture path's file does not change while the window is open
    # and a smoothscale to a fixed size is deterministic, so a cache
    # returns the same pixels by construction -- but the licence is the
    # comparison, not the reasoning.
    'the per-frame texture decode': 'IDENTICAL',
    # DECLARED BEFORE THE CODE, 2026-10-25, at the reviewer's
    # instruction: "the clock was never a good idea in the first place
    # because it only took away from the depth and unnecessarily
    # introduced lots of bias and error-prone bugs with the evaluation
    # and whatnot. It should be off, so you should remove it now."
    #
    # So the plumbing goes, not just the default. Out: the `budget`
    # parameter, the deadline threaded through `_root`, `_search` and
    # `_quiesce`, the `_OutOfTime` exception, the `nodes % 32` clock
    # test, and the partial-iteration guard with its `abandoned`
    # counter.
    #
    # IDENTICAL, and the premise is unusually clean: with no finite
    # budget anywhere, every one of those tests is
    # `time.time() >= float('inf')`, which is never true. The branches
    # are DEAD, and removing dead branches cannot change a decision.
    # Discharged by comparing chosen moves and node counts against the
    # pre-removal implementation recovered from git.
    #
    # NOTE WHAT THIS GIVES UP, since it was argued the other way
    # earlier in this session: a timed match can no longer be run
    # without putting a clock back. The reviewer weighed that and chose
    # removal, and the record says so rather than pretending the trade
    # was free.
    'the move clock plumbing': 'IDENTICAL',
}

#: Switches that reach the player but are OFF. A switch that is off
#: today is a switch somebody turns on, so it is listed rather than
#: omitted -- an omission is indistinguishable from an oversight.
OFF = (
    # BOTH HALVES OF THE TIE-BREAK, and for DIFFERENT reasons, which is
    # why they are listed separately. §1a (threat level) is admissible
    # and INERT -- see `test_the_threat_tie_break_is_structurally_inert`.
    # §1b (centrality) is the only half that can act and has no
    # invariant. `candidate-designs.md` §1 has both arguments.
    'play_mnk.TIE_BREAK_ENABLED',
    'tie-break threat level (admissible, inert)',
    'tie-break centrality level (no invariant)',
    'features.mnk use_reach',
    'features.royal_chess see_intersection_boulder',
    'features EndgamePinned',
    'features BoulderPressure',
)


def test_every_proven_certificate_matches_the_class_it_was_designed_for():
    """THE CHECK AGAINST FITTING THE ARGUMENT TO THE CODE.

    Every certificate proven in this file reports its kind. That kind
    must equal the one declared before the change was built. A change
    that proves a weaker argument than it was designed for has not
    earned a relabelling -- it has failed, and belongs back at the
    design step.
    """
    # RUN THEM HERE rather than trusting file order: a check that
    # depends on another test having run first is a check that passes
    # for the wrong reason the day somebody runs one test alone.
    for certify in (test_the_extraction_rewrite_is_identical,
                    test_late_move_reduction_removal_is_an_unsound_premise,
                    test_the_board_copy_is_identical,
                    test_jumping_is_identical_to_stepping,
                    test_the_cheap_threat_check_is_identical_to_the_general_one,
                    test_the_move_clock_is_an_unsound_premise,
                    test_removing_the_clock_plumbing_is_identical,
                    test_thinking_off_the_ui_thread_is_identical,
                    test_the_exact_grade_is_off_the_move_critical_path,
                    test_the_default_depth_read_from_the_board_is_monotone,
                    test_the_texture_cache_renders_identical_pixels,
                    test_futility_removal_is_an_unsound_premise):
        try:
            certify()
        except Exception as trouble:         # pragma: no cover
            if 'skip' in type(trouble).__name__.lower():
                continue
            raise

    proven = dict(PROVEN)
    missing = sorted(set(DECLARED) - set(proven))
    assert not missing, (
        'declared but never proven in this file: {0}'.format(missing))
    for subject, kind in sorted(DECLARED.items()):
        assert proven[subject] == kind, (
            '{0} was designed as {1} and only proves {2}; redesign it '
            'rather than relabel it'.format(subject, kind,
                                            proven[subject]))


def test_every_switch_is_either_proven_or_recorded_off():
    """ON requires an argument; OFF requires an entry. Neither may be
    silence."""
    for name in OFF:
        assert name not in DECLARED, (
            '{0} is listed as off and also claims a certificate'.format(
                name))
    assert set(DECLARED) & set(OFF) == set()
    assert len(DECLARED) + len(OFF) >= 9


def test_the_switches_that_say_off_really_are_off():
    import inspect

    import lgref.play_mnk as play
    from lgref.experiments.features import mnk, royal_chess

    assert play.TIE_BREAK_ENABLED is False
    assert inspect.signature(mnk).parameters['use_reach'].default is False
    assert inspect.signature(royal_chess).parameters[
        'see_intersection_boulder'].default is False


def test_a_gate_may_refuse_but_never_licence():
    """THE INVERSION THIS FILE EXISTS FOR. `strictly_better` returning
    nothing means nothing was DETECTED, at the power that run had, on
    the phases it reached. It is not a licence, and the one place that
    says so must keep saying it."""
    from lgref.experiments.validate import strictly_better

    quiet = certificate.gate_may_only_refuse(
        strictly_better({'x': (0.5, 0.0, 400)}, {'x': (0.5, 0.0, 400)}))
    assert quiet == []

    def flattened(text):
        return ' '.join(text.lower().split())

    text = flattened(certificate.gate_may_only_refuse.__doc__)
    assert 'not a licence' in text
    assert 'nothing was detected' in text

    module = flattened(certificate.__doc__)
    assert 'may never licence' in module or 'may never license' in module
