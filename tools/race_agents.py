"""Two weight sets playing each other. THE SHIP GATE.

IN THE REPOSITORY ON PURPOSE. This lived in a scratch directory, which
meant the gate that decides what ships was untracked, untested and
free to drift from the window it was supposed to be gating. It did
drift: every race ran at depth 2 while the window plays at
`Game.TD_DEPTH`, so a change raced at one depth was shipped for play at
another -- and a reviewer found the result worse. A test now pins the
two together.

Usage:

    RACE_DEPTH=3 RIVAL=path/to/candidate.json python3 tools/race_agents.py 30

Three changes in this project shipped because a weight table looked
better, and all three were worse in play. The material harness that was
supposed to catch that missed the agent capturing its OWN pieces, which
is what a human actually saw. So the two versions play.

Colours alternate so neither gets the first move as a gift, and
same-player captures are counted directly -- they were invisible to
every aggregate used so far.

READ THAT COUNT CAREFULLY, and this correction matters more than the
count. It uses the PLAYER'S-TURN definition of self-capture
(`docs/key-rule-differences.md` lines 38-42): the captured piece
belongs to the player whose turn it is, whatever colour the capturing
piece is. Every mechanic that produces one is LEGAL in this variant:

  * the KING capturing its own piece -- `RULEBOOK.md` says the king
    "may capture enemy pieces, friendly pieces, and the boulder" and
    "is the only piece that may capture friendly pieces";
  * MANIPULATION driving an enemy piece onto one of the mover's own,
    since the Manipulation Action allows captures;
  * the neutral BOULDER, which either player may move and which
    captures pawns "of either colour", moving onto the mover's pawn.

And a king self-capture can be CORRECT: the Tiny Endgame Rule resets
all distance counts after every capture, so a player facing the
distance limit can legally reset it by taking its own piece.

So the buckets are reported separately, and a fourth -- a non-king
piece of the mover's own colour taking its own colour -- is the only
one that would be a defect. The rulebook forbids it, and
`tests/test_same_colour_capture_rule.py` asserts it never appears in a
legal-move list. A bare total was being read as a bug report.
"""
import collections
import json
import random
import sys
import time

sys.path[:0] = ['.', 'src']
sys.path.insert(
    0, __import__('os').path.dirname(
        __import__('os').path.dirname(
            __import__('os').path.abspath(__file__))))

import os as _os
# THE RACE MUST RUN AT THE DEPTH THE AGENT PLAYS. Every race in this
# issue ran at depth 2 while the window plays at `Game.TD_DEPTH` (3),
# and a change that helps at one depth can hurt at another -- deeper
# search over a flawed evaluation amplifies the flaw. Shipping on a
# depth-2 race for depth-3 play is a methodological hole, and it is
# how a change that a reviewer found WORSE came to be shipped as a
# 25-7 win.
DEPTH = int(_os.environ.get('RACE_DEPTH', '3'))
#: NO CLOCK. A race under a wall budget is not a race at a depth: the
#: depth reached rises as the branching falls, so the two agents are
#: compared at one depth in the opening and another in the endgame, and
#: at a third depth again when the machine is busy. This tool reported
#: results under a 30-second budget until 2026-10-25 and those runs are
#: confounded by it -- their headers record the budget, so they stay
#: attributable. See `docs/candidate-designs.md` §6.
BUDGET = None
MAX_TURNS = 150


def main():
    from experiments.variants import make_engine
    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import (capture_ranker, royal_chess,
                                            with_threshold, without,
                                            drop_prefixes)
    from lgref.experiments.legacy import royal_chess as legacy_features
    from lgref.experiments.search import Searcher

    games = int(sys.argv[1]) if len(sys.argv) > 1 else 24

    def build(path, extractor_for):
        payload = json.load(open(path))
        weights = payload['weights']
        scales = payload.get('scales', {})
        extractor = extractor_for(payload)

        def evaluate(engine, perspective):
            raw = differentials(extractor(engine), perspective)
            return value(weights, normalise(raw, dict(scales),
                                            update=False))

        def make():
            return Searcher(evaluate, capture_ranker(weights, scales),
                            max_depth=DEPTH, quiescence=2)
        return make

    # ONE RECONSTRUCTION, shared with the loader. This script had its
    # own copy, and a copy is how a run gets raced on the feature set it
    # was supposed to be replacing.
    from lgref.experiments.features import royal_chess_extractor

    def current_extractor(payload):
        return royal_chess_extractor(payload)

    current = build('lgref/weights/td_royal_chess.json', current_extractor)
    import os as _os
    rival = _os.environ.get('RIVAL')
    if rival:
        legacy = build(rival, current_extractor)
    else:
        legacy = build('lgref/weights/td_royal_chess_legacy.json',
                       lambda _p: legacy_features)

    # A RACE LOG THAT DOES NOT SAY WHAT IT RACED IS NOT EVIDENCE.
    # A 12-game log from this session reported `current 2 - 8 legacy`
    # at depth 3 and there was no way left to tell WHICH rival those
    # eight losses were against: the environment that chose it was
    # gone with the shell. The result had to be thrown away. So the
    # run states its own terms, and `-` for the rival's hash means the
    # legacy feature set, which is a different vocabulary rather than
    # a different weight table.
    import hashlib

    def fingerprint(path):
        return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:8]

    print('RACE  current={0} ({1})  rival={2} ({3})  '
          'depth={4} clock={5} max_turns={6} games={7}'.format(
              'lgref/weights/td_royal_chess.json',
              fingerprint('lgref/weights/td_royal_chess.json'),
              rival or 'legacy-vocabulary',
              fingerprint(rival) if rival else '-',
              DEPTH,
              'none' if BUDGET is None else '{0:.0f}s'.format(BUDGET),
              MAX_TURNS, games),
          flush=True)

    tally = {'current': 0, 'legacy': 0, 'draw': 0}
    selfcaps = collections.Counter()
    started = time.time()
    from lgref.experiments.random_play import build as random_build

    for index in range(games):
        engine = make_engine('full', max_turns=MAX_TURNS)
        # A RANDOM OPENING PER GAME. Both searchers are deterministic,
        # so without this every game with the same colour assignment is
        # byte-identical -- a first run played 24 games that were two
        # distinct games repeated twelve times each, and returned a dead
        # heat by construction.
        opening = random_build('random', random.Random(1000 + index), 0)
        for _ply in range(random.Random(index).randint(4, 14)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(opening.choose_turn(turns, engine))
        # Alternate who moves first.
        sides = ({'white': ('current', current), 'black': ('legacy', legacy)}
                 if index % 2 == 0 else
                 {'white': ('legacy', legacy), 'black': ('current', current)})
        agents = dict((colour, (name, factory()))
                      for colour, (name, factory) in sides.items())
        plies = 0
        while not engine.is_game_over() and plies < MAX_TURNS:
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            mover = engine.current_player
            name, agent = agents[mover]
            chosen = agent.choose_turn(turns, engine)
            # Did it take one of its own, and BY WHICH MECHANIC? See
            # the module docstring: all three legal ones used to land
            # in a single number that read as a bug report.
            target = getattr(chosen, 'to_sq', None)
            if getattr(chosen, 'is_capture', False) and target is not None:
                victim = engine.board.squares[target[0]][target[1]].piece
                if victim is not None and getattr(victim, 'color',
                                                  None) == mover:
                    source = getattr(chosen, 'from_sq', None)
                    actor = (engine.board.squares[source[0]][source[1]].piece
                             if source else None)
                    colour = getattr(actor, 'color', None)
                    if actor is None:
                        kind = 'unexplained'
                    elif (type(actor).__name__ == 'Boulder'
                          or colour in ('neutral', None, 'none')):
                        kind = 'boulder'
                    elif colour != mover:
                        kind = 'manipulation'
                    elif type(actor).__name__ == 'King':
                        kind = 'king'
                    else:
                        kind = 'unexplained'
                    selfcaps[(name, kind)] += 1
            engine.execute_turn(chosen)
            plies += 1
        winner = engine.winner
        if winner is None:
            tally['draw'] += 1
        else:
            tally[agents[winner][0]] += 1
        print('game {0:>2}: {1:>7} after {2} plies   running '
              'current {3} - {4} legacy, {5} drawn   {6:.0f}s'.format(
                  index + 1,
                  'draw' if winner is None else agents[winner][0],
                  plies, tally['current'], tally['legacy'], tally['draw'],
                  time.time() - started), flush=True)
    print()
    print('FINAL  current {0} - {1} legacy, {2} drawn (of {3})'.format(
        tally['current'], tally['legacy'], tally['draw'], games))
    print('same-player captures played, by mechanic (all legal except '
          'the last):')
    for kind, note in (('king', 'king takes its own -- can be CORRECT, '
                                'it resets the tiny-endgame counts'),
                       ('manipulation', 'enemy piece driven onto its own'),
                       ('boulder', 'neutral boulder onto its own pawn'),
                       ('unexplained', 'A DEFECT if non-zero: the '
                                       'rulebook forbids it')):
        here, there = selfcaps[('current', kind)], selfcaps[('legacy', kind)]
        if here or there or kind == 'unexplained':
            print('   {0:14} current {1}, legacy {2}   ({3})'.format(
                kind, here, there, note))


if __name__ == '__main__':
    main()
