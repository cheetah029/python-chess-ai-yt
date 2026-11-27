"""Saving every random game a Paper A measurement plays (#374).

What is pinned here, and why:

  - recording never changes a result: `walk` returns the same states,
    in the same order, with a recorder active as without one;
  - a record is a FULL record: replaying its joint moves from the
    description's start reproduces the states `walk` visited, and its
    ending and payoffs;
  - an exhaustive census plays no games and records none;
  - the runners write the records of the state set and of every
    validity check to gzipped files, tag each game with its
    intervention, and give the same rows as a run that saves nothing.
"""

import os

import lgref  # noqa: F401  (puts src/ on the path)
from lgref.bench import catalog, probes, wellformed
from lgref.bench import experiments as X


def _text(game):
    with open(catalog.game_path(game)) as handle:
        return handle.read()


def test_recording_changes_nothing():
    for game in ('breakthrough5', 'dotsboxes_2x2', 'foxgeese_mini'):
        text = _text(game)
        plain = wellformed.walk(text, games=12, seed=5)
        with wellformed.recording() as rec:
            recorded = wellformed.walk(text, games=12, seed=5)
        assert plain == recorded
        assert len(rec.games) == 12
        assert set(rec.texts) == {wellformed.description_id(text)}


def test_records_replay_to_the_visited_states():
    text = _text('foxgeese_mini')
    with wellformed.recording() as rec:
        states, _mode = wellformed.walk(text, games=6, seed=2)
    game = wellformed.open_game(text)
    seen = []
    for entry in rec.games:
        game = wellformed.open_game(rec.texts[entry['description']])
        assert entry['roles'] == list(game.roles)
        state = frozenset(game.state)
        for joint in entry['plies']:
            if state not in seen:
                seen.append(state)
            moves = {r: probes._term(m)
                     for r, m in zip(entry['roles'], joint)}
            state = wellformed.successor(game, state, moves)
        if state not in seen and entry['end'] != 'max_plies':
            seen.append(state)
        wellformed.at(game, state)
        assert (entry['end'] == 'terminal') == game.is_terminal()
        if entry['end'] == 'terminal':
            assert entry['goals'] == {
                r: sorted(wellformed.goal_values(game, r))
                for r in game.roles}
    assert seen == states


def test_exhaustive_walk_records_nothing():
    with wellformed.recording() as rec:
        wellformed.walk(_text('chomp_3x3'), exhaustive=True)
    assert rec.games == []


def test_write_and_read_records(tmp_path):
    path = str(tmp_path / 'g' / 'x.jsonl.gz')
    X.write_records(path, {'abc': 'role(a)'}, [{'description': 'abc',
                                                'plies': []}],
                    tag={'group': 3}, mode='wt')
    X.write_records(path, {}, [{'description': 'abc', 'plies': [['m']]}],
                    tag={'group': 4})
    texts, games = X.read_records(path)
    assert texts == {'abc': 'role(a)'}
    assert [g['group'] for g in games] == [3, 4]


def test_intervention_runner_saves_every_validity_game(tmp_path):
    plain, _setup = X.intervention_rows(['nim'], ['lgref'])
    records = str(tmp_path)
    saved, _setup = X.intervention_rows(['nim'], ['lgref'],
                                        records=records)
    for a, b in zip(plain, saved):
        a, b = dict(a), dict(b)
        a.pop('seconds')
        b.pop('seconds')
        assert a == b
    path = os.path.join(records, 'nim', 'interventions.jsonl.gz')
    texts, games = X.read_records(path)
    # Each intervention that reaches the own-play check plays 40 games.
    checked = [r for r in saved if r['valid']
               or (r['invalid_reason'] or '').startswith('own play')]
    assert checked and len(games) == 40 * len(checked)
    assert {(g['method'], g['procedure'], g['group']) for g in games} == {
        (r['method'], r['procedure'], r['group']) for r in checked}
    assert all(g['description'] in texts for g in games)
    # Nim's state set is a census: no games, but the file is written.
    _t, state_games = X.read_records(os.path.join(records, 'nim',
                                                  'state_set.jsonl.gz'))
    assert state_games == []
