"""Tests for manifests, cost accounting and Parquet storage.

These cover the project's non-negotiable engineering rules directly:
reproducibility (config hash, git SHA), accumulate-only storage (nothing
deleted or overwritten), and cost logging.
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lgref.core.cost import CostTracker
from lgref.core.manifest import RunManifest, config_hash
from lgref.core.storage import (ParquetWriter, read_all, read_parts,
                                read_run, run_dir)
from lgref.core import release as R


# ---- config hashing -----------------------------------------------------

def test_config_hash_ignores_key_order():
    assert config_hash({'a': 1, 'b': 2}) == config_hash({'b': 2, 'a': 1})


def test_config_hash_distinguishes_values():
    assert config_hash({'seed': 1}) != config_hash({'seed': 2})


def test_config_hash_distinguishes_nested_values():
    """Nested differences must not collapse — a sweep's variants differ
    only inside engine_kwargs."""
    a = {'engine_kwargs': {'enable_boulder': True}}
    b = {'engine_kwargs': {'enable_boulder': False}}
    assert config_hash(a) != config_hash(b)


# ---- manifests ----------------------------------------------------------

def test_manifest_written_at_start_with_running_status(tmp_path):
    """A killed run must leave evidence it was attempted."""
    m = RunManifest.start('r1', {'iters': 2}, 7, str(tmp_path))
    assert os.path.exists(m.path)
    on_disk = json.load(open(m.path))
    assert on_disk['status'] == 'running'
    assert on_disk['seed'] == 7


def test_manifest_finish_records_outcome_and_wall_clock(tmp_path):
    m = RunManifest.start('r1', {}, 0, str(tmp_path))
    time.sleep(0.01)
    m.finish(status='ok', metrics={'games': 3}, cost={'core_hours': 0.1})
    on_disk = json.load(open(m.path))
    assert on_disk['status'] == 'ok'
    assert on_disk['wall_clock_s'] > 0
    assert on_disk['metrics'] == {'games': 3}
    assert on_disk['cost'] == {'core_hours': 0.1}


def test_manifest_records_provenance_fields(tmp_path):
    m = RunManifest.start('r1', {}, 0, str(tmp_path), repo_root='.')
    for field in ('git_sha', 'config_hash', 'machine', 'engine', 'started_at'):
        assert field in m.data, f'manifest missing {field}'
    assert m.data['machine']['cpu_count']


def test_manifest_roundtrips(tmp_path):
    RunManifest.start('r1', {'x': 1}, 3, str(tmp_path)).finish()
    loaded = RunManifest.load(str(tmp_path))
    assert loaded.data['run_id'] == 'r1'
    assert loaded.data['seed'] == 3


# ---- storage ------------------------------------------------------------

def test_writer_flushes_in_parts(tmp_path):
    d = str(tmp_path / 'games')
    with ParquetWriter(d, 'run1', rows_per_part=2) as w:
        for i in range(5):
            w.append({'game_idx': i})
    parts = sorted(os.listdir(d))
    assert len(parts) == 3, parts          # 2 + 2 + 1
    assert len(read_parts(d)) == 5


def test_storage_never_overwrites_an_existing_part(tmp_path):
    """The accumulate-only guarantee: re-running must not destroy data."""
    d = str(tmp_path / 'games')
    with ParquetWriter(d, 'run1') as w:
        w.extend({'game_idx': i} for i in range(3))
    first = sorted(os.listdir(d))

    with ParquetWriter(d, 'run1') as w:    # same run_id on purpose
        w.append({'game_idx': 99})

    after = sorted(os.listdir(d))
    assert set(first).issubset(set(after)), 'an existing part was removed'
    assert len(after) == len(first) + 1
    df = read_parts(d)
    assert len(df) == 4
    assert 99 in set(df['game_idx'])


def test_read_parts_empty_for_missing_dir(tmp_path):
    assert read_parts(str(tmp_path / 'nope')).empty


def test_dict_columns_survive_as_json(tmp_path):
    """turn_type_counts has open-ended keys (rule names); storing it as
    JSON keeps the schema stable across variants."""
    d = str(tmp_path / 'games')
    with ParquetWriter(d, 'r') as w:
        w.append({'turn_type_counts': {'move': 5, 'boulder': 1}})
    stored = read_parts(d)['turn_type_counts'].iloc[0]
    assert json.loads(stored) == {'move': 5, 'boulder': 1}


def test_variants_with_different_turn_types_share_a_schema(tmp_path):
    """A no-boulder run emits no 'boulder' key; a full run does. Both
    must land in one readable table."""
    root = str(tmp_path)
    for variant, counts in (('full', {'move': 9, 'boulder': 1}),
                            ('no_boulder', {'move': 10})):
        d = os.path.join(run_dir(root, variant, 0), 'games')
        with ParquetWriter(d, 'r') as w:
            w.append({'game_idx': 0, 'turn_type_counts': counts})
    df = read_all(root)
    assert len(df) == 2
    assert set(df['variant']) == {'full', 'no_boulder'}


def test_read_all_labels_variant_and_seed(tmp_path):
    root = str(tmp_path)
    d = os.path.join(run_dir(root, 'no_boulder', 4), 'games')
    with ParquetWriter(d, 'r') as w:
        w.append({'game_idx': 0})
    df = read_run(root, 'no_boulder', 4)
    assert len(df) == 1
    df_all = read_all(root)
    assert df_all['variant'].iloc[0] == 'no_boulder'
    assert df_all['seed'].iloc[0] == 4


# ---- cost ---------------------------------------------------------------

def test_cost_core_hours_scale_with_workers():
    a = CostTracker(n_workers=1)
    b = CostTracker(n_workers=8)
    a._elapsed = b._elapsed = 3600.0
    assert a.core_hours == pytest.approx(1.0)
    assert b.core_hours == pytest.approx(8.0)


def test_cost_dollars_use_the_recorded_rate():
    c = CostTracker(n_workers=2, venue='cloud_spot')
    c._elapsed = 3600.0
    assert c.usd == pytest.approx(2 * c.rate)
    assert c.as_dict()['rate_usd_per_core_hour'] == c.rate


def test_cost_projection_extrapolates_measured_rate():
    """The pilot's overrun report depends on this arithmetic."""
    c = CostTracker(n_workers=4)
    c._elapsed = 100.0
    c.add_units(10, 'games')
    # 100s wall x 4 workers / 10 games = 40 core-s per game
    assert c.core_seconds_per_unit == pytest.approx(40.0)
    proj = c.project(1000)
    assert proj['core_hours'] == pytest.approx(40_000 / 3600.0, rel=1e-3)


def test_cost_report_mentions_units():
    c = CostTracker(n_workers=2)
    c._elapsed = 10.0
    c.add_units(5, 'games')
    assert 'games' in c.format_report()


# ---- release integrity --------------------------------------------------

def test_bundle_verifies_against_committed_checksum(tmp_path):
    rd = os.path.join(run_dir(str(tmp_path), 'full', 0))
    RunManifest.start('r1', {}, 0, rd).finish()
    with ParquetWriter(os.path.join(rd, 'games'), 'r1') as w:
        w.append({'game_idx': 0})
    bundle = R.bundle_run(rd)
    index = os.path.join(str(tmp_path), 'release_index.json')
    R.update_index(index, R.describe_bundle(bundle, rd), 'lgref-data-v1')
    ok, detail = R.verify_bundle(bundle, index)
    assert ok, detail


def test_tampered_bundle_fails_verification(tmp_path):
    """This is the property the whole storage design exists for: a
    reviewer can prove the data matches what produced the figures."""
    rd = run_dir(str(tmp_path), 'full', 0)
    RunManifest.start('r1', {}, 0, rd).finish()
    with ParquetWriter(os.path.join(rd, 'games'), 'r1') as w:
        w.append({'game_idx': 0})
    bundle = R.bundle_run(rd)
    index = os.path.join(str(tmp_path), 'release_index.json')
    R.update_index(index, R.describe_bundle(bundle, rd), 'lgref-data-v1')

    with open(bundle, 'ab') as f:
        f.write(b'tampered')

    ok, detail = R.verify_bundle(bundle, index)
    assert not ok
    assert 'MISMATCH' in detail


def test_unknown_asset_is_not_silently_accepted(tmp_path):
    index = os.path.join(str(tmp_path), 'release_index.json')
    R.update_index(index, {'asset': 'known.tar.gz', 'sha256': 'x', 'bytes': 1})
    ok, detail = R.verify_bundle(str(tmp_path / 'mystery.tar.gz'), index)
    assert not ok
    assert 'not in' in detail


def test_index_carries_provenance_from_the_manifest(tmp_path):
    """The committed index alone must answer 'which code made this?'."""
    rd = run_dir(str(tmp_path), 'full', 5)
    RunManifest.start('r9', {'iters': 1}, 5, rd, repo_root='.').finish()
    with ParquetWriter(os.path.join(rd, 'games'), 'r9') as w:
        w.append({'game_idx': 0})
    rec = R.describe_bundle(R.bundle_run(rd), rd)
    assert rec['run_id'] == 'r9'
    assert rec['seed'] == 5
    assert rec['config_hash']


# ---- config -------------------------------------------------------------

def test_config_inherits_from_base():
    from lgref.core.config import load_config
    c = load_config('pilot.yaml')
    assert c['variant'] == 'full'
    assert c['max_turns'] == 1000          # inherited from base.yaml
    assert c['cost']['n_workers'] == 8     # nested inheritance


def test_config_child_overrides_parent(tmp_path):
    from lgref.core.config import load_config
    (tmp_path / 'base.yaml').write_text('a: 1\nnested: {x: 1, y: 2}\n')
    (tmp_path / 'child.yaml').write_text(
        'extends: base.yaml\na: 99\nnested: {y: 42}\n')
    c = load_config(str(tmp_path / 'child.yaml'))
    assert c['a'] == 99
    assert c['nested'] == {'x': 1, 'y': 42}, 'deep merge lost a parent key'


def test_config_refuses_chained_extends(tmp_path):
    """Two-level inheritance makes 'what did this run use?' unanswerable
    at a glance, so it is refused rather than silently resolved."""
    from lgref.core.config import load_config, ConfigError
    (tmp_path / 'a.yaml').write_text('v: 1\n')
    (tmp_path / 'b.yaml').write_text('extends: a.yaml\n')
    (tmp_path / 'c.yaml').write_text('extends: b.yaml\n')
    with pytest.raises(ConfigError, match='chained'):
        load_config(str(tmp_path / 'c.yaml'))


def test_missing_config_raises():
    from lgref.core.config import load_config, ConfigError
    with pytest.raises(ConfigError, match='not found'):
        load_config('definitely-not-a-config.yaml')


def test_require_reports_all_missing_keys_at_once():
    from lgref.core.config import require, ConfigError
    with pytest.raises(ConfigError) as exc:
        require({'a': 1}, 'a', 'b', 'c')
    assert 'b' in str(exc.value) and 'c' in str(exc.value)


def test_config_hash_is_stable_across_comment_only_edits(tmp_path):
    """Formatting must not change a run's identity."""
    from lgref.core.config import load_config
    (tmp_path / 'x.yaml').write_text('# a comment\na: 1\nb: 2\n')
    first = load_config(str(tmp_path / 'x.yaml'))
    (tmp_path / 'x.yaml').write_text('b: 2\n# different comment\na: 1\n')
    second = load_config(str(tmp_path / 'x.yaml'))
    first.pop('_config_path'); second.pop('_config_path')
    assert config_hash(first) == config_hash(second)
