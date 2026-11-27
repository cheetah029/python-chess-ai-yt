"""One player version, run inside a checkout of ITS OWN commit (#282).

`versions.py` hosts a match; this file is the other end of the pipe.
It is started as

    python version_worker.py ROOT

where ROOT is a checkout of the commit the version was built at. Every
import below resolves inside ROOT, so the player that answers is that
commit's player, with that commit's search, weights and engine -- not
today's code wearing an old name. This file itself must therefore use
only the standard library and APIs that exist at every representative
commit; each builder says which commit it was written against.

THE WORKER KEEPS ITS OWN GAME. The host sends every move that is
played, by either side and in the random opening, as a DESCRIPTION
(plain data, never an object), and the worker replays it on its own
copy. When asked, it describes the move its player chose. A description
the worker cannot resolve is reported, not guessed at: the host then
counts the game as diverged (two commits disagreeing about the rules),
keeps it out of the score, and records it.

Protocol, one JSON object per line in each direction:

    {"op": "new", "version": "v4", "game": "mnk", "args": {...},
     "seed": 7}                                  -> {"ok": true}
    {"op": "play", "move": D}                    -> {"ok": true}
                                                 or {"error": "..."}
    {"op": "go"}                                 -> {"move": D, "secs": s}
    {"op": "quit"}

Descriptions: an int cell index for m,n,k; `repr` of the move term for
a GDL game; `repr(mcts.describe(turn))` for Royal Chess.
"""

import json
import os
import random
import sys
import time

#: The checkout whose code answers. Set by `enter`; the host imports
#: this module for its game adapters with ROOT left as today's tree.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

#: No clock. `float('inf')` rather than None, because the Searcher at
#: 70c2044 computes `time.time() + self.budget` unconditionally.
NO_CLOCK = float('inf')

#: No ply cap, for an engine that compares `turn_number >= max_turns`
#: (None would raise). Far beyond any game that ends by the rules.
NO_CAP = 10 ** 12

#: Trained weights are written here and nowhere else: inside the
#: checkout of the commit that trained them, so two commits with the
#: same feature names can never read each other's builds.
CACHE = os.path.join(ROOT, '.version-cache')


def enter(root):
    """Make `root` the only tree imports can come from.

    The script's own directory is `sys.path[0]` and holds TODAY's
    modules, which must never answer for an old commit, so it is
    replaced rather than prepended to."""
    global ROOT, CACHE
    ROOT = os.path.abspath(root)
    CACHE = os.path.join(ROOT, '.version-cache')
    sys.path[:1] = [ROOT, os.path.join(ROOT, 'src')]
    os.chdir(ROOT)


#: Built once per process. A game is a `new`, and retraining per game
#: would cost seconds a game for the same deterministic weights.
_MEMO = {}


# ---- games --------------------------------------------------------------

class RoyalAdapter(object):
    """The case study on ROOT's own engine."""

    def __init__(self, args):
        from experiments.variants import make_engine
        from lgref.experiments.mcts import describe
        self._describe = describe
        cap = args.get('cap', 1000)
        self.engine = make_engine('full',
                                  max_turns=NO_CAP if cap is None else cap)

    def native(self):
        return self.engine

    def describe(self, turn):
        return repr(self._describe(turn))

    def legal(self):
        return self.engine.get_all_legal_turns()

    def resolve(self, description):
        for turn in self.legal():
            if self.describe(turn) == description:
                return turn
        return None

    def apply(self, turn):
        self.engine.execute_turn(turn)


class MnkAdapter(object):
    """m,n,k on ROOT's `MNK`; a move is a cell index."""

    def __init__(self, args):
        from lgref.experiments.mnk import MNK
        self.engine = MNK(m=args['m'], n=args['n'], k=args['k'])

    def native(self):
        return self.engine

    def describe(self, turn):
        return int(turn)

    def legal(self):
        return self.engine.get_all_legal_turns()

    def resolve(self, description):
        return description if description in self.legal() else None

    def apply(self, turn):
        self.engine.execute_turn(turn)


class GdlAdapter(object):
    """A GDL game on ROOT's interpreter; a move is `repr` of its term."""

    def __init__(self, args):
        from lgref.experiments.gdl import load
        self.engine = load(args['path'], max_turns=args.get('cap'))

    def native(self):
        return self.engine

    def describe(self, turn):
        return repr(turn[1])

    def legal(self):
        return self.engine.get_all_legal_turns()

    def resolve(self, description):
        for turn in self.legal():
            if self.describe(turn) == description:
                return turn
        return None

    def apply(self, turn):
        self.engine.execute_turn(turn)


class MnkAsGdl(GdlAdapter):
    """m,n,k played through a GDL description, for a player (V5) that
    reads only the rules. The wire still speaks the host's cell index;
    cell `i` is `mark(i // n + 1, i % n + 1)`, row-major from 1. Any
    bijection that maps lines to lines is correct, and this one does,
    because both number rows and columns the same way."""

    def __init__(self, args):
        GdlAdapter.__init__(self, {'path': args['gdl'],
                                   'cap': args.get('cap')})
        self.n = args['n']

    def describe(self, turn):
        term = repr(turn[1])
        digits = [int(part) for part in
                  term.replace('(', ' ').replace(')', ' ')
                  .replace(',', ' ').replace("'", ' ').split()
                  if part.isdigit()]
        row, col = digits[-2], digits[-1]
        return (row - 1) * self.n + (col - 1)

    def resolve(self, description):
        for turn in self.legal():
            if self.describe(turn) == description:
                return turn
        return None


GAMES = {'royal': RoyalAdapter, 'mnk': MnkAdapter, 'gdl': GdlAdapter,
         'mnk-gdl': MnkAsGdl}


# ---- players -------------------------------------------------------------
#
# Each returns `choose(adapter) -> native turn`. The configuration of
# each is the representative's, as `docs/agent-versions.md` and
# `docs/experiments/version-win-rates.md` record it.

def build_v0(adapter, args, seed):
    """V0.1: uniform over the legal turns."""
    rng = random.Random(seed)
    return lambda a: rng.choice(a.legal())


def build_v1(adapter, args, seed):
    """V1.4 (96dfbd8): `mcts.MCTSPlayer`, capture-preferring rollouts,
    `args['sims']` simulations, rollout cap 200 (its default)."""
    from lgref.experiments.mcts import MCTSPlayer
    player = MCTSPlayer(n_simulations=args['sims'], rng=random.Random(seed))
    return lambda a: player.choose_turn(a.legal(), a.native())


def build_v2(adapter, args, seed):
    """V2.2 (dcee4b4): `generic.GenericPlayer` over `make_evaluation()`
    with no extractor -- the protocol-only, declared-condition
    evaluation -- at depth 2, quiescence 2 (its defaults)."""
    from lgref.experiments.generic import GenericPlayer, make_evaluation
    player = GenericPlayer(make_evaluation(), depth=2, quiescence=2,
                           rng=random.Random(seed))
    return lambda a: player.choose_turn(a.legal(), a.native())


def _mnk_brain(args):
    """`play_mnk.Brain` as the window builds it (rounds 6, games 60,
    seed 17), with no training clock so the weights cannot depend on
    the machine's load."""
    key = ('brain', args['m'], args['n'], args['k'], args['depth'])
    if key not in _MEMO:
        sys.path.insert(0, os.path.join(ROOT, 'lgref'))
        import play_mnk
        play_mnk.Brain.WRITE_DIR = CACHE
        brain = play_mnk.Brain(6, 60, 17, False, args['depth'],
                               train_budget=None)
        _MEMO[key] = (play_mnk, brain.evaluation(args['m'], args['n'],
                                                 args['k']))
    return _MEMO[key]


def build_v3(adapter, args, seed):
    """V3.1 (76634da) on Royal Chess: the window's `td` agent at that
    commit, `load_player(td_royal_chess.json, with_mobility(royal_chess))`,
    one ply. On m,n,k: today's one-ply player over today's weights,
    `play_mnk --o td1`, the run path `agent-versions.md` names."""
    rng = random.Random(seed)
    if args['game'] == 'royal':
        from lgref.experiments.bootstrap import load_player
        from lgref.experiments.features import royal_chess, with_mobility
        player = load_player(os.path.join(ROOT, 'lgref', 'weights',
                                          'td_royal_chess.json'),
                             with_mobility(royal_chess), rng=rng)
        return lambda a: player.choose_turn(a.legal(), a.native())
    play_mnk, evaluate = _mnk_brain(args)
    choose = play_mnk.make_player('td1', evaluate, args['depth'], rng)
    return lambda a: choose(a.native())


def build_v4(adapter, args, seed):
    """V4.15 (6307d97). Royal Chess: the window's `td` agent,
    `load_royal_chess_searcher(td_royal_chess.json, max_depth=3)`. m,n,k:
    `play_mnk --o td` at `affordable_depth`."""
    if args['game'] == 'royal':
        from lgref.experiments.features import load_royal_chess_searcher
        searcher = load_royal_chess_searcher(
            os.path.join(ROOT, 'lgref', 'weights', 'td_royal_chess.json'),
            max_depth=args['depth'])
        return lambda a: searcher.choose_turn(a.legal(), a.native())
    play_mnk, evaluate = _mnk_brain(args)
    choose = play_mnk.make_player('td', evaluate, args['depth'],
                                  random.Random(seed))
    return lambda a: choose(a.native())


def build_v5(adapter, args, seed):
    """V5.1 (70c2044): features named from the GDL, trained from zero by
    `bootstrap.run` as `test_unseen_gdl._train_and_race` trains them
    (4 rounds of 30 games, alpha 0.08, epsilon 0.3, seed 11), searched by
    `Searcher(quiescence=0, use_tt=False)` at a fixed depth. Training is
    deterministic, so its weights are cached under `CACHE`."""
    from lgref.experiments.bootstrap import normalise, run, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.gdl import features, load
    from lgref.experiments.search import Searcher

    path = args.get('gdl') or args['path']
    cap = args.get('train_cap', 40)
    cache = os.path.join(CACHE, 'v5_{0}_cap{1}.json'.format(
        os.path.basename(path), cap))
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    if cache in _MEMO:
        weights, scales = _MEMO[cache]
    elif os.path.exists(cache):
        with open(cache) as handle:
            stored = json.load(handle)
        weights, scales = stored['weights'], stored['scales']
    else:
        def make(_variant='full', max_turns=None):
            return load(path, max_turns=max_turns or cap)
        scales = {}
        history = run(make, features, rounds=4, games_per_round=30,
                      alpha=0.08, epsilon=0.3, seed=11, max_turns=cap,
                      scales=scales)
        weights = history[-1].weights
        temporary = '{0}.{1}.tmp'.format(cache, os.getpid())
        with open(temporary, 'w') as handle:
            json.dump({'weights': weights, 'scales': scales}, handle)
        os.replace(temporary, cache)
    _MEMO[cache] = (weights, scales)

    def evaluate(game, perspective):
        return value(weights, normalise(
            differentials(features(game), perspective), dict(scales),
            update=False))

    depth = args['depth']

    def choose(a):
        searcher = Searcher(evaluate, max_depth=depth, budget=NO_CLOCK,
                            quiescence=0, use_tt=False)
        return searcher.choose_turn(a.legal(), a.native())
    return choose


def build_v7(adapter, args, seed):
    """V7: the V4 player one ply deeper, everything else unchanged --
    the same construction as `build_v4`, run at V7's own commit with the
    depth `versions.player_args` gives it (Royal Chess 4, quiescence 2;
    m,n,k `DEPTH_BY_CELLS` + 1)."""
    return build_v4(adapter, args, seed)


BUILDERS = {'v0': build_v0, 'v1': build_v1, 'v2': build_v2,
            'v3': build_v3, 'v4': build_v4, 'v5': build_v5,
            'v7': build_v7}


def activate_compiled():
    """Load the commit's compiled hot modules, if it has any built.

    Only a commit with `src/compiled.py` (#362, d244ba4 and later) can,
    and `compiled.activate` loads a module compiled only while its source
    is unchanged, so a commit without a build runs as pure Python. The
    names that loaded compiled are returned and logged with each game."""
    if not os.path.exists(os.path.join(ROOT, 'src', 'compiled.py')):
        return []
    import compiled
    compiled.activate()
    return sorted(compiled.fresh_modules())


def main():
    enter(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
    compiled = activate_compiled()
    adapter = choose = None
    for line in sys.stdin:
        request = json.loads(line)
        op = request['op']
        reply = {'ok': True}
        try:
            if op == 'new':
                args = dict(request.get('args', {}))
                args['game'] = request['game']
                adapter = GAMES[request['game']](args)
                choose = BUILDERS[request['version']](adapter, args,
                                                      request['seed'])
                if compiled:
                    reply['compiled'] = compiled
            elif op == 'play':
                move = request['move']
                turn = adapter.resolve(move)
                if turn is None:
                    reply = {'error': 'cannot resolve {0!r}'.format(move)}
                else:
                    adapter.apply(turn)
            elif op == 'go':
                started = time.time()
                turn = choose(adapter)
                reply = {'move': adapter.describe(turn),
                         'secs': time.time() - started}
            elif op == 'quit':
                break
        except Exception as error:  # reported to the host, never hidden
            reply = {'error': '{0}: {1}'.format(type(error).__name__,
                                                error)}
        sys.stdout.write(json.dumps(reply) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
