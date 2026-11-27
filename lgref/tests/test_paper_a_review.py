"""The blind Claude review (#358): a subjective, secondary metric.

The tests pin what makes it comparable across methods: one fixed prompt,
no method name anywhere in the packet, every method keyed to exactly one
label, identical groupings sharing a label, and a parse that maps the
reviewer's scores back to methods.
"""

import json

import lgref  # noqa: F401
from lgref.bench import methods as M
from lgref.bench import review
from lgref.bench.catalog import game_path
from lgref.bench.experiments import grouping_for
from lgref.identify.clauses import load


def _groupings(game='nim'):
    nodes = load(game_path(game))
    return {m: grouping_for(m, nodes, 0) for m in M.METHODS}


def test_packet_names_no_method():
    text, key = review.build('nim', _groupings())
    for method in M.METHODS:
        assert method not in text
    assert review.PROMPT in text


def test_every_method_has_one_label_and_twins_share_it():
    groupings = _groupings('tictactoe')
    _text, key = review.build('tictactoe', groupings)
    keyed = [m for methods in key.values() for m in methods]
    assert sorted(keyed) == sorted(M.METHODS)
    # LGREF and Leiden give the same grouping on tic-tac-toe.
    assert any({'lgref', 'leiden'} <= set(v) for v in key.values())


def test_the_order_is_seeded():
    groupings = _groupings()
    assert review.build('nim', groupings, seed=1) == review.build(
        'nim', groupings, seed=1)
    assert review.build('nim', groupings, seed=1)[1] != review.build(
        'nim', groupings, seed=2)[1]


def test_parse_and_summarize():
    reply = 'Here: ' + json.dumps({'groupings': {'G1': {
        'groups': {'1': {'score': 4, 'reason': 'x'},
                   '2': {'score': 2, 'reason': 'y'}},
        'overall': {'score': 3, 'reason': 'z'}}}})
    got = review.summarize(review.parse(reply), {'G1': ['a', 'b']})
    assert got['a']['mean_group'] == 3.0 and got['b']['overall'] == 3


def test_recorded_reviews_cover_every_dev_game_and_method():
    from lgref.bench.catalog import in_split
    text = review.table(in_split('dev'))
    for method in M.METHODS:
        assert '| {} |'.format(method) in text
