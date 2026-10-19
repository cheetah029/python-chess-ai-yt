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

A PIECE IS PRICED BY TAKING IT OFF THE BOARD, not by reading a weight,
and that change is the most important thing in this file. These guards
used to compare two weight names -- `learned['Bishop']` against
`learned['Pawn']` -- and that comparison is invalid here, because the
columns are collinear. A queen may take the form of a piece type only
once a friendly piece of that type has been captured, so "bishops I
hold" and "bishop form available to me" are near-complements:
R-squared 0.98 on each other, measured by `replicate.shared_variance`.
The learner only ever sees their sum and splits it arbitrarily.

So the old guards were comparing one arbitrary half of a split pair
against a whole, and they passed a shipped evaluation whose reported
bishop was 1.1 pawns while its actual charge for losing a bishop was
1.6. A reviewer said 1.1 could not be right. They were right that it
was wrong, and wrong about which number was broken.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

WEIGHTS = os.path.join(os.path.dirname(__file__), '..', 'weights',
                       'td_royal_chess.json')

#: Pieces that are worth more than a pawn in this variant. NOT supplied
#: to anything -- this file reads the learned weights and complains. The
#: claim is weak on purpose: a rook sweeps the board, a knight moves to
#: any of sixteen squares and can be invulnerable, a bishop teleports
#: anywhere safe and pins what it sees. Each does more than step one
#: square forward, so each should price above the piece that does.
STRONGER_THAN_A_PAWN = ('Rook', 'Knight', 'Bishop', 'Queen', 'King')


def _remove(game, label, rng):
    """Take one of the mover's pieces of type `label` off the board.

    RECORDED AS CAPTURED rather than deleted, because in this game a
    queen's available forms depend on which friendly types have been
    captured -- so a piece that never existed is a different position
    from a piece that was traded, and the trade is what is being priced.
    """
    board = game.board
    mover = game.current_player
    found = []
    for row in range(len(board.squares)):
        for col in range(len(board.squares[row])):
            piece = board.squares[row][col].piece
            if (piece is not None and type(piece).__name__ == label
                    and getattr(piece, 'color', None) == mover):
                found.append((row, col, piece))
    if not found:
        return False
    row, col, piece = rng.choice(found)
    board.squares[row][col].piece = None
    name = getattr(piece, 'name', label.lower())
    if mover in board.captured_pieces:
        board.captured_pieces[mover].append(name)
    return True


@pytest.fixture(scope='module')
def prices():
    """What the shipped evaluation charges for losing one of each piece,
    measured on real positions with every column that moves included."""
    from experiments.variants import make_engine

    from lgref.experiments.bootstrap import normalise
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import load_royal_chess_searcher
    from lgref.experiments.legacy import royal_chess as legacy
    from lgref.experiments.validate import removal_price

    payload = json.load(open(WEIGHTS))
    weights, scales = payload['weights'], payload.get('scales', {})
    # The loader is called so that a payload the agent could not play
    # fails here too, rather than only in the game.
    load_royal_chess_searcher(WEIGHTS, budget=1.0, max_depth=1)

    def columns_of(game, perspective):
        return normalise(differentials(legacy(game), perspective),
                         dict(scales), update=False)

    return removal_price(lambda: make_engine('full', max_turns=400),
                         columns_of, weights, _remove,
                         ('Pawn',) + STRONGER_THAN_A_PAWN,
                         trials=24, seed=9)


def test_every_piece_is_worth_something(prices):
    """A NEGATIVE piece value is how the bishops were given away.

    `Bishop` was -0.0077: the evaluation preferred not having one. No
    piece in this game is a liability -- the worst case is that it does
    nothing, which is zero.
    """
    for name in ('Pawn',) + STRONGER_THAN_A_PAWN:
        price, samples = prices[name]
        assert samples > 0, 'no position priced a {0}'.format(name)
        assert price > 0.0, (
            'losing a {0} is scored at {1:+.4f}; a negative price means '
            'the agent will give it away for free'.format(name, price))


def test_trading_a_piece_for_a_pawn_is_never_a_gain(prices):
    """The reported blunder, asked directly.

    In the game that prompted this, `5. Pe2-e3` attacked a knight on e4
    and the agent played elsewhere; `6. Pe3xe4` took it and the pawn was
    recaptured. Net: a knight for a pawn. If the evaluation scores that
    as positive, the agent is not blundering, it is obeying.

    Checked by SIGN rather than by a margin, because a margin would be a
    number I made up. The sign is the property that matters: losing more
    than you gain must not read as a gain.
    """
    pawn = prices['Pawn'][0]
    for name in STRONGER_THAN_A_PAWN:
        trade = -prices[name][0] + pawn
        assert trade < 0.0, (
            'giving up a {0} for a pawn scores {1:+.4f}; the agent will '
            'do it'.format(name, trade))


def test_the_pawn_is_not_the_most_valuable_thing_on_the_board(prices):
    """A sanity bound that would have caught the compressed scale.

    When `Knight` fell to 1.3 pawns and `Bishop` to 1.0, every capture
    ranked alike -- which cost strength AND speed, since move ordering
    collapsed and the tree doubled (8916 nodes against 4424 in the early
    game).
    """
    pawn = prices['Pawn'][0]
    assert pawn > 0.0
    for name in STRONGER_THAN_A_PAWN:
        assert prices[name][0] > pawn, (
            '{0} at {1:.1f} pawns'.format(name, prices[name][0] / pawn))


def test_a_royal_is_the_most_expensive_piece_on_the_board(prices):
    """Losing a royal is half the loss condition; nothing else is.

    This is the guard that caught a king priced at +0.0165 against a
    knight's +0.0423 -- a king-for-knight trade read as a gain, which a
    human duly hit.
    """
    royal = min(prices['King'][0], prices['Queen'][0])
    for name in ('Pawn', 'Knight', 'Bishop', 'Rook'):
        assert prices[name][0] < royal, (
            '{0} is priced at or above a royal'.format(name))


def test_a_self_capture_ranks_below_a_quiet_move():
    """Only the king may take a friendly piece (RULEBOOK.md). The ranker
    scored the destination occupant by `abs(weight)` without asking
    whose it was, so "king takes own rook" was the top-ranked move on
    the board -- 124 of them across 40 positions, every one at 0.3952.
    """
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


def test_a_weight_name_is_not_a_price_and_the_pairs_prove_it():
    """The methodological guard, and the reason this file was rewritten.

    If someone goes back to comparing `learned['Bishop']` against
    `learned['Pawn']`, this fails and says why: the column has a
    near-complement, so the name carries only part of the price. The
    threshold is deliberately loose -- the claim is "these two columns
    are mostly the same information", not a particular number.
    """
    from experiments.variants import make_engine

    from lgref.experiments.discover import differentials
    from lgref.experiments.legacy import royal_chess as legacy
    from lgref.experiments.random_play import build
    from lgref.experiments.replicate import shared_variance

    vectors = []
    for trial in range(4):
        game = make_engine('full', max_turns=400)
        mover = build('random', random.Random(trial), 0)
        for _ply in range(90):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(mover.choose_turn(turns, game))
            vectors.append(differentials(legacy(game),
                                         game.current_player))
    explained = shared_variance(vectors)
    for name in ('Bishop', 'Rook', 'Knight'):
        assert explained[name] > 0.7, (
            '{0} is only {1:.2f} explained by the other columns; if that '
            'is really so, a weight name may be read as a price again -- '
            'but check `removal_price` first'.format(name,
                                                     explained[name]))
