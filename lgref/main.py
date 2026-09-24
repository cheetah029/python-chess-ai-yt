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
from lgref.identify.language import LANGUAGE, classify_all

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
    ('2 function inference', 'built',
     'ontology + inference, pre-registered before ablation (#208)'),
    ('3 contribution measurement', 'partly built',
     'agents and metrics exist; the sweep is not wired to the menu'),
    ('4 analysis', 'built',
     'variance decomposition, bootstrap CIs, RCI under four objectives'),
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
    print('PER-RULE ABLATION PLAN')
    print('-' * 72)
    print('A mode is a KIND OF EDIT, not a label the framework assigns to a')
    print('rule. Nothing here picks one mode per rule. Each rule is checked')
    print('against all three, and every mode that applies to it is run --')
    print('they answer different questions, so a rule with two applicable')
    print('modes gets two contributions, not one.')
    print()
    print('  relax    what does this RESTRICTION buy?')
    print('  remove   what does this COMPONENT buy?')
    print('  replace  is THIS VERSION of it the right one?')
    print()
    print('Not every mode applies to every rule, and that is a property of')
    print('the rule, not a choice: a rule with no numeric parameter has')
    print('nothing to vary, and one that governs no entity has nothing to')
    print('delete. Modes that do not apply are shown as "-".')
    print()

    # Language clusters are excluded from the plan. They are the
    # coordinate arithmetic the rules are WRITTEN IN, and ablating one
    # deletes a rule's ability to be expressed rather than testing the
    # rule -- not a design counterfactual anyone would consider (#202).
    kinds = classify_all(nodes, rules)
    language = [r for r in rules if kinds[r.rule_id] == LANGUAGE]
    rules = [r for r in rules if kinds[r.rule_id] != LANGUAGE]
    if language:
        print('Excluded {} language cluster(s) -- coordinate arithmetic with'
              .format(len(language)))
        print('no dependence on game state at any depth, e.g. {}.'.format(
            ', '.join(sorted({n.head_predicate for r in language
                              for n in r.nodes()
                              if n.node_id in r.clause_ids
                              and n.head_predicate}))[:60]))
        print()

    subjects = sorted(Vocabulary.derive(forms).action_subjects)
    by_parameter = {}
    for parameter in params.parameters(forms):
        by_parameter.setdefault(parameter.fluent, []).append(parameter)

    print('The remove column lists the entities a rule\'s clauses act on.')
    print('Those are shared, so removing one ablates every rule that uses')
    print('it -- the column is for attribution, and the distinct removals')
    print('are listed separately below.')
    print()
    print('   {:<5} {:<24} {:<22} {}'.format(
        'rule', 'relax', 'remove', 'replace'))
    print('   ' + '-' * 69)
    total = {'relax': 0, 'remove': 0, 'replace': 0}
    for rule in rules:
        described = rule.describe()
        written = described['fluents_written']

        relaxable = [f for f in written if ops.relax(forms, [f]).dropped]

        entities = [s for s in described['piece_types'] if s in subjects]

        replaceable = []
        for fluent in written:
            for parameter in by_parameter.get(fluent, []):
                values = params.sweep(forms, parameter)
                if values:
                    replaceable.append('{}={}->{}'.format(
                        parameter.predicate[:14], parameter.value, values))

        total['relax'] += len(relaxable)
        total['remove'] += len(entities)
        total['replace'] += len(replaceable)
        if not (relaxable or entities or replaceable):
            continue
        print('   {:<5} {:<24} {:<22} {}'.format(
            rule.rule_id,
            ','.join(relaxable)[:24] or '-',
            ','.join(entities)[:22] or '-',
            '; '.join(replaceable)[:24] or '-'))

    print()
    print('   variants at one per cell: {} relax + {} remove + {} replace'
          ' = {}'.format(total['relax'], total['remove'], total['replace'],
                         sum(total.values())))
    print('   Entities are shared between rules, so the remove column')
    print('   counts each rule-entity pair; the distinct removals are the')
    print('   {} entities below.'.format(len(subjects)))

    gaps = ops.undefined_in(forms)
    print()
    print('-' * 72)
    print('DISTINCT VARIANTS')
    print('-' * 72)
    for name in subjects:
        after = ops.remove_constant(forms, name)
        print('   remove  {:<16} {} -> {:>3} forms  ({} eliminated)'.format(
            name, len(forms), len(after), len(forms) - len(after)))
    shown_any = bool(subjects)
    for fluent, entries in sorted(by_parameter.items()):
        for parameter in entries:
            values = params.sweep(forms, parameter)
            if values:
                shown_any = True
                print('   replace {:<16} {} = {} -> try {}'.format(
                    fluent, parameter.predicate[:22], parameter.value,
                    values))
            elif parameter.kind == 'counter':
                shown_any = True
                print('   replace {:<16} REFUSED: counter-encoded, its value'
                      ' is a chain position'.format(fluent))
    if not subjects:
        print('   remove  none — this description has no action subjects')
    if not by_parameter:
        print('   replace none — this description has no rule parameters')
    if not shown_any:
        print('   (relax is the only mode that applies to this game)')

    return rules


def _labelled(rule_id, functions, characteristics, width=150, gutter=6):
    """Print one rule's labels with continuations aligned under the text.

    Everything after the first line is indented to the content column,
    so the left margin carries rule identifiers and nothing else --
    wrapped text sitting under a rule number reads as if it belonged to
    another rule. The width is generous because labels crammed onto
    narrow lines are harder to scan than long ones.
    """
    body = max(width - gutter, 40)
    first = True

    def emit(items, prefix=''):
        nonlocal first
        line = prefix
        for index, item in enumerate(items):
            piece = item + (', ' if index < len(items) - 1 else '')
            if line and len(line) + len(piece) > body:
                _emit_line(rule_id if first else '', line, gutter)
                first = False
                line = ''
            line += piece
        if line:
            _emit_line(rule_id if first else '', line, gutter)
            first = False

    emit(functions)
    if characteristics:
        emit(characteristics, prefix='characteristics: ')


def _emit_line(label, text, gutter):
    print('{:<{}}{}'.format(label, gutter, text).rstrip())


def cmd_functions(args):
    """Phase 2: strategic functions and design characteristics per rule.

    Reports against the project's own ontology -- 40 functions across
    eight categories -- not against the narrower operational categories
    an earlier version used. Those described what a rule does to the
    move set, which is mechanism rather than strategic role, and could
    not express `space_control` at all.
    """
    from lgref.functions import characteristics as chars
    from lgref.functions.strategic_ontology import (BY_NAME,
                                                    NOT_YET_OPERATIONAL,
                                                    describe)
    from lgref.functions.structural import (coverage, explain_gaps,
                                            predict_all)

    nodes = _load(args.gdl)
    graph = ClauseGraph(nodes)
    resolution = args.resolution
    if resolution == 1.0:
        from lgref.identify.cluster import calibrate_resolution
        resolution = calibrate_resolution(graph, seed=args.seed)
    rules, _ = cluster(graph, resolution=resolution, seed=args.seed)
    kinds = classify_all(nodes, rules)
    skip = {r.rule_id for r in rules if kinds[r.rule_id] == LANGUAGE}

    print(BANNER)
    print('STRATEGIC FUNCTIONS — {}'.format(args.gdl))
    print(BANNER)
    print(describe())
    print()
    print('Predictions are STRUCTURAL: what the rule shape suggests,')
    print('before the game is played. Phase 3 measures and Phase 4 scores')
    print('them, so a prediction here can turn out wrong -- which is what')
    print('makes it evidence rather than description.')
    print()
    print('-' * 72)

    predictions = predict_all(nodes, rules, skip=skip)
    roles = {c for n in nodes if n.head_predicate == 'role'
             for c in (n.raw[1:] if isinstance(n.raw, tuple) else ())
             if isinstance(c, str)}
    context = {'roles': roles}

    unlabelled = 0
    for rule in rules:
        got = predictions.get(rule.rule_id)
        if got is None:
            continue
        if not got:
            unlabelled += 1
            continue
        own = [n for n in rule.nodes() if n.node_id in rule.clause_ids]
        marks = chars.detect(own, context)
        shown = {k: v for k, v in marks.items() if v != chars.UNKNOWN}
        _labelled(
            rule.rule_id,
            ['{} ({:.2f}{})'.format(
                p.function, p.confidence,
                '' if p.falsifiable else ', unfalsifiable') for p in got],
            ['{}={}'.format(k, v) for k, v in shown.items()])

    seen, never = coverage(predictions)
    print()
    print('{} rules labelled, {} carried no signature, {} language clusters '
          'skipped.'.format(len(predictions) - unlabelled, unlabelled,
                            len(rules) - len(predictions)))
    print('{} of {} ontology functions predicted here; {} never.'.format(
        len(seen), len(BY_NAME), len(never)))
    print()
    gaps = explain_gaps(predictions)
    print('Not predicted here, by REASON. One reason is a property of the')
    print('ontology; the other is a shortcoming of these detectors:')
    print()
    labels = {
        'measured_null': 'the NULL RESULT of another function -- the same '
                         'structure\n                with the opposite '
                         'measured outcome, so structure cannot\n'
                         '                propose it (Phase 3 decides '
                         'between them)',
        'detector_gap': 'structurally findable and NOT YET FOUND -- the only '
                        'group\n                that is a shortcoming here',
    }
    for reason, names in gaps.items():
        if not names:
            continue
        print('  {} ({}): {}'.format(reason, len(names), labels[reason]))
        for index in range(0, len(names), 3):
            print('       {}'.format(', '.join(names[index:index + 3])))
        print()
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
    print('summary. Today it does the first two, builds the ablated')
    print('descriptions the third needs, and scores what they measure.')


def cmd_all(args):
    """Every phase that exists, end to end, on one description.

    The long ones are included: the Phase 1 intervention sweep takes
    about 20 minutes at 8 workers and the Phase 3 pilot a few more, so
    this is the "run the whole thing" command rather than the quick
    look. `run` stays the fast path.

    Phases 4-7 do not exist yet and are reported as missing rather than
    skipped silently -- a pipeline that quietly stops early is
    indistinguishable from one that finished.
    """
    import subprocess

    print(BANNER)
    print('LGREF — ALL PHASES')
    print(BANNER)
    print()
    print('Runs every phase that exists on {}.'.format(args.gdl))
    print('Phases 4-7 are not built; they are reported, not skipped.')
    print()

    cmd_identify(args)
    print()
    cmd_ablations(args)
    print()
    cmd_functions(args)
    print()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for label, argv in (
            ('PHASE 1 GATE (intervention sweep, ~20 min at 8 workers)',
             [sys.executable, '-m', 'lgref.identify.gate', '--config',
              'lgref/config/phase1_gate.yaml']),
            ('PHASE 3 PILOT (self-play measurement)',
             [sys.executable, '-m', 'lgref.experiments.pilot', '--config',
              'lgref/config/phase3_pilot.yaml'])):
        print(BANNER)
        print(label)
        print(BANNER, flush=True)
        done = subprocess.run(argv, cwd=root)
        if done.returncode != 0:
            print('{} FAILED (exit {}) — stopping rather than reporting '
                  'a partial pipeline as complete.'.format(
                      label, done.returncode))
            return
        print()

    print(BANNER)
    cmd_status(args)


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
                        choices=['identify', 'ablations', 'functions',
                                 'status', 'run', 'all'])
    parser.add_argument('--gdl', help='path to an infix-HRF GDL description')
    parser.add_argument('--resolution', type=float, default=1.0)
    parser.add_argument('--seed', type=int, default=0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command != 'status' and not args.gdl:
        raise SystemExit('--gdl is required for `{}`'.format(args.command))
    {'identify': cmd_identify, 'ablations': cmd_ablations,
     'functions': cmd_functions, 'status': cmd_status,
     'run': cmd_run, 'all': cmd_all}[args.command](args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
