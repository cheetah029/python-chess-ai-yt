"""What each ablation variant OBSERVABLY does, not what it says it does.

Issue #228. `no_knight_redesign` was described as removing radius-2
movement, jump-capture and leap invulnerability. It removes none of
them: destinations are identical, the jump-capture it substitutes is
broader than the one it replaces, and invulnerability is granted more
often rather than less. Phase 5 then reported that the knight redesign
contradicted three of the functions the designer stated for it, on the
strength of an attack-coverage rise that belonged to the substituted
capture rule.

A description is a claim about behaviour and nothing was checking it.
These tests check it. Each asserts what is MEASURABLY different from
`full`, so a variant cannot be documented as doing something it does
not do -- including, pointedly, the variant that started this.
"""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from experiments.variants import make_engine
from lgref.experiments.mobility import MobilityPlayer


def _play(variant, seed, max_turns=200):
    """A whole game, returning the engine so its record can be read."""
    engine = make_engine(variant, max_turns=max_turns)
    white = MobilityPlayer(rng=random.Random(seed))
    black = MobilityPlayer(rng=random.Random(seed + 99))
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        agent = white if engine.current_player == 'white' else black
        engine.execute_turn(agent.choose_turn(turns, engine))
    return engine


def _turn_types(engine):
    return {turn.get('turn_type')
            for turn in engine.get_game_record().to_dict()['turns']}


def _invulnerable_sightings(variant, seeds=(11, 12)):
    seen = 0
    for seed in seeds:
        engine = make_engine(variant, max_turns=200)
        white = MobilityPlayer(rng=random.Random(seed))
        black = MobilityPlayer(rng=random.Random(seed + 99))
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            agent = white if engine.current_player == 'white' else black
            engine.execute_turn(agent.choose_turn(turns, engine))
            board = engine.board
            seen += sum(
                1 for r in range(8) for c in range(8)
                if board.squares[r][c].piece is not None
                and getattr(board.squares[r][c].piece, 'invulnerable', False))
    return seen


# ---- the variants that do what they say ---------------------------------

def test_no_boulder_removes_the_boulder_and_its_turns():
    engine = _play('no_boulder', 3)
    assert engine.board.boulder is None or not any(
        engine.board.squares[r][c].piece is engine.board.boulder
        for r in range(8) for c in range(8))
    assert 'boulder' not in _turn_types(engine)


def test_full_does_use_the_boulder():
    """Otherwise the test above passes for the wrong reason."""
    assert 'boulder' in _turn_types(_play('full', 3))


def test_no_queen_manipulation_removes_manipulation_turns():
    assert 'manipulation' not in _turn_types(_play('no_queen_manipulation', 3))


def test_full_does_use_manipulation():
    assert 'manipulation' in _turn_types(_play('full', 3))


def test_control_inert_is_rule_identical_to_full():
    """The noise floor of the instrument. Same legal set, same game."""
    one, other = make_engine('full', max_turns=50), \
        make_engine('control_inert', max_turns=50)
    assert len(one.get_all_legal_turns()) == len(other.get_all_legal_turns())
    assert {t.to_sq for t in one.get_all_legal_turns()} == \
        {t.to_sq for t in other.get_all_legal_turns()}


def test_control_double_move_actually_gives_an_extra_turn():
    assert make_engine('control_double_move', max_turns=50).extra_move_every \
        == 10
    assert make_engine('full', max_turns=50).extra_move_every == 0


# ---- the variant that does not (#228) -----------------------------------

def test_no_knight_redesign_does_not_change_knight_movement():
    """The first false claim. Destinations are identical."""
    def destinations(variant):
        engine = make_engine(variant, max_turns=50)
        return {turn.to_sq for turn in engine.get_all_legal_turns()
                if getattr(getattr(turn, 'piece', None), 'name', '')
                == 'knight'}

    assert destinations('no_knight_redesign') == destinations('full'), (
        'if this ever differs, the variant finally restricts movement and '
        'the description should be corrected back')


def test_no_knight_redesign_does_not_remove_invulnerability():
    """The third false claim, and it points the other way.

    Invulnerability is granted MORE often without the "redesign" than
    with it. Whether legacy mode reaching the grant at all is a bug is
    a rule-behaviour question for the designer (#228); this only pins
    that it happens, so the description cannot claim otherwise.
    """
    assert _invulnerable_sightings('no_knight_redesign') > \
        _invulnerable_sightings('full')


def test_no_knight_redesign_threatens_more_not_less():
    """Why the coverage effect attributed to the redesign was not real.

    The substituted pre-v2 jump-capture allows any capturable enemy
    adjacent to the landing square, so the threat map credits a legacy
    knight with far more squares. Phase 5 read the resulting rise as
    the redesign's functions being contradicted.
    """
    from lgref.experiments.metrics import attack_map_coverage

    legacy = make_engine('no_knight_redesign', max_turns=50)
    full = make_engine('full', max_turns=50)
    assert attack_map_coverage(legacy.board, 'white') > \
        attack_map_coverage(full.board, 'white')


def test_the_description_admits_what_it_does_not_isolate():
    """A wrong description is the defect; this pins the correction."""
    from experiments.variants import VARIANTS

    spec = VARIANTS['no_knight_redesign']
    text = getattr(spec, 'description', None) or getattr(spec, 'doc', '')
    assert text, 'the variant carries no description to check'
    assert 'does not isolate' in text.lower() or 'misleading' in text.lower()
    assert '228' in text
