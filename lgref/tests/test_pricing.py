"""Pricing a piece without reading a weight name.

The instruments here exist because a weight name is not a price when
columns are collinear, and in the case study they are: *bishops I hold*
and *bishop form available to me* are near-complements, so the learner
sees only their sum and the reported `Bishop` weight is one arbitrary
half of it. The shipped evaluation was reported as charging 1.1 pawns
for a bishop when it charges 1.6.

The general machinery takes its game knowledge as injected callables,
so these tests check the machinery on a toy and then once on the real
engine.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from lgref.experiments.validate import exclusive_columns


def test_a_column_that_moves_for_everything_belongs_to_nothing():
    """The rule that makes a price adjustable without anyone deciding
    which columns belong to which piece.

    A coverage count changes when ANY piece leaves the board, so it is
    shared and must not be rescaled when one piece's price is corrected
    -- doing so would move every other piece's price with it. A column
    that moves for exactly one label is that label's own.
    """
    table = {'Bishop': {'Bishop': -1.0, 'FormAvailable:bishop': 1.0,
                        'Covers': -6.0},
             'Rook': {'Rook': -1.0, 'Covers': -9.0},
             'Pawn': {'Pawn': -1.0, 'Covers': -2.0}}
    own = exclusive_columns(table)
    assert own['Bishop'] == ['Bishop', 'FormAvailable:bishop']
    assert own['Rook'] == ['Rook']
    assert own['Pawn'] == ['Pawn']
    for label in table:
        assert 'Covers' not in own[label]


def test_a_label_with_no_column_of_its_own_gets_an_empty_list():
    """Royals share `Royal` and `DownToOneRoyal` with each other, so
    neither has an exclusive column and neither can be rescaled alone.
    That is correct, and it must not raise."""
    table = {'King': {'Royal': -1.0}, 'Queen': {'Royal': -1.0}}
    assert exclusive_columns(table) == {'King': [], 'Queen': []}


def _remove(game, label, rng):
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


def _columns_and_weights():
    import json

    from lgref.experiments.bootstrap import normalise
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import royal_chess_extractor

    path = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'td_royal_chess.json')
    payload = json.load(open(path))
    scales = payload.get('scales', {})
    extractor = royal_chess_extractor(payload, path=path)

    def columns_of(game, perspective):
        return normalise(differentials(extractor(game), perspective),
                         dict(scales), update=False)

    return columns_of, payload['weights']


def test_the_shipped_bishop_costs_more_than_its_weight_says():
    """The specific wrong number, pinned.

    `Bishop` is +0.0669 and `Pawn` is +0.0616 in the shipped file, which
    reads as 1.1 pawns. The price charged for losing a bishop is about
    1.6 pawns, because the other half of the pair adds roughly +0.038.
    The test asserts the ORDERING -- that the measured price exceeds the
    bare weight -- rather than a figure, since the figure is a
    measurement with noise in it.
    """
    from experiments.variants import make_engine

    from lgref.experiments.validate import removal_price

    columns_of, weights = _columns_and_weights()
    prices = removal_price(lambda: make_engine('full', max_turns=400),
                           columns_of, weights, _remove,
                           ('Pawn', 'Bishop'), trials=12, seed=9)
    bishop, samples = prices['Bishop']
    assert samples > 0
    assert bishop > weights.get('Bishop', 0.0) * 1.2, (
        'the measured price {0:+.4f} is no larger than the bare weight '
        '{1:+.4f}; if the pair has stopped being collinear, say so in '
        'the handoff rather than deleting this'.format(
            bishop, weights.get('Bishop', 0.0)))
    assert bishop > prices['Pawn'][0] * 1.3


def test_the_pieces_own_columns_are_found_by_removing_them():
    """No list of piece names anywhere: which columns belong to a piece
    is read off what moves when the piece is taken away."""
    from experiments.variants import make_engine

    from lgref.experiments.validate import removal_columns

    columns_of, _weights = _columns_and_weights()
    table = removal_columns(lambda: make_engine('full', max_turns=400),
                            columns_of, _remove,
                            ('Pawn', 'Bishop', 'Rook'), trials=10,
                            seed=9)
    own = exclusive_columns(table)
    assert 'Bishop' in own['Bishop']
    assert 'Rook' in own['Rook']
    for label in ('Pawn', 'Bishop', 'Rook'):
        assert 'Covers' not in own[label], (
            'coverage was attributed to {0}; rescaling it would move '
            'every other price too'.format(label))


def test_the_loader_and_the_probes_rebuild_the_same_extractor():
    """Three scripts had their own copy of this reconstruction and one
    of the copies was wrong, which is how a run was raced on the feature
    set it was supposed to be replacing."""
    import json

    from lgref.experiments.features import royal_chess_extractor

    path = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'td_royal_chess.json')
    payload = json.load(open(path))
    built = royal_chess_extractor(payload, path=path)
    from experiments.variants import make_engine

    engine = make_engine('full', max_turns=400)
    assert built(engine), 'the rebuilt extractor produced no features'
    for family in payload.get('drop_prefixes', ()):
        leaked = [name for _owner, name in built(engine)
                  if name.startswith(family)]
        assert not leaked, 'the ablation was not replayed: {0}'.format(
            leaked)


def test_every_new_instrument_runs_on_the_other_game():
    """THE GENERALITY CLAIM, for the instruments added in this session.

    Each of them takes its game knowledge as an injected callable, so
    the test is whether they actually run on the second game rather than
    whether they avoid saying "bishop". m,n,k has no material and no
    captures, so the honest answers differ: there is nothing to remove
    and nothing to rescue. That must come back as an empty result rather
    than an exception -- an instrument that crashes on a game without
    captures is not general, it is untested.
    """
    from lgref.experiments.bootstrap import normalise, run, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import mnk as mnk_features
    from lgref.experiments.features import with_threshold
    from lgref.experiments.mnk import MNK
    from lgref.experiments.record import audit, fatal, observed, silent
    from lgref.experiments.replicate import shared_variance
    from lgref.experiments.validate import (exchange_opinions,
                                            removal_price, rescue_oracle,
                                            rescuable_losses,
                                            turn_leverage)

    extractor = with_threshold(mnk_features)
    scales = {}

    def make_game(*_args, **_kwargs):
        return MNK(m=4, n=4, k=3)

    history = run(make_game, extractor, rounds=1, games_per_round=4,
                  alpha=0.08, epsilon=0.3, seed=1, max_turns=40,
                  scales=scales, budget_seconds=20.0)
    weights = history[-1].weights

    def columns_of(game, perspective):
        return normalise(differentials(extractor(game), perspective),
                         dict(scales), update=False)

    def evaluate(game, perspective):
        return value(weights, columns_of(game, perspective))

    # The payload audit: a run on this game must pass its own check.
    payload = {'weights': weights, 'scales': scales,
               'extractor': 'with_threshold(mnk)', 'dropped': [],
               'drop_prefixes': []}
    assert not fatal(audit(payload))

    # Which columns restate each other -- no game knowledge at all.
    vectors = []
    game = make_game()
    while True:
        turns = game.get_all_legal_turns()
        if not turns or game.is_game_over():
            break
        game.execute_turn(turns[0])
        vectors.append(differentials(extractor(game),
                                     game.current_player))
    explained = shared_variance(vectors)
    assert explained and all(0.0 <= value_ <= 1.0
                             for value_ in explained.values())

    # Which column decides a move.
    leverage = turn_leverage(make_game, columns_of, weights, trials=3,
                             seed=1, max_setup=6)
    assert leverage, 'no column moved on any turn of a played game'

    # Does a feature fire at all?
    summary = observed(lambda state: differentials(extractor(state),
                                                   'white'),
                       [make_game()])
    assert isinstance(silent(summary), list)

    # NOTHING TO REMOVE AND NOTHING TO RESCUE, reported as such.
    def never(_game, _label, _rng):
        return False

    prices = removal_price(make_game, columns_of, weights, never,
                           ('Anything',), trials=2, seed=1, max_setup=4)
    assert prices['Anything'][1] == 0

    assert exchange_opinions(make_game, evaluate, lambda *_a: 'any',
                             trials=2, seed=1, max_setup=4) == {}

    rescuable, lost, positions = rescuable_losses(
        make_game, rescue_oracle, trials=3, seed=1, max_setup=6)
    assert (rescuable, lost, positions) == (0, 0, 0), (
        'a game with no captures reported rescuable losses')
