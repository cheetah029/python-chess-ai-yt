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


def test_a_jump_capture_counts_as_tactical_and_is_priced_by_its_victim():
    """THE SECOND CAPTURE MECHANIC, which three search paths missed.

    A knight may capture by jumping OVER a piece. Nothing is taken at
    the square it lands on, so the turn reports `is_capture = False` and
    names its victim in `jump_choice` -- and quiescence, move ordering
    and futility pruning all asked `is_capture` directly. Quiescence
    therefore never resolved one: a position where the opponent can take
    a knight by jumping it was evaluated as quiet.

    Found by replaying a reviewer's game. `10... Nf4-d6j` takes the
    white knight on e5; the jumped square is e5; the turn reports
    `is_capture=False, jump_choice=(3, 4)`.

    A DECLINED offer must NOT count: the engine emits both variants of
    such a jump, and only the one with `jump_choice` set takes anything.
    """
    import json

    from lgref.experiments.features import (capture_ranker,
                                            royal_chess_tactical)

    class _Jump(object):
        def __init__(self, choice):
            self.is_capture = False
            self.from_sq = (4, 5)
            self.to_sq = (2, 3)
            self.jump_choice = choice
            self.has_jump_offer = True

    accepted, declined = _Jump((3, 4)), _Jump(None)
    assert royal_chess_tactical(accepted)
    assert not royal_chess_tactical(declined)

    class _Square(object):
        def __init__(self, piece):
            self.piece = piece

    class _Piece(object):
        is_royal = False
        is_transformed = False
        color = 'white'

    class _Knight(_Piece):
        pass

    class _Board(object):
        def __init__(self):
            empty = [[_Square(None) for _ in range(8)] for _ in range(8)]
            empty[3][4] = _Square(_Knight())
            self.squares = empty

    class _Engine(object):
        current_player = 'black'
        board = _Board()

    path = os.path.join(os.path.dirname(__file__), '..', 'weights',
                        'td_royal_chess.json')
    payload = json.load(open(path))
    rank = capture_ranker(payload['weights'], payload.get('scales', {}))
    engine = _Engine()
    # THE VICTIM IS ON THE JUMPED SQUARE, not the landing square. Read
    # at `to_sq` the square is empty and the ranker fell through to its
    # fallback, so a knight taken by a jump ordered like a pawn.
    _Knight.__name__ = 'Knight'
    knight_rank = rank(engine, accepted)
    assert knight_rank > 0.1, (
        'a jumped knight ranked {0:.4f}, the unweighted fallback -- the '
        'victim was looked for at the landing square'.format(knight_rank)) 
    assert rank(engine, declined) == 0.0


def test_quiescence_searches_whatever_the_predicate_calls_tactical():
    """The predicate has to reach quiescence, not just the ranker.

    Checked with a stub game so the assertion is about the search and
    not about any engine: a turn that sets no `is_capture` but is
    declared tactical must still be resolved.
    """
    from lgref.experiments.search import Searcher

    class _Turn(object):
        def __init__(self, name, tactical):
            self.name = name
            self.is_capture = False
            self.tactical = tactical

    taking, quiet = _Turn('take', True), _Turn('quiet', False)

    class _Game(object):
        def __init__(self, depth=0):
            self.depth = depth
            self.current_player = 'a' if depth % 2 == 0 else 'b'

        def get_all_legal_turns(self):
            return [] if self.depth >= 2 else [taking, quiet]

        def is_game_over(self):
            return self.depth >= 2

        winner = None

        def copy(self):
            return _Game(self.depth)

        def execute_turn(self, turn):
            self.depth += 1
            self.current_player = 'a' if self.depth % 2 == 0 else 'b'

    played = []

    class _Watched(_Game):
        def execute_turn(self, turn):
            played.append((self.depth, turn.name))
            _Game.execute_turn(self, turn)

        def copy(self):
            return _Watched(self.depth)

    def evaluate(_game, _perspective):
        return 0.5

    searcher = Searcher(evaluate, max_depth=1, quiescence=2,
                        use_tt=False,
                        is_tactical=lambda turn: turn.tactical)
    searcher.can_undo = False
    searcher.choose_turn([taking, quiet], _Watched())
    # BELOW the frontier -- depth 1 is where quiescence runs, and the
    # only turn it may play there is the one declared tactical.
    assert (1, 'take') in played, (
        'quiescence never played the turn declared tactical, so it was '
        'treated as quiet: {0}'.format(played))
    assert (1, 'quiet') not in played, (
        'quiescence played a quiet turn: {0}'.format(played))


class _StubTurn(object):
    """Module level so `clone_with_turns` can pickle it. A stub defined
    inside a test function cannot be, and the failure arrives as an
    AttributeError from deep inside the cloner."""

    def __init__(self, name, tactical):
        self.name = name
        self.is_capture = tactical


_GRAB = _StubTurn('grab', True)
_QUIET = _StubTurn('quiet', False)


class _StubGame(object):
    """Two columns with different reachability: one moves only when
    something is taken, the other on any quiet turn. COUNTERS rather
    than a single "last move played", because the random setup plies run
    first and a single slot let a setup capture masquerade as a free
    swing -- which is exactly the confusion the instrument exists to
    avoid."""

    current_player = 'me'
    winner = None

    def __init__(self):
        self.grabs = 0
        self.quiets = 0

    def get_all_legal_turns(self):
        return [_GRAB, _QUIET]

    def is_game_over(self):
        return False

    def execute_turn(self, turn):
        if turn.is_capture:
            self.grabs += 1
        else:
            self.quiets += 1


def _stub_columns(game, _perspective):
    return {'OnlyByCapture': float(game.grabs),
            'Lever': float(game.quiets)}


def test_a_free_turn_that_swings_a_column_is_distinguished_from_a_capture():
    """FREE LEVERAGE is the dangerous kind, and the reason is asymmetry.

    A piece count cannot be moved without a capture -- taking something
    off the board costs the opponent a turn. A column the opponent can
    swing just as far with a turn that takes NOTHING is a lever, and an
    agent that believes it will spend real material to stop them pulling
    it.

    That is what four of the reviewer's blunders were: `RoyalForm:Rook`
    carries +0.1467, the opponent can cancel the differential with a
    transformation, and the search priced that phantom threat above a
    pawn and gave the pawn away instead.

    `max_setup=1` here on purpose: every instrument in `validate` passed
    its `max_setup` straight to `randint(4, ...)`, so asking for a
    shallow sample raised `empty range` instead of measuring. This test
    found that.
    """
    from lgref.experiments.validate import free_leverage, lever_columns

    weights = {'OnlyByCapture': 1.0, 'Lever': 1.0}
    free = free_leverage(_StubGame, _stub_columns, weights, trials=3,
                         seed=1, max_setup=1)
    assert 'Lever' in free, free
    assert 'OnlyByCapture' not in free, (
        'a column only a capture can move was counted as free leverage')

    # The bar is a MEASURED price, not a chosen number.
    prices = {'Thing': (0.5, 10), 'Nothing': (0.0, 0)}
    assert lever_columns(free, prices) == ['Lever']
    expensive = {'Thing': (9.9, 10)}
    assert lever_columns(free, expensive) == [], (
        'a swing smaller than the cheapest piece was flagged')


def test_the_lever_bar_is_silent_when_the_game_has_nothing_to_price():
    """m,n,k has no material, so there is no cheapest piece and no bar.
    The honest answer is to flag nothing rather than to invent one."""
    from lgref.experiments.validate import lever_columns

    assert lever_columns({'Anything': (1.0, 9.0, 5)}, {}) == []
    assert lever_columns({'Anything': (1.0, 9.0, 5)},
                         {'X': (0.0, 0)}) == []


def test_the_blunder_metric_has_two_halves_and_they_disagree():
    """`rescuable_losses` MEASURES ONLY FAILURE TO RESCUE.

    It asks whether a piece already in danger was saved. It says nothing
    about walking a safe piece INTO danger, because such a piece was
    never in the at-risk set -- and that is most of what a reviewer
    actually reported: a pawn pushed onto a defended square, then
    another, then another.

    Measured, the two disagree completely: ablating the family that
    caused those pushes moved `rescuable_losses` from 49.4% to 50.0%,
    which is nothing, while winning its match 14-5. The rate was flat
    because it was measuring the other half.

    This test pins the DISTINCTION rather than either number: a position
    where a piece is already in danger belongs to the rescue metric and
    must not be counted by the avoidance one, or the two double-count
    and a fix to one looks like a fix to both.
    """
    import inspect

    from lgref.experiments import validate

    source = inspect.getsource(validate.avoidable_losses)
    assert 'at_risk' in source and 'not in at_risk' in source, (
        'the avoidance metric no longer excludes pieces that are already '
        'in danger, so it double-counts the rescue metric')


def test_the_avoidance_rate_is_conditional_on_the_move_actually_made():
    """A DENOMINATOR BUG, and it is the kind that produces a confident
    wrong number rather than an error.

    The first version counted every position in which a quiet move
    EXISTED, then only scored the ones where the policy chose one. A
    uniform mover picks a capture or a rescue most of the time, so those
    positions landed in the denominator as though the mover had made a
    safe quiet move -- which diluted random play's rate to 2.7% against
    a true base rate of about 5%.

    Validated by hand afterwards: 15.6% of available quiet moves of safe
    pieces land somewhere the opponent can capture, and 33.9% of those
    had a safe alternative for the same piece, so a uniform mover should
    score 15.6% x 33.9% = 5.3%. The fixed metric reports 3.8% on 156
    samples, which is within one standard error of that.
    """
    import inspect

    from lgref.experiments import validate

    source = inspect.getsource(validate.avoidable_losses)
    body = source[source.index('if index is None'):]
    assert 'opportunities += 1' in body, (
        'the denominator is incremented before the chosen move is known '
        'to qualify, which dilutes every rate this returns')


def test_the_avoidance_metric_finds_a_piece_walking_into_a_capture():
    """End to end on the real game, with a policy that deliberately
    walks into danger -- so a zero here means the instrument is broken
    rather than the agent being perfect."""
    from experiments.variants import make_engine

    from lgref.experiments.features import royal_chess_victim_square
    from lgref.experiments.fastcopy import clone_with_turns
    from lgref.experiments.search import generic_is_tactical
    from lgref.experiments.validate import avoidable_losses

    def suicidal(game, _rng):
        """Prefer a quiet move onto a square the opponent can capture."""
        turns = game.get_all_legal_turns()
        for index, turn in enumerate(turns):
            if generic_is_tactical(turn):
                continue
            landing = getattr(turn, 'to_sq', None)
            if landing is None:
                continue
            sim, simulated = clone_with_turns(game, turns)
            sim.execute_turn(simulated[index])
            if any(royal_chess_victim_square(reply) == landing
                   for reply in sim.get_all_legal_turns()):
                return turn
        return turns[0]

    chances, lost, _positions = avoidable_losses(
        lambda: make_engine('full', max_turns=400), suicidal, trials=12,
        seed=5, victim_square=royal_chess_victim_square)
    assert chances > 0, 'no quiet move of a safe piece was ever chosen'
    assert lost > 0, (
        'a policy that deliberately walks into captures scored zero '
        'avoidable losses, so the instrument is not measuring it')
