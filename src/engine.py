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
    """Represents a single complete turn a player can take.

    Turn types:
      - 'move': spatial move (piece from one square to another)
      - 'boulder': boulder move (from intersection or square)
      - 'manipulation': queen manipulates an enemy piece
      - 'transformation': queen transforms to a different piece type

    For moves that involve secondary choices (jump capture, promotion),
    the choices are stored as lists. The AI must select from them.
    """

    def __init__(self, turn_type, piece=None, from_sq=None, to_sq=None,
                 move_obj=None, transform_target=None,
                 jump_capture_targets=None, promotion_options=None,
                 is_capture=False):
        self.turn_type = turn_type              # 'move', 'boulder', 'manipulation', 'transformation'
        self.piece = piece                      # the piece being moved/acted on
        self.from_sq = from_sq                  # (row, col) or None
        self.to_sq = to_sq                      # (row, col) or None
        self.move_obj = move_obj                # Move object for board.move()
        self.transform_target = transform_target  # 'rook', 'bishop', 'knight', 'queen' for transformations
        self.jump_capture_targets = jump_capture_targets  # list of (row, col) or None
        self.promotion_options = promotion_options  # list of type strings or None
        self.is_capture = is_capture            # whether the move captures a piece

    def __repr__(self):
        if self.turn_type == 'transformation':
            return f"Turn(transform {self.piece.name}@{self.from_sq} -> {self.transform_target})"
        elif self.turn_type in ('move', 'boulder', 'manipulation'):
            cap = ' capture' if self.is_capture else ''
            suffix = ''
            if self.jump_capture_targets:
                suffix = f' jump_targets={self.jump_capture_targets}'
            if self.promotion_options:
                suffix += f' promo={self.promotion_options}'
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

    def __init__(self, max_turns=1000, manipulation_mode='original'):
        valid_modes = ('original', 'freeze', 'exclusion_zone',
                       'freeze_invulnerable', 'freeze_invulnerable_no_repeat',
                       'freeze_no_repeat', 'freeze_invulnerable_cooldown')
        if manipulation_mode not in valid_modes:
            raise ValueError(f"Invalid manipulation_mode: {manipulation_mode!r}. "
                             f"Must be one of {valid_modes}.")
        self.manipulation_mode = manipulation_mode
        self.board = Board()
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

        # Clear frozen flags for opponent's pieces (unfreeze after one turn)
        # In invulnerable modes: transition frozen -> invulnerable
        if self.manipulation_mode in ('freeze_invulnerable',
                                      'freeze_invulnerable_no_repeat',
                                      'freeze_invulnerable_cooldown'):
            self.board.transition_frozen_to_invulnerable(color)
        elif self.manipulation_mode in ('freeze', 'freeze_no_repeat'):
            self.board.clear_frozen_for_color(color)

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
                    # Frozen pieces can't make spatial moves but CAN perform actions
                    if not piece.frozen:
                        # Own piece — generate moves
                        self._generate_piece_turns(piece, row, col, 'move', color, turns)

                    # Check transformation options for queens/transformed pieces
                    # (transformations are actions, not spatial moves — allowed even when frozen)
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

                elif piece.color == opponent:
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

            turns.append(Turn(
                turn_type=turn_type,
                piece=piece,
                from_sq=(row, col),
                to_sq=(move.final.row, move.final.col),
                move_obj=move,
                is_capture=is_cap,
                jump_capture_targets=jump_targets,
                promotion_options=promo_options,
            ))

        piece.clear_moves()

    def _predict_jump_targets(self, knight, move):
        """Predict which jump capture targets would be available after a knight move.
        Does NOT execute the move — just checks what board.move() would return."""
        initial = move.initial
        final = move.final

        # Determine jumped square
        dr = final.row - initial.row
        dc = final.col - initial.col
        jumped_row = initial.row + (1 if dr > 0 else (-1 if dr < 0 else 0))
        jumped_col = initial.col + (1 if dc > 0 else (-1 if dc < 0 else 0))

        # Check if knight jumped over a piece
        if not (Square.in_range(jumped_row, jumped_col) and
                self.board.squares[jumped_row][jumped_col].has_piece()):
            return None

        # Landing must be empty for jump capture
        if self.board.squares[final.row][final.col].has_piece():
            return None

        # Find adjacent enemies at landing
        targets = []
        for dr2 in [-1, 0, 1]:
            for dc2 in [-1, 0, 1]:
                if dr2 == 0 and dc2 == 0:
                    continue
                ar, ac = final.row + dr2, final.col + dc2
                if Square.in_range(ar, ac):
                    adj = self.board.squares[ar][ac]
                    if adj.has_enemy_piece(knight.color):
                        targets.append((ar, ac))

        return targets if targets else None

    def execute_turn(self, turn, jump_capture_choice=None, promotion_choice=None):
        """Execute a turn and advance the game state.

        Args:
            turn: Turn object from get_all_legal_turns()
            jump_capture_choice: (row, col) to capture, or None to decline.
                                 Required when turn.jump_capture_targets is not None.
            promotion_choice: piece type string ('queen', 'rook', etc.).
                              Required when turn.promotion_options is not None.

        Returns:
            TurnRecord with all data about this turn.
        """
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
        self.board.update_assassin_squares(self.current_player)
        self.board.decrement_boulder_cooldown()

        # Tiny endgame rule
        if self.board.tiny_endgame_active:
            self.board.update_distance_count(captured=False)
        if not self.board.tiny_endgame_active and self.board.is_tiny_endgame():
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

            # Handle manipulation effect for manipulated knight
            self.board.clear_forbidden_squares()
            if turn.piece.color != self.current_player:
                self._apply_manipulation_effect(turn.piece, turn.from_sq)

        # Handle promotion
        elif turn.promotion_options is not None and promotion_choice:
            record.promotion_choice = promotion_choice
            to_row, to_col = turn.to_sq
            self.board.promote(turn.piece, to_row, to_col, promotion_choice)
            # Promotion path: no update_distance_count (pawn existed)
            self.board.update_assassin_squares(self.current_player)
            self.board.decrement_boulder_cooldown()
            if captured:
                self.winner = self.board.check_winner()
                if self.winner:
                    self.loss_reason = 'royals_captured'
            if self.board.is_tiny_endgame():
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
        if not self.board.tiny_endgame_active and self.board.is_tiny_endgame():
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
            piece.frozen = True

        elif self.manipulation_mode in ('freeze_invulnerable', 'freeze_invulnerable_no_repeat',
                                        'freeze_invulnerable_cooldown'):
            piece.frozen = True
            # Invulnerability is NOT set here — it activates on turn N+2
            # when frozen is cleared (transition: frozen -> invulnerable)
            # Track which piece this player just manipulated
            self._last_manipulated_by[self.current_player] = piece

        elif self.manipulation_mode == 'freeze_no_repeat':
            piece.frozen = True
            # No invulnerability — frozen piece CAN be captured by enemies
            # Track for no-repeat filtering
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
        self.current_player = 'white' if self.current_player == 'black' else 'black'
        self.board.turn_number += 1
        self.turn_number += 1
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
