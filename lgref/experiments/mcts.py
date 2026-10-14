"""UCB1 Monte-Carlo Tree Search over the fast GameEngine.

Phase 3's primary agent (issue #185). Chosen for one property above all:
**it encodes no assumption about which rules matter.**

A hand-written evaluation function would. Mobility is the worst possible
feature for this study — Knight Redesign, Queen Manipulation and Boulder
all directly change how many legal moves exist, so an agent that valued
mobility would play systematically better in high-mobility variants and
the ablation would measure the evaluation function rather than the
rules. Material weights are researcher-chosen too.

MCTS with rollouts avoids this by construction. A rollout knows only
the legal-move generator and the terminal test; it cannot favour a
variant because it knows nothing about variants. Positions are scored
by the win rate of games played from them — the most objective signal
available.

THIS FILE'S OWN WARNING WENT UNHEEDED. Every measurement in this study
was then collected with a mobility agent, which is the feature named
above as the worst possible one, because MCTS was judged unaffordable.
The judgement rested on 0.22 s per simulation, and that number was
never taken apart: it is uniform rollouts running 264 plies because
uniform play makes no progress toward a capture-based win condition,
with a third of them returning no result at all. A playout that
prefers captures runs 40 plies and always returns one (#231).

Search:
  Selection   UCB1 over children, descending while a node is fully expanded
  Expansion   one new child per simulation (lazy)
  Simulation  uniform-random rollout to a terminal state or the depth cap
  Backup      each node credited from its own parent's mover's
              perspective (NOT flip-based negamax — turn order here is
              not strictly alternating; see _backup)

State handling: the engine mutates in place and has no unmake, so each
simulation works on a `copy.deepcopy` of the root engine. Measured at
~5 ms against ~950 plies/s of rollout, so the copy is a few percent of a
simulation's cost and is not worth the risk of a hand-written unmake
that would have to reverse boulder cooldowns, freeze flags,
invulnerability and the repetition history correctly.

Determinism: every rollout and every tie-break draws from an injected
`random.Random`, so a run is reproducible from its seed.
"""

import copy

from lgref.experiments.fastcopy import clone
import math
import random


DRAW_VALUE = 0.5


def describe(turn):
    """A turn as plain data, carrying no reference to any board.

    THE TREE MUST NOT HOLD TURN OBJECTS. A `Turn` points at a piece on
    the board that produced it, and `Board.move` writes `cooldown`,
    `moved` and `last_square` onto that piece -- so replaying a stored
    turn on a different simulation mutates whichever board the turn
    came from. Measured on the live engine: one simulated boulder move
    took the real cooldown 0 -> 2 and the real legal-turn count 73 ->
    69, and every search was doing that hundreds of times per move.

    Descriptions are resolved against the simulation that will execute
    them, so a turn only ever touches its own board.
    """
    # A turn that is already plain data -- the solvable game's turns are
    # plain ints -- holds no reference to any board and is its own
    # description. Only turns carrying a piece can write through to the
    # board that produced them, which is the whole problem this solves.
    if not hasattr(turn, 'turn_type'):
        return turn
    piece = getattr(turn, 'piece', None)
    return (turn.turn_type, getattr(piece, 'name', None),
            getattr(turn, 'from_sq', None), getattr(turn, 'to_sq', None),
            getattr(turn, 'transform_target', None),
            getattr(turn, 'jump_choice', None),
            getattr(turn, 'promo_choice', None),
            getattr(turn, 'has_jump_offer', False))


def resolve(sim, description, legal=None):
    """The turn matching `description` in THIS simulation, or None."""
    for turn in (legal if legal is not None else sim.get_all_legal_turns()):
        if describe(turn) == description:
            return turn
    return None


class _Node:
    """One search-tree node: the state AFTER `turn` was played.

    `turn` is a DESCRIPTION, not a Turn -- see `describe`.
    """

    __slots__ = ('turn', 'parent', 'children', 'untried', 'visits',
                 'value_sum', 'player_to_move', 'amaf_visits',
                 'amaf_value_sum')

    def __init__(self, turn, parent, untried, player_to_move):
        self.turn = turn
        self.parent = parent
        self.children = []
        self.untried = untried
        self.visits = 0
        self.value_sum = 0.0
        self.player_to_move = player_to_move
        # RAVE / all-moves-as-first counters. A move's value estimated
        # from EVERY simulation in which it appeared, not only those
        # where it was played at this node -- which is the whole point:
        # at branching 58 and 800 simulations a child gets 14 plays and
        # the noise swamps the signal, while the same move appears
        # somewhere in hundreds of simulations.
        self.amaf_visits = 0
        self.amaf_value_sum = 0.0

    @property
    def mean_value(self):
        return (self.value_sum / self.visits) if self.visits else 0.0

    @property
    def amaf_mean(self):
        return ((self.amaf_value_sum / self.amaf_visits)
                if self.amaf_visits else 0.0)

    def rave_score(self, exploration, parent_visits, bias):
        """UCB1 with the MC-RAVE blend.

        beta falls from 1 to 0 as real visits accumulate, so the shared
        estimate guides early and the node's own estimate takes over once
        it has enough samples of its own. `bias` is the visit count at
        which the two carry equal weight.
        """
        if not self.visits and not self.amaf_visits:
            return float('inf')
        if not self.visits:
            # Never played, but seen elsewhere: trust the shared estimate
            # rather than returning infinity, which would force the
            # search to try every child before using any information.
            exploit = self.amaf_mean
            beta = 1.0
        else:
            total = self.visits + self.amaf_visits
            beta = (self.amaf_visits / float(total)) if total else 0.0
            # Standard MC-RAVE schedule: equal weight at `bias` visits.
            beta *= bias / float(bias + self.visits)
            exploit = ((1.0 - beta) * self.mean_value
                       + beta * self.amaf_mean)
        explore = exploration * math.sqrt(
            math.log(max(parent_visits, 1)) / max(self.visits, 1))
        return exploit + explore

    def is_fully_expanded(self):
        return not self.untried

    def ucb1(self, exploration, parent_visits):
        if not self.visits:
            return float('inf')
        exploit = self.value_sum / self.visits
        explore = exploration * math.sqrt(math.log(parent_visits) / self.visits)
        return exploit + explore


class MCTSPlayer:
    """Fixed-budget MCTS. Matches the `choose_turn(turns, engine)` interface
    used by AIController and the training loop.

    Args:
        n_simulations: simulations per move. The whole search budget.
        rollout_depth: plies before a rollout is cut off and scored a
            draw. THIS IS THE MOST IMPORTANT SETTING and must not be
            tuned down for speed. Measured fraction of random rollouts
            reaching a terminal state within D plies:

                from ply   D=20  D=50  D=100  D=200  D=400
                       0   0.00  0.00   0.03   0.30   0.65
                      50   0.00  0.00   0.05   0.35   0.75
                     150   0.07  0.17   0.17   0.47   0.78
                     250   0.35  0.42   0.47   0.70   0.88

            Below ~100 plies essentially NO rollout terminates from an
            opening position, so every rollout scores DRAW_VALUE, every
            child has identical value, and UCB1 degenerates to visiting
            the least-visited child — exact round-robin. The search then
            costs full price and returns random play. This was a real bug
            caught by test_mcts_concentrates_visits_rather_than_spreading_them,
            which measured perfectly uniform visits at every budget.

            The default of 200 is the shallowest cap that leaves usable
            signal. Raising it strengthens the agent and costs linearly.
        exploration: UCB1 constant. sqrt(2) is the theoretical value for
            rewards in [0, 1], which is the range used here.
        rng: `random.Random`, injected so runs are reproducible.
    """

    #: What counts as "near-optimal" in THIS agent's units. Values here
    #: are win rates in [0, 1], so five points of win rate. The mobility
    #: heuristic scored in legal-turn counts and used 1.0. A tolerance
    #: is only meaningful beside the scale it applies to, and sharing
    #: one across agents made the near-optimal count mean different
    #: things in different runs.
    score_tolerance = 0.05

    def __init__(self, n_simulations=100, rollout_depth=200,
                 exploration=math.sqrt(2), rng=None, max_turns=1000,
                 use_rave=False, rave_bias=300, use_mast=False,
                 mast_weight=3.0, evaluator=None, eval_depth=0):
        self.n_simulations = n_simulations
        self.rollout_depth = rollout_depth
        self.exploration = exploration
        self.rng = rng if rng is not None else random.Random()
        self.max_turns = max_turns
        # BOTH DEFAULT OFF so the existing agent is byte-identical and
        # the comparison is a clean A/B rather than a replacement.
        #
        # WHY THESE TWO AND NOT AN EVALUATION FUNCTION. The constraint is
        # an evaluator that works across DIFFERENT GAMES while playing
        # well, and a hand-written position score cannot: royals and
        # material are facts about Royal Chess and mean nothing in nim.
        # RAVE and MAST are the general-game-playing answer to exactly
        # this problem -- they derive their guidance from the game's own
        # move set and its own outcomes, so they carry no domain
        # knowledge and transfer unchanged. Both are standard in GGP
        # competition players for high-branching games with no
        # hand-coded features.
        self.use_rave = use_rave
        self.rave_bias = rave_bias
        self.use_mast = use_mast
        self.mast_weight = mast_weight
        #: MAST: a GLOBAL move -> (sum, count) table, indexed by move
        #: description and so independent of the state it was played in.
        #: It biases the ROLLOUT POLICY, which is the sampling device,
        #: not the objective -- a rollout is still scored only by who
        #: won.
        self._mast = {}
        #: An optional learned leaf evaluation, as
        #: `evaluator(engine, perspective) -> value in [0, 1]`. When set,
        #: a rollout runs at most `eval_depth` plies and the evaluation
        #: scores the position it reached, instead of playing on to a
        #: terminal state.
        #:
        #: WHY TRUNCATION IS THE POINT. A full random rollout is a
        #: Bernoulli sample, so its variance is irreducible by anything
        #: except more samples -- and 14 samples per child is what makes
        #: the midgame estimate pure noise. A deterministic evaluation
        #: has NO sampling variance, which is the only thing that changes
        #: the arithmetic.
        self.evaluator = evaluator
        self.eval_depth = eval_depth
        #: The same statistics indexed by DESCRIPTION ALONE, because the
        #: rollout needs the pooled average and recomputing it meant
        #: scanning the whole table for every candidate move at every
        #: rollout step -- O(table x moves x depth) per simulation. On
        #: Royal Chess that made the MAST agent twice as slow as the
        #: baseline for no measurable gain, which a human noticed as "it
        #: takes a really long time to make a move".
        self._mast_pool = {}
        # Populated by the last choose_turn call, for metric collection.
        self.last_root_visits = None
        self.last_root_values = None
        #: How much of the budget bought nothing. A censored rollout
        #: returned no result, and this game has no draw condition, so
        #: that is a measurement failure rather than an outcome.
        self.rollouts_censored = 0
        self.rollouts_total = 0

    @property
    def censored_share(self):
        """Fraction of simulations that returned no result."""
        if not self.rollouts_total:
            return None
        return round(self.rollouts_censored / self.rollouts_total, 4)

    # ---- public interface ------------------------------------------------

    def choose_turn(self, turns, engine=None):
        if not turns:
            return None
        if len(turns) == 1:
            self.last_root_visits = [self.n_simulations]
            self.last_root_values = [0.0]
            return turns[0]
        if engine is None:
            raise ValueError('MCTSPlayer needs the engine to search')

        root = _Node(None, None, [describe(t) for t in turns],
                     engine.current_player)

        for _ in range(self.n_simulations):
            sim = clone(engine)
            # (player, description) for every move this simulation made,
            # in the tree and in the rollout. RAVE and MAST both need it:
            # a move's shared value is estimated from every simulation it
            # appeared in, which is where the extra samples come from.
            played = [] if (self.use_rave or self.use_mast) else None
            node = self._select(root, sim, played)
            node = self._expand(node, sim, played)
            value_of = None
            if self.evaluator is not None:
                value_of = self._truncated_value(sim, played)
                self._backup_value(node, value_of)
                winner = None
            else:
                winner = self._rollout(sim, played)
                self._backup(node, winner)
            # RAVE and MAST are credited from the SAME signal the tree
            # was credited from. Passing the winner alone would hand
            # them `None` whenever an evaluator is in use, and
            # `_value_for(None, p)` is DRAW_VALUE -- so both would be
            # fed a flat 0.5 for every move and go silently inert while
            # still appearing configured.
            if played is not None:
                if self.use_rave:
                    self._backup_amaf(node, winner, played,
                                      value_of=value_of)
                if self.use_mast:
                    self._update_mast(winner, played,
                                      value_of=value_of)

        # Most-visited child is the standard robust choice: it is less
        # sensitive to a single lucky rollout than highest mean value.
        best = max(root.children, key=lambda c: (c.visits, c.mean_value))
        self.last_root_visits = [c.visits for c in root.children]
        self.last_root_values = [c.mean_value for c in root.children]
        # Back to one of the CALLER's turn objects. The tree holds
        # descriptions, and the caller expects a turn it can execute on
        # its own engine.
        chosen = resolve(engine, best.turn, legal=turns)
        if chosen is None:                         # pragma: no cover
            raise RuntimeError(
                'search chose a turn the caller does not offer: {!r}'.format(
                    best.turn))
        # THE NAME THE METRICS READ. `policy_metrics` takes
        # `last_scores`, and this class exposed only `last_root_values`,
        # so switching the agent emptied `mean_policy_branching`,
        # `mean_move_entropy` and both conditional variants -- one of
        # which is a profile dimension. Nothing errored; four columns
        # went quietly blank, and the pre-flight is what noticed.
        self.last_scores = list(self.last_root_values)
        return chosen

    # ---- search phases ---------------------------------------------------

    def _select(self, node, sim, played=None):
        """Descend by UCB1 while fully expanded, replaying moves on `sim`."""
        while node.is_fully_expanded() and node.children:
            if self.use_rave:
                node = max(node.children,
                           key=lambda c: c.rave_score(
                               self.exploration, node.visits,
                               self.rave_bias))
            else:
                node = max(node.children,
                           key=lambda c: c.ucb1(self.exploration,
                                                node.visits))
            turn = resolve(sim, node.turn)
            if turn is None:                       # pragma: no cover
                break
            if played is not None:
                played.append((sim.current_player, node.turn))
            sim.execute_turn(turn)
            if sim.is_game_over():
                break
        return node

    def _expand(self, node, sim, played=None):
        """Add one child for an untried turn, if any remain."""
        if not node.untried or sim.is_game_over():
            return node
        idx = self.rng.randrange(len(node.untried))
        description = node.untried.pop(idx)
        turn = resolve(sim, description)
        if turn is None:                           # pragma: no cover
            return node
        if played is not None:
            played.append((sim.current_player, description))
        sim.execute_turn(turn)
        child_turns = [] if sim.is_game_over() else sim.get_all_legal_turns()
        child = _Node(description, node,
                      [describe(t) for t in child_turns], sim.current_player)
        node.children.append(child)
        return child

    def _backup_amaf(self, node, winner, played, value_of=None):
        """Credit every child whose move appeared later in the simulation.

        THE ALL-MOVES-AS-FIRST ASSUMPTION, stated so it is not mistaken
        for a theorem: that a move's value is roughly independent of WHEN
        it was played. That is false in general -- order matters in every
        interesting game -- which is why the blend in `rave_score` decays
        the shared estimate to zero as a node accumulates its own visits.
        RAVE is a biased estimator used early, where the unbiased one has
        no samples at all, and discarded later.

        The player is part of the match: crediting a child because the
        OPPONENT happened to play that move would invert the sign, which
        is the same class of error as the backup perspective bug above.
        """
        by_player = {}
        for mover, description in played:
            by_player.setdefault(mover, set()).add(description)
        current = node
        while current is not None:
            # A child of `current` was played by whoever is to move AT
            # `current`.
            mover = current.player_to_move
            seen = by_player.get(mover)
            if seen:
                for child in current.children:
                    if child.turn in seen:
                        child.amaf_visits += 1
                        child.amaf_value_sum += (
                            value_of(mover) if value_of is not None
                            else self._value_for(winner, mover))
            current = current.parent

    def _update_mast(self, winner, played, value_of=None):
        """Global per-move averages, for the rollout policy.

        Maintains the pooled index alongside the per-player table, so the
        rollout reads an average instead of recomputing one.
        """
        for mover, description in played:
            value = (value_of(mover) if value_of is not None
                     else self._value_for(winner, mover))
            key = _mast_key(mover, description)
            total, count = self._mast.get(key, (0.0, 0))
            self._mast[key] = (total + value, count + 1)
            total, count = self._mast_pool.get(description, (0.0, 0))
            self._mast_pool[description] = (total + value, count + 1)

    def _value_for(self, winner, player):
        """The outcome from `player`'s point of view."""
        if winner is None:
            return DRAW_VALUE
        return 1.0 if winner == player else 0.0

    def _mast_mean(self, player, description):
        total, count = self._mast.get(_mast_key(player, description),
                                      (0.0, 0))
        return (total / count) if count else None

    def _playout_turn(self, turns):
        """One rollout move: prefer a capture, uniformly among captures.

        WHY THIS IS NOT THE EVALUATION FUNCTION THIS AGENT EXISTS TO
        AVOID. The OBJECTIVE is untouched -- a rollout is still scored
        only by who won. This changes the SAMPLING DEVICE used to
        estimate that objective, which is what a light playout policy is
        for in every MCTS implementation.

        WHY IT WAS NEEDED. This game has no draw condition, so a rollout
        stopped by the depth cap is CENSORED, not drawn, and scoring it
        DRAW_VALUE fed the search a number for a game that had no
        result. Measured from a 20-ply opening position, uniform
        rollouts ran 264 plies and 4 in 12 returned no result at all: a
        third of the search budget bought nothing.

        WHY CAPTURE AND NOT SOMETHING ELSE. The win condition here IS
        the capture of two specific pieces, so capturing is the only
        move class that can make progress toward it. That is read off
        the terminal condition rather than chosen by a researcher, which
        is the distinction that matters -- mobility, material weights
        and piece values are all preferences about how to play well,
        while "captures advance a capture-based win condition" is a
        reading of the rules. It is still a bias in the sampling, and
        its cost is measured against exact play on a solvable game
        rather than argued about.
        """
        captures = [turn for turn in turns
                    if getattr(turn, 'is_capture', False)]
        pool = captures if captures else turns
        if not self.use_mast:
            return self.rng.choice(pool)
        return self._mast_choice(pool)

    def _mast_choice(self, turns, player=None):
        """Pick by a Gibbs distribution over the global move averages.

        DOMAIN-FREE BY CONSTRUCTION: the table is keyed by the game's own
        move descriptions and filled from the game's own outcomes, so the
        same code guides rollouts in Royal Chess, nim and an m,n,k game
        without knowing which it is in.

        Softmax rather than argmax: a greedy rollout policy explores one
        line and makes the estimate confidently wrong, which is worse
        than noisy. Moves never seen get the neutral value so they are
        tried rather than starved.
        """
        weights, seen_any = [], False
        for turn in turns:
            mean = self._mast_mean(player, describe(turn)) \
                if player is not None else None
            if mean is None:
                mean = self._mast_pooled(describe(turn))
            if mean is None:
                mean = DRAW_VALUE
            else:
                seen_any = True
            weights.append(math.exp(self.mast_weight * mean))
        if not seen_any:
            return self.rng.choice(turns)
        total = sum(weights)
        if total <= 0:                             # pragma: no cover
            return self.rng.choice(turns)
        threshold = self.rng.random() * total
        running = 0.0
        for turn, weight in zip(turns, weights):
            running += weight
            if running >= threshold:
                return turn
        return turns[-1]                           # pragma: no cover

    def _mast_pooled(self, description):
        """The move's average over both players, from the index.

        Pooling is the standard MAST formulation: a rollout does not know
        whose statistic it wants without threading the mover through
        every call. The cost is that a move good for one side and bad for
        the other averages out; the benefit is a table that fills an
        order of magnitude faster, which is the point at these budgets.
        """
        total, count = self._mast_pool.get(description, (0.0, 0))
        return (total / count) if count else None

    def _rollout(self, sim, played=None):
        """Play to a terminal state, or to the cap if it is not reached.

        Returns the WINNER ('white', 'black' or None), not a score.
        Returning the winner rather than a perspective-relative number
        is what lets `_backup` assign each node its own perspective
        explicitly -- see the note there on non-alternating turn order.

        A cut-off rollout still counts as a draw and still should not.
        With a terminating playout it is rare rather than routine, and
        `censored_share` reports how often it happens so the rate is
        visible instead of assumed.
        """
        for _ in range(self.rollout_depth):
            if sim.is_game_over():
                break
            turns = sim.get_all_legal_turns()
            if not turns:
                break
            chosen = self._playout_turn(turns)
            if played is not None:
                played.append((sim.current_player, describe(chosen)))
            sim.execute_turn(chosen)
        self.rollouts_total += 1
        if sim.winner is None:
            self.rollouts_censored += 1
        return sim.winner

    def _truncated_value(self, sim, played=None):
        """A callable giving the leaf's value from any perspective.

        Plays at most `eval_depth` plies -- zero means evaluate the leaf
        directly -- and then scores with the learned evaluation. If the
        position is terminal the true outcome is used instead, because a
        learned estimate of a decided position is strictly worse than the
        decision.
        """
        for _ in range(self.eval_depth):
            if sim.is_game_over():
                break
            turns = sim.get_all_legal_turns()
            if not turns:
                break
            chosen = self._playout_turn(turns)
            if played is not None:
                played.append((sim.current_player, describe(chosen)))
            sim.execute_turn(chosen)
        if sim.is_game_over() and sim.winner is not None:
            winner = sim.winner
            return lambda perspective: (1.0 if winner == perspective
                                        else 0.0)
        return lambda perspective: self.evaluator(sim, perspective)

    def _backup_value(self, node, value_of):
        """Like `_backup`, but crediting a VALUE rather than a winner.

        The perspective rule is the same and matters for the same reason:
        a node's value must be stored from the perspective of the player
        who moved INTO it, because selection at the parent maximises over
        children. Storing it from the child's mover's perspective makes
        the parent pick the move best for its opponent -- the sign error
        that once measured 0 wins in 20 games against RandomPlayer.
        """
        while node is not None:
            node.visits += 1
            perspective = (node.parent.player_to_move
                           if node.parent is not None
                           else node.player_to_move)
            node.value_sum += value_of(perspective)
            node = node.parent

    def _backup(self, node, winner):
        """Credit every node on the path, each from its OWN perspective.

        A node's value must be stored from the perspective of the player
        who MOVED INTO it — that is, its parent's mover — because
        selection at the parent takes a max over its children. Storing a
        child's value from the CHILD's mover's perspective instead makes
        the parent pick the move best for its opponent, which is a sign
        error that produces a search actively worse than random. That was
        the original bug here: measured 0 wins in 20 games against
        RandomPlayer even after rollout depth was corrected.

        The perspective is recomputed per node rather than alternated
        with `1 - value`, because turn order in this game is NOT strictly
        alternating: either player may move the boulder, actions and
        moves both consume a turn, and the `extra_move_every` positive
        control deliberately gives one player two turns in a row. A
        flip-based negamax backup silently mis-credits every one of those
        cases.
        """
        while node is not None:
            node.visits += 1
            perspective = (node.parent.player_to_move
                           if node.parent is not None
                           else node.player_to_move)
            if winner is None:
                node.value_sum += DRAW_VALUE
            elif winner == perspective:
                node.value_sum += 1.0
            node = node.parent


# ---- RAVE and MAST: strength without domain knowledge -------------------
#
# WHY THESE AND NOT AN EVALUATION FUNCTION. The requirement is an
# evaluator that works across DIFFERENT GAMES while playing well, and a
# hand-written position score cannot satisfy it: "count the royals" is a
# fact about Royal Chess and is meaningless in nim or an m,n,k game.
#
# The diagnosis says what has to change. At 800 simulations over 56 moves
# each child gets 14.3 rollouts; a win rate from 14 Bernoulli samples has
# standard error 0.134, and the observed spread between root moves is
# 0.139. The entire difference is noise. Since variance falls as 1/sqrt(n),
# buying signal with samples needs ~140,000 simulations per move -- 2.1
# hours. The estimator has to change, not the budget.
#
# Two general-game-playing techniques change it without adding domain
# knowledge, because both derive their guidance from the game's OWN move
# set and its OWN outcomes:
#
#   RAVE  estimates a move's value from every simulation in which it
#         appeared ANYWHERE, not only those where it was played at this
#         node. At branching 58 a child is played 14 times but the same
#         move appears in hundreds of simulations, so the shared estimate
#         has an order of magnitude more samples. That is the sample
#         deficit addressed directly.
#
#   MAST  keeps a global per-move average and biases the ROLLOUT toward
#         moves that have done well. This reduces rollout variance and
#         makes playouts less uniformly random, so the win/loss signal
#         correlates better with the position. It changes the sampling
#         device, not the objective: a rollout is still scored only by
#         who won.
#
# Both are standard in GGP competition players precisely because they
# must play many unseen games with no hand-coded features.


def _mast_key(player, description):
    return (player, description)
