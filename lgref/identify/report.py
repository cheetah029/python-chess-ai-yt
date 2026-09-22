"""Assemble the Phase 1 gate report.

The brief asks Phase 1 to stop and show: identification scores against
hand-verified boundaries with baselines, and the clusters found in the
game under study, as clause lists, for inspection.

The report states what was measured and what was not. A rule the probe
could not demonstrate is listed as undemonstrated, never quietly
dropped — a report that showed only the successes would misrepresent how
much of the game the method actually accounts for.
"""

import collections

from lgref.identify.clauses import load
from lgref.identify.cluster import cluster
from lgref.identify.graph import ClauseGraph
from lgref.identify.intervention import check_all
from lgref.identify.validate import evaluate, format_table as score_table


def validation_section(games, game_dir):
    """Scores on the hand-verified games, with baselines."""
    from lgref.identify.testgames.ground_truth import expected_partition
    rows = []
    for game in games:
        nodes = load('{}/{}.gdl'.format(game_dir, game))
        rows += evaluate(game, nodes, expected_partition(game, nodes))
    return rows


def identify(gdl_path, **kw):
    """Run the whole Phase 1 pipeline on one description."""
    nodes = load(gdl_path)
    graph = ClauseGraph(nodes)
    rules, dropped = cluster(graph, **kw)
    reports = check_all(nodes, rules)
    by_id = {r.rule_id: r for r in reports}
    return nodes, graph, rules, dropped, by_id


def rule_listing(rules, verdicts, max_clauses=14):
    """Candidate rules as clause lists, for inspection.

    Clause lists rather than names. Naming a cluster would assert what it
    is FOR, which Phase 2 infers and Phase 3 tests; stating it here would
    prejudge both.
    """
    lines = []
    for rule in rules:
        report = verdicts.get(rule.rule_id)
        verdict = report.verdict if report else '?'
        described = rule.describe()
        lines.append(
            '{} [{}] {} clauses (+{} shared) actions={} subjects={}'.format(
                rule.rule_id, verdict, described['n_clauses'],
                described['n_shared'],
                described['action_types'] or '-',
                described['piece_types'][:6] or '-'))
        if described['fluents_written']:
            lines.append('      writes: {}'.format(
                ', '.join(described['fluents_written'][:8])))
        heads = collections.Counter(
            n.head_predicate for n in rule.nodes() if n.head_predicate)
        shown = ', '.join('{}x{}'.format(p, c)
                          for p, c in heads.most_common(max_clauses))
        lines.append('      clauses: {}'.format(shown))
        if report and report.actions_lost:
            lines.append('      ablation removes: {}'.format(
                report.actions_lost))
        lines.append('')
    return '\n'.join(lines)


def build_report(gdl_path, games, game_dir, **kw):
    nodes, graph, rules, dropped, verdicts = identify(gdl_path, **kw)
    counts = collections.Counter(r.verdict for r in verdicts.values())

    out = []
    out.append('LGREF PHASE 1 — RULE IDENTIFICATION')
    out.append('=' * 72)
    out.append('')
    out.append('VALIDATION against hand-verified boundaries')
    out.append('')
    out.append(score_table(validation_section(games, game_dir)))
    out.append('')
    out.append('ARI is the headline: recall alone is maximised by one giant')
    out.append('cluster and precision by all singletons, so only')
    out.append('chance-corrected agreement penalises both.')
    out.append('')
    out.append('-' * 72)
    out.append('')
    out.append('GRAPH: {} clauses, {} edges'.format(
        len(nodes), graph.edge_count()))
    for kind, count in sorted(graph.summary()['edges_by_type'].items()):
        out.append('   {:<15} {}'.format(kind, count))
    out.append('')
    out.append('CANDIDATES: {} clusters, {} unclustered'.format(
        len(rules), len(dropped)))
    out.append('   verdicts: {}'.format(dict(counts)))
    out.append('')
    out.append('   rule          measurable by ablation')
    out.append('   load_bearing  real, but removing it leaves no playable')
    out.append('                 game — cannot be measured this way')
    out.append('   inert         nothing observable changed')
    out.append('')
    out.append('-' * 72)
    out.append('')
    out.append(rule_listing(rules, verdicts))
    return '\n'.join(out)
