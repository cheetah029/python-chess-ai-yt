"""GDL-II played fairly: nature is drawn, players see only their view.

Issue #286. Four claims, in the order they depend on each other.

1. KRIEG-TICTACTOE IS THE GAME IT SAYS. Each player is told only whether
   its own mark succeeded or the cell was taken, and it is WELL-FORMED:
   a role's legal moves are the same in every play sequence it cannot
   tell apart from the actual one, checked against `ggp.epistemic`'s own
   indistinguishability relation.

2. THE HOST IS FAIR. Nature is drawn uniformly instead of being handed
   its first legal move. A view is exactly `KnowledgeModel.view`, and a
   GDL-I game never makes a percept query.

3. V6 NEVER READS THE HIDDEN STATE. It is never given the game, the view
   holds nothing that could reach the game, a host state that raises if
   read while V6 chooses is never read, and two different truths that
   look the same to V6 get the same move.

4. V6 IS COMPETENT. Its belief is the true posterior on Monty Hall, and
   it beats V0 on Krieg-TicTacToe in a seat-balanced match.
"""

import collections
import math
import os
import random
import sys

import pytest

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp.epistemic import KnowledgeModel  # noqa: E402
from ggp.game import GGPGame  # noqa: E402

from lgref.experiments import hidden  # noqa: E402
from lgref.experiments.gdl import GdlGame, View, load  # noqa: E402

GAMES = os.path.join(HERE, '..', 'identify', 'testgames')
KRIEG = os.path.join(GAMES, 'kriegtictactoe.gdl')
MONTY = os.path.join(GAMES, 'montyhall.gdl')
NIM = os.path.join(GAMES, 'nim.gdl')


def _rules(path):
    with open(path) as handle:
        return handle.read()


def _v6(rules, role, seed, particles=8, depth=2):
    return hidden.DeterminizedPlayer(rules, role, particles=particles,
                                     depth=depth, seed=seed)


def _v0(_rules_text, role, seed):
    return hidden.UniformPlayer(role, seed=seed)


def _mark(m, n):
    return ('mark', str(m), str(n))


# ---- 1. the game -------------------------------------------------------

def test_krieg_is_gdl_ii_and_not_an_identification_gate():
    from lgref.identify.testgames import ground_truth

    game = GGPGame.from_file(KRIEG)
    assert game.dialect == 'GDL-II'
    assert game.roles == ['oplayer', 'xplayer']
    assert all('krieg' not in str(key).lower()
               for key in ground_truth.GAMES)


def test_a_player_is_told_only_whether_its_own_mark_landed():
    game = load(KRIEG)
    assert game.current_player == 'xplayer'
    game.execute_turn(('xplayer', _mark(2, 2)))
    assert game.view('xplayer').steps == (
        (_mark(2, 2), frozenset({'ok'})),)
    # The opponent is told nothing at all about it.
    assert game.view('oplayer').steps == (('noop', frozenset()),)
    game.execute_turn(('oplayer', _mark(2, 2)))
    assert game.view('oplayer').steps[-1] == (
        _mark(2, 2), frozenset({'taken'}))
    assert game.view('xplayer').steps[-1] == ('noop', frozenset())
    # The failed attempt used the turn, changed no cell, and is never
    # offered again.
    assert ('cell', '2', '2', 'x') in game.state
    assert game.current_player == 'xplayer'
    game.execute_turn(('xplayer', _mark(1, 1)))
    assert _mark(2, 2) not in game.view('oplayer').legal


def test_krieg_is_well_formed_legality_is_a_function_of_the_view():
    """Every role's legal moves agree across the sequences it cannot
    tell apart -- the property that lets V0 be handed its legal moves,
    and V6 read them from its belief, without either learning more."""
    game = GGPGame.from_file(KRIEG)
    model = KnowledgeModel(game, game.state)
    for length in range(1, 5):
        for role in game.roles:
            groups = collections.defaultdict(set)
            for history in model.sequences(length):
                groups[model.view(history, role)].add(
                    tuple(model.legal(history, role)))
            assert groups
            assert all(len(legal) == 1 for legal in groups.values()), (
                role, length)


# ---- 2. the host -------------------------------------------------------

def test_nature_is_drawn_uniformly_not_handed_its_first_move():
    """Before #286 the car was behind door 1 in every game."""
    doors = collections.Counter()
    for seed in range(300):
        game = load(MONTY, seed=seed)
        assert game.current_player == 'candidate'
        game.execute_turn(('candidate', ('choose', '1')))
        car = [f for f in game.state if f[0] == 'car']
        assert len(car) == 1
        doors[car[0][1]] += 1
    assert sorted(doors) == ['1', '2', '3']
    # 300 draws, each door expected 100; 60 is over five deviations out.
    assert all(abs(count - 100) < 40 for count in doors.values()), doors


def test_nature_still_reads_as_the_mover_and_the_host_draws_for_it():
    game = load(MONTY, seed=3)
    game.execute_turn(('candidate', ('choose', '2')))
    # Pinned by the GDL-II fingerprint: unchanged by #286.
    assert game.current_player == 'random'
    role, move = game.nature_turn()
    assert role == 'random' and move in game.ggp.legal_moves('random')
    assert move[0] == 'open_door' and move[1] != '2'


def test_a_view_is_exactly_what_epistemic_indistinguishability_reads():
    game = load(KRIEG)
    rng = random.Random(4)
    history = ()
    while not game.is_game_over():
        mover = game.current_player
        move = rng.choice(game.view(mover).legal)
        joint = dict((role, move if role == mover else 'noop')
                     for role in game.roles)
        history = history + (tuple((r, joint[r]) for r in game.roles),)
        game.execute_turn((mover, move))
    model = KnowledgeModel(GGPGame.from_file(KRIEG),
                           GGPGame.from_file(KRIEG).state)
    for role in game.roles:
        assert game.view(role).steps == model.view(history, role)


def test_a_gdl_i_game_keeps_no_views_and_asks_no_percepts():
    game = load(NIM)

    def refuse(*_args):
        raise AssertionError('a GDL-I game asked for percepts')

    game.ggp.percepts = refuse
    assert game._views is None
    with pytest.raises(ValueError):
        game.view(game.roles[0])
    rng = random.Random(0)
    while not game.is_game_over():
        game.execute_turn(rng.choice(game.get_all_legal_turns()))


def test_nature_draws_are_reproducible_and_survive_copy():
    a, b = load(MONTY, seed=11), load(MONTY, seed=11)
    for game in (a, b):
        game.execute_turn(('candidate', ('choose', '3')))
    assert a.state == b.state
    clone = a.copy()
    assert clone.nature_turn() == a.nature_turn()
    assert clone.view('candidate') == a.view('candidate')


# ---- 3. V6 never reads the hidden state --------------------------------

def _plain(value):
    """True if `value` is built only of strings, ints, tuples and
    frozensets -- nothing with a reference back into a game."""
    if isinstance(value, (str, int)):
        return True
    if isinstance(value, (tuple, frozenset)):
        return all(_plain(item) for item in value)
    return False


class _Sealed(object):
    """A host-side flag: the state may not be read while it is up."""
    up = False


def _seal(game):
    """Make reading `game.ggp.state` raise while `_Sealed.up`."""
    ggp = game.ggp
    held = ggp.__dict__.pop('state')

    class Sealed(type(ggp)):
        @property
        def state(self):
            if _Sealed.up:
                raise AssertionError('the hidden state was read')
            return self.__dict__['_held']

        @state.setter
        def state(self, value):
            self.__dict__['_held'] = value

    ggp.__class__ = Sealed
    ggp.state = held
    return game


class _Watched(object):
    """Hands V6 its view with the host's state sealed, and checks what
    it was handed and what it answered."""

    def __init__(self, player):
        self.player = player
        self.calls = 0

    def choose(self, view):
        assert type(view) is View
        assert _plain(tuple(view)), 'the view holds a live object'
        _Sealed.up = True
        try:
            move = self.player.choose(view)
            derived = (self.player._legal()
                       if hasattr(self.player, '_legal') else view.legal)
        finally:
            _Sealed.up = False
        # V6 reads its legal moves from its belief; in a well-formed
        # game they must be the ones the host would have handed it.
        assert tuple(derived) == view.legal
        assert move in view.legal
        self.calls += 1
        return move


def test_v6_is_never_handed_the_game_and_never_reads_its_state():
    rules = _rules(KRIEG)
    for seed in range(4):
        game = _seal(load(KRIEG))
        watched = {}
        players = {}
        for index, role in enumerate(game.roles):
            if (index + seed) % 2:
                watched[role] = players[role] = _Watched(_v6(rules, role,
                                                             seed))
            else:
                players[role] = _v0(rules, role, seed)
        goals = hidden.play(game, players)
        assert goals is not None
        assert all(w.calls for w in watched.values())


def test_the_seal_is_not_vacuous_a_player_that_peeks_is_caught():
    game = _seal(load(KRIEG))

    class Peeker(object):
        def choose(self, view):
            return sorted(game.ggp.state, key=repr) and view.legal[0]

    with pytest.raises(AssertionError, match='hidden state was read'):
        hidden.play(game, {'xplayer': _Watched(Peeker()),
                           'oplayer': _v0(None, 'oplayer', 0)})
    _Sealed.up = False


def test_v6_holds_no_reference_to_any_host_game():
    rules = _rules(KRIEG)
    player = _v6(rules, 'oplayer', 0)
    game = load(KRIEG)
    game.execute_turn(('xplayer', _mark(1, 1)))
    player.choose(game.view('oplayer'))
    reachable = [value for value in vars(player).values()
                 if isinstance(value, GdlGame) or value is game.ggp]
    assert not reachable


def test_two_truths_that_look_the_same_get_the_same_move():
    """THE BEHAVIOURAL FORM OF THE CLAIM. O's mark is on a different
    cell in the two games, and x's view is identical in both; a player
    that read the state could tell them apart and V6 does not."""
    rules = _rules(KRIEG)
    seen = []
    for o_cell in ((3, 3), (1, 3)):
        game = load(KRIEG)
        game.execute_turn(('xplayer', _mark(2, 2)))
        game.execute_turn(('oplayer', _mark(*o_cell)))
        game.execute_turn(('xplayer', _mark(1, 1)))
        game.execute_turn(('oplayer', _mark(3, 1)))
        player = _v6(rules, 'xplayer', 9)
        view = game.view('xplayer')
        seen.append((view, player.choose(view),
                     sorted(player.last_values.items())))
    assert seen[0][0] == seen[1][0]
    assert seen[0][1:] == seen[1][1:]


def test_the_sample_memo_answers_what_the_resolver_answers():
    """V6's private samples memoise resolver answers by state. That is
    a speed-up only if every answer is the resolver's own: compared
    along seeded random games, twice, so the second pass is served from
    the memo."""
    import copy

    rules = _rules(KRIEG)
    sample = hidden._sample_class()(rules)
    sample._cache = {}
    for _pass in range(2):
        for seed in range(5):
            rng = random.Random(seed)
            plain = GGPGame(rules)
            memo = copy.deepcopy(sample)
            while True:
                assert memo.is_terminal() == plain.is_terminal()
                for role in plain.roles:
                    assert memo.goal(role) == plain.goal(role)
                    # SORTED: the resolver's answer order follows set
                    # iteration and is not stable even for one state, so
                    # every consumer sorts and order is not an answer.
                    assert sorted(memo.legal_moves(role), key=repr) == \
                        sorted(plain.legal_moves(role), key=repr)
                if plain.is_terminal():
                    break
                moves = dict((r, rng.choice(plain.legal_moves(r)))
                             for r in plain.roles)
                for role in plain.roles:
                    assert memo.percepts(role, moves) == \
                        plain.percepts(role, moves)
                plain.step(moves)
                memo.step(moves)
                assert memo.state == plain.state
    assert sample._cache


# ---- 4. V6 is competent ------------------------------------------------

def test_the_belief_is_the_true_posterior_on_monty_hall():
    """Nature's chance is weighted in, so after the host opens a door
    the car is behind the other closed one two times in three. A belief
    uniform over the consistent sequences would say one in two."""
    rules = _rules(MONTY)
    switched = 0
    shares = []
    for seed in range(6):
        game = load(MONTY, seed=seed)
        player = _v6(rules, 'candidate', seed, particles=16, depth=1)
        game.execute_turn(('candidate', player.choose(
            game.view('candidate'))))
        game.execute_turn(game.nature_turn())
        move = player.choose(game.view('candidate'))
        switched += move == 'switch'
        # READ THE BELIEF, not `last_values`: those are searched values,
        # and `GdlGame.winner` scores a lost Monty Hall (0 against
        # nature's 0) as a tie, so switching is valued 2/3 + 1/3 * 1/2.
        elsewhere = mass = 0.0
        for particle in player._particles:
            chosen = [f[1] for f in particle.state if f[0] == 'chosen']
            car = [f[1] for f in particle.state if f[0] == 'car']
            elsewhere += particle.weight * (chosen != car)
            mass += particle.weight
        shares.append(elsewhere / mass)
    assert switched == 6
    # EXACT, not approximately: the belief holds two histories, well
    # under `particles`, so it is enumerated rather than sampled.
    for share in shares:
        assert abs(share - 2.0 / 3.0) < 1e-9, shares


def _wilson_low(score, n, z=1.96):
    centre = score + z * z / (2 * n)
    spread = z * math.sqrt(score * (1 - score) / n + z * z / (4 * n * n))
    return (centre - spread) / (1 + z * z / n)


def test_v6_beats_v0_on_krieg_tictactoe_seat_balanced():
    """The done criterion of #286. Seat-balanced: V6 takes each seat in
    half the games, with the same seeds. A draw scores one half.

    V6 AS SHIPPED, at its defaults. Sixty games so that the claim is
    the 95% interval clearing one half, not a point estimate doing so.
    Measured beforehand at n=40 over several configurations, V6 scored
    65-80%, so this is not tuned to pass."""
    def v6(rules, role, seed):
        return hidden.DeterminizedPlayer(rules, role, seed=seed)

    result = hidden.match(KRIEG, v6, _v0, 60, seed=286)
    assert result['truncated'] == 0
    seats = result['seats']
    assert set(seats) == {'oplayer', 'xplayer'}
    assert all(sum(s.values()) == 30 for s in seats.values())
    assert _wilson_low(result['score'], 60) > 0.5, result
