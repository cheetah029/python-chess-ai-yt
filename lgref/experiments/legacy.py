"""The extractor as it stood at d60adbb, kept so the two can be RACED.

A reviewer reported the agent playing far worse than a version they had
played before, and asked for that version back. Opinions about which is
better are worth nothing here -- this project has already shipped three
changes that looked better in a weight table and were worse in play --
so the old extractor is preserved verbatim and the two are measured
against each other directly.

NOTHING HERE IS MAINTAINED. It is a frozen copy for comparison, and the
weights that go with it are `lgref/weights/td_royal_chess_legacy.json`.
If the legacy version wins, it gets promoted back into `features.py`
rather than being loaded from here forever.
"""

import collections

from lgref.experiments.features import NEUTRAL_OWNERS


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
    except AttributeError:
        # A game without this cache simply omits them. NARROW on
        # purpose: `except Exception` here swallowed every bug in the
        # walk above and the only symptom was two features quietly
        # missing from the vector.
        pass

    # The forms a queen could take are read from the engine's own
    # mapping where it exposes one, rather than restated here.
    forms = sorted(getattr(board, 'TRANSFORM_TARGETS',
                           ('rook', 'bishop', 'knight')))
    for colour, names in getattr(board, 'captured_pieces', {}).items():
        for form in forms:
            counts[(colour, 'FormAvailable:' + form)] = (
                1 if form in names else 0)
    return dict(counts)


