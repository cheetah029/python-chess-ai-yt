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
    royals = {}
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
                # A REFERENCE CATEGORY, dropped on purpose. A queen is
                # in exactly one form, so the form indicators sum to the
                # identity count: RoyalQueen == sum of RoyalQueenForm:*.
                # That is an EXACTLY collinear set, and a linear model
                # fitted on it has infinitely many equally good weight
                # vectors -- gradient descent picks whichever one its
                # path reaches, so the split between the identity and
                # its forms is arbitrary rather than learned.
                #
                # Measured consequence: removing the `Royal` aggregate
                # (also exactly collinear) moved the king's effective
                # value from +0.069 to +0.495 while pushing the rook
                # from +0.201 to +0.095 -- it relocated the
                # arbitrariness instead of removing it. Dropping one
                # level is the standard fix: base form is the reference,
                # so the surviving form features mean "in this form
                # RATHER THAN base" and the identity carries the
                # material.
                if form != 'Queen':
                    counts[(colour, identity + 'Form:' + form)] += 1
            else:
                counts[(colour, form + '*royal' if royal else form)] += 1
            if royal:
                royals[colour] = royals.get(colour, 0) + 1
            # NO `Royal` AGGREGATE. It was exactly King*royal plus
            # RoyalQueen, and an exactly collinear feature does not add
            # information -- it SPLITS the signal, with the split
            # decided by the optimiser's path rather than by the game.
            # Measured consequence: TD learned King*royal +0.419 and
            # Royal -0.144, so the king's effective value came out
            # +0.274, BELOW a rook at +0.860 -- for a piece whose loss
            # is half the terminal condition. Removing the redundancy
            # removes the cancellation.

    # A CONJUNCTIVE TERMINAL CONDITION NEEDS A THRESHOLD FEATURE, and
    # this is a general point rather than a Royal Chess detail. The game
    # ends when BOTH royals are captured (RULEBOOK.md), so losing one
    # royal is survivable and losing the second is immediate defeat. A
    # LINEAR evaluation over royal counts cannot express that: it
    # charges the same for the first loss as for the second, so it
    # cannot represent the conjunction at all.
    #
    # Measured consequence, and exactly the blunder a human reported:
    # the learned evaluation valued the king at +0.0165 and a knight at
    # +0.0423, so trading its own king for a knight read as a GAIN.
    # `King*royal` is sparse as well -- zero whenever both kings live,
    # which is nearly always -- so its linear weight is starved of
    # samples on top of being the wrong shape.
    #
    # `DownToOneRoyal` is an INDICATOR, not a count, which is what lets
    # a linear model represent a threshold. For any game whose terminal
    # condition is a conjunction of k facts, "how many already hold" is
    # derivable from the description -- `objective.py` reads exactly
    # that chain -- and encoding it categorically rather than linearly
    # is what makes the conjunction expressible.
    for colour in royals:
        counts[(colour, 'DownToOneRoyal')] = (
            1 if royals[colour] == 1 else 0)

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


def with_mobility(extractor):
    """`extractor` plus the mover's legal-turn count.

    SUPPLIED AS A CANDIDATE, WITH NO CLAIM ABOUT ITS VALUE. An earlier
    version of this docstring argued that the count is "distance from a
    declared loss condition" because a player with no legal turn loses.
    THAT REASONING IS WRONG and is worth recording. A termination
    condition is an INDICATOR, not a gradient: "no legal turn" separates
    0 from n > 0 and says nothing whatever about 1 versus 100. In this
    game the condition is also reached mainly through the tiny-endgame
    rule, which exists to terminate, so it is rare besides. No mobility
    gradient follows from the rules, and the same applies to royal count:
    "both royals captured" says nothing about 2 alive versus 1.

    So the weight is LEARNED and nothing here asserts a sign. On an
    m,n,k game a full board is a draw, so the same count means something
    different there -- which is precisely why it cannot be a constant.

    A LIMITATION OF THIS PARTICULAR FEATURE, measured. Only the MOVER's
    count is recorded, so the mover-relative differential is always
    +n and never an actual difference between the players: it is closer
    to a game-PHASE signal ("how many options remain at all") than to a
    mobility advantage. TD gave it a weight of +0.54 on m,n,k, slightly
    above the win-condition feature, which is consistent with it being
    used to encode how far along the game is. A true differential would
    need the opponent's count, which costs a clone and a move
    generation per state. Stated rather than hidden, because the name
    promises more than the implementation delivers.
    """
    def extract(state):
        feats = dict(extractor(state))
        owner = getattr(state, 'current_player', None)
        if owner is not None:
            feats[(owner, 'Mobility')] = len(state.get_all_legal_turns())
        return feats
    return extract


def capture_ranker(weights, scales):
    """Rank a capture by the LEARNED weight of what it takes.

    DOMAIN-SPECIFIC, and that is why it lives here rather than in the
    search. Ranking captures among themselves needs to know what a
    capture removes, which means reading this game's pieces; the search
    only needs "captures before quiet moves", which it can get from
    `search.generic_capture_rank`.

    It introduces no value judgement of its own -- the numbers are the
    ones TD derived from terminal outcomes -- and it reads only the
    destination square's occupant, so ordering stays free of
    simulation.
    """
    def rank(engine, turn):
        if not getattr(turn, 'is_capture', False):
            return 0.0
        target = getattr(turn, 'to_sq', None)
        board = getattr(engine, 'board', None)
        if target is None or board is None:
            return 1.0
        try:
            piece = board.squares[target[0]][target[1]].piece
        except Exception:
            return 1.0
        if piece is None:
            return 1.0
        name = type(piece).__name__
        if getattr(piece, 'is_royal', False):
            candidates = ('RoyalQueen', name + '*royal')
        elif getattr(piece, 'is_transformed', False):
            candidates = ('PromotedQueen',)
        else:
            candidates = (name,)
        for candidate in candidates:
            if candidate in weights:
                return abs(weights[candidate]) / max(
                    scales.get(candidate, 1.0), 1.0)
        return 0.1      # an unweighted capture still beats a quiet move
    return rank


def load_royal_chess_searcher(path, budget=2.5, max_depth=8,
                              quiescence=2):
    """A `search.Searcher` over weights saved by a TD run.

    THE SEARCH EVALUATION OMITS MOBILITY, on a measured basis:
    `with_mobility` calls `get_all_legal_turns()`, which made mobility
    97% of the cost of an evaluation (0.567 ms of 0.584 ms) while TD
    gave it an effective weight of 0.0016, the smallest of any feature.
    The learner keeps the full extractor; the search uses the cheap one.
    If that weight ever rises materially, re-make the trade rather than
    inheriting it.
    """
    import json

    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.search import Searcher

    with open(path) as handle:
        payload = json.load(handle)
    weights = payload['weights']
    scales = payload.get('scales', {})

    def evaluate(engine, perspective):
        raw = differentials(royal_chess(engine), perspective)
        return value(weights, normalise(raw, dict(scales), update=False))

    return Searcher(evaluate, capture_ranker(weights, scales),
                    max_depth=max_depth, budget=budget,
                    quiescence=quiescence)
