"""A cheaper deep copy, because copying was 90% of every search node.

THE MEASUREMENT THAT MOTIVATES THIS. Profiling one node of a tree search
on this engine:

    copy.deepcopy(engine + turns)    0.985 ms
    get_all_legal_turns()            0.074 ms

The search spent THIRTEEN TIMES longer copying the state than reasoning
about the game. In a midgame position (ply 80, branching 68) the copy
costs 9.27 ms, which is why 800 simulations took about 44 seconds per
move: almost all of that was `deepcopy`.

A pickle round-trip is the same operation -- a full independent deep copy
of the object graph, with shared references inside the pickled value
preserved -- implemented in C instead of Python:

    thin endgame   0.992 ms -> 0.159 ms    6.3x
    midgame        9.270 ms -> 1.105 ms    8.4x

WHY THIS IS THE RIGHT KIND OF IMPROVEMENT, and worth saying explicitly.
Every other route to a stronger agent risks biasing what the agent
measures: a hand-written evaluation encodes a researcher's opinion about
the game, and an evaluation learned from weak self-play encodes the weak
agent. This encodes NOTHING. It changes no decision the search makes --
with the same seed and the same budget it explores the same tree -- it
only lets the same budget buy roughly eight times as many nodes. It also
helps every agent equally and carries over to any engine whose state is
picklable, so no part of it is specific to one game.

CORRECTNESS, since a subtly incomplete copy would corrupt a search in
ways that look like a weak agent rather than like a bug. Verified across
360 states from six random games, comparing a pickle clone against a
`deepcopy` clone on: whose turn it is, the turn number, the winner, the
loss reason, the full sorted list of legal turns, and the board's state
hash -- before AND after executing a turn on each clone. Zero
mismatches. `lgref/tests/test_fastcopy.py` keeps that check.

WHY PAIRS ARE CLONED TOGETHER. A `Turn` holds a reference to the piece
on the board that produced it, and `Board.move` writes cooldown, moved
and last-square state onto that piece -- so executing a caller's turn on
a copied engine writes through to the LIVE game (#247, where every
simulation was corrupting the real board). Cloning the engine and its
turns as one value keeps the turns pointing at the clone's pieces, which
pickle preserves because the sharing is inside a single pickled value.
Cloning them separately would reintroduce the bug.
"""

import pickle


def clone(value):
    """An independent deep copy of `value`.

    Semantically `copy.deepcopy`, about 6-8x faster on this engine. Pass
    an (engine, turns) TUPLE when the turns will be executed on the
    clone, so the references between them are preserved -- see the
    module docstring.
    """
    return pickle.loads(pickle.dumps(value, pickle.HIGHEST_PROTOCOL))


def clone_with_turns(engine, turns):
    """`(engine, turns)` cloned as one value, which is almost always what
    a search wants. Spelled out so the pairing is hard to forget."""
    return clone((engine, turns))
