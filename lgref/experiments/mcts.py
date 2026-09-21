"""UCB1 Monte-Carlo Tree Search over the fast GameEngine.

Phase 3's primary agent (issue #185). Chosen for one property above all:
**it encodes no assumption about which rules matter.**

A hand-written evaluation function would. Mobility is the worst possible
feature for this study — Knight Redesign, Queen Manipulation and Boulder
all directly change how many legal moves exist, so an agent that valued
mobility would play systematically better in high-mobility variants and
the ablation would measure the evaluation function rather than the
rules. Material weights are researcher-chosen too.

MCTS with random rollouts avoids this by construction. A rollout knows
only the legal-move generator; it cannot favour a variant because it
knows nothing about variants. Positions are scored by the win rate of
random games played from them — the most objective signal available.

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
import math
import random


DRAW_VALUE = 0.5


class _Node:
    """One search-tree node: the state AFTER `turn` was played."""

    __slots__ = ('turn', 'parent', 'children', 'untried', 'visits',
                 'value_sum', 'player_to_move')

    def __init__(self, turn, parent, untried, player_to_move):
        self.turn = turn
        self.parent = parent
        self.children = []
        self.untried = untried
        self.visits = 0
        self.value_sum = 0.0
        self.player_to_move = player_to_move

    @property
    def mean_value(self):
        return (self.value_sum / self.visits) if self.visits else 0.0

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

    def __init__(self, n_simulations=100, rollout_depth=200,
                 exploration=math.sqrt(2), rng=None, max_turns=1000):
        self.n_simulations = n_simulations
        self.rollout_depth = rollout_depth
        self.exploration = exploration
        self.rng = rng if rng is not None else random.Random()
        self.max_turns = max_turns
        # Populated by the last choose_turn call, for metric collection.
        self.last_root_visits = None
        self.last_root_values = None

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

        root = _Node(None, None, list(turns), engine.current_player)

        for _ in range(self.n_simulations):
            sim = copy.deepcopy(engine)
            node = self._select(root, sim)
            node = self._expand(node, sim)
            winner = self._rollout(sim)
            self._backup(node, winner)

        # Most-visited child is the standard robust choice: it is less
        # sensitive to a single lucky rollout than highest mean value.
        best = max(root.children, key=lambda c: (c.visits, c.mean_value))
        self.last_root_visits = [c.visits for c in root.children]
        self.last_root_values = [c.mean_value for c in root.children]
        return best.turn

    # ---- search phases ---------------------------------------------------

    def _select(self, node, sim):
        """Descend by UCB1 while fully expanded, replaying moves on `sim`."""
        while node.is_fully_expanded() and node.children:
            node = max(node.children,
                       key=lambda c: c.ucb1(self.exploration, node.visits))
            sim.execute_turn(node.turn)
            if sim.is_game_over():
                break
        return node

    def _expand(self, node, sim):
        """Add one child for an untried turn, if any remain."""
        if not node.untried or sim.is_game_over():
            return node
        idx = self.rng.randrange(len(node.untried))
        turn = node.untried.pop(idx)
        sim.execute_turn(turn)
        child_turns = [] if sim.is_game_over() else sim.get_all_legal_turns()
        child = _Node(turn, node, list(child_turns), sim.current_player)
        node.children.append(child)
        return child

    def _rollout(self, sim):
        """Uniform-random play to a terminal state or the depth cap.

        Returns the WINNER ('white', 'black' or None), not a score.
        Returning the winner rather than a perspective-relative number is
        what lets `_backup` assign each node its own perspective
        explicitly — see the note there on non-alternating turn order.

        A cut-off rollout counts as a draw. Inventing a positional score
        here would reintroduce exactly the hand-written evaluation this
        agent exists to avoid.
        """
        for _ in range(self.rollout_depth):
            if sim.is_game_over():
                break
            turns = sim.get_all_legal_turns()
            if not turns:
                break
            sim.execute_turn(self.rng.choice(turns))
        return sim.winner

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
