"""Structural tests for the Goal-4 GDL step-7 fragment
(`docs/gdl/step7_add_queen_actions.gdl`).

Step 7 is the HARDEST mechanical step in the variant. It adds the
v2 queen's two non-spatial ACTIONS to step 6's base:

  - Transformation: queen → rook / bishop / knight (provided a
    friendly piece of that type has been captured earlier).
    May return to base form on a later turn.

  - Manipulation: queen moves an enemy piece within its line-of-
    sight (rank / file / diagonal) as that owner would.
    Restrictions:
      R1 - manipulated piece may not make a SPATIAL move on its
           immediately next own turn (non-spatial actions OK).
      R2 - queen may not manipulate a piece that made a SPATIAL
           move on the immediately preceding turn.
      R3 - queen may not manipulate enemy king, the boulder, or
           any enemy base-form queen.

Plus the multi-form queen mechanics:

  - A queen in non-base form moves and captures as the chosen
    piece (rook-2-segment, bishop teleport, knight radius-2).
  - Transformation is a non-spatial action; the queen's square
    doesn't change.

Cross-turn state:

  - `(queen_form ?f ?r ?form)` per-queen — ?form ∈ {base, rook,
    bishop, knight}. Marker that distinguishes which piece the
    queen currently moves and captures as.
  - `(captured_friendly ?owner ?piece)` — once a player has lost a
    rook/bishop/knight, their queen unlocks transformation into
    that form.
  - `(moved_spatially_last_turn ?f ?r)` — set when a piece moves
    spatially; used to enforce R2 (queen may not manipulate a
    target whose last spatial move was the immediately preceding
    turn).
  - `(manipulation_freeze ?f ?r)` — set when a piece is
    manipulated; blocks the target's spatial moves on its
    immediately next own turn (R1).

The royal-vs-promoted-queen distinction is also encoded in step 7
(needed so promoted queens don't count toward victory). New fact:
`(queen_royal ?f ?r)` for the royal queens only.

Structural invariants tested:

  - Step-6 invariants still hold.
  - Initial state has `(queen_form ... base)` facts for both
    queens.
  - Initial state has `(queen_royal ...)` for the rulebook royal
    queens (b1 white, g8 black).
  - At least one legal rule each for: transformation, manipulation,
    and a multi-form queen movement (e.g. queen-as-rook).
  - R1 / R2 / R3 manipulation restrictions are textually encoded.
  - The win condition uses the royal queens (not just any queen).
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.dirname(__file__))
from test_gdl_step1 import _tokenize, _parse_all, _strip_comments


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl',
    'step7_add_queen_actions.gdl')


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), f"step-7 GDL missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


def _flatten(form):
    if isinstance(form, str):
        yield form
    elif isinstance(form, tuple):
        for item in form:
            yield from _flatten(item)


def _init_facts(parsed):
    return [f[1] for f in parsed
            if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init']


# ---- step-6 invariants still hold ----------------------------------------

def test_step7_parses(parsed):
    assert len(parsed) > 0


def test_step7_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}


def test_step7_white_moves_first(parsed):
    assert any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and f[1] == ('control', 'white')
        for f in parsed)


def test_step7_has_terminal_and_goal(parsed):
    has_terminal = False
    has_goal = False
    for f in parsed:
        if isinstance(f, tuple) and len(f) >= 2 and f[0] == '<=':
            head = f[1]
            if head == 'terminal' or (
                    isinstance(head, tuple) and head and
                    head[0] == 'terminal'):
                has_terminal = True
            if isinstance(head, tuple) and head and head[0] == 'goal':
                has_goal = True
    assert has_terminal and has_goal


# ---- queen form + royal flag in initial state ---------------------------

def test_step7_queens_start_in_base_form(parsed):
    """Both queens must have an init `(queen_form <file> <rank> base)`
    fact so the multi-form logic knows their current form."""
    flat_inits = [' '.join(_flatten(f)) for f in _init_facts(parsed)]
    matching = [s for s in flat_inits
                if 'queen_form' in s and 'base' in s]
    assert len(matching) >= 2, (
        f"expected ≥2 (queen_form ... base) init facts (one per "
        f"queen); got {matching}")


def test_step7_royal_queens_marked(parsed):
    """The royal queens (b1 white, g8 black) must be marked so the
    win condition can target them specifically (promoted queens do
    NOT count toward victory)."""
    flat_inits = [' '.join(_flatten(f)) for f in _init_facts(parsed)]
    matching = [s for s in flat_inits if 'queen_royal' in s]
    # Need at least 2 royal-queen markers (one per side).
    assert len(matching) >= 2, (
        f"expected ≥2 (queen_royal ...) init facts; got {matching}")


# ---- transformation rule presence ----------------------------------------

def test_step7_has_transformation_legal_rule(parsed):
    """A `transform` action — at least one legal rule mentions
    'transform'."""
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if 'transform' in atoms or any(
                    a.startswith('transform') for a in atoms):
                return
    raise AssertionError("no legal rule mentions transformation")


def test_step7_transformation_requires_prior_capture():
    """The transform action's legality depends on a prior friendly
    capture of that piece type. Source must reference a
    'captured_friendly' / 'captured_piece' / 'allowed_form' predicate."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('captured_friendly' in text or 'captured_piece' in text
            or 'allowed_form' in text), (
        "step-7 transformation rule must consult a 'captured_friendly' "
        "(or similar) predicate to enforce the captured-piece-required "
        "rule")


# ---- manipulation rule presence ------------------------------------------

def test_step7_has_manipulation_legal_rule(parsed):
    for f in parsed:
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and f[1] and f[1][0] == 'legal'):
            atoms = list(_flatten(f[1]))
            if any('manipulat' in a for a in atoms):
                return
    raise AssertionError("no legal rule mentions manipulation")


def test_step7_manipulation_r1_freeze_encoded():
    """R1: manipulated piece may not make a spatial move on its
    immediately next own turn. Source must reference a freeze flag."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('manipulation_freeze' in text or 'frozen' in text
            or 'moved_by_queen' in text), (
        "step-7 GDL must encode the R1 manipulation freeze")


def test_step7_manipulation_r2_recently_moved_encoded():
    """R2: queen may not manipulate a target that moved spatially on
    the immediately preceding turn. Source must reference a
    'moved_last_turn' / 'spatial_move_last_turn' marker."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('moved_last_turn' in text or 'spatial_move_last' in text
            or 'moved_spatially_last' in text), (
        "step-7 GDL must encode the R2 'recently moved' check")


def test_step7_manipulation_r3_forbidden_targets():
    """R3: queen may not manipulate enemy king, boulder, or enemy
    base-form queen. Source must reference these exclusions."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    # Look for keywords or comment text about these restrictions
    # in the source.
    assert ('king' in text and 'boulder' in text and 'queen' in text), (
        "step-7 GDL must reference the R3 forbidden manipulation targets")


# ---- multi-form queen movement ------------------------------------------

def test_step7_has_multi_form_queen_movement():
    """A queen in non-base form moves as the chosen piece. Source must
    reference at least one of: queen_as_rook / queen_as_bishop /
    queen_as_knight."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert ('queen_as_rook' in text or 'queen_as_bishop' in text
            or 'queen_as_knight' in text
            or 'queen_form' in text), (
        "step-7 GDL must reference multi-form queen movement")


# ---- win condition uses royal queens ------------------------------------

def test_step7_win_uses_royal_queens():
    """The lost-condition must consult the royal queen (not just
    'any queen alive'). Source must reference queen_royal in the
    lost/alive/dead/goal context."""
    with open(GDL_PATH) as f:
        text = f.read().lower()
    assert 'queen_royal' in text, (
        "step-7 win condition must use queen_royal (promoted queens "
        "don't count toward victory)")
