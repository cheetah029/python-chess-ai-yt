"""The work-in-progress command line.

Issue #193. `python3 -m lgref --gdl <game>` is the user-facing entry
point. Two things it must not do: claim a phase is built when it is not,
and produce output that only makes sense for Royal Chess.
"""

import os
import subprocess
import sys

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
    entities = [l.split()[1] for l in out.splitlines()
                if l.strip().startswith('remove ') and len(l.split()) > 1]
    assert '1' in entities and '2' in entities, entities


def test_tictactoe_reports_no_entities_rather_than_inventing_them(capsys):
    """Its action is `mark(X,Y)` -- coordinates, not a piece type."""
    out = run(['ablations', '--gdl',
               os.path.join(GAMES, 'tictactoe.gdl')], capsys)
    assert 'no action subjects' in out
    assert 'no rule parameters' in out, (
        'tic-tac-toe has none; saying nothing would look like a run that '
        'found some and reported nothing')


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


# ------------------------------------------------- runnable, not just importable ----

def _clean_run(argv):
    """Invoke the CLI as a USER would: a subprocess, no PYTHONPATH.

    Every test above imports `lgref.main` inside pytest, which puts the
    repository root on `sys.path` itself -- so all of them passed while
    the command line was, in fact, unrunnable. The user hit
    `ModuleNotFoundError: No module named 'lgref'` running the file
    directly, and `No module named 'ggp'` running `python3 -m lgref`,
    because LGREF imports the game rules from the sibling `src/`
    directory. A test that shares the caller's path cannot see that.
    """
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    return subprocess.run([sys.executable] + argv, capture_output=True,
                          text=True, env=env, cwd=REPO)


def test_module_entry_point_runs_without_pythonpath():
    done = _clean_run(['-m', 'lgref', 'status'])
    assert done.returncode == 0, done.stderr
    assert 'NOT BUILT' in done.stdout


def test_script_entry_point_runs_without_pythonpath():
    """`python3 lgref/main.py` -- the obvious thing to try."""
    done = _clean_run([os.path.join(REPO, 'lgref', 'main.py'), 'status'])
    assert done.returncode == 0, done.stderr
    assert 'BUILD STATUS' in done.stdout


def test_analysis_command_reaches_the_ggp_parser_without_pythonpath():
    """`ggp` lives in src/, so this is the import that actually broke."""
    done = _clean_run(['-m', 'lgref', 'ablations', '--gdl',
                       os.path.join(GAMES, 'nim.gdl')])
    assert done.returncode == 0, done.stderr
    assert 'ABLATION MENU' in done.stdout


def test_gate_entry_point_imports_without_pythonpath():
    done = _clean_run(['-m', 'lgref.identify.gate', '--help'])
    assert done.returncode == 0, done.stderr


def test_runs_from_a_different_working_directory():
    """Nothing may depend on being launched from the repository root."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    done = subprocess.run(
        [sys.executable, os.path.join(REPO, 'lgref', 'main.py'),
         'identify', '--gdl', os.path.join(GAMES, 'nim.gdl')],
        capture_output=True, text=True, env=env, cwd=os.path.dirname(REPO))
    assert done.returncode == 0, done.stderr
    assert 'RULE IDENTIFICATION' in done.stdout


def test_default_run_id_does_not_double_prefix_the_report(tmp_path):
    """`phase1_phase1-20260922T173210.txt` is a naming bug, not a name."""
    from lgref.identify import gate
    config = {
        'seed': 0,
        'cost': {'n_workers': 1, 'venue': 'local'},
        'report_dir': str(tmp_path),
        'identification': {
            'gdl': os.path.join(GAMES, 'nim.gdl'),
            'games': ['nim'],
            'game_dir': GAMES,
            'resolution': 1.0,
            'probe_plies': 6,
            'probe_seeds': 1,
        },
    }
    _, out_path, _ = gate.run(config)
    name = os.path.basename(out_path)
    assert name.startswith('phase1_')
    assert 'phase1_phase1' not in name, name


def test_the_plan_checks_every_rule_against_every_mode(capsys):
    """No mode is assigned to a rule; all three are tried on all rules.

    The presentation matters here: three separate lists invited the
    reading that the framework picks a mode per rule, which it does not.
    """
    out = run(['ablations', '--gdl', OFFICIAL], capsys)
    assert 'PER-RULE ABLATION PLAN' in out
    assert 'not a label the framework assigns' in out
    header = [line for line in out.splitlines()
              if line.strip().startswith('rule ')]
    assert header, 'no per-rule table'
    for mode in ('relax', 'remove', 'replace'):
        assert mode in header[0]


def test_inapplicable_modes_are_shown_not_hidden(capsys):
    """A rule with nothing to vary must say so rather than vanish.

    A silently omitted cell is indistinguishable from a mode that was
    tried and found to do nothing, which are very different results.
    """
    out = run(['ablations', '--gdl', OFFICIAL], capsys)
    rows = [l for l in out.splitlines()
            if l.strip().startswith('R') and l.count(' ') > 4]
    assert any(' -' in row for row in rows), (
        'no row shows an inapplicable mode')


def test_distinct_variants_are_counted_separately_from_rule_pairs(capsys):
    """Entities are shared, so rule-entity pairs overcount the runs."""
    out = run(['ablations', '--gdl', OFFICIAL], capsys)
    assert 'DISTINCT VARIANTS' in out
    assert 'distinct removals' in out


def test_the_all_command_exists_and_needs_a_description():
    """One command for the whole pipeline, per the user's request."""
    from lgref.main import build_parser
    parsed = build_parser().parse_args(['all', '--gdl', 'x.gdl'])
    assert parsed.command == 'all'
    with pytest.raises(SystemExit):
        cli.main(['all'])


def test_all_reports_the_unbuilt_phases_rather_than_stopping_quietly():
    """A pipeline that silently ends early looks like one that finished.

    Checked on the status table `all` prints, rather than by running the
    multi-minute phases.
    """
    from lgref.main import PHASES
    missing = [name for name, state, _ in PHASES if state == 'NOT BUILT']
    assert missing, 'nothing is marked NOT BUILT; update this test'
    assert any(name.startswith('4') for name in missing)
