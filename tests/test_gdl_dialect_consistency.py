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


# ---------------------------------------------------------------------------
# Round-trip fidelity. The text comparison above could not catch this.
# ---------------------------------------------------------------------------

def test_zero_arity_predicates_survive_the_round_trip():
    """`(a_capture_turn)` must not come back as the string.

    Prefix parses `(a_capture_turn)` to the one-tuple
    `('a_capture_turn',)`. Infix writes it bare, and reading it back as
    a plain string loses the distinction -- which is not cosmetic,
    because `board_to_gdl_facts` emits 0-arity fluents as one-tuples.
    A description parsed with bare strings never matched the facts the
    cross-validation harness fed it: the boulder's four first-moves
    vanished from the GGP's legal set and agreement fell from 100% to
    56%.
    """
    forms = parse_infix('a_capture_turn :- does(M, move(P,A,B,C,D))\n'
                        'next(boulder_first_move) :- true(boulder_first_move)\n')
    rule = forms[0]
    assert rule[1] == ('a_capture_turn',), rule[1]
    persistence = forms[1]
    assert persistence[1] == ('next', ('boulder_first_move',)), persistence
    assert persistence[2] == ('true', ('boulder_first_move',)), persistence


def test_a_bare_name_in_argument_position_stays_a_constant():
    """The wrapping must not run away with move terms.

    `legal(P, noop)` has a constant move, not a 0-arity predicate.
    """
    forms = parse_infix('legal(P,noop) :- true(control(P))\n')
    assert forms[0][1] == ('legal', '?p', 'noop'), forms[0][1]


# NO midgame dialect comparison lives here, deliberately.
#
# I wrote two and mutation-testing showed both were vacuous: driven from
# the opening position they cannot reach the rules that differed, because
# the boulder cannot move on White's first turn. A test that passes on a
# known-broken build is worse than no test, so rather than leave a
# comforting one here:
#
#   tests/test_ggp_cross_validation_midgame.py is the behavioural guard.
#
# It plays seeded random plies and compares the engine's legal set with
# the GGP's at every one, ratcheted at 100% agreement. It is what caught
# the 0-arity round-trip loss -- reporting 56.0% -- and it is verified to
# fail when that fix is reverted.
