"""One test per experiment that reported a result it had not measured.

Three runs in issue #278 produced a confident, wrong conclusion because
the pipeline was checked after the number instead of before it. The
checks in `record.py` exist so the artifact contradicts the mistake, and
these tests exist so the checks keep working.

Nothing here knows the case study: a payload is names and numbers.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

from lgref.experiments.bootstrap import run
from lgref.experiments.record import (FATAL, SUSPECT, audit, fatal,
                                      observed, record, silent,
                                      unsupported)


def test_a_payload_claiming_an_ablation_it_cannot_replay_is_fatal():
    """SILENT FAILURE 2, asked directly.

    A run recorded `lean: True` and nothing else. The loader rebuilds a
    feature set from `drop_prefixes` and `dropped`, so a boolean is a
    statement no code acts on -- the weights were replayed on the
    unablated set while every note about the experiment said otherwise.
    """
    payload = {'extractor': 'x', 'weights': {'a': 0.5}, 'lean': True}
    problems = fatal(audit(payload))
    assert problems, 'a claim nothing replays must not pass'
    assert 'lean' in problems[0]


def test_the_same_flag_beside_a_real_replay_field_is_only_suspect():
    """The distinction is whether the transformation is RECORDED, not
    whether a boolean is present. Refusing a redundant note would make
    the check useless, because every lean run carries one."""
    payload = {'extractor': 'x', 'weights': {'a': 0.5}, 'lean': True,
               'drop_prefixes': ['Flag:']}
    complaints = audit(payload)
    assert not fatal(complaints)
    assert any(severity == SUSPECT for severity, _ in complaints)


def test_a_feature_that_never_varied_is_named():
    """SILENT FAILURE 3, asked directly.

    An aggregate added to fix the blunders was computed inside a loop
    that a speed optimisation short-circuits, so it was zero in every
    position of every game. Three seeds agreed on a weight of exactly
    +0.000000 and the agreement read as a finding. The normaliser scale
    is a decaying maximum of the feature's own magnitude, so a scale of
    zero IS the signature, and it is available without replaying
    anything.
    """
    payload = {'extractor': 'x',
               'weights': {'Live': 0.4, 'Dead': 0.0},
               'scales': {'Live': 2.0, 'Dead': 0.0}}
    complaints = audit(payload)
    assert not fatal(complaints)
    text = ' '.join(message for _severity, message in complaints)
    assert 'Dead' in text and 'Live' not in text


def test_a_payload_with_no_extractor_cannot_be_rebuilt():
    assert fatal(audit({'weights': {'a': 1.0}}))


def test_a_dropped_column_that_carries_a_weight_is_a_contradiction():
    """Two descriptions of one feature set. Whichever is replayed, the
    weights were fitted on the other."""
    payload = {'extractor': 'x', 'weights': {'a': 1.0, 'b': 2.0},
               'dropped': ['b']}
    assert fatal(audit(payload))


def test_an_evaluation_that_learned_nothing_is_refused():
    payload = {'extractor': 'x', 'weights': {'a': 0.0, 'b': 0.0}}
    assert fatal(audit(payload))


def test_record_refuses_to_write_the_flag_that_caused_the_failure():
    """The fix is upstream of the check: a trainer that records its
    pipeline through `record` cannot describe an ablation it did not
    perform, because it passes the same value it built the extractor
    from."""
    with pytest.raises(ValueError) as caught:
        record('x', lean=True)
    assert 'drop_prefixes' in str(caught.value)
    assert record('x', drop_prefixes=('A:',))['drop_prefixes'] == ['A:']


def test_record_insists_on_naming_the_extractor():
    with pytest.raises(ValueError):
        record('')


def test_observed_names_the_feature_that_never_fires():
    """The complement: `audit` reads the artifact, `observed` reads the
    extractor against real positions. One call of this before the three
    seeds would have saved the run that tested nothing."""
    states = [{'present': 1.0, 'absent': 0.0},
              {'present': -2.0, 'absent': 0.0}]
    summary = observed(lambda state: state, states)
    assert summary['present'] == (2, 2.0)
    assert summary['absent'] == (0, 0.0)
    assert silent(summary) == ['absent']


def test_the_loader_refuses_a_payload_it_cannot_replay(tmp_path):
    """End to end: the audit runs on every load, not in a procedure
    someone is supposed to remember."""
    from lgref.experiments.features import load_royal_chess_searcher

    path = tmp_path / 'broken.json'
    path.write_text(json.dumps({'extractor': 'legacy', 'lean': True,
                                'weights': {'Pawn': 0.1}}))
    with pytest.raises(ValueError) as caught:
        load_royal_chess_searcher(str(path))
    assert 'cannot be played as saved' in str(caught.value)


def test_the_shipped_weights_pass_their_own_audit():
    path = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'td_royal_chess.json')
    complaints = audit(json.load(open(path)))
    assert not fatal(complaints), complaints


def test_the_severities_are_ordered_worst_first():
    payload = {'extractor': 'x', 'weights': {'a': 1.0, 'b': 0.0},
               'scales': {'a': 1.0, 'b': 0.0}, 'dropped': ['a']}
    complaints = audit(payload)
    assert complaints[0][0] == FATAL


def test_a_large_weight_on_almost_no_data_is_flagged():
    """THE PATTERN THAT CAUSED FOUR BLUNDERS, asked of a payload.

    Adagrad gives a sparse feature a large step on purpose, so that a
    quantity which is almost always zero can still move. The cost is
    that a handful of observations can produce a weight bigger than a
    piece is worth. `RoyalForm:Rook` reached +0.1467 -- over two pawns
    -- on a transformation that happens a few times in eight hundred
    games, and the agent then gave away a pawn rather than let the
    opponent flip it.

    The bar is read from the payload, not chosen: a weight is questioned
    when its magnitude is above the median magnitude AND its observation
    count is far below the typical count.
    """
    payload = {'extractor': 'x',
               'weights': {'Dense': 0.30, 'AlsoDense': 0.20,
                           'Rare': 0.25, 'Small': 0.01},
               'support': {'Dense': 4000, 'AlsoDense': 3800,
                           'Rare': 6, 'Small': 5}}
    # THE BAR IS SUPPLIED BY THE CALLER, and for a game with pieces the
    # meaningful one is the cheapest piece's MEASURED price, from
    # `validate.removal_price` -- "this rare feature outweighs the least
    # valuable thing on the board". Not a number anyone chose: it is read
    # off the evaluation by taking a piece off the board.
    flagged = dict((name, seen)
                   for name, _w, seen in unsupported(payload, floor=0.05))
    assert 'Rare' in flagged and flagged['Rare'] == 6
    assert 'Dense' not in flagged and 'AlsoDense' not in flagged
    # `Small` is barely observed too, but it is below the bar, so it
    # cannot outvote a piece and is not worth a complaint.
    assert 'Small' not in flagged


def test_without_a_bar_the_payloads_own_median_magnitude_is_used():
    """A default that is read from the data rather than chosen, so the
    check still says something on a game where nothing can be removed
    and no piece price exists."""
    payload = {'extractor': 'x',
               'weights': {'a': 0.9, 'b': 0.8, 'c': 0.95, 'd': 0.01},
               'support': {'a': 9000, 'b': 8000, 'c': 3, 'd': 2}}
    flagged = [name for name, _w, _seen in unsupported(payload)]
    assert flagged == ['c'], flagged


def test_a_payload_with_no_observation_counts_says_so():
    """Silence about support is itself worth reporting: a weight table
    with no counts cannot be told from one whose numbers rest on
    thousands of samples."""
    complaints = audit({'extractor': 'x', 'weights': {'a': 0.5}})
    assert not fatal(complaints)
    text = ' '.join(message for _severity, message in complaints)
    assert 'observation counts' in text


def test_unsupported_needs_counts_rather_than_guessing_them():
    assert unsupported({'weights': {'a': 1.0}}) == []


def test_training_records_how_often_each_feature_was_seen():
    """End to end: the counter has to be wired through `run`, not just
    exist. Checked on the solvable game so it is fast."""
    from lgref.experiments.features import mnk as mnk_features
    from lgref.experiments.features import with_threshold
    from lgref.experiments.mnk import MNK

    support = {}
    scales = {}
    history = run(lambda *a, **k: MNK(m=3, n=3, k=3),
                  with_threshold(mnk_features), rounds=1,
                  games_per_round=6, alpha=0.08, epsilon=0.3, seed=2,
                  max_turns=20, scales=scales, support=support)
    assert history, 'no rounds completed'
    assert support, 'no observation counts were recorded'
    for name in history[-1].weights:
        assert name in support or history[-1].weights[name] == 0.0, (
            '{0} carries a weight with no recorded support'.format(name))
    assert max(support.values()) > 1
