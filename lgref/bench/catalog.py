"""The Paper A benchmark: which games exist, and which split each is in.

RECORDED BEFORE ANY PAPER A RESULT EXISTS (issue #347). The split may
only ever gain games: a game's split never changes after it is written
here, and `lgref/tests/test_paper_a_benchmark.py` pins the dev set so a
quiet edit fails the build.

THE UNIT OF SPLITTING IS THE GAME FAMILY. Two encodings of one game, or a
game and its variants, share almost every statement, so one in dev and
the other in test would leak the answer. A family is in one split.

THE SPLITS

  dev           the method may be developed, tuned and debugged here.
                The user's plan fixes it: the two development controls
                (tic-tac-toe, Nim), the failure-analysis game (Corridor)
                and the two pilots that establish the protocol (5x5
                Breakthrough, 4x4 Othello).
  dev_family    related to a dev game, so never scored as test: the
                3x4 Breakthrough, the Kriegspiel tic-tac-toe variants,
                and drop-three, which was a TUNING game under #315.
  test_seen     never tuned on, but already seen: each was run through
                identification before Paper A, and its score (where it
                has labels) is published in docs/lgref-validation.md.
                Reported SEPARATELY from fresh test games, never pooled.
                Monty Hall was used once, for the #315 adoption decision.
  test_fresh    written after the method is frozen (stage 5), by name
                now so the list cannot be chosen after seeing results.
                None of these files exists yet.

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


SPLITS = ('dev', 'dev_family', 'test_seen', 'test_fresh')

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
    # ---- related to a dev game: never test
    Game('breakthrough', 'dev_family', 'breakthrough', 'excluded',
         _old('breakthrough'), '3x4 Breakthrough, same family as a pilot'),
    Game('kriegtictactoe', 'dev_family', 'tictactoe', 'excluded',
         _old('kriegtictactoe'), 'tic-tac-toe with hidden marks'),
    Game('kriegmnk_5_5_4', 'dev_family', 'tictactoe', 'excluded',
         _old('kriegmnk_5_5_4'), 'a larger tic-tac-toe with hidden marks'),
    Game('dropthree', 'dev_family', 'dropthree', 'excluded',
         _old('dropthree'), 'a #315 TUNING game, so not clean as test'),
    # ---- seen before Paper A, never tuned on
    Game('skirmish', 'test_seen', 'skirmish', 'test', _old('skirmish'),
         '#315 test game; score published'),
    Game('muddychildren', 'test_seen', 'muddychildren', 'test',
         _old('muddychildren'), '#315 test game; score published'),
    Game('montyhall', 'test_seen', 'montyhall', 'test', _old('montyhall'),
         '#315 validation game: used once for the adoption decision'),
    Game('kuhnpoker', 'test_seen', 'kuhnpoker', 'test', _old('kuhnpoker'),
         'no reference grouping yet'),
    Game('leducholdem', 'test_seen', 'leducholdem', 'test',
         _old('leducholdem'), 'no reference grouping yet'),
    Game('russiancards', 'test_seen', 'russiancards', 'test',
         _old('russiancards'), 'no reference grouping yet'),
    Game('cherylsbirthday', 'test_seen', 'cherylsbirthday', 'test',
         _old('cherylsbirthday'), 'no reference grouping yet'),
    # ---- written after the freeze (stage 5); named now
    Game('kalah_mini', 'test_fresh', 'kalah', 'test', _new('kalah_mini'),
         'sowing shared by capture and the extra turn'),
    Game('dotsboxes_2x2', 'test_fresh', 'dotsboxes', 'test',
         _new('dotsboxes_2x2'),
         'completing a box both scores and grants another turn'),
    Game('hex_3x3', 'test_fresh', 'hex', 'test', _new('hex_3x3'),
         'a connection win found by recursive path detection'),
    Game('checkers_4x4', 'test_fresh', 'checkers', 'test',
         _new('checkers_4x4'),
         'forced capture: capture availability restricts ordinary moves'),
    Game('foxgeese_mini', 'test_fresh', 'foxgeese', 'test',
         _new('foxgeese_mini'), 'asymmetric roles with different moves'),
    Game('chomp_3x3', 'test_fresh', 'chomp', 'test', _new('chomp_3x3'),
         'one action removes a whole region'),
    Game('synth_independent', 'test_fresh', 'synthetic', 'synthetic',
         _new('synth_independent'), 'generated: independent rules'),
    Game('synth_shared', 'test_fresh', 'synthetic', 'synthetic',
         _new('synth_shared'), 'generated: rules sharing a helper'),
    Game('synth_redundant', 'test_fresh', 'synthetic', 'synthetic',
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
    split. A `test_fresh` game is listed before it is written."""
    return [g.name for g in GAMES
            if (split is None or g.split == split)
            and os.path.exists(g.path)]
