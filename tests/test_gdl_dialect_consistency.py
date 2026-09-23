"""The official infix GDL and the legacy prefix GDL must stay identical.

Issue #190. `docs/gdl/integrated.gdl` (infix HRF) is the OFFICIAL
description of this game: it is what humans read, what documentation
quotes, and what the LGREF framework takes as input.
`docs/gdl/integrated_prefix.gdl` is an outdated-dialect artifact kept
only because the 11 step fragments are still authored in prefix KIF.

Two generated files describing one game is a drift hazard: edit a step
file, rebuild one artifact and forget the other, and the readable file
silently stops matching the game that actually gets played. This module
is the guard. It checks three things, weakest to strongest:

1. The committed infix file is exactly what the build script produces
   from the committed prefix file. Catches "rebuilt one, not the other".
2. The two parse to the same clause set, once prefix `(or A B)` bodies
   are expanded the way the converter expands them. Catches a converter
   change that alters meaning rather than notation.
3. Both yield the SAME legal moves for both roles at the initial state.
   Catches anything the first two miss, because it asks the actual
   reasoner rather than comparing text.

Statement counts differ BY DESIGN and that is not drift: prefix `(or)`
bodies become one rule per branch, so 488 prefix forms become 522 infix
statements. Check 2 is stated in terms of the expansion for that reason.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ggp.game import GGPGame
from ggp.infix import convert_text, forms_to_infix_lines, parse_infix
from ggp.parser import parse

GDL_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'gdl')
OFFICIAL_INFIX = os.path.join(GDL_DIR, 'integrated.gdl')
LEGACY_PREFIX = os.path.join(GDL_DIR, 'integrated_prefix.gdl')

REBUILD = ('re-run BOTH build scripts:\n'
           '  python3 docs/gdl/build_integrated_prefix.py '
           '> docs/gdl/integrated_prefix.gdl\n'
           '  python3 docs/gdl/build_integrated.py')


def _read(path):
    with open(path) as handle:
        return handle.read()


def _statements(text):
    """Non-comment, non-blank lines of an infix file."""
    return [line for line in (l.strip() for l in text.splitlines())
            if line and not line.startswith('%')]


def test_official_file_is_infix_not_prefix():
    """The unsuffixed name must hold the readable dialect."""
    text = _read(OFFICIAL_INFIX)
    assert '(<=' not in text, (
        'docs/gdl/integrated.gdl contains prefix-KIF rules. The official '
        'dialect is infix HRF; the prefix artifact belongs in '
        'integrated_prefix.gdl (issue #190).')
    assert ':-' in text, 'no infix rules found in the official file'


def test_legacy_file_is_prefix():
    assert '(<=' in _read(LEGACY_PREFIX)


def test_infix_is_the_committed_build_of_the_prefix():
    """Check 1: nobody rebuilt one artifact and forgot the other."""
    committed = _statements(_read(OFFICIAL_INFIX))
    regenerated = _statements(convert_text(_read(LEGACY_PREFIX)))
    assert committed == regenerated, (
        'docs/gdl/integrated.gdl is not the build output of '
        'docs/gdl/integrated_prefix.gdl - they have drifted. ' + REBUILD)


def test_same_clauses_after_or_expansion():
    """Check 2: same meaning, not merely same text."""
    from_prefix = forms_to_infix_lines(parse(_read(LEGACY_PREFIX)))
    from_infix = _statements(_read(OFFICIAL_INFIX))
    assert sorted(from_prefix) == sorted(from_infix)


def test_or_expansion_accounts_for_the_count_difference():
    """The count gap is the `or` expansion and nothing else.

    Pinned so that a future gap has to be explained rather than
    shrugged at as "the dialects just differ".
    """
    prefix_forms = parse(_read(LEGACY_PREFIX))
    infix_forms = parse_infix(_read(OFFICIAL_INFIX))
    expanded = len(forms_to_infix_lines(prefix_forms))
    assert len(infix_forms) == expanded
    assert len(infix_forms) >= len(prefix_forms)


def _legal_at_start(path):
    game = GGPGame.from_file(path)
    return {role: sorted(map(str, game.legal_moves(role)))
            for role in game.roles}


@pytest.mark.slow
def test_both_dialects_give_the_same_legal_moves():
    """Check 3: ask the reasoner, not the text."""
    assert _legal_at_start(OFFICIAL_INFIX) == _legal_at_start(LEGACY_PREFIX)
