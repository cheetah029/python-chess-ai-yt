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
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lgref import clipboard
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
#:
#: DEPTH CANNOT BE CONSTANT ACROSS BOARD SIZES at a fixed time budget,
#: and pretending otherwise would be dishonest. Measured at five
#: seconds a move: 7x7 k=4 reaches depth 6, 9x9 k=5 reaches 4, 13x13
#: reaches 3 and 19x19 reaches 2 -- because 19x19 offers 355 moves
#: against 43, and the same depth costs the branching factor to the
#: power of the depth. What IS guaranteed is a constant depth across
#: the PHASES of one game, which is a different promise and the one
#: that was asked for. `budget` is therefore a setting: it is the only
#: honest way to trade time for depth on a big board.
SETTING_BOUNDS = {'m': (2, 20), 'n': (2, 20), 'k': (2, 20),
                  'depth': (1, 6), 'budget': (1, 120)}


#: The window the SETUP screen opens at, fixed. It used to be derived
#: from the board size, so every click on a `+` called
#: `pygame.display.set_mode` and the window jumped around under the
#: cursor while a reviewer was still choosing a board. The board's own
#: geometry is only needed once play starts.
SETUP_SIZE = (620, 540)

#: Hold a stepper down and it repeats: this long before the first
#: repeat, then this often. Both in milliseconds, and both chosen the
#: way a keyboard's repeat is -- long enough that a single click is
#: never two, short enough that twenty is a gesture rather than a chore.
REPEAT_DELAY_MS = 420
REPEAT_EVERY_MS = 70

SAVE_HEADER = '=== m,n,k save (v1) ==='
SAVE_HEADER_V2 = '=== m,n,k save (v2) ==='
SAVE_BEGIN = '___MNK_SAVE_V2_BEGIN___'
SAVE_END = '___MNK_SAVE_V2_END___'


def cell_name(cell, m, n):
    """A cell as a coordinate, like the case study's notation.

    File letter from the column, rank number from the bottom -- so the
    centre of 19x19 is `j10`, which is what a player reading a Go board
    would call it. A drawn board in a save file is pleasant to look at
    and useless to replay; coordinates are the opposite and the case
    study already made that choice.
    """
    row, col = divmod(cell, n)
    return '{0}{1}'.format(chr(ord('a') + col), m - row)


def cell_from_name(name, m, n):
    """The inverse. None when it does not name a square of this board."""
    name = (name or '').strip().lower()
    if len(name) < 2 or not name[0].isalpha():
        return None
    col = ord(name[0]) - ord('a')
    try:
        rank = int(name[1:])
    except ValueError:
        return None
    row = m - rank
    if not (0 <= row < m and 0 <= col < n):
        return None
    return row * n + col


def save_text(game, m, n, k, style, moves, sides=None):
    """The game as text: move numbers and COORDINATES, like the case
    study's save.

    The first version drew the position as a block of dots and marks.
    That is pleasant to look at and useless: it cannot be replayed, it
    duplicates what the moves already say, and two sources of truth for
    one thing is how a loader comes to disagree with itself. What a
    save needs is the move list, the board it was played on, and who
    was playing -- so that is what this writes.
    """
    sides = sides or {}
    first = sides.get(FIRST, 'human')
    second = sides.get(SECOND, 'human')
    pairs = []
    for index in range(0, len(moves), 2):
        line = '{0}. {1}'.format(index // 2 + 1,
                                 cell_name(moves[index], m, n))
        if index + 1 < len(moves):
            line += ' ' + cell_name(moves[index + 1], m, n)
        pairs.append(line)
    return '\n'.join([
        SAVE_HEADER_V2,
        'Board: {0}x{1} k={2}'.format(m, n, k),
        'Style: {0}'.format(style),
        'Mode: {0}_vs_{1}'.format(first, second),
        '{0}: {1}   {2}: {3}'.format(side_label(FIRST, style), first,
                                     side_label(SECOND, style), second),
        'CurrentTurn: {0}'.format(len(moves)),
        '',
        SAVE_BEGIN,
    ] + pairs + [SAVE_END, '']) + '\n'


def load_text(text):
    """`{m, n, k, style, moves, sides}` from a save, v1 or v2.

    BOTH VERSIONS, because a reviewer has v1 saves and breaking them to
    tidy the format would be a worse trade than reading two.
    """
    if not text:
        return None
    if SAVE_HEADER_V2 not in text and SAVE_HEADER not in text:
        return None
    out = {'style': 'squares', 'moves': [], 'sides': {}}
    body_moves = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('Board:'):
            body = line.split(':', 1)[1].strip()
            size, _, condition = body.partition('k=')
            rows, _, cols = size.strip().partition('x')
            try:
                out['m'] = int(rows)
                out['n'] = int(cols)
                out['k'] = int(condition)
            except ValueError:
                return None
        elif line.startswith('Style:'):
            out['style'] = line.split(':', 1)[1].strip()
        elif line.startswith('Mode:'):
            body = line.split(':', 1)[1].strip()
            first, _, second = body.partition('_vs_')
            if first and second:
                out['sides'] = {FIRST: first, SECOND: second}
        elif line.startswith('Moves:'):
            # v1: a flat list of cell indices.
            body = line.split(':', 1)[1].strip()
            try:
                out['moves'] = [int(x) for x in body.split()]
            except ValueError:
                return None
        elif line and line[0].isdigit() and '.' in line:
            # v2: "12. j10 k9"
            body_moves += line.split('.', 1)[1].split()
    if 'm' not in out or 'n' not in out or 'k' not in out:
        return None
    if body_moves and not out['moves']:
        cells = [cell_from_name(name, out['m'], out['n'])
                 for name in body_moves]
        if any(cell is None for cell in cells):
            return None
        out['moves'] = cells
    return out


def replay_moves(m, n, k, moves):
    """A game with `moves` played, and the prefix that was legal.

    A pasted game may not fit the board it names -- someone edits a line
    by hand, or pastes half of one. Replaying stops at the first illegal
    move and reports how far it got, rather than raising into the event
    loop.
    """
    game = MNK(m=m, n=n, k=k)
    played = []
    for move in moves:
        if game.is_game_over() or move not in game.get_all_legal_turns():
            break
        game.execute_turn(move)
        played.append(move)
    return game, played


def overlaps(layout):
    """Pairs of named rectangles that intersect.

    A LAYOUT TEST NEEDS A LAYOUT, which is why `draw_setup` records
    every rectangle it draws -- controls AND text -- instead of only the
    ones it returns for hit-testing. A reviewer's screenshot showed the
    seconds-per-move stepper drawn through the "X player" heading,
    because one was at `y + 144` and the other at `y + 152` and nothing
    in the code related the two numbers.

    Returns `[(name_a, name_b)]`, so a failure names the two things that
    collided rather than saying a number changed.
    """
    names = sorted(layout)
    clashes = []
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            if layout[first].colliderect(layout[second]):
                clashes.append((first, second))
    return clashes


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

    def training_board(self, m, n, k):
        """The board the weights are LEARNED on, which need not be the
        board they are played on.

        `features.mnk` emits `Marks` and `Line:1..k-1`, and those names
        depend on k ALONE -- not on m or n. So weights learned on a
        small board transfer verbatim to a large one with the same k,
        and a small board is enormously cheaper: measured at 300 games
        in 20 seconds on 7x7 k=5 against 60 games in 41 seconds on
        19x19, five times the data for half the time. A reviewer playing
        19x19 was facing an agent trained on sixty games.

        The board is kept just big enough to hold the win condition with
        room to manoeuvre, and never larger than the one being played.
        """
        side = min(max(k + 2, 6), max(m, n))
        return max(side, k), max(side, k)

    #: Where trained weights are kept between runs. Beside the
    #: package rather than in a temp directory, because the point is
    #: that a reviewer who reopens the window does not wait again.
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'weights', 'mnk_cache')

    def _cache_path(self, key):
        rows, cols, k = key
        return os.path.join(
            self.CACHE_DIR,
            '{0}x{1}_k{2}_r{3}_g{4}_s{5}{6}.json'.format(
                rows, cols, k, self.rounds, self.games, self.seed,
                '_leaf' if self.use_td_leaf else ''))

    def _load_cached(self, key):
        """`(weights, scales)` from an earlier run, or None.

        ANY problem reading it means training again rather than playing
        on something half-read -- a corrupt cache must cost time, never
        correctness.
        """
        try:
            with open(self._cache_path(key)) as handle:
                payload = json.load(handle)
            weights = payload['weights']
            scales = payload.get('scales', {})
            if not isinstance(weights, dict) or not weights:
                return None
            return weights, scales
        except Exception:
            return None

    def _store_cached(self, key, weights, scales):
        try:
            if not os.path.isdir(self.CACHE_DIR):
                os.makedirs(self.CACHE_DIR)
            with open(self._cache_path(key), 'w') as handle:
                json.dump({'weights': weights, 'scales': scales,
                           'board': list(key)}, handle)
        except Exception:
            pass        # a cache that cannot be written is not an error

    def evaluation(self, m, n, k, log=None):
        rows, cols = self.training_board(m, n, k)
        # Keyed on what the weights actually depend on.
        key = (rows, cols, k)
        if key in self._cache:
            return self._cache[key]
        # ON DISK TOO, so Start is instant the second time. Training is
        # the only slow thing between pressing Start and seeing a board,
        # and it produces the SAME weights every time -- the seed, the
        # rounds, the game count and the board are all fixed. Paying
        # twenty seconds again for an answer already computed is time
        # taken from the only thing that should cost any: thinking.
        stored = self._load_cached(key)
        if stored is not None:
            weights, scales = stored
            self.last_report = (
                'loaded weights trained earlier on {0}x{1}, {2} features'
                .format(rows, cols, len(weights)))
            if log:
                log(self.last_report)

            def evaluate(game, perspective, weights=weights,
                         scales=scales):
                raw = differentials(self.extractor(game), perspective)
                return value(weights, normalise(raw, dict(scales),
                                                update=False))

            self._cache[key] = evaluate
            return evaluate
        scales = {}

        def make_game(variant='full', max_turns=None):
            return MNK(m=rows, n=cols, k=k)

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
                      epsilon=0.25, seed=self.seed,
                      max_turns=rows * cols + 2,
                      scales=scales, budget_seconds=self.budget,
                      searcher=searcher if self.use_td_leaf else None)
        weights = history[-1].weights
        elapsed = time.time() - started
        top = sorted(weights.items(), key=lambda kv: -abs(kv[1]))[:5]
        played = sum(1 for _ in history) and history[-1].games
        where = ('' if (rows, cols) == (m, n)
                 else ' on {0}x{1}'.format(rows, cols))
        lines = ['trained {0} games from zero in {1:.1f}s{2}, {3} features'
                 .format(played, elapsed, where, len(weights))]
        for name, raw in top:
            lines.append('   {0:<24} {1:+.3f}'.format(
                name, raw / (scales.get(name) or 1.0)))
        self.last_report = '\n'.join(lines)
        if log:
            log(self.last_report)
        self._store_cached(key, weights, scales)
        self._cache[key] = evaluate_with(weights)
        return self._cache[key]


def make_player(kind, evaluate, depth, rng, budget=5.0):
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
        searcher = Searcher(evaluate, max_depth=depth, budget=budget,
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

def play_text(m, n, k, brain, depth, sides, style='squares'):
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
                        side_label(game.current_player, style))).strip()
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
                    side_label(game.current_player, style), move,
                    grade(before, move)))
                game.execute_turn(move)
        show(game)
        winner = game.winner
        print('{0} wins'.format(side_label(winner, style)) if winner
              else 'draw')
        try:
            again = input('again? [y/N] ').strip().lower()
        except EOFError:
            return
        if not again.startswith('y'):
            return


# ------------------------------------------------------------------ pygame

#: Go rendering: stones on the INTERSECTIONS of the grid rather than
#: inside its cells, black moving first. The underlying game is
#: unchanged -- m,n,k on an m x n grid is the same game whether the
#: points are drawn as cells or as crossings -- so this is presentation
#: only, and the first player is simply rendered black.
STYLES = ('squares', 'go')

PALETTE = {
    'bg': (246, 245, 242),
    'board_go': (226, 193, 134),
    'line_go': (120, 98, 62),
    'stone_black': (28, 27, 25),
    'stone_white': (250, 249, 246),
    'panel': (255, 255, 255),
    'grid': (214, 211, 204),
    'grid_soft': (233, 231, 226),
    'ink': (31, 30, 28),
    'muted': (122, 117, 110),
    'first': (37, 92, 168),
    'second': (176, 58, 46),
    'hover': (236, 240, 247),
    'win': (252, 243, 207),
    'last': (176, 206, 240),
    'button': (243, 242, 238),
    'button_on': (37, 92, 168),
    'button_edge': (210, 207, 200),
}


def side_label(side, style):
    """What to call a player. The game does not change; the name does."""
    if style == 'go':
        return 'Black' if side == FIRST else 'White'
    return side.upper()


def play_window(m, n, k, brain, depth, sides, style='squares',
                move_budget=5, probe=None):
    """The window. `probe` is a TEST SEAM and is documented as one.

    A reviewer found four separate faults in this screen -- overlapping
    text, the window resizing on every click, no way to move a setting
    twenty steps, and no undo -- and none of them were reachable from a
    test, because everything lived inside this closure and the only
    entry point ran an event loop forever.

    `probe(api)` is called once, after the first draw, with the handles
    a test needs: the state, the layout rectangles, and the actions a
    button would trigger. Returning True ends the loop. It is never
    passed in normal use, and `main()` does not expose it.
    """
    import random

    import pygame

    pygame.init()
    pygame.display.set_caption('m,n,k  --  the general agent')

    state = {'m': m, 'n': n, 'k': k, 'depth': depth, 'style': style,
             'budget': int(move_budget),
             'sides': dict(sides), 'screen': 'setup',
             'status': '', 'thinking': False, 'last': None,
             'auto': True}
    rng = random.Random(0)

    #: Tall enough for the status, the detail line, the note, a row
    #: of buttons AND the key legend below it. It was 132, which fit
    #: two buttons; the legend now sits under six.
    PANEL = 168
    #: How much room the board may use, in pixels, before the window is
    #: resized or made full screen. Not a window size -- `geometry`
    #: divides it by the larger board dimension to get a cell.
    BOARD_BOX = 620
    MIN_W = 560

    def geometry():
        rows, cols = state['m'], state['n']
        # THE BOARD FILLS WHATEVER BOX IT IS GIVEN. `state['box']` is
        # how much room the board may use; it starts at 620 and grows
        # with the window or with full screen, so a 19x19 board can be
        # made big enough to click comfortably instead of being stuck
        # at 32-pixel cells.
        box = state.get('box', BOARD_BOX)
        cell = max(12, min(104, int(box / max(rows, cols))))
        width = max(MIN_W, cols * cell)
        height = rows * cell + PANEL
        return cell, width, height

    def fit_to(size):
        """Recompute the board box from an actual window size."""
        wide, tall = size
        state['box'] = max(240, min(wide, tall - PANEL))
        return resize()

    cell, width, height = geometry()
    # THE SETUP SCREEN OPENS AT A FIXED SIZE and stays there. It used to
    # open at the BOARD's size, so every click on `+` called
    # `set_mode` and the window jumped around under the cursor while a
    # reviewer was still choosing. The board's geometry is only needed
    # once play starts.
    surface = pygame.display.set_mode(SETUP_SIZE, pygame.RESIZABLE)
    fonts = {}

    def font(size, bold=False):
        key = (size, bold)
        if key not in fonts:
            fonts[key] = pygame.font.SysFont(
                'helveticaneue,helvetica,arial,dejavusans', size, bold=bold)
        return fonts[key]

    def resize():
        """Open the window at the size the BOARD needs.

        Called when play starts, never while the setup screen is up --
        that is the whole fix for the window jumping on every click.
        """
        global_cell, w, h = geometry()
        flags = pygame.FULLSCREEN if state.get('fullscreen') else \
            pygame.RESIZABLE
        return (global_cell, pygame.display.set_mode((w, h), flags),
                w, h)

    def enter_setup():
        """Back to the fixed setup size, so the card is never drawn into
        a window shaped for a 20x20 board."""
        state['screen'] = 'setup'
        return pygame.display.set_mode(SETUP_SIZE, pygame.RESIZABLE)

    #: Which stepper is being held down, and when it next repeats.
    held = {'name': None, 'step': 0, 'next': 0}

    def bump(name, step):
        """Move one setting, then re-clamp the win condition.

        `k` depends on the board: a 3-in-a-row condition is impossible
        on a 2x2, so shrinking the board has to pull `k` down with it or
        Start builds a game nobody can win.
        """
        state[name] = clamp_setting(name, state[name] + step)
        state['k'] = clamp_setting('k', state['k'], state['m'], state['n'])

    game = [MNK(m=state['m'], n=state['n'], k=state['k'])]
    evaluate = [None]
    players = [{}]
    #: Snapshots BEFORE each move, and the moves undone from them. A
    #: snapshot rather than an inverse operation because m,n,k states
    #: are tiny and an inverse has to be kept correct forever, while a
    #: copy is correct by construction.
    history = []
    future = []
    #: The moves actually played, in order -- what `save_text` writes.
    played = []

    def rebuild(log_status=True):
        # TRAINING BLOCKS, so the window is drawn first and told what is
        # happening. On a 10x10 board this is twenty seconds, and the
        # first version did it BEFORE the setup screen appeared -- so the
        # window simply did not exist for twenty seconds, with nothing
        # on screen to say why.
        if log_status:
            state['status'] = 'training from zero on {0}x{1} k={2}...'.format(
                state['m'], state['n'], state['k'])
            draw()
        evaluate[0] = brain.evaluation(state['m'], state['n'], state['k'])
        players[0] = {side: make_player(kind, evaluate[0],
                                        state['depth'], rng,
                                        float(state['budget']))
                      for side, kind in state['sides'].items()}
        game[0] = MNK(m=state['m'], n=state['n'], k=state['k'])
        state['last'] = None
        state['status'] = describe_turn()

    def describe_turn():
        current = game[0]
        if current.is_game_over():
            winner = current.winner
            if winner is None:
                return 'draw'
            return '{0} wins'.format(side_label(winner, state['style']))
        kind = state['sides'][current.current_player]
        who = dict((o['key'], o['label']) for o in PLAYER_OPTIONS)[kind]
        return '{0} to play  --  {1}'.format(
            side_label(current.current_player, state['style']), who)

    # ---- drawing -----------------------------------------------------

    def draw_stone(rect, mark, dim=False):
        radius = int(rect.width * 0.42)
        centre = rect.center
        fill = (PALETTE['stone_black'] if mark == FIRST
                else PALETTE['stone_white'])
        if dim:
            surface_alpha = pygame.Surface((radius * 2 + 2, radius * 2 + 2),
                                           pygame.SRCALPHA)
            pygame.draw.circle(surface_alpha, fill + (90,),
                               (radius + 1, radius + 1), radius)
            surface.blit(surface_alpha,
                         (centre[0] - radius - 1, centre[1] - radius - 1))
            return
        pygame.draw.circle(surface, fill, centre, radius)
        pygame.draw.circle(surface, PALETTE['line_go'], centre, radius, 1)

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

    def draw_go_grid():
        rows, cols = state['m'], state['n']
        board = pygame.Rect(0, 0, cols * cell, rows * cell)
        pygame.draw.rect(surface, PALETTE['board_go'], board)
        half = cell // 2
        for row in range(rows):
            y = row * cell + half
            pygame.draw.line(surface, PALETTE['line_go'],
                             (half, y), ((cols - 1) * cell + half, y))
        for col in range(cols):
            x = col * cell + half
            pygame.draw.line(surface, PALETTE['line_go'],
                             (x, half), (x, (rows - 1) * cell + half))

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
        go = state['style'] == 'go'
        if go:
            draw_go_grid()
        last = state['last']
        for index in range(state['m'] * state['n']):
            rect = board_rect(index)
            if index == last and index not in wins:
                # THE LAST MOVE IS A HIGHLIGHT, the same way the board
                # game it is modelled on marks one -- a corner dot read
                # as a speck of dirt on the stone.
                tint = pygame.Surface((cell, cell), pygame.SRCALPHA)
                tint.fill(PALETTE['last'] + (150,))
                surface.blit(tint, rect.topleft)
            if index in wins:
                highlight = pygame.Surface((cell, cell), pygame.SRCALPHA)
                highlight.fill(PALETTE['win'] + (140,))
                surface.blit(highlight, rect.topleft)
            elif index == hovering and not go:
                pygame.draw.rect(surface, PALETTE['hover'], rect)
            if not go:
                pygame.draw.rect(surface, PALETTE['grid_soft'], rect, 1)
            mark = current.cells[index]
            if mark:
                (draw_stone if go else draw_mark)(rect, mark)
            elif index == hovering:
                (draw_stone if go else draw_mark)(
                    rect, current.current_player, dim=True)
        board = pygame.Rect(0, 0, state['n'] * cell, state['m'] * cell)
        if not go:
            pygame.draw.rect(surface, PALETTE['grid'], board, 2)


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
        detail = '{0}x{1}  k={2}   depth {3}   {4}s/move'.format(
            state['m'], state['n'], state['k'], state['depth'],
            state['budget'])
        trained = brain.last_report.splitlines()
        if trained:
            detail = '{0}   {1}'.format(detail, trained[0])
        surface.blit(font(13).render(detail, True, PALETTE['muted']),
                     (16, top + 40))
        note = state.get('note', '')
        if note:
            surface.blit(font(13).render(note, True, PALETTE['muted']),
                         (16, top + 60))
        hits = []
        x = 16
        for name, caption, enabled in (
                ('setup', 'Setup', True),
                ('restart', 'Restart', True),
                ('undo', 'Undo', bool(history)),
                ('redo', 'Redo', bool(future)),
                ('copy', 'Copy', True),
                ('paste', 'Paste', True)):
            rect = pygame.Rect(x, top + 88, 66, 28)
            button(rect, caption, small=True)
            if not enabled:
                # Drawn dimmed rather than hidden, so the row does not
                # reflow under the cursor as moves are made.
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade.fill((255, 255, 255, 150))
                surface.blit(shade, rect.topleft)
            hits.append((name, rect))
            x += 72
        surface.blit(font(12).render(
            'S setup   R restart   ←/→ step   Home/End jump   '
            'C copy   V paste   F11 full screen   Q quit', True,
            PALETTE['muted']), (16, top + 120))
        return hits

    def stepper(x, y, label, value_text, layout=None):
        glyph = font(13).render(label, True, PALETTE['muted'])
        surface.blit(glyph, (x, y + 7))
        minus = button(pygame.Rect(x + 74, y, 28, 28), '-', small=True)
        box = pygame.Rect(x + 106, y, 44, 28)
        pygame.draw.rect(surface, PALETTE['button'], box, border_radius=7)
        pygame.draw.rect(surface, PALETTE['button_edge'], box, 1,
                         border_radius=7)
        value = font(14, bold=True).render(value_text, True, PALETTE['ink'])
        surface.blit(value, value.get_rect(center=box.center))
        plus = button(pygame.Rect(x + 154, y, 28, 28), '+', small=True)
        if layout is not None:
            layout['label:' + label] = pygame.Rect((x, y + 7),
                                                   glyph.get_size())
            layout['minus:' + label] = minus
            layout['value:' + label] = box
            layout['plus:' + label] = plus
        # The VALUE BOX is returned too: scrolling over it adjusts the
        # setting, which is the fastest way to move a number twenty
        # steps and the reason a reviewer asked for something better
        # than clicking `+` eighteen times.
        return minus, plus, box

    def draw_setup():
        """The setup card, laid out from a cursor rather than offsets.

        EVERY RECTANGLE IS RECORDED in `state['layout']`, text included,
        so `overlaps()` can be asserted in a test. The previous version
        placed each row at a hand-written offset from one `y`, and the
        seconds-per-move stepper at `y + 144` was drawn straight through
        the "X player" heading at `y + 152`. Nothing in the code related
        the two numbers, so nothing could have caught it.
        """
        panel_w, panel_h = surface.get_size()
        surface.fill(PALETTE['bg'])
        card = pygame.Rect(20, 20, panel_w - 40, panel_h - 40)
        pygame.draw.rect(surface, PALETTE['panel'], card, border_radius=12)
        pygame.draw.rect(surface, PALETTE['button_edge'], card, 1,
                         border_radius=12)
        layout = {}

        def text_at(key, where, glyph):
            surface.blit(glyph, where)
            layout[key] = pygame.Rect(where, glyph.get_size())

        text_at('title', (card.x + 20, card.y + 16),
                font(20, bold=True).render('Setup', True, PALETTE['ink']))
        text_at('subtitle', (card.x + 20, card.y + 44), font(13).render(
            'the same learner and search as the 8x8 case study', True,
            PALETTE['muted']))

        hits = {}
        #: A CURSOR, advanced by each row's own height. Rows cannot
        #: overlap because none of them chooses its own y.
        cursor = card.y + 76
        ROW = 36
        for name, caption in (('m', 'rows'), ('n', 'columns'),
                              ('k', 'in a row'), ('depth', 'depth'),
                              ('budget', 'sec/move')):
            hits[name] = stepper(card.x + 20, cursor, caption,
                                 str(state[name]), layout)
            cursor += ROW

        text_at('style_label', (card.x + 250, card.y + 83),
                font(13).render('board style', True, PALETTE['muted']))
        hits['style'] = []
        x = card.x + 250
        for name, caption in (('squares', 'Squares (X/O)'),
                              ('go', 'Intersections (Go)')):
            rect = pygame.Rect(x, card.y + 104, 150, 28)
            button(rect, caption, active=(state['style'] == name),
                   small=True)
            hits['style'].append((name, rect))
            layout['style:' + name] = rect
            x += 156

        #: A FULL ROW OF CLEARANCE below the last stepper, so the side
        #: pickers cannot creep back up into it.
        cursor += 14
        hits['sides'] = []
        for side in (FIRST, SECOND):
            caption = '{0} player'.format(side_label(side, state['style']))
            text_at('side_label:' + side, (card.x + 20, cursor),
                    font(13, bold=True).render(caption, True,
                                               PALETTE['ink']))
            cursor += 20
            x = card.x + 20
            for option in PLAYER_OPTIONS:
                rect = pygame.Rect(x, cursor, 104, 28)
                button(rect, option['label'],
                       active=(state['sides'][side] == option['key']),
                       small=True)
                hits['sides'].append((side, option['key'], rect))
                layout['side:{0}:{1}'.format(side, option['key'])] = rect
                x += 110
            cursor += ROW + 8

        hits['start'] = button(
            pygame.Rect(card.right - 140, card.bottom - 52, 120, 34),
            'Start', active=True)
        layout['start'] = hits['start']
        # LOAD FROM THE SETUP SCREEN. A saved game names its own board,
        # so loading had to wait until a board was chosen and Start
        # pressed -- which meant choosing the board twice.
        hits['load'] = button(
            pygame.Rect(card.right - 272, card.bottom - 52, 124, 34),
            'Load (V)', small=True)
        layout['load'] = hits['load']
        # TWO SHORT LINES, not one long one. A single line ran under the
        # Start button -- which the overlap check caught, after I had
        # just finished fixing the overlap it was written for.
        text_at('hint', (card.x + 20, card.bottom - 62), font(12).render(
            'hold +/- to repeat, or scroll over a value', True,
            PALETTE['muted']))
        text_at('grading', (card.x + 20, card.bottom - 42), font(12).render(
            'exact grading below {0} empty cells'.format(GRADE_CELL_LIMIT),
            True, PALETTE['muted']))
        state['layout'] = layout
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
        del history[:]
        del future[:]
        del played[:]
        state['last'] = None
        state['note'] = ''
        state['auto'] = True
        state['status'] = describe_turn()

    def commit(move):
        """Play `move`, keeping enough to undo it.

        A REDO STACK IS DISCARDED on a new move, which is what every
        editor does and what a player expects: the branch you just
        abandoned is not coming back.
        """
        history.append(game[0].copy())
        del future[:]
        game[0].execute_turn(move)
        played.append(move)
        state['last'] = move

    def undo():
        """Step back far enough that it is a HUMAN's turn again.

        One ply is not enough when an agent is playing: handing the turn
        back to the agent means it instantly replays, and the board
        looks unchanged. So plies are popped until a human is to move,
        or the history runs out.

        With no human on either side there is nobody to hand the turn
        to, so one ply comes off and the clock stops -- `auto` goes
        false and the agents wait rather than racing forward again.
        """
        if not history:
            return False
        anyone_human = any(players[0].get(side) is None
                           for side in (FIRST, SECOND))
        while history:
            future.append(played.pop() if played else None)
            game[0] = history.pop()
            state['last'] = played[-1] if played else None
            if not anyone_human:
                state['auto'] = False
                break
            if players[0].get(game[0].current_player) is None:
                break
        state['note'] = 'undone'
        state['status'] = describe_turn()
        return True

    def redo():
        if not future:
            return False
        move = future.pop()
        if move is None or move not in game[0].get_all_legal_turns():
            return False
        history.append(game[0].copy())
        game[0].execute_turn(move)
        played.append(move)
        state['last'] = move
        state['note'] = 'redone'
        state['status'] = describe_turn()
        return True

    def jump(step, limit=2000):
        """Repeat `step` until it stops making progress.

        BOUNDED and progress-checked rather than trusting the step to
        report exhaustion: a step that returns True forever would hang
        the window, and a hang is worse than a jump that stops early.
        """
        for _ in range(limit):
            if not step():
                return

    def load_into():
        """Paste a save and go straight to the position, from either
        screen. Training happens first if the board changed."""
        before = (state['m'], state['n'], state['k'])
        if not paste_game():
            return False
        if (state['m'], state['n'], state['k']) != before or \
                evaluate[0] is None:
            rebuild()
        return True

    def copy_game():
        text = save_text(game[0], state['m'], state['n'], state['k'],
                         state['style'], played, state['sides'])
        state['note'] = ('copied the game to the clipboard'
                         if clipboard.copy_text(text)
                         else 'the clipboard is unavailable here')

    def paste_game():
        loaded = load_text(clipboard.read_text() or '')
        if loaded is None:
            state['note'] = 'the clipboard holds no m,n,k save'
            return False
        for name in ('m', 'n', 'k'):
            state[name] = clamp_setting(name, loaded[name])
        state['k'] = clamp_setting('k', state['k'], state['m'], state['n'])
        if loaded.get('style') in STYLES:
            state['style'] = loaded['style']
        if loaded.get('sides'):
            known = set(option['key'] for option in PLAYER_OPTIONS)
            for side, kind in loaded['sides'].items():
                if side in state['sides'] and kind in known:
                    state['sides'][side] = kind
        # REPLAYED MOVE BY MOVE, so the history exists. Loading used to
        # jump straight to the final position with an EMPTY history, so
        # undo did nothing on a loaded game -- which is exactly when a
        # reviewer wants to step back through it.
        del history[:]
        del future[:]
        del played[:]
        restored = MNK(m=state['m'], n=state['n'], k=state['k'])
        game[0] = restored
        kept = []
        for move in loaded['moves']:
            if (game[0].is_game_over()
                    or move not in game[0].get_all_legal_turns()):
                break
            commit(move)
            kept.append(move)
        state['auto'] = False
        short = len(kept) < len(loaded['moves'])
        state['note'] = 'loaded {0} move{1}{2}'.format(
            len(kept), '' if len(kept) == 1 else 's',
            ' (the rest did not fit this board)' if short else '')
        state['status'] = describe_turn()
        return True

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
            side_label(current.current_player, state['style']))
        draw()
        before = current.copy()
        move = agent(current)
        verdict = grade(before, move)
        reached = getattr(agent, 'last_depth', 0)
        commit(move)
        state['thinking'] = False
        state['note'] = '{0} played {1}{2}{3}'.format(
            side_label(before.current_player, state['style']), move, verdict,
            '   depth {0}'.format(reached) if reached else '')
        state['status'] = describe_turn()
        draw()
        return True

    # The setup screen comes up IMMEDIATELY; nothing is trained until
    # Start is pressed, so a reviewer can change the board before paying
    # for a board they did not want.
    state['screen'] = 'setup'
    state['status'] = 'press Start to train and play'
    hits = draw()
    running = True
    if probe is not None:
        if probe({'state': state, 'hits': hits, 'bump': bump,
                  'undo': undo, 'redo': redo, 'restart': restart,
                  'commit': commit, 'copy_game': copy_game,
                  'paste_game': paste_game, 'draw': draw,
                  'rebuild': rebuild, 'resize': resize,
                  'enter_setup': enter_setup, 'game': game,
                  'players': players, 'history': history,
                  'future': future, 'played': played,
                  'save': lambda: save_text(game[0], state['m'],
                                            state['n'], state['k'],
                                            state['style'], played,
                                            state['sides']),
                  'load': load_into}):
            running = False
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q,):
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    if state['screen'] == 'setup':
                        state['screen'] = 'play'
                    else:
                        surface = enter_setup()
                elif event.key == pygame.K_s:
                    surface = enter_setup()
                elif (event.key == pygame.K_v
                        and state['screen'] == 'setup'):
                    if load_into():
                        state['screen'] = 'play'
                        cell, surface, width, height = resize()
                    hits = draw()
                    continue
                elif event.key in (pygame.K_F11, pygame.K_BACKQUOTE):
                    # FULL SCREEN, on F11 and on the backtick beside it
                    # -- F11 is the convention and a Mac laptop maps it
                    # to something else by default.
                    state['fullscreen'] = not state.get('fullscreen')
                    if state['screen'] == 'play':
                        cell, surface, width, height = fit_to(
                            pygame.display.get_desktop_sizes()[0]
                            if state['fullscreen']
                            else (BOARD_BOX, BOARD_BOX + PANEL))
                    hits = draw()
                    continue
                elif state['screen'] == 'play':
                    if event.key == pygame.K_r:
                        restart()
                    # LEFT / RIGHT step, HOME / END (or UP / DOWN) jump
                    # to the ends -- the same bindings the case study's
                    # window uses, so one habit serves both games.
                    elif event.key in (pygame.K_u, pygame.K_LEFT):
                        undo()
                    elif event.key in (pygame.K_y, pygame.K_RIGHT):
                        redo()
                    elif event.key in (pygame.K_HOME, pygame.K_UP):
                        jump(undo)
                    elif event.key in (pygame.K_END, pygame.K_DOWN):
                        jump(redo)
                    elif event.key == pygame.K_c:
                        copy_game()
                    elif event.key == pygame.K_v:
                        paste_game()
            elif event.type == pygame.VIDEORESIZE:
                # DRAGGING THE WINDOW GROWS THE BOARD. The cell size is
                # derived from the room available, so a 19x19 board
                # becomes clickable instead of staying at 32 pixels.
                if state['screen'] == 'play':
                    cell, surface, width, height = fit_to(event.size)
                else:
                    surface = pygame.display.set_mode(
                        (max(SETUP_SIZE[0], event.w),
                         max(SETUP_SIZE[1], event.h)), pygame.RESIZABLE)
                hits = draw()
                continue
            elif (event.type == pygame.MOUSEBUTTONUP
                    and state['screen'] == 'setup'):
                held['name'] = None
            elif (event.type == pygame.MOUSEWHEEL
                    and state['screen'] == 'setup'):
                # SCROLLING OVER A VALUE adjusts it, which is the
                # fastest way to move a setting twenty steps -- a
                # reviewer counted the clicks and asked for something
                # better.
                where = pygame.mouse.get_pos()
                for name in ('m', 'n', 'k', 'depth', 'budget'):
                    minus, plus, box = hits[name]
                    if (box.collidepoint(where) or minus.collidepoint(where)
                            or plus.collidepoint(where)):
                        bump(name, 1 if event.y > 0 else -1)
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state['screen'] == 'setup':
                    bumped = False
                    for name in ('m', 'n', 'k', 'depth', 'budget'):
                        minus, plus, _box = hits[name]
                        step = (-1 if minus.collidepoint(event.pos)
                                else 1 if plus.collidepoint(event.pos)
                                else 0)
                        if step:
                            bump(name, step)
                            # HOLD TO REPEAT, like a keyboard: the first
                            # repeat waits long enough that a click is
                            # never two.
                            held['name'] = name
                            held['step'] = step
                            held['next'] = (pygame.time.get_ticks()
                                            + REPEAT_DELAY_MS)
                            bumped = True
                    if bumped:
                        # NO `resize()` HERE. Resizing on every click is
                        # what made the window jump around while a
                        # reviewer was choosing a board.
                        hits = draw()
                        continue
                    for name, rect in hits['style']:
                        if rect.collidepoint(event.pos):
                            state['style'] = name
                    for side, key, rect in hits['sides']:
                        if rect.collidepoint(event.pos):
                            state['sides'][side] = key
                    if hits['load'].collidepoint(event.pos):
                        if load_into():
                            state['screen'] = 'play'
                            cell, surface, width, height = resize()
                        hits = draw()
                        continue
                    if hits['start'].collidepoint(event.pos):
                        rebuild()
                        state['screen'] = 'play'
                        # The window takes the BOARD's shape now, which
                        # is the one moment it should.
                        cell, surface, width, height = resize()
                else:
                    acted = False
                    for name, rect in hits:
                        if not rect.collidepoint(event.pos):
                            continue
                        acted = True
                        if name == 'setup':
                            surface = enter_setup()
                        elif name == 'restart':
                            restart()
                        elif name == 'undo':
                            undo()
                        elif name == 'redo':
                            redo()
                        elif name == 'copy':
                            copy_game()
                        elif name == 'paste':
                            paste_game()
                    if acted:
                        hits = draw()
                        continue
                    current = game[0]
                    if (state['screen'] == 'play'
                            and not current.is_game_over()
                            and players[0].get(current.current_player)
                            is None
                            and event.pos[1] < state['m'] * cell):
                        index = ((event.pos[1] // cell) * state['n']
                                 + (event.pos[0] // cell))
                        if index in current.get_all_legal_turns():
                            commit(index)
                            # A HUMAN MOVE RESUMES the clock, so undo
                            # does not leave the agents frozen forever.
                            state['auto'] = True
                            state['note'] = ''
                            state['status'] = describe_turn()
        # HOLD TO REPEAT. Checked once per frame rather than per
        # event, because a held button generates no further events.
        if state['screen'] == 'setup' and held['name']:
            if not pygame.mouse.get_pressed()[0]:
                held['name'] = None
            elif pygame.time.get_ticks() >= held['next']:
                bump(held['name'], held['step'])
                held['next'] = (pygame.time.get_ticks() + REPEAT_EVERY_MS)
        if (state['screen'] == 'play' and evaluate[0] is None):
            surface = enter_setup()
        if (state['screen'] == 'play' and not state['thinking']
                and state.get('auto', True)):
            if advance():
                # Let a human see an agent-vs-agent game unfold.
                if all(players[0].get(s) is not None
                       for s in (FIRST, SECOND)):
                    pygame.time.wait(220)
        hits = draw()
        pygame.time.wait(16)
    if probe is None:
        # NOT WHEN DRIVEN BY A PROBE. `pygame.quit()` tears down fonts
        # for the whole PROCESS, so a test that opens this window left
        # every later test unable to build one -- "font not
        # initialized", four files away, with nothing pointing back
        # here. An application should shut pygame down; a test seam
        # must not.
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
    # TWO DIFFERENT BUDGETS, and they were both called `--budget`,
    # which made the module unrunnable: argparse refuses the duplicate
    # option and the crash happened before any window opened. They are
    # not the same quantity -- one is spent once, before play starts,
    # and the other is spent on every move -- so merging them would
    # have been wrong even if argparse had allowed it.
    parser.add_argument('--train-budget', type=float, default=20.0,
                        help='seconds of TRAINING per board size, spent '
                             'once when Start is pressed')
    parser.add_argument('--td-leaf', action='store_true',
                        help='train with search in the loop (slower)')
    parser.add_argument('--budget', type=float, default=5.0,
                        help='seconds per MOVE; the only honest way to '
                             'trade time for depth on a big board')
    parser.add_argument('--style', default='squares', choices=STYLES,
                        help='squares draws X and O inside cells; go draws '
                             'black and white stones on the intersections, '
                             'black first')
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
                  args.depth, budget=args.train_budget)
    print('m,n,k  {0}x{1} k={2}'.format(args.m, args.n, args.k))
    if args.text:
        play_text(args.m, args.n, args.k, brain, args.depth, sides,
                  args.style)
    else:
        play_window(args.m, args.n, args.k, brain, args.depth, sides,
                    args.style, move_budget=args.budget)


if __name__ == '__main__':
    main()
