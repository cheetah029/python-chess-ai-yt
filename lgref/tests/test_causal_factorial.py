"""Interventional decomposition, and why observation could not do it.

Feature discovery reported `Bishop` at d = -0.485 and a mechanism was
attached: live bishops deny your own queen the bishop form. The
mechanism cannot be what the feature measures -- the unlock is a
threshold at "one bishop captured", the feature is a linear count, and
they disagree exactly at one bishop versus none.

The underlying problem is structural, not statistical: in played games
bishop count and bishop-form availability CANNOT vary independently,
because one capture does both. These tests pin the design that crosses
them anyway, and the invariant that makes the decomposition checkable.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

from experiments.variants import make_engine

from lgref.experiments.factorial import (A, B, C, CELLS, D, _drop_one,
                                         _set_count, build, effects, run)
from lgref.experiments.positions import sample_layout


def _layout(seed=0, kind='Bishop', count=2):
    import random

    rng = random.Random(seed)
    for _ in range(50):
        base = sample_layout(rng, min_extra=4, max_extra=8)
        shaped = _set_count(base, base.mover, count, kind)
        if shaped is not None:
            return shaped, base.mover
    raise AssertionError('no usable layout')


def test_only_two_of_the_four_cells_are_reachable_in_play():
    """Which is the entire reason this module exists.

    Each side starts with two bishops and the only way to lose one is to
    have it captured -- which is also the only way to unlock the form.
    So "two live bishops AND form available" (C) and "one bishop AND form
    unavailable" (D) are both unreachable, and they are exactly the two
    cells that identify the separate effects.
    """
    reachable = {(2, False), (1, True)}
    assert {(A.bishops, A.form), (B.bishops, B.form)} == reachable
    assert (C.bishops, C.form) not in reachable
    assert (D.bishops, D.form) not in reachable
    assert len(set(CELLS)) == 4


def test_set_count_hits_the_count_and_spares_royals():
    """A converted royal would decide the game by itself."""
    for kind in ('Bishop', 'Rook', 'Knight'):
        shaped, side = _layout(seed=3, kind=kind)
        mine = [p for p in shaped.pieces if p[0] == side and p[1] == kind]
        assert len(mine) == 2, kind
        # Both royals survive on both sides, and nothing royal became a
        # piece of the intervened kind.
        for colour in ('white', 'black'):
            royals = [p for p in shaped.pieces if p[0] == colour and p[2]]
            assert len(royals) == 2, (colour, kind)
            assert {p[1] for p in royals} == {'King', 'Queen'}


def test_the_one_piece_cells_differ_by_exactly_one_piece():
    """Otherwise the pairing is not a pairing."""
    two, side = _layout(seed=5)
    one = _drop_one(two, side, 'Bishop')
    assert len(one.pieces) == len(two.pieces) - 1
    # Every surviving piece is identical, including its square.
    removed = list(two.pieces)
    for piece in one.pieces:
        removed.remove(piece)
    assert len(removed) == 1
    assert removed[0][0] == side and removed[0][1] == 'Bishop'


def test_the_form_is_written_onto_the_capture_record():
    """The intervention has to actually reach the rule it targets.

    Transformation availability is read from `board.captured_pieces`
    (RULEBOOK.md: a form requires a friendly piece of that type to have
    been captured earlier), so that record IS the knob. A constructed
    position has an empty record, which is why cell C cannot arise by
    placement alone.
    """
    two, side = _layout(seed=7)
    off = build(make_engine, two, A, side, max_turns=60)
    on = build(make_engine, two, C, side, max_turns=60)
    assert off is not None and on is not None
    assert off.board.captured_pieces[side] == []
    assert on.board.captured_pieces[side] == ['bishop']
    # And the rule responds: the queen gains bishop form only in `on`.
    def forms(engine):
        for row in range(8):
            for col in range(8):
                piece = engine.board.squares[row][col].piece
                if piece is not None and getattr(piece, 'is_royal', False) \
                        and type(piece).__name__ == 'Queen' \
                        and piece.color == side:
                    return engine.board.get_transformation_options(
                        piece)
        return None
    assert 'bishop' not in (forms(off) or [])
    assert 'bishop' in (forms(on) or [])


def test_the_decomposition_satisfies_its_own_identity():
    """natural = piece - form, exactly, by construction.

        piece - form = [(A-D)+(C-B)]/2 - [(C-A)+(B-D)]/2 = A - B

    So the confounded contrast play produces is the piece effect MINUS
    the form effect. If the two have opposite signs they partly cancel,
    and the observational coefficient understates both -- which is the
    quantitative reason a marginal number could not be trusted here.
    Measured at 585 layouts: piece -0.050, form +0.034, natural -0.084.
    """
    results = run(make_engine, layouts=8, agent='random', seed=13,
                  max_turns=800)
    summary = effects(results)
    identity = summary['piece'].mean - summary['form'].mean
    assert abs(identity - summary['natural'].mean) < 1e-9


def test_a_censored_cell_drops_the_whole_row():
    """Keeping the rest of a row would break the pairing, and scoring a
    censored game as a loss is #260 -- it would bias every cell toward
    whichever intervention lengthens games."""
    results = run(make_engine, layouts=6, agent='random', seed=17,
                  max_turns=14)
    # A 14-ply cap censors essentially everything, so nothing survives.
    summary = effects(results)
    assert summary['rows'] + summary['dropped'] == len(results)
    for row in results:
        if any(row[cell].censored for cell in CELLS):
            assert summary['rows'] < len(results)
            break


def test_cells_are_played_with_common_random_numbers():
    """The four cells must differ by the intervention, not by their dice."""
    first = run(make_engine, layouts=5, agent='random', seed=23,
                max_turns=600)
    second = run(make_engine, layouts=5, agent='random', seed=23,
                 max_turns=600)
    assert [row[cell].won for row in first for cell in CELLS] == \
           [row[cell].won for row in second for cell in CELLS]
