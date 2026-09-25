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


def test_every_function_names_something_that_could_contradict_it():
    """All 40, and each names a quantity a row actually carries.

    Seventeen used to name nothing, and the listing said so with a
    star. The star was honest and the situation was not: a function
    with no evidence cannot be wrong, and Phase 4 has to decline to
    score it, so nearly half the ontology was decoration.

    The way NOT to close this is by inventing a metric so the table
    looks complete. Each of the seventeen is now backed by a quantity
    the sweep records, which `test_metrics` checks from the other end
    by playing a game and looking for every name in the row.
    """
    assert not NOT_YET_OPERATIONAL, NOT_YET_OPERATIONAL
    for entry in ONTOLOGY:
        assert entry.evidence, entry.name
        assert entry.metrics, entry.name


def test_the_marker_still_works_if_a_function_arrives_without_evidence():
    """The machinery that said so has not been deleted, only emptied.

    A new function will be added before its metric exists, and on that
    day the listing has to go back to marking it rather than quietly
    presenting it as checkable.
    """
    from lgref.functions import strategic_ontology as ont

    saved = ont.NOT_YET_OPERATIONAL
    try:
        ont.NOT_YET_OPERATIONAL = ('threat_concentration',)
        text = ont.describe()
        assert 'no operational definition yet' in text
        assert '1 of 40' in text
    finally:
        ont.NOT_YET_OPERATIONAL = saved
    assert 'no operational definition yet' not in ont.describe()


def test_the_listing_says_where_the_measurements_stop_discriminating():
    """Forty definitions are not forty independent claims.

    Several functions are read off the same quantities. Presenting the
    table without saying so would trade one overstatement -- half the
    ontology unfalsifiable -- for a quieter one.
    """
    from lgref.functions.strategic_ontology import describe, shared_evidence

    groups = shared_evidence()
    assert groups, 'nothing shares evidence; check the grouping, not luck'
    text = describe()
    assert 'WHERE THE RESOLUTION ENDS' in text
    for names in groups.values():
        assert len(names) > 1
        for name in names:
            assert name in BY_NAME


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
    """Two reasons, and only one of them excuses the detectors.

    The report used to offer two more: that a function with no
    operational definition was beyond every channel, and that a
    function whose evidence is a measured quantity was never
    structure's to find. Both were false, and between them they
    explained away nine functions this game actually has (#215).
    """
    from lgref.functions.strategic_ontology import MEASURED_NULLS
    from lgref.functions.structural import explain_gaps, predict_all

    nodes, rules, _ = _setup(OFFICIAL)
    gaps = explain_gaps(predict_all(nodes, rules))
    assert set(gaps) == {'measured_null', 'detector_gap'}
    for name in gaps['measured_null']:
        assert MEASURED_NULLS[name] in BY_NAME, name


def test_lacking_an_operational_definition_is_not_a_reason_to_miss_one():
    """Unfalsifiable is not unpredictable, and conflating them cost nine.

    The gap report once justified seven absences by those functions
    having no operational definition, while predicting ten others from
    that same list without difficulty. Nothing lacks a definition now,
    so the conflation cannot recur through that door -- but the door
    itself is what this guards: no reason the report gives may be
    derived from whether a function has evidence.
    """
    from lgref.functions.structural import explain_gaps

    nodes, rules, _ = _setup(OFFICIAL)
    predictions = predict_all(nodes, rules)
    for names in explain_gaps(predictions).values():
        for name in names:
            assert BY_NAME[name].evidence, (
                name, 'a gap reason was derived from missing evidence')


def test_configuration_functions_are_predicted():
    """The nine this game has that the first detector set never found.

    Seven of them live in the queen's rules -- the transformation, the
    form menu that governs it, the manipulation, the promotion -- which
    is why missing them left a whole side of the game undescribed.
    """
    nodes, rules, _ = _setup(OFFICIAL)
    found = {p.function for ps in predict_all(nodes, rules).values()
             for p in ps}
    for required in ('tactical_reconfiguration', 'strategic_diversity',
                     'power_preservation', 'piece_type_balancing',
                     'resource_conversion', 'tactical_flexibility',
                     'threat_redistribution', 'threat_concentration',
                     'decision_compression'):
        assert required in found, required


def test_only_the_measured_null_goes_unpredicted():
    """39 of 40. The one left is not a gap.

    `complexity_without_depth` is what `tactical_flexibility` turns out
    to be when the measurement contradicts the structure: same shape,
    opposite outcome. Structure proposing it would mean proposing that
    its own prediction fails.
    """
    from lgref.functions.strategic_ontology import MEASURED_NULLS

    nodes, rules, _ = _setup(OFFICIAL)
    _, never = coverage(predict_all(nodes, rules))
    assert set(never) == set(MEASURED_NULLS), never


def test_configuration_detectors_stay_silent_where_the_shape_is_absent():
    """The negative control the earlier detectors never had.

    Neither toy game has a mode, a form menu, a piece moved by someone
    else, a ray, or a ban on reversal, so none of these may fire. A
    detector that finds its function everywhere has found nothing, and
    both false positives caught during this work -- a frame clause
    reading as redistribution, an empty square reading as a converted
    resource -- would have passed a Royal-Chess-only test.
    """
    configuration = {'tactical_reconfiguration', 'strategic_diversity',
                     'power_preservation', 'piece_type_balancing',
                     'resource_conversion', 'tactical_flexibility',
                     'threat_redistribution', 'threat_concentration',
                     'decision_compression'}
    for game in ('nim', 'tictactoe'):
        nodes, rules, _ = _setup(os.path.join(GAMES, '{}.gdl'.format(game)))
        found = {p.function for ps in predict_all(nodes, rules).values()
                 for p in ps}
        assert not found & configuration, (game, sorted(found & configuration))


def test_a_repeated_action_argument_is_not_a_ban_on_reversal():
    """The pawn's straight capture repeats a variable, and it mattered.

    `move(pawn,FF,FR,FF,TR)` puts the same variable in the origin file
    and the destination file. Reading only the first occurrence made
    the invulnerability guard -- which tests the destination, as the
    writer stores the destination -- look like a rule against going
    back where you came from, and `decision_compression` was then
    predicted for three rules that have nothing to do with it.
    """
    from lgref.functions.structural import _ctx

    nodes, _rules, _ = _setup(OFFICIAL)
    guards = _ctx(nodes)['config']['reversal_guards']
    assert guards, 'the no-return memory is a ban on reversal'
    fluents = {fluent for _action, fluent in guards}
    assert len(fluents) == 1, sorted(fluents)


def test_a_mode_is_told_from_a_counter_and_from_a_coordinate():
    """Three things share the shape and are not the same function.

    A mode, a countdown and a starting square all put constants in a
    fluent's slot. The countdown's values are related to each other by
    the game's own successor facts; the starting square's are not
    branched on by any legal clause. Getting either wrong pointed the
    whole configuration layer at the wrong slot -- once at a cooldown,
    once at the two files the royal queens start on.
    """
    from lgref.functions.structural import _ctx

    nodes, _rules, _ = _setup(OFFICIAL)
    modes = _ctx(nodes)['config']['modes']
    assert len(modes) == 1, sorted(modes)
    spec = list(modes.values())[0]
    assert len(spec['values']) == 4, sorted(spec['values'])
    assert spec['persistent']
    assert len(spec['initial']) == 1, sorted(spec['initial'])


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


# ---- which way, and in whose frame (#220) --------------------------------

def test_every_metric_has_a_direction_and_every_direction_a_metric():
    """The two must not drift, because nothing else would notice.

    A direction stored beside the metric list rather than inside it
    buys a much smaller diff at the cost of a way to disagree. This is
    the check that makes the trade safe.
    """
    from lgref.functions.strategic_ontology import DIRECTIONS, EXPECTED

    assert set(EXPECTED) == {f.name for f in ONTOLOGY}
    for entry in ONTOLOGY:
        assert set(EXPECTED[entry.name]) == set(entry.metrics), entry.name
        for metric, direction in EXPECTED[entry.name].items():
            assert direction in DIRECTIONS, (entry.name, metric, direction)


def test_opposite_functions_predict_opposite_movements():
    """The pairs that motivated holding direction as data.

    Expansion and restriction name the same two quantities; so do
    compression and clutter. Read as names they are indistinguishable,
    which is how both pairs came to be reported as beyond the
    instrument's resolution when in fact they disagree about
    everything.
    """
    from lgref.functions.strategic_ontology import EXPECTED

    for one, other in (('mobility_expansion', 'mobility_restriction'),
                       ('decision_compression', 'complexity_without_depth')):
        shared = set(EXPECTED[one]) & set(EXPECTED[other])
        assert shared, (one, other)
        assert any(EXPECTED[one][m] != EXPECTED[other][m] for m in shared), (
            one, other, 'no metric distinguishes them')


def test_the_pairs_that_genuinely_collide_are_still_reported():
    """Sharpening the check must not empty it.

    Two collisions were hidden behind the ones direction resolves, and
    a report that now lists nothing would mean the grouping broke
    rather than that the ontology got sharper.
    """
    from lgref.functions.strategic_ontology import shared_evidence

    collided = {name for names in shared_evidence().values()
                for name in names}
    for expected in ('area_denial', 'path_obstruction', 'repositioning',
                     'escape_facilitation', 'anti_drift_control',
                     'termination_acceleration'):
        assert expected in collided, expected
    for resolved in ('mobility_expansion', 'mobility_restriction',
                     'decision_compression', 'complexity_without_depth'):
        assert resolved not in collided, resolved


def test_evidence_is_written_in_the_ablation_frame():
    """One frame, stated in the module and followed by all forty.

    Twelve entries described the rule while PRESENT -- "reachable
    squares ... all increase", true of the rule and backwards as a
    prediction about removing it. A reader could not tell which frame
    an entry was in, and nothing checked, so the two coexisted for as
    long as direction was prose.

    Checked where it can be: a function whose definition says it
    INCREASES something must not predict that same quantity rising
    when it is taken away.
    """
    from lgref.functions.strategic_ontology import EXPECTED, UP

    for entry in ONTOLOGY:
        if not any(word in entry.definition
                   for word in ('increases', 'expands', 'allows more')):
            continue
        for metric, direction in EXPECTED[entry.name].items():
            if metric in ('mean_branching', 'mean_reachable_mover',
                          'mean_policy_branching', 'mean_attack_coverage'):
                assert direction != UP, (
                    entry.name, metric,
                    'a rule that increases this cannot also increase it '
                    'by being removed')
