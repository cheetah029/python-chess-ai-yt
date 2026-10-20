"""The acceptance test: hand it a GDL it has never seen.

A reviewer put it plainly -- the way to know the framework is general
is that the player is COMPETENT on a game given only its rules. Every
other check is a proxy, including the twenty-eight in the generality
audit, which say what a module may not contain rather than what the
agent can do.

So these tests train from zero on GDL files that no extractor was
written for, with every feature named from those files' own relations,
and measure the result against a uniform mover.

WHAT THIS ALREADY FOUND, which is the argument for having it:

  - `differentials` excludes neutral owners, correctly, because a piece
    belonging to nobody scored against the mover is a constant dressed
    as a feature. But nim's ENTIRE state is `pile(5)`, which belongs to
    nobody -- so the learner got one usable feature and the agent lost
    to random 28-92. Shared quantities now belong to the side to move,
    which keeps the evaluation antisymmetric and makes the meaning
    right.
  - at a TERMINAL state every role is left holding an idle move, so
    "who is to move" fell through to `roles[0]` -- right half the time,
    and `search._leaf` scores a finished position as
    `winner == current_player`. Half of all terminal positions were
    read with the sign inverted. On nim, where every line ends within
    five plies, that is most of the tree: 35% against a uniform mover
    before the fix, 91.7% after, with the same weights.

Neither was reachable from the case study or from m,n,k, because both
of those hand the agent a hand-written extractor and a real
`current_player`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

from lgref.experiments.gdl import GdlGame, features, load

GAMES = os.path.join(os.path.dirname(__file__), '..', 'identify',
                     'testgames')


def _path(name):
    return os.path.join(GAMES, name + '.gdl')


@pytest.mark.parametrize('name', ['nim', 'corridor', 'tictactoe'])
def test_a_gdl_file_is_playable_through_the_ordinary_protocol(name):
    """One adapter per DIALECT, not per game. Nothing below knows what
    any of these games is."""
    game = load(_path(name), max_turns=60)
    assert len(game.roles) >= 2
    assert game.current_player in game.roles
    turns = game.get_all_legal_turns()
    assert turns, 'no legal turn in the initial state'
    plies = 0
    while not game.is_game_over() and plies < 60:
        here = game.get_all_legal_turns()
        if not here:
            break
        game.execute_turn(here[0])
        plies += 1
    assert plies > 0
    assert game.winner is None or game.winner in game.roles


@pytest.mark.parametrize('name', ['nim', 'corridor'])
def test_every_feature_name_comes_from_the_games_own_relations(name):
    """NO NAME IS SUPPLIED. `pile`, `control`, `at`, `fresh` are the
    GDL's own symbols; the only things this module adds are the `@index`
    and `is`/`=` markers that say which argument a number or a constant
    came from."""
    with open(_path(name)) as handle:
        text = handle.read()
    game = load(_path(name), max_turns=60)
    for _owner, feature in features(game):
        relation = feature.split('@')[0]
        assert relation in text, (
            '{0!r} is not a relation of {1}.gdl, so it was invented '
            'somewhere'.format(relation, name))


def test_a_shared_quantity_is_attributed_to_the_side_to_move():
    """Nim's whole state belongs to nobody, and `differentials` drops
    neutral owners -- so without this the learner sees one feature and
    the agent loses to a uniform mover."""
    game = load(_path('nim'), max_turns=60)
    owners = dict(((owner, name), value)
                  for (owner, name), value in features(game).items())
    pile = [(owner, name) for (owner, name) in owners
            if name.startswith('pile')]
    assert pile, owners
    for owner, _name in pile:
        assert owner in game.roles, (
            'the pile is owned by {0!r}, which differentials will '
            'drop'.format(owner))


def test_reading_a_state_from_the_other_side_negates_it():
    """TD's whole value identity is `1 - sigma(w.x) == sigma(w.-x)`, so
    the features have to be antisymmetric in the perspective. A shared
    quantity attributed to a FIXED role would break that silently."""
    from lgref.experiments.discover import differentials

    game = load(_path('corridor'), max_turns=60)
    raw = features(game)
    first, second = game.roles[0], game.roles[1]
    mine = differentials(raw, first)
    theirs = differentials(raw, second)
    assert mine, 'no features survived differencing'
    for name, value in mine.items():
        assert theirs.get(name, 0) == -value, (name, value,
                                               theirs.get(name))


def test_a_number_in_a_fluent_is_read_both_ways():
    """A magnitude orders positions; an indicator does not. Nim is
    decided by the pile's PARITY, which no linear weight on its size can
    represent, so both readings are offered and the learner chooses."""
    game = load(_path('nim'), max_turns=60)
    names = set(name for _owner, name in features(game))
    assert 'pile@0' in names, names          # the magnitude
    assert any(name.startswith('pile@0is') for name in names), names


def test_the_player_to_move_is_still_known_at_a_terminal_state():
    """THE SIGN BUG. At a terminal state every role holds nothing but an
    idle move, so the first rule falls through -- and `search._leaf`
    reads a finished position as `winner == current_player`.

    The turn marker is found by SHAPE: a relation true of exactly one
    role. Nothing depends on it being spelled `control`.
    """
    game = load(_path('nim'), max_turns=60)
    seen = []
    while not game.is_game_over():
        turns = game.get_all_legal_turns()
        if not turns:
            break
        seen.append(game.current_player)
        game.execute_turn(turns[0])
    assert game.is_game_over()
    assert game.current_player in game.roles
    # The mover alternates, so the role to move at the end is determined
    # by the number of plies -- not by whichever role happens to be
    # first in the list.
    expected = game.roles[0] if len(seen) % 2 == 0 else game.roles[1]
    ordered = [seen[0], [r for r in game.roles if r != seen[0]][0]]
    expected = ordered[len(seen) % 2]
    assert game.current_player == expected, (
        'at the terminal state the mover reads as {0}, but {1} plies '
        'were played starting with {2}'.format(game.current_player,
                                               len(seen), seen[0]))


def test_the_turn_marker_is_found_by_shape_not_by_its_name():
    class _Fake(object):
        roles = ['alice', 'bob']
        state = {('whose_move', 'bob'), ('score', 'alice', '3')}

    game = GdlGame.__new__(GdlGame)
    game.roles = _Fake.roles
    game.ggp = _Fake()
    assert game._turn_marker() == 'bob'


@pytest.mark.slow
@pytest.mark.parametrize('name,floor', [('corridor', 0.65), ('nim', 0.70)])
def test_the_agent_is_competent_on_a_game_it_was_never_written_for(name,
                                                                   floor):
    """THE ACCEPTANCE TEST ITSELF.

    Train from zero on the GDL, then play the result against a uniform
    mover. The floors are set well under what was measured -- corridor
    81%, nim 92% -- because the point is to catch a COLLAPSE, not to
    pin a number that will drift with the seed.
    """
    import random

    from lgref.experiments.bootstrap import normalise, run, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.search import Searcher

    cap = 40

    def make(_variant='full', max_turns=None):
        return load(_path(name), max_turns=max_turns or cap)

    scales = {}
    history = run(make, features, rounds=4, games_per_round=30,
                  alpha=0.08, epsilon=0.3, seed=11, max_turns=cap,
                  scales=scales)
    weights = history[-1].weights
    assert len(weights) > 1, (
        'only {0} feature(s) were learned, so nothing can be '
        'evaluated'.format(len(weights)))

    def evaluate(game, perspective):
        return value(weights, normalise(
            differentials(features(game), perspective), dict(scales),
            update=False))

    wins = losses = 0
    for index in range(40):
        game = make()
        rng = random.Random(900 + index)
        mine = game.roles[index % len(game.roles)]
        plies = 0
        while not game.is_game_over() and plies < cap:
            turns = game.get_all_legal_turns()
            if not turns:
                break
            if game.current_player == mine:
                searcher = Searcher(evaluate, max_depth=4, budget=5.0,
                                    quiescence=0, use_tt=False)
                chosen = searcher.choose_turn(turns, game)
            else:
                chosen = rng.choice(turns)
            game.execute_turn(chosen)
            plies += 1
        if game.winner == mine:
            wins += 1
        elif game.winner is not None:
            losses += 1
    decided = wins + losses
    assert decided > 10, 'too few decided games to mean anything'
    rate = wins / float(decided)
    assert rate >= floor, (
        'on {0}, a game nothing here was written for, the agent scored '
        '{1:.1%} against a uniform mover'.format(name, rate))
