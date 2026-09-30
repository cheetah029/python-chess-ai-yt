"""Run every pre-flight check and refuse loudly if one fails.

    python3 -m lgref.verify.run --agent random --games 8

Exit status is 0 only when everything passes. A long measurement run is
worth paying for only after this does.
"""

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), 'src'))

from lgref.experiments.metrics import (CENSOR_FREE_TURN_CAP,
                                       require_outcome_safe_cap)
from lgref.verify import checks

BANNER = '=' * 78


def collect(agent, games, seed_groups, max_turns, simulations):
    """A small pilot, shaped like the real run and priced like a test.

    The simulation budget here is deliberately far below the run's. This
    checks the PLUMBING -- that columns vary, that both players get
    sampled, that a seed reproduces -- and none of that needs a strong
    search. Using the run's budget would make the gate cost more than
    the thing it is gating.
    """
    from lgref.experiments.sweep import play_one

    rows = []
    for group in range(seed_groups):
        for game in range(games):
            row, _samples = play_one('full', group * 1000 + game, max_turns,
                                     agent=agent, simulations=simulations)
            rows.append(row)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', default='random')
    # ONE GAME PER SEED GROUP. The pilot needs four groups for the
    # variance check and finished games for the outcome columns, and
    # the cap that stops it censoring is the expensive part -- eight
    # uncensored games at search speed cost more than the gate is
    # worth. Four is enough for every check that reads rows.
    parser.add_argument('--games', type=int, default=1)
    parser.add_argument('--seed-groups', type=int, default=4)
    # THE RUN'S CAP, deliberately not a cheaper one (#254). It was 120,
    # then 400, each time chosen to make the gate quick, and each time
    # the gate was then verifying a configuration the run does not use.
    # At 400 one pilot game in four was still censored and the gate
    # reported PASS, because the check only refused TOTAL censoring.
    #
    # No draw condition exists, so a capped game is censored and
    # contributes no outcome at all. The gate now runs the pilot at the
    # cap the run will use and calls the same `require_outcome_safe_cap`
    # guard `pilot.py` calls -- which the gate never did, while
    # defaulting to half the floor that guard enforces.
    parser.add_argument('--max-turns', type=int, default=CENSOR_FREE_TURN_CAP)
    # DETERMINISM DOES NOT READ OUTCOMES. It replays one seed twice and
    # compares the rows, so it needs enough plies to diverge, not enough
    # to finish -- and paying the run's cap twice over for it is the
    # cost that pushed the pilot cap down in the first place.
    parser.add_argument('--determinism-max-turns', type=int, default=150)
    parser.add_argument('--simulations', type=int, default=40,
                        help='search budget for the PILOT only; the gate '
                             'checks plumbing, not playing strength')
    parser.add_argument('--plies', type=int, default=140)
    parser.add_argument('--config',
                        default='lgref/config/phase4_sweep.yaml')
    args = parser.parse_args(argv)
    # THE GUARD THE GATE ITSELF WAS RUNNING UNDER (#254). A cap
    # below the floor is refused here rather than reported as a
    # check, because a gate that measures the cap cannot tell you
    # anything about the rules.
    require_outcome_safe_cap(args.max_turns)

    from experiments.variants import VARIANTS, make_engine
    from lgref.experiments.sweep import play_one

    print(BANNER)
    print('PRE-FLIGHT — what would invalidate a measurement run')
    print(BANNER)
    print()
    print('A long run is worth paying for only if the things that ruin it')
    print('SILENTLY have been checked. Most of the defects this project')
    print('has found produced plausible numbers rather than errors.')
    print()

    results = []

    def record(result):
        # PRINTED AS IT HAPPENS. The first version printed nothing until
        # every check had finished and took thirty-six minutes to say so,
        # which is the exact failure this project has a written rule
        # against: a run you cannot see is a run you cannot manage.
        print('  {}  {:<48}  {}'.format(
            'PASS' if result.passed else 'FAIL', result.name, result.detail),
            flush=True)
        results.append(result)
        return result

    record(checks.check_control_is_identical(make_engine, args.plies))
    for name in sorted(VARIANTS):
        if name in ('full', 'control_inert'):
            continue
        record(checks.check_variant_changes_something(
            name, make_engine, args.plies))

    record(checks.check_cap_is_censor_free(args.max_turns))
    record(checks.check_determinism(play_one, agent=args.agent,
                                    simulations=args.simulations,
                                    max_turns=args.determinism_max_turns))
    # ACROSS PROCESSES, which the check above structurally cannot do:
    # one process has one hash seed. Run under random play because this
    # asks whether the ENGINE reproduces, and random play exercises a
    # whole game for half a second instead of an hour (#255).
    record(checks.check_determinism_across_processes())
    record(checks.check_config_is_consumed(args.config))
    record(checks.check_agent_objective_is_not_a_dimension(args.agent))
    record(checks.check_rollouts_return_results(args.agent))
    record(checks.check_agent_is_not_superseded(args.agent))
    record(checks.check_agents_expose_the_metric_contract(make_engine))
    record(checks.check_agents_do_not_mutate_the_live_game(make_engine))
    # THE OTHER HALF OF THE #247 FIX. That one stopped the search
    # writing through to the live board by storing DESCRIPTIONS; this
    # one checks the descriptions are sound, because `resolve` returns
    # the first turn that matches and 1.3% of them match more than one
    # (#257).
    record(checks.check_turn_descriptions_are_sound(make_engine))

    print('  ....  playing {} pilot games at {} simulations'.format(
        args.games * args.seed_groups, args.simulations), flush=True)
    rows = collect(args.agent, args.games, args.seed_groups, args.max_turns,
                   args.simulations)
    record(checks.check_pilot_games_finish(rows))
    record(checks.check_both_players_sampled(rows))
    record(checks.check_enough_seed_groups(rows))
    record(checks.check_every_ontology_metric_recorded(rows))
    record(checks.check_columns_are_accounted_for(rows))
    record(checks.check_no_constant_columns(
        rows, ignore=('variant', 'agent', 'winner', 'loss_reason',
                      'agent_simulations')))

    print()
    failed = [r for r in results if not r.passed]
    print()
    print('{} checks, {} failed.'.format(len(results), len(failed)))
    if failed:
        print()
        print('DO NOT START THE RUN. Each failure above is something that')
        print('would have produced numbers rather than an error.')
        return 1
    print()
    print('Pipeline checks pass. NOTE WHAT THIS DOES NOT SAY: it does not')
    print('say the agent is strong enough for its answers to be')
    print('agent-independent. That is what the two-arm design measures.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
