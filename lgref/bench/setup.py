"""Which statements are not ablation candidates, and how well LGREF
tells (Paper A, #358: the user's setup instruction).

Not every statement is a rule one could ablate. The report separates
three kinds, counted per game:

  (a) language   board geometry, coordinate and counting arithmetic
  (b) init       the initial position
  (c) role / outcome   role declarations; terminal and goal statements

(b) and (c) are read from the syntax. (a) is the hard one, and the one
where a mistake matters: a real rule wrongly marked "setup" would never
be ablated, and nothing would report it. So LGREF's language verdict
(`lgref.identify.language`, #202) is scored against the provisional
reference in `references/kinds.yaml` -- precision and recall for "not an
ablation candidate", with every false "language" listed by statement.

Two LGREF verdicts are scored, because the user's order of decision
puts the DEFINITIVE indicator first:

  statement  the statement's head predicate depends on no game state at
             any depth (`state_dependent_predicates`) -- the definitive
             indicator, applied statement by statement
  cluster    production #202: a statement is language when the LGREF
             group that owns it is classified LANGUAGE

Everything not marked language by the definitive indicator is ATTEMPTED
as an ablation (Experiment 1 does), and a failed ablation is reported as
a failed candidate, never relabelled as setup.
"""

import collections
import os

import yaml

from lgref.bench.catalog import game_path
from lgref.identify import language as _language

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS_PATH = os.path.join(HERE, 'references', 'kinds.yaml')
FIXED_TABLES_PATH = os.path.join(HERE, 'references', 'fixed_tables.yaml')
FIXED_TABLES_DOC = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                'docs', 'paper-a', 'fixed-tables.md')

GDL_OUTPUTS = frozenset({'legal', 'next', 'init', 'terminal', 'goal',
                         'role'})


def _syntactic(node):
    if node.head_kind == 'role':
        return 'role'
    if node.head_kind == 'fluent_init':
        return 'init'
    if node.head_kind in ('terminal', 'goal'):
        return 'outcome'
    return None


def reference_kinds(game, nodes):
    """{node id: role | init | outcome | language | rule}."""
    with open(KINDS_PATH) as handle:
        table = yaml.safe_load(handle)['game_kinds'][game]
    language = set(table['language'])
    out = {}
    for node in nodes:
        kind = _syntactic(node)
        if kind is None:
            kind = ('language' if node.head_predicate in language
                    else 'rule')
        out[node.node_id] = kind
    return out


def statement_verdict(nodes):
    """{node id: kind} by the definitive indicator alone."""
    stateful = _language.state_dependent_predicates(nodes)
    out = {}
    for node in nodes:
        kind = _syntactic(node)
        if kind is None:
            static = (node.head_kind in ('fact', 'derived')
                      and node.head_predicate not in stateful)
            kind = 'language' if static else 'rule'
        out[node.node_id] = kind
    return out


def cluster_verdict(nodes, rules):
    """{node id: kind} by production #202 on LGREF's own groups."""
    verdicts = _language.classify_all(nodes, rules)
    language = set()
    for rule in rules:
        if verdicts[rule.rule_id] == _language.LANGUAGE:
            language |= set(rule.clause_ids)
    out = {}
    for node in nodes:
        kind = _syntactic(node)
        if kind is None:
            kind = 'language' if node.node_id in language else 'rule'
        out[node.node_id] = kind
    return out


def score(predicted, reference, nodes):
    """Precision and recall for 'language' (not an ablation candidate),
    over the statements that are neither role, init nor outcome -- those
    are syntactic and cannot be wrong. Lists every rule statement marked
    language: the error the user asked to rule out."""
    pool = [n.node_id for n in nodes if reference[n.node_id]
            in ('language', 'rule')]
    tp = sum(1 for i in pool if predicted[i] == 'language'
             and reference[i] == 'language')
    fp = [i for i in pool if predicted[i] == 'language'
          and reference[i] == 'rule']
    fn = [i for i in pool if predicted[i] == 'rule'
          and reference[i] == 'language']
    return {'precision': (tp / float(tp + len(fp)) if tp + len(fp)
                          else None),
            'recall': tp / float(tp + len(fn)) if tp + len(fn) else None,
            'rules_marked_language': fp, 'language_missed': fn,
            'n_pool': len(pool)}


# ---- the POST-FREEZE amendment (#400): fixed tables as rules ------------

#: Heads through which a fixed table can shape play. `next` is included
#: because the user's own example, Kalah's `ahead`, reaches only `next`.
_OUTPUT_KINDS = ('legal', 'goal', 'terminal', 'fluent_write')


def fixed_table_candidates(nodes):
    """{predicate: sorted output kinds it reaches} for every FIXED TABLE
    that shapes play -- the coded half of decision 3(c).

    A fixed table is a predicate whose every statement is a fact or a
    derived rule and which depends on no game state at any depth. It is
    a candidate when some legal, goal, terminal or next statement reads
    it, directly or through a chain of other fixed tables and helpers.
    Whether the board geometry also uses it is the half no syntactic
    test decides; `references/fixed_tables.yaml` holds that verdict.
    """
    stateful = _language.state_dependent_predicates(nodes)
    defs = collections.defaultdict(list)
    callers = collections.defaultdict(set)
    for node in nodes:
        if node.head_predicate:
            defs[node.head_predicate].append(node)
        for called in node.body_predicates:
            callers[called].add(node)
    tables = {p for p, ns in defs.items()
              if all(n.head_kind in ('fact', 'derived') for n in ns)
              and p not in stateful}
    out = {}
    for table in sorted(tables):
        found, seen, stack = set(), {table}, [table]
        while stack:
            for node in callers[stack.pop()]:
                if node.head_kind in _OUTPUT_KINDS:
                    found.add('next' if node.head_kind == 'fluent_write'
                              else node.head_kind)
                elif node.head_predicate not in seen:
                    seen.add(node.head_predicate)
                    stack.append(node.head_predicate)
        if found:
            out[table] = sorted(found)
    return out


def fixed_table_verdicts(game):
    """{predicate: {'verdict': rule|language, 'why': ...}} for `game`."""
    with open(FIXED_TABLES_PATH) as handle:
        table = yaml.safe_load(handle)['fixed_tables']
    return table.get(game, {})


def amended_reference_kinds(game, nodes):
    """`reference_kinds` with the #400 amendment applied: every fixed
    table judged a RULE is a rule; every fixed table judged LANGUAGE is
    language; everything else is as frozen."""
    frozen = reference_kinds(game, nodes)
    verdicts = fixed_table_verdicts(game)
    out = {}
    for node in nodes:
        kind = frozen[node.node_id]
        verdict = verdicts.get(node.head_predicate)
        if verdict and kind in ('language', 'rule'):
            kind = 'rule' if verdict['verdict'] == 'rule' else 'language'
        out[node.node_id] = kind
    return out


def check_fixed_tables(game, nodes):
    """Problems: a candidate with no verdict, a verdict for a predicate
    that is not a candidate, or a verdict that is neither rule nor
    language."""
    candidates = fixed_table_candidates(nodes)
    verdicts = fixed_table_verdicts(game)
    problems = ['{}: {} has no verdict'.format(game, p)
                for p in candidates if p not in verdicts]
    problems += ['{}: {} is not a fixed table that shapes play'.format(
        game, p) for p in verdicts if p not in candidates]
    problems += ['{}: {} verdict {!r}'.format(game, p, v.get('verdict'))
                 for p, v in verdicts.items()
                 if v.get('verdict') not in ('rule', 'language')]
    return problems


def write_fixed_tables_doc(games, path=FIXED_TABLES_DOC):
    """docs/paper-a/fixed-tables.md: one section per game, each fixed
    table with the outputs it reaches, its verdict and why."""
    from lgref.identify.clauses import load

    lines = ['# Fixed tables: rule or language', '',
             'Paper A, #400. This is the user\'s decision 3, option (c), '
             'a **post-freeze amendment** to the setup/language '
             'reference. The frozen reference (`kinds.yaml`) is kept, and '
             'its numbers are reported beside the amended ones.', '',
             '- **Coded cut** (`lgref.bench.setup.fixed_table_candidates`): '
             'the predicate is a fixed table, meaning it is state-free at '
             'every depth. It is listed only if a legal, goal, terminal or '
             'next statement reads it, directly or through helpers.',
             '- **Judged per entry**: whether the board geometry also uses '
             'it. No syntactic test separates a game\'s content from its '
             'vocabulary. Read as "no other table calls it", the test '
             'would make `opponent`, `forward` and `index` rules.',
             '- **The principle applied**: a table is *language* when it '
             'encodes the board\'s coordinates, adjacency, directions or '
             'arithmetic, or generic vocabulary (players, cards, '
             'opponents) that would be the same in any game on that board. '
             'It is a *rule* when its content is specific to one rule of '
             'this game: which row wins, how a piece moves, the sowing '
             'order, the showdown ranking.',
             '- Every verdict was written by Claude and is provisional. '
             '**The user may veto any entry**: edit '
             '`lgref/bench/references/fixed_tables.yaml` and re-run '
             '`python -m lgref.bench.setup --fixed-tables`.', '']
    for game in games:
        nodes = load(game_path(game))
        candidates = fixed_table_candidates(nodes)
        verdicts = fixed_table_verdicts(game)
        lines.append('## {}'.format(game))
        lines.append('')
        if not candidates:
            lines.append('No fixed table shapes play.')
            lines.append('')
            continue
        lines.append('| table | reaches | verdict | why |')
        lines.append('|---|---|---|---|')
        for table, reach in candidates.items():
            v = verdicts.get(table, {})
            lines.append('| `{}` | {} | **{}** | {} |'.format(
                table, ', '.join(reach), v.get('verdict', 'MISSING'),
                v.get('why', '')))
        lines.append('')
    lines += ['## Effect on metric 11 (setup/language classification)', '',
              'LGREF\'s two verdicts are scored for "language, not an '
              'ablation candidate": the frozen reference first, then the '
              'amended one. The last column lists the rule statements that '
              'the definitive indicator (no state dependence at any depth) '
              'still marks as language. Under the amendment those are '
              'errors.', '', format_amended(report(games)), '']
    with open(path, 'w') as handle:
        handle.write('\n'.join(lines))
    return path


def counts(kinds):
    return dict(collections.Counter(kinds.values()))


def report(games):
    from lgref.identify.clauses import load
    from lgref.identify.cluster import calibrate_resolution, cluster
    from lgref.identify.graph import ClauseGraph

    rows = []
    for game in games:
        nodes = load(game_path(game))
        graph = ClauseGraph(nodes)
        rules, _ = cluster(graph, resolution=calibrate_resolution(graph))
        ref = reference_kinds(game, nodes)
        by_statement = statement_verdict(nodes)
        by_cluster = cluster_verdict(nodes, rules)
        amended = amended_reference_kinds(game, nodes)
        rows.append({'game': game, 'reference': counts(ref),
                     'statement': score(by_statement, ref, nodes),
                     'cluster': score(by_cluster, ref, nodes),
                     'statement_counts': counts(by_statement),
                     'cluster_counts': counts(by_cluster),
                     'amended_reference': counts(amended),
                     'statement_amended': score(by_statement, amended,
                                                nodes),
                     'cluster_amended': score(by_cluster, amended, nodes)})
    return rows


def format_report(rows):
    def fmt(value):
        return 'n/a' if value is None else '{:.2f}'.format(value)

    lines = ['| game | statements: language / init / role / outcome / '
             'rule (reference) | definitive indicator: P / R for '
             '"language" | rules it marks language | #202 cluster '
             'verdict: P / R | rules it marks language |',
             '|---|---|---|---|---|---|']
    for row in rows:
        ref = row['reference']
        lines.append('| {} | {} / {} / {} / {} / {} | {} / {} | {} | '
                     '{} / {} | {} |'.format(
                         row['game'], ref.get('language', 0),
                         ref.get('init', 0), ref.get('role', 0),
                         ref.get('outcome', 0), ref.get('rule', 0),
                         fmt(row['statement']['precision']),
                         fmt(row['statement']['recall']),
                         ', '.join(row['statement']['rules_marked_language'])
                         or 'none',
                         fmt(row['cluster']['precision']),
                         fmt(row['cluster']['recall']),
                         ', '.join(row['cluster']['rules_marked_language'])
                         or 'none'))
    return '\n'.join(lines)


def format_amended(rows):
    """The #400 POST-FREEZE amendment beside the frozen numbers."""
    def fmt(value):
        return 'n/a' if value is None else '{:.2f}'.format(value)

    lines = ['| game | definitive indicator P / R: frozen -> amended | '
             '#202 cluster verdict P / R: frozen -> amended | rules the '
             'indicator marks language (amended) |', '|---|---|---|---|']
    for row in rows:
        a, b = row['statement'], row['statement_amended']
        c, d = row['cluster'], row['cluster_amended']
        lines.append('| {} | {} / {} -> {} / {} | {} / {} -> {} / {} | {} |'
                     .format(row['game'], fmt(a['precision']),
                             fmt(a['recall']), fmt(b['precision']),
                             fmt(b['recall']), fmt(c['precision']),
                             fmt(c['recall']), fmt(d['precision']),
                             fmt(d['recall']),
                             ', '.join(b['rules_marked_language'])
                             or 'none'))
    return '\n'.join(lines)


def main(argv=None):
    import sys
    from lgref.bench.catalog import in_split
    argv = list(argv if argv else sys.argv[1:])
    if argv and argv[0] == '--fixed-tables':
        games = argv[1:] or (list(in_split('dev')) + list(in_split('test')))
        print(write_fixed_tables_doc(games))
        return
    games = argv or in_split('dev')
    rows = report(games)
    print(format_report(rows))
    print()
    print('POST-FREEZE amendment (#400): fixed tables as rules')
    print()
    print(format_amended(rows))


if __name__ == '__main__':
    main()
