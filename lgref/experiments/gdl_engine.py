"""Royal Chess positions read as the GDL's own state, for GDL features.

Issue #397. The shipped Royal Chess evaluation was written by hand:
19 features, mostly material counts. Measured, it was BLIND to 8 of the
12 parts of the state the rules consult -- the boulder's cooldown and
no-return memory, the manipulation freeze, invulnerability, which piece
just moved, reactive arming, and both history counts -- and it saw
piece positions only through attack and cover terms with weights close
to zero. Each blind spot was found the hard way: the boulder, the tiny
endgame and the repetition rule each cost games before anyone noticed.

THE FIX IS NOT TO ADD THE MISSING PARTS BY HAND. Hand-adding them would
make the evaluation a list of what someone remembered about Royal
Chess, and the next rule would be missing from it too. Instead the
position is read AS THE GAME DESCRIPTION'S STATE: every fluent
`docs/gdl/integrated.gdl` declares, produced from the engine by the
converter the cross-validation harness already uses
(`ggp.cross_validation.board_to_gdl_facts`). The features are then the
general GDL features of `lgref.experiments.gdl.features`, the same
extractor every GDL game gets. Nothing in that extractor knows what a
bishop is, so the evaluation is derived from the rules for every game,
and the blindness audit (`lgref/tests/test_evaluation_blindness.py`)
checks that no fluent is left out.

ONE FLUENT THE CONVERTER DID NOT EMIT: `state_repetition_count`. It is
added here, from the engine's own repetition history, so the rules'
repetition counts are part of the state the evaluation reads. The
state's identity in it is a short digest of the engine's state hash:
the GDL leaves the identity abstract, and any stable name serves.
`next_state_hash` is not emitted. It is how the description passes a
successor's identity between two rules, not a property of a position.

GENERAL OVER THE PROTOCOL: this module is the one place that knows the
Royal Chess engine's attributes, which is where that knowledge belongs
(the engine IS the rules). Everything downstream sees GDL fluents.
"""

import hashlib
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

#: The roles as the GDL names them.
ROLES = ('black', 'white')


def _identity(state_hash):
    """A short, stable name for one board state."""
    return hashlib.sha256(repr(state_hash).encode()).hexdigest()[:12]


def engine_facts(engine):
    """The position as a frozenset of GDL fluents (tuples), including the
    repetition counts the converter leaves out."""
    from ggp.cross_validation import board_to_gdl_facts

    board = engine.board
    facts = set(board_to_gdl_facts(board, engine.current_player))
    for state, count in getattr(board, 'state_history', {}).items():
        if count:
            facts.add(('state_repetition_count', _identity(state),
                       str(count)))
    return frozenset(facts)


class StateView(object):
    """What `gdl.features` needs: a state, the roles, the mover.

    `ggp` is None, so the rule relaxations (which need the description's
    rule base) are not computed for an engine position. The fluent
    features are.
    """

    __slots__ = ('state', 'roles', 'current_player', 'ggp')

    def __init__(self, state, current_player, roles=ROLES, ggp=None):
        self.state = state
        self.roles = list(roles)
        self.current_player = current_player
        self.ggp = ggp


def view(engine):
    return StateView(engine_facts(engine), engine.current_player)


_CONSTANTS = None


def description_constants(path=None):
    """Every constant the game description mentions, in any rule or
    fact. Read once from `docs/gdl/integrated.gdl`."""
    global _CONSTANTS
    if _CONSTANTS is not None and path is None:
        return _CONSTANTS
    import re

    path = path or os.path.join(os.path.dirname(_SRC), 'docs', 'gdl',
                                'integrated.gdl')
    text = open(path).read()
    text = '\n'.join(line.split('%', 1)[0] for line in text.splitlines())
    found = frozenset(re.findall(r'\b([a-z0-9][A-Za-z0-9_]*)\b', text))
    if path == os.path.join(os.path.dirname(_SRC), 'docs', 'gdl',
                            'integrated.gdl'):
        _CONSTANTS = found
    return found


def named_by_the_rules(counts, constants):
    """`counts` without the indicator features whose VALUE the rules
    never mention.

    A FEATURE NAMED AFTER A VALUE NO RULE MENTIONS CANNOT BE A RULE-LEVEL
    QUANTITY. The general GDL extractor writes one indicator per value
    an argument takes (`rel@i=v`, and `rel@iisv` for numbers). For a
    value the description itself uses -- a piece name, a file, a form --
    that is a concept of the game. For a value it never mentions it is
    an identity: each state hash in `state_repetition_count` became its
    own feature, which cannot carry from one game to the next. So those
    indicators are dropped; the relation's count and its numeric
    arguments are kept (how many states have been seen twice).

    GENERAL: the test is "does the description mention it", which needs
    no knowledge of the game.
    """
    kept = {}
    for (owner, name), value in counts.items():
        # Only SYMBOLIC values (`rel@i=v`) are tested. A number is a
        # quantity, not an identity: the description computes distances
        # up to 14 and turn numbers without naming each one, and a
        # number's indicator is how a non-monotone quantity (a parity) is
        # expressed at all.
        if '=' in name and name.split('=', 1)[1] not in constants:
            continue
        kept[(owner, name)] = value
    return kept


def features(engine):
    """`{(owner, name): value}` for an engine position, read as the GDL
    state. The extractor protocol (`lgref.experiments.features`)."""
    from lgref.experiments import gdl

    return named_by_the_rules(
        gdl.features(view(engine), roles=ROLES, relaxed=False),
        description_constants())
