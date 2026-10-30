"""Russian Cards: a GDL-III goal that is a conjunction of knowledge.

Alice and Bob win when both know the whole deal and Cath knows the
owner of none of the cards she does not hold -- three `knows`
conditions in the goal rules, one of them negated. Bob's announcement
"Cath holds C" is legal only when he knows it, so knowledge also
decides legality. Checked three ways: the known safe protocol wins on
every deal; Alice naming her hand loses on every deal; and every one
of the 700 complete play sequences (140 deals x Alice's three choices
x Bob's) gets the goal a brute-force solution, written below
without any GDL, says it should.

A reader and epistemic-model correctness test, not a benchmark game:
no player plays knowledge goals, so it is not in `ground_truth.GAMES`.
"""

import copy
import itertools
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(REPO, 'src'))

from ggp import dialect  # noqa: E402
from ggp.game import GGPGame  # noqa: E402

PATH = os.path.join(HERE, '..', 'identify', 'testgames',
                    'russiancards.gdl')

CARDS = range(7)
PLAYERS = ('alice', 'bob', 'cath')


def deals():
    for a in itertools.combinations(CARDS, 3):
        rest = [c for c in CARDS if c not in a]
        for b in itertools.combinations(rest, 3):
            (c,) = [x for x in rest if x not in b]
            yield a, b, c


def brute_force():
    """{(deal, alice's announcement, bob's): safe?} by enumerating the
    possible worlds after each public announcement, no GDL."""
    after_alice = [(d, m) for d in deals()
                   for m in [('sum', sum(d[0]) % 7), ('hand',) + d[0],
                             ('pass',)]]
    caths = {}
    for d, m in after_alice:
        caths.setdefault((d[1], m), set()).add(d[2])
    histories = [(d, m, b) for d, m in after_alice
                 for b in ['pass'] + ([('cath', d[2])]
                                      if len(caths[(d[1], m)]) == 1
                                      else [])]

    def own(role, deal):
        return deal[PLAYERS.index(role)]

    def owner(deal, x):
        return 'alice' if x in deal[0] else 'bob' if x in deal[1] \
            else 'cath'

    classes = {}
    for h in histories:
        for role in PLAYERS:
            classes.setdefault((role, own(role, h[0])) + h[1:],
                               []).append(h)

    def knows_owner(role, h, x):
        alike = classes[(role, own(role, h[0])) + h[1:]]
        return len({owner(o[0], x) for o in alike}) == 1

    return {h: (all(knows_owner(r, h, x)
                    for r in ('alice', 'bob') for x in CARDS)
                and not any(knows_owner('cath', h, x)
                            for x in CARDS if x != h[0][2]))
            for h in histories}


@pytest.fixture(scope='module')
def start():
    return GGPGame.from_file(PATH)


@pytest.fixture(scope='module')
def played(start):
    """Every complete play sequence: {brute-force key: goals}. One
    starting game is deep-copied, so all copies share its knowledge
    model and each play sequence is evaluated once."""
    noop = dict.fromkeys(start.roles, 'noop')
    out = {}
    for deal in start.legal_moves('random'):
        dealt = copy.deepcopy(start)
        dealt.step(dict(noop, random=deal))
        cards = tuple(int(x) for x in deal[1:])
        key_deal = (cards[0:3], cards[3:6], cards[6])
        for said in dealt.legal_moves('alice'):
            told = copy.deepcopy(dealt)
            told.step(dict(noop, alice=said))
            for reply in told.legal_moves('bob'):
                game = copy.deepcopy(told)
                game.step(dict(noop, bob=reply))
                assert game.is_terminal()
                a = (('pass',) if said[1] == 'pass' else
                     (said[1][0],) + tuple(int(x) for x in said[1][1:]))
                b = ('pass' if reply[1] == 'pass'
                     else ('cath', int(reply[1][1])))
                out[(key_deal, a, b)] = {r: game.goal(r)
                                         for r in game.roles}
    return out


def test_it_is_read_as_gdl_iii_with_140_deals(start):
    assert start.dialect == dialect.GDL_III
    assert len(start.legal_moves('random')) == 140 == len(list(deals()))


def test_the_safe_protocol_wins_on_every_deal(played):
    """Alice announces her sum modulo 7, Bob then announces Cath's
    card. Bob can always make that announcement: the sum tells him."""
    safe = {k: g for k, g in played.items()
            if k[1][0] == 'sum' and k[2] != 'pass'}
    assert len(safe) == 140
    assert all(g == {'alice': 100, 'bob': 100, 'cath': 0, 'random': 0}
               for g in safe.values())


def test_alice_announcing_her_hand_loses_on_every_deal(played):
    """Cath, holding one card and now told Alice's three, knows Bob's
    three too."""
    naive = {k: g for k, g in played.items() if k[1][0] == 'hand'}
    assert len(naive) == 280
    assert all(g['alice'] == g['bob'] == 0 and g['cath'] == 100
               for g in naive.values())


def test_the_brute_force_check_agrees_on_every_play_sequence(played):
    brute = brute_force()
    assert len(brute) == 700
    assert set(played) == set(brute)
    assert {k: g['alice'] == 100 for k, g in played.items()} == brute
    # And the agreement is not vacuous: both outcomes occur.
    assert set(brute.values()) == {True, False}


def test_bob_may_name_cath_card_only_when_he_knows_it(start):
    """After 'my hand is 0,1,2', Bob holding 3,4,5 knows Cath holds 6.
    Before any announcement he holds the same cards and cannot know."""
    noop = dict.fromkeys(start.roles, 'noop')
    game = copy.deepcopy(start)
    game.step(dict(noop, random=('deal',) + tuple('0123456')))
    assert not game.knows('bob', ('owns', 'cath', '6'))
    game.step(dict(noop, alice=('announce', ('hand', '0', '1', '2'))))
    assert game.knows('bob', ('owns', 'cath', '6'))
    assert ('announce', ('cath', '6')) in game.legal_moves('bob')


def test_after_alice_passes_bob_cannot_name_cath_card(start):
    """The guard that makes Bob's announcement knowledge, not just
    truth: Cath holds 6, but Bob sees four cards he does not hold."""
    noop = dict.fromkeys(start.roles, 'noop')
    game = copy.deepcopy(start)
    game.step(dict(noop, random=('deal',) + tuple('0123456')))
    game.step(dict(noop, alice=('announce', 'pass')))
    assert not game.knows('bob', ('owns', 'cath', '6'))
    assert game.legal_moves('bob') == [('announce', 'pass')]


def test_after_the_sum_cath_still_cannot_place_any_card(start):
    noop = dict.fromkeys(start.roles, 'noop')
    game = copy.deepcopy(start)
    game.step(dict(noop, random=('deal',) + tuple('0123456')))
    game.step(dict(noop, alice=('announce', ('sum', '3'))))
    assert game.knows('bob', ('owns', 'cath', '6'))
    for x in '012345':
        assert not game.knows('cath', ('owns', 'alice', x))
        assert not game.knows('cath', ('owns', 'bob', x))
