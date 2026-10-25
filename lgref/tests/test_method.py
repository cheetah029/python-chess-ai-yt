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
    searcher = Searcher(lambda state, who: 0.5, max_depth=3,
                        budget=20.0, quiescence=0, use_tt=False)
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

    # AND THE OPERATION IS GONE FROM THE DEFAULTS, not merely argued
    # against. A premise that fails while the operation still runs is
    # an essay.
    assert Searcher(lambda _g, _p: 0.5).budget == float('inf')
    assert inspect.signature(Searcher.__init__
                             ).parameters['budget'].default is None
    assert inspect.signature(features.load_royal_chess_searcher
                             ).parameters['budget'].default is None
    assert inspect.signature(play.make_player
                             ).parameters['budget'].default == float('inf')
    assert Game.TD_BUDGET_SECONDS is None

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


def test_a_clock_could_only_ever_take_depth_away():
    """THE PROPERTY THE REMOVAL RESTS ON, checked rather than asserted.

    Every deadline test in the search is a `break`, a `raise` or a
    `complete = False`; none of them extends `range(1, max_depth + 1)`.
    So the iterations a clocked search completes are a PREFIX of the
    iterations it completes without one -- at every position, on every
    board, under every load. A budget cannot buy a ply.

    This is NOT the inadmissible "deeper is better" argument. The
    configured depth is unchanged; what changes is whether the player
    actually delivers it.
    """
    import random

    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    def flat(_engine, _perspective):
        return 0.5

    rng = random.Random(5)
    checked = 0
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
            free = Searcher(flat, max_depth=3, quiescence=0)
            free.choose_turn(turns, game)
            assert free.depth_reached == 3, (
                'no clock must reach the configured depth, got '
                '{0}'.format(free.depth_reached))
            assert free.abandoned == 0, (
                'without a clock no iteration can be partial, so none '
                'can be abandoned')
            for budget in (0.05, 0.5):
                clocked = Searcher(flat, max_depth=3, budget=budget,
                                   quiescence=0)
                clocked.choose_turn(turns, game)
                assert clocked.depth_reached <= free.depth_reached, (
                    'a {0}s clock reached depth {1} where no clock '
                    'reached {2} on {3}x{4} at {5} marks -- the clock '
                    'is not only a reducer and the removal needs a '
                    'different argument'.format(
                        budget, clocked.depth_reached,
                        free.depth_reached, m, n, marks))
                checked += 1
    assert checked >= 12, checked


def test_the_royal_chess_clock_was_inert_at_the_shipped_depth():
    """NOT A CLASS, A FACT, and recorded as one.

    On the case study the 30-second budget never fired at `TD_DEPTH`:
    the clocked and unclocked searches visit identical node counts and
    choose identical moves. So removing it is free on an idle machine,
    and the thing it removes is the BUSY-machine behaviour, where the
    clock silently drops a ply for reasons outside the position.

    Kept small on purpose -- the full five-position sweep takes about
    a minute, and the finding is a yes/no.
    """
    import os

    from experiments.variants import make_engine
    from lgref.experiments.features import load_royal_chess_searcher

    weights = os.path.join(os.path.dirname(__file__), '..', 'weights',
                           'td_royal_chess.json')
    if not os.path.exists(weights):
        pytest.skip('shipped weights not present')

    engine = make_engine('full', max_turns=400)
    turns = engine.get_all_legal_turns()

    clocked = load_royal_chess_searcher(weights, budget=30.0, max_depth=3)
    first = clocked.choose_turn(turns, engine)
    free = load_royal_chess_searcher(weights, max_depth=3)
    second = free.choose_turn(turns, engine)

    assert clocked.depth_reached == free.depth_reached == 3
    assert clocked.nodes == free.nodes, (
        'the 30s clock fired after all: {0} nodes clocked against '
        '{1} free'.format(clocked.nodes, free.nodes))
    assert repr(first) == repr(second)


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
                       depth=2, budget=1.0)
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
    assert (inspect.signature(play.play_window)
            .parameters['move_budget'].default == 0)


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
                       depth=2, budget=1.0)
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
}

#: Switches that reach the player but are OFF. A switch that is off
#: today is a switch somebody turns on, so it is listed rather than
#: omitted -- an omission is indistinguishable from an oversight.
OFF = (
    'play_mnk.TIE_BREAK_ENABLED',
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
                    test_thinking_off_the_ui_thread_is_identical,
                    test_the_exact_grade_is_off_the_move_critical_path,
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
