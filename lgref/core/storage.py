"""Parquet storage for raw LGREF records — accumulate-only.

Project rules this implements:

  - Raw per-game and per-position records are stored, never only
    aggregates. Analysis reads from stored raw data.
  - Nothing is deleted and recomputed. Results accumulate.

Why Parquet and not JSON: measured at 240 KB of JSON per game
(658 B/ply), the full sweep is ~46,000 games ~= 11 GB of JSON. Parquet's
columnar compression takes that to roughly 1-2 GB, which is the
difference between "publishable as a Release asset" and "not storable".

Layout, one directory per (variant, seed) run:

    <root>/<variant>/seed<k>/
        manifest.json          provenance + cost (see manifest.py)
        games/    part-<nnnnn>-<run_id>.parquet    one row per game
        positions/part-<nnnnn>-<run_id>.parquet    one row per ply

Each writer flush produces a NEW part file; nothing is appended in place
and nothing is overwritten. A part filename collision raises rather than
clobbering, so a re-run cannot silently destroy an earlier result. To
add data you add parts; to correct data you write a new run and leave
the old one standing.

Readers glob the parts, so a partially-written run still reads — that is
deliberate, since a killed Kaggle session should not cost the games it
already played.
"""

import glob
import json
import os

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


COMPRESSION = 'zstd'


def _sanitize(records):
    """Flatten values Parquet cannot store natively.

    Nested dicts with open-ended keys (turn_type_counts, whose keys are
    rule names) are stored as a JSON string rather than a struct, so the
    schema stays stable when a variant introduces a turn type others
    never produce. Tuples become lists so pyarrow infers a list type
    instead of failing.
    """
    out = []
    for rec in records:
        row = {}
        for k, v in rec.items():
            if isinstance(v, dict):
                row[k] = json.dumps(v, sort_keys=True)
            elif isinstance(v, tuple):
                row[k] = list(v)
            else:
                row[k] = v
        out.append(row)
    return out


class ParquetWriter:
    """Buffered, accumulate-only Parquet part writer.

    Rows are buffered and flushed to a new part file every
    `rows_per_part` rows (and on close). Buffering keeps part count and
    per-file overhead sane; a new file per flush keeps the
    never-overwrite guarantee.
    """

    def __init__(self, out_dir, run_id, rows_per_part=2000):
        self.out_dir = out_dir
        self.run_id = run_id
        self.rows_per_part = rows_per_part
        self._buf = []
        self._part = 0
        self._rows_written = 0
        os.makedirs(out_dir, exist_ok=True)

    def append(self, record):
        self._buf.append(record)
        if len(self._buf) >= self.rows_per_part:
            self.flush()
        return self

    def extend(self, records):
        for r in records:
            self.append(r)
        return self

    def _next_path(self):
        while True:
            path = os.path.join(
                self.out_dir, f'part-{self._part:05d}-{self.run_id}.parquet')
            if not os.path.exists(path):
                return path
            # Never clobber an existing part. Skip forward instead, so a
            # resumed run adds to the directory rather than overwriting
            # what a previous attempt already earned.
            self._part += 1

    def flush(self):
        if not self._buf:
            return None
        path = self._next_path()
        table = pa.Table.from_pylist(_sanitize(self._buf))
        pq.write_table(table, path, compression=COMPRESSION)
        self._rows_written += len(self._buf)
        self._buf = []
        self._part += 1
        return path

    def close(self):
        self.flush()
        return self._rows_written

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    @property
    def rows_written(self):
        return self._rows_written + len(self._buf)


def read_parts(out_dir):
    """Read every part in a directory into one DataFrame.

    Returns an empty DataFrame when the directory is missing or has no
    parts, so analysis code can treat "run not done yet" and "run
    produced nothing" uniformly instead of guarding every call site.
    """
    pattern = os.path.join(out_dir, 'part-*.parquet')
    paths = sorted(glob.glob(pattern))
    if not paths:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)


def run_dir(root, variant, seed):
    return os.path.join(root, variant, f'seed{seed}')


def read_run(root, variant, seed, kind='games'):
    return read_parts(os.path.join(run_dir(root, variant, seed), kind))


def read_all(root, kind='games'):
    """Every run under `root`, concatenated, with variant/seed columns.

    This is the entry point for Phase 4: analysis reads stored raw data
    and never recomputes it.
    """
    frames = []
    if not os.path.isdir(root):
        return pd.DataFrame()
    for variant in sorted(os.listdir(root)):
        vdir = os.path.join(root, variant)
        if not os.path.isdir(vdir):
            continue
        for seed_dir in sorted(os.listdir(vdir)):
            if not seed_dir.startswith('seed'):
                continue
            df = read_parts(os.path.join(vdir, seed_dir, kind))
            if df.empty:
                continue
            df['variant'] = variant
            df['seed'] = int(seed_dir[4:])
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
