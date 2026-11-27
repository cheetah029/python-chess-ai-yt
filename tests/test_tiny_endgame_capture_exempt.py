"""The Tiny Endgame limit exempts EVERY capture (issue #391).

RULEBOOK.md, Tiny Endgame Rule, Limit: "A player may not make a
non-capture turn that would cause the count for the resulting royal
distance to become greater than 3." Two captures were wrongly forbidden
by `Board.would_exceed_distance_limit`, which read "capture" off the
landing square alone:

1. A KING TAKING A FRIENDLY PIECE. The king "may capture enemy pieces,
   friendly pieces, and the boulder" (King section), and the engine
   executes the turn as a capture (`Turn.is_capture`, counts reset), but
   the filter saw a piece of the mover's own colour and called it a
   non-capture.
2. AN ACCEPTED KNIGHT JUMP-CAPTURE. The landing square is empty (the
   victim is the jumped piece), and the filter removed the knight move
   before it was split into accept and decline, so the capture went
   with the decline. Only the decline is a non-capture.

The king taking the BOULDER: exempt from the limit, and (user
decision 2026-11-27) a capture for the count reset too, though the
searcher still does not mark it `is_capture`.

Positions are hand-built; each distance is worked out in its comment.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402
pygame.init()
pygame.font.init()

from board import Board  # noqa: E402
from engine import GameEngine  # noqa: E402
from game import Game  # noqa: E402
from move import Move  # noqa: E402
from piece import Boulder, King, Knight, Queen, Rook  # noqa: E402
from square import Square  # noqa: E402


def _sq(name):
    return 8 - int(name[1]), ord(name[0]) - ord('a')


def _engine(pieces, counts, mover='white'):
    """An engine on a board holding exactly `pieces`, the Tiny Endgame
    rule active with the given distance counts."""
    engine = GameEngine()
    board = engine.board
    for r in range(8):
        for c in range(8):
            board.squares[r][c] = Square(r, c)
    board.boulder = None
    board.turn_number = 20
    engine.turn_number = 20
    board.captured_pieces = {'white': [], 'black': []}
    for name, piece in pieces.items():
        r, c = _sq(name)
        board.squares[r][c] = Square(r, c, piece)
    board.tiny_endgame_active = True
    board.distance_counts = [0] * 15
    for d, k in counts.items():
        board.distance_counts[d] = k
    engine.current_player = mover
    return engine


def _turns(engine, origin):
    r, c = _sq(origin)
    return [t for t in engine.get_all_legal_turns() if t.from_sq == (r, c)]


def _to(turns, name):
    return [t for t in turns if t.to_sq == _sq(name)]


# ---- 1. the king takes a friendly piece ----------------------------------
#
# White king d4, white royal queen d5, black king d8. Closest pair:
# d5-d8 = 3. If the king takes its own queen, the king stands on d5:
# d5-d8 = 3 again. Kd4-c4 leaves the queen on d5 (still 3); Kd4-d3 too.
# So with count 3 at distance 3, EVERY king step that leaves the queen
# where it is keeps distance 3 and is forbidden; only Kxd5 is a capture.

def _king_and_queen(count3):
    return _engine({'d4': King('white'), 'd5': Queen('white'),
                    'd8': King('black')}, {3: count3})


def test_king_taking_a_friendly_piece_is_exempt():
    engine = _king_and_queen(3)
    assert engine.board.get_royal_distance() == 3
    takes = _to(_turns(engine, 'd4'), 'd5')
    assert len(takes) == 1 and takes[0].is_capture


def test_the_kings_non_capturing_steps_are_still_forbidden():
    """Guards against over-exemption: every other king step keeps
    distance 3 (the queen stays on d5), so all are forbidden."""
    engine = _king_and_queen(3)
    king_turns = _turns(engine, 'd4')
    assert {t.to_sq for t in king_turns} == {_sq('d5')}


def test_unsaturated_baseline_offers_every_king_step():
    engine = _king_and_queen(2)
    assert len(_turns(engine, 'd4')) == 8


def test_king_friendly_capture_resets_the_counts():
    engine = _king_and_queen(3)
    engine.board.distance_counts[5] = 2
    takes = _to(_turns(engine, 'd4'), 'd5')[0]
    engine.execute_turn(takes)
    counts = engine.board.distance_counts
    # A capture resets every count; the rule may re-activate on the
    # resulting distance (d5-d8 = 3), never anything else.
    assert all(c == 0 for d, c in enumerate(counts) if d != 3)
    assert counts[3] in (0, 1)


def _king_and_boulder(counts):
    """White king d4, black king d8 (distance 4); the boulder on d5.
    Kxd5 leaves d5-d8 = 3."""
    boulder = Boulder()
    boulder.first_move = False
    return _engine({'d4': King('white'), 'd5': boulder,
                    'd8': King('black')}, counts)


def test_king_taking_the_boulder_is_exempt_from_the_limit():
    takes = _to(_turns(_king_and_boulder({3: 3}), 'd4'), 'd5')
    assert len(takes) == 1


def test_king_taking_the_boulder_resets_the_counts():
    """User decision 2026-11-27: the king taking the boulder is a
    capture for the Tiny Endgame counts. All counts go to 0; the rule
    still applies (the boulder never counted toward activation), so the
    resulting distance d5-d8 = 3 starts again at 1."""
    engine = _king_and_boulder({3: 3, 4: 2, 5: 1})
    takes = _to(_turns(engine, 'd4'), 'd5')[0]
    record = engine.execute_turn(takes)
    assert engine.board.tiny_endgame_active
    assert [(d, c) for d, c in enumerate(engine.board.distance_counts)
            if c] == [(3, 1)]
    # CONFINED TO THE COUNTS: the turn is still not marked a capture.
    assert record.is_capture is False


def test_king_taking_the_boulder_is_still_not_tactical():
    """The searcher's tactical classification is deliberately unchanged
    (it drives quiescence and ordering in every phase)."""
    engine = _king_and_boulder({4: 1})
    takes = _to(_turns(engine, 'd4'), 'd5')
    assert len(takes) == 1 and not takes[0].is_capture
    assert takes[0].jump_choice is None
    tactical = engine.get_tactical_turns()
    assert not [t for t in tactical if t.to_sq == _sq('d5')]


def test_a_quiet_king_step_still_increments():
    """Control: Kd4-c3 (distance c3-d8 = 1 + 5 = 6) counts 6 up from
    0 and carries the rest."""
    engine = _king_and_boulder({4: 2})
    step = _to(_turns(engine, 'd4'), 'c3')[0]
    engine.execute_turn(step)
    assert [(d, c) for d, c in enumerate(engine.board.distance_counts)
            if c] == [(4, 2), (6, 1)]


def test_the_window_and_the_engine_reset_alike():
    """The window's AI path (AIController) already reset the counts on
    a king taking the boulder, testing the landing square's occupant;
    the engine now agrees. Same position, same turn, same counts."""
    from ai_controller import AIController

    class _Take(object):
        def choose_turn(self, turns, engine=None):
            return [t for t in turns if t.to_sq == _sq('d5')][0]

    g = Game()
    b = g.board
    for r in range(8):
        for c in range(8):
            b.squares[r][c].piece = None
    b.boulder = None
    boulder = Boulder()
    boulder.first_move = False
    for name, piece in (('d4', King('white')), ('d5', boulder),
                        ('d8', King('black'))):
        r, c = _sq(name)
        b.squares[r][c].piece = piece
    b.turn_number = 20
    b.tiny_endgame_active = True
    b.distance_counts = [0] * 15
    b.distance_counts[3], b.distance_counts[4] = 3, 2
    g.next_player = 'white'
    assert AIController('white', player=_Take()).take_turn(g)

    engine = _king_and_boulder({3: 3, 4: 2})
    engine.execute_turn(_to(_turns(engine, 'd4'), 'd5')[0])
    assert b.distance_counts == engine.board.distance_counts


# ---- 2. the accepted jump-capture ----------------------------------------
#
# White king a1, white royal queen b1, black king h8, black royal queen
# g8: closest pair b1-g8 = 5 + 7 = 12. A white knight on d4 and a black
# rook on d5 that moved last turn. A knight move leaves every royal in
# place, so with count 3 at 12 every knight move is forbidden -- except
# that the three moves jumping d5 (to c6, d6, e6) may still CAPTURE.

def _jump(count12):
    rook = Rook('black')
    rook.moved_last_turn = True
    return _engine({'a1': King('white'), 'b1': Queen('white'),
                    'h8': King('black'), 'g8': Queen('black'),
                    'd4': Knight('white'), 'd5': rook}, {12: count12})


JUMP_LANDINGS = {_sq('c6'), _sq('d6'), _sq('e6')}


def test_accepted_jump_capture_is_exempt_and_its_decline_is_not():
    engine = _jump(3)
    assert engine.board.get_royal_distance() == 12
    knight = _turns(engine, 'd4')
    assert {t.to_sq for t in knight} == JUMP_LANDINGS
    assert all(t.jump_choice == _sq('d5') for t in knight), \
        'only the accepting turns may remain'
    assert all(t.has_jump_offer for t in knight)


def test_unsaturated_jump_offers_both_accept_and_decline():
    engine = _jump(2)
    knight = _turns(engine, 'd4')
    for landing in JUMP_LANDINGS:
        here = [t for t in knight if t.to_sq == landing]
        assert sorted(t.jump_choice is None for t in here) == [False, True]


def test_accepting_the_jump_capture_resets_the_counts():
    engine = _jump(3)
    turn = [t for t in _turns(engine, 'd4') if t.to_sq == _sq('d6')][0]
    engine.execute_turn(turn)
    assert engine.board.squares[3][3].piece is None      # d5 rook taken
    counts = engine.board.distance_counts
    assert all(c == 0 for d, c in enumerate(counts) if d != 12)


def test_tactical_generation_agrees_with_the_full_one():
    engine = _jump(3)
    full = [t for t in engine.get_all_legal_turns()
            if t.is_capture or t.jump_choice is not None]
    key = lambda t: (t.turn_type, t.from_sq, t.to_sq, t.jump_choice)  # noqa
    assert sorted(map(key, engine.get_tactical_turns())) \
        == sorted(map(key, full))


def test_a_forced_jump_capture_is_a_legal_turn_not_a_loss():
    """The bug's sharpest consequence. White king a1, black king h8
    (distance 14); white knight d4, black rook d5 moved last turn.
    Counts 3 at 14 (every knight move and nothing else changes it) and
    at 13 and 12 (Ka2/Kb1 -> 13, Kb2 -> 12). Every non-capture is
    forbidden, so the jump-captures are white's only turns. Before
    #391 white had NO legal turn here and lost."""
    rook = Rook('black')
    rook.moved_last_turn = True
    engine = _engine({'a1': King('white'), 'h8': King('black'),
                      'd4': Knight('white'), 'd5': rook},
                     {12: 3, 13: 3, 14: 3})
    turns = engine.get_all_legal_turns()
    assert {(t.to_sq, t.jump_choice) for t in turns} \
        == {(landing, _sq('d5')) for landing in JUMP_LANDINGS}
    assert engine.board.has_legal_moves('white')


# ---- 3. what the UI reads -----------------------------------------------

def test_filtered_move_says_whether_the_decline_is_forbidden():
    """main.py looks the released move up in the filtered move list and
    reads `decline_forbidden` from it."""
    for count, forbidden in ((3, True), (2, False)):
        board = _jump(count).board
        knight = board.squares[4][3].piece
        knight.clear_moves()
        board.knight_moves(knight, 4, 3)
        board.filter_endgame_moves(knight, 'white')
        released = Move(Square(4, 3), Square(*_sq('d6')))
        listed = next(m for m in knight.moves if m == released)
        assert listed.decline_forbidden is forbidden
        knight.clear_moves()


def test_ui_hides_the_landing_square_when_the_decline_is_forbidden():
    g = Game()
    surface = pygame.Surface((800, 800))
    g.jump_capture_targets = [(3, 3)]
    g.jump_capture_landing = (2, 3)
    drawn = []
    real_rect = pygame.draw.rect

    def spy(surf, color, rect, *a, **k):
        drawn.append(rect)
        return real_rect(surf, color, rect, *a, **k)

    pygame.draw.rect = spy
    try:
        g.jump_decline_forbidden = True
        g.show_jump_capture_targets(surface)
        forbidden = len(drawn)
        drawn.clear()
        g.jump_decline_forbidden = False
        g.show_jump_capture_targets(surface)
        allowed = len(drawn)
    finally:
        pygame.draw.rect = real_rect
    assert (forbidden, allowed) == (1, 2)


def test_cancel_clears_the_forbidden_decline():
    g = Game()
    g.jump_capture_targets = [(3, 3)]
    g.jump_capture_landing = (2, 3)
    g._pre_jump_capture_snapshot = g._snapshot()
    g.jump_decline_forbidden = True
    assert g.cancel_jump_capture()
    assert g.jump_decline_forbidden is False


def test_legacy_knight_mode_is_untouched():
    """The jump-capture exemption is a v2 rule; a legacy-knight board
    keeps no forbidden move."""
    board = _jump(3).board
    board.knight_mode = Board.KNIGHT_MODE_LEGACY
    knight = board.squares[4][3].piece
    knight.clear_moves()
    board.knight_moves(knight, 4, 3)
    board.filter_endgame_moves(knight, 'white')
    assert not any(m.decline_forbidden for m in knight.moves)
