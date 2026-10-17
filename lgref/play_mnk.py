"""Play m,n,k against the SAME agent stack that plays the case study.

Why this exists: "the framework is general" has so far rested on
benchmark numbers I produced. A reviewer who can play the agent by hand
on a second game can judge that claim directly -- and on m,n,k the
reviewer's judgement can be checked against EXACT minimax, which is not
possible on Royal Chess. When intuition and my numbers have disagreed
in this project, intuition has generally been right.

Nothing here is specific to either game. The agent is
`bootstrap.run` (TD, optionally TD-leaf) over `features.mnk`, played
through `search.Searcher` -- the same two modules the Royal Chess agent
uses. The only m,n,k-aware code is the drawing and the mouse mapping.

The weights are trained AT STARTUP, from exactly zero, because on this
game that takes a second or two. That is worth seeing: the same learner
that needs 800 games on an 8x8 variant needs a handful on a 4x4 board,
and nobody told it the difference.

    python3 lgref/play_mnk.py
    python3 lgref/play_mnk.py --m 3 --n 3 --k 3 --depth 4
    python3 lgref/play_mnk.py --text          # no window needed

Keys: R restarts, Q quits. Click a cell to play it.
"""

import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lgref.experiments.bootstrap import normalise, run, value
from lgref.experiments.discover import differentials
from lgref.experiments.features import mnk as mnk_features
from lgref.experiments.features import with_presence
from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.search import Searcher

HUMAN, AGENT = 'x', 'o'


# ---------------------------------------------------------------- learning

def train(m, n, k, rounds, per_round, seed, depth, use_td_leaf):
    """TD from zero on this board size. Returns `(evaluate, weights)`."""
    extractor = with_presence(mnk_features)
    scales = {}

    def make_game(variant='full', max_turns=None):
        return MNK(m=m, n=n, k=k)

    def evaluate_with(weights):
        def evaluate(game, perspective):
            raw = differentials(extractor(game), perspective)
            return value(weights, normalise(raw, dict(scales), update=False))
        return evaluate

    def searcher(weights, scale_map):
        return Searcher(evaluate_with(weights), max_depth=depth,
                        budget=2.0, quiescence=0)

    started = time.time()
    history = run(make_game, extractor, rounds=rounds,
                  games_per_round=per_round, alpha=0.08, epsilon=0.25,
                  seed=seed, max_turns=m * n + 2, scales=scales,
                  searcher=searcher if use_td_leaf else None)
    weights = history[-1].weights
    print('trained {0} games from zero in {1:.1f}s, {2} features'.format(
        rounds * per_round, time.time() - started, len(weights)))
    top = sorted(weights.items(), key=lambda kv: -abs(kv[1]))[:5]
    for name, w in top:
        print('   {0:<22} {1:+.3f}'.format(name, w / (scales.get(name) or 1.0)))
    return evaluate_with(weights), weights


def grade(game, chosen):
    """What exact minimax thinks of the move just played.

    The honest reason to show this: it lets the reviewer see when the
    agent's move is actually wrong, rather than taking my word for the
    aggregate rate. On a board this size the truth is computable.
    """
    try:
        best, _value = optimal_moves(game)
    except Exception:
        return ''
    if not best:
        return ''
    if len(best) == len(game.get_all_legal_turns()):
        return ' (any move is fine here)'
    return ' (optimal)' if chosen in best else ' (NOT optimal)'


# ------------------------------------------------------------------- text

def play_text(m, n, k, evaluate, depth):
    def show(game):
        print()
        for row in range(m):
            cells = []
            for col in range(n):
                index = row * n + col
                mark = game.cells[index]
                cells.append(mark.upper() if mark else str(index))
            print('  ' + ' '.join('{0:>3}'.format(c) for c in cells))
        print()

    while True:
        game = MNK(m=m, n=n, k=k)
        while not game.is_game_over():
            show(game)
            if game.current_player == HUMAN:
                legal = game.get_all_legal_turns()
                try:
                    raw = input('your cell (q to quit): ').strip()
                except EOFError:
                    return
                if raw.lower().startswith('q'):
                    return
                if not raw.isdigit() or int(raw) not in legal:
                    print('not a legal cell')
                    continue
                game.execute_turn(int(raw))
            else:
                searcher = Searcher(evaluate, max_depth=depth, budget=5.0,
                                    quiescence=0)
                before = game.copy()
                move = searcher.choose_turn(game.get_all_legal_turns(), game)
                print('agent plays {0}{1}   depth {2}'.format(
                    move, grade(before, move), searcher.depth_reached))
                game.execute_turn(move)
        show(game)
        winner = game.winner
        print('you win' if winner == HUMAN else
              'agent wins' if winner == AGENT else 'draw')
        try:
            again = input('again? [y/N] ').strip().lower()
        except EOFError:
            return
        if not again.startswith('y'):
            return


# ------------------------------------------------------------------ pygame

def play_window(m, n, k, evaluate, depth):
    import pygame

    cell, margin = 96, 56
    width, height = n * cell, m * cell + margin
    pygame.init()
    pygame.display.set_caption('m,n,k  {0}x{1} k={2}  vs the TD agent'
                               .format(m, n, k))
    screen = pygame.display.set_mode((width, height))
    font = pygame.font.SysFont('menlo,dejavusansmono,monospace', 18)
    big = pygame.font.SysFont('menlo,dejavusansmono,monospace', 52)

    board_bg = (247, 246, 243)
    line = (206, 203, 196)
    ink = (34, 33, 31)
    human_ink = (32, 86, 168)
    agent_ink = (176, 58, 46)
    note_ink = (108, 104, 98)

    game = MNK(m=m, n=n, k=k)
    status = 'your move -- you are X'
    thinking = False

    def draw():
        screen.fill(board_bg)
        for row in range(m):
            for col in range(n):
                rect = pygame.Rect(col * cell, row * cell, cell, cell)
                pygame.draw.rect(screen, line, rect, 1)
                mark = game.cells[row * n + col]
                if mark:
                    colour = human_ink if mark == HUMAN else agent_ink
                    glyph = big.render(mark.upper(), True, colour)
                    screen.blit(glyph, glyph.get_rect(center=rect.center))
        pygame.draw.rect(screen, board_bg,
                         pygame.Rect(0, m * cell, width, margin))
        screen.blit(font.render(status, True, ink), (12, m * cell + 10))
        screen.blit(font.render('R restart    Q quit', True, note_ink),
                    (12, m * cell + 32))
        pygame.display.flip()

    def agent_move():
        searcher = Searcher(evaluate, max_depth=depth, budget=5.0,
                            quiescence=0)
        before = game.copy()
        move = searcher.choose_turn(game.get_all_legal_turns(), game)
        game.execute_turn(move)
        return 'agent played {0}{1}'.format(move, grade(before, move))

    def outcome():
        winner = game.winner
        if winner == HUMAN:
            return 'you win'
        if winner == AGENT:
            return 'agent wins'
        return 'draw'

    draw()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_r:
                    game = MNK(m=m, n=n, k=k)
                    status = 'your move -- you are X'
                    draw()
            elif (event.type == pygame.MOUSEBUTTONDOWN and not thinking
                  and not game.is_game_over()
                  and game.current_player == HUMAN):
                x, y = event.pos
                if y >= m * cell:
                    continue
                index = (y // cell) * n + (x // cell)
                if index not in game.get_all_legal_turns():
                    continue
                game.execute_turn(index)
                if game.is_game_over():
                    status = outcome()
                    draw()
                    continue
                # Draw the human's mark before the search blocks, so the
                # window never looks frozen on an unchanged board.
                status = 'thinking...'
                thinking = True
                draw()
                status = agent_move()
                thinking = False
                if game.is_game_over():
                    status = '{0} -- {1}'.format(status, outcome())
                draw()
        pygame.time.wait(16)
    pygame.quit()


# -------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m', type=int, default=4, help='rows')
    parser.add_argument('--n', type=int, default=4, help='columns')
    parser.add_argument('--k', type=int, default=3, help='in a row to win')
    parser.add_argument('--depth', type=int, default=3,
                        help='search depth for the agent')
    parser.add_argument('--rounds', type=int, default=6)
    parser.add_argument('--games', type=int, default=60,
                        help='training games per round')
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--td-leaf', action='store_true',
                        help='train with search in the loop (slower)')
    parser.add_argument('--text', action='store_true',
                        help='play in the terminal instead of a window')
    args = parser.parse_args()

    print('m,n,k  {0}x{1} k={2}'.format(args.m, args.n, args.k))
    evaluate, _weights = train(args.m, args.n, args.k, args.rounds,
                               args.games, args.seed, args.depth,
                               args.td_leaf)
    if args.text:
        play_text(args.m, args.n, args.k, evaluate, args.depth)
    else:
        play_window(args.m, args.n, args.k, evaluate, args.depth)


if __name__ == '__main__':
    main()
