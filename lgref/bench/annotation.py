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

_SYNTH_RULES = (
    'Red and blue share a tally that starts at 0; red moves first. On a '
    'turn a player either adds 1 to the tally, or adds 2 (at most once '
    'per game), or lights their own lamp (once per game; the tally stays). '
    'The tally may not pass 6. The player who brings it to exactly 6 '
    'wins.')

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
    # ---- the TEST set (#373). Written in plain words from each game's
    # rules, not copied from the description's header comments.
    'skirmish': (
        'A 4x4 board. Each side has a guard and a lancer: white\'s on '
        '(1,1) and (2,1), black\'s on (4,4) and (3,4); white moves '
        'first. A guard steps one square in any direction. A lancer '
        'slides any distance along a row or a column through empty '
        'squares. A piece may move onto an empty square, or onto an enemy '
        'piece, which is captured. Taking the enemy guard wins; after '
        'eight turns the game ends with no winner.'),
    'muddychildren': (
        'Two children, ann and bob. First, nature makes at least one of '
        'them muddy. Each child sees the other\'s forehead but not their '
        'own. Then, for three rounds, both children say yes or no at the '
        'same time, and must say yes exactly when they know they are '
        'muddy; each hears what the other said. A child wins if, at the '
        'end, they know whether they are muddy.'),
    'kuhnpoker': (
        'Three cards, jack < queen < king. Both players put in one chip. '
        'Nature deals each player one card, which only that player sees. '
        'Player1 checks or bets one chip. After a check, player2 checks '
        '(showdown) or bets; after a bet, the other player folds (losing '
        'what they put in) or calls (showdown). Each player sees the '
        'other\'s actions. At a showdown both cards are shown and the '
        'higher card takes the pot.'),
    'leducholdem': (
        'Six cards, two each of jack < queen < king. Both players put in '
        'one chip. Nature deals each player one private card, of which '
        'the player learns the rank. A betting round follows, with bets '
        'of 2: check or bet, then fold, call or raise, with at most one '
        'bet and one raise per round; two checks or a call end the round, '
        'a fold ends the hand. Nature then turns one public card, and a '
        'second betting round follows with bets of 4. Player1 acts first '
        'in each round, and each player sees the other\'s actions. At the '
        'showdown a card pairing the public card wins, otherwise the '
        'higher card; equal ranks split the pot. Payoffs scale the chips '
        'won or lost.'),
    'russiancards': (
        'Seven cards, 0 to 6. Nature deals three to Alice, three to Bob '
        'and one to Cath; each sees only their own. Then two public '
        'announcements, which must be true: Alice announces the sum of '
        'her cards modulo 7, or her whole hand, or nothing; then Bob '
        'announces which card Cath holds, if he knows it, or nothing. '
        'Alice and Bob win if afterwards both know the whole deal and Cath '
        'does not learn who holds any card she does not hold; otherwise '
        'Cath wins.'),
    'cherylsbirthday': (
        'Nature picks Cheryl\'s birthday from ten given dates. Albert is '
        'told the month and Bernard the day. Then, in turn and in public, '
        'each says yes or no to a statement, and must say yes exactly '
        'when it is true: Albert, "I do not know the date, and I know '
        'Bernard does not know it"; Bernard, "now I know the date"; '
        'Albert, "now I know it too". A listener wins if at the end they '
        'know the date.'),
    'kalah_mini': (
        'South owns pits s1, s2, s3 and a store; north owns n1, n2, n3 and '
        'a store. Each pit starts with one seed; south moves first. A '
        'player empties one of their non-empty pits and sows its seeds '
        'one by one into the following positions, around the board, into '
        'their own store but skipping the opponent\'s store. If the last '
        'seed lands in their own store, they move again. If it lands in '
        'one of their own empty pits and the opposite pit holds seeds, '
        'they capture that seed and the opposite seeds into their store. '
        'The game ends when the player to move has no seeds in their '
        'pits; each player scores their store plus the seeds left in their '
        'pits, and more wins, equal draws.'),
    'dotsboxes_2x2': (
        'A 3x3 grid of dots enclosing four boxes, with twelve possible '
        'lines between neighbouring dots. Players a and b take turns '
        'drawing a line that is not yet drawn; a moves first. A line that '
        'completes one or two boxes scores a point per box, and the same '
        'player moves again. When every line is drawn, more points wins; '
        'equal points is a draw.'),
    'hex_3x3': (
        'A 3x3 board of hexagonal cells. Red and blue take turns placing '
        'a stone of their colour on an empty cell; red moves first. Red '
        'wins by joining the bottom row to the top row with a chain of '
        'touching red stones, blue by joining the left column to the right '
        'column with blue stones.'),
    'checkers_4x4': (
        'A 4x4 board, played on the dark squares. White starts with two '
        'men on its first row and moves up; black with two men on the '
        'last row, moving down; white moves first. A man steps one square '
        'diagonally forward onto an empty square; a king steps diagonally '
        'in any direction. A piece jumps diagonally over an adjacent enemy '
        'piece onto the empty square beyond, capturing it; one jump per '
        'turn. If a player can jump, they must. A man ending on the far '
        'row becomes a king. A player with no legal move loses; after 16 '
        'turns in all the game is drawn.'),
    'foxgeese_mini': (
        'A 4x4 board. Four geese start on the bottom row and the fox near '
        'the top; the geese move first. The geese player moves one goose '
        'one square up or sideways onto an empty square. The fox steps '
        'one square up, down, left or right onto an empty square, or jumps '
        'over an adjacent goose onto the empty square beyond, capturing '
        'it. The fox wins by capturing two geese, or by lasting 20 turns. '
        'A side with no legal move on its turn loses.'),
    'chomp_3x3': (
        'A 3x3 bar of chocolate; the bottom-left square is poisoned. '
        'Players take turns choosing a remaining square and eating it '
        'together with every square above it and to its right. The player '
        'who eats the poisoned square loses.'),
    'synth_independent': _SYNTH_RULES,
    'synth_shared': _SYNTH_RULES,
    'synth_redundant': _SYNTH_RULES + (
        ' A player whose lamp is lit may add 1.'),
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
