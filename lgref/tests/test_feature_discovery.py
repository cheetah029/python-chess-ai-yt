"""Inferring what matters instead of being told (#268).

Royal Chess's declared objective is flat almost everywhere, and material
-- which is what actually separates midgame moves -- is nowhere in the
rules. So either a researcher supplies that fact, which fails the
cross-game constraint, or the agent infers it from outcomes. This module
does the inference; these tests pin what it found, including the parts
that say the inference is not yet usable.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.discover import (NEUTRAL_COLOURS, Trace, collect,
                                        conditional, confound_report,
                                        differentials, rank)
from lgref.experiments.features import royal_chess as piece_features
from lgref.experiments.iterate import weights_from


def test_features_are_generated_from_the_position_not_listed():
    """No piece name is hard-coded, so another game yields other features."""
    engine = make_engine('full', max_turns=100)
    feats = piece_features(engine)
    assert feats, 'no features generated'
    kinds = {kind for _colour, kind in feats}
    assert 'Pawn' in kinds and 'Royal' in kinds
    # Both colours appear, and nothing claims a value for any of them.
    assert {c for c, _k in feats} == {'white', 'black', None} - {None} or \
        {'white', 'black'} <= {c for c, _k in feats}


def test_differentials_are_mover_relative():
    """A raw count cannot order positions between players."""
    feats = {('white', 'Rook'): 2, ('black', 'Rook'): 1}
    assert differentials(feats, 'white')['Rook'] == 1
    assert differentials(feats, 'black')['Rook'] == -1


def test_the_neutral_boulder_is_not_a_differential_feature():
    """A piece belonging to neither player cannot have a mover-relative
    value, and this one was being given the same one for both players.

    `Board` spells the boulder's colour as the STRING `'none'`, so the
    `is None` guard in `differentials` missed it and it was scored as an
    enemy of whoever was to move: -1 for white and -1 for black in the
    same position. That is a constant dressed as a feature.

    It measured d = 0.000 under random play, which is why it survived --
    but for the wrong reason. The differential is not structurally
    constant: a king may capture the boulder (RULEBOOK.md, King), and
    the boulder is also absent from the squares while it sits on the
    central intersection. So the feature really tracked "the boulder has
    left the centre", with the same sign for both sides, and read zero
    only because random play rarely disturbs it.
    """
    engine = make_engine('full', max_turns=100)
    feats = piece_features(engine)
    # The boulder is still ENUMERATED -- the vocabulary is read off the
    # board, not filtered by a list of names.
    neutral = [(c, k) for c, k in feats if c in NEUTRAL_COLOURS]
    # ... but it must not reach a mover-relative score.
    for mover in ('white', 'black'):
        assert 'Boulder' not in differentials(feats, mover)
    # And the same holds once it is actually on a square.
    placed = dict(feats)
    placed[('none', 'Boulder')] = 1
    white = differentials(placed, 'white')
    black = differentials(placed, 'black')
    assert 'Boulder' not in white and 'Boulder' not in black
    assert neutral == [] or all(k == 'Boulder' for _c, k in neutral)


def test_a_constant_feature_earns_no_weight():
    """The control that makes the rest credible.

    A feature with the same value in won and lost states carries no
    information, and the procedure must report none rather than invent
    one. This replaces the boulder, which used to serve as this control
    while itself being a bug.
    """
    traces = [Trace(features={'flat': 3}, winner='white',
                    mover='white' if i % 2 else 'black', ply=i * 4,
                    game=i)
              for i in range(20)]
    findings = rank(traces, min_count=10, min_games=8)
    flat = {f.feature: f for f in findings}['flat']
    assert abs(flat.separation) < 1e-9
    assert abs(flat.auc - 0.5) < 1e-9
    assert weights_from(findings) == {}, 'a constant feature got a weight'


def test_a_transformation_changes_no_material():
    """Form was being counted as material, so a Transformation action --
    which captures nothing -- looked like a capture plus a gain.

    RULEBOOK.md: a queen keeps its identity through a Transformation ("A
    marker indicates which piece is the queen"), and only a king or a
    ROYAL QUEEN is royal. But a transformed queen is an instance of its
    form's class, so `type(piece).__name__` reported the royal queen as
    `Knight*royal` after transforming to knight form. The differential
    swung two units -- `Queen*royal` -1 and `Knight*royal` +1 -- for an
    action that moved no piece and took none.

    The consequence was worse than a misnamed row: NO feature measured
    the quantity the declared objective actually depends on, which is
    whether the royal queen is alive at all.
    """
    engine = make_engine('full', max_turns=100)
    before = differentials(piece_features(engine), 'white')
    for row in range(8):
        for col in range(8):
            piece = engine.board.squares[row][col].piece
            if piece is not None and getattr(piece, 'is_royal', False) \
                    and type(piece).__name__ == 'Queen' \
                    and piece.color == 'white':
                engine.board.transform_queen(piece, row, col, 'knight')
                break
    after = differentials(piece_features(engine), 'white')

    # Identity is untouched by a form change. `Royal` is ONE symmetric
    # count covering the king and the royal queen together, because the
    # terminal condition is symmetric in them -- you win by capturing
    # both -- so the rules draw no distinction and the only signal TD
    # has cannot either. Measured with them split: two trainings
    # differing only in seed gave King +0.281 against Queen +0.236, then
    # King +0.100 against Queen +0.160. The ORDERING REVERSED, so the
    # split was allocating noise rather than learning anything.
    assert after['Royal'] == before['Royal'] == 0
    assert 'RoyalQueen' not in after and 'King*royal' not in after
    # `Royal` REPLACED the per-piece royal features rather than
    # accompanying them, which is why it is no longer collinear with
    # anything. The earlier arrangement had `Royal` alongside
    # `King*royal` and `RoyalQueen`, where it was exactly their sum --
    # TD learned King*royal +0.419 against Royal -0.144 and the king's
    # effective value came out below a rook. Removing the aggregate
    # relocated that arbitrariness onto the two remaining features
    # instead of removing it, and only merging them resolved it.
    # An ordinary knight count must NOT move: the royal queen in knight
    # form is not a knight.
    assert after['Knight'] == before['Knight']
    # The form change is visible, but only in the form features.
    assert after['RoyalForm:Knight'] == 1
    # BASE FORM IS THE DROPPED REFERENCE CATEGORY, so there is no
    # `RoyalQueenForm:Queen` feature at all. A queen is in exactly one
    # form, so the form indicators summed to the identity count --
    # `RoyalQueen` == sum of `RoyalQueenForm:*` -- which is an exactly
    # collinear set. A linear model fitted on it has infinitely many
    # equally good weight vectors, so the split between identity and
    # form was decided by gradient descent's path rather than by the
    # game. Dropping one level is the standard fix, and it means the
    # surviving form features read as "in this form RATHER THAN base".
    assert 'RoyalForm:Queen' not in after
    assert 'RoyalForm:Queen' not in before
    # The identity count is what carries the material, and a form
    # change must leave it alone -- which is the point of this test.
    assert after['Royal'] == before['Royal']


def test_the_sample_is_counted_in_games_not_traces():
    """Traces are clustered, and gating on their count overstated the
    sample by the sampling interval.

    States are sampled every few plies and every state in a game carries
    that game's single outcome, so 880 traces came from 14 games. The
    old gate (`min_count` on traces) admitted `Queen` on 20 traces drawn
    from FOUR games and then reported Cohen's d on it as though it were
    precise. A feature seen in too few games must be dropped however
    large its apparent effect -- round 2 of the first iteration run
    reported d = +2.12 on exactly that basis.
    """
    # One game, many traces: plenty of traces, nowhere near enough games.
    traces = [Trace(features={'rare': i % 3}, winner='white',
                    mover='white' if i % 2 else 'black', ply=i * 4,
                    game='only-one-game')
              for i in range(60)]
    assert rank(traces, min_count=10, min_games=8) == [], (
        '60 traces from a single game passed a games gate of 8')
    # The finding reports the game count, so the clustering is visible.
    spread = [Trace(features={'rare': g % 3}, winner='white',
                    mover='white' if g % 2 else 'black', ply=4, game=g)
              for g in range(20)]
    findings = rank(spread, min_count=10, min_games=8)
    assert findings and findings[0].games == 20


def test_censored_games_are_not_labelled():
    """A game with no winner has no outcome to teach, and calling it a
    draw would teach the opposite of #260's lesson."""
    traces = collect(make_engine, piece_features, games=8, agent='random', seed=2,
                     max_turns=12)
    # Every trace must come from a game that actually finished.
    assert all(t.winner in ('white', 'black') for t in traces)


def test_phase_can_be_held_fixed():
    """Because without it the ranking marks the clock.

    Pawn count tracks how early the game is, and how early it is tracks
    who is about to win. The first run reported `Pawn` at d = -0.547, and
    a naive "learn an evaluation" step would have absorbed that silently.
    """
    traces = collect(make_engine, piece_features, games=20, agent='random', seed=3)
    early = rank(traces, min_count=10, ply_window=(0, 40))
    late = rank(traces, min_count=10, ply_window=(120, 10000))
    assert early and late
    # The two bands are scored on different trace sets.
    assert sum(f.n for f in early) != sum(f.n for f in late)


def test_discovery_under_random_play_is_not_yet_a_usable_evaluation():
    """The honest limit, and the reason this is not wired into the search.

    Measured over 60 random games, 6152 sampled states: ordinary material
    carries almost nothing (Rook d = -0.04, Knight d = -0.03) and the
    strongest feature, `Bishop*royal`, FLIPS SIGN between phases --
    -1.015 at plies 40-120 and +0.886 at 120+.

    The reason is structural: you cannot learn what makes a strong player
    strong from the games of a random one. Random play never converts
    material into royal captures, so material has no measured value in
    its traces. The standard answer is iteration -- learn a weak
    evaluation, play slightly better, re-collect -- which is self-play
    policy iteration and is what the execution brief's Phase 3 asked for.
    """
    traces = collect(make_engine, piece_features, games=24, agent='random', seed=4)
    early = {f.feature: f.separation
             for f in rank(traces, min_count=10, ply_window=(40, 120))}
    late = {f.feature: f.separation
            for f in rank(traces, min_count=10, ply_window=(120, 10000))}
    shared = set(early) & set(late)
    assert shared, 'no feature appeared in both phase bands'
    # At least one feature must disagree across phases; if that ever
    # stops being true the traces have become stable enough to revisit
    # wiring a discovered evaluation into the search.
    flips = [name for name in shared
             if early[name] * late[name] < 0]
    assert flips, (
        'no feature flips sign across phases any more -- the discovery '
        'traces may now be stable enough to use, which is worth '
        'rechecking rather than assuming')


def test_cluster_aggregation_changes_d_in_both_directions():
    """The trace-level estimator did not inflate effects -- it distorted
    them, which is worse because the distortion has no safe direction.

    Measured over 40 random games, trace-level vs cluster-aggregated d:

        RoyalQueenForm:Knight   -0.481  ->  -0.073   (6.5x smaller)
        King*royal              +0.048  ->  +0.215   (4.5x larger)
        RoyalQueenForm:Rook     +0.270  ->  -0.212   (sign flip)

    Shrinking happens where within-game variance was being counted as
    sample; growing happens where that same variance was padding the
    pooled SD and burying a real between-game contrast; and a feature
    whose within- and between-game contrasts disagree can flip outright.
    """
    traces = collect(make_engine, piece_features, games=24, agent='random', seed=11)
    clustered = {f.feature: f.separation
                 for f in rank(traces, min_count=30, min_games=8,
                               cluster=True)}
    trace_level = {f.feature: f.separation
                   for f in rank(traces, min_count=30, min_games=8,
                                 cluster=False)}
    shared = set(clustered) & set(trace_level)
    assert shared, 'no feature survived both estimators'
    assert any(abs(clustered[k] - trace_level[k]) > 0.05 for k in shared), (
        'the two estimators agree everywhere -- if the traces have '
        'stopped being clustered that is worth checking, not assuming')


def test_one_game_cannot_supply_a_pooled_spread():
    """Each game contributes one observation per side, so a single game
    gives one won value and one lost value and no spread at all."""
    traces = [Trace(features={'x': i}, winner='white',
                    mover='white' if i % 2 else 'black', ply=i * 4,
                    game='g')
              for i in range(40)]
    # Gated out on games, as it must be.
    assert rank(traces, min_count=10, min_games=2) == []
    # And with the gate lifted, the spread is degenerate rather than
    # producing a confident-looking number.
    loose = rank(traces, min_count=10, min_games=1)
    assert all(f.separation == 0.0 or f.se == float('inf') for f in loose)


def test_a_large_effect_on_a_small_sample_earns_no_weight():
    """The failure mode every spurious weight here has had.

    Round 2 of the first iteration run made `Knight*royal` the search's
    strongest weight at d = +2.12, from a dozen clustered games. An
    effect-size gate cannot catch that; d against its own standard error
    can.
    """
    # A big separation, but only ten clusters behind it.
    small = [Trace(features={'rare': 1 if g < 5 else 0},
                   winner='white',
                   mover='white' if g < 5 else 'black',
                   ply=4, game=g)
             for g in range(10)]
    findings = rank(small, min_count=5, min_games=8)
    assert findings, 'the feature should be measured, just not trusted'
    big = findings[0]
    assert abs(big.separation) > 1.0, 'expected a large apparent effect'
    assert big.auc == 1.0, 'the groups should separate perfectly'
    # Ten clusters is below the gate, so no weight comes out...
    assert weights_from(findings, min_games=12, min_z=2.0) == {}, (
        'a perfect separation on ten games became a weight')
    # ...and when a weight IS admitted it is bounded, because an
    # unbounded one would override every other feature.
    admitted = weights_from(findings, min_games=8, min_z=2.0,
                            max_weight=3.0)
    assert admitted and all(abs(v) <= 3.0 for v in admitted.values())


def test_the_capture_record_is_part_of_the_vocabulary():
    """It gates which ACTIONS are legal, so leaving it out made a whole
    class of mechanism inexpressible.

    Transformation into a form requires a friendly piece of that type to
    have been captured earlier (RULEBOOK.md, Transformation Action), so
    `captured_pieces` is current legal-move-determining state rather
    than history. Without it in the vocabulary, a THRESHOLD quantity
    ("a friendly bishop has been captured") had no feature at all, and a
    threshold mechanism got attributed to a linear count that cannot
    represent one.
    """
    engine = make_engine('full', max_turns=100)
    before = piece_features(engine)
    assert before[('white', 'FormAvailable:bishop')] == 0

    engine.board.captured_pieces['white'] = ['bishop']
    after = piece_features(engine)
    assert after[('white', 'FormAvailable:bishop')] == 1
    assert after[('black', 'FormAvailable:bishop')] == 0
    # Mover-relative, like every other feature.
    assert differentials(after, 'white')['FormAvailable:bishop'] == 1
    assert differentials(after, 'black')['FormAvailable:bishop'] == -1
    # And no piece count moved: a capture record is not material.
    assert after[('white', 'Bishop')] == before[('white', 'Bishop')]


def test_conditioning_collapses_a_feature_that_is_only_a_proxy():
    """A marginal effect does not say whether a feature has its own
    information or is standing in for something else."""
    traces = []
    for game in range(40):
        hidden = game % 2
        traces.append(Trace(features={'cause': hidden, 'proxy': hidden},
                            winner='white',
                            mover='white' if hidden else 'black',
                            ply=4, game=game))
    marginal = {f.feature: f for f in rank(traces, min_count=10,
                                           min_games=8)}
    # Both look identical marginally, because they are identical.
    assert 'proxy' in marginal and 'cause' in marginal
    # Conditioning `proxy` on `cause` leaves no within-stratum variation
    # at all, so the honest answer is "cannot be measured" rather than a
    # number -- which is the signal to run an intervention.
    assert conditional(traces, 'proxy', 'cause') is None


def test_conditioning_reports_a_number_when_contrast_survives():
    """And pools strata by inverse variance, so a tighter stratum counts
    for more than a plain mean would give it."""
    traces = []
    for game in range(90):
        given = game % 3
        mover_won = (game % 2 == 0)
        # OVERLAPPING within each stratum, so d is finite. A perfectly
        # separating stratum has no spread, d is unbounded, and
        # `conditional` correctly declines to pool it.
        # The noise term must vary INDEPENDENTLY of `given`, or every
        # stratum is internally constant and separates perfectly again.
        noise = game % 4
        value = noise + (2 if mover_won else 0)
        traces.append(Trace(features={'feature': value, 'given': given},
                            winner='white',
                            mover='white' if mover_won else 'black',
                            ply=4, game=game))
    found = conditional(traces, 'feature', 'given', min_stratum=4)
    assert found is not None
    assert found.games > 0
    assert found.separation != 0.0


def test_the_confound_report_labels_what_survives():
    """The table that says which marginal numbers may be quoted alone."""
    traces = collect(make_engine, piece_features, games=24, agent='random', seed=31)
    text, rows = confound_report(
        traces, [('Bishop', 'FormAvailable:bishop')])
    assert 'MARGINAL vs CONDITIONAL' in text
    assert rows, 'the pair was not evaluated'
    _feature, _given, base, cond, verdict = rows[0]
    assert verdict in ('SIGN FLIP', 'COLLAPSES', 'survives', 'NO CONTRAST')
    if cond is not None:
        # Whatever the verdict, it must follow from the two numbers.
        if base.separation * cond.separation < 0:
            assert verdict == 'SIGN FLIP'
        elif abs(cond.separation) < 0.5 * abs(base.separation):
            assert verdict == 'COLLAPSES'
        else:
            assert verdict == 'survives'


def test_threat_features_read_zero_rather_than_vanishing():
    """A failing threat cache must ZERO the two threat features, not
    delete them from the vector.

    `differentials` omits a feature that is absent, and an absent
    feature is invisible to the weights loader's staleness guard --
    which compares NAMES -- so the agent would have gone on playing
    with `Attacked` and `Covers` silently missing. The defaults used to
    sit inside the same `try` as the walk that can fail, which made
    that the behaviour on any failure.
    """
    engine = make_engine('full', max_turns=100)

    class Boom(object):
        def __getattr__(self, name):
            raise AttributeError(name)

    board = engine.board
    original = board.update_threat_squares
    board.update_threat_squares = lambda: Boom().nope
    try:
        counts = piece_features(engine)
    finally:
        board.update_threat_squares = original

    for side in ('white', 'black'):
        assert (side, 'Attacked') in counts, side
        assert (side, 'Covers') in counts, side
        assert counts[(side, 'Attacked')] == 0
        assert counts[(side, 'Covers')] == 0


def test_a_broken_threat_walk_is_not_swallowed():
    """`except Exception` around the walk hid every bug in it, and the
    only symptom was two missing features. A real error must surface."""
    engine = make_engine('full', max_turns=100)
    board = engine.board
    original = board.update_threat_squares

    def explode():
        raise RuntimeError('a real bug, not a missing cache')

    board.update_threat_squares = explode
    try:
        raised = False
        try:
            piece_features(engine)
        except RuntimeError:
            raised = True
        assert raised, 'a genuine error was swallowed'
    finally:
        board.update_threat_squares = original


def test_the_threshold_decomposition_prices_zero_separately():
    """A count cannot price "one of these versus none"; a threshold can.

    This is the defect that produced the agent's signature blunder.
    `Bishop` learned -0.0077 per unit against `Pawn` +0.0501, so the
    evaluation scored "lose a bishop, win a pawn" as +0.047 -- a GAIN --
    and a human saw exactly that trade in play. Going from two bishops
    to one costs a little; going from one to none removes the
    reactive-capture pin entirely, and one coefficient cannot be both.

    Each count becomes `Has:X` plus `More:X` and the RAW COUNT IS
    DROPPED, since X == Has + More and keeping all three would be
    perfect multicollinearity.
    """
    from lgref.experiments.features import with_threshold

    engine = make_engine('full', max_turns=100)
    plain = piece_features(engine)
    split = with_threshold(piece_features)(engine)

    for (owner, name), amount in plain.items():
        assert (owner, name) not in split, (
            'the raw count must be dropped, not kept beside the split')
        assert split[(owner, 'Has:' + name)] == (1 if amount >= 1 else 0)
        assert split[(owner, 'More:' + name)] == max(0, amount - 1)
        assert (split[(owner, 'Has:' + name)]
                + split[(owner, 'More:' + name)]) == amount

    twice = with_threshold(with_threshold(piece_features))(engine)
    assert not any(n.startswith('Has:Has:') or n.startswith('More:Has:')
                   for _o, n in twice)


def test_a_threshold_differential_reads_as_one_side_having_it():
    """`Has:` is split PER OWNER, before differencing, so the
    differential lands in {-1, 0, +1} and reads "I have one of these and
    they do not" -- the comparison that matters at zero."""
    from lgref.experiments.features import with_threshold

    engine = make_engine('full', max_turns=100)
    counts = dict(with_threshold(piece_features)(engine))
    counts[('white', 'Has:Bishop')] = 0
    counts[('white', 'More:Bishop')] = 0
    diffs = differentials(counts, 'black')
    assert diffs['Has:Bishop'] == 1, (
        'black holds a bishop and white does not, so the differential '
        'must be exactly +1, not a count difference')
    assert set(v for k, v in diffs.items()
               if k.startswith('Has:')) <= {-1, 0, 1}


def test_the_threshold_split_is_not_specific_to_the_case_study():
    """It is a wrapper over any extractor, not a piece list."""
    from lgref.experiments.features import mnk as mnk_features
    from lgref.experiments.features import with_threshold
    from lgref.experiments.mnk import MNK

    game = MNK(m=4, n=4, k=3)
    game.cells[0] = 'x'
    game.cells[5] = 'o'
    plain = mnk_features(game)
    split = with_threshold(mnk_features)(game)
    assert len(split) == 2 * len(plain), 'one threshold and one slope each'
    assert any(n.startswith('Has:Line:') for _o, n in split)
    assert any(n.startswith('More:Line:') for _o, n in split)


def test_no_two_features_are_identical_on_a_sample_of_positions():
    """THE GUARD THAT FORCED THE DECOMPOSITION.

    Adding `Has:X` beside the count makes the two columns identical
    whenever X never exceeds 1, and most of these features never do.
    This test found NINE such pairs over 150 sampled positions --
    including `Has:Attacked:Rook`, `Has:Hanging:Pawn` and every boolean
    flag -- which is one weight split in half, with the split decided by
    the optimiser rather than by the game. An attempt to suppress them
    from a declared list of binary features caught two of the nine,
    which is how a declared list usually does.
    """
    import random

    from lgref.experiments.features import with_threshold
    from lgref.experiments.random_play import build

    extractor = with_threshold(piece_features)
    vectors = []
    rng = random.Random(5)
    for seed in range(4):
        engine = make_engine('full', max_turns=400)
        mover = build('random', random.Random(seed), 0)
        for _ply in range(rng.randint(10, 50)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(mover.choose_turn(turns, engine))
            vectors.append(differentials(extractor(engine), 'white'))

    names = sorted(set(n for v in vectors for n in v))
    columns = {n: tuple(v.get(n, 0) for v in vectors) for n in names}
    duplicates = []
    seen = {}
    for name in names:
        column = columns[name]
        if any(column):             # an all-zero column is not a pair
            if column in seen:
                duplicates.append((seen[column], name))
            else:
                seen[column] = name
    assert not duplicates, (
        'identical feature columns over {0} positions: {1}'.format(
            len(vectors), duplicates))
