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
    parser.add_argument('--games', type=int, default=2)
    parser.add_argument('--seed-groups', type=int, default=4)
    parser.add_argument('--max-turns', type=int, default=400)
    parser.add_argument('--simulations', type=int, default=40,
                        help='search budget for the PILOT only; the gate '
                             'checks plumbing, not playing strength')
    parser.add_argument('--plies', type=int, default=140)
    parser.add_argument('--config',
                        default='lgref/config/phase4_sweep.yaml')
    args = parser.parse_args(argv)

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
    results.append(checks.check_control_is_identical(make_engine, args.plies))
    for name in sorted(VARIANTS):
        if name in ('full', 'control_inert'):
            continue
        results.append(checks.check_variant_changes_something(
            name, make_engine, args.plies))

    results.append(checks.check_determinism(play_one, agent=args.agent))
    results.append(checks.check_config_is_consumed(args.config))
    results.append(checks.check_agent_objective_is_not_a_dimension(
        args.agent))
    results.append(checks.check_rollouts_return_results(args.agent))
    results.append(checks.check_agent_is_not_superseded(args.agent))

    rows = collect(args.agent, args.games, args.seed_groups, args.max_turns,
                   args.simulations)
    results.append(checks.check_both_players_sampled(rows))
    results.append(checks.check_enough_seed_groups(rows))
    results.append(checks.check_every_ontology_metric_recorded(rows))
    results.append(checks.check_columns_are_accounted_for(rows))
    results.append(checks.check_no_constant_columns(
        rows, ignore=('variant', 'agent', 'winner', 'loss_reason')))

    width = max(len(r.name) for r in results)
    for result in results:
        print('  {}  {:<{}}  {}'.format(
            'PASS' if result.passed else 'FAIL', result.name, width,
            result.detail))
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
