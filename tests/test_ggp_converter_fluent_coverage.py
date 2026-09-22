"""The state converter must supply every fluent the GDL reads.

Issue #170. The GGP's `board_to_gdl_facts` translates a Python board
into the GDL's state. If it omits a fluent that some rule reads, that
rule silently changes meaning: `(true (boulder_cooldown 0))` becomes
unsatisfiable and the boulder stops moving; `(true (captured_friendly
...))` becomes unsatisfiable and no transform is ever legal. The GGP
then disagrees with the engine for reasons that have nothing to do with
the GDL's rules being wrong.

Five fluents were missing when this was first measured — boulder_last,
captured_friendly, manipulation_freeze, distance_count and
tiny_endgame_active — plus boulder_cooldown and boulder_first_move,
which were emitted only while the boulder sat on the central
intersection.

Fixing seven instances by hand would not stop the eighth. So the guard
is structural: parse the official infix integrated.gdl, collect every
fluent read via
`(true (X ...))`, and require the converter to be capable of emitting
each one. A new GDL fluent with no converter support fails this test.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
pygame.init()
pygame.font.init()

from game import Game
from ai_controller import AIController
from ggp.infix import parse_infix
from ggp.cross_validation import board_to_gdl_facts

INTEGRATED = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'integrated.gdl')


# Fluents the converter legitimately never emits, each with a reason.
# Anything NOT listed here must be reachable from some board state.
EXEMPT = {
    # Repetition is enforced host-side by GGPGame (issue #160) rather
    # than through the GDL's own state-history counting, so the
    # converter deliberately does not inject repetition counts.
    'state_repetition_count': 'enforced host-side in GGPGame (#160)',
    # Read by the step-10 repetition sketch only; the host computes
    # successor hashes itself.
    'next_state_hash': 'host-side repetition (#160)',
}


def gdl_fluents_read(path=INTEGRATED):
    """Every fluent name appearing as `(true (X ...))` in the GDL."""
    with open(path) as f:
        forms = parse_infix(f.read())

    found = set()

    def walk(term):
        if not isinstance(term, tuple):
            return
        if term and term[0] == 'true' and len(term) > 1 \
                and isinstance(term[1], tuple) and term[1]:
            found.add(term[1][0])
        for child in term:
            walk(child)

    for form in forms:
        walk(form)
    return found


def _fluents_emitted_over_a_game(n_plies=40, seed=7):
    """Union of fluent names the converter emits across a random game.

    One position cannot exercise every fluent — a boulder on a square,
    a manipulation freeze and a captured piece do not co-occur at ply 0
    — so this samples a whole game.
    """
    import random
    rng = random.Random(seed)
    game = Game()
    emitted = set()
    for _ in range(n_plies):
        if game.winner is not None:
            break
        for fact in board_to_gdl_facts(game.board, game.next_player):
            if isinstance(fact, tuple) and fact:
                emitted.add(fact[0])
        if not AIController(game.next_player).take_turn(game):
            break
    return emitted


def test_gdl_fluent_extraction_finds_the_known_ones():
    """Guard the guard: if parsing silently returned nothing, the
    coverage test below would pass vacuously."""
    fluents = gdl_fluents_read()
    assert {'cell', 'control', 'boulder_cooldown', 'captured_friendly',
            'manipulation_freeze'} <= fluents
    assert len(fluents) >= 15


@pytest.mark.parametrize('fluent', sorted(gdl_fluents_read() - set(EXEMPT)))
def test_converter_can_emit_every_gdl_fluent(fluent):
    """Every non-exempt fluent the GDL reads must be emittable.

    Parametrised so a failure names the specific missing fluent rather
    than reporting one opaque set difference.
    """
    # Deterministic source first. Which branch this test takes must NOT
    # depend on how a random game happened to unfold -- an earlier
    # version consulted the game first and was flaky for boulder_last,
    # which some openings reach and others do not.
    if _reachable_in_constructed_state(fluent):
        return

    emitted = getattr(_fluents_emitted_over_a_game, 'cache', None)
    if emitted is None:
        emitted = _fluents_emitted_over_a_game()
        _fluents_emitted_over_a_game.cache = emitted

    assert fluent in emitted, (
        f'the GDL reads (true ({fluent} ...)) but board_to_gdl_facts '
        f'never emits it. Rules depending on it are silently '
        f'unsatisfiable in the GGP. Add converter support, or add '
        f'{fluent!r} to EXEMPT with a reason.')


def _reachable_in_constructed_state(fluent):
    """Can the converter emit `fluent` from a deliberately built board?"""
    game = Game()
    board = game.board

    if fluent == 'tiny_endgame_active':
        board.tiny_endgame_active = True
    elif fluent == 'distance_count':
        board.tiny_endgame_active = True
        board.distance_counts = [0] * 15
        board.distance_counts[4] = 2
    elif fluent == 'captured_friendly':
        board.captured_pieces['white'].append('rook')
    elif fluent == 'manipulation_freeze':
        for row in range(8):
            for col in range(8):
                piece = board.squares[row][col].piece
                if piece is not None:
                    piece.moved_by_queen = True
                    break
            else:
                continue
            break
    elif fluent == 'boulder_last':
        from piece import Boulder
        boulder = Boulder()
        boulder.on_intersection = False
        boulder.cooldown = 0
        boulder.last_square = (3, 3)
        board.squares[4][4].piece = boulder
        board.boulder = None
    elif fluent == 'invulnerable':
        for row in range(8):
            for col in range(8):
                piece = board.squares[row][col].piece
                if piece is not None:
                    piece.invulnerable = True
                    break
            else:
                continue
            break
    else:
        return False

    emitted = {f[0] for f in board_to_gdl_facts(board, 'white')
               if isinstance(f, tuple) and f}
    return fluent in emitted
