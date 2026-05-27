"""
AI player implementations for self-play.
"""

import random


class RandomPlayer:
    """Picks uniformly at random from all legal turns.

    The engine enumerates each fully-specified combination (move +
    jump_choice + promo_choice) as a separate Turn, so this player needs
    only one decision method: pick one Turn uniformly. Each distinct
    full turn is therefore counted exactly once in the random sampling
    (no implicit branching at sub-choice time)."""

    def choose_turn(self, turns, engine=None):
        """Select a turn from the list of legal turns.

        `engine` is accepted for API parity with NeuralPlayer (which uses
        the engine to simulate turns). RandomPlayer ignores it.
        """
        if not turns:
            return None
        return random.choice(turns)
