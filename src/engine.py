"""
Headless game engine for self-play and data collection.

Manages a full game without any UI dependency. Provides a unified turn API
for AI players: get_all_legal_turns() returns every possible action, and
execute_turn() applies one and advances the game state.
"""

from board import Board
from square import Square
from piece import *
from move import Move


class Turn:
    """One complete, fully-specified legal turn.

    A Turn carries ALL information needed to execute it — no secondary
    choices are deferred. Multi-step turns (knight jump-capture decisions,
    pawn promotion form choices) are enumerated by the engine as
    SEPARATE Turn objects, one per possible (move + sub-choice)
    combination. This means each distinct full turn is counted exactly
    once everywhere (random selection, network evaluation, training
    statistics) — no implicit branching at execution time.

    Turn types:
      - 'move': spatial move (piece from one square to another)
      - 'boulder': boulder move (from intersection or square)
      - 'manipulation': queen manipulates an enemy piece
      - 'transformation': queen transforms to a different piece type

    Sub-choice fields:
      - `jump_choice`: for a knight move that triggers reactive
        jump-capture, this Turn either takes the capture (jump_choice =
        (row, col) of the jumped piece) or declines (jump_choice = None).
        For moves that don't offer jump-capture, this is None.
      - `promo_choice`: for a pawn promotion move, the specific form
        chosen ('queen', 'rook', 'bishop', 'knight'). None otherwise.
    """

    def __init__(self, turn_type, piece=None, from_sq=None, to_sq=None,
                 move_obj=None, transform_target=None,
                 jump_choice=None, promo_choice=None,
                 has_jump_offer=False, is_capture=False):
        self.turn_type = turn_type              # 'move', 'boulder', 'manipulation', 'transformation'
        self.piece = piece                      # the piece being moved/acted on
        self.from_sq = from_sq                  # (row, col) or None
        self.to_sq = to_sq                      # (row, col) or None
        self.move_obj = move_obj                # Move object for board.move()
        self.transform_target = transform_target  # 'rook', 'bishop', 'knight', 'queen' for transformations
        self.jump_choice = jump_choice          # (row, col) target | None (decline OR no jump available)
        self.promo_choice = promo_choice        # promotion form string, or None
        # has_jump_offer distinguishes "no jump offered" (False) from
        # "jump offered but this Turn is the decline option" (True with
        # jump_choice=None). The engine sets this when constructing
        # decline-Turns; execute_turn uses it to apply the
        # invulnerability-after-decline side effects.
        self.has_jump_offer = has_jump_offer
        self.is_capture = is_capture            # whether the move captures a piece

    def __repr__(self):
        if self.turn_type == 'transformation':
            return f"Turn(transform {self.piece.name}@{self.from_sq} -> {self.transform_target})"
        elif self.turn_type in ('move', 'boulder', 'manipulation'):
            cap = ' capture' if self.is_capture else ''
            suffix = ''
            if self.jump_choice is not None:
                suffix = f' jump_capture={self.jump_choice}'
            elif self.has_jump_offer:
                suffix = ' jump_decline'
            if self.promo_choice is not None:
                suffix += f' promo={self.promo_choice}'
            return f"Turn({self.turn_type}{cap} {self.piece.name}@{self.from_sq}->{self.to_sq}{suffix})"
        return f"Turn({self.turn_type})"


class TurnRecord:
    """Data recorded for a single turn."""

    def __init__(self):
        self.turn_number = 0
        self.player = None                  # 'white' or 'black'
        self.turn_type = None               # 'move', 'boulder', 'manipulation', 'transformation'
        self.piece_type = None              # 'king', 'queen', 'rook', etc.
        self.piece_color = None             # color of the piece moved
        self.from_sq = None                 # (row, col)
        self.to_sq = None                   # (row, col)
        self.is_capture = False
        self.captured_piece_type = None     # type of captured piece, if any
        self.captured_piece_color = None    # color of captured piece, if any
        self.jump_capture_taken = None      # True/False/None (None if no jump capture available)
        self.jump_capture_target = None     # (row, col) of jump-captured piece, if any
        self.promotion_choice = None        # piece type chosen for promotion, if any
        self.transform_target = None        # piece type transformed to, if any
        self.legal_turn_count = 0           # branching factor
        self.royal_distance = 0
        self.tiny_endgame_active = False
        self.distance_counts = None         # list of 15 ints
        self.repetition_count = 0           # how many times current state has occurred
        self.pieces_remaining = None        # dict: {color: {type: count}}

    def to_dict(self):
        return {
            'turn_number': self.turn_number,
            'player': self.player,
            'turn_type': self.turn_type,
            'piece_type': self.piece_type,
            'piece_color': self.piece_color,
            'from_sq': self.from_sq,
            'to_sq': self.to_sq,
            'is_capture': self.is_capture,
            'captured_piece_type': self.captured_piece_type,
            'captured_piece_color': self.captured_piece_color,
            'jump_capture_taken': self.jump_capture_taken,
            'jump_capture_target': self.jump_capture_target,
            'promotion_choice': self.promotion_choice,
            'transform_target': self.transform_target,
            'legal_turn_count': self.legal_turn_count,
            'royal_distance': self.royal_distance,
            'tiny_endgame_active': self.tiny_endgame_active,
            'distance_counts': self.distance_counts,
            'repetition_count': self.repetition_count,
            'pieces_remaining': self.pieces_remaining,
        }


class GameRecord:
    """Complete record of a single game."""

    def __init__(self):
        self.game_id = None
        self.winner = None                  # 'white', 'black', or None (turn cap)
        self.loss_reason = None             # 'royals_captured', 'no_legal_moves', 'turn_cap'
        self.total_turns = 0
        self.total_captures = 0
        self.turn_cap_reached = False
        self.tiny_endgame_activated = False
        self.tiny_endgame_activation_turn = None
        self.repetition_blocks = 0          # how many times repetition rule blocked a move
        self.endgame_blocks = 0             # how many times tiny endgame rule blocked a move
        self.manipulation_mode = 'original' # which manipulation variant was used
        self.turns = []                     # list of TurnRecord.to_dict()

    def to_dict(self):
        return {
            'game_id': self.game_id,
            'winner': self.winner,
            'loss_reason': self.loss_reason,
            'total_turns': self.total_turns,
            'total_captures': self.total_captures,
            'turn_cap_reached': self.turn_cap_reached,
            'tiny_endgame_activated': self.tiny_endgame_activated,
            'tiny_endgame_activation_turn': self.tiny_endgame_activation_turn,
            'repetition_blocks': self.repetition_blocks,
            'endgame_blocks': self.endgame_blocks,
            'manipulation_mode': self.manipulation_mode,
            'turns': self.turns,
        }


class GameEngine:
    """Headless game engine for self-play.

    Usage:
        engine = GameEngine()
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            turn = player.choose(turns)
            engine.execute_turn(turn, jump_capture_choice, promotion_choice)
        record = engine.get_game_record()
    """

    def __init__(self, max_turns=1000, manipulation_mode='freeze',
                 knight_mode=Board.KNIGHT_MODE_V2, enable_boulder=True,
                 enable_tiny_endgame=True, enable_manipulation=True,
                 extra_move_every=0):
        # The default manipulation_mode is 'freeze' (v2 rulebook
        # semantics): a manipulated piece is held in place — no
        # spatial move on its immediate next turn. The 'original'
        # mode preserves v1 semantics (forbidden return-to-previous-
        # square) and is only used by historical / variant code that
        # explicitly opts into it. Per RULEBOOK_v2.md (Queen
        # Manipulation, Restriction 1), v2 = freeze, so the default
        # matches the active rule set.
        valid_modes = ('original', 'freeze', 'exclusion_zone',
                       'freeze_invulnerable', 'freeze_invulnerable_no_repeat',
                       'freeze_no_repeat', 'freeze_invulnerable_cooldown')
        if manipulation_mode not in valid_modes:
            raise ValueError(f"Invalid manipulation_mode: {manipulation_mode!r}. "
                             f"Must be one of {valid_modes}.")
        self.manipulation_mode = manipulation_mode
        # --- LGMEF ablation switches (issue #168) ---
        # Each switch removes ONE mechanic relative to the full v2 rule
        # set, so matched self-play runs can measure that mechanic's
        # strategic impact. Defaults preserve the full game.
        #   knight_mode:          Board.KNIGHT_MODE_LEGACY = pre-v2 knight
        #                         (no radius-2 / jump-capture /
        #                         invulnerability) = "No Knight Redesign".
        #   enable_boulder:       False removes the neutral boulder from
        #                         the initial position entirely.
        #   enable_tiny_endgame:  False prevents the tiny-endgame rule
        #                         from ever activating.
        #   enable_manipulation:  False removes queen-manipulation turns
        #                         from generation. NOTE: the no-legal-
        #                         moves loss check still uses the full
        #                         rules (board.has_legal_moves), so a
        #                         player whose ONLY legal turns are
        #                         manipulations yields an empty turn
        #                         list without a loss — callers treat
        #                         that as a draw, which is the intended
        #                         ablation semantics.
        #   extra_move_every:     N > 0 grants the player who completed
        #                         turn number k (k % N == 0) an
        #                         immediate second turn. This is the
        #                         POSITIVE CONTROL — a deliberately
        #                         broken, obviously advantageous
        #                         mechanic that the MCI metric must
        #                         flag. Never part of a real variant.
        self.enable_tiny_endgame = enable_tiny_endgame
        self.enable_manipulation = enable_manipulation
        self.extra_move_every = extra_move_every
        self._extra_granted_last = False
        self.board = Board(knight_mode=knight_mode)
        if not enable_boulder:
            # The boulder starts on the central intersection, referenced
            # only via board.boulder (not on any square).
            self.board.boulder = None
        self.current_player = 'white'
        self.winner = None
        self.loss_reason = None
        self.turn_number = 0
        self.max_turns = max_turns
        self.game_record = GameRecord()
        self.game_record.manipulation_mode = manipulation_mode

        # Record initial board state for repetition rule
        self.board.record_state(self.current_player)

        # Track rule impact statistics
        self._repetition_blocks = 0
        self._endgame_blocks = 0

        # Track last manipulated piece per player (for no_repeat variants)
        self._last_manipulated_by = {'white': None, 'black': None}

        # Track manipulation cooldown per player (for cooldown variant)
        self._manipulation_cooldown = {'white': 0, 'black': 0}

    def is_game_over(self):
        """Check if the game has ended."""
        return self.winner is not None or self.turn_number >= self.max_turns

    def get_all_legal_turns(self):
        """Return all legal turns for the current player.

        Returns a list of Turn objects. Each Turn can be passed to execute_turn().
        Moves are already filtered by repetition and tiny endgame rules.
        """
        color = self.current_player
        opponent = 'black' if color == 'white' else 'white'
        turns = []

        # Clear invulnerable flags for current player's OWN pieces
        # (invulnerability was set on opponent's previous turn, now expires)
        if self.manipulation_mode in ('freeze_invulnerable',
                                      'freeze_invulnerable_no_repeat',
                                      'freeze_invulnerable_cooldown'):
            self.board.clear_invulnerable_for_color(color)

        # Clear moved_by_queen flags on opponent's pieces (the per-turn
        # freeze expires after one turn). In invulnerable manipulation
        # modes, the transition step both clears moved_by_queen and sets
        # the invulnerable flag instead of just clearing.
        if self.manipulation_mode in ('freeze_invulnerable',
                                      'freeze_invulnerable_no_repeat',
                                      'freeze_invulnerable_cooldown'):
            self.board.transition_moved_by_queen_to_invulnerable(color)
        elif self.manipulation_mode in ('freeze', 'freeze_no_repeat'):
            self.board.clear_moved_by_queen_for_opponent(color)

        # Update board state needed for move generation
        self.board.update_lines_of_sight()
        self.board.update_threat_squares()

        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if not piece:
                    continue

                if isinstance(piece, Boulder):
                    # Either player can move boulder (except white on turn 1)
                    if color == 'white' and self.board.turn_number == 0:
                        continue
                    if piece.cooldown > 0:
                        continue
                    self._generate_piece_turns(piece, row, col, 'boulder', color, turns)

                elif piece.color == color:
                    # Pieces held in place by recent manipulation can't make
                    # spatial moves but CAN perform actions.
                    if not piece.moved_by_queen:
                        # Own piece — generate moves
                        self._generate_piece_turns(piece, row, col, 'move', color, turns)

                    # Check transformation options for queens/transformed pieces
                    # (transformations are actions, not spatial moves — allowed
                    # even when the piece is held in place by manipulation)
                    is_queen_or_transformed = isinstance(piece, Queen) or piece.is_transformed
                    if is_queen_or_transformed:
                        options = self.board.get_transformation_options(piece)
                        options = self.board.filter_transformation_options(
                            piece, row, col, options, color)
                        for opt in options:
                            turns.append(Turn(
                                turn_type='transformation',
                                piece=piece,
                                from_sq=(row, col),
                                transform_target=opt,
                            ))

                elif piece.color == opponent and self.enable_manipulation:
                    # Enemy piece — check queen manipulation
                    self._generate_piece_turns(piece, row, col, 'manipulation', color, turns)

        # Boulder on intersection
        if self.board.boulder and self.board.boulder.on_intersection:
            if not (color == 'white' and self.board.turn_number == 0):
                boulder = self.board.boulder
                if boulder.cooldown <= 0:
                    boulder.clear_moves()
                    self.board.boulder_moves(boulder)
                    before = len(boulder.moves)
                    self.board.filter_repetition_moves(boulder, color)
                    self._repetition_blocks += before - len(boulder.moves)
                    before = len(boulder.moves)
                    self.board.filter_endgame_moves(boulder, color)
                    self._endgame_blocks += before - len(boulder.moves)

                    for move in boulder.moves:
                        is_cap = self.board.squares[move.final.row][move.final.col].has_piece()
                        # Check for jump targets (boulder doesn't jump, but use consistent API)
                        turns.append(Turn(
                            turn_type='boulder',
                            piece=boulder,
                            from_sq=None,  # intersection
                            to_sq=(move.final.row, move.final.col),
                            move_obj=move,
                            is_capture=is_cap,
                        ))
                    boulder.clear_moves()

        # Filter: no_repeat variants block manipulation of the same piece
        # the queen manipulated on her previous turn
        if self.manipulation_mode in ('freeze_invulnerable_no_repeat', 'freeze_no_repeat'):
            last_target = self._last_manipulated_by.get(color)
            if last_target is not None:
                turns = [t for t in turns
                         if not (t.turn_type == 'manipulation'
                                 and t.piece is last_target)]

        # Filter: cooldown variant blocks ALL manipulation for one turn after manipulating
        if self.manipulation_mode == 'freeze_invulnerable_cooldown':
            if self._manipulation_cooldown.get(color, 0) > 0:
                turns = [t for t in turns if t.turn_type != 'manipulation']

        return turns

    def _generate_piece_turns(self, piece, row, col, turn_type, color, turns):
        """Generate filtered moves for a piece and append Turn objects to turns list."""
        piece.clear_moves()

        if turn_type == 'manipulation':
            self.board.queen_moves_enemy(piece, row, col)
        elif isinstance(piece, Boulder):
            self.board.boulder_moves(piece, row, col)
        elif isinstance(piece, King):
            self.board.king_moves(piece, row, col)
        elif isinstance(piece, Queen):
            self.board.queen_moves(piece, row, col)
        elif isinstance(piece, Rook):
            self.board.rook_moves(piece, row, col)
        elif isinstance(piece, Bishop):
            self.board.bishop_moves(piece, row, col)
        elif isinstance(piece, Knight):
            self.board.knight_moves(piece, row, col)
        elif isinstance(piece, Pawn):
            self.board.pawn_moves(piece, row, col)

        # Track rule blocks before filtering
        before = len(piece.moves)
        self.board.filter_repetition_moves(piece, color)
        self._repetition_blocks += before - len(piece.moves)
        before = len(piece.moves)
        self.board.filter_endgame_moves(piece, color)
        self._endgame_blocks += before - len(piece.moves)

        for move in piece.moves:
            final_sq = self.board.squares[move.final.row][move.final.col]
            is_cap = final_sq.has_piece() and not isinstance(final_sq.piece, Boulder)

            # Check if this move triggers jump capture
            jump_targets = None
            if isinstance(piece, Knight) and not is_cap:
                jump_targets = self._predict_jump_targets(piece, move)

            # Check if this move triggers promotion
            promo_options = None
            if isinstance(piece, Pawn) and (move.final.row == 0 or move.final.row == 7):
                promo_options = self.board.get_promotion_options(piece.color)

            # Sub-choice expansion: enumerate each (jump_choice, promo_choice)
            # combination as a separate Turn so consumers (AI evaluation,
            # random selection, training statistics) see each fully-specified
            # turn exactly once.
            jump_combinations = (
                [(t[0], t[1]) for t in jump_targets] + [None]
                if jump_targets else [None]
            )
            promo_combinations = list(promo_options) if promo_options else [None]
            has_jump_offer = jump_targets is not None and len(jump_targets) > 0
            for jc in jump_combinations:
                for pc in promo_combinations:
                    turns.append(Turn(
                        turn_type=turn_type,
                        piece=piece,
                        from_sq=(row, col),
                        to_sq=(move.final.row, move.final.col),
                        move_obj=move,
                        is_capture=is_cap,
                        jump_choice=jc,
                        promo_choice=pc,
                        has_jump_offer=has_jump_offer,
                    ))

        piece.clear_moves()

    def _predict_jump_targets(self, knight, move):
        """Predict which jump capture targets would be available after a knight move.
        Does NOT execute the move — just checks what board.move() would return.

        v2 reactive jump-capture: a target list is returned only if the
        jumped piece is an enemy that moved on the immediately preceding
        turn. The list contains exactly that one target (the jumped piece)
        — adjacent (non-jumped) enemies are NOT returned. Returns None if
        no jump-capture is available.
        """
        initial = move.initial
        final = move.final

        # Delegate to the canonical board-level helper so engine and live game
        # agree on what counts as an eligible target.
        targets = self.board.get_jump_capture_targets_for_move(
            knight, initial.row, initial.col, final.row, final.col
        )
        return targets if targets else None

    def execute_turn(self, turn):
        """Execute a fully-specified turn and advance the game state.

        All sub-choices (jump-capture target or decline, promotion form)
        are read from the Turn object itself — the engine enumerates each
        combination as a separate Turn via get_all_legal_turns, so there
        are no implicit branches at execution time.

        Args:
            turn: Turn object from get_all_legal_turns()

        Returns:
            TurnRecord with all data about this turn.
        """
        # Pull sub-choices from the Turn itself.
        jump_capture_choice = turn.jump_choice
        promotion_choice = turn.promo_choice
        # Clear the last-manipulated tracker for this player (restriction lasts one turn)
        if self.manipulation_mode in ('freeze_invulnerable_no_repeat', 'freeze_no_repeat'):
            if turn.turn_type != 'manipulation':
                self._last_manipulated_by[self.current_player] = None

        # Cooldown: decrement cooldown, then set it if this is a manipulation
        if self.manipulation_mode == 'freeze_invulnerable_cooldown':
            cd = self._manipulation_cooldown
            # Decrement at start of turn (cooldown expires after one non-manipulation turn)
            if cd[self.current_player] > 0 and turn.turn_type != 'manipulation':
                cd[self.current_player] -= 1
            if turn.turn_type == 'manipulation':
                cd[self.current_player] = 1  # blocked for next turn

        record = TurnRecord()
        record.turn_number = self.turn_number
        record.player = self.current_player
        record.turn_type = turn.turn_type
        record.piece_type = turn.piece.name
        record.piece_color = turn.piece.color
        record.from_sq = turn.from_sq
        record.to_sq = turn.to_sq
        record.is_capture = turn.is_capture
        record.legal_turn_count = 0  # filled by caller or pre-computed

        # Record what's being captured
        if turn.is_capture and turn.to_sq:
            target = self.board.squares[turn.to_sq[0]][turn.to_sq[1]].piece
            if target:
                record.captured_piece_type = target.name
                record.captured_piece_color = target.color

        # Execute based on turn type
        if turn.turn_type == 'transformation':
            self._execute_transformation(turn, record)
        elif turn.turn_type in ('move', 'boulder', 'manipulation'):
            self._execute_spatial_turn(turn, record, jump_capture_choice, promotion_choice)

        # Record board state after turn
        record.royal_distance = self.board.get_royal_distance()
        record.tiny_endgame_active = self.board.tiny_endgame_active
        record.distance_counts = list(self.board.distance_counts)
        record.pieces_remaining = self._count_pieces()

        # Get repetition count for current state
        state = self.board.get_state_hash(self.current_player)
        record.repetition_count = self.board.state_history.get(state, 0)

        # Store turn record
        self.game_record.turns.append(record.to_dict())
        self.game_record.total_turns = self.turn_number

        return record

    def _execute_transformation(self, turn, record):
        """Execute a transformation turn."""
        row, col = turn.from_sq
        piece = self.board.squares[row][col].piece
        record.transform_target = turn.transform_target

        self.board.transform_queen(piece, row, col, turn.transform_target)
        # First-class flags: an action turn expires all last-move flags.
        self.board.record_action_turn()
        self.board.update_assassin_squares(self.current_player)
        self.board.decrement_boulder_cooldown()

        # Tiny endgame rule
        if self.board.tiny_endgame_active:
            self.board.update_distance_count(captured=False)
        if (self.enable_tiny_endgame
                and not self.board.tiny_endgame_active
                and self.board.is_tiny_endgame()):
            self.board.init_tiny_endgame()
            self.game_record.tiny_endgame_activated = True
            self.game_record.tiny_endgame_activation_turn = self.turn_number

        self._next_turn()

    def _execute_spatial_turn(self, turn, record, jump_capture_choice, promotion_choice):
        """Execute a move, boulder move, or manipulation turn."""
        captured = turn.is_capture

        # Execute the move
        jump_targets = self.board.move(turn.piece, turn.move_obj)

        # Handle jump capture
        if jump_targets:
            if jump_capture_choice and jump_capture_choice in [(t[0], t[1]) for t in jump_targets]:
                cap_piece = self.board.squares[jump_capture_choice[0]][jump_capture_choice[1]].piece
                if cap_piece:
                    record.jump_capture_taken = True
                    record.jump_capture_target = jump_capture_choice
                    record.captured_piece_type = cap_piece.name
                    record.captured_piece_color = cap_piece.color
                self.board.execute_jump_capture(jump_capture_choice[0], jump_capture_choice[1])
                captured = True
            else:
                record.jump_capture_taken = False
                # v2 knight: declined jump-capture → jumped piece survives →
                # knight gains invulnerability for one opponent turn iff the
                # adjacent-enemy condition is met at the landing square.
                # `turn.to_sq` is the landing square; v2 jump_targets always
                # has exactly one entry (the jumped piece), so its coords are
                # at index 0.
                landing_r, landing_c = turn.to_sq
                jumped_r, jumped_c = jump_targets[0]
                self.board.set_invulnerable_after_jump_decline(
                    turn.piece, landing_r, landing_c, jumped_r, jumped_c
                )

            # Handle manipulation effect for manipulated knight
            self.board.clear_forbidden_squares()
            if turn.piece.color != self.current_player:
                self._apply_manipulation_effect(turn.piece, turn.from_sq)

        # Handle promotion
        elif turn.promo_choice is not None and promotion_choice:
            record.promotion_choice = promotion_choice
            to_row, to_col = turn.to_sq
            self.board.promote(turn.piece, to_row, to_col, promotion_choice)
            # Promotion path: no update_distance_count (pawn existed)
            self.board.update_assassin_squares(self.current_player)
            self.board.decrement_boulder_cooldown()

            # If the move that triggered promotion was a manipulation
            # (the manipulator moved an enemy pawn that ended up on its
            # promotion rank), apply the manipulation effect to the
            # newly-promoted piece. Without this, the new piece would
            # default to moved_by_queen=False and could move on its
            # owner's immediate next turn, escaping the manipulation
            # effect entirely.
            if turn.turn_type == 'manipulation':
                new_piece = self.board.squares[to_row][to_col].piece
                self._apply_manipulation_effect(new_piece, turn.from_sq)

            if captured:
                self.winner = self.board.check_winner()
                if self.winner:
                    self.loss_reason = 'royals_captured'
            if self.enable_tiny_endgame and self.board.is_tiny_endgame():
                self.board.init_tiny_endgame()
                self.game_record.tiny_endgame_activated = True
                self.game_record.tiny_endgame_activation_turn = self.turn_number
            self._next_turn()
            record.is_capture = captured
            if captured:
                self.game_record.total_captures += 1
            return

        else:
            # Normal move completion
            self.board.set_true_en_passant(turn.piece)
            self.board.clear_forbidden_squares()
            # Apply manipulation effect based on mode
            if turn.turn_type == 'manipulation':
                self._apply_manipulation_effect(turn.piece, turn.from_sq)

        # Common turn-ending logic (for non-promotion spatial moves)
        self.board.update_assassin_squares(self.current_player)
        self.board.decrement_boulder_cooldown(moved_piece=turn.piece)

        if captured:
            self.winner = self.board.check_winner()
            if self.winner:
                self.loss_reason = 'royals_captured'

        # Tiny endgame rule
        if self.board.tiny_endgame_active:
            self.board.update_distance_count(captured=captured)
        if (self.enable_tiny_endgame
                and not self.board.tiny_endgame_active
                and self.board.is_tiny_endgame()):
            self.board.init_tiny_endgame()
            self.game_record.tiny_endgame_activated = True
            self.game_record.tiny_endgame_activation_turn = self.turn_number

        record.is_capture = captured
        if captured:
            self.game_record.total_captures += 1

        self._next_turn()

    def _apply_manipulation_effect(self, piece, origin_sq):
        """Apply the manipulation aftermath based on the current mode.

        Args:
            piece: the manipulated piece (now at its new location)
            origin_sq: (row, col) where the piece was before manipulation
        """
        if self.manipulation_mode == 'original':
            piece.forbidden_square = origin_sq

        elif self.manipulation_mode == 'freeze':
            piece.moved_by_queen = True

        elif self.manipulation_mode in ('freeze_invulnerable', 'freeze_invulnerable_no_repeat',
                                        'freeze_invulnerable_cooldown'):
            piece.moved_by_queen = True
            # Invulnerability is NOT set here — it activates on turn N+2
            # when moved_by_queen is cleared (transition:
            # moved_by_queen -> invulnerable).
            # Track which piece this player just manipulated.
            self._last_manipulated_by[self.current_player] = piece

        elif self.manipulation_mode == 'freeze_no_repeat':
            piece.moved_by_queen = True
            # No invulnerability — the held-in-place piece CAN be captured by
            # enemies in this variant. Track for no-repeat filtering.
            self._last_manipulated_by[self.current_player] = piece

        elif self.manipulation_mode == 'exclusion_zone':
            # Build the exclusion zone: origin + all adjacent squares
            r, c = origin_sq
            zone = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        zone.append((nr, nc))
            piece.forbidden_zone = zone

    def _next_turn(self):
        """Switch to next player, record state, check for no-legal-moves loss."""
        # Positive-control mechanic (extra_move_every=N): the player who
        # completed turn k with k % N == 0 immediately moves again. The
        # _extra_granted_last latch prevents chaining extras. Turn
        # numbers still advance, and per-turn housekeeping (flag expiry,
        # state recording) runs unchanged — the control is INTENDED to
        # be crudely unbalanced, not rules-coherent.
        grant_extra = (self.extra_move_every > 0
                       and not self._extra_granted_last
                       and (self.turn_number + 1) % self.extra_move_every == 0)
        if grant_extra:
            self._extra_granted_last = True
        else:
            self._extra_granted_last = False
            self.current_player = 'white' if self.current_player == 'black' else 'black'
        self.board.turn_number += 1
        self.turn_number += 1
        # v2 knight: a knight that gained invulnerability on its owner's
        # turn N stayed uncapturable through opponent's turn N+1. At the
        # start of the owner's turn N+2, that invulnerability expires.
        # Mirror the v2 game's Game.next_turn logic here so AI paths agree.
        self.board.clear_invulnerable_for_color(self.current_player)
        self.board.record_state(self.current_player)

        # Check no-legal-moves loss
        if not self.winner and not self.is_game_over():
            if not self.board.has_legal_moves(self.current_player):
                self.winner = 'white' if self.current_player == 'black' else 'black'
                self.loss_reason = 'no_legal_moves'

    def _count_pieces(self):
        """Count remaining pieces by color and type."""
        counts = {'white': {}, 'black': {}}
        for row in range(8):
            for col in range(8):
                piece = self.board.squares[row][col].piece
                if piece and piece.color in counts:
                    name = 'queen' if piece.is_transformed else piece.name
                    counts[piece.color][name] = counts[piece.color].get(name, 0) + 1
        return counts

    def get_game_record(self, game_id=None):
        """Finalize and return the game record."""
        self.game_record.game_id = game_id
        self.game_record.winner = self.winner
        self.game_record.loss_reason = self.loss_reason
        self.game_record.total_turns = self.turn_number
        self.game_record.repetition_blocks = self._repetition_blocks
        self.game_record.endgame_blocks = self._endgame_blocks

        if self.turn_number >= self.max_turns and not self.winner:
            self.game_record.turn_cap_reached = True
            self.game_record.loss_reason = 'turn_cap'

        return self.game_record
