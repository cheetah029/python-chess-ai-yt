"""Every instrument, run on a game it has never seen.

THE STANDING INSTRUCTION behind this file:

    "Make sure everything is still general and can always be applied
    to all games."

The existing audit (`test_generality_audit.py`) checks that a general
module names no game -- no piece names, no board sizes, no values in
one game's units. That catches a module that LEARNED a game. It does
not catch an instrument that quietly requires the shape of one: a
`cells` list, a board of squares, a turn that is an integer.

So this file invents a third game -- not m,n,k, not the case study, no
board at all -- and runs the instruments on it. An instrument that
needs more than the protocol fails here, and the two that genuinely do
need more are listed by name with the reason, so the limitation is a
decision rather than an omission.

NIM is a deliberate choice. It has no geometry, its moves are not
cells, its states are not grids, and nothing about it resembles either
real game. If an instrument reads NIM, it reads the protocol.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import inspect

import pytest

from lgref.experiments import validate


class Nim(object):
    """Heaps of counters; take any number from one heap; taking the
    last counter wins.

    The protocol and nothing else: `current_player`, `winner`,
    `get_all_legal_turns`, `execute_turn`, `is_game_over`, `copy`.
    """

    def __init__(self, heaps=(3, 4, 5), to_move='a'):
        self.heaps = list(heaps)
        self.current_player = to_move
        self.winner = None

    def copy(self):
        clone = Nim(tuple(self.heaps), self.current_player)
        clone.winner = self.winner
        return clone

    def get_all_legal_turns(self):
        return [(index, take)
                for index, heap in enumerate(self.heaps)
                for take in range(1, heap + 1)]

    def execute_turn(self, turn):
        index, take = turn
        mover = self.current_player
        self.heaps[index] -= take
        if not any(self.heaps):
            self.winner = mover
        self.current_player = 'b' if mover == 'a' else 'a'

    def is_game_over(self):
        return self.winner is not None or not any(self.heaps)


def make_nim(_variant='full', max_turns=None):
    return Nim()


def coin(game, rng):
    return rng.choice(game.get_all_legal_turns())


#: Instruments that must read any game that follows the protocol.
GENERAL = (
    'outcome_weights', 'choice_rank', 'tie_rate', 'forced_turns',
    'forced_move_rate', 'optimal_rate', 'optimal_rate_by_phase',
    'optimal_action_rate', 'optimal_turns', 'strictly_better',
    'threat_count', 'initiative_rate',
)

#: Instruments that need MORE than the protocol, each with the reason
#: in its own docstring. Listed so the limitation is a decision rather
#: than something nobody noticed.
LIMITED = {
    'threat_count': 'side to move must be settable on a copy',
    'initiative_rate': 'built on threat_count',
}


def test_every_public_instrument_is_accounted_for():
    """A NEW INSTRUMENT MUST CHOOSE. Adding one that is neither proven
    general nor declared limited should fail here rather than quietly
    becoming a case-study special."""
    public = set()
    for name, value in vars(validate).items():
        if name.startswith('_') or not inspect.isfunction(value):
            continue
        if value.__module__ != validate.__name__:
            continue
        public.add(name)
    declared = set(GENERAL) | set(LIMITED)
    missing = sorted(name for name in public
                     if name not in declared
                     and name.endswith(('_rate', '_rank', '_weights',
                                        '_turns', '_better', '_count',
                                        '_phase')))
    assert not missing, (
        'these instruments are neither proven general nor declared '
        'limited: {0}'.format(missing))


def test_the_rule_derived_prior_reads_a_game_with_no_board():
    """`outcome_weights` on NIM: no cells, no geometry, moves that are
    (heap, count) pairs."""
    weights = validate.outcome_weights(make_nim, trials=60, seed=1)
    assert weights, 'the prior read nothing from NIM'
    assert any(seen >= 5 for _wins, seen in weights.values())
    # NIM's winning move is taking the last counter, which the prior
    # should rate highly without being told the rules.
    best = max(weights.items(),
               key=lambda item: (item[1][0] / item[1][1]
                                 if item[1][1] >= 5 else -1))
    assert best[1][0] / best[1][1] > 0.5, best


def test_the_placement_rank_reads_it_too_and_is_unbiased_there():
    weights = validate.outcome_weights(make_nim, trials=120, seed=1)
    scores = []
    for seed in (2, 5, 9):
        rank, asked = validate.choice_rank(
            make_nim, coin, weights, trials=40, seed=seed,
            min_setup=0, max_setup=2)
        if asked:
            scores.append(rank)
    assert scores, 'nothing was measurable on NIM'
    average = sum(scores) / len(scores)
    assert 0.35 < average < 0.65, (
        'a random player should sit near indifference on NIM, not '
        '{0:.1%}'.format(average))


def test_the_tie_rate_reads_it():
    flat, asked = validate.tie_rate(make_nim, lambda game, turn: 0.0,
                                    trials=8, seed=1, min_setup=0,
                                    max_setup=2)
    assert asked and flat == 1.0
    sharp, asked_two = validate.tie_rate(
        make_nim, lambda game, turn: turn[1], trials=8, seed=1,
        min_setup=0, max_setup=2)
    assert asked_two and sharp < 0.5


def test_the_forced_move_check_reads_it():
    """In NIM a position with one counter left has exactly one winning
    move, which is the shape `forced_turns` looks for."""
    # NOT a one-move position: `forced_turns` returns None when every
    # move is equally forced, by design -- a position where nothing can
    # be got wrong is not evidence about anything.
    assert validate.forced_turns(Nim(heaps=(1, 0, 0))) is None

    # From (2, 1) exactly one move avoids handing over the win.
    wanted = validate.forced_turns(Nim(heaps=(2, 1, 0)))
    assert wanted == [(0, 1)], wanted

    rate, asked = validate.forced_move_rate(make_nim, coin, trials=40,
                                            seed=3, min_setup=1,
                                            max_setup=6)
    assert asked > 0, 'no forced positions found in NIM'
    assert 0.0 <= rate <= 1.0


def test_the_exact_grader_reads_it():
    """NIM is small enough to solve, so `optimal_rate` applies -- and
    an oracle must beat a coin on it."""
    def oracle(game, rng):
        best = validate.optimal_turns(game, cap=40)
        return best[0] if best else game.get_all_legal_turns()[0]

    good, _chance, asked = validate.optimal_rate(
        make_nim, oracle, trials=25, seed=4, cap=40, min_setup=1,
        max_setup=4)
    bad, _chance2, asked_two = validate.optimal_rate(
        make_nim, coin, trials=25, seed=4, cap=40, min_setup=1,
        max_setup=4)
    assert asked > 5 and asked_two > 5, (asked, asked_two)
    assert good == 1.0, good
    assert bad < good


def test_the_two_limited_instruments_say_so_in_their_own_docstrings():
    """A limitation recorded only in a test is a limitation the next
    reader of the function will not see."""
    for name in LIMITED:
        text = inspect.getdoc(getattr(validate, name)) or ''
        assert ('does not port' in text.lower()
                or 'needs a game whose' in text.lower()
                or 'm,n,k-shaped' in text.lower()), (
            '{0} does not declare its limitation'.format(name))


def test_the_limited_pair_still_works_where_it_applies():
    """NIM happens to expose a settable side to move, so they run here
    -- the limitation is real but narrow, and worth not overstating."""
    game = Nim(heaps=(1, 0, 0))
    assert validate.threat_count(game, 'a') == 1
    assert validate.threat_count(game, 'b') == 1
    rate, asked = validate.initiative_rate(make_nim, coin, trials=20,
                                           seed=2, min_setup=1,
                                           max_setup=5)
    assert asked > 0 and 0.0 <= rate <= 1.0


def test_the_gate_is_pure_data_and_needs_no_game_at_all():
    assert validate.strictly_better({'x': (0.5, 0.0, 400)},
                                    {'x': (0.5, 0.0, 400)}) == []
    assert validate.strictly_better({'x': (0.9, 0.0, 400)},
                                    {'x': (0.5, 0.0, 400)})
