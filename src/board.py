from const import *
from square import Square
from piece import *
from move import Move
import copy
import os

class Board:

    def __init__(self):
        self.squares = [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)]
        self.last_move = None    # last spatial move (used for manipulation restriction)
        self.last_action = None  # last non-spatial action square (used for highlight only)
        self.boulder = None  # Boulder reference when on central intersection (not on any square)
        self.turn_number = 0  # incremented each turn; white turn 1 = turn 0
        self.captured_pieces = {'white': [], 'black': []}  # piece names captured per color
        self.state_history = {}  # {state_hash: count} for repetition rule
        self.tiny_endgame_active = False
        self.distance_counts = [0] * 15  # indices 0-14 for royal distances
        self._create()
        self._add_pieces('white')
        self._add_pieces('black')
        self._add_boulder()

    def move(self, piece, move, testing=False):
        initial = move.initial
        final = move.final

        final_square_empty = self.squares[final.row][final.col].isempty()

        # Record capture (before overwriting the square)
        # Transformed queens are recorded as 'queen' (their true identity)
        if not final_square_empty:
            captured_piece = self.squares[final.row][final.col].piece
            if captured_piece and captured_piece.color in self.captured_pieces:
                name = 'queen' if captured_piece.is_transformed else captured_piece.name
                self.captured_pieces[captured_piece.color].append(name)

        # Boulder moving from intersection: don't clear initial square (it's not on one)
        if isinstance(piece, Boulder) and piece.on_intersection:
            self.squares[final.row][final.col].piece = piece
            self.boulder = None  # no longer on intersection
        else:
            # console board move update
            self.squares[initial.row][initial.col].piece = None
            self.squares[final.row][final.col].piece = piece

        if isinstance(piece, Pawn):
            pass
            # # en passant capture
            # diff = final.col - initial.col
            # if diff != 0 and final_square_empty: # Previously en_passant_empty
            #     # console board move update
            #     self.squares[initial.row][initial.col + diff].piece = None
            #     self.squares[final.row][final.col].piece = piece
            #     if not testing:
            #         sound = Sound(
            #             os.path.join('assets/sounds/capture.wav'))
            #         sound.play()

        if isinstance(piece, Knight):
            jumped = self.get_jumped_square(initial.row, initial.col, final.row, final.col)

            # Jump capture: if landing on empty square and jumped over a piece,
            # player may capture one adjacent enemy piece
            if final_square_empty and jumped:
                jumped_row, jumped_col = jumped
                if Square.in_range(jumped_row, jumped_col) and self.squares[jumped_row][jumped_col].has_piece():
                    # Jumped over a piece — find adjacent enemy targets
                    targets = self.get_jump_capture_targets(piece, final.row, final.col)
                    if len(targets) > 0:
                        # Return targets so the UI can let the player choose
                        # move is already done (piece placed on landing square)
                        # set last move and moved flag before returning
                        piece.moved = True
                        piece.clear_moves()
                        self.last_move = move
                        return targets
                    # No adjacent enemies — normal move (no capture)

        # boulder: set cooldown, update memory, clear intersection flag
        if isinstance(piece, Boulder):
            piece.cooldown = 2  # both players must take a turn
            piece.last_square = (initial.row, initial.col)
            piece.first_move = False
            piece.on_intersection = False

        # king castling
        if isinstance(piece, King):
            if self.castling(initial, final) and not testing:
                diff = final.col - initial.col
                rook = piece.left_rook if (diff < 0) else piece.right_rook
                self.move(rook, rook.moves[-1])

        # move
        piece.moved = True

        # clear manipulation restrictions after the piece moves (restriction only lasts one turn)
        piece.forbidden_square = None
        piece.forbidden_zone = None

        # clear valid moves
        piece.clear_moves()

        # set last move (spatial) and clear action highlight
        self.last_move = move
        self.last_action = None

    # Radius-2 move offsets (must match knight_moves())
    KNIGHT_DIFFS = [
        (-2, 0),  (-2, 1),  (-1, 2),  (0, 2),
        (1, 2),   (2, 1),   (2, 0),   (2, -1),
        (1, -2),  (0, -2),  (-1, -2), (-2, -1),
        (-2, 2),  (2, 2),   (2, -2),  (-2, -2),
    ]

    # Jumped square offset for each move index (1 square along primary direction)
    KNIGHT_JUMPED_OFFSETS = [
        (-1, 0),  (-1, 0),  (0, 1),   (0, 1),
        (0, 1),   (1, 0),   (1, 0),   (1, 0),
        (0, -1),  (0, -1),  (0, -1),  (-1, 0),
        (-1, 1),  (1, 1),   (1, -1),  (-1, -1),
    ]

    def get_jumped_square(self, initial_row, initial_col, final_row, final_col):
        """Return (jumped_row, jumped_col) for a knight move, or None if invalid."""
        diff = (final_row - initial_row, final_col - initial_col)
        for i, d in enumerate(self.KNIGHT_DIFFS):
            if d == diff:
                dr, dc = self.KNIGHT_JUMPED_OFFSETS[i]
                return (initial_row + dr, initial_col + dc)
        return None

    def get_jump_capture_targets(self, piece, landing_row, landing_col):
        """Return list of (row, col) of enemy pieces adjacent to landing square
        that could be captured via jump capture."""
        targets = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = landing_row + dr, landing_col + dc
                if Square.in_range(r, c) and self.squares[r][c].has_enemy_piece(piece.color):
                    targets.append((r, c))
        return targets

    def valid_move(self, piece, move):
        return move in piece.moves

    def check_promotion(self, piece, final):
        """Check if a pawn reached the last rank. Returns True if promotion is needed."""
        if isinstance(piece, Pawn) and (final.row == 0 or final.row == 7):
            return True
        return False

    def check_winner(self):
        """Check if either player has lost both royal pieces.
        Returns 'white' if white wins, 'black' if black wins, None otherwise."""
        white_royals = 0
        black_royals = 0
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.is_royal:
                    if piece.color == 'white':
                        white_royals += 1
                    elif piece.color == 'black':
                        black_royals += 1
        if black_royals == 0:
            return 'white'
        if white_royals == 0:
            return 'black'
        return None

    def has_legal_moves(self, color):
        """Check if a player has any legal moves or actions available.
        Considers: own piece moves, boulder moves, enemy piece manipulation,
        and queen transformation options. All filtered by repetition and
        tiny endgame rules. Returns True if at least one legal action exists."""
        opponent = 'black' if color == 'white' else 'white'

        # Check own pieces for moves
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if not piece:
                    continue

                # Boulder — either player can move it (skip turn 1 for white)
                if isinstance(piece, Boulder):
                    if color == 'white' and self.turn_number == 0:
                        continue
                    piece.clear_moves()
                    self.boulder_moves(piece, row, col)
                    self.filter_repetition_moves(piece, color)
                    self.filter_endgame_moves(piece, color)
                    if piece.moves:
                        piece.clear_moves()
                        return True
                    piece.clear_moves()
                    continue

                if piece.color == color:
                    # Frozen / moved-by-queen pieces can't make spatial moves but CAN perform actions
                    if not piece.frozen and not piece.moved_by_queen:
                        piece.clear_moves()
                        if isinstance(piece, King):
                            self.king_moves(piece, row, col)
                        elif isinstance(piece, Queen):
                            self.queen_moves(piece, row, col)
                        elif isinstance(piece, Rook):
                            self.rook_moves(piece, row, col)
                        elif isinstance(piece, Bishop):
                            self.bishop_moves(piece, row, col)
                        elif isinstance(piece, Knight):
                            self.knight_moves(piece, row, col)
                        elif isinstance(piece, Pawn):
                            self.pawn_moves(piece, row, col)

                        self.filter_repetition_moves(piece, color)
                        self.filter_endgame_moves(piece, color)
                        if piece.moves:
                            piece.clear_moves()
                            return True
                        piece.clear_moves()

                    # Check transformation options for queens/transformed pieces
                    # (actions are allowed even when frozen)
                    is_queen_or_transformed = isinstance(piece, Queen) or piece.is_transformed
                    if is_queen_or_transformed:
                        options = self.get_transformation_options(piece)
                        options = self.filter_transformation_options(
                            piece, row, col, options, color)
                        if options:
                            return True

                elif piece.color == opponent:
                    # Check queen manipulation of enemy pieces
                    piece.clear_moves()
                    self.queen_moves_enemy(piece, row, col)
                    self.filter_repetition_moves(piece, color)
                    self.filter_endgame_moves(piece, color)
                    if piece.moves:
                        piece.clear_moves()
                        return True
                    piece.clear_moves()

        # Check boulder on intersection
        if self.boulder and self.boulder.on_intersection:
            if not (color == 'white' and self.turn_number == 0):
                self.boulder.clear_moves()
                self.boulder_moves(self.boulder)
                self.filter_repetition_moves(self.boulder, color)
                self.filter_endgame_moves(self.boulder, color)
                if self.boulder.moves:
                    self.boulder.clear_moves()
                    return True
                self.boulder.clear_moves()

        return False

    def _get_piece_type_for_comparison(self, piece):
        """Get the piece type name for tiny endgame comparison.
        Royal queens count as 'queen' even while transformed.
        Promoted queens also count as 'queen'."""
        if piece.is_royal and piece.name != 'king':
            return 'queen'  # royal queen, even if transformed
        if isinstance(piece, Queen):
            return 'queen'  # promoted queen in base form
        if piece.is_transformed:
            return 'queen'  # promoted queen transformed
        return piece.name

    def is_tiny_endgame(self):
        """Check if the tiny endgame rule is active.
        Requires: no pawns AND (<=4 non-neutral pieces OR <=6 with same types ignoring kings)."""
        pieces = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color != 'none':  # exclude boulder
                    if isinstance(piece, Pawn):
                        return False  # pawns present, rule not active
                    pieces.append(piece)

        count = len(pieces)
        if count <= 4:
            return True

        if count <= 6:
            # Check if both sides have the same remaining piece types (ignoring kings)
            white_types = sorted([self._get_piece_type_for_comparison(p)
                                  for p in pieces if p.color == 'white' and not isinstance(p, King)])
            black_types = sorted([self._get_piece_type_for_comparison(p)
                                  for p in pieces if p.color == 'black' and not isinstance(p, King)])
            return white_types == black_types

        return False

    def get_royal_distance(self):
        """Get the Manhattan distance between the closest pair of opposing royal pieces."""
        white_royals = []
        black_royals = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.is_royal:
                    if piece.color == 'white':
                        white_royals.append((row, col))
                    elif piece.color == 'black':
                        black_royals.append((row, col))

        min_dist = float('inf')
        for wr, wc in white_royals:
            for br, bc in black_royals:
                dist = abs(wr - br) + abs(wc - bc)
                if dist < min_dist:
                    min_dist = dist

        return min_dist if min_dist != float('inf') else 0

    def init_tiny_endgame(self):
        """Initialize distance counts when tiny endgame rule first activates."""
        self.distance_counts = [0] * 15  # indices 0-14, index 0 unused
        self.tiny_endgame_active = True
        dist = self.get_royal_distance()
        if 1 <= dist <= 14:
            self.distance_counts[dist] = 1

    def update_distance_count(self, captured=False):
        """Update distance counts after a turn.
        Non-capture: increment count for resulting distance.
        Capture: reset all counts, re-init if rule still applies."""
        if not self.tiny_endgame_active:
            return

        if captured:
            # Reset all counts
            self.distance_counts = [0] * 15
            # Re-initialize if rule still applies
            if self.is_tiny_endgame():
                dist = self.get_royal_distance()
                if 1 <= dist <= 14:
                    self.distance_counts[dist] = 1
            else:
                self.tiny_endgame_active = False
        else:
            dist = self.get_royal_distance()
            if 1 <= dist <= 14:
                self.distance_counts[dist] += 1

    def would_exceed_distance_limit(self, piece, move, next_player):
        """Check if a non-capture move would push the distance count above 3.
        Capture moves always return False (they're always allowed)."""
        if not self.tiny_endgame_active:
            return False

        final = move.final
        # If the move is a capture, it's always allowed
        if self.squares[final.row][final.col].has_piece() and \
           self.squares[final.row][final.col].piece.color != piece.color:
            return False

        # Simulate the move to find resulting royal distance
        initial = move.initial
        initial_piece = None
        if initial.row >= 0 and initial.col >= 0:
            initial_piece = self.squares[initial.row][initial.col].piece
        captured_piece = self.squares[final.row][final.col].piece

        if initial.row >= 0 and initial.col >= 0:
            self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece

        dist = self.get_royal_distance()

        # Undo
        self.squares[final.row][final.col].piece = captured_piece
        if initial.row >= 0 and initial.col >= 0:
            self.squares[initial.row][initial.col].piece = initial_piece

        if 1 <= dist <= 14:
            return self.distance_counts[dist] >= 3
        return False

    def filter_endgame_moves(self, piece, next_player):
        """Remove non-capture moves that would exceed the distance count limit."""
        if not self.tiny_endgame_active:
            return
        piece.moves = [m for m in piece.moves
                       if not self.would_exceed_distance_limit(piece, m, next_player)]

    def get_state_hash(self, next_player):
        """Compute a hashable representation of the current board state.
        Includes piece positions (type, color, is_royal, is_transformed),
        boulder markers (on_intersection, cooldown, last_square), and whose turn."""
        state = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece:
                    entry = (row, col, piece.name, piece.color,
                             piece.is_royal, piece.is_transformed)
                    # Boulder has additional state that affects the game
                    if isinstance(piece, Boulder):
                        entry = entry + (piece.cooldown, piece.last_square)
                    state.append(entry)
        # Boulder on intersection (not on any square)
        if self.boulder and self.boulder.on_intersection:
            state.append(('boulder_intersection',
                          self.boulder.cooldown, self.boulder.last_square))
        # Whose turn
        state.append(('turn', next_player))
        return tuple(state)

    def record_state(self, next_player):
        """Record the current board state in history. Returns the count."""
        state = self.get_state_hash(next_player)
        self.state_history[state] = self.state_history.get(state, 0) + 1
        return self.state_history[state]

    def would_cause_repetition(self, piece, move, next_player):
        """Check if executing this move would cause a third repetition.
        Temporarily applies the move and all side effects (boulder cooldown,
        memory, intersection), hashes the state, then undoes everything."""
        initial = move.initial
        final = move.final

        # Save piece state
        initial_piece = None
        if initial.row >= 0 and initial.col >= 0:
            initial_piece = self.squares[initial.row][initial.col].piece
        captured_piece = self.squares[final.row][final.col].piece

        # Save boulder state (cooldown/memory may change)
        boulder_states = []
        for row in range(ROWS):
            for col in range(COLS):
                p = self.squares[row][col].piece
                if p and isinstance(p, Boulder):
                    boulder_states.append((row, col, p.cooldown, p.last_square, p.first_move, p.on_intersection))
        saved_board_boulder = self.boulder
        saved_boulder_intersection = None
        if self.boulder and self.boulder.on_intersection:
            saved_boulder_intersection = (self.boulder.cooldown, self.boulder.last_square,
                                           self.boulder.first_move, self.boulder.on_intersection)

        # Apply move
        if isinstance(piece, Boulder) and piece.on_intersection:
            self.squares[final.row][final.col].piece = piece
            self.boulder = None
        else:
            if initial.row >= 0 and initial.col >= 0:
                self.squares[initial.row][initial.col].piece = None
            self.squares[final.row][final.col].piece = piece

        # Simulate boulder side effects (same as board.move does)
        if isinstance(piece, Boulder):
            piece.cooldown = 2
            piece.last_square = (initial.row, initial.col) if initial.row >= 0 else None
            piece.first_move = False
            piece.on_intersection = False

        # Simulate boulder cooldown decrement (same as main.py does after move)
        for row in range(ROWS):
            for col in range(COLS):
                p = self.squares[row][col].piece
                if p and isinstance(p, Boulder) and p is not piece:
                    if p.cooldown > 0:
                        p.cooldown -= 1

        # Hash the resulting state (it will be the opponent's turn)
        opponent = 'black' if next_player == 'white' else 'white'
        state = self.get_state_hash(opponent)
        count = self.state_history.get(state, 0)

        # Undo move
        if isinstance(piece, Boulder) and saved_board_boulder is not None:
            self.boulder = saved_board_boulder
            self.squares[final.row][final.col].piece = captured_piece
        else:
            self.squares[final.row][final.col].piece = captured_piece
            if initial.row >= 0 and initial.col >= 0:
                self.squares[initial.row][initial.col].piece = initial_piece

        # Restore boulder state
        for row, col, cd, ls, fm, oi in boulder_states:
            p = self.squares[row][col].piece
            if p and isinstance(p, Boulder):
                p.cooldown = cd
                p.last_square = ls
                p.first_move = fm
                p.on_intersection = oi
        if saved_boulder_intersection is not None and self.boulder:
            self.boulder.cooldown = saved_boulder_intersection[0]
            self.boulder.last_square = saved_boulder_intersection[1]
            self.boulder.first_move = saved_boulder_intersection[2]
            self.boulder.on_intersection = saved_boulder_intersection[3]

        return count >= 2

    def filter_repetition_moves(self, piece, next_player):
        """Remove moves from a piece's move list that would cause a third repetition."""
        piece.moves = [m for m in piece.moves if not self.would_cause_repetition(piece, m, next_player)]

    def promote(self, piece, row, col, target_type):
        """Promote a pawn to a non-royal queen in the chosen form.
        'queen' = base form Queen, others = transformed piece instance."""
        color = piece.color

        PIECE_CLASSES = {
            'rook': Rook,
            'bishop': Bishop,
            'knight': Knight,
        }

        if target_type == 'queen':
            new_piece = Queen(color, is_royal=False)
            new_piece.is_transformed = False
        else:
            cls = PIECE_CLASSES.get(target_type)
            if not cls:
                return
            new_piece = cls(color)
            new_piece.is_transformed = True
            new_piece.is_royal = False

        new_piece.moved = True
        self.squares[row][col].piece = new_piece

    def get_promotion_options(self, color):
        """Return list of promotion options. Base form queen is always available.
        Other forms only if that piece type has been captured (legal queen forms)."""
        options = ['queen']
        captured = self.captured_pieces.get(color, [])
        captured_types = set(captured)
        for t in ('rook', 'bishop', 'knight'):
            if t in captured_types:
                options.append(t)
        return options

    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    def set_true_en_passant(self, piece):
        
        if not isinstance(piece, Pawn):
            return

        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    self.squares[row][col].piece.en_passant = False
        
        piece.en_passant = True

    def in_check(self, piece, move):
        temp_piece = copy.deepcopy(piece)
        temp_board = copy.deepcopy(self)
        temp_board.move(temp_piece, move, testing=True)
        
        for row in range(ROWS):
            for col in range(COLS):
                if temp_board.squares[row][col].has_enemy_piece(piece.color):
                    p = temp_board.squares[row][col].piece
                    temp_board.calc_moves(p, row, col, bool=False)
                    for m in p.moves:
                        if isinstance(m.final.piece, King):
                            return True
        
        return False

    def execute_jump_capture(self, row, col):
        """Execute a jump capture at the given square. Removes the piece there."""
        if Square.in_range(row, col) and self.squares[row][col].has_piece():
            captured = self.squares[row][col].piece
            if captured.color in self.captured_pieces:
                name = 'queen' if captured.is_transformed else captured.name
                self.captured_pieces[captured.color].append(name)
            self.squares[row][col].piece = None

    def clear_forbidden_squares(self):
        """Clear all forbidden_square and forbidden_zone restrictions."""
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_piece():
                    self.squares[row][col].piece.forbidden_square = None
                    self.squares[row][col].piece.forbidden_zone = None

    def clear_frozen_for_color(self, color):
        """Clear the frozen flag for opponent's pieces.
        Used by non-invulnerable freeze modes (freeze, freeze_no_repeat).
        Called at the start of the manipulating player's turn."""
        opponent = 'black' if color == 'white' else 'white'
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == opponent:
                    piece.frozen = False

    def clear_moved_by_queen_for_opponent(self, color):
        """Clear the moved_by_queen flag for the current player's opponent's pieces.

        Used by v2 game (freeze without no-repeat). Called at the start of
        each turn: when it becomes `color`'s turn, clear the freeze on
        the opponent's pieces, since the freeze only lasts for the owner's
        immediate next turn after manipulation.

        Trace: turn N (color=X manipulates Y's piece P, sets P.moved_by_queen=True);
        turn N+1 (color=Y, P is frozen); turn N+2 (color=X again — at start, clear
        P.moved_by_queen since opponent Y's freeze turn has ended).
        """
        opponent = 'black' if color == 'white' else 'white'
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == opponent:
                    piece.moved_by_queen = False

    def transition_frozen_to_invulnerable(self, color):
        """Transition opponent's frozen pieces to invulnerable.
        Used by invulnerable freeze modes. Called at start of manipulator's turn.
        Frozen flag is cleared, invulnerable flag is set (piece was frozen on
        owner's turn N+1, now becomes invulnerable on manipulator's turn N+2)."""
        opponent = 'black' if color == 'white' else 'white'
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == opponent and piece.frozen:
                    piece.frozen = False
                    piece.invulnerable = True

    def clear_invulnerable_for_color(self, color):
        """Clear the invulnerable flag for the current player's OWN pieces.
        Called at start of owner's turn (N+3) to expire invulnerability that
        was set on the manipulator's previous turn (N+2)."""
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == color:
                    piece.invulnerable = False

    def decrement_boulder_cooldown(self, moved_piece=None):
        """Decrement the boulder's cooldown by 1 (called each turn).
        Skip if the boulder itself was the piece that just moved (same turn)."""
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_piece() and isinstance(self.squares[row][col].piece, Boulder):
                    boulder = self.squares[row][col].piece
                    if boulder is moved_piece:
                        continue  # don't decrement on the same turn boulder was moved
                    if boulder.cooldown > 0:
                        boulder.cooldown -= 1

    def would_transformation_cause_repetition(self, piece, row, col, target_type, next_player):
        """Check if transforming a piece would cause a third repetition.
        Temporarily applies the transformation and boulder cooldown decrement,
        hashes the state, then undoes everything."""
        # Save current piece
        saved_piece = self.squares[row][col].piece

        # Save boulder state
        boulder_states = []
        for r in range(ROWS):
            for c in range(COLS):
                p = self.squares[r][c].piece
                if p and isinstance(p, Boulder):
                    boulder_states.append((r, c, p.cooldown, p.last_square, p.first_move, p.on_intersection))
        saved_board_boulder = self.boulder
        saved_boulder_intersection = None
        if self.boulder and self.boulder.on_intersection:
            saved_boulder_intersection = (self.boulder.cooldown, self.boulder.last_square,
                                           self.boulder.first_move, self.boulder.on_intersection)

        # Apply transformation
        self.transform_queen(piece, row, col, target_type)

        # Simulate boulder cooldown decrement (same as main.py does after transformation)
        for r in range(ROWS):
            for c in range(COLS):
                p = self.squares[r][c].piece
                if p and isinstance(p, Boulder):
                    if p.cooldown > 0:
                        p.cooldown -= 1

        # Hash the resulting state (it will be the opponent's turn)
        opponent = 'black' if next_player == 'white' else 'white'
        state = self.get_state_hash(opponent)
        count = self.state_history.get(state, 0)

        # Undo transformation — restore original piece
        self.squares[row][col].piece = saved_piece

        # Restore boulder state
        for r, c, cd, ls, fm, oi in boulder_states:
            p = self.squares[r][c].piece
            if p and isinstance(p, Boulder):
                p.cooldown = cd
                p.last_square = ls
                p.first_move = fm
                p.on_intersection = oi
        if saved_boulder_intersection is not None and self.boulder:
            self.boulder.cooldown = saved_boulder_intersection[0]
            self.boulder.last_square = saved_boulder_intersection[1]
            self.boulder.first_move = saved_boulder_intersection[2]
            self.boulder.on_intersection = saved_boulder_intersection[3]

        return count >= 2

    def would_transformation_exceed_distance_limit(self):
        """Check if any transformation (a non-capture, non-movement action)
        would push the distance count above 3. Since transformations don't
        change piece positions, the royal distance stays the same."""
        if not self.tiny_endgame_active:
            return False
        dist = self.get_royal_distance()
        if 1 <= dist <= 14:
            return self.distance_counts[dist] >= 3
        return False

    def filter_transformation_options(self, piece, row, col, options, next_player):
        """Remove transformation options that would cause a third repetition
        or would exceed the tiny endgame distance limit."""
        # If distance limit is exceeded, block all transformations
        # (non-capture, non-movement actions can't change the distance)
        if self.would_transformation_exceed_distance_limit():
            return []
        return [opt for opt in options
                if not self.would_transformation_cause_repetition(piece, row, col, opt, next_player)]

    def get_transformation_options(self, piece):
        """Return list of piece type names the piece can transform into.
        Excludes the current form. Includes 'queen' (revert) if transformed."""
        color = piece.color
        captured = self.captured_pieces.get(color, [])
        # Deduplicate captured types
        captured_types = list(set(captured))
        options = []

        if isinstance(piece, Queen):
            # In base form: can transform into any captured type
            for t in captured_types:
                if t in ('rook', 'bishop', 'knight'):
                    options.append(t)
        else:
            # Transformed form: can revert to queen or transform into other captured types
            options.append('queen')
            current_type = piece.name
            for t in captured_types:
                if t in ('rook', 'bishop', 'knight') and t != current_type:
                    options.append(t)

        return options

    def transform_queen(self, piece, row, col, target_type):
        """Transform a queen (or transformed queen) into the target piece type.
        Preserves color, is_royal, and position. Sets is_transformed accordingly."""
        is_royal = piece.is_royal

        PIECE_CLASSES = {
            'rook': Rook,
            'bishop': Bishop,
            'knight': Knight,
            'queen': Queen,
        }

        cls = PIECE_CLASSES.get(target_type)
        if not cls:
            return

        if target_type == 'queen':
            # Revert to base form
            new_piece = Queen(piece.color, is_royal=is_royal)
            new_piece.is_transformed = False
        else:
            # Transform into target piece
            new_piece = cls(piece.color)
            new_piece.is_transformed = True
            new_piece.is_royal = is_royal

        new_piece.moved = True
        self.squares[row][col].piece = new_piece

        # Highlight the transformed piece's square (non-spatial action)
        self.last_action = Square(row, col)

    def _diagonal_crosses_center(self, from_row, from_col, to_row, to_col):
        """Check if a diagonal step from (from_row, from_col) to (to_row, to_col)
        crosses the central intersection point (3.5, 3.5).
        This happens when moving diagonally between {d4, e5} and {e4, d5}:
          (4,3) <-> (3,4) or (3,3) <-> (4,4)."""
        pair = {(from_row, from_col), (to_row, to_col)}
        return pair == {(3, 3), (4, 4)} or pair == {(3, 4), (4, 3)}

    def straightline_squares(self, piece, row, col, incrs):
        squares = []

        for incr in incrs:
            row_incr, col_incr = incr
            possible_square_row = row + row_incr
            possible_square_col = col + col_incr

            prev_row, prev_col = row, col
            while True:
                if Square.in_range(possible_square_row, possible_square_col):
                    # Boulder on intersection blocks diagonals crossing the center
                    if self.boulder and self.boulder.on_intersection:
                        if self._diagonal_crosses_center(prev_row, prev_col, possible_square_row, possible_square_col):
                            break

                    # has team piece = break (boulder treated as friendly by both)
                    if self.squares[possible_square_row][possible_square_col].has_team_piece(piece.color):
                        break

                    # append possible squares
                    final_piece = self.squares[possible_square_row][possible_square_col].piece
                    squares.append(Square(possible_square_row, possible_square_col, final_piece))

                    # has enemy piece = break, empty = continue looping
                    if self.squares[possible_square_row][possible_square_col].has_enemy_piece(piece.color):
                        break

                # not in range
                else: break

                # incrementing incrs
                prev_row, prev_col = possible_square_row, possible_square_col
                possible_square_row += row_incr
                possible_square_col += col_incr

        # after looping through all incrs, return the list of squares
        return squares

    def straightline_of_sight_squares(self, row, col, incrs):
        squares = []

        for incr in incrs:
            row_incr, col_incr = incr
            possible_square_row = row + row_incr
            possible_square_col = col + col_incr
            prev_row, prev_col = row, col

            while True:
                if Square.in_range(possible_square_row, possible_square_col):
                    # Boulder on intersection blocks diagonal LOS crossing the center
                    if self.boulder and self.boulder.on_intersection:
                        if self._diagonal_crosses_center(prev_row, prev_col, possible_square_row, possible_square_col):
                            break

                    # append possible squares
                    final_piece = self.squares[possible_square_row][possible_square_col].piece
                    squares.append(Square(possible_square_row, possible_square_col, final_piece))

                    # has piece = break (boulder also blocks LOS)
                    if self.squares[possible_square_row][possible_square_col].has_piece():
                        break

                # not in range
                else: break

                # incrementing incrs
                prev_row, prev_col = possible_square_row, possible_square_col
                possible_square_row += row_incr
                possible_square_col += col_incr

        # after looping through all incrs, return the list of squares
        return squares

    def update_assassin_squares(self, color):
        for r in self.squares:
            for sq in r:
                if sq.has_team_piece(color):
                    piece = sq.piece

                    if isinstance(piece, Bishop):
                        piece.assassin_squares = []

                        squares = self.straightline_of_sight_squares(sq.row, sq.col, incrs=[
                            (-1, 1), # up-right
                            (1, 1), # down-right
                            (1, -1), # down-left
                            (-1, -1), # up-left
                        ])

                        for square in squares:
                            if square.has_enemy_piece(piece.color):
                                piece.assassin_squares.append(square)

    def update_lines_of_sight(self):
        for r in self.squares:
            for sq in r:
                if sq.has_piece():
                    piece = sq.piece
                    piece.line_of_sight = []
                    row = sq.row
                    col = sq.col

                    if isinstance(piece, Pawn):
                        line_of_sight = [
                            (row-1, col+0), # up
                            (row-1, col+1), # up-right
                            (row+0, col+1),  # right
                            (row+0, col-1), # left
                            (row-1, col-1) # up-left
                        ] if piece.dir == -1 else [
                            (row+1, col+0), # down
                            (row+1, col-1), # down-left
                            (row+0, col-1),  # left
                            (row+0, col+1), # right
                            (row+1, col+1) # down-right
                        ]

                        for square in line_of_sight:
                            square_row, square_col = square
                            if Square.in_range(square_row, square_col):
                                piece.line_of_sight.append(Square(square_row, square_col))

                    elif isinstance(piece, Knight):
                        # Radius-2 move destinations + adjacent squares (for jump capture)
                        line_of_sight = [
                            (row-2, col+0), # 2 up
                            (row-2, col+1), # 2 up, 1 right (L-shape)
                            (row-1, col+2), # 1 up, 2 right (L-shape)
                            (row+0, col+2), # 2 right
                            (row+1, col+2), # 1 down, 2 right (L-shape)
                            (row+2, col+1), # 2 down, 1 right (L-shape)
                            (row+2, col+0), # 2 down
                            (row+2, col-1), # 2 down, 1 left (L-shape)
                            (row+1, col-2), # 1 down, 2 left (L-shape)
                            (row+0, col-2), # 2 left
                            (row-1, col-2), # 1 up, 2 left (L-shape)
                            (row-2, col-1), # 2 up, 1 left (L-shape)
                            (row-2, col+2), # diagonal up-right
                            (row+2, col+2), # diagonal down-right
                            (row+2, col-2), # diagonal down-left
                            (row-2, col-2), # diagonal up-left
                            # Adjacent squares (for jump capture range)
                            (row-1, col+0), # 1 up
                            (row-1, col+1), # 1 up-right
                            (row+0, col+1), # 1 right
                            (row+1, col+1), # 1 down-right
                            (row+1, col+0), # 1 down
                            (row+1, col-1), # 1 down-left
                            (row+0, col-1), # 1 left
                            (row-1, col-1), # 1 up-left
                        ]

                        for square in line_of_sight:
                            square_row, square_col = square
                            if Square.in_range(square_row, square_col):
                                piece.line_of_sight.append(Square(square_row, square_col))

                    elif isinstance(piece, Bishop):
                        incrs = [
                            (-1, 1), # up-right
                            (1, 1),  # down-right
                            (1, -1), # down-left
                            (-1, -1) # up-left
                        ]

                        piece.line_of_sight = self.straightline_of_sight_squares(row, col, incrs)

                    elif isinstance(piece, Rook):
                        initial_squares = [
                            (row-1, col+0), # up
                            (row+0, col+1), # right
                            (row+1, col+0), # down
                            (row+0, col-1)  # left
                        ]

                        incr_pairs = [
                            [(0, 1), (0, -1)], # up: right, left
                            [(1, 0), (-1, 0)], # right: down, up
                            [(0, -1), (0, 1)], # down: left, right
                            [(-1, 0), (1, 0)]  # left: up, down
                        ]

                        indices_to_remove = []

                        for i in range(len(initial_squares)):
                            initial_row, initial_col = initial_squares[i]
                            if Square.in_range(initial_row, initial_col) and self.squares[initial_row][initial_col].isempty():
                                piece.line_of_sight.append(Square(initial_row, initial_col))
                            else:
                                indices_to_remove.append(i)

                        indices_to_remove.sort(reverse=True)

                        for i in range(len(indices_to_remove)):
                            index_to_remove = indices_to_remove[i]
                            initial_squares.remove(initial_squares[index_to_remove])
                            incr_pairs.remove(incr_pairs[index_to_remove])

                        for i in range(len(initial_squares)):
                            initial_row, initial_col = initial_squares[i]
                            incr_pair = incr_pairs[i]
                            squares = self.straightline_of_sight_squares(initial_row, initial_col, incr_pair)
                            piece.line_of_sight[len(piece.line_of_sight):] = squares[:]

                    elif isinstance(piece, Queen):
                        incrs = [
                            (-1, 0), # up
                            (-1, 1), # up-right
                            (0, 1),  # right
                            (1, 1),  # down-right
                            (1, 0),  # down
                            (1, -1), # down-left
                            (0, -1), # left
                            (-1, -1) # up-left
                        ]

                        piece.line_of_sight = self.straightline_of_sight_squares(row, col, incrs)

                    elif isinstance(piece, King):
                        line_of_sight = [
                            (row-1, col+0), # up
                            (row-1, col+1), # up-right
                            (row+0, col+1),  # right
                            (row+1, col+1),  # down-right
                            (row+1, col+0),  # down
                            (row+1, col-1), # down-left
                            (row+0, col-1), # left
                            (row-1, col-1) # up-left
                        ]

                        for square in line_of_sight:
                            square_row, square_col = square
                            if Square.in_range(square_row, square_col):
                                piece.line_of_sight.append(Square(square_row, square_col))

    def update_threat_squares(self):
        """Update threat_squares for each piece on the board.

        Unlike update_lines_of_sight(), this only tracks squares where
        pieces can actually move or capture — not extended line of sight.

        Per the updated rulebook:
          - Bishops are ignored entirely (they don't threaten squares
            for the purpose of enemy bishop teleportation).
          - The queen's threat range is only adjacent squares (king's
            distance), not her full line of sight.
          - All other pieces use their normal move/capture ranges.
        """
        for r in self.squares:
            for sq in r:
                if sq.has_piece():
                    piece = sq.piece
                    piece.threat_squares = []
                    row = sq.row
                    col = sq.col

                    if isinstance(piece, Pawn):
                        # Pawns threaten: forward, diag-forward-left, diag-forward-right
                        # Plus sideways movement squares (left, right)
                        threats = [
                            (row + piece.dir, col),      # forward
                            (row + piece.dir, col - 1),  # diag forward-left
                            (row + piece.dir, col + 1),  # diag forward-right
                            (row, col - 1),              # left
                            (row, col + 1),              # right
                        ]

                        for square_row, square_col in threats:
                            if Square.in_range(square_row, square_col):
                                piece.threat_squares.append(Square(square_row, square_col))

                    elif isinstance(piece, Knight):
                        # Knight threatens all 16 radius-2 destinations
                        # Plus: for each move with a vacant landing on the board,
                        # the jumped square is threatened (a piece landing there
                        # would become the jumped piece and could be captured)
                        knight_offsets = [
                            (-2, 0), (0, 2), (2, 0), (0, -2),      # orthogonal 2
                            (-2, 2), (2, 2), (2, -2), (-2, -2),    # diagonal 2
                            (-2, 1), (-2, -1), (2, 1), (2, -1),    # L-shape
                            (-1, 2), (1, 2), (-1, -2), (1, -2),    # L-shape
                        ]

                        for i, (dr, dc) in enumerate(knight_offsets):
                            landing_r, landing_c = row + dr, col + dc
                            if Square.in_range(landing_r, landing_c):
                                # The landing square itself is always threatened
                                piece.threat_squares.append(Square(landing_r, landing_c))

                                if self.squares[landing_r][landing_c].isempty():
                                    jumped = self.get_jumped_square(row, col, landing_r, landing_c)
                                    if jumped:
                                        jr, jc = jumped
                                        if Square.in_range(jr, jc):
                                            # 1) Jumped square is threatened: any piece
                                            #    there becomes jumpable
                                            piece.threat_squares.append(Square(jr, jc))

                                            # 2) If jumped square already has a piece,
                                            #    adjacent squares around the landing are
                                            #    also threatened via jump capture
                                            if self.squares[jr][jc].has_piece():
                                                for adr in [-1, 0, 1]:
                                                    for adc in [-1, 0, 1]:
                                                        if adr == 0 and adc == 0:
                                                            continue
                                                        ar, ac = landing_r + adr, landing_c + adc
                                                        if Square.in_range(ar, ac):
                                                            piece.threat_squares.append(Square(ar, ac))

                    elif isinstance(piece, Bishop):
                        # Bishops are IGNORED for threat calculation per rulebook
                        pass

                    elif isinstance(piece, Rook):
                        # Rook threatens: step-1 orthogonal + step-2 perpendicular
                        inits = [(-1, 0), (0, 1), (1, 0), (0, -1)]

                        for i in range(len(inits)):
                            row_init, col_init = inits[i]
                            init_row = row + row_init
                            init_col = col + col_init

                            if Square.in_range(init_row, init_col) and self.squares[init_row][init_col].isempty():
                                piece.threat_squares.append(Square(init_row, init_col))

                                # Perpendicular directions (90° turn)
                                perp = [inits[(i + 1) % 4], inits[(i + 3) % 4]]
                                for incr_r, incr_c in perp:
                                    tr, tc = init_row + incr_r, init_col + incr_c
                                    while Square.in_range(tr, tc):
                                        piece.threat_squares.append(Square(tr, tc))
                                        if not self.squares[tr][tc].isempty():
                                            break
                                        tr += incr_r
                                        tc += incr_c

                    elif isinstance(piece, Queen):
                        # Queen only threatens adjacent squares (king's distance)
                        adjs = [
                            (row-1, col), (row-1, col+1), (row, col+1), (row+1, col+1),
                            (row+1, col), (row+1, col-1), (row, col-1), (row-1, col-1),
                        ]
                        for square_row, square_col in adjs:
                            if Square.in_range(square_row, square_col):
                                piece.threat_squares.append(Square(square_row, square_col))

                    elif isinstance(piece, King):
                        adjs = [
                            (row-1, col), (row-1, col+1), (row, col+1), (row+1, col+1),
                            (row+1, col), (row+1, col-1), (row, col-1), (row-1, col-1),
                        ]
                        for square_row, square_col in adjs:
                            if Square.in_range(square_row, square_col):
                                piece.threat_squares.append(Square(square_row, square_col))

    def calc_moves_v0(self, piece, row, col, bool=True):

        '''
            Calculate all the possible (valid) moves of an specific piece on a specific position
        '''
        
        def pawn_moves():
            # steps
            steps = 1 if piece.moved else 2

            # vertical moves
            start = row + piece.dir
            end = row + (piece.dir * (1 + steps))
            for possible_move_row in range(start, end, piece.dir):
                if Square.in_range(possible_move_row):
                    if self.squares[possible_move_row][col].isempty():
                        # create initial and final move squares
                        initial = Square(row, col)
                        final = Square(possible_move_row, col)
                        # create a new move
                        move = Move(initial, final)

                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                        else:
                            # append new move
                            piece.add_move(move)
                    # blocked
                    else: break
                # not in range
                else: break

            # diagonal moves
            possible_move_row = row + piece.dir
            possible_move_cols = [col-1, col+1]
            for possible_move_col in possible_move_cols:
                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                        # create initial and final move squares
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a new move
                        move = Move(initial, final)
                        
                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                        else:
                            # append new move
                            piece.add_move(move)

            # en passant moves
            r = 3 if piece.color == 'white' else 4
            fr = 2 if piece.color == 'white' else 5
            # left en pessant
            if Square.in_range(col-1) and row == r:
                if self.squares[row][col-1].has_enemy_piece(piece.color):
                    p = self.squares[row][col-1].piece
                    if isinstance(p, Pawn):
                        if p.en_passant:
                            # create initial and final move squares
                            initial = Square(row, col)
                            final = Square(fr, col-1, p)
                            # create a new move
                            move = Move(initial, final)
                            
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)
            
            # right en pessant
            if Square.in_range(col+1) and row == r:
                if self.squares[row][col+1].has_enemy_piece(piece.color):
                    p = self.squares[row][col+1].piece
                    if isinstance(p, Pawn):
                        if p.en_passant:
                            # create initial and final move squares
                            initial = Square(row, col)
                            final = Square(fr, col+1, p)
                            # create a new move
                            move = Move(initial, final)
                            
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)


        def knight_moves():
            # 8 possible moves
            possible_moves = [
                (row-2, col+1),
                (row-1, col+2),
                (row+1, col+2),
                (row+2, col+1),
                (row+2, col-1),
                (row+1, col-2),
                (row-1, col-2),
                (row-2, col-1),
            ]

            for possible_move in possible_moves:
                possible_move_row, possible_move_col = possible_move

                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        # create squares of the new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create new move
                        move = Move(initial, final)
                        
                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                            else: break
                        else:
                            # append new move
                            piece.add_move(move)

        def straightline_moves(incrs):
            for incr in incrs:
                row_incr, col_incr = incr
                possible_move_row = row + row_incr
                possible_move_col = col + col_incr

                while True:
                    if Square.in_range(possible_move_row, possible_move_col):
                        # create squares of the possible new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a possible new move
                        move = Move(initial, final)

                        # empty = continue looping
                        if self.squares[possible_move_row][possible_move_col].isempty():
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)

                        # has enemy piece = add move + break
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                            # check potencial checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new move
                                    piece.add_move(move)
                            else:
                                # append new move
                                piece.add_move(move)
                            break

                        # has team piece = break
                        elif self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color):
                            break
                    
                    # not in range
                    else: break

                    # incrementing incrs
                    possible_move_row = possible_move_row + row_incr
                    possible_move_col = possible_move_col + col_incr

        def king_moves():
            adjs = [
                (row-1, col+0), # up
                (row-1, col+1), # up-right
                (row+0, col+1), # right
                (row+1, col+1), # down-right
                (row+1, col+0), # down
                (row+1, col-1), # down-left
                (row+0, col-1), # left
                (row-1, col-1), # up-left
            ]

            # normal moves
            for possible_move in adjs:
                possible_move_row, possible_move_col = possible_move

                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        # create squares of the new move
                        initial = Square(row, col)
                        final = Square(possible_move_row, possible_move_col) # piece=piece
                        # create new move
                        move = Move(initial, final)
                        # check potencial checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new move
                                piece.add_move(move)
                            else: break
                        else:
                            # append new move
                            piece.add_move(move)

            # castling moves
            if not piece.moved:
                # queen castling
                left_rook = self.squares[row][0].piece
                if isinstance(left_rook, Rook):
                    if not left_rook.moved:
                        for c in range(1, 4):
                            # castling is not possible because there are pieces in between ?
                            if self.squares[row][c].has_piece():
                                break

                            if c == 3:
                                # adds left rook to king
                                piece.left_rook = left_rook

                                # rook move
                                initial = Square(row, 0)
                                final = Square(row, 3)
                                moveR = Move(initial, final)

                                # king move
                                initial = Square(row, col)
                                final = Square(row, 2)
                                moveK = Move(initial, final)

                                # check potencial checks
                                if bool:
                                    if not self.in_check(piece, moveK) and not self.in_check(left_rook, moveR):
                                        # append new move to rook
                                        left_rook.add_move(moveR)
                                        # append new move to king
                                        piece.add_move(moveK)
                                else:
                                    # append new move to rook
                                    left_rook.add_move(moveR)
                                    # append new move king
                                    piece.add_move(moveK)

                # king castling
                right_rook = self.squares[row][7].piece
                if isinstance(right_rook, Rook):
                    if not right_rook.moved:
                        for c in range(5, 7):
                            # castling is not possible because there are pieces in between ?
                            if self.squares[row][c].has_piece():
                                break

                            if c == 6:
                                # adds right rook to king
                                piece.right_rook = right_rook

                                # rook move
                                initial = Square(row, 7)
                                final = Square(row, 5)
                                moveR = Move(initial, final)

                                # king move
                                initial = Square(row, col)
                                final = Square(row, 6)
                                moveK = Move(initial, final)

                                # check potencial checks
                                if bool:
                                    if not self.in_check(piece, moveK) and not self.in_check(right_rook, moveR):
                                        # append new move to rook
                                        right_rook.add_move(moveR)
                                        # append new move to king
                                        piece.add_move(moveK)
                                else:
                                    # append new move to rook
                                    right_rook.add_move(moveR)
                                    # append new move king
                                    piece.add_move(moveK)

        if isinstance(piece, Pawn): 
            pawn_moves()

        elif isinstance(piece, Knight): 
            knight_moves()

        elif isinstance(piece, Bishop): 
            straightline_moves([
                (-1, 1), # up-right
                (-1, -1), # up-left
                (1, 1), # down-right
                (1, -1), # down-left
            ])

        elif isinstance(piece, Rook): 
            straightline_moves([
                (-1, 0), # up
                (0, 1), # right
                (1, 0), # down
                (0, -1), # left
            ])

        elif isinstance(piece, Queen): 
            straightline_moves([
                (-1, 1), # up-right
                (-1, -1), # up-left
                (1, 1), # down-right
                (1, -1), # down-left
                (-1, 0), # up
                (0, 1), # right
                (1, 0), # down
                (0, -1) # left
            ])

        elif isinstance(piece, King): 
            king_moves()

    # Status:
    # King: Need to implement sword
    # Pawn (Swordsman): Fully Functional
    # Rook (Chariot): Fully Functional
    # Knight (Hippogriff): Fully Functional
    # Bishop (Assassin): Fully Functional
    # Queen: Spells done, need to implement transformation

    # def calc_moves(self, piece, row, col, bool=True):
    def boulder_moves(self, piece, row=None, col=None):
        """Generate moves for the boulder.
        First move (from intersection): only to central squares d4, e4, d5, e5.
        Later moves: like a king (1 square any direction).
        Can only capture pawns. Cannot move if cooldown > 0."""

        # Cannot move if cooling down
        if piece.cooldown > 0:
            return

        if piece.on_intersection:
            # First move from intersection: only central squares
            central = [(3, 3), (3, 4), (4, 3), (4, 4)]  # d5, e5, d4, e4
            for r, c in central:
                target = self.squares[r][c]
                # Can move to empty square or capture a pawn
                if target.isempty() or (target.has_piece() and isinstance(target.piece, Pawn)):
                    initial = Square(-1, -1)  # sentinel: boulder is on intersection, not a square
                    final = Square(r, c)
                    move = Move(initial, final)
                    piece.add_move(move)
        else:
            # Later moves: like a king
            adjs = [
                (row-1, col+0), (row-1, col+1), (row+0, col+1), (row+1, col+1),
                (row+1, col+0), (row+1, col-1), (row+0, col-1), (row-1, col-1),
            ]
            for r, c in adjs:
                if Square.in_range(r, c):
                    target = self.squares[r][c]
                    # Check memory: cannot return to last square
                    if piece.last_square and (r, c) == piece.last_square:
                        continue
                    # Can move to empty or capture pawns only
                    if target.isempty() or (target.has_piece() and isinstance(target.piece, Pawn)):
                        initial = Square(row, col)
                        final = Square(r, c)
                        move = Move(initial, final)
                        piece.add_move(move)

    def king_moves(self, piece, row, col):
        # not todo: Implement saving the queen after she is captured
        # TODO: Implement the king's sword
        adjs = [
            (row-1, col+0), # up
            (row-1, col+1), # up-right
            (row+0, col+1), # right
            (row+1, col+1), # down-right
            (row+1, col+0), # down
            (row+1, col-1), # down-left
            (row+0, col-1), # left
            (row-1, col-1), # up-left
        ]

        # normal moves
        for possible_move in adjs:
            possible_move_row, possible_move_col = possible_move

            if Square.in_range(possible_move_row, possible_move_col):
                # Boulder on intersection blocks diagonal king moves across center
                if self.boulder and self.boulder.on_intersection:
                    if self._diagonal_crosses_center(row, col, possible_move_row, possible_move_col):
                        continue

                # if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                # create squares of the new move
                initial = Square(row, col)
                final = Square(possible_move_row, possible_move_col) # piece=piece
                # create new move
                move = Move(initial, final)
                # append new move
                piece.add_move(move)

    def queen_moves(self, piece, row, col):
        # not todo: Implement jail after queen is captured, if in jail cannot move or be captured
        # TODO: Implement transformation
        adjs = [
            (row-1, col+0), # up
            (row-1, col+1), # up-right
            (row+0, col+1), # right
            (row+1, col+1), # down-right
            (row+1, col+0), # down
            (row+1, col-1), # down-left
            (row+0, col-1), # left
            (row-1, col-1), # up-left
        ]

        # normal moves
        for possible_move in adjs:
            possible_move_row, possible_move_col = possible_move

            if Square.in_range(possible_move_row, possible_move_col):
                # Boulder on intersection blocks diagonal queen moves across center
                if self.boulder and self.boulder.on_intersection:
                    if self._diagonal_crosses_center(row, col, possible_move_row, possible_move_col):
                        continue

                if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                    # create squares of the new move
                    initial = Square(row, col)
                    final = Square(possible_move_row, possible_move_col) # piece=piece
                    # create new move
                    move = Move(initial, final)
                    # append new move
                    piece.add_move(move)

    def queen_moves_enemy(self, enemy_piece, row, col):
        # Find any friendly queen (base form) that has the target in line of sight
        queen = None
        target_square = self.squares[row][col]

        for r in self.squares:
            for sq in r:
                if sq.has_enemy_piece(enemy_piece.color) and isinstance(sq.piece, Queen):
                    if target_square in sq.piece.line_of_sight:
                        queen = sq.piece
                        break
            if queen:
                break

        if not queen:
            return

        # Cannot manipulate the enemy king
        if isinstance(enemy_piece, King):
            return

        # Cannot manipulate the boulder
        if isinstance(enemy_piece, Boulder):
            return

        # Cannot manipulate any queen in base form (royal or promoted)
        if isinstance(enemy_piece, Queen) and not enemy_piece.is_transformed:
            return

        # Cannot manipulate a piece that moved on the immediately preceding turn
        if self.last_move:
            last_final = self.last_move.final
            if last_final.row == row and last_final.col == col:
                return

        args = [enemy_piece, row, col]

        if (isinstance(enemy_piece, Rook)):
            self.rook_moves(*args)
        elif (isinstance(enemy_piece, Bishop)):
            self.bishop_moves(*args)
        elif (isinstance(enemy_piece, Knight)):
            self.knight_moves(*args)
        elif (isinstance(enemy_piece, Pawn)):
            self.pawn_moves(*args)
        elif (isinstance(enemy_piece, Queen)):
            # Transformed queen — move using the form it's transformed as
            # TODO: move using transformed piece's movement rules
            self.queen_moves(*args)

    def rook_moves(self, piece, row, col):
        inits = [
            (-1, 0), # up
            (0, 1), # right
            (1, 0), # down
            (0, -1), # left
        ]

        for i in range(len(inits)):
            init = inits[i]
            row_init, col_init = init
            possible_init_row = row + row_init
            possible_init_col = col + col_init

            if Square.in_range(possible_init_row, possible_init_col):
                if self.squares[possible_init_row][possible_init_col].has_team_piece(piece.color):
                    continue

                if self.squares[possible_init_row][possible_init_col].has_enemy_piece(piece.color):
                    # create squares of the possible new move
                    initial = Square(row, col)
                    final_piece = self.squares[possible_init_row][possible_init_col].piece
                    final = Square(possible_init_row, possible_init_col, final_piece)
                    # create a possible new move
                    move = Move(initial, final)
                    # append a new move
                    piece.add_move(move)
                    continue

                # create squares of the possible new move
                initial = Square(row, col)
                final = Square(possible_init_row, possible_init_col)
                # create a possible new move
                init_move = Move(initial, final)
                # append a new move
                piece.add_move(init_move)

                incrs = [inits[(i + 1) % 4], inits[(i + 3) % 4]]
                # incrs = [x if condition else y, a if condition else b]

                for incr in incrs:
                    row_incr, col_incr = incr
                    possible_move_row = possible_init_row + row_incr
                    possible_move_col = possible_init_col + col_incr

                    while True:
                        if not(Square.in_range(possible_move_row, possible_move_col)):
                            # not in range
                            break

                        # create squares of the possible new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a possible new move
                        move = Move(initial, final)

                        # empty = continue looping
                        if self.squares[possible_move_row][possible_move_col].isempty():
                            # # check potencial checks
                            # if bool:
                            #     if not self.in_check(piece, move):
                            #         # append new move
                            #         piece.add_move(move)
                            # else:
                            #     # append new move
                            piece.add_move(move)

                        # has enemy piece = add move + break
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                            # # check potencial checks
                            # if bool:
                            #     if not self.in_check(piece, move):
                            #         # append new move
                            #         piece.add_move(move)
                            # else:
                            #     # append new move
                            piece.add_move(move)
                            break

                        # has team piece = break
                        elif self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color):
                            break

                        # incrementing incrs
                        possible_move_row = possible_move_row + row_incr
                        possible_move_col = possible_move_col + col_incr

    def bishop_moves(self, piece, row, col):
        # Remove bishop from board for the entire calculation so it doesn't
        # block enemy lines of sight or affect threat calculations
        self.squares[row][col].piece = None

        self.update_threat_squares()

        # Collect all squares threatened by enemy pieces
        # Per rulebook: enemy bishops are ignored entirely,
        # and the enemy queen only threatens adjacent squares (king's distance)
        enemy_threatened = []

        for r in self.squares:
            for sq in r:
                if sq.has_enemy_piece(piece.color):
                    enemy_piece = sq.piece
                    # Skip enemy bishops — they are ignored for this calculation
                    if isinstance(enemy_piece, Bishop):
                        continue
                    enemy_threatened[len(enemy_threatened):] = enemy_piece.threat_squares[:]

        for r in self.squares:
            for sq in r:
                if sq.isempty() and not (sq.row == row and sq.col == col):
                    if sq not in enemy_threatened:
                        # create initial and final move squares
                        initial = Square(row, col)
                        final = Square(sq.row, sq.col)
                        # create a new move
                        move = Move(initial, final)
                        piece.add_move(move)

        # Assassin capture (independent of teleportation safety)
        if self.last_move:
            last_move_initial = self.last_move.initial
            last_move_final = self.last_move.final
            last_move_piece = self.squares[last_move_final.row][last_move_final.col].piece

            if last_move_initial in piece.assassin_squares and last_move_initial != last_move_final:
                # Only assassin-capture enemy pieces (boulder is friendly to both)
                if self.squares[last_move_final.row][last_move_final.col].has_enemy_piece(piece.color):
                    # create initial and final move squares
                    initial = Square(row, col)
                    final_piece = last_move_piece
                    final = Square(last_move_final.row, last_move_final.col, final_piece)
                    # create a new move
                    move = Move(initial, final)
                    piece.add_move(move)

        # Put bishop back on the board
        self.squares[row][col].piece = piece

    def knight_moves(self, piece, row, col):
        # Radius-2 pattern: 16 destinations
        moves = [
            (row-2, col+0), # 2 up
            (row-2, col+1), # 2 up, 1 right (L-shape)
            (row-1, col+2), # 1 up, 2 right (L-shape)
            (row+0, col+2), # 2 right
            (row+1, col+2), # 1 down, 2 right (L-shape)
            (row+2, col+1), # 2 down, 1 right (L-shape)
            (row+2, col+0), # 2 down
            (row+2, col-1), # 2 down, 1 left (L-shape)
            (row+1, col-2), # 1 down, 2 left (L-shape)
            (row+0, col-2), # 2 left
            (row-1, col-2), # 1 up, 2 left (L-shape)
            (row-2, col-1), # 2 up, 1 left (L-shape)
            (row-2, col+2), # 2 up, 2 right (diagonal)
            (row+2, col+2), # 2 down, 2 right (diagonal)
            (row+2, col-2), # 2 down, 2 left (diagonal)
            (row-2, col-2), # 2 up, 2 left (diagonal)
        ]

        # normal moves
        for i in range(len(moves)):
            possible_move_row, possible_move_col = moves[i]

            if Square.in_range(possible_move_row, possible_move_col):
                if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                    # create squares of the new move
                    initial = Square(row, col)
                    final = Square(possible_move_row, possible_move_col)
                    # create new move
                    move = Move(initial, final)
                    # append new move
                    piece.add_move(move)

    def pawn_moves(self, piece, row, col):
        # steps
        steps = 1

        # vertical moves
        start = row + piece.dir
        end = row + (piece.dir * (1 + steps))
        for possible_move_row in range(start, end, piece.dir):
            if Square.in_range(possible_move_row):
                if self.squares[possible_move_row][col].isempty_or_enemy(piece.color):
                    # create initial and final move squares
                    initial = Square(row, col)

                    if self.squares[possible_move_row][col].isempty():
                        final = Square(possible_move_row, col)
                    else:
                        final_piece = self.squares[possible_move_row][col].piece
                        final = Square(possible_move_row, col, final_piece)
                    # create a new move
                    move = Move(initial, final)

                    # # check potencial checks
                    # if bool:
                    #     if not self.in_check(piece, move):
                    #         # append new move
                    #         piece.add_move(move)
                    # else:
                    #     # append new move
                    piece.add_move(move)
                # blocked
                else: break
            # not in range
            else: break

        # horizontal moves
        possible_move_cols = [col-1, col+1]
        for possible_move_col in possible_move_cols:
            if Square.in_range(row, possible_move_col):
                if self.squares[row][possible_move_col].isempty():
                    # create initial and final move squares
                    initial = Square(row, col)
                    final = Square(row, possible_move_col)
                    # create a new move
                    move = Move(initial, final)

                    # # check potencial checks
                    # if bool:
                    #     if not self.in_check(piece, move):
                    #         # append new move
                    #         piece.add_move(move)
                    # else:
                    #     # append new move
                    piece.add_move(move)

        # diagonal moves
        possible_move_row = row + piece.dir
        possible_move_cols = [col-1, col+1]
        for possible_move_col in possible_move_cols:
            if Square.in_range(possible_move_row, possible_move_col):
                # Boulder on intersection blocks diagonal captures across center
                if self.boulder and self.boulder.on_intersection:
                    if self._diagonal_crosses_center(row, col, possible_move_row, possible_move_col):
                        continue
                if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                    # create initial and final move squares
                    initial = Square(row, col)
                    final_piece = self.squares[possible_move_row][possible_move_col].piece
                    final = Square(possible_move_row, possible_move_col, final_piece)
                    # create a new move
                    move = Move(initial, final)

                    # # check potencial checks
                    # if bool:
                    #     if not self.in_check(piece, move):
                    #         # append new move
                    #         piece.add_move(move)
                    # else:
                    #     # append new move
                    piece.add_move(move)

    # possible_move_rows = [0, 1, 2, 3, 4, 5, 6, 7]
    # possible_move_cols = [0, 1, 2, 3, 4, 5, 6, 7]
    # for possible_move_row in possible_move_rows:
    #     for possible_move_col in possible_move_cols:
    #         if Square.in_range(possible_move_row, possible_move_col):
    #             if row != possible_move_row or col != possible_move_col:
    #                 if not(self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color)):
    #                     # create initial and final move squares
    #                     initial = Square(row, col)

    #                     final_piece = None

    #                     if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
    #                         final_piece = self.squares[possible_move_row][possible_move_col].piece

    #                     if final_piece:
    #                         final = Square(possible_move_row, possible_move_col, final_piece)
    #                     else:
    #                         final = Square(possible_move_row, possible_move_col)

    #                     # create a new move
    #                     move = Move(initial, final)
    #                     piece.add_move(move)

    def _create(self):
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[row][col] = Square(row, col)

    def _add_pieces(self, color):
        row_pawn, row_other = (6, 7) if color == 'white' else (1, 0)

        # pawns
        for col in range(COLS):
            self.squares[row_pawn][col] = Square(row_pawn, col, Pawn(color))

        # knights
        self.squares[row_other][3] = Square(row_other, 3, Knight(color))
        self.squares[row_other][4] = Square(row_other, 4, Knight(color))

        # bishops
        self.squares[row_other][0] = Square(row_other, 0, Bishop(color))
        self.squares[row_other][7] = Square(row_other, 7, Bishop(color))

        # rooks
        self.squares[row_other][2] = Square(row_other, 2, Rook(color))
        self.squares[row_other][5] = Square(row_other, 5, Rook(color))

        # white queen/black king
        self.squares[row_other][1] = Square(row_other, 1, Queen(color)) if color == 'white' else Square(row_other, 1, King(color))

        # white king/black queen
        self.squares[row_other][6] = Square(row_other, 6, King(color)) if color == 'white' else Square(row_other, 6, Queen(color))

    def _add_boulder(self):
        """Create the boulder on the central intersection (not on any square)."""
        boulder = Boulder()
        boulder.on_intersection = True
        self.boulder = boulder