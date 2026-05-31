"""Monte Carlo Tree Search player for GGPGame.

Plays the variant (or any GDL game) by building a search tree
rooted at the current state, expanding nodes via UCB1, and
estimating leaf values via uniform-random rollouts.

  - Selection: UCB1 (Upper Confidence Bound applied to trees)
  - Expansion: add ONE child per visit (lazy expansion)
  - Simulation: uniform-random rollout to terminal or step cap
  - Backup: propagate the winner's goal up the tree, averaged
    per visit

The state-machine layer is `GGPGame`. We snapshot game state
(the Python set of `(true ?fact)` tuples) for tree nodes,
restore on each rollout. This is cheap because the state is a
hashable frozenset of small tuples.

Usage:

    from ggp.game import GGPGame
    from ggp.mcts import MCTSPlayer

    g = GGPGame.from_file('docs/gdl/step1_kings_queens.gdl')
    p = MCTSPlayer('white', n_rollouts=200, rollout_max_steps=80)
    move = p.choose(g)
    g.step({'white': move, 'black': 'noop'})

`choose(game)` does NOT mutate `game`. It snapshots+restores
internally.
"""

import math
import random as _random


_INFINITY = float('inf')


class MCTSNode:
    """One node in the search tree.

    Attributes:
        state_snapshot — frozen Python set of state facts
        to_move — role whose turn it is (for the move that
                  generated this node's children)
        parent — MCTSNode or None (root)
        action — the move that produced this node from parent
        children — dict {action: MCTSNode}
        n_visits — int
        total_value — float (sum of rollout values for the
                      `to_move` role across visits)
        untried_actions — list of legal moves not yet expanded
        terminal — None until determined; True/False after first
                   visit
    """

    __slots__ = (
        'state_snapshot', 'to_move', 'parent', 'action',
        'children', 'n_visits', 'total_value',
        'untried_actions', 'terminal',
    )

    def __init__(self, state_snapshot, to_move, parent=None,
                 action=None):
        self.state_snapshot = state_snapshot
        self.to_move = to_move
        self.parent = parent
        self.action = action
        self.children = {}
        self.n_visits = 0
        self.total_value = 0.0
        self.untried_actions = None  # populated lazily
        self.terminal = None         # populated lazily


def _snapshot(game):
    return frozenset(game.state)


def _restore(game, snapshot):
    game.state = set(snapshot)


class MCTSPlayer:
    """MCTS-driven move chooser for a GGPGame.

    Args:
        role: which role this player plays (e.g. 'white')
        n_rollouts: rollouts per move (more = stronger but slower)
        rollout_max_steps: cap rollout depth (avoids infinite
                           rollouts in non-terminating game states)
        ucb_c: UCB exploration constant (sqrt(2) is the textbook
               default)
        seed: RNG seed for reproducibility
    """

    def __init__(self, role, n_rollouts=200, rollout_max_steps=80,
                 ucb_c=math.sqrt(2), seed=None):
        self.role = role
        self.n_rollouts = n_rollouts
        self.rollout_max_steps = rollout_max_steps
        self.ucb_c = ucb_c
        self._rng = _random.Random(seed)

    # ---- public API ----------------------------------------------------

    def choose(self, game):
        """Return the action this player chooses from the current
        `game` state. Does NOT mutate `game` — snapshots/restores
        around the search."""
        saved = _snapshot(game)
        try:
            root = MCTSNode(saved, to_move=self.role)
            self._ensure_untried_actions(root, game)
            if not root.untried_actions:
                return None
            if len(root.untried_actions) == 1:
                # Only one legal move — skip the search.
                return root.untried_actions[0]
            for _ in range(self.n_rollouts):
                _restore(game, saved)
                self._iterate(root, game)
            # Pick the most-visited child (robust child).
            best_action = None
            best_visits = -1
            for action, child in root.children.items():
                if child.n_visits > best_visits:
                    best_visits = child.n_visits
                    best_action = action
            return best_action
        finally:
            _restore(game, saved)

    # ---- single MCTS iteration ----------------------------------------

    def _iterate(self, root, game):
        # 1. SELECTION: walk down the tree using UCB1 until we reach
        #    a leaf (unexpanded actions) or a terminal node.
        node = root
        while True:
            if node.terminal is None:
                node.terminal = game.is_terminal()
            if node.terminal:
                break
            self._ensure_untried_actions(node, game)
            if node.untried_actions:
                break
            # No untried actions AND no children → can't progress
            # the tree (typically happens when our role has only
            # 'noop' available because it's the opponent's
            # control turn). Skip to rollout from here.
            if not node.children:
                break
            # All actions expanded — pick best UCB1 child.
            action, child = self._best_ucb_child(node)
            game.step({self.role: action, self._opponent(): 'noop'})
            node = child

        # 2. EXPANSION: if non-terminal and has untried actions, add
        #    a child for one of them.
        if not node.terminal and node.untried_actions:
            action = node.untried_actions.pop(self._rng.randrange(
                len(node.untried_actions)))
            game.step({self.role: action, self._opponent(): 'noop'})
            child = MCTSNode(
                _snapshot(game), to_move=self.role,
                parent=node, action=action)
            node.children[action] = child
            node = child

        # 3. SIMULATION: uniform random rollout from this node.
        value = self._rollout(game)

        # 4. BACKUP: propagate value up.
        cur = node
        while cur is not None:
            cur.n_visits += 1
            cur.total_value += value
            cur = cur.parent

    # ---- helpers -------------------------------------------------------

    def _opponent(self):
        return 'black' if self.role == 'white' else 'white'

    def _ensure_untried_actions(self, node, game):
        if node.untried_actions is None:
            moves = game.legal_moves(self.role)
            # Filter out 'noop' (the off-turn role's only option).
            node.untried_actions = [m for m in moves if m != 'noop']

    def _best_ucb_child(self, node):
        log_n = math.log(node.n_visits) if node.n_visits > 0 else 0.0
        best_score = -_INFINITY
        best_pair = None
        for action, child in node.children.items():
            if child.n_visits == 0:
                # Unvisited child should be picked first.
                return action, child
            exploit = child.total_value / child.n_visits
            explore = self.ucb_c * math.sqrt(log_n / child.n_visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_pair = (action, child)
        return best_pair

    def _rollout(self, game):
        """Uniform-random simulation to terminal or step cap.
        Returns the value for THIS player's role (1.0 = win,
        0.5 = neutral / cap, 0.0 = loss)."""
        steps = 0
        while not game.is_terminal() and steps < self.rollout_max_steps:
            my_moves = game.legal_moves(self.role)
            opp_moves = game.legal_moves(self._opponent())
            if not my_moves or not opp_moves:
                break
            my_choice = self._rng.choice(my_moves)
            opp_choice = self._rng.choice(opp_moves)
            game.step({
                self.role: my_choice,
                self._opponent(): opp_choice,
            })
            steps += 1
        if game.is_terminal():
            my_goal = game.goal(self.role)
            opp_goal = game.goal(self._opponent())
            if my_goal > opp_goal:
                return 1.0
            if my_goal < opp_goal:
                return 0.0
            return 0.5
        # Hit the step cap — neutral.
        return 0.5
