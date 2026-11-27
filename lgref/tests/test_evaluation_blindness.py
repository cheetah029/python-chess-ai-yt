"""The evaluation must see every part of every game's state (#397).

WHY THIS EXISTS. Three times a part of Royal Chess the evaluation could
not see cost games before anyone noticed: the boulder, the tiny endgame
and the repetition rule. Measured on 2026-11-27, the shipped
hand-written evaluation was blind to 8 of the 12 parts of the state the
rules consult. A blind spot is invisible in play -- the player simply
treats two different positions as the same -- so it has to be caught by
a test, and the test has to cover games nobody has written yet.

WHAT "SEES" MEANS, precisely. A part of the state is SEEN when changing
it changes the evaluation's features. The parts are the game
description's own fluents, so the list is the GDL's, not anyone's
memory of the game:

1. COVERAGE. Every fluent relation the description declares (the head
   of a `next` rule, or an `init` fact) must turn up in states reached
   by seeded random play. A relation never reached cannot be checked,
   so it must be listed in `NOT_REACHED` with the reason.
2. SENSITIVITY. For every relation reached, removing one of its fluents
   from a state, or changing one of its non-role arguments to another
   value the relation takes, must change the features on at least one
   sampled state.

A relation that fails either check is a blind spot, and the test fails
naming it. `KNOWN_BLIND` holds the blind spots that are known and not
yet fixed, each with its reason. The test also fails if a listed one is
no longer blind, so the list can only shrink.

The games: every development and test game of Paper A's catalog, and
Royal Chess, whose positions are read through the engine-to-GDL
converter (`lgref.experiments.gdl_engine`).
"""

import collections
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'src')]

from lgref.bench import catalog  # noqa: E402
from lgref.experiments import gdl  # noqa: E402

#: (game, relation) -> why it is never reached by random play.
NOT_REACHED = {}

#: (game, relation) -> why the evaluation cannot see it yet.
KNOWN_BLIND = {}


def _relation(term):
    return term[0] if isinstance(term, tuple) else term


def declared(kb):
    """Fluent relations the description declares: `next` heads and
    `init` facts."""
    found = set()
    for head, _body in kb.rules_for('next'):
        found.add(_relation(head[1]))
    for fact in kb.facts_for('init'):
        found.add(_relation(fact[1]))
    return found


def _changes(state, relation, domain, roles):
    """Every single-fluent change of `relation` in `state`: remove one
    fluent, or change one non-role argument to another value seen at
    that position."""
    for term in sorted((t for t in state if _relation(t) == relation),
                       key=repr)[:3]:
        yield frozenset(state) - {term}
        if not isinstance(term, tuple):
            continue
        for index in range(1, len(term)):
            if str(term[index]) in roles:
                continue
            for other in sorted(domain[(relation, index)] - {term[index]},
                                key=repr)[:2]:
                changed = term[:index] + (other,) + term[index + 1:]
                if changed not in state:
                    yield frozenset(state) - {term} | {changed}


def audit(states, declared_relations, features, roles, instances=8):
    """`{relation: verdict}` with verdict 'seen', 'blind' or 'not
    reached'.

    `states` are `(state, context)` pairs and `features(state, context)`
    reads a state in the context it was reached in (its mover). A
    changed state keeps its original context: otherwise a change could
    look "seen" only because the mover changed with it -- which is
    exactly the error the first version of this test made, and the
    mutation check caught."""
    domain = collections.defaultdict(set)
    reached = set()
    for state, _context in states:
        for term in state:
            reached.add(_relation(term))
            if isinstance(term, tuple):
                for index, value in enumerate(term[1:], 1):
                    domain[(_relation(term), index)].add(value)
    verdicts = {}
    for relation in sorted(declared_relations | reached):
        if relation not in reached:
            verdicts[relation] = 'not reached'
            continue
        seen = False
        for state, context in states:
            if seen:
                break
            if not any(_relation(t) == relation for t in state):
                continue
            base = features(state, context)
            for changed in _changes(state, relation, domain, roles):
                if features(changed, context) != base:
                    seen = True
                    break
        verdicts[relation] = 'seen' if seen else 'blind'
    # EVERY FLUENT, NOT ONLY EVERY RELATION. A relation counts as seen
    # above when one change to it registers, which an extractor that
    # ignores SOME of its fluents -- one column of cells, one value --
    # would still pass (a mutant did). So on the first states, removing
    # any single fluent must change the features too.
    for state, context in states[:instances]:
        base = features(state, context)
        for term in sorted(state, key=repr):
            if features(frozenset(state) - {term}, context) == base:
                verdicts[_relation(term)] = 'blind'
    return verdicts


def _gdl_states(path, games=4, plies=30, seed=0):
    game0 = gdl.load(path, seed=seed)
    states = [(frozenset(game0.state), game0.current_player)]
    rng = random.Random(seed)
    for _g in range(games):
        game = gdl.load(path, seed=rng.randrange(10 ** 6))
        for _ply in range(plies):
            if game.is_game_over():
                break
            turns = game.get_all_legal_turns()
            if not turns:
                break
            game.execute_turn(rng.choice(turns))
            states.append((frozenset(game.state), game.current_player))
    return game0, states


GDL_GAMES = sorted(catalog.in_split('dev') + catalog.in_split('test'))


def _verdicts(name):
    game, states = _gdl_states(catalog.game_path(name))
    kb = game.ggp._rules_kb
    roles = set(game.roles)

    class At(object):
        def __init__(self, state, mover):
            self.state = state
            self.roles = game.roles
            self.current_player = mover
            self.ggp = game.ggp

    def features(state, mover):
        return gdl.features(At(state, mover), roles=game.roles)

    return audit(states[:40], declared(kb), features, roles)


def _check(name, verdicts):
    blind = set((name, r) for r, v in verdicts.items() if v == 'blind')
    unreached = set((name, r) for r, v in verdicts.items()
                    if v == 'not reached')
    known = set(k for k in KNOWN_BLIND if k[0] == name)
    listed = set(k for k in NOT_REACHED if k[0] == name)
    assert blind <= known, 'BLIND, and not listed: {0}'.format(
        sorted(blind - known))
    assert known <= blind, (
        'listed as blind but now SEEN, so remove from KNOWN_BLIND: '
        '{0}'.format(sorted(known - blind)))
    assert unreached <= listed, (
        'declared but never reached by random play, so it was not '
        'checked: {0}'.format(sorted(unreached - listed)))


@pytest.mark.parametrize('name', GDL_GAMES)
def test_the_gdl_features_see_every_fluent_of_the_game(name):
    _check(name, _verdicts(name))


def _royal_states(count=14, seed=5):
    """Engine positions along seeded random games -- EVERY position, not
    only the last, so rare fluents (a freeze, an invulnerable knight) are
    reached -- plus tiny-endgame positions with a history."""
    from experiments.variants import make_engine
    from lgref.experiments.fastcopy import clone
    from lgref.experiments.positions import apply_layout, sample_layout
    from lgref.experiments.random_play import build

    engines, rng = [], random.Random(seed)
    for _game in range(count):
        engine = make_engine('full', max_turns=10 ** 9)
        mover = build('random', random.Random(rng.randrange(10 ** 6)), 0)
        for _ply in range(rng.randint(20, 150)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(mover.choose_turn(turns, engine))
            if not engine.is_game_over():
                engines.append(clone(engine))
    found = 0
    while found < 3:
        engine = make_engine('full', max_turns=10 ** 9)
        apply_layout(engine, sample_layout(rng, min_extra=1, max_extra=2,
                                           endgame=True))
        if not engine.board.tiny_endgame_active or engine.is_game_over():
            continue
        mover = build('random', random.Random(found), 0)
        for _ply in range(12):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(mover.choose_turn(turns, engine))
            if (not engine.is_game_over()
                    and engine.board.tiny_endgame_active):
                engines.append(clone(engine))
        found += 1
    return engines


#: Royal Chess fluents that are not a property of a position.
ROYAL_NOT_STATE = {
    'next_state_hash': 'how the description hands a successor state '
                       'to the repetition count rule; never a fluent '
                       'of a reached position',
}


def test_royal_chess_gdl_features_see_every_fluent():
    from ggp.game import GGPGame

    from lgref.experiments import gdl_engine

    path = os.path.join(ROOT, 'docs', 'gdl', 'integrated.gdl')
    kb = GGPGame.from_file(path)._rules_kb
    engines = _royal_states()
    states = [(gdl_engine.engine_facts(e), e.current_player)
              for e in engines]

    constants = gdl_engine.description_constants()

    def features(state, mover):
        # Exactly what `gdl_engine.features` computes for an engine
        # position, so the extractor audited is the one that is played.
        return gdl_engine.named_by_the_rules(
            gdl.features(gdl_engine.StateView(state, mover),
                         roles=gdl_engine.ROLES, relaxed=False),
            constants)

    wanted = declared(kb) - set(ROYAL_NOT_STATE)
    verdicts = audit(states, wanted, features, set(gdl_engine.ROLES))
    _check('royalchess', verdicts)
    assert set(r for r, v in verdicts.items() if v == 'seen') >= wanted


def test_the_audit_catches_a_blind_extractor():
    """BITE: an extractor that ignores one relation is reported blind,
    and one that never sees a relation's arguments is too."""
    states = [(frozenset({('cell', '1', 'x'), ('control', 'a')}), 'a'),
              (frozenset({('cell', '2', 'o'), ('control', 'b')}), 'b')]

    def ignores_control(state, _mover):
        return sorted(t for t in state if t[0] != 'control')

    verdicts = audit(states, {'cell', 'control'}, ignores_control,
                     {'a', 'b'})
    assert verdicts == {'cell': 'seen', 'control': 'blind'}

    def counts_only(state, _mover):
        return collections.Counter(t[0] for t in state)

    verdicts = audit(states, {'cell', 'control', 'score'}, counts_only,
                     {'a', 'b'})
    assert verdicts['cell'] == 'seen'
    assert verdicts['score'] == 'not reached'


#: The shipped hand-written Royal Chess evaluation, audited on the
#: engine's own state. It is RECORDED, not endorsed: these are exactly
#: the blind spots #397 replaces it to remove. If one starts being seen,
#: the test says so and the entry comes out.
HAND_WRITTEN_BLIND = {
    'boulder cooldown', 'boulder no-return memory',
    'manipulation freeze', 'invulnerable', 'moved last turn',
    'reactive armed', 'tiny endgame distance counts', 'repetition counts',
}


def test_the_hand_written_evaluation_blind_spots_are_recorded():
    import json

    from lgref.experiments.discover import differentials
    from lgref.experiments.fastcopy import clone
    from lgref.experiments.features import royal_chess_extractor
    from piece import Bishop, Boulder, Knight

    with open(os.path.join(ROOT, 'lgref', 'weights',
                           'td_royal_chess.json')) as handle:
        extractor = royal_chess_extractor(json.load(handle))

    def feats(engine):
        return differentials(extractor(engine), engine.current_player)

    def pieces(engine, wanted):
        return [engine.board.squares[r][c].piece for r in range(8)
                for c in range(8)
                if engine.board.squares[r][c].piece is not None
                and wanted(engine.board.squares[r][c].piece)]

    def flip(attr, wanted, value=lambda old: not old):
        def change(engine):
            found = pieces(engine, wanted)
            if not found:
                return False
            setattr(found[0], attr, value(getattr(found[0], attr, False)))
        return change

    def counts(engine):
        engine.board.distance_counts[5] = 3

    def history(engine):
        board = engine.board
        board.state_history[board.get_state_hash(engine.current_player)] = 2

    parts = {
        'boulder cooldown': flip('cooldown',
                                 lambda p: isinstance(p, Boulder),
                                 lambda old: 0 if old else 2),
        'boulder no-return memory': flip(
            'last_square', lambda p: isinstance(p, Boulder),
            lambda old: None if old else (3, 3)),
        'manipulation freeze': flip('moved_by_queen',
                                    lambda p: not isinstance(p, Boulder)),
        'invulnerable': flip('invulnerable',
                             lambda p: isinstance(p, Knight)),
        'moved last turn': flip('moved_last_turn',
                                lambda p: not isinstance(p, Boulder)),
        'reactive armed': flip('reactive_armed',
                               lambda p: isinstance(p, Bishop)),
        'tiny endgame distance counts': counts,
        'repetition counts': history,
    }
    blind = set()
    for name, change in parts.items():
        seen = False
        for engine in _royal_states(count=3, seed=9)[::7]:
            copy = clone(engine)
            before = feats(copy)
            if change(copy) is False:
                continue
            if feats(copy) != before:
                seen = True
                break
        if not seen:
            blind.add(name)
    assert blind == HAND_WRITTEN_BLIND, (blind ^ HAND_WRITTEN_BLIND)


def test_a_state_identity_is_never_read_as_a_number():
    """REGRESSION: the identities in `state_repetition_count` were bare
    hex digests, and `3e851...` is a number to `float` -- it parsed to
    infinity and the first training run's weights all became NaN within
    one game. An identity must be a symbol."""
    import math

    from lgref.experiments import gdl_engine

    names = [gdl_engine._identity(index) for index in range(20000)]
    for name in names:
        try:
            float(name)
        except ValueError:
            continue
        raise AssertionError('identity {0} reads as a number'.format(name))
    engine = _royal_states(count=1, seed=2)[-1]
    for value in gdl_engine.features(engine).values():
        assert not math.isnan(value) and not math.isinf(value)
