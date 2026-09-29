"""A seed must reproduce its game in ANOTHER process (#255).

The framework's whole measurement programme rests on a seed naming a
game. It did not: `Board.get_transformation_options` ordered its result
with `list(set(captured))` over piece-name STRINGS, CPython randomises
string hashing per process, and that order reached the legal-turn list.
An agent picking `turns[rng.randrange(len(turns))]` then chose a
different turn from the same RNG draw.

    seed 0, three consecutive processes:  689, 304 and 236 plies

The in-process determinism check could never see this -- one process
has one hash seed -- and reported PASS throughout.
"""

import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _options(captured):
    """Transformation options for a queen whose side lost `captured`."""
    sys.path.insert(0, os.path.join(REPO, 'src'))
    import pygame
    pygame.init()
    from board import Board
    from piece import Queen

    board = Board()
    board.captured_pieces = {'white': list(captured), 'black': []}
    return board.get_transformation_options(Queen('white'))


def test_transformation_options_do_not_depend_on_insertion_order():
    """The rulebook offers a SET of forms, so order is ours to fix.

    "The queen may transform into a rook, bishop, or knight — provided a
    friendly piece of that type has been captured earlier." Nothing
    ranks them, so any fixed order is correct; only instability was
    wrong.
    """
    forwards = _options(['rook', 'bishop', 'knight'])
    backwards = _options(['knight', 'bishop', 'rook'])
    duplicated = _options(['bishop', 'rook', 'bishop', 'knight', 'rook'])

    assert forwards == backwards == duplicated
    assert sorted(forwards) == forwards, 'order must be canonical, not hashed'
    assert set(forwards) == {'bishop', 'knight', 'rook'}


@pytest.mark.parametrize('seed', [0, 3])
def test_a_seed_reproduces_its_game_under_a_different_hash_seed(seed):
    """The property the sweep's reproducibility claim depends on.

    Run as subprocesses with PYTHONHASHSEED set explicitly, because the
    bug is invisible to anything sharing one interpreter.
    """
    script = (
        'import hashlib, random, sys\n'
        'from experiments.variants import make_engine\n'
        'from lgref.experiments.random_play import build\n'
        'from lgref.experiments.mcts import describe\n'
        'seed = int(sys.argv[1])\n'
        'engine = make_engine("full", max_turns=400)\n'
        'w = build("random", random.Random(seed * 2 + 1), 0)\n'
        'b = build("random", random.Random(seed * 2 + 2), 0)\n'
        'h = hashlib.md5()\n'
        'while not engine.is_game_over():\n'
        '    turns = engine.get_all_legal_turns()\n'
        '    if not turns:\n'
        '        break\n'
        '    p = w if engine.current_player == "white" else b\n'
        '    chosen = p.choose_turn(turns, engine)\n'
        '    h.update(repr((len(turns), describe(chosen))).encode())\n'
        '    engine.execute_turn(chosen)\n'
        'print(h.hexdigest())\n')

    path = os.pathsep.join([REPO, os.path.join(REPO, 'src')])
    digests = []
    for hashseed in ('0', '1'):
        env = dict(os.environ, PYTHONHASHSEED=hashseed, PYTHONPATH=path)
        out = subprocess.check_output(
            [sys.executable, '-c', script, str(seed)], env=env, timeout=600)
        digests.append(out.decode().strip().splitlines()[-1])

    assert digests[0] == digests[1], (
        'seed {} played a different game under a different interpreter '
        'hash seed: something orders on str hashing'.format(seed))
