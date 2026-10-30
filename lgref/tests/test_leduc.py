"""Leduc Hold'em: two rounds, raises and a public card (issue #292).

The same four claims as Kuhn poker's tests, in the order they depend on
each other.

1. LEDUC IS THE GAME IT SAYS. Each player is told its own card's rank,
   the public card's rank and the opponent's betting, and the opponent's
   card only at a showdown. On every betting sequence and every pattern
   of ranks, the GDL's legal moves and payoffs are the reference's. It
   is WELL-FORMED for GDL-II.

2. THE DEAL IS FAIR: 30 ordered private deals, then one of the four
   cards left, drawn uniformly by `GdlGame`.

3. V6 AND V0 PLAY FROM THEIR VIEWS ONLY, with the sealed host state.

4. THE REFERENCE IS RIGHT, so what it says about V6 can be believed:
   CFR+ reaches an equilibrium worth about -0.0856 to player1 (the
   published value) with near-zero exploitability, and the exploitability
   measure catches a strategy known to leak. What it says about V6 is a
   LIMIT, recorded, not a gate.
"""

import collections
import os
import sys

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp.epistemic import KnowledgeModel  # noqa: E402
from ggp.game import GGPGame  # noqa: E402

from lgref.experiments import hidden, leduc  # noqa: E402
from lgref.experiments.gdl import load  # noqa: E402
from lgref.tests.test_hidden import _Watched, _seal  # noqa: E402

LEDUC = os.path.join(HERE, '..', 'identify', 'testgames', 'leducholdem.gdl')


def _rules():
    with open(LEDUC) as handle:
        return handle.read()


def _chips(game, role):
    goal = game.ggp.goal(role)
    assert (goal - 50) % 3 == 0, goal
    return (goal - 50) // 3


def _play(deal, h1, h2):
    """The host after `deal` and the betting `(h1, h2)`."""
    game = load(LEDUC)
    game.execute_turn(('random', ('deal', deal[0], deal[1])))
    for action in h1:
        game.execute_turn((game.current_player, action))
    if h2 is not None:
        game.execute_turn(('random', ('reveal', deal[2])))
        for action in h2:
            game.execute_turn((game.current_player, action))
    return game


def _leaves():
    out = []

    def walk(h1, h2):
        state = leduc.status(h1, h2)
        if state[0] == 'board':
            walk(h1, ())
        elif state[0] == 'act':
            for action in state[2]:
                walk(*leduc._children(h1, h2, action))
        else:
            out.append((h1, h2))
    walk((), None)
    return out


# ---- 1. the game -------------------------------------------------------

def test_leduc_is_gdl_ii_and_not_an_identification_gate():
    from lgref.identify.testgames import ground_truth

    game = GGPGame.from_file(LEDUC)
    assert game.dialect == 'GDL-II'
    assert game.roles == ['player1', 'player2', 'random']
    assert all('leduc' not in str(key).lower()
               for key in ground_truth.GAMES)


def test_a_player_sees_ranks_its_own_card_and_the_board_only():
    game = _play(('j1', 'k2', 'k1'), (), None)
    assert game.view('player1').steps == (
        ('noop', frozenset({('mycard', 'j')})),)
    assert game.view('player2').steps == (
        ('noop', frozenset({('mycard', 'k')})),)
    assert game.view('player1').legal == ('bet', 'check')
    game = _play(('j1', 'k2', 'k1'), ('check', 'check'), ())
    for role in leduc.SEATS:
        assert game.view(role).steps[-1] == (
            'noop', frozenset({('board', 'k')}))
    assert game.current_player == 'player1'


def test_the_two_cards_of_a_rank_look_the_same():
    """j1 and j2 differ only physically, so the views must not."""
    views = set()
    for mine in ('q1', 'q2'):
        game = _play((mine, 'k1', 'j1'), ('bet', 'call'), ())
        views.add(game.view('player1'))
    assert len(views) == 1


def test_every_betting_sequence_matches_the_reference():
    """All 49 complete betting sequences on one deal of each of the 24
    rank patterns: the legal moves at every node, then the chips."""
    patterns = {}
    for deal in leduc.DEALS:
        patterns.setdefault(tuple(leduc.RANK[c] for c in deal), deal)
    leaves = _leaves()
    assert len(patterns) == 24 and len(leaves) == 49
    for deal in patterns.values():
        for h1, h2 in leaves:
            game = load(LEDUC)
            game.execute_turn(('random', ('deal', deal[0], deal[1])))
            rounds = [(1, h1)] + ([(2, h2)] if h2 is not None else [])
            for number, actions in rounds:
                if number == 2:
                    assert game.current_player == 'random'
                    game.execute_turn(('random', ('reveal', deal[2])))
                for index, action in enumerate(actions):
                    node = (leduc.status(actions[:index], None)
                            if number == 1
                            else leduc.status(h1, actions[:index]))
                    assert node[0] == 'act'
                    assert game.current_player == node[1]
                    assert game.view(node[1]).legal == node[2]
                    game.execute_turn((node[1], action))
            assert game.is_game_over(), (h1, h2)
            assert _chips(game, 'player1') == leduc.payoff(deal, h1, h2)
            assert (game.ggp.goal('player1')
                    + game.ggp.goal('player2')) == 100


def test_a_showdown_shows_cards_and_a_fold_shows_none():
    game = _play(('q1', 'j2', 'q2'), ('bet', 'call'), ('bet', 'call'))
    assert game.is_game_over()
    assert _chips(game, 'player1') == 7            # ante 1 + 2 + 4, paired
    assert ('shown', 'j') in game.view('player1').steps[-1][1]
    assert ('shown', 'q') in game.view('player2').steps[-1][1]
    game = _play(('q1', 'j2', 'q2'), ('bet', 'raise', 'fold'), None)
    assert game.is_game_over()
    assert _chips(game, 'player1') == -3           # ante 1 + the bet of 2
    for role in leduc.SEATS:
        assert not [p for _move, ps in game.view(role).steps for p in ps
                    if p[0] == 'shown']


def test_equal_ranks_split_the_pot():
    game = _play(('k1', 'k2', 'j1'), ('check', 'check'), ('check', 'check'))
    assert game.ggp.goal('player1') == game.ggp.goal('player2') == 50


def test_leduc_is_well_formed_legality_is_a_function_of_the_view():
    game = GGPGame.from_file(LEDUC)
    model = KnowledgeModel(game, game.state)
    for length in range(1, 4):
        for role in leduc.SEATS:
            groups = collections.defaultdict(set)
            for history in model.sequences(length):
                groups[model.view(history, role)].add(
                    tuple(model.legal(history, role)))
            assert groups
            assert all(len(legal) == 1 for legal in groups.values()), (
                role, length)


# ---- 2. the deal -------------------------------------------------------

def test_the_deal_and_the_board_are_uniform():
    deals, boards = collections.Counter(), collections.Counter()
    for seed in range(1200):
        game = load(LEDUC, seed=seed)
        assert game.current_player == 'random'
        game.execute_turn(game.nature_turn())
        held = dict((f[1], f[2]) for f in game.state if f[0] == 'holds')
        deals[(held['player1'], held['player2'])] += 1
        game.execute_turn(('player1', 'check'))
        game.execute_turn(('player2', 'check'))
        assert game.current_player == 'random'
        game.execute_turn(game.nature_turn())
        (board,) = [f[1] for f in game.state if f[0] == 'board']
        assert board not in held.values()
        boards[board] += 1
    assert len(deals) == 30
    # 1200 draws: 40 expected per deal (sd ~6.2), 200 per board card
    # (sd ~13): both bounds are over four sd.
    assert all(abs(count - 40) < 26 for count in deals.values()), deals
    assert sorted(boards) == sorted(leduc.CARDS)
    assert all(abs(count - 200) < 55 for count in boards.values()), boards


# ---- 3. V6 and V0 play from their views only ---------------------------

def test_v6_and_v0_are_never_handed_the_game_and_never_read_its_state():
    rules = _rules()
    for seed in range(6):
        game = _seal(load(LEDUC, seed=seed))
        players = {}
        for index, role in enumerate(leduc.SEATS):
            inner = (hidden.DeterminizedPlayer(rules, role, seed=seed)
                     if (index + seed) % 2
                     else hidden.UniformPlayer(role, seed=seed))
            players[role] = _Watched(inner)
        assert hidden.play(game, players) is not None
        assert any(w.calls for w in players.values())


def test_the_opponents_card_does_not_change_v6s_move():
    rules = _rules()
    seen = []
    for other in ('j1', 'k1'):
        game = _play(('q1', other, 'k2'), ('check', 'bet'), None)
        player = hidden.DeterminizedPlayer(rules, 'player1', seed=3)
        view = game.view('player1')
        seen.append((view, player.choose(view),
                     sorted(player.last_values.items())))
    assert seen[0] == seen[1]


# ---- 4. the reference --------------------------------------------------

def test_the_tree_has_the_published_shape():
    assert len(leduc.DEALS) == 120
    assert len(leduc.nodes()) == 36
    assert all(len(leduc.infosets(s)) == 144 for s in leduc.SEATS)


def test_cfr_plus_reaches_the_published_value_with_tiny_exploitability():
    """Southey et al. and later work give Leduc's value to player1 as
    about -0.0856. 300 iterations land within 0.002 of it with each
    seat exploitable by under 0.005 chips."""
    eq, value = leduc.solve(300)
    assert abs(value - (-0.0856)) < 0.002, value
    for seat in leduc.SEATS:
        gap = leduc.exploitability(eq[seat], seat, value)
        assert -1e-3 < gap < 0.005, (seat, gap)


def test_the_reference_catches_a_strategy_that_never_folds():
    """Calling down with everything is a known leak."""
    eq, value = leduc.solve(300)
    station = {}
    for key, table in eq['player2'].items():
        if 'call' in table:
            station[key] = dict((a, 1.0 if a == 'call' else 0.0)
                                for a in table)
        else:
            station[key] = table
    assert leduc.exploitability(station, 'player2', value) > 0.2


def test_a_view_at_an_information_set_does_not_depend_on_the_deal():
    """Checked on every round-2 information set of player2 with a jack."""
    for key in leduc.infosets('player2'):
        if key[0] != 'j' or not key[1]:
            continue
        h1, _, h2 = key[2].partition('/')
        h1 = tuple(a for a in h1.split(',') if a)
        h2 = tuple(a for a in h2.split(',') if a)
        views = set()
        for deal in leduc.DEALS:
            if (leduc.RANK[deal[1]] == 'j'
                    and leduc.RANK[deal[2]] == key[1]):
                views.add(_play(deal, h1, h2).view('player2'))
        assert views == {leduc.view_at(LEDUC, 'player2', key)}, key
        assert leduc.read(next(iter(views))) == key


def test_the_strategy_player_plays_its_table_from_the_view():
    key = ('k', 'k', 'bet,call/')
    table = {key: {'bet': 1.0, 'check': 0.0}}
    player = leduc.StrategyPlayer('player1', table, seed=0)
    assert player.choose(leduc.view_at(LEDUC, 'player1', key)) == 'bet'


def test_v6_is_exploitable_and_never_folds_a_recorded_limit():
    """THE FINDING, pinned so the doc cannot drift from it. Not a gate.

    Measured at 200 reads per information set: exploitability 2.23 as
    player1 and 1.55 as player2, where a uniform random strategy's is
    2.57 and 2.17. V6 never folds in either seat: a fold ends every
    sample at once in a loss, while any other move reaches a position
    the depth-2 flat search scores as a tie.
    `docs/experiments/version-win-rates.md` has the numbers."""
    _eq, value = leduc.solve(300)
    for seat in leduc.SEATS:
        mine = leduc.strategy_of(LEDUC, hidden.PLAYERS['v6'], seat,
                                 seeds=2)
        assert leduc.exploitability(mine, seat, value) > 1.0, seat
        assert all(table.get('fold', 0.0) == 0.0
                   for table in mine.values()), seat
