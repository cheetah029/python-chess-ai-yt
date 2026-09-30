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


def check_pilot_games_finish(rows):
    '''Every pilot game must reach a result, or the outcome columns lie.

    THE TRAP THIS PROJECT KEEPS FALLING INTO. There is no draw
    condition, so a game stopped by the turn cap is CENSORED, not
    drawn. `white_win`, `black_win` and `decisive` are then all False
    for reasons that have nothing to do with the rules, and they look
    like measurements.

    It caught its own author: the pilot cap was lowered to 120 to make
    the gate cheap, and at that cap under a 40-simulation search every
    game was capped -- four of four, `winner=None`. The constant-column
    check reported `white_win` and could not say why. This says why.

    WHAT LENGTHENS A GAME IS WEAK PLAY, NOT A SMALL SEARCH BUDGET, and
    an earlier version of this docstring had it backwards. It claimed a
    cheap search plays on LONGER than the run's agent and used that to
    justify a pilot cap below the run's. Measured at cap 1600 (#254):

        seed 0     random 689 turns     MCTS-40 184 turns

    over twelve seeds random play ran to a median of ~340 turns and a
    maximum of 865, while a 40-simulation search finished seed 0 in
    184. Search SHORTENS games -- it finds the win rather than shuffling
    toward it. The cap that random play needs therefore bounds the cap
    any search needs, which is why `CENSOR_FREE_TURN_CAP` can be set
    from the random-play sample in #204 and still be generous here.

    The cap was never the reason the cheap pilot is slow. At 40
    simulations a ply costs 2.14s of THINKING; the game is short and
    each move is expensive. Lowering the cap did not buy speed, it
    bought censored games.
    '''
    if not rows:
        return _fail('pilot games reach a result', 'no rows')
    capped = [r for r in rows if r.get('turn_cap_reached')]
    if len(capped) == len(rows):
        return _fail('pilot games reach a result',
                     'all {} games hit the turn cap: every outcome column '
                     'is censored, not measured. Raise --max-turns'.format(
                         len(rows)))
    if capped:
        return _fail('pilot games reach a result',
                     '{} of {} games hit the turn cap. A censored game is '
                     'not a draw -- this variant has no draw condition -- '
                     'so it contributes NO outcome at all. Raise '
                     '--max-turns'.format(len(capped), len(rows)))
    return _ok('pilot games reach a result',
               'all {} finished; at {} games that bounds the censored '
               'share at {:.0%}, not at zero'.format(
                   len(rows), len(rows), _rule_of_three(len(rows))))


def _rule_of_three(n):
    """95% upper bound on a rate when zero events were observed.

    THE PILOT CANNOT PROVE THE CAP IS SAFE, and this is the number that
    says so out loud. Four games that all finish are consistent with a
    censoring rate as high as 75%; the check above passing is weak
    evidence, not a guarantee. The guarantee has to come from the CAP
    being above a value measured on a real sample, which is what
    `check_cap_is_censor_free` tests -- deterministically, for free,
    and with power the pilot does not have.
    """
    return 3.0 / n if n else 1.0


def check_cap_is_censor_free(max_turns):
    """The configuration check that the pilot is too small to replace.

    WHY A SEPARATE CHECK. `check_pilot_games_finish` reads four games.
    Four games that all finish bound the censored share at 75%, which
    is no bound at all -- a run losing a third of its outcomes would
    pass it more often than not. This reads the cap instead, and the cap
    rests on 400 uncapped games (#260), not on the four the pilot plays.

    WHAT IT CANNOT PROMISE. No finite cap censors nothing: every one of
    those 400 games terminated, but the maximum was 1775 and each
    tenfold increase in sample size has found a longer game -- 1600 was
    "censor-free" against the forty games of #204 and censors 0.5% of
    four hundred. So this checks the cap clears the measured tail with
    headroom, and the analysis separately EXCLUDES censored games from
    the metrics they do not observe rather than relying on there being
    none.

    It caught the gate itself: `--max-turns` defaulted to 400, half of
    `OUTCOME_SAFE_TURN_CAP` and a level where 48% of games are cut off,
    and nothing objected because the gate never called the guard that
    `pilot.py` calls. The one component whose job is to refuse an
    invalid configuration was running under one.
    """
    from lgref.experiments.metrics import (CENSOR_FREE_TURN_CAP,
                                           OUTCOME_SAFE_TURN_CAP)
    name = 'the turn cap does not censor'
    if max_turns < OUTCOME_SAFE_TURN_CAP:
        return _fail(name,
                     'cap {} is below the floor {}, where a win rate '
                     'measures the cap rather than the rules'.format(
                         max_turns, OUTCOME_SAFE_TURN_CAP))
    if max_turns < CENSOR_FREE_TURN_CAP:
        return _fail(name,
                     'cap {} is above the floor {} but below {}, the only '
                     'level measured to end every game. Games between '
                     'those caps are censored, and a censored game is not '
                     'a draw'.format(max_turns, OUTCOME_SAFE_TURN_CAP,
                                     CENSOR_FREE_TURN_CAP))
    return _ok(name, 'cap {} — over 400 uncapped games every game ended, '
                     'the longest at 1775 turns (#260)'.format(max_turns))


def check_no_constant_columns(rows, ignore=()):
    """A column that never moves is a measurement that is not happening.

    Five columns were a constant zero across 1440 games because
    `play_one` hand-built a four-key record and the reader filled the
    rest with `.get(key, 0)`. They looked like real numbers.
    """
    if len(rows) < 2:
        return _fail('no column is constant', 'need at least two rows')
    # THE CENSORING COLUMNS ARE CONSTANT AT BOTH EXTREMES, and one of
    # those extremes is the outcome we want. If every game was capped,
    # every outcome column is False for reasons unrelated to the rules
    # and `check_pilot_games_finish` carries that failure. If every game
    # FINISHED, `turn_cap_reached` and `draw_or_censored` are False
    # throughout precisely because nothing was cut off -- flagging that
    # as a suspect constant reports success as a defect, which is what
    # it did.
    capped = [r.get('turn_cap_reached') for r in rows]
    if all(capped):
        ignore = tuple(ignore) + ('white_win', 'black_win', 'decisive',
                                  'draw_or_censored', 'turn_cap_reached')
    elif not any(capped):
        ignore = tuple(ignore) + ('draw_or_censored', 'turn_cap_reached')
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


def check_agents_do_not_mutate_the_live_game(make_engine, simulations=25):
    '''An agent deciding a move must leave the board exactly as it found it.

    THE WORST DEFECT THIS PROJECT HAS HAD. A `Turn` holds a direct
    reference to a piece on the board that produced it, and
    `Board.move` writes `cooldown`, `moved` and `last_square` onto that
    piece. Every agent simulated by deepcopying the engine and then
    executing the CALLER'S turn objects on the copy -- so each
    simulation wrote through to the live game.

    Measured before the fix: one simulated boulder move took the real
    cooldown from 0 to 2 and the real legal-turn count from 73 to 69.
    A search does that hundreds of times per move. It is why the
    boulder appeared legally movable on 1% of turns under search and
    87% under random play -- a difference that cannot be explained by
    the rules, since a cooldown of 2 can block at most half of all
    turns even if the boulder moves at every opportunity.

    Every measurement taken before this was on a corrupted board.
    '''
    import random

    from lgref.experiments.random_play import AGENTS, build

    broken = []
    for name in AGENTS:
        engine = make_engine('full', max_turns=200)
        rng = random.Random(2)
        for _ in range(40):
            turns = engine.get_all_legal_turns()
            if any(t.turn_type == 'boulder' for t in turns):
                break
            engine.execute_turn(turns[rng.randrange(len(turns))])
        turns = engine.get_all_legal_turns()
        before = _fingerprint(engine)
        build(name, random.Random(1), simulations).choose_turn(turns, engine)
        after = _fingerprint(engine)
        if before != after:
            broken.append(name)
    if broken:
        return _fail('choosing a move leaves the board unchanged',
                     'these agents mutate the live game while thinking: '
                     '{}'.format(', '.join(broken)))
    return _ok('choosing a move leaves the board unchanged',
               '{} agents'.format(len(AGENTS)))


def _fingerprint(engine):
    '''Everything a simulation could write through to.'''
    board = engine.board
    out = [engine.current_player, engine.turn_number,
           len(engine.get_all_legal_turns())]
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            out.append((row, col, piece.name, piece.color,
                        getattr(piece, 'cooldown', None),
                        getattr(piece, 'moved', None),
                        getattr(piece, 'invulnerable', None),
                        getattr(piece, 'moved_by_queen', None),
                        getattr(piece, 'moved_last_turn', None),
                        getattr(piece, 'reactive_armed', None),
                        getattr(piece, 'last_square', None)))
    return tuple(out)


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


def check_determinism_across_processes(variant='full', seed=0,
                                       max_turns=1600, agent='random',
                                       simulations=0):
    """Replay a seed under a DIFFERENT interpreter hash seed (#255).

    WHY THE IN-PROCESS CHECK CANNOT DO THIS. `check_determinism` plays
    one seed twice inside this process, and a process has exactly one
    hash seed, so anything ordered by string hashing scrambles the same
    way both times and the two runs agree. The property it is meant to
    guarantee -- that a seed reproduces its game -- only breaks when the
    hash seed changes, which is every fresh process.

    That is not hypothetical. `Board.get_transformation_options` built
    its option list with `list(set(captured))` over piece-name STRINGS,
    and seed 0 played out to 689, 304 and 236 plies in three consecutive
    processes while the in-process check reported PASS.

    AND THE SWEEP IS MULTI-PROCESS. `n_workers: 8`, and multiprocessing
    uses spawn on macOS, so each worker has its own hash seed: the same
    seed produced a different game depending on which worker took it.
    Reproducing a published row from its own manifest would have been
    impossible, and nothing would have said why.

    It compares a CHECKSUM OF EVERY MOVE, not the final score. Two
    different games can end on the same ply with the same winner, and a
    check that compared only the outcome would call that reproducible.
    """
    import hashlib
    import json
    import os
    import subprocess
    import sys

    name = 'a seed reproduces its run in another process'
    script = (
        'import hashlib, json, random, sys\n'
        'from experiments.variants import make_engine\n'
        'from lgref.experiments.random_play import build\n'
        'from lgref.experiments.mcts import describe\n'
        'variant, seed, cap, agent, sims = (sys.argv[1], int(sys.argv[2]),\n'
        '                                  int(sys.argv[3]), sys.argv[4],\n'
        '                                  int(sys.argv[5]))\n'
        'engine = make_engine(variant, max_turns=cap)\n'
        'w = build(agent, random.Random(seed * 2 + 1), sims)\n'
        'b = build(agent, random.Random(seed * 2 + 2), sims)\n'
        'h, n = hashlib.md5(), 0\n'
        'while not engine.is_game_over():\n'
        '    turns = engine.get_all_legal_turns()\n'
        '    if not turns:\n'
        '        break\n'
        '    p = w if engine.current_player == "white" else b\n'
        '    chosen = p.choose_turn(turns, engine)\n'
        '    h.update(repr((len(turns), describe(chosen))).encode())\n'
        '    engine.execute_turn(chosen)\n'
        '    n += 1\n'
        'print(json.dumps({"plies": n, "winner": engine.winner,\n'
        '                  "moves": h.hexdigest()[:16]}))\n')

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))
    path = os.pathsep.join([repo, os.path.join(repo, 'src')])
    args = [variant, str(seed), str(max_turns), agent, str(simulations)]

    results = []
    # TWO NAMED HASH SEEDS, not two random ones: two random seeds can
    # collide and report a pass that proves nothing.
    for hashseed in ('0', '1'):
        env = dict(os.environ, PYTHONHASHSEED=hashseed, PYTHONPATH=path)
        try:
            out = subprocess.check_output(
                [sys.executable, '-c', script] + args, env=env,
                stderr=subprocess.STDOUT, timeout=900)
        except subprocess.SubprocessError as exc:   # pragma: no cover
            return _fail(name, 'replay failed: {}'.format(exc))
        try:
            results.append(json.loads(out.decode().strip().splitlines()[-1]))
        except ValueError:                          # pragma: no cover
            return _fail(name, 'replay produced no result: {!r}'.format(
                out[-200:]))

    if results[0] != results[1]:
        return _fail(name,
                     'same seed, different game under a different hash '
                     'seed: {} vs {}. Something orders on str hashing -- '
                     'a `list(set(...))` of names reaching the legal-turn '
                     'list is how this happened before (#255)'.format(
                         results[0], results[1]))
    return _ok(name, 'seed {} gives the same {} moves under both hash '
                     'seeds'.format(seed, results[0]['plies']))


def _state_fingerprint(engine):
    """Everything the rulebook says determines the legal-move set.

    Deliberately WIDER than piece positions. The rulebook's "board state"
    includes per-piece status flags -- royal and transformed markers,
    manipulation freeze, invulnerability, moved-last-turn,
    reactive-armed -- plus the boulder's cooldown and no-return memory.
    A comparison that read positions alone would call two states equal
    while they offered different legal turns.
    """
    out = []
    board = engine.board
    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if piece is None:
                continue
            out.append((row, col, type(piece).__name__,
                        getattr(piece, 'color', None),
                        getattr(piece, 'name', None),
                        getattr(piece, 'is_royal', None),
                        getattr(piece, 'is_transformed', None),
                        getattr(piece, 'invulnerable', False),
                        getattr(piece, 'moved_by_queen', False),
                        getattr(piece, 'moved_last_turn', False),
                        getattr(piece, 'reactive_armed', False),
                        getattr(piece, 'cooldown', None),
                        getattr(piece, 'last_square', None)))
    return (tuple(out), engine.current_player, engine.winner)


def check_turn_descriptions_are_sound(make_engine, games=2, max_turns=120):
    """Turns sharing a description must lead to the same state (#257).

    WHAT THE SEARCH RESTS ON. `describe()` reduces a Turn to plain data
    so the tree holds no reference to a live board -- the #247 fix --
    and `resolve()` maps a description back by returning the FIRST legal
    turn that matches. That is sound only if a description identifies a
    turn's EFFECT.

    IT DOES NOT IDENTIFY THE TURN. Measured over 62,033 descriptions,
    1.3% are shared by two or more distinct legal turns. The variant's
    rook moves one square orthogonally and then turns 90 degrees and
    sweeps, so (0,5) -> (1,6) exists as both up-then-right and
    right-then-up, and `describe` keeps only the endpoints.

    IT DOES IDENTIFY THE EFFECT, which is the property that matters:
    every collision group measured produced ONE resulting fingerprint.
    Both rook paths need the same squares clear and land on the same
    square, and a manipulating queen does not move.

    So this does not check injectivity -- that is false and does not
    need to be true. It checks that `resolve` returning "the wrong one"
    cannot change the game. If a rule ever makes the rook's path
    observable, the search would explore one turn and play another with
    no error and entirely plausible numbers, and this is what would say
    so.
    """
    import collections
    import copy
    import random

    from lgref.experiments.mcts import describe
    from lgref.experiments.random_play import build

    name = 'turns sharing a description share an outcome'
    groups_checked = shared = 0
    for seed in range(games):
        engine = make_engine('full', max_turns=max_turns)
        white = build('random', random.Random(seed * 2 + 1), 0)
        black = build('random', random.Random(seed * 2 + 2), 0)
        while not engine.is_game_over():
            turns = engine.get_all_legal_turns()
            if not turns:
                break
            by_description = collections.defaultdict(list)
            for index, turn in enumerate(turns):
                by_description[describe(turn)].append(index)
            for description, indexes in by_description.items():
                if len(indexes) < 2:
                    continue
                shared += 1
                # COPY THE ENGINE AND THE TURNS TOGETHER. A Turn holds a
                # reference to a piece on the board that made it, so
                # executing a caller's turn on a copy writes through to
                # the live game (#247).
                prints = set()
                for index in indexes:
                    sim, sim_turns = copy.deepcopy((engine, turns))
                    sim.execute_turn(sim_turns[index])
                    prints.add(_state_fingerprint(sim))
                groups_checked += 1
                if len(prints) > 1:
                    return _fail(
                        name,
                        '{} legal turns share the description {!r} and lead '
                        'to {} DIFFERENT states: the search explores one and '
                        'plays another'.format(len(indexes), description,
                                               len(prints)))
            player = white if engine.current_player == 'white' else black
            engine.execute_turn(player.choose_turn(turns, engine))
    if not groups_checked:
        return Result(name, True,
                      'no two legal turns shared a description in {} games -- '
                      'nothing to disprove, and nothing proved'.format(games))
    return _ok(name, '{} shared descriptions, every group one outcome'.format(
        groups_checked))
