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
                for flag, setting in list(vars(piece).items()):
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
        identities = set()
        for (row, col), (owner, identity, _piece) in where.items():
            identities.add(identity)
            reachers = threatened.get((row, col), ())
            hostile = [o for o in reachers if o != owner]
            if not hostile:
                continue
            counts[(owner, 'Attacked:' + identity)] += 1
            if owner not in reachers:
                counts[(owner, 'Hanging:' + identity)] += 1

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
    for side in ('white', 'black'):
        for flag in flag_names:
            counts.setdefault((side, 'Flag:' + flag), 0)

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
    """Every count REPLACED by a threshold and a slope.

        Has:X    1 if there is at least one X
        More:X   how many beyond the first, max(0, X - 1)

    and the raw count is dropped, because `X == Has:X + More:X` and
    keeping all three would be perfect multicollinearity.

    THE GENERAL FORM OF A SPECIFIC FAILURE. A linear model over counts
    assumes every unit of a quantity is worth the same, and for a piece
    whose capability is gated on having ANY of it, that is false at
    exactly one place: zero. Going from two bishops to one costs a
    little; going from one to none costs the reactive-capture pin
    entirely, because there is no bishop left to arm it.

    Measured, before this existed: `Bishop` learned -0.0077 per unit
    against `Pawn` +0.0501, so the evaluation scored "lose a bishop,
    win a pawn" as +0.047 -- a GAIN -- and a human reported precisely
    that trade as the agent's signature blunder. The reviewer had argued
    the case a month earlier in the clearest possible terms: comparing
    one bishop against none, one is almost always better. A single
    linear count cannot express that and no amount of training data will
    teach it to.

    WHY THE DECOMPOSITION RATHER THAN AN ADDED INDICATOR, which is what
    this did first. Adding `Has:X` beside the count makes the two
    columns IDENTICAL whenever X never exceeds 1 -- and most of these
    features never do. A duplicate-column test over 150 sampled
    positions found nine such pairs, including `Has:Attacked:Rook`,
    `Has:Hanging:Pawn` and every boolean flag. That is not two findings,
    it is one weight split in half, with the split decided by the
    optimiser's path rather than by the game; the same trap that once
    put the king's effective value below a rook's. An attempt to
    suppress them from a declared list of binary features caught two of
    the nine, which is how a declared list usually does.

    Under the decomposition a feature that never exceeds 1 simply has an
    all-zero `More:` column, which earns no gradient and is inert --
    harmless rather than duplicative.

    APPLIED TO EVERY COUNT, not to the pieces someone believes matter.
    Choosing which features get a threshold is exactly the hand-picking
    this framework exists to avoid. The split is done PER OWNER, before
    differencing, so `Has:` lands in {-1, 0, +1} and reads "I have one
    of these and they do not" -- the comparison the reviewer posed.
    """
    def extract(engine):
        counts = extractor(engine)
        out = {}
        for key, amount in counts.items():
            try:
                owner, name = key
            except (TypeError, ValueError):
                out[key] = amount       # a non-(owner, name) key is kept
                continue
            if isinstance(name, str) and (name.startswith('Has:')
                                          or name.startswith('More:')):
                out[key] = amount       # already decomposed
                continue
            out[(owner, 'Has:{0}'.format(name))] = 1 if amount >= 1 else 0
            out[(owner, 'More:{0}'.format(name))] = max(0, amount - 1)
        return out

    extract.__name__ = 'with_threshold({0})'.format(
        getattr(extractor, '__name__', 'extractor'))
    return extract


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
        raw = differentials(royal_chess(engine), perspective)
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
