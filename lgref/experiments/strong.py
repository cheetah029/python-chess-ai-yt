"""A player built from what was MEASURED about this game, not from how it
plays. Every design choice below cites an agent-free number.

WHY THE EXISTING AGENTS ARE WEAK. Four measurements, none of which
involves judging anyone's gameplay:

  COPYING DOMINATED THE SEARCH.  `deepcopy` was 90% of a node: 0.985 ms
      against 0.074 ms of move generation, and 9.27 ms in a midgame
      position. Fixed in `fastcopy` (6-8x), which is why this agent can
      afford to search at all.

  THE BRANCHING IS INFLATED BY INTERCHANGEABLE MOVES.  In sampled
      midgame positions, averaging 100 legal turns, the bishop supplies
      42.3% of them while being 24.5% of the material -- and 0.0% of
      bishop moves are captures, because the bishop has no direct attack
      (RULEBOOK.md). So two fifths of the search's width is "teleport to
      one of ~40 safe empty squares", options that are mostly
      interchangeable and never tactical. Meanwhile the queen, the only
      piece with Manipulation, supplies 8.1% of moves against 17.9% of
      material -- 0.4x its share. An undirected search spends its budget
      in inverse proportion to where the game is decided.

  RANDOM ROLLOUTS CARRY ALMOST NO SIGNAL.  Random games run a median 308
      plies, so a rollout from the midgame is hundreds of plies of noise
      before any outcome. At 800 simulations over 56 root moves each
      child gets 14 rollouts, whose standard error (0.134) exceeds the
      observed spread between root moves (0.139). The estimate is noise,
      and no amount of tree policy fixes a noisy estimator.

  THERE IS NO SHALLOW TACTICAL TARGET.  Winning requires capturing BOTH
      royals, so exact one-ply search over 56 midgame moves finds 0 wins
      and 0 losses. A tactics layer keyed on the win condition has
      nothing to fire on, which is why `tactics.py` is inert here.

WHAT THIS AGENT DOES ABOUT EACH. Alpha-beta to a fixed depth, because
exhaustive-to-depth cannot miss a line inside its horizon and the
branching is far too wide for sampling to cover. Captures are searched
first and extended (quiescence), because material change is the only
irreversible, shallow, decidable event this game offers. And the
bishop's interchangeable teleports are ABSTRACTED to a sample, turning
two fifths of the width into a few representatives.

THE ONE PRIOR, DECLARED. The leaf evaluation counts material. That IS a
researcher-supplied opinion and it is the thing `minimax.py` was written
to avoid, for a good reason: an evaluation that correlates with a rule
being ablated makes the agent play better under that rule and the study
measures the evaluation. So:

  * This agent is for PLAYING -- a human-testable opponent, and a
    stronger reference for measuring other agents. It must NOT be the
    instrument in a rule-ablation sweep. `minimax.py` and the
    rollout-only MCTS remain the unbiased-but-weak instruments.
  * The weights are uniform (every non-royal piece counts 1, royals
    count more because losing both ends the game). No per-piece values
    are tuned, so there is no table of opinions, only the claim that
    captures matter -- which is the win condition's own currency.
  * The method that produced a validated evaluation elsewhere --
    discover + validate against exact play -- scored 92.0% optimal
    against a 32.1% baseline on m,n,k. That pipeline is the principled
    route; it cannot be run here because Royal Chess has no solvable
    region (games run ~63 plies even in thin endgames, and a node costs
    1.1 ms). Until it can, material is a stated prior, not a finding.
"""

import random


#: Royals count more than other pieces because the game ENDS when both
#: of a player's royals are gone (RULEBOOK.md, Objective) -- that is the
#: win condition, not a valuation. Everything else counts 1, so no
#: per-piece opinion is encoded.
ROYAL_WEIGHT = 6.0
PIECE_WEIGHT = 1.0

#: How many of a piece's interchangeable moves to keep. The bishop
#: supplies 42.3% of legal turns and 0.0% of captures, so most of its
#: options differ only in which empty square it lands on. Keeping a
#: sample costs a little completeness and buys a lot of depth.
TELEPORT_SAMPLE = 6


def material(engine, perspective):
    """Material difference from `perspective`, royals weighted.

    Counts only. No per-piece values, so this encodes "captures move you
    toward the win condition" and nothing finer.
    """
    total = 0.0
    board = engine.board
    for row in range(len(board.squares)):
        for col in range(len(board.squares[row])):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            colour = getattr(piece, 'color', None)
            if colour not in ('white', 'black'):
                continue           # the boulder belongs to neither side
            weight = (ROYAL_WEIGHT if getattr(piece, 'is_royal', False)
                      else PIECE_WEIGHT)
            total += weight if colour == perspective else -weight
    return total


def abstract_turns(turns, rng, sample=TELEPORT_SAMPLE):
    """Keep every capture, and a SAMPLE of each piece's quiet moves.

    MEASURED, not guessed: the bishop contributes 42.3% of legal turns
    and none of them are captures, so the search was spending two fifths
    of its width distinguishing teleport destinations. Captures and
    actions are always kept, because those are the turns that change
    material or capability.

    This is an abstraction, so it is lossy -- the best quiet move may be
    dropped. It is applied to EVERY piece uniformly rather than to the
    bishop by name, so the agent carries no opinion about which piece
    matters; the bishop simply benefits most because it has the most
    interchangeable moves.
    """
    keep = []
    quiet = {}
    for turn in turns:
        if getattr(turn, 'is_capture', False) or \
                turn.turn_type in ('transformation', 'manipulation'):
            keep.append(turn)
            continue
        name = getattr(turn.piece, 'name', None) or turn.turn_type
        quiet.setdefault(str(name), []).append(turn)
    for _name, group in sorted(quiet.items()):
        if len(group) <= sample:
            keep.extend(group)
        else:
            keep.extend(rng.sample(group, sample))
    return keep or list(turns)


class StrongPlayer:
    """Alpha-beta with a material leaf, quiescence, and move abstraction.

    Args:
        depth: plies of full-width (post-abstraction) search.
        quiescence: extra plies searched through CAPTURES ONLY, so a
            material swing is never evaluated mid-exchange. This is what
            removes the "gives a piece away" class of mistake, and it is
            cheap because captures are a small fraction of turns.
        sample: quiet moves kept per piece (see `abstract_turns`).
    """

    def __init__(self, depth=2, quiescence=2, sample=TELEPORT_SAMPLE,
                 rng=None):
        self.depth = depth
        self.quiescence = quiescence
        self.sample = sample
        self.rng = rng or random.Random()
        self.nodes = 0

    def choose_turn(self, turns, engine=None):
        from lgref.experiments.fastcopy import clone_with_turns

        if engine is None or len(turns) == 1:
            return turns[0] if turns else None
        me = engine.current_player
        self.nodes = 0
        candidates = abstract_turns(turns, self.rng, self.sample)
        # Captures first: a cutoff found early prunes the most.
        candidates.sort(key=lambda t: not getattr(t, 'is_capture', False))
        best = None
        best_value = float('-inf')
        alpha = float('-inf')
        for turn in candidates:
            index = turns.index(turn)
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[index])
            value = -self._search(sim, self.depth - 1, -float('inf'),
                                  -alpha, me, flip=True)
            if value > best_value:
                best_value, best = value, turn
            alpha = max(alpha, value)
        return best if best is not None else turns[0]

    def _search(self, engine, depth, alpha, beta, me, flip):
        from lgref.experiments.fastcopy import clone_with_turns

        self.nodes += 1
        if engine.is_game_over():
            return self._terminal(engine, me, flip)
        turns = engine.get_all_legal_turns()
        if not turns:
            # No legal turn is a LOSS for the player to move
            # (RULEBOOK.md, No Legal Moves Loss) -- decided by the rules,
            # not guessed.
            sign = -1.0 if flip else 1.0
            return sign * -1000.0 if engine.current_player != me \
                else sign * 1000.0
        if depth <= 0:
            return self._quiesce(engine, self.quiescence, alpha, beta, me,
                                 flip)
        candidates = abstract_turns(turns, self.rng, self.sample)
        candidates.sort(key=lambda t: not getattr(t, 'is_capture', False))
        value = float('-inf')
        for turn in candidates:
            index = turns.index(turn)
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[index])
            value = max(value, -self._search(sim, depth - 1, -beta, -alpha,
                                             me, not flip))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    def _quiesce(self, engine, depth, alpha, beta, me, flip):
        """Search CAPTURES ONLY, so no leaf is scored mid-exchange.

        Without this, a search that stops one ply before a recapture
        reads a position as a piece up when it is level -- which is the
        mechanism behind most of what looks like a blunder.
        """
        from lgref.experiments.fastcopy import clone_with_turns

        sign = -1.0 if flip else 1.0
        standing = sign * material(engine, me)
        if depth <= 0 or engine.is_game_over():
            return standing
        turns = engine.get_all_legal_turns()
        captures = [t for t in turns if getattr(t, 'is_capture', False)]
        if not captures:
            return standing
        value = standing            # standing pat: captures are optional
        alpha = max(alpha, value)
        for turn in captures:
            index = turns.index(turn)
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[index])
            self.nodes += 1
            value = max(value, -self._quiesce(sim, depth - 1, -beta,
                                              -alpha, me, not flip))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    def _terminal(self, engine, me, flip):
        sign = -1.0 if flip else 1.0
        if engine.winner is None:
            return 0.0
        return sign * (1000.0 if engine.winner == me else -1000.0)
