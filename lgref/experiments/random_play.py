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


AGENTS = {'mobility': None, 'random': RandomPlayer}


def build(name, rng):
    """One agent by name, so a config can ask for either."""
    if name == 'random':
        return RandomPlayer(rng=rng)
    if name == 'mobility':
        from lgref.experiments.mobility import MobilityPlayer
        return MobilityPlayer(rng=rng)
    raise ValueError('unknown agent {!r}; known: {}'.format(
        name, ', '.join(sorted(AGENTS))))
