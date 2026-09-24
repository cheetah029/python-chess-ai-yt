"""Phase 2: strategic functions, assigned before any ablation runs.

Issue #208. Every label is a prediction about what Phase 3 will measure.
Assigned afterwards, a label would fit whatever the numbers were;
assigned first it can be wrong, which is what makes it evidence.

These tests check the properties that make that true: the labels are
derivable from structure alone, they are game-agnostic, language
clusters are never labelled, and the frozen record cannot be edited
without detection.
"""

import json
import os
import tempfile

import pytest

from lgref.functions import freeze
from lgref.functions.infer import DETECTOR_STRENGTH, infer, predictions
from lgref.functions.ontology import BY_NAME, ONTOLOGY
from lgref.identify.clauses import load
from lgref.identify.cluster import calibrate_resolution, cluster
from lgref.identify.graph import ClauseGraph
from lgref.identify.language import LANGUAGE, classify_all

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAMES = os.path.join(REPO, 'lgref', 'identify', 'testgames')
OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')


def _setup(path):
    nodes = load(path)
    graph = ClauseGraph(nodes)
    resolution = calibrate_resolution(graph)
    rules, _ = cluster(graph, resolution=resolution)
    return nodes, rules, resolution


# ------------------------------------------------------------- ontology ----

def test_every_class_carries_a_falsifiable_prediction():
    """A class that predicts nothing cannot be wrong, so it proves nothing."""
    for entry in ONTOLOGY:
        assert entry.prediction and entry.metric
        assert entry.direction in ('increase', 'decrease', 'change')


def test_every_class_has_its_detector_strength_declared():
    """Three detectors rest on reserved words, three on weaker proxies.

    Presenting a proxy as firm would misrepresent the evidence; the
    remedy is to say which is which, not to drop the weak ones -- a weak
    detector making a falsifiable claim is what pre-registration is for.
    """
    assert set(DETECTOR_STRENGTH) == {f.name for f in ONTOLOGY}
    assert set(DETECTOR_STRENGTH.values()) == {'strong', 'weak'}


# ------------------------------------------------------------ inference ----

def test_language_clusters_are_never_labelled():
    """Asking what job `file_delta_1` does is the error this waited on."""
    nodes, rules, _ = _setup(OFFICIAL)
    kinds = classify_all(nodes, rules)
    labelled = infer(nodes, rules)
    for rule in rules:
        if kinds[rule.rule_id] == LANGUAGE:
            assert rule.rule_id not in labelled, rule.rule_id


def test_labels_are_multi_and_ordered_by_evidence():
    nodes, rules, _ = _setup(OFFICIAL)
    labelled = infer(nodes, rules)
    multi = [ls for ls in labelled.values() if len(ls) > 1]
    assert multi, 'no cluster got more than one function; forcing one label '\
                  'would misrepresent rules that plainly do several jobs'
    for labels in labelled.values():
        confidences = [l.confidence for l in labels]
        assert confidences == sorted(confidences, reverse=True)


@pytest.mark.parametrize('game', ['nim', 'tictactoe'])
def test_inference_works_on_games_that_are_not_royal_chess(game):
    nodes, rules, _ = _setup(os.path.join(GAMES, '{}.gdl'.format(game)))
    labelled = infer(nodes, rules)
    assert labelled, game
    found = {l.function for ls in labelled.values() for l in ls}
    # Any game with an ending and turns should show at least these.
    assert 'termination_pressure' in found, (game, found)
    assert 'turn_structure' in found, (game, found)


def test_nothing_in_phase_2_names_a_royal_chess_concept():
    import inspect

    from lgref.functions import infer as infer_module
    from lgref.functions import ontology as ontology_module
    for module in (infer_module, ontology_module, freeze):
        source = inspect.getsource(module).lower()
        for concept in ('boulder', 'knight', 'bishop', 'rook', 'pawn',
                        'queen', 'royal_chess'):
            assert concept not in source, (module.__name__, concept)


def test_an_unowned_function_is_reported_not_dropped():
    """`capture_regime` matches no cluster here, and that is a result.

    All 36 clauses carrying the capture signature are generic-effect:
    held out of the partition and attached as SHARED members, so they
    belong to no single rule. Capture in this description is not one
    rule's business -- it is the board-update machinery every movement
    rule routes through. A detector that fired on nothing would look
    broken; saying so explicitly makes it a claim about the game.
    """
    nodes, rules, resolution = _setup(OFFICIAL)
    record = freeze.build(nodes, rules, OFFICIAL, resolution, 0)
    assert 'capture_regime' in record['unattributed_functions']


# ------------------------------------------------------ pre-registration ----

def test_the_frozen_record_detects_tampering():
    nodes, rules, resolution = _setup(OFFICIAL)
    record = freeze.build(nodes, rules, OFFICIAL, resolution, 0)
    with tempfile.TemporaryDirectory() as out:
        path = freeze.write(record, out)
        assert freeze.verify(path)
        with open(path) as handle:
            data = json.load(handle)
        # A rule that HAS labels: the first version of this test picked
        # whichever came first, which was one with none, so "emptying"
        # it changed nothing and the record verified exactly as it
        # should have. The test was passing vacuously in the other
        # direction -- it would have failed had the tamper-check broken,
        # but it never demonstrated the check working.
        target = next(k for k, v in data['rules'].items() if v['labels'])
        data['rules'][target]['labels'] = []
        with open(path, 'w') as handle:
            json.dump(data, handle)
        assert not freeze.verify(path), (
            'predictions were edited and the record still verified')


def test_freezing_refuses_to_overwrite():
    """A pre-registration that can be quietly rewritten is not one."""
    nodes, rules, resolution = _setup(OFFICIAL)
    record = freeze.build(nodes, rules, OFFICIAL, resolution, 0)
    with tempfile.TemporaryDirectory() as out:
        freeze.write(record, out)
        with pytest.raises(FileExistsError):
            freeze.write(record, out)


def test_the_record_pins_what_produced_it():
    """Resolution and seed, so the clusters can be regenerated exactly."""
    nodes, rules, resolution = _setup(OFFICIAL)
    record = freeze.build(nodes, rules, OFFICIAL, resolution, 0)
    assert record['resolution'] == round(float(resolution), 4)
    assert record['seed'] == 0
    assert record['n_clauses'] == len(nodes)


def test_predictions_carry_the_metric_phase_3_will_use():
    nodes, rules, _ = _setup(OFFICIAL)
    for labels in infer(nodes, rules).values():
        for claim in predictions(labels):
            assert claim['metric'] == BY_NAME[claim['function']].metric
            assert claim['direction'] in ('increase', 'decrease', 'change')
