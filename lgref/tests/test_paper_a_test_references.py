"""The Paper A TEST-set references (#373): sheets, kinds, rules in plain
words, reference variants and probes.

What is pinned here, and why:

  - every test game has a reference sheet that lists exactly its
    statements, says it is Claude's and NOT a human annotation, and
    records the conventions it follows;
  - the conventions hold: geometry and arithmetic (the `language` list
    of kinds.yaml) are unassigned, and each piece type's starting
    placement is in that piece's rule group;
  - reference variants exist for exactly the perfect-information test
    games, every probe discriminates, and every variant is a
    well-formed game; the no-effect change really changes nothing on
    any reachable state;
  - the plain-words rules exist for every test game and do not copy the
    description's design notes.
"""

import os

import pytest
import yaml

import lgref  # noqa: F401  (puts src/ on the path)
from lgref.bench import annotation, catalog, probes, setup, wellformed
from lgref.bench.simulators import SIMULATORS
from lgref.identify.clauses import load

TEST = sorted(catalog.in_split('test'))
#: Imperfect-information games: no reference variants (as Monty Hall on
#: the dev set). Everything else in the test set has them.
HIDDEN = {'muddychildren', 'kuhnpoker', 'leducholdem', 'russiancards',
          'cherylsbirthday'}
VARIANTS = sorted(set(TEST) - HIDDEN)


def _text(game):
    with open(catalog.game_path(game)) as handle:
        return handle.read()


@pytest.mark.parametrize('game', TEST)
def test_sheet_matches_description_and_is_provisional(game):
    sheet = annotation.reference(game)
    assert annotation.check_sheet(sheet) == []
    assert 'Claude' in sheet.author and 'NOT a human' in sheet.author
    assert 'geometry and arithmetic are language' in \
        sheet.meta['conventions']
    assert sheet.meta['issue'] == '#373'


@pytest.mark.parametrize('game', TEST)
def test_language_statements_are_unassigned(game):
    with open(setup.KINDS_PATH) as handle:
        table = yaml.safe_load(handle)['game_kinds'][game]
    language = set(table['language'])
    assert not language & set(table['ambiguous'])
    sheet = annotation.reference(game)
    for row, node in zip(sheet.rows, load(catalog.game_path(game))):
        if node.head_predicate in language and node.head_kind in (
                'fact', 'derived'):
            assert row['rules'] == [], (game, row['statement'])
        if node.head_predicate in table['ambiguous']:
            assert row['rules'], (game, row['statement'])


@pytest.mark.parametrize('game,piece,group', [
    ('skirmish', ',guard,', 'guard_movement'),
    ('skirmish', ',lancer,', 'lancer_movement'),
    ('checkers_4x4', ',man,', 'man_movement'),
    ('foxgeese_mini', 'init(goose(', 'geese_movement'),
    ('foxgeese_mini', 'init(fox(', 'fox_movement'),
])
def test_piece_placement_is_in_the_piece_group(game, piece, group):
    rows = [r for r in annotation.reference(game).rows
            if r['statement'].startswith('init(') and piece in
            r['statement']]
    assert rows
    for row in rows:
        assert row['rules'] == [group], row


def test_every_test_game_has_plain_rules():
    for game in TEST:
        assert game in annotation.RULES, game
        assert 'WHAT IT ADDS' not in annotation.RULES[game]


def test_packets_for_test_games_are_current():
    for game in TEST:
        path = os.path.join(annotation.PACKET_DIR, game, 'sheet.csv')
        sheet = annotation.read_sheet(path, game)
        assert all(not r['rules'] for r in sheet.rows)
        assert [r['statement'] for r in sheet.rows] == [
            t for _i, t in annotation.statements(game)]


def test_variants_exist_for_the_perfect_information_test_games():
    have = set(probes.games_with_variants()) & set(TEST)
    assert have == set(VARIANTS)


@pytest.mark.parametrize('game', VARIANTS)
def test_probes_discriminate(game):
    assert probes.check_references(game) == []


@pytest.mark.parametrize('game', VARIANTS)
def test_reference_variants_are_well_formed(game):
    base = _text(game)
    meta, changes = probes.load_variants(game)
    assert 'Claude' in meta['author']
    for change in changes:
        text = probes.variant_text(base, change)
        states, _mode = wellformed.walk(text, games=40, seed=3)
        assert wellformed.check(text, states) == [], change


def test_the_no_effect_change_changes_nothing():
    """The redundant rule's removal agrees with the unmodified game's
    simulator on every reachable state."""
    changes = {c.id: c for c in probes.load_variants('synth_redundant')[1]}
    change = changes['no_lit_step']
    assert change.kind == 'no_effect'
    text = probes.variant_text(_text('synth_redundant'), change)
    states, mode = wellformed.walk(text, exhaustive=True)
    assert mode == 'exhaustive'
    assert wellformed.check(text, states,
                            SIMULATORS['synth_redundant']()) == []


def test_lancer_removal_also_removes_its_placement():
    """The placement convention, applied to a reference ablation."""
    changes = {c.id: c for c in probes.load_variants('skirmish')[1]}
    text = probes.variant_text(_text('skirmish'), changes['no_lancer'])
    game = wellformed.open_game(text)
    assert not any(f[0] == 'at' and f[2] == 'lancer' for f in game.state)
    assert any(f[0] == 'at' and f[2] == 'guard' for f in game.state)
