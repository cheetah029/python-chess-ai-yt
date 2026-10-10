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

from lgref.experiments.discover import (collect, differentials,
                                        piece_features, rank)


def test_features_are_generated_from_the_position_not_listed():
    """No piece name is hard-coded, so another game yields other features."""
    engine = make_engine('full', max_turns=100)
    feats = piece_features(engine)
    assert feats, 'no features generated'
    kinds = {kind for _colour, kind in feats}
    assert 'Pawn' in kinds and 'King*royal' in kinds
    # Both colours appear, and nothing claims a value for any of them.
    assert {c for c, _k in feats} == {'white', 'black', None} - {None} or \
        {'white', 'black'} <= {c for c, _k in feats}


def test_differentials_are_mover_relative():
    """A raw count cannot order positions between players."""
    feats = {('white', 'Rook'): 2, ('black', 'Rook'): 1}
    assert differentials(feats, 'white')['Rook'] == 1
    assert differentials(feats, 'black')['Rook'] == -1


def test_the_neutral_boulder_carries_no_information():
    """The control that makes the rest credible.

    The boulder is shared, so its differential is the same constant in
    every position and it cannot predict anything. Measured at exactly
    d = 0.000, AUC 0.500 -- the procedure reports no weight where there
    is no information, rather than inventing one.
    """
    traces = collect(make_engine, games=12, agent='random', seed=1)
    findings = {f.feature: f for f in rank(traces, min_count=10)}
    boulder = findings.get('Boulder')
    assert boulder is not None, 'the boulder feature was not evaluated'
    assert abs(boulder.separation) < 1e-9
    assert abs(boulder.auc - 0.5) < 1e-9


def test_censored_games_are_not_labelled():
    """A game with no winner has no outcome to teach, and calling it a
    draw would teach the opposite of #260's lesson."""
    traces = collect(make_engine, games=8, agent='random', seed=2,
                     max_turns=12)
    # Every trace must come from a game that actually finished.
    assert all(t.winner in ('white', 'black') for t in traces)


def test_phase_can_be_held_fixed():
    """Because without it the ranking marks the clock.

    Pawn count tracks how early the game is, and how early it is tracks
    who is about to win. The first run reported `Pawn` at d = -0.547, and
    a naive "learn an evaluation" step would have absorbed that silently.
    """
    traces = collect(make_engine, games=20, agent='random', seed=3)
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
    traces = collect(make_engine, games=24, agent='random', seed=4)
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
