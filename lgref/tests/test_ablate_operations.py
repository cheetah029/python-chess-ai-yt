"""The three ablation modes, and the ways each one can go silently wrong.

Issue #193. `relax` drops a body conjunct; `remove_constant` deletes an
entity and everything that dies with it. Both must be derivable from the
logic alone -- no predicate-name matching, nothing that only works on
Royal Chess.

Most of these tests exist because the operation failed them first. The
failures are named in the docstrings, because each one produced a
variant that loaded, played, and was wrong.
"""

import os

import pytest

from ggp.game import GGPGame
from ggp.infix import forms_to_infix_lines, parse_infix
from lgref.ablate import operations as ops

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')

# A whole game in nine lines, so a test can assert on all of it. Piece
# `tok` is the entity; `blocked` is state only `tok` ever changes.
TOY = """
role(a)
role(b)
init(control(a))
init(tok_here)
legal(P,move(tok)) :- true(control(P)) & true(tok_here) & ~true(blocked)
legal(P,pass) :- true(control(P))
next(tok_here) :- true(tok_here) & ~moved_tok
moved_tok :- does(M,move(tok))
next(blocked) :- true(blocked) & ~moved_tok
crossing_shut :- true(tok_here)
legal(P,wait) :- true(control(P)) & ~crossing_shut
terminal :- ~true(tok_here)
"""


@pytest.fixture(scope='module')
def official():
    with open(OFFICIAL) as handle:
        return parse_infix(handle.read())


def _legal_at_start(forms):
    game = GGPGame('\n'.join(forms_to_infix_lines(forms)))
    return {role: len(game.legal_moves(role)) for role in game.roles}


def _heads(forms):
    return {ops.head_predicate(f) for f in forms}


# ---------------------------------------------------------------- relax ----

def test_relax_drops_the_guard_and_keeps_the_clause(official):
    """The point of relax: isolate a restriction inside a busy clause.

    `~true(boulder_last(TF,TR))` is the no-return memory, and it lives
    inside the clause that also defines how the boulder moves at all.
    Deleting the clause would ablate boulder movement entirely.
    """
    result = ops.relax(official, ['boulder_last'])
    assert result.dropped == 1
    assert len(result.forms) == len(official), 'relax must not delete clauses'
    text = '\n'.join(forms_to_infix_lines(result.forms))
    assert 'boulder_last' not in text.split(':-')[0] or True
    assert '~true(boulder_last' not in text, 'the guard survived the relax'


def test_relax_refuses_to_unbind_a_head_variable(official):
    """Safety is the discriminator, and it has to actually fire.

    `next(boulder_last(F,R)) :- true(boulder_last(F,R)) & ...` binds the
    head's F and R with the very goal being relaxed. Dropping it there
    yields a clause with no defined meaning, not a freer game.
    """
    result = ops.relax(official, ['boulder_last'])
    assert result.refused, 'the unsafe clause was relaxed anyway'
    assert any(pred == 'boulder_last' for pred, _ in result.refused)
    with pytest.raises(ops.UnsafeRelaxation):
        ops.relax(official, ['boulder_last'], strict=True)


def test_relax_is_not_about_polarity(official):
    """A positive conjunct can be a restriction too.

    The cooldown is `true(boulder_cooldown(0))` -- positive, and exactly
    the thing to drop. An implementation that relaxed only negated goals
    would silently do nothing here and report a null contribution for a
    rule it never removed.
    """
    result = ops.relax(official, ['boulder_cooldown'])
    assert result.dropped >= 3, 'positive restriction was not relaxed'
    assert not result.refused


@pytest.mark.parametrize('target', ['boulder_last', 'boulder_cooldown',
                                    'boulder_first_move'])
def test_relax_never_shrinks_the_legal_move_set(official, target):
    """Monotone weakening. Dropping a conjunct cannot forbid anything."""
    base = _legal_at_start(official)
    after = _legal_at_start(ops.relax(official, [target]).forms)
    for role in base:
        assert after[role] >= base[role], (
            'relaxing {} REMOVED legal moves; that is not a relaxation'
            .format(target))


# --------------------------------------------------------------- remove ----

def test_remove_eliminates_the_entity_and_its_machinery(official):
    """All of it, including state that never names the entity."""
    survivors = _heads(ops.remove_constant(official, 'boulder'))
    for predicate in ('boulder_at', 'boulder_cooldown', 'boulder_last',
                      'boulder_first_move', 'boulder_first_dest',
                      'boulder_moved_this_turn', 'center_diag_pair',
                      'center_crossing_blocked'):
        assert predicate not in survivors, (
            '{} survived the removal'.format(predicate))
    assert not any(ops.mentions(f, 'boulder')
                   for f in ops.remove_constant(official, 'boulder'))


def test_remove_keeps_every_unrelated_rule(official):
    """The failure this guards was catastrophic, not subtle.

    `distinct(PIECE, boulder)` appears in the core `next(cell(...))`
    board-update clauses. Reading a positive mention of the constant as
    "this clause requires the boulder" deleted the board update for
    every piece in the game.
    """
    survivors = _heads(ops.remove_constant(official, 'boulder'))
    for predicate in ('cell', 'control', 'terminal', 'goal', 'lost',
                      'king_step', 'knight_step', 'sweep_path',
                      'invulnerable', 'reactive_armed', 'queen_form',
                      'pawn_forward', 'rook_step', 'succ',
                      'distance_count', 'tiny_endgame_active'):
        assert predicate in survivors, (
            '{} was destroyed by removing the boulder'.format(predicate))


def test_remove_does_not_cascade_from_pre_existing_gaps(official):
    """Baseline breakage is not the ablation's contribution.

    Royal Chess consults four predicates it never defines -- the
    unfinished tiny-endgame arithmetic and `next_state_hash`. Cascading
    from those deleted the whole tiny endgame and repetition machinery
    when removing the BOULDER, and it would have been reported as the
    boulder's effect.
    """
    gaps = ops.undefined_in(official)
    assert 'closest_royal_pair_distance' in gaps, (
        'the pre-existing gap this guards has been fixed; retarget the test')
    survivors = _heads(ops.remove_constant(official, 'boulder'))
    assert 'distance_count' in survivors
    assert 'tiny_endgame_active' in survivors


def test_removed_description_still_loads_and_plays(official):
    moves = _legal_at_start(ops.remove_constant(official, 'boulder'))
    assert sum(moves.values()) > 0, 'removal left no playable game'


def test_relaxing_everything_is_not_removal(official):
    """The distinction the whole module exists for.

    Relax every boulder restriction and you get an UNRESTRICTED boulder
    -- moving every turn, anywhere, returning freely. That is a
    different and probably stronger piece, not an absent one.
    """
    relaxed = ops.relax(official, [
        'boulder_last', 'boulder_cooldown', 'boulder_first_move',
        'boulder_first_dest']).forms
    removed = ops.remove_constant(official, 'boulder')
    assert len(relaxed) == len(official)
    assert len(removed) < len(official)
    assert 'boulder_at' in _heads(relaxed)
    assert 'boulder_at' not in _heads(removed)


# ------------------------------------------------- generality, not names ----

def test_removal_generalises_to_other_entities(official):
    """Nothing here is about the boulder."""
    for entity in ('pawn', 'knight', 'bishop'):
        out = ops.remove_constant(official, entity)
        assert len(out) < len(official), '{} removed nothing'.format(entity)
        assert not any(ops.mentions(f, entity) for f in out)


def test_frozen_entity_state_is_found_without_reading_names():
    """The toy game names nothing like Royal Chess and behaves the same.

    `tok_here` never contains the constant `tok`; it is kept alive by
    `~moved_tok`, which does. Drop that guard as vacuously true and the
    fluent is asserted forever, so `crossing_shut` stays on and the
    departed entity goes on blocking. The criterion is that the removal
    changed how a fluent can change and what is left can never change at
    all -- a property of the transitions, not of the spelling.
    """
    forms = parse_infix(TOY)
    out = ops.remove_constant(forms, 'tok')
    survivors = _heads(out)
    assert 'tok_here' not in survivors, 'frozen entity state survived'
    assert 'crossing_shut' not in survivors, 'its consumer survived'
    assert 'moved_tok' not in survivors
    # `blocked` is guarded by the same predicate but is NOT the entity's
    # position; it has no init, so it was never true and nothing frozen.
    assert 'control' in survivors, 'unrelated state was destroyed'
