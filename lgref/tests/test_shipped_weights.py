"""Guards on the SHIPPED weights, for the case study specifically.

DOMAIN-SPECIFIC ON PURPOSE, and separated from the generality audit for
that reason. These assert properties of one artifact for one game; they
are not inputs to learning and nothing here is supplied to the learner.
A different game would need its own file, or none.

Every check corresponds to a blunder a human found by playing, after an
aggregate statistic had said the agent was fine:

  - it gave away bishops, because `Bishop` was -0.0077 while `Pawn` was
    +0.0501, so "lose a bishop, win a pawn" scored +0.047, A GAIN.
  - it gave away knights, because `Knight` fell to 1.3 pawns and the
    same trade came to -0.0045, which is free.
  - it captured its OWN pieces, because the capture ranker scored the
    destination occupant by `abs(weight)` without asking whose it was.

The material harness missed all three. It samples random positions and
scores two plies of material, and none of these are visible that way.

A PIECE IS PRICED BY TAKING IT OFF THE BOARD, not by reading a weight,
and that change is the most important thing in this file. These guards
used to compare two weight names -- `learned['Bishop']` against
`learned['Pawn']` -- and that comparison is invalid here, because the
columns are collinear. A queen may take the form of a piece type only
once a friendly piece of that type has been captured, so "bishops I
hold" and "bishop form available to me" are near-complements:
R-squared 0.98 on each other, measured by `replicate.shared_variance`.
The learner only ever sees their sum and splits it arbitrarily.

So the old guards were comparing one arbitrary half of a split pair
against a whole, and they passed a shipped evaluation whose reported
bishop was 1.1 pawns while its actual charge for losing a bishop was
1.6. A reviewer said 1.1 could not be right. They were right that it
was wrong, and wrong about which number was broken.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

WEIGHTS = os.path.join(os.path.dirname(__file__), '..', 'weights',
                       'td_royal_chess.json')

#: Pieces that are worth more than a pawn in this variant. NOT supplied
#: to anything -- this file reads the learned weights and complains. The
#: claim is weak on purpose: a rook sweeps the board, a knight moves to
#: any of sixteen squares and can be invulnerable, a bishop teleports
#: anywhere safe and pins what it sees. Each does more than step one
#: square forward, so each should price above the piece that does.
STRONGER_THAN_A_PAWN = ('Rook', 'Knight', 'Bishop', 'Queen', 'King')


def _remove(game, label, rng):
    """Take one of the mover's pieces of type `label` off the board.

    RECORDED AS CAPTURED rather than deleted, because in this game a
    queen's available forms depend on which friendly types have been
    captured -- so a piece that never existed is a different position
    from a piece that was traded, and the trade is what is being priced.
    """
    board = game.board
    mover = game.current_player
    found = []
    for row in range(len(board.squares)):
        for col in range(len(board.squares[row])):
            piece = board.squares[row][col].piece
            if (piece is not None and type(piece).__name__ == label
                    and getattr(piece, 'color', None) == mover):
                found.append((row, col, piece))
    if not found:
        return False
    row, col, piece = rng.choice(found)
    board.squares[row][col].piece = None
    name = getattr(piece, 'name', label.lower())
    if mover in board.captured_pieces:
        board.captured_pieces[mover].append(name)
    return True


@pytest.fixture(scope='module')
def prices():
    """What the shipped evaluation charges for losing one of each piece,
    measured on real positions with every column that moves included."""
    from experiments.variants import make_engine

    from lgref.experiments.bootstrap import normalise
    from lgref.experiments.discover import differentials
    from lgref.experiments.features import load_royal_chess_searcher
    from lgref.experiments.legacy import royal_chess as legacy
    from lgref.experiments.validate import removal_price

    payload = json.load(open(WEIGHTS))
    weights, scales = payload['weights'], payload.get('scales', {})
    # The loader is called so that a payload the agent could not play
    # fails here too, rather than only in the game.
    load_royal_chess_searcher(WEIGHTS, budget=1.0, max_depth=1)

    def columns_of(game, perspective):
        return normalise(differentials(legacy(game), perspective),
                         dict(scales), update=False)

    return removal_price(lambda: make_engine('full', max_turns=400),
                         columns_of, weights, _remove,
                         ('Pawn',) + STRONGER_THAN_A_PAWN,
                         trials=24, seed=9)


def test_every_piece_is_worth_something(prices):
    """A NEGATIVE piece value is how the bishops were given away.

    `Bishop` was -0.0077: the evaluation preferred not having one. No
    piece in this game is a liability -- the worst case is that it does
    nothing, which is zero.
    """
    for name in ('Pawn',) + STRONGER_THAN_A_PAWN:
        price, samples = prices[name]
        assert samples > 0, 'no position priced a {0}'.format(name)
        assert price > 0.0, (
            'losing a {0} is scored at {1:+.4f}; a negative price means '
            'the agent will give it away for free'.format(name, price))


def test_trading_a_piece_for_a_pawn_is_never_a_gain(prices):
    """The reported blunder, asked directly.

    In the game that prompted this, `5. Pe2-e3` attacked a knight on e4
    and the agent played elsewhere; `6. Pe3xe4` took it and the pawn was
    recaptured. Net: a knight for a pawn. If the evaluation scores that
    as positive, the agent is not blundering, it is obeying.

    Checked by SIGN rather than by a margin, because a margin would be a
    number I made up. The sign is the property that matters: losing more
    than you gain must not read as a gain.
    """
    pawn = prices['Pawn'][0]
    for name in STRONGER_THAN_A_PAWN:
        trade = -prices[name][0] + pawn
        assert trade < 0.0, (
            'giving up a {0} for a pawn scores {1:+.4f}; the agent will '
            'do it'.format(name, trade))


def test_the_pawn_is_not_the_most_valuable_thing_on_the_board(prices):
    """A sanity bound that would have caught the compressed scale.

    When `Knight` fell to 1.3 pawns and `Bishop` to 1.0, every capture
    ranked alike -- which cost strength AND speed, since move ordering
    collapsed and the tree doubled (8916 nodes against 4424 in the early
    game).
    """
    pawn = prices['Pawn'][0]
    assert pawn > 0.0
    for name in STRONGER_THAN_A_PAWN:
        assert prices[name][0] > pawn, (
            '{0} at {1:.1f} pawns'.format(name, prices[name][0] / pawn))


def test_a_royal_is_the_most_expensive_piece_on_the_board(prices):
    """Losing a royal is half the loss condition; nothing else is.

    This is the guard that caught a king priced at +0.0165 against a
    knight's +0.0423 -- a king-for-knight trade read as a gain, which a
    human duly hit.
    """
    royal = min(prices['King'][0], prices['Queen'][0])
    for name in ('Pawn', 'Knight', 'Bishop', 'Rook'):
        assert prices[name][0] < royal, (
            '{0} is priced at or above a royal'.format(name))


def test_a_self_capture_ranks_below_a_quiet_move():
    """Only the king may take a friendly piece (RULEBOOK.md). The ranker
    scored the destination occupant by `abs(weight)` without asking
    whose it was, so "king takes own rook" was the top-ranked move on
    the board -- 124 of them across 40 positions, every one at 0.3952.
    """
    from experiments.variants import make_engine

    from lgref.experiments.features import capture_ranker
    from lgref.experiments.random_play import build

    payload = json.load(open(WEIGHTS))
    rank = capture_ranker(payload['weights'], payload.get('scales', {}))

    found = 0
    for seed in range(12):
        engine = make_engine('full', max_turns=400)
        mover = build('random', random.Random(seed), 0)
        for _ply in range(random.Random(seed).randint(10, 60)):
            turns = engine.get_all_legal_turns()
            if not turns or engine.is_game_over():
                break
            engine.execute_turn(mover.choose_turn(turns, engine))
        side = engine.current_player
        for turn in engine.get_all_legal_turns():
            target = getattr(turn, 'to_sq', None)
            if not getattr(turn, 'is_capture', False) or target is None:
                continue
            victim = engine.board.squares[target[0]][target[1]].piece
            if victim is None or getattr(victim, 'color', None) != side:
                continue
            found += 1
            assert rank(engine, turn) < 0.0, (
                'a self-capture ranked {0:+.4f}, at or above a quiet '
                'move'.format(rank(engine, turn)))
    assert found > 10, 'too few self-captures seen to mean anything'


def test_the_shipped_weights_load_and_choose_a_move():
    """The end-to-end check that was missing while the staleness guard
    fired five times in one session."""
    from experiments.variants import make_engine

    from lgref.experiments.features import load_royal_chess_searcher
    from lgref.experiments.random_play import build

    engine = make_engine('full', max_turns=400)
    mover = build('random', random.Random(1), 0)
    for _ply in range(30):
        turns = engine.get_all_legal_turns()
        if not turns or engine.is_game_over():
            break
        engine.execute_turn(mover.choose_turn(turns, engine))
    searcher = load_royal_chess_searcher(WEIGHTS, budget=30.0,
                                         max_depth=2)
    turns = engine.get_all_legal_turns()
    assert searcher.choose_turn(turns, engine) in turns


def test_a_weight_name_is_not_a_price_and_the_pairs_prove_it():
    """The methodological guard, and the reason this file was rewritten.

    If someone goes back to comparing `learned['Bishop']` against
    `learned['Pawn']`, this fails and says why: the column has a
    near-complement, so the name carries only part of the price. The
    threshold is deliberately loose -- the claim is "these two columns
    are mostly the same information", not a particular number.
    """
    from experiments.variants import make_engine

    from lgref.experiments.discover import differentials
    from lgref.experiments.legacy import royal_chess as legacy
    from lgref.experiments.random_play import build
    from lgref.experiments.replicate import shared_variance

    vectors = []
    for trial in range(4):
        game = make_engine('full', max_turns=400)
        mover = build('random', random.Random(trial), 0)
        for _ply in range(90):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(mover.choose_turn(turns, game))
            vectors.append(differentials(legacy(game),
                                         game.current_player))
    explained = shared_variance(vectors)
    for name in ('Bishop', 'Rook', 'Knight'):
        assert explained[name] > 0.7, (
            '{0} is only {1:.2f} explained by the other columns; if that '
            'is really so, a weight name may be read as a price again -- '
            'but check `removal_price` first'.format(name,
                                                     explained[name]))


def test_every_shipped_version_is_kept_and_the_index_matches():
    """AN ARCHIVE THAT GOES STALE IS WORSE THAN NONE, because it reads
    as a complete record while missing the version you want.

    Every set of weights that was ever shipped must have its payload in
    `lgref/weights/archive/`, so any of them can be put back with a
    copy. Checked against git rather than against a list someone
    maintains.

    Keyed on the PAYLOAD, not on the commit that shipped it. Those come
    apart in exactly the case that matters: a revert ships a payload
    that is already archived under the name of the commit it came from,
    and a check that wanted a file per commit would report the revert as
    an unrestorable version while the bytes sat in the archive. What has
    to be true is that every version can be RESTORED, and that is a
    statement about content.
    """
    import glob
    import hashlib
    import subprocess

    root = os.path.join(os.path.dirname(__file__), '..', '..')
    archive = os.path.join(os.path.dirname(__file__), '..', 'weights',
                           'archive')
    log = subprocess.run(
        ['git', 'log', '--format=%H', '--',
         'lgref/weights/td_royal_chess.json'],
        cwd=root, stdout=subprocess.PIPE, timeout=120)
    commits = [line.strip() for line in
               log.stdout.decode().strip().splitlines() if line.strip()]
    assert commits, 'no history for the shipped weights'

    kept = {}
    for path in glob.glob(os.path.join(archive, '*.json')):
        digest = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        kept[digest] = os.path.basename(path)

    missing = []
    for commit in commits:
        blob = subprocess.run(
            ['git', 'show',
             '{0}:lgref/weights/td_royal_chess.json'.format(commit)],
            cwd=root, stdout=subprocess.PIPE, timeout=120)
        digest = hashlib.sha256(blob.stdout).hexdigest()
        if digest not in kept:
            missing.append('{0} (payload {1})'.format(commit[:8],
                                                      digest[:8]))
    assert not missing, (
        'these shipped versions are not archived, so they cannot be '
        'restored: {0}'.format(missing))
    assert os.path.exists(os.path.join(archive, 'INDEX.md'))


def test_an_archived_version_that_claims_to_load_actually_loads():
    """The index has a `loadable` column; it must not lie."""
    import glob

    from lgref.experiments.features import load_royal_chess_searcher
    from lgref.experiments.record import audit, fatal

    archive = os.path.join(os.path.dirname(__file__), '..', 'weights',
                           'archive')
    index = open(os.path.join(archive, 'INDEX.md')).read()
    checked = 0
    for path in sorted(glob.glob(os.path.join(archive, '*.json'))):
        name = os.path.basename(path)
        claims = '`{0}` |'.format(name) in index
        assert claims, '{0} is not listed in INDEX.md'.format(name)
        payload = json.load(open(path))
        if fatal(audit(payload)):
            continue
        load_royal_chess_searcher(path, budget=1.0, max_depth=1)
        checked += 1
    assert checked >= 5, (
        'only {0} archived versions were loadable; the archive is not '
        'serving its purpose'.format(checked))


def test_the_ship_gate_races_at_the_depth_the_agent_plays():
    """THE METHODOLOGICAL HOLE THAT SHIPPED A REGRESSION.

    Every race in this issue ran at depth 2 while the window plays at
    `Game.TD_DEPTH`. A change that helps at one depth can hurt at
    another -- this project has already measured deeper search
    AMPLIFYING an evaluation's flaw rather than correcting it, and has
    a reviewer position where depth 2 saved a bishop that depth 3 gave
    away.

    So a weight set raced at depth 2 and shipped for depth-3 play has
    not actually been gated. The race harness now defaults to the play
    depth, and this test keeps the two from drifting apart again.
    """
    import re

    here = os.path.dirname(__file__)
    harness = os.path.join(here, '..', '..', 'tools', 'race_agents.py')
    assert os.path.exists(harness), (
        'the ship gate is not in the repository, so it cannot be kept '
        'in step with the window it gates -- which is how a change '
        'raced at depth 2 came to be shipped for depth-3 play')
    text = open(harness).read()
    found = re.search(r"RACE_DEPTH['\"],\s*['\"](\d+)['\"]", text)
    assert found, 'the race harness no longer names a default depth'
    from game import Game

    assert int(found.group(1)) == Game.TD_DEPTH, (
        'the ship gate races at depth {0} while the window plays at '
        '{1}'.format(found.group(1), Game.TD_DEPTH))


def test_every_candidate_is_kept_including_the_ones_that_lost():
    """A failed candidate is evidence: it says what was tried and what
    it cost. More than one idea here was rejected only after a race
    that a weight table had made look good."""
    import glob

    archive = os.path.join(os.path.dirname(__file__), '..', 'weights',
                           'archive', 'candidates')
    assert os.path.isdir(archive), 'the candidate archive is gone'
    kept = glob.glob(os.path.join(archive, '*.json'))
    assert len(kept) > 20, (
        'only {0} candidates kept; the record is not being '
        'maintained'.format(len(kept)))
    assert os.path.exists(os.path.join(archive, 'README.md'))
