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


def _captured_rank(engine, turn, weights, scales):
    """How much the piece this turn captures is worth, by LEARNED weight.

    Reads the destination square's occupant -- no simulation. Returns 0
    for a non-capture. The weights come from TD, so ordering by them
    introduces no value judgement that the agent did not derive itself.
    """
    if not getattr(turn, 'is_capture', False):
        return 0.0
    target = getattr(turn, 'to_sq', None)
    if target is None:
        return 0.0
    board = getattr(engine, 'board', None)
    if board is None:
        return 0.0
    try:
        piece = board.squares[target[0]][target[1]].piece
    except Exception:
        return 0.0
    if piece is None:
        return 0.0
    name = type(piece).__name__
    if getattr(piece, 'is_royal', False):
        candidates = ('RoyalQueen', name + '*royal', 'Royal')
    elif getattr(piece, 'is_transformed', False):
        candidates = ('PromotedQueen',)
    else:
        candidates = (name,)
    for candidate in candidates:
        if candidate in weights:
            return abs(weights[candidate]) / max(scales.get(candidate, 1.0),
                                                 1.0)
    return 0.1          # a capture of something unweighted still beats a
                        # quiet move, because material is irreversible


def order_turns(engine, turns, best, weights, scales, killers=(),
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
            rank = _captured_rank(engine, turn, weights, scales)
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

    def __init__(self, evaluate, weights=None, scales=None, max_depth=5,
                 budget=3.0, quiescence=3, use_tt=True):
        self.evaluate = evaluate
        self.weights = weights or {}
        self.scales = scales or {}
        self.max_depth = max_depth
        self.budget = budget
        self.quiescence = quiescence
        self.use_tt = use_tt
        self.tt = {}
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
        self.depth_reached = 0
        deadline = time.time() + self.budget
        me = engine.current_player
        best_turn = turns[0]
        best_description = None

        for depth in range(1, self.max_depth + 1):
            if depth > 1 and time.time() >= deadline:
                break          # no time to start another depth
            try:
                value, turn = self._root(engine, turns, depth, me,
                                         best_description, deadline)
            except _OutOfTime:
                break
            if turn is not None:
                best_turn = turn
                best_description = describe(turn)
                self.depth_reached = depth
            if time.time() >= deadline:
                break
        return best_turn

    # ---- internals ------------------------------------------------------

    def _root(self, engine, turns, depth, me, best_description, deadline):
        alpha, beta = 0.0, 1.0
        best_value, best_turn = -1.0, None
        for turn in order_turns(engine, turns, best_description,
                                self.weights, self.scales,
                                self.killers.get(depth, ()), self.history,
                                depth):
            if time.time() >= deadline and best_turn is not None:
                # Out of time with an answer in hand from this depth.
                # Returning it is sound: the moves already searched were
                # the best-ordered ones, so the partial result is the
                # same kind of answer a shallower search would give.
                break
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            value = 1.0 - self._search(sim, depth - 1, 1.0 - beta,
                                       1.0 - alpha, me, deadline)
            if value > best_value:
                best_value, best_turn = value, turn
            alpha = max(alpha, value)
        return best_value, best_turn

    def _leaf(self, engine, me):
        if engine.is_game_over():
            winner = engine.winner
            if winner is None:
                return 0.5
            return 1.0 if winner == me else 0.0
        return self.evaluate(engine, me)

    def _search(self, engine, depth, alpha, beta, me, deadline):
        self.nodes += 1
        # CHECKED OFTEN ENOUGH TO MATTER. At 256 the granularity was
        # about half a second and a 2s budget overran to 5s, because
        # `_root` never checked at all and a single depth cannot be
        # abandoned halfway without losing its answer.
        if self.nodes % 32 == 0 and time.time() >= deadline:
            raise _OutOfTime()
        if engine.is_game_over():
            return self._leaf(engine, me)

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
        ordered = order_turns(engine, turns, hint, self.weights,
                              self.scales, self.killers.get(depth, ()),
                              self.history, depth)
        for position, turn in enumerate(ordered):
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
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
            value = 1.0 - self._search(sim, depth - 1 - reduction,
                                       1.0 - beta, 1.0 - alpha, me,
                                       deadline)
            if reduction and value > alpha:
                # It beat alpha despite the reduction, so the shallow
                # score cannot be trusted: re-search at full depth.
                value = 1.0 - self._search(sim, depth - 1, 1.0 - beta,
                                           1.0 - alpha, me, deadline)
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
        standing = self._leaf(engine, me)
        if depth <= 0 or engine.is_game_over():
            return standing
        turns = engine.get_all_legal_turns()
        if not turns:
            return 1.0 if engine.current_player != me else 0.0
        candidates = [t for t in turns if getattr(t, 'is_capture', False)]
        if not candidates:
            return standing
        value = standing                 # standing pat
        alpha = max(alpha, value)
        if alpha >= beta:
            return value
        for turn in order_turns(engine, candidates, None, self.weights,
                                self.scales):   # captures only; tiers 3-4 idle
            self.nodes += 1
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            value = max(value, 1.0 - self._quiesce(sim, depth - 1,
                                                   1.0 - beta, 1.0 - alpha,
                                                   me, deadline))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value


class _OutOfTime(Exception):
    """Raised to abandon an unfinished depth; the previous one stands."""


def load_searcher(path, budget=2.5, max_depth=8, quiescence=2):
    """A `Searcher` over weights saved by a TD training run.

    THE SEARCH EVALUATION OMITS MOBILITY, deliberately and on a measured
    basis. `features.with_mobility` calls `get_all_legal_turns()`, which
    made mobility 97% of the cost of an evaluation -- 0.567 ms of
    0.584 ms -- while TD gave it an effective weight of 0.0016, the
    smallest of any feature. Paying a third of a millisecond per node
    for a term worth a thousandth of a unit is a bad trade, so the
    search uses the cheap extractor and the learner keeps the full one.

    If mobility's learned weight ever rises materially, this trade
    should be re-made rather than inherited.
    """
    import json

    from lgref.experiments.bootstrap import normalise, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import royal_chess

    with open(path) as handle:
        payload = json.load(handle)
    weights = payload['weights']
    scales = payload.get('scales', {})

    def evaluate(engine, perspective):
        raw = differentials(royal_chess(engine), perspective)
        return value(weights, normalise(raw, dict(scales), update=False))

    return Searcher(evaluate, weights, scales, max_depth=max_depth,
                    budget=budget, quiescence=quiescence)
