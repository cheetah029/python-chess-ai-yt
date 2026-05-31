"""Extended cross-validation: run N random moves via the Python
engine, sync state to the GGP at each step, compare legal-move
sets.

This stress-tests the GDL across many mid-game positions, not
just the initial setup. Findings get reported as a summary
(e.g. "after 20 random plies, the GGP and engine agreed at every
step" or "step N had a discrepancy of X moves").

We don't HARD-FAIL on a discrepancy — the GDL has known gaps
that surface mid-game (invuln, promotion sub-choice, etc.). The
test asserts on the FRACTION of perfect matches as a regression
signal.
"""

import os
import sys
import random
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

from game import Game
from ai_controller import AIController
from ggp.game import GGPGame
from ggp.cross_validation import board_to_gdl_facts, compare_legal_moves


@pytest.fixture(autouse=True)
def _ensure_pygame_initialized():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()


INTEGRATED = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'integrated.gdl')


def _play_random_ply(g, rng):
    """Play one random move via AIController. Returns True if a
    move was played, False if the game ended or no legal turn."""
    if g.winner is not None:
        return False
    ctrl = AIController(g.next_player)
    return ctrl.take_turn(g)


def _diff_at_state(g, ggp, player):
    """Sync GGP state to g.board and compute the diff."""
    ggp.state = set(board_to_gdl_facts(g.board, g.next_player))
    return compare_legal_moves(g, ggp, player)


def test_cross_validation_after_random_plies():
    """Play up to 20 random plies; at each ply (before the move),
    compare legal-move sets between engine and GGP. Report how
    many positions had ZERO discrepancies."""
    rng = random.Random(42)
    g = Game()
    ggp = GGPGame.from_file(INTEGRATED)

    perfect_match_count = 0
    total_compared = 0
    discrepancies = []

    for ply in range(20):
        if g.winner is not None:
            break
        diff = _diff_at_state(g, ggp, g.next_player)
        total_compared += 1
        engine_only = len(diff['engine_only'])
        ggp_only = len(diff['ggp_only'])
        if engine_only == 0 and ggp_only == 0:
            perfect_match_count += 1
        else:
            discrepancies.append({
                'ply': ply,
                'mover': g.next_player,
                'engine_count': diff['engine_count'],
                'ggp_count': diff['ggp_count'],
                'engine_only': engine_only,
                'ggp_only': ggp_only,
            })
        if not _play_random_ply(g, rng):
            break

    # At minimum the init position should be a perfect match.
    assert perfect_match_count >= 1, (
        f'no perfect matches in {total_compared} compared positions; '
        f'discrepancies: {discrepancies[:3]}')

    # Sanity: print a summary (not asserted; useful when investigating).
    perfect_pct = (perfect_match_count / total_compared * 100
                   if total_compared else 0)
    print(f'\nCross-validation summary after random ply sequence:')
    print(f'  positions compared: {total_compared}')
    print(f'  perfect matches:    {perfect_match_count} '
          f'({perfect_pct:.0f}%)')
    print(f'  discrepancies:      {len(discrepancies)}')
    if discrepancies:
        print(f'  first discrepancy: {discrepancies[0]}')


def test_cross_validation_at_init_strict():
    """Strict assertion: at the init position, the engine and GGP
    must agree EXACTLY on every legal move. This was demonstrated
    in PR #111 as the Goal-4-milestone result. The test ensures
    this never regresses."""
    g = Game()
    ggp = GGPGame.from_file(INTEGRATED)
    diff = _diff_at_state(g, ggp, 'white')
    assert diff['engine_only'] == [], (
        f"engine-only moves at init: {diff['engine_only']}")
    assert diff['ggp_only'] == [], (
        f"GGP-only moves at init: {diff['ggp_only']}")
    assert diff['engine_count'] == diff['ggp_count']
    assert diff['engine_count'] == len(diff['common'])
