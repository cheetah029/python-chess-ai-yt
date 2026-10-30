"""The rulebook's same-colour-capture invariant, asserted.

`RULEBOOK.md`, King: "the king may capture enemy pieces, friendly
pieces, and the boulder. It is the only piece that may capture friendly
pieces or the boulder."

`docs/key-rule-differences.md` states the invariant that follows:
"the only same-color capture is the king capturing its own piece. All
manipulation-induced friendly captures use an enemy-colored capturing
piece."

THIS WAS UNASSERTED, and a measurement was resting on it. `race_agents.py`
counts "self-captures played" and its header called them a defect --
"the material harness that was supposed to catch that missed the agent
capturing its OWN pieces". Scanning the legal turns of 40 random
positions produced 160 turns that the counter flags, and every one of
them is permitted by a rule:

    131   the king capturing its own piece        (King rule)
     18   the mover driving an ENEMY piece onto
          one of its own                          (Manipulation Action:
                                                   "captures are allowed")
     11   the mover moving the NEUTRAL BOULDER
          onto its own pawn                       (either player may move
                                                   the boulder; it captures
                                                   pawns "of either colour")
      0   anything else

So a self-capture count is not by itself evidence of a defect, and the
third mechanic is not covered by either definition in the cheat sheet
-- the boulder is neutral, so it is neither a friendly nor an enemy
capturing piece.

WHAT WOULD BE A DEFECT is the fourth bucket: a non-king piece of the
mover's own colour capturing a piece of its own colour. The rulebook
forbids it outright, so if it is ever legal the move generator is
wrong. That is what these tests check.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random

NEUTRAL = ('neutral', None, 'none')


def _positions(count=40, seed=3, max_plies=70):
    from experiments.variants import make_engine

    rng = random.Random(seed)
    out = []
    while len(out) < count:
        engine = make_engine('full', max_turns=400)
        for _ply in range(rng.randint(0, max_plies)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(rng.choice(turns))
        if not engine.is_game_over():
            out.append(engine)
    return out


def _classify(engine, turn):
    """Which rule, if any, permits this same-player capture."""
    target = getattr(turn, 'to_sq', None)
    if not getattr(turn, 'is_capture', False) or target is None:
        return None
    victim = engine.board.squares[target[0]][target[1]].piece
    mover = engine.current_player
    if victim is None or getattr(victim, 'color', None) != mover:
        return None
    source = getattr(turn, 'from_sq', None)
    actor = (engine.board.squares[source[0]][source[1]].piece
             if source else None)
    if actor is None:
        return 'unexplained'
    colour = getattr(actor, 'color', None)
    if type(actor).__name__ == 'Boulder' or colour in NEUTRAL:
        return 'boulder'
    if colour != mover:
        return 'manipulation'
    if type(actor).__name__ == 'King':
        return 'king'
    return 'unexplained'


def test_only_the_king_makes_a_same_colour_capture():
    """The invariant itself. A non-king piece capturing a piece of its
    OWN colour is forbidden by the rulebook, so a move generator that
    offers one is wrong -- and every aggregate built on top of it is
    measuring a game nobody is playing."""
    offenders = []
    scanned = 0
    for engine in _positions():
        for turn in engine.get_all_legal_turns():
            scanned += 1
            if _classify(engine, turn) == 'unexplained':
                source = getattr(turn, 'from_sq', None)
                target = getattr(turn, 'to_sq', None)
                actor = engine.board.squares[source[0]][source[1]].piece
                victim = engine.board.squares[target[0]][target[1]].piece
                offenders.append('{0} {1} at {2} captures own {3} at {4}'
                                 .format(getattr(actor, 'color', '?'),
                                         type(actor).__name__, source,
                                         type(victim).__name__, target))
    assert scanned > 2000, 'too few turns scanned to mean anything'
    assert not offenders, (
        'RULEBOOK.md permits only the king to capture a friendly piece, '
        'and the move generator offered {0} that are not the king:\n  '
        '{1}'.format(len(offenders), '\n  '.join(offenders[:10])))


def test_a_self_capture_count_is_not_by_itself_a_defect():
    """The counter in `race_agents.py` uses the PLAYER'S-TURN definition
    of self-capture (`docs/key-rule-differences.md` lines 38-42), which
    is deliberate -- but all three mechanics it catches are legal, so a
    non-zero count is a thing to explain and not a bug to report.

    Asserted so that nobody re-derives "the agent is capturing its own
    pieces, therefore the agent is broken" from a bare number.
    """
    seen = set()
    for engine in _positions():
        for turn in engine.get_all_legal_turns():
            kind = _classify(engine, turn)
            if kind:
                seen.add(kind)
    assert 'king' in seen, (
        'no legal king self-capture found in any sampled position, so '
        'this suite is not reaching the rule it claims to cover')
    assert 'unexplained' not in seen
    assert seen <= {'king', 'boulder', 'manipulation'}, seen


def test_the_king_self_capture_is_a_resource_not_only_a_blunder():
    """Why the count must not be read as a defect, stated concretely.

    `RULEBOOK.md`, Tiny Endgame Rule, Distance Counts: "After every
    capture, reset all distance counts to 0." A player who would
    otherwise lose to the distance limit can reset the counter, and the
    king capturing one of its OWN pieces is a legal way to do it. So
    there are positions in which a self-capture is the correct move.

    Checked against the rulebook text rather than against play, because
    using the agent's own choices as evidence here would be circular.
    """
    import io

    here = os.path.dirname(__file__)
    rulebook = io.open(os.path.join(here, '..', 'RULEBOOK.md'),
                       encoding='utf-8').read()
    # MARKDOWN BOLD IS IN THE SOURCE, so the text is matched with the
    # emphasis the file actually carries -- this project has already
    # lost a reading to a regex that assumed plain text.
    assert 'reset all distance counts to **0**' in rulebook, (
        'the Tiny Endgame Rule no longer resets the distance counts on '
        'a capture, so the reason a self-capture can be correct has '
        'changed and this test is out of date')
    assert ('the king may capture enemy pieces, friendly pieces, and the '
            'boulder' in rulebook)
    assert ('It is the only piece that may capture friendly pieces or '
            'the boulder' in rulebook)
