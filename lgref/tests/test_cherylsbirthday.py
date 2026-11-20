"""Cheryl's Birthday: GDL-III announcements are knowledge conditions.

The puzzle's three public statements are moves legal exactly when they
are true, so each is a `knows` condition, and the third nests one
role's knowledge inside another's. The answer, July 16, is checked
three independent ways: by playing the game and asking
`GGPGame.knows`, by reading the `KnowledgeModel`'s play sequences
directly, and against a brute-force solution of the puzzle written
below without any GDL.

A reader and epistemic-model correctness test, not a benchmark game:
no player plays knowledge goals, so it is not in `ground_truth.GAMES`.
"""

import copy
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp import dialect  # noqa: E402
from ggp.game import GGPGame  # noqa: E402

PATH = os.path.join(HERE, '..', 'identify', 'testgames',
                    'cherylsbirthday.gdl')

DATES = [('may', 15), ('may', 16), ('may', 19), ('june', 17),
         ('june', 18), ('july', 14), ('july', 16), ('august', 14),
         ('august', 15), ('august', 17)]
LISTENERS = ('albert', 'bernard')


def brute_force():
    """The puzzle solved by filtering the candidate set, no GDL."""
    def known(cands, date, by):
        # Albert is told the month (index 0), Bernard the day (1).
        return sum(1 for c in cands if c[by] == date[by]) == 1

    cands = list(DATES)
    # 1. Albert doesn't know, and knows Bernard doesn't know.
    cands = [d for d in cands if not known(DATES, d, 0)
             and all(not known(DATES, o, 1)
                     for o in DATES if o[0] == d[0])]
    # 2. Bernard now knows.
    cands = [d for d in cands if known(cands, d, 1)]
    # 3. Albert now knows too.
    cands = [d for d in cands if known(cands, d, 0)]
    return cands


@pytest.fixture(scope='module')
def start():
    return GGPGame.from_file(PATH)


def _play(start, month, day):
    """Play one birthday to the end; return the game and what was said
    (each round's only legal move is forced by the truth)."""
    game = copy.deepcopy(start)
    game.step({'random': ('birthday', month, str(day)),
               'albert': 'noop', 'bernard': 'noop'})
    said = []
    while not game.is_terminal():
        moves = {r: game.legal_moves(r) for r in game.roles}
        assert all(len(m) == 1 for m in moves.values()), moves
        said += [m[0][1] for m in moves.values() if m[0] != 'noop']
        game.step({r: m[0] for r, m in moves.items()})
    return game, said


def test_the_brute_force_check_solves_the_puzzle():
    assert brute_force() == [('july', 16)]


def test_it_is_read_as_gdl_iii(start):
    assert start.dialect == dialect.GDL_III
    assert sorted(m[1:] for m in start.legal_moves('random')) == sorted(
        (m, str(d)) for m, d in DATES)


def test_july_16_is_the_only_date_with_all_three_announcements(start):
    allowed = [(m, d) for m, d in DATES
               if _play(start, m, d)[1] == ['yes', 'yes', 'yes']]
    assert allowed == brute_force() == [('july', 16)]


@pytest.mark.parametrize('month, day', DATES)
def test_every_announcement_matches_the_brute_force_filter(start, month,
                                                           day):
    """Not just the answer: each date's yes/no at each round is what
    the candidate-set filter says, including the dates where a later
    'no' teaches the listener (August 14: Bernard's no tells Albert)."""
    def known(cands, date, by):
        return sum(1 for c in cands if c[by] == date[by]) == 1

    date = (month, day)
    first = (not known(DATES, date, 0)
             and all(not known(DATES, o, 1)
                     for o in DATES if o[0] == month))
    after1 = [d for d in DATES
              if (not known(DATES, d, 0)
                  and all(not known(DATES, o, 1)
                          for o in DATES if o[0] == d[0])) == first]
    second = known(after1, date, 1)
    after2 = [d for d in after1 if known(after1, d, 1) == second]
    third = known(after2, date, 0)
    expected = ['yes' if x else 'no' for x in (first, second, third)]
    assert _play(start, month, day)[1] == expected


def test_knowledge_at_each_stage_of_july_16(start):
    game = copy.deepcopy(start)
    date = ('isDate', 'july', '16')
    game.step({'random': ('birthday', 'july', '16'),
               'albert': 'noop', 'bernard': 'noop'})
    # Told only July and 16, nobody knows yet ...
    assert not game.knows('albert', date)
    assert not game.knows('bernard', date)
    # ... yet Albert already knows Bernard doesn't: July holds no
    # unique day (May 19 and June 18 are the unique ones).
    assert game.knows('albert', ('bernardIgnorant',))
    game.step({'random': 'noop', 'albert': ('say', 'yes'),
               'bernard': 'noop'})
    assert game.knows('bernard', date)
    assert not game.knows('albert', date)
    game.step({'random': 'noop', 'albert': 'noop',
               'bernard': ('say', 'yes')})
    assert game.knows('albert', date)
    game.step({'random': 'noop', 'albert': ('say', 'yes'),
               'bernard': 'noop'})
    assert game.is_terminal()
    assert {r: game.goal(r) for r in game.roles} == {
        'albert': 100, 'bernard': 100, 'random': 0}
    # Everything was public after the deal, so the date is now common
    # knowledge: no play sequence of this length is linked to it by
    # either listener's uncertainty.
    assert game.knows(None, date)


def test_the_knowledge_model_alone_gives_the_same_answer(start):
    """Read the play sequences off the model, without playing: those of
    full length in which all three announcements were yes."""
    model = start._knowledge
    full = model.sequences(4)
    assert len(full) == len(DATES)
    allowed = []
    for history in full:
        said = [move for joint in history[1:] for role, move in joint
                if role in LISTENERS and move != 'noop']
        if said == [('say', 'yes')] * 3:
            birthday = dict(history[0])['random']
            allowed.append((birthday[1], int(birthday[2])))
            for listener in LISTENERS:
                assert model.knows(history, listener,
                                   ('isDate',) + birthday[1:])
    assert allowed == brute_force()
