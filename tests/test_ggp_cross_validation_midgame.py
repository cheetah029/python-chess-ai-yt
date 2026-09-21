"""Extended cross-validation: the engine-vs-GGP agreement gate.

LGREF identifies rules from GDL clauses (Phase 1) and measures their
contributions by ablation in the engine (Phase 3). That is only valid if
the GDL and the engine describe the SAME game, so the agreement rate is
a gate, not a report.

History (issues #170, #177). This file previously asserted
`perfect_match_count >= 1`, which the initial position satisfies
unconditionally — so it passed while agreement sat at 5%. A test that
cannot fail is worse than no test, because it advertises a guarantee it
never checked.

Measured progression as Phase 0.5 fixes landed:

    14%     baseline
    54.7%   after the GGP converter + translator fixes (#170)
    73.0%   after GDL boulder-capture + bishop-safety fixes (#177 B1, B3)
    87.0%   after the central-intersection diagonal fix (#177 B2)

`MIN_AGREEMENT` is a RATCHET: it records the level already achieved and
fails if a change regresses below it. Raise it as the remaining
divergences (#177 B4 and the residuals in docs/ggp_gdl_audit.md) are
closed; never lower it to make a change pass.
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


# Ratchet: the agreement level already achieved on a DEEP sample.
# Raise it as divergences close; never lower it to make a change pass.
# Set below the measured 64.0% (300 positions, 30 plies x 10 games) to
# absorb ply-sequence variation while still failing loudly on a real
# regression. The pre-fix baseline was 14%, so a regression to anything
# near the old behaviour trips this immediately.
MIN_AGREEMENT = 55.0

# Sample size for the gate. Kept modest so the test stays usable in a
# normal run (the GGP resolver is ~1.7s per position), but spread over
# several games and deep enough to include the late-game states where
# the remaining divergences actually occur.
N_GAMES = 4
PLIES_PER_GAME = 25

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
    """The agreement gate: sample many positions across several games
    and require the rate to stay at or above the ratchet.

    Sampling matters more than it looks. Agreement DEGRADES with depth —
    later positions carry transformed queens, invulnerability and
    manipulation freezes, which are exactly where the remaining
    divergences live. A shallow sample therefore flatters the result:
    measured after the Phase 0.5 fixes, the first 20 plies of 5 games
    gave 87%, while 30 plies of 10 games gave 64%.

    So this samples SEVERAL games to a useful depth. A single 20-ply
    game would both overstate agreement and be too small to
    distinguish a real regression from ply-sequence noise.
    """
    ggp = GGPGame.from_file(INTEGRATED)

    perfect_match_count = 0
    total_compared = 0
    discrepancies = []

    for trial in range(N_GAMES):
        rng = random.Random(42 + trial)
        g = Game()
        for ply in range(PLIES_PER_GAME):
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
                    'trial': trial,
                    'ply': ply,
                    'mover': g.next_player,
                    'engine_count': diff['engine_count'],
                    'ggp_count': diff['ggp_count'],
                    'engine_only': engine_only,
                    'ggp_only': ggp_only,
                })
            if not _play_random_ply(g, rng):
                break

    perfect_pct = (perfect_match_count / total_compared * 100
                   if total_compared else 0)
    assert perfect_pct >= MIN_AGREEMENT, (
        f'engine/GGP agreement regressed to {perfect_pct:.1f}% over '
        f'{total_compared} positions (ratchet: {MIN_AGREEMENT}%).\n'
        f'First discrepancies: {discrepancies[:3]}\n'
        f'If this is an intentional GDL change, fix the divergence — '
        f'do not lower MIN_AGREEMENT.')
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
