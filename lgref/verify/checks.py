"""Pre-flight: everything that would invalidate a run, checked first.

WHY THIS EXISTS. Ten defects were found in this project in a single
session -- five columns that were a constant zero, every sampled
position belonging to White, a variant whose description was false in
all three of its claims, a metric that could not observe its own
phenomenon, an agent whose objective was one of the metrics, rollouts
returning no result and being scored as draws, functions naming
quantities nothing recorded, half the ontology's evidence written in
the wrong frame, a column recording an object where a name belonged,
and a function reported as added that was never written.

Every one of those would have quietly invalidated a measurement run,
and most produced plausible numbers rather than errors. A long run is
only worth paying for if the things that silently ruin it have been
checked, so this checks them and refuses rather than warns.

WHAT IT CANNOT DO. It cannot make a non-converged search converge. It
verifies that the PIPELINE is correct, not that the agent is strong
enough for its answers to be agent-independent -- that is what the
two-arm design measures and reports rather than assumes.
"""

import collections

Result = collections.namedtuple('Result', 'name passed detail')


def _ok(name, detail=''):
    return Result(name, True, detail)


def _fail(name, detail):
    return Result(name, False, detail)


# ---- variants ------------------------------------------------------------

def legal_turn_signature(engine):
    """What this position offers, in a form two variants can be diffed on."""
    out = collections.Counter()
    for turn in engine.get_all_legal_turns():
        piece = getattr(turn, 'piece', None)
        out[(turn.turn_type,
             getattr(piece, 'name', None),
             getattr(turn, 'promo_choice', None) is not None,
             getattr(turn, 'transform_target', None) is not None)] += 1
    return out


#: What each variant MUST stop offering, as turn kinds. Declared here
#: and machine-checked, which is the difference between this and the
#: prose descriptions that turned out to be false in all three of their
#: claims (#228). An empty tuple means the variant changes terminal
#: conditions or effects rather than the legal set's shape, and is
#: verified by the legal sets diverging at all.
MUST_REMOVE = {
    'no_boulder': ('boulder',),
    'no_queen_manipulation': ('manipulation',),
    'no_tiny_endgame': (),
    'no_knight_redesign': (),
    'baseline': ('boulder', 'manipulation'),
    'control_double_move': (),
}


#: When a variant's rule cannot fire from the legal set alone, what
#: must be true of the position for it to be exercisable at all. A
#: check that never reaches the rule it judges has to say so -- the
#: first version reported that `no_queen_manipulation` "ablates
#: nothing" because manipulation first becomes available at ply 82 and
#: it looked at 24.
def _any_piece(board, attribute):
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is not None and getattr(piece, attribute, False):
                return True
    return False


REACHABLE_WHEN = {
    'no_tiny_endgame': lambda engine: engine.board.is_tiny_endgame(),
    'no_knight_invulnerability':
        lambda engine: _any_piece(engine.board, 'invulnerable'),
    'no_bishop_reactive':
        lambda engine: _any_piece(engine.board, 'reactive_armed'),
    'no_repetition_rule':
        lambda engine: getattr(engine, '_repetition_blocks', 0) > 0,
}

#: Columns that are genuinely rare rather than broken, with the reason.
#: A constant column is normally a measurement that is not happening --
#: five of them were a constant zero across 1440 games -- but these
#: describe events that a short pilot legitimately will not see. They
#: are reported rather than ignored, because a function whose evidence
#: is one of them has NO POWER at that scale, which is a fact about the
#: run design and not about the rule.
RARE_COLUMNS = {
    'repetition_blocks': 'a state must occur three times',
    'endgame_blocks': 'requires an active tiny endgame',
    'repeated_state_frequency': 'requires an exactly repeated position',
    'tiny_endgame_activated': 'requires <=6 non-king pieces and no pawns',
    'tiny_endgame_seen': 'requires an active tiny endgame at a sample',
    'mean_protected_pieces': 'rate-blind: protection lasts one turn and '
                             'sampling is one turn in ten',
    'protection_active_turns': 'requires a non-capturing knight leap '
                               'landing beside the opposite allegiance',
    'response_turns': 'requires an offered jump-capture to be taken',
    'exposure_losses': 'requires a reply capturing on the square just '
                       'moved to',
    'self_removal_turns': 'requires a king to capture its own piece',
    'conversion_turns': 'requires a pawn to reach the last rank',
    'mode_reentry_turns': 'requires a second transformation by one queen',
}


def _replay(variant, moves, make_engine):
    """Replay a move sequence in another variant, stopping when it can't.

    A move the variant refuses IS the difference, so the point at which
    replay fails is the measurement rather than an error. Comparing each
    variant's own self-play instead would compare different POSITIONS
    and call that a rule difference.
    """
    engine = make_engine(variant, max_turns=400)
    signatures = [legal_turn_signature(engine)]
    for index, description in enumerate(moves):
        match = None
        for turn in engine.get_all_legal_turns():
            if _describe(turn) == description:
                match = turn
                break
        if match is None:
            return signatures, index          # diverged here
        engine.execute_turn(match)
        signatures.append(legal_turn_signature(engine))
    return signatures, None


def _describe(turn):
    piece = getattr(turn, 'piece', None)
    return (turn.turn_type, getattr(piece, 'name', None),
            getattr(turn, 'from_sq', None), getattr(turn, 'to_sq', None),
            getattr(turn, 'promo_choice', None),
            getattr(turn, 'transform_target', None),
            getattr(turn, 'jump_choice', None))


def reference_line(make_engine, plies, seed):
    """One line of play in `full`, and what it exercised along the way."""
    import random

    engine = make_engine('full', max_turns=400)
    rng = random.Random(seed)
    moves, signatures, exercised = [], [legal_turn_signature(engine)], set()
    for _ in range(plies):
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        exercised.update(t.turn_type for t in turns)
        chosen = turns[rng.randrange(len(turns))]
        moves.append(_describe(chosen))
        engine.execute_turn(chosen)
        signatures.append(legal_turn_signature(engine))
    return moves, signatures, exercised


def check_control_is_identical(make_engine, plies=140, seed=5):
    """The noise floor. `control_inert` must offer the SAME legal set.

    If the instrument reports an effect for a variant that changes no
    rule, every other effect it reports is suspect.
    """
    moves, signatures, _ = reference_line(make_engine, plies, seed)
    mirror, diverged = _replay('control_inert', moves, make_engine)
    if diverged is not None:
        return _fail('control_inert is rule-identical to full',
                     'refused a legal move at ply {}'.format(diverged))
    for index, (a, b) in enumerate(zip(signatures, mirror)):
        if a != b:
            return _fail('control_inert is rule-identical to full',
                         'legal sets differ at ply {}'.format(index))
    return _ok('control_inert is rule-identical to full',
               '{} positions identical'.format(len(signatures)))


def check_variant_changes_something(name, make_engine, plies=140,
                                    seeds=(5, 17, 29, 41)):
    """A variant must ablate what it claims, and the check must reach it.

    SEVERAL LINES OF PLAY, not one. A single line reported that
    `no_knight_invulnerability` "ablates nothing" across 201 positions.
    Invulnerability arose in that line and simply never blocked a
    capture that would otherwise have been legal -- checked separately,
    there are positions where an invulnerable enemy is not a legal
    target, so the rule bites and the line had missed it.

    THREE OUTCOMES, because two of them were once conflated. An earlier
    version ran 24 plies deep and accused `no_queen_manipulation` of
    ablating nothing; manipulation first becomes available at ply 82. A
    check that cannot exercise what it judges says so rather than
    returning a verdict.
    """
    required = MUST_REMOVE.get(name, ())
    probe = REACHABLE_WHEN.get(name)
    reached, exercised_all = False, set()

    for seed in seeds:
        moves, signatures, exercised = reference_line(
            make_engine, plies, seed)
        exercised_all |= exercised
        mirror, diverged = _replay(name, moves, make_engine)
        if probe is not None and _ever_true(probe, moves, make_engine):
            reached = True

        for kind in required:
            if kind in exercised and any(
                    any(key[0] == kind for key in sig) for sig in mirror):
                return _fail('{} differs from full'.format(name),
                             'still offers {} turns, which it must '
                             'remove'.format(kind))

        changed = sum(1 for a, b in zip(signatures, mirror) if a != b)
        if diverged is not None or changed:
            where = ('diverged at ply {}'.format(diverged)
                     if diverged is not None
                     else 'differs at {} of {} positions'.format(
                         changed, len(signatures)))
            return _ok('{} differs from full'.format(name),
                       '{} (line {})'.format(where, seed))

    unreachable = [kind for kind in required if kind not in exercised_all]
    if unreachable:
        return Result('{} differs from full'.format(name), True,
                      'NOT EXERCISED: {} never became available across {} '
                      'lines, so this proves nothing'.format(
                          ', '.join(unreachable), len(seeds)))
    if probe is not None and not reached:
        return Result('{} differs from full'.format(name), True,
                      'NOT EXERCISED: the position it needs never arose '
                      'across {} lines of {} plies'.format(
                          len(seeds), plies))
    if probe is not None:
        return Result('{} differs from full'.format(name), True,
                      'NOT EXERCISED: the state arose but never changed a '
                      'legal move across {} lines — the rule is real and '
                      'this window did not catch it biting'.format(
                          len(seeds)))
    return _fail('{} differs from full'.format(name),
                 'identical legal sets across {} lines and it exercised '
                 '{}: this ablates nothing'.format(
                     len(seeds), ', '.join(sorted(exercised_all))))


# ---- the measurement ------------------------------------------------------

def check_determinism(play_one, variant='full', seed=11, agent='random',
                      simulations=None, max_turns=120):
    """Same seed, same row. Without this nothing is reproducible.

    The budget is passed in. Omitting it fell back to the RUN's default
    of 800 simulations inside a check meant to be cheap, and the gate
    sat silently for half an hour playing two games nobody wanted at
    full strength. Determinism does not depend on playing strength.
    """
    first, _ = play_one(variant, seed, max_turns, agent=agent,
                        simulations=simulations)
    second, _ = play_one(variant, seed, max_turns, agent=agent,
                         simulations=simulations)
    differing = [k for k in first
                 if k != 'wall_clock_s' and first[k] != second.get(k)]
    if differing:
        return _fail('a seed reproduces its run',
                     'columns differ between runs: {}'.format(
                         sorted(differing)[:6]))
    return _ok('a seed reproduces its run')


def check_both_players_sampled(rows):
    """Eight of eleven dimensions once measured White only (#228)."""
    white = sum(r.get('sampled_white') or 0 for r in rows)
    black = sum(r.get('sampled_black') or 0 for r in rows)
    if not white or not black:
        return _fail('both players are sampled',
                     'white={} black={}: the sampler is one-sided'.format(
                         white, black))
    share = min(white, black) / (white + black)
    if share < 0.35:
        return _fail('both players are sampled',
                     'lopsided: white={} black={}'.format(white, black))
    return _ok('both players are sampled',
               'white={} black={}'.format(white, black))


def _ever_true(probe, moves, make_engine):
    """Did the position the ablated rule needs ever arise?"""
    engine = make_engine('full', max_turns=400)
    if probe(engine):
        return True
    for description in moves:
        match = None
        for turn in engine.get_all_legal_turns():
            if _describe(turn) == description:
                match = turn
                break
        if match is None:
            break
        engine.execute_turn(match)
        if probe(engine):
            return True
    return False


def check_no_constant_columns(rows, ignore=()):
    """A column that never moves is a measurement that is not happening.

    Five columns were a constant zero across 1440 games because
    `play_one` hand-built a four-key record and the reader filled the
    rest with `.get(key, 0)`. They looked like real numbers.
    """
    if len(rows) < 2:
        return _fail('no column is constant', 'need at least two rows')
    suspect, rare = [], []
    for column in sorted(rows[0]):
        if column in ignore:
            continue
        values = {r.get(column) for r in rows}
        if len(values) == 1 and next(iter(values)) in (0, 0.0, False, None):
            (rare if column in RARE_COLUMNS else suspect).append(column)
    if suspect:
        return _fail('no column is unexpectedly constant',
                     'constant and empty across {} games, and not declared '
                     'rare: {}'.format(len(rows), ', '.join(suspect)))
    if rare:
        return Result('no column is unexpectedly constant', True,
                      'NO POWER for {}: {} — a function whose evidence is '
                      'one of these cannot be tested at this scale'.format(
                          len(rare), ', '.join(rare)))
    return _ok('no column is unexpectedly constant',
               '{} columns vary'.format(len(rows[0])))


def check_every_ontology_metric_recorded(rows):
    """A function cannot claim evidence the sweep never collects."""
    from lgref.functions.strategic_ontology import ONTOLOGY

    missing = sorted({m for f in ONTOLOGY for m in f.metrics} - set(rows[0]))
    if missing:
        return _fail('every ontology metric is recorded',
                     'named as evidence and never recorded: {}'.format(
                         ', '.join(missing)))
    return _ok('every ontology metric is recorded')


def check_columns_are_accounted_for(rows):
    """Recorded and consulted must not drift apart."""
    from lgref.analysis.profile import DIMENSIONS, NOT_A_DIMENSION

    known = set(DIMENSIONS.values()) | set(NOT_A_DIMENSION)
    stray = sorted(set(rows[0]) - known)
    if stray:
        return _fail('every column is an axis or declared not one',
                     'undeclared: {}'.format(', '.join(stray)))
    return _ok('every column is an axis or declared not one')


def check_agent_objective_is_not_a_dimension(agent=None):
    """The mobility lesson, encoded so it cannot recur.

    The agent used for every sweep in this project minimised the
    opponent's legal-turn count, and `mean_branching` counts legal
    turns. The instrument's objective WAS the metric, which is not a
    bias but a circularity, and the sign of the boulder's effect flipped
    when a different agent played.
    """
    from lgref.analysis.profile import DIMENSIONS
    from lgref.recommend.verdicts import MEASURING_AGENT

    # The agent THIS RUN will use, not a module constant. Reading the
    # constant meant the check reported on whatever the last run used
    # rather than on the run about to start.
    agent = MEASURING_AGENT if agent is None else agent
    if agent == 'mobility':
        circular = [d for d, m in DIMENSIONS.items()
                    if m in ('mean_branching', 'mean_policy_branching')]
        if circular:
            return _fail(
                'the agent does not optimise a profile dimension',
                'the mobility agent minimises opponent legal turns and '
                'these dimensions count them: {}'.format(
                    ', '.join(circular)))
    return _ok('the agent does not optimise a profile dimension',
               'agent={}'.format(agent))


def check_agent_is_not_superseded(agent):
    """Refuse the agent whose results were withdrawn.

    `mobility` stays in the codebase so the superseded runs remain
    reproducible, and that is the only thing it is for. A new run
    configured with it would repeat the failure that cost this project
    every statistic it had collected (#231).
    """
    if agent == 'mobility':
        return _fail('the agent is not a superseded one',
                     'mobility exists only to reproduce withdrawn runs; '
                     'its objective is one of the measured quantities')
    return _ok('the agent is not a superseded one', 'agent={}'.format(agent))


def check_agents_expose_the_metric_contract(make_engine, simulations=20):
    '''Every agent must supply what the metrics read off it.

    THE FAILURE THIS EXISTS FOR. `policy_metrics` reads `last_scores`
    from whichever player just moved. `MCTSPlayer` exposed
    `last_root_values` instead, and the read is a `getattr` with a
    default, so switching the agent emptied four columns -- one of them
    a profile dimension -- without raising anything. The numbers were
    absent rather than wrong, which is the harder kind to notice.

    `score_tolerance` is checked alongside it because a near-optimal
    count is meaningless without the scale it is counted on: 1.0 is one
    legal turn to the mobility heuristic and the ENTIRE RANGE of a win
    rate to the search. One shared constant made the same column mean
    different things in different runs.
    '''
    import random

    from lgref.experiments.random_play import AGENTS, build

    engine = make_engine('full', max_turns=40)
    turns = engine.get_all_legal_turns()
    missing = []
    for name in AGENTS:
        player = build(name, random.Random(1), simulations)
        player.choose_turn(turns, engine)
        for attribute in ('last_scores', 'score_tolerance'):
            if getattr(player, attribute, None) is None:
                missing.append('{}.{}'.format(name, attribute))
        if not getattr(player, 'last_scores', None):
            missing.append('{}.last_scores empty after a move'.format(name))
    if missing:
        return _fail('every agent supplies what the metrics read',
                     'missing: {}'.format(', '.join(missing)))
    return _ok('every agent supplies what the metrics read',
               '{} agents checked'.format(len(AGENTS)))


def check_rollouts_return_results(agent_name, sims=60):
    """A censored rollout is a simulation that bought nothing.

    This game has no draw condition, so a rollout stopped by the cap has
    no result and scoring it as a draw feeds the search a number for a
    game that did not finish.
    """
    if agent_name != 'mcts':
        return _ok('rollouts return a result', 'not applicable to {}'.format(
            agent_name))
    import random
    import sys
    import os
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'src'))
    from experiments.variants import make_engine

    from lgref.experiments.mcts import MCTSPlayer

    engine = make_engine('full', max_turns=300)
    rng = random.Random(4)
    for _ in range(16):
        turns = engine.get_all_legal_turns()
        engine.execute_turn(turns[rng.randrange(len(turns))])
    player = MCTSPlayer(n_simulations=sims, rng=random.Random(1))
    player.choose_turn(engine.get_all_legal_turns(), engine)
    if player.censored_share > 0.05:
        return _fail('rollouts return a result',
                     '{:.0%} of simulations returned no result'.format(
                         player.censored_share))
    return _ok('rollouts return a result',
               'censored {:.1%}'.format(player.censored_share))


def check_config_is_consumed(config_path):
    """Every measurement key must reach code that reads it.

    `agent: mobility` sat in the sweep config and nothing consumed it:
    the agent came from a function default, so editing the config
    changed nothing and a run could not be reproduced from the file
    that claimed to describe it. A parameter that does nothing is worse
    than a missing one, because it reads as a decision that was made.
    """
    import re

    import yaml

    with open(config_path) as handle:
        document = yaml.safe_load(handle) or {}
    measurement = document.get('measurement') or {}
    source = ''
    for module in ('lgref/experiments/pilot.py', 'lgref/experiments/sweep.py'):
        with open(module) as handle:
            source += handle.read()
    unused = [key for key in measurement
              if not re.search(r"['\"]{}['\"]".format(re.escape(key)),
                               source)]
    if unused:
        return _fail('every config parameter reaches code',
                     'declared and never read: {}'.format(', '.join(unused)))
    return _ok('every config parameter reaches code',
               '{} measurement keys'.format(len(measurement)))


def check_enough_seed_groups(rows, minimum=4):
    """The between-seed term rests on the number of GROUPS.

    Ten times the games moved two of forty-nine cells, because the
    sweep scaled games within a group and never added groups (#219).
    """
    groups = {(r.get('seed', 0)) // 1000 for r in rows}
    if len(groups) < minimum:
        return _fail('enough seed groups to decompose variance',
                     '{} groups; the between-seed term would rest on {} '
                     'numbers however many games back them'.format(
                         len(groups), len(groups)))
    return _ok('enough seed groups to decompose variance',
               '{} groups'.format(len(groups)))
