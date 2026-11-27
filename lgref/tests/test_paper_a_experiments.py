"""The Paper A runners and tables, end to end on Nim (the fastest game).

The numbers themselves are the experiments' business; these tests pin
the plumbing: what a row holds, which statements a reference edit
touches, what counts as reproducing a change, and that the tables say
"n/a" where nothing was measured.
"""

import json

import pytest

import lgref  # noqa: F401
from lgref.bench import experiments as X
from lgref.bench import probes, report
from lgref.bench.catalog import game_path


def _text(game):
    with open(game_path(game)) as handle:
        return handle.read()


def test_edited_statements_names_the_edit():
    base = _text('nim')
    changes = {c.id: c for c in probes.load_variants('nim')[1]}
    touched = X.edited_statements(
        base, probes.variant_text(base, changes['take_one_only']))
    assert touched == {3}       # legal(P,take(2)) :- ...


def test_edited_statements_of_a_relaxation():
    base = _text('corridor')
    changes = {c.id: c for c in probes.load_variants('corridor')[1]}
    touched = X.edited_statements(
        base, probes.variant_text(base, changes['no_boundary']))
    assert touched == {10, 11}  # the two step permissions


def test_grouping_rows_hold_every_metric():
    rows = X.grouping_rows(['nim'], ['lgref', 'singletons'], seeds=(0, 1))
    assert [r['method'] for r in rows] == ['lgref', 'lgref', 'singletons']
    for key in ('f1', 'precision', 'recall', 'coverage', 'ari',
                'shared_recovery', 'n_scored'):
        assert key in rows[0]
    assert rows[0]['shared_recovery'] is None   # nim shares nothing


def test_random_baseline_is_matched_at_the_same_seed():
    from lgref.bench import methods as M
    from lgref.identify.clauses import load

    nodes = load(game_path('corridor'))
    got = X.grouping_for('random_matched', nodes, 4)
    want = M.random_matched(nodes, seed=4,
                            reference=M.lgref(nodes, seed=4))
    assert got.groups == want.groups


@pytest.fixture(scope='module')
def nim_record():
    rows, setup = X.intervention_rows(['nim'], ['lgref', 'singletons'])
    return {'rows': rows, 'setup': setup, 'games': ['nim']}


def test_intervention_rows(nim_record):
    rows = nim_record['rows']
    assert {r['procedure'] for r in rows} == {'ownership', 'delete_group'}
    for row in rows:
        assert set(row['changes_by_ref']) == {'take_one_only',
                                              'last_taker_wins'}
        if row['empty']:
            assert not row['valid'] and row['invalid_reason'] == 'empty'


def test_deleting_the_take_two_permission_reproduces_take_one_only(
        nim_record):
    """The singleton group holding exactly `legal(P,take(2))` is the
    reference edit itself, so it must reproduce the change with F1 1."""
    row = next(r for r in nim_record['rows']
               if r['method'] == 'singletons'
               and r['procedure'] == 'delete_group' and r['touched'] == [3])
    agree = row['changes_by_ref']['take_one_only']
    assert row['valid'] and agree['all_probes'] and agree['f1'] == 1.0
    summary = report.intervention_summary(nim_record, 'delete_group')
    assert summary[('nim', 'singletons')]['by_change'][
        'take_one_only']['reproduced'] >= 1


def test_tables_render_and_say_na(nim_record):
    text = report.intervention_table(nim_record)
    assert 'lgref' in text and 'nim:take_one_only' in text
    rows = X.grouping_rows(['nim'], ['lgref'], seeds=(0,))
    table = report.grouping_table(rows, 'shared_recovery')
    assert 'n/a' in table


def test_a_record_round_trips_through_json(nim_record, tmp_path):
    path = tmp_path / 'r.json'
    path.write_text(json.dumps(nim_record, default=list))
    again = json.loads(path.read_text())
    assert report.intervention_table(again) == report.intervention_table(
        nim_record)
