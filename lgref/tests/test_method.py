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
