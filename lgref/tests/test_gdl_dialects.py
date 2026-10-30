"""GDL-III is read, and GDL-I and GDL-II are read exactly as before.

Issue #280. Two claims, and the second is the one that matters more.

1. GDL-III's `knows` means what Thielscher's semantics say it means. The
   test game is the paper's own worked example, Muddy Children with two
   children (IJCAI 2017, Example 1), and the knowledge states are the
   ones printed in the paper.

2. NOTHING ELSE CHANGED. The proof was declared before the code was
   written. Everything the reader produces for the GDL-I and GDL-II
   games was fingerprinted on the UNCHANGED code: parsed forms, clause
   nodes, clause-graph edges, the cluster partition and its language
   verdicts, and seeded playouts recording legal moves, terminal, goals,
   the mover and `gdl.features`. Those fingerprints are pinned below and
   must still match. A fingerprint is a hash of the full output, so any
   difference at all fails it, not just a difference somebody thought
   to check.

   Regenerate a fingerprint only for a change that is MEANT to alter
   that game's reading, and say so in the commit.
"""

import hashlib
import os
import pickle
import random
import sys

import pytest

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp import dialect  # noqa: E402
from ggp.epistemic import CircularKnowledge  # noqa: E402
from ggp.game import GGPGame  # noqa: E402
from ggp.resolver import Resolver  # noqa: E402

from lgref.experiments.gdl import GdlGame, features  # noqa: E402
from lgref.identify.clauses import load  # noqa: E402
from lgref.identify.cluster import calibrate_resolution, cluster  # noqa
from lgref.identify.graph import ClauseGraph  # noqa: E402
from lgref.identify.language import (  # noqa: E402
    RULE, UNDETERMINED, classify_all, undefined_predicates)

GAMES = os.path.join(HERE, '..', 'identify', 'testgames')
PATHS = {
    'royal': os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl'),
    'nim': os.path.join(GAMES, 'nim.gdl'),
    'corridor': os.path.join(GAMES, 'corridor.gdl'),
    'tictactoe': os.path.join(GAMES, 'tictactoe.gdl'),
    'montyhall': os.path.join(GAMES, 'montyhall.gdl'),
    'muddychildren': os.path.join(GAMES, 'muddychildren.gdl'),
}

#: Captured on commit 0a68ca0, BEFORE any #280 code existed, and checked
#: stable across PYTHONHASHSEED values.
BEFORE = {
    'royal': {'forms': '6137aeac2e50a21d', 'nodes': '2ec80f7eafb8dd06',
              'edges': 'b5e81d8fc04f5c77', 'trace': 'e845a3e0db918176',
              'trace_len': 6},
    'nim': {'forms': '5cd578b991194c67', 'nodes': '27c15717df191d83',
            'edges': '6f68f4578b8b08ee', 'rules': '6687b018471db0a2',
            'trace': 'bfb4c4dd00023f87', 'trace_len': 27},
    'corridor': {'forms': '55d1795a30a41a9e', 'nodes': '268a41569e03f4ba',
                 'edges': '192debb0f42a975b', 'rules': '0af6155c973e60f1',
                 'trace': '17284403f102be02', 'trace_len': 76},
    'tictactoe': {'forms': 'c83dc2c7afa38d0d', 'nodes': '7d3e5dbc840e5269',
                  'edges': '69861cf74b73d8f5', 'rules': 'e44fa31c601bea0a',
                  'trace': '6912760d17232cb4', 'trace_len': 55},
    'montyhall': {'forms': '931f8c596c26ea12', 'nodes': 'b7f2155a546f789c',
                  'edges': 'fb60b1037f902417', 'rules': '3c3ba0cf8aba0c5b',
                  'trace': 'c92052342be22b66', 'trace_len': 24},
}


def _hash(obj):
    return hashlib.sha256(repr(obj).encode()).hexdigest()[:16]


def _node_signature(n):
    """Every attribute that existed before #280, in a stable order."""
    return (n.node_id, n.kind, n.head_kind, n.arity,
            sorted(n.body_predicates), sorted(n.fluents_read),
            sorted(n.fluents_written), sorted(n.actions_read),
            n.action_type, sorted(n.piece_types), sorted(n.negated_goals),
            n.terminal_dependency, n.generic_effect,
            sorted(n.action_subjects))


def fingerprint(name):
    path = PATHS[name]
    record = {}
    with open(path) as handle:
        record['forms'] = _hash(GGPGame._parse_any_dialect(handle.read()))
    nodes = load(path)
    record['nodes'] = _hash([_node_signature(n) for n in nodes])
    graph = ClauseGraph(nodes)
    record['edges'] = _hash({k: sorted(v) for k, v in graph.edges.items()})
    if name != 'royal':
        resolution = calibrate_resolution(graph, seed=0)
        rules, _dropped = cluster(graph, resolution=resolution, seed=0)
        kinds = classify_all(nodes, rules)
        record['rules'] = _hash(sorted(
            (sorted(r.clause_ids), sorted(r.shared_clause_ids),
             kinds[r.rule_id]) for r in rules))
    trace = []
    for seed in range(2 if name == 'royal' else 6):
        rng = random.Random(seed)
        ggp = GGPGame.from_file(path)
        game = GdlGame(ggp)
        for _ply in range(3 if name == 'royal' else 30):
            legal = {r: sorted(ggp.legal_moves(r), key=repr)
                     for r in ggp.roles}
            terminal = ggp.is_terminal()
            goals = {r: ggp.goal(r) for r in ggp.roles}
            trace.append((sorted(ggp.state, key=repr), legal, terminal,
                          goals, game.current_player,
                          sorted(features(game).items(), key=repr)))
            if terminal or any(not v for v in legal.values()):
                break
            ggp.step({r: rng.choice(v) for r, v in legal.items()})
    record['trace'] = _hash(trace)
    record['trace_len'] = len(trace)
    return record


# ---- 2. nothing else changed --------------------------------------------

@pytest.mark.parametrize('name', sorted(BEFORE))
def test_gdl_i_and_ii_are_read_exactly_as_before(name):
    assert fingerprint(name) == BEFORE[name]


@pytest.mark.parametrize('name', ['royal', 'nim', 'tictactoe', 'montyhall'])
def test_gdl_i_and_ii_never_touch_the_epistemic_path(name):
    """The guarantee is structural, not only measured: no history is
    recorded and the plain resolver is used, so search speed on these
    games cannot have changed either."""
    game = GGPGame.from_file(PATHS[name])
    assert game._knowledge is None
    assert type(game._resolver(game._state_kb())) is Resolver
    moves = {r: game.legal_moves(r)[0] for r in game.roles}
    game.step(moves)
    assert game.history == ()


# ---- dialect detection --------------------------------------------------

@pytest.mark.parametrize('name, expected', [
    ('royal', dialect.GDL_I), ('nim', dialect.GDL_I),
    ('corridor', dialect.GDL_I), ('tictactoe', dialect.GDL_I),
    ('montyhall', dialect.GDL_II), ('muddychildren', dialect.GDL_III)])
def test_the_dialect_is_read_from_the_description(name, expected):
    assert GGPGame.from_file(PATHS[name]).dialect == expected


def test_random_alone_or_sees_alone_makes_gdl_ii():
    assert dialect.detect([('role', 'random')]) == dialect.GDL_II
    assert dialect.detect([('<=', ('sees', '?r', 'x'), ('role', '?r'))]) \
        == dialect.GDL_II
    assert dialect.detect([('role', 'white')]) == dialect.GDL_I
    negated = ('<=', 'terminal', ('not', ('knows', 'p')))
    assert dialect.detect([negated]) == dialect.GDL_III


# ---- GDL-II: percepts ---------------------------------------------------

def test_monty_hall_tells_the_candidate_only_the_opened_door():
    game = GGPGame.from_file(PATHS['montyhall'])
    first = {'random': ('hide_car', '1'), 'candidate': ('choose', '2')}
    assert game.percepts('candidate', first) == frozenset()
    game.step(first)
    opened = {'random': ('open_door', '3'), 'candidate': 'noop'}
    assert game.legal_moves('random') == [('open_door', '3')]
    assert game.percepts('candidate', opened) == {('opened', '3')}
    assert game.percepts('random', opened) == frozenset()


def test_monty_hall_switching_wins_two_thirds():
    """The known answer, computed by exhausting the game: a check on the
    GDL-II file, not on any player."""
    wins = {'stay': 0, 'switch': 0}
    total = 0
    for car in '123':
        for choice in '123':
            for final in ('noop', 'switch'):
                game = GGPGame.from_file(PATHS['montyhall'])
                game.step({'random': ('hide_car', car),
                           'candidate': ('choose', choice)})
                door = game.legal_moves('random')[0]
                game.step({'random': door, 'candidate': 'noop'})
                game.step({'random': 'noop', 'candidate': final})
                assert game.is_terminal()
                key = 'switch' if final == 'switch' else 'stay'
                wins[key] += game.goal('candidate') == 100
            total += 1
    assert (wins['stay'], wins['switch'], total) == (3, 6, 9)


# ---- 1. GDL-III: the paper's worked example -----------------------------

CHILDREN = ('ann', 'bob')


def _known(game):
    return {(c, d) for c in CHILDREN for d in CHILDREN
            if game.knows(c, ('isMuddy', d))}


def _announce(game):
    moves = {c: game.legal_moves(c) for c in CHILDREN}
    assert all(len(m) == 1 for m in moves.values()), moves
    said = {c: m[0][1] for c, m in moves.items()}
    game.step(dict({c: m[0] for c, m in moves.items()}, random='noop'))
    return said


def _muddy(a, b):
    game = GGPGame.from_file(PATHS['muddychildren'])
    game.step({'random': ('muddy', a, b), 'ann': 'noop', 'bob': 'noop'})
    return game


@pytest.mark.parametrize('a, b, after_one, after_two', [
    # Thielscher 2017, Example 1: K_01.NN, K_11.NN, K_10.NN, K_11.NN.NN
    ('0', '1', {('ann', 'bob'), ('bob', 'bob')},
     {('ann', 'bob'), ('bob', 'bob')}),
    ('1', '1', {('ann', 'bob'), ('bob', 'ann')},
     {('ann', 'ann'), ('ann', 'bob'), ('bob', 'ann'), ('bob', 'bob')}),
    ('1', '0', {('ann', 'ann'), ('bob', 'ann')},
     {('ann', 'ann'), ('bob', 'ann')}),
])
def test_muddy_children_knowledge_matches_the_paper(a, b, after_one,
                                                    after_two):
    game = _muddy(a, b)
    # "Nothing is observed as a direct consequence of this choice."
    assert _known(game) == set()
    assert _announce(game) == {'ann': 'no', 'bob': 'no'}
    assert _known(game) == after_one
    _announce(game)
    assert _known(game) == after_two
    assert game.is_terminal()


def test_knowledge_decides_legality():
    """`legal(C, say(yes)) :- knows(C, isMuddy(C))` -- before #280 the
    reader treated `knows` as an undefined predicate, so nobody could
    ever say yes."""
    game = _muddy('0', '1')
    _announce(game)
    assert game.legal_moves('bob') == [('say', 'yes')]
    assert game.legal_moves('ann') == [('say', 'no')]


def test_the_one_muddy_child_wins_and_the_other_learns_by_elimination():
    game = _muddy('0', '1')
    _announce(game)
    said = _announce(game)
    assert said == {'ann': 'no', 'bob': 'yes'}
    # ann is clean and, hearing bob say yes, knows it.
    assert game.knows('ann', ('isClean', 'ann'))
    assert {r: game.goal(r) for r in game.roles} == {
        'ann': 100, 'bob': 100, 'random': 0}


def test_nested_knowledge_through_an_auxiliary_predicate():
    """`knows(ann, knowsOwn(bob))`: ann knows that bob knows his state."""
    game = _muddy('1', '1')
    _announce(game)
    assert not game.knows('ann', ('knowsOwn', 'bob'))
    _announce(game)
    assert game.knows('ann', ('knowsOwn', 'bob'))


def test_common_knowledge_is_the_closure_over_every_role():
    game = GGPGame.from_file(PATHS['muddychildren'])
    assert not game.knows(None, 'someMuddy')
    game = _muddy('0', '1')
    # Every random move muddies someone, and the rules are common
    # knowledge, so this is known to all before anything is seen.
    assert game.knows(None, 'someMuddy')
    _announce(game)
    # Both children know bob is muddy, yet it is NOT common knowledge:
    # 01.NN ~ann 11.NN ~bob 10.NN, and bob is clean in 10.
    assert {('ann', 'bob'), ('bob', 'bob')} <= _known(game)
    assert not game.knows(None, ('isMuddy', 'bob'))


def test_knows_with_variables_finds_every_known_instance():
    game = _muddy('1', '0')
    _announce(game)
    resolver = game._resolver(game._state_kb())
    found = sorted(b['?c'] for b in resolver.query(
        ('knows', '?c', ('isMuddy', 'ann'))))
    assert found == ['ann', 'bob', 'random']


def test_circular_knowledge_is_refused_not_looped():
    text = '\n'.join([
        'role(a)',
        'init(s)',
        'legal(a,go) :- true(s)',
        'p :- ~knows(a,p)',
        'terminal :- p',
        'goal(a,0)',
    ])
    game = GGPGame(text)
    with pytest.raises(CircularKnowledge):
        game.is_terminal()


def test_a_gdl_iii_game_survives_both_ways_of_copying():
    """`GdlGame.copy` deep-copies and the search's fast copy pickles;
    both must keep the history, and deepcopy shares the model."""
    import copy

    game = _muddy('1', '1')
    clone = copy.deepcopy(game)
    assert clone._knowledge is game._knowledge
    assert clone.history == game.history
    pickled = pickle.loads(pickle.dumps(game))
    assert pickled.history == game.history
    assert _known(pickled) == _known(game) == set()


# ---- the LGREF clause reader --------------------------------------------

def test_knows_is_a_keyword_not_an_undefined_predicate():
    nodes = load(PATHS['muddychildren'])
    assert 'knows' not in undefined_predicates(nodes)
    assert all('knows' not in n.body_predicates for n in nodes)
    yes = [n for n in nodes if n.head_kind == 'legal'
           and n.raw[1][2] == ('say', 'yes')]
    assert yes and all('isMuddy' in n.body_predicates for n in yes)


def test_knowledge_is_state_dependent_for_rule_identification():
    nodes = load(PATHS['muddychildren'])
    graph = ClauseGraph(nodes)
    rules, _dropped = cluster(
        graph, resolution=calibrate_resolution(graph, seed=0), seed=0)
    kinds = classify_all(nodes, rules)
    by_clause = {c: kinds[r.rule_id] for r in rules for c in r.clause_ids}
    knowing = [n.node_id for n in nodes if n.knowledge_read]
    assert knowing
    for clause in knowing:
        if clause in by_clause:
            assert by_clause[clause] == RULE
    assert UNDETERMINED not in set(kinds.values())
