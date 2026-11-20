"""The validation protocol and the games it runs on (#315).

What is tested here is the DISCIPLINE, not a score: the dev split is the
only one tuned on, the validation split is consulted once by a rule fixed
in code, the test split never influences a choice, and the games and
labels are what they claim to be.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.identify import protocol
from lgref.identify.clauses import load
from lgref.identify.testgames.ground_truth import (GAMES, SPLITS,
                                                   expected_partition,
                                                   matches)

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, '..', 'identify', 'testgames')

NEW_GAMES = ('dropthree', 'breakthrough', 'skirmish')


def _nodes(game):
    return load(os.path.join(GAME_DIR, game + '.gdl'))


# ---- the splits -----------------------------------------------------------

def test_every_labelled_game_is_in_exactly_one_split():
    placed = [g for games in SPLITS.values() for g in games]
    assert sorted(placed) == sorted(GAMES)
    assert len(placed) == len(set(placed))


def test_the_test_split_is_bigger_than_one_game():
    """The reviewer's point: one held-out game is not evidence about
    generalisation."""
    assert len(SPLITS['test']) >= 4


# ---- the protocol only looks where it is allowed to -----------------------

def _spy(monkeypatch):
    seen = []
    real = protocol.score

    def score(game, procedure, seed=0):
        seen.append(game)
        return real(game, procedure, seed)

    monkeypatch.setattr(protocol, 'score', score)
    return seen


def test_tuning_reads_the_dev_split_only(monkeypatch):
    seen = _spy(monkeypatch)
    protocol.select()
    assert set(seen) == set(SPLITS['dev'])


def test_the_decision_reads_the_validation_split_only(monkeypatch):
    seen = _spy(monkeypatch)
    protocol.decide(('coverage', 0.05))
    assert set(seen) == set(SPLITS['validation'])


def test_a_tie_on_validation_keeps_the_default(monkeypatch):
    monkeypatch.setattr(protocol, 'mean_ari', lambda games, p, seed=0: 0.5)
    adopted, _ours, _base = protocol.decide(('scaled', 0.75))
    assert adopted == protocol.DEFAULT


def test_a_tie_on_dev_keeps_the_default(monkeypatch):
    monkeypatch.setattr(protocol, 'mean_ari', lambda games, p, seed=0: 0.5)
    chosen, _table = protocol.select()
    assert chosen == protocol.DEFAULT


def test_raw_resolutions_are_never_candidates():
    """A raw resolution tuned on 35-statement games does not transfer to
    a 522-statement description, so it is reported, never chosen."""
    assert all(kind != 'fixed' for kind, _v in protocol.CANDIDATES)
    assert protocol.DEFAULT in protocol.CANDIDATES


def test_the_protocol_is_deterministic():
    assert protocol.run() == protocol.run()


# ---- failure modes ---------------------------------------------------------

def test_failure_modes_are_reported_for_every_game():
    for game in GAMES:
        report = protocol.failure_modes(game)
        assert set(report) == {'game', 'fragmented', 'merged', 'dropped',
                               'shared_lost', 'n_shared'}
        assert len(report['shared_lost']) <= report['n_shared']


def test_a_perfect_partition_has_no_failure_modes(monkeypatch):
    """The analysis has to be able to say "nothing wrong", or it would
    report failures that are artefacts of itself."""
    from lgref.identify.cluster import CandidateRule
    from lgref.identify.graph import ClauseGraph

    game = 'tictactoe'
    nodes = _nodes(game)
    graph = ClauseGraph(nodes)
    expected = expected_partition(game, nodes)
    rules = []
    for name in GAMES[game]:
        members = {c for c, names in expected.items() if name in names}
        rules.append(CandidateRule(name, members, set(), graph))
    monkeypatch.setattr(protocol, 'cluster',
                        lambda *a, **k: (rules, []))
    report = protocol.failure_modes(game)
    assert report['fragmented'] == {} and report['merged'] == {}
    assert report['dropped'] == []


# ---- the games are well formed, and the labels select what they say ------

@pytest.mark.parametrize('game', NEW_GAMES)
def test_a_new_game_never_leaves_the_player_in_control_without_a_move(
        game):
    """A non-terminal state with no legal move makes a GDL game
    MALFORMED, not merely degenerate (`reference.py`). Breakthrough is
    enumerated exhaustively; the larger two are enumerated to a bound."""
    from lgref.identify.testgames.reference import enumerate_game

    limit = 200000 if game == 'breakthrough' else 1500
    result = enumerate_game(game, limit=limit)
    assert result.stuck == 0
    assert result.terminals > 0
    assert len(result.wins) == 2, 'both sides must be able to win'


def test_selectors_narrow_by_action_and_subject():
    nodes = {n.node_id: n for n in _nodes('skirmish')}
    guard = [n for n in nodes.values() if matches('legal/move.guard', n)]
    lancer = [n for n in nodes.values() if matches('legal/move.lancer', n)]
    noop = [n for n in nodes.values() if matches('legal/noop', n)]
    assert len(guard) == 2 and len(lancer) == 2 and len(noop) == 2
    assert not set(map(id, guard)) & set(map(id, lancer))

    plain = [n for n in _nodes('breakthrough') if matches('cell/', n)]
    # the frame statement and the twelve initial cells
    assert len(plain) == 13
    assert all('advance' not in repr(n.raw) and 'capture' not in repr(n.raw)
               for n in plain)


def test_every_label_entry_selects_something():
    """An entry that matches nothing is a typo that silently shrinks the
    reference partition."""
    for game, spec in GAMES.items():
        nodes = _nodes(game)
        for entries in spec.values():
            for entry in entries:
                assert any(matches(entry, n) for n in nodes), (game, entry)
