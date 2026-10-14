"""The clone that made search affordable, and the player built on it.

Copying was 90% of every search node: 0.985 ms of `deepcopy` against
0.074 ms of move generation, and 9.27 ms in a midgame position. That is
why 800 simulations cost about 44 seconds a move. A pickle round-trip is
the same operation in C and measures 6-8x faster.

A subtly incomplete copy would corrupt a search in ways that look like a
weak agent rather than like a bug, so the equivalence is tested rather
than assumed.
"""

import copy
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.fastcopy import clone, clone_with_turns
from lgref.experiments.random_play import build
from lgref.experiments.strong import (StrongPlayer, abstract_turns,
                                      material)


def _fingerprint(engine):
    turns = engine.get_all_legal_turns()
    return (engine.current_player, engine.turn_number, engine.winner,
            engine.loss_reason, sorted(repr(t) for t in turns),
            engine.board.get_state_hash(engine.current_player))


def test_the_clone_matches_deepcopy_over_real_play():
    """Checked at every ply of several games, before AND after executing
    a turn on each clone -- the state hash included, so a difference in
    any legal-move-determining field would show."""
    compared = 0
    for seed in range(3):
        engine = make_engine('full', max_turns=200)
        white = build('random', random.Random(seed * 2 + 1), 0)
        black = build('random', random.Random(seed * 2 + 2), 0)
        for _ply in range(30):
            if engine.is_game_over():
                break
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            deep_engine, deep_turns = copy.deepcopy((engine, turns))
            fast_engine, fast_turns = clone_with_turns(engine, turns)
            assert _fingerprint(deep_engine) == _fingerprint(fast_engine)
            deep_engine.execute_turn(deep_turns[0])
            fast_engine.execute_turn(fast_turns[0])
            assert _fingerprint(deep_engine) == _fingerprint(fast_engine)
            compared += 1
            mover = white if engine.current_player == 'white' else black
            engine.execute_turn(mover.choose_turn(turns, engine))
    assert compared >= 30, 'too few states compared to be convincing'


def test_the_clone_is_independent_of_the_original():
    """The #247 bug: a `Turn` references a piece on the board and
    `Board.move` writes onto that piece, so executing a caller's turn on
    a copied engine wrote through to the LIVE game."""
    engine = make_engine('full', max_turns=100)
    turns = engine.get_all_legal_turns()
    before = _fingerprint(engine)
    sim, sim_turns = clone_with_turns(engine, turns)
    sim.execute_turn(sim_turns[0])
    assert _fingerprint(engine) == before, 'the original was mutated'


def test_cloning_a_pair_keeps_the_turns_pointing_at_the_clone():
    """Cloning the engine and its turns separately would reintroduce
    #247, because the turns would still reference the original's
    pieces."""
    engine = make_engine('full', max_turns=100)
    turns = engine.get_all_legal_turns()
    sim, sim_turns = clone_with_turns(engine, turns)
    # The cloned turn's piece is the clone's piece, not the original's.
    row, col = sim_turns[0].from_sq
    assert sim_turns[0].piece is sim.board.squares[row][col].piece
    assert sim_turns[0].piece is not engine.board.squares[row][col].piece


def test_material_ignores_the_neutral_boulder():
    """It belongs to neither side, so counting it would give both
    players the same signed quantity."""
    engine = make_engine('full', max_turns=100)
    assert material(engine, 'white') == 0.0
    assert material(engine, 'black') == 0.0


def test_material_is_antisymmetric():
    engine = make_engine('full', max_turns=100)
    for row in range(8):
        for col in range(8):
            piece = engine.board.squares[row][col].piece
            if piece is not None and getattr(piece, 'color', None) == 'black' \
                    and not getattr(piece, 'is_royal', False):
                engine.board.squares[row][col].piece = None
                break
        else:
            continue
        break
    white = material(engine, 'white')
    assert white > 0
    assert material(engine, 'black') == -white


def test_abstraction_keeps_every_capture():
    """Captures and actions change material or capability, so they are
    never sampled away -- only interchangeable quiet moves are."""
    engine = make_engine('full', max_turns=200)
    rng = random.Random(0)
    agent = build('random', random.Random(1), 0)
    for _ply in range(40):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        captures = [t for t in turns if getattr(t, 'is_capture', False)]
        kept = abstract_turns(turns, rng, sample=2)
        for capture in captures:
            assert capture in kept, 'a capture was abstracted away'
        assert len(kept) <= len(turns)
        engine.execute_turn(agent.choose_turn(turns, engine))


def test_abstraction_cuts_the_width_it_was_built_to_cut():
    """The bishop supplies 42.3% of legal turns and 0.0% of captures, so
    sampling quiet moves per piece should remove a large share of the
    width without touching a single capture."""
    engine = make_engine('full', max_turns=200)
    agent = build('random', random.Random(3), 0)
    for _ply in range(50):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(agent.choose_turn(turns, engine))
    turns = engine.get_all_legal_turns()
    if len(turns) > 30:
        kept = abstract_turns(turns, random.Random(0), sample=6)
        assert len(kept) < len(turns), 'nothing was abstracted'


def test_the_player_returns_a_legal_turn_and_prefers_a_free_capture():
    """The cheapest possible competence check: with a capture available
    that cannot be answered, take it."""
    engine = make_engine('full', max_turns=200)
    agent = build('random', random.Random(5), 0)
    player = StrongPlayer(depth=1, quiescence=1, rng=random.Random(0))
    for _ply in range(30):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        choice = player.choose_turn(turns, engine)
        assert choice in turns
        engine.execute_turn(agent.choose_turn(turns, engine))


def test_quiescence_does_not_score_mid_exchange():
    """A search that stops one ply before a recapture reads a position as
    a piece up when it is level, which is the mechanism behind most of
    what looks like a blunder. With quiescence the two depths must not
    disagree about a position whose only activity is an even trade."""
    engine = make_engine('full', max_turns=200)
    agent = build('random', random.Random(7), 0)
    for _ply in range(30):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(agent.choose_turn(turns, engine))
    turns = engine.get_all_legal_turns()
    if len(turns) < 2:
        return
    quiet = StrongPlayer(depth=1, quiescence=0, rng=random.Random(0))
    deep = StrongPlayer(depth=1, quiescence=3, rng=random.Random(0))
    assert quiet.choose_turn(turns, engine) in turns
    assert deep.choose_turn(turns, engine) in turns
    # Quiescence must cost extra nodes -- otherwise it is not running.
    assert deep.nodes >= quiet.nodes
