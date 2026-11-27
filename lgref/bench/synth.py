"""The three synthetic Paper A test games, generated from one template.

Written for #370, AFTER the freeze (ab7b33b). The catalog names them
`synth_independent`, `synth_shared` and `synth_redundant`: one small race
game whose rules are put together from fixed modules, so the rule
structure of each description is known by construction.

THE GAME. Red and blue share a tally that starts at 0; red moves first.
On a turn the player to move does one of:

  step   add 1 to the tally;
  jump   add 2 to the tally, at most once per game (it spends the
         player's one jump token), and only if the tally stays at most 6;
  light  light their own lamp, once per game, leaving the tally alone.

The player who brings the tally to exactly 6 wins. Every player always
has a step available below 6, so no one is ever stuck, and each player
can jump and light at most once, so every game ends.

THE THREE DESCRIPTIONS.

  synth_independent  step, jump and light each have their own
                     statements; no rule calls another rule's helper.
  synth_shared       step and jump share one helper, `room`, and one
                     tally update: the shared-helper case.
  synth_redundant    synth_independent plus one REDUNDANT rule: "a
                     player whose lamp is lit may step". Step is legal
                     whenever this is, so it changes no behaviour.

`python -m lgref.bench.synth` rewrites the three files; a test checks the
files equal what this module generates, so they cannot drift apart.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR = os.path.join(HERE, 'games')

NAMES = ('synth_independent', 'synth_shared', 'synth_redundant')

_BANNER = '% ' + '=' * 60

_RULES_TEXT = """\
% Red and blue share a tally that starts at 0; red moves first. On
% a turn the player to move either STEPS (adds 1), JUMPS (adds 2,
% at most once per game, spending their one jump token), or LIGHTS
% their own lamp (once per game; the tally is left alone). The
% tally may never pass 6. The player who brings it to exactly 6
% wins."""

_ADDS = {
    'synth_independent': (
        'Step, jump and light have their own statements, and no\n'
        '% rule calls a helper of another rule.'),
    'synth_shared': (
        'Step and jump share one helper, `room`, and one tally\n'
        '% update.'),
    'synth_redundant': (
        'A redundant rule: "a player whose lamp is lit may step".\n'
        '% Step is legal whenever it is, so it changes no behaviour.'),
}

_ROLES = ['role(red)', 'role(blue)']

_ARITHMETIC = (['% ---- tally arithmetic']
               + ['plus({},1,{})'.format(n, n + 1) for n in range(6)]
               + ['plus({},2,{})'.format(n, n + 2) for n in range(5)]
               + ['opponent(red,blue)', 'opponent(blue,red)'])

_STEP_OWN = [
    '% ---- step: add 1',
    'legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M)',
    'next(tally(M)) :- does(P,add(1)) & true(tally(N)) & plus(N,1,M)',
]

_JUMP_OWN = [
    '% ---- jump: add 2, once, spending the jump token',
    'legal(P,add(2)) :- true(control(P)) & true(tally(N)) & plus(N,2,M) '
    '& true(token(P))',
    'next(tally(M)) :- does(P,add(2)) & true(tally(N)) & plus(N,2,M)',
    'next(token(P)) :- true(token(P)) & ~does(P,add(2))',
]

_STEP_AND_JUMP_SHARED = [
    '% ---- the helper and the tally update step and jump share',
    'room(P,K,M) :- true(control(P)) & true(tally(N)) & plus(N,K,M)',
    'next(tally(M)) :- does(P,add(K)) & true(tally(N)) & plus(N,K,M)',
    '% ---- step: add 1',
    'legal(P,add(1)) :- room(P,1,M)',
    '% ---- jump: add 2, once, spending the jump token',
    'legal(P,add(2)) :- room(P,2,M) & true(token(P))',
    'next(token(P)) :- true(token(P)) & ~does(P,add(2))',
]

_LIGHT = [
    '% ---- light: light the lamp, once; the tally stays',
    'legal(P,light) :- true(control(P)) & ~true(lit(P))',
    'next(lit(P)) :- does(P,light)',
    'next(lit(P)) :- true(lit(P))',
    'next(tally(N)) :- true(tally(N)) & does(P,light)',
]

_REDUNDANT = [
    '% ---- a lit lamp lets its player step (redundant: step is',
    '%      legal whenever this is)',
    'legal(P,add(1)) :- true(control(P)) & true(tally(N)) & plus(N,1,M) '
    '& true(lit(P))',
]

_ALTERNATION = [
    '% ---- alternation',
    'legal(Q,noop) :- true(control(P)) & opponent(P,Q)',
    'next(control(Q)) :- true(control(P)) & opponent(P,Q)',
]

_ENDING = [
    '% ---- ending: the tally reaches 6; whoever brought it there wins',
    'terminal :- true(tally(6))',
    'goal(P,100) :- true(tally(6)) & opponent(P,Q) & true(control(Q))',
    'goal(P,0) :- true(tally(6)) & true(control(P))',
]

_INIT = ['init(tally(0))', 'init(token(red))', 'init(token(blue))',
         'init(control(red))']


def text(name):
    """The description of one synthetic game, as infix HRF text."""
    if name not in NAMES:
        raise ValueError('unknown synthetic game {!r}'.format(name))
    header = [_BANNER,
              '% {} -- Paper A synthetic test game, infix HRF (the'.format(
                  name),
              "% project's OFFICIAL dialect, issue #190). GENERATED by",
              '% lgref/bench/synth.py for #370, AFTER the freeze (ab7b33b).',
              '%', _RULES_TEXT, '%',
              '% WHAT IT ADDS. ' + _ADDS[name], _BANNER, '']
    body = _ROLES + [''] + _ARITHMETIC + ['']
    if name == 'synth_shared':
        body += _STEP_AND_JUMP_SHARED
    else:
        body += _STEP_OWN + [''] + _JUMP_OWN
    body += [''] + _LIGHT
    if name == 'synth_redundant':
        body += [''] + _REDUNDANT
    body += [''] + _ALTERNATION + [''] + _ENDING + [''] + _INIT
    return '\n'.join(header + body) + '\n'


def path(name):
    return os.path.join(GAMES_DIR, name + '.gdl')


def write():
    for name in NAMES:
        with open(path(name), 'w') as handle:
            handle.write(text(name))
        print(path(name))


if __name__ == '__main__':
    write()
    sys.exit(0)
