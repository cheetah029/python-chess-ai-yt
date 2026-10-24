"""The acceptance test: hand it a GDL it has never seen.

A reviewer put it plainly -- the way to know the framework is general
is that the player is COMPETENT on a game given only its rules. Every
other check is a proxy, including the twenty-eight in the generality
audit, which say what a module may not contain rather than what the
agent can do.

So these tests train from zero on GDL files that no extractor was
written for, with every feature named from those files' own relations,
and measure the result against a uniform mover.

WHAT THIS ALREADY FOUND, which is the argument for having it:

  - `differentials` excludes neutral owners, correctly, because a piece
    belonging to nobody scored against the mover is a constant dressed
    as a feature. But nim's ENTIRE state is `pile(5)`, which belongs to
    nobody -- so the learner got one usable feature and the agent lost
    to random 28-92. Shared quantities now belong to the side to move,
    which keeps the evaluation antisymmetric and makes the meaning
    right.
  - at a TERMINAL state every role is left holding an idle move, so
    "who is to move" fell through to `roles[0]` -- right half the time,
    and `search._leaf` scores a finished position as
    `winner == current_player`. Half of all terminal positions were
    read with the sign inverted. On nim, where every line ends within
    five plies, that is most of the tree: 35% against a uniform mover
    before the fix, 91.7% after, with the same weights.

Neither was reachable from the case study or from m,n,k, because both
of those hand the agent a hand-written extractor and a real
`current_player`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

import pytest

from lgref.experiments.gdl import GdlGame, features, load

GAMES = os.path.join(os.path.dirname(__file__), '..', 'identify',
                     'testgames')


def _path(name):
    return os.path.join(GAMES, name + '.gdl')


@pytest.mark.parametrize('name', ['nim', 'corridor', 'tictactoe'])
def test_a_gdl_file_is_playable_through_the_ordinary_protocol(name):
    """One adapter per DIALECT, not per game. Nothing below knows what
    any of these games is."""
    game = load(_path(name), max_turns=60)
    assert len(game.roles) >= 2
    assert game.current_player in game.roles
    turns = game.get_all_legal_turns()
    assert turns, 'no legal turn in the initial state'
    plies = 0
    while not game.is_game_over() and plies < 60:
        here = game.get_all_legal_turns()
        if not here:
            break
        game.execute_turn(here[0])
        plies += 1
    assert plies > 0
    assert game.winner is None or game.winner in game.roles


@pytest.mark.parametrize('name', ['nim', 'corridor'])
def test_every_feature_name_comes_from_the_games_own_relations(name):
    """NO NAME IS SUPPLIED. `pile`, `control`, `at`, `fresh` are the
    GDL's own symbols; the only things this module adds are the `@index`
    and `is`/`=` markers that say which argument a number or a constant
    came from."""
    with open(_path(name)) as handle:
        text = handle.read()
    game = load(_path(name), max_turns=60)
    for _owner, feature in features(game):
        relation = feature.split('@')[0]
        assert relation in text, (
            '{0!r} is not a relation of {1}.gdl, so it was invented '
            'somewhere'.format(relation, name))


def test_a_shared_quantity_is_attributed_to_the_side_to_move():
    """Nim's whole state belongs to nobody, and `differentials` drops
    neutral owners -- so without this the learner sees one feature and
    the agent loses to a uniform mover."""
    game = load(_path('nim'), max_turns=60)
    owners = dict(((owner, name), value)
                  for (owner, name), value in features(game).items())
    pile = [(owner, name) for (owner, name) in owners
            if name.startswith('pile')]
    assert pile, owners
    for owner, _name in pile:
        assert owner in game.roles, (
            'the pile is owned by {0!r}, which differentials will '
            'drop'.format(owner))


def test_reading_a_state_from_the_other_side_negates_it():
    """TD's whole value identity is `1 - sigma(w.x) == sigma(w.-x)`, so
    the features have to be antisymmetric in the perspective. A shared
    quantity attributed to a FIXED role would break that silently."""
    from lgref.experiments.discover import differentials

    game = load(_path('corridor'), max_turns=60)
    raw = features(game)
    first, second = game.roles[0], game.roles[1]
    mine = differentials(raw, first)
    theirs = differentials(raw, second)
    assert mine, 'no features survived differencing'
    for name, value in mine.items():
        assert theirs.get(name, 0) == -value, (name, value,
                                               theirs.get(name))


def test_a_number_in_a_fluent_is_read_both_ways():
    """A magnitude orders positions; an indicator does not. Nim is
    decided by the pile's PARITY, which no linear weight on its size can
    represent, so both readings are offered and the learner chooses."""
    game = load(_path('nim'), max_turns=60)
    names = set(name for _owner, name in features(game))
    assert 'pile@0' in names, names          # the magnitude
    assert any(name.startswith('pile@0is') for name in names), names


def test_the_player_to_move_is_still_known_at_a_terminal_state():
    """THE SIGN BUG. At a terminal state every role holds nothing but an
    idle move, so the first rule falls through -- and `search._leaf`
    reads a finished position as `winner == current_player`.

    The turn marker is found by SHAPE: a relation true of exactly one
    role. Nothing depends on it being spelled `control`.
    """
    game = load(_path('nim'), max_turns=60)
    seen = []
    while not game.is_game_over():
        turns = game.get_all_legal_turns()
        if not turns:
            break
        seen.append(game.current_player)
        game.execute_turn(turns[0])
    assert game.is_game_over()
    assert game.current_player in game.roles
    # The mover alternates, so the role to move at the end is determined
    # by the number of plies -- not by whichever role happens to be
    # first in the list.
    expected = game.roles[0] if len(seen) % 2 == 0 else game.roles[1]
    ordered = [seen[0], [r for r in game.roles if r != seen[0]][0]]
    expected = ordered[len(seen) % 2]
    assert game.current_player == expected, (
        'at the terminal state the mover reads as {0}, but {1} plies '
        'were played starting with {2}'.format(game.current_player,
                                               len(seen), seen[0]))


def test_the_turn_marker_is_found_by_shape_not_by_its_name():
    class _Fake(object):
        roles = ['alice', 'bob']
        state = {('whose_move', 'bob'), ('score', 'alice', '3')}

    game = GdlGame.__new__(GdlGame)
    game.roles = _Fake.roles
    game.ggp = _Fake()
    assert game._turn_marker() == 'bob'


def _train_and_race(name, cap=40, rounds=4, per_round=30, games=40,
                    depth=4):
    """Train from zero on a GDL, then play BOTH the learned evaluation
    and a FLAT one against a uniform mover, through the same search.

    THE FLAT ROW IS THE CONTROL AND IT IS NOT OPTIONAL. A depth-4 search
    reads terminal states directly, so on a small game it already beats
    a uniform mover with an evaluation of all zeros -- measured at 82.5%
    on nim and 81.2% on corridor. "The agent wins 81%" therefore says
    almost nothing about whether anything was learned, and I reported
    exactly that number as though it did.

    The quantity that means something is the DIFFERENCE.
    """
    import random

    from lgref.experiments.bootstrap import normalise, run, value
    from lgref.experiments.discover import differentials
    from lgref.experiments.search import Searcher

    def make(_variant='full', max_turns=None):
        return load(_path(name), max_turns=max_turns or cap)

    scales = {}
    history = run(make, features, rounds=rounds, games_per_round=per_round,
                  alpha=0.08, epsilon=0.3, seed=11, max_turns=cap,
                  scales=scales)
    weights = history[-1].weights

    def rate_for(table):
        def evaluate(game, perspective):
            return value(table, normalise(
                differentials(features(game), perspective), dict(scales),
                update=False))

        wins = losses = 0
        for index in range(games):
            game = make()
            rng = random.Random(900 + index)
            mine = game.roles[index % len(game.roles)]
            plies = 0
            while not game.is_game_over() and plies < cap:
                turns = game.get_all_legal_turns()
                if not turns:
                    break
                if game.current_player == mine:
                    searcher = Searcher(evaluate, max_depth=depth,
                                        budget=5.0, quiescence=0,
                                        use_tt=False)
                    chosen = searcher.choose_turn(turns, game)
                else:
                    chosen = rng.choice(turns)
                game.execute_turn(chosen)
                plies += 1
            if game.winner == mine:
                wins += 1
            elif game.winner is not None:
                losses += 1
        decided = wins + losses
        return (wins / float(decided)) if decided else 0.0, decided

    flat, decided = rate_for(dict((key, 0.0) for key in weights))
    learned, _decided = rate_for(weights)
    return weights, flat, learned, decided


@pytest.mark.slow
@pytest.mark.parametrize('name,floor', [('corridor', 0.65), ('nim', 0.70)])
def test_the_agent_is_competent_on_a_game_it_was_never_written_for(name,
                                                                   floor):
    """THE ACCEPTANCE TEST ITSELF.

    Floors set well under what was measured -- corridor 82.5%, nim 90%
    -- because the point is to catch a COLLAPSE, not to pin a number
    that drifts with the seed.
    """
    weights, _flat, learned, decided = _train_and_race(name)
    assert len(weights) > 1, (
        'only {0} feature(s) were learned, so nothing can be '
        'evaluated'.format(len(weights)))
    assert decided > 10, 'too few decided games to mean anything'
    assert learned >= floor, (
        'on {0}, a game nothing here was written for, the agent scored '
        '{1:.1%} against a uniform mover'.format(name, learned))


@pytest.mark.slow
def test_the_learning_contributes_something_over_a_flat_evaluation():
    """THE CONTROL, and the reason it exists.

    A depth-4 search with all-zero weights scores 82.5% on nim and
    81.2% on corridor against a uniform mover, because it reads
    terminal states directly. So the headline win rate is mostly the
    SEARCH, and quoting it as evidence that the learner works -- which
    I did -- is the same error as quoting a blunder rate without its
    floor.

    THE SIGN IS NOT ESTABLISHED AND THIS TEST DOES NOT ASSERT ONE.
    Two configurations disagree: at 200 training games and 80 evaluation
    games the learned evaluation beat flat 90.0% to 82.5%, and at 120
    and 40 it LOST, 77.5% to 95.0%. Both samples are small enough that
    one standard error is six to eight points, so the honest reading is
    that the difference is not resolved.

    There is also a reason to expect flat to do well here: on a game
    small enough that a depth-4 search reaches terminal states, a flat
    evaluation plays near-perfectly and any evaluation ERROR can only
    degrade it. The learner earns its place where the horizon bites,
    which these games do not have.

    So this asserts a COLLAPSE GUARD -- the learned evaluation must not
    be dramatically worse than no evaluation at all -- and records the
    comparison for a measurement with enough games to settle it.
    """
    _weights, flat, learned, _decided = _train_and_race('nim')
    assert learned > flat - 0.30, (
        'the learned evaluation scored {0:.1%} against the flat '
        'evaluation\'s {1:.1%}: learning is actively destroying a '
        'search that could already see the end of the game'.format(
            learned, flat))


def test_a_constant_that_discriminates_roles_is_bound_to_one():
    """Tic-tac-toe's roles are `xplayer` and `oplayer` and its marks are
    `x` and `o`, so no `cell` fluent names a role -- and before this the
    whole board was attributed to the side to move, which flips every
    ply. Measured: the learned evaluation scored 60.9% optimal against a
    flat evaluation's 60.9%. It contributed nothing at all.
    """
    from lgref.experiments.gdl import infer_ownership

    bound = infer_ownership(lambda: load(_path('tictactoe'),
                                         max_turns=30),
                            games=8, plies=30, seed=1)
    assert bound == {'x': 'xplayer', 'o': 'oplayer'}, bound


@pytest.mark.parametrize('name', ['nim', 'corridor'])
def test_a_constant_only_one_role_happens_to_produce_is_not_bound(name):
    """UNANIMITY IS NOT ENOUGH, and this is the case that proves it.

    Nim starts at five with `first` to move, so a pile of FOUR is only
    ever produced by first -- true, and nothing to do with ownership.
    Corridor starts white on square 0, so squares 1 and 2 are only ever
    reached by white. Both were bound under a unanimity rule, and both
    were STABLE at eight, forty and a hundred and fifty games, so more
    data would never have removed them.

    The partition rule rejects them: a constant binds only when every
    role writing that slot uses its own constants and no other role's.
    """
    from lgref.experiments.gdl import infer_ownership

    bound = infer_ownership(lambda: load(_path(name), max_turns=40),
                            games=20, plies=40, seed=1)
    assert bound == {}, (
        '{0} bound {1}, which is a fact about its opening rather than '
        'about ownership'.format(name, bound))


def test_a_bound_constant_changes_who_owns_the_fluent():
    """The inference is only worth having if `features` consults it."""
    from lgref.experiments.gdl import features as gdl_features

    game = load(_path('tictactoe'), max_turns=30)
    game.execute_turn(game.get_all_legal_turns()[0])
    plain = gdl_features(game)
    bound = gdl_features(game, ownership={'x': 'xplayer', 'o': 'oplayer'})
    marks = [(owner, name) for (owner, name) in bound
             if name.endswith('=x')]
    assert marks, bound
    for owner, _name in marks:
        assert owner == 'xplayer'
    assert plain != bound, 'the ownership map changed nothing'


def test_the_move_list_is_in_a_stable_order_across_processes():
    """A GDL state is a SET and the resolver walks it, so the move order
    depended on the hash seed -- which made every measurement on this
    path irreproducible. Two identical comparisons sampled 46 and 53
    positions, and I read the difference as an effect for a while.
    """
    import subprocess
    import sys as _sys

    script = (
        'import sys; sys.path[:0] = [".", "src"];'
        'from lgref.experiments.gdl import load;'
        'g = load("lgref/identify/testgames/tictactoe.gdl",'
        ' max_turns=20);'
        'print([t[1] for t in g.get_all_legal_turns()])')
    root = os.path.join(os.path.dirname(__file__), '..', '..')
    seen = set()
    for seed in ('0', '1', '2'):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run([_sys.executable, '-c', script], cwd=root,
                             stdout=subprocess.PIPE, env=env,
                             timeout=180)
        seen.add(out.stdout.decode('utf-8').strip())
    assert len(seen) == 1, (
        'the move order differs between hash seeds, so nothing measured '
        'on this path reproduces: {0}'.format(seen))


def test_the_games_own_derived_relations_are_discoverable():
    """`line`, `row`, `column`, `diagonal`, `open` -- the concepts the
    game's author named. Discovering them is cheap and correct; what it
    does NOT do is close the gap to the hand-written extractor, and the
    reason is recorded in `derived_relations`."""
    from lgref.experiments.gdl import derived_relations

    game = load(_path('tictactoe'), max_turns=20)
    found = dict(derived_relations(game))
    for expected in ('line', 'row', 'column', 'diagonal'):
        assert expected in found, found
    for keyword in ('legal', 'next', 'goal', 'terminal', 'role'):
        assert keyword not in found, (
            '{0} is part of the DIALECT, not a concept this game '
            'named'.format(keyword))


def test_derived_relations_are_off_until_they_earn_their_place():
    """MEASURED AND NOT KEPT ON. Switching them on moved the
    optimal-action rate from 69.4% to 67.3%, so they are available and
    not default. A feature that costs a resolver query per evaluation
    has to pay for itself."""
    import inspect

    from lgref.experiments import gdl

    signature = inspect.signature(gdl.features)
    assert signature.parameters['derived'].default is False


def test_partial_satisfaction_is_counted_but_never_ranked():
    """THE CONSTRAINT A REVIEWER SET, and it shaped the design.

    A game's declared outcome separates NONE from SOME: `line(x)` holds
    or it does not, and nothing in it says two-of-three beats
    one-of-three. Reading an ordering into partial satisfaction is the
    same error as deciding two royals must beat one, which this project
    has already made and measured.

    So each level is its OWN feature with no ordering, no sign and no
    combination into a single "progress" number -- a single number would
    BE the assumption. The learner may price `line~2` highly and
    `line~1` at zero, or both at zero, which is the honest answer on a
    game where partial satisfaction means nothing.
    """
    from lgref.experiments import gdl

    # CHECKED BEHAVIOURALLY, not by grepping the source -- the first
    # version of this test searched for the word "progress" and matched
    # its OWN docstring, which argues against using one.
    game = load(_path('tictactoe'), max_turns=20)
    for _ply in range(4):
        game.execute_turn(game.get_all_legal_turns()[0])
    counts = gdl.relaxations(game, {'x': 'xplayer', 'o': 'oplayer'})
    levels = sorted(set(name for _owner, name in counts
                        if name.startswith('line')))
    assert levels == ['line/1', 'line/2', 'line/3',
                      'line~1', 'line~2', 'line~3'], levels
    # NO SINGLE ORDERED QUANTITY. If one of these were a combined
    # "progress" number the levels would collapse to one feature, and
    # the ordering between them would be this module's opinion rather
    # than the learner's finding.
    assert len(levels) > 2, levels
    # The levels carry no implied sign either: every count here is a
    # plain tally, so a learner is free to price any of them at zero.
    for (_owner, name), value in counts.items():
        if name.startswith('line'):
            assert value >= 0, (name, value)


def test_a_blocked_conjunct_needs_a_RIVAL_not_just_a_difference():
    """Tic-tac-toe fills every square from the start -- `cell(1,2,b)` --
    so "occupied by a different value" is true of every EMPTY square,
    and the first version of this check marked every line dead.

    What makes a block real is that the occupying value belongs to
    ANOTHER ROLE, which `infer_ownership` already learns. `b` is bound
    to nobody and blocks nothing. No list of blank markers anywhere.
    """
    from lgref.experiments import gdl

    game = load(_path('tictactoe'), max_turns=20)
    for _ply in range(4):
        game.execute_turn(game.get_all_legal_turns()[0])
    counts = gdl.relaxations(game, {'x': 'xplayer', 'o': 'oplayer'})
    reachable = sum(value for (_owner, name), value in counts.items()
                    if name.startswith('line~'))
    assert reachable > 0, (
        'every line reads as blocked, so the blank marker is being '
        'treated as a rival')


def test_a_disjunction_inherits_its_disjuncts_counts():
    """`line(W) :- row(M,W)` and `:- column(N,W)` and `:- diagonal(W)`.
    The GDL is saying these are one concept, so splitting them leaves
    each feature a third of the data. The aggregation is READ from the
    rules: a body that is a single non-state literal is a renaming."""
    from lgref.experiments import gdl

    game = load(_path('tictactoe'), max_turns=20)
    for _ply in range(4):
        game.execute_turn(game.get_all_legal_turns()[0])
    counts = gdl.relaxations(game, {'x': 'xplayer', 'o': 'oplayer'})
    for level in ('~1', '~2'):
        parts = sum(counts.get(('xplayer', part + level), 0)
                    for part in ('row', 'column', 'diagonal'))
        whole = counts.get(('xplayer', 'line' + level), 0)
        assert whole == parts, (level, whole, parts)


def test_an_absent_level_reads_as_zero():
    """`differentials` omits a feature nobody holds, so a weight for
    "two of this line are mine" would be fitted only on positions where
    somebody already has two -- never on the ones where the count is
    what distinguishes the sides. `features.mnk` sets the same zeros for
    the same reason."""
    from lgref.experiments import gdl

    game = load(_path('tictactoe'), max_turns=20)
    counts = gdl.relaxations(game, {'x': 'xplayer', 'o': 'oplayer'})
    for role in ('xplayer', 'oplayer'):
        for level in (1, 2, 3):
            assert ('line~{0}'.format(level)) in [
                name for owner, name in counts if owner == role], (
                    role, level, sorted(counts))


def test_narrowing_the_fact_index_changes_no_answer():
    """THE INDEX NARROWS, IT DOES NOT DECIDE.

    Every state fact is `true(something)`, so indexing by predicate
    alone left every state fact a candidate for every `true` goal --
    4.2 million unifications in one legal-move query on the case study.
    The second-level index keys on the inner head, which is sound
    because a fact whose inner head differs from the goal's cannot
    unify with it: both are ground constants in that position.

    Sound is not the same as correct-in-practice, so this checks the
    narrowed set against the flat one directly.
    """
    from ggp.kb import KnowledgeBase

    kb = KnowledgeBase()
    for form in (('true', ('cell', '1', '1', 'x')),
                 ('true', ('cell', '1', '2', 'o')),
                 ('true', ('control', 'xplayer')),
                 ('true', ('pile', '5'))):
        kb.add_clause(form)

    # A goal with a ground inner head sees only its own relation...
    narrowed = kb.candidate_facts(('true', ('cell', '?m', '?n', '?w')))
    assert len(narrowed) == 2, narrowed
    assert all(f[1][0] == 'cell' for f in narrowed)
    # ...and every one of them is in the flat list.
    flat = kb.facts_for('true')
    assert all(f in flat for f in narrowed)
    # A relation with no facts narrows to nothing rather than to
    # everything.
    assert kb.candidate_facts(('true', ('nothing', '?x'))) == []
    # A goal whose argument is a VARIABLE cannot be narrowed, so it
    # must see the whole list.
    assert len(kb.candidate_facts(('true', '?anything'))) == len(flat)


def test_the_case_study_gdl_still_agrees_with_its_engine():
    """71 legal turns in the initial position, from two independent
    implementations. This is the check that a resolver optimisation
    cannot be allowed to break."""
    import os as _os
    import sys as _sys

    root = _os.path.join(_os.path.dirname(__file__), '..', '..')
    if root not in _sys.path:
        _sys.path.insert(0, root)
    from experiments.variants import make_engine

    gdl = load(_os.path.join(root, 'docs', 'gdl', 'integrated.gdl'),
               max_turns=200)
    engine = make_engine('full', max_turns=400)
    assert len(gdl.get_all_legal_turns()) == \
        len(engine.get_all_legal_turns())


def test_legal_moves_are_cached_per_state_not_across_moves():
    """The cache is keyed on the state itself and rebuilt rather than
    invalidated, so a stale entry is not expressible."""
    game = load(_path('tictactoe'), max_turns=20)
    first = game.get_all_legal_turns()
    assert game.get_all_legal_turns() == first
    game.execute_turn(first[0])
    assert len(game.get_all_legal_turns()) == len(first) - 1
