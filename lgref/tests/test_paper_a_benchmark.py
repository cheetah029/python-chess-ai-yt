"""The Paper A benchmark (#347): split, pilots, reference variants,
probes and reference sheets.

What is pinned here, and why:

  - the DEV split is exactly the five games the plan names, and no game
    family spans dev and test, so a test game can never share its
    statements with a game the method was developed on;
  - both pilots are infix GDL that load, play, terminate, and agree
    with an independent plain-Python implementation in every visited
    state -- and that comparison FAILS on a mutated description, so it
    is a real check;
  - every reference variant applies, is itself a well-formed game, and
    every probe discriminates: a `changed` probe fails on the unmodified
    game, an `unchanged` probe holds there;
  - every reference sheet lists exactly its game's statements and says
    it was written by Claude, not by a human annotator.
"""

import os

import pytest

import lgref  # noqa: F401  (puts src/ on the path)
from lgref.bench import annotation, catalog, probes, wellformed
from lgref.bench.simulators import SIMULATORS

DEV = {'tictactoe', 'nim', 'corridor', 'breakthrough5', 'othello4',
       'dropthree', 'montyhall'}
#: Dev games with reference variants and probes. Drop-three and Monty
#: Hall joined dev in #358 and are scored on groupings only.
VARIANT_GAMES = {'tictactoe', 'nim', 'corridor', 'breakthrough5',
                 'othello4'}
TEST_SEEN = {'skirmish', 'muddychildren', 'kuhnpoker', 'leducholdem',
             'russiancards', 'cherylsbirthday'}
EXCLUDED = {'breakthrough', 'kriegtictactoe', 'kriegmnk_5_5_4'}
PILOTS = ('breakthrough5', 'othello4')


def _text(game):
    with open(catalog.game_path(game)) as handle:
        return handle.read()


# ---- the split ----------------------------------------------------------

def test_dev_split_is_the_plan():
    assert set(catalog.in_split('dev')) == DEV


def test_two_sets_and_the_exclusions():
    assert catalog.SPLITS == ('dev', 'test', 'excluded')
    assert set(catalog.in_split('excluded')) == EXCLUDED
    assert TEST_SEEN <= set(catalog.in_split('test'))
    assert len(catalog.in_split('test')) == len(TEST_SEEN) + 9


def test_no_family_spans_dev_and_test():
    dev_families = {g.family for g in catalog.GAMES
                    if g.split in ('dev', 'excluded')}
    for game in catalog.GAMES:
        if game.split == 'test':
            assert game.family not in dev_families, game


def test_every_split_is_known():
    assert {g.split for g in catalog.GAMES} <= set(catalog.SPLITS)


def test_every_existing_test_game_is_classified():
    """No game file sits in a games directory without a split."""
    for directory in (catalog.OLD_GAMES, catalog.NEW_GAMES):
        for name in os.listdir(directory):
            if name.endswith('.gdl'):
                assert name[:-4] in catalog.BY_NAME, name


def test_dev_games_exist():
    assert set(catalog.existing('dev')) == DEV


# ---- the pilots ---------------------------------------------------------

@pytest.mark.parametrize('game', PILOTS)
def test_pilot_is_infix(game):
    assert '(<=' not in _text(game)


@pytest.mark.parametrize('game', PILOTS)
def test_pilot_agrees_with_simulator(game):
    text = _text(game)
    states, mode = wellformed.walk(text, games=60, seed=1)
    assert 'random' in mode and len(states) > 300
    assert wellformed.check(text, states, SIMULATORS[game]()) == []


@pytest.mark.parametrize('game,old,new', [
    ('othello4', 'delta(sw,m,m)\n', ''),
    ('breakthrough5', 'beside(4,5)\n', ''),
    ('breakthrough5', ' & empty(X,Y2)', ''),
])
def test_simulator_comparison_fails_on_a_mutant(game, old, new):
    text = _text(game)
    assert text.count(old) == 1
    mutant = text.replace(old, new)
    states, _mode = wellformed.walk(mutant, games=30, seed=0)
    assert wellformed.check(mutant, states, SIMULATORS[game]())


def test_problems_show_nested_terms():
    """#372: a problem in a state holding a nested term is reported,
    not raised as TypeError while formatting it."""
    assert wellformed._show({('drawn', ('h', '1', '2')), ('control', 'a')}) \
        == 'control(a) drawn(h(1,2))'
    text = 'role(a)\nlegal(a,draw(h(1,1))) :- true(go)\ninit(go)\n' \
        'next(drawn(h(1,1))) :- does(a,draw(h(1,1)))\n'
    states, _mode = wellformed.walk(text, exhaustive=True)
    problems = wellformed.check(text, states)
    assert problems == ['non-terminal state, a has no legal move: '
                        'drawn(h(1,1))']


def test_breakthrough_moves_share_one_action():
    """The point of the pilot: the three kinds of move are told apart by
    nothing in the action term or the head predicate."""
    from lgref.identify.clauses import load
    actions = {n.action_type for n in load(catalog.game_path('breakthrough5'))
               if n.head_predicate == 'legal' and n.action_type != 'noop'}
    assert actions == {'move'}


def test_pilot_games_end():
    for game in PILOTS:
        text = _text(game)
        g = wellformed.open_game(text)
        states, _ = wellformed.walk(text, games=40, seed=2)
        terminals = [s for s in states
                     if wellformed.at(g, s).is_terminal()]
        assert terminals, game


# ---- reference variants and probes --------------------------------------

def test_variants_exist_for_the_variant_games():
    # The test set's variants (#373) are pinned in
    # test_paper_a_test_references.py.
    assert set(probes.games_with_variants()) & DEV == VARIANT_GAMES


@pytest.mark.parametrize('game', sorted(VARIANT_GAMES))
def test_probes_discriminate(game):
    assert probes.check_references(game) == []


@pytest.mark.parametrize('game', sorted(VARIANT_GAMES))
def test_reference_variants_are_well_formed(game):
    base = _text(game)
    for change in probes.load_variants(game)[1]:
        text = probes.variant_text(base, change)
        states, _ = wellformed.walk(text, games=40, seed=3)
        assert wellformed.check(text, states) == [], change


def test_the_first_experiment_is_specified():
    """Disable diagonal captures in Breakthrough, with the plan's three
    probes: (a) capture illegal, (b) diagonal move still legal, (c) a
    move onto the far rank still wins."""
    changes = {c.id: c for c in probes.load_variants('breakthrough5')[1]}
    change = changes['no_capture']
    roles = {p['id']: p['role'] for p in change.probes}
    assert roles['a_capture_illegal'] == 'changed'
    assert roles['b_diagonal_move_still_legal'] == 'unchanged'
    assert roles['c_far_rank_still_wins'] == 'unchanged'


def test_edits_must_apply_exactly_once():
    with pytest.raises(ValueError):
        probes.apply_edits('a b a', [{'remove': 'a'}])
    with pytest.raises(ValueError):
        probes.apply_edits('a b', [{'remove': 'c'}])
    assert probes.apply_edits('a b', [{'replace': 'b', 'with': 'c'}]) == 'a c'


def test_a_description_that_does_not_load_fails_every_probe():
    change = probes.load_variants('nim')[1][0]
    results = probes.run_probes('this is not gdl :- & &', change)
    assert results and all(not ok for ok, _r in results.values())


def test_a_changed_probe_that_holds_on_the_base_is_caught(
        tmp_path, monkeypatch):
    """`check_references` must refuse a probe that tests nothing."""
    spec = ('game: nim\nauthor: test\nchanges:\n'
            '  - id: vacuous\n    summary: nothing\n    edits: []\n'
            '    probes:\n      - id: p\n        role: changed\n'
            '        state: control(first) pile(5)\n        expect:\n'
            '          - legal: first take(1)\n')
    (tmp_path / 'nim.yaml').write_text(spec)
    monkeypatch.setattr(probes, 'VARIANT_DIR', str(tmp_path))
    problems = probes.check_references('nim')
    assert any('tests nothing' in p for p in problems)


# ---- reference sheets and the annotation packet -------------------------

@pytest.mark.parametrize('game', sorted(DEV))
def test_reference_sheet_matches_description(game):
    sheet = annotation.reference(game)
    assert annotation.check_sheet(sheet) == []


@pytest.mark.parametrize('game', sorted(DEV))
def test_reference_sheet_is_marked_provisional(game):
    author = annotation.reference(game).author
    assert 'Claude' in author and 'NOT a human' in author


@pytest.mark.parametrize('game', PILOTS)
def test_pilot_sheets_record_sharing(game):
    sheet = annotation.reference(game)
    assert sheet.shared() and sheet.ambiguous()


def test_packet_is_blank_and_hides_the_authors_grouping(tmp_path):
    out = annotation.write_packet('othello4', str(tmp_path))
    blank = annotation.read_sheet(os.path.join(out, 'sheet.csv'))
    assert all(not row['rules'] for row in blank.rows)
    assert [r['index'] for r in blank.rows] == [
        i for i, _t in annotation.statements('othello4')]
    with open(os.path.join(out, 'statements.md')) as handle:
        text = handle.read()
    # The file header's design notes say what is shared; the packet
    # must give the rules of play only.
    assert 'WHAT IT ADDS' not in text and 'closes' in text


def test_instructions_ask_for_independence(tmp_path):
    path = annotation.write_instructions(str(tmp_path))
    with open(path) as handle:
        text = handle.read()
    assert 'independently' in text and 'do not open' in text


def test_packet_in_docs_is_current():
    for game in sorted(DEV):
        path = os.path.join(annotation.PACKET_DIR, game, 'sheet.csv')
        sheet = annotation.read_sheet(path, game)
        assert [r['statement'] for r in sheet.rows] == [
            t for _i, t in annotation.statements(game)]
