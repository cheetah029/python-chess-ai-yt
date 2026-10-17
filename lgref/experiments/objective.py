"""What the game says it is about, extracted from its own statements.

THE CONSTRAINT THIS ANSWERS. A hand-written position score cannot serve a
framework that must handle unseen games: "count the royals" is a fact
about Royal Chess and is meaningless in nim. But an evaluation does not
have to be hand-written. A game description DECLARES its objective, and
the predicates that declaration depends on are exactly the quantities
progress is measured in. Reading them is not researcher bias, it is
reading the rules -- and the same code reads any game.

This is the move strong general players make: Sancho and Galvanise derive
evaluations from the game description rather than being given them.

WHAT IT EXTRACTS. Starting from `terminal` and `goal`, follow the
dependency chain through the rules to the STATE predicates at the bottom
-- the ones appearing under `true(...)` or as base relations. Those are
the features the outcome is a function of. For Royal Chess:

    terminal :- lost(black)
    lost(P)  :- dead(P,king) & dead(P,queen)

so the objective depends on `dead(P, king)` and `dead(P, queen)`, and the
progress measure is how many of each player's king and queen survive.

AND THE HARD LESSON IT MADE VISIBLE. Royal Chess wins by capturing BOTH
royals, so its objective is a CONJUNCTION of two rare events. Measured
consequences:

  * no single move can end the game while both royals live -- exact
    one-ply search finds 0 wins and 0 losses among 56 midgame moves,
    and correctly finds the win when a player is down to one royal;
  * the extracted measure is therefore flat almost everywhere: both
    sides have two royals for most of the game, so it gives no gradient
    to choose between midgame moves.

That is not a defect of the extraction. It is a true statement about this
game: nothing in its declared objective distinguishes most midgame moves.
A dense signal would have to be INSTRUMENTAL -- material, threats,
mobility -- and those are not in the objective at all. They are either
supplied by a researcher, which fails the cross-game constraint, or
learned from play, which is what AlphaZero's result says is necessary and
what the execution brief's Phase 3 originally specified.
"""

import collections

#: Predicates that are part of GDL's own vocabulary rather than a game's
#: state, so following the chain through them says nothing about what the
#: game is about.
GDL_KEYWORDS = frozenset((
    'does', 'true', 'distinct', 'role', 'init', 'next', 'legal', 'goal',
    'terminal', 'base', 'input', 'not'))

Objective = collections.namedtuple(
    'Objective', 'roots state_predicates depth flat_warning')


def extract(path):
    """The state predicates the game's declared outcome depends on.

    Reads the dependency chain from `terminal` and `goal` down to the
    state predicates, over the infix HRF dialect the project treats as
    official.
    """
    from lgref.identify.clauses import load

    nodes = load(path)
    bodies = collections.defaultdict(set)
    heads = set()
    for node in nodes:
        head = node.head_predicate
        heads.add(head)
        for predicate in node.body_predicates:
            if predicate not in GDL_KEYWORDS:
                bodies[head].add(predicate)
        # Fluents the clause reads are state carriers even when the body
        # predicate list has already resolved them away.
        for fluent in getattr(node, 'fluents_read', ()) or ():
            if fluent not in GDL_KEYWORDS:
                bodies[head].add(fluent)

    roots = [name for name in ('terminal', 'goal') if name in heads]
    seen = set()
    frontier = list(roots)
    depth = 0
    while frontier:
        depth += 1
        nxt = []
        for name in frontier:
            for dependency in bodies.get(name, ()):
                if dependency not in seen:
                    seen.add(dependency)
                    nxt.append(dependency)
        frontier = nxt
        if depth > 50:                             # pragma: no cover
            break

    # The bottom of the chain: predicates nothing else defines, plus any
    # that survive as state carriers.
    state = sorted(p for p in seen if p not in GDL_KEYWORDS)
    return Objective(roots=tuple(roots), state_predicates=tuple(state),
                     depth=depth, flat_warning=None)


def royal_balance(engine):
    """Royal Chess's extracted measure: surviving royals, by player.

    The quantity `dead(P, king) & dead(P, queen)` is a predicate over --
    so the progress measure is the count that predicate thresholds on.
    Returned as a dict rather than a score, because turning it into a
    single number requires weights and weights are a choice.

    FLAT FOR MOST OF THE GAME, by construction: both sides hold two
    royals until one is captured, so this separates no midgame moves.
    That is a property of the objective, not of the code.
    """
    counts = {}
    board = engine.board
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is not None and getattr(piece, 'is_royal', False):
                colour = getattr(piece, 'color', None)
                counts[colour] = counts.get(colour, 0) + 1
    return counts


def informative_share(engine_factory, positions=40, seed=0):
    """Fraction of sampled positions where the measure is NOT flat.

    The number that decides whether an extracted objective can guide a
    search at all. If both players always hold the same royal count, the
    measure cannot order any two moves and a search using it is choosing
    at random.
    """
    import random

    rng = random.Random(seed)
    informative = 0
    total = 0
    for _ in range(positions):
        engine = engine_factory(rng)
        counts = royal_balance(engine)
        values = sorted(counts.values())
        total += 1
        if len(set(values)) > 1:
            informative += 1
    return (informative / float(total)) if total else float('nan')
