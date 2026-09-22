"""The Phase 1 gate report.

The brief asks Phase 1 to stop and show its scores against hand-verified
boundaries with baselines, plus the clusters found, as clause lists.
These tests check the report actually says those things — including the
unflattering ones.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.identify.report import build_report, identify, rule_listing

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, '..', 'identify', 'testgames')
GAMES = ('tictactoe', 'nim')


@pytest.fixture(scope='module')
def report():
    return build_report(os.path.join(GAME_DIR, 'nim.gdl'), GAMES, GAME_DIR)


def test_report_shows_the_baselines_not_just_our_score(report):
    """A score with nothing to compare against is not evidence."""
    assert 'name_similarity' in report
    assert 'static_only' in report
    assert 'trace_only' in report


def test_report_states_why_ari_is_the_headline(report):
    """The reader should not have to know why F1 alone would mislead."""
    assert 'ARI' in report
    assert 'singletons' in report


def test_report_lists_clusters_as_clause_lists_not_names(report):
    """Naming a cluster would assert what it is FOR, which Phase 2 infers
    and Phase 3 tests. Stating it here would prejudge both."""
    assert 'clauses:' in report
    for banned in ('boulder rule', 'knight rule', 'space control'):
        assert banned not in report.lower()


def test_report_shows_every_verdict_including_unusable_clusters(report):
    """Showing only measurable rules would misrepresent how much of the
    game the method accounts for."""
    assert 'load_bearing' in report
    assert 'inert' in report
    assert 'verdicts:' in report


def test_report_explains_what_load_bearing_means(report):
    assert 'cannot be measured' in report


def test_trace_only_shows_not_measured_rather_than_zero(report):
    """`0.000` would read as 'tried and failed' — a different and more
    flattering claim than 'not run'."""
    assert 'n/m' in report


def test_identify_returns_a_verdict_for_every_cluster():
    nodes, graph, rules, dropped, verdicts = identify(
        os.path.join(GAME_DIR, 'tictactoe.gdl'))
    assert rules
    assert set(verdicts) == {r.rule_id for r in rules}


def test_rule_listing_reports_shared_clauses_separately():
    """A shared helper belongs to several rules; hiding that would make
    each rule look self-contained when it is not."""
    _n, _g, rules, _d, verdicts = identify(
        os.path.join(GAME_DIR, 'tictactoe.gdl'))
    listing = rule_listing(rules, verdicts)
    assert 'shared' in listing
