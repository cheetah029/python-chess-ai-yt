"""Host-side repetition enforcement for GGP games (issue #160).

Pure GDL-I cannot express the repetition rule — state hashing is
inexpressible in the language (documented in the audit; step 10's
`next_state_hash` fluent is never computed by any rule). The
resolution lives in the HOST wrapper: GGPGame tracks a repetition
history over its own fact-set states and filters legal moves whose
successor state would occur a THIRD time, mirroring the engine's
rule (RULEBOOK_v2.md Repetition Rule):

  - The repetition KEY excludes the monotonically-increasing
    turn_number fact (otherwise no state could ever repeat) and the
    rule-tracking counter families the rulebook itself excludes
    (state_repetition_count, distance_count).
  - Counting happens in step() (the initial state seeds count 1,
    mirroring the engine's record_state at game start).
  - Filtering is opt-in via `game.enforce_repetition = True` — the
    one-step lookahead costs a next-state query per legal move, so
    search code can leave it off for rollouts.
  - all_moves_repetition_blocked(player) exposes the loss condition
    ("if every legal turn would cause a third repetition, that
    player loses").
  - Direct state injection (tests, cross-validation, MCTS restore)
    desyncs any trajectory history — reset_repetition_history()
    reseeds from the current state.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()

import pytest

from ggp.game import GGPGame

INTEGRATED = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl',
                          'integrated.gdl')


@pytest.fixture(scope='module')
def ggp():
    return GGPGame.from_file(INTEGRATED)


CYCLE_FACTS = [
    ('cell', 'a', '8', 'black', 'king'),
    ('cell', 'h', '8', 'white', 'king'),
    ('cell', 'd', '4', 'white', 'rook'),
    ('cell', 'a', '1', 'black', 'rook'),
    ('control', 'white'),
    ('turn_number', '4'),
]


def _inject(ggp, facts):
    ggp.state = set(facts)
    ggp.reset_repetition_history()
    return ggp


def _shuffle_once(g):
    """One full cycle: white rook d4->d5, black rook a1->a2,
    white rook d5->d4, black rook a2->a1 — returns to the start
    position (turn_number differs; the key must ignore it)."""
    g.step({'white': ('move', 'rook', 'd', '4', 'd', '5'), 'black': 'noop'})
    g.step({'black': ('move', 'rook', 'a', '1', 'a', '2'), 'white': 'noop'})
    g.step({'white': ('move', 'rook', 'd', '5', 'd', '4'), 'black': 'noop'})
    g.step({'black': ('move', 'rook', 'a', '2', 'a', '1'), 'white': 'noop'})


def test_repetition_key_ignores_turn_number(ggp):
    """The key is the fact set minus the exempt counters. NOTE: it is
    deliberately FINER than the engine's conditional hash (raw
    last-move fluents are included), which is the SAFE direction —
    the host never wrongly blocks a move the engine allows; it may
    detect a cycle one lap later. So we compare recurring states
    from the first recurrence onward: after one full shuffle the
    position + its last-move fluents recur identically, and only
    turn_number differs — the key must match."""
    g = _inject(ggp, CYCLE_FACTS)
    _shuffle_once(g)
    k1 = g.repetition_key()
    _shuffle_once(g)
    assert g.repetition_key() == k1, (
        'the same position (incl. last-move fluents) at a different '
        'turn number must produce the same repetition key')


def test_step_counts_recurrences(ggp):
    g = _inject(ggp, CYCLE_FACTS)
    _shuffle_once(g)
    k1 = g.repetition_key()
    assert g.repetition_history[k1] == 1
    _shuffle_once(g)
    assert g.repetition_history[k1] == 2


def test_third_occurrence_move_filtered_when_enforcing(ggp):
    """After two full shuffles the post-shuffle state has occurred
    twice; the move that closes a third lap must be filtered."""
    g = _inject(ggp, CYCLE_FACTS)
    _shuffle_once(g)
    _shuffle_once(g)
    # Walk the third lap up to its closing move.
    g.step({'white': ('move', 'rook', 'd', '4', 'd', '5'), 'black': 'noop'})
    g.step({'black': ('move', 'rook', 'a', '1', 'a', '2'), 'white': 'noop'})
    g.step({'white': ('move', 'rook', 'd', '5', 'd', '4'), 'black': 'noop'})
    # Black to move; a2->a1 would recreate the post-shuffle state
    # for the 3rd time.
    closing = ('move', 'rook', 'a', '2', 'a', '1')
    unfiltered = g.legal_moves('black')
    assert closing in unfiltered, 'sanity: the move is legal per the rules'
    g.enforce_repetition = True
    try:
        filtered = g.legal_moves('black')
    finally:
        g.enforce_repetition = False
    assert closing not in filtered, (
        'a move that would cause a third repetition must be filtered')
    assert any(m != closing for m in filtered), (
        'other, non-repeating moves must survive the filter')


def test_all_moves_repetition_blocked_detection(ggp):
    """Stuff the history so EVERY legal successor is at count 2 —
    the loss condition must be detected."""
    g = _inject(ggp, CYCLE_FACTS)
    for move in g.legal_moves('white'):
        nxt = g.peek_repetition_key({'white': move, 'black': 'noop'})
        g.repetition_history[nxt] = 2
    assert g.all_moves_repetition_blocked('white') is True
    g.reset_repetition_history()
    assert g.all_moves_repetition_blocked('white') is False


def test_reset_reseeds_from_current_state(ggp):
    g = _inject(ggp, CYCLE_FACTS)
    _shuffle_once(g)
    _shuffle_once(g)
    assert g.repetition_history[g.repetition_key()] == 2
    g.reset_repetition_history()
    assert g.repetition_history == {g.repetition_key(): 1}
