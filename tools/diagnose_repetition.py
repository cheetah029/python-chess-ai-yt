#!/usr/bin/env python3
"""Repetition diagnostic — diagnose 'why does this position seem to
repeat without the rule firing?' for any saved game.

Usage:
    python3 tools/diagnose_repetition.py path/to/saved_game.txt

The saved-game file should be in the format produced by the
pause-dialog Copy button (the full save text including the
___VARIANT_SAVE_V1_BEGIN___ / END___ markers).

What this tool does:
  1. Loads the saved game.
  2. Prints state_history (which hashes have been recorded and how
     many times).
  3. Prints the CURRENT state's hash + its current count.
  4. For each legal move, checks `would_cause_repetition` and reports
     which moves are blocked.
  5. If many "visually identical" states aren't matching by hash,
     diagnoses WHY (which fields of the hash entries differ).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import argparse

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()

from game import Game
from engine import GameEngine


def diagnose(save_path):
    with open(save_path) as f:
        text = f.read()
    g = Game()
    ok = g.load_from_text(text)
    if not ok:
        # Maybe it's a FEN.
        ok = g.load_from_fen(text)
    if not ok:
        print(f'ERROR: could not load {save_path} as save or FEN')
        sys.exit(1)

    print('=' * 70)
    print(f'Loaded game state:')
    print(f'  Mode: {g.mode}')
    print(f'  Turn: {g.board.turn_number}  ({g.next_player} to move)')
    print(f'  Winner: {g.winner}')
    print()

    print(f'state_history ({len(g.board.state_history)} distinct hashes):')
    for hsh, count in sorted(
            g.board.state_history.items(),
            key=lambda kv: -kv[1])[:20]:
        # Print summary (hash is a long tuple). Compress to a short
        # signature: number of pieces + turn marker.
        n_pieces = sum(1 for e in hsh
                       if isinstance(e, tuple) and len(e) >= 3
                       and e[2] in ('king', 'queen', 'rook', 'bishop',
                                    'knight', 'pawn'))
        turn_marker = next(
            (e[1] for e in hsh if isinstance(e, tuple) and len(e) > 1
             and e[0] == 'turn'), '?')
        print(f'  count={count:3}  pieces={n_pieces:2}  turn={turn_marker}'
              f'  hash[..20]={str(hash(hsh))[:14]}')
    print()

    current_hash = g.board.get_state_hash(g.next_player)
    print(f'Current state hash count: '
          f'{g.board.state_history.get(current_hash, 0)}')
    print(f'  hash signature: {hash(current_hash):020}')
    print()

    # Check which legal moves are blocked by repetition.
    engine = GameEngine(g.board)
    engine.current_player = g.next_player
    engine.turn_number = g.board.turn_number
    engine._repetition_blocks = 0
    all_turns = engine.get_all_legal_turns()
    print(f'Engine legal turns: {len(all_turns)}')
    print(f'Repetition blocks during enumeration: '
          f'{engine._repetition_blocks}')
    print()

    # Highlight: if repetition_blocks is 0 yet current_hash count is
    # already 2, the rule SHOULD fire on next moves but isn't. That's
    # the bug.
    if g.board.state_history.get(current_hash, 0) >= 2 \
            and engine._repetition_blocks == 0:
        print('!!!  WARNING: current state hash count >= 2, but no moves')
        print('!!!  were blocked by repetition during enumeration. This')
        print('!!!  is the bug pattern. Investigating which legal moves')
        print('!!!  would actually loop back to a recorded state...')
        print()
        for turn in all_turns[:30]:
            # For each move-type turn, simulate via
            # would_cause_repetition with verbose tracing.
            if turn.turn_type != 'move':
                continue
            piece = g.board.squares[turn.from_sq[0]][turn.from_sq[1]].piece
            if piece is None:
                continue
            from move import Move
            from square import Square
            mv = Move(Square(*turn.from_sq), Square(*turn.to_sq))
            would_block = g.board.would_cause_repetition(
                piece, mv, g.next_player)
            print(f'  {turn.from_sq} -> {turn.to_sq} '
                  f'({piece.color} {piece.name}): blocked={would_block}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('save_path', help='path to saved-game file')
    args = p.parse_args()
    diagnose(args.save_path)


if __name__ == '__main__':
    main()
