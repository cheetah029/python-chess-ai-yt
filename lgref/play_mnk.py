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
#: And the search cost goes as the branching factor to the power of the
#: depth, so a depth that is instant on 9x9 is minutes on 20x20 --
#: which is why `affordable_depth` reads the default off the board.
#:
#: `k` above both dimensions would make every game a draw by
#: construction, so it is clamped against the board.
#:
#: THERE IS NO LONGER A sec/move SETTING, and the question it used to
#: answer -- "why is the depth different every move?" -- no longer has
#: an answer, because it no longer happens. The search ran under a
#: per-move wall clock, so the depth reached was whatever fitted, and
#: what fitted grew as the board filled and the branching fell: 3 plies
#: at two marks on 13x13, 6 at twenty, 10 at sixty. That made the agent
#: a different player in every phase of one game.
#:
#: THE CLOCK IS GONE FROM THE SEARCHER ENTIRELY. It had no premise --
#: neither game here constrains move time, both being bounded in plies
#: -- and it could only ever take depth AWAY from the depth that was
#: asked for. The depth is now exactly the depth, in every phase, on
#: every machine. See `Searcher.__init__` and
#: `docs/candidate-designs.md` §6.
#:
#: DEPTH STILL CANNOT BE CONSTANT ACROSS BOARD SIZES, and pretending
#: otherwise would be dishonest -- 19x19 offers 361 moves against 25,
#: and the same depth costs the branching factor to the power of the
#: depth. What IS guaranteed is a constant depth across the PHASES of
#: one game, which is the promise that was actually asked for.
SETTING_BOUNDS = {'m': (2, 20), 'n': (2, 20), 'k': (2, 20),
                  'depth': (1, 10)}


#: THE DEPTH THE BOARD CAN AFFORD, measured rather than chosen.
#:
#: Removing the per-move clock left a real residual. The configured
#: depth was 3 for every board, and the clock had been quietly
#: delivering less on the big ones -- so with the clock gone, a 19x19
#: move went from five seconds at depth 2 to forty-seven at depth 3.
#:
#: WORST-CASE SECONDS A MOVE, no clock, shipped evaluation and shipped
#: search settings (futility and late-move reduction are both off for
#: this game now, which makes the tree bigger than older numbers in
#: this file suggest):
#:
#:      board       depth 2   depth 3   depth 4
#:      5x5 k4         0.00      0.03      0.07
#:      7x7 k4         0.01      0.17      0.88
#:      9x9 k5         0.04      0.48      2.76
#:      13x13 k5       0.15      4.02     17.03
#:      19x19 k5       1.35     46.70    218.83
#:
#: WHY A BRANCHING RULE AND NOT A TABLE OF BOARDS. The cost is about
#: `b ** d` where `b` is the branching factor, and in this game the
#: branching factor is the number of empty cells -- a quantity the
#: RULES give, not one anybody supplies. So the threshold is written
#: against the cell count and the measurements above fix where it
#: falls. A table of named boards would not generalise to the next
#: board somebody types into the steppers.
#:
#: CAPPED AT THE OLD DEFAULT ON PURPOSE. Depth 4 fits comfortably up
#: to 9x9, and raising it there would be the "deeper is obviously
#: better" argument that `docs/strictly-better-method.md` refuses. The
#: cap keeps this change to what it claims: the same depth the clocked
#: player delivered, in less time, constant across the phases of a
#: game instead of varying with them.
#:
#: MEASURED ON ONE MACHINE, which is the honest weakness. A slower
#: machine affords less. The window reports the depth it picked and
#: the stepper overrides it, so the number is visible and never
#: binding.
#: Anchored on the measurements above: 13x13 is 169 cells and depth 3
#: costs 4.02 s there, while 19x19 is 361 cells and costs 46.70 s. The
#: boundary sits at 200 because that is the last cell count with a
#: measurement under it.
DEPTH_BY_CELLS = ((200, 3), (None, 2))


#: WHAT A DEPTH WILL COST, so the stepper cannot quietly offer a
#: setting that never finishes. The reviewer asked "how long does depth
#: 10 take? It takes forever. Is that normal or is there an abnormal
#: cause?" -- it is normal, and the arithmetic is worth putting on the
#: screen rather than in a reply.
#:
#: MEASURED GROWTH PER EXTRA PLY, no clock, shipped evaluation:
#:
#:      board      per-ply multiplier   sqrt(cells)
#:      5x5 k4            5.8x              5
#:      9x9 k5            9.6x              9
#:
#: That is what alpha-beta with working move ordering costs: `b**d`
#: without ordering, about `b**(d/2)` with it, so each extra ply
#: multiplies the work by about the SQUARE ROOT of the branching
#: factor. In this game the branching factor is the number of empty
#: cells, which the rules give. The measured multipliers sit just above
#: the square root, so the model carries a 1.15 fudge and is honest
#: about being one.
#:
#: ANCHORS, worst observed seconds at depth 2:
_DEPTH2_SECONDS = ((25, 0.004), (49, 0.01), (81, 0.04),
                   (169, 0.15), (361, 1.35))


def estimated_move_seconds(m, n, depth):
    """Roughly what one move will cost. Within about 2x, checked
    against measurements four orders of magnitude apart:

        13x13 depth 3   estimate 2.2s    measured 4.02s
        19x19 depth 3   estimate 30s     measured 46.7s
        9x9 depth 4     estimate 4.3s    measured 2.76s
        5x5 depth 9     estimate 852s    measured 1305s

    Two-x on a number used to warn somebody is accuracy to spare; it is
    deliberately not presented as more than an order of magnitude.
    """
    cells = m * n
    base = _DEPTH2_SECONDS[-1][1]
    for limit, seconds in _DEPTH2_SECONDS:
        if cells <= limit:
            base = seconds
            break
    else:
        # Beyond the largest anchor, scale the last one by area.
        base = _DEPTH2_SECONDS[-1][1] * (cells / _DEPTH2_SECONDS[-1][0]) ** 2
    multiplier = (cells ** 0.5) * 1.15
    return base * multiplier ** max(0, depth - 2)


def describe_move_cost(seconds):
    """The estimate in words a person reads at a glance."""
    if seconds < 1.0:
        return 'instant'
    if seconds < 60.0:
        return 'about {0:.0f}s a move'.format(seconds)
    if seconds < 3600.0:
        return 'about {0:.0f} min a move'.format(seconds / 60.0)
    if seconds < 86400.0:
        hours = seconds / 3600.0
        return 'about {0:.0f} hour{1} a move'.format(
            hours, '' if hours < 1.5 else 's')
    return 'days a move -- unusable'


def affordable_depth(m, n, cap=3):
    """The deepest search this board can afford, capped at `cap`.

    GENERAL OVER THE BOARD rather than a lookup of the sizes that
    happen to have been measured: the cell count IS the branching
    factor in this game, so a board nobody has measured still lands in
    the right band.
    """
    cells = m * n
    for limit, depth in DEPTH_BY_CELLS:
        if limit is None or cells <= limit:
            return min(depth, cap)
    return min(DEPTH_BY_CELLS[-1][1], cap)


#: The window the SETUP screen opens at, fixed. It used to be derived
#: from the board size, so every click on a `+` called
#: `pygame.display.set_mode` and the window jumped around under the
#: cursor while a reviewer was still choosing a board. The board's own
#: geometry is only needed once play starts.
SETUP_SIZE = (680, 540)

#: Hold a stepper down and it repeats: this long before the first
#: repeat, then this often. Both in milliseconds, and both chosen the
#: way a keyboard's repeat is -- long enough that a single click is
#: never two, short enough that twenty is a gesture rather than a chore.
REPEAT_DELAY_MS = 420
REPEAT_EVERY_MS = 70

SAVE_HEADER = '=== m,n,k save (v1) ==='
SAVE_HEADER_V2 = '=== m,n,k save (v2) ==='
SAVE_HEADER_V3 = '=== m,n,k save (v3) ==='
SAVE_HEADER_V4 = '=== m,n,k save (v4) ==='
SAVE_HEADER_V5 = '=== m,n,k save (v5) ==='
SAVE_BEGIN = '___MNK_SAVE_V2_BEGIN___'
SAVE_END = '___MNK_SAVE_V2_END___'

#: Stated in every save, because a coordinate without its convention is
#: a guess. `10,10` is ROW 10 COUNTED FROM THE BOTTOM, COLUMN 10, both
#: 1-based -- so on 19x19 it is the exact centre, which is the property
#: that makes the notation readable at a glance.
#:
#: ROW FIRST, AND THE REASON IS THE LINE ABOVE IT IN THE FILE. The save
#: states the board as `Board: 19x13`, which is m x n -- ROWS by
#: COLUMNS, because that is what m and n mean in a game called m,n,k.
#: A column-first coordinate contradicts that three lines later, and
#: two orderings in one file is how a reader gets it wrong. (On a
#: square board nothing distinguishes them, which is exactly why the
#: mistake would have survived every test until somebody played on
#: 19x13.) The internal index agrees as well: `divmod(cell, n)` gives
#: (row, col).
#:
#: The case against, for the record: the letter-number form this
#: replaced was column-first (`j10`), as is chess, as is the case
#: study's own a-h/1-8. But a letter is self-disambiguating -- nobody
#: reads `j10` as rank j -- so that notation never had to pick an
#: order, and the habit it builds cannot be misapplied to it. Numbers
#: must pick, so they should match the file they live in.
COORDINATE_NOTE = ('row,column from the bottom-left, both starting at 1'
                   ' (the same order as the board line, which is'
                   ' rows x columns)')


def cell_name(cell, m, n):
    """A cell as a NUMERIC coordinate: `10,10`, row first.

    THE THREE CHOICES, since a coordinate system is only useful if its
    convention is fixed and stated:

    *Row first, then column*, matching the board line in the same
    file -- `Board: 19x13` is m x n, rows by columns, because that is
    what m and n mean in a game called m,n,k -- and matching the
    internal index, where `divmod(cell, n)` gives (row, col). See
    `COORDINATE_NOTE` for the case against, which is the chess habit.

    *Both starting at 1*, because every other number a player reads
    here starts at 1 -- the board is 19x19, not 18x18, and `k=5` counts
    five stones. A zero-based centre of `9,9` on a 19-wide board reads
    as wrong even when it is right.

    *The row counted from the BOTTOM*, as a rank is, so the first row
    is the one nearest the player. The internal index is row-major from
    the top, and that difference is this function's whole job.

    Those three together put the centre of 19x19 at `10,10`.

    AND NO PARENTHESES. The move list is parsed by splitting on
    whitespace, so one move has to be one token; `(10, 10)` is two and
    `(10,10)` spends two characters saying what the comma already said.
    The brackets would also invite a space after the comma, which is
    the form that breaks. The window labels the move instead -- "X
    played 10,10" -- which is where the reading help belongs.
    """
    row, col = divmod(cell, n)
    return '{0},{1}'.format(m - row, col + 1)


def cell_from_name(name, m, n, column_first=False):
    """The inverse. None when it does not name a square of this board.

    `column_first` reads the v3 spelling, where the pair was written
    the other way round. THE ORDER CANNOT BE GUESSED FROM THE PAIR --
    on a square board both readings are valid and only one is right --
    so it comes from the save's own version header rather than from
    the numbers.

    Reads the letter-number form too (`j10`), because a reviewer has
    saves in it and refusing to load them to tidy the parser would be
    a worse trade than keeping four lines. A letter needs no flag: it
    can only be a column.
    """
    name = (name or '').strip().lower()
    if not name:
        return None
    if ',' in name:
        first, _, second = name.partition(',')
        try:
            first = int(first.strip('( '))
            second = int(second.strip(') '))
        except ValueError:
            return None
        col, rank = ((first - 1, second) if column_first
                     else (second - 1, first))
    elif name[0].isalpha():
        col = ord(name[0]) - ord('a')
        try:
            rank = int(name[1:])
        except ValueError:
            return None
    else:
        return None
    if col < 0:
        return None
    row = m - rank
    if not (0 <= row < m and 0 <= col < n):
        return None
    return row * n + col


def save_text(game, m, n, k, style, moves, sides=None, settings=None,
              future=None):
    """The game as text: move numbers and COORDINATES, like the case
    study's save.

    The first version drew the position as a block of dots and marks.
    That is pleasant to look at and useless: it cannot be replayed, it
    duplicates what the moves already say, and two sources of truth for
    one thing is how a loader comes to disagree with itself. What a
    save needs is the move list, the board it was played on, and who
    was playing -- so that is what this writes.

    `future` is the redo stack, so the WHOLE TIMELINE is written and
    not merely the part currently applied. The case study's save has
    always done this -- its header carries `Timeline` beside
    `CurrentTurn`, and loading replays the lot and stops at the
    position you were looking at. This one wrote `played` alone, so a
    game saved after pressing undo lost everything ahead of the cursor:
    you could not step forward through a game you had just stepped back
    through, and nothing said so.

    `settings` carries the REST of what produced the game: the search
    depth and the per-move budget, and the training parameters the
    evaluation was fitted with. A save that records the board but not
    the depth describes a position rather than a game: the same moves
    at depth 2 and depth 6 are two different agents playing, and a
    reviewer reporting "it blundered here" needs the save to say which
    one blundered. The training parameters are PROVENANCE -- they are
    reported on load, not applied, because applying them would mean a
    paste could silently start a three-minute retrain.
    """
    sides = sides or {}
    settings = dict(settings or {})
    first = sides.get(FIRST, 'human')
    second = sides.get(SECOND, 'human')
    # The redo stack is kept with the NEXT move to replay on top, so
    # the chronological continuation is it reversed.
    applied = list(moves)
    timeline = applied + [move for move in reversed(list(future or []))
                          if move is not None]
    moves = timeline
    pairs = []
    for index in range(0, len(moves), 2):
        line = '{0}. {1}'.format(index // 2 + 1,
                                 cell_name(moves[index], m, n))
        if index + 1 < len(moves):
            line += ' ' + cell_name(moves[index + 1], m, n)
        pairs.append(line)
    head = [
        SAVE_HEADER_V5,
        'Board: {0}x{1} k={2}'.format(m, n, k),
        'Coordinates: {0}'.format(COORDINATE_NOTE),
        'Style: {0}'.format(style),
        'Mode: {0}_vs_{1}'.format(first, second),
        '{0}: {1}   {2}: {3}'.format(side_label(FIRST, style), first,
                                     side_label(SECOND, style), second),
    ]
    if 'depth' in settings:
        head.append('Depth: {0}'.format(settings['depth']))
    training = settings.get('training')
    if training:
        head.append('Training: {0}'.format(training))
    head.append('CurrentTurn: {0}'.format(len(applied)))
    head.append('Timeline: {0}'.format(len(timeline)))
    # THE OUTCOME, like the case study's `Winner` header. A draw is a
    # real result in this game -- a full board with no line -- and the
    # case study has no way to say it, so this records it explicitly
    # rather than leaving a finished game looking unfinished.
    if game is not None and game.is_game_over():
        head.append('Winner: {0}'.format(
            game.winner if game.winner else 'draw'))
    return '\n'.join(head + ['', SAVE_BEGIN]
                      + pairs + [SAVE_END, '']) + '\n'


def load_text(text):
    """`{m, n, k, style, moves, sides, depth, budget, training}` from a
    save -- v1, v2 or v3.

    EVERY VERSION, because a reviewer has saves in each and breaking
    them to tidy the format would be a worse trade than reading three.
    The keys a version does not carry are simply absent, so a caller
    restores what the save actually said and leaves the rest alone --
    which is why this returns the settings rather than defaults for
    them.
    """
    if not text:
        return None
    if not any(header in text for header in
               (SAVE_HEADER_V5, SAVE_HEADER_V4, SAVE_HEADER_V3,
                SAVE_HEADER_V2, SAVE_HEADER)):
        return None
    # THE ORDER COMES FROM THE VERSION, NOT FROM THE NUMBERS. v3 wrote
    # the pair column-first; v4 writes it row-first, to agree with the
    # board line in the same file. On a square board the two readings
    # are indistinguishable, so a save that did not say which it meant
    # would replay silently wrong on the first non-square board.
    column_first = (SAVE_HEADER_V3 in text and SAVE_HEADER_V4 not in text)
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
        elif line.startswith('Depth:'):
            try:
                out['depth'] = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith('SecondsPerMove:'):
            try:
                out['budget'] = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith('Training:'):
            out['training'] = line.split(':', 1)[1].strip()
        elif line.startswith('Winner:'):
            out['winner'] = line.split(':', 1)[1].strip()
        elif line.startswith('CurrentTurn:'):
            try:
                out['current'] = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith('Timeline:'):
            try:
                out['timeline'] = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
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
        cells = [cell_from_name(name, out['m'], out['n'], column_first)
                 for name in body_moves]
        if any(cell is None for cell in cells):
            return None
        out['moves'] = cells
    # WHERE THE CURSOR SAT. Everything after it is the future: real
    # moves, reachable with redo, which is what `Timeline` counts.
    # Absent (v1) or too large (a hand-edited file) means "all of it",
    # which is what every version before v5 meant anyway.
    current = out.get('current')
    if current is None or not (0 <= current <= len(out['moves'])):
        out['current'] = len(out['moves'])
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
                 train_budget=20.0):
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
        self.train_budget = train_budget
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
    #: Where trained weights are kept between runs.
    #:
    #: OVERRIDABLE, AND THE TESTS OVERRIDE IT. A test run used to write
    #: its own tiny builds -- rounds=1, games=2 -- into the repository
    #: beside the player's real ones, and a tool that globbed the
    #: directory then picked one up and reported a weight of +0.0531
    #: where the player's is +0.1249. A whole diagnosis was published
    #: from that file. Test output does not belong next to shipped
    #: artefacts, and a directory a person has to remember to clean is
    #: one that eventually gets committed.
    #: WHERE TRAINED WEIGHTS ARE KEPT.
    #:
    #: THE REPOSITORY COPY IS READ-ONLY, and that is the point. A test
    #: run once wrote its own tiny builds -- rounds=1, games=2 -- into
    #: `lgref/weights/mnk_cache/` beside the player's real ones, a tool
    #: globbed the directory and picked one up, and a diagnosis was
    #: PUBLISHED from an agent nobody plays. A session fixture was
    #: added to point the tests elsewhere, which fixed the tests and
    #: left every script and every interactive run free to do it again
    #: -- and one did, on 2026-10-25, committing three more.
    #:
    #: So writes go to a scratch directory unless the caller asks
    #: otherwise. Reads still check the repository first, so the shipped
    #: weights are found; only the WRITE side is redirected, which is
    #: the half that caused the damage.
    CACHE_DIR = os.environ.get(
        'MNK_CACHE_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'weights', 'mnk_cache'))

    #: Writes land here when `MNK_CACHE_DIR` is not set. `None` means
    #: "work it out on first use", so importing this module touches no
    #: filesystem.
    WRITE_DIR = None

    def _vocabulary_tag(self, rows, cols, k):
        """A short fingerprint of the FEATURE NAMES this brain uses.

        THE CACHE KEY MUST INCLUDE THE VOCABULARY. Weights are only
        meaningful for the feature set they were fitted on, and the set
        changed under this cache once already -- a feature was added,
        then removed, and a cache keyed only on the board would have
        handed the new extractor the old extractor's weights without
        anything saying so. That is the same silent-staleness failure
        the case study's loader has a whole audit for.
        """
        import hashlib

        probe = MNK(m=rows, n=cols, k=k)
        for cell in probe.get_all_legal_turns()[:2]:
            probe.execute_turn(cell)
        names = sorted(name for _owner, name in self.extractor(probe))
        digest = hashlib.sha1('|'.join(names).encode('utf-8'))
        return digest.hexdigest()[:8]

    def _cache_path(self, key):
        rows, cols, k = key
        return os.path.join(
            self.CACHE_DIR,
            '{0}x{1}_k{2}_r{3}_g{4}_s{5}{6}_{7}.json'.format(
                rows, cols, k, self.rounds, self.games, self.seed,
                '_leaf' if self.use_td_leaf else '',
                self._vocabulary_tag(rows, cols, k)))

    def _load_cached(self, key):
        """`(weights, scales)` from an earlier run, or None.

        ANY problem reading it means training again rather than playing
        on something half-read -- a corrupt cache must cost time, never
        correctness.
        """
        try:
            where = self._cache_path(key)
            if not os.path.exists(where):
                # A build this run made earlier, in the scratch
                # directory. The repository copy is preferred when both
                # exist, because that is the shipped one.
                scratch = os.path.join(self._write_dir(),
                                       os.path.basename(where))
                if os.path.exists(scratch):
                    where = scratch
            with open(where) as handle:
                payload = json.load(handle)
            weights = payload['weights']
            scales = payload.get('scales', {})
            if not isinstance(weights, dict) or not weights:
                return None
            return weights, scales
        except Exception:
            return None

    def _write_dir(self):
        """Where a newly trained build is stored.

        `MNK_CACHE_DIR` wins, so a test or a caller that has chosen a
        directory keeps it. Otherwise a scratch directory, never the
        repository -- see `CACHE_DIR`.
        """
        if os.environ.get('MNK_CACHE_DIR'):
            return self.CACHE_DIR
        if Brain.WRITE_DIR is None:
            import tempfile
            Brain.WRITE_DIR = os.path.join(tempfile.gettempdir(),
                                           'mnk-weight-cache')
        return Brain.WRITE_DIR

    def _store_cached(self, key, weights, scales):
        try:
            target = self._write_dir()
            if not os.path.isdir(target):
                os.makedirs(target)
            with open(os.path.join(
                    target,
                    os.path.basename(self._cache_path(key))), 'w') as handle:
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
                            quiescence=0)

        started = time.time()
        games = self.games
        history = run(make_game, self.extractor, rounds=self.rounds,
                      games_per_round=games, alpha=0.08,
                      epsilon=0.25, seed=self.seed,
                      max_turns=rows * cols + 2,
                      scales=scales, budget_seconds=self.train_budget,
                      searcher=searcher if self.use_td_leaf else None)
        weights = history[-1].weights
        elapsed = time.time() - started
        top = sorted(weights.items(), key=lambda kv: -abs(kv[1]))[:5]
        played = sum(1 for _ in history) and history[-1].games
        where = ('' if (rows, cols) == (m, n)
                 else ' on {0}x{1}'.format(rows, cols))
        lines = ['trained {0} games from zero in {1:.1f}s{2}, {3} features'
                 .format(played, elapsed, where, len(weights))]
        # A TRUNCATED TRAINING RUN MUST SAY SO. `train_budget` is a wall
        # clock that stops starting new games, so on a slower machine
        # the same settings and the same seed produce a DIFFERENT agent
        # -- and the old line reported the count it managed without
        # saying it was short of the count that was asked for, which
        # reads as a fact about the board rather than about the clock.
        #
        # Measured on this machine: the window's 6 rounds x 60 games
        # finish in 10.7 s against a 20 s budget, so the clock is inert
        # here. "Inert on the machine I measured" is not "inert", which
        # is why it is reported rather than assumed.
        asked = self.rounds * self.games
        if played < asked:
            lines[0] += ('   SHORT: the {0:.0f}s budget stopped this at '
                         '{1} of {2} games, so these weights are not the '
                         'ones the settings describe'
                         .format(self.train_budget or 0.0, played, asked))
        for name, raw in top:
            lines.append('   {0:<24} {1:+.3f}'.format(
                name, raw / (scales.get(name) or 1.0)))
        self.last_report = '\n'.join(lines)
        if log:
            log(self.last_report)
        self._store_cached(key, weights, scales)
        self._cache[key] = evaluate_with(weights)
        return self._cache[key]


def opening_prior(m, n, k, trials=400, seed=5):
    """Which moves keep turning up on the winning side, from random
    play under the rules.

    THE RULER FOR TIED MOVES, and it is learned rather than written
    down: nothing here knows what the centre of a board is. On 9x9 k=5
    it recovers it anyway -- correlation -0.55 with distance from the
    middle -- because more winning lines pass through the middle.
    Cached per board, because it costs 400 random games and the answer
    does not change.
    """
    from lgref.experiments.validate import (configuration_centrality,
                                             outcome_weights)

    key = (m, n, k, trials, seed)
    if key in _PRIORS:
        return _PRIORS[key]
    game = MNK(m=m, n=n, k=k)
    enumerate_wins = getattr(game, 'winning_configurations', None)
    if enumerate_wins is not None:
        # EXACT AND INSTANT, from the win condition itself. Sampling
        # the same quantity cost 10.4 seconds on 19x19 -- which a
        # person waiting for a board can feel, and a reviewer did --
        # and was NOISE at that size: 400 playouts give a top win rate
        # of 0.615 +/- 0.038 while the top ten cells span 0.033, so the
        # best-looking cell was essentially random. Measured on the
        # agent, it opened at 13,12 instead of 10,10.
        _PRIORS[key] = configuration_centrality(enumerate_wins())
    else:
        # The general fallback, for a game that cannot enumerate its
        # own wins: play at random and see which moves keep turning up
        # on the winning side. Needs only the rules.
        _PRIORS[key] = dict(
            (move, wins / float(seen) if seen >= 5 else 0.0)
            for move, (wins, seen) in outcome_weights(
                lambda *a, **kw: MNK(m=m, n=n, k=k), trials=trials,
                seed=seed).items())
    return _PRIORS[key]


def tie_breaker(game, prior=None):
    """Rank tied root moves by whether they are ACTIVE.

    TWO LEVELS, AND NEITHER SHIPS -- for different reasons, which is
    the whole finding. `prior=None` gives the THREAT level alone (§1a
    of `docs/candidate-designs.md`); passing a `prior` adds the
    CENTRALITY level (§1b).

    §1a IS ADMISSIBLE AND INERT. Its premises hold -- confined to ties,
    monotone on the active-move rate -- but it can never act, because
    the two conditions are disjoint and the rules make them so. A move
    is active only if some winning configuration already holds k-2
    marks; a tie at the root happens only while the line counts have
    not separated the candidates, which is the first few plies, before
    any line can hold k-2. Measured on 19x19 k=5: 121 moves tied at the
    maximum on an empty board and NONE of them active; by 24 marks the
    tie is down to one or two and all of them are active. Zero of 66
    positions had a tie containing both.

    §1b IS THE ONLY LEVEL THAT CAN ACT, and it has no invariant: there
    is no statement of the rules saying the more central of two moves
    the evaluation calls equal is never worse.

    A CORRECTION TO WHAT THIS DOCSTRING USED TO SAY. It credited the
    threat level with recovering a 0.8-point midgame tempo loss the
    centrality level had caused -- "a tie that used to pick a
    threatening move by chance now picks one whenever the tie contains
    one. Re-measured, tempo came back IDENTICAL on every seed." The
    tempo did come back identical. The threat level cannot be why,
    because it never fires; that movement was seed noise. Kept
    reachable, and listed in `OFF`, because the opening defect is still
    open and this is still its only known lever.

    WHY THE AGENT NEEDED THIS AT ALL. Measured on 13x13 k=5 across four
    training seeds, the plain agent's opening placement is 15.5% -- a
    random player scores 50%, so it was markedly WORSE than random at
    choosing where to open. Not because the evaluation preferred the
    edges, but because it could not tell the candidates apart: the line
    count saturates, the top moves tie, and the one taken was whichever
    the generator listed first.

    WHAT RANKING BY THE PRIOR MEASURED. It fixed the opening
    (15.5% -> 74.8% against a circular ruler; +7.0 points against an
    independent one) and cost 0.8 points of midgame tempo, down on all
    four seeds -- inside the noise floor and a consistent direction,
    which is not good enough under a rule that says a version ships by
    losing nothing.
    """
    from lgref.experiments.mcts import describe
    from lgref.experiments.validate import threat_count

    # CAN ANY SINGLE MOVE CHANGE THE THREAT COUNT AT ALL? If not, the
    # threat level is the same for every move and cannot reorder
    # anything, so computing it is pure cost.
    #
    # THIS WAS A 20x SLOWDOWN AND IT BROKE THE OPENING. `threat_count`
    # is the general instrument and it clones the game once per legal
    # move, so ranking one candidate on a 19x19 board costs 0.108s and
    # a full root sweep 9.74s against 0.47s without it. The window's
    # 5-second budget then could not finish even depth 1 -- 143 of 361
    # root moves -- so the agent played the best of an arbitrary
    # partial set and stopped opening in the centre. The fix for an
    # opening was breaking the opening.
    #
    # The precondition comes from the win condition: a move can create
    # an immediate win only by taking a configuration from k-2 marks to
    # k-1, and can remove one only where k-1 already stands. So if no
    # configuration holds k-2 of ONE side with the rest empty, no move
    # changes anything and the level is provably constant. On an empty
    # board that is immediate, which is exactly where the cost hurt.
    def threats_reachable(state):
        enumerate_wins = getattr(state, 'winning_configurations', None)
        if enumerate_wins is None:
            return True             # cannot prove it; pay the cost
        for configuration in enumerate_wins():
            held = {}
            for position in configuration:
                mark = state.cells[position]
                if mark is not None:
                    held[mark] = held.get(mark, 0) + 1
            if len(held) == 1:
                owner, count = next(iter(held.items()))
                if count >= len(configuration) - 2:
                    return True
        return False

    live = threats_reachable(game)

    me = game.current_player
    if live:
        probe = game.copy()
        probe.execute_turn(game.get_all_legal_turns()[0])
        opponent = probe.current_player
        was_mine = threat_count(game, me)
        was_theirs = threat_count(game, opponent)
    else:
        opponent = None
        was_mine = was_theirs = 0
    # THE PRIOR IS AN OPENING INSTRUMENT AND MUST NOT REACH PAST ONE.
    # It is learned from whole random games, so it says which squares
    # are good IN GENERAL -- and in an endgame the answer is not
    # general, it is concrete. Measured on 5x5 k=4 across four training
    # seeds: consulting it everywhere cost 0.9 points of optimal-action
    # rate against exact play in the endgame band, down on all four
    # seeds, while gaining 15 points of opening placement. A gain and a
    # loss is not strictly better.
    #
    # THE BOUNDARY COMES FROM THE WIN CONDITION. With fewer than `k`
    # marks on the board no line can be completed by anybody, so there
    # is no concrete calculation for the prior to contradict; past that
    # point tactics exist and the search's own ordering knows more than
    # a general statistic does. `k` is the rule, not a threshold anyone
    # chose.
    marks = sum(1 for cell in game.cells if cell)
    consult_prior = prior is not None and marks < game.k
    known = {}

    # ONLY THE CONFIGURATIONS THROUGH THE PLAYED POSITION CAN CHANGE,
    # which is what makes this affordable. `threat_count` is the
    # general instrument and rescans every legal move, so ranking one
    # candidate on a 19x19 board costs 0.108s; the search then managed
    # 641 nodes in five seconds against 347 legal moves and could not
    # finish a ply. Reading the lines through one cell is a few dozen
    # checks. `test_no_lag.py` asserts the two agree move for move.
    through = _lines_through(game)

    def rank(turn):
        key = describe(turn)
        if key not in known:
            if live and through is not None:
                active = False
                for configuration in through.get(turn, ()):
                    mine = theirs = empty = 0
                    for position in configuration:
                        mark = game.cells[position]
                        if mark is None:
                            empty += 1
                        elif mark == me:
                            mine += 1
                        else:
                            theirs += 1
                    if theirs == 0 and empty == 2 and mine == len(
                            configuration) - 2:
                        active = True   # my move makes it one-from-won
                        break
                    if mine == 0 and empty == 1 and theirs == len(
                            configuration) - 1:
                        active = True   # my move takes their win away
                        break
                    if theirs == 0 and empty == 1 and mine == len(
                            configuration) - 1:
                        active = True   # my move wins outright
                        break
            elif live:
                nxt = game.copy()
                nxt.execute_turn(turn)
                active = (threat_count(nxt, me) > was_mine
                          or threat_count(nxt, opponent) < was_theirs
                          or (nxt.is_game_over()
                              and getattr(nxt, 'winner', None) == me))
            else:
                active = False
            square = prior.get(key, 0.0) if consult_prior else 0.0
            known[key] = (1 if active else 0, square)
        return known[key]
    return rank


def _lines_through(game):
    """position -> the winning configurations containing it.

    Built once per board and kept, because it is a fact about the rules
    and not about the position. `None` for a game that cannot enumerate
    its winning configurations, which sends the caller back to the
    general instrument.
    """
    enumerate_wins = getattr(game, 'winning_configurations', None)
    if enumerate_wins is None:
        return None
    key = (game.m, game.n, game.k)
    if key not in _LINES_THROUGH:
        index = {}
        for configuration in enumerate_wins():
            for position in configuration:
                index.setdefault(position, []).append(configuration)
        _LINES_THROUGH[key] = index
    return _LINES_THROUGH[key]


#: WHETHER THE PLAYER USES THE OPENING TIE-BREAK. OFF, at the
#: reviewer's instruction, until it has been shown strictly better
#: against a search that works.
#:
#: WHY THE EVIDENCE FOR IT IS VOID. Every gate number quoted for the
#: tie-break -- +7.0 points of opening placement on 13x13, nothing
#: lost elsewhere -- was measured while the tie-break itself was
#: costing 0.108s per ranked candidate. The search could not finish
#: one ply on a 19x19 board, so those runs describe an agent reduced
#: to depth 1 by the very thing being measured. They are not evidence
#: about the agent that exists now, and a number measured on a
#: crippled search is not a weaker argument -- it is a different
#: claim.
#:
#: The code and its tests stay. `tools/phase_rates.py` re-gates it
#: against the repaired search, and this flips back when that lands
#: clean -- not before.
TIE_BREAK_ENABLED = False

#: Line indices, one per board. See `_lines_through`.
_LINES_THROUGH = {}

#: Opening priors, one per board. Module level so a window that changes
#: board size and comes back does not pay for the same 400 games twice.
_PRIORS = {}


def make_player(kind, evaluate, depth, rng, prior=None,
                tie_break=False):
    """A callable `(game) -> turn`, or None for a human.

    `tie_break` turns the THREAT level on (§1a, which carries a
    certificate). `prior` additionally turns the CENTRALITY level on
    (§1b, which does not) and is left at None by the player. They are
    separate arguments because they are separate claims.
    """
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
        searcher = Searcher(
            evaluate, max_depth=depth, quiescence=0,
            tie_break=(tie_breaker(game, prior)
                       if (tie_break or prior is not None) else None))
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
    # A WARNING, NOT AN ERROR. Used for the depth note when the
    # estimated move time passes a minute: the setting is allowed, it
    # just costs something the person should see first.
    'warn': (162, 92, 20),
    'first': (37, 92, 168),
    'second': (176, 58, 46),
    'hover': (236, 240, 247),
    'win': (252, 243, 207),
    'last': (176, 206, 240),
    'button': (243, 242, 238),
    'button_on': (37, 92, 168),
    'button_edge': (210, 207, 200),
    # DIM ON BOTH BOARDS: the labels are drawn inside the playing area,
    # over the pale squares AND over the wood of the Go board, so the
    # colour has to be dark enough to read on the lighter one without
    # competing with the stones on either.
    'coord': (138, 124, 100),
}


def side_label(side, style):
    """What to call a player. The game does not change; the name does."""
    if style == 'go':
        return 'Black' if side == FIRST else 'White'
    return side.upper()


def play_window(m, n, k, brain, depth, sides, style='squares',
                probe=None):
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

    THERE IS NO `move_budget`. It was a per-move wall clock, and it is
    gone from the searcher outright -- see `Searcher.__init__`.
    It mattered more than a setting usually does: with a clock, the
    background search and the blocking search could reach DIFFERENT
    DEPTHS from the same position, because the drawing loop competes
    for the interpreter lock and the clock fired a ply earlier. The
    responsiveness tests caught exactly that -- same move, "depth 2"
    one way and "depth 1" the other -- which is the concrete form of
    why the clock had to go before the search could move off the UI
    thread. See `docs/candidate-designs.md` §6.
    """
    import random

    import pygame

    pygame.init()
    pygame.display.set_caption('m,n,k  --  the general agent')

    state = {'m': m, 'n': n, 'k': k, 'depth': depth, 'style': style,
             'sides': dict(sides), 'screen': 'setup',
             'status': '', 'thinking': False, 'last': None,
             'auto': True, 'flash': '', 'confirm': None, 'mode': None,
             #: True once the depth stepper has been used, after which
             #: the depth stops following the board size.
             'depth_set': False}
    rng = random.Random(0)

    #: Tall enough for the status, the detail line, the move text, a
    #: row of buttons, the transient message BELOW them and the key
    #: legend below that. It was 132, which fit two buttons; the legend
    #: now sits under six, and the message line under those.
    PANEL = 190
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
        """Recompute the board box from an actual window size.

        IGNORED WHILE FULL SCREEN. The size is the display's and is not
        up for negotiation; recomputing from it only sets the mode
        again, which reports another resize. That loop was the flicker.
        """
        if state.get('fullscreen'):
            return cell, surface, width, height
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

        AND IT SETS THE MODE ONLY WHEN THE MODE CHANGES. `set_mode`
        makes the driver report a resize; a resize recomputed the board
        and called `set_mode` again, and that cycle is what flickered --
        on entering full screen until it happened to settle, and again
        every time the window was MOVED, because a move reports a
        resize too even though nothing resized. The last mode asked for
        is remembered, and an identical request is served from the
        surface already on screen.
        """
        if state.get('fullscreen'):
            # AT THE DISPLAY'S OWN SIZE, once. Asking for a smaller
            # full-screen surface makes the driver choose a mode, hand
            # back a size that is not the one requested, and report a
            # resize about it -- so the next pass asks for something
            # different again.
            if state.get('mode') != 'full':
                state['mode'] = 'full'
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                screen = pygame.display.get_surface()
            wide, tall = screen.get_size()
            state['box'] = max(240, min(wide, tall - PANEL))
            return geometry()[0], screen, wide, tall
        global_cell, w, h = geometry()
        if state.get('mode') != (w, h):
            state['mode'] = (w, h)
            screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        else:
            screen = pygame.display.get_surface()
        return global_cell, screen, w, h

    def enter_setup():
        """Back to the fixed setup size, so the card is never drawn into
        a window shaped for a 20x20 board."""
        _abort_think()
        state['screen'] = 'setup'
        state['mode'] = None
        return pygame.display.set_mode(SETUP_SIZE, pygame.RESIZABLE)

    #: Which stepper is being held down, and when it next repeats.
    held = {'name': None, 'step': 0, 'next': 0}

    def jump_setting(name, to_max):
        """Put one setting at its own limit.

        THE LIMIT COMES FROM THE BOUNDS TABLE, not from a number typed
        here, so a setting whose range changes does not need this
        touched as well. `k` is then re-clamped against the board for
        the same reason `bump` does it: a 20-in-a-row condition on a
        3x3 is a game nobody can win.
        """
        low, high = SETTING_BOUNDS[name]
        state[name] = clamp_setting(name, high if to_max else low)
        state['k'] = clamp_setting('k', state['k'], state['m'], state['n'])
        # SAME RULE AS `bump`: a jump is still somebody using the
        # stepper, and a jump on the board still moves the board.
        if name == 'depth':
            state['depth_set'] = True
        elif name in ('m', 'n') and not state.get('depth_set'):
            state['depth'] = affordable_depth(state['m'], state['n'])

    def bump(name, step):
        """Move one setting, then re-clamp the win condition.

        `k` depends on the board: a 3-in-a-row condition is impossible
        on a 2x2, so shrinking the board has to pull `k` down with it or
        Start builds a game nobody can win.
        """
        state[name] = clamp_setting(name, state[name] + step)
        state['k'] = clamp_setting('k', state['k'], state['m'], state['n'])
        # THE DEPTH FOLLOWS THE BOARD UNTIL SOMEBODY TOUCHES IT. A
        # board three times the cells is a search the cube of that, so
        # a depth that was instant on 9x9 is forty-seven seconds on
        # 19x19 -- see `affordable_depth`. Once the stepper has been
        # used the number is the user's and is left alone.
        if name == 'depth':
            state['depth_set'] = True
        elif name in ('m', 'n') and not state.get('depth_set'):
            state['depth'] = affordable_depth(state['m'], state['n'])

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

    def rebuild(log_status=True, reset_board=True):
        """Train if needed, build the players, and start a fresh game.

        `reset_board=False` keeps the position that is already on the
        board, which is what LOADING needs. Without it, `load_into`
        pasted the position, then called this to train for the new
        board size, and this threw the position away:

            game[0] = MNK(...)        # a fresh, EMPTY board

        `history` and `played` survived, so the window showed an empty
        board and pressing UNDO popped back to the loaded position --
        which is precisely how the reviewer described it. The replay is
        expensive to redo and there is no reason to: the only thing
        loading needs from here is the trained evaluation and the
        players built around it.
        """
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
        # NO PRIOR. The threat level ships (§1a); the centrality level
        # (§1b) has no invariant and stays off, so the player is given
        # a tie-break that reads only whether a move makes a threat or
        # removes one.
        players[0] = {side: make_player(kind, evaluate[0],
                                        state['depth'], rng,
                                        tie_break=TIE_BREAK_ENABLED)
                      for side, kind in state['sides'].items()}
        _abort_think()
        if reset_board:
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
        draw_coordinates()

    def draw_coordinates():
        """Column numbers along the bottom, row numbers up the left --
        the same two edges the case study labels, so a coordinate read
        off one board is read the same way off the other.

        Drawn INSIDE the board rather than in a margin. A margin would
        move every cell, and every cell's position is also its
        hit-test; labels that cost a geometry change are labels that
        can put a stone one square from where it was clicked.
        """
        rows, cols = state['m'], state['n']
        if cell < 20:
            # Below this the digits are wider than the cell and would
            # read as noise over the stones.
            return
        size = max(9, min(13, int(cell * 0.3)))
        glyphs = font(size)
        for row in range(rows):
            label = glyphs.render(str(rows - row), True, PALETTE['coord'])
            surface.blit(label, (3, row * cell + 2))
        bottom = (rows - 1) * cell
        for col in range(cols):
            label = glyphs.render(str(col + 1), True, PALETTE['coord'])
            width_, height_ = label.get_size()
            surface.blit(label, (col * cell + cell - width_ - 3,
                                 bottom + cell - height_ - 2))


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
        # THE DEPTH IS THE DEPTH. This line used to have to say
        # whether it was exact or a ceiling, because under a per-move
        # clock the depth reached was whatever fitted and "depth 4"
        # beside a move that reached 6 read as a bug. There is no clock
        # now, so there is one number and it is the truth.
        detail = '{0}x{1}  k={2}   depth {3}'.format(
            state['m'], state['n'], state['k'], state['depth'])
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
        pending = state.get('confirm')
        for name, caption, enabled in (
                ('setup', 'Setup', True),
                ('restart', 'Restart', True),
                ('undo', 'Undo', bool(history)),
                ('redo', 'Redo', bool(future)),
                ('copy', 'Copy', True),
                ('paste', 'Paste', True)):
            rect = pygame.Rect(x, top + 88, 66, 28)
            # A BUTTON THAT IS ASKING says so on its face, and is the
            # thing that must be clicked again. A confirmation written
            # only in the message line is a confirmation a reviewer
            # answers by clicking the same place twice without reading.
            button(rect, 'Sure?' if pending == name else caption,
                   active=(pending == name), small=True)
            if not enabled:
                # Drawn dimmed rather than hidden, so the row does not
                # reflow under the cursor as moves are made.
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade.fill((255, 255, 255, 150))
                surface.blit(shade, rect.topleft)
            hits.append((name, rect))
            x += 72
        # THE TRANSIENT MESSAGE SITS BELOW THE BUTTONS, on a line of
        # its own. It used to share the line above them with the move
        # text, so copying a game REPLACED "O played 10,10 (optimal)"
        # with "copied the game to the clipboard" -- the one piece of
        # information a reviewer was reading, overwritten by an
        # acknowledgement they already knew.
        flash = state.get('flash', '')
        if flash:
            surface.blit(font(13).render(flash, True, PALETTE['ink']),
                         (16, top + 120))
        # SPELLED OUT, not drawn as arrows. The arrow characters came
        # out as empty boxes in the rendered legend: the system font
        # this falls back to has no glyph for them, and a legend that
        # names a key with a character the reader cannot see is worse
        # than no legend.
        surface.blit(font(12).render(
            'S setup   R restart   Left/Right step   Home/End jump   '
            'C copy   V paste   F11 full screen   Q quit', True,
            PALETTE['muted']), (16, top + 142))
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
        # JUMP TO EITHER END. Holding `+` from 2 to 20 is eighteen
        # repeats and about two seconds of waiting, and a reviewer who
        # wanted a 19x19 board had to do it three times. Scrolling over
        # the value helps and still has to be aimed; these do not.
        # Spelled out rather than drawn as arrows -- the fallback font
        # has no glyph for those, as the key legend found out.
        lowest = button(pygame.Rect(x + 186, y, 30, 28), 'min',
                        small=True)
        highest = button(pygame.Rect(x + 220, y, 30, 28), 'max',
                         small=True)
        if layout is not None:
            layout['label:' + label] = pygame.Rect((x, y + 7),
                                                   glyph.get_size())
            layout['minus:' + label] = minus
            layout['value:' + label] = box
            layout['plus:' + label] = plus
            layout['min:' + label] = lowest
            layout['max:' + label] = highest
        # The VALUE BOX is returned too: scrolling over it adjusts the
        # setting, which is the fastest way to move a number twenty
        # steps and the reason a reviewer asked for something better
        # than clicking `+` eighteen times.
        return minus, plus, box, lowest, highest

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
        # NO sec/move ROW. The per-move clock is gone from the
        # searcher entirely, so a stepper for it would set a number
        # that nothing reads.
        for name, caption in (('m', 'rows'), ('n', 'columns'),
                              ('k', 'in a row'), ('depth', 'depth')):
            shown = str(state[name])
            hits[name] = stepper(card.x + 20, cursor, caption, shown,
                                 layout)
            if name == 'depth':
                # WHAT THE DEPTH WILL COST, beside the setting it
                # describes rather than on the line at the bottom of
                # the card -- that line already carries the grading
                # note, and a second clause there ran straight under
                # the Load button, which is the overlap this screen was
                # fixed for once already.
                #
                # THE STEPPER GOES TO 10 AND IS NOT CAPPED. Capping it
                # would take away a setting somebody might want on a
                # tiny board; saying what it costs takes nothing away.
                # A reviewer asked whether a depth-10 move taking
                # forever was normal -- it is, and the screen should
                # have said so before they picked it.
                seconds = estimated_move_seconds(state['m'], state['n'],
                                                 state['depth'])
                words = describe_move_cost(seconds)
                text_at('depth_note', (card.x + 310, cursor + 7),
                        font(12).render(
                            words if words == 'instant'
                            else '~{0}'.format(words), True,
                            PALETTE['warn'] if seconds > 60
                            else PALETTE['muted']))
            cursor += ROW

        text_at('style_label', (card.x + 310, card.y + 83),
                font(13).render('board style', True, PALETTE['muted']))
        hits['style'] = []
        x = card.x + 310
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
            'hold +/- to repeat, scroll over a value, or jump with '
            'min/max', True, PALETTE['muted']))
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

    def press(name):
        """Act on one play-screen button. True if the screen changed.

        NAMED AND EXPOSED ON PURPOSE. This was inline in the event
        loop, so the only way to reach it was to post a mouse event --
        and the confirmation tests called `guard()` directly instead,
        which meant the CLICK PATH for Setup and Restart was never
        exercised by anything. A guard can be perfect and still never
        run if the dispatch around it is wrong, and that gap is
        precisely the shape of "the confirmation is gone".
        """
        if name == 'setup':
            if guard('setup', lambda: True):
                enter_setup()
                return True
            return False
        if name == 'restart':
            guard('restart', restart)
            return False
        # EVERY OTHER BUTTON DISARMS A PENDING ASK. Clicking elsewhere
        # is an answer of no, so a mis-click on a neighbour cancels
        # rather than confirming.
        state['confirm'] = None
        if name == 'undo':
            undo()
        elif name == 'redo':
            redo()
        elif name == 'copy':
            copy_game()
        elif name == 'paste':
            paste_game()
        return False

    def needs_confirm():
        """Whether there is a game to lose. An empty board and a
        finished game are both nothing to protect, and a confirmation
        that fires when there is nothing at stake trains the reviewer
        to click through it."""
        return bool(played) and not game[0].is_game_over()

    def guard(name, action):
        """Run `action`, or ask first.

        Restart and Setup both discard the position, and both sat one
        click from Undo on a row of six identical buttons with no way
        back: the move list is gone, so undo cannot recover it. The
        first click arms, the second acts, and arming ANY of them
        disarms the other -- so a mis-click on the neighbour cancels
        rather than confirming.
        """
        if state.get('confirm') == name or not needs_confirm():
            state['confirm'] = None
            return action()
        state['confirm'] = name
        state['flash'] = ('{0} discards this game -- click it again to '
                          'confirm'.format(name))
        return None

    def restart():
        # DROP A MOVE IN FLIGHT. `rebuild`, `undo`, `redo`, a human move
        # and the setup screen all abort a pending search; this did not,
        # so an agent thinking about the position being thrown away
        # could land its answer on the fresh board -- a stone appearing
        # from nowhere one frame after Restart.
        _abort_think()
        game[0] = MNK(m=state['m'], n=state['n'], k=state['k'])
        del history[:]
        del future[:]
        del played[:]
        state['last'] = None
        state['note'] = ''
        state['flash'] = ''
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
        # DROP A MOVE IN FLIGHT. Without this, an agent that was
        # thinking about the position being undone can land its answer
        # onto the board the person is now looking at.
        _abort_think()
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
        state['flash'] = 'undone'
        state['status'] = describe_turn()
        return True

    def redo():
        """Step forward far enough that it is a HUMAN's turn again.

        THE MIRROR OF `undo`, WHICH IT WAS NOT. Undo steps back past
        the agent's reply so the turn comes back to the person -- two
        plies. Redo stepped forward exactly one. So undo once, redo
        once, and the board did not return to where it started: it sat
        one ply along, with the agent to move, in a position the person
        had never been handed. Pressing redo again then played the
        agent's old reply and the two stacks were out of step for the
        rest of the game.

        The symmetry is the rule: whatever undo steps over, redo steps
        back over. With no human on either side there is nobody to hand
        the turn to, so one ply goes forward, matching undo's one ply
        back.
        """
        if not future:
            return False
        _abort_think()
        anyone_human = any(players[0].get(side) is None
                           for side in (FIRST, SECOND))
        stepped = False
        while future:
            move = future[-1]
            if move is None or move not in game[0].get_all_legal_turns():
                break
            future.pop()
            history.append(game[0].copy())
            game[0].execute_turn(move)
            played.append(move)
            state['last'] = move
            stepped = True
            if not anyone_human or game[0].is_game_over():
                break
            if players[0].get(game[0].current_player) is None:
                break
        if not stepped:
            return False
        state['flash'] = 'redone'
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
            # `reset_board=False` OR THE POSITION JUST LOADED IS THROWN
            # AWAY. This said `rebuild()`, which replaced `game[0]` with
            # an empty board while `history` and `played` survived -- so
            # the window came up blank and UNDO revealed the game.
            rebuild(reset_board=False)
        return True

    def training_text():
        """The parameters the evaluation was fitted with."""
        return ('rounds={0} games={1} seed={2} td_leaf={3} '
                'budget={4:.0f}s'.format(
                    brain.rounds, brain.games, brain.seed,
                    'yes' if brain.use_td_leaf else 'no', brain.train_budget))

    def settings_text():
        return {'depth': state['depth'], 'training': training_text()}

    def copy_game():
        text = save_text(game[0], state['m'], state['n'], state['k'],
                         state['style'], played, state['sides'],
                         settings_text(), future)
        state['flash'] = ('copied the game to the clipboard'
                          if clipboard.copy_text(text)
                          else 'the clipboard is unavailable here')

    def paste_game():
        loaded = load_text(clipboard.read_text() or '')
        if loaded is None:
            state['flash'] = 'the clipboard holds no m,n,k save'
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
        # THE PLAY SETTINGS COME BACK TOO. The same moves at depth 2 and
        # at depth 6 are two different agents playing, so a save that
        # restores the board and not the depth restores a position
        # rather than a game.
        # `budget` IS READ AND IGNORED. Saves written before the
        # per-move clock was removed carry a `SecondsPerMove` line, and
        # an older file must still load -- it just no longer sets
        # anything, because there is nothing to set.
        if loaded.get('depth') is not None:
            state['depth'] = clamp_setting('depth', loaded['depth'])
            # A DEPTH FROM A FILE IS THE USER'S DEPTH. Without this the
            # depth stops following the board only when the STEPPER is
            # touched, so loading a 19x19 game saved at depth 5 and then
            # nudging the board size would silently drop it back to the
            # board's default -- replacing the agent the save recorded.
            state['depth_set'] = True
        # THE TRAINING PARAMETERS ARE REPORTED, NOT APPLIED. Applying
        # them would let a pasted file start a three-minute retrain
        # with nothing asking first -- and the one thing a reviewer has
        # said twice about this window is that it must not go away and
        # think. Reported only when they DIFFER, because an
        # acknowledgement that is always there is read as decoration.
        trained = ''
        if loaded.get('training') and loaded['training'] != training_text():
            trained = '   (was trained {0})'.format(loaded['training'])
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
        # BACK TO WHERE THE CURSOR WAS. The save carries the whole
        # timeline and says how much of it was applied, so the moves
        # after that point are stepped back off -- which leaves them on
        # the redo stack, exactly where redo expects to find them.
        # Loading used to apply everything and lose the distinction.
        cursor = loaded.get('current')
        if cursor is not None:
            while len(played) > cursor and history:
                future.append(played.pop())
                game[0] = history.pop()
            state['last'] = played[-1] if played else None
        state['auto'] = False
        short = len(kept) < len(loaded['moves'])
        ahead = len(kept) - len(played)
        state['flash'] = 'loaded {0} move{1}{2}{3}{4}'.format(
            len(played), '' if len(played) == 1 else 's',
            '   {0} ahead (redo)'.format(ahead) if ahead > 0 else '',
            ' (the rest did not fit this board)' if short else '',
            trained)
        state['status'] = describe_turn()
        return True

    # ---- thinking off the UI thread ----------------------------------
    #
    # WHY THIS EXISTS. This function used to choose AND apply in one
    # call, and the event loop called it directly, so for the whole
    # search no event was read: undo, redo, the mode buttons and the
    # close box all did nothing until the computer had finished. Royal
    # Chess had the same defect and fixed it (`src/ai_controller.py`,
    # `tests/test_async_thinking.py`); this window never got the same
    # treatment, and removing the per-move clock made its freeze
    # longer, not shorter.
    #
    # TWO SLOW PARTS, NOT ONE. The search is the obvious one. The other
    # is `grade`, which runs an exact solver below `GRADE_CELL_LIMIT`
    # empty cells -- bounded, but exponential inside that bound -- and
    # it ran on the UI thread straight after the move. Both go on the
    # worker.
    #
    # NO DATA RACE TO ARRANGE, which is why this is simpler than the
    # Royal Chess version. An m,n,k turn is a plain cell index, so the
    # worker's answer is already a description and needs no resolving
    # against freshly enumerated turns; and it works on `copy()` so the
    # board being drawn is never touched.
    think = {'thread': None, 'result': None, 'generation': 0,
             'switch': None}

    #: THE GRADE IS AN ANNOTATION, NOT PART OF CHOOSING A MOVE, so it
    #: gets its own worker and the move does not wait for it.
    #:
    #: `grade` runs an exact solver to label the move "(optimal)" or
    #: "(NOT optimal)". It used to run after the move was already
    #: chosen, which meant the move could not APPEAR until the label
    #: did. Measured: 8.98 s on a full 4x4 board -- the default this
    #: window opens at -- 7.72 s at 15 empty cells on 5x5 and over 20 s
    #: at 16.
    #:
    #: `parts` is the note with a hole where the verdict goes, so a
    #: late verdict is spliced in rather than the note rebuilt from
    #: state that has since moved on. A stale one is dropped by
    #: generation, exactly as a stale move is.
    judge = {'thread': None, 'result': None, 'generation': 0,
             'parts': None}

    #: How long a thread may hold the interpreter lock while a search
    #: runs. The Royal Chess measurement that chose this value: at the
    #: 5 ms default the drawing loop saw a 54 ms worst-case gap between
    #: frames; at 1 ms, 13.8 ms. Shorter buys more frames and a WORSE
    #: tail, because the switching itself starts to cost.
    switch_interval = 0.001

    def _begin_think():
        """Start an agent move in the background. True if started."""
        import threading

        current = game[0]
        if current.is_game_over():
            state['status'] = describe_turn()
            return False
        agent = players[0].get(current.current_player)
        if agent is None:
            return False
        if think['thread'] is not None:
            return False
        state['thinking'] = True
        state['status'] = '{0} thinking...'.format(
            side_label(current.current_player, state['style']))
        before = current.copy()
        working = current.copy()
        think['result'] = None
        think['generation'] += 1
        generation = think['generation']

        def work():
            try:
                move = agent(working)
                answer = (move, getattr(agent, 'last_depth', 0))
            except Exception:
                answer = None
            if generation == think['generation']:
                think['result'] = answer

        think['switch'] = sys.getswitchinterval()
        sys.setswitchinterval(switch_interval)
        think['thread'] = threading.Thread(target=work)
        think['thread'].daemon = True
        think['thread'].start()
        return True

    def _restore_switch():
        if think['switch'] is not None:
            sys.setswitchinterval(think['switch'])
            think['switch'] = None

    def _thinking_done():
        """True once the worker has finished, however it finished."""
        thread = think['thread']
        return thread is not None and not thread.is_alive()

    def _land_think():
        """Apply the move the worker chose. True if one was applied."""
        answer = think['result']
        # READ BEFORE `commit`, which advances the side to move.
        mover = game[0].current_player
        think['thread'] = None
        think['result'] = None
        _restore_switch()
        state['thinking'] = False
        if answer is None:
            state['status'] = describe_turn()
            return False
        move, reached = answer
        before = game[0].copy()
        commit(move)
        # IN COORDINATES, not the internal cell index. This line read
        # "White played 179", which is a row-major offset into a flat
        # list -- an implementation detail of the board representation,
        # shown to someone who wanted to know where the stone went.
        #
        # WRITTEN WITHOUT THE VERDICT FIRST. The move is known now; the
        # label may take seconds, and nobody should wait for a label to
        # see where the stone went.
        head = '{0} played {1}'.format(
            side_label(mover, state['style']),
            cell_name(move, state['m'], state['n']))
        tail = '   depth {0}'.format(reached) if reached else ''
        judge['parts'] = (head, tail)
        state['note'] = head + tail
        state['status'] = describe_turn()
        _begin_judge(before, move)
        draw()
        return True

    def _begin_judge(before, move):
        """Grade the move that just landed, in the background."""
        import threading

        judge['generation'] += 1
        generation = judge['generation']
        judge['result'] = None

        def work():
            try:
                verdict = grade(before, move)
            except Exception:
                verdict = ''
            if generation == judge['generation']:
                # A TUPLE, so an empty verdict is still an answer. A
                # bare '' would be indistinguishable from "not ready".
                judge['result'] = (verdict,)

        judge['thread'] = threading.Thread(target=work)
        judge['thread'].daemon = True
        judge['thread'].start()

    def _land_judge():
        """Splice a finished verdict into the note. True if spliced."""
        thread = judge['thread']
        if thread is None or thread.is_alive():
            return False
        answer = judge['result']
        parts = judge['parts']
        judge['thread'] = None
        judge['result'] = None
        if answer is None or parts is None:
            return False
        head, tail = parts
        # ONLY IF THE NOTE IS STILL THE ONE THIS VERDICT IS ABOUT. An
        # undo or another ply rewrites it, and a label from the
        # previous position is worse than no label.
        if state.get('note') != head + tail:
            return False
        state['note'] = head + answer[0] + tail
        return True

    def _abort_judge():
        judge['generation'] += 1
        judge['thread'] = None
        judge['result'] = None
        judge['parts'] = None

    def _abort_think():
        """Forget a move in flight, and any verdict in flight with it.

        The thread is not killed -- Python cannot -- so its answer is
        tagged with a generation and a stale one is dropped. Otherwise a
        move chosen for a position the user has since undone could be
        played onto the board they are now looking at.
        """
        think['generation'] += 1
        think['thread'] = None
        think['result'] = None
        _restore_switch()
        _abort_judge()
        state['thinking'] = False

    def advance():
        """One agent move, if it is an agent's turn -- BLOCKING.

        Kept as the composition of the three pieces above rather than
        as a second implementation, so there is exactly one search path
        and the blocking and background routes cannot drift. The event
        loop uses the pieces; tests and the probe seam use this.
        """
        if not _begin_think():
            return False
        draw()
        think['thread'].join()
        if not _land_think():
            return False
        # AND WAIT FOR THE VERDICT TOO. The background route fills the
        # label in later; this one is the reference the certificate
        # compares against, so it returns the finished note.
        if judge['thread'] is not None:
            judge['thread'].join()
            _land_judge()
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
                                            state['sides'],
                                            settings_text(), future),
                  'guard': guard, 'needs_confirm': needs_confirm,
                  'press': press,
                  'jump': jump_setting,
                  # THE THINKING PATH, both routes. `advance` blocks
                  # and is the composition of the other three, so a
                  # test can prove the background route plays the same
                  # move as the blocking one rather than taking it on
                  # trust -- which is the certificate this change
                  # ships on.
                  'advance': advance, 'begin_think': _begin_think,
                  'thinking_done': _thinking_done,
                  'land_think': _land_think, 'abort_think': _abort_think,
                  'land_judge': _land_judge, 'judging': judge,
                  'fit_to': fit_to, 'load': load_into}):
            running = False
    #: WHICH SCREEN `hits` DESCRIBES. The setup screen's hit map is a
    #: dict keyed by control name; the play screen's is a list of
    #: `(name, rect)`. Four handlers change `state['screen']` without
    #: rebuilding it -- Escape both ways, the Start button and the `S`
    #: key -- so the NEXT event in the same batch was dispatched
    #: against the wrong shape:
    #:
    #:     for name, rect in hits        -> ValueError, unpacking a key
    #:     hits['m']                     -> TypeError, indexing a list
    #:
    #: A single click delivers DOWN and UP together, and a key press
    #: landing in the same batch as a click is ordinary, so this was
    #: reachable rather than theoretical. Patching the four handlers
    #: would leave the fifth one somebody adds later, so the guard is
    #: central: before dispatching an event, rebuild the hit map if the
    #: screen has moved since it was built.
    hits_screen = state['screen']
    while running:
        events = pygame.event.get()
        for event in events:
            if hits_screen != state['screen']:
                hits = draw()
                hits_screen = state['screen']
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
                    if guard('setup', lambda: True):
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
                    if not state['fullscreen']:
                        # BACK TO THE SIZE IT HAD, not to whatever the
                        # full-screen box left behind.
                        state['box'] = BOARD_BOX
                        state['mode'] = None
                    if state['screen'] == 'play':
                        cell, surface, width, height = resize()
                    hits = draw()
                    continue
                elif state['screen'] == 'play':
                    if event.key == pygame.K_r:
                        guard('restart', restart)
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
                if state.get('fullscreen'):
                    # Nothing to do: the size is the display's.
                    continue
                if state['screen'] == 'play':
                    cell, surface, width, height = fit_to(event.size)
                elif surface.get_size() != (max(SETUP_SIZE[0], event.w),
                                            max(SETUP_SIZE[1], event.h)):
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
                for name in ('m', 'n', 'k', 'depth'):
                    minus, plus, box, lowest, highest = hits[name]
                    if (box.collidepoint(where) or minus.collidepoint(where)
                            or plus.collidepoint(where)
                            or lowest.collidepoint(where)
                            or highest.collidepoint(where)):
                        bump(name, 1 if event.y > 0 else -1)
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state['screen'] == 'setup':
                    bumped = False
                    for name in ('m', 'n', 'k', 'depth'):
                        minus, plus, _box, lowest, highest = hits[name]
                        # EITHER END IN ONE CLICK, checked before the
                        # steppers so a jump never also counts as a
                        # step.
                        if lowest.collidepoint(event.pos):
                            jump_setting(name, to_max=False)
                            bumped = True
                            continue
                        if highest.collidepoint(event.pos):
                            jump_setting(name, to_max=True)
                            bumped = True
                            continue
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
                        if rect.collidepoint(event.pos):
                            acted = True
                            if press(name):
                                surface = pygame.display.get_surface()
                    if acted:
                        hits = draw()
                        hits_screen = state['screen']
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
                            # A MOVE DISARMS A PENDING CONFIRMATION:
                            # playing on is an answer of no.
                            state['confirm'] = None
                            _abort_think()
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
        # THE SEARCH RUNS ON A WORKER and this loop keeps drawing. It
        # is two steps rather than one call: land an answer that is
        # ready, otherwise start thinking about the position on screen.
        # A VERDICT THAT HAS ARRIVED, spliced into the note. Checked
        # every frame and cheap: it is a thread liveness test.
        if state['screen'] == 'play':
            _land_judge()
        if state['screen'] == 'play' and _thinking_done():
            if _land_think():
                # Let a human see an agent-vs-agent game unfold.
                if all(players[0].get(s) is not None
                       for s in (FIRST, SECOND)):
                    pygame.time.wait(220)
        elif (state['screen'] == 'play' and not state['thinking']
                and state.get('auto', True)):
            _begin_think()
        hits = draw()
        hits_screen = state['screen']
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
    parser.add_argument('--depth', type=int, default=None,
                        help='search depth; the default is read from the '
                             'board size (see affordable_depth)')
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
    # ZERO MEANS NO CLOCK, and that is the default now rather than a
    # setting somebody has to find. A per-move budget could only ever
    # take depth AWAY from the depth that was asked for -- see
    # `Searcher.budget` -- and which ply it took depended on what else
    # the machine was running. Measured on 13x13: the clock cut depth 3
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
    # THE BOARD CHOOSES THE DEPTH unless the command line did. See
    # `affordable_depth`: a 19x19 move at depth 3 is 46.70 s where the
    # same depth on 9x9 is 0.48 s, so one number cannot serve both.
    depth = (args.depth if args.depth is not None
             else affordable_depth(args.m, args.n))
    brain = Brain(args.rounds, args.games, args.seed, args.td_leaf,
                  depth, train_budget=args.train_budget)
    print('m,n,k  {0}x{1} k={2}   depth {3}{4}'.format(
        args.m, args.n, args.k, depth,
        '' if args.depth is not None else ' (from the board size)'))
    if args.text:
        play_text(args.m, args.n, args.k, brain, depth, sides,
                  args.style)
    else:
        play_window(args.m, args.n, args.k, brain, depth, sides,
                    args.style)


if __name__ == '__main__':
    main()
