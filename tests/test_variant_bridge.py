"""Does the ENGINE variant describe the same game as the GDL ablation?

Issue #210. Phase 3 measures outcomes on engine variants and structure
on GDL ablations. They are two implementations of one intent, so if
`no_boulder` and `remove boulder` diverge, the two tiers describe
different games and no care in the analysis repairs it.

WHERE THE CHECK HAS TO BE TAKEN. At the opening, the ablated and
unablated games both give 71 legal moves, because White cannot move the
boulder on turn 1 anyway. A comparison taken where nothing can differ is
not a comparison -- that mistake has now been made twice on this
project, once on the GDL dialects and once here.
"""

import os
import random
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

import pygame                                       # noqa: E402
pygame.init()

from engine import GameEngine                       # noqa: E402
from ggp.cross_validation import (board_to_gdl_facts,   # noqa: E402
                                  compare_legal_moves)
from ggp.game import GGPGame                        # noqa: E402
from ggp.infix import forms_to_infix_lines, parse_infix  # noqa: E402
from lgref.ablate import operations as ops          # noqa: E402

OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')


class _Carrier(object):
    """What `compare_legal_moves` needs: something with a `.board`.

    The engine owns its own board -- `enable_boulder=False` sets
    `board.boulder = None` there -- so the comparison must be driven
    from the ENGINE's board. Building a `Game()` and swapping its
    engine afterwards leaves the original board, boulder and all, which
    is how an earlier attempt at this measured 4.8% agreement against a
    variant it was not actually testing.
    """

    def __init__(self, engine):
        self.board = engine.board
        self.next_player = engine.current_player


def _agreement(gdl_text, engine_kwargs, trials=2, plies=10):
    ggp = GGPGame(gdl_text)
    agree = total = 0
    diffs = []
    for trial in range(trials):
        engine = GameEngine(max_turns=1000, **engine_kwargs)
        rng = random.Random(6000 + trial)
        for _ in range(plies):
            if engine.is_game_over():
                break
            mover = engine.current_player
            ggp.state = set(board_to_gdl_facts(engine.board, mover))
            # ONLY the player to move: the state names one mover, so
            # asking about the other compares a player who cannot act
            # and lands at a tidy-looking 50%.
            result = compare_legal_moves(_Carrier(engine), ggp, mover)
            total += 1
            if result['engine_only'] or result['ggp_only']:
                diffs.append((len(result['engine_only']),
                              len(result['ggp_only'])))
            else:
                agree += 1
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            engine.execute_turn(turns[rng.randrange(len(turns))])
    return agree, total, diffs


@pytest.mark.slow
def test_unablated_engine_and_gdl_agree():
    """The control: without this, an ablation result means nothing."""
    with open(OFFICIAL) as handle:
        forms = parse_infix(handle.read())
    text = '\n'.join(forms_to_infix_lines(forms))
    agree, total, diffs = _agreement(text, {})
    assert total >= 8
    assert agree == total, 'baseline disagreement: {}'.format(diffs[:3])


@pytest.mark.slow
def test_engine_no_boulder_matches_the_gdl_removal():
    """The bridge Phase 3's two measurement tiers rest on."""
    with open(OFFICIAL) as handle:
        forms = parse_infix(handle.read())
    ablated = ops.remove_constant(forms, 'boulder')
    text = '\n'.join(forms_to_infix_lines(ablated))
    agree, total, diffs = _agreement(text, {'enable_boulder': False})
    assert total >= 8
    assert agree == total, (
        'engine no_boulder and GDL remove-boulder disagree on {} of {} '
        'positions: {}'.format(total - agree, total, diffs[:3]))
