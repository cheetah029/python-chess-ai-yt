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

from lgref.experiments.metrics import (advances_no_own_material,
                                       mean_advance, outcome_row,
                                       policy_metrics,
                                       position_metrics, protection_active,
                                       reply_captures, rule_usage,
                                       require_outcome_safe_cap, turn_effects)
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


def _is_sample_turn(turn_number, sample_every):
    """Sample on ALTERNATING parity, so both players are measured.

    `turn_number % sample_every == 0` with an even stride lands on the
    same parity every time, and players alternate by turn number, so
    every sampled position belonged to WHITE. Eight of the eleven
    profile dimensions are read off sampled positions, which made them
    measurements of one player's experience wearing the name of a
    property of the game.

    Worse for the question they were being used to answer: a
    single-sided near-optimal count cannot separate "this rule gives ME
    options" from "this rule stops THEM constraining me", because both
    land on the same side of the average.

    This offsets each sample by the parity of its index -- 0, 11, 20,
    31, 40 -- so the two sides alternate while the spacing stays about
    `sample_every`.
    """
    index = turn_number // sample_every
    return turn_number % sample_every == index % 2


def play_one(variant, seed, max_turns, sample_every=10, agent='mobility'):
    """One self-play game. Returns a row and the sampled positions.

    `agent` is recorded in the row, because the SIGN of an effect can
    belong to the agent rather than to the rule. Removing the neutral
    object raises mean branching under the mobility agent and lowers it
    under random play: that agent minimises the opponent's legal-turn
    count and `mean_branching` counts legal turns, so a rule that hands
    it a cheaper way to suppress mobility measures as suppressing
    mobility (#230).
    """
    from experiments.variants import make_engine

    from lgref.experiments.random_play import build

    engine = make_engine(variant, max_turns=max_turns)
    white = build(agent, random.Random(seed * 2 + 1))
    black = build(agent, random.Random(seed * 2 + 2))

    samples, started = [], time.time()
    effects = collections.Counter()
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        sample = None
        if sample_every and _is_sample_turn(engine.turn_number, sample_every):
            try:
                sample = position_metrics(engine)
            except Exception:                      # pragma: no cover
                sample = None
        # NOT `agent`, which is the parameter naming which kind of
        # player this is. Reassigning it here put a player object into
        # the row's provenance field where the agent's NAME belongs.
        player = white if engine.current_player == 'white' else black
        chosen = player.choose_turn(turns, engine)
        # AFTER the agent has chosen, because the policy metrics are
        # read off the scores it produced while choosing. They cost
        # nothing extra -- the agent already evaluated every root move,
        # and the alternative is a second evaluation of the same turns
        # to learn what it already knew.
        if sample is not None:
            sample.update(policy_metrics(getattr(player, 'last_scores', ())))
            samples.append(sample)
        # BEFORE executing: three of these ask who owns what is about to
        # move and what is about to be taken, and after the turn there
        # is nothing left at the destination to ask.
        for name, happened in turn_effects(engine, chosen).items():
            effects[name] += 1 if happened else 0
        if advances_no_own_material(engine, chosen):
            effects['no_own_advance'] += 1
        engine.execute_turn(chosen)
        # Counted EVERY turn, not at sampled positions. Protection here
        # lasts one opponent turn, and a sampler that looks at one turn
        # in ten reported it as never happening at all.
        if protection_active(engine.board):
            effects['protection_active'] += 1

    # THE ENGINE'S OWN RECORD, not a hand-built stand-in. The stand-in
    # carried four keys; `outcome_row` reads nine, and the five it could
    # not find it filled with `.get(key, 0)`. So captures, repetition
    # blocks, endgame blocks, tiny-endgame activation and repeated-state
    # frequency were reported as ZERO in every game of every sweep --
    # 1440 rows of a constant that looked like a measurement (#221). The
    # engine had all five the whole time.
    record = engine.get_game_record().to_dict()
    record.setdefault('winner', engine.winner)
    record.setdefault('loss_reason', getattr(engine, 'loss_reason', None))
    record['turn_cap_reached'] = engine.winner is None
    row = outcome_row(record, max_turns)
    row.update({
        'variant': variant,
        'seed': seed,
        'agent': agent,
        'wall_clock_s': round(time.time() - started, 3),
        'sampled_positions': len(samples),
        # Recorded so the parity fix cannot silently regress: a run
        # where one of these is zero is measuring one player again.
        'sampled_white': sum(1 for s in samples if s.get('player') == 'white'),
        'sampled_black': sum(1 for s in samples if s.get('player') == 'black'),
        'loss_reason': record['loss_reason'],
        'mean_branching': _mean(samples, 'legal_branching'),
        'mean_reachable_mover': _mean(samples, 'reachable_squares_mover'),
        'mean_attack_coverage': _mean(samples, 'attack_coverage_mover'),
        # The three the ontology named as evidence and the sweep did
        # not record (#216), so five functions were reported as
        # falsifiable against numbers that did not exist.
        'mean_policy_branching': _mean(samples, 'policy_branching'),
        'mean_move_entropy': _mean(samples, 'move_entropy'),
        'mean_action_types': _mean(samples, 'action_types'),
        'mean_denied_squares': _mean(samples, 'denied_squares'),
        'mean_attack_overlap': _mean(samples, 'attack_overlap'),
        'mean_protected_pieces': _mean(samples, 'protected_pieces'),
        'mean_restrained_pieces': _mean(samples, 'restrained_pieces'),
        'mean_armed_responses': _mean(samples, 'armed_responses'),
        'mean_max_same_type': _mean(samples, 'max_same_type'),
        'mean_distinct_types': _mean(samples, 'distinct_types'),
        'mean_foreign_options': _mean(samples, 'foreign_options'),
        'mean_pieces': _mean(samples, 'pieces_on_board'),
        # Options PER PIECE, so a rule that removes material is not
        # mistaken for one that restricts movement.
        'mean_branching_per_piece': _mean(
            [dict(s, ratio=(s['legal_branching'] / s['pieces_on_board']))
             for s in samples if s.get('pieces_on_board')], 'ratio'),
        # THE SAME QUANTITY, SPLIT BY WHETHER THE MOVER HAD THE OPTION.
        # An ablation cannot answer whether a rule widens the acting
        # player's good choices, because removing it also stops the
        # opponent using it. These two compare positions WITHIN one
        # game instead, which holds the opponent's use of the rule
        # fixed.
        'mean_policy_branching_with_foreign': _mean(
            [s for s in samples if s.get('foreign_options')],
            'policy_branching'),
        'mean_policy_branching_without_foreign': _mean(
            [s for s in samples if not s.get('foreign_options')],
            'policy_branching'),
        'mean_objective_distance': _mean(samples, 'royal_distance'),
        # What a turn DID, counted over the game.
        'foreign_turns': effects['foreign'],
        'shared_entity_turns': effects['shared'],
        'mode_change_turns': effects['mode_change'],
        'mode_reentry_turns': effects['mode_reentry'],
        'conversion_turns': effects['conversion'],
        'response_turns': effects['response'],
        'self_removal_turns': effects['self_removal'],
        'protection_active_turns': effects['protection_active'],
        # The cost side of the ontology (#230).
        'no_own_advance_turns': effects['no_own_advance'],
        'exposure_losses': reply_captures(record),
        'mean_advance': mean_advance(record),
        'tiny_endgame_seen': any(
            s.get('tiny_endgame_active') for s in samples) or None,
    })
    # Per-rule usage frequency, which the brief lists and nothing was
    # recording: the engine's own name for which rule produced each
    # executed turn.
    for turn_type, count in rule_usage(record).items():
        row['turns_{}'.format(turn_type)] = count
    return row, samples


def run_variant(variant, seeds, games, max_turns, sample_every=10,
                progress=None, agent='mobility'):
    rows = []
    for seed in seeds:
        for game in range(games):
            row, _ = play_one(variant, seed * 1000 + game, max_turns,
                              sample_every, agent=agent)
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
