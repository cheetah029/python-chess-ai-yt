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

WHAT IS FROZEN IS THE OUTPUT. The shipped player evaluates with this
copy, so it has been made faster twice (#279): the threat walk reads
the threat squares once instead of twice, and then the material and
the threat squares are read in one walk over the board. Each change is
proven to return the same dictionary -- keys, values and key order --
as the function before it, loaded from git, by
`test_the_evaluation_walks_the_threat_squares_once` and
`test_evaluation_walks_once_and_remembers_keys` in
`lgref/tests/test_method.py`. Any further change must carry the same
proof.
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
    # ONE WALK OVER THE BOARD (#279). The threat squares are brought up
    # to date first, which changes nothing the material count reads, so
    # the walk can note each owned piece's square and threat list as it
    # counts the material. Everything after the walk is added in the
    # order it was before. An AttributeError from the update, or from
    # the threat walk below, drops only the threat counts, as it did.
    # Every piece is a `Piece`, whose `__init__` sets `color`,
    # `is_royal`, `is_transformed` and `threat_squares`, so they are
    # read directly rather than through `getattr` with a default.
    try:
        board.update_threat_squares()
        threats_current = True
    except AttributeError:
        threats_current = False
    standing = []
    reaches = []
    for row, line in enumerate(board.squares):
        for col, square in enumerate(line):
            piece = square.piece
            if piece is None:
                continue
            colour = piece.color
            form = type(piece).__name__
            royal = piece.is_royal
            queen_kind = isinstance(piece, Queen) or piece.is_transformed
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
            if threats_current and colour not in NEUTRAL_OWNERS:
                standing.append((colour, (row, col)))
                reach = piece.threat_squares
                if reach:
                    reaches.append((colour, reach))
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
    if threats_current:
        try:
            # ONE SET PER COLOUR over the threat squares (#279). It used to
            # be two maps: one built, for every square, the set of colours
            # that reach it, and the other, for every colour, the set of
            # squares it reaches. The second holds the first -- the colours
            # reaching a square are exactly those whose set holds it -- so
            # only it is built, and a piece is counted as attacked once for
            # each OTHER colour whose set holds its square, as it was once
            # for each attacking colour. A colour gets a set only if it
            # reaches some square, as before. The pieces and their lists
            # were noted, in board order, by the walk above.
            covered = {}
            for owner, reach in reaches:
                reached = covered.get(owner)
                if reached is None:
                    reached = covered[owner] = set()
                reached.update([(square.row, square.col) for square in reach])
            for owner, square in standing:
                for attacker, reached in covered.items():
                    # Counted against the piece's OWNER: one of their
                    # pieces stands on a square an enemy can reach.
                    if attacker != owner and square in reached:
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


