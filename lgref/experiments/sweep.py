"""Phase 3: measure what each ablation actually does.

Issue #210. Plays each variant with the mobility agent, records one row
per game, and reports the DECISIVE-GAME RATE first.

Why that first. This game has no draw condition -- one win condition and
four loss conditions, none of them a draw -- so a game stopped by the
turn cap is CENSORED, not drawn (#204). A win rate computed over
censored games measures the cap rather than the rules, and it looks
entirely reasonable in a results table. Earlier runs at cap 100 reported
that agents "mostly drew" when in fact not one game in forty had
finished. So a variant whose games stop finishing is reported as such,
rather than contributing a meaningless number.

Raw rows go to Parquet and accumulate; aggregates are derived from them
and never stored in their place.
"""

import collections
import random
import time

from lgref.experiments.metrics import (outcome_row, position_metrics,
                                       require_outcome_safe_cap)
from lgref.experiments.mobility import MobilityPlayer


def _mean(samples, key):
    """Mean of a sampled metric, or None.

    None rather than 0.0 when the key is absent. The first version used
    `.get(key, 0)` against a key that did not exist, so every game
    reported a mean branching factor of 0.0 -- a missing measurement
    wearing the clothes of a real one, which is exactly what would have
    reached a results table unnoticed.
    """
    values = [s[key] for s in samples if key in s and s[key] is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def play_one(variant, seed, max_turns, sample_every=10):
    """One self-play game. Returns a row and the sampled positions."""
    from experiments.variants import make_engine

    engine = make_engine(variant, max_turns=max_turns)
    white = MobilityPlayer(rng=random.Random(seed * 2 + 1))
    black = MobilityPlayer(rng=random.Random(seed * 2 + 2))

    samples, captures, started = [], 0, time.time()
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        if sample_every and engine.turn_number % sample_every == 0:
            try:
                samples.append(position_metrics(engine))
            except Exception:                      # pragma: no cover
                pass
        agent = white if engine.current_player == 'white' else black
        engine.execute_turn(agent.choose_turn(turns, engine))

    record = {
        'winner': engine.winner,
        'total_turns': engine.turn_number,
        'turn_cap_reached': engine.winner is None,
    }
    row = outcome_row(record, max_turns)
    row.update({
        'variant': variant,
        'seed': seed,
        'wall_clock_s': round(time.time() - started, 3),
        'sampled_positions': len(samples),
        'mean_branching': _mean(samples, 'legal_branching'),
        'mean_reachable_mover': _mean(samples, 'reachable_squares_mover'),
        'mean_attack_coverage': _mean(samples, 'attack_coverage_mover'),
        'tiny_endgame_seen': any(
            s.get('tiny_endgame_active') for s in samples) or None,
    })
    return row, samples


def run_variant(variant, seeds, games, max_turns, sample_every=10,
                progress=None):
    rows = []
    for seed in seeds:
        for game in range(games):
            row, _ = play_one(variant, seed * 1000 + game, max_turns,
                              sample_every)
            rows.append(row)
            if progress:
                progress(variant, len(rows), len(seeds) * games, row)
    return rows


def decisive_report(rows):
    """Decisive rate per variant -- the gate on the whole sweep.

    Reported before any win rate, because a win rate is only meaningful
    among games that finished.
    """
    by_variant = collections.defaultdict(list)
    for row in rows:
        by_variant[row['variant']].append(row)

    out = []
    for variant in sorted(by_variant):
        got = by_variant[variant]
        decisive = [r for r in got if r['decisive']]
        rate = len(decisive) / len(got)
        lengths = [r['total_turns'] for r in decisive]
        out.append({
            'variant': variant,
            'games': len(got),
            'decisive_rate': round(rate, 3),
            'censored': len(got) - len(decisive),
            'mean_turns': round(sum(lengths) / len(lengths), 1)
            if lengths else None,
            'white_wins': sum(1 for r in decisive if r['white_win']),
            'black_wins': sum(1 for r in decisive if r['black_win']),
            'usable': rate >= MIN_DECISIVE_RATE,
        })
    return out


#: Below this, a variant's outcome metrics are not reported as win rates.
#: Not a tuning knob: with no draw condition, a censored game carries no
#: outcome, so a win rate over mostly-censored games is a statement about
#: the turn cap wearing a results table's clothes.
MIN_DECISIVE_RATE = 0.8


def format_decisive(report):
    lines = ['{:<24} {:>6} {:>10} {:>9} {:>10} {:>7} {:>7}  {}'.format(
        'variant', 'games', 'decisive', 'censored', 'mean turns',
        'white', 'black', 'usable?')]
    lines.append('-' * 92)
    for entry in report:
        lines.append(
            '{:<24} {:>6} {:>9.0%} {:>9} {:>10} {:>7} {:>7}  {}'.format(
                entry['variant'], entry['games'], entry['decisive_rate'],
                entry['censored'], entry['mean_turns'] or '-',
                entry['white_wins'], entry['black_wins'],
                'yes' if entry['usable'] else 'NO — outcome metrics '
                'would measure the turn cap'))
    return '\n'.join(lines)


def require_usable(report):
    """Names the variants whose outcome metrics must not be reported."""
    return [e['variant'] for e in report if not e['usable']]
