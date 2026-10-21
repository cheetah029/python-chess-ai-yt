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
import sys


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
        #: Background search state -- see `start_thinking`.
        self._thinking = None
        self._result = None
        #: Bumped on abort so a stale thread's answer is discarded.
        self._generation = 0

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

    # ---- thinking off the main thread ------------------------------------
    #
    # WHY THIS EXISTS. `take_turn` chooses and applies in one call, and
    # choosing is where the seconds go -- up to the search's whole
    # budget. The UI loop called it directly, so for that entire time no
    # event was read: flipping the board, changing the theme, pausing,
    # undo and redo all appeared to do NOTHING until the computer had
    # finished its move. A reviewer reported exactly that, and it is
    # worst in computer-vs-computer where the user is only ever
    # watching.
    #
    # The search runs on a COPY. It is read-only on the live board in
    # principle, but a Turn holds a reference to the piece that produced
    # it and `Board.move` writes `moved`, `cooldown` and `last_square`
    # through that reference -- so handing the live board to another
    # thread would be a data race with the renderer. The thread gets its
    # own deep copy and returns a DESCRIPTION, which the main thread
    # resolves against freshly enumerated turns. That is the same
    # discipline `mcts.py` adopted after a simulated boulder move took
    # the real cooldown 0 -> 2.

    def is_thinking(self):
        return self._thinking is not None and self._thinking.is_alive()

    def start_thinking(self, game):
        """Begin choosing a turn in the background. True if started."""
        import threading

        if self._thinking is not None:
            return False
        if not self.is_ai_turn(game):
            return False
        turns = self.legal_turns(game)
        if not turns:
            return False
        from lgref.experiments.fastcopy import clone_with_turns

        try:
            engine, cloned = clone_with_turns(self._engine, turns)
        except Exception:
            # A game whose engine cannot be copied falls back to the
            # blocking path rather than losing the move.
            self._result = self._describe(
                self.player.choose_turn(turns, self._engine))
            return True
        self._result = None
        self._generation += 1
        generation = self._generation

        def work():
            try:
                chosen = self.player.choose_turn(cloned, engine)
                described = self._describe(chosen)
            except Exception:
                described = None
            if generation == self._generation:
                self._result = described

        # GIVE THE UI THREAD THE GIL MORE OFTEN. A CPU-bound Python
        # thread holds the interpreter lock for `sys.getswitchinterval`
        # at a time, five milliseconds by default, and the drawing loop
        # waits behind it -- measured at a 54 ms worst-case gap between
        # frames and 298 frames in two and a half seconds, which is what
        # dragging a piece felt like while the computer was thinking.
        #
        # At one millisecond: a 13.8 ms worst gap and 903 frames over
        # the same window, three times as responsive. Shorter than that
        # buys more frames but a WORSE tail (17.2 ms at 0.2 ms),
        # because the switching itself starts to cost.
        #
        # Restored when the move lands, so nothing outside a search runs
        # with a changed interpreter setting.
        self._previous_switch = sys.getswitchinterval()
        sys.setswitchinterval(self.THINKING_SWITCH_INTERVAL)
        self._thinking = threading.Thread(target=work)
        self._thinking.daemon = True
        self._thinking.start()
        return True

    def _restore_switch_interval(self):
        previous = getattr(self, '_previous_switch', None)
        if previous is not None:
            sys.setswitchinterval(previous)
            self._previous_switch = None

    def poll(self):
        """The chosen turn's description once ready, else None."""
        if self._result is not None and not self.is_thinking():
            return self._result
        if self._thinking is not None and not self._thinking.is_alive():
            return self._result
        return None

    #: How long a thread may hold the interpreter lock while a search
    #: is running. See `start_thinking`.
    THINKING_SWITCH_INTERVAL = 0.001

    def abort(self):
        """Forget the move in flight.

        The thread itself is not killed -- Python cannot -- but its
        result is tagged with a generation and a stale one is dropped,
        so a move chosen for a position the user has since undone can
        never be played.
        """
        self._generation += 1
        self._thinking = None
        self._result = None
        self._restore_switch_interval()

    def finish_turn(self, game, description):
        """Apply a description chosen earlier, resolved against NOW.

        Resolved rather than stored: the turn objects the thread saw
        belong to its own copy of the board, and applying one of those
        would move a piece that is not on the screen.
        """
        self._thinking = None
        self._result = None
        self._restore_switch_interval()
        if description is None or not self.is_ai_turn(game):
            return False
        turns = self.legal_turns(game)
        from lgref.experiments.mcts import describe

        for turn in turns:
            if describe(turn) == description:
                self._apply_turn(game, turn)
                return True
        return False

    @staticmethod
    def _describe(turn):
        if turn is None:
            return None
        from lgref.experiments.mcts import describe

        return describe(turn)

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
        # First-class flags: an action turn expires all last-move flags.
        board.record_action_turn()
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
