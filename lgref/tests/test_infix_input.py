"""LGREF takes infix GDL in and writes infix GDL out.

Issue #190. Infix HRF is this project's official dialect. Two things
have to hold for that to be true in practice rather than on paper:

1. `load` accepts infix and REFUSES prefix. Refusal matters more than it
   looks. The two dialects do not have the same statement count -- a
   prefix `(or A B)` body becomes one rule per branch in infix -- so a
   silent prefix fallback would change every clause count in the report
   while appearing to work.

2. Ablated descriptions are written back in infix, so a variant can be
   read by a human and re-fed to the framework in the same notation as
   the original.
"""

import os
import tempfile

import pytest

from lgref.identify.clauses import load
from lgref.identify.intervention import ablate_forms, _write_gdl

REPO = os.path.join(os.path.dirname(__file__), '..', '..')
OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')
LEGACY_PREFIX = os.path.join(REPO, 'docs', 'gdl', 'integrated_prefix.gdl')
TESTGAMES = os.path.join(os.path.dirname(__file__), '..',
                         'identify', 'testgames')

INFIX_NIM = """\
role(first)
role(second)
legal(P,take(1)) :- true(control(P)) & true(pile(N)) & positive(N)
next(pile(M)) :- does(P,take(1)) & true(pile(N)) & succ(M,N)
terminal :- true(pile(0))
"""


def test_load_accepts_infix():
    with tempfile.NamedTemporaryFile('w', suffix='.gdl', delete=False) as fh:
        fh.write(INFIX_NIM)
        path = fh.name
    nodes = load(path)
    os.unlink(path)
    assert len(nodes) == 5
    heads = {n.head_predicate for n in nodes}
    assert {'role', 'legal', 'pile', 'terminal'} <= heads


def test_load_refuses_prefix_by_name():
    """A prefix file must fail loudly, naming the converter."""
    with pytest.raises(ValueError) as excinfo:
        load(LEGACY_PREFIX)
    message = str(excinfo.value)
    assert 'prefix' in message
    assert 'build_integrated.py' in message, (
        'the refusal must tell the caller how to convert')


def test_the_validation_games_are_infix():
    for game in ('tictactoe', 'nim'):
        path = os.path.join(TESTGAMES, '{}.gdl'.format(game))
        with open(path) as handle:
            text = handle.read()
        assert '(<=' not in text, '{} is still prefix'.format(game)
        assert load(path), '{} did not parse as infix'.format(game)


def test_the_official_description_loads_as_infix():
    nodes = load(OFFICIAL)
    assert len(nodes) > 400
    # The or-expansion means infix carries MORE statements than prefix.
    # Pinned so a silent dialect regression cannot pass unnoticed.
    assert len(nodes) == 522


def test_ablated_descriptions_are_written_in_infix():
    """An ablated variant must round-trip through the official dialect."""
    nodes = load(os.path.join(TESTGAMES, 'nim.gdl'))
    victim = next(n.node_id for n in nodes if n.head_predicate == 'succ')
    forms = ablate_forms(nodes, {victim})
    path = _write_gdl(forms)
    try:
        with open(path) as handle:
            text = handle.read()
        assert '(<=' not in text, 'ablated output is prefix, not infix'
        assert ':-' in text, 'no infix rules in the ablated output'
        # And it must be readable back by the framework itself.
        reloaded = load(path)
        assert len(reloaded) == len(nodes) - 1
    finally:
        os.unlink(path)
