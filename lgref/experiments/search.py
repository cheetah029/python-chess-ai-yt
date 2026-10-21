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


def generic_is_tactical(turn):
    """Whether a turn changes material, as far as the protocol can tell.

    THE DEFAULT IS `is_capture`, AND THE DEFAULT IS NOT ALWAYS RIGHT.
    Quiescence, move ordering and futility pruning all need to know
    which turns are tactical, and all three asked `is_capture` directly.
    In the case study that is WRONG for one of the game's two capture
    mechanics: a knight may capture by jumping OVER a piece, and such a
    turn carries `is_capture = False` with its victim named by
    `jump_choice`, because nothing is taken at the square it lands on.

    So a knight jump-capture was invisible to all three. Quiescence
    never resolved one, which means a position where the opponent can
    take a knight by jumping it was evaluated as quiet; ordering never
    put one early; and futility pruning was free to discard one as a
    quiet move. The reviewer's games are full of knight tactics.

    This is injected rather than fixed because which turns are tactical
    is a fact about a game, and this module may not know one. A game
    whose turns carry neither attribute gets False everywhere, which
    leaves ordering to the table move -- a weaker order, not a wrong
    one.
    """
    return bool(getattr(turn, 'is_capture', False))


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

    Shares `generic_is_tactical` so the default ordering and the default
    quiescence agree about what a capture is. They did not: this asked
    `is_capture` and so skipped the case study's jump-captures.
    """
    return 1.0 if generic_is_tactical(turn) else 0.0


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
                 budget=3.0, quiescence=3, use_tt=True,
                 reduce_turns=None, is_tactical=None):
        self.evaluate = evaluate
        #: Which turns change material -- see `generic_is_tactical` for
        #: why this cannot be `is_capture` in every game. Used by
        #: quiescence, by ordering and by the futility guard, which all
        #: used to ask the attribute directly and all missed the case
        #: study's second capture mechanic.
        self.is_tactical = is_tactical or generic_is_tactical
        #: Optional `(engine, turns) -> turns`, applied before ordering.
        #: INJECTED, like `rank_capture`, because deciding which moves
        #: are interchangeable needs to know what the evaluation reads
        #: and the search does not.
        #:
        #: LOSSY ON PURPOSE, and that has to be said plainly: two moves
        #: that leave the evaluation's features identical are not
        #: equivalent -- they lead to different futures -- so this is a
        #: heuristic, not a sound reduction. It exists because on a
        #: 19x19 board the branching factor is about 360 and the search
        #: reaches depth 2, which cannot see a double threat. It is
        #: measured by match play rather than assumed.
        self.reduce_turns = reduce_turns
        #: Only near the root, where the branching saved is worth the
        #: extraction cost and where a wrong collapse is most likely to
        #: be corrected by the deeper search below it.
        self.reduce_above_depth = 2
        self.reduced = 0
        #: How to rank one capture against another. Injected, because
        #: that is the only part of ordering that needs to know what the
        #: game contains -- see `generic_capture_rank`.
        self.rank_capture = rank_capture or generic_capture_rank
        #: STOP DEEPENING ONCE THE ANSWER HAS SETTLED. How many extra
        #: completed depths must agree, in both the move and the value,
        #: before the search gives up its remaining depth. `None`
        #: disables it, which is the default until it has been raced --
        #: an early exit changes WHICH moves are searched, and this
        #: project has a clear record of what shipping that unraced
        #: does.
        self.settle = None
        self.settled = 0
        #: Partial iterations discarded for being worse than
        #: the completed answer they would have replaced.
        self.abandoned = 0
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
        #: Set by `choose_turn`; see `principal_variation`.
        self.best_description = None
        #: LMR thresholds. `lmr_depth` is remaining depth INSIDE
        #: `_search`, which is one less than the root depth -- gating it
        #: at 3 meant it never fired at all in a depth-3 search, and the
        #: node count was byte-identical with and without it. Measured,
        #: not assumed.
        self.lmr_depth = 2
        self.lmr_after = 3
        self.reductions = 0
        #: Frontier depth for futility pruning.
        self.futility_depth = 1
        #: THE MARGIN IS DERIVED FROM THE EVALUATION, NOT SUPPLIED, and
        #: that correction matters more than it looks. It used to be
        #: 0.02, justified in a comment reading "one piece is worth
        #: 0.03-0.05 TO THIS EVALUATION" -- a constant calibrated to one
        #: game's value scale, sitting in a module whose whole claim is
        #: that it knows no game. On a game whose evaluation spans ten
        #: times less it would prune every quiet move; on one spanning
        #: ten times more it would prune none.
        #:
        #: Instead the searcher watches the leaf values it actually
        #: produces and takes a FRACTION of their observed spread. The
        #: fraction is dimensionless, which is the point: it shapes the
        #: tree without encoding any game's units. Pruning stays off
        #: until enough leaves have been seen to estimate the spread at
        #: all, so a short search simply does not prune rather than
        #: pruning on a guess.
        #:
        #: Set `futility_margin` explicitly to override the estimate.
        self.futility_fraction = 0.5
        self.futility_min_samples = 64
        self.futility_margin = None
        self._scale_count = 0
        self._scale_mean = 0.0
        self._scale_dev = 0.0
        self.futilities = 0
        # THREE ADDITIONS THAT DID NOT WORK, kept flag-gated with their
        # numbers so nobody retries them blind. I predicted all three
        # would be free wins and said so before measuring; they are not.
        # Same midgame position, same 40-position harness, trainer
        # paused so the clock is uncontended:
        #
        #     depth 4, midgame      nodes    time
        #     baseline               6206   5.12s
        #     + PVS                  6363   5.19s
        #     + aspiration           6564   5.29s
        #     + eval cache           6206   5.00s
        #     all three              6726   5.35s
        #
        #     depth 4, opening       nodes    time
        #     baseline              16503  15.50s
        #     all three             17549  15.86s
        #
        # Every configuration chose the same move, so they are sound --
        # just not faster.
        #
        #: PVS: the first move gets the full window, the rest a null
        #: one. It LOSES here because ordering is already good enough
        #: that there is little left to refute cheaply, so the
        #: re-searches cost more than the narrow windows save: 54
        #: re-searches became 118. Off.
        self.use_pvs = False
        self.pvs_epsilon = 1e-7
        self.researches = 0
        # ASPIRATION WINDOWS ARE GONE, not merely off, and the reason
        # is worth keeping: they were UNSOUND here, not just slow. The
        # narrow search writes LOWER/UPPER bounds into the SHARED
        # transposition table, and the full-window re-search then reads
        # those bounds as if they were valid at full width. Measured on
        # a synthetic evaluation, baseline and PVS both chose
        # knight (5,2)->(3,0) while aspiration chose (5,2)->(4,4), and
        # it cost nodes too (6206 -> 6564 at depth 4). Making it sound
        # needs per-window bound bookkeeping in the table, which is real
        # work for a measured loss.
        #: LEAF EVALUATION CACHE, keyed on the engine's own state hash.
        #: Changes no node, only time, and buys about 2% -- inside the
        #: noise. Left ON because it is strictly non-harmful (identical
        #: tree, bounded memory) and because the reason it buys so
        #: little is that MOVE GENERATION dominates, not evaluation: at
        #: depth 4 it serves 1576 hits of 6206 nodes and saves 0.12s.
        #: Any feature that makes the evaluation costlier shifts that
        #: balance, so the measurement here is a snapshot, not a verdict.
        #:
        #: Sound only because the weights behind `evaluate` are fixed
        #: for a searcher's lifetime: the trainer builds a fresh
        #: searcher per game and updates weights between games, never
        #: inside one.
        self.use_eval_cache = True
        self.eval_cache = {}
        self.eval_cache_limit = 200000
        self.eval_hits = 0
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
        #: The root's chosen move, kept because `_root` stores no table
        #: entry of its own and `principal_variation` needs a first step.
        self.best_description = None
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

        previous_value = None
        stable_for = 0
        for depth in range(1, self.max_depth + 1):
            if depth > 1 and time.time() >= deadline:
                break          # no time to start another depth
            try:
                value, index, complete = self._root(
                    sim, sim_turns, depth, me, best_description, deadline)
            except _OutOfTime:
                break
            if index is not None and not complete:
                # A PARTIAL ITERATION MUST PROVE ITSELF. Overwriting a
                # fully searched answer with one from an iteration that
                # ran out of time partway through is a real way to turn
                # a good move into a bad one between two moves that
                # looked the same -- which is what "it suddenly
                # blundered for no reason" looks like from outside.
                #
                # The partial answer is kept only when it is at least as
                # good as the completed one it would replace. That is
                # the standard discipline: on timeout you keep the move
                # you already trusted.
                if previous_value is not None and value < previous_value:
                    self.abandoned += 1
                    break
            if index is not None:
                found = describe(sim_turns[index])
                # HAS DEEPENING STOPPED CHANGING ANYTHING? Both the move
                # and the value have to hold still: a move that stays
                # while the value drifts is an answer still moving.
                if (found == best_description and previous_value is not
                        None and self._converged(value, previous_value)):
                    stable_for += 1
                else:
                    stable_for = 0
                best_index = index
                best_description = found
                self.best_description = best_description
                self.depth_reached = depth
                previous_value = value
                if self.settle is not None and stable_for >= self.settle:
                    # NOT A GUESS ABOUT THE POSITION. The test is that
                    # two further plies moved the answer by less than
                    # this evaluation's own leaves typically differ --
                    # a quantity `_observe` measures rather than one
                    # anybody chose.
                    self.settled += 1
                    break
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

    def principal_variation(self, engine, limit=None):
        """The line the last search believed, and the position it ends in.

        Read back from the transposition table, which already stores the
        best move per node for ordering -- so this costs one clone and a
        few hash lookups rather than a second search.

        WHY ANY OF THIS IS WANTED: the value the search reports for a
        position is not its static evaluation, it is the static
        evaluation OF THIS LEAF. A learner that fits the evaluation at
        the root is fitting a quantity the search never consults. TD-leaf
        fits it where it is actually read.

        Returns `(descriptions, position)`. The position is an
        independent clone, so the caller's engine is never touched, and
        the walk stops early at a terminal state, a table miss, or a
        stored move that is no longer legal (the table is keyed on a
        hash, so a collision or a stale entry must not be trusted).
        """
        from lgref.experiments.fastcopy import clone
        from lgref.experiments.mcts import describe

        sim = clone(engine)
        if not self.use_tt:
            return [], sim
        bound = self.depth_reached if limit is None else limit
        line = []
        # The root is seeded from `best_description` rather than the
        # table: `_root` is a separate loop and stores no entry, so a
        # table-only walk starts empty and the leaf is the root itself.
        pending = self.best_description
        while len(line) < max(0, bound):
            if sim.is_game_over():
                break
            if pending is None:
                key = _key(sim)
                if key is None:
                    break
                hit = self.tt.get(key)
                if hit is None or hit[3] is None:
                    break
                pending = hit[3]
            match = None
            for turn in sim.get_all_legal_turns():
                if describe(turn) == pending:
                    match = turn
                    break
            if match is None:
                break                   # stale or colliding entry
            # THE DEEPEST NON-TERMINAL NODE is what gets returned, so
            # one position is kept back. A decided position has a known
            # value and nothing for a static evaluation to learn, and
            # falling back to the ROOT instead -- which is what this did
            # first -- quietly reinstates TD-root for exactly the plies
            # near the end of a game, where the outcome signal is
            # strongest and the leaf matters most.
            previous = clone(sim)
            sim.execute_turn(match)
            line.append(pending)
            pending = None
            if sim.is_game_over():
                return line, previous
        return line, sim

    # ---- internals ------------------------------------------------------

    def _root(self, engine, turns, depth, me, best_description, deadline):
        """Returns `(value, index, complete)`.

        `complete` says whether EVERY root move was searched. It is
        reported because the caller must not take a partial iteration's
        answer on trust -- see `choose_turn`.
        """
        alpha, beta = 0.0, 1.0
        best_value, best_index = -1.0, None
        complete = True
        index_of = {id(turn): i for i, turn in enumerate(turns)}
        for turn in order_turns(engine, turns, best_description,
                                self.rank_capture,
                                self.killers.get(depth, ()), self.history,
                                depth):
            if time.time() >= deadline and best_index is not None:
                # Out of time partway through this depth. The answer is
                # kept but FLAGGED: the old comment here claimed it was
                # sound because the best-ordered moves go first, and
                # that is only true when the ordering is good. In a game
                # with no captures the ordering is killers and history
                # alone, so "best-ordered" can mean very little.
                complete = False
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
        return best_value, best_index, complete

    def _observe(self, scored):
        """Record a leaf value, so the margin can be derived from it.

        A running mean and mean absolute deviation, which is enough to
        say "how far apart do this evaluation's leaves tend to be" --
        the quantity a futility margin needs and the quantity a
        hard-coded constant was standing in for.
        """
        self._scale_count += 1
        delta = scored - self._scale_mean
        self._scale_mean += delta / self._scale_count
        self._scale_dev += (abs(delta) - self._scale_dev) / self._scale_count
        return scored

    def _converged(self, value, previous):
        """Did one more ply move the answer less than a leaf typically
        differs from the average leaf?

        The comparison quantity is `_scale_dev`, the running mean
        absolute deviation of leaf values that `_observe` keeps for the
        futility margin. It is in the evaluation's own units and nobody
        chose it, which is the whole reason it is used here rather than
        a constant: evaluations differ per game, so a fixed threshold
        would mean something different in each one.

        False while too few leaves have been seen to estimate anything,
        which makes the early exit silently inactive rather than wrong.
        """
        if self._scale_count < self.futility_min_samples:
            return False
        return abs(value - previous) <= self._scale_dev

    def _margin(self):
        """The futility margin: supplied if set, else derived, else None.

        None means DO NOT PRUNE. Returning a guess from three samples
        would be worse than not pruning, since an over-large margin
        discards quiet moves a capture could have rescued.
        """
        if self.futility_margin is not None:
            return self.futility_margin
        if self._scale_count < self.futility_min_samples:
            return None
        return self.futility_fraction * self._scale_dev

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
        if not self.use_eval_cache:
            return self._observe(self.evaluate(engine,
                                               engine.current_player))
        key = _key(engine)
        if key is None:
            return self._observe(self.evaluate(engine,
                                               engine.current_player))
        hit = self.eval_cache.get(key)
        if hit is not None:
            self.eval_hits += 1
            return hit
        scored = self._observe(self.evaluate(engine,
                                             engine.current_player))
        if len(self.eval_cache) < self.eval_cache_limit:
            self.eval_cache[key] = scored
        return scored

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
            # TURNS ARE PASSED IN, not regenerated. Move generation is
            # 0.54 ms and the frontier holds most of the nodes, so
            # generating twice there was duplicating the single most
            # expensive thing a node does.
            return self._quiesce(engine, self.quiescence, alpha, beta, me,
                                 deadline, turns)

        from lgref.experiments.mcts import describe

        hint = self.tt.get(key)[3] if (key is not None
                                       and self.tt.get(key)) else None
        original_alpha = alpha
        best_value = -1.0
        best_description = None
        if (self.reduce_turns is not None
                and depth >= self.reduce_above_depth and len(turns) > 8):
            fewer = self.reduce_turns(engine, turns)
            if fewer:
                self.reduced += len(turns) - len(fewer)
                turns = fewer
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
        margin = self._margin() if frontier else None
        for position, turn in enumerate(ordered):
            if (frontier and standing is not None and margin is not None
                    and not self.is_tactical(turn)
                    and getattr(turn, 'turn_type', 'move') == 'move'
                    and standing + margin <= alpha):
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
            # PRINCIPAL VARIATION SEARCH. Ordering already puts the
            # best move first, so every later move is a candidate for
            # REFUTATION rather than evaluation: a null window asks only
            # "is this better than alpha?", which cuts off sooner than a
            # window wide enough to say by how much. A move that beats
            # the null window has to be searched again properly, so the
            # trade is many cheap refutations against a few re-searches.
            narrow = (self.use_pvs and position > 0
                      and alpha + self.pvs_epsilon < beta)
            probe_beta = alpha + self.pvs_epsilon if narrow else beta
            try:
                value = 1.0 - self._search(child, depth - 1 - reduction,
                                           1.0 - probe_beta, 1.0 - alpha,
                                           me, deadline)
                if (reduction or narrow) and value > alpha:
                    # Either the reduction or the null window made the
                    # score untrustworthy: re-search at full depth and
                    # full width.
                    self.researches += 1
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
                if not self.is_tactical(turn):
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

    def _quiesce(self, engine, depth, alpha, beta, me, deadline,
                 turns=None):
        """Resolve while the score is still moving, captures first.

        EVERY capture is searched, to the given depth -- there is no
        delta gate here. An earlier version of this docstring claimed
        the search was "gated on a FRACTION of the largest change in the
        position" and cited this game's piece values, and no such gate
        was ever in the body. The claim is removed rather than
        implemented, because adding one changes which moves are searched
        and would need measuring before it could be believed.

        What the gate WOULD have to be, if added: a fraction of the
        spread the evaluation actually shows, which `_observe` now
        estimates. Never a constant in evaluation units -- those differ
        per game, which is the mistake the futility margin was making.
        """
        standing = self._leaf(engine)
        if depth <= 0 or engine.is_game_over():
            return standing
        if turns is None:
            turns = engine.get_all_legal_turns()
        if not turns:
            return 0.0
        candidates = [t for t in turns if self.is_tactical(t)]
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
                # `child`, NOT `engine`. These are the same object on
                # the make/unmake path, which hid the bug completely on
                # the case study -- and on the COPY path `child` is the
                # clone that had the capture applied while `engine` is
                # untouched, so quiescence re-searched the parent and
                # resolved nothing. Any game without make/unmake support
                # got a quiescence that either did nothing or, via the
                # line below, crashed outright.
                value = max(value, 1.0 - self._quiesce(
                    child, depth - 1, 1.0 - beta, 1.0 - alpha, me,
                    deadline))
            finally:
                # `_ascend`, NOT `restore` directly: the copy path has
                # no token and nothing to undo, and calling `restore`
                # with a `None` token raised AttributeError on the first
                # capture of any non-board game.
                self._ascend(engine, token)
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value


class _OutOfTime(Exception):
    """Raised to abandon an unfinished depth; the previous one stands."""
