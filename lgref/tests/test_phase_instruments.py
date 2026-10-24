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


def test_tempo_is_in_the_gate_because_the_reviewer_put_it_there():
    """THIS TEST USED TO ASSERT THE OPPOSITE, and the reason it changed
    is worth keeping.

    Tempo was reported and not gated, on the grounds that a quiet move
    is not automatically a bad one -- building towards a double threat
    is quiet until it is not. That argument is real. It was also never
    mine to settle, and the reviewer settled it:

        "Do not make any later versions fix the opening moves while
        simultaneously compromising everything else and all the good
        moves it makes afterwards. Reach did exactly that and so it
        was overall more ineffective than the original."

    A tempo regression is a failing result for m,n,k, whatever else the
    change buys. The instrument's own docstring still says it describes
    a style rather than judging it -- that remains true, and is why the
    judgement is recorded here as the reviewer's rather than as the
    instrument's.
    """
    source = open(os.path.join(os.path.dirname(__file__), '..', '..',
                               'tools', 'phase_rates.py')).read()
    assert "measured[label]['midgame (tempo)']" in source, (
        'the tempo number no longer reaches the gate')
    assert '(descriptive)' not in source, (
        'the tempo row is still labelled descriptive')
    # And the reason is in the file, not only in a commit message.
    assert 'reviewer' in source.lower()


def test_the_gate_fails_a_change_that_trades_the_midgame_for_the_opening():
    """THE REACH SHAPE, which is the thing being guarded against:
    better at the opening, worse in the midgame. The gate must report
    the loss rather than netting it off against the gain."""
    before = {'opening (sharpness)': (0.60, float('nan'), 900),
              'midgame (tempo)': (0.73, float('nan'), 1680)}
    after = {'opening (sharpness)': (0.95, float('nan'), 900),
             'midgame (tempo)': (0.68, float('nan'), 1680)}
    worse = strictly_better(before, after, detectable=0.04)
    assert [name for name, _why in worse] == ['midgame (tempo)'], worse


def test_the_gate_does_not_pass_a_run_too_small_to_see_the_real_regression():
    """THE NUMBER THAT WOULD HAVE LET REACH THROUGH. Its tempo cost is
    4.6 points, and a single 1500-trial run gives n=859 a side, where
    the noise floor is 4.4. At the default `detectable` of ten points
    the gate calls that a pass -- it cannot see a four-point drop and
    says nothing about it.

    Told that four points matter, it reports the run as UNDERPOWERED
    instead, which is the honest answer: run it again with another
    seed. Pooling two seeds (n=1680) is what actually resolved it.
    """
    before = {'midgame (tempo)': (0.729, float('nan'), 859)}
    after = {'midgame (tempo)': (0.686, float('nan'), 859)}

    assert strictly_better(before, after) == [], (
        'the default is no longer lax -- rewrite this test around the '
        'new default rather than deleting it')

    worse = strictly_better(before, after, detectable=0.04)
    assert worse and 'underpowered' in dict(worse)['midgame (tempo)']

    # Pooled over two sampling seeds, the same difference resolves.
    pooled_before = {'midgame (tempo)': (0.732, float('nan'), 1680)}
    pooled_after = {'midgame (tempo)': (0.686, float('nan'), 1680)}
    resolved = strictly_better(pooled_before, pooled_after,
                               detectable=0.04)
    assert resolved and 'underpowered' not in dict(resolved)[
        'midgame (tempo)'], resolved


def test_the_tool_tells_the_gate_how_big_a_regression_matters():
    source = open(os.path.join(os.path.dirname(__file__), '..', '..',
                               'tools', 'phase_rates.py')).read()
    assert 'detectable=0.04' in source, (
        'the gate runs at its lax default, which cannot see the '
        'regression it exists to catch')


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


def test_the_comparison_pools_over_training_seeds():
    """TRAINING ONCE PER ARM MEASURES THE TRAINING RUN, NOT THE FEATURE
    SET, and on this game the difference between runs swamps the
    difference between feature sets. Measured on 13x13 k=5 at 1500
    trials:

        train seed 11   Reach 4.6 points of tempo WORSE, identical
                        on opening sharpness and forced-move answering
        train seed 23   Reach 13.1 points of opening sharpness and
                        4.5 points of forced answering BETTER, tempo
                        inside the floor

    Same comparison, opposite verdict. A gate that trains once reports
    whichever run it happened to draw, and I published the seed-11
    numbers as though they described `Reach:j`.

    So the tool takes several training seeds and pools them by COUNT --
    summing hits and positions rather than averaging rates, so a seed
    that sampled few qualifying positions does not weigh the same as
    one that sampled many.
    """
    import subprocess

    source = open(os.path.join(os.path.dirname(__file__), '..', '..',
                               'tools', 'phase_rates.py')).read()
    assert "'--train-seeds'" in source
    assert 'hits[phase] += rate * count' in source, (
        'the pooling averages rates rather than summing counts')

    done = subprocess.run(
        [sys.executable, 'tools/phase_rates.py', '4', '4', '3',
         '--rounds', '1', '--games', '4', '--trials', '8',
         '--cap', '10', '--train-seeds', '11,23'],
        cwd=os.path.join(os.path.dirname(__file__), '..', '..'),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    out = done.stdout.decode()
    assert 'seed 11' in out and 'seed 23' in out, out[-600:]
    assert out.count('POOLED') == 2, (
        'each arm should report one pooled row:\n' + out[-600:])
    assert 'train seeds 11,23' in out, (
        'the run does not record which seeds it trained on')


def test_a_tie_break_cannot_change_a_move_the_evaluation_can_separate():
    """THE CONFINEMENT PROPERTY, which is the whole reason the opening
    fix lives in the search rather than in the evaluation.

    A feature changes every value everywhere, and the last attempt to
    fix the m,n,k opening that way (`Reach:j`) cost 2.4 points of
    midgame tempo across four training seeds. A tie-break is consulted
    only between root moves the search values IDENTICALLY, so where the
    evaluation has an opinion it is never asked.
    """
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    game = MNK(m=4, n=4, k=3)

    # An evaluation with a strict opinion about every cell.
    def opinionated(state, perspective):
        return 0.5 + 0.001 * sum(i for i, c in enumerate(state.cells)
                                 if c == perspective)

    plain = Searcher(opinionated, max_depth=1, budget=5.0,
                     quiescence=0, use_tt=False)
    # A tie-break that would prefer the exact opposite move if asked.
    tilted = Searcher(opinionated, max_depth=1, budget=5.0,
                      quiescence=0, use_tt=False,
                      tie_break=lambda turn: -turn)
    turns = game.get_all_legal_turns()
    assert plain.choose_turn(turns, game) == tilted.choose_turn(
        turns, game), (
        'the tie-break changed a decision the evaluation had already '
        'made')


def test_a_tie_break_decides_when_the_evaluation_is_indifferent():
    """And it must actually do something where the evaluation ties, or
    it is not a fix."""
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    game = MNK(m=4, n=4, k=3)
    flat = lambda state, perspective: 0.5
    turns = game.get_all_legal_turns()

    plain = Searcher(flat, max_depth=1, budget=5.0, quiescence=0,
                     use_tt=False).choose_turn(turns, game)
    wanted = max(turns)
    tilted = Searcher(flat, max_depth=1, budget=5.0, quiescence=0,
                      use_tt=False,
                      tie_break=lambda turn: turn).choose_turn(turns,
                                                               game)
    assert tilted == wanted, (tilted, wanted)
    assert plain != wanted, (
        'the two agree by accident, so this proves nothing')


def test_the_tie_break_is_general_and_knows_no_game():
    """It takes a turn and returns a number. The Searcher is in the
    audited set, so this is belt and braces -- but the point is that
    the m,n,k prior is SUPPLIED to it, not built into it."""
    import inspect

    from lgref.experiments.search import Searcher

    source = inspect.getsource(Searcher.__init__)
    assert 'tie_break' in source
    body = inspect.getsource(Searcher._root)
    assert 'self.tie_break(' in body
    for word in ('Line', 'cell', 'centre', 'center', 'board'):
        assert word not in body.replace('tie_break', ''), word
