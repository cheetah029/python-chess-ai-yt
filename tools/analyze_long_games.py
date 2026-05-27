#!/usr/bin/env python3
"""Analyze how very-long games (>1000 turns) unfold.

Loads a specified network checkpoint (which characterises the AI's
playing strength at that point in training), runs self-play games up
to a high turn cap, and for any game that exceeds the long-game
threshold logs detailed per-turn statistics so we can see what's
happening at the slow-burn endgame stages.

Usage examples:
    # Use early-iteration checkpoint (random-ish play) to find long games.
    python3 tools/analyze_long_games.py \\
        --checkpoint models/variant_freeze_v3/model_iter_0002.pt \\
        --num-games 30 --max-turns 2000 --long-threshold 1000

    # Snapshot the position at turn 1000 of any qualifying game.
    python3 tools/analyze_long_games.py \\
        --checkpoint models/variant_freeze_v3/model_iter_0001.pt \\
        --num-games 50 --max-turns 1500 --long-threshold 1000 \\
        --snapshot-turn 1000

Output:
    For each long game found, prints a per-game summary:
      - Game length, winner, loss reason.
      - Material counts at the snapshot turn (default: 1000).
      - Loss-reason category distribution at end.
    The board snapshot at the requested turn is also rendered to
    stdout as a piece-character grid (printable, no pygame required).
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Stub pygame so this script runs in any environment.
import importlib
import types

class _Stub:
    def __getattr__(self, n): return self
    def __call__(self, *a, **k): return self
sys.modules.setdefault('pygame', _Stub())
sys.modules.setdefault('pygame.gfxdraw', _Stub())

from board import Board
from engine import GameEngine
from network import ValueNetwork
from trainer import NeuralPlayer
from piece import King, Queen, Rook, Bishop, Knight, Pawn, Boulder


_PIECE_CHAR = {
    'pawn':   'P',
    'rook':   'R',
    'knight': 'N',
    'bishop': 'B',
    'queen':  'Q',
    'king':   'K',
    'boulder': '#',
}


def render_board(board):
    """Render the board as an 8-row text grid. Uppercase = white pieces,
    lowercase = black pieces, '#' = boulder, '.' = empty."""
    rows = []
    rows.append('   ' + ' '.join('abcdefgh'))
    for r in range(8):
        row_cells = []
        for c in range(8):
            piece = board.squares[r][c].piece
            if piece is None:
                row_cells.append('.')
            elif isinstance(piece, Boulder):
                row_cells.append('#')
            else:
                ch = _PIECE_CHAR.get(piece.name, '?')
                if piece.color == 'black':
                    ch = ch.lower()
                row_cells.append(ch)
        rank_label = str(8 - r)
        rows.append(f' {rank_label} ' + ' '.join(row_cells))
    return '\n'.join(rows)


def count_material(board):
    """Count pieces by side / type."""
    counts = {'white': {}, 'black': {}, 'boulder': 0}
    for r in range(8):
        for c in range(8):
            piece = board.squares[r][c].piece
            if piece is None:
                continue
            if isinstance(piece, Boulder):
                counts['boulder'] += 1
                continue
            counts[piece.color][piece.name] = counts[piece.color].get(piece.name, 0) + 1
    return counts


def fmt_material(counts):
    def fmt_side(d):
        return ' '.join(f'{_PIECE_CHAR.get(k, k)}={v}' for k, v in sorted(d.items()))
    return f"W: {fmt_side(counts['white'])} | B: {fmt_side(counts['black'])} | boulder={counts['boulder']}"


def play_one_game(network, max_turns, snapshot_turn, manipulation_mode='freeze',
                  epsilon=0.0):
    """Play a single self-play game; return a record dict including
    snapshots at the configured turn (if reached)."""
    engine = GameEngine(max_turns=max_turns, manipulation_mode=manipulation_mode)
    player = NeuralPlayer(network, device='cpu', epsilon=epsilon)

    snapshot = None
    while engine.winner is None and engine.turn_number < max_turns:
        if engine.turn_number == snapshot_turn and snapshot is None:
            snapshot = {
                'turn': engine.turn_number,
                'next_player': engine.current_player,
                'board_text': render_board(engine.board),
                'material': count_material(engine.board),
            }

        turns = engine.get_all_legal_turns()
        if not turns:
            break
        turn = player.choose_turn(turns, engine)

        jump_choice = None
        if turn.jump_capture_targets:
            jump_choice = player.choose_jump_capture(turn.jump_capture_targets)
        promo_choice = None
        if turn.promotion_options:
            promo_choice = player.choose_promotion(turn.promotion_options)

        engine.execute_turn(turn, jump_choice, promo_choice)

    return {
        'total_turns': engine.turn_number,
        'winner': engine.winner,
        'loss_reason': engine.loss_reason,
        'snapshot': snapshot,
        'final_material': count_material(engine.board),
        'final_board_text': render_board(engine.board),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True,
                        help='Path to .pt network checkpoint to use as both players.')
    parser.add_argument('--num-games', type=int, default=20)
    parser.add_argument('--max-turns', type=int, default=2000)
    parser.add_argument('--long-threshold', type=int, default=1000)
    parser.add_argument('--snapshot-turn', type=int, default=1000,
                        help='Capture board snapshot at this turn number.')
    parser.add_argument('--epsilon', type=float, default=0.0,
                        help='Exploration during evaluation. 0 = deterministic.')
    parser.add_argument('--manipulation-mode', default='freeze')
    args = parser.parse_args()

    if not os.path.exists(args.checkpoint):
        print(f'Checkpoint not found: {args.checkpoint}', file=sys.stderr)
        return 1

    print(f'Loading checkpoint: {args.checkpoint}')
    network = ValueNetwork.load(args.checkpoint, device='cpu')

    print(f'Playing {args.num_games} self-play games (max_turns={args.max_turns}, '
          f'snapshot at turn {args.snapshot_turn}, epsilon={args.epsilon})...')
    print()

    long_games = []
    length_buckets = {'<=200': 0, '201-500': 0, '501-1000': 0, '1001+': 0}
    decisive_reasons = {}

    t_start = time.time()
    for i in range(args.num_games):
        game_start = time.time()
        result = play_one_game(
            network, args.max_turns, args.snapshot_turn,
            manipulation_mode=args.manipulation_mode, epsilon=args.epsilon)
        elapsed = time.time() - game_start

        n = result['total_turns']
        if n <= 200: length_buckets['<=200'] += 1
        elif n <= 500: length_buckets['201-500'] += 1
        elif n <= 1000: length_buckets['501-1000'] += 1
        else: length_buckets['1001+'] += 1

        reason = result['loss_reason'] or 'unfinished'
        decisive_reasons[reason] = decisive_reasons.get(reason, 0) + 1

        marker = ' [LONG]' if n >= args.long_threshold else ''
        print(f'  game {i+1:>3}: {n:>4} turns, winner={result["winner"]!s:>5}, '
              f'reason={reason:>20}, took {elapsed:.1f}s{marker}')

        if n >= args.long_threshold:
            long_games.append((i + 1, result))

    total_elapsed = time.time() - t_start
    print()
    print(f'=== Summary ===')
    print(f'Total time: {total_elapsed:.0f}s')
    print(f'Length distribution: {length_buckets}')
    print(f'End reasons:        {decisive_reasons}')
    print(f'Long games (>= {args.long_threshold} turns): {len(long_games)}/{args.num_games}')
    print()

    for game_idx, result in long_games:
        print(f'=== Game #{game_idx} ({result["total_turns"]} turns, '
              f'winner={result["winner"]}, reason={result["loss_reason"]}) ===')
        if result['snapshot']:
            s = result['snapshot']
            print(f'  Snapshot at turn {s["turn"]} (next player: {s["next_player"]})')
            print(f'    Material: {fmt_material(s["material"])}')
            print('    Board:')
            for line in s['board_text'].splitlines():
                print('     ', line)
        print(f'  Final material: {fmt_material(result["final_material"])}')
        print('  Final board:')
        for line in result['final_board_text'].splitlines():
            print('   ', line)
        print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
