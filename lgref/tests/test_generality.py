"""The inference must not know what game it is looking at.

`discover.py` had quietly become a Royal Chess module while its own
docstring claimed that no piece name was hard-coded: it walked
`range(8)` twice, imported a Royal Chess piece class, and listed
`('rook', 'bishop', 'knight')` by hand. A framework whose purpose is to
handle games it has not seen cannot carry the case study inside its
estimator.

So these tests check the separation structurally, and then check that
the same machinery actually runs on a second game and gets the RIGHT
ANSWER, verified against exact play rather than against a significance
level.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from lgref.experiments.discover import collect, differentials, rank
from lgref.experiments.features import NEUTRAL_OWNERS, mnk as mnk_features
from lgref.experiments.iterate import make_evaluator, weights_from
from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.validate import (evaluator_policy,
                                        optimal_action_rate,
                                        uniform_policy)


def _make_mnk(variant='full', max_turns=None, m=4, n=4, k=3):
    return MNK(m=m, n=n, k=k)


def test_the_inference_module_names_no_piece_and_no_board_size():
    """A source guard, because this regressed once already.

    Domain knowledge belongs in an extractor behind a documented
    protocol. Checked against the module's CODE, not its prose: the
    docstrings legitimately discuss the case study, and explaining a
    domain is not encoding it.
    """
    import ast
    import inspect

    import lgref.experiments.discover as module

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
                   'royal', 'boulder', 'squares', 'captured_pieces',
                   'is_royal'):
        assert banned not in haystack, (
            '{0!r} is reachable from the inference code; it belongs in '
            'an extractor'.format(banned))


def test_a_second_game_yields_a_different_vocabulary():
    """Same inference, different game, no shared names."""
    game = _make_mnk()
    game.execute_turn(0)
    game.execute_turn(5)
    names = {name for _owner, name in mnk_features(game)}
    assert 'Marks' in names
    assert any(n.startswith('Line:') for n in names)
    # Nothing from the case study leaks in.
    assert not {'Royal', 'DownToOneRoyal', 'Bishop'} & names


def test_mnk_features_are_derived_from_the_win_condition():
    """`Line:j` counts lines holding j of a player's marks and none of
    the opponent's, which comes from `win_lines` -- the set of lines the
    RULES declare winning. Nobody supplied "two in a row is good"."""
    game = _make_mnk()
    game.cells[0] = 'x'
    game.cells[1] = 'x'
    feats = mnk_features(game)
    # x holds a line with two marks and no o marks.
    assert feats[('x', 'Line:2')] >= 1
    # Blocking it removes that line from x's count.
    game.cells[2] = 'o'
    after = mnk_features(game)
    assert after[('x', 'Line:2')] == feats[('x', 'Line:2')] - 1


def test_material_is_measured_as_exactly_uninformative_in_mnk():
    """The control that shows the procedure is reading the game and not
    a prior. Players alternate, so mark counts can never differ by more
    than the turn parity and `Marks` carries no information. Measured at
    d = 0.000 -- a material prior transplanted from chess would have
    given it a weight.
    """
    traces = collect(_make_mnk, mnk_features, games=120, agent='random',
                     seed=4)
    findings = rank(traces, min_count=30, min_games=20)
    by_name = {f.feature: f for f in findings}
    assert 'Marks' in by_name, 'the feature was not even evaluated'
    assert abs(by_name['Marks'].separation) < 0.1
    assert 'Marks' not in weights_from(findings)


def test_the_uniform_control_lands_on_its_own_baseline():
    """The harness self-check, and the reason three defects were caught.

    A uniform random policy scores the chance baseline BY DEFINITION. A
    run where it does not is a broken comparison, not a finding -- and
    when this was violated (6.1% against a 15.7% baseline) it was
    because `optimal_moves` returns `(best, value)` and the pair was
    being used as the set.
    """
    result = optimal_action_rate(_make_mnk, optimal_moves, uniform_policy,
                                 trials=400, seed=99)
    assert result.n > 50, 'too few decision positions to judge'
    assert abs(result.rate - result.chance) < 0.08, (
        'the control missed its own baseline by {:.3f} -- the harness is '
        'wrong, not the policy'.format(abs(result.rate - result.chance)))


def test_the_discovered_evaluation_beats_chance_against_exact_play():
    """The acceptance test the pipeline was missing.

    Learned from random self-play alone, with no ground truth and no
    supplied features, then scored against exact minimax. Measured 92.0%
    optimal against a 32.1% chance baseline on 4x4 k=3.

    This is the only test here that bears on PLAYING STRENGTH. Cohen's d
    and AUC measure correlation over whole games and can be large while
    the argmax of the resulting score is a bad move.
    """
    traces = collect(_make_mnk, mnk_features, games=200, agent='random',
                     seed=4)
    weights = weights_from(rank(traces, min_count=30, min_games=20))
    assert weights, 'nothing was learned'
    evaluate = make_evaluator(weights, mnk_features)
    learned = optimal_action_rate(_make_mnk, optimal_moves,
                                  evaluator_policy(evaluate), trials=400,
                                  seed=99)
    control = optimal_action_rate(_make_mnk, optimal_moves,
                                  uniform_policy, trials=400, seed=99)
    # The control is the guard: if it has drifted, ignore the comparison.
    assert abs(control.rate - control.chance) < 0.08
    assert learned.rate > 2.0 * learned.chance, (
        'learned {:.1%} against chance {:.1%}'.format(learned.rate,
                                                      learned.chance))


def test_a_decided_position_uses_the_true_outcome_not_the_estimate():
    """Because a feature set sampled from non-terminal states can be
    blind to winning outright.

    Completing a line turns `Line:k-1` into `Line:k`, and `Line:k`
    appears only in terminal states, which the sampler never records.
    Measured: the learned score of a winning move equalled that of a
    quiet move EXACTLY (0.2749 both). The policy must therefore read the
    outcome rather than the estimate.
    """
    evaluate = make_evaluator({'Line:2': 0.97}, mnk_features)
    game = _make_mnk()
    game.cells[0] = 'x'
    game.cells[1] = 'x'
    game.cells[5] = 'o'
    game.cells[6] = 'o'
    game.current_player = 'x'
    winning = 2                      # completes x's line 0,1,2
    import random

    pick = evaluator_policy(evaluate)(game, random.Random(0))
    assert pick == winning, (
        'the policy declined an immediate win, so it is trusting the '
        'estimate over the outcome')


def test_neutral_owners_are_shared_by_the_protocol():
    """One definition, so a neutral piece cannot be scored as an enemy of
    both players again."""
    assert None in NEUTRAL_OWNERS and 'none' in NEUTRAL_OWNERS
    feats = {('none', 'Boulder'): 1, ('white', 'Rook'): 2}
    assert 'Boulder' not in differentials(feats, 'white')
    assert differentials(feats, 'white')['Rook'] == 2
