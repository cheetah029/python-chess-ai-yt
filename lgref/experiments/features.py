"""Per-game feature extractors, kept OUT of the inference machinery.

WHY THIS FILE EXISTS. `discover.py` had quietly become a Royal Chess
module. Its own docstring claimed "no piece name is hard-coded" while
the code contained `range(8)` twice, `from piece import Queen`, the
literal tuple `('rook', 'bishop', 'knight')`, and reads of `is_royal`
and `captured_pieces`. A framework whose stated purpose is to handle
games it has not seen cannot have the case study baked into its
estimator, and a docstring asserting otherwise is worse than no
docstring.

THE SEPARATION. Domain knowledge belongs in an EXTRACTOR, which is
injected. The inference -- cluster-aggregated effect sizes, standard
errors, stratified conditioning, the factorial design -- never learns
what a bishop is.

THE PROTOCOL, which is the whole interface:

    extractor(state) -> {(owner, name): value}

`owner` identifies the player the quantity belongs to, or is any member
of `NEUTRAL_OWNERS` for something belonging to nobody. `name` is a
string generated from the state, not chosen by a researcher. `value` is
numeric. `discover.differentials` turns that into mover-relative
features and nothing downstream needs to know the game.

WHAT STAYS DOMAIN-SPECIFIC, legitimately. An extractor is where a
game's vocabulary lives, so `royal_chess` may read `is_royal` and
`captured_pieces` -- those are that game's state. What matters is that
it is one named function behind a documented protocol, swappable for
another game's, rather than a hard-coded assumption inside the
estimator. `mnk` is the second implementation, and it exists so that
"this generalises" is a thing the test suite checks rather than a thing
this docstring claims.
"""

import collections

#: Owners that belong to no player. Royal Chess's boulder reaches an
#: extractor as the STRING 'none', not `None`, which once made a neutral
#: piece score -1 for both players at the same time.
NEUTRAL_OWNERS = frozenset((None, 'none', 'neutral', ''))


def royal_chess(engine):
    """{(colour, name): count} for the case study.

    DOMAIN-SPECIFIC BY DESIGN, and isolated here for that reason.

    Counted by IDENTITY, not by form. A queen keeps its identity through
    a Transformation (RULEBOOK.md: "A marker indicates which piece is
    the queen"), but a transformed queen is an INSTANCE of its form's
    class -- so reading `type(piece).__name__` reported a royal queen in
    knight form as a knight, and a Transformation that captures nothing
    looked like a capture plus a gain.

    The capture record is included because it gates which
    TRANSFORMATIONS ARE LEGAL, making it current legal-move-determining
    state rather than history. Without it, a threshold quantity ("a
    friendly bishop has been captured") had no feature at all.
    """
    from piece import Queen

    counts = collections.Counter()
    board = engine.board
    rows = len(board.squares)
    for row in range(rows):
        cols = len(board.squares[row])
        for col in range(cols):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            colour = getattr(piece, 'color', None)
            form = type(piece).__name__
            royal = getattr(piece, 'is_royal', False)
            queen_kind = (isinstance(piece, Queen)
                          or getattr(piece, 'is_transformed', False))
            if queen_kind:
                identity = 'RoyalQueen' if royal else 'PromotedQueen'
                counts[(colour, identity)] += 1
                counts[(colour, identity + 'Form:' + form)] += 1
            else:
                counts[(colour, form + '*royal' if royal else form)] += 1
            if royal:
                counts[(colour, 'Royal')] += 1

    # The forms a queen could take are read from the engine's own
    # mapping where it exposes one, rather than restated here.
    forms = sorted(getattr(board, 'TRANSFORM_TARGETS',
                           ('rook', 'bishop', 'knight')))
    for colour, names in getattr(board, 'captured_pieces', {}).items():
        for form in forms:
            counts[(colour, 'FormAvailable:' + form)] = (
                1 if form in names else 0)
    return dict(counts)


def mnk(game):
    """{(player, name): count} for an m,n,k game.

    THE SECOND IMPLEMENTATION, and the reason it exists is that a single
    extractor proves nothing about generality.

    Features are derived from the game's OWN win condition rather than
    from anyone's idea of what matters in tic-tac-toe. `win_lines` is
    the set of k-in-a-row lines the rules declare winning, so:

      Marks        how many cells a player holds
      Line:j       lines holding exactly j of the player's marks and
                   none of the opponent's -- a line still winnable, j
                   steps along

    `Line:k-1` is "one move from winning", which no one told it; it
    falls out of reading the win condition. That is the same move
    `objective.py` makes for a GDL description, done here for an engine.
    """
    from lgref.experiments.mnk import win_lines

    counts = collections.Counter()
    players = {c for c in game.cells if c is not None}
    for player in players:
        counts[(player, 'Marks')] = sum(1 for c in game.cells
                                        if c == player)
    for line in win_lines(game.m, game.n, game.k):
        held = collections.Counter(game.cells[i] for i in line
                                   if game.cells[i] is not None)
        if len(held) != 1:
            continue                    # contested, so winnable by neither
        player, count = next(iter(held.items()))
        counts[(player, 'Line:{}'.format(count))] += 1
    # Players with no mark yet still need their zero, or the feature is
    # absent rather than zero and the comparison silently changes.
    for player in players:
        for j in range(1, game.k):
            counts.setdefault((player, 'Line:{}'.format(j)), 0)
    return dict(counts)
