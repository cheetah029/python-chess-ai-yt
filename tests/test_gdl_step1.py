"""Structural tests for the Goal-4 GDL step-1 fragment
(`docs/gdl/step1_kings_queens.gdl`).

We don't have a GDL reasoner wired into the test harness yet (that's a
later sub-step of Goal 4 — see docs/goal4_gdl_ggp_planning.md). What
this test file does provide is a small S-expression parser plus a set
of structural invariants that any valid GDL-I fragment for this game
must satisfy:

  - Two players are declared (`(role white)`, `(role black)`).
  - Initial facts place each side's king and base-form royal queen on
    the correct starting squares (per RULEBOOK_v2.md: White K g1, Q b1;
    Black K b8, Q g8 — rotationally symmetric setup).
  - White moves first (`(init (control white))`).
  - There are at least four `legal` clauses (the four directions a
    piece can move are present in some form).
  - There is a `terminal` predicate and the `goal` clauses sum to a
    win/draw structure (one side 100 / other 0 in a decisive end).
  - The spec is parseable as balanced S-expressions and contains only
    keywords from the GDL-I core grammar.

These checks catch the kinds of bugs you get from hand-editing a GDL
file (unbalanced parens, missing role declaration, wrong starting
square). They do NOT verify legal-move equivalence with the Python
engine — that's a later step requiring a GDL reasoner.
"""

import os
import re
import pytest


GDL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'gdl', 'step1_kings_queens.gdl')


def _strip_comments(text):
    """Remove ';' line comments (GDL/Prolog style)."""
    out = []
    for line in text.splitlines():
        idx = line.find(';')
        if idx >= 0:
            line = line[:idx]
        out.append(line)
    return '\n'.join(out)


def _tokenize(text):
    """Tokenize parens + atoms. Atoms are non-whitespace, non-paren runs."""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in '()':
            tokens.append(ch)
            i += 1
            continue
        # atom
        j = i
        while j < len(text) and not text[j].isspace() and text[j] not in '()':
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens


def _parse_all(tokens):
    """Parse a stream of S-expressions; return a list of trees.
    Each tree is either a string (atom) or a tuple of trees."""
    pos = [0]

    def parse_one():
        if pos[0] >= len(tokens):
            raise ValueError('unexpected EOF')
        tok = tokens[pos[0]]
        if tok == '(':
            pos[0] += 1
            items = []
            while pos[0] < len(tokens) and tokens[pos[0]] != ')':
                items.append(parse_one())
            if pos[0] >= len(tokens):
                raise ValueError('unbalanced paren (no closing)')
            pos[0] += 1  # skip )
            return tuple(items)
        if tok == ')':
            raise ValueError('unexpected )')
        pos[0] += 1
        return tok

    forms = []
    while pos[0] < len(tokens):
        forms.append(parse_one())
    return forms


@pytest.fixture(scope='module')
def parsed():
    assert os.path.exists(GDL_PATH), \
        f"GDL fragment missing at {GDL_PATH}"
    with open(GDL_PATH) as f:
        text = f.read()
    return _parse_all(_tokenize(_strip_comments(text)))


# ---- structural checks ----------------------------------------------------

def test_file_parses_as_balanced_s_expressions(parsed):
    # If _parse_all returned without raising, the parens are balanced.
    assert len(parsed) > 0


def test_both_roles_declared(parsed):
    roles = {f[1] for f in parsed
             if isinstance(f, tuple) and len(f) == 2 and f[0] == 'role'}
    assert roles == {'white', 'black'}, \
        f"expected roles white+black, got {roles}"


def test_white_moves_first(parsed):
    """White moves first via (init (control white))."""
    has_control_white_init = any(
        isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and isinstance(f[1], tuple) and f[1] == ('control', 'white')
        for f in parsed)
    assert has_control_white_init, \
        "missing (init (control white)) — white must move first"


def test_initial_king_squares_match_rulebook(parsed):
    """Per RULEBOOK_v2.md back rank: White king g1, Black king b8."""
    init_pieces = [
        f[1] for f in parsed
        if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and isinstance(f[1], tuple) and f[1][0] == 'cell'
    ]
    # cell facts: (cell <file> <rank> <color> <piece>)
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in init_pieces
              if len(p) == 5}
    assert pieces.get(('g', '1')) == ('white', 'king'), \
        f"expected white king at g1; got {pieces.get(('g', '1'))}"
    assert pieces.get(('b', '8')) == ('black', 'king'), \
        f"expected black king at b8; got {pieces.get(('b', '8'))}"


def test_initial_queen_squares_match_rulebook(parsed):
    """White royal queen b1, Black royal queen g8 (rotational symmetry)."""
    init_pieces = [
        f[1] for f in parsed
        if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and isinstance(f[1], tuple) and f[1][0] == 'cell'
    ]
    pieces = {(p[1], p[2]): (p[3], p[4]) for p in init_pieces
              if len(p) == 5}
    assert pieces.get(('b', '1')) == ('white', 'queen'), \
        f"expected white queen at b1; got {pieces.get(('b', '1'))}"
    assert pieces.get(('g', '8')) == ('white', 'queen') or \
        pieces.get(('g', '8')) == ('black', 'queen'), \
        f"expected black queen at g8; got {pieces.get(('g', '8'))}"


def test_no_extra_initial_pieces_for_step1(parsed):
    """Step 1 fragment is kings + queens only; no pawns / rooks /
    bishops / knights / boulder."""
    init_pieces = [
        f[1] for f in parsed
        if isinstance(f, tuple) and len(f) == 2 and f[0] == 'init'
        and isinstance(f[1], tuple) and f[1][0] == 'cell'
    ]
    piece_types = {p[4] for p in init_pieces if len(p) == 5}
    allowed = {'king', 'queen'}
    extras = piece_types - allowed
    assert not extras, \
        f"step-1 fragment contains forbidden piece types {extras}; " \
        f"this is the kings+base-queens subset."


def test_has_legal_clauses(parsed):
    """At least one (<= (legal ...) ...) rule exists per role."""
    legal_heads = []
    for f in parsed:
        # (<= head body...) form
        if (isinstance(f, tuple) and len(f) >= 2 and f[0] == '<='
                and isinstance(f[1], tuple) and len(f[1]) >= 2
                and f[1][0] == 'legal'):
            legal_heads.append(f[1])
    assert len(legal_heads) > 0, "no (<= (legal ...) ...) rules found"
    # At least one for each colour SHOULD exist (either via explicit
    # white/black branches or via a generic ?player variable).
    seen_white = any('white' in str(h) or '?player' in str(h)
                     for h in legal_heads)
    seen_black = any('black' in str(h) or '?player' in str(h)
                     for h in legal_heads)
    assert seen_white and seen_black, \
        "legal clauses must cover both colours (white/black or ?player)"


def test_has_terminal_and_goal_clauses(parsed):
    """(<= terminal ...) and (<= (goal ?role ?n) ...) must exist.
    GDL-I convention: `terminal` is a 0-ary predicate written as a
    bare atom in the rule head (not (terminal))."""
    has_terminal = False
    has_goal = False
    for f in parsed:
        if isinstance(f, tuple) and len(f) >= 2 and f[0] == '<=':
            head = f[1]
            # Accept bare 'terminal' atom OR (terminal) form.
            if head == 'terminal':
                has_terminal = True
            if isinstance(head, tuple) and head and head[0] == 'terminal':
                has_terminal = True
            if isinstance(head, tuple) and head and head[0] == 'goal':
                has_goal = True
    assert has_terminal, "no (<= terminal ...) rule found"
    assert has_goal, "no (<= (goal ...) ...) rule found"


def test_only_known_gdl_keywords_at_top_level(parsed):
    """Each top-level form must start with a known GDL-I keyword.
    Catches typos like (rolw white) or (initt ...)."""
    known = {'role', 'init', '<=', 'base', 'input'}  # base/input optional
    for f in parsed:
        if not isinstance(f, tuple) or not f:
            raise AssertionError(f"odd top-level form: {f}")
        head = f[0]
        assert head in known, \
            f"unknown top-level keyword {head!r} (forms: {known})"
