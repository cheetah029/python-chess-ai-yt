"""Exact reference effects for the Phase B benchmarks.

Phase B asks for "reference effects using an independent exact solver
where applicable", and the benchmarks are small enough that "exact" means
exhaustive: enumerate every reachable state and report the effect of each
rule ablation as a difference between two complete enumerations. No
sampling, no agent, no interval.

WHY THE PROPERTIES ARE COMPUTED AND NOT DECLARED. `corridor.gdl` claims a
redundant rule and an interacting pair. Both claims were WRONG the first
two times they were written:

  * the redundancy was stated against the wrong counterpart, and the
    first ablation deleted the guard's DEFINING statements instead of
    relaxing the guard -- which does not make a rule redundant, it makes
    the game unplayable (1 reachable state, no legal move);
  * the interaction produced a state with no legal move for the player in
    control, which is not an interesting interaction but a MALFORMED GDL
    game.

A benchmark whose advertised properties are not the properties it has is
worse than no benchmark, so `verify()` checks each one and the tests fail
if any stops holding.

HOW A RULE IS ABLATED. By RELAXING a body conjunct -- dropping `& inside(B)`
from the step rule -- not by deleting the statements that define `inside`.
Dropping a conjunct makes a rule easier to satisfy, so the game becomes
more permissive; deleting a guard's definition makes the rule impossible to
satisfy, so the game becomes empty. `lgref/ablate/operations.py` draws the
same distinction and this file follows it.
"""

import collections
import itertools
import os

HERE = os.path.dirname(os.path.abspath(__file__))

#: Each ablatable rule, as the exact body fragments to remove. Stated as
#: text because that is what makes the ablation auditable: the reader can
#: see precisely which conjunct goes.
ABLATIONS = {
    'corridor': {
        'boundary': (' & inside(B)', ' & inside(C)'),
        'blocking': (' & clear(P,B)', ' & clear(P,C)'),
        'no_double_double': (' & true(fresh(P))',),
    },
}

#: What each benchmark is built to exhibit, checked by `verify`.
CLAIMS = {
    'corridor': {
        'redundant': ('boundary',),
        'interacting': ('blocking', 'no_double_double'),
    },
}

Enumeration = collections.namedtuple(
    'Enumeration', 'states terminals stuck mean_branching wins')


def game_text(game, relax=()):
    """The benchmark's statements, with the named rules relaxed."""
    with open(os.path.join(HERE, game + '.gdl')) as handle:
        text = handle.read()
    for name in relax:
        for fragment in ABLATIONS[game][name]:
            if fragment not in text:
                raise KeyError(
                    'ablation {!r} of {!r} expects the fragment {!r}, which '
                    'is not in the file -- the game was edited and this '
                    'ablation no longer names anything'.format(
                        name, game, fragment))
            text = text.replace(fragment, '')
    return text


def enumerate_game(game, relax=(), limit=200000):
    """Every reachable state, exhaustively.

    Returns counts plus the mean branching factor of the player in
    control, which is the structural quantity the ablations move.
    """
    from ggp.game import GGPGame

    text = game_text(game, relax)
    root = GGPGame(text)
    seen = set()
    stuck = terminals = 0
    branching = []
    wins = collections.Counter()
    frontier = [root]
    while frontier and len(seen) < limit:
        current = frontier.pop()
        key = tuple(sorted(map(str, current.state)))
        if key in seen:
            continue
        seen.add(key)
        if current.is_terminal():
            terminals += 1
            for role in current.roles:
                if current.goal(role) == 100:
                    wins[role] += 1
            continue
        options = {}
        empty = False
        for role in current.roles:
            moves = current.legal_moves(role)
            if not moves:
                empty = True
            else:
                # Only the player with a choice contributes: the waiting
                # player always has exactly one move and would drag the
                # mean to 1.
                if len(moves) > 1:
                    branching.append(len(moves))
            options[role] = moves or ['wait']
        if empty:
            # A non-terminal state with no legal move for some player.
            # Malformed rather than interesting; counted so `verify` can
            # refuse it.
            stuck += 1
            continue
        for combination in itertools.product(
                *[options[r] for r in current.roles]):
            child = GGPGame(text)
            child.state = set(current.state)
            try:
                child.step(dict(zip(current.roles, combination)))
            except Exception:                      # noqa: BLE001
                continue
            frontier.append(child)
    mean = (sum(branching) / float(len(branching))) if branching else 0.0
    return Enumeration(len(seen), terminals, stuck, mean, dict(wins))


def effects(game):
    """{rule: (baseline, ablated)} enumerations, the exact reference."""
    base = enumerate_game(game)
    return {name: (base, enumerate_game(game, (name,)))
            for name in ABLATIONS[game]}


def verify(game):
    """Check the benchmark exhibits what it advertises.

    Returns a list of failure strings; empty means every claim holds.
    """
    problems = []
    base = enumerate_game(game)
    if base.stuck:
        problems.append(
            '{}: {} non-terminal states leave a player with no legal move. '
            'That is a malformed GDL game, not an interesting one'.format(
                game, base.stuck))
    if not base.terminals:
        problems.append(
            '{}: no reachable terminal state, so no outcome can be '
            'measured'.format(game))

    claims = CLAIMS.get(game, {})

    # REDUNDANCY is checked on everything observable: a redundant rule
    # must change no reachable state, no outcome AND no option count.
    for name in claims.get('redundant', ()):
        ablated = enumerate_game(game, (name,))
        mine = (base.states, base.terminals, round(base.mean_branching, 9))
        theirs = (ablated.states, ablated.terminals,
                  round(ablated.mean_branching, 9))
        if mine != theirs:
            problems.append(
                '{}: {!r} is declared REDUNDANT but relaxing it changes the '
                'game: {} states/{} terminals/{:.3f} branching -> '
                '{}/{}/{:.3f}'.format(
                    game, name, base.states, base.terminals,
                    base.mean_branching, ablated.states, ablated.terminals,
                    ablated.mean_branching))

    # INTERACTION is checked on MEAN BRANCHING, which is the quantity
    # these rules move. State and terminal counts are the wrong metric
    # here: `hold` is always legal, so the same positions stay reachable
    # whether or not a step is barred -- only the number of OPTIONS
    # changes. (That mismatch is why this check first reported the
    # interaction as absent.) Mean branching is also the project's own
    # `choice_diversity` dimension, so the benchmark exercises the same
    # statistic the Royal Chess profile reports.
    pair = claims.get('interacting', ())
    if len(pair) == 2:
        first, second = pair
        only_first = enumerate_game(game, (first,))
        only_second = enumerate_game(game, (second,))
        both = enumerate_game(game, pair)
        for name, got in ((first, only_first), (second, only_second)):
            if abs(got.mean_branching - base.mean_branching) < 1e-9:
                problems.append(
                    '{}: {!r} is declared INTERACTING but relaxing it alone '
                    'leaves mean branching at {:.3f}'.format(
                        game, name, base.mean_branching))
        alone = ((only_first.mean_branching - base.mean_branching)
                 + (only_second.mean_branching - base.mean_branching))
        together = both.mean_branching - base.mean_branching
        if together <= alone + 1e-9:
            problems.append(
                '{}: {!r} and {!r} are declared INTERACTING but their joint '
                'effect on mean branching ({:+.4f}) does not exceed the sum '
                'of the single effects ({:+.4f})'.format(
                    game, first, second, together, alone))
    return problems


def report(game='corridor'):
    base = enumerate_game(game)
    lines = [
        'EXACT REFERENCE EFFECTS -- {} (Phase B)'.format(game),
        '',
        'Exhaustive enumeration of every reachable state, so these are',
        'exact: no sampling, no agent, no interval. A rule is ablated by',
        'RELAXING a body conjunct, which makes the game more permissive --',
        'not by deleting the guard\'s definition, which makes it empty.',
        '',
        '{:<22} {:>8} {:>10} {:>7} {:>14}'.format(
            'variant', 'states', 'terminals', 'stuck', 'mean branching'),
        '{:<22} {:>8} {:>10} {:>7} {:>14.3f}'.format(
            'baseline', base.states, base.terminals, base.stuck,
            base.mean_branching),
    ]
    for name in sorted(ABLATIONS[game]):
        got = enumerate_game(game, (name,))
        lines.append('{:<22} {:>8} {:>10} {:>7} {:>14.3f}'.format(
            'relax ' + name, got.states, got.terminals, got.stuck,
            got.mean_branching))
    problems = verify(game)
    lines.append('')
    if problems:
        lines.append('CLAIMS NOT HELD:')
        lines.extend('  ' + p for p in problems)
    else:
        lines.append('Every advertised property holds.')
    return '\n'.join(lines)
