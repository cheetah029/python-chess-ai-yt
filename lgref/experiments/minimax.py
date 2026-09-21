"""Alpha-beta minimax with Monte-Carlo leaf evaluation.

Phase 3's cross-check agent (issue #185), paired with MCTS.

WHY MONTE-CARLO LEAVES

Minimax needs to score the positions where it stops searching, and that
scoring function is where researcher bias enters. For an ablation study
it is the wrong place to put an opinion: Knight Redesign, Queen
Manipulation and Boulder all directly change how many legal moves exist,
so an evaluation that valued mobility would make the agent play better in
high-mobility variants and the study would measure the evaluation instead
of the rules. Material weights are equally researcher-chosen — the design
notes put R ~ N ~ B only "in aggregate", with different shapes.

So leaves are scored the objective way: play `n_rollouts` uniform-random
games from the position and take the win rate. A rollout knows only the
legal-move generator, so it cannot favour any variant.

WHY PAIR IT WITH MCTS AT ALL

The two fail differently, which is what makes a cross-check worth its
cost. MCTS grows an asymmetric tree under UCB1 and can miss a line it
never expanded. Minimax is exhaustive to its depth: within that horizon
it cannot miss anything, and beyond it is blind. Agreement between two
agents with unrelated blind spots is much stronger evidence than either
alone.

COST

Monte-Carlo leaves are expensive — every leaf costs `n_rollouts` random
games. Alpha-beta pruning matters more here than in a normal engine,
because each pruned node saves whole rollouts rather than one cheap
evaluation. Move ordering is randomised (seeded) rather than
heuristic-ordered, since any ordering heuristic worth having would itself
be a hand-written evaluation.

Determinism: all randomness comes from an injected `random.Random`.
"""

import copy
import random


DRAW_VALUE = 0.5


class MonteCarloMinimaxPlayer:
    """Alpha-beta to fixed depth, leaves scored by random-rollout win rate.

    Args:
        depth: plies of exhaustive search. Branching is ~68 in Royal
            Chess, so each extra ply multiplies cost by roughly that.
        n_rollouts: random games per leaf. More rollouts means a less
            noisy leaf score; the variance of a win rate from n games is
            ~0.25/n, so this trades directly against search width.
        rollout_depth: plies before a rollout is cut off and scored a
            draw. Cutting off as a draw rather than guessing a positional
            score is deliberate — a guess would be the hand-written
            evaluation this agent exists to avoid.

            Must be deep enough that rollouts actually terminate, or every
            leaf scores DRAW_VALUE and the search has no signal at all.
            Measured: from an opening position, ~0% of random rollouts
            terminate within 50 plies, 3% within 100, 30% within 200. See
            the table in lgref/experiments/mcts.py.
        rng: `random.Random`, injected for reproducibility.
    """

    def __init__(self, depth=2, n_rollouts=8, rollout_depth=200, rng=None,
                 max_turns=1000):
        if depth < 1:
            raise ValueError('depth must be >= 1')
        self.depth = depth
        self.n_rollouts = n_rollouts
        self.rollout_depth = rollout_depth
        self.rng = rng if rng is not None else random.Random()
        self.max_turns = max_turns
        self.nodes_evaluated = 0
        self.leaves_evaluated = 0

    # ---- public interface ------------------------------------------------

    def choose_turn(self, turns, engine=None):
        if not turns:
            return None
        if len(turns) == 1:
            return turns[0]
        if engine is None:
            raise ValueError('MonteCarloMinimaxPlayer needs the engine')

        self.nodes_evaluated = 0
        self.leaves_evaluated = 0
        root_player = engine.current_player

        # Randomised move order: any heuristic ordering good enough to
        # help pruning would itself encode a positional opinion.
        ordered = list(turns)
        self.rng.shuffle(ordered)

        best_turn, best_value = None, -1.0
        alpha, beta = -1.0, 2.0
        for turn in ordered:
            sim = copy.deepcopy(engine)
            sim.execute_turn(turn)
            value = self._search(sim, self.depth - 1, alpha, beta, root_player)
            if value > best_value:
                best_value, best_turn = value, turn
            alpha = max(alpha, best_value)
        return best_turn

    # ---- search ----------------------------------------------------------

    def _search(self, sim, depth, alpha, beta, root_player):
        """Alpha-beta value of `sim`, always from `root_player`'s view.

        Scoring from ONE fixed perspective (rather than negamax) keeps the
        comparison direction explicit, which matters because this game's
        turn order is not strictly alternating — a boulder move or an
        action can be taken by either side, and `extra_move_every` (the
        positive control variant) deliberately gives one player two turns
        in a row. Deciding max-vs-min from `sim.current_player` rather
        than from parity is therefore required for correctness here.
        """
        self.nodes_evaluated += 1

        if sim.is_game_over():
            return self._terminal_value(sim, root_player)
        if depth <= 0:
            return self._evaluate(sim, root_player)

        turns = sim.get_all_legal_turns()
        if not turns:
            return self._terminal_value(sim, root_player)

        ordered = list(turns)
        self.rng.shuffle(ordered)
        maximizing = (sim.current_player == root_player)

        if maximizing:
            value = -1.0
            for turn in ordered:
                child = copy.deepcopy(sim)
                child.execute_turn(turn)
                value = max(value, self._search(child, depth - 1, alpha,
                                                beta, root_player))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        value = 2.0
        for turn in ordered:
            child = copy.deepcopy(sim)
            child.execute_turn(turn)
            value = min(value, self._search(child, depth - 1, alpha,
                                            beta, root_player))
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value

    # ---- evaluation ------------------------------------------------------

    def _terminal_value(self, sim, root_player):
        if sim.winner is None:
            return DRAW_VALUE
        return 1.0 if sim.winner == root_player else 0.0

    def _evaluate(self, sim, root_player):
        """Win rate of `n_rollouts` uniform-random games from here."""
        self.leaves_evaluated += 1
        total = 0.0
        for _ in range(self.n_rollouts):
            total += self._rollout(copy.deepcopy(sim), root_player)
        return total / self.n_rollouts

    def _rollout(self, sim, root_player):
        for _ in range(self.rollout_depth):
            if sim.is_game_over():
                break
            turns = sim.get_all_legal_turns()
            if not turns:
                break
            sim.execute_turn(self.rng.choice(turns))
        return self._terminal_value(sim, root_player)
