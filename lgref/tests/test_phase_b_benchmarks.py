"""The Phase B benchmarks must have the properties they advertise.

Phase B asks for "small, completely solvable games with recorded
statement-to-rule mappings, including shared statements, redundant rules,
and interacting rules", with the mappings retained outside the model
input.

RECORDED and HIDDEN are two properties of one artifact and Phase B needs
both: recorded so there is something to score against, hidden so the
method cannot score by reading the answer. The hiding is enforced in
test_label_isolation; this file checks the recording is true.

Every property here was WRONG at least once while the game was being
built -- the redundancy was stated against the wrong counterpart, the
first ablation deleted a guard's definition instead of relaxing it
(making the game unplayable), the interaction produced a state with no
legal move (a malformed GDL game), and the sharing existed only in a
docstring. A benchmark whose advertised properties are not its real
properties is worse than no benchmark.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'src'))

from lgref.identify.testgames import reference
from lgref.identify.testgames.ground_truth import GAMES, SPLITS, STRUCTURE


def test_every_benchmark_is_solvable_by_enumeration():
    """"Completely solvable" is the requirement, and small enough to
    enumerate is how these satisfy it."""
    got = reference.enumerate_game('corridor')
    assert got.states > 10, 'too small to exercise anything'
    assert got.states < 100000, 'not exhaustively solvable'
    assert got.terminals > 0, 'no reachable outcome'


def test_no_benchmark_state_leaves_a_player_stuck():
    """A GDL game whose non-terminal state offers no legal move is
    MALFORMED. An earlier corridor did exactly that, and it looked like
    an interesting rule interaction."""
    assert reference.enumerate_game('corridor').stuck == 0


def test_the_redundant_rule_measures_exactly_zero():
    """What redundancy MEANS, as a checkable number.

    Relaxing `boundary` must change no reachable state, no outcome and no
    option count -- the arithmetic already bounds the corridor, because
    `succ` stops at 7. A method reporting an effect here reports noise.
    """
    base = reference.enumerate_game('corridor')
    relaxed = reference.enumerate_game('corridor', ('boundary',))
    assert relaxed.states == base.states
    assert relaxed.terminals == base.terminals
    assert abs(relaxed.mean_branching - base.mean_branching) < 1e-9


def test_the_interacting_pair_is_super_additive():
    """The failure mode this game exists to expose.

    Measured: blocking alone +0.1232, tempo alone +0.1467, together
    +0.4149 on mean branching -- 54% more than the sum. A study ablating
    one rule at a time sees the two small numbers and misses the rest.
    """
    base = reference.enumerate_game('corridor').mean_branching
    first = reference.enumerate_game('corridor', ('blocking',))
    second = reference.enumerate_game('corridor', ('no_double_double',))
    both = reference.enumerate_game(
        'corridor', ('blocking', 'no_double_double'))

    alone = ((first.mean_branching - base)
             + (second.mean_branching - base))
    together = both.mean_branching - base
    assert first.mean_branching > base, 'blocking must bind on its own'
    assert second.mean_branching > base, 'tempo must bind on its own'
    assert together > alone, (
        'joint {:+.4f} vs sum of parts {:+.4f}'.format(together, alone))


def test_the_reference_verifies_its_own_claims():
    """`verify` is what keeps the advertised properties honest."""
    assert reference.verify('corridor') == []


def test_an_ablation_naming_a_vanished_fragment_is_refused():
    """Silent no-ops are how an ablation stops ablating.

    If the game is edited and a conjunct renamed, the ablation must fail
    loudly rather than return the baseline and look like a zero effect.
    """
    import pytest

    real = reference.ABLATIONS['corridor']['boundary']
    reference.ABLATIONS['corridor']['boundary'] = (' & no_such_guard(X)',)
    try:
        with pytest.raises(KeyError):
            reference.game_text('corridor', ('boundary',))
    finally:
        reference.ABLATIONS['corridor']['boundary'] = real


def test_the_splits_keep_related_variants_together():
    placed = [g for names in SPLITS.values() for g in names]
    assert sorted(placed) == sorted(GAMES)
    assert len(placed) == len(set(placed))


def test_the_structure_record_covers_every_game():
    assert sorted(STRUCTURE) == sorted(GAMES)
