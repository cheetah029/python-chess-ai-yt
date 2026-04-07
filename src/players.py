"""
AI player implementations for self-play.
"""

import random


class RandomPlayer:
    """Picks uniformly at random from all legal turns.
    For multi-step turns (jump capture, promotion), also picks randomly."""

    def choose_turn(self, turns):
        """Select a turn from the list of legal turns."""
        if not turns:
            return None
        return random.choice(turns)

    def choose_jump_capture(self, targets):
        """Choose whether to jump-capture and which target.
        Returns (row, col) to capture, or None to decline."""
        # Randomly capture or decline (equal probability for each option)
        options = list(targets) + [None]
        return random.choice(options)

    def choose_promotion(self, options):
        """Choose which piece type to promote to."""
        return random.choice(options)
