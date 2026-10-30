"""The guarantees that made the opening fix safe, as standing tests.

THE STANDING REQUIREMENT: "ensure everything you have done is strictly
better and doesn't disimprove anything."

A gate run says a change lost nothing ON THE DAY. It cannot stop
someone removing the property that made that true. These tests pin the
properties themselves, behaviourally, so the guarantee survives the
next edit:

  1. a tie-break never changes a decision the evaluation can make;
  2. past `k` marks the opening prior is silent, because a prior
     learned over whole games misleads where concrete play decides --
     measured at 0.9 points of endgame optimal-action rate, down on
     all four training seeds;
  3. where the tie-break DOES change a move, the new move is at least
     as active as the old -- which is why tempo came back identical
     rather than merely within noise.

Each number in those sentences came from a run that refused a change.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import lgref.play_mnk as play
from lgref.experiments.mnk import MNK
from lgref.experiments.search import Searcher
from lgref.experiments.validate import threat_count


def board(m=5, n=5, k=4):
    return MNK(m=m, n=n, k=k)


def sampled(count, m=5, n=5, k=4, seed=7, marks=None):
    """Positions reached by random play, optionally with at least
    `marks` stones down."""
    rng = random.Random(seed)
    out = []
    while len(out) < count:
        game = board(m, n, k)
        for _ply in range(rng.randint(0, m * n - 2)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over() or len(game.get_all_legal_turns()) < 2:
            continue
        if marks is not None:
            if sum(1 for cell in game.cells if cell) < marks:
                continue
        out.append(game)
    return out


def flat(_state, _perspective):
    return 0.5


def opinionated(state, perspective):
    """An evaluation with a strict opinion about every position.

    IT HAS TO READ BOTH SIDES. A first version summed only the
    perspective player's cells -- and the search evaluates each child
    from the OPPONENT's perspective, whose cells a move does not
    change, so every root move scored identically and the fixture was
    measuring a tie rather than an opinion.
    """
    mine = sum(i for i, c in enumerate(state.cells) if c == perspective)
    theirs = sum(i for i, c in enumerate(state.cells)
                 if c and c != perspective)
    return 0.5 + 0.00001 * (mine - theirs)


def test_a_tie_break_never_overrides_an_evaluation_with_an_opinion():
    """THE CONFINEMENT. Where the evaluation can separate two moves it
    is never asked, which is what makes the opening fix unable to
    regress the rest of the game."""
    prior = play.opening_prior(5, 5, 4)
    for game in sampled(12):
        turns = game.get_all_legal_turns()
        plain = Searcher(opinionated, max_depth=1, quiescence=0, use_tt=False)
        tilted = Searcher(opinionated, max_depth=1, quiescence=0, use_tt=False,
                          tie_break=play.tie_breaker(game, prior))
        assert plain.choose_turn(turns, game) == tilted.choose_turn(
            turns, game)


def test_the_prior_is_silent_once_a_line_could_exist():
    """BOUNDED BY THE WIN CONDITION, not by a number anyone chose.
    Below `k` marks no line can be completed by anybody, so there is
    no concrete calculation for a general statistic to contradict."""
    prior = play.opening_prior(5, 5, 4)
    for game in sampled(10, marks=4):
        rank = play.tie_breaker(game, prior)
        squares = set(rank(turn)[1] for turn in
                      game.get_all_legal_turns())
        assert squares == {0.0}, (
            'the prior still speaks at {0} marks'.format(
                sum(1 for cell in game.cells if cell)))


def test_the_prior_speaks_while_no_line_is_possible():
    prior = play.opening_prior(5, 5, 4)
    game = board()
    game.execute_turn(12)
    rank = play.tie_breaker(game, prior)
    squares = set(rank(turn)[1] for turn in game.get_all_legal_turns())
    assert len(squares) > 1, 'the prior is silent where it is wanted'


def test_a_changed_move_is_never_less_active_than_the_one_it_replaced():
    """WHY TEMPO CAME BACK IDENTICAL rather than merely within noise.
    Ranking tied moves by the square alone cost 0.8 points of tempo,
    down on all four training seeds. Preferring an active move first
    means a tie that used to pick one by chance now picks one whenever
    the tie contains one -- so the rate can only rise.
    """
    prior = play.opening_prior(5, 5, 4)
    checked = changed = 0
    for game in sampled(25, seed=11):
        turns = game.get_all_legal_turns()
        plain = Searcher(flat, max_depth=1, quiescence=0,
                         use_tt=False).choose_turn(turns, game)
        rank = play.tie_breaker(game, prior)
        tilted = Searcher(flat, max_depth=1, quiescence=0,
                          use_tt=False,
                          tie_break=rank).choose_turn(turns, game)
        checked += 1
        if plain == tilted:
            continue
        changed += 1
        assert rank(tilted)[0] >= rank(plain)[0], (
            'the tie-break swapped an active move for a quiet one')
    assert checked and changed, (
        'the tie-break never changed anything here, so this proves '
        'nothing')


def test_the_recorded_floor_names_what_a_later_version_must_beat():
    """A baseline nobody wrote down is a baseline nobody can be held
    to."""
    import re

    record = open(os.path.join(os.path.dirname(__file__), '..',
                               'weights', 'APPROVED.md')).read()
    section = record.split('## m,n,k')[1]
    assert 'floor a later' in section
    numbers = re.findall(r'\d+\.\d+%', section)
    assert len(numbers) >= 3, (
        'the m,n,k floor records fewer than three measured phases')


def test_the_gate_still_refuses_a_change_that_trades_phases():
    """The instrument that refused two earlier forms of this very fix
    must still refuse that shape."""
    from lgref.experiments.validate import strictly_better

    traded = strictly_better(
        {'opening': (0.61, float('nan'), 2400),
         'endgame': (0.996, float('nan'), 936)},
        {'opening': (0.76, float('nan'), 2400),
         'endgame': (0.987, float('nan'), 936)},
        detectable=0.04)
    assert [name for name, _why in traded] == ['endgame'], traded


def test_the_player_does_not_use_the_tie_break_until_it_is_proven():
    """REVERTED AT THE REVIEWER'S INSTRUCTION, and this is the test
    that keeps it reverted.

    Every gate number quoted for the tie-break -- +7.0 points of
    opening placement on 13x13, nothing lost elsewhere -- was measured
    while the tie-break itself cost 0.108s per ranked candidate. The
    search could not finish one ply on a 19x19 board, so those runs
    describe an agent reduced to depth 1 BY THE THING BEING MEASURED.
    A number measured on a crippled search is not weaker evidence; it
    is evidence about a different agent.

    The code and its tests stay, because the defect it addresses is
    real and measured. The PLAYER does not use it until a gate run
    against the repaired search says it loses nothing.
    """
    assert play.TIE_BREAK_ENABLED is False, (
        'the tie-break is on; it may only be switched on by a gate run '
        'against a search that works, and APPROVED.md must record it')

    import inspect
    source = inspect.getsource(play.play_window)
    assert 'TIE_BREAK_ENABLED' in source, (
        'the window no longer consults the switch')


def test_turning_it_on_is_one_line_and_still_works():
    """A revert that rots is a revert nobody can undo. The switch has
    to still do what it says."""
    from lgref.experiments.mnk import MNK

    prior = play.opening_prior(9, 9, 5)
    game = MNK(m=9, n=9, k=5)
    rank = play.tie_breaker(game, prior)
    centre = rank(4 * 9 + 4)
    corner = rank(0)
    assert centre[1] > corner[1], (
        'the tie-break no longer prefers the centre, so switching it '
        'back on would restore nothing')
