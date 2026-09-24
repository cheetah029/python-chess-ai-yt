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

from lgref.functions import characteristics as chars
from lgref.functions import freeze
from lgref.functions.strategic_ontology import (BY_NAME, CATEGORIES,
                                                NOT_YET_OPERATIONAL, ONTOLOGY)
from lgref.functions.structural import coverage, predict_all
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

def test_the_ontology_is_the_specified_one():
    """40 functions across the eight specified categories.

    An earlier version of mine had six operational classes -- what a
    rule does to the move set, which is mechanism -- and could not
    express `space_control` at all.
    """
    assert len(ONTOLOGY) == 40, len(ONTOLOGY)
    assert set(CATEGORIES) == set('ABCDEFGH')
    for required in ('space_control', 'cycle_prevention',
                     'termination_acceleration', 'draw_suppression',
                     'outcome_balancing', 'tactical_flexibility',
                     'complexity_without_depth', 'escape_facilitation',
                     'threat_projection', 'survivability',
                     'piece_transformation', 'mobility_expansion',
                     'mobility_restriction'):
        assert required in BY_NAME, required


def test_functions_without_an_operational_definition_are_marked():
    """Predictable from structure, not yet falsifiable -- and said so.

    Inventing a metric so every row looks complete would make the
    scoring in Phase 4 meaningless.
    """
    assert NOT_YET_OPERATIONAL
    for name in NOT_YET_OPERATIONAL:
        assert BY_NAME[name].evidence is None
    for entry in ONTOLOGY:
        if entry.evidence:
            assert entry.metrics, entry.name


def test_characteristics_are_a_separate_layer():
    """A characteristic is how a rule is BUILT, not what it does.

    Collapsing them is how "shared neutral influence" gets mistaken for
    a strategic effect.
    """
    assert not set(chars.BY_NAME) & set(BY_NAME)
    undetectable = [d.name for d in chars.DIMENSIONS if not d.detectable]
    assert undetectable, 'every dimension claims to be detectable'


def test_undetectable_characteristics_are_unknown_not_guessed():
    nodes = load(OFFICIAL)
    rules = _setup(OFFICIAL)[1]
    own = [n for n in rules[0].nodes() if n.node_id in rules[0].clause_ids]
    got = chars.detect(own, {'roles': {'white', 'black'}})
    for dimension in chars.DIMENSIONS:
        if not dimension.detectable:
            assert got[dimension.name] == chars.UNKNOWN, dimension.name


# ------------------------------------------------------------ inference ----

def test_language_clusters_are_never_labelled():
    """Asking what job `file_delta_1` does is the error this waited on."""
    nodes, rules, _ = _setup(OFFICIAL)
    kinds = classify_all(nodes, rules)
    labelled = predict_all(nodes, rules)
    for rule in rules:
        if kinds[rule.rule_id] == LANGUAGE:
            assert rule.rule_id not in labelled, rule.rule_id


def test_labels_are_multi_and_ordered_by_evidence():
    nodes, rules, _ = _setup(OFFICIAL)
    labelled = predict_all(nodes, rules)
    multi = [ls for ls in labelled.values() if len(ls) > 1]
    assert multi, 'no cluster got more than one function; forcing one label '\
                  'would misrepresent rules that plainly do several jobs'
    for labels in labelled.values():
        confidences = [l.confidence for l in labels]
        assert confidences == sorted(confidences, reverse=True)


@pytest.mark.parametrize('game', ['nim', 'tictactoe'])
def test_inference_works_on_games_that_are_not_royal_chess(game):
    nodes, rules, _ = _setup(os.path.join(GAMES, '{}.gdl'.format(game)))
    labelled = predict_all(nodes, rules)
    assert labelled, game
    found = {l.function for ls in labelled.values() for l in ls}
    assert found, (game, 'no function predicted at all')
    assert found <= set(BY_NAME), (game, found - set(BY_NAME))


def test_nothing_in_phase_2_names_a_royal_chess_concept():
    import ast
    import inspect

    from lgref.functions import strategic_ontology as ontology_module
    from lgref.functions import structural as structural_module

    def _code_only(module):
        """Source with docstrings stripped.

        The check is about game-specific LOGIC, not prose. These modules
        explain themselves using the project's own example -- the
        boulder is why functions and characteristics are separate layers
        -- and forbidding that would push the reasoning out of the code
        rather than the game-specific behaviour this guards against.
        """
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef)) and \
                    ast.get_docstring(node):
                node.body = node.body[1:]
        return ast.unparse(tree).lower()

    for module in (structural_module, ontology_module, freeze, chars):
        source = _code_only(module)
        for concept in ('boulder', 'knight', 'bishop', 'rook', 'pawn',
                        'queen', 'royal_chess'):
            assert concept not in source, (module.__name__, concept)


def test_unattributed_functions_are_reported_not_dropped():
    """A function nothing predicts is a claim about the description.

    All 36 clauses carrying the capture signature are generic-effect:
    held out of the partition and attached as SHARED members, so they
    belong to no single rule. Capture in this description is not one
    rule's business -- it is the board-update machinery every movement
    rule routes through. A detector that fired on nothing would look
    broken; saying so explicitly makes it a claim about the game.
    """
    nodes, rules, resolution = _setup(OFFICIAL)
    record = freeze.build(nodes, rules, OFFICIAL, resolution, 0)
    assert record['unattributed_functions']
    assert set(record['unattributed_functions']) <= set(BY_NAME)


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
        target = next(k for k, v in data['rules'].items() if v['functions'])
        data['rules'][target]['functions'] = []
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
    record = freeze.build(nodes, rules, OFFICIAL, _setup(OFFICIAL)[2], 0)
    for entry in record['rules'].values():
        for claim in entry['functions']:
            spec = BY_NAME[claim['function']]
            assert claim['category'] == spec.category
            assert claim['falsifiable'] == (spec.evidence is not None)


# ------------------------------------------------- detector comprehensiveness ----

def test_the_functions_this_game_clearly_has_are_predicted():
    """Named in review as obviously present and obviously missing.

    The first detector set predicted 14 of 40 and missed functions this
    game plainly implements -- cycle prevention from the repetition
    rule, anti-drift from the tiny endgame, area denial from the
    boulder, pinning from reactive capture. Each needed a structural
    signature that was simply not written yet, not a subtler method.
    """
    from lgref.functions.structural import predict_all

    nodes, rules, _ = _setup(OFFICIAL)
    found = {p.function for ps in predict_all(nodes, rules).values()
             for p in ps}
    for required in ('cycle_prevention', 'anti_drift_control', 'area_denial',
                     'draw_suppression', 'pinning_immobilization',
                     'path_obstruction', 'temporary_protection',
                     'survivability', 'retaliation', 'royal_preservation',
                     'shared_object_influence', 'threat_projection'):
        assert required in found, required


def test_permission_by_omission_is_detected():
    """Some rules are written as the ABSENCE of a guard.

    Every `friend_at` use in this description is negated, so no clause
    REQUIRES a friendly target -- the rule letting a piece take its own
    is the clause that simply lacks the guard its siblings carry. A
    detector matching on what a clause contains cannot see it.
    """
    from lgref.functions.structural import predict_all

    nodes, rules, _ = _setup(OFFICIAL)
    found = {p.function for ps in predict_all(nodes, rules).values()
             for p in ps}
    assert 'sacrificial_clearance' in found


def test_unpredicted_functions_are_explained_not_just_listed():
    """An undifferentiated list reads as poor detectors.

    For some of these that is right; for others it is a category
    error -- a function whose evidence is a measured quantity was never
    findable from structure at all.
    """
    from lgref.functions.structural import explain_gaps, predict_all

    nodes, rules, _ = _setup(OFFICIAL)
    gaps = explain_gaps(predict_all(nodes, rules))
    assert set(gaps) == {'behavioural', 'undefined', 'detector_gap'}
    assert gaps['behavioural'], 'nothing attributed to behaviour'
    for name in gaps['behavioural']:
        assert BY_NAME[name].metrics, name
    for name in gaps['undefined']:
        assert name in NOT_YET_OPERATIONAL, name


def test_ontology_descriptions_are_not_truncated():
    """Definitions print in full.

    Whitespace is normalised before comparing rather than trying to
    reverse the wrapping: an earlier version reconstructed line joins by
    assuming the continuation indent, and broke the moment the indent
    changed while the property it checked was still perfectly true.
    """
    from lgref.functions.strategic_ontology import describe

    flattened = ' '.join(describe().split())
    for entry in ONTOLOGY:
        assert ' '.join(entry.definition.split()) in flattened, entry.name
