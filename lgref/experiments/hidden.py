"""V6: play a GDL-II game from what the player is told, and nothing else.

Issue #286. Every player before this one (V1-V5) reads `GdlGame.state`,
which in an imperfect-information game is the hidden truth: in
Krieg-TicTacToe it is the opponent's marks. Their cells on the
imperfect-information rows were marked † for that reason
(`docs/experiments/version-win-rates.md`).

WHAT THIS PLAYER IS GIVEN. The game's RULES, which are public, its own
role, and at each move a `gdl.View`: its own moves so far, the `sees`
percepts each one earned, and its legal moves now. That is the whole of
what GDL-II entitles a player to (Schiffel & Thielscher 2014), and it is
the same information `ggp.epistemic` uses to decide which play sequences
a role cannot tell apart. The player never holds the host's game, so
there is no reference through which it could read the state;
`lgref/tests/test_hidden.py` asserts that structurally and by
behaviour.

HOW IT DECIDES: DETERMINIZATION, also called Perfect Information Monte
Carlo (Long, Sturtevant, Buro & Furtak 2010).

  1. BELIEF. The play sequences consistent with the view, each with
     the state it leads to and its probability. At each new step the
     player's own move is fixed. Every joint move of the other roles
     that would have produced the percepts actually seen, and left the
     game live, is a continuation, weighted by its chance under the
     prior. The belief is EXACT while it holds at most `particles`
     sequences and is resampled to that many beyond it, which makes it a
     particle filter only once it has to be one.

  2. SEARCH. On each sampled state, the existing alpha-beta `Searcher`
     values every legal move at a fixed depth, as if the state were
     known. Duplicate states are searched once.

  3. CHOICE. The move with the highest weighted mean value. Ties are
     broken by the seeded generator, not by list order, so equal moves
     are not all resolved to the first cell.

THE WEIGHTS ARE A LIKELIHOOD, and the prior behind them is stated
because it is a choice. Nature's moves are uniform: GDL-II defines
`random` that way, so for nature this is exact, and the weighting is
what makes Monty Hall come out at 2/3 for switching instead of 1/2
(`test_the_belief_is_the_true_posterior_on_monty_hall`). The OPPONENT'S
moves are also taken as uniform, which is an assumption: it is the
least-informed prior, and it is exactly right against V0.

KNOWN LIMITS OF DETERMINIZATION, which are the method's and not a bug.
Each sample is searched as if both sides could see everything, so the
player cannot value hiding information or gathering it ("strategy
fusion" and "non-locality" in Frank & Basin 1998). Inside a sample,
nature's FUTURE moves are searched like any other player's. ISMCTS
(Cowling, Powley & Whitehouse 2012) is the known next step.

EVALUATION. Flat: 0.5 for any position the search does not see the end
of, so values come from terminal positions alone. No learned weights and
no hand-written features are read, which is what keeps V6 a player that
needs nothing but the rules, and it shares nothing with the approved
Royal Chess or m,n,k builds.
"""

import collections
import copy as _copy
import itertools
import random as _random

from lgref.experiments.gdl import GdlGame


Particle = collections.namedtuple('Particle', ('state', 'history', 'weight'))

#: rules text -> memo of resolver answers; see `_sample_class`.
_MEMOS = {}


def _ggp_class():
    import os
    import sys

    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    source = os.path.join(here, 'src')
    if source not in sys.path:
        sys.path.insert(0, source)
    from ggp.game import GGPGame

    return GGPGame


def _flat(_engine, _perspective):
    return 0.5


def _sample_class():
    """`GGPGame` with its answers memoised by state, for V6's own samples.

    MEASURED FIRST. Profiling four V6 games: `is_terminal` was 55% of
    the time and the resolver 78%, because the search asks the same
    state the same question several times per node and many samples
    share states. In GDL-II every one of these answers is a function of
    the state and the moves alone, so a memo keyed on them returns what
    the resolver would. A copy shares the rules and the memo -- nothing
    in a step writes to either -- and copies only what a step changes.

    Used only on the player's private samples, never on the host's
    game. GDL-III is excluded by the caller: there `knows` reads the
    history, which this key does not hold.
    """
    base = _ggp_class()

    class Sample(base):

        def __deepcopy__(self, _memo):
            clone = _copy.copy(self)
            clone.state = set(self.state)
            clone.repetition_history = dict(self.repetition_history)
            return clone

        def _remember(self, key, compute):
            cache = self._cache
            if key not in cache:
                if len(cache) > 500000:
                    cache.clear()
                cache[key] = compute()
            return cache[key]

        def is_terminal(self):
            return self._remember(('terminal', frozenset(self.state)),
                                  lambda: base.is_terminal(self))

        def goal(self, player):
            return self._remember(('goal', frozenset(self.state), player),
                                  lambda: base.goal(self, player))

        def _raw_legal_moves(self, player):
            return list(self._remember(
                ('legal', frozenset(self.state), player),
                lambda: tuple(base._raw_legal_moves(self, player))))

        def percepts(self, player, moves):
            return self._remember(
                ('sees', frozenset(self.state), player,
                 frozenset(moves.items())),
                lambda: base.percepts(self, player, moves))

        def step(self, moves):
            after = self._remember(
                ('next', frozenset(self.state), frozenset(moves.items())),
                lambda: self._successor(moves))
            self.state = set(after)
            key = self.repetition_key()
            self.repetition_history[key] = \
                self.repetition_history.get(key, 0) + 1

        def _successor(self, moves):
            probe = _copy.copy(self)
            probe.repetition_history = {}
            base.step(probe, moves)
            return frozenset(probe.state)

    return Sample


class UniformPlayer(object):
    """V0 on the view: a uniform choice among the role's legal moves.

    The same distribution as `RandomGGPPlayer`, which V0.1 is, but
    handed the view instead of the game.
    """

    def __init__(self, role, seed=None):
        self.role = role
        self._rng = _random.Random(seed)

    def choose(self, view):
        return self._rng.choice(view.legal) if view.legal else None


class DeterminizedPlayer(object):
    """V6.0. See the module docstring.

    `rules` is the GDL text, `role` this player's role. `particles` is
    the size of the belief, `depth` the fixed search depth per sample.
    """

    #: Population sizes tried, as multiples of `particles`, when every
    #: particle has been ruled out and the belief is rebuilt from the
    #: start of the game.
    REBUILD = (4, 16, 64)

    def __init__(self, rules, role, particles=16, depth=2, seed=None):
        self.role = role
        self.size = particles
        self.depth = depth
        self._rng = _random.Random(seed)
        plain = _ggp_class()(rules)
        self._gdl3 = plain.dialect == 'GDL-III'
        if self._gdl3:
            self._template = plain
        else:
            self._template = _sample_class()(rules)
            # ONE MEMO PER RULE TEXT, shared by every player of that
            # game: its entries are functions of the rules and the state
            # alone, so a second player or a second game reuses them.
            self._template._cache = _MEMOS.setdefault(rules, {})
        self.roles = [str(r) for r in self._template.roles]
        self._initial = frozenset(self._template.state)
        self.reset()
        #: Diagnostics of the last decision.
        self.last_values = {}
        self.rebuilds = 0

    def reset(self):
        self._particles = [Particle(self._initial, (), 1.0)]
        self._seen = 0

    # ---- deciding --------------------------------------------------

    def choose(self, view):
        if view.role != self.role:
            raise ValueError('a view for {0!r} handed to {1!r}'.format(
                view.role, self.role))
        if len(view.steps) < self._seen:
            self.reset()                       # a new game
        self._observe(view.steps)
        moves = self._legal()
        if not moves:
            return None
        if len(moves) == 1:
            self.last_values = {moves[0]: None}
            return moves[0]
        total = collections.defaultdict(float)
        mass = 0.0
        searched = {}
        for particle in self._particles:
            key = (particle.state, particle.history if self._gdl3 else None)
            if key not in searched:
                searched[key] = self._values(particle, moves)
            for move, value in searched[key].items():
                total[move] += particle.weight * value
            mass += particle.weight
        self.last_values = dict((move, total[move] / mass)
                                for move in moves)
        best = max(self.last_values.values())
        tied = [move for move in moves
                if self.last_values[move] >= best - 1e-12]
        return self._rng.choice(tied)

    def _legal(self):
        """This role's legal moves, read from the belief.

        In a well-formed GDL-II game they are the same in every
        consistent state. The intersection is taken so that a
        description which is not well-formed can only make the player
        more cautious, never make it offer a move the truth forbids.
        """
        common = None
        for particle in self._particles:
            game = self._at(particle)
            found = set(game.legal_moves(self.role))
            common = found if common is None else common & found
        return sorted(common or (), key=repr)

    def _values(self, particle, moves):
        """Each move's value to this role, searching the sample as if it
        were the truth, with the shared alpha-beta `Searcher`."""
        from lgref.experiments.search import Searcher

        searcher = Searcher(_flat, max_depth=self.depth, quiescence=0,
                            use_tt=False)
        # WHAT `choose_turn` WOULD DETECT on this engine, set here
        # because the root is walked below rather than by
        # `choose_turn`: a GDL game has no board to make/unmake on, and
        # its turns are not captures, so futility has no premise.
        searcher.can_undo = False
        searcher.has_tactics = False
        root = GdlGame(self._at(particle), seed=self._rng.random())
        # A sample is searched as perfect information, so the views the
        # host keeps for its players are not kept here: they would cost
        # two percept queries per node and be read by nothing.
        root._views = None
        values = {}
        for move in moves:
            child = root.copy()
            child.execute_turn((self.role, move))
            if child.is_game_over():
                winner = child.winner
                values[move] = (0.5 if winner is None
                                else 1.0 if winner == self.role else 0.0)
                continue
            # The negamax convention: `_search` answers for the child's
            # own mover. ONE FULL WINDOW PER MOVE, because a value is
            # wanted for every move and not just the best.
            value = searcher._search(child, self.depth - 1, 0.0, 1.0,
                                     self.role)
            values[move] = (value if child.current_player == self.role
                            else 1.0 - value)
        return values

    # ---- belief ----------------------------------------------------

    def _at(self, particle):
        """A game standing on a particle. The rules are shared, not
        copied: nothing in a step writes to them."""
        game = _copy.copy(self._template)
        game.state = set(particle.state)
        if self._gdl3:
            game.history = particle.history
        game.reset_repetition_history()
        return game

    def _observe(self, steps):
        new = steps[self._seen:]
        if not new:
            return
        survivors = self._filter(self._particles, new)
        if not survivors:
            # EVERY PARTICLE RULED OUT. The truth is consistent with the
            # view and has positive probability under the prior, so a
            # large enough population finds it; rebuild from the start.
            self.rebuilds += 1
            for factor in self.REBUILD:
                survivors = self._filter(
                    [Particle(self._initial, (), 1.0)], steps,
                    population=factor * self.size)
                if survivors:
                    break
        if not survivors:
            raise RuntimeError(
                'no play sequence consistent with {0!r}\'s view was '
                'found'.format(self.role))
        self._particles = survivors
        self._seen = len(steps)

    def _filter(self, particles, steps, population=None):
        population = population or self.size
        for step in steps:
            grown = []
            for particle in particles:
                grown.extend(self._extend(particle, step))
            if not grown:
                return []
            # EXACT WHILE IT FITS. Every consistent continuation is kept
            # with its own weight, so while the belief holds at most
            # `population` histories it IS the posterior, not a sample of
            # it. Only past that is it resampled. Measured on Monty Hall
            # before this: drawing one continuation per particle left 16
            # particles' share of the car's door to chance, V6 stayed
            # when the share fell to a half, and it won 59.8% where
            # always switching wins 66.7%.
            if len(grown) > population:
                particles = self._resample(grown, population)
            else:
                mass = sum(p.weight for p in grown)
                particles = [Particle(p.state, p.history,
                                      p.weight * len(grown) / mass)
                             for p in grown]
        if len(particles) > self.size:
            particles = self._resample(particles, self.size)
        return particles

    def _extend(self, particle, step):
        """Every continuation of `particle` the view allows, weighted.

        This role's move is the one it made. Every other role's joint
        move is one that would have produced the percepts it saw and
        left the game live, and each carries weight 1/(number of joint
        moves): the chance of that move under the uniform prior. Empty
        if the view rules the particle out.
        """
        own_move, own_percepts = step
        game = self._at(particle)
        if game.is_terminal():
            return []
        if own_move not in game.legal_moves(self.role):
            return []
        others = [role for role in self.roles if role != self.role]
        options = [sorted(game.legal_moves(role), key=repr)
                   for role in others]
        if not all(options):
            return []
        consistent = []
        total = 0
        for chosen in itertools.product(*options):
            total += 1
            moves = dict(zip(others, chosen))
            moves[self.role] = own_move
            if game.percepts(self.role, moves) == own_percepts:
                consistent.append(moves)
        out = []
        for moves in consistent:
            child = self._at(particle)
            child.step(moves)
            if child.is_terminal():
                # THE GAME NOT HAVING ENDED IS SEEN TOO. A view is only
                # ever asked for while the game is live, so every step
                # in it led to a live position. Checked here rather than
                # at the next step: measured on Krieg-TicTacToe, a
                # belief that learned it a step late was mostly samples
                # where the hidden marks had already made a line, and it
                # died out entirely late in a game.
                continue
            joint = tuple((role, moves[role]) for role in self.roles)
            out.append(Particle(frozenset(child.state),
                                particle.history + (joint,),
                                particle.weight / float(total)))
        return out

    def _resample(self, particles, size):
        """Systematic resampling to `size` equally weighted particles."""
        weights = [p.weight for p in particles]
        mass = sum(weights)
        step = mass / size
        mark = self._rng.random() * step
        out, running, index = [], weights[0], 0
        for _ in range(size):
            while mark > running and index < len(particles) - 1:
                index += 1
                running += weights[index]
            chosen = particles[index]
            out.append(Particle(chosen.state, chosen.history, 1.0))
            mark += step
        return out


# ---- the host ------------------------------------------------------

def play(game, players):
    """Play one GDL-II game to the end; `players` maps role -> player.

    The host is the only thing that touches the game. A player is asked
    only when its role is to move, and is handed only its `View`.
    Nature is drawn by the game itself. Returns `{role: goal}`, or None
    for a game the turn cap stopped, which is a truncation and not a
    result.
    """
    while not game.is_game_over():
        mover = game.current_player
        if mover == game.nature:
            game.execute_turn(game.nature_turn())
            continue
        move = players[mover].choose(game.view(mover))
        game.execute_turn((mover, move))
    if not game.ggp.is_terminal():
        return None
    return dict((role, game.ggp.goal(role)) for role in players)


def match(path, make_a, make_b, games, seed=0, max_turns=200):
    """A seat-balanced match of `make_a` against `make_b` on a GDL file.

    `make_x(rules, role, seed)` builds a player. Game i seats A in role
    `i % 2` of the two non-nature roles, so A takes each seat equally
    often, with the same game seeds. Returns per-seat W/D/L for A,
    the truncation count, and A's score (wins + draws/2) over the games
    that finished.
    """
    from lgref.experiments.gdl import load

    with open(path) as handle:
        rules = handle.read()
    record = {'W': 0, 'D': 0, 'L': 0, 'truncated': 0,
              'seats': collections.defaultdict(
                  lambda: {'W': 0, 'D': 0, 'L': 0})}
    for index in range(games):
        game = load(path, max_turns=max_turns, seed=seed + index)
        seats = [role for role in game.roles if role != game.nature]
        mine = seats[index % 2]
        players = {}
        for offset, role in enumerate(seats):
            make = make_a if role == mine else make_b
            players[role] = make(rules, role, seed * 7919 + index * 31
                                 + offset)
        goals = play(game, players)
        if goals is None:
            record['truncated'] += 1
            continue
        theirs = [goals[role] for role in seats if role != mine]
        best = max(theirs) if theirs else 0
        outcome = ('W' if goals[mine] > best
                   else 'L' if goals[mine] < best else 'D')
        record[outcome] += 1
        record['seats'][mine][outcome] += 1
    played = record['W'] + record['D'] + record['L']
    record['score'] = ((record['W'] + 0.5 * record['D']) / played
                       if played else None)
    record['seats'] = dict(record['seats'])
    return record


def win_rate(path, make, games, seed=0, max_turns=200):
    """A one-player game against nature: `make`'s wins over `games`.

    Game i is drawn with seed `seed + i`, and the player is built with
    seed i. Returns (wins, finished games)."""
    from lgref.experiments.gdl import load

    with open(path) as handle:
        rules = handle.read()
    wins = finished = 0
    for index in range(games):
        game = load(path, max_turns=max_turns, seed=seed + index)
        (role,) = [r for r in game.roles if r != game.nature]
        goals = play(game, {role: make(rules, role, index)})
        if goals is None:
            continue
        finished += 1
        wins += goals[role] == 100
    return wins, finished


PLAYERS = {
    'v0': lambda rules, role, seed: UniformPlayer(role, seed=seed),
    'v6': lambda rules, role, seed: DeterminizedPlayer(rules, role,
                                                       seed=seed),
}


def main(argv=None):
    """`python -m lgref.experiments.hidden GDL A [B] GAMES SEED`.

    With two players, a seat-balanced match of A against B. With one,
    its win rate against nature. A and B are `v0` or `v6`. This is the
    command behind the imperfect-information cells of
    `docs/experiments/version-win-rates.md`.
    """
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    path, games, seed = args[0], int(args[-2]), int(args[-1])
    names = args[1:-2]
    if len(names) == 2:
        print(match(path, PLAYERS[names[0]], PLAYERS[names[1]], games,
                    seed=seed))
    else:
        print(win_rate(path, PLAYERS[names[0]], games, seed=seed))


if __name__ == '__main__':
    main()
