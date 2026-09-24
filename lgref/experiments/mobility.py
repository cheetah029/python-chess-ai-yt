"""A one-ply agent that looks at every legal move.

Issue #206. MCTS at an affordable budget is not searching: on a 68-move
root, 40 simulations give 0.59 visits per child, UCB1 round-robins, and
measured self-agreement is 0% -- the same position with two seeds never
yields the same move. Making it a real search needs thousands of
simulations per move, which at 0.22 s/simulation puts a 441-turn game at
tens of hours.

The cheaper thing is also the better thing here: evaluate every root
move ONCE. Sixty-eight cheap evaluations beat two thousand rollouts that
cannot distinguish anything.

WHAT THIS HEURISTIC ACTUALLY IS, corrected. I first justified it as
tracking the loss conditions: three of this game's four are forms of
running out of legal turns. That justification was WRONG, and the
measurements already contradicted it -- all twenty self-play games ended
by `royals_captured`, not one by having no legal turn. Those conditions
fire through the repetition and tiny-endgame filters rather than through
natural mobility exhaustion, and natural stalemate is rare here because
every piece is more mobile than its chess counterpart.

What the heuristic is really doing is approximating MATERIAL. Fewer
enemy pieces means fewer enemy legal moves, so minimising opponent
mobility rewards capturing, and capturing royals is how the game is won.
That is a proxy, and a game-specific one: it works here because move
count tracks material, and there is no reason to expect that elsewhere.
Measured on tic-tac-toe, where move count tracks nothing, this agent
scores 69% against exact play while MCTS at 50 simulations scores 87%.

THE VALIDITY THREAT THIS CREATES. A material-greedy agent will make
ablations that change material dynamics look more important than
ablations that do not. Phase 3 therefore reports effects under this
agent AND under random play, so that an effect appearing only under one
of them is visible as agent-dependent rather than reported as a property
of the rule.

WHY IT STAYS GAME-AGNOSTIC. It consults only the rules' own legal-turn
function and the game's own terminal and winner tests. No piece values,
no board geometry, nothing that names a Royal Chess concept -- the
framework has to evaluate rules in any GDL game, so an agent tuned to
one of them would not be usable.
"""

import copy


class MobilityPlayer:
    """Pick the turn leaving me with options and the opponent without.

    One ply, deterministic given a seed. Cost is one legal-turn
    generation per root move, which is roughly two orders of magnitude
    below an MCTS search that still cannot tell its moves apart.
    """

    def __init__(self, rng=None, opponent_weight=1.0, max_turns=1000):
        self.rng = rng
        self.opponent_weight = opponent_weight
        self.max_turns = max_turns
        self.last_scores = []

    def _score(self, engine, me):
        """Higher is better for `me`, from the rules' own vocabulary."""
        if engine.is_game_over():
            if engine.winner == me:
                return float('inf')
            if engine.winner is None:
                return 0.0           # cap reached: no information
            return float('-inf')
        mine = len(engine.get_all_legal_turns())
        # The opponent moves next, so their count is the live one; ours
        # is what we would face afterwards and is not worth a second
        # expensive generation at this depth.
        return -self.opponent_weight * mine if engine.current_player != me \
            else float(mine)

    def choose_turn(self, turns, engine):
        me = engine.current_player
        scored = []
        for turn in turns:
            sim = copy.deepcopy(engine)
            sim.execute_turn(turn)
            scored.append((self._score(sim, me), turn))
        self.last_scores = [s for s, _ in scored]

        best = max(s for s, _ in scored)
        winners = [t for s, t in scored if s == best]
        if len(winners) == 1 or self.rng is None:
            return winners[0]
        # Ties broken by the seeded rng, so the agent stays deterministic
        # for a given seed while not always preferring move order.
        return winners[self.rng.randrange(len(winners))]
