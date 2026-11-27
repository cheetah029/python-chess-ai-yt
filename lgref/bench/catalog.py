"""The Paper A benchmark: which games exist, and which set each is in.

First recorded before any Paper A result existed (#347). Revised once,
on 2026-11-27 (#358), at the user's instruction: there are exactly TWO
sets, development and test, and every game is in one of them or is
excluded with a reason. A game's set never changes again; the tests pin
both lists so a quiet edit fails the build.

THE UNIT OF SPLITTING IS THE GAME FAMILY. Two encodings of one game, or a
game and its variants, share almost every statement, so one in dev and
the other in test would leak the answer.

  dev       the method may be developed, tuned and debugged here.
            The plan's five (tic-tac-toe, Nim, Corridor, the two pilots),
            plus the two games already used to MAKE A CHOICE before
            Paper A: drop-three (a #315 tuning game) and Monty Hall (the
            #315 adoption decision). A game a choice was made on cannot
            be a test game.
  test      never used for any choice. Games seen before Paper A but
            only ever REPORTED (skirmish, muddy children; the card and
            puzzle games, which were never scored against a grouping),
            and the nine games written after the freeze, named now so the
            list cannot be chosen after the results are seen.
  excluded  a relative of a dev game, so it can be in neither set: the
            3x4 Breakthrough and the two Kriegspiel tic-tac-toe games.

Every reference grouping in this benchmark is written by Claude, the
same author as the method, and is PROVISIONAL until human annotators
label the games independently (docs/paper-a/annotation/).
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OLD_GAMES = os.path.join(ROOT, 'identify', 'testgames')
NEW_GAMES = os.path.join(HERE, 'games')


class Game(object):
    __slots__ = ('name', 'split', 'family', 'role', 'path', 'note')

    def __init__(self, name, split, family, role, path, note=''):
        self.name = name
        self.split = split
        self.family = family
        self.role = role
        self.path = path
        self.note = note

    def __repr__(self):
        return '<Game {} {}>'.format(self.name, self.split)


def _old(name):
    return os.path.join(OLD_GAMES, name + '.gdl')


def _new(name):
    return os.path.join(NEW_GAMES, name + '.gdl')


SPLITS = ('dev', 'test', 'excluded')

GAMES = [
    # ---- dev: fixed by the user's plan
    Game('tictactoe', 'dev', 'tictactoe', 'control', _old('tictactoe'),
         'placement vs line detection vs ending'),
    Game('nim', 'dev', 'nim', 'control', _old('nim'),
         'taking objects vs turn alternation vs ending'),
    Game('corridor', 'dev', 'corridor', 'failure analysis',
         _old('corridor'), 'blocking and tempo merge into movement'),
    Game('breakthrough5', 'dev', 'breakthrough', 'pilot',
         _new('breakthrough5'),
         'movement and capture share one action and one board update'),
    Game('othello4', 'dev', 'othello', 'pilot', _new('othello4'),
         'outflanking decides placement and flips; availability decides '
         'passing and the end'),
    # ---- dev: used for a choice before Paper A, so never test
    Game('dropthree', 'dev', 'dropthree', 'used before Paper A',
         _old('dropthree'), 'a #315 TUNING game: a choice was made on it'),
    Game('montyhall', 'dev', 'montyhall', 'used before Paper A',
         _old('montyhall'),
         '#315 validation game: the adoption decision was made on it'),
    # ---- related to a dev game: in neither set
    Game('breakthrough', 'excluded', 'breakthrough', 'excluded',
         _old('breakthrough'), '3x4 Breakthrough, same family as a pilot'),
    Game('kriegtictactoe', 'excluded', 'tictactoe', 'excluded',
         _old('kriegtictactoe'), 'tic-tac-toe with hidden marks'),
    Game('kriegmnk_5_5_4', 'excluded', 'tictactoe', 'excluded',
         _old('kriegmnk_5_5_4'), 'a larger tic-tac-toe with hidden marks'),
    # ---- test: seen before Paper A, but never used for any choice
    Game('skirmish', 'test', 'skirmish', 'test', _old('skirmish'),
         '#315 test game; score published'),
    Game('muddychildren', 'test', 'muddychildren', 'test',
         _old('muddychildren'), '#315 test game; score published'),
    Game('kuhnpoker', 'test', 'kuhnpoker', 'test', _old('kuhnpoker'),
         'no reference grouping yet'),
    Game('leducholdem', 'test', 'leducholdem', 'test',
         _old('leducholdem'), 'no reference grouping yet'),
    Game('russiancards', 'test', 'russiancards', 'test',
         _old('russiancards'), 'no reference grouping yet'),
    Game('cherylsbirthday', 'test', 'cherylsbirthday', 'test',
         _old('cherylsbirthday'), 'no reference grouping yet'),
    # ---- test: written after the freeze (stage 5); named now
    Game('kalah_mini', 'test', 'kalah', 'test', _new('kalah_mini'),
         'sowing shared by capture and the extra turn'),
    Game('dotsboxes_2x2', 'test', 'dotsboxes', 'test',
         _new('dotsboxes_2x2'),
         'completing a box both scores and grants another turn'),
    Game('hex_3x3', 'test', 'hex', 'test', _new('hex_3x3'),
         'a connection win found by recursive path detection'),
    Game('checkers_4x4', 'test', 'checkers', 'test',
         _new('checkers_4x4'),
         'forced capture: capture availability restricts ordinary moves'),
    Game('foxgeese_mini', 'test', 'foxgeese', 'test',
         _new('foxgeese_mini'), 'asymmetric roles with different moves'),
    Game('chomp_3x3', 'test', 'chomp', 'test', _new('chomp_3x3'),
         'one action removes a whole region'),
    Game('synth_independent', 'test', 'synthetic', 'synthetic',
         _new('synth_independent'), 'generated: independent rules'),
    Game('synth_shared', 'test', 'synthetic', 'synthetic',
         _new('synth_shared'), 'generated: rules sharing a helper'),
    Game('synth_redundant', 'test', 'synthetic', 'synthetic',
         _new('synth_redundant'), 'generated: a redundant rule'),
]

BY_NAME = {g.name: g for g in GAMES}


def game(name):
    return BY_NAME[name]


def game_path(name):
    return BY_NAME[name].path


def in_split(split):
    return [g.name for g in GAMES if g.split == split]


def existing(split=None):
    """Names of games whose description file exists, optionally in one
    set. A fresh test game is listed before it is written."""
    return [g.name for g in GAMES
            if (split is None or g.split == split)
            and os.path.exists(g.path)]
