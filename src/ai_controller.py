"""
AIController — drives one side of a `Game` with an AI player, for the
human-vs-AI game mode.

Design (Option A): the controller reuses `GameEngine` ONLY to *enumerate* the
legal turns for the side to move, then *applies* the chosen turn through the
exact same board-mutation path the human UI uses in `main.py`
(`board.move` / `transform_queen` / `promote` / `execute_jump_capture` /
`set_invulnerable_after_jump_decline`), and advances the turn with
`Game.next_turn()`.

`Game.next_turn()` therefore remains the single turn-lifecycle authority
(undo history, repetition recording, freeze/invulnerability expiry, and the
no-legal-moves loss check). The engine is NEVER used to advance the turn
(that would double-advance against `Game.next_turn()`).

The post-move bookkeeping below mirrors the human path in `main.py`
(set_true_en_passant, clear_forbidden_squares, manipulation freeze,
update_assassin_squares, decrement_boulder_cooldown, winner check, and the
tiny-endgame distance-count update) so an AI turn is indistinguishable from a
human turn as far as game state is concerned.
"""

from engine import GameEngine
from players import RandomPlayer


class AIController:
    """Plays one color of a Game with an AI player.

    Usage (in the UI loop):
        ai = AIController('black')          # AI plays black
        ...
        if ai.is_ai_turn(game):
            ai.take_turn(game)
    """

    def __init__(self, color, player=None, manipulation_mode='freeze'):
        if color not in ('white', 'black'):
            raise ValueError(f"color must be 'white' or 'black', got {color!r}")
        self.color = color
        self.player = player if player is not None else RandomPlayer()
        # A GameEngine used *solely* as a turn-enumerator. It is re-bound to the
        # live Game board on every call (see legal_turns). It is never asked to
        # execute/advance a turn.
        self._engine = GameEngine(manipulation_mode=manipulation_mode)

    # ---- queries ---------------------------------------------------------

    def is_ai_turn(self, game):
        """True if the game is not over and it's this AI's color to move."""
        return game.winner is None and game.next_player == self.color

    def legal_turns(self, game):
        """Enumerate all legal Turn objects for the side to move, by pointing
        the enumeration engine at the live Game board.

        Note: GameEngine.get_all_legal_turns() performs idempotent per-turn
        setup (clearing the *opponent's* moved_by_queen freeze, recomputing
        assassin squares). In 'freeze' mode this never clears the current
        mover's own frozen pieces, so freeze lifecycles set up via
        Game.next_turn() are preserved.
        """
        eng = self._engine
        eng.board = game.board
        eng.current_player = game.next_player
        eng.turn_number = game.board.turn_number
        return eng.get_all_legal_turns()

    # ---- driving a turn --------------------------------------------------

    def take_turn(self, game):
        """If it's this AI's turn, choose and fully apply one legal turn.

        Returns True if a turn was taken, False otherwise (not the AI's turn,
        game already over, or no legal turn available — the latter having
        already been flagged as a loss by Game.next_turn()).
        """
        if not self.is_ai_turn(game):
            return False
        turns = self.legal_turns(game)
        if not turns:
            return False
        # Pass the engine through to choose_turn so neural-network players
        # can simulate the resulting positions for evaluation. RandomPlayer
        # ignores the engine argument (kept for API parity).
        turn = self.player.choose_turn(turns, self._engine)
        if turn is None:
            return False
        self._apply_turn(game, turn)
        return True

    # ---- apply (mirrors the human UI path in main.py) --------------------

    def _apply_turn(self, game, turn):
        if turn.turn_type == 'transformation':
            self._apply_transformation(game, turn)
        else:  # 'move', 'boulder', 'manipulation' — all spatial via board.move
            self._apply_spatial(game, turn)

    def _apply_transformation(self, game, turn):
        board = game.board
        mover = game.next_player
        row, col = turn.from_sq
        # record_highlight: this is a REAL executed transformation (the
        # AI's committed turn, mirroring the human confirmation click),
        # so the highlight moves to the queen's square.
        board.transform_queen(board.squares[row][col].piece, row, col,
                              turn.transform_target,
                              record_highlight=True)
        board.update_assassin_squares(mover)
        board.decrement_boulder_cooldown()
        if board.tiny_endgame_active:
            board.update_distance_count(captured=False)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        game.next_turn()

    def _apply_spatial(self, game, turn):
        """Apply a fully-specified spatial Turn (move / boulder / manipulation).

        The Turn already carries its sub-choices (jump_choice, promo_choice)
        — engine.get_all_legal_turns enumerated each combination as a
        separate Turn — so this method just unconditionally applies them.
        """
        board = game.board
        mover = game.next_player
        to_r, to_c = turn.to_sq
        # Detect a normal capture BEFORE the move executes (mirrors main.py).
        captured = board.squares[to_r][to_c].has_piece()

        jump_targets = board.move(turn.piece, turn.move_obj)

        # Jump-capture branch: turn.has_jump_offer is True iff the move
        # offered a jump-capture decision. turn.jump_choice is the chosen
        # target (capture) or None (decline). When has_jump_offer is
        # False, no jump-capture was offered and we fall through.
        if turn.has_jump_offer:
            if turn.jump_choice is not None:
                jr, jc = turn.jump_choice
                board.execute_jump_capture(jr, jc)
                jump_captured = True
            else:
                # Declined — jumped piece survives. v2 knight may gain
                # invulnerability for one opponent turn (board helper
                # checks the adjacent-enemy condition).
                landing_r, landing_c = turn.to_sq
                # jump_targets always has exactly one entry in v2 (the
                # jumped piece) — its coords are the jumped square.
                jumped_r, jumped_c = jump_targets[0]
                board.set_invulnerable_after_jump_decline(
                    turn.piece, landing_r, landing_c, jumped_r, jumped_c)
                jump_captured = False
            board.clear_forbidden_squares()
            if turn.piece.color != mover:
                turn.piece.moved_by_queen = True
            board.update_assassin_squares(mover)
            board.decrement_boulder_cooldown()
            if jump_captured:
                game.winner = board.check_winner()
            if board.tiny_endgame_active:
                board.update_distance_count(captured=jump_captured)
            if not board.tiny_endgame_active and board.is_tiny_endgame():
                board.init_tiny_endgame()
            game.play_sound(captured=jump_captured)
            game.next_turn()
            return

        # Promotion branch: turn.promo_choice carries the chosen form.
        if turn.promo_choice is not None:
            was_manipulation = turn.piece.color != mover
            board.promote(turn.piece, to_r, to_c, turn.promo_choice)
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
            game.play_sound(captured=captured)
            game.next_turn()
            return

        # Normal move completion.
        board.set_true_en_passant(turn.piece)
        board.clear_forbidden_squares()
        # Manipulation freeze: if the moved piece is an enemy of the mover, the
        # mover manipulated it -> hold it in place for its owner's next turn.
        # (Boulder is neutral, so has_enemy_piece is False -> never frozen.)
        if board.squares[to_r][to_c].has_enemy_piece(mover):
            board.squares[to_r][to_c].piece.moved_by_queen = True
        board.update_assassin_squares(mover)
        board.decrement_boulder_cooldown(moved_piece=turn.piece)
        if captured:
            game.winner = board.check_winner()
        if board.tiny_endgame_active:
            board.update_distance_count(captured=captured)
        if not board.tiny_endgame_active and board.is_tiny_endgame():
            board.init_tiny_endgame()
        # Audio feedback for the human watching the AI's turn — mirrors the
        # human-move path in main.py. Sound is a no-op in headless tests.
        game.play_sound(captured=captured)
        game.next_turn()
