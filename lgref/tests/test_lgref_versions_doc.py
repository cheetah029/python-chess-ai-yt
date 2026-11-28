"""LGREF's identification numbering is a record, so it must point at real
commits and agree with the code and the freeze.

Issue #409. `docs/lgref-versions.md` numbers LGREF's grouping builds as
`docs/agent-versions.md` numbers the players. A number pointing at a
mistyped SHA, a baseline quietly given a version number, or a
representative that is not the frozen commit would each make "V1" mean
two things.
"""

import json
import os
import re
import subprocess

import pytest

REPO = os.path.join(os.path.dirname(__file__), '..', '..')
DOC = os.path.join(REPO, 'docs', 'lgref-versions.md')
FREEZE = os.path.join(REPO, 'docs', 'paper-a', 'freeze.md')
FINGERPRINTS = os.path.join(REPO, 'docs', 'lgref-version-fingerprints.json')

SHORT_SHA = re.compile(r'(?<![0-9a-zA-Z_])[0-9a-f]{7}(?![0-9a-zA-Z_])')

#: Paths whose change is a change to identification (the doc's
#: definition). A sub-version's commit must touch one of them.
IDENTIFICATION = ('lgref/identify/', 'lgref/bench/methods.py',
                  'lgref/bench/interventions.py')


def _text():
    with open(DOC) as handle:
        return handle.read()


def _git(*args):
    return subprocess.run(['git', '-C', REPO] + list(args), check=True,
                          capture_output=True, text=True).stdout


def _git_available():
    try:
        _git('rev-parse', 'HEAD')
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


needs_git = pytest.mark.skipif(not _git_available(),
                               reason='needs a git checkout')


def _majors():
    sections = re.split(r'^## (V\d+): ', _text(), flags=re.MULTILINE)
    return dict(zip(sections[1::2], sections[2::2]))


def _sub_versions():
    """[(sub-version, sha)] from every major section's table rows."""
    out = []
    for body in _majors().values():
        for sub, sha in re.findall(
                r'^\| \*\*(V\d+\.\d+)\*\* \| [\d-]+ \| ([0-9a-f]{7}) \|',
                body, flags=re.MULTILINE):
            out.append((sub, sha))
    return out


@needs_git
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
    text = _text()
    majors = _majors()
    assert sorted(majors) == ['V0', 'V1']
    for major, body in majors.items():
        rows = [line for line in body.splitlines()
                if line.startswith('| **{}.'.format(major))
                and 'Representative' in line]
        assert len(rows) == 1, '{} has {} representatives'.format(
            major, len(rows))
        sub, sha = re.match(r'\| \*\*(V[\d.]+)\*\* \| [\d-]+ \| '
                            r'([0-9a-f]{7}) ', rows[0]).groups()
        assert '| **{}** | {} ({}) |'.format(major, sub, sha) in text, (
            'the summary does not name {} ({}) for {}'.format(
                sub, sha, major))


def test_the_representative_is_the_latest_sub_version():
    for major, body in _majors().items():
        subs = re.findall(r'^\| \*\*({}\.(\d+))\*\*'.format(major), body,
                          flags=re.MULTILINE)
        numbers = [int(n) for _s, n in subs]
        assert numbers == list(range(len(numbers))), (
            '{} sub-versions are not numbered 0, 1, 2, ...'.format(major))
        latest = [line for line in body.splitlines()
                  if line.startswith('| **{}.{}**'.format(major,
                                                          numbers[-1]))]
        assert 'Representative' in latest[0]


def test_v1_representative_is_the_paper_a_freeze():
    with open(FREEZE) as handle:
        frozen = re.search(r'\*\*`([0-9a-f]{40})`\*\*',
                           handle.read()).group(1)
    assert '| **V1** | V1.8 ({}) |'.format(frozen[:7]) in _text()


@needs_git
def test_sub_versions_are_in_commit_order():
    shas = [sha for _sub, sha in _sub_versions() if _sub.startswith('V1')]
    for older, newer in zip(shas, shas[1:]):
        result = subprocess.run(['git', '-C', REPO, 'merge-base',
                                 '--is-ancestor', older, newer],
                                capture_output=True)
        assert result.returncode == 0, '{} is not before {}'.format(
            older, newer)


@needs_git
def test_every_sub_version_touches_identification_code():
    for sub, sha in _sub_versions():
        changed = _git('diff', '--name-only', sha + '^1', sha).split()
        assert any(path.startswith(IDENTIFICATION) for path in changed), (
            '{} ({}) changes no identification code'.format(sub, sha))


def test_baseline_methods_are_labelled_and_never_numbered():
    """Every method the bench compares is either a version's method or a
    listed baseline, and no baseline sits in a version table."""
    from lgref.bench.methods import METHODS
    text = _text()
    baselines = re.search(r'^## Baselines are not versions\n(.*?)^## ',
                          text, flags=re.MULTILINE | re.DOTALL).group(1)
    listed = set(re.findall(r'^\| `(\w+)` \|', baselines,
                            flags=re.MULTILINE))
    versions = {'lgref', 'random_matched'}
    assert set(METHODS) - versions <= listed, (
        'baselines missing from the doc: {}'.format(
            sorted(set(METHODS) - versions - listed)))
    assert not listed & versions
    for major, body in _majors().items():
        for row in body.splitlines():
            if row.startswith('| **{}.'.format(major)):
                named = set(re.findall(r'`(\w+)`', row)) & listed
                assert not named, '{} appears in a {} row'.format(
                    sorted(named), major)


def _fingerprints():
    with open(FINGERPRINTS) as handle:
        return json.load(handle)


def _label(cell):
    """'V1.1 (259a78d)', 'V1.1' or '1d52ee3' -> a SHA."""
    sha = re.search(r'[0-9a-f]{7}', cell)
    if sha:
        return sha.group(0)
    subs = dict(_sub_versions())
    return subs[cell.strip()]


def test_the_change_table_matches_the_recorded_fingerprints():
    """Every row of "How changed and identical were checked" is
    recomputed from the fingerprints recorded at each commit."""
    data = _fingerprints()
    prints = data['commits']
    table = re.search(r'^\| from \| to \|.*?\n\|---.*?\n((?:\|.*\n)+)',
                      _text(), flags=re.MULTILINE).group(1)
    rows = [[c.strip() for c in line.split('|')[1:-1]]
            for line in table.strip().splitlines()]
    pairs = list(zip(data['order'], data['order'][1:]))
    assert [(_label(r[0]), _label(r[1])) for r in rows] == pairs
    for (a, b), row in zip(pairs, rows):
        games = [g for g in prints[b]
                 if 'error' not in prints[a].get(g, {'error': 1})
                 and 'error' not in prints[b][g]]
        groups = sum(prints[a][g]['groups'] != prints[b][g]['groups']
                     for g in games)
        if prints[b][games[0]]['ownership'] is None:
            own = 'n/a'
        elif prints[a][games[0]]['ownership'] is None:
            own = 'new'
        else:
            own = str(sum(prints[a][g]['ownership']
                          != prints[b][g]['ownership'] for g in games))
        assert row[2:] == [str(len(games)), str(groups), own], (a, b, row)


def test_commits_named_not_sub_versions_change_nothing():
    data = _fingerprints()
    prints = data['commits']
    subs = {sha for _s, sha in _sub_versions()}
    order = data['order']
    for before, sha in zip(order, order[1:]):
        if sha in subs:
            continue
        assert prints[before] == prints[sha], sha
    assert set(order) - subs, 'no non-sub-version commit was checked'
    text = _text()
    section = text[text.index('### Commits that did not change'):
                   text.index('### How')]
    for sha in set(order) - subs:
        assert sha in section, sha


def test_every_sub_version_is_fingerprinted():
    order = _fingerprints()['order']
    for sub, sha in _sub_versions():
        if sub.startswith('V1'):
            assert sha in order, sub


def test_functional_identification_has_its_own_section():
    assert re.search(r'^## Functional identification', _text(),
                     flags=re.MULTILINE)
