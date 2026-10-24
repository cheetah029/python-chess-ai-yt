"""A player that uses only the protocol, and the gap that remains.

`strong.py` is NOT general -- it raises AttributeError on the first call
against an m,n,k game, because it walks `engine.board.squares`, reads
`piece.color`/`is_royal` and tests `turn.is_capture`. Its leaf also
counts material with hand-chosen weights, so its 0% hanging-material
result is largely circular.

`generic.py` contains no piece name, no board walk and no notion of a
capture. These tests check that structurally, check that it actually
plays well on a game it knows nothing about (verified against exact
minimax), and pin the gap that is left: the rule-derived features do not
include ordinary material, so it will happily capture its own pawn.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.discover import collect, rank
from lgref.experiments.features import (mnk as mnk_features, royal_chess,
                                        with_mobility)
from lgref.experiments.generic import (GenericPlayer, delta_groups,
                                       make_evaluation, mobility)
from lgref.experiments.iterate import weights_from
from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.validate import (optimal_action_rate, uniform_policy)


def _make_mnk(variant='full', max_turns=None):
    return MNK(m=4, n=4, k=3)


def test_the_generic_player_names_no_piece_and_walks_no_board():
    """The structural guard. Checked against live code, not docstrings --
    explaining a domain is not encoding it."""
    import ast
    import inspect

    import lgref.experiments.generic as module

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
    haystack = ' '.join(live)
    for banned in ('Rook', 'Bishop', 'Knight', 'Pawn', 'Queen', 'King',
                   'is_royal', 'squares', 'is_capture', 'transformation',
                   'manipulation'):
        assert banned not in haystack, (
            '{0!r} is reachable from the generic player'.format(banned))


def test_it_runs_on_a_game_the_chess_specific_player_cannot():
    """`strong.StrongPlayer` raises AttributeError here; this must not."""
    from lgref.experiments.strong import StrongPlayer

    game = _make_mnk()
    turns = game.get_all_legal_turns()

    failed = False
    try:
        StrongPlayer(depth=1, rng=random.Random(0)).choose_turn(turns, game)
    except AttributeError:
        failed = True
    assert failed, ('StrongPlayer now runs on m,n,k -- if it was made '
                    'general, this comparison needs rewriting')

    player = GenericPlayer(make_evaluation(), depth=1, quiescence=1,
                           rng=random.Random(0))
    assert player.choose_turn(turns, game) in turns


def test_it_runs_on_the_case_study_too():
    engine = make_engine('full', max_turns=60)
    turns = engine.get_all_legal_turns()
    player = GenericPlayer(make_evaluation(), depth=1, quiescence=0,
                           rng=random.Random(0))
    assert player.choose_turn(turns, engine) in turns


def test_it_plays_well_above_chance_against_exact_play():
    """The only test that bears on strength, on the only game here where
    truth is computable. Measured 83.5% optimal against a 34.5% chance
    baseline -- using nothing but the protocol."""
    extractor = with_mobility(mnk_features)
    traces = collect(_make_mnk, extractor, games=200, agent='random',
                     seed=4)
    weights = weights_from(rank(traces, min_count=30, min_games=20))
    assert weights, 'nothing was learned'
    evaluate = make_evaluation(extractor, weights, mobility_weight=0.0,
                               repetition_weight=0.0)
    player = GenericPlayer(evaluate, depth=2, quiescence=1,
                           extractor=extractor, sample=3,
                           rng=random.Random(0))

    def policy(game, rng):
        return player.choose_turn(game.get_all_legal_turns(), game)

    learned = optimal_action_rate(_make_mnk, optimal_moves, policy,
                                  trials=120, seed=99)
    control = optimal_action_rate(_make_mnk, optimal_moves,
                                  uniform_policy, trials=120, seed=99)
    assert abs(control.rate - control.chance) < 0.10, (
        'control missed its baseline; the harness is wrong')
    assert learned.rate > 1.8 * learned.chance, (
        '{:.1%} against chance {:.1%}'.format(learned.rate, learned.chance))


def test_the_mobility_weight_is_learned_rather_than_assumed():
    """It cannot be a fixed heuristic, because having no legal turn is a
    LOSS in Royal Chess (RULEBOOK.md) and a DRAW in an m,n,k game. So the
    feature is supplied and the weight is left to the outcomes -- and on
    m,n,k it comes out NEGATIVE (measured d = -0.364, z = 3.1)."""
    extractor = with_mobility(mnk_features)
    traces = collect(_make_mnk, extractor, games=200, agent='random',
                     seed=4)
    findings = {f.feature: f for f in rank(traces, min_count=30,
                                           min_games=20)}
    assert 'Mobility' in findings, 'the feature was not evaluated'
    assert findings['Mobility'].separation < 0, (
        'mobility should not predict winning on a game whose full board '
        'is a draw')


def test_mobility_is_read_from_the_protocol_alone():
    game = _make_mnk()
    assert mobility(game) == len(game.get_all_legal_turns())
    engine = make_engine('full', max_turns=60)
    assert mobility(engine) == len(engine.get_all_legal_turns())


def test_interchangeable_moves_collapse_without_naming_them():
    """Moves with an identical effect on the feature vector are
    indistinguishable to the evaluation, so only a sample is searched.

    In Royal Chess this collapses the bishop's ~40 teleports -- which
    supply 42.3% of legal turns and 0.0% of captures -- automatically,
    because they all produce the same delta: none. Nothing here mentions
    a bishop.
    """
    engine = make_engine('full', max_turns=60)
    turns = engine.get_all_legal_turns()
    kept = delta_groups(engine, turns, royal_chess, sample=2,
                        rng=random.Random(0))
    assert 0 < len(kept) < len(turns), (
        'nothing collapsed: {} of {}'.format(len(kept), len(turns)))


def test_the_remaining_gap_material_is_not_rule_derived():
    """The honest limit, pinned so it is not forgotten.

    The declared conditions give royal count, mobility and repetition
    pressure. None of them is ordinary material, because no win or loss
    condition mentions a pawn -- so an evaluation built only from the
    rules plus random-play learning has no non-royal term and will
    capture its OWN pawn (legal: only the king may capture friendlies).

    Material matters INSTRUMENTALLY, and getting that generically needs
    either a solvable region to anchor on (Royal Chess has none: ~63
    plies even in thin endgames at 1.1 ms a node) or bootstrapping the
    value target from the search itself. Until then this gap is real.
    """
    extractor = with_mobility(royal_chess)
    traces = collect(make_engine, extractor, games=30, agent='random',
                     seed=4, max_turns=400)
    weights = weights_from(rank(traces, min_count=30, min_games=20))
    # Whatever is learned, ordinary material is not among the survivors.
    for name in ('Pawn', 'Rook', 'Knight', 'Bishop'):
        assert name not in weights, (
            '{0} now survives -- if ordinary material has become '
            'learnable, the gap this test documents has closed and the '
            'claim should be re-examined rather than assumed'.format(name))
