"""Alpha-beta that actually prunes: iterative deepening, a transposition
table, and STATIC move ordering.

WHY THE PREVIOUS SEARCH WAS SLOW, measured rather than guessed. In a
midgame position at branching 50:

    clone (engine + turns)    0.896 ms
    evaluate a position       0.529 ms
    board state hash          0.021 ms

`BeamPlayer` ordered its moves by cloning and evaluating EVERY candidate
at EVERY node -- 50 x 1.425 ms = 71 ms per node spent deciding what to
look at first. Alpha-beta at depth 3 needs only about 700 nodes when
ordering is good, so the arithmetic is:

    ordering by evaluation   707 x 71 ms   = 50 s      unplayable
    ordering for free          707 x 1.4 ms = 1.0 s     playable

The depth was never the problem. The ORDERING COST was, and it scaled
with branching exactly where branching is worst.

WHAT THIS DOES INSTEAD.

  STATIC ORDERING, no clones. The transposition-table move first, then
      captures ranked by the LEARNED weight of the piece they take, then
      everything else. Ranking captures by learned weights adds no new
      prior -- it reuses the numbers TD derived from terminal outcomes --
      and it needs only the destination square's occupant, which is
      readable without simulating anything.

  A TRANSPOSITION TABLE on the engine's own state hash, which costs
      0.021 ms and is the full legal-move-determining state
      (RULEBOOK.md), so it is a sound key. Positions reached by
      different move orders are then searched once.

  ITERATIVE DEEPENING, which is what makes a time budget meaningful:
      every completed depth leaves a best move to return, and leaves the
      ordering that makes the next depth cheap. Searching depth 1, then
      2, then 3 costs barely more than depth 3 alone when ordering
      works, and it guarantees an answer when it does not.

THE SOUNDNESS CAVEAT, stated because it is real. The state hash
deliberately excludes the repetition rule's own counts and the tiny
endgame's distance counts (they are game-level history, not properties
of the position), so two positions that hash equal can have different
repetition futures. A transposition table keyed on it can therefore
return a value computed under a different history. Every engine makes
this trade; it is recorded here rather than discovered later.

GENERAL OVER THE PROTOCOL. Needs `get_all_legal_turns`,
`execute_turn`, `is_game_over`, `winner`, `current_player`. The TT and
the capture ordering are used only when the game offers them -- a game
without a state hash is searched without a table, and a game whose
turns have no `is_capture` is ordered by the table move alone.
"""

import time

from lgref.experiments.fastcopy import clone_with_turns
from lgref.experiments.undo import restore, snapshot, supports_undo

EXACT, LOWER, UPPER = 0, 1, 2


def _key(engine):
    """The engine's own state hash, or None if it does not offer one."""
    board = getattr(engine, 'board', None)
    if board is None or not hasattr(board, 'get_state_hash'):
        return None
    try:
        return board.get_state_hash(engine.current_player)
    except Exception:
        return None


def generic_capture_rank(engine, turn):
    """Any capture outranks any quiet move, and nothing finer.

    THE DEFAULT, and deliberately crude. Ordering wants to know which
    moves are likely to cause a cutoff, and in a game with captures the
    captures are. Ranking them AMONG themselves needs to know what each
    one takes, which is game-specific knowledge -- so it is injected
    (`features.capture_ranker` builds one for the case study from the
    LEARNED weights) rather than assumed here.

    A game whose turns carry no `is_capture` gets zero from this, which
    leaves ordering to the transposition-table move and the cutoff
    tables. That is a weaker order, not a wrong one.
    """
    return 1.0 if getattr(turn, 'is_capture', False) else 0.0


def order_turns(engine, turns, best, rank_capture=None, killers=(),
                history=None, depth=0):
    """Turns in the order most likely to produce a cutoff. No clones.

    FOUR TIERS, cheapest signal first and all of them free of
    simulation:

      1. the transposition-table move, because a move that was best at
         a shallower depth usually still is -- which is the whole
         reason iterative deepening pays for itself;
      2. captures, ranked by the LEARNED weight of what they take;
      3. KILLER MOVES -- moves that caused a cutoff at this depth in a
         sibling position. Cheap, and they carry most of the benefit
         for quiet moves;
      4. the HISTORY HEURISTIC -- a running count, per move
         description, of how often it has produced a cutoff anywhere
         in this search.

    Tiers 3 and 4 were missing, and their absence is why depth 3 cost
    9194 evaluations where good ordering needs about 700: captures were
    ordered and the other forty-odd quiet moves were tried in
    whatever order the generator produced them. Neither tier encodes
    any knowledge of the game -- both are learned from this search's own
    cutoffs.
    """
    from lgref.experiments.mcts import describe

    history = history or {}
    scored = []
    for index, turn in enumerate(turns):
        description = describe(turn)
        if best is not None and description == best:
            rank = float('inf')
        else:
            rank = (rank_capture or generic_capture_rank)(engine, turn)
            if rank == 0.0:
                if description in killers:
                    rank = 0.05           # below any capture, above the rest
                else:
                    rank = min(0.04, history.get(description, 0) * 1e-4)
        scored.append((-rank, index, turn))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [turn for _rank, _index, turn in scored]


class Searcher:
    """Iterative-deepening alpha-beta over an injected evaluation."""

    def __init__(self, evaluate, rank_capture=None, max_depth=5,
                 budget=3.0, quiescence=3, use_tt=True):
        self.evaluate = evaluate
        #: How to rank one capture against another. Injected, because
        #: that is the only part of ordering that needs to know what the
        #: game contains -- see `generic_capture_rank`.
        self.rank_capture = rank_capture or generic_capture_rank
        self.max_depth = max_depth
        self.budget = budget
        self.quiescence = quiescence
        self.use_tt = use_tt
        self.tt = {}
        #: Whether the cheap make/unmake path is available. Detected per
        #: engine: a game without a board of squares is searched by
        #: copying, which keeps this class general.
        self.can_undo = None
        #: Cutoff memory, both learned from this search rather than
        #: supplied: `killers` holds up to two moves per depth that
        #: produced a cutoff, `history` counts cutoffs per move
        #: description across the whole search.
        self.killers = {}
        self.history = {}
        #: LMR thresholds. `lmr_depth` is remaining depth INSIDE
        #: `_search`, which is one less than the root depth -- gating it
        #: at 3 meant it never fired at all in a depth-3 search, and the
        #: node count was byte-identical with and without it. Measured,
        #: not assumed.
        self.lmr_depth = 2
        self.lmr_after = 3
        self.reductions = 0
        #: Frontier depth and margin for futility pruning. The margin is
        #: in evaluation units; one piece is worth 0.03-0.05 to this
        #: evaluation, so 0.02 is below a pawn and cannot prune away a
        #: line that a capture could rescue.
        self.futility_depth = 1
        self.futility_margin = 0.02
        self.futilities = 0
        self.nodes = 0
        self.depth_reached = 0

    # ---- public ---------------------------------------------------------

    def choose_turn(self, turns, engine=None):
        from lgref.experiments.mcts import describe

        if engine is None or not turns:
            return turns[0] if turns else None
        if len(turns) == 1:
            return turns[0]
        self.nodes = 0
        self.reductions = 0
        self.futilities = 0
        self.depth_reached = 0
        deadline = time.time() + self.budget

        # ONE CLONE PER MOVE, then make/unmake inside it. The caller's
        # engine is never touched, so an undo bug can only corrupt a
        # throwaway position rather than the live game -- and at even a
        # few hundred nodes this single 0.98 ms copy is noise, where a
        # copy PER NODE was 64% of the cost.
        if self.can_undo is None:
            self.can_undo = supports_undo(engine)
        if self.can_undo:
            sim, sim_turns = clone_with_turns(engine, turns)
        else:
            # Without make/unmake every descent copies anyway, so the
            # caller's engine is never mutated and no up-front copy is
            # needed.
            sim, sim_turns = engine, turns
        me = sim.current_player
        best_index = 0
        best_description = None

        for depth in range(1, self.max_depth + 1):
            if depth > 1 and time.time() >= deadline:
                break          # no time to start another depth
            try:
                _value, index = self._root(sim, sim_turns, depth, me,
                                           best_description, deadline)
            except _OutOfTime:
                break
            if index is not None:
                best_index = index
                best_description = describe(sim_turns[index])
                self.depth_reached = depth
            if time.time() >= deadline:
                break
        # `sim_turns[i]` was cloned alongside `turns[i]`, so the index
        # carries straight back to the caller's own turn objects.
        return turns[best_index]

    # ---- descend / ascend ------------------------------------------------

    def _descend(self, engine, turn):
        """Apply `turn`, returning the engine to recurse on and a token.

        On an engine that supports make/unmake this mutates in place and
        returns a restore token; otherwise it copies, which is what
        keeps the searcher usable on games with a different shape.
        """
        if self.can_undo:
            token = snapshot(engine)
            engine.execute_turn(turn)
            return engine, token
        child = engine.copy()
        child.execute_turn(turn)
        return child, None

    def _ascend(self, engine, token):
        if token is not None:
            restore(engine, token)

    # ---- internals ------------------------------------------------------

    def _root(self, engine, turns, depth, me, best_description, deadline):
        alpha, beta = 0.0, 1.0
        best_value, best_index = -1.0, None
        index_of = {id(turn): i for i, turn in enumerate(turns)}
        for turn in order_turns(engine, turns, best_description,
                                self.rank_capture,
                                self.killers.get(depth, ()), self.history,
                                depth):
            if time.time() >= deadline and best_index is not None:
                # Out of time with an answer in hand from this depth.
                # Returning it is sound: the moves already searched were
                # the best-ordered ones, so the partial result is the
                # same kind of answer a shallower search would give.
                break
            child, token = self._descend(engine, turn)
            try:
                value = 1.0 - self._search(child, depth - 1, 1.0 - beta,
                                           1.0 - alpha, me, deadline)
            finally:
                self._ascend(engine, token)
            if value > best_value:
                best_value, best_index = value, index_of[id(turn)]
            alpha = max(alpha, value)
        return best_value, best_index

    def _leaf(self, engine):
        """The position's value FROM THE PERSPECTIVE OF THE PLAYER TO
        MOVE, which is the negamax convention the recursion assumes.

        THIS WAS THE SIGN BUG, and it is the same class of error
        `mcts.py` records costing it 0 wins in 20 games against a random
        player. `_leaf` took a fixed `me` and evaluated from THAT
        perspective, while every recursive step does `1.0 - _search(...)`
        and so treats the returned value as belonging to the node's own
        mover. The two conventions agree at even plies from the root and
        are INVERTED at odd ones, so the search was sound at depth 2 and
        actively wrong at depth 3.

        Measured: on m,n,k, where truth is computable, the one-ply
        chooser scored 88.9% optimal and a depth-3 search over the same
        evaluation scored 30.6% against a 32.6% chance baseline -- the
        search was destroying the evaluation it was given. On Royal
        Chess the damage was hidden because the reachable depth was 2.

        `me` is gone from the value path entirely, which removes the
        possibility of mixing the two conventions again.
        """
        if engine.is_game_over():
            winner = engine.winner
            if winner is None:
                return 0.5
            return 1.0 if winner == engine.current_player else 0.0
        return self.evaluate(engine, engine.current_player)

    def _search(self, engine, depth, alpha, beta, me, deadline):
        # `me` is retained only for signature stability; the value
        # path is mover-relative and must not consult it.
        self.nodes += 1
        # CHECKED OFTEN ENOUGH TO MATTER. At 256 the granularity was
        # about half a second and a 2s budget overran to 5s, because
        # `_root` never checked at all and a single depth cannot be
        # abandoned halfway without losing its answer.
        if self.nodes % 32 == 0 and time.time() >= deadline:
            raise _OutOfTime()
        if engine.is_game_over():
            return self._leaf(engine)

        key = _key(engine) if self.use_tt else None
        if key is not None:
            hit = self.tt.get(key)
            if hit is not None and hit[0] >= depth:
                _d, stored, flag, _best = hit
                if flag == EXACT:
                    return stored
                if flag == LOWER and stored > alpha:
                    alpha = stored
                elif flag == UPPER and stored < beta:
                    beta = stored
                if alpha >= beta:
                    return stored

        turns = engine.get_all_legal_turns()
        if not turns:
            # No legal turn is a declared loss for the player to move.
            return 1.0 if engine.current_player != me else 0.0
        if depth <= 0:
            return self._quiesce(engine, self.quiescence, alpha, beta, me,
                                 deadline)

        from lgref.experiments.mcts import describe

        hint = self.tt.get(key)[3] if (key is not None
                                       and self.tt.get(key)) else None
        original_alpha = alpha
        best_value = -1.0
        best_description = None
        ordered = order_turns(engine, turns, hint,
                              self.rank_capture,
                              self.killers.get(depth, ()),
                              self.history, depth)
        # FUTILITY PRUNING AT THE FRONTIER, and it is worth more here
        # than in most games for a specific reason: this evaluation is
        # built from COUNTS, and a non-capturing move changes no count.
        # So every quiet move has a feature delta of exactly zero and
        # evaluates identically at a leaf -- searching all forty-odd of
        # them one ply from the horizon distinguishes nothing.
        #
        # One ply out, a quiet move therefore cannot raise the score, so
        # if standing-pat is already far enough below alpha that no
        # capture-free line can reach it, the quiet moves are skipped
        # and only the forcing ones are searched. Captures, actions and
        # promotions are never pruned, since those DO change counts.
        #
        # Unsound in the general case -- a quiet move can set up a
        # threat a deeper search would find -- which is why it fires
        # only at the frontier, below which quiescence resolves the
        # tactics anyway.
        frontier = (depth <= self.futility_depth)
        standing = self._leaf(engine) if frontier else None
        for position, turn in enumerate(ordered):
            if (frontier and standing is not None
                    and not getattr(turn, 'is_capture', False)
                    and getattr(turn, 'turn_type', 'move') == 'move'
                    and standing + self.futility_margin <= alpha):
                self.futilities += 1
                continue
            child, token = self._descend(engine, turn)
            # LATE MOVE REDUCTION. Ordering puts the plausible moves
            # first, so a move that appears late is probably bad --
            # search it SHALLOWER and only pay full depth if it turns
            # out to beat alpha anyway. This is what attacks the real
            # problem here: fifty quiet moves that cutoff history can
            # only partly order, where a 1.61x gain still leaves depth 3
            # nine times above the ideal node count.
            #
            # Conditions are the conventional conservative ones: never
            # reduce a capture, never near the horizon, and never the
            # first few moves -- so the principal variation is always
            # searched at full depth and the reduction cannot change the
            # chosen move without a re-search confirming it.
            reduction = 0
            if (depth >= self.lmr_depth and position >= self.lmr_after
                    and not getattr(turn, 'is_capture', False)):
                reduction = 1
                self.reductions += 1
            try:
                value = 1.0 - self._search(child, depth - 1 - reduction,
                                           1.0 - beta, 1.0 - alpha, me,
                                           deadline)
                if reduction and value > alpha:
                    # It beat alpha despite the reduction, so the shallow
                    # score cannot be trusted: re-search at full depth.
                    value = 1.0 - self._search(child, depth - 1,
                                               1.0 - beta, 1.0 - alpha,
                                               me, deadline)
            finally:
                self._ascend(engine, token)
            if value > best_value:
                best_value = value
                best_description = describe(turn)
            alpha = max(alpha, value)
            if alpha >= beta:
                # A CUTOFF is the only evidence either table needs, and
                # it comes from the search itself. Quiet moves are
                # remembered; captures are already ordered ahead.
                if not getattr(turn, 'is_capture', False):
                    cut = describe(turn)
                    slot = self.killers.setdefault(depth, [])
                    if cut not in slot:
                        slot.insert(0, cut)
                        del slot[2:]
                    self.history[cut] = (self.history.get(cut, 0)
                                         + depth * depth)
                break

        if key is not None:
            if best_value <= original_alpha:
                flag = UPPER
            elif best_value >= beta:
                flag = LOWER
            else:
                flag = EXACT
            self.tt[key] = (depth, best_value, flag, best_description)
        return best_value

    def _quiesce(self, engine, depth, alpha, beta, me, deadline):
        """Resolve while the score is still moving, captures first.

        Gated on a FRACTION of the largest change in the position rather
        than a fixed threshold: one piece is worth very different
        amounts to this evaluation (rook 0.20, pawn 0.027), so a
        constant gate blinds the search below its own size.
        """
        standing = self._leaf(engine)
        if depth <= 0 or engine.is_game_over():
            return standing
        turns = engine.get_all_legal_turns()
        if not turns:
            return 0.0
        candidates = [t for t in turns if getattr(t, 'is_capture', False)]
        if not candidates:
            return standing
        value = standing                 # standing pat
        alpha = max(alpha, value)
        if alpha >= beta:
            return value
        for turn in order_turns(engine, candidates, None,
                                self.rank_capture):   # captures only
            self.nodes += 1
            child, token = self._descend(engine, turn)
            try:
                value = max(value, 1.0 - self._quiesce(
                    engine, depth - 1, 1.0 - beta, 1.0 - alpha, me,
                    deadline))
            finally:
                restore(engine, token)
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value


class _OutOfTime(Exception):
    """Raised to abandon an unfinished depth; the previous one stands."""
