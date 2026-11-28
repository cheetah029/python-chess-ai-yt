"""Show a grouping: every group, every statement, its line in the file.

Issue #396. The user asked to SEE the groupings LGREF produces, next to
the random grouping it is compared with, with each statement's line
number in the `.gdl` file, so a claim like "random groups beat LGREF"
can be checked by eye.

    python -m lgref.bench.show_groups --split test --compare random_matched
    python -m lgref identify --gdl lgref/bench/games/checkers_4x4.gdl \\
        --show-groups --compare random_matched

Each game gets two views, printed and written to
`docs/paper-a/groupings/<game>.md`:

  side by side  one row per statement: its line, its text, and the
                group(s) each method puts it in ('-' for none)
  by group      each method's groups in turn, with every member's line
                and text, and whether it is shared with another group

The random grouping shown is exactly the one Experiment 1 scored: LGREF's
grouping at the same seed, with statements permuted by that seed.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(REPO, 'docs', 'paper-a', 'groupings')


def statement_lines(path):
    """[line number] per statement, in `load` order, or None for a
    statement that could not be placed (a statement spanning lines)."""
    from ggp.infix import parse_infix

    with open(path) as handle:
        text = handle.read()
    forms = parse_infix(text)
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('%'):
            continue
        try:
            found = parse_infix(stripped)
        except Exception:                          # noqa: BLE001
            return [None] * len(forms)
        lines.extend([number] * len(found))
    if len(lines) != len(forms):
        return [None] * len(forms)
    return lines


def _texts(nodes):
    from ggp.infix import forms_to_infix_lines
    return [' '.join(forms_to_infix_lines([n.raw])) for n in nodes]


def _labels(grouping):
    """{node id: 'G03'-style labels}, and the label of each group."""
    names = ['G{:02d}'.format(i) for i in range(len(grouping.groups))]
    member = {n: [] for n in grouping.node_ids}
    for name, group in zip(names, grouping.groups):
        for node in sorted(group):
            member[node].append(name)
    return member, names


def render(title, path, nodes, groupings):
    """Markdown for one description. `groupings` is an ordered
    {label: Grouping} over `nodes`."""
    lines_of = statement_lines(path)
    texts = _texts(nodes)
    ids = [n.node_id for n in nodes]
    labelled = {label: _labels(g) for label, g in groupings.items()}
    out = ['# {} -- groupings'.format(title), '',
           'File: `{}`. Line numbers are lines of that file.'.format(
               os.path.relpath(path, REPO)), '']
    for label, grouping in groupings.items():
        out.append('- **{}**: {} groups, {} statements in no group'.format(
            label, len(grouping.groups), len(grouping.unclustered())))
    out += ['', '## Side by side', '',
            '| line | statement | ' + ' | '.join(groupings) + ' |',
            '|---|---|' + '---|' * len(groupings)]
    for i, node_id in enumerate(ids):
        cells = [', '.join(labelled[label][0][node_id]) or '-'
                 for label in groupings]
        out.append('| {} | `{}` | {} |'.format(
            lines_of[i] if lines_of[i] is not None else '?',
            texts[i].replace('|', '\\|'), ' | '.join(cells)))
    for label, grouping in groupings.items():
        member, names = labelled[label]
        out += ['', '## {} by group'.format(label), '']
        for name, group in zip(names, grouping.groups):
            out.append('### {} {} ({} statements)'.format(
                label, name, len(group)))
            out.append('')
            for i, node_id in enumerate(ids):
                if node_id not in group:
                    continue
                others = [g for g in member[node_id] if g != name]
                out.append('- line {}: `{}`{}'.format(
                    lines_of[i] if lines_of[i] is not None else '?',
                    texts[i], ' (also in {})'.format(', '.join(others))
                    if others else ''))
            out.append('')
        loose = [i for i, n in enumerate(ids) if not member[n]]
        if loose:
            out.append('### {}: statements in no group'.format(label))
            out.append('')
            for i in loose:
                out.append('- line {}: `{}`'.format(
                    lines_of[i] if lines_of[i] is not None else '?',
                    texts[i]))
            out.append('')
    return '\n'.join(out) + '\n'


#: Short names the command line accepts.
ALIASES = {'random': 'random_matched'}


def groupings_for(nodes, methods, seed=0):
    from lgref.bench.experiments import grouping_for
    methods = [ALIASES.get(m, m) for m in methods]
    return {m: grouping_for(m, nodes, seed) for m in methods}


def show(path, methods=('lgref',), seed=0, title=None, out_dir=None):
    """Render `path`'s groupings; write the file when `out_dir` is
    given. Returns (markdown, written path or None)."""
    from lgref.identify.clauses import load

    nodes = load(path)
    title = title or os.path.splitext(os.path.basename(path))[0]
    text = render(title, path, nodes, groupings_for(nodes, methods, seed))
    written = None
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        written = os.path.join(out_dir, title + '.md')
        with open(written, 'w') as handle:
            handle.write(text)
    return text, written


def main(argv=None):
    from lgref.bench.catalog import existing, game_path

    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--split', default='')
    parser.add_argument('--games', default='')
    parser.add_argument('--compare', default='random_matched')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--out', default=OUT_DIR)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args(argv)
    games = (args.games.split(',') if args.games
             else existing(args.split or None))
    methods = ['lgref'] + [m for m in args.compare.split(',') if m]
    for game in games:
        text, written = show(game_path(game), methods, args.seed, game,
                             args.out)
        if not args.quiet:
            sys.stdout.write(text)
        sys.stderr.write('wrote {}\n'.format(written))


if __name__ == '__main__':
    main()
