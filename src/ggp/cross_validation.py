"""Cross-validation harness: compare GGP `legal_moves` (from
integrated.gdl) against the Python engine's `get_all_legal_turns`
for the SAME game state.

This is the real correctness gate for the GDL specification —
structural tests proved the GDL parses + contains the right
predicates; the GGP plays it; this harness checks that the GGP's
output actually MATCHES the Python engine.

Approach:

1. Translate Python `Board` state → set of GDL `(true ?fact)` facts:
   - Each piece on the board → `(cell ?f ?r ?color ?type)`
   - Boulder state → `(boulder_at intersection)` or `(cell ?f ?r none boulder)`
     + `(boulder_cooldown N)` + (optionally) `(boulder_first_move)`
   - Per-piece queen state → `(queen_form ?f ?r ?form)`, `(queen_royal ?f ?r)`
   - Control + turn_number
2. Load `integrated.gdl` into GGPGame; replace its state with the
   converted set.
3. Query both: GGP's `legal_moves(player)` + engine's
   `get_all_legal_turns()`.
4. Translate engine Turns → GDL move terms.
5. Compare sets.

This module exposes:
  - `board_to_gdl_facts(board, next_player)` → frozenset of facts
  - `turn_to_gdl_move(turn)` → GDL move term tuple
  - `compare_legal_moves(game, ggp_game, player)` → diff dict

Discrepancies are EXPECTED at this stage of the GDL series — the
elaborated audit (`docs/gdl_audit_against_rulebook.md`) flagged
known gaps (invuln guards on non-king captures, pawn promotion
form choice, bishop manipulation, etc.). The harness REPORTS the
diff so each can be triaged individually.
"""

from piece import (Pawn, King, Queen, Rook, Bishop, Knight,
                   Boulder)


# Board dimensions, named locally so this module does not depend on
# const.py's import side effects.
ROWS_ = 8
COLS_ = 8


# ---- Python piece type → GDL piece name --------------------------------

_PIECE_TYPE_TO_GDL = {
    Pawn:    'pawn',
    King:    'king',
    Queen:   'queen',
    Rook:    'rook',
    Bishop:  'bishop',
    Knight:  'knight',
    Boulder: 'boulder',
}


# ---- coordinate translation -------------------------------------------

def _file(col):
    """Board col 0..7 → GDL file 'a'..'h'."""
    return chr(ord('a') + col)


def _rank(row):
    """Board row 0..7 → GDL rank '8'..'1'."""
    return str(8 - row)


def _col_from_file(f):
    return ord(f) - ord('a')


def _row_from_rank(r):
    return 8 - int(r)


# ---- Board → GDL state facts ------------------------------------------

def board_to_gdl_facts(board, next_player, turn_number=None):
    """Convert a Python Board snapshot to a frozenset of GDL
    `(true ?fact)`-eligible terms (the inner ?fact only — the
    wrapping into `(true ...)` is done by GGPGame's state-KB
    builder).

    Args:
        board: src/board.py Board instance
        next_player: 'white' or 'black' (whose turn it is)
        turn_number: optional override; defaults to board.turn_number

    Returns:
        frozenset of fact tuples (cell/control/turn_number/queen_form/
        queen_royal/boulder_at/boulder_first_move/boulder_cooldown/
        invulnerable/...)
    """
    facts = set()

    # Pieces on the board.
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            f = _file(col)
            r = _rank(row)
            piece_name = _PIECE_TYPE_TO_GDL.get(type(piece))
            if piece_name is None:
                continue  # unknown piece type — skip
            color = piece.color  # 'white', 'black', or 'none'
            facts.add(('cell', f, r, color, piece_name))

            # Per-piece extra state. Transformed queens are engine
            # Rook/Bishop/Knight instances with is_transformed=True;
            # the GDL represents every queen as cell=queen plus a
            # queen_form fact (2026-07-20 converter fidelity fix —
            # previously they mapped to plain pieces, losing queen
            # identity AND royalty in injected states).
            if getattr(piece, 'is_transformed', False):
                form = {'rook': 'rook', 'bishop': 'bishop',
                        'knight': 'knight'}.get(piece_name)
                if form is not None:
                    facts.discard(('cell', f, r, color, piece_name))
                    facts.add(('cell', f, r, color, 'queen'))
                    facts.add(('queen_form', f, r, form))
                    if piece.is_royal:
                        facts.add(('queen_royal', f, r))
            elif isinstance(piece, Queen):
                facts.add(('queen_form', f, r, 'base'))
                if piece.is_royal:
                    facts.add(('queen_royal', f, r))
            if getattr(piece, 'invulnerable', False):
                facts.add(('invulnerable', f, r))
            # First-class last-move flags (2026-07-20, PR #151): the
            # engine stores them on pieces; the GDL models them as the
            # spatial_move_last_turn fluent plus recorded
            # reactive_armed pairs (emitted below, once the moved
            # piece's square is known).
            if getattr(piece, 'moved_last_turn', False):
                facts.add(('spatial_move_last_turn', f, r))

    # ---- Boulder state (issue #170) -----------------------------------
    #
    # `board.boulder` is ONLY the intersection reference: Board sets it
    # to None the moment the boulder moves onto a square, after which
    # the Boulder object lives in squares[r][c].piece. The previous
    # version nested this whole block under `if board.boulder is not
    # None`, so once the boulder left the centre NO boulder_cooldown,
    # boulder_first_move or boulder_last fact was emitted at all. The
    # GDL's boulder-move rule requires `(true (boulder_cooldown 0))`,
    # so with the fact absent the rule could not fire and the GGP
    # offered no boulder moves from a square — the single largest
    # source of engine/GGP disagreement.
    boulder = board.boulder if (board.boulder is not None
                                and board.boulder.on_intersection) else None
    boulder_sq = None
    if boulder is None:
        for row in range(ROWS_):
            for col in range(COLS_):
                p_ = board.squares[row][col].piece
                if isinstance(p_, Boulder):
                    boulder = p_
                    boulder_sq = (row, col)
                    break
            if boulder is not None:
                break

    if boulder is not None:
        if boulder_sq is None:
            facts.add(('boulder_at', 'intersection'))
        if getattr(boulder, 'first_move', False):
            facts.add(('boulder_first_move',))
        facts.add(('boulder_cooldown', str(boulder.cooldown)))
        # No-return memory. The engine stores (-1, -1) as "no memory";
        # only a real square becomes a boulder_last fact.
        last = getattr(boulder, 'last_square', None)
        if last is not None and last[0] >= 0 and last[1] >= 0:
            facts.add(('boulder_last', _file(last[1]), _rank(last[0])))

    # ---- Manipulation freeze (Restriction 1) --------------------------
    #
    # A piece moved by queen manipulation may not make a spatial move on
    # its immediately next turn. The engine stores this as
    # piece.moved_by_queen; the GDL reads it as
    # `(not (true (manipulation_freeze ?f ?r)))` on every move rule.
    # Never emitted before, so the GGP ignored Restriction 1 entirely.
    for row in range(ROWS_):
        for col in range(COLS_):
            p_ = board.squares[row][col].piece
            if p_ is not None and getattr(p_, 'moved_by_queen', False):
                facts.add(('manipulation_freeze', _file(col), _rank(row)))

    # ---- Transformation eligibility -----------------------------------
    #
    # A queen may transform to rook/bishop/knight only if a friendly
    # piece of that type was captured earlier. The engine tracks this in
    # board.captured_pieces; the GDL derives `allowed_form` from
    # `(true (captured_friendly ?owner ?type))`. Never emitted before,
    # so allowed_form could only ever derive `base` and the GGP could
    # never offer any transform.
    for owner, names in getattr(board, 'captured_pieces', {}).items():
        if owner not in ('white', 'black'):
            continue
        for piece_type in set(names):
            facts.add(('captured_friendly', owner, piece_type))

    # ---- Tiny endgame state -------------------------------------------
    #
    # Emitted so the GGP can see the rule's activation and its distance
    # counts. NOTE: integrated.gdl currently DERIVES tiny_endgame_active
    # by rule while also querying it as `(true (tiny_endgame_active))`,
    # and no `next` rule ever writes it — so the fluent is unsatisfiable
    # and the tiny-endgame loss condition is dead in the GGP. Tracked in
    # #177; emitting the fact here is what makes that rule reachable at
    # all once the GDL side is fixed.
    if getattr(board, 'tiny_endgame_active', False):
        facts.add(('tiny_endgame_active',))
    for dist, count in enumerate(getattr(board, 'distance_counts', [])):
        if dist >= 1 and count:
            facts.add(('distance_count', str(dist), str(count)))

    # Recorded reactive arming (begin-time, per the first-class
    # flags): each armed bishop pairs with the moved piece's square
    # (its capture target). The engine guarantees armed ⇒ a flagged
    # moved piece exists.
    moved_sq = None
    for row in range(8):
        for col in range(8):
            p = board.squares[row][col].piece
            if p is not None and getattr(p, 'moved_last_turn', False):
                moved_sq = (_file(col), _rank(row))
                break
        if moved_sq is not None:
            break
    if moved_sq is not None:
        for row in range(8):
            for col in range(8):
                p = board.squares[row][col].piece
                if p is not None and getattr(p, 'reactive_armed', False):
                    facts.add(('reactive_armed', _file(col), _rank(row),
                               moved_sq[0], moved_sq[1]))

    # Control + turn_number.
    facts.add(('control', next_player))
    tn = turn_number if turn_number is not None else board.turn_number
    # The integrated.gdl's `succ` chain goes up to turn 10; for
    # larger turn numbers we just record the int as-is.
    facts.add(('turn_number', str(tn + 1)))  # GDL uses 1-indexed

    return frozenset(facts)


# ---- engine Turn → GDL move term --------------------------------------

def turn_to_gdl_move(turn):
    """Translate a `engine.Turn` object to the GDL move-term tuple
    shape (e.g. `('move', 'pawn', 'a', '2', 'a', '3')`).

    Returns None if the turn type is one the GDL doesn't yet encode
    (e.g. transformation actions, jump-capture sub-choices).
    """
    if turn.turn_type == 'transformation':
        # GDL transform action: ('transform', f, r, new_form)
        row, col = turn.from_sq
        return ('transform', _file(col), _rank(row),
                turn.transform_target)
    if turn.turn_type in ('move', 'boulder', 'manipulation'):
        # Boulder first move, from the central intersection (#170).
        # The intersection is not a square, so the engine leaves
        # from_sq None and the GDL names it with the atom
        # `intersection`: (move boulder intersection ?tf ?tr). This
        # used to bail out here, which dropped every engine boulder
        # first-move from the comparison and made all four of the
        # GGP's look GGP-only.
        if turn.from_sq is None and turn.to_sq is not None \
                and getattr(turn.piece, 'on_intersection', False):
            to_row, to_col = turn.to_sq
            return ('move', 'boulder', 'intersection',
                    _file(to_col), _rank(to_row))
        if turn.from_sq is None or turn.to_sq is None:
            return None
        from_row, from_col = turn.from_sq
        to_row, to_col = turn.to_sq
        piece = turn.piece
        piece_name = _PIECE_TYPE_TO_GDL.get(type(piece), '?')
        if turn.turn_type == 'manipulation':
            # GDL: (manipulate ?qf ?qr ?ef ?er ?tf ?tr), which names
            # the manipulating queen. The engine's Turn does not,
            # because it does not need to: the queen does not move and
            # is otherwise unaffected, so two queens with line-of-sight
            # to the same target produce the SAME successor state, and
            # the engine correctly enumerates that as one turn.
            #
            # The GDL's finer granularity is therefore a
            # representational artifact, not a rule difference. Both
            # sides are normalised to the engine's granularity by
            # dropping the queen's square (see _normalize_manipulate),
            # which is a deliberate normalisation, not a fix to either
            # side. Comparing without it would report a spurious
            # disagreement on every manipulation in the game.
            return ('manipulate', _file(from_col), _rank(from_row),
                    _file(to_col), _rank(to_row))
        if piece_name == 'bishop' and turn.is_capture:
            # A bishop capture is ALWAYS the reactive capture (bishops
            # have no other capture mechanic; a queen-as-bishop maps
            # to the same GDL action term).
            return ('reactive_capture', _file(from_col), _rank(from_row),
                    _file(to_col), _rank(to_row))
        if turn.promo_choice is not None:
            # Promotion carries its chosen form (2026-07-20: the GDL
            # promote action replaced auto-promotion).
            return ('promote', _file(from_col), _rank(from_row),
                    _file(to_col), _rank(to_row), turn.promo_choice)
        if getattr(turn.piece, 'is_transformed', False):
            # A transformed queen is a Rook/Bishop/Knight instance in
            # the engine but moves as (move queen ...) in the GDL.
            return ('move', 'queen', _file(from_col), _rank(from_row),
                    _file(to_col), _rank(to_row))
        return ('move', piece_name, _file(from_col), _rank(from_row),
                _file(to_col), _rank(to_row))
    return None


def _normalize_manipulate(move):
    """Drop the manipulating queen's square from a GDL manipulate term.

    `(manipulate ?qf ?qr ?ef ?er ?tf ?tr)` -> `(manipulate ?ef ?er ?tf ?tr)`.

    The queen neither moves nor changes state when it manipulates, so
    every queen with line-of-sight to the same target yields the same
    successor position. The engine enumerates that as ONE turn; the GDL
    enumerates one action per queen. Normalising to the engine's
    granularity compares the two on the thing that actually differs —
    which enemy piece moves where — instead of reporting a spurious
    disagreement whenever two queens can reach the same target.

    Terms of any other shape pass through unchanged.
    """
    if isinstance(move, tuple) and move and move[0] == 'manipulate' \
            and len(move) == 7:
        return ('manipulate',) + move[3:]
    return move


# ---- compare ----------------------------------------------------------

def compare_legal_moves(game, ggp_game, player):
    """Compare the Python engine's legal turns against the GGP's
    legal moves at the SAME game state.

    Args:
        game: src/game.py Game (Python engine carrier)
        ggp_game: ggp.game.GGPGame instance (already loaded from
                  integrated.gdl) — caller MUST set its state to
                  match `game.board` before calling
        player: 'white' or 'black'

    Returns a dict:
        {
            'engine_count': int,
            'ggp_count': int,
            'engine_only': list of move-term tuples,
            'ggp_only': list of move-term tuples,
            'common': list of move-term tuples,
            'untranslatable': list of engine Turn types that
                              couldn't be mapped (e.g. manipulation
                              without queen-source info),
        }
    """
    from engine import GameEngine

    # Engine side. NOTE (2026-07-20 fix): GameEngine's first
    # positional parameter is max_turns, NOT a board — the old
    # `GameEngine(game.board)` silently enumerated a fresh INITIAL
    # board, so every injected-state comparison ran against the
    # opening position. Bind the live board explicitly (mirrors
    # AIController.legal_turns).
    engine = GameEngine()
    engine.board = game.board
    engine.current_player = player
    engine.turn_number = game.board.turn_number
    engine_turns = engine.get_all_legal_turns()
    engine_set = set()
    untranslatable = []
    for t in engine_turns:
        gdl_move = turn_to_gdl_move(t)
        if gdl_move is None:
            untranslatable.append(t.turn_type)
        else:
            engine_set.add(gdl_move)

    # GGP side.
    ggp_moves = ggp_game.legal_moves(player)
    ggp_set = set(_normalize_manipulate(m)
                  for m in ggp_moves if isinstance(m, tuple))

    return {
        'engine_count': len(engine_turns),
        'ggp_count': len(ggp_moves),
        'engine_only': sorted(engine_set - ggp_set),
        'ggp_only': sorted(ggp_set - engine_set),
        'common': sorted(engine_set & ggp_set),
        'untranslatable': untranslatable,
    }
