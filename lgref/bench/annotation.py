"""Reference groupings on statement sheets, and the annotation packet.

A REFERENCE GROUPING says, for every statement of a game, which rules
it belongs to -- none, one, or several -- and whether the call was
ambiguous. It is stored as a SHEET: a CSV with one row per statement,
in the order `lgref.identify.clauses.load` numbers them, preceded by
`#` metadata lines that name the author.

    index,statement,rules,ambiguous,note
    32,"legal(P,move(X,Y,X2,Y2)) :- true(control(P)) & capture(...)",capture,,

`rules` is a `;`-separated list of rule names the AUTHOR chose. Names
are never compared across sheets: the agreement measures used on them
(extended BCubed) compare which statements are grouped TOGETHER, so two
annotators who call the same rule "capture" and "taking" agree fully.

WHO WROTE WHICH SHEET. `lgref/bench/references/` holds the sheets used
for scoring. Every one of them is currently written by Claude -- the
pilots' for #347, and the controls' converted from the head-predicate
labels in `lgref/identify/testgames/ground_truth.py`, which an earlier
Claude session wrote. They are PROVISIONAL. The packet this module
writes (`python -m lgref.bench.annotation`) is for human annotators to
label the same statements independently; agreement between annotators
is reported only when such sheets exist.
"""

import csv
import io
import os
import sys

from lgref.bench.catalog import game_path

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE_DIR = os.path.join(HERE, 'references')
REPO = os.path.dirname(os.path.dirname(HERE))
PACKET_DIR = os.path.join(REPO, 'docs', 'paper-a', 'annotation')

COLUMNS = ('index', 'statement', 'rules', 'ambiguous', 'note')


class Sheet(object):
    """One annotator's grouping of one game."""

    __slots__ = ('game', 'meta', 'rows')

    def __init__(self, game, meta, rows):
        self.game = game
        self.meta = meta
        self.rows = rows

    @property
    def author(self):
        return self.meta.get('author', '')

    def membership(self):
        """{statement index: frozenset of rule names}; unassigned
        statements map to the empty set, so none is silently dropped."""
        return {row['index']: frozenset(row['rules']) for row in self.rows}

    def ambiguous(self):
        return sorted(r['index'] for r in self.rows if r['ambiguous'])

    def shared(self):
        return sorted(r['index'] for r in self.rows if len(r['rules']) > 1)

    def unassigned(self):
        return sorted(r['index'] for r in self.rows if not r['rules'])


def statements(game):
    """[(index, infix text)] for every statement, in `load` order."""
    from ggp.infix import forms_to_infix_lines
    from lgref.identify.clauses import load

    out = []
    for node in load(game_path(game)):
        lines = forms_to_infix_lines([node.raw])
        out.append((node.index, ' '.join(lines)))
    return out


def read_sheet(path, game=None):
    meta, body = {}, []
    with open(path) as handle:
        for line in handle:
            if line.startswith('#'):
                key, _, value = line[1:].partition(':')
                meta[key.strip()] = value.strip()
            else:
                body.append(line)
    rows = []
    for record in csv.DictReader(io.StringIO(''.join(body))):
        rules = [r.strip() for r in (record.get('rules') or '').split(';')
                 if r.strip()]
        rows.append({'index': int(record['index']),
                     'statement': record['statement'],
                     'rules': rules,
                     'ambiguous': bool((record.get('ambiguous') or '')
                                       .strip()),
                     'note': record.get('note') or ''})
    return Sheet(game or meta.get('game'), meta, rows)


def write_sheet(path, game, meta, rows):
    """`rows` is [(index, statement, [rules], ambiguous, note)]."""
    handle = io.StringIO()
    for key in sorted(meta):
        handle.write('# {}: {}\n'.format(key, meta[key]))
    writer = csv.writer(handle, lineterminator='\n')
    writer.writerow(COLUMNS)
    for index, statement, rules, ambiguous, note in rows:
        writer.writerow([index, statement, ';'.join(rules),
                         'y' if ambiguous else '', note])
    with open(path, 'w') as out:
        out.write(handle.getvalue())


def reference(game):
    """The scoring sheet for `game` (provisional; see module doc)."""
    return read_sheet(os.path.join(REFERENCE_DIR, game + '.csv'), game)


def has_reference(game):
    return os.path.exists(os.path.join(REFERENCE_DIR, game + '.csv'))


def check_sheet(sheet):
    """Problems with a sheet: it must list exactly the game's statements,
    in order, with the statement text matching the description."""
    expected = statements(sheet.game)
    got = [(r['index'], r['statement']) for r in sheet.rows]
    problems = []
    if [i for i, _ in got] != [i for i, _ in expected]:
        problems.append('{}: indices {} do not match the description\'s '
                        '{} statements'.format(sheet.game, len(got),
                                               len(expected)))
        return problems
    for (index, text), (_i, want) in zip(got, expected):
        if text != want:
            problems.append('{}#{}: sheet says {!r}, description says {!r}'
                            .format(sheet.game, index, text, want))
    if not sheet.author:
        problems.append('{}: the sheet names no author'.format(sheet.game))
    return problems


# ---- the packet ---------------------------------------------------------

#: The rules of play given to annotators, in plain words. Deliberately
#: NOT the description's header comment: those headers say which
#: statements the author meant to be shared ("WHAT IT ADDS"), and the
#: section comments in the files group statements outright. An annotator
#: shown either would be copying the author, not labelling independently.
RULES = {
    'tictactoe': (
        'Two players, x and o, take turns marking a blank cell of a 3x3 '
        'grid; x moves first. Three of one mark in a row, a column or a '
        'diagonal wins. If the grid fills with no such line, the game '
        'ends with no winner.'),
    'nim': (
        'One pile of five objects. Two players take turns removing one or '
        'two objects. When the pile is empty the game ends, and the '
        'player who would move next wins (so taking the last object '
        'loses).'),
    'corridor': (
        'Two tokens on a corridor of squares 0 to 7: white starts on 0, '
        'black on 2; white moves first. On a turn a player steps their '
        'token one or two squares forward, or holds. A token may not land '
        'on the other token, may not leave the corridor, and may not make '
        'a two-square step straight after its own two-square step. '
        'Reaching square 7 wins.'),
    'breakthrough5': (
        'A 5x5 board. White starts with ten pawns on rows 1 and 2, black '
        'with ten on rows 4 and 5; white moves first and moves up the '
        'board, black down. On a turn a player moves one pawn one row '
        'forward: straight ahead onto an empty square, diagonally ahead '
        'onto an empty square, or diagonally ahead onto an enemy pawn, '
        'which is captured. A pawn never captures straight ahead. A pawn '
        'reaching the far row wins. A player with no legal move loses.'),
    'dropthree': (
        'A grid four columns wide and three rows high, standing upright. '
        'Two players, red and yellow, take turns dropping a counter into a '
        'column that is not full; red moves first. A counter falls to the '
        'lowest empty cell of its column. Three of one colour in a row, '
        'in a column or on a diagonal wins. If the grid fills with no such '
        'line, the game ends with no winner.'),
    'montyhall': (
        'A game show with three doors. First, the host (a random player) '
        'hides a car behind one door while the candidate picks a door. '
        'Second, the host opens a door that is still closed, hides no '
        'car and was not picked; the candidate sees which. Third, the '
        'candidate may switch to the other closed door, or stay. The '
        'candidate wins if the door they end with hides the car.'),
    'othello4': (
        'A 4x4 board. The four centre squares start filled: white on '
        '(2,2) and (3,3), black on (2,3) and (3,2). Black moves first. A '
        'player places a disc on an empty square so that it outflanks at '
        'least one line of the opponent\'s discs: a straight or diagonal '
        'run of opponent discs closed at the far end by one of the '
        'player\'s own. Every outflanked disc, in every direction, flips '
        'to the player. A player who has no such placement passes. The '
        'game ends when neither player can place; the player with more '
        'discs wins, and equal counts are a draw.'),
}


INSTRUCTIONS = """\
# Labelling the statements of a game into rules

You are asked to group the statements of a game description into the
RULES of the game, as a reader who knows the rules would. Your sheet is
compared with other annotators' and with a computer method's, so please
label independently: do not discuss your labels with anyone until you
have finished, and do not open the `.gdl` files in the repository --
their comments group the statements for you.

For each game folder:

1. Read `statements.md`: the rules of play in plain words, then the
   statements of the description, numbered.
2. Fill in `sheet.csv` (any spreadsheet program opens it). Put your
   name, the date and roughly how long it took in the `#` lines at the
   top.
3. For each statement, write in the `rules` column the rule or rules it
   belongs to. Choose your own short names (`capture`, `scoring`, ...);
   only which statements you group together is compared, never the
   names. Use the SAME name for the same rule throughout one game.
   - A statement that serves several rules gets several names,
     separated by `;` -- for example `capture;ending`.
   - A statement that belongs to no rule (a role declaration, say)
     stays blank.
   - Put `y` in `ambiguous` when you hesitated, and a few words in
     `note` saying between what.
4. A RULE here is something a player would name when explaining the
   game: how a piece moves, how a capture works, when the game ends, who
   wins. Group statements by what they DO in the game, not by where they
   appear in the list or what they are called.

There are no trick questions and no single right answer: disagreement
between careful annotators is exactly what is being measured.
"""


def write_packet(game, out_dir=None):
    """statements.md and a blank sheet.csv for one game."""
    out_dir = os.path.join(out_dir or PACKET_DIR, game)
    os.makedirs(out_dir, exist_ok=True)
    rows = statements(game)
    with open(os.path.join(out_dir, 'statements.md'), 'w') as handle:
        handle.write('# {} -- statements to label\n\n'.format(game))
        handle.write('## The rules of play\n\n{}\n\n'.format(RULES[game]))
        handle.write('## The statements, numbered as on the sheet\n\n')
        handle.write('`~` is "not", `&` is "and", and `true(...)` reads '
                     'the current position, `does(...)` the move being '
                     'played, and `next(...)` what holds after it. '
                     'Capitalised words are variables.\n\n```\n')
        for index, text in rows:
            handle.write('{:>3}  {}\n'.format(index, text))
        handle.write('```\n')
    write_sheet(os.path.join(out_dir, 'sheet.csv'), game,
                {'game': game, 'author': '(your name)',
                 'date': '(date)', 'time_spent': '(minutes)'},
                [(index, text, [], False, '') for index, text in rows])
    return out_dir


def write_instructions(out_dir=None):
    out_dir = out_dir or PACKET_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'README.md')
    with open(path, 'w') as handle:
        handle.write(INSTRUCTIONS)
    return path


def main(argv=None):
    from lgref.bench.catalog import existing
    games = (argv if argv else sys.argv[1:]) or existing('dev')
    print(write_instructions())
    for game in games:
        print(write_packet(game))


if __name__ == '__main__':
    main()
