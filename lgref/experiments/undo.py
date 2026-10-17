"""Make/unmake: search without paying for a copy at every node.

WHY. A search node costs a clone plus a move generation, measured in a
midgame position at branching 50:

    clone (engine + turns)   0.978 ms
    move generation          0.538 ms

and a snapshot of only the MUTABLE state costs 0.019 ms -- fifty times
less than the clone. So a node can cost 0.557 ms instead of 1.515 ms,
which is 2.7x the nodes for the same wall clock. It also matters for
TRAINING, where one-ply action selection clones once per candidate on
every ply of every game; that is where most of the fifty minutes of an
800-game run goes.

THE SAFETY DESIGN, which is the important part. This does NOT mutate the
caller's engine. A searcher clones ONCE per move and then uses
apply/undo inside that private copy, so a subtle undo bug can only
corrupt a throwaway position, never the live game. Paying one clone per
move instead of per node keeps essentially all of the benefit: at even a
few hundred nodes the single clone is noise.

WHAT HAS TO BE RESTORED, and this list is the whole risk. `Board.move`
does far more than move a piece:

  * the grid, obviously -- and a promotion or transformation REPLACES
    the piece object, so restoring the grid also restores identity;
  * per-piece flags, on EVERY piece and not just the mover, because
    `clear_turn_flags` wipes `moved_last_turn` and `reactive_armed`
    board-wide and then re-arms bishops anywhere on the board;
  * the boulder's own state: position, cooldown, no-return memory,
    `on_intersection`, `first_move`;
  * `captured_pieces`, which gates which TRANSFORMATIONS are legal, so
    getting it wrong changes the legal-move set;
  * the repetition history and the tiny-endgame distance counts, which
    the state hash deliberately EXCLUDES -- so the hash alone cannot
    verify an undo and both are checked separately;
  * the scalars: whose turn, turn number, winner, loss reason,
    last move and its turn number, and the tiny-endgame flag.

HOW IT IS VERIFIED. `lgref/tests/test_undo.py` applies and undoes every
legal turn in thousands of positions, including nested sequences, and
after each undo requires the board state hash, the full sorted
legal-turn list, the repetition counts, the distance counts and the
capture record all to match what they were. The hash is defined as the
full legal-move-determining state, so hash plus the two excluded
counters plus the legal-move list is a complete check.
"""

import collections

#: Every mutable per-piece attribute. Over-inclusive on purpose: a flag
#: that does not exist on a piece reads as None and restores as None,
#: which costs a little and removes a whole class of omission.
PIECE_FLAGS = (
    'moved', 'cooldown', 'last_square', 'moved_last_turn',
    'reactive_armed', 'invulnerable', 'moved_by_queen', 'is_transformed',
    'is_royal', 'en_passant', 'on_intersection', 'first_move',
    'assassin_squares', 'line_of_sight', 'threat_squares', 'moves',
    'name', 'color', 'dir',
)

Token = collections.namedtuple(
    'Token', 'grid flags boulder scalars history distances captured')


def supports_undo(engine):
    """Can this engine be snapshotted cheaply?

    The fast path reads a board of squares and per-piece attributes, so
    it is available only for games shaped that way. A game without one
    -- an m,n,k board is a flat list of marks -- is searched by copying
    instead, which is correct and merely slower. Capability is DETECTED,
    not assumed, so adding the fast path did not cost the generality it
    was built alongside.
    """
    board = getattr(engine, 'board', None)
    return board is not None and hasattr(board, 'squares')


def snapshot(engine):
    """Capture everything a turn can change. Cheap by design."""
    board = engine.board
    grid = [[square.piece for square in row] for row in board.squares]
    flags = []
    seen = set()
    for row in board.squares:
        for square in row:
            piece = square.piece
            if piece is not None and id(piece) not in seen:
                seen.add(id(piece))
                flags.append((piece, [getattr(piece, name, None)
                                      for name in PIECE_FLAGS]))
    # The boulder may be held off-board while on the intersection, so it
    # is captured separately as well as through the grid.
    boulder = board.boulder
    if boulder is not None and id(boulder) not in seen:
        flags.append((boulder, [getattr(boulder, name, None)
                                for name in PIECE_FLAGS]))
    scalars = (
        engine.current_player, engine.turn_number, engine.winner,
        engine.loss_reason, board.turn_number, board.last_move,
        board.last_move_turn_number, board.tiny_endgame_active,
        board.last_action, board.boulder,
        getattr(engine, '_last_manipulated_by', None),
        getattr(engine, '_manipulation_cooldown', None),
        getattr(engine, '_extra_granted_last', None),
        getattr(engine, '_repetition_blocks', None),
        getattr(engine, '_endgame_blocks', None),
    )
    return Token(
        grid=grid,
        flags=flags,
        boulder=boulder,
        scalars=scalars,
        history=dict(board.state_history),
        distances=list(board.distance_counts),
        captured={colour: list(names)
                  for colour, names in board.captured_pieces.items()},
    )


def restore(engine, token):
    """Put everything back, exactly."""
    board = engine.board
    for row_index, row in enumerate(board.squares):
        saved_row = token.grid[row_index]
        for col_index, square in enumerate(row):
            square.piece = saved_row[col_index]
    for piece, values in token.flags:
        for name, value in zip(PIECE_FLAGS, values):
            if value is not None or hasattr(piece, name):
                setattr(piece, name, value)
    (engine.current_player, engine.turn_number, engine.winner,
     engine.loss_reason, board.turn_number, board.last_move,
     board.last_move_turn_number, board.tiny_endgame_active,
     board.last_action, board.boulder, manipulated, cooldown, extra,
     rep_blocks, end_blocks) = token.scalars
    engine._last_manipulated_by = manipulated
    engine._manipulation_cooldown = cooldown
    engine._extra_granted_last = extra
    engine._repetition_blocks = rep_blocks
    engine._endgame_blocks = end_blocks
    board.state_history.clear()
    board.state_history.update(token.history)
    board.distance_counts[:] = token.distances
    for colour, names in token.captured.items():
        board.captured_pieces[colour][:] = names
    # The threat cache is keyed on the occupants tuple, which the
    # restore has just changed back -- but the key is recomputed lazily,
    # so invalidating it explicitly costs nothing and removes any doubt.
    if hasattr(board, '_threat_key'):
        board._threat_key = None


def fingerprint(engine):
    """Everything an undo has to reproduce, as comparable data.

    The state hash is the full legal-move-determining state, but it
    deliberately omits the repetition counts and the tiny-endgame
    distance counts, so those are included here explicitly -- otherwise
    an undo that corrupted them would pass unnoticed.
    """
    board = engine.board
    turns = engine.get_all_legal_turns()
    return (
        board.get_state_hash(engine.current_player),
        engine.current_player, engine.turn_number, engine.winner,
        engine.loss_reason,
        tuple(sorted(repr(turn) for turn in turns)),
        tuple(sorted(board.state_history.items())),
        tuple(board.distance_counts),
        tuple(sorted((colour, tuple(names))
                     for colour, names in board.captured_pieces.items())),
    )
