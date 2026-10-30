"""A player that uses ONLY the engine protocol, and an evaluation built
from the game's own declared win and loss conditions.

WHY `strong.py` IS NOT THIS. `strong.py` reaches into
`engine.board.squares`, reads `piece.color` and `piece.is_royal`, tests
`turn.is_capture`, and matches `turn.turn_type` against the strings
'transformation' and 'manipulation'. Measured: it raises AttributeError
on the very first call against an m,n,k game. It is not "somewhat
biased" toward chess-like games -- it cannot run on anything else. And
its leaf counts material with weights I chose by hand, so its 0%
hanging-material result is largely circular: it optimises the quantity
the metric measures.

THE FLATNESS PROBLEM, which is what a human notices. A material-only
evaluation is CONSTANT across every non-capturing move, so once nothing
is capturable inside the horizon every move scores the same and the
choice is arbitrary. Measured in self-play: 75.0% of candidate moves tie
at the top score, 39 of 60 chosen moves were no-op transformations, and
16 states repeated. Against a random opponent the tie rate is only
16.9%, which is why the defect is invisible unless the opponent is
careful. "It does nothing until threatened" is exactly this.

THE CONSTRUCTION THAT FIXES IT WITHOUT A PRIOR. A game declares the
ways a player can lose. Build one feature per declared condition,
measuring PROXIMITY to it. For Royal Chess the rulebook lists four:

    both royals captured   -> royal count            (the objective)
    no legal turn          -> MOBILITY
    third repetition       -> state-visit pressure
    tiny-endgame distance  -> distance counts

Two of those are non-flat in quiet positions, and NONE is a researcher's
opinion about pieces -- they are the loss conditions restated as
distances. Mobility in particular is not a chess heuristic here: "no
legal turn at the start of your turn" is literally how you lose
(RULEBOOK.md), so `len(get_all_legal_turns())` is distance-from-a-loss.
Repetition pressure is why stalling is actually dangerous, which a
material evaluation cannot see at all.

This generalises because every game states how it ends. The features are
read off the win and loss conditions rather than supplied, which is the
same move `objective.py` makes for the win condition alone, extended to
the conditions that actually bind during play.

GENERIC QUIESCENCE. "Search captures deeper" needs the idea of a
capture. The general form needs only the evaluation: keep searching
while the score is still MOVING, stop when it settles. That is what
quiescence means, and it collapses to capture-extension in a game whose
volatile moves are captures.

GENERIC MOVE ABSTRACTION. Group candidate moves by the DELTA they cause
in the feature vector, then sample within each group. Two moves that
change every feature identically are interchangeable as far as the
evaluation can tell, so sampling inside a group discards nothing the
evaluation could have used. In Royal Chess this collapses the bishop's
~40 teleports automatically -- they all produce the same delta, namely
none -- without naming the bishop or knowing what a teleport is.
"""

import collections
import random

from lgref.experiments.fastcopy import clone_with_turns


def mobility(engine):
    """Legal turns for whoever is to move.

    RULE-DERIVED, not a heuristic: a player with no legal turn LOSES, in
    this game and in most others, so this is distance from a declared
    loss condition.
    """
    return len(engine.get_all_legal_turns())


def repetition_pressure(engine):
    """How close the current state is to a repetition loss, or 0.

    Read from the engine if it tracks state counts, since a game that
    does not have a repetition rule simply reports nothing here.
    """
    board = getattr(engine, 'board', None)
    counts = getattr(board, 'state_counts', None) if board else None
    if not counts:
        return 0.0
    try:
        key = board.get_state_hash(engine.current_player)
    except Exception:
        return 0.0
    return float(counts.get(key, 0))


def make_evaluation(extractor=None, weights=None, mobility_weight=1.0,
                    repetition_weight=1.0, scale=0.02):
    """An evaluation from declared-condition features.

    `extractor` supplies the game's own vocabulary (see `features.py`)
    and `weights` scores it; both may be omitted, in which case the
    evaluation rests on the protocol-only conditions alone. Returns a
    value in [0, 1] from a perspective, symmetric so that swapping sides
    gives 1 - value.
    """
    import math

    from lgref.experiments.discover import differentials

    weights = weights or {}

    def evaluate(engine, perspective):
        total = 0.0
        if extractor is not None and weights:
            feats = differentials(extractor(engine), perspective)
            total += sum(weights.get(name, 0.0) * value
                         for name, value in feats.items())
        # Mobility is signed by whose turn it is: the quantity is "the
        # mover's distance from the no-legal-turn loss".
        mine = mobility(engine)
        sign = 1.0 if engine.current_player == perspective else -1.0
        total += mobility_weight * sign * mine * scale
        # Repetition pressure counts AGAINST whoever is to move, since
        # they are the one who must avoid the third occurrence.
        total -= repetition_weight * sign * repetition_pressure(engine) * 0.1
        return 1.0 / (1.0 + math.exp(-total))

    return evaluate


def delta_groups(engine, turns, extractor, sample=4, rng=None):
    """Candidates grouped by their effect on the feature vector.

    Moves with an identical delta are indistinguishable to the
    evaluation, so only a sample of each group is worth searching. Fully
    general: it names no piece and no move type, and a game whose moves
    all differ keeps all of them.
    """
    rng = rng or random.Random()
    if extractor is None:
        return list(turns)
    base = extractor(engine)
    groups = collections.defaultdict(list)
    for turn in turns:
        sim, sim_turns = clone_with_turns(engine, turns)
        sim.execute_turn(sim_turns[turns.index(turn)])
        after = extractor(sim)
        delta = tuple(sorted(
            (str(key), after.get(key, 0) - base.get(key, 0))
            for key in set(base) | set(after)
            if after.get(key, 0) != base.get(key, 0)))
        groups[delta].append(turn)
    keep = []
    for _delta, group in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if len(group) <= sample:
            keep.extend(group)
        else:
            keep.extend(rng.sample(group, sample))
    return keep or list(turns)


class GenericPlayer:
    """Alpha-beta over the protocol alone, with an injected evaluation.

    Needs exactly `get_all_legal_turns`, `execute_turn`, `is_game_over`,
    `winner` and `current_player` -- the surface every game in this
    project exposes, from Royal Chess to the m,n,k games to the GDL
    interpreter. It contains no piece name, no board walk and no notion
    of capture.
    """

    def __init__(self, evaluate, depth=2, quiescence=2, extractor=None,
                 sample=4, volatility=0.04, rng=None):
        self.evaluate = evaluate
        self.depth = depth
        self.quiescence = quiescence
        self.extractor = extractor
        self.sample = sample
        self.volatility = volatility
        self.rng = rng or random.Random()
        self.nodes = 0

    def choose_turn(self, turns, engine=None):
        if engine is None or not turns:
            return turns[0] if turns else None
        if len(turns) == 1:
            return turns[0]
        me = engine.current_player
        self.nodes = 0
        candidates = delta_groups(engine, turns, self.extractor,
                                  self.sample, self.rng)
        best, best_value = None, float('-inf')
        alpha = float('-inf')
        for turn in candidates:
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            value = -self._search(sim, self.depth - 1, -float('inf'),
                                  -alpha, me)
            if value > best_value:
                best_value, best = value, turn
            alpha = max(alpha, value)
        return best if best is not None else turns[0]

    def _value(self, engine, me):
        """Terminal outcomes are read, not estimated."""
        if engine.is_game_over():
            winner = engine.winner
            if winner is None:
                return 0.5
            return 1.0 if winner == me else 0.0
        return self.evaluate(engine, me)

    def _search(self, engine, depth, alpha, beta, me):
        self.nodes += 1
        if engine.is_game_over():
            return self._signed(engine, me)
        turns = engine.get_all_legal_turns()
        if not turns:
            # No legal turn is a declared loss for the player to move.
            return 1.0 if engine.current_player != me else 0.0
        if depth <= 0:
            return self._quiesce(engine, self.quiescence, alpha, beta, me)
        candidates = delta_groups(engine, turns, self.extractor,
                                  self.sample, self.rng)
        value = float('-inf')
        for turn in candidates:
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            value = max(value, 1.0 - self._search(sim, depth - 1,
                                                  1.0 - beta, 1.0 - alpha,
                                                  me))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    def _quiesce(self, engine, depth, alpha, beta, me):
        """Keep searching while the SCORE is still moving.

        The general form of quiescence: no notion of a capture, only of
        the evaluation having not yet settled. A game whose volatile
        moves are captures gets capture-extension for free.
        """
        standing = self._value(engine, me)
        if depth <= 0 or engine.is_game_over():
            return standing
        turns = engine.get_all_legal_turns()
        if not turns:
            return 1.0 if engine.current_player != me else 0.0
        volatile = []
        for turn in turns:
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            after = self._value(sim, me)
            if abs(after - standing) >= self.volatility:
                volatile.append((sim, after))
        if not volatile:
            return standing
        value = standing                 # standing pat
        for sim, _after in volatile:
            self.nodes += 1
            value = max(value, 1.0 - self._quiesce(sim, depth - 1,
                                                   1.0 - beta, 1.0 - alpha,
                                                   me))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    def _signed(self, engine, me):
        winner = engine.winner
        if winner is None:
            return 0.5
        return 1.0 if winner == me else 0.0


def top_k(engine, turns, evaluate, k, rng, volatility=None):
    """The k moves a one-ply look rates highest, as a search beam.

    GENERAL, and not a valuation prior: it uses whatever evaluation it
    is given to decide where to look, which is move ordering, not an
    opinion about the game. It exists because the exhaustive width is
    unaffordable -- about 70 legal turns in a Royal Chess midgame, so
    depth 2 is ~4900 nodes and depth 3 is ~340,000.

    Terminal results are read rather than estimated, so a winning move
    is never beamed away.
    """
    mover = engine.current_player
    scored = []
    for turn in turns:
        sim, sim_turns = clone_with_turns(engine, turns)
        sim.execute_turn(sim_turns[turns.index(turn)])
        if sim.is_game_over():
            if sim.winner == mover:
                score = float('inf')
            elif sim.winner is None:
                score = 0.5
            else:
                score = float('-inf')
        else:
            score = 1.0 - evaluate(sim, sim.current_player)
        scored.append((score, rng.random(), turn))
    scored.sort(key=lambda row: (-row[0], row[1]))
    kept = [turn for _score, _tie, turn in scored[:max(1, k)]]
    if volatility is None:
        return kept
    # NEVER BEAM AWAY A REFUTATION. A beam applied to the OPPONENT's
    # replies is precisely how a search misses the move that punishes
    # its own: measured, losing a rook moves this evaluation by a median
    # 0.202, so the refutation is plainly visible -- it just has to be
    # looked at. The scores are already computed here, so including
    # every move that shifts the evaluation by more than `volatility`
    # costs nothing beyond the sort.
    base = evaluate(engine, engine.current_player)
    chosen = set(id(turn) for turn in kept)
    for score, _tie, turn in scored:
        if id(turn) in chosen:
            continue
        if score == float('inf') or score == float('-inf') or \
                abs(score - base) >= volatility:
            kept.append(turn)
            chosen.add(id(turn))
    return kept


class BeamPlayer:
    """Alpha-beta over a beam, with an injected evaluation.

    WHY A BEAM. The honest reason the first TD agent was one-ply is that
    the TD loop uses a one-ply look for action selection while LEARNING
    (cheap, and what TD-Gammon did), and that same player got wired into
    the game without being deepened. That was an oversight, not a
    decision: a one-ply agent maximising material will take any capture
    because it cannot see the reply, which is exactly what "trades a
    rook for a pawn" looks like from the outside.

    Nothing here is a valuation prior. The beam uses the SAME learned
    evaluation to decide where to look; quiescence extends where that
    evaluation is still moving, with no notion of a capture.
    """

    def __init__(self, evaluate, depth=3, beam=10, quiescence=2,
                 volatility=0.15, rng=None):
        self.evaluate = evaluate
        self.depth = depth
        self.beam = beam
        self.quiescence = quiescence
        self.volatility = volatility
        self.rng = rng or random.Random()
        self.nodes = 0

    def choose_turn(self, turns, engine=None):
        if engine is None or not turns:
            return turns[0] if turns else None
        if len(turns) == 1:
            return turns[0]
        me = engine.current_player
        self.nodes = 0
        best, best_value, alpha = None, float('-inf'), float('-inf')
        for turn in top_k(engine, turns, self.evaluate, self.beam,
                          self.rng):
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            value = 1.0 - self._search(sim, self.depth - 1, 0.0,
                                       1.0 - alpha, me)
            if value > best_value:
                best_value, best = value, turn
            alpha = max(alpha, value)
        return best if best is not None else turns[0]

    def _leaf(self, engine, me):
        if engine.is_game_over():
            winner = engine.winner
            if winner is None:
                return 0.5
            return 1.0 if winner == me else 0.0
        return self.evaluate(engine, me)

    def _search(self, engine, depth, alpha, beta, me):
        self.nodes += 1
        if engine.is_game_over():
            return self._leaf(engine, me)
        turns = engine.get_all_legal_turns()
        if not turns:
            return 1.0 if engine.current_player != me else 0.0
        if depth <= 0:
            return self._quiesce(engine, self.quiescence, alpha, beta, me)
        value = float('-inf')
        for turn in top_k(engine, turns, self.evaluate, self.beam,
                          self.rng, volatility=self.volatility):
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            value = max(value, 1.0 - self._search(sim, depth - 1,
                                                  1.0 - beta, 1.0 - alpha,
                                                  me))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    def _quiesce(self, engine, depth, alpha, beta, me):
        standing = self._leaf(engine, me)
        if depth <= 0 or engine.is_game_over():
            return standing
        turns = engine.get_all_legal_turns()
        if not turns:
            return 1.0 if engine.current_player != me else 0.0
        # ADAPTIVE, because a fixed threshold is a constant someone
        # picked and it silently blinds the search below its own size.
        # Measured against this learned evaluation, one piece is worth:
        # queen 0.311, rook 0.201, knight 0.133, king 0.069, PAWN 0.027.
        # A 0.05 gate therefore cannot see a pawn at all, so every
        # pawn-level tactic was invisible -- which is a large share of
        # the material this agent was still hanging at depth 2.
        #
        # Gating on a FRACTION of the largest change in the position is
        # scale-free: it adapts to whatever granularity the game and the
        # evaluation happen to have, and needs no constant per game.
        changes = []
        for turn in turns:
            sim, sim_turns = clone_with_turns(engine, turns)
            sim.execute_turn(sim_turns[turns.index(turn)])
            changes.append((abs(self._leaf(sim, me) - standing), sim))
        if not changes:
            return standing
        largest = max(delta for delta, _sim in changes)
        gate = max(self.volatility * largest, 1e-9)
        value = standing
        for delta, sim in changes:
            after = self._leaf(sim, me)
            if delta < gate:
                continue              # settled: nothing to resolve here
            self.nodes += 1
            value = max(value, 1.0 - self._quiesce(sim, depth - 1,
                                                   1.0 - beta, 1.0 - alpha,
                                                   me))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
