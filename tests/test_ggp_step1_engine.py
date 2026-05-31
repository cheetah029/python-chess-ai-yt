"""End-to-end test: load step-1 GDL into the GGP, enumerate legal
moves from the initial state, and sanity-check the count.

Step 1 is kings + queens only:

  White: King g1, Queen b1   (both move king-step = 1 square in any
                              of 8 directions)
  Black: King b8, Queen g8
  White to move.

Expected legal moves from initial state for white:
  King at g1 can move to any of 8 chebyshev-1 squares minus
  off-board minus self-piece. g1's neighbours: f1, h1, f2, g2,
  h2 (and the 'g0' / 'h0' / 'f0' squares are off-board). The
  white queen at b1 doesn't block g1's neighbourhood. So 5 king
  moves.
  Queen at b1 can move to a1, c1, a2, b2, c2 (5 destinations).
  Total: 5 + 5 = 10 spatial moves for white. Black plays noop.

(Step 1 doesn't include the queen's transformation / manipulation
actions — those arrive in step 7.)

This is the FIRST end-to-end GGP integration validation. Future
GGP work will extend to steps 2-11 with cross-validation against
src/engine.py's get_all_legal_turns().
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from ggp.parser import parse
from ggp.kb import KnowledgeBase
from ggp.resolver import Resolver


def _load(filename):
    path = os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'gdl', filename)
    with open(path) as f:
        text = f.read()
    kb = KnowledgeBase()
    for form in parse(text):
        kb.add_clause(form)
    return kb


def _project_initial_state(kb):
    """Step 1 doesn't have an explicit 'state' — the initial state
    is the set of (init ?fact) facts. For GGP queries we need
    to lift each (init ?fact) into a (true ?fact) representing
    the current-state KB.

    Returns a NEW KnowledgeBase containing all rule clauses from
    `kb` plus a (true ?fact) for each init fact.
    """
    state_kb = KnowledgeBase()
    # Copy all rules unchanged.
    for pred in kb.all_predicates():
        for head, body in kb.rules_for(pred):
            state_kb._add_rule(head, body)
        for fact in kb.facts_for(pred):
            # Ground init facts → wrap in `(true ...)`. Other ground
            # facts (e.g. `(role white)`, `(file_eastward a b)`) are
            # PERMANENT facts and stay as-is.
            if isinstance(fact, tuple) and fact and fact[0] == 'init':
                inner = fact[1]
                state_kb._add_fact(('true', inner))
            else:
                state_kb._add_fact(fact)
    return state_kb


def test_step1_loads_into_kb():
    kb = _load('step1_kings_queens.gdl')
    assert kb.fact_count() > 0
    assert kb.rule_count() > 0


def test_step1_init_state_has_kings_and_queens():
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    results = sorted(
        (b['?f'], b['?r'], b['?c'], b['?p'])
        for b in r.query(('true', ('cell', '?f', '?r', '?c', '?p'))))
    assert ('g', '1', 'white', 'king') in results
    assert ('b', '1', 'white', 'queen') in results
    assert ('b', '8', 'black', 'king') in results
    assert ('g', '8', 'black', 'queen') in results
    assert len(results) == 4


def test_step1_white_legal_move_count_from_init():
    """The headline end-to-end check: legal moves for white from
    the initial state.

    Expected: 5 king destinations from g1 + 5 queen destinations
    from b1 = 10 moves. (Plus white's noop is NOT legal here —
    only the off-turn role plays noop.)
    """
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    results = list(r.query(('legal', 'white', '?move')))
    moves = [b['?move'] for b in results]
    assert len(moves) == 10, (
        f'expected 10 legal moves for white from init; got '
        f'{len(moves)}: {moves}')


def test_step1_black_only_legal_move_is_noop():
    """Black is the off-turn role at the initial state, so the only
    legal black move is noop."""
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    results = list(r.query(('legal', 'black', '?move')))
    moves = [b['?move'] for b in results]
    assert moves == ['noop'], (
        f'black should only have noop; got {moves}')


def test_step1_white_king_can_move_to_f1():
    """Specific legal-move check: white king at g1 can move to f1."""
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    target = ('legal', 'white', ('move', 'king', 'g', '1', 'f', '1'))
    results = list(r.query(target))
    assert len(results) >= 1, 'white king should be able to move g1 -> f1'


def test_step1_white_king_cannot_move_off_board():
    """Step 1 has no g0 file or rank, so any 'off-board' move
    should not be legal."""
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    # g1 → g0 is off-board. Should produce no legal result.
    target = ('legal', 'white', ('move', 'king', 'g', '1', 'g', '0'))
    results = list(r.query(target))
    assert len(results) == 0, 'g1 -> g0 must be off-board'


def test_step1_white_king_cannot_move_to_b1():
    """g1 -> b1 is 5 squares away, NOT king-step adjacency.
    Should not be legal."""
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    target = ('legal', 'white', ('move', 'king', 'g', '1', 'b', '1'))
    results = list(r.query(target))
    assert len(results) == 0


def test_step1_not_terminal_at_init():
    """Game is not over at the start."""
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    # `terminal` is a 0-ary predicate.
    results = list(r.query('terminal'))
    assert results == []


def test_step1_white_queen_can_move_to_a1():
    """White queen at b1 can move to a1 (king-step)."""
    kb = _load('step1_kings_queens.gdl')
    state_kb = _project_initial_state(kb)
    r = Resolver(state_kb)
    target = ('legal', 'white', ('move', 'queen', 'b', '1', 'a', '1'))
    results = list(r.query(target))
    assert len(results) >= 1
