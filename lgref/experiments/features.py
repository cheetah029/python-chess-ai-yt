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
#: Re-exported from the estimator, which owns the convention. The
#: adapter depends on the general module and never the other way round.
from lgref.experiments.discover import NEUTRAL_OWNERS

#: Flags the IDENTITY encoding already consumes, so counting them again
#: would add an EXACTLY COLLINEAR feature. That is not a preference: a
#: piece is counted as `Royal` precisely when `is_royal` is set, and as
#: a queen identity precisely when `is_transformed` or `Queen` holds, so
#: `Flag:is_royal` would be the `Royal` count under a second name. An
#: exactly collinear feature does not add information, it SPLITS the
#: signal between two weights, with the split decided by the
#: optimiser's path rather than by the game -- measured once already,
#: when a `Royal` aggregate alongside `King*royal` dropped the king's
#: effective value below a rook's.
CONSUMED_FLAGS = frozenset(('is_royal', 'is_transformed'))



def royal_chess(engine, skip=()):
    """{(colour, name): count} for the case study.

    `skip` names feature-family prefixes the caller will discard, so the
    work of computing them can be skipped rather than done and thrown
    away. That was costing real time: the shipped agent ablates the
    relational and flag families, and filtering them out AFTER
    extraction left the expensive walks running. Measured at depth 3,
    early game: 17.3 seconds against 7.6 for the version without those
    families at all.

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

    skipped = tuple(skip or ())

    def wanted(prefix):
        """Is this family worth computing, or will the caller drop it?"""
        return not any(prefix.startswith(s) for s in skipped)

    counts = collections.Counter()
    #: (row, col) -> (owner, identity, piece). Built in the pass below
    #: so the threat pass can break its counts down BY PIECE, which is
    #: what turns a scalar "how many of mine are attacked" into "a rook
    #: of mine is attacked".
    where = {}
    flag_names = set()
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
                if royal:
                    # ONE ROYAL COUNT, not one feature per royal piece.
                    # The terminal condition is SYMMETRIC in the king and
                    # the royal queen -- you win by capturing both -- so
                    # the rules draw no distinction between them and the
                    # only signal TD has cannot either. Asking a linear
                    # model to split a symmetric quantity across two
                    # features does not learn anything; it allocates
                    # noise.
                    #
                    # Measured: two trainings differing only in seed put
                    # King*royal at +0.281 against RoyalQueen +0.236,
                    # and then at +0.100 against +0.160 -- the ORDERING
                    # REVERSED. A human reasonably objected that the
                    # king should not outrank the queen; the truthful
                    # answer is that the model never consistently held
                    # that view.
                    #
                    # The queen IS stronger than the king in play, but
                    # for reasons no count can see -- manipulation,
                    # transformation, the queen-as-bishop teleport
                    # escape. Those belong to the form and availability
                    # features, and that is where the difference should
                    # be learned if it is learnable at all.
                    identity = 'Royal'
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
                # Royal pieces all count as `Royal` above; a non-queen
                # royal is the king, and it is not given a feature of
                # its own for the symmetry reason recorded there.
                if royal:
                    counts[(colour, 'Royal')] += 1
                else:
                    counts[(colour, form)] += 1
            if colour not in NEUTRAL_OWNERS:
                stored = 'Royal' if royal else (
                    identity if queen_kind else form)
                where[(row, col)] = (colour, stored, piece)
                # EVERY BOOLEAN THE ENGINE KEEPS ON A PIECE, counted as
                # a feature, and the rule is mechanical rather than a
                # selection: whatever per-piece state this engine
                # maintains gets read, and a different game's flags get
                # read the same way. These are not decorations -- they
                # are legal-move-determining state, which is why they
                # are in the repetition hash (RULEBOOK.md) and in
                # `undo.PIECE_FLAGS`.
                #
                # It is also the only route by which the BISHOP's
                # offensive power becomes visible at all. The board's
                # threat cache excludes bishops entirely by design
                # ("Bishops are ignored entirely"), so a bishop
                # contributes nothing to `Covers` or `Attacked` and its
                # reactive-capture pin -- the thing that makes it an
                # active piece -- had no feature of any kind. That is a
                # second, independent reason `Bishop` learned -0.008.
                for flag, setting in (list(vars(piece).items())
                                      if wanted('Flag:') else ()):
                    if not isinstance(setting, bool):
                        continue
                    if flag in CONSUMED_FLAGS:
                        continue
                    flag_names.add(flag)
                    if setting:
                        counts[(colour, 'Flag:' + flag)] += 1
            # NO `Royal` AGGREGATE. It was exactly King*royal plus
            # RoyalQueen, and an exactly collinear feature does not add
            # information -- it SPLITS the signal, with the split
            # decided by the optimiser's path rather than by the game.
            # Measured consequence: TD learned King*royal +0.419 and
            # Royal -0.144, so the king's effective value came out
            # +0.274, BELOW a rook at +0.860 -- for a piece whose loss
            # is half the terminal condition. Removing the redundancy
            # removes the cancellation.

    # THE CONJUNCTIVE TERMINAL CONDITION IS NOW CARRIED BY THE
    # THRESHOLD SPLIT, so the explicit `DownToOneRoyal` indicator that
    # used to live here is gone.
    #
    # The game ends when BOTH royals are captured (RULEBOOK.md), so
    # losing one royal is survivable and losing the second is immediate
    # defeat. A LINEAR count cannot express that -- it charges the same
    # for the first loss as for the second -- which is why an indicator
    # was added, and the measured consequence of not having one was the
    # agent trading its own king for a knight.
    #
    # `with_threshold` now splits every count into `Has:` and `More:`,
    # and for a quantity that ranges over {0, 1, 2} that pair is a
    # COMPLETE encoding: `Has:Royal` is "at least one royal alive" and
    # `More:Royal` is "both alive". The conjunction is expressible
    # without any extra feature, and keeping `DownToOneRoyal` beside
    # them made it affinely dependent on `More:Royal` -- detected at
    # slope -1.00 over 285 positions, because royals number 1 or 2 in
    # every state that is not already decided.

    # THREAT AND VULNERABILITY, which is what makes the evaluation
    # non-flat in a quiet position. Measured before adding them: 93.7%
    # of legal moves TIED at the top score in agent self-play, because
    # every feature was a COUNT and no quiet move changes a count. The
    # agent could therefore only distinguish moves that won or lost
    # material inside the horizon, which is exactly the "plays tactics,
    # otherwise drifts" behaviour a human reported.
    #
    # Both quantities come from the game's own move generator rather
    # than from anyone's idea of what matters -- "how many of my pieces
    # could be captured next turn" and "how many of theirs could I
    # capture" -- so the PRINCIPLE generalises to any game with
    # captures. They are read from `threat_squares`, which the board
    # already computes and caches for move generation, so they cost
    # almost nothing; computing them from a fresh move generation would
    # have cost 0.54 ms a node, which is the mistake `with_mobility`
    # makes.
    #
    # PRESENT AS ZERO, not absent, and set OUTSIDE the try. A missing
    # feature is not the same as a zero one: `differentials` omits it
    # entirely, so the model sees nothing rather than "none", and a
    # weight fitted only on the positions where it happens to be
    # non-zero is fitted on a biased subsample. The same mistake was
    # caught and fixed for the m,n,k line counts.
    #
    # Outside, because inside the try a failure in the threat walk would
    # delete both features from the vector instead of zeroing them --
    # and an ABSENT feature is invisible to the loader's staleness
    # guard, which compares names, so the agent would quietly play
    # without them. Zeroing is the honest failure.
    if hasattr(board, 'update_threat_squares'):
        for side in ('white', 'black'):
            counts.setdefault((side, 'Attacked'), 0)
            counts.setdefault((side, 'Covers'), 0)
            counts.setdefault((side, 'Hanging'), 0)
    try:
        board.update_threat_squares()
        threatened = {}
        for row in range(rows):
            for col in range(len(board.squares[row])):
                piece = board.squares[row][col].piece
                if piece is None:
                    continue
                owner = getattr(piece, 'color', None)
                if owner in NEUTRAL_OWNERS:
                    continue
                for square in getattr(piece, 'threat_squares', ()) or ():
                    threatened.setdefault((square.row, square.col),
                                          set()).add(owner)
        for row in range(rows):
            for col in range(len(board.squares[row])):
                piece = board.squares[row][col].piece
                if piece is None:
                    continue
                owner = getattr(piece, 'color', None)
                if owner in NEUTRAL_OWNERS:
                    continue
                for attacker in threatened.get((row, col), ()):  # who hits it
                    if attacker == owner:
                        continue
                    # Counted against the piece's OWNER: one of their
                    # pieces stands on a square an enemy can reach.
                    counts[(owner, 'Attacked')] += 1
        # COVERAGE: how many distinct squares each side can reach. This
        # is the one feature here that changes with almost every quiet
        # move, which is the point -- `Attacked` alone doubled the share
        # of distinguishable moves from 9.6% to 19.7%, and four fifths
        # still tied.
        #
        # THE INSTRUMENT CAVEAT, because this is the feature #231 warns
        # about: coverage is mobility-like, and the ablated rules change
        # how many moves exist, so an agent that values it plays better
        # under high-mobility variants and an ablation would measure the
        # evaluation rather than the rule. Fine for an OPPONENT, not for
        # a sweep instrument -- and the weight is learned, so if it is
        # worth nothing it will read as nothing.
        covered = {}
        for row in range(rows):
            for col in range(len(board.squares[row])):
                piece = board.squares[row][col].piece
                if piece is None:
                    continue
                owner = getattr(piece, 'color', None)
                if owner in NEUTRAL_OWNERS:
                    continue
                for square in getattr(piece, 'threat_squares', ()) or ():
                    covered.setdefault(owner, set()).add(
                        (square.row, square.col))
        for owner, squares in covered.items():
            counts[(owner, 'Covers')] = len(squares)

        # RELATIONAL FEATURES: not "how many of mine are attacked" but
        # WHICH, and whether anything is defending it. The scalar
        # version cannot tell a hanging rook from a hanging pawn, and
        # the measured failure was exactly that shape -- over 40
        # positions with exhaustive 2-ply material truth the agent
        # declined nearly every hanging move (1/40) but MISSED winnable
        # material in 6 to 8 of the 28 positions where material was
        # winnable, and more depth did not fix it (regret 0.20 at depth
        # 2 against 0.17 at depth 4, a 14x compute increase).
        #
        # Three families, all read from the game's own move generator
        # and broken down by the engine's own identities, so no opinion
        # about which pieces matter enters:
        #
        #   Attacked:I   a piece of mine, of identity I, stands on a
        #                square an enemy can reach
        #   Hanging:I    the same, and NO piece of mine can reach that
        #                square -- undefended
        #   Threatens:I  how many enemy pieces a piece of mine of
        #                identity I can reach -- the offensive half, and
        #                keyed on the ATTACKER because keying it on the
        #                target made it exactly -Attacked:I
        #
        # `Hanging` is separable from `Attacked` only because the
        # engine's threat cache includes friendly-occupied squares,
        # which was checked rather than assumed: 64 of 153 threat
        # entries in a sampled midgame pointed at a friendly piece.
        # THE AGGREGATE IS COMPUTED FIRST, and separately, because it
        # must survive the ablation that removes the per-identity
        # families. It did not: it lived inside the loop below, which
        # the `skip` guard short-circuits, so the feature was silently
        # zero in every training run that used it -- `scale` came back
        # 0.0000 in all three seeds, which is what gave it away.
        for (row, col), (owner, _identity, _piece) in where.items():
            reachers = threatened.get((row, col), ())
            if any(o != owner for o in reachers) and owner not in reachers:
                counts[(owner, 'Hanging')] += 1

        identities = set()
        for (row, col), (owner, identity, _piece) in where.items():
            if not (wanted('Attacked:') or wanted('Hanging:')):
                break
            identities.add(identity)
            reachers = threatened.get((row, col), ())
            hostile = [o for o in reachers if o != owner]
            if not hostile:
                continue
            counts[(owner, 'Attacked:' + identity)] += 1
            if owner not in reachers:
                counts[(owner, 'Hanging:' + identity)] += 1
                # (the aggregate is counted above, outside this loop)
                # THE AGGREGATE, kept when the per-identity families are
                # ablated. Measured with a value-free blunder metric:
                # the agent leaves 47.5% of RESCUABLE pieces to die --
                # pieces an enemy turn can take, which had a legal move
                # to a square no enemy turn reaches. Every candidate
                # scored 47-51%, so it is not the weights.
                #
                # The lean set has `Attacked`, which counts pieces an
                # enemy can reach whether or not anything defends them.
                # "Attacked AND undefended" is the quantity that
                # distinguishes a trade from a gift, and it had no
                # feature at all. ONE aggregate, not the ten per-identity
                # columns that were added all at once and measurably
                # hurt.

        # THREATENS IS KEYED ON THE ATTACKER, and getting that wrong
        # made the whole offensive family worthless. The first version
        # counted `Attacks:<target identity>` for the attacking side --
        # which records the SAME EVENT as `Attacked:<identity>` on the
        # other side, so after differencing it was exactly
        # `-Attacked:<identity>`. An affine-dependence check found all
        # five pairs at slope -1.00 over 285 positions. The family
        # added to fix "does not attack very well" carried no
        # information whatsoever.
        #
        # Keyed on the attacker it is a different quantity: "my rook can
        # reach something of theirs", not "their rook is reachable".
        for (row, col), (owner, _identity, piece) in where.items():
            if not wanted('Threatens:'):
                break
            squares = getattr(piece, 'threat_squares', ()) or ()
            reach = 0
            for square in squares:
                target = where.get((square.row, square.col))
                if target is not None and target[0] != owner:
                    reach += 1
            if reach:
                counts[(owner, 'Threatens:' + _identity)] += reach
        for side in ('white', 'black'):
            for identity in identities:
                for family in ('Attacked:', 'Hanging:', 'Threatens:'):
                    if wanted(family):
                        counts.setdefault((side, family + identity), 0)
    except AttributeError:
        # A game without this cache simply omits them. NARROW on
        # purpose: `except Exception` here swallowed every bug in the
        # walk above and the only symptom was two features quietly
        # missing from the vector.
        pass

    # PRESENT AS ZERO for every flag SEEN ANYWHERE on the board, not
    # just the ones currently set. A flag that happens to be false for
    # both sides must read 0 rather than vanish, for the same reason as
    # the threat features: `differentials` omits an absent feature, so a
    # weight fitted only where it is non-zero is fitted on a biased
    # subsample.
    if wanted('Flag:'):
        for side in ('white', 'black'):
            for flag in flag_names:
                counts.setdefault((side, 'Flag:' + flag), 0)

    # `FormAvailable:X` IS GONE, because it was the piece count under a
    # second name. A queen may take a form only once a friendly piece of
    # that type has been captured (RULEBOOK.md), and each side starts
    # with exactly two of each -- and a promotion yields a queen, never
    # another rook, bishop or knight, so the starting count is also the
    # maximum. So availability is exactly `count < 2`: a deterministic
    # function of a feature already present, carrying no information of
    # its own.
    #
    # It was not harmless. In DIFFERENTIAL space the constant cancels,
    # which makes the count, `Missing:X` and `FormAvailable:X` exactly
    # dependent as a TRIPLE -- `X = -Missing:X - FormAvailable:X` --
    # and a pairwise dependence check cannot see a three-way relation.
    # What it saw instead was `Bishop` paired with
    # `FormAvailable:bishop`, and the decorrelation pass dropped
    # `Bishop`: the actual material count, in favour of a thresholded
    # restatement of it. Removing the family removes the triple.
    #
    # The transformation rule is still represented -- by the count it
    # was always a function of.
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


def generic(engine):
    """Features from the MOVE PROTOCOL ALONE -- no board, no piece list.

    Built to answer a direct challenge: that the per-game extractors are
    hand-picked, and `Attacked` / `Covers` in particular are someone's
    idea of what matters in chess. This one cannot be, because it reads
    only what every engine in this framework must already provide:
    `get_all_legal_turns()`, `current_player`, and whatever
    `mcts.describe` can see on a turn. It walks no board and names no
    piece type.

    WHAT IT MEASURES, all derived rather than chosen:

        Mobility      how many legal turns exist
        Reach         how many DISTINCT destinations they lead to
        Moves:N       turns belonging to each piece identity N, which is
                      a per-piece mobility
        Captures:N    how many of those are captures -- the offensive
                      quantity, per piece
        Type:T        turns of each turn type the engine declares

    Piece identities come from the turn, so they are the engine's own
    names; on a game whose turns are plain data (m,n,k's are integers)
    the per-identity families are simply absent and only `Mobility` and
    `Reach` remain.

    THE STRUCTURAL LIMIT, and it is the honest answer to why per-game
    adapters exist at all: an engine generates legal turns only for the
    PLAYER TO MOVE. So everything here is mover-relative and there is no
    opponent-side counterpart to difference against -- the differential
    of a mover-only feature is always +n rather than a comparison, the
    same limitation `with_mobility` records. A SYMMETRIC evaluation
    needs both sides' state at once, and the only thing that exposes
    that is the board, which the protocol does not require an engine to
    have. That is a property of the protocol, not a shortcut taken here,
    and the cost of it is measured rather than asserted: see
    `docs/spec/generic-vs-adapter.md`.
    """
    from lgref.experiments.mcts import describe

    counts = collections.Counter()
    mover = getattr(engine, 'current_player', None)
    if mover is None:
        return {}
    try:
        turns = engine.get_all_legal_turns()
    except Exception:
        return {}
    counts[(mover, 'Mobility')] = len(turns)
    destinations = set()
    for turn in turns:
        description = describe(turn)
        if isinstance(description, tuple) and len(description) >= 4:
            turn_type, name, _from_sq, to_sq = description[:4]
            if turn_type is not None:
                counts[(mover, 'Type:{0}'.format(turn_type))] += 1
            if name is not None:
                counts[(mover, 'Moves:{0}'.format(name))] += 1
                if getattr(turn, 'is_capture', False):
                    counts[(mover, 'Captures:{0}'.format(name))] += 1
            destinations.add(to_sq if to_sq is not None else description)
        else:
            # Plain-data turns: the destination IS the description.
            destinations.add(description)
    counts[(mover, 'Reach')] = len(destinations)
    return dict(counts)


def with_threshold(extractor):
    """Every count KEPT, plus a flag for having none of it.

        X            the count itself, unchanged
        Missing:X    1 if there are none, else 0

    THIS IS THE SECOND PARAMETERISATION, and the first one made the
    agent measurably worse. It emitted `Has:X` (at least one) and
    `More:X` (how many beyond the first) and DROPPED the count. That
    prices the step at zero, which was the point -- and it also moves
    almost all the weight onto the threshold, which only fires when the
    last one is gone. Measured against the parameterisation it replaced:

        cost of losing one piece, holding another of its kind
        piece    count (old)   More: only (new)
        Rook          0.5522             0.1712   3.2x weaker
        Knight        0.2140             0.0413   5.2x weaker

    Losing one of two rooks is the COMMON midgame case, and its price
    fell by three times, because most of a rook's value had moved into
    `Has:Rook` -- a feature that cannot change while you still hold one.
    On the material harness, misses went from 8 of 28 to 14 of 28 and
    mean regret from 0.23 to 0.47. Adagrad makes it worse rather than
    better: `Has:` is sparse, so it takes large steps and absorbs the
    weight, while the dense `More:` anneals small.

    Keeping the count restores uniform marginal pricing -- every unit
    costs the same, which is what a count is for -- and `Missing:` adds
    the one thing a count cannot say: that going to NONE is different in
    kind. Going from two bishops to one costs a bishop; going from one
    to none also removes the reactive-capture pin, because there is no
    bishop left to arm it.

    NOT COLLINEAR for a count that reaches two: with X over {0, 1, 2},
    `Missing:X` is (1, 0, 0), which no line through the first two points
    predicts at X = 2. For a count that never exceeds one it IS
    collinear, and that is handled by `decorrelate`, from data, rather
    than by a list of exceptions here.

    The split is done PER OWNER, before differencing, so `Missing:`
    lands in {-1, 0, +1} and reads "they have none of these and I do".
    """
    # FORWARD THE SKIP HINT, so a family the caller will drop is never
    # computed. Without this the chain
    # `drop_prefixes(with_threshold(royal_chess))` filtered at the top
    # while the expensive walks still ran underneath.
    import inspect as _inspect
    try:
        takes_skip = 'skip' in _inspect.signature(extractor).parameters
    except (TypeError, ValueError):
        takes_skip = False

    def extract(engine, skip=()):
        counts = (extractor(engine, skip=skip) if takes_skip
                  else extractor(engine))
        out = {}
        for key, amount in counts.items():
            out[key] = amount
            try:
                owner, name = key
            except (TypeError, ValueError):
                continue
            if isinstance(name, str) and name.startswith('Missing:'):
                continue                # already a flag
            out[(owner, 'Missing:{0}'.format(name))] = (
                1 if amount == 0 else 0)
        return out

    extract.__name__ = 'with_threshold({0})'.format(
        getattr(extractor, '__name__', 'extractor'))
    return extract


def without(extractor, names):
    """`extractor` with the named features removed.

    Used to replay a decorrelation decision: the names dropped at
    training time are saved with the weights and re-applied at load
    time, so the loader and the trainer cannot see different feature
    sets. That divergence has already happened once.
    """
    dropped = frozenset(names or ())

    def extract(engine):
        counts = extractor(engine)
        return dict((key, amount) for key, amount in counts.items()
                    if not (isinstance(key, tuple) and len(key) == 2
                            and key[1] in dropped))

    extract.__name__ = 'without({0})'.format(
        getattr(extractor, '__name__', 'extractor'))
    return extract


#: Prefixes that mark a DERIVED column -- one a wrapper computed from
#: another column rather than read from the game. Structural, not
#: domain knowledge: `with_threshold` is what creates them, and when a
#: derived column is redundant with the one it came from, the derived one
#: is the one to drop. Getting this backwards dropped `Bishop` and
#: `Knight` and kept their flags, which is how the material sensitivity
#: was lost in the first place.
DERIVED_PREFIXES = ('Missing:', 'Has:', 'More:')


def dedupe_by_features(extractor, perspective_of=None):
    """`(engine, turns) -> turns`, keeping one move per distinct feature
    vector.

    If two moves leave the evaluation reading exactly the same numbers,
    the evaluation cannot tell them apart, so searching both spends the
    budget twice on one answer. On a 19x19 board almost every move far
    from the existing stones produces the same counts as every other,
    which is why the branching factor there is 360 and the search
    reaches depth 2.

    LOSSY, and the docstring in `search.Searcher` says why: identical
    features now does not mean identical futures. It is a heuristic
    that buys depth, and it has to earn its place in a match rather
    than in an argument.

    Domain-free: it takes an extractor and compares what that extractor
    returns.
    """
    from lgref.experiments.discover import differentials

    def reduce_turns(engine, turns):
        seen = {}
        for turn in turns:
            try:
                child = engine.copy()
                child.execute_turn(turn)
                mover = perspective_of or getattr(engine, 'current_player',
                                                  None)
                key = tuple(sorted(
                    differentials(extractor(child), mover).items()))
            except Exception:
                return turns        # cannot reduce safely; do not try
            seen.setdefault(key, turn)
        return list(seen.values())

    return reduce_turns


def drop_prefixes(extractor, prefixes):
    """`extractor` without any feature whose name starts with one of
    `prefixes`.

    An ablation handle, so a feature FAMILY can be removed and measured
    rather than argued about. Added because the relational and flag
    families were justified by a diagnosis -- the agent misses winnable
    material -- and then never tested against a run without them.
    """
    banned = tuple(prefixes)
    # PASS THE HINT DOWN where the extractor can use it, so a family
    # that will be discarded is never computed. Filtering after the
    # fact left the expensive walks running.
    import inspect as _inspect
    try:
        takes_skip = 'skip' in _inspect.signature(extractor).parameters
    except (TypeError, ValueError):
        takes_skip = False

    def extract(engine):
        counts = (extractor(engine, skip=banned) if takes_skip
                  else extractor(engine))
        out = {}
        for key, amount in counts.items():
            name = key[1] if (isinstance(key, tuple) and len(key) == 2
                              and isinstance(key[1], str)) else None
            if name is not None:
                bare = name[len('Missing:'):] if name.startswith(
                    'Missing:') else name
                if bare.startswith(banned):
                    continue
            out[key] = amount
        return out

    extract.__name__ = 'drop_prefixes({0})'.format(
        getattr(extractor, '__name__', 'extractor'))
    return extract


def decorrelate(extractor, make_engine, games=16, plies=140, seed=5):
    """`(filtered_extractor, dropped_names)` -- redundancy found from DATA.

    Two feature columns that are affinely dependent over the positions
    actually seen carry one signal between two weights, with the split
    decided by the optimiser's path rather than by the game. That has
    now caused three separate defects in this project: an added
    indicator equal to its own count (nine pairs), an offensive family
    that was exactly the negation of the defensive one (five pairs), and
    an explicit royal indicator that duplicated a threshold (one pair).

    Every one of them was found by a dependence check and NOT by
    inspection, and two survived an attempt to list the exceptions by
    hand. So the check runs as a pipeline step instead: sample positions
    by random play, difference them, drop one column from each dependent
    pair, and record what was dropped.

    WHICH ONE IS DROPPED, in order: a DERIVED column before a column
    read from the game, then the one with fewer distinct values, then
    the smaller spread, then the name so the result is reproducible.

    The derived-first rule is structural rather than a preference --
    `with_threshold` is what computes those columns -- and it is there
    because getting it wrong is not symmetric. A first attempt ranked on
    spread alone, which on a sample where the bishop count never
    differed by two made `Bishop` and `Missing:Bishop` look
    interchangeable; it dropped `Bishop`, the actual count, and kept the
    flag. That is the exact failure this reparameterisation exists to
    undo.

    SAMPLE SIZE MATTERS for the same reason: a column that looks binary
    in a short sample may not be, and a dependence found on too little
    data is a false one. Sampling is deliberately generous, and the
    check is cheap -- under a second.

    Domain-free: it takes an extractor and an engine factory and reads
    neither's internals.
    """
    import random as _random

    from lgref.experiments.discover import differentials
    from lgref.experiments.random_play import build
    from lgref.experiments.replicate import dependent_columns

    vectors = []
    reach = {}
    rng = _random.Random(seed)
    for index in range(games):
        engine = make_engine('full', max_turns=400)
        mover = build('random', _random.Random(seed * 1000 + index), 0)
        for _ply in range(rng.randint(max(1, plies // 4), plies)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(mover.choose_turn(turns, engine))
            owner = getattr(engine, 'current_player', None)
            raw = extractor(engine)
            for key, amount in raw.items():
                if isinstance(key, tuple) and len(key) == 2:
                    try:
                        reach[key[1]] = max(reach.get(key[1], 0), amount)
                    except TypeError:
                        pass
            vectors.append(differentials(raw, owner))
    if not vectors:
        return extractor, []

    # A ZERO FLAG ONLY EARNS ITS PLACE ON A COUNT THAT REACHES TWO.
    # `Missing:X` says "there are none of these", which is a DIFFERENT
    # statement from the count only when the count can be more than one.
    # Where X never exceeds 1, `Missing:X` is just `1 - X`, and in
    # differential space that is an exact dependency -- one signal split
    # across two weights.
    #
    # This is decided from the sample rather than from a list, and
    # raising the sample does not fix it: measured at 16x140 and 40x240
    # plies the residual dependent pairs on three held-out samples were
    # [4, 6, 14] and [5, 7, 15]. Random play simply does not produce two
    # hanging rooks often enough for the pairwise check to tell a real
    # count from a flag, so the question is settled structurally.
    dropped = set()
    for name, highest in reach.items():
        if not isinstance(name, str) or not name.startswith('Missing:'):
            continue
        base = name[len('Missing:'):]
        if reach.get(base, 0) < 2:
            dropped.add(name)

    def rank(name):
        column = [vector.get(name, 0.0) for vector in vectors]
        derived = any(name.startswith(prefix)
                      for prefix in DERIVED_PREFIXES)
        # Lower sorts first and is dropped first.
        return (0 if derived else 1, len(set(column)),
                max(column) - min(column), name)

    for first, second, _slope in dependent_columns(vectors):
        if first in dropped or second in dropped:
            continue
        dropped.add(first if rank(first) < rank(second) else second)
    return without(extractor, sorted(dropped)), sorted(dropped)


#: The previous name, kept so existing callers and saved runs still
#: resolve. The semantics changed with the decomposition above.
with_presence = with_threshold


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
        # A SELF-CAPTURE IS NOT A GAIN. This ranked them as the most
        # valuable move on the board: it read the destination occupant
        # and returned `abs(weight)` without ever asking WHOSE piece it
        # was, so "king takes own rook" outranked every enemy capture.
        #
        # Only the king may capture a friendly piece (RULEBOOK.md), so
        # these are rare in the move list and catastrophic when played.
        # A human's game showed the agent doing it twice by move 8 --
        # `Kb8xb7` and `Kb7xc6`, taking its own pawn and then its own
        # knight. Measured over 40 random positions: 124 self-captures
        # available, every one ranked 0.3952, the top rank there is.
        #
        # Ranked BELOW a quiet move rather than merely lower, because
        # giving a piece away for nothing is worse than any quiet move,
        # and ordering is what decides ties when the evaluation cannot.
        mover = getattr(engine, 'current_player', None)
        if mover is not None and getattr(piece, 'color', None) == mover:
            return -1.0
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


def royal_chess_extractor(payload, path='<payload>'):
    """The extractor a saved run's weights were fitted on, rebuilt.

    THE PAYLOAD IS THE ONLY RECORD OF ITS OWN FEATURE SET, and this
    drifted once with every weight silently unused: the trainer moved to
    `with_threshold(royal_chess)`, which renames every count, while the
    loader still evaluated the raw extractor -- so NOT ONE weight name
    matched and the agent would have played a flat evaluation.

    Three decisions are REPLAYED rather than recomputed:

      `extractor`      which vocabulary. `legacy` is the frozen copy at
                       `d60adbb`, kept because a reviewer asked for the
                       agent they had measured as most competent and it
                       needs the set it was fitted on.
      `drop_prefixes`  which families were ablated. Measured: the
                       per-identity relational families and the
                       per-piece flag counts make the agent much worse.
      `dropped`        which columns decorrelation removed. That
                       decision is made from a random sample at training
                       time, so recomputing it here would sample
                       differently and could drop a DIFFERENT column --
                       handing the weights a feature set they were never
                       fitted on.

    Lives beside the loader rather than inside it because the probes and
    the race need the same reconstruction, and when each had its own
    copy one of them was wrong.
    """
    name = payload.get('extractor', 'with_threshold(royal_chess)')

    def _legacy():
        # Imported lazily so the frozen copy is not a load-time
        # dependency of the live one.
        from lgref.experiments.legacy import royal_chess as frozen
        return frozen

    builders = {'royal_chess': royal_chess,
                'with_threshold(royal_chess)': with_threshold(royal_chess),
                'with_presence(royal_chess)': with_threshold(royal_chess),
                'legacy': _legacy()}
    if name not in builders:
        raise ValueError(
            'weights at {0} name an extractor this loader does not '
            'know: {1!r}. Known: {2}.'.format(path, name,
                                              sorted(builders)))
    extractor = drop_prefixes(builders[name],
                              payload.get('drop_prefixes', ()))
    return without(extractor, payload.get('dropped', ()))


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

    from lgref.experiments.record import audit, fatal

    with open(path) as handle:
        payload = json.load(handle)
    weights = payload['weights']
    scales = payload.get('scales', {})

    # THE PAYLOAD IS AUDITED BEFORE IT IS PLAYED. Three experiments in
    # a row were read as results when the artifact itself said they
    # could not be -- see `record.py` for the three and for the two
    # signatures. The check is cheap and runs on every load, because
    # the alternative is a procedure someone has to remember at the
    # moment they are most eager to read a number.
    problems = fatal(audit(payload))
    if problems:
        raise ValueError(
            'the weights at {0} cannot be played as saved:\n  - {1}'
            .format(path, '\n  - '.join(problems)))

    # THE LOADER MUST USE THE EXTRACTOR THE WEIGHTS WERE TRAINED WITH,
    # and it is rebuilt from the payload by `royal_chess_extractor` so
    # that the probes and the race use the same reconstruction. Three of
    # them had their own copy and one of the copies was wrong.
    extractor = royal_chess_extractor(payload, path=path)

    # A STALE WEIGHTS FILE MUST NOT DEGRADE SILENTLY. Changing the
    # feature set renames features, and a weight whose name no longer
    # exists simply never contributes -- so the agent keeps running and
    # plays with part of its evaluation missing. Caught in exactly that
    # state: after the royal features were merged, the saved file held
    # 17 names against 11 current ones with only 8 overlapping, and
    # `Royal`, `Attacked` and `Covers` had NO weight at all. The agent
    # would have had no royal value whatsoever, which is worse than the
    # version it replaced.
    #
    # Failing loudly is right here: the only fix is to retrain, and a
    # silent half-evaluation is harder to notice than an exception.
    # Checked once, on the first evaluation, because the feature set is
    # only knowable from a real position.
    state = {'checked': False}

    def evaluate(engine, perspective):
        raw = differentials(extractor(engine), perspective)
        if not state['checked']:
            state['checked'] = True
            missing = set(raw) - set(weights)
            if missing:
                raise ValueError(
                    'weights at {0} do not match the current feature set: '
                    '{1} have no weight. The feature vocabulary changed, '
                    'so retrain -- a partial evaluation would run '
                    'silently and play worse than the version it '
                    'replaced.'.format(path, sorted(missing)))
        return value(weights, normalise(raw, dict(scales), update=False))

    return Searcher(evaluate, capture_ranker(weights, scales),
                    max_depth=max_depth, budget=budget,
                    quiescence=quiescence)
