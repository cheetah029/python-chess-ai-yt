"""The Tiny Endgame limit in the GDL filters `legal` by each turn's
RESULTING royal distance (issue #389).

RULEBOOK.md, Tiny Endgame Rule, Limit: "A player may not make a
non-capture turn that would cause the count for the resulting royal
distance to become greater than 3. If every legal turn would do so,
that player loses." The royal distance is the Manhattan distance of the
closest opposing pair of royal pieces (kings and royal queens, in any
form).

THE BUG. The old filter was

    legal_after_tiny_filter(PLAYER,MOVE) :-
        legal(PLAYER,MOVE) & ~tiny_endgame_limit_exceeded(NEXT_D)

with NEXT_D never bound to the move, so under negation as failure it
banned every non-capture turn as soon as ANY distance had count 3. It
was also a separate relation: `legal` stayed unfiltered, so a GGP
player was offered turns the rules forbid.

THE FIX. Every legal rule for a turn that can be a non-capture ends
with `~tiny_endgame_forbids(<its move>)`, and tiny_endgame_forbids
computes where the royals stand after the turn (including an enemy
manipulation of a transformed royal queen).

Three groups of tests:

1. Hand-built positions whose answer is worked out by hand in the
   comments (the GDL alone).
2. The non-capture distance-count update, by hand.
3. Cross-validation against the engine, in tiny-endgame positions,
   for the filtered legal moves and for the count update. The engine
   wrongly forbids two kinds of capture (#391); those are excluded
   explicitly and pinned by strict-xfail tests that start passing
   when the engine is fixed.
"""

import os
import random
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, ROOT)

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402
pygame.init()

from ggp.game import GGPGame  # noqa: E402

INTEGRATED = os.path.join(ROOT, 'docs', 'gdl', 'integrated.gdl')


@pytest.fixture(scope='module')
def ggp():
    return GGPGame.from_file(INTEGRATED)


def _legal(ggp, facts, player='white'):
    ggp.state = set(facts)
    return set(m for m in ggp.legal_moves(player) if m != 'noop')


def _counts(**by_distance):
    """distance_count facts, e.g. _counts(d3=3, d4=2)."""
    return [('distance_count', k[1:], str(v)) for k, v in by_distance.items()]


ACTIVE = [('tiny_endgame_active',)]
WHITE = [('control', 'white'), ('turn_number', '40')]

# ---- Position A: two lone kings, white to move -------------------------
#
# White king d4, black king d8: royal distance 0 + 4 = 4. The white
# king's eight steps and the distance each leaves (to d8):
#     d5 -> 3      c5, e5 -> 4      c4, e4, d3 -> 5      c3, e3 -> 6
KINGS_A = [('cell', 'd', '4', 'white', 'king'),
           ('cell', 'd', '8', 'black', 'king')]


def _king(tf, tr):
    return ('move', 'king', 'd', '4', tf, tr)


ALL_KING_STEPS = {_king(f, r) for f, r in
                  [('c', '3'), ('c', '4'), ('c', '5'), ('d', '3'),
                   ('d', '5'), ('e', '3'), ('e', '4'), ('e', '5')]}


def test_unrestricted_position_offers_all_eight_king_steps(ggp):
    """The baseline the other tests subtract from."""
    assert _legal(ggp, KINGS_A + WHITE) == ALL_KING_STEPS
    assert _legal(ggp, KINGS_A + WHITE + ACTIVE) == ALL_KING_STEPS


def test_only_steps_to_the_saturated_distance_are_forbidden(ggp):
    """Count 3 at distance 3: only d5 (distance 3) is forbidden."""
    moves = _legal(ggp, KINGS_A + WHITE + ACTIVE + _counts(d3=3, d4=2))
    assert moves == ALL_KING_STEPS - {_king('d', '5')}


def test_a_saturated_distance_no_turn_reaches_forbids_nothing(ggp):
    """THE #389 REGRESSION. Count 3 at distance 10, which no turn here
    produces, must forbid nothing. The old unbound filter banned every
    non-capture turn here."""
    moves = _legal(ggp, KINGS_A + WHITE + ACTIVE + _counts(d10=3))
    assert moves == ALL_KING_STEPS


def test_the_filter_needs_the_rule_to_be_active(ggp):
    moves = _legal(ggp, KINGS_A + WHITE + _counts(d3=3))
    assert moves == ALL_KING_STEPS


def test_saturated_current_distance_forbids_every_turn_that_keeps_it(ggp):
    """Count 3 at the CURRENT distance 4. A rook move leaves both kings
    where they are, so every rook move is forbidden; of the king steps,
    c5 and e5 keep distance 4 and are forbidden, the rest are allowed."""
    rook = [('cell', 'h', '1', 'white', 'rook')]
    unrestricted = _legal(ggp, KINGS_A + rook + WHITE + ACTIVE)
    rook_moves = {m for m in unrestricted if m[1] == 'rook'}
    assert rook_moves, 'the rook must have moves when nothing is saturated'
    moves = _legal(ggp, KINGS_A + rook + WHITE + ACTIVE + _counts(d4=3))
    assert moves == ALL_KING_STEPS - {_king('c', '5'), _king('e', '5')}


@pytest.mark.parametrize('occupant', [
    ('black', 'rook'),        # an ordinary capture
    ('white', 'rook'),        # the king takes a friendly piece
    ('none', 'boulder'),      # only a king may capture the boulder
])
def test_a_capture_onto_the_saturated_distance_is_allowed(ggp, occupant):
    """Captures are exempt. Kxd5 leaves distance 3, whose count is 3."""
    piece = [('cell', 'd', '5') + occupant]
    extra = [('boulder_cooldown', '0')] if occupant[1] == 'boulder' else []
    moves = _legal(ggp, KINGS_A + piece + extra + WHITE + ACTIVE
                   + _counts(d3=3))
    assert _king('d', '5') in moves


def test_every_non_capture_forbidden_is_a_loss(ggp):
    """White king a1 alone (its royal queen is gone), black king h8:
    distance 14. The king's steps a2, b1 (13) and b2 (12) are all
    forbidden, so white has no legal turn and loses."""
    facts = [('cell', 'a', '1', 'white', 'king'),
             ('cell', 'h', '8', 'black', 'king')] + WHITE + ACTIVE
    ggp.state = set(facts + _counts(d12=3, d13=3))
    assert _legal(ggp, ggp.state) == set()
    assert ggp.is_terminal()
    assert ggp.goal('white') == 0 and ggp.goal('black') == 100

    ggp.state = set(facts + _counts(d12=2, d13=3))
    assert _legal(ggp, ggp.state) == {('move', 'king', 'a', '1', 'b', '2')}
    assert not ggp.is_terminal()


# ---- Transformation ------------------------------------------------------
#
# A transformation moves nothing, so its resulting distance is the
# current one. White king a1, white royal queen in base form c3, black
# king h8: closest pair c3-h8 = 5 + 5 = 10.
TRANSFORM_POS = [('cell', 'a', '1', 'white', 'king'),
                 ('cell', 'c', '3', 'white', 'queen'),
                 ('queen_form', 'c', '3', 'base'),
                 ('queen_royal', 'c', '3'),
                 ('cell', 'h', '8', 'black', 'king'),
                 ('captured_friendly', 'white', 'knight')] + WHITE + ACTIVE


def test_transform_is_forbidden_only_when_the_current_distance_is_saturated(
        ggp):
    to_knight = ('transform', 'c', '3', 'knight')
    assert to_knight in _legal(ggp, TRANSFORM_POS + _counts(d10=2))
    assert to_knight not in _legal(ggp, TRANSFORM_POS + _counts(d10=3))


def test_reverting_to_base_is_forbidden_too(ggp):
    pos = [f for f in TRANSFORM_POS if f != ('queen_form', 'c', '3', 'base')]
    pos.append(('queen_form', 'c', '3', 'knight'))
    to_base = ('transform', 'c', '3', 'base')
    assert to_base in _legal(ggp, pos + _counts(d10=2))
    assert to_base not in _legal(ggp, pos + _counts(d10=3))


# ---- Manipulating a transformed royal queen -----------------------------
#
# White king a1, white royal queen (base) e1. Black king h8, black
# ROYAL queen in knight form e5 -- the white queen sees it up the open
# e-file and may manipulate it, because it is transformed. Current
# distance: e1-e5 = 4. The knight's sixteen destinations and the
# distance each leaves (closest of a1/e1 to the moved queen; the kings'
# pair a1-h8 = 14 and e1-h8 = 10 never win):
#     e3 -> 2    d3, f3 -> 3    c3, g3 -> 4    c4, g4 -> 5
#     c5, g5, e7 -> 6    c6, g6, d7, f7 -> 7    c7, g7 -> 8
MANIP_POS = [('cell', 'a', '1', 'white', 'king'),
             ('cell', 'e', '1', 'white', 'queen'),
             ('queen_form', 'e', '1', 'base'),
             ('queen_royal', 'e', '1'),
             ('cell', 'h', '8', 'black', 'king'),
             ('cell', 'e', '5', 'black', 'queen'),
             ('queen_form', 'e', '5', 'knight'),
             ('queen_royal', 'e', '5')] + WHITE + ACTIVE

MANIP_DISTANCE = {
    ('e', '3'): 2, ('d', '3'): 3, ('f', '3'): 3, ('c', '3'): 4,
    ('g', '3'): 4, ('c', '4'): 5, ('g', '4'): 5, ('c', '5'): 6,
    ('g', '5'): 6, ('e', '7'): 6, ('c', '6'): 7, ('g', '6'): 7,
    ('d', '7'): 7, ('f', '7'): 7, ('c', '7'): 8, ('g', '7'): 8,
}


def _manips(moves):
    return {(m[5], m[6]) for m in moves
            if m[0] == 'manipulate' and (m[3], m[4]) == ('e', '5')}


def test_manipulation_destinations_baseline(ggp):
    assert _manips(_legal(ggp, MANIP_POS)) == set(MANIP_DISTANCE)


@pytest.mark.parametrize('saturated', [2, 3, 4, 7])
def test_manipulating_a_royal_queen_is_judged_by_where_it_lands(
        ggp, saturated):
    """A manipulation moves a royal, so each destination has its own
    resulting distance. Count 3 at `saturated` forbids exactly the
    destinations that leave that distance."""
    counts = _counts(**{'d{}'.format(saturated): 3})
    allowed = _manips(_legal(ggp, MANIP_POS + counts))
    expected = {sq for sq, d in MANIP_DISTANCE.items() if d != saturated}
    assert allowed == expected


# ---- The knight's jump-capture and its declined twin --------------------
#
# White king a1, white royal queen b1, black king h8, black royal queen
# g8: closest pair b1-g8 = 5 + 7 = 12. A white knight on d4; a black
# rook on d5 moved last turn, so the knight may jump it. A knight move
# leaves every royal where it is, so with count 3 at 12 every knight
# move is forbidden -- but the jump-CAPTURE is a capture and is allowed.
JUMP_POS = [('cell', 'a', '1', 'white', 'king'),
            ('cell', 'b', '1', 'white', 'queen'),
            ('queen_form', 'b', '1', 'base'), ('queen_royal', 'b', '1'),
            ('cell', 'h', '8', 'black', 'king'),
            ('cell', 'g', '8', 'black', 'queen'),
            ('queen_form', 'g', '8', 'base'), ('queen_royal', 'g', '8'),
            ('cell', 'd', '4', 'white', 'knight'),
            ('cell', 'd', '5', 'black', 'rook'),
            ('spatial_move_last_turn', 'd', '5')] + WHITE + ACTIVE


def test_jump_capture_allowed_its_declined_twin_forbidden(ggp):
    jump = ('jump_capture', 'd', '4', 'd', '6', 'd', '5')
    decline = ('move', 'knight', 'd', '4', 'd', '6')
    free = _legal(ggp, JUMP_POS + _counts(d12=2))
    assert jump in free and decline in free
    capped = _legal(ggp, JUMP_POS + _counts(d12=3))
    assert jump in capped
    assert decline not in capped
    assert not {m for m in capped if m[:2] == ('move', 'knight')}


# ---- 2. The distance-count update, by hand -------------------------------

def _step(ggp, facts, move, player='white'):
    ggp.state = set(facts)
    other = 'black' if player == 'white' else 'white'
    ggp.step({player: move, other: 'noop'})
    return ggp.state


def _count_facts(state):
    return {(f[1], f[2]) for f in state
            if isinstance(f, tuple) and f[0] == 'distance_count'}


def test_non_capture_increments_the_resulting_distance_and_carries_the_rest(
        ggp):
    """Kd4-d3 leaves distance 5: its count goes 1 -> 2, the count at the
    old distance 4 is carried unchanged, and the rule stays active."""
    state = _step(ggp, KINGS_A + WHITE + ACTIVE + _counts(d4=2, d5=1),
                  _king('d', '3'))
    assert _count_facts(state) == {('4', '2'), ('5', '2')}
    assert ('tiny_endgame_active',) in state


def test_a_distance_with_no_count_starts_at_one(ggp):
    """Kd4-c3 leaves distance 6, which had no count (0)."""
    state = _step(ggp, KINGS_A + WHITE + ACTIVE + _counts(d4=2),
                  _king('c', '3'))
    assert _count_facts(state) == {('4', '2'), ('6', '1')}


def test_a_turn_that_moves_no_royal_counts_the_current_distance(ggp):
    rook = [('cell', 'h', '1', 'white', 'rook')]
    state = _step(ggp, KINGS_A + rook + WHITE + ACTIVE + _counts(d4=2),
                  ('move', 'rook', 'h', '1', 'h', '2'))
    assert _count_facts(state) == {('4', '3')}


def test_an_enemy_manipulation_of_a_royal_counts_where_it_lands(ggp):
    """White manipulates the black royal queen e5 -> g7: distance 8."""
    state = _step(ggp, MANIP_POS + _counts(d4=1),
                  ('manipulate', 'e', '1', 'e', '5', 'g', '7'))
    assert _count_facts(state) == {('4', '1'), ('8', '1')}


def test_counts_are_not_touched_when_the_rule_is_off(ggp):
    state = _step(ggp, KINGS_A + WHITE + _counts(d4=2), _king('d', '3'))
    assert _count_facts(state) == set()


# ---- 3. Cross-validation against the engine ------------------------------

from board import Board  # noqa: E402
from engine import GameEngine  # noqa: E402
from piece import King, Knight, Queen, Rook  # noqa: E402
from square import Square  # noqa: E402
from ggp.cross_validation import (  # noqa: E402
    board_to_gdl_facts, compare_legal_moves, turn_to_gdl_move,
    _normalize_manipulate)
from lgref.experiments.positions import (  # noqa: E402
    apply_layout, sample_layout)


def _diff(ggp, board, player):
    ggp.state = set(board_to_gdl_facts(board, player))
    return compare_legal_moves(types.SimpleNamespace(board=board), ggp,
                               player)


def _king_takes_friend(board, move):
    """Engine bug #391, class 1: the engine's filter treats a king taking
    its own piece as a non-capture."""
    if move[:2] != ('move', 'king'):
        return False
    row, col = 8 - int(move[5]), ord(move[4]) - ord('a')
    target = board.squares[row][col].piece
    mover = board.squares[8 - int(move[3])][ord(move[2]) - ord('a')].piece
    return target is not None and target.color == mover.color


def _saturated_positions(seed, n):
    """Seeded tiny-endgame positions with random saturated counts.

    Layouts come from the LGREF sampler's endgame regime (equal
    non-queen material, so the rule activates). Counts are drawn at
    random for every distance, and half the time the CURRENT distance
    is saturated too -- the case that forbids every turn moving no
    royal.
    """
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        layout = sample_layout(rng, min_extra=1, max_extra=2, endgame=True)
        engine = GameEngine()
        apply_layout(engine, layout)
        board = engine.board
        if not board.tiny_endgame_active:
            continue
        for d in range(1, 15):
            board.distance_counts[d] = rng.choice((0, 1, 2, 3, 3))
        if rng.random() < 0.5:
            board.distance_counts[board.get_royal_distance()] = 3
        out.append(engine)
    return out


def test_filtered_legal_moves_match_the_engine(ggp):
    """GGP legal == engine legal in 40 saturated tiny-endgame positions,
    except the engine's #391 king-takes-friend class, which the GDL
    rightly allows. Also checks the test is not vacuous: the filter
    must actually remove turns in most positions."""
    restricted = 0
    for engine in _saturated_positions(seed=389, n=40):
        board, player = engine.board, engine.current_player
        d = _diff(ggp, board, player)
        assert d['engine_only'] == [], d['engine_only']
        unexplained = [m for m in d['ggp_only']
                       if not _king_takes_friend(board, m)]
        assert unexplained == [], unexplained
        # Non-vacuity: switch the rule off and count what it removed.
        ggp.state = set(board_to_gdl_facts(board, player)) - {
            ('tiny_endgame_active',)}
        if len(ggp.legal_moves(player)) > d['ggp_count']:
            restricted += 1
    assert restricted >= 20, restricted


def test_count_update_matches_the_engine(ggp):
    """After a random non-capture turn, the GDL's distance counts and
    activation flag equal the engine's. Captures are not compared: the
    re-initialisation after a capture still rests on the sketched
    activation predicate (issue #389)."""
    rng = random.Random(3891)
    compared = 0
    for engine in _saturated_positions(seed=3890, n=25):
        board, player = engine.board, engine.current_player
        facts = set(board_to_gdl_facts(board, player))
        ggp.state = set(facts)
        gdl_moves = [m for m in ggp.legal_moves(player) if m != 'noop']
        by_term = {_normalize_manipulate(m): m for m in gdl_moves}
        quiet = [t for t in engine.get_all_legal_turns()
                 if not t.is_capture and t.jump_choice is None
                 and turn_to_gdl_move(t) in by_term]
        if not quiet:
            continue
        turn = rng.choice(quiet)
        gdl_move = by_term[turn_to_gdl_move(turn)]
        engine.execute_turn(turn)
        other = 'black' if player == 'white' else 'white'
        ggp.state = set(facts)
        ggp.step({player: gdl_move, other: 'noop'})
        expected = {(str(d), str(c))
                    for d, c in enumerate(engine.board.distance_counts)
                    if d >= 1 and c}
        assert _count_facts(ggp.state) == expected, (gdl_move, expected)
        assert (('tiny_endgame_active',) in ggp.state) \
            == engine.board.tiny_endgame_active
        compared += 1
    assert compared >= 20, compared


def _engine_board(pieces, counts):
    board = Board()
    for r in range(8):
        for c in range(8):
            board.squares[r][c] = Square(r, c)
    board.boulder = None
    board.turn_number = 20
    board.captured_pieces = {'white': [], 'black': []}
    for name, piece in pieces.items():
        r, c = 8 - int(name[1]), ord(name[0]) - ord('a')
        board.squares[r][c] = Square(r, c, piece)
    board.tiny_endgame_active = True
    board.distance_counts = [0] * 15
    for d, k in counts.items():
        board.distance_counts[d] = k
    return board


def _jump_board(count):
    rook = Rook('black')
    rook.moved_last_turn = True
    return _engine_board({'a1': King('white'), 'b1': Queen('white'),
                          'h8': King('black'), 'g8': Queen('black'),
                          'd4': Knight('white'), 'd5': rook}, {12: count})


def test_engine_and_gdl_agree_on_the_jump_position_when_not_saturated(ggp):
    d = _diff(ggp, _jump_board(2), 'white')
    assert d['engine_only'] == [] and d['ggp_only'] == []
    assert ('jump_capture', 'd', '4', 'd', '6', 'd', '5') in d['common']


@pytest.mark.xfail(strict=True, reason='engine bug #391: the engine '
                   'forbids an accepted jump-capture and a king taking a '
                   'friendly piece when the distance is saturated')
def test_engine_allows_the_captures_the_rulebook_exempts(ggp):
    """In the saturated jump position the GDL offers Ka1xb1 (the king
    takes its own royal queen) and the three jump-captures of d5; the
    engine offers none of them. Passes once #391 is fixed."""
    d = _diff(ggp, _jump_board(3), 'white')
    assert d['ggp_only'] == [], d['ggp_only']


@pytest.mark.parametrize('facts', [
    MANIP_POS + _counts(d3=3),
    JUMP_POS + _counts(d12=3),
    KINGS_A + WHITE + ACTIVE + _counts(d4=3),
], ids=['manipulation', 'jump', 'kings'])
def test_the_reference_resolver_agrees(ggp, facts):
    """The fast reasoner and the top-down reference resolver give the
    same filtered legal moves (the resolver evaluates bodies left to
    right, so the guard's argument order matters to it)."""
    reference = GGPGame.from_file(INTEGRATED, reasoner='resolver')
    assert reference.reasoner == 'resolver'
    assert _legal(reference, facts) == _legal(ggp, facts)
