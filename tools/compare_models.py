#!/usr/bin/env python3
"""Pit two network checkpoints against each other in N self-play games.

Useful for measuring relative strength as training progresses (e.g.,
"is iter 50 actually stronger than iter 25?"). Also useful for picking
a sensible Easy/Medium/Hard difficulty mapping by quantifying
checkpoint-to-checkpoint win rates.

Each game alternates which checkpoint plays white (50/50) to factor out
any first-mover advantage. Results report win rates per checkpoint along
with average game length, distribution, and end-reason breakdown.

Example:
    python3 tools/compare_models.py \\
        --model-a models/variant_freeze_v3/model_iter_0010.pt \\
        --model-b models/variant_freeze_v3/model_iter_0025.pt \\
        --num-games 30 --max-turns 1500
"""

import argparse
import os
import sys
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Stub pygame so this script runs in any environment.
class _Stub:
    def __getattr__(self, n): return self
    def __call__(self, *a, **k): return self
sys.modules.setdefault('pygame', _Stub())
sys.modules.setdefault('pygame.gfxdraw', _Stub())

from engine import GameEngine
from network import ValueNetwork
from trainer import NeuralPlayer


def play_match(player_white, player_black, max_turns, manipulation_mode='freeze'):
    """Play one game with given white/black players. Returns
    (winner, total_turns, loss_reason).
    """
    engine = GameEngine(max_turns=max_turns, manipulation_mode=manipulation_mode)
    while engine.winner is None and engine.turn_number < max_turns:
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        player = player_white if engine.current_player == 'white' else player_black
        turn = player.choose_turn(turns, engine)
        engine.execute_turn(turn)
    return engine.winner, engine.turn_number, engine.loss_reason


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-a', required=True, help='Checkpoint A')
    parser.add_argument('--model-b', required=True, help='Checkpoint B')
    parser.add_argument('--num-games', type=int, default=20)
    parser.add_argument('--max-turns', type=int, default=1500)
    parser.add_argument('--epsilon', type=float, default=0.0,
                        help='Exploration rate (0 = deterministic; >0 lets the '
                             'network mix in random moves for diversity).')
    parser.add_argument('--manipulation-mode', default='freeze')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if not os.path.exists(args.model_a):
        print(f'Model A not found: {args.model_a}', file=sys.stderr)
        return 1
    if not os.path.exists(args.model_b):
        print(f'Model B not found: {args.model_b}', file=sys.stderr)
        return 1

    print(f'Model A: {args.model_a}')
    print(f'Model B: {args.model_b}')
    net_a = ValueNetwork.load(args.model_a, device='cpu')
    net_b = ValueNetwork.load(args.model_b, device='cpu')
    player_a = NeuralPlayer(net_a, device='cpu', epsilon=args.epsilon)
    player_b = NeuralPlayer(net_b, device='cpu', epsilon=args.epsilon)

    print(f'Playing {args.num_games} games (max_turns={args.max_turns}, '
          f'epsilon={args.epsilon})...')
    print(f"  {'Game':>5}  {'A as':>6}  {'Winner':>7}  {'Turns':>5}  {'Reason':>20}  Elapsed")

    a_wins = b_wins = draws = 0
    a_white_wins = a_black_wins = 0
    lengths = []
    end_reasons = {}
    t_start = time.time()

    for i in range(args.num_games):
        # Alternate which model plays white.
        a_is_white = (i % 2 == 0)
        if a_is_white:
            pw, pb = player_a, player_b
            a_as = 'white'
        else:
            pw, pb = player_b, player_a
            a_as = 'black'

        t = time.time()
        winner, turns, reason = play_match(
            pw, pb, args.max_turns, manipulation_mode=args.manipulation_mode)
        elapsed = time.time() - t

        # Map winner color → which model won.
        if winner is None:
            draws += 1
            who = 'draw'
        elif (a_is_white and winner == 'white') or (not a_is_white and winner == 'black'):
            a_wins += 1
            if a_is_white: a_white_wins += 1
            else: a_black_wins += 1
            who = 'A'
        else:
            b_wins += 1
            who = 'B'

        lengths.append(turns)
        reason = reason or 'unfinished'
        end_reasons[reason] = end_reasons.get(reason, 0) + 1

        print(f"  {i+1:>5}  {a_as:>6}  {who:>7}  {turns:>5}  {reason:>20}  {elapsed:.1f}s")

    total = time.time() - t_start
    print()
    print(f'=== Results ({args.num_games} games, {total:.0f}s total) ===')
    print(f'  Model A wins: {a_wins}/{args.num_games} ({100*a_wins/args.num_games:.1f}%)')
    print(f'    as white: {a_white_wins}, as black: {a_black_wins}')
    print(f'  Model B wins: {b_wins}/{args.num_games} ({100*b_wins/args.num_games:.1f}%)')
    print(f'  Draws:        {draws}/{args.num_games} ({100*draws/args.num_games:.1f}%)')
    print(f'  Game length:  min={min(lengths)}, max={max(lengths)}, '
          f'mean={sum(lengths)/len(lengths):.0f}')
    print(f'  End reasons:  {end_reasons}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
