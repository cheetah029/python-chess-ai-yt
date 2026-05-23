"""Diagnostic: play N random self-play games and report WHY each one ends.

Categorises endings into:
  - win_white / win_black: a side captured both opponent royals (or won via
    a tiny-endgame distance-count loss, repetition loss, or no-legal-moves
    loss — see `loss_reason`).
  - max_turns_cap: hit the turn cap without a winner (the "draw" bucket).
  - in_progress: never reached game-over (should not occur).

For each game also records ending statistics (turn count, non-king material
remaining, pawn count, whether tiny endgame activated, royal distance,
total captures) so we can see WHY draws happen — in particular whether
games even reach the ≤6 non-king range where the tiny endgame rule could
activate.

Usage:
    python3 tools/analyze_random_draws.py [N=50] [max_turns=120]
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
from collections import Counter

from engine import GameEngine
from players import RandomPlayer
from piece import Boulder


def play_one(seed, max_turns, manipulation_mode='freeze'):
    random.seed(seed)
    eng = GameEngine(max_turns=max_turns, manipulation_mode=manipulation_mode)
    p = {'white': RandomPlayer(), 'black': RandomPlayer()}
    while not eng.is_game_over():
        turns = eng.get_all_legal_turns()
        if not turns:
            break  # safety; engine should set a winner via no-legal-moves loss
        turn = p[eng.current_player].choose_turn(turns)
        jc = (p[eng.current_player].choose_jump_capture(turn.jump_capture_targets)
              if turn.jump_capture_targets is not None else None)
        promo = (p[eng.current_player].choose_promotion(turn.promotion_options)
                 if turn.promotion_options is not None else None)
        eng.execute_turn(turn, jc, promo)
    return summarize(eng)


def summarize(eng):
    b = eng.board
    counts = Counter()
    for row in b.squares:
        for sq in row:
            if sq.piece:
                p = sq.piece
                if isinstance(p, Boulder):
                    key = ('neutral', 'boulder', False, False)
                else:
                    key = (p.color, p.name, p.is_royal, p.is_transformed)
                counts[key] += 1
    if eng.winner:
        end = f'win_{eng.winner}'
    elif eng.turn_number >= eng.max_turns:
        end = 'max_turns_cap'
    else:
        end = 'other'

    def by_color(color, predicate):
        return sum(c for (col, name, royal, _t), c in counts.items()
                   if col == color and predicate(name, royal))

    non_king_white = by_color('white', lambda n, r: n != 'king')
    non_king_black = by_color('black', lambda n, r: n != 'king')
    pawns_w = by_color('white', lambda n, r: n == 'pawn')
    pawns_b = by_color('black', lambda n, r: n == 'pawn')
    queens_w = by_color('white', lambda n, r: n == 'queen' or (r and n != 'king'))
    queens_b = by_color('black', lambda n, r: n == 'queen' or (r and n != 'king'))
    # Royals remaining (king + royal-queen-in-any-form)
    royals_w = sum(c for (col, name, royal, _), c in counts.items()
                   if col == 'white' and (name == 'king' or royal))
    royals_b = sum(c for (col, name, royal, _), c in counts.items()
                   if col == 'black' and (name == 'king' or royal))

    return {
        'end': end,
        'turns': eng.turn_number,
        'winner': eng.winner,
        'loss_reason': eng.loss_reason,
        'tiny_endgame_activated': eng.game_record.tiny_endgame_activated,
        'tiny_endgame_activation_turn': eng.game_record.tiny_endgame_activation_turn,
        'total_captures': eng.game_record.total_captures,
        'non_king_total': non_king_white + non_king_black,
        'non_king_w': non_king_white, 'non_king_b': non_king_black,
        'pawns_total': pawns_w + pawns_b,
        'royals_w': royals_w, 'royals_b': royals_b,
        'royal_distance': b.get_royal_distance(),
    }


def report(results, label):
    N = len(results)
    cnt = Counter(r['end'] for r in results)
    print(f"\n=== {label}  (N={N}) ===")
    for k in ('win_white', 'win_black', 'max_turns_cap', 'other'):
        if cnt.get(k, 0):
            print(f"  {k:18s} {cnt[k]:4d}  ({cnt[k]/N:.0%})")
    loss_reasons = Counter(r['loss_reason'] for r in results if r['winner'])
    if loss_reasons:
        print("  decisive-by-reason:", dict(loss_reasons))
    tiny_activated = [r for r in results if r['tiny_endgame_activated']]
    print(f"  tiny_endgame activated in {len(tiny_activated)}/{N} games "
          f"({len(tiny_activated)/N:.0%})")
    if tiny_activated:
        avg_t = sum(r['tiny_endgame_activation_turn'] for r in tiny_activated) / len(tiny_activated)
        print(f"    avg activation turn: {avg_t:.0f}")
    avg_turns = sum(r['turns'] for r in results) / N
    avg_caps = sum(r['total_captures'] for r in results) / N
    avg_nonking = sum(r['non_king_total'] for r in results) / N
    avg_pawns = sum(r['pawns_total'] for r in results) / N
    print(f"  averages: turns={avg_turns:.1f}  captures={avg_caps:.1f}  "
          f"end_non_king={avg_nonking:.1f}  end_pawns={avg_pawns:.1f}")
    draws = [r for r in results if r['end'] == 'max_turns_cap']
    if draws:
        avg_nonking_d = sum(r['non_king_total'] for r in draws) / len(draws)
        avg_pawns_d = sum(r['pawns_total'] for r in draws) / len(draws)
        avg_caps_d = sum(r['total_captures'] for r in draws) / len(draws)
        avg_rd = sum(r['royal_distance'] for r in draws) / len(draws)
        ge6_total = sum(1 for r in draws if r['non_king_total'] > 6)
        le6_total = len(draws) - ge6_total
        print(f"  DRAW snapshot (end positions of max-turn games):")
        print(f"    avg end non-king={avg_nonking_d:.1f}  avg end pawns={avg_pawns_d:.1f}  "
              f"avg captures={avg_caps_d:.1f}  avg royal_dist={avg_rd:.1f}")
        print(f"    draws with >6 non-king at end: {ge6_total}/{len(draws)} "
              f"({ge6_total/len(draws):.0%})")
        print(f"    draws with ≤6 non-king at end: {le6_total}/{len(draws)}")
        # Composition histogram of draw endings (just the non-king-totals bucket)
        buckets = Counter()
        for r in draws:
            nk = r['non_king_total']
            buckets[nk] += 1
        print(f"    non_king_total histogram (drawn games): "
              f"{sorted(buckets.items())}")


if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    for mt in [int(x) for x in (sys.argv[2:] or [120, 500, 1500])]:
        results = [play_one(seed=1000 + i, max_turns=mt) for i in range(N)]
        report(results, f"max_turns={mt}")
