#!/usr/bin/env python3
"""Benchmark a checkpoint by pitting it against RandomPlayer in N games.

Measures absolute strength: how often does this checkpoint beat a
purely-random opponent? Useful for confirming that a checkpoint is
actually better than random play (a stronger floor than relative
checkpoint-vs-checkpoint matchups).

Alternates colors 50/50 across games to factor out first-mover effects.

Example:
    python3 tools/benchmark_checkpoint.py \\
        --checkpoint models/variant_freeze_v3/model_iter_0025.pt \\
        --num-games 30 --max-turns 1500
"""

import argparse
import os
import sys
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class _Stub:
    def __getattr__(self, n): return self
    def __call__(self, *a, **k): return self
sys.modules.setdefault('pygame', _Stub())
sys.modules.setdefault('pygame.gfxdraw', _Stub())

from engine import GameEngine
from network import ValueNetwork
from trainer import NeuralPlayer
from players import RandomPlayer


def play_match(player_white, player_black, max_turns, manipulation_mode='freeze'):
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
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--num-games', type=int, default=20)
    parser.add_argument('--max-turns', type=int, default=1500)
    parser.add_argument('--epsilon', type=float, default=0.0)
    parser.add_argument('--manipulation-mode', default='freeze')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if not os.path.exists(args.checkpoint):
        print(f'Checkpoint not found: {args.checkpoint}', file=sys.stderr)
        return 1

    print(f'Checkpoint: {args.checkpoint}')
    network = ValueNetwork.load(args.checkpoint, device='cpu')
    net_player = NeuralPlayer(network, device='cpu', epsilon=args.epsilon)
    rand_player = RandomPlayer()

    print(f'Playing {args.num_games} games vs RandomPlayer '
          f'(max_turns={args.max_turns}, epsilon={args.epsilon})...')
    print(f"  {'Game':>5}  {'Net as':>7}  {'Winner':>7}  {'Turns':>5}  Elapsed")

    net_wins = rand_wins = draws = 0
    net_white_wins = net_black_wins = 0
    lengths = []
    end_reasons = {}
    t_start = time.time()

    for i in range(args.num_games):
        net_is_white = (i % 2 == 0)
        if net_is_white:
            pw, pb = net_player, rand_player
            net_as = 'white'
        else:
            pw, pb = rand_player, net_player
            net_as = 'black'

        t = time.time()
        winner, turns, reason = play_match(
            pw, pb, args.max_turns, manipulation_mode=args.manipulation_mode)
        elapsed = time.time() - t

        if winner is None:
            draws += 1
            who = 'draw'
        elif (net_is_white and winner == 'white') or (not net_is_white and winner == 'black'):
            net_wins += 1
            if net_is_white: net_white_wins += 1
            else: net_black_wins += 1
            who = 'Net'
        else:
            rand_wins += 1
            who = 'Random'

        lengths.append(turns)
        reason = reason or 'unfinished'
        end_reasons[reason] = end_reasons.get(reason, 0) + 1

        print(f"  {i+1:>5}  {net_as:>7}  {who:>7}  {turns:>5}  {elapsed:.1f}s")

    total = time.time() - t_start
    print()
    print(f'=== Benchmark Results ({args.num_games} games, {total:.0f}s total) ===')
    print(f'  Network wins:  {net_wins}/{args.num_games} ({100*net_wins/args.num_games:.1f}%)')
    print(f'    as white: {net_white_wins}, as black: {net_black_wins}')
    print(f'  Random wins:   {rand_wins}/{args.num_games} ({100*rand_wins/args.num_games:.1f}%)')
    print(f'  Draws:         {draws}/{args.num_games} ({100*draws/args.num_games:.1f}%)')
    print(f'  Game length:   min={min(lengths)}, max={max(lengths)}, '
          f'mean={sum(lengths)/len(lengths):.0f}')
    print(f'  End reasons:   {end_reasons}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
