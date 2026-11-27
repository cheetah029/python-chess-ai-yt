"""The grouping-version tables (#410) are generated from the saved runs,
and each cell means what the header says.

Small hand-built cases pin the comparison rules; the last tests
regenerate `docs/paper-a/grouping-version-tables.md` from the runs and
check it against the file, and against `docs/lgref-versions.md`.
"""

import os
import re

import pytest

from lgref.bench import version_tables as vt

REPO = os.path.join(os.path.dirname(__file__), '..', '..')
DOC = os.path.join(REPO, 'docs', 'paper-a', 'grouping-version-tables.md')
VERSIONS_DOC = os.path.join(REPO, 'docs', 'lgref-versions.md')

M = vt.MISSING


def _key(row):
    return (row['game'], row['procedure'], row['group'])


# ---- the comparison rules, on hand-built values ----------------------------

def test_smaller_wins_and_equal_ties():
    assert vt.outcome(0, 5) == 1
    assert vt.outcome(5, 0) == -1
    assert vt.outcome(3, 3) == 0


def test_a_missing_ablation_loses_to_any_value_and_ties_with_missing():
    assert vt.outcome(10 ** 9, M) == 1
    assert vt.outcome(M, 0) == -1
    assert vt.outcome(M, M) == 0


def test_wins_ties_losses_over_rules():
    col = [{'a': 0, 'b': 4, 'c': M, 'd': 2}]
    base = [{'a': 3, 'b': 4, 'c': 1, 'd': M}]
    assert vt.wins_ties_losses(col, base, ['a', 'b', 'c', 'd']) == (
        2.0, 1.0, 1.0)
    assert vt.wins_ties_losses(col, base, ['a']) == (1.0, 0.0, 0.0)


def test_against_draws_the_cell_is_the_mean_over_draws():
    col = [{'r': 1, 's': 1}]
    draws = [{'r': 0, 's': 0}, {'r': 2, 's': 2}, {'r': 1, 's': 5}]
    # draw 0: 0 W, 0 T, 2 L; draw 1: 2 W; draw 2: 1 T, 1 W
    assert vt.wins_ties_losses(col, draws, ['r', 's']) == pytest.approx(
        (1.0, 1.0 / 3, 2.0 / 3))


def test_difference_interval():
    mean, low, high = vt.difference_interval([1, 1, 1, 1], [0, 0, 0, 0])
    assert (mean, low, high) == (1.0, 1.0, 1.0)
    mean, low, high = vt.difference_interval([1, 0, 1, 0], [0, 0, 0, 0])
    assert mean == 0.5 and 0.0 <= low <= 0.5 <= high <= 1.0
    assert vt.difference_interval([], [1]) == (None, None, None)
    assert vt.difference_interval([0.75], [0.25]) == (0.5, None, None)
    # deterministic for a fixed seed
    a = vt.difference_interval([0.1, 0.9, 0.4], [0.3, 0.2])
    assert a == vt.difference_interval([0.1, 0.9, 0.4], [0.3, 0.2])


def test_columns_shrink_as_the_baseline_rises():
    v0 = vt.columns_for('V0')
    assert v0[0] == ('V1 (V1.8)', 'lgref')
    assert [m for _l, m in v0][1:] == ([m for m, _ in vt.VARIANTS]
                                       + list(vt.BASELINES))
    assert vt.columns_for('V1') == []


def test_count_metric_values_on_a_hand_built_ablation():
    ab = {'exactness': 7, 'collateral': 2, 'shortfall': 5,
          'rules_broken': ['x', 'y'],
          'exactness_by_kind': {'legal': 3, 'terminal': 1, 'goal': 1,
                                'next': 2}}
    trace = {'legal_differences': 4, 'terminal_differences': 1,
             'goal_differences': 2}
    got = {key: fn(ab, trace) for key, _t, _d, fn in vt.COUNT_METRICS}
    assert got == {'exact': 7, 'legal': 3, 'terminal': 1, 'goal': 1,
                   'next': 2, 'breakage': 1, 'fragility': 2,
                   'shortfall': 5, 'playout': 7}
    # the four kinds add up to exactness
    assert sum(got[k] for k in ('legal', 'terminal', 'goal', 'next')) \
        == got['exact']
    playout = dict((m[0], m[3]) for m in vt.COUNT_METRICS)['playout']
    assert playout(ab, None) is None


# ---- on the saved runs -----------------------------------------------------

@pytest.fixture(scope='module')
def data():
    return {split: vt.load(split=split) for split in vt.SPLITS}


def test_v0_has_thirty_draws_and_draw_0_is_the_published_single_draw(
        data):
    import json
    for split in vt.SPLITS:
        assert data[split]['n_draws'] == 30
        with open(os.path.join(vt.RUNS, 'exp1_{}.json'.format(split))) as h:
            single = [r for r in json.load(h)['rows']
                      if r['method'] == 'random_matched']
        draw0 = data[split]['exp1']['random_matched'][0]

        def strip(rows):
            # Timing differs between runs. So do the last digit of the
            # scatter entropy and how an invalid reason prints a state;
            # neither is scored. Validity itself is compared.
            return sorted(repr({k: v for k, v in sorted(r.items())
                                if k not in ('draw', 'seconds', 'scatter',
                                             'invalid_reason')})
                          for r in rows)
        assert strip(draw0) == strip(single)
        for a, b in zip(sorted(draw0, key=_key), sorted(single, key=_key)):
            for field, x in (a['scatter'] or {}).items():
                assert x == pytest.approx(b['scatter'][field], rel=1e-12)


def test_draw_0_play_outs_equal_the_published_ones(data):
    """The draw-aware trace runner rebuilds each draw's grouping; on draw
    0 it must give the rows the single-draw runner gave."""
    import json
    for split in vt.SPLITS:
        with open(os.path.join(vt.RUNS,
                               'traces_{}.json'.format(split))) as h:
            single = [r for r in json.load(h)['rows']
                      if r['method'] == 'random_matched']
        drawn = [{k: v for k, v in r.items() if k != 'draw'}
                 for r in data[split]['traces'][('random_matched', 0)]]
        assert sorted(map(repr, drawn)) == sorted(map(repr, single))
        draws = {d for m, d in data[split]['traces'] if m == 'random_matched'}
        assert draws == set(range(30))


def test_exact_counts_agree_with_the_published_summary(data):
    """The per-rule values reproduce report.ablation_summary's exact
    counts, so the tables score the ablations the results docs score."""
    from lgref.bench import report
    for split in vt.SPLITS:
        d = data[split]
        for procedure, _label in vt.PROCEDURES:
            for method in ('lgref', 'singletons', 'link_communities'):
                values = vt.rule_values(d, method, procedure, 'exact')[0]
                record = {'rows': d['exp1'][method][0], 'games': d['games'],
                          'setup': d['setup']}
                cell = report.ablation_summary(record, procedure)[method]
                assert sum(v == 0 for v in values.values()) == cell['exact']
                assert sum(v is not M for v in values.values()) \
                    == cell['n_found']


def test_v0_exact_mean_matches_the_draws_summary(data):
    from lgref.bench import report
    for split in vt.SPLITS:
        d = data[split]
        per = vt.rule_values(d, 'random_matched', 'ownership', 'exact')
        counts = [sum(v == 0 for v in cell.values()) for cell in per]
        record = {'rows': [r for rows in d['exp1']['random_matched']
                           for r in rows],
                  'games': d['games'], 'setup': d['setup']}
        assert counts == report.draws_summary(record, 'ownership')[0]


def test_valid_rate_units_match_the_intervention_summary(data):
    from lgref.bench import report
    d = data['test']
    record = {'rows': d['exp1']['lgref'][0], 'games': d['games'],
              'setup': d['setup']}
    summary = report.intervention_summary(record, 'ownership')
    for (game, method), cell in summary.items():
        got = vt.units(d, method, 'valid', 'ownership', game)
        assert (len(got), sum(got)) == (cell['attempted'], cell['valid'])


def test_the_doc_is_what_the_generator_writes():
    with open(DOC) as handle:
        assert handle.read() == vt.build(), (
            'regenerate: python -m lgref.bench.version_tables > '
            'docs/paper-a/grouping-version-tables.md')


def test_columns_are_the_representatives_in_the_numbering():
    with open(VERSIONS_DOC) as handle:
        text = handle.read()
    for major, sub, _method, sha in vt.VERSIONS:
        assert '| **{}** | {} ({}) |'.format(major, sub, sha) in text
    listed = re.search(r'^## Baselines are not versions\n(.*?)^## ', text,
                       flags=re.MULTILINE | re.DOTALL).group(1)
    for method in vt.BASELINES:
        assert '| `{}` |'.format(method) in listed


def test_every_table_has_both_sets_and_their_totals():
    with open(DOC) as handle:
        text = handle.read()
    tables = re.findall(r'^### Baseline V0 · .*?\n\n(\| game \|.*?)\n\n',
                        text + '\n\n', flags=re.MULTILINE | re.DOTALL)
    assert len(tables) == 2 * len(vt.COUNT_METRICS) + 2 + 1
    for table in tables:
        labels = [line.split('|')[1].strip()
                  for line in table.splitlines()[2:]]
        assert '**dev total**' in labels and '**test total**' in labels
        assert labels.index('**dev total**') < labels.index(
            '**test total**')
        assert all(lab.startswith(('dev · ', 'test · ', '**'))
                   for lab in labels)
