"""Is a benchmark description a well-formed game, and the game it says?

Two checks, both over the states actually reached:

  well-formed   in every non-terminal state every role has at least one
                legal move; in every terminal state no role has two
                goal values. A state that fails is a defect in the
                description, never an interesting property. A role
                with NO goal value is allowed: the older benchmark
                games give the loser none, and the engine reads that
                as 0.
  agrees        where a plain-Python implementation exists
                (`lgref.bench.simulators`), the GDL and the simulator
                give the same legal moves, successors, ending and
                payoffs in every visited state.

`walk` visits states exhaustively (breadth-first, up to a limit) or by
seeded random playouts, and says which it did, so a sample is never
reported as a census.

Run as a module for the full check of a pilot:

    python -m lgref.bench.wellformed othello4 --exhaustive
    python -m lgref.bench.wellformed breakthrough5 --games 2000
"""

import argparse
import collections
import random
import sys

from lgref.bench.catalog import game_path


def open_game(text):
    from ggp.game import GGPGame
    return GGPGame(text)


def at(game, state):
    """Point `game` at `state` and return it."""
    game.state = set(state)
    return game


def goal_values(game, role):
    """EVERY goal value the description gives `role` in the current
    state -- `GGPGame.goal` returns one, and two would be a defect."""
    if game._program is not None:
        return {int(f[2]) for f in game._ask(game._model(),
                                             ('goal', role, '?n'))}
    kb = game._state_kb()
    return {int(b['?n']) for b in game._resolver(kb).query(
        ('goal', role, '?n'))}


def successor(game, state, moves):
    at(game, state)
    game.step(moves)
    return frozenset(game.state)


def walk(text, exhaustive=False, limit=100000, games=200, seed=0,
         max_plies=200):
    """States of the game described by `text`, and how they were found.

    Returns (states, mode). Exhaustive mode stops at `limit` states and
    says so in `mode`, so a truncated census is never read as complete.
    """
    game = open_game(text)
    root = frozenset(game.state)
    if exhaustive:
        seen, order = {root}, [root]
        queue = collections.deque([root])
        while queue and len(seen) < limit:
            state = queue.popleft()
            at(game, state)
            if game.is_terminal():
                continue
            options = [game.legal_moves(r) or [None] for r in game.roles]
            if any(o == [None] for o in options):
                continue
            for joint in _product(options):
                child = successor(game, state, dict(zip(game.roles, joint)))
                if child not in seen:
                    seen.add(child)
                    order.append(child)
                    queue.append(child)
        mode = 'exhaustive' if not queue else 'truncated at {}'.format(limit)
        return order, mode
    seen, order = set(), []
    for index in range(games):
        rng = random.Random(seed * 100003 + index)  # nosec B311: play
        state = root
        for _ply in range(max_plies):
            if state not in seen:
                seen.add(state)
                order.append(state)
            at(game, state)
            if game.is_terminal():
                break
            joint = {}
            for role in game.roles:
                moves = game.legal_moves(role)
                if not moves:
                    break
                joint[role] = rng.choice(moves)
            if len(joint) < len(game.roles):
                break
            state = successor(game, state, joint)
    return order, '{} random games, seed {}'.format(games, seed)


def _product(options):
    import itertools
    return itertools.product(*options)


def check(text, states, simulator=None):
    """Problems found in `states`, as strings; empty means none."""
    game = open_game(text)
    problems = []
    for state in states:
        at(game, state)
        terminal = game.is_terminal()
        legal = {r: list(game.legal_moves(r)) for r in game.roles}
        if terminal:
            for role in game.roles:
                values = goal_values(at(game, state), role)
                if len(values) > 1:
                    problems.append('terminal state, {} has goal values '
                                    '{}: {}'.format(role, sorted(values),
                                                    _show(state)))
        else:
            for role, moves in legal.items():
                if not moves:
                    problems.append('non-terminal state, {} has no legal '
                                    'move: {}'.format(role, _show(state)))
        if simulator is None:
            continue
        if simulator.terminal(state) != terminal:
            problems.append('ending differs (gdl {}): {}'.format(
                terminal, _show(state)))
            continue
        if terminal:
            want = simulator.goals(state)
            for role in game.roles:
                got = goal_values(at(game, state), role)
                if got != want[role]:
                    problems.append('goal of {} differs (gdl {}, sim {}): '
                                    '{}'.format(role, sorted(got),
                                                sorted(want[role]),
                                                _show(state)))
            continue
        for role in game.roles:
            want = sorted(simulator.legal(state, role), key=repr)
            got = sorted(legal[role], key=repr)
            if got != want:
                problems.append('legal moves of {} differ: gdl {} sim {}: '
                                '{}'.format(role, got, want, _show(state)))
        for joint in _product([legal[r] for r in game.roles]):
            moves = dict(zip(game.roles, joint))
            got = successor(game, state, moves)
            want = simulator.next(state, moves)
            if got != want:
                problems.append('successor of {} differs: gdl-only {} '
                                'sim-only {}'.format(
                                    moves, sorted(got - want),
                                    sorted(want - got)))
    return problems


def _term(term):
    """A ground term in infix: ('cell', '2', ('h', '1', '1')) is
    cell(2,h(1,1)). Recursive, so nested terms format too (#372: the
    flat join raised TypeError on a fact such as drawn(h(1,1)))."""
    if isinstance(term, tuple):
        return '{}({})'.format(term[0], ','.join(_term(t) for t in term[1:]))
    return term


def _show(state):
    return ' '.join(sorted(_term(f) for f in state))


def main(argv=None):
    from lgref.bench.simulators import SIMULATORS

    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('game')
    parser.add_argument('--exhaustive', action='store_true')
    parser.add_argument('--limit', type=int, default=100000)
    parser.add_argument('--games', type=int, default=200)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args(argv)
    with open(game_path(args.game)) as handle:
        text = handle.read()
    states, mode = walk(text, exhaustive=args.exhaustive, limit=args.limit,
                        games=args.games, seed=args.seed)
    print('{}: {} states ({})'.format(args.game, len(states), mode),
          flush=True)
    factory = SIMULATORS.get(args.game)
    problems = check(text, states, factory() if factory else None)
    for line in problems[:20]:
        print('  ' + line)
    print('{} problems; simulator {}'.format(
        len(problems), 'compared' if factory else 'not available'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
