"""LGREF command line — WORK IN PROGRESS.

    python3 -m lgref --gdl path/to/game.gdl

Point it at a GDL description and it runs the parts of the framework
that exist, then says plainly which parts do not. The finished tool is
meant to take a game in and produce, per discovered rule: its formal
clauses, its strategic functions, the measured effect of ablating it, a
retain/revise/remove recommendation and a grounded summary. Phases 2
and 4-7 are not built, so this prints their status rather than
pretending.

Nothing here is specific to Royal Chess. Hand it tic-tac-toe, nim, or
any other GDL game and every number is derived from that description.

INPUT DIALECT. Infix HRF, this project's official dialect (issue #190):

    legal(P, move(boulder, FF, FR, TF, TR)) :- true(control(P)) & ...

Prefix KIF is refused with a message naming the converter, because the
two dialects do not have the same statement count and a silent fallback
would change every number below without saying so.

Subcommands:

    identify    Phase 1 -- clauses, graph, candidate rules, verdicts
    ablations   the ablation menu: what could be relaxed or removed
    status      which phases are built, and what each one needs
    run         identify + ablations, then the status of the rest
"""

import argparse
import os
import sys

# Runnable as `python3 lgref/main.py`, not only as `python3 -m lgref`.
# Running the file directly puts lgref/ on the path but not its parent,
# so `import lgref` fails before lgref/__init__.py can fix anything.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lgref.ablate import operations as ops
from lgref.ablate import parameters as params
from lgref.identify.clauses import Vocabulary, load
from lgref.identify.cluster import cluster
from lgref.identify.graph import ClauseGraph

BANNER = '=' * 72

# What exists, what does not, and what the missing part is waiting on.
# Stated here so `status` cannot drift from reality quietly -- if a
# phase lands and this is not updated, the CLI lies about the tool.
PHASES = [
    ('0.5 cross-validation', 'built',
     'GDL reproduces the engine on 1200/1200 sampled positions'),
    ('1 rule identification', 'built',
     'clause graph, clustering, intervention coherence'),
    ('1b ablation operations', 'built',
     'relax and remove; replace is designer-supplied (#193)'),
    ('2 function inference', 'NOT BUILT',
     'needs the Phase 1 candidate list to stabilise (#189)'),
    ('3 contribution measurement', 'partly built',
     'agents and metrics exist; the sweep is not wired to the menu'),
    ('4 analysis', 'NOT BUILT', 'needs Phase 3 output'),
    ('5 recommendation', 'NOT BUILT', 'needs Phase 4 output'),
    ('6 explanation', 'NOT BUILT', 'needs Phase 5 output'),
    ('7 results package', 'NOT BUILT', 'needs everything above'),
]


def _load(path):
    if not os.path.exists(path):
        raise SystemExit('no such description: {}'.format(path))
    return load(path)


def cmd_identify(args):
    nodes = _load(args.gdl)
    graph = ClauseGraph(nodes)
    rules, dropped = cluster(graph, resolution=args.resolution, seed=args.seed)

    print(BANNER)
    print('RULE IDENTIFICATION — {}'.format(args.gdl))
    print(BANNER)
    print('{} clauses, {} edges'.format(len(nodes), graph.edge_count()))
    for kind, count in sorted(graph.summary()['edges_by_type'].items()):
        print('   {:<15} {}'.format(kind, count))
    print()
    print('{} candidate rules at resolution {} (seed {}), {} unclustered'
          .format(len(rules), args.resolution, args.seed, len(dropped)))
    print()
    print('NOTE: resolution is a scale parameter and 1.0 was calibrated on')
    print('22-34 clause games. On a large description it is too coarse; see')
    print('issue #189. Try --resolution 8 to compare.')
    print()
    for rule in rules:
        described = rule.describe()
        print('{}  {:>3} clauses (+{} shared)  actions={}'.format(
            rule.rule_id, described['n_clauses'], described['n_shared'],
            described['action_types'] or '-'))
    print()
    print('Verdicts (rule / load_bearing / inert / broken) need the')
    print('intervention probe, which takes minutes. Run the gate for those:')
    print('   python3 -m lgref.identify.gate --config '
          'lgref/config/phase1_gate.yaml')
    return rules


def cmd_ablations(args):
    """The menu: what could be ablated, in which of the three modes."""
    nodes = _load(args.gdl)
    forms = [n.raw for n in nodes]
    graph = ClauseGraph(nodes)
    rules, _ = cluster(graph, resolution=args.resolution, seed=args.seed)

    print(BANNER)
    print('ABLATION MENU — {}'.format(args.gdl))
    print(BANNER)
    print()
    print('Three modes. Two are generated from the description; the third')
    print('cannot be, because it needs an alternative someone has written.')
    print()
    print('  relax    drop a body conjunct -- the game gets MORE permissive')
    print('  remove   delete an entity and everything that dies with it')
    print('  replace  substitute an alternative definition — DESIGNER-SUPPLIED')
    print()
    print('Relaxing every restriction on a piece does NOT remove the piece.')
    print('It leaves an unrestricted one, which is a different experiment.')
    print()

    gaps = ops.undefined_in(forms)
    if gaps:
        print('Description health: {} predicate(s) consulted but never'
              .format(len(gaps)))
        print('defined — {}.'.format(', '.join(sorted(gaps))))
        print('These are pre-existing and are excluded from removal')
        print('cascades, so baseline breakage is not reported as an')
        print('ablation effect.')
        print()

    print('-' * 72)
    print('RELAX candidates — one per piece of state a rule governs')
    print('-' * 72)
    print('Listed per FLUENT, not per cluster: a restriction is usually one')
    print('conjunct, and relaxing a whole cluster at once is the coarse')
    print('experiment this mode exists to avoid.')
    print()
    seen = set()
    for rule in rules:
        for fluent in rule.describe()['fluents_written']:
            if fluent in seen:
                continue
            seen.add(fluent)
            result = ops.relax(forms, [fluent])
            if not result.dropped:
                continue
            note = ('  [{} clause(s) refused: would unbind a head variable]'
                    .format(len(result.refused)) if result.refused else '')
            print('   relax {:<30} drops {:>3} conjunct(s){}'.format(
                fluent, result.dropped, note))
    if not seen:
        print('   none — no cluster in this game writes state')

    print()
    print('-' * 72)
    print('REMOVE candidates — the entities this description acts on')
    print('-' * 72)
    print('Taken from the discriminator slot of the game\'s own action')
    print('terms, so the list is whatever this game is about.')
    print()
    subjects = sorted(Vocabulary.derive(forms).action_subjects)
    for name in subjects:
        after = ops.remove_constant(forms, name)
        print('   remove {:<16} {} -> {:>3} forms  ({} clauses eliminated)'
              .format(name, len(forms), len(after), len(forms) - len(after)))
    if not subjects:
        print('   none — this description has no action subjects')

    print()
    print('-' * 72)
    print('REPLACE candidates — rule parameters, varied automatically')
    print('-' * 72)
    print('A rule parameterised by a constant in its own clauses can be')
    print('varied without anyone writing an alternative, which turns a')
    print('binary ablation into a dose-response curve. This is what makes')
    print('a REVISE verdict reachable; relax and remove cannot produce one.')
    print()
    shown = set()
    for parameter in params.parameters(forms):
        key = (parameter.predicate, parameter.value)
        if key in shown:
            continue
        shown.add(key)
        values = params.sweep(forms, parameter)
        if parameter.kind == 'counter':
            print('   {:<32} = {:<3} REFUSED: {} is counter-encoded, so its'
                  .format(parameter.predicate, parameter.value,
                          parameter.fluent))
            print('   {:<32}   value is a chain position, not a setting;'
                  .format(''))
            print('   {:<32}   substituting it silently shortens the rule.'
                  .format(''))
        elif values:
            print('   {:<32} = {:<3} try {}'.format(
                parameter.predicate, parameter.value, values))
        else:
            print('   {:<32} = {:<3} no reachable neighbour to try'.format(
                parameter.predicate, parameter.value))
    if not shown:
        print('   none — this description has no numeric rule parameters')

    print()
    print('Structural replacements (swapping one rule\'s geometry for')
    print('another\'s) and novel mechanics are not generated here; see #196.')

    return rules


def cmd_status(args):
    print(BANNER)
    print('LGREF — BUILD STATUS (work in progress)')
    print(BANNER)
    for name, state, note in PHASES:
        print('  {:<28} {:<14} {}'.format(name, state, note))
    print()
    print('The finished tool takes a GDL description and reports, per')
    print('rule: its clauses, its strategic functions, the measured')
    print('effect of ablating it, a recommendation and a grounded')
    print('summary. Today it does the first of those and can build the')
    print('ablated descriptions the third one needs.')


def cmd_run(args):
    cmd_identify(args)
    print()
    cmd_ablations(args)
    print()
    cmd_status(args)


def build_parser():
    parser = argparse.ArgumentParser(
        prog='lgref', description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', nargs='?', default='run',
                        choices=['identify', 'ablations', 'status', 'run'])
    parser.add_argument('--gdl', help='path to an infix-HRF GDL description')
    parser.add_argument('--resolution', type=float, default=1.0)
    parser.add_argument('--seed', type=int, default=0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command != 'status' and not args.gdl:
        raise SystemExit('--gdl is required for `{}`'.format(args.command))
    {'identify': cmd_identify, 'ablations': cmd_ablations,
     'status': cmd_status, 'run': cmd_run}[args.command](args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
