"""Kuhn poker as a measuring stick for V6 (issue #288).

Krieg-TicTacToe and Monty Hall have no opponent who holds hidden
information and uses it. Kuhn poker is the smallest game that does,
and it is solved (Kuhn 1950), so a player's strategy there can be
scored exactly instead of only by its record against another player.

THIS MODULE KNOWS KUHN POKER. It is a reference, like
`testgames/reference.py`: the equilibrium strategy and the exact
game-tree arithmetic below are written by hand for this one game, and
nothing in V6 reads them. They exist to grade V6, never to help it.

THE GAME, with player1 acting first. Information sets are a card and
the public history before the decision:

  player1  ''           check or bet
  player2  'check'      check or bet
  player2  'bet'        fold or call
  player1  'check,bet'  fold or call

A STRATEGY here is, for each of those twelve (card, history) pairs, the
probability of the AGGRESSIVE action: bet where a player may bet, call
where it faces one.

THE EQUILIBRIUM. A one-parameter family for player1, alpha in [0, 1/3]:
bet a jack with alpha, a king with 3 alpha, never a queen; facing a
bet, fold a jack, call a queen with alpha + 1/3, call a king. Player2's
equilibrium is unique: bet a king, bet a jack with 1/3 after a check;
facing a bet, call a king, call a queen with 1/3, fold a jack. The game
is worth -1/18 of a chip to player1.

WHAT IS MEASURED AND WHY TWO NUMBERS. Against a fixed equilibrium, many
strategies earn exactly the game value -- an equilibrium does not punish
a mistake its own mixing makes it indifferent to -- so "payoff against
Nash" can hide a strategy that is badly exploitable. EXPLOITABILITY is
the other number: what an opponent that knows the strategy earns
against it with a best response, minus what it would earn at the
equilibrium. Zero means the strategy is an equilibrium.
"""

import random as _random

from lgref.experiments.gdl import load

CARDS = ('j', 'q', 'k')
RANK = dict((card, index) for index, card in enumerate(CARDS))
SEATS = ('player1', 'player2')
#: Each seat's information-set histories and the aggressive move at each.
HISTORIES = {
    'player1': (('', 'bet'), ('check,bet', 'call')),
    'player2': (('check', 'bet'), ('bet', 'call')),
}
#: The game's value to player1 under equilibrium play.
VALUE = -1.0 / 18.0


def nash(alpha=1.0 / 3.0):
    """The equilibrium strategies as `{seat: {(card, history): p}}`."""
    return {
        'player1': {
            ('j', ''): alpha, ('q', ''): 0.0, ('k', ''): 3 * alpha,
            ('j', 'check,bet'): 0.0, ('q', 'check,bet'): alpha + 1.0 / 3,
            ('k', 'check,bet'): 1.0,
        },
        'player2': {
            ('j', 'check'): 1.0 / 3, ('q', 'check'): 0.0,
            ('k', 'check'): 1.0,
            ('j', 'bet'): 0.0, ('q', 'bet'): 1.0 / 3, ('k', 'bet'): 1.0,
        },
    }


def _showdown(mine, theirs, stake):
    return stake if RANK[mine] > RANK[theirs] else -stake


def expected(first, second):
    """Player1's exact expected chips, `first` against `second`."""
    total = 0.0
    for c1 in CARDS:
        for c2 in CARDS:
            if c1 == c2:
                continue
            bet = first[(c1, '')]
            call = second[(c2, 'bet')]
            after_bet = call * _showdown(c1, c2, 2) + (1 - call) * 1
            raise_ = second[(c2, 'check')]
            back = first[(c1, 'check,bet')]
            after_raise = back * _showdown(c1, c2, 2) + (1 - back) * -1
            after_check = (raise_ * after_raise
                           + (1 - raise_) * _showdown(c1, c2, 1))
            total += bet * after_bet + (1 - bet) * after_check
    return total / 6.0


def best_response(strategy, seat):
    """`(value, strategy)`: the responder's best pure reply to
    `strategy` played in `seat`, and the chips it wins per hand.

    The responder has six information sets with two moves each, so all
    64 pure strategies are enumerated; a best response is always found
    among the pure ones.
    """
    me = 'player2' if seat == 'player1' else 'player1'
    response = {}
    for card in CARDS:
        for history, _move in HISTORIES[me]:
            response[(card, history)] = 0.0
    best = None
    keys = sorted(response)
    for bits in range(2 ** len(keys)):
        trial = dict((key, float((bits >> i) & 1))
                     for i, key in enumerate(keys))
        if me == 'player1':
            value = expected(trial, strategy)
        else:
            value = -expected(strategy, trial)
        if best is None or value > best[0] + 1e-12:
            best = (value, trial)
    return best


def exploitability(strategy, seat):
    """Chips a best response wins against `strategy` in `seat`, above
    what it would win against the equilibrium."""
    value, _response = best_response(strategy, seat)
    fair = -VALUE if seat == 'player1' else VALUE
    return value - fair


def _history(view):
    """The public betting history before this decision, as in
    `HISTORIES`, read from the view: own moves and `opponent_did`."""
    actions = []
    card = None
    for move, percepts in view.steps:
        for percept in percepts:
            if percept[0] == 'mycard':
                card = percept[1]
            if percept[0] == 'opponent_did':
                actions.append(percept[1])
        if move != 'noop':
            actions.append(move)
    return card, ','.join(actions)


class StrategyPlayer(object):
    """Plays a fixed `{(card, history): p}` strategy from its view."""

    def __init__(self, role, strategy, seed=None):
        self.role = role
        self.strategy = strategy
        self._rng = _random.Random(seed)

    def choose(self, view):
        card, history = _history(view)
        aggressive = 'bet' if 'bet' in view.legal else 'call'
        passive = 'check' if aggressive == 'bet' else 'fold'
        p = self.strategy[(card, history)]
        return aggressive if self._rng.random() < p else passive


def view_at(path, seat, card, history):
    """The view `seat` has at an information set, built by the host.

    The opponent's card is any other card: by construction the view does
    not depend on it, which `test_kuhn.py` checks."""
    other = [c for c in CARDS if c != card][0]
    deal = (card, other) if seat == 'player1' else (other, card)
    game = load(path)
    game.execute_turn(('random', ('deal',) + deal))
    for action in [a for a in history.split(',') if a]:
        game.execute_turn((game.current_player, action))
    if game.current_player != seat:
        raise ValueError('{0!r} is not to move after {1!r}'.format(
            seat, history))
    return game.view(seat)


def strategy_of(path, make, seat, seeds=32):
    """A player's strategy in `seat`, read by asking fresh players.

    `make(rules, role, seed)` builds the player. Each information set is
    shown to `seeds` freshly seeded players, so a player that breaks
    ties at random is read as the frequency it actually plays."""
    with open(path) as handle:
        rules = handle.read()
    strategy = {}
    for card in CARDS:
        for history, aggressive in HISTORIES[seat]:
            view = view_at(path, seat, card, history)
            hits = sum(make(rules, seat, seed).choose(view) == aggressive
                       for seed in range(seeds))
            strategy[(card, history)] = hits / float(seeds)
    return strategy


def chips(path, make_a, make_b, games, seed=0):
    """A seat-balanced sample of `make_a`'s mean chips against `make_b`.

    Game i seats A as player1 when i is even. Returns
    `{seat: (total chips, games)}` for A."""
    from lgref.experiments import hidden

    with open(path) as handle:
        rules = handle.read()
    out = dict((seat, [0, 0]) for seat in SEATS)
    for index in range(games):
        game = load(path, seed=seed + index)
        mine = SEATS[index % 2]
        players = {}
        for offset, role in enumerate(SEATS):
            make = make_a if role == mine else make_b
            players[role] = make(rules, role, seed * 7919 + index * 31
                                 + offset)
        goals = hidden.play(game, players)
        out[mine][0] += (goals[mine] - 50) // 25
        out[mine][1] += 1
    return dict((seat, tuple(v)) for seat, v in out.items())


def goal_searched(rules, role, seed):
    """A DIAGNOSTIC, NOT A VERSION: V6's belief and choice, with each
    sample searched to the end on the GOAL instead of the winner.

    V6 values a finished sample by `GdlGame.winner`, so losing one chip
    and losing two are the same loss to it. This player differs from V6
    in that one respect, which splits the cost of that collapse from the
    cost of determinization itself. It subclasses V6 without changing
    it, and nothing outside this module plays it.
    """
    from lgref.experiments import hidden

    class GoalSearched(hidden.DeterminizedPlayer):

        def _values(self, particle, moves):
            return dict((move, self._after(particle.state, self.role, move))
                        for move in moves)

        def _after(self, state, mover, move):
            game = self._at(hidden.Particle(state, (), 1.0))
            game.step(dict((r, move if r == mover else 'noop')
                           for r in self.roles))
            if game.is_terminal():
                return game.goal(self.role) / 100.0
            (nxt,) = [r for r in SEATS if 'noop' not in
                      game.legal_moves(r)]
            values = [self._after(frozenset(game.state), nxt, m)
                      for m in game.legal_moves(nxt)]
            return max(values) if nxt == self.role else min(values)

    return GoalSearched(rules, role, seed=seed)


def main(argv=None):
    """`python -m lgref.experiments.kuhn GAMES SEED`: V6's chips against
    V0 and against the equilibrium, sampled; then its strategy, read
    from 400 fresh players per information set, scored exactly.

    The win-rate cells come from `python -m lgref.experiments.hidden`,
    as on the other imperfect-information rows."""
    import os
    import sys

    from lgref.experiments import hidden

    args = list(sys.argv[1:] if argv is None else argv)
    games, seed = int(args[0]), int(args[1])
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'identify', 'testgames',
        'kuhnpoker.gdl')
    v6 = hidden.PLAYERS['v6']
    equilibrium = nash()

    def nash_player(_rules, role, s):
        return StrategyPlayer(role, equilibrium[role], seed=s)

    print('v6 chips vs v0', chips(path, v6, hidden.PLAYERS['v0'], games,
                                  seed=seed))
    print('v6 chips vs nash', chips(path, v6, nash_player, games,
                                    seed=seed))
    for name, make in (('v6', v6), ('goal-searched', goal_searched)):
        for seat in SEATS:
            _report(path, name, make, seat, equilibrium)


def _report(path, name, make, seat, equilibrium):
    mine = strategy_of(path, make, seat, seeds=400)
    other = 'player2' if seat == 'player1' else 'player1'
    exact = (expected(mine, equilibrium[other]) if seat == 'player1'
             else -expected(equilibrium[other], mine))
    print(name, seat, 'strategy', sorted(mine.items()))
    print(name, seat, 'exact chips vs nash', exact,
          'exploitability', exploitability(mine, seat),
          'best response', best_response(mine, seat))


if __name__ == '__main__':
    main()
