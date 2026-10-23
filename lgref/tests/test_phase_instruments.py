"""Measuring a change PER PHASE, and the gate that uses it.

WHY THIS FILE EXISTS. A reviewer's warning, after a change shipped on a
race and turned out worse in play:

    *Winning a race does not mean the player is strictly better.*

A race reports an aggregate over positions. `Reach:j` fixed the m,n,k
opening -- on a large board the plain line count saturates and ties
across every cell of the middle, so nothing in the evaluation could
prefer the centre -- and the same reviewer found the midgame worse.
Both are true, and an aggregate reports whichever effect is larger.

So the phases are measured apart, by three instruments, because one
does not reach them all; and `strictly_better` is the gate, which is
cleared only by losing nothing.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from lgref.experiments.mnk import MNK
from lgref.experiments.validate import (_setup_plies, forced_move_rate,
                                        forced_turns,
                                        optimal_rate_by_phase,
                                        strictly_better, tie_rate)


def board(m=5, n=5, k=4):
    def make(_variant='full', max_turns=None):
        return MNK(m=m, n=n, k=k)
    return make


# ---- sampling a phase at all ---------------------------------------

def test_a_band_can_name_both_of_its_ends():
    """Without a lower end there is no such thing as a phase: every
    instrument sampled from `min(4, max_setup)` upwards, so an
    'opening' sample and a 'midgame' sample were drawn from overlapping
    populations and a per-phase claim could not be made at all."""
    rng = random.Random(0)
    drawn = set(_setup_plies(rng, 9, 6) for _ in range(200))
    assert drawn <= set(range(6, 10)), drawn
    assert min(drawn) == 6 and max(drawn) == 9
    # The empty board is a legitimate sample for an opening claim.
    assert _setup_plies(random.Random(1), 0, 0) == 0
    # And the old behaviour is untouched when no lower end is given.
    assert set(_setup_plies(rng, 9) for _ in range(200)) <= set(range(4, 10))


def test_a_band_that_cannot_be_satisfied_does_not_raise():
    """`randint(4, 1)` raises, and that defect cost six instruments a
    measurement once already. A lower end above the upper one is the
    same shape of mistake."""
    rng = random.Random(0)
    assert _setup_plies(rng, 2, 7) <= 2
    assert _setup_plies(rng, 1, 1) == 1
    assert _setup_plies(rng, 0, 0) >= 0


# ---- the opening instrument ----------------------------------------

def test_a_flat_evaluation_ties_every_move_and_a_sharp_one_does_not():
    """THE OPENING CANNOT BE GRADED EXACTLY -- the solver costs 88
    seconds at 14 empty cells on this project's own boards. What can be
    measured is whether the evaluation is choosing at all.

    Positive and negative control in one test: a constant score must
    report everything tied, and a score that varies must not.
    """
    make = board(9, 9, 5)
    flat, flat_n = tie_rate(make, lambda game, turn: 0.0, trials=6,
                            seed=1, min_setup=0, max_setup=2)
    assert flat == 1.0 and flat_n == 6

    def sharp(game, turn):
        row, col = divmod(turn, 9)
        return -((row - 4) ** 2 + (col - 4) ** 2)

    tied, asked = tie_rate(make, sharp, trials=6, seed=1, min_setup=0,
                           max_setup=2)
    assert asked == 6
    assert tied < 0.05, tied


def test_the_tie_rate_is_a_necessary_condition_and_not_a_sufficient_one():
    """An evaluation can discriminate confidently and be wrong. The
    docstring says so; this pins it, so nobody reads a low tie rate as
    a competence claim."""
    make = board(5, 5, 4)

    def confidently_wrong(game, turn):
        return turn      # a strict order over cells, and meaningless

    tied, asked = tie_rate(make, confidently_wrong, trials=6, seed=1,
                           min_setup=0, max_setup=2)
    assert asked and tied < 0.2, (
        'a meaningless but strict ordering should still look sharp -- '
        'if it does not, this instrument is measuring something else')


# ---- the midgame instrument ----------------------------------------

def test_a_win_in_front_of_it_is_a_forced_move():
    game = MNK(m=5, n=5, k=4)
    for cell in (0, 10, 1, 11, 2, 12):      # X has three in a row
        game.execute_turn(cell)
    wanted = forced_turns(game)
    assert wanted == [3], wanted


def test_a_loss_in_front_of_it_is_a_forced_move():
    game = MNK(m=5, n=5, k=4)
    # O builds three in a row on the second rank; X must block.
    for cell in (20, 5, 21, 6, 22, 7, 24):
        game.execute_turn(cell)
    wanted = forced_turns(game)
    assert wanted is not None
    assert 8 in wanted, (
        'the only move that stops O completing the line is not among '
        'the forced ones: {0}'.format(wanted))


def test_a_position_where_nothing_can_be_got_wrong_is_not_counted():
    """The same rule `optimal_rate` applies. An empty board has no
    forced move, and counting it would dilute every rate with
    positions that cannot distinguish anything."""
    assert forced_turns(MNK(m=5, n=5, k=4)) is None


def test_the_forced_rate_separates_an_oracle_from_a_coin():
    """POSITIVE AND NEGATIVE CONTROL. An instrument that does not
    separate these two is measuring nothing, and this project has
    shipped on an instrument that did not."""
    make = board(6, 6, 4)

    def oracle(game, _rng):
        wanted = forced_turns(game)
        return wanted[0] if wanted else game.get_all_legal_turns()[0]

    def coin(game, rng):
        return rng.choice(game.get_all_legal_turns())

    good, asked = forced_move_rate(make, oracle, trials=40, seed=3,
                                   min_setup=8, max_setup=24)
    bad, asked_too = forced_move_rate(make, coin, trials=40, seed=3,
                                      min_setup=8, max_setup=24)
    assert asked >= 5 and asked_too >= 5, (asked, asked_too)
    assert good == 1.0, good
    assert bad < 0.5, bad


def test_the_forced_rate_needs_no_solver_and_no_evaluation():
    """It is decided in two plies from the rules, which is the whole
    reason it reaches boards the solver cannot."""
    import inspect

    source = inspect.getsource(forced_turns)
    assert 'optimal_turns' not in source
    assert 'Searcher' not in source


# ---- the gate ------------------------------------------------------

def test_a_change_that_loses_a_phase_does_not_clear_the_gate():
    """THE SHAPE OF THE REACH RESULT: better at one phase, worse at
    another. A race would have reported one number for it.

    The sample sizes are 400 because the gate's own power check
    rejects smaller ones -- at thirty positions a ten-point drop
    cannot be told from noise, and the first version of this test
    asserted a ten-point drop on thirty positions.
    """
    before = {'opening': (0.50, 0.2, 400), 'midgame': (0.40, 0.2, 400)}
    after = {'opening': (0.90, 0.2, 400), 'midgame': (0.30, 0.2, 400)}
    worse = strictly_better(before, after)
    assert [name for name, _why in worse] == ['midgame']
    assert '40.0% -> 30.0%' in dict(worse)['midgame']


def test_a_change_that_loses_nothing_clears_it():
    before = {'opening': (0.50, 0.2, 400), 'midgame': (0.40, 0.2, 400)}
    after = {'opening': (0.90, 0.2, 400), 'midgame': (0.40, 0.2, 400)}
    assert strictly_better(before, after) == []


def test_an_unmeasured_phase_is_not_a_passing_phase():
    """THE ONE THING A GATE MUST NEVER DO is read 'no evidence' as 'no
    problem'. An empty sample is the shape that looks like a pass."""
    before = {'opening': (0.50, 0.2, 30)}
    assert strictly_better(before, {'opening': (0.90, 0.2, 0)})
    assert strictly_better(before, {})
    assert strictly_better({}, {'opening': (0.9, 0.2, 30)})
    assert strictly_better(before, {'opening': (float('nan'), 0.2, 5)})


def test_the_phases_are_measured_from_different_populations():
    """If two bands sample the same positions, a per-phase claim is
    not a claim about phases.

    ON A 3x3, because the exact solver costs 88 seconds at 14 empty
    cells and 0.75 at 12 -- measured. A version of this test on a 4x4
    asked for an EARLY band, which is 14 empty cells, and took minutes
    to assert something about sampling.
    """
    make = board(3, 3, 3)
    seen = {}

    def spy(game, _rng):
        seen.setdefault(id(game), sum(1 for c in game.cells if c))
        return game.get_all_legal_turns()[0]

    out = optimal_rate_by_phase(
        make, spy, [('early', 1, 2), ('late', 5, 6)], trials=12,
        seed=4, cap=9)
    assert set(out) == {'early', 'late'}
    counts = sorted(seen.values())
    assert min(counts) <= 2 and max(counts) >= 5, counts


def test_the_gate_does_not_fail_a_build_against_itself():
    """ZERO IS THE WRONG TOLERANCE for a measured quantity: it makes
    every re-run of the same build fail its own gate. The first run of
    this one flagged 98.5% against 98.4% on sixty samples, where one
    standard error is 1.6 points."""
    assert strictly_better({'opening': (0.985, 0.0, 60)},
                           {'opening': (0.984, 0.0, 60)}) == []


def test_the_gate_still_fails_a_real_regression():
    worse = strictly_better({'midgame': (0.90, 0.0, 200)},
                            {'midgame': (0.70, 0.0, 200)})
    assert [name for name, _why in worse] == ['midgame']
    assert 'noise floor' in dict(worse)['midgame']


def test_a_sample_too_small_to_detect_a_regression_is_not_a_pass():
    """The same rule as an empty sample, one step further in: a gate
    that passes a twenty-point drop because it only saw five positions
    is not a gate. It says UNDERPOWERED, and says what it would take.
    """
    worse = strictly_better({'endgame': (0.90, 0.0, 5)},
                            {'endgame': (0.70, 0.0, 5)})
    assert worse and 'underpowered' in dict(worse)['endgame']
    assert '5' in dict(worse)['endgame']
    # An explicit tolerance is the caller taking responsibility, and
    # then the power check is theirs to make.
    assert strictly_better({'endgame': (0.90, 0.0, 5)},
                           {'endgame': (0.70, 0.0, 5)},
                           tolerance=0.5) == []


# ---- the tempo instrument ------------------------------------------

def test_a_threat_is_a_move_away_from_winning():
    """Read off the rules -- a position from which one legal move ends
    the game in your favour -- rather than off the board. Nothing in
    `threat_count` knows what a line is."""
    from lgref.experiments.validate import threat_count
    import inspect

    game = MNK(m=5, n=5, k=4)
    for cell in (0, 10, 1, 11, 2):          # X has three in a row
        game.execute_turn(cell)
    assert threat_count(game, 'x') == 1     # completing at cell 3
    assert threat_count(game, 'o') == 0
    # And it answers for the side NOT to move, which is the whole point
    # when asking whether a move took a threat away.
    assert game.current_player == 'o'
    source = inspect.getsource(threat_count)
    assert 'line' not in source.lower().split('"""')[2].lower()


def test_tempo_separates_an_active_player_from_a_drifting_one():
    """THE REVIEWER'S WORDS MADE MEASURABLE: "fails to attack
    effectively and wastes tempo". A move that neither makes a threat
    nor removes one is quiet; an instrument that cannot tell a quiet
    player from an active one cannot speak to that complaint."""
    from lgref.experiments.validate import initiative_rate

    make = board(6, 6, 4)

    def coin(game, rng):
        return rng.choice(game.get_all_legal_turns())

    def adjacent(game, rng):
        wanted = forced_turns(game)
        if wanted:
            return wanted[0]
        mine = [i for i, c in enumerate(game.cells)
                if c == game.current_player]
        for cell in game.get_all_legal_turns():
            row, col = divmod(cell, 6)
            for own in mine:
                orow, ocol = divmod(own, 6)
                if abs(row - orow) <= 1 and abs(col - ocol) <= 1:
                    return cell
        return game.get_all_legal_turns()[0]

    drifting, n_one = initiative_rate(make, coin, trials=50, seed=2,
                                      min_setup=4, max_setup=20)
    active, n_two = initiative_rate(make, adjacent, trials=50, seed=2,
                                    min_setup=4, max_setup=20)
    assert n_one >= 20 and n_two >= 20, (n_one, n_two)
    assert active > drifting + 0.1, (active, drifting)


def test_tempo_is_descriptive_and_is_not_in_the_gate():
    """A quiet move is not automatically a bad one -- building towards
    a double threat is quiet until it is not. The tool reports it
    beside the others and does not let it decide anything."""
    source = open(os.path.join(os.path.dirname(__file__), '..', '..',
                               'tools', 'phase_rates.py')).read()
    assert 'descriptive' in source
    # The tempo number may be stored and printed; it may not reach the
    # list the gate is computed from.
    for line in source.splitlines():
        if 'activity' not in line or line.strip().startswith('#'):
            continue
        assert 'worse' not in line, (
            'the tempo number reaches the gate: {0!r}'.format(line))
    gate = [line for line in source.splitlines()
            if 'worse = strictly_better' in line]
    assert gate, 'the gate call moved'


def test_the_sampling_seed_can_be_varied_independently_of_training():
    """THREE RUNS AGREEING IS NOT THREE RESULTS when they share a
    sampling seed: a run with more trials draws a LARGER SAMPLE OF THE
    SAME SEQUENCE, with the small run nested inside the big one. That
    is one run agreeing with itself.

    The sampling seed was fixed at 5 in the tool, so a replication was
    not possible without editing it. It is now a flag, separate from
    the training seed.
    """
    source = open(os.path.join(os.path.dirname(__file__), '..', '..',
                               'tools', 'phase_rates.py')).read()
    assert "'--measure-seed'" in source
    assert 'seed=5' not in source, (
        'an instrument still has the sampling seed hard-coded, so it '
        'cannot be replicated')
    assert 'args.measure_seed' in source
    # And it is reported, because a number whose seed is not recorded
    # cannot be replicated by anyone else either.
    assert 'sampling seed' in source


def test_two_sampling_seeds_draw_different_positions():
    """The flag has to actually change what is measured."""
    make = board(6, 6, 4)
    seen = {}

    def spy(game, _rng, tag=None):
        seen.setdefault(tag, []).append(
            tuple(1 if c else 0 for c in game.cells))
        return game.get_all_legal_turns()[0]

    import functools

    from lgref.experiments.validate import forced_move_rate

    for tag in (5, 99):
        forced_move_rate(make, functools.partial(spy, tag=tag), trials=15,
                         seed=tag, min_setup=6, max_setup=18)
    assert seen.get(5) and seen.get(99)
    assert seen[5] != seen[99], (
        'two sampling seeds drew the same positions')
