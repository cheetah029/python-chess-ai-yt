"""Equivalent descriptions must give the same rules (#314).

A reviewer's point: interpreting an action's FIRST argument as its
subject is an assumption about how a game is encoded, and two equivalent
encodings -- `move(knight, FF, FR, TF, TR)` and `move(FF, FR, TF, TR,
knight)` -- would be analysed differently. These tests rewrite each game
into equivalent forms and require the identical partition.

Measured before the fix: rotating the action arguments changed 49 of the
rules found in Royal Chess, and a consistent renaming of every predicate
changed 32 there and 2 in nim, because clustering ordered statements by
an id that carries the predicate's name.

An OPAQUE renaming (every name replaced by a code) used to change Royal
Chess's rules, because alias detection recognised `occupied_except` as a
variant of `occupied` partly by its NAME. Detection is structural now
(#320), and the opaque renaming is invariant like the others.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.identify.clauses import discover_subject_slots, load
from lgref.identify.robustness import (compare, forms_of, rename_symbols,
                                       rotate_action_arguments)

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, '..', 'identify', 'testgames')
ROYAL = os.path.join(HERE, '..', '..', 'docs', 'gdl', 'integrated.gdl')
SMALL = [os.path.join(GAME_DIR, g + '.gdl')
         for g in ('tictactoe', 'nim', 'corridor', 'montyhall',
                   'muddychildren')]


# ---- the subject slot is discovered, not assumed -------------------------

def test_royal_chess_finds_the_piece_in_the_first_argument():
    actions = [form[1][2] for form in forms_of(ROYAL)
               if isinstance(form, tuple) and form[0] == '<='
               and isinstance(form[1], tuple) and form[1][0] == 'legal']
    slots, subjects = discover_subject_slots(actions)
    assert slots['move'] == {4: frozenset({1}), 5: frozenset({1})}
    assert {'knight', 'bishop', 'boulder', 'king', 'pawn', 'queen',
            'rook'} <= subjects
    # A single constant is a tag, not a choice among subjects:
    # `transform(?, ?, base)` names no subject.
    assert 'transform' not in slots
    assert 'base' not in subjects


def test_the_slot_follows_the_subject_wherever_it_is_written():
    rotated = rotate_action_arguments(forms_of(ROYAL))
    actions = [form[1][2] for form in rotated
               if isinstance(form, tuple) and form[0] == '<='
               and isinstance(form[1], tuple) and form[1][0] == 'legal']
    slots, _ = discover_subject_slots(actions)
    # Rotated left by one, the piece is now the LAST argument of each
    # form of `move`.
    assert slots['move'] == {4: frozenset({4}), 5: frozenset({5})}


def test_an_ambiguous_slot_is_no_slot():
    """Two unrelated positions each offering two constants: which is the
    subject cannot be read off the description, so none is claimed."""
    actions = [('play', 'red', 'low'), ('play', 'blue', 'high')]
    slots, subjects = discover_subject_slots(actions)
    assert slots == {} and subjects == set()


def test_mirror_image_effects_are_treated_alike():
    """Muddy children's update for Ann reads `does(random, muddy(1, B))`
    and for Bob `does(random, muddy(A, 1))`. They are mirror images, and
    the first-argument rule called only Bob's GENERIC -- because of where
    the 1 was written. `muddy` has no subject, and neither names a
    particular anything less than the other."""
    nodes = load(os.path.join(GAME_DIR, 'muddychildren.gdl'))
    updates = [n for n in nodes if n.head_predicate == 'has'
               and 'muddy' in repr(n.raw)]
    assert len(updates) == 2
    assert updates[0].generic_effect == updates[1].generic_effect


# ---- equivalent encodings, same rules ------------------------------------

@pytest.mark.parametrize('path', SMALL + [ROYAL],
                         ids=lambda p: os.path.basename(p))
def test_rotating_action_arguments_changes_nothing(path):
    result = compare(path, rotate_action_arguments)
    assert result['same'], result


@pytest.mark.parametrize('path', SMALL + [ROYAL],
                         ids=lambda p: os.path.basename(p))
def test_renaming_every_symbol_changes_nothing(path):
    result = compare(path, lambda forms: rename_symbols(forms, 'prefix'))
    assert result['same'], result


@pytest.mark.parametrize('path', SMALL + [ROYAL],
                         ids=lambda p: os.path.basename(p))
def test_opaque_renaming_changes_nothing(path):
    """Every name replaced by a code. Before #320 this failed on Royal
    Chess: the five `_except` variants were found by their names."""
    result = compare(path, rename_symbols)
    assert result['same'], result


def test_opaque_renaming_keeps_every_alias():
    """The aliases found are the same ones, under the new names."""
    from lgref.identify.clauses import detect_predicate_aliases

    forms = forms_of(ROYAL)
    plain = detect_predicate_aliases(forms)
    opaque = detect_predicate_aliases(rename_symbols(forms))
    assert len(plain) == 5
    assert len(opaque) == len(plain)
