"""A player with no objective, which is the point of it.

THE CONTROL THE DESIGN ALREADY PROMISED AND NOBODY BUILT. The mobility
agent's docstring says Phase 3 "reports effects under this agent AND
under random play, so that an effect appearing only under one of them
is visible as agent-dependent rather than reported as a property of the
rule". Every sweep ran the mobility agent alone.

WHY IT MATTERS MORE THAN A SECOND OPINION USUALLY DOES. The mobility
agent minimises the opponent's legal-turn count, and `mean_branching`
counts legal turns. The instrument's objective is the metric. So any
rule that hands the agent a cheaper way to suppress mobility will be
measured as reducing mobility -- which is a fact about the agent.

Measured: removing the neutral object raises mean branching by 6.6
turns under the mobility agent and LOWERS it by 3.4 under random play.
The sign of the effect belongs to the agent, not to the rule. The
designer's intuition -- that a movable neutral piece adds options --
is what random play shows.

This player is not good and is not meant to be. It is the answer to
"would this effect exist if nobody were chasing it".
"""


class RandomPlayer:
    """Uniform over the legal turns offered, seeded for reproducibility."""

    #: Every option scores zero, so every option is near-optimal.
    #: That is the honest reading: this player genuinely cannot
    #: tell its moves apart.
    score_tolerance = 0.0

    def __init__(self, rng=None, max_turns=1000):
        self.rng = rng
        self.max_turns = max_turns
        #: Kept so the policy metrics have the same interface as the
        #: mobility agent's. FLAT scores are honest here: this player
        #: genuinely cannot tell its options apart, so the near-optimal
        #: count it reports is the whole legal set rather than a
        #: judgement about which moves are good.
        self.last_scores = []

    def choose_turn(self, turns, engine):
        self.last_scores = [0.0] * len(turns)
        if self.rng is None:
            return turns[0]
        return turns[self.rng.randrange(len(turns))]


AGENTS = ('mcts', 'mobility', 'random')

#: Simulations per move when the agent is the search. Measured against
#: exact play on a solvable game: 50 -> 0.833, 200 -> 0.867, 800 ->
#: 0.967, where chance is 0.550 and the mobility heuristic is 0.725.
#: Self-agreement on Royal Chess is a different and worse story -- a
#: 53-wide root gives 2/4 at 2000 -- so this number buys accuracy, not
#: convergence.
DEFAULT_SIMULATIONS = 800


def build(name, rng, simulations=DEFAULT_SIMULATIONS):
    """One agent by name, so a config can ask for any of them.

    `mobility` is kept ONLY so the superseded runs remain reproducible.
    It must not be used for new measurement: it minimises the opponent's
    legal-turn count and `mean_branching` counts legal turns, so the
    instrument's objective is one of the metrics (#231). The pre-flight
    refuses a run configured with it.
    """
    if name == 'random':
        return RandomPlayer(rng=rng)
    if name == 'mcts':
        from lgref.experiments.mcts import MCTSPlayer
        return MCTSPlayer(n_simulations=simulations, rng=rng)
    if name == 'mobility':
        from lgref.experiments.mobility import MobilityPlayer
        return MobilityPlayer(rng=rng)
    raise ValueError('unknown agent {!r}; known: {}'.format(
        name, ', '.join(AGENTS)))
