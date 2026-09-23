"""Varying a rule's numeric parameter — the automatable part of `replace`.

Issue #196. `relax` and `remove` can only say whether a rule matters.
They cannot say whether THIS version of it is the right one, so they
cannot produce the REVISE verdict the project's deliverable requires.
Varying a parameter can, and needs no designer.

The danger is silent: substituting the wrong constant yields a variant
that loads, plays, and means something else. These tests pin the
distinction that avoids it.
"""

import os

import pytest

from ggp.game import GGPGame
from ggp.infix import forms_to_infix_lines, parse_infix
from lgref.ablate import parameters as P

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')


@pytest.fixture(scope='module')
def official():
    with open(OFFICIAL) as handle:
        return parse_infix(handle.read())


def _legal_at_start(forms):
    game = GGPGame('\n'.join(forms_to_infix_lines(forms)))
    return {role: len(game.legal_moves(role)) for role in game.roles}


def _params(forms):
    return {(p.predicate, p.value): p for p in P.parameters(forms)}


# ------------------------------------------------------- what is a parameter ----

def test_counter_encoded_fluents_are_identified(official):
    """The cooldown's length is a chain length, not a constant."""
    assert 'boulder_cooldown' in P.counters(official)


def test_thresholds_are_identified(official):
    found = _params(official)
    for predicate, value in (('tiny_endgame_limit_exceeded', '3'),
                             ('would_repeat_third_time', '2'),
                             ('and_white_and_turn_1', '1')):
        assert (predicate, value) in found, (predicate, value)
        assert found[(predicate, value)].kind == 'threshold'


def test_counter_constants_are_never_offered_for_substitution(official):
    """The refusal that matters, and why.

    Substituting into a counter chain produces a variant that loads and
    plays and is wrong in the opposite direction from the intent, with
    no error anywhere. See test_substituting_into_a_counter_breaks_the_chain.
    """
    for parameter in P.parameters(official):
        if parameter.kind == 'counter':
            assert P.sweep(official, parameter) == []


def test_substituting_into_a_counter_breaks_the_chain(official):
    """Demonstrates the failure the refusal prevents.

    `next(boulder_cooldown(2)) :- boulder_moved_this_turn` sets the
    counter, and `next(boulder_cooldown(1)) :- true(boulder_cooldown(2))`
    steps it down. Substitute 2 -> 3 and the set value is no longer the
    stepped-down value: nothing reads 2 back, so the counter falls off
    its chain and the cooldown gets SHORTER. The resulting game still
    loads and still plays, which is exactly why this must be refused
    structurally rather than caught by a smoke test.
    """
    from lgref.ablate.operations import (body_of, head_of, head_predicate,
                                         is_negated, is_rule)
    perturbed, count = P.perturb(official, 'boulder_cooldown', '2', '3')
    assert count, 'nothing was substituted; the test proves nothing'

    written, read = set(), set()
    for form in perturbed:
        head = head_of(form)
        if (isinstance(head, tuple) and head
                and head[0] in ('next', 'init')
                and head_predicate(form) == 'boulder_cooldown'):
            payload = head[1]
            if isinstance(payload, tuple) and len(payload) > 1:
                written.add(payload[1])
        if is_rule(form):
            for goal in body_of(form):
                inner = goal[1] if is_negated(goal) else goal
                if isinstance(inner, tuple) and inner and inner[0] == 'true':
                    payload = inner[1]
                    if (isinstance(payload, tuple) and payload
                            and payload[0] == 'boulder_cooldown'):
                        read.add(payload[1])

    assert written - read, (
        'expected a counter value that nothing reads back')
    assert _legal_at_start(perturbed), (
        'the broken variant still loads and plays -- which is the point')


# -------------------------------------------------------------- the sweep ----

def test_sweep_offers_neighbouring_reachable_values(official):
    found = _params(official)
    assert P.sweep(official, found[('tiny_endgame_limit_exceeded', '3')]) \
        == [2, 4]
    assert P.sweep(official, found[('would_repeat_third_time', '2')]) \
        == [1, 3]


def test_sweep_never_offers_an_unreachable_value(official):
    """A cap of 99 on a counter that reaches 3 is no rule, not a mild one.

    It would load, play, and be reported as a null contribution for a
    provision that was never actually varied.
    """
    for parameter in P.parameters(official):
        reachable = {int(v) for v
                     in P.reachable_values(official, parameter.fluent)}
        for value in P.sweep(official, parameter):
            assert value in reachable


def test_range_inference_follows_a_variable_binding(official):
    """`distance_count` counts up through `succ`, so its range is succ's.

    Reading only the literals in its `next` heads gives {0, 1} and the
    threshold of 3 then looks out of range, so no perturbation would be
    offered for the tiny endgame cap at all.
    """
    reachable = {int(v) for v in P.reachable_values(official,
                                                    'distance_count')}
    assert max(reachable) >= 4, sorted(reachable)


# ------------------------------------------------------- it actually works ----

@pytest.mark.parametrize('predicate,old,new', [
    ('tiny_endgame_limit_exceeded', '3', '2'),
    ('tiny_endgame_limit_exceeded', '3', '4'),
    ('would_repeat_third_time', '2', '1'),
])
def test_perturbed_descriptions_load_and_play(official, predicate, old, new):
    perturbed, count = P.perturb(official, predicate, old, new)
    assert count == 1
    assert sum(_legal_at_start(perturbed).values()) > 0


def test_a_perturbation_with_a_visible_effect(official):
    """Lifting the turn-1 bar hands White its four boulder first-moves.

    A perturbation that changes no observable behaviour would be
    indistinguishable from one that silently did nothing, so at least
    one case has to show the change arriving.
    """
    base = _legal_at_start(official)['white']
    perturbed, _ = P.perturb(official, 'and_white_and_turn_1', '1', '2')
    assert _legal_at_start(perturbed)['white'] == base + 4


def test_substitution_is_confined_to_the_named_predicate(official):
    """`3` is all over a board description; only one clause may change."""
    _, count = P.perturb(official, 'tiny_endgame_limit_exceeded', '3', '2')
    assert count == 1


def test_the_submodule_is_not_shadowed_by_the_function():
    """`lgref.ablate.parameters` must stay the MODULE.

    Re-exporting the `parameters` function from the package `__init__`
    rebinds this attribute to the function, so
    `from lgref.ablate import parameters as params` hands back a
    function and every `params.perturb(...)` fails with
    `'function' object has no attribute`. The CLI hit exactly that.
    """
    import types

    from lgref.ablate import parameters as maybe_module
    assert isinstance(maybe_module, types.ModuleType), (
        'the parameters submodule is shadowed by a same-named export')
    assert callable(maybe_module.parameters)
    assert callable(maybe_module.perturb)
