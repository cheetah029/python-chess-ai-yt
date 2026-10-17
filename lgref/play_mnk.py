"""Play m,n,k against the SAME agent stack that plays the case study.

Why this exists: "the framework is general" should not rest only on
benchmark numbers I produced. A reviewer who can play the agent by hand
on a second game can judge that claim directly -- and on these boards
the reviewer's judgement can be checked against EXACT MINIMAX, which is
not possible on an 8x8 variant. Every agent move is annotated
`(optimal)` or `(NOT optimal)` as it is played.

Nothing here is specific to either game. The agent is
`bootstrap.run` (TD, optionally TD-leaf) over `features.mnk` played
through `search.Searcher` -- the same two modules the case study's agent
uses. The only game-aware code is the drawing and the mouse mapping.

Weights are trained AT STARTUP, from exactly zero, and retrained
whenever the board changes. That takes about a second, and the contrast
is worth seeing: the same learner needs 800 games on an 8x8 variant and
a handful here, with nothing told it about the difference.

    python3 lgref/play_mnk.py
    python3 lgref/play_mnk.py --m 5 --n 5 --k 4 --depth 4
    python3 lgref/play_mnk.py --text          # no window needed

In the window: click a cell to play it. The SETUP screen adjusts the
board, who plays each side, and the search depth. Keys: S setup,
R restart, Q quit.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lgref.experiments.bootstrap import normalise, run, value
from lgref.experiments.discover import differentials
from lgref.experiments.features import mnk as mnk_features
from lgref.experiments.features import with_threshold
from lgref.experiments.mnk import MNK, optimal_moves
from lgref.experiments.search import Searcher

FIRST, SECOND = 'x', 'o'

#: The same shape as the case study's mode menu: one catalog, offered
#: independently to each side.
PLAYER_OPTIONS = [
    {'key': 'human', 'label': 'Human'},
    {'key': 'random', 'label': 'Random'},
    # One ply on the learned value. Cheap, and the honest baseline for
    # what the evaluation alone is worth without search.
    {'key': 'td1', 'label': 'TD one-ply'},
    # The learned value behind the shared alpha-beta searcher. This is
    # the agent whose numbers the research reports.
    {'key': 'td', 'label': 'TD + search'},
]

#: What the setup screen's steppers may produce. Raised to 20 on
#: request, so the game can be made genuinely harder than tic-tac-toe
#: -- an 8x8 variant is far more complex than a 4x4 board, and a
#: strength impression formed on nine cells is not worth much.
#:
#: TWO THINGS STOP WORKING AS THE BOARD GROWS, and both degrade rather
#: than break. Exact minimax grading switches itself off above
#: `GRADE_CELL_LIMIT` empty cells, because the solver is exponential.
#: And the branching factor reaches 400 on a 20x20 board, so the search
#: will not finish depth 3 inside its budget -- iterative deepening
#: returns whatever depth it did finish, and the status line reports
#: it rather than implying the configured depth was reached.
#:
#: `k` above both dimensions would make every game a draw by
#: construction, so it is clamped against the board.
SETTING_BOUNDS = {'m': (2, 20), 'n': (2, 20), 'k': (2, 20),
                  'depth': (1, 6)}


def clamp_setting(name, value, m=None, n=None):
    """One stepper click, bounded. Extracted so it can be tested without
    a window, which is also why `k` is clamped against the board here
    rather than in the event loop."""
    low, high = SETTING_BOUNDS[name]
    value = max(low, min(high, value))
    if name == 'k' and m is not None and n is not None:
        value = min(value, max(m, n))
    return value


#: Above this many cells, exact minimax grading is switched off rather
#: than left to stall the window. Derived from the board, not a
#: preference: the solver is exponential in empty cells.
GRADE_CELL_LIMIT = 20


# ---------------------------------------------------------------- learning

class Brain(object):
    """Trains and caches one evaluation per board size.

    Cached because the setup screen lets the board change and retraining
    a size already seen would be wasted; keyed on `(m, n, k)` because
    nothing learned on one board transfers to another -- which is itself
    the point being demonstrated.
    """

    def __init__(self, rounds, games, seed, use_td_leaf, depth,
                 budget=20.0):
        self.rounds = rounds
        self.games = games
        self.seed = seed
        self.use_td_leaf = use_td_leaf
        self.depth = depth
        #: A WALL-CLOCK BUDGET, not a game count. One game is nine plies
        #: on 3x3 and four hundred on 20x20, with branching to match, so
        #: a count that trains in a second on one board takes minutes on
        #: another -- measured at 229s for 20x20 before this existed,
        #: which is not a setup screen anybody would use. Fewer games on
        #: a bigger board is a real cost in strength, and the panel says
        #: how many it managed rather than hiding it.
        self.budget = budget
        self.extractor = with_threshold(mnk_features)
        self._cache = {}
        self.last_report = ''

    def evaluation(self, m, n, k, log=None):
        key = (m, n, k)
        if key in self._cache:
            return self._cache[key]
        scales = {}

        def make_game(variant='full', max_turns=None):
            return MNK(m=m, n=n, k=k)

        def evaluate_with(weights):
            def evaluate(game, perspective):
                raw = differentials(self.extractor(game), perspective)
                return value(weights, normalise(raw, dict(scales),
                                                update=False))
            return evaluate

        def searcher(weights, _scales):
            return Searcher(evaluate_with(weights), max_depth=self.depth,
                            budget=2.0, quiescence=0)

        started = time.time()
        games = self.games
        history = run(make_game, self.extractor, rounds=self.rounds,
                      games_per_round=games, alpha=0.08,
                      epsilon=0.25, seed=self.seed, max_turns=m * n + 2,
                      scales=scales, budget_seconds=self.budget,
                      searcher=searcher if self.use_td_leaf else None)
        weights = history[-1].weights
        elapsed = time.time() - started
        top = sorted(weights.items(), key=lambda kv: -abs(kv[1]))[:5]
        played = sum(1 for _ in history) and history[-1].games
        lines = ['trained {0} games from zero in {1:.1f}s, {2} features'
                 .format(played, elapsed, len(weights))]
        for name, raw in top:
            lines.append('   {0:<24} {1:+.3f}'.format(
                name, raw / (scales.get(name) or 1.0)))
        self.last_report = '\n'.join(lines)
        if log:
            log(self.last_report)
        self._cache[key] = evaluate_with(weights)
        return self._cache[key]


def make_player(kind, evaluate, depth, rng):
    """A callable `(game) -> turn`, or None for a human."""
    if kind == 'human':
        return None
    if kind == 'random':
        return lambda game: rng.choice(game.get_all_legal_turns())
    if kind == 'td1':
        def one_ply(game):
            mover = game.current_player
            best, best_value = None, float('-inf')
            for turn in game.get_all_legal_turns():
                nxt = game.copy()
                nxt.execute_turn(turn)
                if nxt.is_game_over():
                    scored = (1.0 if nxt.winner == mover
                              else 0.5 if nxt.winner is None else 0.0)
                else:
                    scored = 1.0 - evaluate(nxt, nxt.current_player)
                if scored > best_value:
                    best_value, best = scored, turn
            return best
        return one_ply

    def searched(game):
        searcher = Searcher(evaluate, max_depth=depth, budget=5.0,
                            quiescence=0)
        searched.last_depth = searcher.depth_reached
        turn = searcher.choose_turn(game.get_all_legal_turns(), game)
        searched.last_depth = searcher.depth_reached
        return turn
    searched.last_depth = 0
    return searched


def grade(game, chosen):
    """What exact minimax thinks of the move just played.

    Shown next to every agent move so the reviewer can see the agent be
    wrong, rather than taking an aggregate rate on faith.
    """
    empty = sum(1 for c in game.cells if c is None)
    if empty > GRADE_CELL_LIMIT:
        return ''
    try:
        best, _value = optimal_moves(game)
    except Exception:
        return ''
    if not best:
        return ''
    if len(best) == len(game.get_all_legal_turns()):
        return '  (any move is fine)'
    return '  (optimal)' if chosen in best else '  (NOT optimal)'


def winning_line(game):
    """The cells that won, for highlighting. Read from the game's own
    win condition rather than recomputed here."""
    from lgref.experiments.mnk import win_lines

    for line in win_lines(game.m, game.n, game.k):
        first = game.cells[line[0]]
        if first and all(game.cells[i] == first for i in line):
            return list(line)
    return []


# ------------------------------------------------------------------- text

def play_text(m, n, k, brain, depth, sides):
    evaluate = brain.evaluation(m, n, k, log=print)
    import random
    rng = random.Random(0)
    players = {side: make_player(kind, evaluate, depth, rng)
               for side, kind in sides.items()}

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
            agent = players[game.current_player]
            if agent is None:
                legal = game.get_all_legal_turns()
                try:
                    raw = input('{0} to play (q to quit): '.format(
                        game.current_player.upper())).strip()
                except EOFError:
                    return
                if raw.lower().startswith('q'):
                    return
                if not raw.isdigit() or int(raw) not in legal:
                    print('not a legal cell')
                    continue
                game.execute_turn(int(raw))
            else:
                before = game.copy()
                move = agent(game)
                print('{0} plays {1}{2}'.format(
                    game.current_player.upper(), move, grade(before, move)))
                game.execute_turn(move)
        show(game)
        winner = game.winner
        print('{0} wins'.format(winner.upper()) if winner else 'draw')
        try:
            again = input('again? [y/N] ').strip().lower()
        except EOFError:
            return
        if not again.startswith('y'):
            return


# ------------------------------------------------------------------ pygame

PALETTE = {
    'bg': (246, 245, 242),
    'panel': (255, 255, 255),
    'grid': (214, 211, 204),
    'grid_soft': (233, 231, 226),
    'ink': (31, 30, 28),
    'muted': (122, 117, 110),
    'first': (37, 92, 168),
    'second': (176, 58, 46),
    'hover': (236, 240, 247),
    'win': (252, 243, 207),
    'button': (243, 242, 238),
    'button_on': (37, 92, 168),
    'button_edge': (210, 207, 200),
}


def play_window(m, n, k, brain, depth, sides):
    import random

    import pygame

    pygame.init()
    pygame.display.set_caption('m,n,k  --  the general agent')

    state = {'m': m, 'n': n, 'k': k, 'depth': depth,
             'sides': dict(sides), 'screen': 'setup',
             'status': '', 'thinking': False, 'last': None,
             'auto': True}
    rng = random.Random(0)

    PANEL = 132
    MIN_W = 560

    def geometry():
        rows, cols = state['m'], state['n']
        # Fit the board inside a fixed box rather than growing the
        # window, so a 20x20 board still opens on a laptop screen.
        cell = max(16, min(104, int(620 / max(rows, cols))))
        width = max(MIN_W, cols * cell)
        height = rows * cell + PANEL
        return cell, width, height

    cell, width, height = geometry()
    surface = pygame.display.set_mode((width, height))
    fonts = {}

    def font(size, bold=False):
        key = (size, bold)
        if key not in fonts:
            fonts[key] = pygame.font.SysFont(
                'helveticaneue,helvetica,arial,dejavusans', size, bold=bold)
        return fonts[key]

    def resize():
        global_cell, w, h = geometry()
        return global_cell, pygame.display.set_mode((w, h)), w, h

    game = [MNK(m=state['m'], n=state['n'], k=state['k'])]
    evaluate = [None]
    players = [{}]

    def rebuild(log_status=True):
        if log_status:
            state['status'] = 'training from zero...'
            draw()
        evaluate[0] = brain.evaluation(state['m'], state['n'], state['k'])
        players[0] = {side: make_player(kind, evaluate[0], state['depth'],
                                        rng)
                      for side, kind in state['sides'].items()}
        game[0] = MNK(m=state['m'], n=state['n'], k=state['k'])
        state['last'] = None
        state['status'] = describe_turn()

    def describe_turn():
        current = game[0]
        if current.is_game_over():
            winner = current.winner
            return ('{0} wins'.format(winner.upper()) if winner else 'draw')
        kind = state['sides'][current.current_player]
        who = dict((o['key'], o['label']) for o in PLAYER_OPTIONS)[kind]
        return '{0} to play  --  {1}'.format(
            current.current_player.upper(), who)

    # ---- drawing -----------------------------------------------------

    def draw_mark(rect, mark, dim=False):
        pad = int(rect.width * 0.26)
        box = rect.inflate(-2 * pad, -2 * pad)
        colour = PALETTE['first'] if mark == FIRST else PALETTE['second']
        if dim:
            colour = tuple(int(c + (245 - c) * 0.55) for c in colour)
        stroke = max(3, int(rect.width * 0.10))
        if mark == FIRST:
            pygame.draw.line(surface, colour, box.topleft, box.bottomright,
                             stroke)
            pygame.draw.line(surface, colour, box.bottomleft, box.topright,
                             stroke)
        else:
            pygame.draw.ellipse(surface, colour, box, stroke)

    def board_rect(index):
        row, col = divmod(index, state['n'])
        return pygame.Rect(col * cell, row * cell, cell, cell)

    def draw_board():
        current = game[0]
        wins = set(winning_line(current))
        mouse = pygame.mouse.get_pos()
        hovering = None
        if (not current.is_game_over() and not state['thinking']
                and players[0].get(current.current_player) is None
                and mouse[1] < state['m'] * cell):
            candidate = ((mouse[1] // cell) * state['n']
                         + (mouse[0] // cell))
            if candidate in current.get_all_legal_turns():
                hovering = candidate
        for index in range(state['m'] * state['n']):
            rect = board_rect(index)
            if index in wins:
                pygame.draw.rect(surface, PALETTE['win'], rect)
            elif index == hovering:
                pygame.draw.rect(surface, PALETTE['hover'], rect)
            pygame.draw.rect(surface, PALETTE['grid_soft'], rect, 1)
            mark = current.cells[index]
            if mark:
                draw_mark(rect, mark)
            elif index == hovering:
                draw_mark(rect, current.current_player, dim=True)
        board = pygame.Rect(0, 0, state['n'] * cell, state['m'] * cell)
        pygame.draw.rect(surface, PALETTE['grid'], board, 2)
        if state['last'] is not None:
            spot = board_rect(state['last'])
            pygame.draw.circle(surface, PALETTE['muted'],
                               (spot.right - 9, spot.top + 9), 3)

    def button(rect, label, active=False, small=False):
        pygame.draw.rect(surface,
                         PALETTE['button_on'] if active
                         else PALETTE['button'], rect, border_radius=7)
        if not active:
            pygame.draw.rect(surface, PALETTE['button_edge'], rect, 1,
                             border_radius=7)
        glyph = font(13 if small else 14, bold=active).render(
            label, True, (255, 255, 255) if active else PALETTE['ink'])
        surface.blit(glyph, glyph.get_rect(center=rect.center))
        return rect

    def draw_panel():
        top = state['m'] * cell
        pygame.draw.rect(surface, PALETTE['panel'],
                         pygame.Rect(0, top, width, PANEL))
        pygame.draw.line(surface, PALETTE['grid_soft'], (0, top),
                         (width, top))
        surface.blit(font(17, bold=True).render(state['status'], True,
                                                PALETTE['ink']),
                     (16, top + 14))
        detail = '{0}x{1}  k={2}   depth {3}'.format(
            state['m'], state['n'], state['k'], state['depth'])
        surface.blit(font(13).render(detail, True, PALETTE['muted']),
                     (16, top + 40))
        note = state.get('note', '')
        if note:
            surface.blit(font(13).render(note, True, PALETTE['muted']),
                         (16, top + 60))
        hits = []
        hits.append(('setup', button(pygame.Rect(16, top + 88, 76, 28),
                                     'Setup', small=True)))
        hits.append(('restart', button(pygame.Rect(100, top + 88, 76, 28),
                                       'Restart', small=True)))
        surface.blit(font(12).render('S setup   R restart   Q quit', True,
                                     PALETTE['muted']),
                     (190, top + 95))
        return hits

    def stepper(x, y, label, value_text):
        surface.blit(font(13).render(label, True, PALETTE['muted']),
                     (x, y + 7))
        minus = button(pygame.Rect(x + 74, y, 28, 28), '-', small=True)
        box = pygame.Rect(x + 106, y, 44, 28)
        pygame.draw.rect(surface, PALETTE['button'], box, border_radius=7)
        pygame.draw.rect(surface, PALETTE['button_edge'], box, 1,
                         border_radius=7)
        glyph = font(14, bold=True).render(value_text, True, PALETTE['ink'])
        surface.blit(glyph, glyph.get_rect(center=box.center))
        plus = button(pygame.Rect(x + 154, y, 28, 28), '+', small=True)
        return minus, plus

    def draw_setup():
        surface.fill(PALETTE['bg'])
        card = pygame.Rect(20, 20, width - 40, height - 40)
        pygame.draw.rect(surface, PALETTE['panel'], card, border_radius=12)
        pygame.draw.rect(surface, PALETTE['button_edge'], card, 1,
                         border_radius=12)
        surface.blit(font(20, bold=True).render('Setup', True,
                                                PALETTE['ink']),
                     (card.x + 20, card.y + 16))
        surface.blit(font(13).render(
            'the same learner and search as the 8x8 case study', True,
            PALETTE['muted']), (card.x + 20, card.y + 44))

        hits = {}
        y = card.y + 76
        hits['m'] = stepper(card.x + 20, y, 'rows', str(state['m']))
        hits['n'] = stepper(card.x + 20, y + 36, 'columns', str(state['n']))
        hits['k'] = stepper(card.x + 20, y + 72, 'in a row',
                            str(state['k']))
        hits['depth'] = stepper(card.x + 20, y + 108, 'depth',
                                str(state['depth']))

        y2 = y + 152
        hits['sides'] = []
        for offset, side in enumerate((FIRST, SECOND)):
            label = '{0} player'.format(side.upper())
            surface.blit(font(13, bold=True).render(label, True,
                                                    PALETTE['ink']),
                         (card.x + 20, y2 + offset * 62))
            x = card.x + 20
            for option in PLAYER_OPTIONS:
                rect = pygame.Rect(x, y2 + offset * 62 + 20, 104, 28)
                button(rect, option['label'],
                       active=(state['sides'][side] == option['key']),
                       small=True)
                hits['sides'].append((side, option['key'], rect))
                x += 110

        hits['start'] = button(
            pygame.Rect(card.right - 140, card.bottom - 52, 120, 34),
            'Start', active=True)
        surface.blit(font(12).render(
            'exact grading is on below {0} empty cells'.format(
                GRADE_CELL_LIMIT), True, PALETTE['muted']),
            (card.x + 20, card.bottom - 42))
        pygame.display.flip()
        return hits

    def draw():
        if state['screen'] == 'setup':
            return draw_setup()
        surface.fill(PALETTE['bg'])
        draw_board()
        hits = draw_panel()
        pygame.display.flip()
        return hits

    # ---- play --------------------------------------------------------

    def restart():
        game[0] = MNK(m=state['m'], n=state['n'], k=state['k'])
        state['last'] = None
        state['note'] = ''
        state['status'] = describe_turn()

    def advance():
        """One agent move, if it is an agent's turn."""
        current = game[0]
        if current.is_game_over():
            state['status'] = describe_turn()
            return False
        agent = players[0].get(current.current_player)
        if agent is None:
            return False
        state['thinking'] = True
        state['status'] = '{0} thinking...'.format(
            current.current_player.upper())
        draw()
        before = current.copy()
        move = agent(current)
        verdict = grade(before, move)
        reached = getattr(agent, 'last_depth', 0)
        current.execute_turn(move)
        state['last'] = move
        state['thinking'] = False
        state['note'] = '{0} played {1}{2}{3}'.format(
            before.current_player.upper(), move, verdict,
            '   depth {0}'.format(reached) if reached else '')
        state['status'] = describe_turn()
        draw()
        return True

    rebuild(log_status=False)
    state['screen'] = 'setup'
    hits = draw()
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q,):
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    state['screen'] = ('play' if state['screen'] == 'setup'
                                       else 'setup')
                elif event.key == pygame.K_s:
                    state['screen'] = 'setup'
                elif event.key == pygame.K_r and state['screen'] == 'play':
                    restart()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state['screen'] == 'setup':
                    bumped = False
                    for name in ('m', 'n', 'k', 'depth'):
                        minus, plus = hits[name]
                        step = (-1 if minus.collidepoint(event.pos)
                                else 1 if plus.collidepoint(event.pos)
                                else 0)
                        if step:
                            state[name] = clamp_setting(
                                name, state[name] + step)
                            bumped = True
                    if bumped:
                        state['k'] = clamp_setting('k', state['k'],
                                                   state['m'], state['n'])
                        cell, surface, width, height = resize()
                        hits = draw()
                        continue
                    for side, key, rect in hits['sides']:
                        if rect.collidepoint(event.pos):
                            state['sides'][side] = key
                    if hits['start'].collidepoint(event.pos):
                        rebuild()
                        state['screen'] = 'play'
                else:
                    for name, rect in hits:
                        if rect.collidepoint(event.pos):
                            if name == 'setup':
                                state['screen'] = 'setup'
                            else:
                                restart()
                    current = game[0]
                    if (state['screen'] == 'play'
                            and not current.is_game_over()
                            and players[0].get(current.current_player)
                            is None
                            and event.pos[1] < state['m'] * cell):
                        index = ((event.pos[1] // cell) * state['n']
                                 + (event.pos[0] // cell))
                        if index in current.get_all_legal_turns():
                            current.execute_turn(index)
                            state['last'] = index
                            state['note'] = ''
                            state['status'] = describe_turn()
        if state['screen'] == 'play' and not state['thinking']:
            if advance():
                # Let a human see an agent-vs-agent game unfold.
                if all(players[0].get(s) is not None
                       for s in (FIRST, SECOND)):
                    pygame.time.wait(220)
        hits = draw()
        pygame.time.wait(16)
    pygame.quit()


# -------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m', type=int, default=4, help='rows')
    parser.add_argument('--n', type=int, default=4, help='columns')
    parser.add_argument('--k', type=int, default=3, help='in a row to win')
    parser.add_argument('--depth', type=int, default=3,
                        help='search depth for the TD + search agent')
    parser.add_argument('--x', default='human',
                        help='who plays X: ' + ', '.join(
                            o['key'] for o in PLAYER_OPTIONS))
    parser.add_argument('--o', default='td',
                        help='who plays O')
    parser.add_argument('--rounds', type=int, default=6)
    parser.add_argument('--games', type=int, default=60,
                        help='training games per round')
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--budget', type=float, default=20.0,
                        help='seconds of training per board size')
    parser.add_argument('--td-leaf', action='store_true',
                        help='train with search in the loop (slower)')
    parser.add_argument('--text', action='store_true',
                        help='play in the terminal instead of a window')
    args = parser.parse_args()

    known = set(o['key'] for o in PLAYER_OPTIONS)
    for side, kind in (('--x', args.x), ('--o', args.o)):
        if kind not in known:
            parser.error('{0} must be one of {1}'.format(
                side, ', '.join(sorted(known))))

    sides = {FIRST: args.x, SECOND: args.o}
    brain = Brain(args.rounds, args.games, args.seed, args.td_leaf,
                  args.depth, budget=args.budget)
    print('m,n,k  {0}x{1} k={2}'.format(args.m, args.n, args.k))
    if args.text:
        play_text(args.m, args.n, args.k, brain, args.depth, sides)
    else:
        play_window(args.m, args.n, args.k, brain, args.depth, sides)


if __name__ == '__main__':
    main()
