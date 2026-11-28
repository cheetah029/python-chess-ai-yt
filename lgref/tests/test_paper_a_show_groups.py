"""#396: groupings made visible, and the random baseline over draws.

The line numbers must be the file's own; every statement must appear in
the side-by-side table exactly once; the random grouping shown must be
the one Experiment 1 scored; and the random baseline's draws must be
independent permutations of ONE LGREF grouping, summarised per draw
rather than merged.
"""

import os

import pytest

import lgref  # noqa: F401
from lgref.bench import experiments as X
from lgref.bench import methods as M
from lgref.bench import report, show_groups
from lgref.bench.catalog import game_path
from lgref.identify.clauses import load


@pytest.mark.parametrize('game', ['nim', 'checkers_4x4', 'othello4',
                                  'skirmish', 'kalah_mini'])
def test_line_numbers_are_the_files_own(game):
    from ggp.infix import parse_infix
    path = game_path(game)
    lines = show_groups.statement_lines(path)
    with open(path) as handle:
        text = handle.read().splitlines()
    forms = parse_infix('\n'.join(text))
    assert None not in lines and len(lines) == len(forms)
    for number, form in zip(lines, forms):
        assert form in parse_infix(text[number - 1])


def test_every_statement_appears_once_side_by_side():
    path = game_path('checkers_4x4')
    nodes = load(path)
    text, _ = show_groups.show(path, ['lgref', 'random_matched'])
    table = text.split('## Side by side')[1].split('## lgref by group')[0]
    rows = [r for r in table.splitlines() if r.startswith('| ') and
            r[2:3].isdigit()]
    assert len(rows) == len(nodes)


def test_the_random_grouping_shown_is_the_one_scored():
    nodes = load(game_path('synth_shared'))
    shown = show_groups.groupings_for(nodes, ['random_matched'])
    assert shown['random_matched'].groups == X.grouping_for(
        'random_matched', nodes, 0).groups


def test_identify_cli_shows_the_groups(tmp_path, capsys):
    from lgref import main as cli
    cli.main(['identify', '--gdl', game_path('nim'), '--show-groups',
              '--compare', 'random_matched', '--groups-out',
              str(tmp_path)])
    out = capsys.readouterr().out
    assert '## lgref by group' in out and '## random_matched by group' in out
    assert os.path.exists(os.path.join(str(tmp_path), 'nim.md'))


def test_identify_groups_are_the_paper_a_lgref_groups():
    """`lgref identify` and Paper A's `methods.lgref` must show the same
    partition, or the visible groups would not be the scored ones."""
    from lgref.identify.cluster import calibrate_resolution, cluster
    from lgref.identify.graph import ClauseGraph
    nodes = load(game_path('checkers_4x4'))
    graph = ClauseGraph(nodes)
    rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
    assert sorted(sorted(r.all_clause_ids) for r in rules) == sorted(
        sorted(g) for g in M.lgref(nodes).groups)


def test_draws_permute_one_lgref_grouping_and_are_summarised_per_draw():
    rows, setup = X.intervention_rows(['nim'], ['lgref', 'random_matched'],
                                      draws=3)
    random_rows = [r for r in rows if r['method'] == 'random_matched']
    assert {r['draw'] for r in random_rows} == {0, 1, 2}
    assert all(r['draw'] is None for r in rows if r['method'] == 'lgref')
    record = {'rows': rows, 'setup': setup, 'games': ['nim']}
    counts, mean, (low, high), n = report.draws_summary(record)
    assert len(counts) == 3 and n == 2
    assert mean == sum(counts) / 3.0
    # Merging draws would take the best of three: the summary must not.
    merged = report.ablation_summary(
        dict(record, rows=random_rows))['random_matched']['exact']
    assert merged >= max(counts)


def test_random_is_an_alias_for_the_matched_baseline():
    nodes = load(game_path('nim'))
    got = show_groups.groupings_for(nodes, ['random'])
    assert list(got) == ['random_matched']


def test_the_published_draw_numbers_match_the_saved_runs():
    """#396: every number in results-random-draws.md's table is
    recomputed from the saved draws."""
    import gzip
    import json
    here = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), 'docs', 'paper-a')
    with open(os.path.join(here, 'results-random-draws.md')) as handle:
        doc = handle.read()
    for split in ('dev', 'test'):
        with gzip.open(os.path.join(here, 'runs', 'draws_exp1_{}.json.gz'
                                    .format(split)), 'rt') as handle:
            record = json.load(handle)
        for procedure in ('ownership', 'delete_group'):
            counts, mean, (low, high), _n = report.draws_summary(
                record, procedure)
            assert len(counts) == 30
            cell = '{:.2f} [{:.2f}, {:.2f}]'.format(mean, low, high)
            assert cell in doc, (split, procedure, cell)
