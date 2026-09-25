"""Phase 5: matching measurements to intentions, and deciding.

The reasoning here is more dangerous than the arithmetic. A
recommendation is an argument, and an argument with a plausible shape
and a broken premise reads exactly like a sound one. These tests are
mostly about premises.
"""

import collections
import os

import pytest

from lgref.analysis.effects import Effect
from lgref.functions.strategic_ontology import DOWN, FLAT, SHAPE, UP
from lgref.recommend import policy
from lgref.recommend.verdicts import (CONFIRMED, CONTRADICTED, NOT_COMPARABLE,
                                      UNTESTED, check_function, check_metric)


def _effect(metric, d, verdict='effect'):
    return Effect(metric, 'v', 90, 90, 1.0, 1.0 + d, d, d,
                  d - 0.1, d + 0.1, 0.9, verdict)


# ---- one predicted movement against one measurement ---------------------

def test_a_movement_in_the_predicted_direction_confirms():
    assert check_metric('m', UP, _effect('m', +1.0)).outcome == CONFIRMED
    assert check_metric('m', DOWN, _effect('m', -1.0)).outcome == CONFIRMED


def test_a_movement_the_other_way_contradicts():
    assert check_metric('m', UP, _effect('m', -1.0)).outcome == CONTRADICTED
    assert check_metric('m', DOWN, _effect('m', +1.0)).outcome == CONTRADICTED


def test_an_unusable_effect_is_untested_not_a_failure():
    """Not seeing something is not seeing that it is absent."""
    for verdict in ('seed-dominated', 'inconclusive'):
        got = check_metric('m', UP, _effect('m', 0.4, verdict))
        assert got.outcome == UNTESTED, verdict
    assert check_metric('m', UP, None).outcome == UNTESTED


def test_a_flat_prediction_is_confirmed_by_an_interval_spanning_zero():
    """The one place where finding nothing is finding something.

    Most of the ontology predicts movement, and there an inconclusive
    interval means the test did not run. `FLAT` predicts that a
    quantity does NOT move, so the same interval is the outcome it
    asked for. Under the opposite convention every control clause in
    the ontology would be silently unfalsifiable.
    """
    got = check_metric('m', FLAT, _effect('m', 0.05, 'inconclusive'))
    assert got.outcome == CONFIRMED


def test_a_flat_prediction_is_contradicted_by_a_real_effect():
    got = check_metric('m', FLAT, _effect('m', 1.4))
    assert got.outcome == CONTRADICTED


def test_a_flat_prediction_is_untested_when_seed_noise_swamps_it():
    """Holding still and not being seen are different things."""
    got = check_metric('m', FLAT, _effect('m', 0.2, 'seed-dominated'))
    assert got.outcome == UNTESTED


def test_a_distribution_is_not_compared_as_a_level():
    got = check_metric('m', SHAPE, _effect('m', 1.0))
    assert got.outcome == NOT_COMPARABLE


# ---- a whole function ----------------------------------------------------

def _patch(monkeypatch, expected):
    from lgref.functions import strategic_ontology as ont
    monkeypatch.setitem(ont.EXPECTED, 'probe', expected)


def test_contradiction_beats_confirmation(monkeypatch):
    """Half a match is a refutation, not a half-score.

    A function claiming two movements and getting one has been shown to
    be the wrong description. Averaging the two would turn that into a
    passing grade.
    """
    _patch(monkeypatch, {'a': UP, 'b': UP})
    got = check_function('probe', {'a': _effect('a', +1.0),
                                   'b': _effect('b', -1.0)})
    assert got.outcome == CONTRADICTED


def test_a_control_clause_alone_cannot_confirm(monkeypatch):
    """`threat_concentration` came back supported on one flat interval.

    Its real claim -- that concentration falls -- was untested, and the
    control clause stood in for it. A clause that says "and this other
    thing stayed put" corroborates a checked claim; it is not one.
    """
    _patch(monkeypatch, {'main': DOWN, 'control': FLAT})
    got = check_function('probe', {
        'main': _effect('main', 0.3, 'seed-dominated'),
        'control': _effect('control', 0.02, 'inconclusive')})
    assert got.outcome == UNTESTED


def test_a_directional_confirmation_carries_the_function(monkeypatch):
    _patch(monkeypatch, {'main': DOWN, 'control': FLAT})
    got = check_function('probe', {
        'main': _effect('main', -0.9),
        'control': _effect('control', 0.02, 'inconclusive')})
    assert got.outcome == CONFIRMED


# ---- what a recommendation may rest on -----------------------------------

def _row(**verdicts):
    return {name: _effect(name, 1.0, verdict)
            for name, verdict in verdicts.items()}


def test_revise_requires_a_declared_intent():
    """The bug this caught made every measurable rule a revision.

    An earlier version fired `revise` whenever ANY of the forty
    ontology functions was contradicted by the signature. Of course a
    boulder ablation contradicts `anti_drift_control` -- the boulder
    was never for that. Matching against the whole ontology says what
    the evidence rules out; it cannot say the rule failed, because it
    does not know what the rule was trying to do.
    """
    Verdict = collections.namedtuple('Verdict', 'function outcome')
    contradicted = [Verdict('anti_drift_control', CONTRADICTED)]
    weights = {'game_length': 1.0}
    row = _row(game_length='effect')

    without = policy.recommend('v', 'o', weights, row, 1.0, contradicted,
                               intended=None)
    assert without.verdict != policy.REVISE
    assert without.intent_checked is False

    with_intent = policy.recommend('v', 'o', weights, row, 1.0, contradicted,
                                   intended=('anti_drift_control',))
    assert with_intent.verdict == policy.REVISE


def test_an_intent_that_survived_does_not_trigger_revision():
    Verdict = collections.namedtuple('Verdict', 'function outcome')
    got = policy.recommend(
        'v', 'o', {'game_length': 1.0}, _row(game_length='effect'), 1.0,
        [Verdict('space_control', CONFIRMED)], intended=('space_control',))
    assert got.verdict == policy.REMOVE


def test_the_sign_convention_is_the_ablated_game():
    """Effects are measured on the variant, so positive means without."""
    weights = {'game_length': 1.0}
    row = _row(game_length='effect')
    assert policy.recommend('v', 'o', weights, row, +1.0).verdict == \
        policy.REMOVE
    assert policy.recommend('v', 'o', weights, row, -1.0).verdict == \
        policy.RETAIN


def test_too_little_evidence_is_said_rather_than_guessed():
    """Two usable cells out of seven is not a design recommendation."""
    weights = {'a': 1.0, 'b': 1.0, 'c': 1.0, 'd': 1.0}
    row = _row(a='effect', b='seed-dominated', c='seed-dominated',
               d='inconclusive')
    got = policy.recommend('v', 'o', weights, row, 2.0)
    assert got.verdict == policy.INSUFFICIENT
    assert '1 of 4' in got.reason


def test_disagreement_across_objectives_is_reported():
    made = [policy.Recommendation('v', 'one', policy.RETAIN, -1, 3, 3, '', 0),
            policy.Recommendation('v', 'two', policy.REMOVE, 1, 3, 3, '', 0),
            policy.Recommendation('w', 'one', policy.RETAIN, -1, 3, 3, '', 0),
            policy.Recommendation('w', 'two', policy.RETAIN, -1, 3, 3, '', 0)]
    clashes = policy.disagreements(made)
    assert 'v' in clashes and 'w' not in clashes


def test_insufficient_evidence_is_not_counted_as_disagreement():
    """Not knowing twice over is not two different answers."""
    made = [policy.Recommendation('v', 'one', policy.RETAIN, -1, 3, 3, '', 0),
            policy.Recommendation('v', 'two', policy.INSUFFICIENT,
                                  0, 0, 3, '', 0)]
    assert not policy.disagreements(made)


# ---- the intent file -----------------------------------------------------

def test_undeclared_and_declared_empty_are_different_answers():
    """A blank template entry must not read as "this rule is for nothing".

    Treating an unfilled placeholder as an empty intent would make
    every unlabelled rule pass its own test by having no test.
    """
    from lgref.recommend.intent import Intent, declared

    blank = Intent('r', (), '', None, 'unknown', ())
    filled = Intent('r', ('space_control',), '', 'framework', 'stated', ())
    assert declared({'v': [blank]}, 'v') is None
    assert declared({}, 'missing') is None
    assert declared({'w': [filled]}, 'w') == ('space_control',)


def test_one_ablation_may_answer_for_several_rules():
    """`no_knight_redesign` removes the invulnerability AND the jump.

    Keying one rule per variant silently dropped whichever came
    second, which would have hidden half of what that ablation is
    answerable for.
    """
    from lgref.recommend.intent import declared, load

    intents = load()
    assert len(intents['no_knight_redesign']) > 1, intents[
        'no_knight_redesign']
    functions = declared(intents, 'no_knight_redesign')
    rules = {entry.rule for entry in intents['no_knight_redesign']}
    assert 'knight_invulnerability' in rules and 'knight_jump_capture' in rules
    assert len(functions) >= 3, functions


def test_a_mapping_the_framework_proposed_is_marked_as_such():
    """The designer wrote prose; somebody turned it into names.

    That somebody was this framework, and a verdict resting on the
    translation rests on an interpretation. Losing the distinction
    would make the system the author of the intent it judges itself
    against, which is the circularity the whole directory exists to
    prevent.
    """
    from lgref.recommend.intent import load, proposed_by_framework

    intents = load()
    assert proposed_by_framework(intents, 'no_boulder')


def test_the_designers_own_words_are_kept_verbatim():
    """The prose is the authoritative layer; the names are derived."""
    from lgref.recommend.intent import load_all

    everything = load_all()
    assert len(everything) >= 14, sorted(everything)
    for rule, entry in everything.items():
        assert entry.statement, rule


def test_every_mapped_function_is_a_real_ontology_function():
    """A label naming something the ontology lacks cannot be scored."""
    from lgref.functions.strategic_ontology import BY_NAME
    from lgref.recommend.intent import load_all

    for rule, entry in load_all().items():
        for function in entry.functions:
            assert function in BY_NAME, (rule, function)


def test_the_ontology_gaps_come_from_every_rule_not_only_measured_ones():
    """Coverage is a claim about the VOCABULARY, not about one rule.

    Keying this by ablation variant reported two gaps and hid three,
    because nine of the fourteen annotated rules have no variant that
    measures them. What those nine say about the ontology is still
    evidence about the ontology.
    """
    from lgref.recommend.intent import load, unmapped_phrases

    gaps = unmapped_phrases()
    measured = {entry.rule for entries in load().values()
                for entry in entries}
    assert set(gaps) - measured, (
        'every reported gap comes from a measured rule; the unmeasured '
        'ones are being dropped again')
    assert 'bishop_teleport' in gaps


def test_reading_the_labels_here_does_not_weaken_the_isolation():
    """The isolation that makes reading them in Phase 5 non-circular.

    `test_label_isolation.py` walks the AST of every module under
    `identify/` and `functions/` and fails the build if one names this
    directory. That guard is what keeps a prediction from being scored
    against labels it was allowed to see, and it covers the two
    packages that make predictions -- not this one, which judges them.
    """
    from lgref.tests import test_label_isolation

    import lgref.recommend.intent as intent_mod

    assert test_label_isolation is not None
    assert intent_mod.REFERENCE.endswith(
        os.path.join('reference', 'seed_labels.yaml'))
    assert os.path.exists(intent_mod.REFERENCE)
