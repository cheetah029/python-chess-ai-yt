"""Seat-balanced matches between player VERSIONS, each at its own commit.

The runner behind the perfect-information cells of
`docs/experiments/version-win-rates.md` (#282). Each side of a match is
a `version_worker.py` process started inside a checkout of that
version's commit, so V4 is V4.15's own code and weights, not today's
code with an old label. This process is the HOST: it keeps the game on
today's engine, which is the referee, and tells both workers every move.

    python -m lgref.experiments.versions play GAME A@ROOT B@ROOT \\
        GAMES SEED --log FILE [--first I]
    python -m lgref.experiments.versions summary FILE...

GAME is `royal`, `mnk:M,N,K` or `nim`. A and B are `v0`..`v5`.

WHAT ONE CELL MEANS is the doc's protocol, implemented here:

  * SEATS ALTERNATE. Game `i` seats A in the first role when `i` is
    even. Games `2j` and `2j+1` start from the SAME opening, so every
    opening is played once from each side.
  * A RANDOM OPENING PER PAIR. Most of these players are deterministic,
    so without one every game in a seat is the same game: a 400-game
    cell would be two games repeated. The opening is a few uniformly
    random plies (`OPENING_PLIES`) drawn from the pair's seed, the same
    device `tools/race_agents.py` uses. Both sides play it as given.
  * FIXED DEPTH, NEVER A CLOCK (`PLAYED`).
  * TRUNCATED and DIVERGED games are kept out of the score and counted.
    Diverged means the two commits disagreed about a move's legality,
    which happens only where the rules were fixed between them.

Each game is one JSON line in the log, appended as it finishes, so a run
can be split across processes (`--first`) and resumed: indices already
in the log are skipped.
"""

import json
import math
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = os.path.dirname(os.path.dirname(HERE))
WORKER = os.path.join(HERE, 'version_worker.py')

#: Uniformly random plies before the versions take over, per game.
#: Royal Chess's range is `race_agents.py`'s. m,n,k's is small enough
#: that the opening rarely decides the game, and long enough to give a
#: deterministic pair many distinct games.
OPENING_PLIES = {'royal': (4, 14), 'mnk:3,3,3': (0, 2),
                 'mnk:5,5,4': (0, 4), 'mnk:13,13,5': (0, 6), 'nim': (0, 1)}

#: `VERSIONS_VERBOSE=1` prints every searched move's cost to stderr, for
#: measuring a player too slow to finish a game in a pilot.
VERBOSE = os.environ.get('VERSIONS_VERBOSE') == '1'

#: The game's own ply cap. Royal Chess's is the engine's default; m,n,k
#: and nim end by themselves well before theirs.
CAP = {'royal': 1000, 'nim': 60}


def mnk_depth(m, n):
    """`play_mnk.DEPTH_BY_CELLS`: depth 3 up to 200 cells, else 2."""
    return 3 if m * n <= 200 else 2


#: How each version plays each kind of game. One table, so a cell's
#: settings are a lookup and not a choice made at the command line.
#: V1's 200 simulations are the budget its recorded evidence used
#: (`agent-versions.md`, V1.1 and V1.4: "MCTS-200").
V1_SIMULATIONS = 200


def player_args(version, game):
    """The worker's `args` for `version` on `game`."""
    args = {}
    if game == 'royal':
        args['cap'] = CAP['royal']
        if version == 'v4':
            args['depth'] = 3          # `Game.TD_DEPTH`
    elif game.startswith('mnk:'):
        m, n, k = (int(part) for part in game[4:].split(','))
        args.update(m=m, n=n, k=k, depth=mnk_depth(m, n))
    elif game == 'nim':
        args.update(path=os.path.join(TODAY, 'lgref', 'identify',
                                      'testgames', 'nim.gdl'),
                    cap=CAP['nim'])
        if version == 'v5':
            args['depth'] = 4          # V5.0's measured setting
    if version == 'v1':
        args['sims'] = V1_SIMULATIONS
    return args


def worker_game(version, game):
    """Which adapter the worker plays `game` through."""
    if game == 'royal':
        return 'royal'
    if game == 'nim':
        return 'gdl'
    if version == 'v5':
        return 'mnk-gdl'           # V5 reads only rules
    return 'mnk'


def host_game(game):
    """Today's game, as an adapter from `version_worker`."""
    for entry in (os.path.join(TODAY, 'src'), TODAY):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from lgref.experiments import version_worker as vw
    args = player_args('v0', game)
    kind = worker_game('v0', game)
    return vw.GAMES[kind](args)


#: Plain m,n,k in infix GDL, for V5, which plays only from rules.
#: Krieg-m,n,k's generator with the hidden information taken out: the
#: same lines, written one rule per line, and `tictactoe.gdl`'s moves.
MNK_RULES = """\
legal(P,mark(M,N)) :- true(control(P)) & true(cell(M,N,b))
legal(xplayer,noop) :- true(control(oplayer))
legal(oplayer,noop) :- true(control(xplayer))
next(cell(M,N,S)) :- does(P,mark(M,N)) & symbol(P,S)
next(cell(M,N,W)) :- true(cell(M,N,W)) & distinct(W,b)
next(cell(M,N,b)) :- true(cell(M,N,b)) & ~marked(M,N)
marked(M,N) :- does(P,mark(M,N))
next(control(xplayer)) :- true(control(oplayer))
next(control(oplayer)) :- true(control(xplayer))
open :- true(cell(M,N,b))
terminal :- line(x)
terminal :- line(o)
terminal :- ~open
goal(xplayer,100) :- line(x)
goal(xplayer,0) :- line(o)
goal(xplayer,50) :- ~line(x) & ~line(o)
goal(oplayer,100) :- line(o)
goal(oplayer,0) :- line(x)
goal(oplayer,50) :- ~line(x) & ~line(o)
"""


def mnk_gdl_text(m, n, k):
    """The infix GDL of m,n,k: m rows, n columns, k in a row wins."""
    from lgref.identify.testgames.kriegmnk import lines
    parts = ['% m,n,k {0},{1},{2}, generated by '
             'lgref/experiments/versions.py\n'.format(m, n, k),
             'role(xplayer)\nrole(oplayer)\n',
             'symbol(xplayer,x)\nsymbol(oplayer,o)\n',
             ''.join('init(cell({0},{1},b))\n'.format(r, c)
                     for r in range(1, m + 1) for c in range(1, n + 1)),
             'init(control(xplayer))\n', MNK_RULES]
    for cells in lines(m, n, k):
        body = ' & '.join('true(cell({0},{1},W))'.format(r, c)
                          for r, c in cells)
        parts.append('line(W) :- {0} & distinct(W,b)\n'.format(body))
    return ''.join(parts)


def mnk_gdl(m, n, k):
    """A path to that GDL, written once under today's `.version-cache`."""
    folder = os.path.join(TODAY, '.version-cache')
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, 'mnk_{0}_{1}_{2}.gdl'.format(m, n, k))
    text = mnk_gdl_text(m, n, k)
    if not os.path.exists(path) or open(path).read() != text:
        temporary = '{0}.{1}.tmp'.format(path, os.getpid())
        with open(temporary, 'w') as handle:
            handle.write(text)
        os.replace(temporary, path)
    return path


class Worker(object):
    """One version in its own process, at its own commit."""

    def __init__(self, version, root):
        self.version, self.root = version, os.path.abspath(root)
        python = os.path.join(self.root, '.venv', 'bin', 'python')
        if not os.path.exists(python):
            python = sys.executable
        env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUNBUFFERED='1')
        self.process = subprocess.Popen(
            [python, WORKER, self.root], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, cwd=self.root, env=env,
            universal_newlines=True, bufsize=1)

    def ask(self, **request):
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('worker {0} at {1} exited'.format(
                self.version, self.root))
        return json.loads(line)

    def new(self, game, seed):
        args = player_args(self.version, game)
        if self.version == 'v5' and game.startswith('mnk:'):
            args['gdl'] = mnk_gdl(args['m'], args['n'], args['k'])
            args['train_cap'] = args['m'] * args['n'] + 2
        self.args = args
        return self.ask(op='new', version=self.version,
                        game=worker_game(self.version, game), args=args,
                        seed=seed)

    def close(self):
        try:
            self.ask(op='quit')
        except Exception:
            pass
        self.process.wait()


def first_role(adapter):
    engine = adapter.native()
    return engine.current_player


def play_game(game, index, seed, worker_a, worker_b):
    """One game; returns its log record."""
    pair = index // 2
    host = host_game(game)
    lo, hi = OPENING_PLIES[game]
    opening_rng = random.Random(seed * 1000003 + pair)
    plies = opening_rng.randint(lo, hi)
    first = first_role(host)
    a_first = index % 2 == 0
    record = {'index': index, 'pair': pair, 'seed': seed, 'game': game,
              'a': worker_a.version, 'b': worker_b.version,
              'a_first': a_first, 'opening_moves': [], 'plies': 0,
              'a_secs': 0.0, 'b_secs': 0.0, 'a_max': 0.0, 'b_max': 0.0}
    for offset, worker in enumerate((worker_a, worker_b)):
        reply = worker.new(game, seed * 7919 + index * 31 + offset)
        if 'error' in reply:
            raise RuntimeError('{0}: {1}'.format(worker.version,
                                                 reply['error']))
    record['args_a'], record['args_b'] = worker_a.args, worker_b.args
    started = time.time()

    def broadcast(description):
        for worker in (worker_a, worker_b):
            reply = worker.ask(op='play', move=description)
            if 'error' in reply:
                return '{0} refused {1!r}: {2}'.format(
                    worker.version, description, reply['error'])
        return None

    problem = None
    engine = host.native()
    for _ply in range(plies):
        if engine.is_game_over():
            break
        legal = sorted(host.legal(), key=lambda t: repr(host.describe(t)))
        if not legal:
            break
        turn = opening_rng.choice(legal)
        description = host.describe(turn)
        host.apply(turn)
        record['opening_moves'].append(description)
        problem = broadcast(description)
        if problem:
            break
    while problem is None and not engine.is_game_over():
        if not host.legal():
            break
        mover = engine.current_player
        a_moves = (mover == first) == a_first
        worker, key = (worker_a, 'a') if a_moves else (worker_b, 'b')
        reply = worker.ask(op='go')
        if 'error' in reply:
            problem = '{0} failed to choose: {1}'.format(worker.version,
                                                         reply['error'])
            break
        if VERBOSE:
            sys.stderr.write('  ply {0}: {1} {2:.1f}s\n'.format(
                record['plies'] + 1, worker.version, reply['secs']))
            sys.stderr.flush()
        record[key + '_secs'] += reply['secs']
        record[key + '_max'] = max(record[key + '_max'], reply['secs'])
        turn = host.resolve(reply['move'])
        if turn is None:
            problem = '{0} chose {1!r}, illegal on today\'s engine'.format(
                worker.version, reply['move'])
            break
        host.apply(turn)
        record['plies'] += 1
        problem = broadcast(reply['move'])
    record['wall'] = time.time() - started
    if problem is not None:
        record['result'] = 'diverged'
        record['problem'] = problem
        return record
    record['result'] = outcome(game, engine, first, a_first)
    return record


def outcome(game, engine, first, a_first):
    """'A', 'B', 'draw' or 'truncated', from the host's referee."""
    if game == 'nim':
        if not engine.ggp.is_terminal():
            return 'truncated'
    elif game == 'royal':
        if engine.winner is None:
            return 'truncated'
    winner = engine.winner
    if winner is None:
        return 'draw'
    return 'A' if (winner == first) == a_first else 'B'


def done_indices(path):
    seen = set()
    if os.path.exists(path):
        with open(path) as handle:
            for line in handle:
                if line.strip():
                    seen.add(json.loads(line)['index'])
    return seen


def play(game, spec_a, spec_b, games, seed, log, first=0):
    """Play games `first .. first+games-1`, appending each to `log`."""
    version_a, root_a = spec_a.split('@', 1)
    version_b, root_b = spec_b.split('@', 1)
    done = done_indices(log)
    todo = [i for i in range(first, first + games) if i not in done]
    if not todo:
        return
    worker_a = Worker(version_a, root_a)
    worker_b = Worker(version_b, root_b)
    started = time.time()
    try:
        for count, index in enumerate(todo, 1):
            record = play_game(game, index, seed, worker_a, worker_b)
            record['root_a'], record['root_b'] = root_a, root_b
            with open(log, 'a') as handle:
                handle.write(json.dumps(record, sort_keys=True) + '\n')
            elapsed = time.time() - started
            print('{0} {1}v{2} game {3}: {4:9} {5:4d} plies  {6:6.1f}s  '
                  '[{7}/{8}, {9:.0f}s, ~{10:.0f}s left]'.format(
                      game, version_a, version_b, index, record['result'],
                      record['plies'], record['wall'], count, len(todo),
                      elapsed, elapsed / count * (len(todo) - count)),
                  flush=True)
    finally:
        worker_a.close()
        worker_b.close()


# ---- the cell ------------------------------------------------------------

def wilson(score, n, z=1.96):
    """The 95% Wilson interval for a proportion `score` over `n`."""
    if not n:
        return None
    centre = (score + z * z / (2 * n)) / (1 + z * z / n)
    half = (z * math.sqrt(score * (1 - score) / n + z * z / (4 * n * n))
            / (1 + z * z / n))
    return centre - half, centre + half


def summarise(records):
    """A's cell: W/D/L, score, interval and the per-seat scores."""
    tally = {'A': 0, 'draw': 0, 'B': 0, 'truncated': 0, 'diverged': 0}
    seats = {True: [0, 0, 0], False: [0, 0, 0]}
    for record in records:
        result = record['result']
        tally[result] += 1
        if result in ('A', 'draw', 'B'):
            seats[record['a_first']][('A', 'draw', 'B').index(result)] += 1
    n = tally['A'] + tally['draw'] + tally['B']
    score = (tally['A'] + 0.5 * tally['draw']) / n if n else None

    def seat(row):
        played = sum(row)
        return (row[0] + 0.5 * row[1]) / played if played else None
    return {'W': tally['A'], 'D': tally['draw'], 'L': tally['B'],
            'truncated': tally['truncated'],
            'diverged': tally['diverged'], 'n': n, 'score': score,
            'ci': wilson(score, n) if n else None,
            'first': seat(seats[True]), 'second': seat(seats[False]),
            'games': len(records)}


def cell_text(summary):
    """`71.5% [66.9, 75.7] n=400`, the doc's cell format."""
    if not summary['n']:
        return ''
    low, high = summary['ci']
    return '{0:.1f}% [{1:.1f}, {2:.1f}] n={3}'.format(
        100 * summary['score'], 100 * low, 100 * high, summary['n'])


def load_records(paths):
    records = {}
    for path in paths:
        with open(path) as handle:
            for line in handle:
                if line.strip():
                    record = json.loads(line)
                    records[record['index']] = record
    return [records[i] for i in sorted(records)]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == 'summary':
        summary = summarise(load_records(args[1:]))
        print(json.dumps(summary, sort_keys=True))
        print(cell_text(summary))
        return
    if not args or args[0] != 'play':
        raise SystemExit(__doc__)
    first = 0
    log = None
    rest = []
    iterator = iter(args[1:])
    for item in iterator:
        if item == '--first':
            first = int(next(iterator))
        elif item == '--log':
            log = next(iterator)
        else:
            rest.append(item)
    game, spec_a, spec_b, games, seed = rest
    play(game, spec_a, spec_b, int(games), int(seed), log, first=first)


if __name__ == '__main__':
    main()
