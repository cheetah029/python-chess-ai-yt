"""The work-in-progress command line.

Issue #193. `python3 -m lgref --gdl <game>` is the user-facing entry
point. Two things it must not do: claim a phase is built when it is not,
and produce output that only makes sense for Royal Chess.
"""

import os

import pytest

from lgref import main as cli

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OFFICIAL = os.path.join(REPO, 'docs', 'gdl', 'integrated.gdl')
GAMES = os.path.join(REPO, 'lgref', 'identify', 'testgames')
LEGACY_PREFIX = os.path.join(REPO, 'docs', 'gdl', 'integrated_prefix.gdl')


def run(argv, capsys):
    assert cli.main(argv) == 0
    return capsys.readouterr().out


def test_status_needs_no_description(capsys):
    out = run(['status'], capsys)
    assert 'NOT BUILT' in out, (
        'status must say which phases are missing, not imply completeness')
    assert 'work in progress' in out.lower()


def test_status_matches_the_phases_table():
    """The table is the single source of truth for what exists.

    A phase landing without this being updated makes the CLI lie about
    the tool, which is worse than having no status command.
    """
    names = [name for name, _, _ in cli.PHASES]
    assert any(n.startswith('1 ') for n in names)
    assert any(n.startswith('7 ') for n in names)
    states = {state for _, state, _ in cli.PHASES}
    assert states <= {'built', 'partly built', 'NOT BUILT'}


@pytest.mark.parametrize('game', ['tictactoe', 'nim'])
def test_runs_on_games_that_are_not_royal_chess(game, capsys):
    """Genericity, checked rather than asserted in a docstring."""
    path = os.path.join(GAMES, '{}.gdl'.format(game))
    out = run(['ablations', '--gdl', path], capsys)
    assert 'ABLATION MENU' in out
    assert 'boulder' not in out.lower(), (
        'Royal Chess vocabulary leaked into another game\'s menu')


def test_nim_entities_are_its_own(capsys):
    """nim's `take(1)` / `take(2)` give entities 1 and 2.

    Removing one is a real ablation of nim -- "what if you could only
    take one?" -- derived from the description with no idea what nim is.
    """
    out = run(['ablations', '--gdl', os.path.join(GAMES, 'nim.gdl')], capsys)
    assert 'remove 1' in out and 'remove 2' in out


def test_tictactoe_reports_no_entities_rather_than_inventing_them(capsys):
    """Its action is `mark(X,Y)` -- coordinates, not a piece type."""
    out = run(['ablations', '--gdl',
               os.path.join(GAMES, 'tictactoe.gdl')], capsys)
    assert 'no action subjects' in out


def test_identify_reports_the_resolution_caveat(capsys):
    out = run(['identify', '--gdl', os.path.join(GAMES, 'nim.gdl')], capsys)
    assert '#189' in out, (
        'the cluster list must carry the known-too-coarse caveat')


def test_prefix_input_is_refused_with_a_usable_message():
    with pytest.raises(ValueError) as excinfo:
        cli.main(['identify', '--gdl', LEGACY_PREFIX])
    assert 'build_integrated.py' in str(excinfo.value)


def test_missing_description_fails_cleanly():
    with pytest.raises(SystemExit):
        cli.main(['identify', '--gdl', '/nonexistent/game.gdl'])


def test_gdl_is_required_for_analysis_commands():
    with pytest.raises(SystemExit):
        cli.main(['ablations'])
