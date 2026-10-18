"""Guards on the SHIPPED weights, for the case study specifically.

DOMAIN-SPECIFIC ON PURPOSE, and separated from the generality audit for
that reason. These assert properties of one artifact for one game; they
are not inputs to learning and nothing here is supplied to the learner.
A different game would need its own file, or none.

Every check corresponds to a blunder a human found by playing, after an
aggregate statistic had said the agent was fine:

  - it gave away bishops, because `Bishop` was -0.0077 while `Pawn` was
    +0.0501, so "lose a bishop, win a pawn" scored +0.047, A GAIN.
  - it gave away knights, because `Knight` fell to 1.3 pawns and the
    same trade came to -0.0045, which is free.
  - it captured its OWN pieces, because the capture ranker scored the
    destination occupant by `abs(weight)` without asking whose it was.

The material harness missed all three. It samples random positions and
scores two plies of material, and none of these are visible that way.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

from lgref.experiments.replicate import effective

WEIGHTS = os.path.join(os.path.dirname(__file__), '..', 'weights',
                       'td_royal_chess.json')

#: Pieces that are worth more than a pawn in this variant. NOT supplied
#: to anything -- this file reads the learned weights and complains. The
#: claim is weak on purpose: a rook sweeps the board, a knight moves to
#: any of sixteen squares and can be invulnerable, a bishop teleports
#: anywhere safe and pins what it sees. Each does more than step one
#: square forward, so each should price above the piece that does.
STRONGER_THAN_A_PAWN = ('Rook', 'Knight', 'Bishop', 'Royal')


@pytest.fixture(scope='module')
def learned():
    return effective(json.load(open(WEIGHTS)))


def test_every_piece_is_worth_something(learned):
    """A NEGATIVE piece value is how the bishops were given away.

    `Bishop` was -0.0077: the evaluation preferred not having one. No
    piece in this game is a liability -- the worst case is that it does
    nothing, which is zero.
    """
    for name in STRONGER_THAN_A_PAWN + ('Pawn',):
        value = learned.get(name, 0.0)
        assert value > 0.0, (
            '{0} is priced at {1:+.4f}; a negative piece value means the '
            'agent will give it away for free'.format(name, value))


def test_trading_a_piece_for_a_pawn_is_never_a_gain(learned):
    """The reported blunder, asked directly.

    In the game that prompted this, `5. Pe2-e3` attacked a knight on e4
    and the agent played elsewhere; `6. Pe3xe4` took it and the pawn was
    recaptured. Net: a knight for a pawn. If the evaluation scores that
    as positive, the agent is not blundering, it is obeying.

    Checked by SIGN rather than by a margin, because a margin would be a
    number I made up. The sign is the property that matters: losing more
    than you gain must not read as a gain.
    """
    pawn = learned.get('Pawn', 0.0)
    for name in STRONGER_THAN_A_PAWN:
        trade = -learned.get(name, 0.0) + pawn
        assert trade < 0.0, (
            'giving up a {0} for a pawn scores {1:+.4f}; the agent will '
            'do it'.format(name, trade))


def test_the_pawn_is_not_the_most_valuable_thing_on_the_board(learned):
    """A sanity bound that would have caught the compressed scale.

    When `Knight` fell to 1.3 pawns and `Bishop` to 1.0, every capture
    ranked alike -- which cost strength AND speed, since move ordering
    collapsed and the tree doubled (8916 nodes against 4424 in the early
    game).
    """
    pawn = learned.get('Pawn', 0.0)
    assert pawn > 0.0
    for name in STRONGER_THAN_A_PAWN:
        assert learned.get(name, 0.0) > pawn, (
            '{0} at {1:.1f} pawns'.format(name,
                                          learned.get(name, 0.0) / pawn))


def test_a_self_capture_ranks_below_a_quiet_move():
    """Only the king may take a friendly piece (RULEBOOK.md). The ranker
    scored the destination occupant by `abs(weight)` without asking
    whose it was, so "king takes own rook" was the top-ranked move on
    the board -- 124 of them across 40 positions, every one at 0.3952.
    """
    import random

    from experiments.variants import make_engine

    from lgref.experiments.features import capture_ranker
    from lgref.experiments.random_play import build

    payload = json.load(open(WEIGHTS))
    rank = capture_ranker(payload['weights'], payload.get('scales', {}))

    found = 0
    for seed in range(12):
        engine = make_engine('full', max_turns=400)
        mover = build('random', random.Random(seed), 0)
        for _ply in range(random.Random(seed).randint(10, 60)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(mover.choose_turn(turns, engine))
        side = engine.current_player
        for turn in engine.get_all_legal_turns():
            target = getattr(turn, 'to_sq', None)
            if not getattr(turn, 'is_capture', False) or target is None:
                continue
            victim = engine.board.squares[target[0]][target[1]].piece
            if victim is None or getattr(victim, 'color', None) != side:
                continue
            found += 1
            assert rank(engine, turn) < 0.0, (
                'a self-capture ranked {0:+.4f}, at or above a quiet '
                'move'.format(rank(engine, turn)))
    assert found > 10, 'too few self-captures seen to mean anything'


def test_the_shipped_weights_load_and_choose_a_move():
    """The end-to-end check that was missing while the staleness guard
    fired five times in one session."""
    import random

    from experiments.variants import make_engine

    from lgref.experiments.features import load_royal_chess_searcher
    from lgref.experiments.random_play import build

    engine = make_engine('full', max_turns=400)
    mover = build('random', random.Random(1), 0)
    for _ply in range(30):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(mover.choose_turn(turns, engine))
    searcher = load_royal_chess_searcher(WEIGHTS, budget=30.0,
                                         max_depth=2)
    turns = engine.get_all_legal_turns()
    assert searcher.choose_turn(turns, engine) in turns
