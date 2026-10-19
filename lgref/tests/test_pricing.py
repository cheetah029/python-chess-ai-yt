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
