"""The version-match runner implements the cell protocol it claims (#282).

`lgref/experiments/versions.py` fills the perfect-information cells of
`docs/experiments/version-win-rates.md`. Each claim of that doc's
protocol is checked here against the runner, not against a description
of it:

1. A cell is (W + D/2) / n with a 95% Wilson interval, and the numbers
   it prints reproduce a cell already in the doc.
2. Truncated and diverged games are kept out of the score and counted.
3. Seats alternate game by game, and the two games of a pair start from
   the same random opening, so each opening is played from both sides.
4. A worker answers for the tree it was started in, refuses a move its
   own rules do not allow (the host then records a divergence), and a
   seeded match is reproduced exactly by a second run.
"""

import json
import os
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO)

from lgref.experiments import versions  # noqa: E402


def _record(result, a_first=True, index=0):
    return {'result': result, 'a_first': a_first, 'index': index}


def test_the_score_and_interval_reproduce_a_cell_in_the_doc():
    """Krieg-TicTacToe V0 vs V0: W186 D33 L181 is `50.6% [45.7, 55.5]`."""
    records = ([_record('A')] * 186 + [_record('draw')] * 33
               + [_record('B')] * 181)
    summary = versions.summarise(records)
    assert versions.cell_text(summary) == '50.6% [45.7, 55.5] n=400'


def test_truncated_and_diverged_games_are_counted_but_not_scored():
    records = [_record('A'), _record('B'), _record('truncated'),
               _record('diverged'), _record('draw')]
    summary = versions.summarise(records)
    assert summary['n'] == 3
    assert summary['score'] == pytest.approx(0.5)
    assert summary['truncated'] == 1 and summary['diverged'] == 1
    assert summary['games'] == 5


def test_the_per_seat_scores_split_by_who_moved_first():
    records = [_record('A', True), _record('A', True),
               _record('B', False), _record('draw', False)]
    summary = versions.summarise(records)
    assert summary['first'] == pytest.approx(1.0)
    assert summary['second'] == pytest.approx(0.25)


def _match(tmp_path, name, game='mnk:3,3,3', a='v0', b='v0', games=8,
           seed=5):
    log = str(tmp_path / name)
    versions.play(game, '{0}@{1}'.format(a, REPO),
                  '{0}@{1}'.format(b, REPO), games, seed, log)
    return versions.load_records([log])


def test_seats_alternate_and_each_opening_is_played_from_both_sides(
        tmp_path):
    records = _match(tmp_path, 'seats.jsonl', game='mnk:5,5,4', games=12)
    assert [r['a_first'] for r in records] == [True, False] * 6
    for even, odd in zip(records[0::2], records[1::2]):
        assert even['pair'] == odd['pair']
        assert even['opening_moves'] == odd['opening_moves']
    # The openings differ between pairs, or a deterministic pair of
    # players would play one game per seat however long the cell.
    assert len(set(json.dumps(r['opening_moves'])
                   for r in records[0::2])) > 1


def test_a_seeded_match_is_reproduced_by_a_second_run(tmp_path):
    first = _match(tmp_path, 'one.jsonl', a='v1', games=4)
    second = _match(tmp_path, 'two.jsonl', a='v1', games=4)
    keys = ('result', 'opening_moves', 'plies', 'a_first')
    assert ([[r[k] for k in keys] for r in first]
            == [[r[k] for k in keys] for r in second])


def test_a_log_resumes_rather_than_replaying(tmp_path):
    log = str(tmp_path / 'resume.jsonl')
    spec = 'v0@{0}'.format(REPO)
    versions.play('mnk:3,3,3', spec, spec, 4, 3, log)
    versions.play('mnk:3,3,3', spec, spec, 6, 3, log)
    indices = [r['index'] for r in versions.load_records([log])]
    assert indices == list(range(6))
    with open(log) as handle:
        assert len(handle.readlines()) == 6


@pytest.mark.parametrize('compiled_off', [True, False])
def test_a_worker_refuses_a_move_its_rules_do_not_allow(compiled_off,
                                                        monkeypatch):
    """With a compiled build present (#362), the reply to `new` also
    names the modules that loaded compiled (#364), so the reply is
    checked field by field. With compiled modules off it is exactly
    `{'ok': True}`, as before. The test used to fail in any checkout
    that had a build (#384)."""
    if compiled_off:
        monkeypatch.setenv('LGREF_COMPILED', '0')
    else:
        monkeypatch.delenv('LGREF_COMPILED', raising=False)
    worker = versions.Worker('v0', REPO)
    try:
        reply = worker.new('mnk:3,3,3', 1)
        if compiled_off:
            assert reply == {'ok': True}
        else:
            assert reply.get('ok') is True
            assert set(reply) <= {'ok', 'compiled'}
            assert all(isinstance(name, str)
                       for name in reply.get('compiled', []))
        assert worker.ask(op='play', move=4) == {'ok': True}
        reply = worker.ask(op='play', move=4)    # the cell is taken
        assert 'error' in reply
    finally:
        worker.close()


def test_a_divergence_is_recorded_not_scored(tmp_path, monkeypatch):
    """When a worker refuses a move the host played, the game is
    `diverged` and says why."""
    original = versions.Worker.ask

    def refuse_the_centre(self, **request):
        if request.get('op') == 'play' and request.get('move') == 4:
            return {'error': 'not legal here'}
        return original(self, **request)

    monkeypatch.setattr(versions.Worker, 'ask', refuse_the_centre)
    records = _match(tmp_path, 'diverged.jsonl', games=20)
    diverged = [r for r in records if r['result'] == 'diverged']
    assert diverged, 'no game reached the refused move'
    assert all('refused 4' in r['problem'] for r in diverged)
    assert versions.summarise(records)['diverged'] == len(diverged)


def test_the_worker_imports_only_from_the_tree_it_was_given(tmp_path):
    """A worker started at an old commit must not fall back on today's
    modules, which sit beside the worker script itself."""
    import subprocess
    script = ('import sys, json; sys.argv = ["w", {0!r}]; '
              'sys.path.insert(0, {1!r}); '
              'import version_worker as w; w.enter({0!r}); '
              'print(json.dumps(sys.path[:2]))').format(
                  str(tmp_path), os.path.join(REPO, 'lgref', 'experiments'))
    out = subprocess.run([sys.executable, '-c', script],
                         capture_output=True, universal_newlines=True,
                         check=True).stdout
    assert json.loads(out) == [str(tmp_path),
                               os.path.join(str(tmp_path), 'src')]


def test_the_played_settings_are_fixed_per_version_and_game():
    """Fixed depth, never a clock: the settings are a lookup."""
    assert versions.player_args('v4', 'royal')['depth'] == 3
    assert versions.player_args('v4', 'mnk:5,5,4')['depth'] == 3
    assert versions.player_args('v4', 'mnk:13,13,5')['depth'] == 3
    assert versions.player_args('v4', 'mnk:19,19,5')['depth'] == 2
    assert versions.player_args('v1', 'royal')['sims'] == 200
    assert versions.player_args('v5', 'nim')['depth'] == 4
    # V7 is V4 one ply deeper, and nothing else.
    assert versions.player_args('v7', 'royal')['depth'] == 4
    assert versions.player_args('v7', 'mnk:5,5,4')['depth'] == 4
    assert versions.player_args('v7', 'mnk:13,13,5')['depth'] == 4
    assert versions.player_args('v7', 'mnk:19,19,5')['depth'] == 3
    for version in ('v0', 'v1', 'v2', 'v3', 'v4', 'v5', 'v7'):
        assert 'budget' not in versions.player_args(version, 'royal')


@pytest.mark.parametrize('m,n,k', [(3, 3, 3), (5, 5, 4), (4, 6, 3)])
def test_the_generated_mnk_gdl_is_the_game_the_engine_plays(m, n, k):
    """V5 plays m,n,k from a generated GDL while the host referees on
    `MNK`; they must agree on every legal move and every result, with
    cell `i` as `mark(i // n + 1, i % n + 1)`."""
    import random

    sys.path.insert(0, os.path.join(REPO, 'src'))
    from lgref.experiments.gdl import load
    from lgref.experiments.mnk import MNK

    path = versions.mnk_gdl(m, n, k)
    for seed in range(15):
        rng = random.Random(seed)
        gdl, engine = load(path), MNK(m=m, n=n, k=k)

        def cell(turn):
            return (int(turn[1][1]) - 1) * n + int(turn[1][2]) - 1
        while not engine.is_game_over():
            assert not gdl.is_game_over()
            assert (sorted(cell(t) for t in gdl.get_all_legal_turns())
                    == sorted(engine.get_all_legal_turns()))
            chosen = rng.choice(engine.get_all_legal_turns())
            gdl.execute_turn([t for t in gdl.get_all_legal_turns()
                              if cell(t) == chosen][0])
            engine.execute_turn(chosen)
        assert gdl.is_game_over()
        expected = {'x': 'xplayer', 'o': 'oplayer', None: None}
        assert gdl.winner == expected[engine.winner]


def test_verbose_reports_each_searched_move(tmp_path, monkeypatch, capsys):
    """A pilot of a player too slow to finish a game still yields a
    per-move cost."""
    monkeypatch.setattr(versions, 'VERBOSE', True)
    records = _match(tmp_path, 'verbose.jsonl', games=2)
    lines = [line for line in capsys.readouterr().err.splitlines()
             if line.strip().startswith('ply ')]
    assert len(lines) == sum(r['plies'] for r in records)


def test_royal_chess_has_no_ply_cap():
    """Royal Chess ends every game by its rules, so a capped game would
    be an artefact of the harness (reviewer, 2026-11-27)."""
    for version in ('v0', 'v1', 'v3', 'v4', 'v7'):
        assert versions.player_args(version, 'royal')['cap'] is None
    sys.path.insert(0, os.path.join(REPO, 'src'))
    from lgref.experiments import version_worker
    engine = version_worker.RoyalAdapter({'cap': None}).native()
    assert engine.max_turns >= 10 ** 9


def test_the_watchdog_alerts_and_never_stops_a_game(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(versions, 'WATCHDOG_PLIES', 5)
    records = _match(tmp_path, 'watchdog.jsonl', game='mnk:5,5,4',
                     games=6)
    long_games = [r for r in records
                  if len(r['opening_moves']) + r['plies'] >= 5]
    assert long_games
    assert all(r.get('watchdog') for r in long_games)
    assert all(r['result'] in ('A', 'B', 'draw') for r in records)
    assert capsys.readouterr().err.count('WATCHDOG') == len(long_games)


def test_a_commit_without_compiled_modules_runs_as_python(tmp_path):
    """Only a commit with `src/compiled.py` and a build loads compiled
    modules; every older representative runs exactly as Python."""
    import subprocess
    script = ('import sys, json; sys.path.insert(0, {0!r}); '
              'import version_worker as w; w.enter({1!r}); '
              'print(json.dumps(w.activate_compiled()))').format(
                  os.path.join(REPO, 'lgref', 'experiments'), str(tmp_path))
    out = subprocess.run([sys.executable, '-c', script],
                         capture_output=True, universal_newlines=True,
                         check=True).stdout
    assert json.loads(out) == []


def test_every_game_is_saved_as_a_full_record_and_reads_back(tmp_path):
    """No game should ever have to be replayed to be studied: each one
    is written as gzip JSON with every move from the start and the side
    that chose it, and it reads back to the logged row."""
    records = str(tmp_path / 'records')
    log = str(tmp_path / 'full.jsonl')
    spec = 'v0@{0}'.format(REPO)
    versions.play('mnk:5,5,4', spec, spec, 4, 9, log, records=records)
    rows = versions.load_records([log])
    for row in rows:
        path = versions.record_path(records, 'mnk:5,5,4', 'v0', 'v0',
                                    row['index'])
        full = versions.read_record(path)
        for key in ('index', 'pair', 'seed', 'result', 'a_first',
                    'opening_moves', 'plies', 'args_a', 'args_b'):
            assert full[key] == row[key]
        moves = [step['move'] for step in full['sequence']]
        assert moves[:len(row['opening_moves'])] == row['opening_moves']
        assert len(moves) == len(row['opening_moves']) + row['plies']
        sides = set(step['side'] for step in full['sequence'])
        assert sides <= {'opening', 'A', 'B'}
        # Replaying the saved moves reaches the logged result.
        sys.path.insert(0, os.path.join(REPO, 'src'))
        from lgref.experiments.mnk import MNK
        engine = MNK(m=5, n=5, k=4)
        for move in moves:
            engine.execute_turn(move)
        assert engine.is_game_over()
        first_won = engine.winner == 'x'
        if engine.winner is None:
            assert row['result'] == 'draw'
        else:
            assert (row['result'] == 'A') == (first_won == row['a_first'])


def test_a_royal_chess_record_carries_the_engines_own_record(tmp_path):
    records = str(tmp_path / 'records')
    log = str(tmp_path / 'royal.jsonl')
    spec = 'v0@{0}'.format(REPO)
    versions.play('royal', spec, spec, 1, 3, log, records=records)
    row = versions.load_records([log])[0]
    full = versions.read_record(versions.record_path(
        records, 'royal', 'v0', 'v0', 0))
    turns = full['engine_record']['turns']
    assert len(turns) == len(row['opening_moves']) + row['plies']
    assert full['engine_record']['winner'] in ('white', 'black')


def test_the_version_cache_is_ignored_by_git():
    """The runner writes `.version-cache/` into the repository root. Left
    untracked, it made `git status` change in the middle of
    `test_a_dirty_tree_saves_its_diff` (#382), which then failed at
    random. It is a cache, regenerated on demand, so git ignores it."""
    import subprocess

    root = os.path.join(os.path.dirname(__file__), '..', '..')
    if subprocess.run(['git', '-C', root, 'rev-parse'],
                      capture_output=True).returncode != 0:
        pytest.skip('needs a git checkout')
    probe = os.path.join('.version-cache', 'nim_play.gdl')
    ignored = subprocess.run(['git', '-C', root, 'check-ignore', '-q', probe],
                             capture_output=True)
    assert ignored.returncode == 0, '.version-cache/ is not git-ignored'
