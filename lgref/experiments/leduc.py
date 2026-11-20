"""Leduc Hold'em as a measuring stick for V6 (issue #292).

Kuhn poker (#288) showed where V6's determinization meets a bluffing
opponent, in a game small enough to solve by hand. Leduc Hold'em is the
next size up and the standard mid-sized poker benchmark: two betting
rounds, raises, and a public card that makes pairs. It has no closed-
form equilibrium, so this module computes one.

THIS MODULE KNOWS LEDUC HOLD'EM. Like `kuhn.py` it is a reference,
written by hand for this one game, and nothing in V6 reads it: it
exists to grade V6, never to help it.

THE GAME (Southey et al. 2005), as `leducholdem.gdl` states it. Six
cards, two each of jack < queen < king. Both ante 1. Round 1: one
private card each, bets of 2. Round 2: one public card, bets of 4.
Each round allows one bet and one raise, and player1 acts first in
both. A pair with the public card wins the showdown; otherwise the
higher card; equal ranks split.

THE TREE. A deal is a triple of physical cards (player1's, player2's,
the public one), and the 120 triples are equally likely -- which is
what dealing two cards and then turning one of the four left gives. A
public node is the betting so far, one tuple of actions per round.
Every computation below walks the public tree ONCE with a vector over
the 120 deals, so a whole pass is a few thousand vector operations.

INFORMATION SETS are `(card rank, board rank or '', history)`, with the
history written as in a view: actions joined by ',', rounds by '/'.
Player1 has 144 and player2 has 144.

WHAT IS MEASURED, as for Kuhn poker. A strategy is a probability for
each legal action at each information set. Its EXPLOITABILITY is what a
best response to it wins above the game value; 0 means equilibrium.
Payoff against an equilibrium alone can hide a leak, so both are
reported.

THE EQUILIBRIUM is computed by CFR+ (Tammelin 2014): regret matching
with regrets floored at zero, alternating updates, and the average
strategy weighted by iteration. Its own exploitability is reported with
it, so "Nash" below always says how close to one it is.
"""

import random as _random

RANKS = ('j', 'q', 'k')
ORDER = dict((rank, index) for index, rank in enumerate(RANKS))
CARDS = ('j1', 'j2', 'q1', 'q2', 'k1', 'k2')
RANK = dict((card, card[0]) for card in CARDS)
SEATS = ('player1', 'player2')
SIZE = {1: 2, 2: 4}
DEALS = tuple((a, b, c) for a in CARDS for b in CARDS for c in CARDS
              if len({a, b, c}) == 3)
N = len(DEALS)


# ---- the betting --------------------------------------------------------

def _round(actions):
    """`('act', seat, legal)`, `('over',)` or `('fold', seat)` for one
    round's actions so far."""
    if actions and actions[-1] == 'fold':
        return ('fold', SEATS[(len(actions) - 1) % 2])
    if actions and (actions[-1] == 'call'
                    or tuple(actions) == ('check', 'check')):
        return ('over',)
    seat = SEATS[len(actions) % 2]
    bets = sum(1 for a in actions if a in ('bet', 'raise'))
    if actions and actions[-1] in ('bet', 'raise'):
        legal = ('call', 'fold') + (('raise',) if bets == 1 else ())
    else:
        legal = ('bet', 'check')
    return ('act', seat, tuple(sorted(legal)))


def status(h1, h2):
    """The public node `(h1, h2)`: h2 is None until the board is up.
    Returns `('act', seat, legal)`, `('fold', seat)`, `('board',)` when
    round 1 is over, or `('showdown',)`."""
    if h2 is None:
        state = _round(h1)
        return ('board',) if state[0] == 'over' else state
    state = _round(h2)
    return ('showdown',) if state[0] == 'over' else state


def put_in(h1, h2):
    """Chips each seat has put in at the end of this betting."""
    put = {'player1': 1, 'player2': 1}
    for number, actions in ((1, h1), (2, h2 or ())):
        for index, action in enumerate(actions):
            me = SEATS[index % 2]
            other = SEATS[1 - index % 2]
            if action in ('bet', 'raise'):
                put[me] = put[other] + SIZE[number]
            elif action == 'call':
                put[me] = put[other]
    return put


def strength(card, board):
    """Higher is better: a pair beats any unpaired card."""
    return (RANK[card] == RANK[board], ORDER[RANK[card]])


def payoff(deal, h1, h2):
    """Player1's chips at a terminal node."""
    put = put_in(h1, h2)
    state = status(h1, h2)
    if state[0] == 'fold':
        return -put['player1'] if state[1] == 'player1' else put['player2']
    mine, theirs = strength(deal[0], deal[2]), strength(deal[1], deal[2])
    if mine == theirs:
        return 0
    return put['player2'] if mine > theirs else -put['player1']


def history(h1, h2):
    text = ','.join(h1)
    return text if h2 is None else text + '/' + ','.join(h2)


def infoset(seat, deal, h1, h2):
    card = deal[0] if seat == 'player1' else deal[1]
    board = '' if h2 is None else RANK[deal[2]]
    return (RANK[card], board, history(h1, h2))


def nodes():
    """Every public decision node, as `(h1, h2, seat, legal)`."""
    out = []

    def walk(h1, h2):
        state = status(h1, h2)
        if state[0] == 'board':
            walk(h1, ())
        elif state[0] == 'act':
            out.append((h1, h2, state[1], state[2]))
            for action in state[2]:
                if h2 is None:
                    walk(h1 + (action,), None)
                else:
                    walk(h1, h2 + (action,))
    walk((), None)
    return out


def infosets(seat):
    """`{infoset: legal}` for `seat`, every one reachable."""
    out = {}
    for h1, h2, mover, legal in nodes():
        if mover != seat:
            continue
        for deal in DEALS:
            out[infoset(seat, deal, h1, h2)] = legal
    return out


def _children(h1, h2, action):
    return (h1 + (action,), None) if h2 is None else (h1, h2 + (action,))


# ---- values -------------------------------------------------------------

def expected(first, second):
    """Player1's exact expected chips per hand, strategy `first` as
    player1 against `second` as player2."""
    strategies = {'player1': first, 'player2': second}

    def walk(h1, h2, reach):
        state = status(h1, h2)
        if state[0] == 'board':
            return walk(h1, (), reach)
        if state[0] != 'act':
            return sum(r * payoff(d, h1, h2)
                       for r, d in zip(reach, DEALS) if r)
        seat, legal = state[1], state[2]
        table = strategies[seat]
        total = 0.0
        for action in legal:
            child = [r * table[infoset(seat, d, h1, h2)][action] if r else 0.0
                     for r, d in zip(reach, DEALS)]
            total += walk(*_children(h1, h2, action), reach=child)
        return total
    return walk((), None, [1.0] * N) / N


def best_response(strategy, seat):
    """`(chips, response)`: the other seat's best pure reply to
    `strategy` played in `seat`, and what it wins per hand."""
    me = SEATS[1 - SEATS.index(seat)]
    sign = 1.0 if me == 'player1' else -1.0
    response = {}

    def walk(h1, h2, reach):
        state = status(h1, h2)
        if state[0] == 'board':
            return walk(h1, (), reach)
        if state[0] != 'act':
            return [r * sign * payoff(d, h1, h2) if r else 0.0
                    for r, d in zip(reach, DEALS)]
        mover, legal = state[1], state[2]
        if mover == seat:
            out = [0.0] * N
            for action in legal:
                child = [r * strategy[infoset(seat, d, h1, h2)][action]
                         if r else 0.0 for r, d in zip(reach, DEALS)]
                values = walk(*_children(h1, h2, action), reach=child)
                out = [a + b for a, b in zip(out, values)]
            return out
        values = dict((action, walk(*_children(h1, h2, action), reach=reach))
                      for action in legal)
        groups = {}
        for index, deal in enumerate(DEALS):
            groups.setdefault(infoset(me, deal, h1, h2), []).append(index)
        out = [0.0] * N
        for key, members in groups.items():
            best = max(legal, key=lambda a: (
                sum(values[a][i] for i in members), a))
            response[key] = dict((a, 1.0 if a == best else 0.0)
                                 for a in legal)
            for i in members:
                out[i] = values[best][i]
        return out
    chips = sum(walk((), None, [1.0] * N)) / N
    return chips, response


def value_of(seat, value):
    """The equilibrium value of `seat`, given player1's `value`."""
    return value if seat == 'player1' else -value


def exploitability(strategy, seat, value):
    """Chips a best response wins against `strategy` in `seat`, above
    what it would win at equilibrium (player1's game value `value`)."""
    chips, _response = best_response(strategy, seat)
    return chips - value_of(SEATS[1 - SEATS.index(seat)], value)


# ---- the equilibrium ----------------------------------------------------

def cfr_plus(iterations):
    """`(average strategies, player1's value against itself)` after
    `iterations` rounds of CFR+."""
    tables = dict((seat, infosets(seat)) for seat in SEATS)
    regret = dict((seat, dict((key, dict((a, 0.0) for a in legal))
                              for key, legal in tables[seat].items()))
                  for seat in SEATS)
    total = dict((seat, dict((key, dict((a, 0.0) for a in legal))
                             for key, legal in tables[seat].items()))
                 for seat in SEATS)

    def current(seat, key):
        r = regret[seat][key]
        positive = sum(v for v in r.values() if v > 0)
        if positive <= 0:
            return dict((a, 1.0 / len(r)) for a in r)
        return dict((a, max(v, 0.0) / positive) for a, v in r.items())

    def walk(h1, h2, reach, learner, weight):
        """Per-deal values to `learner`. `reach` is per deal and per seat."""
        state = status(h1, h2)
        if state[0] == 'board':
            return walk(h1, (), reach, learner, weight)
        sign = 1.0 if learner == 'player1' else -1.0
        if state[0] != 'act':
            return [sign * payoff(d, h1, h2) for d in DEALS]
        mover, legal = state[1], state[2]
        keys = [infoset(mover, d, h1, h2) for d in DEALS]
        sigma = {}
        for key in set(keys):
            sigma[key] = current(mover, key)
        values = {}
        for action in legal:
            child = dict(reach)
            child[mover] = [r * sigma[k][action]
                            for r, k in zip(reach[mover], keys)]
            values[action] = walk(*_children(h1, h2, action), reach=child,
                                  learner=learner, weight=weight)
        out = [sum(sigma[k][a] * values[a][i] for a in legal)
               for i, k in enumerate(keys)]
        if mover == learner:
            other = SEATS[1 - SEATS.index(mover)]
            gains = {}
            for i, key in enumerate(keys):
                cf = reach[other][i]
                row = gains.setdefault(key, dict((a, 0.0) for a in legal))
                for a in legal:
                    row[a] += cf * (values[a][i] - out[i])
                own = reach[mover][i]
                acc = total[mover][key]
                for a in legal:
                    acc[a] += weight * own * sigma[key][a]
            for key, row in gains.items():
                r = regret[mover][key]
                for a in legal:
                    r[a] = max(r[a] + row[a], 0.0)
        return out

    for t in range(1, iterations + 1):
        for learner in SEATS:
            walk((), None, {'player1': [1.0] * N, 'player2': [1.0] * N},
                 learner, float(t))
    average = {}
    for seat in SEATS:
        average[seat] = {}
        for key, acc in total[seat].items():
            norm = sum(acc.values())
            average[seat][key] = (
                dict((a, v / norm) for a, v in acc.items()) if norm > 0
                else dict((a, 1.0 / len(acc)) for a in acc))
    return average, expected(average['player1'], average['player2'])


_SOLVED = {}


def solve(iterations=1000):
    """The CFR+ equilibrium, cached per process: `(strategies, value)`."""
    if iterations not in _SOLVED:
        _SOLVED[iterations] = cfr_plus(iterations)
    return _SOLVED[iterations]


# ---- players and views --------------------------------------------------

def read(view):
    """`(card rank, board rank or '', history)` from a view: the
    information set the view is at, written as `infoset` writes it."""
    card, board = None, ''
    rounds = [[]]
    for move, percepts in view.steps:
        for percept in sorted(percepts):
            if percept[0] == 'mycard':
                card = percept[1]
            elif percept[0] == 'board':
                board = percept[1]
                rounds.append([])
        for percept in percepts:
            if percept[0] == 'opponent_did':
                rounds[-1].append(percept[1])
        if move != 'noop':
            rounds[-1].append(move)
    text = ','.join(rounds[0])
    if len(rounds) > 1:
        text += '/' + ','.join(rounds[1])
    return card, board, text


class StrategyPlayer(object):
    """Plays a fixed `{infoset: {action: p}}` strategy from its view."""

    def __init__(self, role, strategy, seed=None):
        self.role = role
        self.strategy = strategy
        self._rng = _random.Random(seed)

    def choose(self, view):
        table = self.strategy[read(view)]
        roll = self._rng.random()
        for action in sorted(table):
            roll -= table[action]
            if roll < 0:
                return action
        return sorted(table)[-1]


def view_at(path, seat, key):
    """The view `seat` has at information set `key`, built by the host
    from one concrete deal that fits it. By construction the view does
    not depend on which deal; `test_leduc.py` checks that."""
    from lgref.experiments.gdl import load

    card, board, text = key
    deal = next(d for d in DEALS
                if RANK[d[0 if seat == 'player1' else 1]] == card
                and (not board or RANK[d[2]] == board))
    h1, _, h2 = text.partition('/')
    game = load(path)
    game.execute_turn(('random', ('deal', deal[0], deal[1])))
    for action in [a for a in h1.split(',') if a]:
        game.execute_turn((game.current_player, action))
    if board:
        game.execute_turn(('random', ('reveal', deal[2])))
        for action in [a for a in h2.split(',') if a]:
            game.execute_turn((game.current_player, action))
    if game.current_player != seat:
        raise ValueError('{0!r} is not to move at {1!r}'.format(seat, key))
    return game.view(seat)


def strategy_of(path, make, seat, seeds=16):
    """A player's strategy in `seat`, read by asking fresh players.

    `make(rules, role, seed)` builds the player. Every information set
    is shown to `seeds` freshly seeded players, so a player that breaks
    ties at random is read as the frequency it actually plays."""
    with open(path) as handle:
        rules = handle.read()
    strategy = {}
    for key, legal in sorted(infosets(seat).items()):
        view = view_at(path, seat, key)
        counts = dict((a, 0) for a in legal)
        for seed in range(seeds):
            counts[make(rules, seat, seed).choose(view)] += 1
        strategy[key] = dict((a, counts[a] / float(seeds)) for a in legal)
    return strategy


def chips(path, make_a, make_b, games, seed=0):
    """A seat-balanced sample of `make_a`'s chips against `make_b`.

    Game i seats A as player1 when i is even. Returns `{seat: (total
    chips, games)}` for A."""
    from lgref.experiments import hidden
    from lgref.experiments.gdl import load

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
        out[mine][0] += (goals[mine] - 50) // 3
        out[mine][1] += 1
    return dict((seat, tuple(v)) for seat, v in out.items())


def main(argv=None):
    """`python -m lgref.experiments.leduc GAMES SEED [ITERATIONS
    [READS]]`: the equilibrium and how close it is; V6's chips against
    V0 and against it, sampled; then V6's strategy, read from READS
    fresh players per information set, scored exactly."""
    import os
    import sys
    import time

    from lgref.experiments import hidden

    args = list(sys.argv[1:] if argv is None else argv)
    games, seed = int(args[0]), int(args[1])
    iterations = int(args[2]) if len(args) > 2 else 1000
    reads = int(args[3]) if len(args) > 3 else 16
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'identify', 'testgames',
        'leducholdem.gdl')
    start = time.time()
    eq, value = solve(iterations)
    print('cfr+', iterations, 'iterations, value', value,
          'exploitability', dict((s, exploitability(eq[s], s, value))
                                 for s in SEATS),
          '%.0fs' % (time.time() - start), flush=True)
    v6 = hidden.PLAYERS['v6']

    def nash_player(_rules, role, s):
        return StrategyPlayer(role, eq[role], seed=s)

    for name, other in (('v0', hidden.PLAYERS['v0']), ('nash', nash_player)):
        print('v6 chips vs', name, chips(path, v6, other, games, seed=seed),
              flush=True)
    for seat in SEATS:
        mine = strategy_of(path, v6, seat, seeds=reads)
        other = SEATS[1 - SEATS.index(seat)]
        exact = (expected(mine, eq[other]) if seat == 'player1'
                 else -expected(eq[other], mine))
        print('v6', seat, 'exact chips vs nash', exact, 'value',
              value_of(seat, value), 'exploitability',
              exploitability(mine, seat, value), flush=True)


if __name__ == '__main__':
    main()
