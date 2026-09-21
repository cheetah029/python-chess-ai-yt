"""The repetition-filter early exit must not change a single legal move.

Issue #171. Profiling the LGREF workload found `filter_repetition_moves`
was 73% of all move-generation time: `would_cause_repetition` ran once per
candidate move (~68 per position at the measured branching factor), and
each call make/unmakes the move and hashes all 64 squares plus per-piece
line-of-sight checks.

The optimisation is an early return, and it is behaviour-preserving BY
CONSTRUCTION rather than by approximation: `would_cause_repetition` blocks
a move only when the successor state has already occurred twice, so when no
state has occurred twice every call would have returned False anyway.

That argument is only as good as its premises, and the premises are about
the whole codebase — that nothing decrements `state_history`, and that the
hash is unaffected. So this file does not test the reasoning; it tests the
OUTCOME, move for move, with the guard forced off to reproduce the original
code path exactly.

This matters more than a normal optimisation test. A silent change to the
repetition rule would alter every LGREF measurement while leaving the rest
of the suite green — the exact failure mode the project brief warns about.
"""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import board as board_mod
from experiments.variants import VARIANTS, make_engine


_ORIGINAL_GUARD = board_mod.Board._any_state_seen_twice


@pytest.fixture
def restore_guard():
    yield
    board_mod.Board._any_state_seen_twice = _ORIGINAL_GUARD


def _turn_key(turn):
    # repr, not a raw tuple: from_sq is None for the intersection boulder
    # and None does not order against tuples.
    return repr((turn.turn_type, getattr(turn.piece, 'name', None),
                 turn.from_sq, turn.to_sq, turn.jump_choice,
                 turn.promo_choice, turn.transform_target,
                 turn.has_jump_offer))


def _play(variant, seed, max_turns, early_exit):
    """Play one seeded game, recording the full legal-turn set at every ply.

    `early_exit=False` forces the guard to report True always, which
    reproduces the pre-optimisation path exactly.
    """
    board_mod.Board._any_state_seen_twice = (
        _ORIGINAL_GUARD if early_exit else (lambda self: True))
    rng = random.Random(seed)
    engine = make_engine(variant, max_turns=max_turns)
    trace = []
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        trace.append(sorted(_turn_key(t) for t in turns))
        engine.execute_turn(rng.choice(turns))
    return trace, engine.winner, engine.turn_number


@pytest.mark.parametrize('variant', sorted(VARIANTS))
def test_early_exit_preserves_every_legal_move(variant, restore_guard):
    """Move-for-move identity, per variant, under a fixed seed."""
    with_exit, winner_a, turns_a = _play(variant, 0, 120, True)
    without, winner_b, turns_b = _play(variant, 0, 120, False)

    assert len(with_exit) == len(without), (
        f'{variant}: game lengths diverged '
        f'({len(with_exit)} vs {len(without)} plies)')

    for ply, (a, b) in enumerate(zip(with_exit, without)):
        assert a == b, (
            f'{variant} ply {ply}: the early exit changed the legal-move '
            f'set.\n  only with exit: {sorted(set(a) - set(b))[:3]}\n'
            f'  only without:   {sorted(set(b) - set(a))[:3]}')

    assert (winner_a, turns_a) == (winner_b, turns_b), (
        f'{variant}: outcome diverged — '
        f'{winner_a}/{turns_a} vs {winner_b}/{turns_b}')


def test_guard_is_false_at_game_start():
    """No state has occurred twice at ply 0, so the exit must be taken —
    otherwise the optimisation never fires and the test above passes for
    the wrong reason."""
    engine = make_engine('full')
    assert engine.board._any_state_seen_twice() is False


def test_guard_becomes_true_once_a_state_repeats():
    """And it must stop firing once a repeat exists, or the filter would
    be skipped when it actually matters."""
    engine = make_engine('full')
    engine.board.state_history = {'some-state': 2}
    assert engine.board._any_state_seen_twice() is True


def test_guard_ignores_states_seen_only_once():
    engine = make_engine('full')
    engine.board.state_history = {'a': 1, 'b': 1, 'c': 1}
    assert engine.board._any_state_seen_twice() is False
