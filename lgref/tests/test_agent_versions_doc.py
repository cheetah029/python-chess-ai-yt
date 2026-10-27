"""The version numbering is a record, so it must point at real commits.

Issue #281. `docs/agent-versions.md` names a commit for every agent
build. A number that points at a mistyped or rebased-away SHA cannot be
checked out, so the build is lost while appearing documented.
"""

import os
import re
import subprocess

import pytest

REPO = os.path.join(os.path.dirname(__file__), '..', '..')
DOC = os.path.join(REPO, 'docs', 'agent-versions.md')

#: A short SHA as the doc writes them: exactly seven hex digits standing
#: alone. Weight-file hashes (16 digits) and vocabulary fingerprints
#: (8) are deliberately not matched.
SHORT_SHA = re.compile(r'(?<![0-9a-zA-Z_])[0-9a-f]{7}(?![0-9a-zA-Z_])')


def _text():
    with open(DOC) as handle:
        return handle.read()


def _git_available():
    try:
        subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'],
                       check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


@pytest.mark.skipif(not _git_available(), reason='needs a git checkout')
def test_every_sha_in_the_numbering_is_a_commit():
    missing = []
    for sha in sorted(set(SHORT_SHA.findall(_text()))):
        result = subprocess.run(
            ['git', '-C', REPO, 'cat-file', '-e', sha + '^{commit}'],
            capture_output=True)
        if result.returncode != 0:
            missing.append(sha)
    assert not missing, 'not commits in this repository: {}'.format(missing)


def test_each_major_version_has_exactly_one_representative():
    """The tables' columns are the representatives, so each major
    version needs one and only one, and the summary must name it."""
    text = _text()
    sections = re.split(r'^## (V\d+) ', text, flags=re.MULTILINE)
    majors = dict(zip(sections[1::2], sections[2::2]))
    assert sorted(majors) == ['V0', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
    for major, body in majors.items():
        rows = [line for line in body.splitlines()
                if line.startswith('| **{}.'.format(major))
                and 'Representative' in line]
        assert len(rows) == 1, '{} has {} representatives'.format(
            major, len(rows))
        sub = re.match(r'\| \*\*(V[\d.]+)\*\*', rows[0]).group(1)
        assert '| **{}** | {} '.format(major, sub) in text, (
            'the summary table does not name {} for {}'.format(sub, major))


TABLES = os.path.join(REPO, 'docs', 'experiments', 'version-win-rates.md')


def test_the_tables_play_each_column_as_its_representative():
    """A column labelled V4 but measured on an older V4 is a different
    player under the same name, which is the defect numbering prevents."""
    with open(TABLES) as handle:
        tables = handle.read()
    text = _text()
    columns = re.findall(r'^\| (V\d) \| (V[\d.]+) .*\| ([0-9a-f]{7}) \|$',
                         tables, flags=re.MULTILINE)
    assert [c[0] for c in columns] == ['V0', 'V1', 'V2', 'V3', 'V4',
                                       'V5', 'V6']
    for major, sub, sha in columns:
        assert '| **{}** | {} ({})'.format(major, sub, sha) in text, (
            '{} is played as {} {} in the tables but the numbering '
            'disagrees'.format(major, sub, sha))


def test_every_baseline_table_has_the_same_rows_and_columns():
    with open(TABLES) as handle:
        tables = handle.read()
    blocks = re.findall(r'^## Table (\d) — baseline (V\d).*?\n\n(?:.*\n)*?'
                        r'(\| Game \|.*\n(?:\|.*\n)+)', tables,
                        flags=re.MULTILINE)
    assert [b[1] for b in blocks] == ['V0', 'V1', 'V2', 'V3', 'V4', 'V5']
    shapes = set()
    for _number, _baseline, table in blocks:
        lines = table.strip().splitlines()
        shapes.add((lines[0], tuple(line.split('|')[1].strip()
                                    for line in lines[2:])))
    assert len(shapes) == 1, 'baseline tables differ in rows or columns'
