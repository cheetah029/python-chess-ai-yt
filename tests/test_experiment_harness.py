"""LGMEF experiment harness (issue #168).

Covers the engine ablation switches, the variant registry, the
well-formedness gate, and the per-game metrics emitted by
play_training_game. Engine-level only — no torch training epochs; the
one play_training_game test uses epsilon=1.0 so the network is never
consulted (network=None).
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pytest

from board import Board
from engine import GameEngine
from piece import King, Rook
from experiments.variants import VARIANTS, get_variant, make_engine
from experiments.wellformedness import check_variant


def _play_random(engine, rng, max_plies):
    """Random playout helper; returns executed turn-type counts."""
    counts = {}
    for _ in range(max_plies):
        if engine.is_game_over():
            break
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        turn = rng.choice(turns)
        counts[turn.turn_type] = counts.get(turn.turn_type, 0) + 1
        engine.execute_turn(turn)
    return counts


# ---- Variant registry ----------------------------------------------------

def test_registry_has_all_planned_variants():
    assert set(VARIANTS) == {
        'full', 'no_boulder', 'no_tiny_endgame', 'no_queen_manipulation',
        'no_knight_redesign', 'baseline', 'control_inert',
        'control_double_move'}


def test_unknown_variant_raises_with_valid_list():
    with pytest.raises(ValueError, match='no_boulder'):
        get_variant('nonsense')


def test_control_inert_is_rule_identical_to_full():
    assert get_variant('control_inert').engine_kwargs == \
        get_variant('full').engine_kwargs == {}


# ---- Engine ablation switches --------------------------------------------

def test_default_engine_unchanged():
    """The full game: boulder present, v2 knight, flags on."""
    e = GameEngine()
    assert e.board.boulder is not None
    assert e.board.knight_mode == Board.KNIGHT_MODE_V2
    assert e.enable_tiny_endgame and e.enable_manipulation
    assert e.extra_move_every == 0


def test_no_boulder_removes_boulder_and_boulder_turns():
    e = make_engine('no_boulder')
    assert e.board.boulder is None
    counts = _play_random(e, random.Random(1), 60)
    assert 'boulder' not in counts


def test_no_knight_redesign_uses_legacy_board():
    e = make_engine('no_knight_redesign')
    assert e.board.knight_mode == Board.KNIGHT_MODE_LEGACY


def test_no_queen_manipulation_never_offers_manipulation_turns():
    e = make_engine('no_queen_manipulation')
    rng = random.Random(2)
    for _ in range(60):
        if e.is_game_over():
            break
        turns = e.get_all_legal_turns()
        if not turns:
            break
        assert all(t.turn_type != 'manipulation' for t in turns)
        e.execute_turn(rng.choice(turns))


def test_no_tiny_endgame_never_activates():
    """Craft a board that satisfies is_tiny_endgame (K+R vs K+R, no
    pawns) and verify the disabled engine never activates the rule
    while the default engine does."""
    def _make(enable):
        e = GameEngine(enable_tiny_endgame=enable)
        for row in range(8):
            for col in range(8):
                e.board.squares[row][col].piece = None
        e.board.boulder = None
        e.board.squares[0][0].piece = King('black')
        e.board.squares[7][7].piece = King('white')
        e.board.squares[0][7].piece = Rook('black')
        e.board.squares[7][0].piece = Rook('white')
        assert e.board.is_tiny_endgame()
        turns = e.get_all_legal_turns()
        e.execute_turn(random.Random(3).choice(turns))
        return e

    assert _make(True).board.tiny_endgame_active is True
    assert _make(False).board.tiny_endgame_active is False


def test_double_move_control_grants_consecutive_turns():
    e = GameEngine(extra_move_every=2)
    rng = random.Random(4)
    players = []
    for _ in range(8):
        turns = e.get_all_legal_turns()
        players.append(e.current_player)
        e.execute_turn(rng.choice(turns))
    # With N=2 the mover of every 2nd completed turn repeats, so some
    # consecutive pair shares a player — impossible without the control.
    assert any(a == b for a, b in zip(players, players[1:]))
    # The latch prevents chained extras: never 3 in a row.
    assert not any(a == b == c for a, b, c in
                   zip(players, players[1:], players[2:]))


# ---- Metrics in play_training_game ---------------------------------------

def test_play_training_game_emits_metrics():
    from trainer import play_training_game
    # epsilon=1.0 → pure random turn choice; the network is never used.
    states, outcomes, info = play_training_game(
        network=None, device='cpu', max_turns=30, epsilon=1.0,
        engine_kwargs=get_variant('no_boulder').engine_kwargs)
    m = info['metrics']
    assert m['avg_branching'] > 0 and m['max_branching'] >= m['avg_branching']
    assert sum(m['turn_type_counts'].values()) == info['total_turns']
    assert 'boulder' not in m['turn_type_counts']
    assert 'captures' in m and 'tiny_endgame_activated' in m


# ---- Well-formedness gate ------------------------------------------------

@pytest.mark.parametrize('variant', ['full', 'baseline', 'control_double_move'])
def test_wellformedness_gate_passes_for(variant):
    report = check_variant(variant, n_games=3, max_turns=80, seed=5)
    assert report['ok'], report['anomalies']
    assert len(report['games']) == 3
    for g in report['games']:
        assert g['total_turns'] <= 80
        assert g['avg_branching'] > 0
