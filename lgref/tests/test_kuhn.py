"""Kuhn poker: a strategic opponent with hidden information (issue #288).

Four claims, in the order they depend on each other.

1. KUHN POKER IS THE GAME IT SAYS. Each player is told its own card and
   the opponent's betting actions, and the opponent's card only at a
   showdown. It is WELL-FORMED: a role's legal moves are the same in
   every play sequence it cannot tell apart from the actual one.

2. THE DEAL IS FAIR. Nature's single move is one of the six ordered
   deals, drawn uniformly by `GdlGame`.

3. V6 AND V0 PLAY FROM THEIR VIEWS ONLY, checked with the same sealed
   host state as Krieg-TicTacToe.

4. THE REFERENCE IS RIGHT, so what it says about V6 can be believed:
   the equilibrium is worth -1/18 to player1 and is unexploitable. What
   it says about V6 is a LIMIT, recorded, not a gate V6 must pass.
"""

import collections
import os
import sys

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp.epistemic import KnowledgeModel  # noqa: E402
from ggp.game import GGPGame  # noqa: E402

from lgref.experiments import hidden, kuhn  # noqa: E402
from lgref.experiments.gdl import load  # noqa: E402
from lgref.tests.test_hidden import _Watched, _seal  # noqa: E402

KUHN = os.path.join(HERE, '..', 'identify', 'testgames', 'kuhnpoker.gdl')


def _rules():
    with open(KUHN) as handle:
        return handle.read()


def _dealt(c1, c2):
    game = load(KUHN)
    game.execute_turn(('random', ('deal', c1, c2)))
    return game


def _chips(game, role):
    return (game.ggp.goal(role) - 50) // 25


# ---- 1. the game -------------------------------------------------------

def test_kuhn_is_gdl_ii_and_not_an_identification_gate():
    from lgref.identify.testgames import ground_truth

    game = GGPGame.from_file(KUHN)
    assert game.dialect == 'GDL-II'
    assert game.roles == ['player1', 'player2', 'random']
    assert all('kuhn' not in str(key).lower()
               for key in ground_truth.GAMES)


def test_a_player_is_told_its_own_card_and_nothing_of_the_other():
    game = _dealt('k', 'j')
    assert game.view('player1').steps == (
        ('noop', frozenset({('mycard', 'k')})),)
    assert game.view('player2').steps == (
        ('noop', frozenset({('mycard', 'j')})),)
    assert game.current_player == 'player1'
    assert game.view('player1').legal == ('bet', 'check')
    assert game.view('player2').legal == ('noop',)


def test_betting_is_public_and_a_fold_shows_no_card():
    game = _dealt('q', 'k')
    game.execute_turn(('player1', 'bet'))
    assert game.view('player2').steps[-1] == (
        'noop', frozenset({('opponent_did', 'bet')}))
    assert game.view('player1').steps[-1] == ('bet', frozenset())
    assert game.view('player2').legal == ('call', 'fold')
    game.execute_turn(('player2', 'fold'))
    assert game.is_game_over()
    assert game.view('player1').steps[-1] == (
        'noop', frozenset({('opponent_did', 'fold')}))
    assert _chips(game, 'player1') == 1 and _chips(game, 'player2') == -1


def test_a_showdown_shows_both_cards_and_pays_the_pot():
    cases = [
        (('check', 'check'), 'player1', 1),            # pot 2, K holds
        (('check', 'bet', 'call'), 'player1', 2),      # pot 4
        (('check', 'bet', 'fold'), 'player2', 1),
        (('bet', 'call'), 'player1', 2),
    ]
    for actions, winner, stake in cases:
        game = _dealt('k', 'q')
        for action in actions:
            game.execute_turn((game.current_player, action))
        assert game.is_game_over(), actions
        loser = 'player2' if winner == 'player1' else 'player1'
        assert _chips(game, winner) == stake, actions
        assert _chips(game, loser) == -stake, actions
        assert game.ggp.goal('player1') + game.ggp.goal('player2') == 100
        shown = dict((role, [p for p in game.view(role).steps[-1][1]
                             if p[0] == 'shown'])
                     for role in kuhn.SEATS)
        if actions[-1] == 'fold':
            assert shown == {'player1': [], 'player2': []}
        else:
            assert shown == {'player1': [('shown', 'q')],
                             'player2': [('shown', 'k')]}


def test_kuhn_is_well_formed_legality_is_a_function_of_the_view():
    game = GGPGame.from_file(KUHN)
    model = KnowledgeModel(game, game.state)
    for length in range(1, 5):
        for role in kuhn.SEATS:
            groups = collections.defaultdict(set)
            for history in model.sequences(length):
                groups[model.view(history, role)].add(
                    tuple(model.legal(history, role)))
            assert groups
            assert all(len(legal) == 1 for legal in groups.values()), (
                role, length)


# ---- 2. the deal -------------------------------------------------------

def test_the_deal_is_uniform_over_the_six_deals():
    deals = collections.Counter()
    for seed in range(600):
        game = load(KUHN, seed=seed)
        assert game.current_player == 'random'
        game.execute_turn(game.nature_turn())
        held = dict((f[1], f[2]) for f in game.state if f[0] == 'holds')
        deals[(held['player1'], held['player2'])] += 1
    assert sorted(deals) == sorted((a, b) for a in kuhn.CARDS
                                   for b in kuhn.CARDS if a != b)
    # 600 draws, 100 expected per deal, sd about 9: 40 is over four sd.
    assert all(abs(count - 100) < 40 for count in deals.values()), deals


# ---- 3. V6 and V0 play from their views only ---------------------------

def test_v6_and_v0_are_never_handed_the_game_and_never_read_its_state():
    rules = _rules()
    for seed in range(6):
        game = _seal(load(KUHN, seed=seed))
        players = {}
        for index, role in enumerate(kuhn.SEATS):
            inner = (hidden.DeterminizedPlayer(rules, role, seed=seed)
                     if (index + seed) % 2
                     else hidden.UniformPlayer(role, seed=seed))
            players[role] = _Watched(inner)
        assert hidden.play(game, players) is not None
        assert any(w.calls for w in players.values())


def test_the_opponents_card_does_not_change_v6s_move():
    """Player1 holds the queen; player2 holds the jack in one game and
    the king in the other. The views are equal, so the moves are."""
    rules = _rules()
    seen = []
    for other in ('j', 'k'):
        game = _dealt('q', other)
        game.execute_turn(('player1', 'check'))
        game.execute_turn(('player2', 'bet'))
        player = hidden.DeterminizedPlayer(rules, 'player1', seed=3)
        view = game.view('player1')
        seen.append((view, player.choose(view),
                     sorted(player.last_values.items())))
    assert seen[0] == seen[1]


# ---- 4. the reference, and what it says about V6 ------------------------

def test_the_equilibrium_is_worth_minus_one_eighteenth_and_unexploitable():
    for alpha in (0.0, 1.0 / 6, 1.0 / 3):
        eq = kuhn.nash(alpha)
        assert abs(kuhn.expected(eq['player1'], eq['player2'])
                   - kuhn.VALUE) < 1e-12
        for seat in kuhn.SEATS:
            assert abs(kuhn.exploitability(eq[seat], seat)) < 1e-12


def test_the_reference_catches_a_strategy_that_never_bluffs():
    """Not bluffing is the textbook leak: against it the opponent folds
    every jack and queen to a bet and wins more than the game value."""
    honest = dict(kuhn.nash(0.0)['player2'])
    honest[('j', 'check')] = 0.0
    assert kuhn.exploitability(honest, 'player2') > 0.05


def test_a_view_at_an_information_set_does_not_depend_on_the_hidden_card():
    for seat in kuhn.SEATS:
        for card in kuhn.CARDS:
            for history, _move in kuhn.HISTORIES[seat]:
                views = set()
                for other in kuhn.CARDS:
                    if other == card:
                        continue
                    deal = ((card, other) if seat == 'player1'
                            else (other, card))
                    game = _dealt(*deal)
                    for action in [a for a in history.split(',') if a]:
                        game.execute_turn((game.current_player, action))
                    views.add(game.view(seat))
                assert len(views) == 1
                assert views == {kuhn.view_at(KUHN, seat, card, history)}


def test_the_strategy_player_plays_its_table_from_the_view():
    eq = kuhn.nash()
    player = kuhn.StrategyPlayer('player1', eq['player1'], seed=0)
    # A king with alpha = 1/3 is always bet; a jack facing a bet folds.
    assert player.choose(kuhn.view_at(KUHN, 'player1', 'k', '')) == 'bet'
    assert player.choose(
        kuhn.view_at(KUHN, 'player1', 'j', 'check,bet')) == 'fold'


def test_v6_is_exploitable_in_both_seats_a_recorded_limit():
    """THE FINDING, pinned so the doc cannot drift from it. Not a gate:
    it says what V6 is. Each sample is searched as if both hands were
    face up, so a bluff never pays inside a sample, and a finished
    sample is valued by `winner`, so losing one chip and losing two
    tie. `docs/experiments/version-win-rates.md` has the numbers."""
    for seat in kuhn.SEATS:
        mine = kuhn.strategy_of(KUHN, hidden.PLAYERS['v6'], seat,
                                seeds=16)
        assert kuhn.exploitability(mine, seat) > 0.1, (seat, mine)
    # Determinization alone, without the win/loss collapse: never bluffs
    # a jack in either seat, where the equilibrium bluffs player2's jack
    # one time in three.
    for seat, history in (('player1', ''), ('player2', 'check')):
        diag = kuhn.strategy_of(KUHN, kuhn.goal_searched, seat, seeds=4)
        assert diag[('j', history)] == 0.0
