"""Per-variant well-formedness gate (issue #168).

Before any variant enters a training run, random playouts must show it
is a playable, terminating game (feedback item #6 on the LGMEF plan:
an ablation can silently produce a degenerate or non-terminating game,
which would poison the MCI comparison). This module runs N random
playouts of a named variant and checks:

  - every non-terminal position offers at least one legal turn
    (an empty turn list without a winner is recorded as a
    'dead_position' anomaly — expected occasionally ONLY for
    no_queen_manipulation, where the loss check still uses full rules;
    see GameEngine.enable_manipulation),
  - the game terminates within the turn cap or by a rule outcome,
  - both kings survive until a 'royals_captured' outcome,
  - ablated mechanics never fire (no boulder turns in no_boulder, no
    manipulation turns in no_queen_manipulation, no tiny-endgame
    activation in no_tiny_endgame).

Pure engine + random.Random — no torch, no pygame, fast enough for a
pre-run gate on Kaggle or locally.
"""

import random

from experiments.variants import get_variant, make_engine


def _royals_present(board):
    """Both sides retain at least one ROYAL piece (king or royal
    queen). NOTE: in Royal Chess a king can legitimately be captured
    mid-game while the royal queen survives — the loss condition is
    capturing ALL of a side's royals, so the invariant is per-side
    royal count >= 1, not king presence."""
    royals = {'white': 0, 'black': 0}
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece and getattr(piece, 'is_royal', False) \
                    and piece.color in royals:
                royals[piece.color] += 1
    return royals['white'] >= 1 and royals['black'] >= 1


def check_variant(name, n_games=20, max_turns=300, seed=0):
    """Run random playouts of `name` and return a report dict.

    Report: {variant, n_games, ok, anomalies: [str], games: [per-game
    dicts with winner/loss_reason/turns/branching]}. `ok` is True iff
    no anomaly was recorded.
    """
    spec = get_variant(name)
    rng = random.Random(seed)
    anomalies = []
    games = []

    for g in range(n_games):
        engine = make_engine(name, max_turns=max_turns)
        branching = []
        turn_types = {}
        dead_position = False

        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                dead_position = True
                break
            branching.append(len(turns))
            turn = rng.choice(turns)
            turn_types[turn.turn_type] = turn_types.get(turn.turn_type, 0) + 1
            engine.execute_turn(turn)

        record = engine.get_game_record()

        if dead_position and engine.winner is None:
            if name == 'no_queen_manipulation':
                # Known semantics: only-manipulation-turns positions
                # surface as empty turn lists here. Count, don't fail.
                pass
            else:
                anomalies.append(
                    f'game {g}: dead position (no legal turns, no '
                    f'winner) at turn {engine.turn_number}')
        if engine.winner and engine.loss_reason == 'royals_captured':
            pass  # all royals captured IS the outcome; nothing to check after
        elif not _royals_present(engine.board):
            anomalies.append(
                f'game {g}: a side lost all royals without a '
                f'royals_captured outcome '
                f'(loss_reason={engine.loss_reason!r})')

        # Ablated mechanics must never fire.
        if spec.engine_kwargs.get('enable_boulder', True) is False \
                and turn_types.get('boulder'):
            anomalies.append(f'game {g}: boulder turn in no-boulder variant')
        if spec.engine_kwargs.get('enable_manipulation', True) is False \
                and turn_types.get('manipulation'):
            anomalies.append(
                f'game {g}: manipulation turn in no-manipulation variant')
        if spec.engine_kwargs.get('enable_tiny_endgame', True) is False \
                and record.tiny_endgame_activated:
            anomalies.append(
                f'game {g}: tiny endgame activated in no-tiny-endgame variant')

        games.append({
            'winner': engine.winner,
            'loss_reason': engine.loss_reason,
            'total_turns': engine.turn_number,
            'dead_position': dead_position,
            'avg_branching': (sum(branching) / len(branching)) if branching else 0.0,
            'turn_type_counts': turn_types,
        })

    return {
        'variant': name,
        'n_games': n_games,
        'max_turns': max_turns,
        'seed': seed,
        'ok': not anomalies,
        'anomalies': anomalies,
        'games': games,
    }
