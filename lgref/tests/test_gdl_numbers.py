"""A GDL number is digits, never 'nan', 'inf' or '1e5' (#401)."""

import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'src')]

from lgref.experiments import gdl  # noqa: E402


def _old_is_number(value):
    """The previous test, kept here to prove what changed."""
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def test_symbols_that_float_accepts_are_not_numbers():
    for symbol in ('nan', 'NaN', 'inf', 'Infinity', '1e5', '3e851',
                   '1E3', '1.', '.5', ''):
        assert not gdl._is_number(symbol), symbol
    for number in ('0', '7', '12', '-3', '+7', '0.5', '14'):
        assert gdl._is_number(number), number


def test_no_constant_of_any_game_in_the_repository_changes_reading():
    """CONFINED: on every GDL file in the repository, every constant is
    read exactly as before, so no current game's features change. Only
    a constant spelled like 'nan' or '1e5' would, and none exists."""
    files = sorted(set(
        glob.glob(os.path.join(ROOT, 'lgref', '**', '*.gdl'),
                  recursive=True)
        + glob.glob(os.path.join(ROOT, 'docs', 'gdl', '*.gdl'))))
    assert len(files) > 20
    checked = 0
    for path in files:
        with open(path) as handle:
            text = handle.read()
        text = '\n'.join(line.split(';', 1)[0].split('%', 1)[0]
                         for line in text.splitlines())
        for token in set(re.findall(r'[A-Za-z0-9_.+-]+', text)):
            assert gdl._is_number(token) == _old_is_number(token), (
                path, token)
            checked += 1
    assert checked > 1000
