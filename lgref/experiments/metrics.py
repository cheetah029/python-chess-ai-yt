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
    }


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
