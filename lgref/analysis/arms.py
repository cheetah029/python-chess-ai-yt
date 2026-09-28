"""Two arms, and the effects whose sign does not survive both.

THE CONTROL THE DESIGN PROMISED AND NEVER RAN. The measuring agent's
docstring has always said Phase 3 "reports effects under this agent AND
under random play, so that an effect appearing only under one of them is
visible as agent-dependent rather than reported as a property of the
rule". Every sweep ran one agent.

WHAT IT CATCHES. Removing the neutral object raises mean branching by
6.6 turns under an agent that minimises the opponent's legal-turn count,
and LOWERS it by 3.4 under random play. The sign of that effect belongs
to the agent. Nothing in a single-arm run could have said so, and the
number looked perfectly reasonable.

WHAT AGREEMENT DOES AND DOES NOT BUY. Two arms agreeing is not proof
that an effect is agent-independent -- two agents can share a bias. It
is a falsification test that a single arm cannot run at all, and an
effect that fails it must not be reported as a property of a rule.
"""

import collections

from lgref.analysis import profile as profile_mod
from lgref.analysis.effects import effect

Comparison = collections.namedtuple(
    'Comparison', 'variant dimension verdict detail')

AGREES = 'agrees'
DISAGREES = 'sign flips'
ONE_ARM = 'one arm only'
NEITHER = 'neither arm'


def split_by_agent(rows):
    """{agent: rows}. An unlabelled row predates the provenance column."""
    out = collections.defaultdict(list)
    for row in rows:
        out[row.get('agent') or 'unrecorded'].append(row)
    return dict(out)


def _effects(rows, baseline):
    by_variant = collections.defaultdict(list)
    for row in rows:
        by_variant[row['variant']].append(row)
    if baseline not in by_variant:
        return {}
    base = by_variant[baseline]
    out = {}
    for variant in sorted(by_variant):
        if variant == baseline:
            continue
        found = {}
        for metric in sorted(set(profile_mod.DIMENSIONS.values())):
            got = effect(metric, base, by_variant[variant], variant,
                         seed_key='seed_group')
            if got is not None:
                found[metric] = got
        out[variant] = found
    return out


def ladder(rows, order, baseline='full'):
    """The same effect at several playing strengths, in order.

    Two arms answer "is this the agent's doing?". A LADDER answers the
    question the project actually asks: what does the effect tend
    toward as play improves? If the magnitude is monotone and
    flattening, the limit can be bounded by extrapolation, and the
    claim becomes "the effect tends to x as play improves" rather than
    "the effect was x under our agent".

    `order` names the arms weakest first -- accuracy against exact play
    on a solvable game is the ordering used, not a guess. Arms missing
    from the data are skipped rather than assumed.

    See `docs/spec/objectivity.md`. This is Route 3, and it is the one
    that converts a conditional result into a measured trend.
    """
    arms = split_by_agent(rows)
    present = [name for name in order if name in arms]
    effects = {name: _effects(arms[name], baseline) for name in present}

    out = collections.OrderedDict()
    for variant in sorted({v for e in effects.values() for v in e}):
        for dimension, metric in profile_mod.DIMENSIONS.items():
            series = []
            for name in present:
                entry = effects[name].get(variant, {}).get(metric)
                series.append(
                    (name, entry.cohens_d
                     if entry is not None and entry.verdict == 'effect'
                     else None))
            if any(d is not None for _n, d in series):
                out[(variant, dimension)] = series
    return present, out


def trend(series):
    """Is this effect settling down as the agent gets stronger?

    Three answers and no fourth. `settling` means the steps between
    consecutive strengths are shrinking, which is what licenses an
    extrapolation. `unstable` means they are not, and that instability
    is the finding rather than something to average away. `too few` is
    the honest answer below three measured points, because two points
    always look like a trend.
    """
    values = [d for _n, d in series if d is not None]
    if len(values) < 3:
        return 'too few'
    steps = [abs(b - a) for a, b in zip(values, values[1:])]
    return 'settling' if steps[-1] <= steps[0] else 'unstable'


def compare(rows, strong='mcts', control='random', baseline='full'):
    """Every (variant, dimension) cell, judged across the two arms."""
    arms = split_by_agent(rows)
    if strong not in arms or control not in arms:
        raise SystemExit(
            'need both arms; found {}'.format(sorted(arms)))
    left = _effects(arms[strong], baseline)
    right = _effects(arms[control], baseline)

    out = []
    for variant in sorted(set(left) | set(right)):
        for dimension, metric in profile_mod.DIMENSIONS.items():
            a = left.get(variant, {}).get(metric)
            b = right.get(variant, {}).get(metric)
            real = [e for e in (a, b) if e is not None
                    and e.verdict == 'effect']
            if not real:
                out.append(Comparison(variant, dimension, NEITHER, ''))
                continue
            if len(real) == 1:
                which = strong if real[0] is a else control
                out.append(Comparison(
                    variant, dimension, ONE_ARM,
                    'only under {} (d={:+.2f})'.format(
                        which, real[0].cohens_d)))
                continue
            if (a.cohens_d > 0) == (b.cohens_d > 0):
                out.append(Comparison(
                    variant, dimension, AGREES,
                    '{} d={:+.2f}, {} d={:+.2f}'.format(
                        strong, a.cohens_d, control, b.cohens_d)))
            else:
                out.append(Comparison(
                    variant, dimension, DISAGREES,
                    '{} d={:+.2f} but {} d={:+.2f}'.format(
                        strong, a.cohens_d, control, b.cohens_d)))
    return out


def report(comparisons, strong='mcts', control='random'):
    counts = collections.Counter(c.verdict for c in comparisons)
    lines = ['AGENT AGREEMENT — which effects survive a second player',
             '',
             'An effect whose SIGN differs between agents is a property of',
             'the agent. Agreement is not proof of independence -- two',
             'agents can share a bias -- but disagreement is disproof, and',
             'a single-arm run cannot run the test at all.',
             '']
    for verdict in (DISAGREES, AGREES, ONE_ARM, NEITHER):
        rows = [c for c in comparisons if c.verdict == verdict]
        if not rows:
            continue
        lines.append('  {} ({}):'.format(verdict.upper(), len(rows)))
        for c in rows if verdict != NEITHER else []:
            lines.append('      {:<26} {:<20} {}'.format(
                c.variant[:25], c.dimension, c.detail))
        lines.append('')
    trustworthy = counts[AGREES]
    total = sum(counts.values()) - counts[NEITHER]
    lines.append('{} of {} measured cells agree across arms.'.format(
        trustworthy, total))
    if counts[DISAGREES]:
        lines.append('{} cells FLIP SIGN and must not be reported as '
                     'properties of a rule.'.format(counts[DISAGREES]))
    return '\n'.join(lines)
