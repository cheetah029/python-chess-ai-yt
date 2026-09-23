"""The unsuffixed rulebook name must be the authoritative one.

Issue #197. `RULEBOOK.md` used to hold the original DRAFT while the real
rules lived in `RULEBOOK_v2.md`. That is a live hazard, not untidiness:
CLAUDE.md opens with a mandatory procedure to read the rulebook before
answering any rule question, precisely because pretrained chess
intuition gives wrong answers for this variant. A reader who opened the
most prominent file got superseded rules while believing they had
followed the procedure.

These tests fail if that arrangement comes back, or if a rename leaves a
dangling reference behind.
"""

import os
import re
import subprocess

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OFFICIAL = os.path.join(REPO, 'RULEBOOK.md')
SUPERSEDED = os.path.join(REPO, 'RULEBOOK_v1_superseded.md')
ELABORATED = os.path.join(REPO, 'docs', 'RULEBOOK_elaborated.md')


def _read(path):
    with open(path) as handle:
        return handle.read()


def test_the_official_rulebook_is_the_unsuffixed_name():
    assert os.path.exists(OFFICIAL)
    text = _read(OFFICIAL)
    assert 'Draft Rulebook' not in text, (
        'RULEBOOK.md is the old draft again')
    # Rules only the current ruleset has.
    assert 'Tiny Endgame Rule' in text
    assert 'cancel' in text.lower()


def test_the_superseded_draft_says_so_in_its_first_lines():
    """A filename is a weak signal once the file is open."""
    head = _read(SUPERSEDED)[:600]
    assert 'SUPERSEDED' in head
    assert 'RULEBOOK.md' in head, 'the banner must point at the real one'


def test_the_elaborated_rulebook_matches_the_naming():
    assert os.path.exists(ELABORATED)
    assert not os.path.exists(
        os.path.join(REPO, 'docs', 'RULEBOOK_v2_elaborated.md'))


def test_no_live_file_references_a_rulebook_that_does_not_exist():
    """Catches a rename that updated the files but not the pointers.

    `snapshots/` is excluded on purpose: those are frozen historical
    copies carrying their own `RULEBOOK_v2.md`, and rewriting their
    references would make a snapshot describe files that did not exist
    when it was taken.
    """
    tracked = subprocess.run(
        ['git', 'ls-files'], capture_output=True, text=True,
        cwd=REPO, check=True).stdout.split()
    pattern = re.compile(r'RULEBOOK[A-Za-z0-9_]*\.md')
    dangling = []
    for name in tracked:
        if name.startswith('snapshots/') or not name.endswith(
                ('.md', '.py', '.txt', '.yaml')):
            continue
        if name == 'RULEBOOK_v1_superseded.md':
            continue          # its banner names the historical filename
        try:
            text = _read(os.path.join(REPO, name))
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for referenced in set(pattern.findall(text)):
            here = os.path.join(REPO, referenced)
            docs = os.path.join(REPO, 'docs', referenced)
            if not (os.path.exists(here) or os.path.exists(docs)):
                dangling.append('{} -> {}'.format(name, referenced))
    assert not dangling, 'dangling rulebook references:\n  ' + \
        '\n  '.join(sorted(set(dangling)))


@pytest.mark.parametrize('stale', ['RULEBOOK_v2.md'])
def test_the_old_names_are_gone_from_the_repository_root(stale):
    assert not os.path.exists(os.path.join(REPO, stale))
