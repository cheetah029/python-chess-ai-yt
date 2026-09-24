"""Per-game and per-position metrics for LGREF ablation runs.

The project brief lists twelve metrics. They split cleanly by what they
need, and the split is what makes the sweep affordable:

  STRUCTURAL — properties of the RULES, readable from any game however
  it was played. Legal branching factor, rule-usage frequency, reachable
  squares, attack-map coverage, repeated-state frequency, game length,
  draw/degeneracy rate. Cheap random playouts measure these perfectly
  well; a stronger agent adds cost without adding information, because
  the quantity being measured is a property of the position, not of the
  player.

  OUTCOME — need skilled play to mean anything. Win/loss/draw by side,
  per-rule outcome sensitivity, policy-effective branching, value swing.
  A random player's win rate says nothing about whether a rule favours
  White.

Everything here is a pure function of a position or a finished game, so
each is testable on a hand-constructed board whose answer can be checked
by hand — which the brief requires of every metric function.

Nothing here interprets a value. A rule that lengthens games produces a
larger `total_turns`; whether that is good depends on the design
objective, and that judgement belongs in Phase 5, not here.
"""

import collections
import math


ROWS = COLS = 8


# ---- position-level (structural) ----------------------------------------

def legal_branching_factor(engine):
    """Number of fully-specified legal turns available to the mover.

    The engine enumerates each (move, jump_choice, promo_choice)
    combination as a separate Turn, so this counts decisions actually
    facing the player, not distinct destination squares.
    """
    return len(engine.get_all_legal_turns())


def reachable_squares(engine, color):
    """Distinct destination squares `color`'s pieces can move to.

    Distinct SQUARES, not turns: several turns may share a destination
    (a promotion offers one per form), and this measures spatial reach
    rather than decision count. Board-level mobility, so it is affected
    by the rules under ablation rather than by any policy.
    """
    saved_player = engine.current_player
    engine.current_player = color
    try:
        squares = set()
        for turn in engine.get_all_legal_turns():
            if turn.to_sq is not None:
                squares.add(turn.to_sq)
        return len(squares)
    finally:
        engine.current_player = saved_player


def attack_map_coverage(board, color):
    """Squares threatened by `color`, via the board's own threat map.

    Uses Board.update_threat_squares rather than a reimplementation, so
    the metric cannot drift from the rules it is measuring. Bishops are
    included here: they threaten reactively, and excluding them would
    bake in a judgement about which threats "count".
    """
    board.update_threat_squares()
    covered = set()
    for row in range(ROWS):
        for col in range(COLS):
            piece = board.squares[row][col].piece
            if piece is None or piece.color != color:
                continue
            for square in getattr(piece, 'threat_squares', []) or []:
                covered.add((square.row, square.col))
    return len(covered)


def position_metrics(engine):
    """Structural metrics for the current position, as one row."""
    board = engine.board
    mover = engine.current_player
    opponent = 'black' if mover == 'white' else 'white'
    return {
        'turn_number': engine.turn_number,
        'player': mover,
        'legal_branching': legal_branching_factor(engine),
        'reachable_squares_mover': reachable_squares(engine, mover),
        'reachable_squares_opponent': reachable_squares(engine, opponent),
        'attack_coverage_mover': attack_map_coverage(board, mover),
        'attack_coverage_opponent': attack_map_coverage(board, opponent),
        'royal_distance': board.get_royal_distance(),
        'tiny_endgame_active': bool(board.tiny_endgame_active),
        'action_types': action_types_available(engine),
    }


def action_types_available(engine):
    """How many KINDS of turn the mover may choose between.

    Not how many turns -- how many sorts of thing they are. A rule that
    grants an action type has, as its evidence, that ablating it makes
    that type vanish from the legal set, and a count of turns cannot
    show that: a transformation disappearing among ninety moves moves
    the branching factor by one.
    """
    return len({getattr(turn, 'turn_type', None)
                for turn in engine.get_all_legal_turns()})


#: A score difference at or below this is not a difference. The agent's
#: score is a COUNT of the opponent's legal turns, so one is the
#: smallest step it can express and anything finer is arithmetic noise
#: rather than a distinction the agent is drawing.
POLICY_TOLERANCE = 1.0


def policy_metrics(scores):
    """What the mover's options look like to the agent evaluating them.

    `policy_branching` is the near-optimal action count: how many turns
    score within POLICY_TOLERANCE of the best. Set against
    `legal_branching`, it is the entire distinction between a rule that
    adds CHOICES and one that adds only actions -- the first raises
    this count, the second leaves it flat while the legal count climbs.
    Two strategic functions are defined as exactly that contrast, and
    without this number neither could be told from the other.

    `move_entropy` is the entropy, in nats, of a softmax over the
    scores after STANDARDISING them -- subtract the mean, divide by the
    spread. Standardising is what makes it comparable at all: the raw
    scores are opponent-mobility counts whose scale falls with the
    material on the board, so a softmax at a fixed temperature would
    report a crowded opening and a bare endgame as different policies
    when only the scale had changed.

    It is deliberately NOT the agent's own sampling distribution. That
    agent is deterministic and breaks ties uniformly, so its entropy
    would be the log of the near-optimal count and would carry nothing
    the first number does not already say.

    Decided and lost positions are read as they are meant: an option
    that wins outright is in a class of its own, and options that merely
    differ in how much they lose are not choices worth counting apart.
    """
    scores = list(scores)
    if not scores:
        return {'policy_branching': None, 'move_entropy': None}

    best = max(scores)
    if best == float('inf'):
        near = sum(1 for s in scores if s == float('inf'))
    else:
        near = sum(1 for s in scores
                   if s != float('-inf') and best - s <= POLICY_TOLERANCE)
        near = near or len(scores)
    finite = [s for s in scores if abs(s) != float('inf')]
    return {'policy_branching': near,
            'move_entropy': _standardised_entropy(finite)}


def _standardised_entropy(values):
    """Entropy of a softmax over z-scored values, in nats."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    spread = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    if spread == 0:
        # Nothing to tell the options apart: a flat policy over all of
        # them, whose entropy is the log of how many there are.
        return round(math.log(len(values)), 4)
    weights = [math.exp((v - mean) / spread) for v in values]
    total = sum(weights)
    return round(
        -sum((w / total) * math.log(w / total) for w in weights), 4)


# ---- game-level ----------------------------------------------------------

def rule_usage(game_record):
    """How often each turn TYPE was executed — per-rule usage frequency.

    Turn type is the engine's own name for which rule produced the turn
    ('move', 'boulder', 'manipulation', 'transformation'), so a variant
    with a rule ablated shows a zero here rather than a missing key,
    which keeps the Parquet schema stable across variants.
    """
    counts = collections.Counter()
    for turn in game_record.get('turns', []):
        counts[turn.get('turn_type')] += 1
    return {
        'move': counts.get('move', 0),
        'boulder': counts.get('boulder', 0),
        'manipulation': counts.get('manipulation', 0),
        'transformation': counts.get('transformation', 0),
    }


def repeated_state_frequency(game_record):
    """Fraction of turns that landed on an already-seen state.

    Uses the per-turn `repetition_count` the engine records. Counts
    turns with count >= 2, i.e. the position had occurred before. This
    is the degeneracy signal the repetition rule exists to bound.
    """
    turns = game_record.get('turns', [])
    if not turns:
        return 0.0
    repeats = sum(1 for t in turns if (t.get('repetition_count') or 0) >= 2)
    return repeats / len(turns)


#: Below this, games do not finish and an outcome metric measures the
#: cap rather than the rules. Measured (#204): 0% of games terminate at
#: cap 100, 8% at 200, 52% at 400, 92% at 800, 100% at 1600, with the
#: longest observed game 949 turns.
OUTCOME_SAFE_TURN_CAP = 800


class TurnCapTooLow(ValueError):
    """An outcome metric was requested at a cap that censors most games.

    Raised rather than warned. A win rate computed over mostly-censored
    games is not a noisy estimate of the real one, it is a measurement
    of the cap -- and it looks entirely reasonable in a results table.
    """


def require_outcome_safe_cap(max_turns, floor=OUTCOME_SAFE_TURN_CAP):
    if max_turns < floor:
        raise TurnCapTooLow(
            'turn cap {} is below {}, where most games are censored '
            'rather than decided. This variant has no draw condition, so '
            'a censored game is not a draw and a win rate over them '
            'measures the cap. Use `max_turns: 1000` (base.yaml) for '
            'outcome metrics, or call the structural metrics instead '
            '(issue #204).'.format(max_turns, floor))


def outcome_row(game_record, max_turns):
    """Win/loss/draw and degeneracy for one finished game.

    `turn_cap` is reported separately from a rule-decided draw: a game
    stopped by the cap is CENSORED, not drawn, and collapsing the two
    would silently turn "we ran out of patience" into a property of the
    rules.
    """
    winner = game_record.get('winner')
    total = game_record.get('total_turns', 0)
    capped = bool(game_record.get('turn_cap_reached')) or total >= max_turns
    return {
        'winner': winner,
        'white_win': winner == 'white',
        'black_win': winner == 'black',
        'decisive': winner is not None,
        'turn_cap_reached': capped,
        'draw_or_censored': winner is None,
        'loss_reason': game_record.get('loss_reason'),
        'total_turns': total,
        'total_captures': game_record.get('total_captures', 0),
        'tiny_endgame_activated': bool(
            game_record.get('tiny_endgame_activated')),
        'repetition_blocks': game_record.get('repetition_blocks', 0),
        'endgame_blocks': game_record.get('endgame_blocks', 0),
        'repeated_state_frequency': repeated_state_frequency(game_record),
    }


def game_metrics(game_record, max_turns):
    """One flat row per game: outcome + rule usage."""
    row = outcome_row(game_record, max_turns)
    row['rule_usage'] = rule_usage(game_record)
    return row


# ---- agent-derived (outcome tier) ---------------------------------------

def policy_effective_branching(visits, threshold=0.10):
    """How many moves the agent considered genuinely competitive.

    Counts children whose visit share is at least `threshold` of the
    most-visited child. Legal branching says how many moves EXIST;
    this says how many were worth considering, which is the quantity
    a designer means by "meaningful choice".

    Defined over MCTS visit counts rather than over an evaluation
    function, so it inherits the agent's freedom from hand-written
    positional opinion.
    """
    if not visits:
        return 0
    best = max(visits)
    if best <= 0:
        return 0
    return sum(1 for v in visits if v >= threshold * best)


def value_swing(values_before, values_after):
    """Absolute change in the agent's position assessment across a turn.

    Large swings mark tactically sharp positions. Both arguments are
    root win-rate estimates in [0, 1]; returns None when either is
    missing so a caller can distinguish "no swing" from "not measured".
    """
    if values_before is None or values_after is None:
        return None
    return abs(values_after - values_before)


def move_entropy(visits):
    """Shannon entropy (bits) of the agent's visit distribution.

    0 means the search was certain; higher means it spread effort over
    many comparable moves. Reported in bits so it is comparable across
    positions with different legal-move counts only after normalising —
    which analysis does deliberately, rather than hiding it here.
    """
    import math
    total = sum(visits)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for v in visits:
        if v <= 0:
            continue
        p = v / total
        entropy -= p * math.log(p, 2)
    return entropy
