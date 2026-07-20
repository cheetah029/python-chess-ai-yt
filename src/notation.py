"""Royal chess notation — the movetext layer of the V3 save format.

Standard chess PGNs record only the per-turn differences between board
states; the V2 save instead pickled every full board snapshot in the
undo history (compressed, but still large). This module provides the
variant's own notation so a game can be saved as a short, readable
movetext and reconstructed exactly by replaying it.

TOKEN GRAMMAR (one token per turn, ASCII only):

  Spatial turn:      [>] L ['] FROM (-|x) TO [=F] [j] [#]
  Transformation:        L ['] SQ = F [#]

    >    the mover manipulated an ENEMY piece (queen manipulation)
    L    piece letter as it stood BEFORE the turn:
         K king, Q queen, R rook, B bishop, N knight, P pawn,
         O the neutral boulder
    '    the piece is a TRANSFORMED queen (e.g. R' = queen-as-rook)
    FROM/TO/SQ  algebraic squares a1..h8 (row 0 = rank 8);
         the boulder's first move uses FROM = ** (central intersection)
    -    move to an empty landing square
    x    landing capture (includes the king capturing a friendly piece
         or the boulder, the boulder capturing a pawn, and a bishop's
         reactive capture — which is just a bishop move onto the
         victim's square)
    =F   promotion form (Q base, or transformed R/B/N) for a pawn
         reaching the last rank; on a transformation token, the form
         the queen transforms into (=Q returns to base form)
    j    accepted jump-capture: the knight captures the piece on its
         jumped square. The jumped square is NOT written — the
         rulebook derives it uniquely from FROM and TO
         (Board.get_jumped_square). A token without `j` whose move
         happens to offer a jump-capture is a DECLINE; declines and
         all automatic effects (manipulation freeze, knight
         invulnerability, boulder cooldown/no-return, repetition
         recording, tiny-endgame counts, winner checks) are
         reproduced by the replay path, not encoded.

    #    the turn ended the game (a winner exists in the resulting
         state — the variant's counterpart of the checkmate mark;
         there is no check/checkmate, so it marks ANY terminal turn:
         second royal captured, or opponent left with no legal turn)

  Examples: Pe2-e3   Nb1-b3j   >Pd7-d6   R'a4xa7   Qd4=B   O**-d4
            Pe7-e8=N   >Pe2-e1=Q   Ka2xb2   Qa2xa1#

REPLAY: `apply_token` mirrors AIController._apply_turn (which itself
mirrors the human path in main.py) minus sounds, branching on the
ACTUAL jump-offer returned by Board.move rather than a precomputed
flag. Game.next_turn stays the single turn-lifecycle authority, so a
replayed turn is indistinguishable from a live one — the undo
history, repetition state and winner checks all rebuild themselves.

INFERENCE: `infer_token` reconstructs the token for one turn from two
consecutive undo-history snapshots by diffing piece signatures
(class/color/royal/transformed — mutable flags like freeze and
invulnerability are deliberately ignored, since they change on
non-moved pieces too). The serializer self-verifies by replaying the
inferred movetext and comparing every state hash, so a bad inference
can never produce a wrong save (Game falls back to the V2 container).
"""

import copy

from move import Move
from square import Square
from piece import Boulder, Pawn


class NotationError(Exception):
    """Raised when a game cannot be expressed or replayed in royal
    notation (the caller falls back to the V2 pickle container)."""


PIECE_LETTERS = {
    'King': 'K', 'Queen': 'Q', 'Rook': 'R', 'Bishop': 'B',
    'Knight': 'N', 'Pawn': 'P', 'Boulder': 'O',
}
LETTER_TO_FORM = {'Q': 'queen', 'R': 'rook', 'B': 'bishop', 'N': 'knight'}
FORM_TO_LETTER = {v: k for k, v in LETTER_TO_FORM.items()}

INTERSECTION = '**'   # boulder's initial central-intersection "square"


# ---- squares -------------------------------------------------------------

def square_name(row, col):
    """Board (row, col) -> algebraic. Row 0 = rank 8, col 0 = file a
    (same mapping as Game.to_fen)."""
    if not (0 <= row <= 7 and 0 <= col <= 7):
        raise NotationError(f'square out of range: {(row, col)}')
    return chr(ord('a') + col) + str(8 - row)


def parse_square(name):
    """Algebraic -> board (row, col). Inverse of square_name."""
    if (len(name) != 2 or not ('a' <= name[0] <= 'h')
            or not ('1' <= name[1] <= '8')):
        raise NotationError(f'bad square name: {name!r}')
    return 8 - int(name[1]), ord(name[0]) - ord('a')


# ---- piece signatures (inference diffing) --------------------------------

def _sig(piece):
    """Identity signature of a square's occupant. Mutable per-turn
    flags (moved_by_queen, invulnerable, moved, en_passant) are
    EXCLUDED — they change on pieces that did not move this turn."""
    if piece is None:
        return None
    return (type(piece).__name__, piece.color,
            getattr(piece, 'is_royal', False),
            getattr(piece, 'is_transformed', False))


def _letter_of(piece):
    letter = PIECE_LETTERS.get(type(piece).__name__)
    if letter is None:
        raise NotationError(f'unknown piece class: {type(piece).__name__}')
    return letter


def _piece_prefix(piece):
    """Piece letter + transformed-queen marker."""
    return _letter_of(piece) + ("'" if getattr(piece, 'is_transformed', False)
                                else '')


# ---- inference: snapshot pair -> token -----------------------------------

def infer_token(snap_a, snap_b):
    """Reconstruct the royal-notation token for the single turn that
    led from snapshot A to snapshot B (Game._snapshot dicts). Raises
    NotationError when no supported turn shape explains the diff.

    A turn whose RESULTING state is terminal (a winner exists) gets a
    trailing '#' — the variant's counterpart of the checkmate mark.
    There is no check/checkmate here, so '#' marks any game-ending
    turn: capturing the opponent's second royal, or leaving the
    opponent with no legal turn (including repetition-forced and
    tiny-endgame-forced losses). It can follow any token shape, since
    the no-legal-moves check runs after every turn type."""
    token = _infer_token_base(snap_a, snap_b)
    if snap_b['winner'] is not None:
        token += '#'
    return token


def _infer_token_base(snap_a, snap_b):
    a, b = snap_a['board'], snap_b['board']
    mover = snap_a['next_player']

    changed = [(r, c) for r in range(8) for c in range(8)
               if _sig(a.squares[r][c].piece) != _sig(b.squares[r][c].piece)]

    if len(changed) == 1:
        r, c = changed[0]
        before = a.squares[r][c].piece
        after = b.squares[r][c].piece
        if after is not None and isinstance(after, Boulder):
            # Boulder's first move off the central intersection.
            if not (a.boulder is not None and a.boulder.on_intersection):
                raise NotationError('boulder appeared without intersection')
            sep = 'x' if before is not None else '-'
            return f'O{INTERSECTION}{sep}{square_name(r, c)}'
        if before is None or after is None:
            raise NotationError(f'unexplained single-square change {changed}')
        if before.color != after.color:
            raise NotationError(f'color change without move at {changed}')
        # Transformation action (queen form change in place).
        form = LETTER_TO_FORM.get(_letter_of(after))
        if form is None:
            raise NotationError(f'transformation to non-form at {changed}')
        return f'{_piece_prefix(before)}{square_name(r, c)}={_letter_of(after)}'

    if len(changed) == 2:
        return _infer_spatial(a, b, mover, changed, jumped=None)

    if len(changed) == 3:
        # Accepted jump-capture: from-square + jumped square vacated,
        # empty landing square gained the knight.
        gained = [sq for sq in changed if b.squares[sq[0]][sq[1]].piece
                  is not None and a.squares[sq[0]][sq[1]].piece is None]
        if len(gained) != 1:
            raise NotationError(f'unsupported 3-square diff: {changed}')
        to_sq = gained[0]
        vacated = [sq for sq in changed if sq != to_sq]
        knight = b.squares[to_sq[0]][to_sq[1]].piece
        for from_sq in vacated:
            other = [sq for sq in vacated if sq != from_sq][0]
            origin = a.squares[from_sq[0]][from_sq[1]].piece
            if (origin is not None and _sig(origin) == _sig(knight)
                    and a.get_jumped_square(from_sq[0], from_sq[1],
                                            to_sq[0], to_sq[1]) == other):
                return _spatial_token(origin, mover, from_sq, to_sq,
                                      capture=False, promo=None, jumpcap=True)
        raise NotationError(f'3-square diff is not a jump-capture: {changed}')

    raise NotationError(f'unsupported diff of {len(changed)} squares')


def _infer_spatial(a, b, mover, changed, jumped):
    """Two-square diff: a plain spatial move (possibly a landing
    capture, promotion, manipulation, or boulder move)."""
    vacated = [sq for sq in changed
               if a.squares[sq[0]][sq[1]].piece is not None
               and b.squares[sq[0]][sq[1]].piece is None]
    if len(vacated) != 1:
        raise NotationError(f'unsupported 2-square diff: {changed}')
    from_sq = vacated[0]
    to_sq = [sq for sq in changed if sq != from_sq][0]
    origin = a.squares[from_sq[0]][from_sq[1]].piece
    landed = b.squares[to_sq[0]][to_sq[1]].piece
    if landed is None:
        raise NotationError(f'no piece landed in 2-square diff: {changed}')
    captured = a.squares[to_sq[0]][to_sq[1]].piece is not None

    promo = None
    if isinstance(origin, Pawn) and not isinstance(landed, Pawn):
        if origin.color != landed.color:
            raise NotationError('promotion changed color')
        promo = _letter_of(landed)
    elif _sig(origin) != _sig(landed):
        raise NotationError(f'mover changed identity: {changed}')

    return _spatial_token(origin, mover, from_sq, to_sq,
                          capture=captured, promo=promo, jumpcap=False)


def _spatial_token(origin, mover, from_sq, to_sq, capture, promo, jumpcap):
    letter = _letter_of(origin)
    # Manipulation: the mover moved an ENEMY piece. The neutral
    # boulder ('none' color) is a normal boulder turn, never a
    # manipulation (the rulebook forbids manipulating the boulder).
    manip = '>' if (letter != 'O' and origin.color != mover) else ''
    sep = 'x' if capture else '-'
    token = (f'{manip}{_piece_prefix(origin)}{square_name(*from_sq)}'
             f'{sep}{square_name(*to_sq)}')
    if promo:
        token += f'={promo}'
    if jumpcap:
        token += 'j'
    return token


# ---- parsing -------------------------------------------------------------

def parse_token(token):
    """Token string -> dict. Keys: kind ('spatial'|'transform'),
    manip, letter, transformed, from_sq (None = intersection), to_sq,
    capture, promo (form name or None), jumpcap, terminal; for
    'transform': letter, transformed, sq, target (form name),
    terminal. `terminal` ('#' suffix) is informational — the replay
    re-derives the game-ending state from the moves themselves."""
    original, tok = token, token
    terminal = tok.endswith('#')
    if terminal:
        tok = tok[:-1]
    manip = tok.startswith('>')
    if manip:
        tok = tok[1:]
    if not tok or tok[0] not in 'KQRBNPO':
        raise NotationError(f'bad piece letter in token: {original!r}')
    letter, tok = tok[0], tok[1:]
    transformed = tok.startswith("'")
    if transformed:
        tok = tok[1:]

    # Transformation action: L['] sq = F   (no -/x separator).
    if '-' not in tok and 'x' not in tok:
        if len(tok) != 4 or tok[2] != '=' or tok[3] not in LETTER_TO_FORM:
            raise NotationError(f'bad transformation token: {original!r}')
        if manip or letter == 'O':
            raise NotationError(f'invalid transformation token: {original!r}')
        return {'kind': 'transform', 'letter': letter,
                'transformed': transformed, 'sq': parse_square(tok[:2]),
                'target': LETTER_TO_FORM[tok[3]], 'terminal': terminal}

    if tok.startswith(INTERSECTION):
        from_sq, tok = None, tok[len(INTERSECTION):]
        if letter != 'O':
            raise NotationError(f'intersection origin needs O: {original!r}')
    else:
        from_sq, tok = parse_square(tok[:2]), tok[2:]
    if not tok or tok[0] not in '-x':
        raise NotationError(f'missing move separator: {original!r}')
    capture, tok = tok[0] == 'x', tok[1:]
    to_sq, tok = parse_square(tok[:2]), tok[2:]

    promo = None
    if tok.startswith('='):
        if len(tok) < 2 or tok[1] not in LETTER_TO_FORM:
            raise NotationError(f'bad promotion suffix: {original!r}')
        promo, tok = LETTER_TO_FORM[tok[1]], tok[2:]
    jumpcap = tok == 'j'
    if tok not in ('', 'j'):
        raise NotationError(f'trailing garbage in token: {original!r}')

    return {'kind': 'spatial', 'manip': manip, 'letter': letter,
            'transformed': transformed, 'from_sq': from_sq, 'to_sq': to_sq,
            'capture': capture, 'promo': promo, 'jumpcap': jumpcap,
            'terminal': terminal}


# ---- replay --------------------------------------------------------------

def apply_token(game, token):
    """Apply one token to a live Game. Mirrors
    AIController._apply_turn / _apply_transformation (which mirror the
    human path in main.py) minus sounds, branching on the ACTUAL
    jump-offer returned by Board.move. Raises NotationError when the
    token does not match the board (corrupt/edited movetext)."""
    tok = parse_token(token) if isinstance(token, str) else token
    board = game.board
    mover = game.next_player
    if game.winner is not None:
        raise NotationError('turn after the game already ended')

    if tok['kind'] == 'transform':
        r, c = tok['sq']
        piece = board.squares[r][c].piece
        if piece is None or _letter_of(piece) != tok['letter']:
            raise NotationError(f'no matching piece for transform at '
                                f'{square_name(r, c)}')
        board.transform_queen(piece, r, c, tok['target'],
                              record_highlight=True)
        board.update_assassin_squares(mover)
        board.decrement_boulder_cooldown()
        if board.tiny_endgame_active:
            board.update_distance_count(captured=False)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        game.next_turn()
        return

    # Spatial turn.
    to_r, to_c = tok['to_sq']
    if tok['from_sq'] is None:
        piece = board.boulder
        if piece is None or not piece.on_intersection:
            raise NotationError('boulder not on intersection')
        initial = Square(-1, -1)
    else:
        fr, fc = tok['from_sq']
        piece = board.squares[fr][fc].piece
        if piece is None or _letter_of(piece) != tok['letter']:
            raise NotationError(
                f'no matching {tok["letter"]} at {square_name(fr, fc)}')
        initial = Square(fr, fc)
    captured = board.squares[to_r][to_c].has_piece()
    move = Move(initial, Square(to_r, to_c))

    jump_targets = board.move(piece, move)

    if jump_targets:
        # Jump-capture offer: accept iff the token says so; a plain
        # token is a decline (the jumped piece survives and the
        # knight may gain invulnerability — board helper checks).
        jumped_r, jumped_c = jump_targets[0]
        if tok['jumpcap']:
            board.execute_jump_capture(jumped_r, jumped_c)
            jump_captured = True
        else:
            board.set_invulnerable_after_jump_decline(
                piece, to_r, to_c, jumped_r, jumped_c)
            jump_captured = False
        board.clear_forbidden_squares()
        if piece.color != mover:
            piece.moved_by_queen = True
        board.update_assassin_squares(mover)
        board.decrement_boulder_cooldown()
        if jump_captured:
            game.winner = board.check_winner()
        if board.tiny_endgame_active:
            board.update_distance_count(captured=jump_captured)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        game.next_turn()
        return
    if tok['jumpcap']:
        raise NotationError('token claims a jump-capture; none offered')

    if tok['promo'] is not None:
        was_manipulation = piece.color != mover
        board.promote(piece, to_r, to_c, tok['promo'])
        if was_manipulation:
            new_piece = board.squares[to_r][to_c].piece
            if new_piece is not None:
                new_piece.moved_by_queen = True
        board.update_assassin_squares(mover)
        board.decrement_boulder_cooldown()
        if captured:
            game.winner = board.check_winner()
        if board.is_tiny_endgame():
            board.init_tiny_endgame()
        game.next_turn()
        return

    board.set_true_en_passant(piece)
    board.clear_forbidden_squares()
    if board.squares[to_r][to_c].has_enemy_piece(mover):
        board.squares[to_r][to_c].piece.moved_by_queen = True
    board.update_assassin_squares(mover)
    board.decrement_boulder_cooldown(moved_piece=piece)
    if captured:
        game.winner = board.check_winner()
    if board.tiny_endgame_active:
        board.update_distance_count(captured=captured)
    if not board.tiny_endgame_active and board.is_tiny_endgame():
        board.init_tiny_endgame()
    game.next_turn()


# ---- movetext ------------------------------------------------------------

def tokens_to_movetext(tokens):
    """Numbered PGN-style movetext: '1. <white> <black>' per line."""
    lines = []
    for i in range(0, len(tokens), 2):
        pair = ' '.join(tokens[i:i + 2])
        lines.append(f'{i // 2 + 1}. {pair}')
    return '\n'.join(lines)


def movetext_to_tokens(movetext):
    """Inverse of tokens_to_movetext; move numbers ('N.') dropped."""
    tokens = []
    for raw in movetext.split():
        if raw.endswith('.') and raw[:-1].isdigit():
            continue
        tokens.append(raw)
    return tokens


def infer_timeline_tokens(timeline):
    """Full timeline (history + reversed redo stack, oldest first) ->
    token list, one per turn."""
    return [infer_token(timeline[i], timeline[i + 1])
            for i in range(len(timeline) - 1)]
